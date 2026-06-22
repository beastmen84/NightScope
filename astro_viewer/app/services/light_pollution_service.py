from __future__ import annotations

import csv
import math
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.sky import SkyQuality


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

    def __init__(self, repository: SkyQualityRepository, dataset_path: Path | None = None):
        self._repository = repository
        dataset_paths = _candidate_dataset_paths(dataset_path)
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
