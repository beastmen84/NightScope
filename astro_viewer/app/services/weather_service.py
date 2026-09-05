"""Fetch, cache, and normalize Open-Meteo forecasts behind a service port."""

from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime, timedelta
from threading import local
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.weather_cache_repository import WeatherCacheRepository
from astro_viewer.app.models.weather import WeatherHour, WeatherSummary
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.services.localization import tr


logger = logging.getLogger(__name__)
WEATHER_UNAVAILABLE_MESSAGE = tr("Servizio meteo temporaneamente non disponibile.")


class WeatherService(Protocol):
    retry_recommended: bool

    def hourly_forecast(self, location: ObserverLocation, force_refresh: bool = False) -> list[WeatherHour]:
        ...

    def observing_summary(self, location: ObserverLocation) -> WeatherSummary:
        ...


def score_observability(hours: list[WeatherHour]) -> WeatherSummary:
    return ObservingScoreService().weather_score(hours)


class MockWeatherService:
    retry_recommended = False

    def hourly_forecast(self, location: ObserverLocation, force_refresh: bool = False) -> list[WeatherHour]:
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
    REQUEST_TIMEOUT_SECONDS = (3, 8)
    FORECAST_HOURS = 48

    def __init__(self, cache_repository: WeatherCacheRepository | None = None):
        self._cache_repository = cache_repository
        self._request_status = local()
        self.last_error = ""
        self.last_http_status: int | None = None
        self.retry_recommended = False

    @property
    def last_error(self) -> str:
        return getattr(self._request_status, "last_error", "")

    @last_error.setter
    def last_error(self, value: str) -> None:
        self._request_status.last_error = value

    @property
    def last_http_status(self) -> int | None:
        return getattr(self._request_status, "last_http_status", None)

    @last_http_status.setter
    def last_http_status(self, value: int | None) -> None:
        self._request_status.last_http_status = value

    @property
    def retry_recommended(self) -> bool:
        return bool(getattr(self._request_status, "retry_recommended", False))

    @retry_recommended.setter
    def retry_recommended(self, value: bool) -> None:
        self._request_status.retry_recommended = bool(value)

    def hourly_forecast(self, location: ObserverLocation, force_refresh: bool = False) -> list[WeatherHour]:
        self.last_error = ""
        self.last_http_status = None
        self.retry_recommended = False
        cache_key = self._cache_key(location)
        cached = self._read_cache(cache_key) or self._read_cache(self._legacy_cache_key(location))
        cache_age = datetime.now(UTC) - cached[0] if cached else None
        if cache_age is not None and cache_age < timedelta(0):
            cached = None
        if not force_refresh and cached and cache_age < self.CACHE_TTL:
            cached_hours = self._parse_payload(cached[1])
            if cached_hours:
                return cached_hours

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
                    "wind_gusts_10m",
                    "visibility",
                    "dew_point_2m",
                    "cloud_cover_low",
                    "cloud_cover_mid",
                    "cloud_cover_high",
                ]
            ),
            "forecast_hours": self.FORECAST_HOURS,
            "timezone": location.timezone,
            "timeformat": "unixtime",
        }
        try:
            response = self._get_with_timeout_retry(params)
            response.raise_for_status()
            payload = response.json()
        except requests.Timeout:
            return self._fallback(cached, tr("Richiesta meteo scaduta."), retry_recommended=True)
        except requests.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            self.last_http_status = status_code if isinstance(status_code, int) else None
            if self.last_http_status == 429:
                return self._fallback(
                    cached,
                    tr("Open-Meteo HTTP status=429: limite richieste raggiunto."),
                )
            retry_recommended = _http_error_is_retryable(self.last_http_status)
            status_label = self.last_http_status if self.last_http_status is not None else "unknown"
            return self._fallback(
                cached,
                f"Open-Meteo HTTP status={status_label}.",
                retry_recommended=retry_recommended,
            )
        except requests.RequestException:
            return self._fallback(
                cached,
                tr("API meteo non raggiungibile."),
                retry_recommended=True,
            )
        except (TypeError, ValueError):
            return self._fallback(
                cached,
                tr("L'API meteo ha restituito JSON non valido."),
                retry_recommended=True,
            )

        if not isinstance(payload, dict):
            return self._fallback(
                cached,
                tr("L'API meteo ha restituito dati inattesi."),
                retry_recommended=True,
            )

        hours = self._parse_payload(payload)
        if not hours:
            return self._fallback(
                cached,
                tr("L'API meteo ha restituito una previsione vuota."),
                retry_recommended=True,
            )

        if self._cache_repository:
            self._cache_repository.set(cache_key, datetime.now(UTC).isoformat(), json.dumps(payload))
        return hours

    def observing_summary(self, location: ObserverLocation) -> WeatherSummary:
        return score_observability(self.hourly_forecast(location))

    def _get_with_timeout_retry(self, params: dict) -> requests.Response:
        last_timeout: requests.Timeout | None = None
        for index, timeout_seconds in enumerate(self.REQUEST_TIMEOUT_SECONDS):
            try:
                return requests.get(self.BASE_URL, params=params, timeout=timeout_seconds)
            except requests.Timeout as exc:
                last_timeout = exc
                if index + 1 >= len(self.REQUEST_TIMEOUT_SECONDS):
                    break
                next_timeout = self.REQUEST_TIMEOUT_SECONDS[index + 1]
                logger.info(
                    "Open-Meteo request timed out after %ss; retrying with %ss.",
                    timeout_seconds,
                    next_timeout,
                )
        if last_timeout is not None:
            raise last_timeout
        raise requests.Timeout("Open-Meteo request timed out.")

    def _fallback(
        self,
        cached: tuple[datetime, dict] | None,
        reason: str,
        *,
        retry_recommended: bool = False,
    ) -> list[WeatherHour]:
        self.last_error = WEATHER_UNAVAILABLE_MESSAGE
        self.retry_recommended = retry_recommended
        logger.warning(reason)
        if not cached:
            return []
        try:
            hours = self._parse_payload(cached[1])
        except (TypeError, ValueError):
            logger.warning("Weather cache payload could not be parsed.", exc_info=True)
            return []
        if hours:
            logger.info("Using cached weather forecast.")
        return hours

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
        except (TypeError, ValueError, KeyError):
            logger.warning("Weather cache is invalid and will be ignored.", exc_info=True)
            return None

    @classmethod
    def _parse_payload(cls, payload: dict) -> list[WeatherHour]:
        """Keep only hours with finite, physically bounded core measurements.

        Zero is a measurement, never a missing-value sentinel. Optional seeing
        inputs remain unknown and disable that estimate, not the weather row.
        New requests use Unix seconds (UTC); local ISO caches remain readable
        except ambiguous/nonexistent DST clocks, which cannot identify an instant.
        Units are provider defaults: Celsius, km/h, metres and percentages.
        """
        if not isinstance(payload, dict) or not isinstance(payload.get("hourly"), dict):
            return []
        hourly = payload["hourly"]
        hours: list[WeatherHour] = []
        timestamps = hourly.get("time", [])
        if not isinstance(timestamps, list):
            return []
        seen: set[str] = set()
        for index, timestamp in enumerate(timestamps[: cls.FORECAST_HOURS]):
            parsed = _forecast_datetime(timestamp, payload.get("timezone"))
            if parsed is None:
                continue
            instant = parsed.astimezone(UTC).isoformat() if parsed.tzinfo else parsed.isoformat()
            if instant in seen:
                continue
            core = [
                _measurement(hourly, key, index, lower, upper)
                for key, lower, upper in (
                    ("cloud_cover", 0, 100),
                    ("precipitation_probability", 0, 100),
                    ("wind_speed_10m", 0, 500),
                    ("relative_humidity_2m", 0, 100),
                    ("temperature_2m", -100, 70),
                )
            ]
            if any(value is None for value in core):
                continue
            seen.add(instant)
            optional = {
                key: _measurement(hourly, key, index, lower, upper)
                for key, lower, upper in (
                    ("visibility", 0, 1_000_000),
                    ("cloud_cover_low", 0, 100),
                    ("cloud_cover_mid", 0, 100),
                    ("cloud_cover_high", 0, 100),
                    ("wind_gusts_10m", 0, 500),
                    ("dew_point_2m", -100, 70),
                )
            }
            cloud, rain, wind, humidity, temperature = core
            hours.append(
                WeatherHour(
                    timestamp=parsed.isoformat(timespec="minutes"),
                    time=parsed.strftime("%H:%M"),
                    cloud_cover=round(cloud),
                    precipitation_probability=round(rain),
                    wind_kmh=round(wind),
                    humidity=round(humidity),
                    temperature_c=round(temperature, 1),
                    visibility_m=_rounded(optional["visibility"]),
                    cloud_cover_low=_rounded(optional["cloud_cover_low"]),
                    cloud_cover_mid=_rounded(optional["cloud_cover_mid"]),
                    cloud_cover_high=_rounded(optional["cloud_cover_high"]),
                    wind_gusts_kmh=_rounded(optional["wind_gusts_10m"]),
                    dew_point_c=optional["dew_point_2m"],
                    seeing_inputs_complete=all(value is not None for value in optional.values()),
                )
            )
        return hours

    @staticmethod
    def _cache_key(location: ObserverLocation) -> str:
        return f"{location.latitude:.4f}:{location.longitude:.4f}:{location.timezone}:48h"

    @staticmethod
    def _legacy_cache_key(location: ObserverLocation) -> str:
        return f"{location.latitude:.4f}:{location.longitude:.4f}:{location.timezone}:24h"


