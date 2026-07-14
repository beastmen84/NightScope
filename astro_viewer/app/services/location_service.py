from __future__ import annotations

import json
import logging
import math
import subprocess
from dataclasses import asdict, dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

import requests

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.coordinate_timezone_service import (
    DEFAULT_COORDINATE_TIMEZONE_RESOLVER,
    CoordinateTimezoneResolver,
    is_iana_timezone,
)
from astro_viewer.app.services.localization import format_number, tr


logger = logging.getLogger(__name__)

WINDOWS_TO_IANA_TIMEZONES = {
    "W. Europe Standard Time": "Europe/Berlin",
    "Romance Standard Time": "Europe/Paris",
    "Central Europe Standard Time": "Europe/Budapest",
    "GMT Standard Time": "Europe/London",
    "Greenwich Standard Time": "Atlantic/Reykjavik",
    "E. Africa Standard Time": "Africa/Nairobi",
    "Eastern Standard Time": "America/New_York",
    "Central Standard Time": "America/Chicago",
    "Mountain Standard Time": "America/Denver",
    "Pacific Standard Time": "America/Los_Angeles",
    "Tokyo Standard Time": "Asia/Tokyo",
    "AUS Eastern Standard Time": "Australia/Sydney",
    "Argentina Standard Time": "America/Argentina/Buenos_Aires",
}

WINDOWS_LOCATION_UNAVAILABLE_MESSAGE = (
    tr("La posizione Windows non è disponibile. Scegli una città o inserisci le coordinate manualmente.")
)
APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE = (
    tr("La posizione approssimata online non è disponibile. Scegli una città o inserisci le coordinate manualmente.")
)


@dataclass(frozen=True)
class LocationDetectionResult:
    location: ObserverLocation
    provider: str
    source: str
    accuracy: str
    approximate: bool = False
    region: str = ""
    country_code: str = ""
    raw_provider_timezone: str = ""
    message: str = ""

    def to_qml(self) -> dict:
        data = asdict(self)
        data["location"] = {
            "city": self.location.city,
            "country": self.location.country,
            "country_code": self.country_code,
            "latitude": self.location.latitude,
            "longitude": self.location.longitude,
            "timezone": self.location.timezone,
        }
        return data


class LocationUnavailableError(RuntimeError):
    """Raised when a provider cannot return a usable location."""

    def __init__(self, message: str = WINDOWS_LOCATION_UNAVAILABLE_MESSAGE, reason: str = "unavailable provider"):
        super().__init__(message)
        self.reason = reason


class LocationProvider(Protocol):
    name: str

    def detect(self) -> LocationDetectionResult:
        ...


class CityReverseLookup(Protocol):
    def nearest_by_coordinates(self, latitude: float, longitude: float, max_radius_km: float = 50.0) -> dict | None:
        ...


class WindowsLocationProvider:
    name = "windows_precise"

    def detect(self) -> LocationDetectionResult:
        payload = self._windows_location_payload(_windows_geolocation_script(precise=True))
        location = self._location_from_windows_payload(
            payload,
            provider_label=tr("Posizione Windows"),
        )
        accuracy = payload.get("accuracy")
        accuracy_label = (
            tr("{value} m", value=format_number(float(accuracy)))
            if _is_number(accuracy)
            else tr("precisa")
        )
        raw_timezone = str(payload.get("raw_provider_timezone") or payload.get("timezone") or "")
        return LocationDetectionResult(
            location=location,
            provider=self.name,
            source="Windows.Devices.Geolocation.Geolocator",
            accuracy=accuracy_label,
            approximate=False,
            raw_provider_timezone=raw_timezone,
            message=tr("Posizione Windows acquisita."),
        )

    def diagnostics(self) -> dict:
        report = _run_windows_location_diagnostics()
        logger.info("Windows location diagnostics report: %s", json.dumps(report, ensure_ascii=True))
        return report

    def _windows_location_payload(self, script: str) -> dict:
        try:
            result = subprocess.run(
                ["powershell", "-Sta", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                timeout=18,
                check=False,
                **_hidden_subprocess_kwargs(),
            )
        except subprocess.TimeoutExpired as exc:
            _log_windows_failure("timeout", "PowerShell location request timed out.")
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE, "timeout") from exc
        except (OSError, subprocess.SubprocessError) as exc:
            _log_windows_failure("unavailable provider", str(exc))
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE, "unavailable provider") from exc

        payload = _parse_provider_stdout(result.stdout)
        if not payload:
            reason = _reason_from_error(result.stderr or result.stdout)
            _log_windows_failure(reason, result.stderr.strip() or "No provider output.")
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE, reason)
        if not payload.get("ok", False):
            reason = _normalize_reason(str(payload.get("reason") or "unavailable provider"))
            _log_windows_failure(reason, str(payload.get("detail") or "Provider returned failure."))
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE, reason)
        return payload

    def _location_from_windows_payload(
        self,
        payload: dict,
        provider_label: str,
    ) -> ObserverLocation:
        latitude = _required_coordinate(payload, "latitude", -90.0, 90.0, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE)
        longitude = _required_coordinate(payload, "longitude", -180.0, 180.0, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE)
        windows_timezone = payload.get("timezone", "")
        return ObserverLocation(
            city=provider_label,
            country="",
            latitude=latitude,
            longitude=longitude,
            timezone=WINDOWS_TO_IANA_TIMEZONES.get(windows_timezone, system_timezone()),
        )


