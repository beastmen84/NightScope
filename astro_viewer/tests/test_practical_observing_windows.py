"""Protect practical windows without changing existing scientific/scoring inputs."""

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from PySide6.QtCore import QObject

from astro_viewer.app.astronomy.comet_windows import CometWindowEventSource, _NightWindow
from astro_viewer.app.astronomy.engine import ObserverLocation, ObservingNightWindow, advance_time, as_utc
from astro_viewer.app.astronomy.planetary_opportunities import (
    PlanetaryNightGrid, _multi_planet_events, add_planetary_opportunities, build_night_grid, night_periods,
)
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.models.observing import AstronomicalEvent
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.calendar_overview import CalendarOverviewService
from astro_viewer.app.services.weather_presentation import (
    WeatherPresentationService, good_weather_windows, weather_window_label,
)
from astro_viewer.app.viewmodels.app_controller import AppController


NOW = datetime(2026, 9, 19, 18, tzinfo=ZoneInfo("Africa/Addis_Ababa"))
LOCATION = ObserverLocation("Addis Ababa", "", 9.03, 38.74, "Africa/Addis_Ababa")


def hour(instant, cloud=10, rain=0, wind=5, humidity=65):
    return WeatherHour(instant.isoformat(), instant.strftime("%H:%M"), cloud, rain, wind, humidity, 15)


def test_weather_good_window_covers_evening_without_losing_dawn_peak():
    start = NOW.replace(hour=19)
    clouds = [52, 47, 11, 16, 15, 18, 20, 13, 15, 5, 5, 8]
    hours = [hour(start + timedelta(hours=index), cloud) for index, cloud in enumerate(clouds)]
    night = ObservingNightWindow.bounded(NOW, (NOW + timedelta(days=1)).replace(hour=6, minute=14))
    digest = WeatherPresentationService(None).digest(hours, night, LOCATION.timezone)
    assert digest["goodWindows"] == ["21:00 - 06:14"]
    assert digest["bestWindow"] == "19:00 - 06:14"  # Longest usable opening, distinct from the peak.
    assert digest["bestWindowText"] == "Picco meteo previsto: 04:00 - 06:14"
    assert len(digest["bestHours"]) == 5  # Existing evenly-spaced forecast preview.
    assert digest["bestWindowMatchesGood"] is False
    assert WeatherPresentationService(None).digest([], night, LOCATION.timezone)["goodWindowText"] == ""


@pytest.mark.parametrize("clouds,start_hour,duplicates", [
    ([10, 10], 19, True), ([10, 10, 10], 19, True),
    ([10, 10, 10, 10], 19, False), ([10, 10, 85, 10, 10], 19, False),
    ([85, 85], 19, False), ([], 19, False), ([10], 19, False),
    ([10, 10], 23, True),
])
def test_weather_peak_duplicate_flag_compares_the_entire_good_window(clouds, start_hour, duplicates):
    start = NOW.replace(hour=start_hour)
    hours = [hour(start + timedelta(hours=index), cloud) for index, cloud in enumerate(clouds)]
    night = ObservingNightWindow.bounded(NOW, (NOW + timedelta(days=1)).replace(hour=6, minute=14))
    digest = WeatherPresentationService(None).digest(hours, night, LOCATION.timezone)
    assert digest["bestWindowMatchesGood"] is duplicates
    if duplicates:
        # Only Home hides the redundant line; other consumers retain the peak.
        assert len(digest["goodWindows"]) == 1
        assert digest["bestWindowText"] == f"Picco meteo previsto: {digest['goodWindows'][0]}"


@pytest.mark.parametrize("bad", [dict(cloud=36), dict(rain=21), dict(wind=21), dict(humidity=101),
                                 dict(cloud=-1), dict(cloud=35, rain=20, wind=20, humidity=100)])
def test_good_weather_splits_bad_hours_and_does_not_promote_a_single_sample(bad):
    hours = [hour(NOW + timedelta(hours=index)) for index in range(7)]
    hours[2] = hour(NOW + timedelta(hours=2), **bad)
    hours.pop(5)  # Missing forecast also breaks the final pair.
    assert [[value.time for value in group] for group in good_weather_windows(hours)] == [
        ["18:00", "19:00"], ["21:00", "22:00"],
    ]
    assert good_weather_windows([hours[0]]) == []
    assert good_weather_windows([]) == []


