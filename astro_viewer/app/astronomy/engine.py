from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Protocol

from astro_viewer.app.astronomy.catalog import (
    mock_deep_sky,
    mock_events,
    mock_moon,
    mock_planets,
)
from astro_viewer.app.models.observing import (
    AstronomicalEvent,
    CelestialObject,
    MoonGeometrySummary,
    MoonSummary,
)


@dataclass(frozen=True)
class ObserverLocation:
    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str


@dataclass(frozen=True)
class ObservingNightWindow:
    """Location-aware planning bounds for the current or next observing night."""

    state: str
    start: datetime | None = None
    end: datetime | None = None

    @classmethod
    def bounded(cls, start: datetime, end: datetime) -> "ObservingNightWindow":
        return cls("bounded", start, end)

    @classmethod
    def continuous_night(
        cls,
        start: datetime,
        end: datetime | None = None,
    ) -> "ObservingNightWindow":
        return cls("continuous_night", start, end or start + timedelta(hours=24))

    @classmethod
    def no_night(cls) -> "ObservingNightWindow":
        return cls("no_night")

    @classmethod
    def unavailable(cls) -> "ObservingNightWindow":
        return cls("unavailable")

    @property
    def has_observing_window(self) -> bool:
        return self.start is not None and self.end is not None and self.end > self.start

    def contains(self, value: datetime) -> bool:
        if not self.has_observing_window:
            return False
        return self.start <= value < self.end

    def datetime_for_clock(self, hour: int, minute: int) -> datetime | None:
        if not self.has_observing_window or not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        current_date = self.start.date()
        while current_date <= self.end.date():
            candidate = datetime.combine(
                current_date,
                time(hour, minute),
                tzinfo=self.start.tzinfo,
            )
            if self.contains(candidate):
                return candidate
            current_date += timedelta(days=1)
        return None


class AstronomyEngine(Protocol):
    def observing_night_window(self, location: ObserverLocation) -> ObservingNightWindow:
        ...

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

    def refresh_current_positions(
        self,
        objects: list[CelestialObject],
        location: ObserverLocation,
    ) -> list[CelestialObject]:
        ...

    def moon_summary(self, location: ObserverLocation) -> MoonSummary:
        ...

    def moon_geometry(self, location: ObserverLocation, target: CelestialObject) -> MoonGeometrySummary | None:
        ...

    def upcoming_events(self, location: ObserverLocation) -> list[AstronomicalEvent]:
        ...


class MockAstronomyEngine:
    """First iteration engine. The public methods mirror the future Skyfield/Astropy boundary."""

    def observing_night_window(self, location: ObserverLocation) -> ObservingNightWindow:
        return ObservingNightWindow.unavailable()

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

    def refresh_current_positions(
        self,
        objects: list[CelestialObject],
        location: ObserverLocation,
    ) -> list[CelestialObject]:
        return objects

    def moon_summary(self, location: ObserverLocation) -> MoonSummary:
        return mock_moon()

    def moon_geometry(self, location: ObserverLocation, target: CelestialObject) -> MoonGeometrySummary | None:
        return None

    def upcoming_events(self, location: ObserverLocation) -> list[AstronomicalEvent]:
        return mock_events()


class SkyfieldAstropyEngine:
    """Real implementation placeholder for the next iteration."""

    def observing_night_window(self, location: ObserverLocation) -> ObservingNightWindow:
        raise NotImplementedError("Location-aware night calculations will be added in a later iteration.")

    def visible_planets(self, location: ObserverLocation) -> list[CelestialObject]:
        raise NotImplementedError("Skyfield planet calculations will be added in a later iteration.")

    def recommended_deep_sky(self, location: ObserverLocation) -> list[CelestialObject]:
        raise NotImplementedError("Astropy coordinate transforms will be added in a later iteration.")

    def moon_summary(self, location: ObserverLocation) -> MoonSummary:
        raise NotImplementedError("Moon phase calculations will be added in a later iteration.")

    def moon_geometry(self, location: ObserverLocation, target: CelestialObject) -> MoonGeometrySummary | None:
        raise NotImplementedError("Moon geometry calculations will be added in a later iteration.")

    def upcoming_events(self, location: ObserverLocation) -> list[AstronomicalEvent]:
        raise NotImplementedError("Astronomical event generation will be added in a later iteration.")
