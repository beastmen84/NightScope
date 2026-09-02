"""Resolve location commands without coupling their policy to the Qt controller.

The workflow owns search, selection, provider fallback, validation, startup
resolution, recent-location deduplication, and user-facing command outcomes.
The controller remains responsible for Qt slots, cancellation generations,
state mutation, refresh scheduling, and signal publication.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from astro_viewer.app.services.localization import format_number, tr
from astro_viewer.app.services.location_preferences import (
    StartupLocationPreferences,
)
from astro_viewer.app.services.location_service import (
    APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE,
    LocationDetectionResult,
    LocationUnavailableError,
)


class LocationRepositoryPort(Protocol):
    """Expose only the location queries required by command handling."""

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Return matching city and observatory projections."""

        ...

    def get_city(self, city_id: int) -> dict | None:
        """Return one embedded city by stable identifier."""

        ...

    def get_observatory(self, mpc_code: str) -> dict | None:
        """Return one MPC observatory by code."""

        ...


class LocationServicePort(Protocol):
    """Expose provider and normalization operations used by location commands."""

    def detect_system_location(self) -> LocationDetectionResult:
        """Detect a location through the current platform providers."""

        ...

    def detect_ip_location(self, allow_online: bool) -> LocationDetectionResult:
        """Detect an approximate location through the online provider."""

        ...

    def from_city_result(self, city: dict) -> LocationDetectionResult:
        """Normalize an embedded city record into a provider result."""

        ...

    def from_mpc_observatory_result(
        self,
        observatory: dict,
    ) -> LocationDetectionResult:
        """Normalize an MPC observatory record into a provider result."""

        ...

    def from_manual_coordinates_result(
        self,
        latitude: float,
        longitude: float,
        label: str = "Coordinate manuali",
    ) -> LocationDetectionResult:
        """Normalize validated coordinates into a provider result."""

        ...


LocationResultLoader = Callable[[], LocationDetectionResult | None]


@dataclass(frozen=True)
class StoredLocationInputs:
    """Provide saved and cached results lazily and in precedence order."""

    load_saved: LocationResultLoader
    load_cached: LocationResultLoader


@dataclass(frozen=True)
class StartupLocationInputs:
    """Capture one startup policy plus its lazy persisted-location sources."""

    preferences: StartupLocationPreferences
    stored: StoredLocationInputs


@dataclass(frozen=True)
class LocationSearchResult:
    """Describe whether a query is active and its immutable result sequence."""

    has_query: bool
    matches: tuple[dict, ...] = ()


@dataclass(frozen=True)
class LocationProviderFailure:
    """Record one unavailable provider without leaking an exception to Qt."""

    provider: str
    reason: str


@dataclass(frozen=True)
class LocationCommandResult:
    """Return the complete state-independent outcome of one UI command."""

    handled: bool
    detection: LocationDetectionResult | None = None
    message: str = ""
    offer_online_fallback: bool | None = None
    remember_online_consent: bool = False
    failure: LocationProviderFailure | None = None

    @classmethod
    def ignored(cls) -> LocationCommandResult:
        """Represent an unknown or no-longer-existing selection."""

        return cls(handled=False)

    @classmethod
    def selected(
        cls,
        detection: LocationDetectionResult,
        *,
        remember_online_consent: bool = False,
    ) -> LocationCommandResult:
        """Represent a successfully resolved location selection."""

        return cls(
            handled=True,
            detection=detection,
            remember_online_consent=remember_online_consent,
        )


@dataclass(frozen=True)
class StartupLocationResult:
    """Describe the result crossing the startup worker/Qt signal boundary."""

    detection: LocationDetectionResult | None
    persist: bool
    message: str
    failures: tuple[LocationProviderFailure, ...] = field(default_factory=tuple)