def test_weather_end_uses_elapsed_hour_at_autumn_fold():
    zone = ZoneInfo("Europe/Rome")
    start = datetime(2026, 10, 25, 2, tzinfo=zone, fold=0)
    night = ObservingNightWindow.bounded(start, start.replace(minute=30, fold=1))
    # The first 02:00 forecast ends at the second 02:00, not at 03:00.
    assert weather_window_label([hour(start)], night, "Europe/Rome") == "02:00 - 02:00"


@pytest.fixture(scope="module")
def engine():
    value = SkyfieldAstronomyEngine(Path(__file__).resolve().parents[1] / "data", None)
    yield value
    value.close()


def test_preferred_plateau_uses_existing_curve_and_preserves_sample_maximum(engine):
    samples = [(NOW + timedelta(hours=index), alt) for index, alt in enumerate([60, 75, 80, 75, 60])]
    before = engine._sample_window(samples, 8)
    assert engine._preferred_window_label(samples) == "18:40 - 21:20"
    assert engine._sample_window(samples, 8) == before
    assert before[1] == NOW + timedelta(hours=2)


@pytest.mark.parametrize("altitudes,minutes", [([], 60), ([15, 25, 15], 60), ([20, 31, 20], 15),
                                             ([float("nan")], 60)])
def test_no_invented_preferred_plateau_for_low_short_or_missing_curves(engine, altitudes, minutes):
    assert engine._preferred_window_label([
        (advance_time(NOW, timedelta(minutes=index * minutes)), alt) for index, alt in enumerate(altitudes)
    ]) == ""


@pytest.mark.parametrize("location,instant", [
    (LOCATION, NOW),
    (ObserverLocation("Rome", "", 41.9, 12.5, "Europe/Rome"), datetime(2026, 10, 25, 1, tzinfo=ZoneInfo("Europe/Rome"))),
    (ObserverLocation("Tromso", "", 69.6, 18.9, "Europe/Oslo"), datetime(2026, 6, 21, 12, tzinfo=ZoneInfo("Europe/Oslo"))),
])
def test_new_target_field_preserves_every_existing_solar_system_value(engine, location, instant):
    with patch.object(engine, "_now", return_value=instant):
        with patch.object(engine, "_preferred_window_label", return_value=""):
            reference = [asdict(value) for value in engine.solar_system_objects(location)]
        actual = [asdict(value) for value in engine.solar_system_objects(location)]
        night = engine.observing_night_window(location)
        assert engine.astronomical_darkness(location, night) == engine._deep_sky_night_window(location, night)
    for old, new in zip(reference, actual, strict=True):
        old.pop("preferred_window")
        new.pop("preferred_window")
        assert new == old


def test_home_darkness_getter_never_calculates_and_rejects_previous_location():
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._location = LOCATION
    controller._has_valid_location = lambda: True
    controller._astronomy_engine = Mock()
    controller._darkness_location = LOCATION
    controller._astronomical_darkness = ObservingNightWindow.bounded(NOW, NOW + timedelta(hours=9))
    assert controller.astronomicalDarkness["windowLabel"] == "18:00 – 03:00"
    controller._location = replace(LOCATION, latitude=35)
    assert controller.astronomicalDarkness["state"] == "unavailable"
    controller._location = replace(LOCATION, timezone="UTC")
    assert controller.astronomicalDarkness["state"] == "unavailable"
    assert controller._astronomy_engine.mock_calls == []
    controller._location = LOCATION
    controller._astronomical_darkness = ObservingNightWindow.no_night()
    assert controller.astronomicalDarkness["windowLabel"] == "Assente in questa notte"


def grid(angles, *, sun=-20, times=None):
    times = times or (NOW, NOW + timedelta(hours=1))
    length = len(times)
    directions = {key: np.repeat(np.asarray([[np.cos(np.radians(angle))],
                                            [np.sin(np.radians(angle))], [0.0]]), length, axis=1)
                  for key, angle in angles.items()}
    return PlanetaryNightGrid(tuple(times), np.full(length, sun, dtype=float),
                              {key: np.full(length, 30.0) for key in angles}, directions,
                              {key: np.ones(length) for key in angles})


def group_engine(ids):
    return SimpleNamespace(BODY_CONFIGS=[SimpleNamespace(object_id=value, name=value) for value in ids])


