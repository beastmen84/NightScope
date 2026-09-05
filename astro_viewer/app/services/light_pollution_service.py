"""Resolve Bortle sky quality from VIIRS, cache, or local fallback data."""

from __future__ import annotations

import csv
import io
import logging
import math
import re
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Callable, Protocol

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.earthdata_credentials import (
    EarthdataCredentialStore,
    temporary_earthdata_netrc,
)
from astro_viewer.app.services.localization import tr

try:
    import h5py
    import numpy as np
except Exception:  # pragma: no cover - optional runtime dependency fallback
    h5py = None
    np = None


logger = logging.getLogger(__name__)


BORTLE_LIMITING_MAGNITUDE = {
    1: 7.6,
    2: 7.1,
    3: 6.6,
    4: 6.1,
    5: 5.6,
    6: 5.1,
    7: 4.6,
    8: 4.1,
    9: 3.8,
}

BORTLE_SKY_BRIGHTNESS = {
    1: 22.0,
    2: 21.7,
    3: 21.3,
    4: 20.8,
    5: 20.1,
    6: 19.4,
    7: 18.8,
    8: 18.1,
    9: 17.5,
}

VIIRS_CACHE_RECHECK_INTERVAL = timedelta(days=7)
VIIRS_CACHE_REUSE_RADIUS_KM = 0.5


class ViirsCacheState(str, Enum):
    MISSING = "missing"
    FRESH = "fresh"
    STALE = "stale"


class LightPollutionService:
    """Resolve sky quality from real local datasets or NASA VIIRS."""

    def __init__(
        self,
        repository: SkyQualityRepository,
        data_dir: Path | None = None,
        earthdata_credentials: EarthdataCredentialStore | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
        viirs_cache_recheck_interval: timedelta = VIIRS_CACHE_RECHECK_INTERVAL,
        viirs_cache_reuse_radius_km: float = VIIRS_CACHE_REUSE_RADIUS_KM,
    ):
        self._repository = repository
        self._clock = clock or (lambda: datetime.now(UTC))
        self._viirs_cache_recheck_interval = viirs_cache_recheck_interval
        self._viirs_cache_reuse_radius_km = max(0.0, float(viirs_cache_reuse_radius_km))
        self.last_remote_error = ""
        deleted_estimates = self._repository.delete_non_viirs_estimates()
        if deleted_estimates:
            logger.info(
                "Removed %s non-VIIRS sky-quality cache entries.",
                deleted_estimates,
            )
        dataset_paths = _candidate_dataset_paths(data_dir)
        self._remote_providers: list[LightPollutionProvider] = [
            NasaViirsBlackMarbleProvider(earthdata_credentials),
        ]
        self._providers: list[LightPollutionProvider] = [
            WorldAtlasCsvProvider(dataset_paths),
        ]

    def sky_quality(self, location: ObserverLocation) -> SkyQuality | None:
        viirs_cached = self._cached_viirs_row(location)
        if viirs_cached:
            return self._to_model(viirs_cached)
        return self._provider_quality(location)

    def viirs_cache_state(self, location: ObserverLocation) -> ViirsCacheState:
        cached = self._cached_viirs_row(location)
        return self._viirs_cache_state(cached)

    def _viirs_cache_state(self, cached: dict | None) -> ViirsCacheState:
        if not cached or not self._is_viirs_cache(cached):
            return ViirsCacheState.MISSING
        updated_at = _parse_cache_datetime(cached.get("updated_at"))
        if updated_at is None:
            return ViirsCacheState.STALE
        age = self._now() - updated_at
        if timedelta(0) <= age <= self._viirs_cache_recheck_interval:
            return ViirsCacheState.FRESH
        return ViirsCacheState.STALE

    def remote_sky_quality(self, location: ObserverLocation) -> SkyQuality | None:
        self.last_remote_error = ""
        key = self._location_key(location)
        cached = self._cached_viirs_row(location)
        if cached and self._viirs_cache_state(cached) is ViirsCacheState.FRESH:
            return self._to_model(cached)

        for provider in self._remote_providers:
            try:
                quality = provider.lookup(location)
            except Exception:
                logger.warning("%s failed during remote sky-quality lookup.", provider.name, exc_info=True)
                self.last_remote_error = tr(
                    "Dati NASA VIIRS non disponibili al momento."
                )
                continue
            if not quality:
                provider_error = getattr(provider, "last_error", "")
                if isinstance(provider_error, str) and provider_error:
                    self.last_remote_error = provider_error
                continue
            self._repository.set(
                key,
                quality.bortle_class,
                quality.limiting_magnitude,
                quality.sky_brightness,
                quality.source,
                quality.confidence,
                self._now().isoformat(),
            )
            return quality
        return None

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        return now.astimezone(UTC)

    def _cached_viirs_row(self, location: ObserverLocation) -> dict | None:
        exact_key = self._location_key(location)
        exact = self._repository.get(exact_key)
        if exact and self._is_viirs_cache(exact):
            return exact

        nearest = None
        nearest_distance = math.inf
        for row in self._repository.list_estimates():
            if not self._is_viirs_cache(row):
                continue
            coordinates = self._coordinates_from_location_key(row.get("location_key"))
            if coordinates is None:
                continue
            distance = _distance_km(
                location.latitude,
                location.longitude,
                coordinates[0],
                coordinates[1],
            )
            if distance <= self._viirs_cache_reuse_radius_km and distance < nearest_distance:
                nearest = row
                nearest_distance = distance
        return nearest

    def _provider_quality(self, location: ObserverLocation) -> SkyQuality | None:
        for provider in self._providers:
            quality = provider.lookup(location)
            if quality:
                return quality
        return None

    @staticmethod
    def _description(bortle: int) -> str:
        return _description(bortle)

    @staticmethod
    def _location_key(location: ObserverLocation) -> str:
        return f"{location.latitude:.3f}:{location.longitude:.3f}:{location.city.lower()}"

    @staticmethod
    def _coordinates_from_location_key(value: object) -> tuple[float, float] | None:
        if not isinstance(value, str):
            return None
        parts = value.split(":", 2)
        if len(parts) < 2:
            return None
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None

    @staticmethod
    def _to_model(row: dict) -> SkyQuality:
        viirs_radiance, viirs_observation_count = _viirs_details_from_source(row.get("source") or "")
        return SkyQuality(
            bortle_class=int(row["bortle_class"]),
            limiting_magnitude=float(row["limiting_magnitude"]),
            sky_brightness=float(row["sky_brightness"]),
            source=row["source"],
            description=_description(int(row["bortle_class"])),
            confidence=row.get("confidence") or "medium",
            viirs_radiance=viirs_radiance,
            viirs_observation_count=viirs_observation_count,
        )

    @staticmethod
    def _is_viirs_cache(row: dict) -> bool:
        return "NASA Black Marble VNP46A3" in (row.get("source") or "")


