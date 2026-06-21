from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Protocol

import requests

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.weather_cache_repository import WeatherCacheRepository
from astro_viewer.app.models.weather import WeatherHour, WeatherSummary
from astro_viewer.app.services.observing_score_service import ObservingScoreService


class WeatherService(Protocol):
    def hourly_forecast(self, location: ObserverLocation) -> list[WeatherHour]:
        ...

    def observing_summary(self, location: ObserverLocation) -> WeatherSummary:
        ...


def score_observability(hours: list[WeatherHour]) -> WeatherSummary:
    return ObservingScoreService().weather_score(hours)


class MockWeatherService:
    def hourly_forecast(self, location: ObserverLocation) -> list[WeatherHour]:
        return [
            WeatherHour("mock-20", "20:00", 18, 4, 9, 58, 22.1),
            WeatherHour("mock-21", "21:00", 15, 3, 8, 61, 20.7),
            WeatherHour("mock-22", "22:00", 22, 5, 7, 64, 19.8),
            WeatherHour("mock-23", "23:00", 28, 8, 6, 66, 18.9),
            WeatherHour("mock-00", "00:00", 35, 10, 6, 69, 18.2),
            WeatherHour("mock-01", "01:00", 48, 12, 8, 71, 17.8),
            WeatherHour("mock-02", "02:00", 56, 16, 10, 74, 17.3),
            WeatherHour("mock-03", "03:00", 42, 12, 11, 75, 16.9),
        ]

    def observing_summary(self, location: ObserverLocation) -> WeatherSummary:
        return score_observability(self.hourly_forecast(location))


class OpenMeteoWeatherService:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    CACHE_TTL = timedelta(minutes=45)

    def __init__(self, cache_repository: WeatherCacheRepository | None = None):
        self._cache_repository = cache_repository

    def hourly_forecast(self, location: ObserverLocation) -> list[WeatherHour]:
        cache_key = self._cache_key(location)
        cached = self._read_cache(cache_key)
        if cached and datetime.now(UTC) - cached[0] < self.CACHE_TTL:
            return self._parse_payload(cached[1])

        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "hourly": ",".join(
                [
                    "cloud_cover",
                    "precipitation_probability",
                    "temperature_2m",
                    "relative_humidity_2m",
                    "wind_speed_10m",
                    "visibility",
                ]
            ),
            "forecast_hours": 24,
            "timezone": location.timezone,
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=8)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException:
            if cached:
                return self._parse_payload(cached[1])
            return []

        if self._cache_repository:
            self._cache_repository.set(cache_key, datetime.now(UTC).isoformat(), json.dumps(payload))
        return self._parse_payload(payload)

    def observing_summary(self, location: ObserverLocation) -> WeatherSummary:
        return score_observability(self.hourly_forecast(location))

    def _read_cache(self, cache_key: str) -> tuple[datetime, dict] | None:
        if not self._cache_repository:
            return None
        cached = self._cache_repository.get(cache_key)
        if not cached:
            return None
        try:
            fetched_at = datetime.fromisoformat(cached["fetched_at"])
            if fetched_at.tzinfo is None:
                fetched_at = fetched_at.replace(tzinfo=UTC)
            return fetched_at.astimezone(UTC), json.loads(cached["payload"])
        except (ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def _parse_payload(payload: dict) -> list[WeatherHour]:
        hourly = payload.get("hourly", {})
        hours: list[WeatherHour] = []
        timestamps = hourly.get("time", [])
        for index, timestamp in enumerate(timestamps[:24]):
            time_label = str(timestamp)[-5:]
            hours.append(
                WeatherHour(
                    timestamp=str(timestamp),
                    time=time_label,
                    cloud_cover=_safe_int(_hourly_value(hourly, "cloud_cover", index, 0)),
                    precipitation_probability=_safe_int(_hourly_value(hourly, "precipitation_probability", index, 0)),
                    wind_kmh=round(_safe_float(_hourly_value(hourly, "wind_speed_10m", index, 0))),
                    humidity=_safe_int(_hourly_value(hourly, "relative_humidity_2m", index, 0)),
                    temperature_c=round(_safe_float(_hourly_value(hourly, "temperature_2m", index, 0.0)), 1),
                    visibility_m=_safe_int(_hourly_value(hourly, "visibility", index, 0)),
                )
            )
        return hours

    @staticmethod
    def _cache_key(location: ObserverLocation) -> str:
        return f"{location.latitude:.4f}:{location.longitude:.4f}:{location.timezone}:24h"


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _hourly_value(hourly: dict, key: str, index: int, default):
    values = hourly.get(key) or []
    if index >= len(values):
        return default
    return values[index]