def test_compact_groups_require_all_pairs_not_a_chain():
    chain = grid({"venus": 0, "mars": 5, "jupiter": 10})
    assert _multi_planet_events(group_engine(chain.altitude), chain, NOW, NOW + timedelta(days=1)) == []
    compact = grid({"venus": 0, "mars": 2, "jupiter": 4})
    events = _multi_planet_events(group_engine(compact.altitude), compact, NOW, NOW + timedelta(days=1))
    assert len(events) == 1
    assert events[0].event_type_code == "planetary_group"
    assert set(events[0].target_object_ids) == set(compact.altitude)
    assert events[0].timing_kind == "window"


def test_maximal_compact_group_deduplicates_subgroups_and_parade():
    compact = grid({"venus": 0, "mars": 1, "jupiter": 2, "saturn": 3})
    events = _multi_planet_events(group_engine(compact.altitude), compact, NOW, NOW + timedelta(days=1))
    assert len(events) == 1
    assert len(events[0].target_object_ids) == 4
    assert events[0].event_type_code == "planetary_group"


def test_broad_parade_is_not_called_a_compact_conjunction():
    parade = grid({"venus": 0, "mars": 30, "jupiter": 60, "saturn": 90}, sun=-8)
    events = _multi_planet_events(group_engine(parade.altitude), parade, NOW, NOW + timedelta(days=1))
    assert len(events) == 1 and events[0].event_type_code == "planet_parade"
    assert "non necessariamente ravvicinati" in events[0].note


def test_faint_group_requires_darkness_and_every_member_above_altitude_floor():
    value = grid({"venus": 0, "mars": 2, "uranus": 4}, sun=-8)
    assert not value.visible(tuple(value.altitude)).any()
    value.sun_altitude[:] = -20
    value.altitude["uranus"][:] = 14.99
    assert not value.visible(tuple(value.altitude)).any()


def test_nights_do_not_bridge_missing_hour_or_dst_fold():
    value = grid({"mars": 0}, times=[NOW, NOW + timedelta(hours=2)])
    assert value.useful_nights(np.ones(2, dtype=bool)) == set()
    zone = ZoneInfo("Europe/Rome")
    first = datetime(2026, 10, 25, 2, tzinfo=zone, fold=0)
    value = grid({"mars": 0}, times=[first, first.replace(fold=1)])
    assert value.useful_nights(np.ones(2, dtype=bool)) == {datetime(2026, 10, 24).toordinal()}
    day = NOW.date().toordinal()
    assert len(night_periods({day, day + 1, day + 3}, NOW.tzinfo)) == 2


def event(kind="Opposizione", ids=("mars",)):
    return AstronomicalEvent("test", "Test", kind, "19/09/2026", "18:00", 92, "setup", "note",
                             event_at=NOW.isoformat(), target_object_id=ids[0], target_object_ids=ids,
                             angular_separation_deg=0.5)


def test_opposition_period_uses_apparent_size_not_arbitrary_fixed_days():
    times = [NOW + timedelta(days=day, hours=hour) for day in range(4) for hour in (0, 1)]
    value = grid({"mars": 0}, times=times)
    value.distance["mars"][:] = [1.1, 1.1, 1.0, 1.0, 1.02, 1.02, 1.06, 1.06]
    source = event()
    fake = group_engine(value.altitude)
    with patch("astro_viewer.app.astronomy.planetary_opportunities.build_night_grid", return_value=value) as build:
        result = add_planetary_opportunities(fake, LOCATION, [source], NOW, NOW + timedelta(days=4))[0]
        repeated = add_planetary_opportunities(fake, LOCATION, [source], NOW + timedelta(minutes=10), NOW + timedelta(days=4))
    assert len(result.favorable_periods) == 1
    assert result.favorable_periods[0][0].startswith("2026-09-20T12")
    assert result.favorable_periods[0][1].startswith("2026-09-22T12")
    assert repeated[0].favorable_periods == result.favorable_periods
    build.assert_called_once()
    assert replace(result, favorable_periods=(), period_note="", analysis_end_at="") == source


def test_conjunction_before_and_after_instant_but_not_outside_separation_limit():
    value = grid({"venus": 0, "mars": 2})
    source = event("Congiunzione planetaria", ("venus", "mars"))
    fake = group_engine(value.altitude)
    with patch("astro_viewer.app.astronomy.planetary_opportunities.build_night_grid", return_value=value):
        result = add_planetary_opportunities(fake, LOCATION, [source], NOW, NOW + timedelta(days=3))[0]
    assert result.favorable_periods
    value.direction["mars"][:] = [[0], [1], [0]]  # 90 degrees, cannot qualify.
    result = add_planetary_opportunities(fake, LOCATION, [source], NOW, NOW + timedelta(days=3))[0]
    assert result.favorable_periods == ()
    assert result.event_at == source.event_at


