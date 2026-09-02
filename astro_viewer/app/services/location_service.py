"""Coordinate location-provider selection, enrichment, and timezone policy.

Concrete Windows, GeoClue, online, cache, and manual adapters live in
``location_providers``. Their historical imports are re-exported here to keep
existing integrations source-compatible while this module owns only selection
and normalization policy.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path
from typing import Protocol, Sequence

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.platform_capabilities import (
    PlatformCapabilities,
    detect_platform_capabilities,
)
from astro_viewer.app.services.coordinate_timezone_service import (
    DEFAULT_COORDINATE_TIMEZONE_RESOLVER,
    CoordinateTimezoneResolver,
    is_iana_timezone,
)
from astro_viewer.app.services.localization import tr
from astro_viewer.app.services.location_providers import (
    APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE,
    SYSTEM_LOCATION_UNAVAILABLE_MESSAGE,
    WINDOWS_LOCATION_UNAVAILABLE_MESSAGE,
    WINDOWS_TO_IANA_TIMEZONES,
    GeoClueLocationProvider,
    IpGeolocationProvider,
    LocationDetectionResult,
    LocationProvider,
    LocationProviderAdapters,
    LocationUnavailableError,
    ManualCityProvider,
    ManualCoordinatesProvider,
    WindowsCoarseLocationProvider,
    WindowsLocationProvider,
    _create_geoclue_position_source,
    _hidden_subprocess_kwargs,
    _is_number,
    _log_windows_failure,
    _normalize_reason,
    _parse_provider_stdout,
    _qt_horizontal_accuracy,
    _qt_position_error_reason,
    _reason_from_error,
    _request_qt_position,
    _required_coordinate,
    _run_windows_location_diagnostics,
    _validate_coordinate,
    _validated_coordinate,
    _windows_async_bridge_script,
    _windows_diagnostics_script,
    _windows_geolocation_script,
    build_location_provider_adapters,
    system_timezone,
)


__all__ = [
    "APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE",
    "CityReverseLookup",
    "GeoClueLocationProvider",
    "IpGeolocationProvider",
    "LocationDetectionResult",
    "LocationProvider",
    "LocationProviderAdapters",
    "LocationService",
    "LocationUnavailableError",
    "ManualCityProvider",
    "ManualCoordinatesProvider",
    "SYSTEM_LOCATION_UNAVAILABLE_MESSAGE",
    "WINDOWS_LOCATION_UNAVAILABLE_MESSAGE",
    "WINDOWS_TO_IANA_TIMEZONES",
    "WindowsCoarseLocationProvider",
    "WindowsLocationProvider",
    "_create_geoclue_position_source",
    "_hidden_subprocess_kwargs",
    "_is_number",
    "_log_windows_failure",
    "_normalize_reason",
    "_parse_provider_stdout",
    "_qt_horizontal_accuracy",
    "_qt_position_error_reason",
    "_reason_from_error",
    "_request_qt_position",
    "_required_coordinate",
    "_run_windows_location_diagnostics",
    "_validate_coordinate",
    "_validated_coordinate",
    "_windows_async_bridge_script",
    "_windows_diagnostics_script",
    "_windows_geolocation_script",
    "build_location_provider_adapters",
    "system_timezone",
]


logger = logging.getLogger(__name__)


class CityReverseLookup(Protocol):
    """Find the nearest locally known city for detected coordinates."""

    def nearest_by_coordinates(
        self,
        latitude: float,
        longitude: float,
        max_radius_km: float = 50.0,
    ) -> dict | None:
        ...


class LocationService:
    def __init__(
        self,
        windows_provider: LocationProvider | None = None,
        windows_coarse_provider: LocationProvider | None = None,
        ip_provider: IpGeolocationProvider | None = None,
        city_provider: ManualCityProvider | None = None,
        coordinates_provider: ManualCoordinatesProvider | None = None,
        city_resolver: CityReverseLookup | None = None,
        timezone_resolver: CoordinateTimezoneResolver | None = None,
        cache_path: Path | None = None,
        platform_capabilities: PlatformCapabilities | None = None,
        system_providers: Sequence[LocationProvider] | None = None,
        provider_adapters: LocationProviderAdapters | None = None,
    ):
        self.platform_capabilities = platform_capabilities or detect_platform_capabilities()
        adapters = provider_adapters or build_location_provider_adapters(cache_path)
        self.windows_provider = windows_provider or adapters.windows
        self.windows_coarse_provider = windows_coarse_provider or adapters.windows_coarse
        self.geoclue_provider = adapters.geoclue
        self.system_providers = tuple(
            system_providers
            if system_providers is not None
            else self._default_system_providers()
        )
        self.ip_provider = ip_provider or adapters.ip
        self.city_provider = city_provider or adapters.city
        self.coordinates_provider = coordinates_provider or adapters.coordinates
        self.city_resolver = city_resolver
        self.timezone_resolver = (
            timezone_resolver
            if timezone_resolver is not None
            else DEFAULT_COORDINATE_TIMEZONE_RESOLVER
        )
        self.last_result: LocationDetectionResult | None = None
        self.last_error_reason = ""

    def detect_best_location(self, allow_ip: bool = False) -> LocationDetectionResult:
        providers = list(self.system_providers)
        if allow_ip:
            providers.append(self.ip_provider)
        errors = []
        for provider in providers:
            try:
                result = provider.detect()
            except LocationUnavailableError as exc:
                errors.append(f"{provider.name}: {exc.reason}")
                self.last_error_reason = exc.reason
                continue
            result = self._normalize_result(result)
            self.last_result = result
            return result
        raise LocationUnavailableError(
            SYSTEM_LOCATION_UNAVAILABLE_MESSAGE,
            "; ".join(errors) or "unavailable provider",
        )

    def detect_system_location(self) -> LocationDetectionResult:
        errors = []
        for provider in self.system_providers:
            try:
                result = provider.detect()
            except LocationUnavailableError as exc:
                errors.append(f"{provider.name}: {exc.reason}")
                self.last_error_reason = exc.reason
                continue
            result = self._normalize_result(result)
            self.last_result = result
            return result
        raise LocationUnavailableError(
            SYSTEM_LOCATION_UNAVAILABLE_MESSAGE,
            "; ".join(errors) or "unavailable provider",
        )

    def detect_windows_location(self) -> LocationDetectionResult:
        for provider in (self.windows_provider, self.windows_coarse_provider):
            try:
                result = provider.detect()
            except LocationUnavailableError as exc:
                self.last_error_reason = exc.reason
                continue
            result = self._normalize_result(result)
            self.last_result = result
            return result
        raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE, self.last_error_reason or "unavailable provider")

    def detect_ip_location(self, allow_online: bool) -> LocationDetectionResult:
        if not allow_online:
            raise LocationUnavailableError(APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE, "online location not allowed")
        result = self._normalize_result(self.ip_provider.detect())
        self.last_result = result
        return result

    def from_city_result(self, city: dict) -> LocationDetectionResult:
        result = self._normalize_result(self.city_provider.detect_from_city(city))
        self.last_result = result
        return result

    def from_manual_coordinates_result(
        self,
        latitude: float,
        longitude: float,
        label: str = "Coordinate manuali",
    ) -> LocationDetectionResult:
        result = self._normalize_result(
            self.coordinates_provider.detect_from_coordinates(latitude, longitude, label)
        )
        self.last_result = result
        return result

    def from_city(self, city: dict) -> ObserverLocation:
        return self.from_city_result(city).location

    def from_mpc_observatory_result(self, observatory: dict) -> LocationDetectionResult:
        code = str(observatory["mpc_code"]).strip().upper()
        name = str(observatory["name"]).strip()
        result = LocationDetectionResult(
            location=ObserverLocation(
                city=name,
                country="",
                latitude=float(observatory["latitude"]),
                longitude=float(observatory["longitude"]),
                timezone="UTC",
            ),
            provider="mpc_observatory",
            source="MPC Observatory Codes",
            accuracy=tr("coordinate MPC"),
            approximate=False,
            message=tr(
                "Località impostata su {observatory} (MPC {code}).",
                observatory=name,
                code=code,
            ),
        )
        result = self._normalize_result(result)
        self.last_result = result
        return result

    def from_manual_coordinates(
        self,
        latitude: float,
        longitude: float,
        label: str = "Coordinate manuali",
    ) -> ObserverLocation:
        return self.from_manual_coordinates_result(latitude, longitude, label).location

    def from_windows_location(self) -> ObserverLocation:
        return self.detect_windows_location().location

    def from_system_location(self) -> ObserverLocation:
        return self.detect_system_location().location

    def from_ip_location(self, allow_online: bool) -> ObserverLocation:
        return self.detect_ip_location(allow_online).location

    def _location_from_windows_payload(self, payload: dict) -> ObserverLocation:
        return WindowsLocationProvider()._location_from_windows_payload(
            payload,
            provider_label=tr("Posizione Windows"),
        )

    def windows_location_diagnostics(self) -> dict:
        provider = self.windows_provider
        if hasattr(provider, "diagnostics"):
            return provider.diagnostics()
        report = {
            "ok": False,
            "provider": getattr(provider, "name", "windows_precise"),
            "providerStatus": "diagnostics unavailable",
            "accessStatus": "n/d",
            "coordinatesReceived": False,
            "errorDetails": {
                "type": "UnsupportedProvider",
                "message": "Injected Windows provider does not expose diagnostics.",
            },
            "rawProviderResponse": "",
        }
        logger.info(
            "Windows location diagnostics unavailable: status=%s.",
            report["providerStatus"],
        )
        return report

    def system_timezone(self) -> str:
        return system_timezone()

    def _normalize_result(self, result: LocationDetectionResult) -> LocationDetectionResult:
        if result.provider in {"windows_precise", "windows_coarse", "geoclue2"}:
            return self._normalize_system_result(result)
        if result.provider in {"manual_city", "manual_coordinates", "mpc_observatory"}:
            return self._normalize_coordinate_timezone(result)
        if result.provider == "ip_geolocation":
            raw_timezone = result.raw_provider_timezone.strip()
            if is_iana_timezone(raw_timezone):
                return _with_timezone(result, raw_timezone)
            return self._normalize_coordinate_timezone(result)
        return result

    def _normalize_coordinate_timezone(self, result: LocationDetectionResult) -> LocationDetectionResult:
        coordinate_timezone = self._coordinate_timezone(
            result.location.latitude,
            result.location.longitude,
        )
        if not coordinate_timezone:
            fallback_timezone = _valid_timezone_or_none(system_timezone()) or "UTC"
            return _with_timezone(result, fallback_timezone)

        logger.info(
            "Location timezone resolved from coordinates: provider=%s.",
            result.provider,
        )
        return _with_timezone(
            result,
            coordinate_timezone,
            source_suffix="coordinate timezone",
        )

    def _normalize_system_result(self, result: LocationDetectionResult) -> LocationDetectionResult:
        latitude = result.location.latitude
        longitude = result.location.longitude
        raw_timezone = result.raw_provider_timezone or result.location.timezone
        coordinate_timezone = self._coordinate_timezone(latitude, longitude)
        city = (
            self._nearest_city(latitude, longitude, max_radius_km=50.0)
            if result.provider in {"windows_precise", "geoclue2"}
            else None
        )
        if city:
            timezone_name = (
                coordinate_timezone
                or self._provider_timezone_fallback(result)
            )
            logger.info(
                "System location enriched from the local city database: "
                "provider=%s distance_km=%.1f coordinate_timezone=%s.",
                result.provider,
                float(city.get("distance_km") or 0.0),
                bool(coordinate_timezone),
            )
            source = _append_source_once(result.source, "local City reverse lookup")
            if coordinate_timezone:
                source = _append_source_once(source, "coordinate timezone")
            return replace(
                result,
                location=ObserverLocation(
                    city=city["city"],
                    country=city["country"],
                    latitude=latitude,
                    longitude=longitude,
                    timezone=timezone_name,
                ),
                source=source,
                region=str(city.get("admin_region") or result.region),
                country_code=str(city.get("country_code") or result.country_code),
                raw_provider_timezone=raw_timezone,
                message=tr(
                    "Posizione di sistema acquisita: {city}, {country}.",
                    city=city["city"],
                    country=city["country"],
                ),
            )

        timezone_name = coordinate_timezone or self._provider_timezone_fallback(result)
        if coordinate_timezone:
            logger.info(
                "System location timezone resolved from coordinates: provider=%s.",
                result.provider,
            )
            return _with_timezone(
                replace(result, raw_provider_timezone=raw_timezone),
                timezone_name,
                source_suffix="coordinate timezone",
            )

        logger.info(
            "System location kept the provider/system timezone after coordinate lookup miss: provider=%s.",
            result.provider,
        )
        return _with_timezone(
            replace(result, raw_provider_timezone=raw_timezone),
            timezone_name,
        )

    def _normalize_windows_result(self, result: LocationDetectionResult) -> LocationDetectionResult:
        return self._normalize_system_result(result)

    def _nearest_city(self, latitude: float, longitude: float, max_radius_km: float) -> dict | None:
        if self.city_resolver is None:
            return None
        try:
            return self.city_resolver.nearest_by_coordinates(latitude, longitude, max_radius_km=max_radius_km)
        except Exception:
            logger.warning("City reverse lookup failed for system location.", exc_info=True)
            return None

    def _coordinate_timezone(self, latitude: float, longitude: float) -> str | None:
        try:
            timezone_name = self.timezone_resolver.timezone_at(latitude, longitude)
        except Exception:
            logger.warning("Coordinate timezone resolver failed.", exc_info=True)
            return None
        return _valid_timezone_or_none(str(timezone_name or ""))

    @staticmethod
    def _provider_timezone_fallback(result: LocationDetectionResult) -> str:
        raw_timezone = result.raw_provider_timezone.strip()
        candidates = (
            WINDOWS_TO_IANA_TIMEZONES.get(raw_timezone, ""),
            raw_timezone,
            result.location.timezone,
        )
        for candidate in candidates:
            valid_timezone = _valid_timezone_or_none(candidate)
            if valid_timezone:
                return valid_timezone
        return _valid_timezone_or_none(system_timezone()) or "UTC"

    def _default_system_providers(self) -> tuple[LocationProvider, ...]:
        if self.platform_capabilities.is_windows:
            return self.windows_provider, self.windows_coarse_provider
        if self.platform_capabilities.is_linux:
            return (self.geoclue_provider,)
        return ()


def _with_timezone(
    result: LocationDetectionResult,
    timezone_name: str,
    *,
    source_suffix: str = "",
) -> LocationDetectionResult:
    source = (
        _append_source_once(result.source, source_suffix)
        if source_suffix
        else result.source
    )
    if result.location.timezone == timezone_name and source == result.source:
        return result
    return replace(
        result,
        location=replace(result.location, timezone=timezone_name),
        source=source,
    )


def _append_source_once(source: str, suffix: str) -> str:
    parts = [part.strip() for part in source.split(";") if part.strip()]
    if suffix not in parts:
        parts.append(suffix)
    return "; ".join(parts)


def _valid_timezone_or_none(timezone_name: str) -> str | None:
    normalized = str(timezone_name or "").strip()
    return normalized if is_iana_timezone(normalized) else None