class LocationCommandWorkflow:
    """Execute location-facing application commands with explicit outcomes."""

    def __init__(
        self,
        *,
        repository: LocationRepositoryPort,
        service: LocationServicePort,
    ) -> None:
        self._repository = repository
        self._service = service

    def search(self, query: str, *, limit: int = 20) -> LocationSearchResult:
        """Search only when the normalized UI query is non-empty."""

        if not query.strip():
            return LocationSearchResult(has_query=False)
        return LocationSearchResult(
            has_query=True,
            matches=tuple(self._repository.search(query, limit=limit)),
        )

    @staticmethod
    def select_recent(
        index: int,
        candidates: Sequence[LocationDetectionResult],
    ) -> LocationCommandResult:
        """Resolve a recent-location index without trusting stale UI input."""

        if not 0 <= index < len(candidates):
            return LocationCommandResult.ignored()
        return LocationCommandResult.selected(candidates[index])

    def select_city(self, city_id: int) -> LocationCommandResult:
        """Resolve a city identifier through the repository and location policy."""

        city = self._repository.get_city(city_id)
        if not city:
            return LocationCommandResult.ignored()
        return LocationCommandResult.selected(self._service.from_city_result(city))

    def select_observatory(self, mpc_code: str) -> LocationCommandResult:
        """Resolve an MPC code through the repository and location policy."""

        observatory = self._repository.get_observatory(mpc_code)
        if not observatory:
            return LocationCommandResult.ignored()
        return LocationCommandResult.selected(
            self._service.from_mpc_observatory_result(observatory)
        )

    def select(self, kind: str, selection_id: str) -> LocationCommandResult:
        """Dispatch the stable kind/id pair exposed by the unified search model."""

        if kind == "city":
            try:
                city_id = int(selection_id)
            except ValueError:
                return LocationCommandResult.ignored()
            return self.select_city(city_id)
        if kind == "mpc_observatory":
            return self.select_observatory(selection_id)
        return LocationCommandResult.ignored()

    def set_manual(
        self,
        latitude: str,
        longitude: str,
        label: str,
    ) -> LocationCommandResult:
        """Validate localized coordinate text and resolve a manual location."""

        try:
            parsed_latitude = float(latitude.replace(",", "."))
            parsed_longitude = float(longitude.replace(",", "."))
        except ValueError:
            return LocationCommandResult(
                handled=True,
                message=tr("Coordinate non valide."),
            )

        if not -90 <= parsed_latitude <= 90 or not -180 <= parsed_longitude <= 180:
            return LocationCommandResult(
                handled=True,
                message=tr("Coordinate fuori intervallo."),
            )

        clean_label = label.strip() or tr("Coordinate manuali")
        return LocationCommandResult.selected(
            self._service.from_manual_coordinates_result(
                parsed_latitude,
                parsed_longitude,
                label=clean_label,
            )
        )

    def detect_system(self) -> LocationCommandResult:
        """Resolve the system-provider command into success or fallback UI state."""

        try:
            return LocationCommandResult.selected(
                self._service.detect_system_location()
            )
        except LocationUnavailableError as exc:
            return LocationCommandResult(
                handled=True,
                message=tr(
                    "La posizione di sistema non è disponibile. "
                    "Provare la posizione approssimata online?"
                ),
                offer_online_fallback=True,
                failure=LocationProviderFailure("system", exc.reason),
            )

    def detect_online(self) -> LocationCommandResult:
        """Resolve the consented approximate-online provider command."""

        try:
            result = self._service.detect_ip_location(allow_online=True)
        except LocationUnavailableError as exc:
            return LocationCommandResult(
                handled=True,
                message=APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE,
                failure=LocationProviderFailure("approximate_online", exc.reason),
            )
        return LocationCommandResult.selected(
            result,
            remember_online_consent=True,
        )

    def resolve_startup(
        self,
        inputs: StartupLocationInputs,
    ) -> StartupLocationResult:
        """Apply startup provider precedence, then saved/cache fallback lazily."""

        failures: list[LocationProviderFailure] = []
        preferences = inputs.preferences
        if preferences.use_system_location_on_startup:
            try:
                return StartupLocationResult(
                    self._service.detect_system_location(),
                    True,
                    "",
                )
            except LocationUnavailableError as exc:
                failures.append(LocationProviderFailure("system", exc.reason))

        if preferences.allow_approximate_online_location:
            try:
                return StartupLocationResult(
                    self._service.detect_ip_location(allow_online=True),
                    True,
                    "",
                    tuple(failures),
                )
            except LocationUnavailableError as exc:
                failures.append(
                    LocationProviderFailure("approximate_online", exc.reason)
                )

        stored = self.resolve_stored(inputs.stored)
        if stored is not None:
            return StartupLocationResult(
                stored.detection,
                stored.persist,
                stored.message,
                tuple(failures),
            )
        return StartupLocationResult(
            None,
            False,
            tr("Configura una località per ottenere meteo e cielo locale."),
            tuple(failures),
        )

    def resolve_stored(
        self,
        inputs: StoredLocationInputs,
    ) -> StartupLocationResult | None:
        """Load the first valid saved or cached location without eager I/O."""

        saved = inputs.load_saved()
        if saved is not None and self.result_has_valid_location(saved):
            return StartupLocationResult(
                saved,
                False,
                tr(
                    "Posizione salvata caricata: {city}.",
                    city=saved.location.city,
                ),
            )

        cached = inputs.load_cached()
        if cached is not None and self.result_has_valid_location(cached):
            return StartupLocationResult(
                cached,
                False,
                tr(
                    "Ultima posizione caricata: {city}.",
                    city=cached.location.city,
                ),
            )
        return None

    def recent_results(
        self,
        active: LocationDetectionResult | None,
        stored: StoredLocationInputs,
    ) -> tuple[LocationDetectionResult, ...]:
        """Return at most five valid locations, deduplicated by observer identity."""

        candidates = (active, stored.load_saved(), stored.load_cached())
        unique: list[LocationDetectionResult] = []
        seen: set[tuple[object, ...]] = set()
        for result in candidates:
            if result is None or not self.result_has_valid_location(result):
                continue
            key = (
                result.location.city,
                result.location.country,
                round(result.location.latitude, 3),
                round(result.location.longitude, 3),
                result.location.timezone,
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(result)
        return tuple(unique[:5])

    @staticmethod
    def result_has_valid_location(
        result: LocationDetectionResult | None,
    ) -> bool:
        """Validate the coordinates and timezone required by downstream refreshes."""

        if result is None:
            return False
        location = result.location
        return bool(
            location.timezone
            and -90 <= location.latitude <= 90
            and -180 <= location.longitude <= 180
        )

    @staticmethod
    def result_message(result: LocationDetectionResult) -> str:
        """Project a normalized provider result into the established UI message."""

        location = result.location
        if result.provider == "manual_city":
            return tr(
                "Posizione impostata su {city}, {country}.",
                city=location.city,
                country=location.country,
            )
        if result.provider == "manual_coordinates":
            return tr(
                "Coordinate impostate: {latitude}, {longitude}.",
                latitude=format_number(location.latitude, decimals=4),
                longitude=format_number(location.longitude, decimals=4),
            )
        if result.provider == "mpc_observatory":
            return result.message or tr("Osservatorio MPC selezionato.")
        if result.provider == "ip_geolocation":
            if result.source.endswith(" cached"):
                return tr(
                    "Ultima posizione caricata: {city}.",
                    city=location.city,
                )
            return tr(
                "Posizione approssimata rilevata tramite connessione internet: "
                "{city}, {country}. La precisione può essere limitata.",
                city=location.city,
                country=location.country or tr("sconosciuto"),
            )
        if result.provider in {"windows_precise", "windows_coarse", "geoclue2"}:
            if location.country:
                return tr(
                    "Posizione di sistema acquisita: {city}, {country}.",
                    city=location.city,
                    country=location.country,
                )
            return tr("Posizione di sistema acquisita.")
        return result.message or tr("Posizione caricata.")
