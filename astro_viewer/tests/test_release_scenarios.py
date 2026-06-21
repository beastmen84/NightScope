from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.services.location_service import LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE
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
            with self._controller_with_weather(side_effect=requests.Timeout) as controller:
                self.assertEqual(controller.weatherStatus, "Weather service temporarily unavailable.")
                self.assertGreater(len(controller.solarSystemObjects), 0)
                self.assertIn("Meteo non disponibile", controller.weatherSummary["alert"])

    def test_windows_location_unavailable_keeps_current_location(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            previous_location = controller.location["city"]
            with patch.object(
                controller._location_service,
                "from_windows_location",
                side_effect=LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE),
            ):
                controller.useWindowsLocation()

            self.assertEqual(controller.location["city"], previous_location)
            self.assertEqual(controller.locationMessage, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE)

    def _controller_with_weather(self, response: Mock | None = None, side_effect=None):
        return _ControllerContext(response=response, side_effect=side_effect)


class _ControllerContext:
    def __init__(self, response: Mock | None = None, side_effect=None):
        self._response = response
        self._side_effect = side_effect
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self._patcher = None
        self._controller: AppController | None = None

    def __enter__(self) -> AppController:
        self._temp_dir = tempfile.TemporaryDirectory()
        base_dir = Path(__file__).resolve().parents[1]
        database_path = Path(self._temp_dir.name) / "nightscope.db"
        initialize_database(database_path, base_dir / "data" / "schema.sql")
        self._patcher = patch(
            "astro_viewer.app.services.weather_service.requests.get",
            return_value=self._response,
            side_effect=self._side_effect,
        )
        self._patcher.start()
        self._controller = AppController(base_dir=base_dir, database_path=database_path)
        return self._controller

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._controller and hasattr(self._controller._astronomy_engine, "close"):
            self._controller._astronomy_engine.close()
        if self._patcher:
            self._patcher.stop()
        if self._temp_dir:
            self._temp_dir.cleanup()


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