class WindowsCoarseLocationProvider(WindowsLocationProvider):
    name = "windows_coarse"

    def detect(self) -> LocationDetectionResult:
        payload = self._windows_location_payload(_windows_geolocation_script(precise=False))
        location = self._location_from_windows_payload(
            payload,
            provider_label=tr("Posizione Windows approssimata"),
        )
        accuracy = payload.get("accuracy")
        accuracy_label = (
            tr("{value} m", value=format_number(float(accuracy)))
            if _is_number(accuracy)
            else tr("approssimata")
        )
        raw_timezone = str(payload.get("raw_provider_timezone") or payload.get("timezone") or "")
        return LocationDetectionResult(
            location=location,
            provider=self.name,
            source="Windows.Devices.Geolocation.Geolocator coarse",
            accuracy=accuracy_label,
            approximate=True,
            raw_provider_timezone=raw_timezone,
            message=tr("Posizione Windows approssimata acquisita."),
        )


class IpGeolocationProvider:
    name = "ip_geolocation"
    REQUEST_TIMEOUT_SECONDS = 4
    ENDPOINTS = (
        "https://ipapi.co/json/",
        "https://ipwho.is/",
    )

    def __init__(self, cache_path: Path | None = None):
        self._cache_path = cache_path

    def detect(self) -> LocationDetectionResult:
        last_error = ""
        for endpoint in self.ENDPOINTS:
            try:
                response = requests.get(endpoint, timeout=self.REQUEST_TIMEOUT_SECONDS)
                response.raise_for_status()
                payload = response.json()
                result = self._result_from_payload(endpoint, payload)
            except (requests.RequestException, LocationUnavailableError, TypeError, ValueError) as exc:
                last_error = str(exc)
                logger.warning("IP geolocation provider failed: %s", endpoint, exc_info=True)
                continue
            self._write_cache(result)
            return result

        cached = self._read_cache()
        if cached:
            logger.info("Using cached approximate IP geolocation.")
            return cached
        raise LocationUnavailableError(APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE, last_error or "unavailable provider")

    def _result_from_payload(self, endpoint: str, payload: dict) -> LocationDetectionResult:
        if not isinstance(payload, dict):
            raise ValueError("IP geolocation returned a non-object payload.")
        if endpoint.endswith("ipwho.is/") and payload.get("success") is False:
            raise ValueError(str(payload.get("message") or "IP geolocation failed."))

        city = str(payload.get("city") or "").strip() or tr("Posizione approssimata")
        region = str(payload.get("region") or payload.get("region_name") or "").strip()
        country = str(payload.get("country_name") or payload.get("country") or "").strip()
        timezone_value = payload.get("timezone")
        if isinstance(timezone_value, dict):
            timezone_value = timezone_value.get("id")
        provider_timezone = str(timezone_value or "").strip()
        latitude = _required_coordinate(payload, "latitude", -90.0, 90.0, APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE)
        longitude = _required_coordinate(payload, "longitude", -180.0, 180.0, APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE)
        accuracy = payload.get("accuracy_radius") or payload.get("accuracy") or tr("livello città")
        location = ObserverLocation(
            city=city,
            country=country,
            latitude=latitude,
            longitude=longitude,
            timezone=provider_timezone or system_timezone(),
        )
        return LocationDetectionResult(
            location=location,
            provider=self.name,
            source=endpoint,
            accuracy=str(accuracy),
            approximate=True,
            region=region,
            raw_provider_timezone=provider_timezone,
            message=tr(
                "Posizione approssimata rilevata tramite connessione internet: "
                "{city}, {country}. La precisione può essere limitata.",
                city=city,
                country=country or tr("sconosciuto"),
            ),
        )

    def _write_cache(self, result: LocationDetectionResult) -> None:
        if not self._cache_path:
            return
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = result.to_qml()
            payload.pop("message", None)
            payload["cachedAt"] = datetime.now().isoformat(timespec="seconds")
            self._cache_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            logger.warning("Could not write approximate location cache.", exc_info=True)

    def _read_cache(self) -> LocationDetectionResult | None:
        if not self._cache_path or not self._cache_path.exists():
            return None
        try:
            payload = json.loads(self._cache_path.read_text(encoding="utf-8"))
            location_payload = payload["location"]
            location = ObserverLocation(
                city=location_payload["city"],
                country=location_payload["country"],
                latitude=float(location_payload["latitude"]),
                longitude=float(location_payload["longitude"]),
                timezone=location_payload["timezone"],
            )
            return LocationDetectionResult(
                location=location,
                provider=payload.get("provider", self.name),
                source=f"{payload.get('source', 'cached IP geolocation')} cached",
                accuracy=payload.get("accuracy", tr("livello città")),
                approximate=True,
                region=payload.get("region", ""),
                raw_provider_timezone=str(payload.get("raw_provider_timezone") or ""),
                message=tr(
                    "Posizione approssimata rilevata tramite connessione internet: "
                    "{city}, {country}. La precisione può essere limitata.",
                    city=location.city,
                    country=location.country or tr("sconosciuto"),
                ),
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            logger.warning("Approximate location cache is invalid.", exc_info=True)
            return None


class ManualCityProvider:
    name = "manual_city"

    def detect_from_city(self, city: dict) -> LocationDetectionResult:
        location = ObserverLocation(
            city=city["city"],
            country=city["country"],
            latitude=float(city["latitude"]),
            longitude=float(city["longitude"]),
            timezone=city["timezone"],
        )
        return LocationDetectionResult(
            location=location,
            provider=self.name,
            source="SQLite City",
            accuracy=tr("coordinate della città"),
            approximate=False,
            country_code=str(city.get("country_code") or ""),
            message=tr(
                "Posizione impostata su {city}, {country}.",
                city=city["city"],
                country=city["country"],
            ),
        )


class ManualCoordinatesProvider:
    name = "manual_coordinates"

    def detect_from_coordinates(
        self,
        latitude: float,
        longitude: float,
        label: str = "Coordinate manuali",
        timezone: str | None = None,
    ) -> LocationDetectionResult:
        _validate_coordinate(latitude, -90.0, 90.0, "Invalid latitude.")
        _validate_coordinate(longitude, -180.0, 180.0, "Invalid longitude.")
        location = ObserverLocation(
            city=label,
            country="",
            latitude=latitude,
            longitude=longitude,
            timezone=timezone or system_timezone(),
        )
        return LocationDetectionResult(
            location=location,
            provider=self.name,
            source=tr("Coordinate manuali"),
            accuracy=tr("fornita dall'utente"),
            approximate=False,
            raw_provider_timezone=str(timezone or "").strip(),
            message=tr(
                "Coordinate impostate: {latitude}, {longitude}.",
                latitude=format_number(latitude, decimals=4),
                longitude=format_number(longitude, decimals=4),
            ),
        )


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
    ):
        self.windows_provider = windows_provider or WindowsLocationProvider()
        self.windows_coarse_provider = windows_coarse_provider or WindowsCoarseLocationProvider()
        self.ip_provider = ip_provider or IpGeolocationProvider(cache_path)
        self.city_provider = city_provider or ManualCityProvider()
        self.coordinates_provider = coordinates_provider or ManualCoordinatesProvider()
        self.city_resolver = city_resolver
        self.timezone_resolver = (
            timezone_resolver
            if timezone_resolver is not None
            else DEFAULT_COORDINATE_TIMEZONE_RESOLVER
        )
        self.last_result: LocationDetectionResult | None = None
        self.last_error_reason = ""

    def detect_best_location(self, allow_ip: bool = False) -> LocationDetectionResult:
        providers: list[LocationProvider] = [self.windows_provider, self.windows_coarse_provider]
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
            result = self.normalize_result(result)
            self.last_result = result
            return result
        raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE, "; ".join(errors) or "unavailable provider")

    def detect_windows_location(self) -> LocationDetectionResult:
        for provider in (self.windows_provider, self.windows_coarse_provider):
            try:
                result = provider.detect()
            except LocationUnavailableError as exc:
                self.last_error_reason = exc.reason
                continue
            result = self.normalize_result(result)
            self.last_result = result
            return result
        raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE, self.last_error_reason or "unavailable provider")

    def detect_ip_location(self, allow_online: bool) -> LocationDetectionResult:
        if not allow_online:
            raise LocationUnavailableError(APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE, "online location not allowed")
        result = self.normalize_result(self.ip_provider.detect())
        self.last_result = result
        return result

    def from_city_result(self, city: dict) -> LocationDetectionResult:
        result = self.city_provider.detect_from_city(city)
        self.last_result = result
        return result

    def from_manual_coordinates_result(
        self,
        latitude: float,
        longitude: float,
        label: str = "Coordinate manuali",
        timezone: str | None = None,
    ) -> LocationDetectionResult:
        result = self.normalize_result(
            self.coordinates_provider.detect_from_coordinates(latitude, longitude, label, timezone)
        )
        self.last_result = result
        return result

    def from_city(self, city: dict) -> ObserverLocation:
        return self.from_city_result(city).location

    def from_manual_coordinates(
        self,
        latitude: float,
        longitude: float,
        label: str = "Coordinate manuali",
        timezone: str | None = None,
    ) -> ObserverLocation:
        return self.from_manual_coordinates_result(latitude, longitude, label, timezone).location

    def from_windows_location(self) -> ObserverLocation:
        return self.detect_windows_location().location

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
        logger.info("Windows location diagnostics report: %s", json.dumps(report, ensure_ascii=True))
        return report

    def system_timezone(self) -> str:
        return system_timezone()

    def normalize_result(self, result: LocationDetectionResult) -> LocationDetectionResult:
        if result.provider in {"windows_precise", "windows_coarse"}:
            return self._normalize_windows_result(result)
        if result.provider == "manual_coordinates":
            return self._normalize_coordinate_timezone(
                result,
                preserve_valid_provider_timezone=True,
            )
        if result.provider == "ip_geolocation":
            return self._normalize_coordinate_timezone(
                result,
                preserve_valid_provider_timezone=True,
            )
        return result

    def _normalize_coordinate_timezone(
        self,
        result: LocationDetectionResult,
        *,
        preserve_valid_provider_timezone: bool,
    ) -> LocationDetectionResult:
        raw_timezone = result.raw_provider_timezone.strip()
        if preserve_valid_provider_timezone and is_iana_timezone(raw_timezone):
            return _with_timezone(result, raw_timezone)

        coordinate_timezone = self._coordinate_timezone(
            result.location.latitude,
            result.location.longitude,
        )
        if not coordinate_timezone:
            return result

        logger.info(
            "Location timezone resolved from coordinates: provider=%s timezone=%s",
            result.provider,
            coordinate_timezone,
        )
        return _with_timezone(
            result,
            coordinate_timezone,
            source_suffix="coordinate timezone",
        )

    def _normalize_windows_result(self, result: LocationDetectionResult) -> LocationDetectionResult:
        latitude = result.location.latitude
        longitude = result.location.longitude
        raw_timezone = result.raw_provider_timezone or result.location.timezone
        coordinate_timezone = self._coordinate_timezone(latitude, longitude)
        city = (
            self._nearest_city(latitude, longitude, max_radius_km=50.0)
            if result.provider == "windows_precise"
            else None
        )
        if city:
            timezone_name = (
                coordinate_timezone
                or self._provider_timezone_fallback(result)
            )
            logger.info(
                "Windows precise location normalized via local City database: raw_timezone=%s city=%s country=%s timezone=%s distance_km=%.1f",
                raw_timezone,
                city["city"],
                city["country"],
                timezone_name,
                float(city.get("distance_km") or 0.0),
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
                    "Posizione Windows acquisita: {city}, {country}.",
                    city=city["city"],
                    country=city["country"],
                ),
            )

        timezone_name = coordinate_timezone or self._provider_timezone_fallback(result)
        if coordinate_timezone:
            logger.info(
                "Windows location timezone resolved from coordinates: provider=%s raw_timezone=%s timezone=%s",
                result.provider,
                raw_timezone,
                timezone_name,
            )
            return _with_timezone(
                replace(result, raw_provider_timezone=raw_timezone),
                timezone_name,
                source_suffix="coordinate timezone",
            )

        logger.info(
            "Windows location kept provider/system timezone after coordinate lookup miss: provider=%s raw_timezone=%s",
            result.provider,
            raw_timezone,
        )
        return _with_timezone(
            replace(result, raw_provider_timezone=raw_timezone),
            timezone_name,
        )

    def _nearest_city(self, latitude: float, longitude: float, max_radius_km: float) -> dict | None:
        if self.city_resolver is None:
            return None
        try:
            return self.city_resolver.nearest_by_coordinates(latitude, longitude, max_radius_km=max_radius_km)
        except Exception:
            logger.warning("City reverse lookup failed for Windows precise location.", exc_info=True)
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
            system_timezone(),
            "UTC",
        )
        for candidate in candidates:
            valid_timezone = _valid_timezone_or_none(candidate)
            if valid_timezone:
                return valid_timezone
        return "UTC"


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


