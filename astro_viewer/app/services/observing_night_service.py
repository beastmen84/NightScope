"""Select and group forecast hours inside local observing-night windows."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from math import isfinite
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from astro_viewer.app.astronomy.engine import ObservingNightWindow, advance_time, as_utc
from astro_viewer.app.models.weather import WeatherHour


def is_usable_weather_hour(hour: WeatherHour) -> bool:
    values = (hour.precipitation_probability, hour.cloud_cover, hour.wind_kmh, hour.humidity)
    if any(not isinstance(value, (int, float)) or not isfinite(value) or value < 0 for value in values):
        return False
    return (
        hour.precipitation_probability <= 35
        and hour.cloud_cover <= 65
        and hour.wind_kmh <= 28
        and hour.humidity <= 100
        and weather_hour_observing_score(hour) >= 45
    )


def weather_hour_observing_score(hour: WeatherHour) -> int:
    score = 100
    score -= min(55, round(hour.cloud_cover * 0.55))
    score -= min(30, round(hour.precipitation_probability * 0.45))
    score -= max(0, hour.wind_kmh - 10)
    score -= max(0, round((hour.humidity - 70) * 0.25))
    return max(0, min(100, score))


def usable_weather_intervals(
    hours: Sequence[WeatherHour],
    night_window: ObservingNightWindow | None,
) -> tuple[tuple[datetime, datetime], ...]:
    """Return UTC forecast bins, without bridging missing/bad/ambiguous hours.

    A row covers at most one elapsed hour, or until the next row if earlier.
    Conflicting duplicates are conservative: every row at that instant must pass.
    """
    rows: dict[datetime, bool] = {}
    for hour in hours:
        instant = _parse_timestamp(hour)
        if instant is None:
            continue
        if instant.tzinfo is None:
            if night_window is None or night_window.start is None:
                continue
            zone = night_window.start.tzinfo
            first = instant.replace(tzinfo=zone, fold=0)
            second = instant.replace(tzinfo=zone, fold=1)
            # Offset-free ambiguous/nonexistent DST hours cannot locate a bin.
            if first.utcoffset() != second.utcoffset():
                continue
            instant = first
        instant = as_utc(instant)
        rows[instant] = rows.get(instant, True) and is_usable_weather_hour(hour)
    timestamps = sorted(rows)
    intervals: list[tuple[datetime, datetime]] = []
    for index, start in enumerate(timestamps):
        if not rows[start]:
            continue
        end = start + timedelta(hours=1)
        if index + 1 < len(timestamps):
            end = min(end, timestamps[index + 1])
        if night_window is not None and night_window.has_observing_window:
            start = max(start, as_utc(night_window.start))
            end = min(end, as_utc(night_window.end))
        if start >= end:
            continue
        if intervals and intervals[-1][1] == start:
            intervals[-1] = (intervals[-1][0], end)
        else:
            intervals.append((start, end))
    return tuple(intervals)


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
    parsed_hours.sort(key=lambda item: as_utc(item[0]))
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
    end = advance_time(start, timedelta(hours=24))
    parsed_hours = [
        (timestamp, hour)
        for hour in hours
        if (timestamp := weather_hour_datetime(hour, timezone)) is not None
    ]
    if not parsed_hours:
        return list(hours[:24])
    parsed_hours.sort(key=lambda item: as_utc(item[0]))
    return [hour for timestamp, hour in parsed_hours if as_utc(start) <= as_utc(timestamp) < as_utc(end)]


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
