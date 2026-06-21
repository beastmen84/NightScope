from __future__ import annotations

from datetime import UTC, datetime

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
    """Local sky quality estimator with a repository-backed cache.

    The current implementation is intentionally offline: it uses known-city seed
    values and a conservative fallback for manual coordinates. The service is
    isolated so a future VIIRS or World Atlas raster lookup can replace the
    estimate without touching ViewModels or QML.
    """

    def __init__(self, repository: SkyQualityRepository):
        self._repository = repository

    def sky_quality(self, location: ObserverLocation) -> SkyQuality:
        key = self._location_key(location)
        cached = self._repository.get(key)
        if cached:
            return self._to_model(cached)

        bortle = self._estimate_bortle(location)
        quality = SkyQuality(
            bortle_class=bortle,
            limiting_magnitude=BORTLE_LIMITING_MAGNITUDE[bortle],
            sky_brightness=BORTLE_SKY_BRIGHTNESS[bortle],
            source="Stima locale NightScope; pronta per VIIRS/World Atlas",
            description=self._description(bortle),
        )
        self._repository.set(
            key,
            quality.bortle_class,
            quality.limiting_magnitude,
            quality.sky_brightness,
            quality.source,
            datetime.now(UTC).isoformat(),
        )
        return quality

    @staticmethod
    def _estimate_bortle(location: ObserverLocation) -> int:
        city_key = location.city.lower().strip()
        if city_key in KNOWN_CITY_BORTLE:
            return KNOWN_CITY_BORTLE[city_key]
        if location.city.lower().startswith("coordinate"):
            return 5
        return 6

    @staticmethod
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
            description=LightPollutionService._description(int(row["bortle_class"])),
        )

