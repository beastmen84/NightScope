from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.location_service import (
    LocationDetectionResult,
    LocationUnavailableError,
    WINDOWS_LOCATION_UNAVAILABLE_MESSAGE,
)
from astro_viewer.app.services.location_preferences import LocationPreferenceStore
from astro_viewer.app.viewmodels.app_controller import AppController


class ReleaseScenarioTests(unittest.TestCase):
    def test_addis_ababa_with_available_weather_keeps_app_usable(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            controller.setManualLocation("9.03", "38.74", "Addis Ababa")

            self.assertEqual(controller.location["city"], "Addis Ababa")
            self.assertGreater(len(controller.solarSystemObjects), 0)
            self.assertGreater(len(controller.weatherHourly), 0)

    def test_offline_weather_keeps_app_usable(self) -> None:
        with self.assertLogs("astro_viewer.app.services.weather_service", level="WARNING"):
            with self._controller_with_weather(side_effect=requests.Timeout, saved_location=True) as controller:
                self.assertEqual(controller.weatherStatus, "Weather service temporarily unavailable.")
                self.assertGreater(len(controller.solarSystemObjects), 0)
                self.assertIn("Meteo non disponibile", controller.weatherSummary["alert"])

    def test_app_starts_with_saved_location_and_refreshes_weather(self) -> None:
        with self._controller_with_weather(_valid_weather_response(), saved_location=True) as controller:
            self.assertEqual(controller.location["city"], "Addis Ababa")
            self.assertEqual(controller.location["timezone"], "Africa/Addis_Ababa")
            self.assertGreater(len(controller.weatherHourly), 0)
            self.assertEqual(controller.activeLocationLabel, "Addis Ababa — Africa/Addis_Ababa")

    def test_app_starts_without_location_and_no_consent(self) -> None:
        context = self._controller_with_weather(_valid_weather_response())
        with context as controller:
            self.assertFalse(controller.hasValidLocation)
            self.assertEqual(controller.location["city"], "")
            self.assertEqual(controller.weatherStatus, "Configura una posizione per visualizzare il meteo.")
            self.assertEqual(controller.weatherHourly, [])
            self.assertEqual(controller.activeLocationLabel, "Nessuna posizione configurata")
            context.weather_requests.assert_not_called()

    def test_app_starts_with_approximate_online_consent(self) -> None:
        ip_response = Mock()
        ip_response.raise_for_status.return_value = None
        ip_response.json.return_value = {
            "city": "Addis Ababa",
            "region": "Addis Ababa",
            "country_name": "Ethiopia",
            "latitude": 9.03,
            "longitude": 38.74,
            "timezone": "Africa/Addis_Ababa",
            "accuracy_radius": 25,
        }
        weather_response = _valid_weather_response()

        def response_for_url(url, *args, **kwargs):
            if "ipapi" in url or "ipwho" in url:
                return ip_response
            return weather_response

        with self._controller_with_weather(
            side_effect=response_for_url,
            preferences={
                "auto_detect_location_on_startup": True,
                "allow_approximate_online_location": True,
            },
            patch_location_requests=True,
        ) as controller:
            self.assertEqual(controller.location["city"], "Addis Ababa")
            self.assertEqual(controller.location["timezone"], "Africa/Addis_Ababa")
            self.assertEqual(controller.activeLocationSource, "Approximate online")
            self.assertGreater(len(controller.weatherHourly), 0)

    def test_windows_location_unavailable_keeps_current_location(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            previous_location = controller.location["city"]
            with patch.object(
                controller._location_service,
                "detect_windows_location",
                side_effect=LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE),
            ):
                with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="WARNING"):
                    controller.useWindowsLocation()

            self.assertEqual(controller.location["city"], previous_location)
            self.assertEqual(controller.locationMessage, "Windows location is unavailable. Try approximate online location?")
            self.assertTrue(controller.canUseApproximateOnlineLocation)

    def test_weather_not_called_without_valid_location(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            fake_weather_service = Mock()
            fake_weather_service.hourly_forecast.return_value = []
            fake_weather_service.last_error = ""
            controller._weather_service = fake_weather_service
            controller._location = None

            with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="WARNING"):
                controller._refresh_weather_and_conditions()

            fake_weather_service.hourly_forecast.assert_not_called()

    def test_weather_refreshes_after_valid_location(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            fake_weather_service = Mock()
            fake_weather_service.hourly_forecast.return_value = [
                WeatherHour("2026-06-21T22:00", "22:00", 20, 0, 6, 55, 18.0, 18_000)
            ]
            fake_weather_service.last_error = ""
            controller._weather_service = fake_weather_service

            controller.setManualLocation("41.9028", "12.4964", "Roma")

            fake_weather_service.hourly_forecast.assert_called()

    def test_approximate_online_location_refreshes_weather(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            fake_weather_service = Mock()
            fake_weather_service.hourly_forecast.return_value = [
                WeatherHour("2026-06-21T22:00", "22:00", 20, 0, 6, 55, 18.0, 18_000)
            ]
            fake_weather_service.last_error = ""
            controller._weather_service = fake_weather_service
            result = LocationDetectionResult(
                location=ObserverLocation("Rome", "Italy", 41.9, 12.5, "Europe/Rome"),
                provider="ip_geolocation",
                source="test",
                accuracy="city-level",
                approximate=True,
                message="Approximate location detected from internet connection: Rome, Italy. Accuracy may be limited.",
            )
            with patch.object(controller._location_service, "detect_ip_location", return_value=result):
                controller.useApproximateOnlineLocation()

            self.assertEqual(controller.location["city"], "Rome")
            self.assertIn("Approximate location detected", controller.locationMessage)
            fake_weather_service.hourly_forecast.assert_called()

    def test_weather_page_displays_active_location_context(self) -> None:
        qml = (Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "WeatherPage.qml").read_text(encoding="utf-8")
        self.assertIn("Meteo per: ", qml)
        self.assertIn("controller.activeLocationLabel", qml)
        self.assertIn("controller.activeLocationSource", qml)
        self.assertIn("Configura una posizione per visualizzare il meteo.", qml)

    def test_home_page_displays_active_location_context(self) -> None:
        qml = (Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "HomePage.qml").read_text(encoding="utf-8")
        self.assertIn("controller.activeLocationLabel", qml)
        self.assertIn("controller.activeLocationSource", qml)

    def _controller_with_weather(self, response: Mock | None = None, side_effect=None, **kwargs):
        return _ControllerContext(response=response, side_effect=side_effect, **kwargs)


class _ControllerContext:
    def __init__(
        self,
        response: Mock | None = None,
        side_effect=None,
        saved_location: bool = False,
        preferences: dict | None = None,
        patch_location_requests: bool = False,
    ):
        self._response = response
        self._side_effect = side_effect
        self._saved_location = saved_location
        self._preferences = preferences or {}
        self._patch_location_requests = patch_location_requests
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self._patcher = None
        self._location_patcher = None
        self.weather_requests = None
        self.location_requests = None
        self._controller: AppController | None = None

    def __enter__(self) -> AppController:
        self._temp_dir = tempfile.TemporaryDirectory()
        base_dir = Path(__file__).resolve().parents[1]
        database_path = Path(self._temp_dir.name) / "nightscope.db"
        initialize_database(database_path, base_dir / "data" / "schema.sql")
        self._seed_preferences(database_path)
        self._patcher = patch(
            "astro_viewer.app.services.weather_service.requests.get",
            return_value=self._response,
            side_effect=self._side_effect,
        )
        self.weather_requests = self._patcher.start()
        if self._patch_location_requests:
            self._location_patcher = patch(
                "astro_viewer.app.services.location_service.requests.get",
                return_value=self._response,
                side_effect=self._side_effect,
            )
            self.location_requests = self._location_patcher.start()
        self._controller = AppController(base_dir=base_dir, database_path=database_path)
        return self._controller

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._controller and hasattr(self._controller._astronomy_engine, "close"):
            self._controller._astronomy_engine.close()
        if self._patcher:
            self._patcher.stop()
        if self._location_patcher:
            self._location_patcher.stop()
        if self._temp_dir:
            self._temp_dir.cleanup()

    def _seed_preferences(self, database_path: Path) -> None:
        store = LocationPreferenceStore(
            database_path.parent / "user_preferences.json",
            database_path.parent / "location_cache.json",
        )
        if self._preferences:
            store.update_preferences(
                auto_detect_location_on_startup=self._preferences.get("auto_detect_location_on_startup"),
                allow_approximate_online_location=self._preferences.get("allow_approximate_online_location"),
                use_windows_location_on_startup=self._preferences.get("use_windows_location_on_startup"),
            )
        if self._saved_location:
            store.save_location(
                LocationDetectionResult(
                    location=ObserverLocation("Addis Ababa", "Etiopia", 9.03, 38.74, "Africa/Addis_Ababa"),
                    provider="manual_city",
                    source="SQLite City",
                    accuracy="city coordinates",
                    approximate=False,
                    country_code="ET",
                    message="Posizione impostata su Addis Ababa, Etiopia.",
                )
            )


def _valid_weather_response() -> Mock:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "hourly": {
            "time": [f"2026-06-21T{hour:02d}:00" for hour in range(24)],
            "cloud_cover": [18] * 24,
            "precipitation_probability": [0] * 24,
            "temperature_2m": [17.5] * 24,
            "relative_humidity_2m": [56] * 24,
            "wind_speed_10m": [7] * 24,
            "visibility": [18000] * 24,
        }
    }
    return response


if __name__ == "__main__":
    unittest.main()