def _parse_cache_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class LightPollutionProvider(Protocol):
    name: str

    def lookup(self, location: ObserverLocation) -> SkyQuality | None:
        ...


class CsvSkyQualityProvider:
    name = "CsvSkyQualityProvider"

    def __init__(self, dataset_paths: Iterable[Path | None], default_source: str, default_confidence: str):
        self._records = _load_light_pollution_records(dataset_paths, default_source, default_confidence)

    def lookup(self, location: ObserverLocation) -> SkyQuality | None:
        record = _nearest_record(location, self._records)
        if not record:
            return None
        return SkyQuality(
            bortle_class=record["bortle_class"],
            limiting_magnitude=record["limiting_magnitude"],
            sky_brightness=record["sky_brightness"],
            source=f"Fonte: {record['source']}",
            description=_description(record["bortle_class"]),
            confidence=record["confidence"],
        )


class WorldAtlasCsvProvider(CsvSkyQualityProvider):
    name = "WorldAtlasCsvProvider"

    def __init__(self, dataset_paths: Iterable[Path | None]):
        super().__init__(
            dataset_paths,
            default_source="World Atlas / VIIRS preprocessed local dataset",
            default_confidence="high",
        )


@dataclass(frozen=True)
class ViirsTile:
    h: int
    v: int
    row: int
    col: int

    @property
    def identifier(self) -> str:
        return f"h{self.h:02d}v{self.v:02d}"


@dataclass(frozen=True)
class ViirsGranule:
    directory_url: str
    file_name: str
    product_month: str


class _ViirsProviderError(RuntimeError):
    pass


