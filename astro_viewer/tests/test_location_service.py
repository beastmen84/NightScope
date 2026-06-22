from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.city_repository import CityRepository
from astro_viewer.app.services.location_service import (
    APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE,
    IpGeolocationProvider,
    LocationDetectionResult,
    LocationService,
    LocationUnavailableError,
    WINDOWS_LOCATION_UNAVAILABLE_MESSAGE,
    _windows_diagnostics_script,
    _windows_geolocation_script,
)
from astro_viewer.tests.geonames_fixture import write_small_geonames_fixture


class LocationServiceWindowsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = LocationService()

    def test_valid_windows_location_payload(self) -> None:
        location = self.service._location_from_windows_payload(
            {
                "latitude": -1.2921,
                "longitude": 36.8219,
                "timezone": "E. Africa Standard Time",
            }
        )

        self.assertEqual(location.city, "Posizione Windows")
        self.assertEqual(location.latitude, -1.2921)
        self.assertEqual(location.longitude, 36.8219)
        self.assertEqual(location.timezone, "Africa/Nairobi")

    def test_windows_permission_allowed(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["powershell"],
            returncode=0,
            stdout='{"ok":true,"access_status":"Allowed","latitude":41.9028,"longitude":12.4964,"timezone":"W. Europe Standard Time","accuracy":20}',
            stderr="",
        )
        with patch("astro_viewer.app.services.location_service.subprocess.run", return_value=completed):
            result = self.service.detect_windows_location()

        self.assertEqual(result.provider, "windows_precise")
        self.assertEqual(result.location.latitude, 41.9028)
        self.assertEqual(result.location.longitude, 12.4964)

    def test_windows_coordinates_near_addis_resolve_to_local_city_timezone(self) -> None:
        with _temp_city_repository() as repository:
            completed = subprocess.CompletedProcess(
                args=["powershell"],
                returncode=0,
                stdout=(
                    '{"ok":true,"access_status":"Allowed",'
                    '"latitude":8.951475146070246,'
                    '"longitude":38.78120889791471,'
                    '"timezone":"E. Africa Standard Time",'
                    '"raw_provider_timezone":"E. Africa Standard Time",'
                    '"accuracy":84}'
                ),
                stderr="",
            )
            service = LocationService(city_resolver=repository)

            with patch("astro_viewer.app.services.location_service.subprocess.run", return_value=completed):
                result = service.detect_windows_location()

        self.assertEqual(result.provider, "windows_precise")
        self.assertEqual(result.location.city, "Addis Ababa")
        self.assertEqual(result.location.country, "Etiopia")
        self.assertEqual(result.country_code, "ET")
        self.assertEqual(result.location.timezone, "Africa/Addis_Ababa")
        self.assertEqual(result.raw_provider_timezone, "E. Africa Standard Time")
        self.assertAlmostEqual(result.location.latitude, 8.951475146070246)
        self.assertAlmostEqual(result.location.longitude, 38.78120889791471)

    def test_manual_city_selection_remains_unchanged_with_city_resolver(self) -> None:
        with _temp_city_repository() as repository:
            city = next(item for item in repository.search("Addis Ababa") if item["country_code"] == "ET")
            result = LocationService(city_resolver=repository).from_city_result(city)

        self.assertEqual(result.provider, "manual_city")
        self.assertEqual(result.location.city, "Addis Ababa")
        self.assertEqual(result.location.country, "Etiopia")
        self.assertEqual(result.country_code, "ET")
        self.assertEqual(result.location.timezone, "Africa/Addis_Ababa")
        self.assertEqual(result.source, "SQLite City")

    def test_approximate_online_location_remains_unchanged_with_city_resolver(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "city": "Rome",
            "region": "Lazio",
            "country_name": "Italy",
            "latitude": 41.9,
            "longitude": 12.5,
            "timezone": "Europe/Rome",
            "accuracy_radius": 25,
        }

        with patch("astro_viewer.app.services.location_service.requests.get", return_value=response):
            result = LocationService(city_resolver=_ExplodingCityResolver()).detect_ip_location(allow_online=True)

        self.assertEqual(result.provider, "ip_geolocation")
        self.assertTrue(result.approximate)
        self.assertEqual(result.location.city, "Rome")
        self.assertEqual(result.location.country, "Italy")
        self.assertEqual(result.location.timezone, "Europe/Rome")

    def test_windows_location_uses_fallback_timezone_when_no_nearby_city_exists(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["powershell"],
            returncode=0,
            stdout=(
                '{"ok":true,"access_status":"Allowed",'
                '"latitude":0.0,'
                '"longitude":-160.0,'
                '"timezone":"W. Europe Standard Time",'
                '"raw_provider_timezone":"W. Europe Standard Time",'
                '"accuracy":25}'
            ),
            stderr="",
        )
        service = LocationService(city_resolver=_NoCityResolver())

        with patch("astro_viewer.app.services.location_service.subprocess.run", return_value=completed):
            result = service.detect_windows_location()

        self.assertEqual(result.location.city, "Posizione Windows")
        self.assertEqual(result.location.timezone, "Europe/Berlin")
        self.assertEqual(result.raw_provider_timezone, "W. Europe Standard Time")

    def test_windows_location_latitude_none(self) -> None:
        with self.assertLogs("astro_viewer.app.services.location_service", level="WARNING"):
            with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE):
                self.service._location_from_windows_payload(
                    {"latitude": None, "longitude": 36.8219, "timezone": "E. Africa Standard Time"}
                )

    def test_windows_location_longitude_none(self) -> None:
        with self.assertLogs("astro_viewer.app.services.location_service", level="WARNING"):
            with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE):
                self.service._location_from_windows_payload(
                    {"latitude": -1.2921, "longitude": None, "timezone": "E. Africa Standard Time"}
                )

    def test_windows_location_both_coordinates_none(self) -> None:
        with self.assertLogs("astro_viewer.app.services.location_service", level="WARNING"):
            with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE):
                self.service._location_from_windows_payload(
                    {"latitude": None, "longitude": None, "timezone": "E. Africa Standard Time"}
                )

    def test_windows_location_permission_denied_or_unavailable_provider(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["powershell"],
            returncode=1,
            stdout="",
            stderr="Access denied",
        )
        with patch("astro_viewer.app.services.location_service.subprocess.run", return_value=completed):
            with self.assertLogs("astro_viewer.app.services.location_service", level="WARNING"):
                with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE):
                    self.service.from_windows_location()

    def test_windows_permission_denied(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["powershell"],
            returncode=0,
            stdout='{"ok":false,"reason":"permission denied","access_status":"Denied"}',
            stderr="",
        )
        with patch("astro_viewer.app.services.location_service.subprocess.run", return_value=completed):
            with self.assertLogs("astro_viewer.app.services.location_service", level="WARNING"):
                with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE) as context:
                    self.service.detect_windows_location()

        self.assertEqual(context.exception.reason, "permission denied")

    def test_windows_returns_null_coordinates(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["powershell"],
            returncode=0,
            stdout='{"ok":true,"access_status":"Allowed","latitude":null,"longitude":12.4964,"timezone":"W. Europe Standard Time"}',
            stderr="",
        )
        with patch("astro_viewer.app.services.location_service.subprocess.run", return_value=completed):
            with self.assertLogs("astro_viewer.app.services.location_service", level="WARNING"):
                with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE) as context:
                    self.service.detect_windows_location()

        self.assertEqual(context.exception.reason, "null coordinates")

    def test_windows_timeout(self) -> None:
        with patch(
            "astro_viewer.app.services.location_service.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="powershell", timeout=18),
        ):
            with self.assertLogs("astro_viewer.app.services.location_service", level="WARNING"):
                with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE) as context:
                    self.service.detect_windows_location()

        self.assertEqual(context.exception.reason, "timeout")

    def test_windows_location_diagnostics_report(self) -> None:
        diagnostic_json = (
            '{"ok":false,'
            '"provider":"windows_precise",'
            '"providerStatus":"RequestAccessAsync AsTask conversion throws",'
            '"accessStatus":"not-requested",'
            '"coordinatesReceived":false,'
            '"coordinates":null,'
            '"errorDetails":{"type":"System.Management.Automation.MethodException","message":"Cannot find an overload for AsTask"},'
            '"thread":{"apartment":"STA","managedThreadId":1},'
            '"winrt":{"geolocatorTypeAvailable":true,"asTaskMethodCount":0},'
            '"steps":[]}'
        )
        completed = subprocess.CompletedProcess(
            args=["powershell"],
            returncode=0,
            stdout=diagnostic_json,
            stderr="",
        )

        with patch("astro_viewer.app.services.location_service.subprocess.run", return_value=completed):
            with self.assertLogs("astro_viewer.app.services.location_service", level="INFO"):
                report = self.service.windows_location_diagnostics()

        self.assertEqual(report["accessStatus"], "not-requested")
        self.assertFalse(report["coordinatesReceived"])
        self.assertEqual(report["thread"]["apartment"], "STA")
        self.assertTrue(report["winrt"]["geolocatorTypeAvailable"])
        self.assertIn("AsTask", report["errorDetails"]["message"])
        self.assertEqual(report["rawProviderResponse"], diagnostic_json)

    def test_windows_scripts_use_typed_winrt_async_bridge(self) -> None:
        location_script = _windows_geolocation_script(precise=True)
        diagnostics_script = _windows_diagnostics_script()

        for script in (location_script, diagnostics_script):
            self.assertIn("Convert-NightScopeIAsyncOperationToTask", script)
            self.assertIn("AsTask<TResult>(IAsyncOperation<TResult>)", script)
            self.assertIn("GeolocationAccessStatus", script)
            self.assertIn("Geoposition", script)
            self.assertNotIn("::AsTask($accessOperation)", script)
            self.assertNotIn("::AsTask($positionOperation)", script)
            self.assertNotIn("::AsTask($operation)", script)

    def test_ip_geolocation_success(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "city": "Rome",
            "region": "Lazio",
            "country_name": "Italy",
            "latitude": 41.9,
            "longitude": 12.5,
            "timezone": "Europe/Rome",
            "accuracy_radius": 25,
        }

        with patch("astro_viewer.app.services.location_service.requests.get", return_value=response):
            result = IpGeolocationProvider().detect()

        self.assertTrue(result.approximate)
        self.assertEqual(result.location.city, "Rome")
        self.assertEqual(result.location.country, "Italy")
        self.assertEqual(result.location.timezone, "Europe/Rome")

    def test_ip_geolocation_failure(self) -> None:
        with patch("astro_viewer.app.services.location_service.requests.get", side_effect=requests.Timeout):
            with self.assertLogs("astro_viewer.app.services.location_service", level="WARNING"):
                with self.assertRaisesRegex(LocationUnavailableError, APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE):
                    IpGeolocationProvider().detect()

    def test_fallback_order(self) -> None:
        calls: list[str] = []
        precise = _FakeProvider("precise", calls, error=LocationUnavailableError("no precise", "timeout"))
        coarse_result = LocationDetectionResult(
            location=ObserverLocation("Coarse", "", 45.0, 9.0, "Europe/Rome"),
            provider="coarse",
            source="test",
            accuracy="coarse",
            approximate=True,
        )
        coarse = _FakeProvider("coarse", calls, result=coarse_result)
        ip = _FakeProvider("ip", calls, result=coarse_result)
        service = LocationService(windows_provider=precise, windows_coarse_provider=coarse, ip_provider=ip)

        result = service.detect_best_location(allow_ip=True)

        self.assertEqual(result.provider, "coarse")
        self.assertEqual(calls, ["precise", "coarse"])


class _FakeProvider:
    def __init__(
        self,
        name: str,
        calls: list[str],
        result: LocationDetectionResult | None = None,
        error: LocationUnavailableError | None = None,
    ):
        self.name = name
        self._calls = calls
        self._result = result
        self._error = error

    def detect(self) -> LocationDetectionResult:
        self._calls.append(self.name)
        if self._error:
            raise self._error
        if not self._result:
            raise LocationUnavailableError("missing fake result", "test")
        return self._result


class _NoCityResolver:
    def nearest_by_coordinates(self, latitude: float, longitude: float, max_radius_km: float = 50.0) -> dict | None:
        return None


class _ExplodingCityResolver:
    def nearest_by_coordinates(self, latitude: float, longitude: float, max_radius_km: float = 50.0) -> dict | None:
        raise AssertionError("Approximate online location must not use local city reverse lookup.")


class _temp_city_repository:
    def __enter__(self) -> CityRepository:
        self._temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self._temp_dir.name)
        write_small_geonames_fixture(temp_path)
        database_path = temp_path / "nightscope.db"
        base_dir = Path(__file__).resolve().parents[1]
        initialize_database(database_path, base_dir / "data" / "schema.sql")
        self.repository = CityRepository(database_path)
        return self.repository

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._temp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
