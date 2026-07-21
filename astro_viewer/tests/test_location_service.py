from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
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
    _hidden_subprocess_kwargs,
    _windows_diagnostics_script,
    _windows_geolocation_script,
)
from astro_viewer.app.services.location_preferences import LocationPreferenceStore
from astro_viewer.tests.geonames_fixture import write_small_geonames_fixture


class LocationServiceWindowsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = LocationService()

    def test_valid_windows_location_payload(self) -> None:
        with patch(
            "astro_viewer.app.services.location_service.system_timezone",
            side_effect=AssertionError("Known Windows timezones must not start the fallback."),
        ):
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

    def test_windows_location_subprocess_is_hidden_when_supported(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["powershell"],
            returncode=0,
            stdout='{"ok":true,"access_status":"Allowed","latitude":41.9028,"longitude":12.4964,"timezone":"W. Europe Standard Time","accuracy":20}',
            stderr="",
        )

        with patch("astro_viewer.app.services.location_service.subprocess.run", return_value=completed) as run:
            self.service.detect_windows_location()

        kwargs = run.call_args.kwargs
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            self.assertEqual(kwargs["creationflags"], subprocess.CREATE_NO_WINDOW)
        if hasattr(subprocess, "STARTUPINFO"):
            self.assertEqual(kwargs["startupinfo"].wShowWindow, 0)

    def test_hidden_subprocess_kwargs_are_platform_safe(self) -> None:
        kwargs = _hidden_subprocess_kwargs()

        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            self.assertEqual(kwargs["creationflags"], subprocess.CREATE_NO_WINDOW)
        else:
            self.assertNotIn("creationflags", kwargs)

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
            service = LocationService(
                city_resolver=repository,
                timezone_resolver=_StaticTimezoneResolver("Africa/Addis_Ababa"),
            )

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

    def test_manual_city_selection_uses_coordinate_timezone(self) -> None:
        with _temp_city_repository() as repository:
            city = next(item for item in repository.search("Addis Ababa") if item["country_code"] == "ET")
            city["timezone"] = "Europe/Rome"
            with patch(
                "astro_viewer.app.services.location_service.system_timezone",
                side_effect=AssertionError("Successful coordinate lookup must not start the fallback."),
            ):
                result = LocationService(
                    city_resolver=repository,
                    timezone_resolver=_StaticTimezoneResolver("Africa/Addis_Ababa"),
                ).from_city_result(city)

        self.assertEqual(result.provider, "manual_city")
        self.assertEqual(result.location.city, "Addis Ababa")
        self.assertEqual(result.location.country, "Etiopia")
        self.assertEqual(result.country_code, "ET")
        self.assertEqual(result.location.timezone, "Africa/Addis_Ababa")
        self.assertEqual(result.source, "SQLite City; coordinate timezone")

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
            result = LocationService(
                city_resolver=_ExplodingCityResolver(),
                timezone_resolver=_ExplodingTimezoneResolver(),
            ).detect_ip_location(allow_online=True)

        self.assertEqual(result.provider, "ip_geolocation")
        self.assertTrue(result.approximate)
        self.assertEqual(result.location.city, "Rome")
        self.assertEqual(result.location.country, "Italy")
        self.assertEqual(result.location.timezone, "Europe/Rome")

    def test_manual_city_does_not_use_geonames_timezone_as_fallback(self) -> None:
        city = {
            "city": "Addis Ababa",
            "country": "Etiopia",
            "country_code": "ET",
            "latitude": 8.9515,
            "longitude": 38.7811,
            "timezone": "Africa/Addis_Ababa",
        }
        service = LocationService(timezone_resolver=_StaticTimezoneResolver(None))

        with patch(
            "astro_viewer.app.services.location_service.system_timezone",
            return_value="UTC",
        ):
            result = service.from_city_result(city)

        self.assertEqual(result.location.timezone, "UTC")

    def test_windows_location_uses_coordinate_timezone_when_no_nearby_city_exists(self) -> None:
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
        city_resolver = _RecordingNoCityResolver()
        service = LocationService(
            city_resolver=city_resolver,
            timezone_resolver=_StaticTimezoneResolver("Etc/GMT+11"),
        )

        with patch("astro_viewer.app.services.location_service.subprocess.run", return_value=completed):
            result = service.detect_windows_location()

        self.assertEqual(result.location.city, "Posizione Windows")
        self.assertEqual(result.location.timezone, "Etc/GMT+11")
        self.assertEqual(result.raw_provider_timezone, "W. Europe Standard Time")
        self.assertEqual(city_resolver.radii, [50.0])

    def test_windows_location_uses_provider_timezone_only_when_coordinate_lookup_fails(self) -> None:
        result = LocationDetectionResult(
            location=ObserverLocation("Posizione Windows", "", 0.0, -160.0, "Europe/Berlin"),
            provider="windows_precise",
            source="test",
            accuracy="25 m",
            raw_provider_timezone="W. Europe Standard Time",
        )
        service = LocationService(
            city_resolver=_NoCityResolver(),
            timezone_resolver=_StaticTimezoneResolver(None),
        )

        with patch(
            "astro_viewer.app.services.location_service.system_timezone",
            side_effect=AssertionError("A valid Windows mapping must not start the fallback."),
        ):
            normalized = service._normalize_windows_result(result)

        self.assertEqual(normalized.location.timezone, "Europe/Berlin")

    def test_windows_city_metadata_does_not_choose_timezone(self) -> None:
        with _temp_city_repository() as repository:
            result = LocationDetectionResult(
                location=ObserverLocation("Posizione Windows", "", 8.9515, 38.7811, "Europe/Berlin"),
                provider="windows_precise",
                source="test",
                accuracy="25 m",
                raw_provider_timezone="W. Europe Standard Time",
            )
            service = LocationService(
                city_resolver=repository,
                timezone_resolver=_StaticTimezoneResolver(None),
            )

            normalized = service._normalize_windows_result(result)

        self.assertEqual(normalized.location.city, "Addis Ababa")
        self.assertEqual(normalized.location.country, "Etiopia")
        self.assertEqual(normalized.location.timezone, "Europe/Berlin")

    def test_windows_coarse_location_uses_coordinate_timezone_without_city_guess(self) -> None:
        result = LocationDetectionResult(
            location=ObserverLocation("Posizione Windows approssimata", "", 8.95, 38.78, "Africa/Nairobi"),
            provider="windows_coarse",
            source="test",
            accuracy="50 km",
            approximate=True,
            raw_provider_timezone="E. Africa Standard Time",
        )
        service = LocationService(
            city_resolver=_ExplodingCityResolver(),
            timezone_resolver=_StaticTimezoneResolver("Africa/Addis_Ababa"),
        )

        normalized = service._normalize_windows_result(result)

        self.assertEqual(normalized.location.city, "Posizione Windows approssimata")
        self.assertEqual(normalized.location.country, "")
        self.assertEqual(normalized.location.timezone, "Africa/Addis_Ababa")

    def test_manual_coordinates_use_coordinate_timezone_and_preserve_label(self) -> None:
        service = LocationService(
            city_resolver=_ExplodingCityResolver(),
            timezone_resolver=_StaticTimezoneResolver("Africa/Addis_Ababa"),
        )

        with patch(
            "astro_viewer.app.services.location_service.system_timezone",
            side_effect=AssertionError("Successful coordinate lookup must not start the fallback."),
        ):
            result = service.from_manual_coordinates_result(
                8.9515,
                38.7811,
                label="Osservatorio",
            )

        self.assertEqual(result.location.city, "Osservatorio")
        self.assertEqual(result.location.country, "")
        self.assertAlmostEqual(result.location.latitude, 8.9515)
        self.assertAlmostEqual(result.location.longitude, 38.7811)
        self.assertEqual(result.location.timezone, "Africa/Addis_Ababa")

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

    def test_out_of_range_coordinate_log_does_not_expose_value(self) -> None:
        with self.assertLogs(
            "astro_viewer.app.services.location_service", level="WARNING"
        ) as logs:
            with self.assertRaisesRegex(
                LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE
            ):
                self.service._location_from_windows_payload(
                    {
                        "latitude": 91.234567,
                        "longitude": 12.4964,
                        "timezone": "E. Africa Standard Time",
                    }
                )

        log_text = "\n".join(logs.output)
        self.assertIn("out-of-range latitude", log_text)
        self.assertNotIn("91.234567", log_text)

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
            with self.assertLogs("astro_viewer.app.services.location_service", level="INFO") as logs:
                report = self.service.windows_location_diagnostics()

        self.assertEqual(report["accessStatus"], "not-requested")
        self.assertFalse(report["coordinatesReceived"])
        self.assertEqual(report["thread"]["apartment"], "STA")
        self.assertTrue(report["winrt"]["geolocatorTypeAvailable"])
        self.assertIn("AsTask", report["errorDetails"]["message"])
        self.assertEqual(report["rawProviderResponse"], diagnostic_json)
        log_text = "\n".join(logs.output)
        self.assertNotIn(diagnostic_json, log_text)
        self.assertNotIn("Cannot find an overload for AsTask", log_text)

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

    def test_ip_geolocation_missing_timezone_uses_coordinate_lookup(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "city": "Addis Ababa",
            "country_name": "Ethiopia",
            "latitude": 8.9515,
            "longitude": 38.7811,
        }
        service = LocationService(
            timezone_resolver=_StaticTimezoneResolver("Africa/Addis_Ababa")
        )

        with patch("astro_viewer.app.services.location_service.requests.get", return_value=response):
            result = service.detect_ip_location(allow_online=True)

        self.assertEqual(result.location.timezone, "Africa/Addis_Ababa")
        self.assertEqual(result.raw_provider_timezone, "")

    def test_ip_geolocation_failure(self) -> None:
        with patch("astro_viewer.app.services.location_service.requests.get", side_effect=requests.Timeout):
            with self.assertLogs("astro_viewer.app.services.location_service", level="WARNING"):
                with self.assertRaisesRegex(LocationUnavailableError, APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE):
                    IpGeolocationProvider().detect()

    def test_recent_ip_cache_is_explicitly_reused_after_network_failure(self) -> None:
        now = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "location_cache.json"
            provider = IpGeolocationProvider(cache_path, clock=lambda: now)
            provider._write_cache(
                LocationDetectionResult(
                    location=ObserverLocation(
                        "Rome",
                        "Italy",
                        41.9,
                        12.5,
                        "Europe/Rome",
                    ),
                    provider="ip_geolocation",
                    source="https://ipapi.co/json/",
                    accuracy="25 km",
                    approximate=True,
                )
            )

            with patch(
                "astro_viewer.app.services.location_service.requests.get",
                side_effect=requests.Timeout,
            ):
                with self.assertLogs(
                    "astro_viewer.app.services.location_service",
                    level="WARNING",
                ):
                    result = provider.detect()

        self.assertTrue(result.source.endswith(" cached"))
        self.assertEqual(result.message, "Posizione caricata.")
        self.assertEqual(result.location.city, "Rome")

    def test_expired_ip_cache_is_not_presented_as_current_location(self) -> None:
        now = datetime(2026, 7, 21, 12, 0, tzinfo=UTC)
        clock = {"now": now}
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "location_cache.json"
            provider = IpGeolocationProvider(
                cache_path,
                clock=lambda: clock["now"],
            )
            provider._write_cache(
                LocationDetectionResult(
                    location=ObserverLocation(
                        "Old city",
                        "Old country",
                        1.0,
                        2.0,
                        "UTC",
                    ),
                    provider="ip_geolocation",
                    source="https://ipapi.co/json/",
                    accuracy="city",
                    approximate=True,
                )
            )
            clock["now"] = now + timedelta(hours=24, seconds=1)

            with patch(
                "astro_viewer.app.services.location_service.requests.get",
                side_effect=requests.Timeout,
            ):
                with self.assertLogs(
                    "astro_viewer.app.services.location_service",
                    level="WARNING",
                ):
                    with self.assertRaises(LocationUnavailableError):
                        provider.detect()

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


