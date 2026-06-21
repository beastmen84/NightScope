from __future__ import annotations

import json
import math
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

from astro_viewer.app.astronomy.engine import ObserverLocation


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
    "Windows location is not available. Please choose a city or enter coordinates manually."
)


class LocationUnavailableError(RuntimeError):
    """Raised when Windows cannot provide a usable location."""



class LocationService:
    def from_city(self, city: dict) -> ObserverLocation:
        return ObserverLocation(
            city=city["city"],
            country=city["country"],
            latitude=float(city["latitude"]),
            longitude=float(city["longitude"]),
            timezone=city["timezone"],
        )

    def from_manual_coordinates(
        self,
        latitude: float,
        longitude: float,
        label: str = "Coordinate manuali",
        timezone: str | None = None,
    ) -> ObserverLocation:
        return ObserverLocation(
            city=label,
            country="",
            latitude=latitude,
            longitude=longitude,
            timezone=timezone or self.system_timezone(),
        )

    def from_windows_location(self) -> ObserverLocation:
        script = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Devices.Geolocation.Geolocator,Windows.Devices.Geolocation,ContentType=WindowsRuntime]
$locator = [Windows.Devices.Geolocation.Geolocator]::new()
$locator.DesiredAccuracy = [Windows.Devices.Geolocation.PositionAccuracy]::High
$operation = $locator.GetGeopositionAsync()
$task = [System.WindowsRuntimeSystemExtensions]::AsTask($operation)
if (-not $task.Wait(10000)) { throw "Timeout posizione Windows" }
$position = $task.Result.Coordinate.Point.Position
[pscustomobject]@{
  latitude = $position.Latitude
  longitude = $position.Longitude
  timezone = (Get-TimeZone).Id
} | ConvertTo-Json -Compress
"""
        payload = self._windows_location_payload(script)
        return self._location_from_windows_payload(payload)

    def _windows_location_payload(self, script: str) -> dict:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired) as exc:
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE) from exc

        if result.returncode != 0 or not result.stdout.strip():
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE)

        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE) from exc
        if not isinstance(payload, dict):
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE)
        return payload

    def _location_from_windows_payload(self, payload: dict) -> ObserverLocation:
        latitude = self._required_coordinate(payload, "latitude", -90.0, 90.0)
        longitude = self._required_coordinate(payload, "longitude", -180.0, 180.0)
        windows_timezone = payload.get("timezone", "")
        return ObserverLocation(
            city="Posizione Windows",
            country="",
            latitude=latitude,
            longitude=longitude,
            timezone=WINDOWS_TO_IANA_TIMEZONES.get(windows_timezone, self.system_timezone()),
        )

    @staticmethod
    def _required_coordinate(payload: dict, key: str, minimum: float, maximum: float) -> float:
        value = payload.get(key)
        if value is None:
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE)
        try:
            coordinate = float(value)
        except (TypeError, ValueError) as exc:
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE) from exc
        if not math.isfinite(coordinate) or not minimum <= coordinate <= maximum:
            raise LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE)
        return coordinate

    def system_timezone(self) -> str:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-TimeZone).Id"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
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
