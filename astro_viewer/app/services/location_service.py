from __future__ import annotations

import json
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
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise RuntimeError(result.stderr.strip() or "Posizione Windows non disponibile.")

        payload = json.loads(result.stdout)
        windows_timezone = payload.get("timezone", "")
        return ObserverLocation(
            city="Posizione Windows",
            country="",
            latitude=float(payload["latitude"]),
            longitude=float(payload["longitude"]),
            timezone=WINDOWS_TO_IANA_TIMEZONES.get(windows_timezone, self.system_timezone()),
        )

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