def _measurement(hourly: dict, key: str, index: int, lower: float, upper: float) -> float | None:
    values = hourly.get(key)
    if not isinstance(values, list) or index >= len(values) or isinstance(values[index], bool):
        return None
    try:
        value = float(values[index])
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and lower <= value <= upper else None


def _rounded(value: float | None) -> int | None:
    return round(value) if value is not None else None


def _forecast_datetime(value: object, timezone_name: str | None) -> datetime | None:
    """Reject malformed clocks and legacy DST ambiguities; preserve UTC identity."""
    try:
        zone = ZoneInfo(timezone_name) if timezone_name else UTC
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return datetime.fromtimestamp(value, UTC).astimezone(zone)
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is not None:
            return parsed.astimezone(zone) if timezone_name else parsed
        if not timezone_name:
            return parsed  # Historical fixtures/caches without location metadata.
        candidates = {
            candidate.astimezone(UTC): candidate
            for fold in (0, 1)
            if (candidate := parsed.replace(tzinfo=zone, fold=fold)).astimezone(UTC)
            .astimezone(zone).replace(tzinfo=None) == parsed
        }
        return next(iter(candidates.values())) if len(candidates) == 1 else None
    except (TypeError, ValueError, OverflowError, OSError, ZoneInfoNotFoundError):
        return None


def _http_error_is_retryable(status_code: int | None) -> bool:
    if status_code is None:
        return False
    return status_code in {408, 425} or 500 <= status_code <= 599