class LocationPreferenceStoreTests(unittest.TestCase):
    def test_startup_sources_are_cleared_when_auto_detect_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = _preference_store(Path(temp_dir))
            store.update_preferences(
                auto_detect_location_on_startup=True,
                use_windows_location_on_startup=True,
                allow_approximate_online_location=True,
            )

            preferences = store.update_preferences(auto_detect_location_on_startup=False)

        self.assertFalse(preferences.auto_detect_location_on_startup)
        self.assertFalse(preferences.use_windows_location_on_startup)
        self.assertFalse(preferences.allow_approximate_online_location)

    def test_auto_detect_defaults_to_windows_when_no_source_is_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preferences = _preference_store(Path(temp_dir)).update_preferences(
                auto_detect_location_on_startup=True
            )

        self.assertTrue(preferences.auto_detect_location_on_startup)
        self.assertTrue(preferences.use_windows_location_on_startup)
        self.assertFalse(preferences.allow_approximate_online_location)

    def test_startup_preferences_cannot_persist_auto_detect_without_a_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = _preference_store(Path(temp_dir))
            store.update_preferences(
                auto_detect_location_on_startup=True,
                use_windows_location_on_startup=False,
                allow_approximate_online_location=True,
            )

            preferences = store.update_preferences(allow_approximate_online_location=False)

        self.assertTrue(preferences.auto_detect_location_on_startup)
        self.assertTrue(preferences.use_windows_location_on_startup)
        self.assertFalse(preferences.allow_approximate_online_location)

    def test_invalid_startup_preferences_are_normalized_on_read(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            preferences_path = temp_path / "preferences.json"
            preferences_path.write_text(
                json.dumps(
                    {
                        "auto_detect_location_on_startup": True,
                        "use_windows_location_on_startup": False,
                        "allow_approximate_online_location": False,
                    }
                ),
                encoding="utf-8",
            )

            preferences = _preference_store(temp_path).preferences()

        self.assertTrue(preferences.auto_detect_location_on_startup)
        self.assertTrue(preferences.use_windows_location_on_startup)
        self.assertFalse(preferences.allow_approximate_online_location)


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


def _preference_store(path: Path) -> LocationPreferenceStore:
    return LocationPreferenceStore(path / "preferences.json", path / "cache.json")


class _NoCityResolver:
    def nearest_by_coordinates(self, latitude: float, longitude: float, max_radius_km: float = 50.0) -> dict | None:
        return None


class _RecordingNoCityResolver(_NoCityResolver):
    def __init__(self) -> None:
        self.radii: list[float] = []

    def nearest_by_coordinates(self, latitude: float, longitude: float, max_radius_km: float = 50.0) -> dict | None:
        self.radii.append(max_radius_km)
        return None


class _ExplodingCityResolver:
    def nearest_by_coordinates(self, latitude: float, longitude: float, max_radius_km: float = 50.0) -> dict | None:
        raise AssertionError("Approximate online location must not use local city reverse lookup.")


class _StaticTimezoneResolver:
    def __init__(self, timezone_name: str | None):
        self.timezone_name = timezone_name
        self.calls: list[tuple[float, float]] = []

    def timezone_at(self, latitude: float, longitude: float) -> str | None:
        self.calls.append((latitude, longitude))
        return self.timezone_name


class _ExplodingTimezoneResolver:
    def timezone_at(self, latitude: float, longitude: float) -> str | None:
        raise AssertionError("A valid provider timezone must not be replaced.")


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
