"""Protect observing status, timing, Moon, and weather presentation helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.observing_presentation import (
    ObservingPresentationService,
    parse_degrees,
)
from astro_viewer.app.services.observing_time import (
    all_times,
    first_observing_datetime,
)
from astro_viewer.app.services.weather_presentation import WeatherPresentationService


def _target(**updates: object) -> CelestialObject:
    values = {
        "id": "M 42",
        "name": "M 42",
        "object_type": "Nebula",
        "image": "",
        "magnitude": "4.0",
        "distance": "",
        "max_altitude": "55°",
        "direction": "SE",
        "best_time": "22:00",
        "observing_window": "22:00 - 01:00",
        "notes": "",
        "recommended_setup": "",
        "visibility_class": "",
        "azimuth": "",
        "time_above_horizon": "3 h",
        "current_altitude": "42°",
        "observable_now": True,
    }
    values.update(updates)
    return CelestialObject(**values)


def _weather_hour(value: datetime, cloud_cover: int) -> WeatherHour:
    return WeatherHour(
        timestamp=value.isoformat(),
        time=value.strftime("%H:%M"),
        cloud_cover=cloud_cover,
        precipitation_probability=5,
        wind_kmh=8,
        humidity=60,
        temperature_c=12.0,
    )


def test_observing_status_service_uses_prepared_runtime_context() -> None:
    zone = ZoneInfo("Europe/Rome")
    now = datetime(2026, 9, 2, 22, 30, tzinfo=zone)
    night_window = ObservingNightWindow.bounded(
        now - timedelta(hours=2),
        now + timedelta(hours=6),
    )

    code, title, detail = ObservingPresentationService().status_data(
        _target(),
        catalogue_name=None,
        now=now,
        night_window=night_window,
        monthly_visibility_blocked=False,
        useful_datetime=now,
        window="22:00 - 01:00",
        altitude_threshold=15.0,
    )

    assert code == "observable_now"
    assert title
    assert "42" in detail
    assert "22:00 - 01:00" in detail


@pytest.mark.parametrize("best_hour", (0, 4))
@pytest.mark.parametrize("altitude", ("52°", "39°", "10°", "-3°"))
@pytest.mark.parametrize("observable_now", (False, None))
def test_ended_dark_interval_never_claims_low_altitude_or_a_future_window(
    best_hour: int, altitude: str, observable_now: bool | None,
) -> None:
    zone = ZoneInfo("Europe/Rome")
    night = ObservingNightWindow.bounded(
        datetime(2026, 9, 5, 19, 30, tzinfo=zone),
        datetime(2026, 9, 6, 6, 40, tzinfo=zone),
    )
    item = _target(
        observing_start_at="2026-09-05T21:14:00+02:00",
        observing_end_at="2026-09-06T05:03:00+02:00",
        best_observing_at=datetime(2026, 9, 6, best_hour, tzinfo=zone).isoformat(),
        current_altitude=altitude,
        observable_now=observable_now,
        night_eligible=True,
    )
    code, title, detail = ObservingPresentationService().status_data(
        item, catalogue_name=None,
        now=datetime(2026, 9, 6, 4, 20, tzinfo=UTC),
        night_window=night, monthly_visibility_blocked=False,
        useful_datetime=None, window="21:14 - 05:03", altitude_threshold=15,
    )
    assert code == "unavailable"
    assert title == "Finestra conclusa"
    assert detail == "La finestra utile di questa notte era 21:14 - 05:03."


@pytest.mark.parametrize(
    ("minute", "altitude", "expected"),
    ((59, "42°", "observable_now"), (60, "42°", "unavailable"),
     (-180, "7°", "later"), (-180, "42°", "later")),
)
def test_status_respects_half_open_absolute_useful_interval(
    minute: int, altitude: str, expected: str,
) -> None:
    zone = ZoneInfo("Europe/Rome")
    start = datetime(2026, 9, 6, 4, 0, tzinfo=zone)
    night = ObservingNightWindow.bounded(
        start - timedelta(hours=8), start + timedelta(hours=3),
    )
    item = _target(
        observing_start_at=start.isoformat(),
        observing_end_at=(start + timedelta(hours=1)).isoformat(),
        best_observing_at=(start + timedelta(minutes=30)).isoformat(),
        observable_now=None, current_altitude=altitude, night_eligible=True,
    )
    code, _title, detail = ObservingPresentationService().status_data(
        item, catalogue_name=None, now=start + timedelta(minutes=minute),
        night_window=night, monthly_visibility_blocked=False,
        useful_datetime=None, window="04:00 - 05:00", altitude_threshold=15,
    )
    assert code == expected
    if altitude == "42°":
        assert "sotto la soglia" not in detail


def test_weather_digest_is_independent_from_controller_state() -> None:
    zone = ZoneInfo("Europe/Rome")
    start = datetime(2026, 9, 2, 22, 0, tzinfo=zone)
    night_window = ObservingNightWindow.bounded(
        start - timedelta(hours=1),
        start + timedelta(hours=7),
    )
    hours = [
        _weather_hour(start + timedelta(hours=index), cloud_cover)
        for index, cloud_cover in enumerate((30, 10, 20))
    ]

    digest = WeatherPresentationService(NightPlannerService()).digest(
        hours,
        night_window,
        "Europe/Rome",
    )

    assert digest["cloudAverage"] == 20
    assert digest["rainProbability"] == 5
    assert digest["bestWindow"] == "22:00 - 01:00"
    assert len(digest["bestHours"]) == 3


def test_shared_time_helpers_keep_after_midnight_inside_the_same_night() -> None:
    zone = ZoneInfo("Europe/Rome")
    night_window = ObservingNightWindow.bounded(
        datetime(2026, 9, 2, 20, 0, tzinfo=zone),
        datetime(2026, 9, 3, 6, 0, tzinfo=zone),
    )

    parsed = first_observing_datetime("01:30", night_window)

    assert all_times("22:00 / 01:30 / 27:00") == [(22, 0), (1, 30)]
    assert parse_degrees("quota -12,5°") == -12.5
    assert parsed == datetime(2026, 9, 3, 1, 30, tzinfo=zone)
