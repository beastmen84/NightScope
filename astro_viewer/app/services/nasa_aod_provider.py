from __future__ import annotations

import json
import logging
import math
import os
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Iterable, Protocol

import h5py
import netCDF4
import numpy as np

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.earthdata_credentials import EarthdataCredentialStore


logger = logging.getLogger(__name__)

NASA_AOD_PROVIDER = "NASA Earthdata"
NASA_AOD_CACHE_TTL = timedelta(hours=18)
NASA_AOD_CACHE_REUSE_RADIUS_KM = 0.5
NASA_AOD_SEARCH_DAYS = 10
NASA_AOD_GRANULE_LIMIT = 12
VIIRS_PRODUCT = "VNP19A2.002"
MODIS_PRODUCT = "MCD19A2.061"


@dataclass(frozen=True)
class NasaAodProduct:
    short_name: str
    version: str
    label: str
    reader: str

    @property
    def product_id(self) -> str:
        return f"{self.short_name}.{self.version}"


VIIRS_MAIAC_AOD = NasaAodProduct("VNP19A2", "002", VIIRS_PRODUCT, "hdf5")
MODIS_MAIAC_AOD = NasaAodProduct("MCD19A2", "061", MODIS_PRODUCT, "netcdf4")
NASA_AOD_PRODUCTS = (VIIRS_MAIAC_AOD, MODIS_MAIAC_AOD)


@dataclass(frozen=True)
class NasaAodGranule:
    product: NasaAodProduct
    granule_id: str
    acquisition_date: date
    native: Any = None


@dataclass(frozen=True)
class NasaAodExtraction:
    aod_550: float
    uncertainty: float | None
    qa_raw: int | None
    method: str
    local_valid_pixel_count: int | None = None


@dataclass(frozen=True)
class NasaAodResult:
    available: bool
    status: str
    message: str
    provider: str = NASA_AOD_PROVIDER
    product: str = ""
    aod_550: float | None = None
    uncertainty: float | None = None
    qa_raw: int | None = None
    acquisition_date: str = ""
    granule_id: str = ""
    method: str = ""
    local_valid_pixel_count: int | None = None
    retrieved_at: str = ""
    cache_hit: bool = False
    interpretation: str = "—"

    @classmethod
    def no_credentials(cls) -> NasaAodResult:
        return cls(False, "no_credentials", "Credenziali Earthdata non configurate o non verificate.")

    @classmethod
    def no_location(cls) -> NasaAodResult:
        return cls(False, "no_location", "Configura una posizione per recuperare i dati NASA AOD.")

    @classmethod
    def failure(cls, status: str, message: str) -> NasaAodResult:
        return cls(False, status, message)

    @classmethod
    def ok(
        cls,
        *,
        product: str,
        extraction: NasaAodExtraction,
        granule: NasaAodGranule,
        retrieved_at: datetime,
    ) -> NasaAodResult:
        return cls(
            True,
            "ok",
            "Dati NASA AOD disponibili.",
            product=product,
            aod_550=round(extraction.aod_550, 3),
            uncertainty=round(extraction.uncertainty, 4) if extraction.uncertainty is not None else None,
            qa_raw=extraction.qa_raw,
            acquisition_date=granule.acquisition_date.isoformat(),
            granule_id=granule.granule_id,
            method=extraction.method,
            local_valid_pixel_count=extraction.local_valid_pixel_count,
            retrieved_at=retrieved_at.astimezone(UTC).isoformat(),
            interpretation=_interpret_aod(extraction.aod_550),
        )

    def as_cache_hit(self) -> NasaAodResult:
        return replace(self, status="cache_hit", cache_hit=True)

    def to_qml(self) -> dict[str, object]:
        has_data = self.available and self.aod_550 is not None
        freshness_category = _aod_freshness_category(self.acquisition_date) if has_data else "unavailable"
        return {
            "visible": self.status != "no_credentials",
            "hasData": has_data,
            "status": self.status,
            "message": self.message,
            "provider": self.provider,
            "product": self.product,
            "productLabel": _product_label(self.product),
            "aod550": f"{self.aod_550:.3f}" if self.aod_550 is not None else "—",
            "uncertainty": f"{self.uncertainty:.4f}" if self.uncertainty is not None else "—",
            "qaRaw": str(self.qa_raw) if self.qa_raw is not None else "—",
            "acquisitionDate": self.acquisition_date or "—",
            "granuleId": self.granule_id,
            "method": self.method,
            "methodLabel": _method_label(self.method),
            "localValidPixelCount": self.local_valid_pixel_count or 0,
            "retrievedAt": self.retrieved_at,
            "cacheHit": self.cache_hit,
            "transparency": _interpretation_label(self.interpretation) if has_data else "—",
            "freshness": _aod_freshness_label(self.acquisition_date) if has_data else "—",
            "freshnessCategory": freshness_category,
            "freshnessWarning": freshness_category in ("stale", "historical", "unavailable"),
            "sourceDetail": _source_detail(self) if has_data else "",
            "running": False,
        }


