from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.observing_night_service import weather_hours_for_night
from astro_viewer.app.viewmodels.app_controller import AppController


def test_weather_selection_keeps_only_one_location_aware_night() -> None:
    zone = ZoneInfo("Africa/Addis_Ababa")
    night_window = ObservingNightWindow.bounded(
        datetime(2026, 7, 10, 18, 48, tzinfo=zone),
        datetime(2026, 7, 11, 6, 12, tzinfo=zone),
    )
    forecast_start = datetime(2026, 7, 10, 22, 0)
    hours = [_weather_hour(forecast_start + timedelta(hours=index)) for index in range(24)]

    selected = weather_hours_for_night(hours, night_window, "Africa/Addis_Ababa")

    assert [hour.timestamp for hour in selected] == [
        "2026-07-10T22:00",
        "2026-07-10T23:00",
        "2026-07-11T00:00",
        "2026-07-11T01:00",
        "2026-07-11T02:00",
        "2026-07-11T03:00",
        "2026-07-11T04:00",
        "2026-07-11T05:00",
        "2026-07-11T06:00",
    ]


def test_best_weather_window_never_bridges_a_daytime_gap() -> None:
    hours = [
        _weather_hour(datetime(2026, 7, 10, 5, 0)),
        _weather_hour(datetime(2026, 7, 10, 20, 0)),
        _weather_hour(datetime(2026, 7, 10, 21, 0)),
    ]

    best = AppController._best_weather_hours(hours)
    label = AppController._weather_window_label(best)

    assert [hour.time for hour in best] == ["20:00", "21:00"]
    assert label == "20:00 - 22:00"
    assert label != "05:00 - 22:00"


def test_weather_selection_includes_last_hour_before_sunrise() -> None:
    zone = ZoneInfo("Africa/Addis_Ababa")
    night_window = ObservingNightWindow.bounded(
        datetime(2026, 7, 10, 18, 48, tzinfo=zone),
        datetime(2026, 7, 11, 6, 12, tzinfo=zone),
    )
    hours = [
        _weather_hour(datetime(2026, 7, 10, 18, 0)),
        _weather_hour(datetime(2026, 7, 10, 19, 0)),
        _weather_hour(datetime(2026, 7, 11, 6, 0)),
        _weather_hour(datetime(2026, 7, 11, 7, 0)),
    ]

    selected = weather_hours_for_night(hours, night_window, "Africa/Addis_Ababa")

    assert [hour.time for hour in selected] == ["19:00", "06:00"]


def test_best_weather_window_label_is_clamped_to_sunrise() -> None:
    zone = ZoneInfo("Africa/Addis_Ababa")
    night_window = ObservingNightWindow.bounded(
        datetime(2026, 7, 10, 18, 48, tzinfo=zone),
        datetime(2026, 7, 11, 6, 12, tzinfo=zone),
    )
    hours = [
        _weather_hour(datetime(2026, 7, 11, hour, 0))
        for hour in (4, 5, 6)
    ]

    label = AppController._weather_window_label(
        hours,
        night_window,
        "Africa/Addis_Ababa",
    )

    assert label == "04:00 - 06:12"


def _weather_hour(timestamp: datetime) -> WeatherHour:
    return WeatherHour(
        timestamp=timestamp.isoformat(timespec="minutes"),
        time=timestamp.strftime("%H:%M"),
        cloud_cover=10,
        precipitation_probability=0,
        wind_kmh=5,
        humidity=50,
        temperature_c=18.0,
    )
