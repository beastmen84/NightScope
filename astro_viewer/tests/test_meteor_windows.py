"""Protect advance meteor planning, source drift, forecast gaps and worker isolation."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from threading import Event, RLock
from time import monotonic, sleep
from types import SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication
from skyfield import almanac
from skyfield.api import Star, wgs84

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.astronomy.meteor_windows import (
    MIN_WINDOW, STEP, MeteorGeometry, MeteorWindow, radiant_at, remaining_window, windows_from_samples,
)
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.models.observing import AstronomicalEvent
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.calendar_overview import CalendarOverviewService
from astro_viewer.app.services.imo_calendar import ImoCalendar, MeteorShower
from astro_viewer.app.services.imo_meteor_events import _weather_text, annual_meteor_events
from astro_viewer.app.services.imo_radiant_drift import extract_drift_layout, radiant_drift_rows
from astro_viewer.app.viewmodels.meteor_window_manager import MeteorWindowManager


NOW = datetime(2026, 9, 20, tzinfo=UTC)
START = datetime(2026, 10, 9, 19, tzinfo=UTC)
ROME = ObserverLocation("Rome", "", 41.9, 12.5, "Europe/Rome")
DRA = MeteorShower("DRA", date(2026, 10, 9), date(2026, 10, 6), date(2026, 10, 10), 262, 54, "5")


def samples(count=25, *, sun=-25, radiant=45, moon=-10, illumination=90):
    times = [START + index * STEP for index in range(count)]
    return (times, [sun] * count, [radiant] * count, [moon] * count, [illumination] * count, [True] * count)


@pytest.mark.parametrize("sun,radiant,moon,illumination,reason,favorable", [
    (-25, 45, -10, 100, "ok", True), (-18, 30, -0.83, 90, "ok", True),
    (-25, 45, 40, 25, "ok", True), (-25, 45, 40, 26, "ok", False),
    (-25, 15, -10, 0, "ok", False), (-25, 29.9, -10, 0, "ok", False),
    (-17.9, 80, -10, 0, "no_darkness", False), (-25, 14.9, -10, 0, "low_radiant", False),
    (-25, -20, -10, 0, "low_radiant", False), (float("nan"), 45, -10, 0, "unavailable", False),
])
def test_sample_thresholds(sun, radiant, moon, illumination, reason, favorable):
    result = windows_from_samples(*samples(sun=sun, radiant=radiant, moon=moon, illumination=illumination))
    assert result.reason == reason
    assert any(window.favorable for window in result.windows) == favorable
    assert all(window.start == START and window.end == START + timedelta(hours=2) for window in result.windows)


@pytest.mark.parametrize("count,expected", [(1, False), (6, False), (7, True)])
def test_minimum_duration_and_no_added_trailing_sample(count, expected):
    result = windows_from_samples(*samples(count))
    assert bool(result.windows) is expected
    assert all(window.end == START + (count - 1) * STEP for window in result.windows)


def test_bad_sample_and_missing_sample_split_intervals():
    values = samples()
    values[2][10] = 0
    for array in values:
        del array[18]
    result = windows_from_samples(*values)
    assert [(window.start, window.end) for window in result.windows if window.favorable] == [
        (START, START + 9 * STEP), (START + 11 * STEP, START + 17 * STEP)]
    assert windows_from_samples([], [], [], [], [], []).reason == "unavailable"


def test_ra_wrap_interpolation_and_no_extrapolation():
    shower = replace(DRA, radiant_drift=((date(2026, 10, 8), 359, 54), (date(2026, 10, 10), 1, 56)))
    assert radiant_at(shower, START.replace(hour=0)) == (0, 55, True)
    assert radiant_at(shower, START.replace(day=7)) == (262, 54, False)
    assert radiant_at(shower, START.replace(day=11)) == (262, 54, False)


def test_drift_parser_preserves_empty_columns_and_rejects_ambiguity():
    layout = "Date                  ORI                DRA\nOct 05                80° +14°           261° +54°\nOct 10                88° +15°           262° +54°\nOct 15                91° +15°           263° +54°"
    result = radiant_drift_rows(layout, DRA)
    assert [row[1] for row in result] == [261, 262, 263]
    assert radiant_drift_rows(layout.replace("262° +54°", "362° +54°"), DRA) == ()
    assert radiant_drift_rows(layout + "\nDRA", DRA) == ()
    assert radiant_drift_rows(layout.replace("DRA", "XXX"), DRA) == ()
    assert radiant_drift_rows("", DRA) == ()


def test_pdf_projection_preserves_sparse_columns_and_ignores_raised_glyphs():
    class Page:
        def extract_text(self, *, visitor_text):
            for text, x, y, size in [("DRA", 120, 100, 10), ("Oct 5", 0, 90, 10),
                                     ("261", 100, 90, 10), ("+54", 135, 90, 10),
                                     ("◦", 113, 93.6, 7), ("Oct 10", 0, 80, 10),
                                     ("262", 100, 80, 10), ("+54", 135, 80, 10)]:
                visitor_text(text, [1., 0., 0., 1., 0., 0.], [1., 0., 0., 1., x, y], {}, size)
    assert len(radiant_drift_rows(extract_drift_layout(Page()), DRA)) == 2


def calendar():
    return ImoCalendar(2026, (DRA,), NOW, Path("calendar-2026.pdf"))


def base_event():
    return AstronomicalEvent("planet", "Planet", "Opposizione", "", "", 90, "", "", event_at=START.isoformat())


def window(**values):
    return replace(MeteorWindow(START, START + timedelta(hours=2), True, 40, 60, -10, 90, False), **values)


def test_annual_overlay_retains_peak_and_non_meteors_but_exposes_local_geometry():
    other = base_event()
    local = MeteorGeometry((window(),), "ok")
    result = annual_meteor_events([other], calendar(), NOW, geometry={"DRA": local}, location=ROME)
    assert next(item for item in result if item.id == "planet") is other
    meteor = next(item for item in result if item.source_code == "imo_calendar")
    assert meteor.best_time == "09/10/2026 (UT)" and not meteor.peak_at
    assert meteor.visibility_state == "favorable" and meteor.visibility_label == "Geometria favorevole"
    assert "21:00" in meteor.observing_window  # Location zone, even when caller's now is UTC.
    assert "deriva non disponibile" in meteor.period_note
    assert "non un picco" in meteor.note
    facts = {code: value for code, _, value in meteor.event_facts}
    assert "non disponibili" in facts["meteor_weather"]
    assert "Sotto l'orizzonte" in facts["moon"]
    overview = CalendarOverviewService().build(events=[item.to_qml() for item in result], now=NOW, has_configured_equipment=False)
    assert next(item for item in overview["items"] if item["typeCode"] == "meteor_shower")["priorityLabel"] == "Calendario IMO"


@pytest.mark.parametrize("reason,label,state", [("no_darkness", "Buio", "poor"), ("low_radiant", "Radiante", "poor"),
                                                ("too_short", "30 minuti", "poor"), ("unavailable", "non disponibile", "check")])
def test_no_false_window_when_local_geometry_fails(reason, label, state):
    result = annual_meteor_events([base_event()], calendar(), NOW, geometry={"DRA": MeteorGeometry(reason=reason)}, location=ROME)
    meteor = next(item for item in result if item.source_code == "imo_calendar")
    assert meteor.visibility_state == state and label in meteor.visibility_detail


def test_current_time_clips_expired_windows_and_preserves_next_local_night():
    first = window(start=START - timedelta(days=1), end=START - timedelta(days=1) + timedelta(hours=2))
    next_night = window(start=START + timedelta(days=1), end=START + timedelta(days=1, hours=2))
    now = START + timedelta(hours=1, minutes=40)
    result = annual_meteor_events([base_event()], calendar(), now, geometry={"DRA": MeteorGeometry((first, window(), next_night), "ok")}, location=ROME)
    meteor = next(item for item in result if item.source_code == "imo_calendar")
    assert "10/10/2026" in meteor.observing_window
    assert "09/10/2026" not in meteor.observing_window


def weather(instant, cloud=10):
    return WeatherHour(instant.isoformat(), "", cloud, 0, 5, 65, 15)


@pytest.mark.parametrize("rows,expected", [
    ([], "non disponibili"), ([weather(START - timedelta(days=1))], "non disponibili"),
    ([weather(START)], "Previsioni parziali; meteo utilizzabile"),
    ([weather(START, 100)], "Previsioni parziali: nessuna apertura"),
    ([weather(START, 100), weather(START + timedelta(hours=1), 100)], "Meteo sfavorevole"),
    ([weather(START), weather(START + timedelta(hours=1))], "Meteo utilizzabile"),
    ([weather(START), weather(START, 100), weather(START + timedelta(hours=1), 100)], "Meteo sfavorevole"),
])
def test_forecast_is_separate_and_never_fills_gaps(rows, expected):
    assert expected in _weather_text(window(), rows, ROME.timezone, NOW)


def test_forecast_ambiguous_dst_hour_and_real_elapsed_time():
    zone = ZoneInfo("Europe/Rome")
    instant = datetime(2026, 10, 25, 0, tzinfo=UTC)
    bounded = window(start=instant, end=instant + timedelta(hours=2))
    assert "non disponibili" in _weather_text(bounded, [weather(datetime(2026, 10, 25, 2))], zone.key, NOW)
    rows = [weather(instant), weather(instant + timedelta(hours=1))]
    label = _weather_text(bounded, rows, zone.key, NOW)
    assert "Meteo utilizzabile" in label
    assert "UTC+0200" in label and "UTC+0100" in label


@pytest.fixture(scope="module")
def engine():
    value = SkyfieldAstronomyEngine(Path(__file__).resolve().parents[1] / "data", None)
    yield value
    value.close()


@pytest.mark.parametrize("location", [ROME, ObserverLocation("Addis", "", 9.03, 38.74, "Africa/Addis_Ababa"),
                                     ObserverLocation("Cape Town", "", -33.9, 18.4, "Africa/Johannesburg")])
def test_real_geometry_matches_independent_skyfield_directions(engine, location):
    result = engine.meteor_geometry(location, DRA)
    observer = engine._ephemeris["earth"] + wgs84.latlon(location.latitude, location.longitude)
    for interval in result.windows:
        assert interval.end - interval.start >= MIN_WINDOW
        instants = [interval.start, interval.start + (interval.end - interval.start) / 2, interval.end]
        times = engine._timescale.from_datetimes(instants)
        positions = observer.at(times)
        alt = positions.observe(Star(ra_hours=262 / 15, dec_degrees=54)).apparent().altaz()[0].degrees
        sun = positions.observe(engine._ephemeris["sun"]).apparent().altaz()[0].degrees
        moon = positions.observe(engine._ephemeris["moon"]).apparent().altaz()[0].degrees
        illumination = almanac.fraction_illuminated(engine._ephemeris, "moon", times) * 100
        assert np.all(sun <= -18)
        assert np.all(alt >= (30 if interval.favorable else 15) - 0.02)
        assert abs(alt[0] - interval.radiant_max) < 0.02  # Draconids descend in these windows.
        if interval.favorable:
            assert np.all((moon <= -0.83) | (illumination <= 25))


def test_polar_summer_does_not_invent_darkness(engine):
    shower = replace(DRA, peak=date(2026, 6, 21), active_start=date(2026, 6, 20), active_end=date(2026, 6, 22))
    result = engine.meteor_geometry(ObserverLocation("Tromso", "", 69.65, 18.95, "Europe/Oslo"), shower)
    assert result.reason == "no_darkness" and not result.windows


@pytest.mark.parametrize("return_to_original", [False, True])
def test_worker_coalesces_and_rejects_old_location_without_blocking_qt(return_to_original):
    app = QCoreApplication.instance() or QCoreApplication([])
    entered, release = Event(), Event()
    calls = []
    def calculate(location, shower):
        calls.append(location)
        entered.set()
        release.wait(2)
        return MeteorGeometry(reason=location.city)
    manager = MeteorWindowManager(calculate, RLock())
    second = replace(ROME, city="Second", latitude=-33.9)
    try:
        assert manager.request(calendar(), ROME, NOW.date()) == {}
        manager._timer.stop()
        manager._start()
        assert entered.wait(1)
        assert manager.request(calendar(), second, NOW.date()) == {}
        selected = ROME if return_to_original else second
        if return_to_original:
            assert manager.request(calendar(), selected, NOW.date()) == {}
        release.set()
        deadline = monotonic() + 3
        while manager._published_key != manager._key and monotonic() < deadline:
            app.processEvents()
            sleep(0.005)
        assert manager.request(calendar(), selected, NOW.date())["DRA"].reason == selected.city
        assert calls == [ROME, selected]
        assert manager.request(None, None, None) == {}
    finally:
        release.set()
        manager.stop()


def test_worker_failure_and_stop_never_publish_stale_data(monkeypatch):
    app = QCoreApplication.instance() or QCoreApplication([])
    pending = []
    monkeypatch.setattr("astro_viewer.app.viewmodels.meteor_window_manager.Thread",
                        lambda **kwargs: SimpleNamespace(start=lambda: pending.append(kwargs["target"])))
    manager = MeteorWindowManager(Mock(side_effect=ValueError("bad ephemeris")), RLock())
    assert app and manager.request(calendar(), ROME, NOW.date()) == {}
    manager._timer.stop()
    manager._start()
    pending.pop()()
    assert manager.request(calendar(), ROME, NOW.date())["DRA"].reason == "unavailable"
    manager.stop()
    assert manager.request(calendar(), ROME, NOW.date()) == {}


def test_ongoing_window_recomputes_moon_and_radiant_facts():
    values = samples()
    values[3][:6] = [40] * 6
    values[2][:6] = [70] * 6
    result = windows_from_samples(*values)
    useful = next(item for item in result.windows if not item.favorable)
    clipped = remaining_window(useful, START + 6 * STEP)
    assert clipped.moon_altitude_max == -10
    assert clipped.radiant_max == 45
    assert clipped.start == START + 6 * STEP
