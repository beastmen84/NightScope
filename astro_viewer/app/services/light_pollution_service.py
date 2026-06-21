from __future__ import annotations

import csv
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.sky import SkyQuality


KNOWN_CITY_BORTLE = {
    "milano": 8,
    "roma": 8,
    "torino": 7,
    "napoli": 8,
    "palermo": 7,
    "londra": 8,
    "parigi": 8,
    "berlino": 7,
    "new york": 9,
    "los angeles": 9,
    "tokyo": 9,
    "sydney": 8,
    "nairobi": 7,
    "madrid": 8,
    "buenos aires": 8,
}

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


class LightPollutionService:
    """Provider-backed sky quality lookup with cache and offline fallback."""

    def __init__(self, repository: SkyQualityRepository, dataset_path: Path | None = None):
        self._repository = repository
        self._providers: list[LightPollutionProvider] = [
            WorldAtlasProvider(dataset_path),
            ViirsBlackMarbleProvider(dataset_path),
            OfflineEstimateProvider(),
        ]

    def sky_quality(self, location: ObserverLocation) -> SkyQuality:
        key = self._location_key(location)
        cached = self._repository.get(key)
        if cached:
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


class LightPollutionProvider(Protocol):
    name: str

    def lookup(self, location: ObserverLocation) -> SkyQuality | None:
        ...


class OfflineEstimateProvider:
    name = "OfflineEstimateProvider"

    def lookup(self, location: ObserverLocation) -> SkyQuality:
        city_key = location.city.lower().strip()
        if city_key in KNOWN_CITY_BORTLE:
            bortle = KNOWN_CITY_BORTLE[city_key]
            confidence = "medium"
        elif location.city.lower().startswith("coordinate"):
            bortle = 5
            confidence = "low"
        else:
            bortle = 6
            confidence = "low"
        return SkyQuality(
            bortle_class=bortle,
            limiting_magnitude=BORTLE_LIMITING_MAGNITUDE[bortle],
            sky_brightness=BORTLE_SKY_BRIGHTNESS[bortle],
            source="Fonte: stima offline NightScope",
            description=_description(bortle),
            confidence=confidence,
        )


class WorldAtlasProvider:
    name = "WorldAtlasProvider"

    def __init__(self, dataset_path: Path | None = None):
        self._dataset_path = dataset_path
        self._records = _load_light_pollution_records(dataset_path)

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


class ViirsBlackMarbleProvider(WorldAtlasProvider):
    name = "ViirsBlackMarbleProvider"

    def lookup(self, location: ObserverLocation) -> SkyQuality | None:
        return None


def _load_light_pollution_records(dataset_path: Path | None) -> list[dict]:
    if not dataset_path or not dataset_path.exists():
        return []
    records = []
    with dataset_path.open("r", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            records.append(
                {
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "radius_km": float(row.get("radius_km") or 0),
                    "bortle_class": int(float(row["bortle_class"])),
                    "sky_brightness": float(row["sky_brightness"]),
                    "limiting_magnitude": float(row["limiting_magnitude"]),
                    "source": row.get("source", "dataset locale"),
                    "confidence": row.get("confidence", "medium"),
                }
            )
    return records


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