class NasaViirsBlackMarbleProvider:
    name = "NasaViirsBlackMarbleProvider"

    BASE_URL = "https://ladsweb.modaps.eosdis.nasa.gov/opendap/RemoteResources/laads/allData"
    COLLECTION = "5200"
    PRODUCT = "VNP46A3"
    VERSION = "002"
    PIXELS_PER_TILE = 2400
    GRID_PATH = "/HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data_Fields"
    FIELD_RADIANCE = "AllAngle_Composite_Snow_Free"
    FIELD_OBSERVATIONS = "AllAngle_Composite_Snow_Free_Num"
    FIELD_QUALITY = "AllAngle_Composite_Snow_Free_Quality"

    def __init__(self, credentials: EarthdataCredentialStore | None, months_to_search: int = 36):
        self._credentials = credentials
        self._months_to_search = months_to_search
        self.last_error = ""

    def lookup(self, location: ObserverLocation) -> SkyQuality | None:
        self.last_error = ""
        if h5py is None or np is None:
            self.last_error = tr("Librerie HDF5 non disponibili.")
            return None
        credentials = self._verified_credentials()
        if not credentials:
            self.last_error = tr("Credenziali Earthdata non verificate.")
            return None

        username, password = credentials
        try:
            session_source = self._session(username, password)
            if hasattr(session_source, "__enter__"):
                with session_source as session:
                    quality = self._lookup_with_session(session, location)
            else:
                quality = self._lookup_with_session(session_source, location)
        except _ViirsProviderError as exc:
            self.last_error = str(exc)
            return None
        if quality:
            return quality

        self.last_error = tr("Dati NASA VIIRS non disponibili per questa posizione.")
        return None

    def _lookup_with_session(self, session: requests.Session, location: ObserverLocation) -> SkyQuality | None:
        tile = self._tile_for_location(location)
        for month_start in self._candidate_months(datetime.now(UTC).date(), self._months_to_search):
            granule = self._find_granule(session, tile, month_start)
            if not granule:
                continue
            payload = self._fetch_subset(session, granule, tile)
            if not payload:
                continue
            quality = self._parse_subset(payload, granule.product_month)
            if quality:
                return quality
        return None

    def _verified_credentials(self) -> tuple[str, str] | None:
        if not self._credentials:
            return None
        state = self._credentials.state()
        if not state.connection_verified:
            return None
        password = self._credentials.password()
        if not state.username or not password:
            return None
        return state.username, password

    def _find_granule(self, session: requests.Session, tile: ViirsTile, month_start: date) -> ViirsGranule | None:
        doy = month_start.timetuple().tm_yday
        directory_url = (
            f"{self.BASE_URL}/{self.COLLECTION}/{self.PRODUCT}/{month_start.year}/{doy:03d}/"
        )
        try:
            response = session.get(directory_url, timeout=(5, 12), allow_redirects=True)
        except requests.RequestException as exc:
            logger.info("VIIRS directory lookup failed for %s: %s", directory_url, exc)
            raise _ViirsProviderError(
                tr(
                    "Connessione NASA VIIRS non riuscita: {error_type}.",
                    error_type=exc.__class__.__name__,
                )
            ) from exc
        if response.status_code != 200:
            if response.status_code == 404:
                return None
            raise _ViirsProviderError(self._http_error_message(response.status_code))
        pattern = re.compile(
            rf"({self.PRODUCT}\.A{month_start.year}{doy:03d}\.{tile.identifier}\.{self.VERSION}\.\d+\.h5)"
        )
        matches = sorted(set(pattern.findall(response.text)))
        if not matches:
            return None
        return ViirsGranule(
            directory_url=directory_url,
            file_name=matches[-1],
            product_month=f"{month_start.year}-{month_start.month:02d}",
        )

    def _fetch_subset(self, session: requests.Session, granule: ViirsGranule, tile: ViirsTile) -> bytes | None:
        row_start, row_end = self._window(tile.row)
        col_start, col_end = self._window(tile.col)
        subset = f"[{row_start}:1:{row_end}][{col_start}:1:{col_end}]"
        fields = [
            f"{self.GRID_PATH}/{self.FIELD_OBSERVATIONS}{subset}",
            f"{self.GRID_PATH}/{self.FIELD_RADIANCE}{subset}",
            f"{self.GRID_PATH}/{self.FIELD_QUALITY}{subset}",
        ]
        constraint = "/HDFEOS/ADDITIONAL;" + ";".join(fields)
        url = f"{granule.directory_url}{granule.file_name}.dap.nc4"
        try:
            response = session.get(url, params={"dap4.ce": constraint}, timeout=(8, 45), allow_redirects=True)
        except requests.RequestException as exc:
            logger.info("VIIRS subset lookup failed for %s: %s", url, exc)
            raise _ViirsProviderError(
                tr(
                    "Connessione NASA VIIRS non riuscita: {error_type}.",
                    error_type=exc.__class__.__name__,
                )
            ) from exc
        if response.status_code != 200:
            if response.status_code == 404:
                return None
            raise _ViirsProviderError(self._http_error_message(response.status_code))
        if not response.content:
            return None
        return response.content

    @staticmethod
    def _http_error_message(status_code: int) -> str:
        if status_code in (401, 403):
            return tr(
                "Autenticazione Earthdata non riuscita durante il recupero VIIRS."
            )
        if status_code == 429:
            return tr(
                "NASA VIIRS ha applicato un limite di traffico. Riprova più tardi."
            )
        return tr(
            "NASA VIIRS ha risposto con HTTP {status_code}.",
            status_code=status_code,
        )

    def _parse_subset(self, payload: bytes, product_month: str) -> SkyQuality | None:
        """Read the configured VNP46A3 collection-002 snow-free composite.

        The median radiance is upward satellite-observed nW/(cm^2 sr), not
        ground-based zenith sky brightness. Bortle, SQM-like brightness and NELM
        below are empirical projections; confidence describes pixel quality and
        observation count, not a calibration of those derived estimates.
        Do not substitute collection-001 packed integers without decoding their
        scale/fill metadata: the product formats are not interchangeable.
        """

        with h5py.File(io.BytesIO(payload), "r") as data:
            group = data["HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data_Fields"]
            radiance = np.asarray(group[self.FIELD_RADIANCE][()], dtype=float)
            observations = np.asarray(group[self.FIELD_OBSERVATIONS][()], dtype=float)
            quality = np.asarray(group[self.FIELD_QUALITY][()], dtype=float)

        valid = np.isfinite(radiance) & (radiance >= 0) & np.isfinite(observations) & (observations > 0)
        good = valid & (quality == 0)
        usable = good if bool(np.any(good)) else valid & (quality <= 2)
        if not bool(np.any(usable)):
            return None

        radiance_value = float(np.nanmedian(radiance[usable]))
        observation_count = int(round(float(np.nanmedian(observations[usable]))))
        quality_code = int(round(float(np.nanmedian(quality[usable]))))
        bortle = _bortle_from_viirs_radiance(radiance_value)
        confidence = "high" if quality_code == 0 and observation_count >= 3 else "medium"
        return SkyQuality(
            bortle_class=bortle,
            limiting_magnitude=BORTLE_LIMITING_MAGNITUDE[bortle],
            sky_brightness=BORTLE_SKY_BRIGHTNESS[bortle],
            source=(
                f"Fonte: NASA Black Marble VNP46A3 {product_month} "
                f"(radiance {radiance_value:.2f} nW/cm^2 sr, obs {observation_count})"
            ),
            description=_description(bortle),
            confidence=confidence,
            viirs_radiance=round(radiance_value, 2),
            viirs_observation_count=observation_count,
        )

    @classmethod
    def _tile_for_location(cls, location: ObserverLocation) -> ViirsTile:
        h = math.floor((location.longitude + 180.0) / 10.0)
        v = math.floor((90.0 - location.latitude) / 10.0)
        h = max(0, min(35, h))
        v = max(0, min(17, v))
        west = -180.0 + h * 10.0
        north = 90.0 - v * 10.0
        pixels_per_degree = cls.PIXELS_PER_TILE / 10.0
        col = math.floor((location.longitude - west) * pixels_per_degree)
        row = math.floor((north - location.latitude) * pixels_per_degree)
        return ViirsTile(h, v, max(0, min(cls.PIXELS_PER_TILE - 1, row)), max(0, min(cls.PIXELS_PER_TILE - 1, col)))

    @classmethod
    def _window(cls, index: int, radius: int = 1) -> tuple[int, int]:
        return max(0, index - radius), min(cls.PIXELS_PER_TILE - 1, index + radius)

    @staticmethod
    def _candidate_months(reference_date: date, count: int) -> Iterable[date]:
        year = reference_date.year
        month = reference_date.month
        for _ in range(count):
            yield date(year, month, 1)
            month -= 1
            if month == 0:
                month = 12
                year -= 1

    @staticmethod
    @contextmanager
    def _session(username: str, password: str):
        with temporary_earthdata_netrc(
            username,
            password,
            prefix="nightscope-viirs-",
        ):
            session = NasaViirsBlackMarbleProvider._requests_session()
            try:
                yield session
            finally:
                session.close()

    @staticmethod
    def _requests_session() -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=2,
            connect=2,
            read=1,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=2, pool_maxsize=2))
        session.headers.update({"User-Agent": "NightScope NASA VIIRS light pollution lookup", "Accept": "*/*"})
        session.trust_env = True
        return session


