from __future__ import annotations

import csv
import io
import logging
import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Protocol

import requests

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.earthdata_credentials import EarthdataCredentialStore

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

LEGACY_CACHE_SOURCES = {
    "Fonte: stima offline NightScope",
}
LEGACY_CACHE_MARKERS = (
    "pending World Atlas import",
)


class LightPollutionService:
    """Provider-backed sky quality lookup with cache and offline fallback."""

    def __init__(
        self,
        repository: SkyQualityRepository,
        dataset_path: Path | None = None,
        earthdata_credentials: EarthdataCredentialStore | None = None,
    ):
        self._repository = repository
        dataset_paths = _candidate_dataset_paths(dataset_path)
        self._remote_providers: list[LightPollutionProvider] = [
            NasaViirsBlackMarbleProvider(earthdata_credentials),
        ]
        self._providers: list[LightPollutionProvider] = [
            WorldAtlasCsvProvider(dataset_paths),
            LocalSkyQualityCsvProvider([dataset_path] if dataset_path else []),
            OfflineEstimateProvider(),
        ]

    def sky_quality(self, location: ObserverLocation) -> SkyQuality:
        key = self._location_key(location)
        cached = self._repository.get(key)
        if cached and not self._is_stale_cache(cached):
            return self._to_model(cached)

        quality = self._provider_quality(location)
        self._repository.set(
            key,
            quality.bortle_class,
            quality.limiting_magnitude,
            quality.sky_brightness,
            quality.source,
            quality.confidence,
            datetime.now(UTC).isoformat(),
        )
        return quality

    def remote_sky_quality(self, location: ObserverLocation) -> SkyQuality | None:
        key = self._location_key(location)
        cached = self._repository.get(key)
        if cached and self._is_viirs_cache(cached):
            return self._to_model(cached)

        for provider in self._remote_providers:
            try:
                quality = provider.lookup(location)
            except Exception:
                logger.warning("%s failed during remote sky-quality lookup.", provider.name, exc_info=True)
                continue
            if not quality:
                continue
            self._repository.set(
                key,
                quality.bortle_class,
                quality.limiting_magnitude,
                quality.sky_brightness,
                quality.source,
                quality.confidence,
                datetime.now(UTC).isoformat(),
            )
            return quality
        return None

    def _provider_quality(self, location: ObserverLocation) -> SkyQuality:
        for provider in self._providers:
            quality = provider.lookup(location)
            if quality:
                return quality
        return OfflineEstimateProvider().lookup(location)

    @staticmethod
    def _description(bortle: int) -> str:
        return _description(bortle)

    @staticmethod
    def _location_key(location: ObserverLocation) -> str:
        return f"{location.latitude:.3f}:{location.longitude:.3f}:{location.city.lower()}"

    @staticmethod
    def _to_model(row: dict) -> SkyQuality:
        return SkyQuality(
            bortle_class=int(row["bortle_class"]),
            limiting_magnitude=float(row["limiting_magnitude"]),
            sky_brightness=float(row["sky_brightness"]),
            source=row["source"],
            description=_description(int(row["bortle_class"])),
            confidence=row.get("confidence") or "medium",
        )

    @staticmethod
    def _is_stale_cache(row: dict) -> bool:
        source = row.get("source") or ""
        return source in LEGACY_CACHE_SOURCES or any(marker in source for marker in LEGACY_CACHE_MARKERS)

    @staticmethod
    def _is_viirs_cache(row: dict) -> bool:
        return "NASA Black Marble VNP46A3" in (row.get("source") or "")


class LightPollutionProvider(Protocol):
    name: str

    def lookup(self, location: ObserverLocation) -> SkyQuality | None:
        ...


class OfflineEstimateProvider:
    name = "OfflineEstimateProvider"

    def lookup(self, location: ObserverLocation) -> SkyQuality:
        if location.city.lower().startswith("coordinate"):
            bortle = 5
        else:
            bortle = 6
        return SkyQuality(
            bortle_class=bortle,
            limiting_magnitude=BORTLE_LIMITING_MAGNITUDE[bortle],
            sky_brightness=BORTLE_SKY_BRIGHTNESS[bortle],
            source="Fonte: stima offline NightScope (nessun dataset locale)",
            description=_description(bortle),
            confidence="low",
        )


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


class LocalSkyQualityCsvProvider(CsvSkyQualityProvider):
    name = "LocalSkyQualityCsvProvider"

    def __init__(self, dataset_paths: Iterable[Path | None]):
        super().__init__(
            dataset_paths,
            default_source="NightScope local sky-quality seed",
            default_confidence="medium",
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
            self.last_error = "Librerie HDF5 non disponibili."
            return None
        credentials = self._verified_credentials()
        if not credentials:
            self.last_error = "Credenziali Earthdata non verificate."
            return None

        username, password = credentials
        session = self._session(username, password)
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

        self.last_error = "Dati NASA VIIRS non disponibili per questa posizione."
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
        except requests.RequestException:
            logger.info("VIIRS directory lookup failed for %s", directory_url, exc_info=True)
            return None
        if response.status_code != 200:
            return None
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
        except requests.RequestException:
            logger.info("VIIRS subset lookup failed for %s", url, exc_info=True)
            return None
        if response.status_code != 200 or not response.content:
            return None
        return response.content

    def _parse_subset(self, payload: bytes, product_month: str) -> SkyQuality | None:
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
    def _session(username: str, password: str) -> requests.Session:
        session = requests.Session()
        session.auth = (username, password)
        session.headers.update({"User-Agent": "NightScope NASA VIIRS light pollution lookup", "Accept": "*/*"})
        session.trust_env = True
        return session


def _candidate_dataset_paths(dataset_path: Path | None) -> list[Path]:
    if not dataset_path:
        return []
    data_dir = dataset_path.parent
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
        return "Excellent Dark Sky"
    if bortle <= 4:
        return "Rural Sky"
    if bortle <= 6:
        return "Suburban Sky"
    if bortle <= 8:
        return "Urban Sky"
    return "Inner City Sky"
