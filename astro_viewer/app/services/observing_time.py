"""Parse and format clock values relative to an observing-night boundary."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.localization import tr


def same_observing_night(
    left: ObservingNightWindow,
    right: ObservingNightWindow,
) -> bool:
    if left.state != right.state:
        return False
    if left.start is None or left.end is None or right.start is None or right.end is None:
        return left.start == right.start and left.end == right.end
    return (
        abs((left.start - right.start).total_seconds()) < 60
        and abs((left.end - right.end).total_seconds()) < 60
    )


def home_time_label(
    item: CelestialObject,
    night_window: ObservingNightWindow | None,
) -> str:
    useful_best = first_observing_datetime(item.best_time, night_window)
    if useful_best:
        return format_home_datetime(useful_best)
    useful_window = first_observing_datetime(item.observing_window, night_window)
    if useful_window:
        return format_home_datetime(useful_window)
    return tr("Non in finestra notturna")


def home_window_label(
    item: CelestialObject,
    night_window: ObservingNightWindow | None,
) -> str:
    useful_times = [
        candidate
        for hour, minute in all_times(item.observing_window)
        if (
            candidate := observing_datetime_for_clock(
                night_window,
                hour,
                minute,
            )
        )
        is not None
    ]
    if len(useful_times) >= 2:
        return (
            f"{useful_times[0].strftime('%H:%M')} - "
            f"{useful_times[-1].strftime('%H:%M')}"
        )
    if useful_times:
        return format_home_datetime(useful_times[0])
    return item.observing_window


def first_useful_time(
    value: str,
    night_window: ObservingNightWindow | None,
) -> tuple[int, int] | None:
    candidate = first_observing_datetime(value, night_window)
    if candidate is not None:
        return candidate.hour, candidate.minute
    return None


def first_observing_datetime(
    value: str,
    night_window: ObservingNightWindow | None,
) -> datetime | None:
    for hour, minute in all_times(value):
        candidate = observing_datetime_for_clock(night_window, hour, minute)
        if candidate is not None:
            return candidate
    return None


def observing_datetime_for_clock(
    night_window: ObservingNightWindow | None,
    hour: int,
    minute: int,
) -> datetime | None:
    if night_window is None:
        day = 2 if hour < 12 else 1
        return datetime(2000, 1, day, hour, minute, tzinfo=ZoneInfo("UTC"))
    return night_window.datetime_for_clock(hour, minute)


def all_times(value: str) -> list[tuple[int, int]]:
    return [
        (int(hour), int(minute))
        for hour, minute in re.findall(r"\b([0-2]?\d):([0-5]\d)\b", value or "")
        if 0 <= int(hour) <= 23
    ]


def parse_hour_minute(value: str) -> tuple[int, int] | None:
    match = re.search(r"\b([0-2]?\d):([0-5]\d)\b", value or "")
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23:
        return None
    return hour, minute


def parse_event_date(value: str, now: datetime) -> datetime | None:
    for fmt in ("%d/%m/%Y", "%d/%m"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        year = parsed.year if "%Y" in fmt else now.year
        candidate = datetime(year, parsed.month, parsed.day, tzinfo=now.tzinfo)
        if candidate < now - timedelta(days=1) and "%Y" not in fmt:
            candidate = datetime(
                now.year + 1,
                parsed.month,
                parsed.day,
                tzinfo=now.tzinfo,
            )
        return candidate
    return None


def format_home_datetime(value: datetime) -> str:
    return value.strftime("%H:%M")


def home_time_period_code(
    value: datetime,
    night_window: ObservingNightWindow | None,
) -> str:
    if night_window is not None and night_window.state == "bounded":
        if night_window.start is not None and value.date() == night_window.start.date():
            return "evening"
        if night_window.end is not None and night_window.end - value <= timedelta(hours=3):
            return "before_dawn"
    return "night"


def format_clock(hour: int, minute: int) -> str:
    return f"{hour:02d}:{minute:02d}"