class NasaAodClient(Protocol):
    def authenticate(self, username: str, password: str) -> None: ...

    def search(
        self,
        product: NasaAodProduct,
        location: ObserverLocation,
        start_date: date,
        end_date: date,
        limit: int,
    ) -> list[NasaAodGranule]: ...

    def download(self, granule: NasaAodGranule, target_dir: Path) -> Path: ...


class NasaAodExtractor(Protocol):
    def extract(
        self,
        product: NasaAodProduct,
        path: Path,
        location: ObserverLocation,
    ) -> NasaAodExtraction | None: ...


class NasaAodProvider:
    """NASA MAIAC AOD provider for Weather display and condition inputs.

    AOD stays separate from forecast transparency and seeing. AppController can pass
    accepted provider results into ObservationConditionsService, where the explicit
    aerosol feature flag and provider-quality gates decide whether they affect
    condition-adjusted target scores.
    """

    def __init__(
        self,
        credentials: EarthdataCredentialStore | None,
        *,
        client: NasaAodClient | None = None,
        extractor: NasaAodExtractor | None = None,
        clock: Callable[[], datetime] | None = None,
        cache_ttl: timedelta = NASA_AOD_CACHE_TTL,
        cache_reuse_radius_km: float = NASA_AOD_CACHE_REUSE_RADIUS_KM,
        search_days: int = NASA_AOD_SEARCH_DAYS,
        granule_limit: int = NASA_AOD_GRANULE_LIMIT,
        cache_path: Path | None = None,
    ) -> None:
        self._credentials = credentials
        self._client = client or EarthaccessNasaAodClient()
        self._extractor = extractor or MaiacAodExtractor()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._cache_ttl = cache_ttl
        self._cache_reuse_radius_km = max(0.0, float(cache_reuse_radius_km))
        self._search_days = search_days
        self._granule_limit = granule_limit
        self._cache_path = cache_path
        self._cache: dict[tuple[float, float, str, str], tuple[datetime, NasaAodResult]] = {}
        self._location_cache_keys: dict[tuple[float, float], tuple[float, float, str, str]] = {}

    def clear_cache(self) -> None:
        self._cache.clear()
        self._location_cache_keys.clear()
        self._clear_disk_cache()

    def cached_aod(self, location: ObserverLocation | None) -> NasaAodResult | None:
        """Return a fresh processed result without provider authentication or network access."""
        return self._cached_result(location) if location is not None else None

    def aod(self, location: ObserverLocation | None) -> NasaAodResult:
        if location is None:
            return NasaAodResult.no_location()

        credentials = self._verified_credentials()
        if credentials is None:
            return NasaAodResult.no_credentials()

        cached = self._cached_result(location)
        if cached is not None:
            return cached

        username, password = credentials
        try:
            self._client.authenticate(username, password)
        except Exception as exc:
            logger.warning("NASA AOD Earthdata authentication failed: %s", exc.__class__.__name__)
            return NasaAodResult.failure("auth_error", f"Autenticazione Earthdata AOD non riuscita: {exc.__class__.__name__}.")

        now = self._clock().astimezone(UTC)
        end_date = now.date()
        start_date = end_date - timedelta(days=max(1, self._search_days))
        last_status = "no_granules"
        last_message = "Nessun granulo NASA AOD trovato per questa località."

        for product in NASA_AOD_PRODUCTS:
            try:
                granules = self._client.search(product, location, start_date, end_date, self._granule_limit)
            except Exception as exc:
                logger.warning("NASA AOD CMR search failed for %s: %s", product.product_id, exc.__class__.__name__)
                last_status = "download_error"
                last_message = f"Ricerca NASA AOD non riuscita per {product.product_id}: {exc.__class__.__name__}."
                continue

            sorted_granules = sorted(granules, key=lambda granule: granule.acquisition_date, reverse=True)
            if not sorted_granules:
                continue

            last_status = "no_valid_pixel"
            last_message = f"Nessun pixel AOD valido trovato in {product.product_id}."
            result = self._first_valid_result(product, sorted_granules, location, now)
            if result.available:
                self._store_cache(location, result)
                return result
            last_status = result.status
            last_message = result.message

        return NasaAodResult.failure(last_status, last_message)

    def _first_valid_result(
        self,
        product: NasaAodProduct,
        granules: Iterable[NasaAodGranule],
        location: ObserverLocation,
        retrieved_at: datetime,
    ) -> NasaAodResult:
        last_status = "no_valid_pixel"
        last_message = f"Nessun pixel AOD valido trovato in {product.product_id}."
        with tempfile.TemporaryDirectory(prefix="nightscope-aod-") as temp_dir:
            target_dir = Path(temp_dir)
            for granule in granules:
                granule_path: Path | None = None
                try:
                    granule_path = self._client.download(granule, target_dir)
                except Exception as exc:
                    logger.info("NASA AOD granule download failed for %s: %s", granule.granule_id, exc.__class__.__name__)
                    last_status = "download_error"
                    last_message = f"Download NASA AOD non riuscito per {granule.granule_id}: {exc.__class__.__name__}."
                    continue

                try:
                    extraction = self._extractor.extract(product, granule_path, location)
                except Exception as exc:
                    logger.info("NASA AOD granule processing failed for %s: %s", granule.granule_id, exc.__class__.__name__)
                    last_status = "parse_error"
                    last_message = f"Parsing NASA AOD non riuscito per {granule.granule_id}: {exc.__class__.__name__}."
                    continue
                finally:
                    if granule_path is not None:
                        _delete_file(granule_path)

                if extraction is not None:
                    return NasaAodResult.ok(
                        product=product.product_id,
                        extraction=extraction,
                        granule=granule,
                        retrieved_at=retrieved_at,
                    )
                last_status = "no_valid_pixel"
                last_message = f"Nessun pixel AOD valido trovato in {granule.granule_id}."

        return NasaAodResult.failure(last_status, last_message)

    def _verified_credentials(self) -> tuple[str, str] | None:
        if self._credentials is None:
            return None
        state = self._credentials.state()
        password = self._credentials.password()
        if not state.connection_verified or not state.username or not password:
            return None
        return state.username, password

    def _cached_result(self, location: ObserverLocation) -> NasaAodResult | None:
        location_key = self._location_key(location)
        cached = self._cached_memory_result(location_key)
        if cached is not None:
            return cached

        disk_cached = self._cached_disk_result(location_key)
        if disk_cached is None:
            return None
        cached_at, result = disk_cached
        cache_key = (*location_key, result.product, result.granule_id)
        self._cache[cache_key] = (cached_at, result)
        self._location_cache_keys[location_key] = cache_key
        return result.as_cache_hit()

    def _cache_is_fresh(self, cached_at: datetime) -> bool:
        now = self._clock().astimezone(UTC)
        age = now - cached_at
        return timedelta(0) <= age <= self._cache_ttl

    def _cached_memory_result(self, location_key: tuple[float, float]) -> NasaAodResult | None:
        nearest = None
        nearest_distance = math.inf
        for cached_location, cache_key in list(self._location_cache_keys.items()):
            cached = self._cache.get(cache_key)
            if cached is None:
                self._location_cache_keys.pop(cached_location, None)
                continue
            cached_at, result = cached
            if not self._cache_is_fresh(cached_at):
                self._cache.pop(cache_key, None)
                self._location_cache_keys.pop(cached_location, None)
                continue
            distance = _distance_km(*location_key, *cached_location)
            if distance <= self._cache_reuse_radius_km and distance < nearest_distance:
                nearest = result
                nearest_distance = distance
        return nearest.as_cache_hit() if nearest is not None else None

    def _cached_disk_result(self, location_key: tuple[float, float]) -> tuple[datetime, NasaAodResult] | None:
        if self._cache_path is None:
            return None
        payload = self._read_disk_cache()
        entries = payload.get("entries")
        if not isinstance(entries, dict):
            return None
        candidates: list[tuple[float, datetime, NasaAodResult]] = []
        changed = False
        for entry_key, entry in list(entries.items()):
            cached_location = self._parse_disk_location_key(entry_key)
            if cached_location is None:
                continue
            distance = _distance_km(*location_key, *cached_location)
            if distance > self._cache_reuse_radius_km:
                continue
            if not isinstance(entry, dict):
                entries.pop(entry_key, None)
                changed = True
                continue
            cached_at = _parse_datetime(entry.get("cached_at"))
            result = _result_from_cache_payload(entry.get("result"))
            if cached_at is None or result is None or not self._cache_is_fresh(cached_at):
                entries.pop(entry_key, None)
                changed = True
                continue
            candidates.append((distance, cached_at, result))
        if changed:
            self._write_disk_cache(payload)
        if not candidates:
            return None
        _, cached_at, result = min(candidates, key=lambda item: item[0])
        return cached_at, result

    def _read_disk_cache(self) -> dict[str, object]:
        if self._cache_path is None or not self._cache_path.exists():
            return {"version": 1, "entries": {}}
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.info("NASA AOD processed cache could not be read: %s", self._cache_path)
            return {"version": 1, "entries": {}}
        return payload if isinstance(payload, dict) else {"version": 1, "entries": {}}

    def _write_disk_cache(self, payload: dict[str, object]) -> None:
        if self._cache_path is None:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            logger.info("NASA AOD processed cache could not be written: %s", self._cache_path)

    def _clear_disk_cache(self) -> None:
        if self._cache_path is None:
            return
        try:
            if self._cache_path.exists():
                self._cache_path.unlink()
        except OSError:
            logger.info("NASA AOD processed cache could not be deleted: %s", self._cache_path)

    def _store_cache(self, location: ObserverLocation, result: NasaAodResult) -> None:
        if not result.available or not result.product or not result.granule_id:
            return
        cached_at = self._clock().astimezone(UTC)
        location_key = self._location_key(location)
        cache_key = (*location_key, result.product, result.granule_id)
        self._cache[cache_key] = (cached_at, result)
        self._location_cache_keys[location_key] = cache_key
        self._store_disk_cache(location_key, cached_at, result)

    def _store_disk_cache(self, location_key: tuple[float, float], cached_at: datetime, result: NasaAodResult) -> None:
        if self._cache_path is None:
            return
        payload = self._read_disk_cache()
        entries = payload.get("entries")
        if not isinstance(entries, dict):
            entries = {}
            payload["entries"] = entries
        payload["version"] = 1
        entries[self._disk_location_key(location_key)] = {
            "cached_at": cached_at.astimezone(UTC).isoformat(),
            "result": asdict(result),
        }
        self._write_disk_cache(payload)

    @staticmethod
    def _disk_location_key(location_key: tuple[float, float]) -> str:
        return f"{location_key[0]:.3f}:{location_key[1]:.3f}"

    @staticmethod
    def _parse_disk_location_key(value: object) -> tuple[float, float] | None:
        if not isinstance(value, str):
            return None
        parts = value.split(":", 1)
        if len(parts) != 2:
            return None
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            return None

    @staticmethod
    def _location_key(location: ObserverLocation) -> tuple[float, float]:
        return round(location.latitude, 3), round(location.longitude, 3)


