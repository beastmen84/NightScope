from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.weather import WeatherHour


def weather_hours_for_night(
    hours: list[WeatherHour],
    night_window: ObservingNightWindow,
    timezone: str,
) -> list[WeatherHour]:
    if not night_window.has_observing_window:
        return []
    parsed_hours = [
        (timestamp, hour)
        for hour in hours
        if (timestamp := weather_hour_datetime(hour, timezone)) is not None
        and night_window.contains(timestamp)
    ]
    parsed_hours.sort(key=lambda item: item[0])
    return [hour for _, hour in parsed_hours]


def weather_hours_for_next_24(
    hours: list[WeatherHour],
    timezone: str,
    now: datetime,
) -> list[WeatherHour]:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    local_now = now.replace(tzinfo=zone) if now.tzinfo is None else now.astimezone(zone)
    start = local_now.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=24)
    parsed_hours = [
        (timestamp, hour)
        for hour in hours
        if (timestamp := weather_hour_datetime(hour, timezone)) is not None
    ]
    if not parsed_hours:
        return list(hours[:24])
    parsed_hours.sort(key=lambda item: item[0])
    return [hour for timestamp, hour in parsed_hours if start <= timestamp < end]


def consecutive_weather_groups(
    hours: list[WeatherHour],
    *,
    max_gap_minutes: int = 90,
) -> list[list[WeatherHour]]:
    groups: list[list[WeatherHour]] = []
    current: list[WeatherHour] = []
    previous: datetime | None = None
    for hour in hours:
        timestamp = _timestamp_order_value(hour)
        if timestamp is None:
            if current:
                groups.append(current)
            groups.append([hour])
            current = []
            previous = None
            continue
        gap_minutes = (timestamp - previous).total_seconds() / 60 if previous else 0
        if previous is not None and not (0 < gap_minutes <= max_gap_minutes):
            if current:
                groups.append(current)
            current = []
        current.append(hour)
        previous = timestamp
    if current:
        groups.append(current)
    return groups


def weather_hour_datetime(hour: WeatherHour, timezone: str) -> datetime | None:
    parsed = _parse_timestamp(hour)
    if parsed is None:
        return None
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=zone)
    return parsed.astimezone(zone)


def _parse_timestamp(hour: WeatherHour) -> datetime | None:
    try:
        return datetime.fromisoformat(str(hour.timestamp))
    except (TypeError, ValueError):
        return None


def _timestamp_order_value(hour: WeatherHour) -> datetime | None:
    parsed = _parse_timestamp(hour)
    if parsed is None:
        return None
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed
