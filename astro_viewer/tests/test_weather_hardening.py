from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.weather_cache_repository import WeatherCacheRepository
from astro_viewer.app.services.weather_service import WEATHER_UNAVAILABLE_MESSAGE, OpenMeteoWeatherService


class WeatherHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.location = ObserverLocation("Roma", "Italia", 41.9028, 12.4964, "Europe/Rome")

    def test_timeout_returns_empty_forecast_without_traceback(self) -> None:
        service = OpenMeteoWeatherService()
        with patch("astro_viewer.app.services.weather_service.requests.get", side_effect=requests.Timeout):
            with self.assertLogs("astro_viewer.app.services.weather_service", level="WARNING"):
                self.assertEqual(service.hourly_forecast(self.location), [])
        self.assertEqual(service.last_error, WEATHER_UNAVAILABLE_MESSAGE)
        self.assertTrue(service.retry_recommended)

    def test_timeout_retries_once_before_falling_back(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "hourly": {
                "time": ["2026-06-21T22:00"],
                "cloud_cover": [12],
                "precipitation_probability": [0],
                "temperature_2m": [18.0],
                "relative_humidity_2m": [55],
                "wind_speed_10m": [6],
                "visibility": [18000],
            }
        }
        service = OpenMeteoWeatherService()

        with patch("astro_viewer.app.services.weather_service.requests.get", side_effect=[requests.Timeout(), response]) as weather_get:
            with self.assertLogs("astro_viewer.app.services.weather_service", level="INFO") as logs:
                forecast = service.hourly_forecast(self.location)

        self.assertEqual(len(forecast), 1)
        self.assertEqual(forecast[0].cloud_cover, 12)
        self.assertEqual(service.last_error, "")
        self.assertFalse(service.retry_recommended)
        self.assertEqual(weather_get.call_count, 2)
        self.assertEqual(weather_get.call_args_list[0].kwargs["timeout"], 3)
        self.assertEqual(weather_get.call_args_list[1].kwargs["timeout"], 8)
        self.assertIn("retrying", "\n".join(logs.output))

    def test_malformed_json_returns_empty_forecast_without_traceback(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("bad json")
        service = OpenMeteoWeatherService()

        with patch("astro_viewer.app.services.weather_service.requests.get", return_value=response):
            with self.assertLogs("astro_viewer.app.services.weather_service", level="WARNING"):
                self.assertEqual(service.hourly_forecast(self.location), [])

        self.assertEqual(service.last_error, WEATHER_UNAVAILABLE_MESSAGE)
        self.assertTrue(service.retry_recommended)

    def test_empty_response_returns_empty_forecast_without_traceback(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"hourly": {"time": []}}
        service = OpenMeteoWeatherService()

        with patch("astro_viewer.app.services.weather_service.requests.get", return_value=response):
            with self.assertLogs("astro_viewer.app.services.weather_service", level="WARNING"):
                self.assertEqual(service.hourly_forecast(self.location), [])

        self.assertEqual(service.last_error, WEATHER_UNAVAILABLE_MESSAGE)
        self.assertTrue(service.retry_recommended)

    def test_server_http_error_logs_status_and_recommends_retry(self) -> None:
        response = Mock()
        response.status_code = 503
        error = requests.HTTPError("service unavailable")
        error.response = response
        response.raise_for_status.side_effect = error
        service = OpenMeteoWeatherService()

        with patch("astro_viewer.app.services.weather_service.requests.get", return_value=response):
            with self.assertLogs("astro_viewer.app.services.weather_service", level="WARNING") as logs:
                forecast = service.hourly_forecast(self.location)

        self.assertEqual(forecast, [])
        self.assertEqual(service.last_http_status, 503)
        self.assertTrue(service.retry_recommended)
        self.assertIn("status=503", "\n".join(logs.output))

    def test_client_http_error_logs_status_without_short_retry(self) -> None:
        response = Mock()
        response.status_code = 400
        error = requests.HTTPError("bad request")
        error.response = response
        response.raise_for_status.side_effect = error
        service = OpenMeteoWeatherService()

        with patch("astro_viewer.app.services.weather_service.requests.get", return_value=response):
            with self.assertLogs("astro_viewer.app.services.weather_service", level="WARNING") as logs:
                forecast = service.hourly_forecast(self.location)

        self.assertEqual(forecast, [])
        self.assertEqual(service.last_http_status, 400)
        self.assertFalse(service.retry_recommended)
        self.assertIn("status=400", "\n".join(logs.output))

    def test_rate_limit_uses_cached_forecast(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)
            repository = WeatherCacheRepository(database_path)
            service = OpenMeteoWeatherService(repository)
            cache_key = service._cache_key(self.location)
            repository.set(
                cache_key,
                (datetime.now(UTC) - timedelta(hours=2)).isoformat(),
                json.dumps(
                    {
                        "hourly": {
                            "time": ["2026-06-21T22:00"],
                            "cloud_cover": [12],
                            "precipitation_probability": [0],
                            "temperature_2m": [18.0],
                            "relative_humidity_2m": [55],
                            "wind_speed_10m": [6],
                            "visibility": [18000],
                        }
                    }
                ),
            )
            response = Mock()
            response.status_code = 429
            error = requests.HTTPError("rate limited")
            error.response = response
            response.raise_for_status.side_effect = error

            with patch("astro_viewer.app.services.weather_service.requests.get", return_value=response):
                with self.assertLogs("astro_viewer.app.services.weather_service", level="WARNING"):
                    forecast = service.hourly_forecast(self.location)

        self.assertEqual(len(forecast), 1)
        self.assertEqual(forecast[0].cloud_cover, 12)
        self.assertEqual(service.last_error, WEATHER_UNAVAILABLE_MESSAGE)
        self.assertEqual(service.last_http_status, 429)
        self.assertFalse(service.retry_recommended)

    def test_force_refresh_bypasses_fresh_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)
            repository = WeatherCacheRepository(database_path)
            service = OpenMeteoWeatherService(repository)
            repository.set(
                service._cache_key(self.location),
                datetime.now(UTC).isoformat(),
                json.dumps(
                    {
                        "hourly": {
                            "time": ["2026-06-21T22:00"],
                            "cloud_cover": [80],
                            "precipitation_probability": [0],
                            "temperature_2m": [18.0],
                            "relative_humidity_2m": [55],
                            "wind_speed_10m": [6],
                            "visibility": [18000],
                        }
                    }
                ),
            )
            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {
                "hourly": {
                    "time": ["2026-06-21T23:00"],
                    "cloud_cover": [10],
                    "precipitation_probability": [0],
                    "temperature_2m": [17.0],
                    "relative_humidity_2m": [50],
                    "wind_speed_10m": [5],
                    "visibility": [20000],
                }
            }

            with patch("astro_viewer.app.services.weather_service.requests.get", return_value=response) as weather_get:
                forecast = service.hourly_forecast(self.location, force_refresh=True)

        weather_get.assert_called_once()
        self.assertEqual(forecast[0].cloud_cover, 10)


if __name__ == "__main__":
    unittest.main()