def test_calendar_retains_active_season_and_keeps_exact_instant_distinct():
    source = replace(event(), event_at=(NOW - timedelta(days=2)).isoformat(),
                     favorable_periods=night_periods({NOW.date().toordinal()}, NOW.tzinfo))
    overview = CalendarOverviewService().build(events=[source.to_qml()], now=NOW, has_configured_equipment=True)
    item = overview["items"][0]
    assert item["daysUntil"] == 0
    assert item["eventAt"] == source.event_at
    assert item["favorablePeriodText"] == "19/09/2026 – 19/09/2026"
    assert CalendarOverviewService().build(events=[source.to_qml()], now=NOW + timedelta(days=2),
                                          has_configured_equipment=True)["items"] == []
    future = replace(source, favorable_periods=night_periods({NOW.date().toordinal() + 50}, NOW.tzinfo))
    upcoming = CalendarOverviewService().build(events=[future.to_qml()], now=NOW, has_configured_equipment=True)
    assert upcoming["items"][0]["daysUntil"] == 50
    assert upcoming["highlights"] == []  # A past instant cannot hide a long gap.


def test_calendar_30_day_filter_can_include_a_season_before_distant_exact_event():
    source = replace(event(), event_at=(NOW + timedelta(days=40)).isoformat(),
                     favorable_periods=night_periods({NOW.date().toordinal()}, NOW.tzinfo))
    item = CalendarOverviewService().build(events=[source.to_qml()], now=NOW,
                                          has_configured_equipment=True)["items"][0]
    assert item["daysUntil"] == 0
    assert item["eventAt"] == source.event_at


def test_comet_does_not_advertise_last_sample_as_absolute_best():
    source = CometWindowEventSource(None)
    windows = [_NightWindow((NOW + timedelta(days=day)).date(), NOW + timedelta(days=day),
                           NOW + timedelta(days=day, hours=10), NOW + timedelta(days=day, hours=5),
                           12 - day * 0.1, 50 + day, 80, 90, 0.1) for day in range(3)]
    prepared = SimpleNamespace(cache_record=SimpleNamespace(fetched_at=NOW.isoformat()), freshness="fresh")
    record = SimpleNamespace(spk_id="123", designation="Test comet")
    end = windows[-1].end
    result = source._event(record, windows, prepared, analysis_end=end)
    assert result.peak_at == windows[-1].peak.isoformat()  # Technical metadata retained.
    assert result.best_time == result.date_label
    assert "05:00" not in result.best_time
    assert "limite del periodo analizzato" in result.period_note
    assert result.analysis_end_at == end.isoformat()
    assert result.favorable_periods == ((windows[0].start.isoformat(), end.isoformat()),)


def test_real_planetary_grid_matches_scalar_geometry_and_keeps_bounded_cache(engine):
    value = build_night_grid(engine, LOCATION, NOW, NOW + timedelta(days=1))
    assert len(value.times) > 0
    assert all(instant.tzinfo is not None for instant in value.times)
    for index in (0, len(value.times) // 2, len(value.times) - 1):
        observer = engine._observer(LOCATION).at(engine._to_skyfield_time(value.times[index]))
        mars = observer.observe(engine._ephemeris["mars"]).apparent()
        venus = observer.observe(engine._ephemeris["venus"]).apparent()
        assert value.altitude["mars"][index] == pytest.approx(mars.altaz()[0].degrees, abs=1e-8)
        assert value.separation("mars", "venus")[index] == pytest.approx(mars.separation_from(venus).degrees, abs=1e-8)
    assert all(as_utc(right) > as_utc(left) for left, right in zip(value.times, value.times[1:]))


def test_real_polar_day_grid_has_no_fabricated_summer_nights(engine):
    location = ObserverLocation("North pole", "", 90, 0, "UTC")
    now = datetime(2026, 7, 1, 12, tzinfo=UTC)
    value = build_night_grid(engine, location, now, now + timedelta(days=1))
    # The 90-day look-back also lies in polar daylight at this latitude/date.
    assert value.times == ()
    assert _multi_planet_events(engine, value, now, now + timedelta(days=1)) == []
