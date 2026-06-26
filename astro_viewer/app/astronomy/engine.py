from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from astro_viewer.app.astronomy.catalog import (
    mock_deep_sky,
    mock_events,
    mock_moon,
    mock_planets,
)
from astro_viewer.app.models.observing import AstronomicalEvent, CelestialObject, MoonSummary


@dataclass(frozen=True)
class ObserverLocation:
    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str


class AstronomyEngine(Protocol):
    def visible_planets(self, location: ObserverLocation) -> list[CelestialObject]:
        ...

    def recommended_deep_sky(self, location: ObserverLocation) -> list[CelestialObject]:
        ...

    def catalogue_month_visibility(
        self,
        catalogue_objects: list[dict],
        location: ObserverLocation,
        year: int,
        month: int,
        altitude_threshold: float,
    ) -> dict[str, bool]:
        ...

    def moon_summary(self, location: ObserverLocation) -> MoonSummary:
        ...

    def upcoming_events(self, location: ObserverLocation) -> list[AstronomicalEvent]:
        ...


class MockAstronomyEngine:
    """First iteration engine. The public methods mirror the future Skyfield/Astropy boundary."""

    def solar_system_objects(self, location: ObserverLocation) -> list[CelestialObject]:
        return mock_planets()

    def visible_planets(self, location: ObserverLocation) -> list[CelestialObject]:
        return mock_planets()

    def recommended_deep_sky(self, location: ObserverLocation) -> list[CelestialObject]:
        return mock_deep_sky()

    def catalogue_month_visibility(
        self,
        catalogue_objects: list[dict],
        location: ObserverLocation,
        year: int,
        month: int,
        altitude_threshold: float,
    ) -> dict[str, bool]:
        return {}

    def moon_summary(self, location: ObserverLocation) -> MoonSummary:
        return mock_moon()

    def upcoming_events(self, location: ObserverLocation) -> list[AstronomicalEvent]:
        return mock_events()


class SkyfieldAstropyEngine:
    """Real implementation placeholder for the next iteration."""

    def visible_planets(self, location: ObserverLocation) -> list[CelestialObject]:
        raise NotImplementedError("Skyfield planet calculations will be added in a later iteration.")

    def recommended_deep_sky(self, location: ObserverLocation) -> list[CelestialObject]:
        raise NotImplementedError("Astropy coordinate transforms will be added in a later iteration.")

    def moon_summary(self, location: ObserverLocation) -> MoonSummary:
        raise NotImplementedError("Moon phase calculations will be added in a later iteration.")

    def upcoming_events(self, location: ObserverLocation) -> list[AstronomicalEvent]:
        raise NotImplementedError("Astronomical event generation will be added in a later iteration.")