def _candidate_dataset_paths(data_dir: Path | None) -> list[Path]:
    if not data_dir:
        return []
    return [
        data_dir / "light_pollution_world_atlas.csv",
        data_dir / "light_pollution_viirs_samples.csv",
    ]


def _load_light_pollution_records(
    dataset_paths: Iterable[Path | None],
    default_source: str,
    default_confidence: str,
) -> list[dict]:
    records = []
    for dataset_path in dataset_paths:
        if not dataset_path or not dataset_path.exists():
            continue
        records.extend(_read_light_pollution_records(dataset_path, default_source, default_confidence))
    return records


def _read_light_pollution_records(dataset_path: Path, default_source: str, default_confidence: str) -> list[dict]:
    records = []
    with dataset_path.open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            record = _normalize_record(row, default_source, default_confidence)
            if record:
                records.append(record)
    return records


def _normalize_record(row: dict, default_source: str, default_confidence: str) -> dict | None:
    latitude = _row_float(row, "latitude", "lat")
    longitude = _row_float(row, "longitude", "lon", "lng")
    if latitude is None or longitude is None:
        return None

    sky_brightness = _row_float(row, "sky_brightness", "sqm_mag_arcsec2", "mag_arcsec2", "sqm")
    bortle = _row_int(row, "bortle_class", "bortle")
    if bortle is None and sky_brightness is not None:
        bortle = _bortle_from_sky_brightness(sky_brightness)
    if bortle is None:
        return None
    bortle = max(1, min(9, bortle))

    limiting_magnitude = _row_float(row, "limiting_magnitude", "nelm")
    if limiting_magnitude is None:
        limiting_magnitude = BORTLE_LIMITING_MAGNITUDE[bortle]
    if sky_brightness is None:
        sky_brightness = BORTLE_SKY_BRIGHTNESS[bortle]

    radius_km = _row_float(row, "radius_km", "cell_size_km")
    if radius_km is None:
        radius_km = 5.0

    return {
        "latitude": latitude,
        "longitude": longitude,
        "radius_km": radius_km,
        "bortle_class": bortle,
        "sky_brightness": sky_brightness,
        "limiting_magnitude": limiting_magnitude,
        "source": row.get("source") or default_source,
        "confidence": row.get("confidence") or default_confidence,
    }