def _windows_geolocation_script(precise: bool) -> str:
    accuracy = "High" if precise else "Default"
    desired_accuracy_meters = "" if precise else "$locator.DesiredAccuracyInMeters = 50000"
    return rf"""
$ErrorActionPreference = "Stop"
function Emit($payload) {{ $payload | ConvertTo-Json -Compress; exit 0 }}
try {{
  Add-Type -AssemblyName System.Runtime.WindowsRuntime
  {_windows_async_bridge_script()}
  $null = [Windows.Devices.Geolocation.Geolocator,Windows.Devices.Geolocation,ContentType=WindowsRuntime]
  $null = [Windows.Devices.Geolocation.GeolocationAccessStatus,Windows.Devices.Geolocation,ContentType=WindowsRuntime]
  $null = [Windows.Devices.Geolocation.PositionAccuracy,Windows.Devices.Geolocation,ContentType=WindowsRuntime]
  $accessOperation = [Windows.Devices.Geolocation.Geolocator]::RequestAccessAsync()
  $accessTask = Convert-NightScopeIAsyncOperationToTask $accessOperation ([Windows.Devices.Geolocation.GeolocationAccessStatus,Windows.Devices.Geolocation,ContentType=WindowsRuntime])
  if (-not $accessTask.Wait(10000)) {{ Emit(@{{ ok = $false; reason = "timeout"; detail = "RequestAccessAsync timed out" }}) }}
  $status = $accessTask.Result.ToString()
  if ($status -eq "Denied") {{ Emit(@{{ ok = $false; reason = "permission denied"; access_status = $status; detail = "GeolocationAccessStatus.Denied" }}) }}
  if ($status -eq "Unspecified") {{ Emit(@{{ ok = $false; reason = "service disabled"; access_status = $status; detail = "GeolocationAccessStatus.Unspecified" }}) }}
  if ($status -ne "Allowed") {{ Emit(@{{ ok = $false; reason = "unavailable provider"; access_status = $status; detail = "Unexpected GeolocationAccessStatus" }}) }}
  $locator = [Windows.Devices.Geolocation.Geolocator]::new()
  $locator.DesiredAccuracy = [Windows.Devices.Geolocation.PositionAccuracy]::{accuracy}
  {desired_accuracy_meters}
  $operation = $locator.GetGeopositionAsync()
  $task = Convert-NightScopeIAsyncOperationToTask $operation ([Windows.Devices.Geolocation.Geoposition,Windows.Devices.Geolocation,ContentType=WindowsRuntime])
  if (-not $task.Wait(10000)) {{ Emit(@{{ ok = $false; reason = "timeout"; access_status = $status; detail = "GetGeopositionAsync timed out" }}) }}
  $coordinate = $task.Result.Coordinate
  $position = $coordinate.Point.Position
  Emit(@{{
    ok = $true
    access_status = $status
    latitude = $position.Latitude
    longitude = $position.Longitude
    accuracy = $coordinate.Accuracy
    timezone = (Get-TimeZone).Id
    raw_provider_timezone = (Get-TimeZone).Id
  }})
}} catch {{
  $message = $_.Exception.Message
  $reason = "WinRT error"
  if ($message -match "RPC_E_WRONG_THREAD|wrong thread|context") {{ $reason = "called from wrong thread/context" }}
  elseif ($message -match "denied|unauthorized|access") {{ $reason = "permission denied" }}
  elseif ($message -match "disabled") {{ $reason = "service disabled" }}
  elseif ($message -match "timeout|timed out") {{ $reason = "timeout" }}
  Emit(@{{ ok = $false; reason = $reason; detail = $message }})
}}
"""