class EarthaccessNasaAodClient:
    def __init__(
        self,
        *,
        login_attempts: int = 3,
        backoff_seconds: tuple[float, ...] = (0.0, 2.0, 5.0),
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._login_attempts = max(1, login_attempts)
        self._backoff_seconds = backoff_seconds
        self._sleep = sleep
        self._earthaccess = None

    def authenticate(self, username: str, password: str) -> None:
        if not username or not password:
            raise RuntimeError("Earthdata credentials are missing.")
        last_error: Exception | None = None
        for attempt in range(self._login_attempts):
            if attempt < len(self._backoff_seconds) and self._backoff_seconds[attempt] > 0:
                self._sleep(self._backoff_seconds[attempt])
            try:
                earthaccess = self._import_earthaccess()
                with _temporary_earthdata_environment(username, password):
                    earthaccess.login(strategy="environment", persist=False)
                return
            except Exception as exc:  # pragma: no cover - network-specific branch
                last_error = exc
                logger.info("Earthaccess login attempt %s failed: %s", attempt + 1, exc.__class__.__name__)
        if last_error is not None:
            raise last_error
        raise RuntimeError("Earthaccess login failed.")

    def search(
        self,
        product: NasaAodProduct,
        location: ObserverLocation,
        start_date: date,
        end_date: date,
        limit: int,
    ) -> list[NasaAodGranule]:
        earthaccess = self._import_earthaccess()
        results = earthaccess.search_data(
            short_name=product.short_name,
            version=product.version,
            point=(location.longitude, location.latitude),
            temporal=(start_date.isoformat(), end_date.isoformat()),
            count=limit,
        )
        granules = [_granule_from_earthaccess_result(product, result) for result in results]
        return [granule for granule in granules if granule is not None]

    def download(self, granule: NasaAodGranule, target_dir: Path) -> Path:
        earthaccess = self._import_earthaccess()
        files = earthaccess.download([granule.native], local_path=str(target_dir))
        if not files:
            raise RuntimeError(f"Earthaccess did not download {granule.granule_id}.")
        return Path(files[0])

    def _import_earthaccess(self):
        if self._earthaccess is None:
            import earthaccess  # type: ignore[import-not-found]

            self._earthaccess = earthaccess
        return self._earthaccess


class MaiacAodExtractor:
    def extract(
        self,
        product: NasaAodProduct,
        path: Path,
        location: ObserverLocation,
    ) -> NasaAodExtraction | None:
        if product.reader == "hdf5":
            return _extract_hdf5_aod(path, location)
        if product.reader == "netcdf4":
            return _extract_netcdf4_aod(path, location)
        raise ValueError(f"Unsupported NASA AOD reader: {product.reader}")


@contextmanager
def _temporary_earthdata_environment(username: str, password: str):
    previous_username = os.environ.get("EARTHDATA_USERNAME")
    previous_password = os.environ.get("EARTHDATA_PASSWORD")
    previous_token = os.environ.get("EARTHDATA_TOKEN")
    os.environ["EARTHDATA_USERNAME"] = username
    os.environ["EARTHDATA_PASSWORD"] = password
    os.environ.pop("EARTHDATA_TOKEN", None)
    try:
        yield
    finally:
        _restore_env("EARTHDATA_USERNAME", previous_username)
        _restore_env("EARTHDATA_PASSWORD", previous_password)
        _restore_env("EARTHDATA_TOKEN", previous_token)


def _restore_env(key: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value


def _granule_from_earthaccess_result(product: NasaAodProduct, result: Any) -> NasaAodGranule | None:
    try:
        granule_id = str(result["meta"].get("native-id") or result["meta"].get("concept-id") or "")
        start_time = (
            result.get("umm", {})
            .get("TemporalExtent", {})
            .get("RangeDateTime", {})
            .get("BeginningDateTime")
        )
    except Exception:
        return None
    acquisition_date = _parse_date(start_time)
    if not granule_id or acquisition_date is None:
        return None
    return NasaAodGranule(product, granule_id, acquisition_date, result)


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _result_from_cache_payload(value: Any) -> NasaAodResult | None:
    if not isinstance(value, dict):
        return None
    if not value.get("available") or not value.get("product") or not value.get("granule_id"):
        return None
    return NasaAodResult(
        available=bool(value.get("available")),
        status=str(value.get("status") or "ok"),
        message=str(value.get("message") or "Dati NASA AOD disponibili."),
        provider=str(value.get("provider") or NASA_AOD_PROVIDER),
        product=str(value.get("product") or ""),
        aod_550=_optional_float(value.get("aod_550")),
        uncertainty=_optional_float(value.get("uncertainty")),
        qa_raw=_optional_int(value.get("qa_raw")),
        acquisition_date=str(value.get("acquisition_date") or ""),
        granule_id=str(value.get("granule_id") or ""),
        method=str(value.get("method") or ""),
        local_valid_pixel_count=_optional_int(value.get("local_valid_pixel_count")),
        retrieved_at=str(value.get("retrieved_at") or ""),
        cache_hit=False,
        interpretation=str(value.get("interpretation") or "—"),
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _extract_hdf5_aod(path: Path, location: ObserverLocation) -> NasaAodExtraction | None:
    with h5py.File(path, "r") as handle:
        aod = _hdf5_dataset(handle, "Optical_Depth_055")
        qa = _hdf5_dataset(handle, "AOD_QA")
        uncertainty = _hdf5_dataset(handle, "AOD_Uncertainty")
        if aod is None or qa is None:
            raise ValueError("Required VIIRS MAIAC AOD layers were not found.")
        metadata = _hdf5_struct_metadata(handle)
        return _extract_from_arrays(
            aod,
            qa,
            uncertainty,
            location,
            metadata,
            scale=_attribute_scalar(aod.attrs.get("scale_factor"), 0.001),
            fill=int(_attribute_scalar(aod.attrs.get("_FillValue"), -28672)),
            uncertainty_scale=_attribute_scalar(
                uncertainty.attrs.get("scale_factor") if uncertainty is not None else None,
                0.0001,
            ),
            uncertainty_fill=int(
                _attribute_scalar(uncertainty.attrs.get("_FillValue") if uncertainty is not None else None, -28672)
            ),
        )


def _extract_netcdf4_aod(path: Path, location: ObserverLocation) -> NasaAodExtraction | None:
    with netCDF4.Dataset(str(path)) as dataset:
        dataset.set_auto_maskandscale(False)
        aod = dataset.variables.get("Optical_Depth_055")
        qa = dataset.variables.get("AOD_QA")
        uncertainty = dataset.variables.get("AOD_Uncertainty")
        if aod is None or qa is None:
            raise ValueError("Required MODIS MAIAC AOD layers were not found.")
        return _extract_from_arrays(
            aod,
            qa,
            uncertainty,
            location,
            str(getattr(dataset, "StructMetadata.0")),
            scale=_attribute_scalar(getattr(aod, "scale_factor", None), 0.001),
            fill=int(_attribute_scalar(getattr(aod, "_FillValue", None), -28672)),
            uncertainty_scale=_attribute_scalar(getattr(uncertainty, "scale_factor", None), 0.0001)
            if uncertainty is not None
            else 0.0001,
            uncertainty_fill=int(_attribute_scalar(getattr(uncertainty, "_FillValue", None), -28672))
            if uncertainty is not None
            else -28672,
        )


def _extract_from_arrays(
    aod: Any,
    qa: Any,
    uncertainty: Any | None,
    location: ObserverLocation,
    metadata: str,
    *,
    scale: float,
    fill: int,
    uncertainty_scale: float,
    uncertainty_fill: int,
) -> NasaAodExtraction | None:
    ydim = int(aod.shape[-2])
    xdim = int(aod.shape[-1])
    row, col = _row_col_from_sinusoidal_metadata(metadata, location, ydim, xdim)
    if not (0 <= row < ydim and 0 <= col < xdim):
        return None

    direct = _direct_pixel(aod, qa, uncertainty, row, col, scale, fill, uncertainty_scale, uncertainty_fill)
    if direct is not None:
        return direct
    return _local_neighborhood(aod, qa, uncertainty, row, col, scale, fill, uncertainty_scale, uncertainty_fill)


def _direct_pixel(
    aod: Any,
    qa: Any,
    uncertainty: Any | None,
    row: int,
    col: int,
    scale: float,
    fill: int,
    uncertainty_scale: float,
    uncertainty_fill: int,
) -> NasaAodExtraction | None:
    for orbit in range(_orbit_count(aod)):
        key = _array_key(aod, orbit, row, col)
        raw = int(aod[key])
        if not _valid_aod_raw(raw, fill):
            continue
        return NasaAodExtraction(
            aod_550=raw * scale,
            uncertainty=_uncertainty_value(uncertainty, key, uncertainty_scale, uncertainty_fill),
            qa_raw=int(qa[key]) if qa is not None else None,
            method="direct_pixel",
        )
    return None


def _local_neighborhood(
    aod: Any,
    qa: Any,
    uncertainty: Any | None,
    row: int,
    col: int,
    scale: float,
    fill: int,
    uncertainty_scale: float,
    uncertainty_fill: int,
) -> NasaAodExtraction | None:
    best: NasaAodExtraction | None = None
    for orbit in range(_orbit_count(aod)):
        aod_window = _window(aod, orbit, row, col)
        mask = (aod_window != fill) & (aod_window >= 0) & (aod_window <= 6000)
        valid_count = int(mask.sum())
        if valid_count <= 0:
            continue
        uncertainty_value = None
        if uncertainty is not None:
            uncertainty_window = _window(uncertainty, orbit, row, col)
            uncertainty_mask = mask & (uncertainty_window != uncertainty_fill) & (uncertainty_window >= 0)
            if bool(np.any(uncertainty_mask)):
                uncertainty_value = float(np.nanmedian(np.where(uncertainty_mask, uncertainty_window * uncertainty_scale, np.nan)))
        qa_raw = None
        if qa is not None:
            qa_window = _window(qa, orbit, row, col)
            qa_raw = int(round(float(np.nanmedian(np.where(mask, qa_window, np.nan)))))
        candidate = NasaAodExtraction(
            aod_550=float(np.nanmedian(np.where(mask, aod_window * scale, np.nan))),
            uncertainty=uncertainty_value,
            qa_raw=qa_raw,
            method="local_neighborhood",
            local_valid_pixel_count=valid_count,
        )
        if best is None or (candidate.local_valid_pixel_count or 0) > (best.local_valid_pixel_count or 0):
            best = candidate
    return best


def _window(array: Any, orbit: int, row: int, col: int, radius: int = 2) -> np.ndarray:
    ydim = int(array.shape[-2])
    xdim = int(array.shape[-1])
    r0 = max(0, row - radius)
    r1 = min(ydim, row + radius + 1)
    c0 = max(0, col - radius)
    c1 = min(xdim, col + radius + 1)
    if len(array.shape) == 3:
        return np.asarray(array[orbit, r0:r1, c0:c1])
    return np.asarray(array[r0:r1, c0:c1])


def _array_key(array: Any, orbit: int, row: int, col: int) -> tuple[int, int, int] | tuple[int, int]:
    if len(array.shape) == 3:
        return orbit, row, col
    return row, col


def _orbit_count(array: Any) -> int:
    return int(array.shape[0]) if len(array.shape) == 3 else 1


def _valid_aod_raw(value: int, fill: int) -> bool:
    return value != fill and 0 <= value <= 6000


def _uncertainty_value(
    uncertainty: Any | None,
    key: tuple[int, int, int] | tuple[int, int],
    scale: float,
    fill: int,
) -> float | None:
    if uncertainty is None:
        return None
    raw = int(uncertainty[key])
    if raw == fill or raw < 0:
        return None
    return raw * scale


def _hdf5_dataset(handle: h5py.File, suffix: str):
    matches = []

    def visit(name: str, obj: Any) -> None:
        if hasattr(obj, "shape") and name.endswith(suffix):
            matches.append(obj)

    handle.visititems(visit)
    return matches[0] if matches else None


def _hdf5_struct_metadata(handle: h5py.File) -> str:
    node = handle.get("HDFEOS INFORMATION/StructMetadata.0")
    if node is None:
        raise ValueError("HDF-EOS structure metadata was not found.")
    value = node[()]
    if isinstance(value, bytes):
        return value.decode("ascii", "ignore")
    if hasattr(value, "tobytes"):
        return value.tobytes().decode("ascii", "ignore")
    return str(value)


def _row_col_from_sinusoidal_metadata(
    metadata: str,
    location: ObserverLocation,
    ydim: int,
    xdim: int,
) -> tuple[int, int]:
    import re

    match = re.search(
        r"UpperLeftPointMtrs=\(([-0-9.]+),([-0-9.]+)\).*?"
        r"LowerRightMtrs=\(([-0-9.]+),([-0-9.]+)\).*?"
        r"ProjParams=\(([^)]*)\)",
        metadata,
        re.S,
    )
    if not match:
        raise ValueError("Sinusoidal projection metadata was not found.")
    ulx, uly, lrx, lry = map(float, match.groups()[:4])
    proj_params = [float(item) for item in match.group(5).split(",")]
    radius = proj_params[0]
    lon0 = proj_params[4] / 1_000_000.0 if abs(proj_params[4]) > 360 else proj_params[4]
    x = radius * math.radians(location.longitude - lon0) * math.cos(math.radians(location.latitude))
    y = radius * math.radians(location.latitude)
    row = int((uly - y) / ((uly - lry) / ydim))
    col = int((x - ulx) / ((lrx - ulx) / xdim))
    return row, col


def _attribute_scalar(value: Any, fallback: float) -> float:
    if value is None:
        return fallback
    array = np.asarray(value)
    if array.shape:
        return float(array.ravel()[0])
    return float(array.item())


def _interpret_aod(value: float) -> str:
    if value < 0.15:
        return "low"
    if value < 0.35:
        return "moderate"
    if value < 0.7:
        return "elevated"
    return "high"


def _interpretation_label(value: str) -> str:
    return {
        "low": "Molto buona",
        "moderate": "Buona",
        "elevated": "Velata",
        "high": "Aerosol elevati",
    }.get(value, "—")


def _product_label(product: str) -> str:
    if product == VIIRS_PRODUCT:
        return "VIIRS MAIAC"
    if product == MODIS_PRODUCT:
        return "MODIS MAIAC"
    return product or "NASA MAIAC"


def _method_label(method: str) -> str:
    if method == "direct_pixel":
        return "Pixel diretto"
    if method == "local_neighborhood":
        return "Area locale 5x5"
    return method or "—"


def _aod_freshness_category(acquisition_date: str) -> str:
    age_days = _aod_age_days(acquisition_date)
    if age_days is None:
        return "unavailable"
    if age_days < 3:
        return "current"
    if age_days <= 7:
        return "stale"
    return "historical"


def _aod_freshness_label(acquisition_date: str) -> str:
    age_days = _aod_age_days(acquisition_date)
    if age_days is None:
        return "Aggiornamento non disponibile"
    if age_days == 0:
        return "Misura di oggi"
    if age_days == 1:
        return "Misura di ieri"
    if age_days < 3:
        return f"Misura di {age_days} giorni fa"
    if age_days <= 7:
        return f"Misura vecchia di {age_days} giorni"
    return f"Misura storica di {age_days} giorni"


def _aod_age_days(acquisition_date: str) -> int | None:
    if not acquisition_date:
        return None
    try:
        measured = datetime.fromisoformat(acquisition_date).date()
    except ValueError:
        return None
    return max(0, (datetime.now().date() - measured).days)


def _source_detail(result: NasaAodResult) -> str:
    parts = [_product_label(result.product), result.acquisition_date]
    if result.method:
        method = _method_label(result.method)
        if result.method == "local_neighborhood" and result.local_valid_pixel_count is not None:
            method = f"{method}, {result.local_valid_pixel_count} pixel validi"
        parts.append(method)
    if result.uncertainty is not None:
        parts.append(f"Incertezza {result.uncertainty:.4f}")
    if result.qa_raw is not None:
        parts.append(f"QA {result.qa_raw}")
    if result.cache_hit:
        parts.append("Da cache")
    return " · ".join(part for part in parts if part)


def _delete_file(path: Path) -> None:
    try:
        if path.exists() and path.is_file():
            path.unlink()
    except OSError:
        logger.info("NASA AOD temporary granule could not be deleted: %s", path)