def _row_float(row: dict, *keys: str) -> float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return float(str(value).replace(",", "."))
        except ValueError:
            continue
    return None


def _row_int(row: dict, *keys: str) -> int | None:
    value = _row_float(row, *keys)
    return int(round(value)) if value is not None else None


def _bortle_from_sky_brightness(sky_brightness: float) -> int:
    if sky_brightness >= 21.75:
        return 1
    if sky_brightness >= 21.5:
        return 2
    if sky_brightness >= 21.0:
        return 3
    if sky_brightness >= 20.4:
        return 4
    if sky_brightness >= 19.5:
        return 5
    if sky_brightness >= 18.9:
        return 6
    if sky_brightness >= 18.3:
        return 7
    if sky_brightness >= 17.8:
        return 8
    return 9


def _bortle_from_viirs_radiance(radiance: float) -> int:
    if radiance < 0.2:
        return 2
    if radiance < 1.0:
        return 3
    if radiance < 5.0:
        return 4
    if radiance < 15.0:
        return 5
    if radiance < 40.0:
        return 6
    if radiance < 100.0:
        return 7
    if radiance < 300.0:
        return 8
    return 9


def _viirs_details_from_source(source: str) -> tuple[float | None, int | None]:
    match = re.search(r"radiance\s+([0-9]+(?:\.[0-9]+)?)\s+nW/cm\^2\s+sr,\s+obs\s+(\d+)", source)
    if not match:
        return None, None
    try:
        return round(float(match.group(1)), 2), int(match.group(2))
    except ValueError:
        return None, None


def _nearest_record(location: ObserverLocation, records: list[dict]) -> dict | None:
    best_record = None
    best_distance = math.inf
    for record in records:
        distance = _distance_km(location.latitude, location.longitude, record["latitude"], record["longitude"])
        if distance <= record["radius_km"] and distance < best_distance:
            best_distance = distance
            best_record = record
    return best_record


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _description(bortle: int) -> str:
    if bortle <= 2:
        return tr("Cielo buio eccellente")
    if bortle <= 4:
        return tr("Cielo rurale")
    if bortle <= 6:
        return tr("Cielo suburbano")
    if bortle <= 8:
        return tr("Cielo urbano")
    return tr("Cielo urbano centrale")
