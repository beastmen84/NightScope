"""Define astronomy ports, shared location values, and deterministic mock behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
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
from astro_viewer.app.services.localization import tr


ASTRONOMY_UNAVAILABLE_MESSAGE = tr(
    "Effemeridi non disponibili: calcoli astronomici e piano osservativo disattivati."
)


@dataclass(frozen=True)
class ObserverLocation:
    """Observer identity and WGS84 geodetic coordinates in decimal degrees.

    North/east are positive; ``timezone`` is an IANA name, not a UTC offset.
    City/country are labels only. This DTO has no elevation: current astronomy
    observers use zero metres above the WGS84 ellipsoid, without terrain data.
    """

    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str


class TransientCalendarEventSource(Protocol):
    """Produces location-aware events outside the annual astronomy pipeline."""

    refresh_interval: timedelta

    def prepare_event_data(
        self,
        location: ObserverLocation,
        *,
        now: datetime,
    ) -> object | None:
        ...

    def build_events(
        self,
        location: ObserverLocation,
        *,
        now: datetime,
        timescale: object,
        ephemeris: object,
        prepared_data: object,
    ) -> list[AstronomicalEvent]:
        ...


@dataclass(frozen=True)
class PreparedTransientCalendarEvents:
    """Network/cache data ready for a short Skyfield calculation."""

    now: datetime
    entries: tuple[tuple[TransientCalendarEventSource, object], ...] = ()
    attempted_sources: tuple[TransientCalendarEventSource, ...] = ()


@dataclass(frozen=True)
class ObservingNightWindow:
    """Location-aware planning bounds for the current or next observing night.

    Real-engine bounds are aware local datetimes; containment is start-inclusive
    and end-exclusive. ``no_night`` (polar daylight) differs from ``unavailable``
    (no trustworthy calculation). A bounded night starts at sunset, not at the
    end of astronomical twilight. This value object does not validate or
    normalize its inputs; callers own that contract.
    """

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
        return cls("continuous_night", start, end or advance_time(start, timedelta(hours=24)))

    @classmethod
    def no_night(cls) -> "ObservingNightWindow":
        return cls("no_night")

    @classmethod
    def unavailable(cls) -> "ObservingNightWindow":
        return cls("unavailable")

    @property
    def has_observing_window(self) -> bool:
        return (
            self.start is not None
            and self.end is not None
            and as_utc(self.end) > as_utc(self.start)
        )

    def contains(self, value: datetime) -> bool:
        if not self.has_observing_window:
            return False
        return as_utc(self.start) <= as_utc(value) < as_utc(self.end)

    def datetime_for_clock(
        self, hour: int, minute: int, *, fold: int | None = None, include_end: bool = False,
    ) -> datetime | None:
        """Locate the first matching wall-clock minute overlapping this night.

        This is a compatibility bridge for display-only HH:MM fields, not an
        unambiguous timestamp parser. Prefer absolute target timestamps. Callers
        can select a repeated hour with ``fold``; nonexistent local clocks are
        rejected. ``include_end`` is only for parsing an interval's closing bound.
        """

        if not self.has_observing_window or not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        current_date = self.start.date()
        while current_date <= self.end.date():
            clock = datetime.combine(
                current_date,
                time(hour, minute),
                tzinfo=self.start.tzinfo,
            )
            for candidate_fold in ((0, 1) if fold is None else (fold,)):
                candidate = clock.replace(fold=candidate_fold)
                if (
                    candidate.tzinfo
                    and as_utc(candidate).astimezone(candidate.tzinfo).replace(tzinfo=None)
                    != clock.replace(tzinfo=None)
                ):
                    continue
                instant = as_utc(candidate)
                if include_end and instant == as_utc(self.end):
                    return self.end
                if (
                    instant < as_utc(self.end)
                    and instant + timedelta(minutes=1) > as_utc(self.start)
                ):
                    return max(candidate, self.start, key=as_utc)
            current_date += timedelta(days=1)
        return None


def as_utc(value: datetime) -> datetime:
    """Order aware instants in UTC, preserving naive legacy/test clock values."""
    return value.astimezone(UTC) if value.tzinfo is not None else value


def advance_time(value: datetime, elapsed: timedelta) -> datetime:
    """Advance elapsed time, not wall-clock time, across offset transitions."""
    result = as_utc(value) + elapsed
    return result.astimezone(value.tzinfo) if value.tzinfo is not None else result


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

    def moon_geometry_batch(
        self,
        location: ObserverLocation,
        targets: list[CelestialObject],
    ) -> dict[str, MoonGeometrySummary | None]:
        ...

    def upcoming_events(self, location: ObserverLocation) -> list[AstronomicalEvent]:
        ...


class UnavailableAstronomyEngine:
    """Fail closed after ephemeris recovery fails; never substitute sample skies."""

    data_quality = "unavailable"

    def observing_night_window(self, location: ObserverLocation) -> ObservingNightWindow:
        return ObservingNightWindow.unavailable()

    def solar_system_objects(self, location: ObserverLocation) -> list[CelestialObject]:
        return []

    def visible_planets(self, location: ObserverLocation) -> list[CelestialObject]:
        return []

    def recommended_deep_sky(self, location: ObserverLocation) -> list[CelestialObject]:
        return []

    def catalogue_month_visibility(
        self, catalogue_objects, location, year, month, altitude_threshold,
    ) -> dict[str, bool]:
        return {}

    def refresh_current_positions(self, objects, location) -> list[CelestialObject]:
        return []

    def moon_summary(self, location: ObserverLocation) -> MoonSummary:
        return MoonSummary(
            tr("n/d"), tr("n/d"), tr("n/d"), tr("n/d"),
            ASTRONOMY_UNAVAILABLE_MESSAGE, "",
        )

    def moon_geometry(self, location, target) -> MoonGeometrySummary | None:
        return None

    def moon_geometry_batch(self, location, targets) -> dict[str, MoonGeometrySummary | None]:
        return {target.id: None for target in targets}

    def upcoming_events(self, location: ObserverLocation) -> list[AstronomicalEvent]:
        return []


class MockAstronomyEngine:
    """Return deterministic demonstration data, independent of location or date.

    Only explicitly injected tests/demonstrations use this engine. Production
    failure uses UnavailableAstronomyEngine, never these nonlocal sample values.
    """

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

    def moon_geometry_batch(
        self,
        location: ObserverLocation,
        targets: list[CelestialObject],
    ) -> dict[str, MoonGeometrySummary | None]:
        return {target.id: None for target in targets}

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

    def moon_geometry_batch(
        self,
        location: ObserverLocation,
        targets: list[CelestialObject],
    ) -> dict[str, MoonGeometrySummary | None]:
        raise NotImplementedError("Moon geometry calculations will be added in a later iteration.")

    def upcoming_events(self, location: ObserverLocation) -> list[AstronomicalEvent]:
        raise NotImplementedError("Astronomical event generation will be added in a later iteration.")