def _windows_async_bridge_script() -> str:
    return r"""
function Get-NightScopeAsTaskOperationMethod {
  if ($script:nightScopeAsTaskOperationMethod) {
    return $script:nightScopeAsTaskOperationMethod
  }
  $methods = [System.WindowsRuntimeSystemExtensions].GetMethods()
  foreach ($method in $methods) {
    $parameters = $method.GetParameters()
    if (
      $method.Name -eq "AsTask" -and
      $method.IsGenericMethodDefinition -and
      $method.GetGenericArguments().Length -eq 1 -and
      $parameters.Length -eq 1 -and
      $parameters[0].ParameterType.Name -eq 'IAsyncOperation`1'
    ) {
      $script:nightScopeAsTaskOperationMethod = $method
      return $method
    }
  }
  throw "System.WindowsRuntimeSystemExtensions.AsTask<TResult>(IAsyncOperation<TResult>) was not found."
}

function Convert-NightScopeIAsyncOperationToTask($operation, [Type]$resultType) {
  $method = Get-NightScopeAsTaskOperationMethod
  $closedMethod = $method.MakeGenericMethod([Type[]]@($resultType))
  return $closedMethod.Invoke($null, [object[]]@($operation))
}
"""


def _run_windows_location_diagnostics() -> dict:
    try:
        result = subprocess.run(
            ["powershell", "-Sta", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", _windows_diagnostics_script()],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
            **_hidden_subprocess_kwargs(),
        )
    except subprocess.TimeoutExpired as exc:
        report = {
            "ok": False,
            "provider": "windows_precise",
            "providerStatus": "timeout",
            "accessStatus": "n/d",
            "coordinatesReceived": False,
            "coordinates": None,
            "errorDetails": {
                "type": "subprocess.TimeoutExpired",
                "message": f"Windows diagnostics timed out after {exc.timeout} seconds.",
            },
            "process": {"timeoutSeconds": exc.timeout},
            "rawProviderResponse": "",
            "rawProviderError": "",
        }
        logger.error("Windows location diagnostics process timed out.", exc_info=True)
        return report
    except (OSError, subprocess.SubprocessError) as exc:
        report = {
            "ok": False,
            "provider": "windows_precise",
            "providerStatus": "process error",
            "accessStatus": "n/d",
            "coordinatesReceived": False,
            "coordinates": None,
            "errorDetails": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
            "process": {},
            "rawProviderResponse": "",
            "rawProviderError": "",
        }
        logger.error("Windows location diagnostics process failed.", exc_info=True)
        return report

    payload = _parse_provider_stdout(result.stdout) or {
        "ok": False,
        "provider": "windows_precise",
        "providerStatus": "invalid diagnostic response",
        "accessStatus": "n/d",
        "coordinatesReceived": False,
        "coordinates": None,
        "errorDetails": {
            "type": "InvalidProviderResponse",
            "message": "PowerShell diagnostics did not return JSON.",
        },
    }
    payload["process"] = {
        "returnCode": result.returncode,
        "stderrPresent": bool(result.stderr.strip()),
    }
    payload["rawProviderResponse"] = result.stdout.strip()
    payload["rawProviderError"] = result.stderr.strip()
    return payload


def _windows_diagnostics_script() -> str:
    return r"""
$ErrorActionPreference = "Stop"
function ExceptionInfo($errorRecord) {
  $exception = $errorRecord.Exception
  return [ordered]@{
    type = $exception.GetType().FullName
    message = $exception.Message
    hresult = ('0x{0:X8}' -f $exception.HResult)
    fullyQualifiedErrorId = $errorRecord.FullyQualifiedErrorId
    category = $errorRecord.CategoryInfo.ToString()
    scriptStackTrace = $errorRecord.ScriptStackTrace
  }
}
function AddStep($name, $status, $data) {
  $script:diagnostic.steps += [ordered]@{
    name = $name
    status = $status
    data = $data
  }
}
function Emit() {
  $script:diagnostic | ConvertTo-Json -Depth 12 -Compress
  exit 0
}

$script:diagnostic = [ordered]@{
  ok = $false
  provider = "windows_precise"
  providerStatus = "started"
  accessStatus = "not-requested"
  requestAccessResult = $null
  coordinatesReceived = $false
  coordinates = $null
  errorDetails = $null
  rawProviderTimezone = $null
  timestamp = (Get-Date).ToString("o")
  thread = [ordered]@{
    apartment = [System.Threading.Thread]::CurrentThread.GetApartmentState().ToString()
    managedThreadId = [System.Threading.Thread]::CurrentThread.ManagedThreadId
    isThreadPoolThread = [System.Threading.Thread]::CurrentThread.IsThreadPoolThread
  }
  environment = [ordered]@{
    powershellVersion = $PSVersionTable.PSVersion.ToString()
    process64Bit = [Environment]::Is64BitProcess
    os64Bit = [Environment]::Is64BitOperatingSystem
    osVersion = [Environment]::OSVersion.VersionString
  }
  winrt = [ordered]@{
    systemRuntimeWindowsRuntimeLoaded = $false
    geolocatorTypeAvailable = $false
    accessStatusTypeAvailable = $false
    positionAccuracyTypeAvailable = $false
    systemWindowsRuntimeExtensionsAvailable = $false
    asTaskMethodCount = 0
    asTaskSignatures = @()
  }
  steps = @()
}

try {
  try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    __WINDOWS_ASYNC_BRIDGE__
    $script:diagnostic.winrt.systemRuntimeWindowsRuntimeLoaded = $true
    AddStep "Load System.Runtime.WindowsRuntime" "ok" @{}
  } catch {
    $script:diagnostic.providerStatus = "WinRT assembly unavailable"
    $script:diagnostic.errorDetails = ExceptionInfo $_
    AddStep "Load System.Runtime.WindowsRuntime" "error" $script:diagnostic.errorDetails
    Emit
  }

  try {
    $null = [Windows.Devices.Geolocation.Geolocator,Windows.Devices.Geolocation,ContentType=WindowsRuntime]
    $script:diagnostic.winrt.geolocatorTypeAvailable = $true
    AddStep "Resolve Geolocator WinRT type" "ok" @{}
  } catch {
    $script:diagnostic.providerStatus = "Geolocator WinRT type unavailable"
    $script:diagnostic.errorDetails = ExceptionInfo $_
    AddStep "Resolve Geolocator WinRT type" "error" $script:diagnostic.errorDetails
    Emit
  }

  try {
    $null = [Windows.Devices.Geolocation.GeolocationAccessStatus,Windows.Devices.Geolocation,ContentType=WindowsRuntime]
    $script:diagnostic.winrt.accessStatusTypeAvailable = $true
    $null = [Windows.Devices.Geolocation.PositionAccuracy,Windows.Devices.Geolocation,ContentType=WindowsRuntime]
    $script:diagnostic.winrt.positionAccuracyTypeAvailable = $true
    AddStep "Resolve supporting WinRT types" "ok" @{}
  } catch {
    $script:diagnostic.providerStatus = "Supporting WinRT type unavailable"
    $script:diagnostic.errorDetails = ExceptionInfo $_
    AddStep "Resolve supporting WinRT types" "error" $script:diagnostic.errorDetails
    Emit
  }

  try {
    $extensionsType = [System.WindowsRuntimeSystemExtensions]
    $script:diagnostic.winrt.systemWindowsRuntimeExtensionsAvailable = $true
    $asTaskMethods = @($extensionsType.GetMethods() | Where-Object { $_.Name -eq "AsTask" })
    $script:diagnostic.winrt.asTaskMethodCount = $asTaskMethods.Count
    $script:diagnostic.winrt.asTaskSignatures = @($asTaskMethods | ForEach-Object { $_.ToString() })
    AddStep "Inspect System.WindowsRuntimeSystemExtensions.AsTask" "ok" @{
      count = $script:diagnostic.winrt.asTaskMethodCount
      signatures = $script:diagnostic.winrt.asTaskSignatures
    }
  } catch {
    $script:diagnostic.providerStatus = "WindowsRuntimeSystemExtensions unavailable"
    $script:diagnostic.errorDetails = ExceptionInfo $_
    AddStep "Inspect System.WindowsRuntimeSystemExtensions.AsTask" "error" $script:diagnostic.errorDetails
    Emit
  }

  try {
    $accessOperation = [Windows.Devices.Geolocation.Geolocator]::RequestAccessAsync()
    AddStep "RequestAccessAsync invoked" "ok" @{
      operationType = $accessOperation.GetType().FullName
    }
  } catch {
    $script:diagnostic.providerStatus = "RequestAccessAsync throws"
    $script:diagnostic.errorDetails = ExceptionInfo $_
    AddStep "RequestAccessAsync invoked" "error" $script:diagnostic.errorDetails
    Emit
  }

  try {
    $accessTask = Convert-NightScopeIAsyncOperationToTask $accessOperation ([Windows.Devices.Geolocation.GeolocationAccessStatus,Windows.Devices.Geolocation,ContentType=WindowsRuntime])
    AddStep "RequestAccessAsync AsTask conversion" "ok" @{
      taskType = $accessTask.GetType().FullName
      conversion = "AsTask<TResult>(IAsyncOperation<TResult>)"
    }
  } catch {
    $script:diagnostic.providerStatus = "RequestAccessAsync AsTask conversion throws"
    $script:diagnostic.errorDetails = ExceptionInfo $_
    AddStep "RequestAccessAsync AsTask conversion" "error" $script:diagnostic.errorDetails
    Emit
  }

  if (-not $accessTask.Wait(10000)) {
    $script:diagnostic.providerStatus = "RequestAccessAsync timeout"
    $script:diagnostic.errorDetails = @{
      type = "Timeout"
      message = "RequestAccessAsync did not complete within 10 seconds."
    }
    AddStep "RequestAccessAsync wait" "timeout" $script:diagnostic.errorDetails
    Emit
  }

  $status = $accessTask.Result.ToString()
  $script:diagnostic.accessStatus = $status
  $script:diagnostic.requestAccessResult = $status
  AddStep "RequestAccessAsync result" "ok" @{
    accessStatus = $status
  }

  if ($status -ne "Allowed") {
    $script:diagnostic.providerStatus = "access not allowed"
    $script:diagnostic.errorDetails = @{
      type = "GeolocationAccessStatus"
      message = "GeolocationAccessStatus returned $status."
    }
    Emit
  }

  try {
    $locator = [Windows.Devices.Geolocation.Geolocator]::new()
    $locator.DesiredAccuracy = [Windows.Devices.Geolocation.PositionAccuracy]::High
    $script:diagnostic.providerStatus = $locator.LocationStatus.ToString()
    AddStep "Create Geolocator" "ok" @{
      desiredAccuracy = $locator.DesiredAccuracy.ToString()
      locationStatus = $locator.LocationStatus.ToString()
    }
  } catch {
    $script:diagnostic.providerStatus = "Geolocator construction throws"
    $script:diagnostic.errorDetails = ExceptionInfo $_
    AddStep "Create Geolocator" "error" $script:diagnostic.errorDetails
    Emit
  }

  try {
    $positionOperation = $locator.GetGeopositionAsync()
    AddStep "GetGeopositionAsync invoked" "ok" @{
      operationType = $positionOperation.GetType().FullName
      locationStatus = $locator.LocationStatus.ToString()
    }
  } catch {
    $script:diagnostic.providerStatus = "GetGeopositionAsync throws"
    $script:diagnostic.errorDetails = ExceptionInfo $_
    AddStep "GetGeopositionAsync invoked" "error" $script:diagnostic.errorDetails
    Emit
  }

  try {
    $positionTask = Convert-NightScopeIAsyncOperationToTask $positionOperation ([Windows.Devices.Geolocation.Geoposition,Windows.Devices.Geolocation,ContentType=WindowsRuntime])
    AddStep "GetGeopositionAsync AsTask conversion" "ok" @{
      taskType = $positionTask.GetType().FullName
      conversion = "AsTask<TResult>(IAsyncOperation<TResult>)"
    }
  } catch {
    $script:diagnostic.providerStatus = "GetGeopositionAsync AsTask conversion throws"
    $script:diagnostic.errorDetails = ExceptionInfo $_
    AddStep "GetGeopositionAsync AsTask conversion" "error" $script:diagnostic.errorDetails
    Emit
  }

  if (-not $positionTask.Wait(10000)) {
    $script:diagnostic.providerStatus = "GetGeopositionAsync timeout"
    $script:diagnostic.errorDetails = @{
      type = "Timeout"
      message = "GetGeopositionAsync did not complete within 10 seconds."
    }
    AddStep "GetGeopositionAsync wait" "timeout" $script:diagnostic.errorDetails
    Emit
  }

  try {
    $result = $positionTask.Result
    $coordinate = $result.Coordinate
    $point = $coordinate.Point
    $position = $point.Position
    $latitude = $position.Latitude
    $longitude = $position.Longitude
    $script:diagnostic.providerStatus = $locator.LocationStatus.ToString()
    $script:diagnostic.rawProviderTimezone = (Get-TimeZone).Id
    $script:diagnostic.coordinates = [ordered]@{
      latitude = $latitude
      longitude = $longitude
      accuracy = $coordinate.Accuracy
      altitude = $position.Altitude
      timestamp = $coordinate.Timestamp.ToString("o")
      rawProviderTimezone = $script:diagnostic.rawProviderTimezone
    }
    $script:diagnostic.coordinatesReceived = ($null -ne $latitude -and $null -ne $longitude)
    AddStep "Read coordinates" "ok" $script:diagnostic.coordinates
    if (-not $script:diagnostic.coordinatesReceived) {
      $script:diagnostic.providerStatus = "null coordinates"
      $script:diagnostic.errorDetails = @{
        type = "NullCoordinates"
        message = "Provider completed but latitude or longitude is null."
      }
      Emit
    }
    $script:diagnostic.ok = $true
    Emit
  } catch {
    $script:diagnostic.providerStatus = "coordinate extraction throws"
    $script:diagnostic.errorDetails = ExceptionInfo $_
    AddStep "Read coordinates" "error" $script:diagnostic.errorDetails
    Emit
  }
} catch {
  $script:diagnostic.providerStatus = "unhandled diagnostics exception"
  $script:diagnostic.errorDetails = ExceptionInfo $_
  AddStep "Unhandled diagnostics exception" "error" $script:diagnostic.errorDetails
  Emit
}
""".replace("__WINDOWS_ASYNC_BRIDGE__", _windows_async_bridge_script())


def _parse_provider_stdout(stdout: str) -> dict | None:
    clean_output = stdout.strip()
    if not clean_output:
        return None
    candidates = [clean_output, *reversed([line.strip() for line in clean_output.splitlines() if line.strip()])]
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _required_coordinate(payload: dict, key: str, minimum: float, maximum: float, message: str) -> float:
    value = payload.get(key)
    if value is None:
        logger.warning("Location provider returned null coordinates: %s", key)
        raise LocationUnavailableError(message, "null coordinates")
    try:
        coordinate = float(value)
    except (TypeError, ValueError) as exc:
        logger.warning("Location provider returned non-numeric coordinates: %s", key)
        raise LocationUnavailableError(message, "null coordinates") from exc
    if not math.isfinite(coordinate) or not minimum <= coordinate <= maximum:
        logger.warning("Location provider returned out-of-range coordinates: %s=%s", key, coordinate)
        raise LocationUnavailableError(message, "null coordinates")
    return coordinate


def _validate_coordinate(value: float, minimum: float, maximum: float, message: str) -> None:
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise LocationUnavailableError(message, "null coordinates")


def _is_number(value) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _log_windows_failure(reason: str, detail: str) -> None:
    logger.warning("Windows location failed: %s. %s", reason, detail)


def _normalize_reason(reason: str) -> str:
    lower = reason.lower()
    if "denied" in lower or "unauthorized" in lower:
        return "permission denied"
    if "disabled" in lower or "unspecified" in lower:
        return "service disabled"
    if "timeout" in lower or "timed out" in lower:
        return "timeout"
    if "null" in lower:
        return "null coordinates"
    if "wrong thread" in lower or "context" in lower or "rpc_e_wrong_thread" in lower:
        return "called from wrong thread/context"
    if "winrt" in lower:
        return "WinRT error"
    return reason


def _reason_from_error(error_text: str) -> str:
    lower = error_text.lower()
    if "access" in lower or "denied" in lower or "unauthorized" in lower:
        return "permission denied"
    if "disabled" in lower:
        return "service disabled"
    if "timeout" in lower or "timed out" in lower:
        return "timeout"
    if "provider" in lower or "not available" in lower:
        return "unavailable provider"
    if "wrong thread" in lower or "context" in lower or "rpc_e_wrong_thread" in lower:
        return "called from wrong thread/context"
    if "winrt" in lower:
        return "WinRT error"
    return "unavailable provider"


def system_timezone() -> str:
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-TimeZone).Id"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
            **_hidden_subprocess_kwargs(),
        )
        windows_timezone = result.stdout.strip()
        if windows_timezone in WINDOWS_TO_IANA_TIMEZONES:
            return WINDOWS_TO_IANA_TIMEZONES[windows_timezone]
    except (OSError, subprocess.SubprocessError):
        pass

    local_tz = datetime.now().astimezone().tzinfo
    if isinstance(local_tz, ZoneInfo):
        return local_tz.key
    return "UTC"


def _hidden_subprocess_kwargs() -> dict:
    kwargs = {}
    if hasattr(subprocess, "STARTUPINFO") and hasattr(subprocess, "STARTF_USESHOWWINDOW"):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        kwargs["startupinfo"] = startupinfo
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kwargs
