"""Protect twilight-derived observing-night windows across locations and seasons."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from astro_viewer.app.astronomy.engine import ObserverLocation, ObservingNightWindow
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.services.night_planner_service import NightPlannerService


@pytest.fixture(scope="module")
def astronomy_engine() -> SkyfieldAstronomyEngine:
    base_dir = Path(__file__).resolve().parents[1]
    engine = SkyfieldAstronomyEngine(base_dir / "data", Mock())
    yield engine
    engine.close()


def test_addis_ababa_upcoming_night_uses_local_sunset_and_sunrise(
    astronomy_engine: SkyfieldAstronomyEngine,
) -> None:
    location = ObserverLocation(
        "Addis Ababa",
        "Etiopia",
        9.03,
        38.74,
        "Africa/Addis_Ababa",
    )
    zone = ZoneInfo(location.timezone)

    window = astronomy_engine.observing_night_window(
        location,
        datetime(2026, 7, 10, 12, 0, tzinfo=zone),
    )

    assert window.state == "bounded"
    assert window.start is not None
    assert window.end is not None
    assert window.start.date().isoformat() == "2026-07-10"
    assert window.start.strftime("%H:%M") == "18:48"
    assert window.end.date().isoformat() == "2026-07-11"
    assert window.end.strftime("%H:%M") == "06:12"


def test_addis_ababa_current_night_keeps_previous_sunset(
    astronomy_engine: SkyfieldAstronomyEngine,
) -> None:
    location = ObserverLocation(
        "Addis Ababa",
        "Etiopia",
        9.03,
        38.74,
        "Africa/Addis_Ababa",
    )
    zone = ZoneInfo(location.timezone)
    reference = datetime(2026, 7, 11, 3, 0, tzinfo=zone)

    window = astronomy_engine.observing_night_window(location, reference)

    assert window.state == "bounded"
    assert window.start is not None
    assert window.end is not None
    assert window.start.date().isoformat() == "2026-07-10"
    assert window.end.date().isoformat() == "2026-07-11"
    assert window.contains(reference)


def test_minute_clock_label_keeps_the_minute_containing_sunset() -> None:
    zone = ZoneInfo("Africa/Addis_Ababa")
    start = datetime(2026, 7, 10, 18, 48, 31, tzinfo=zone)
    window = ObservingNightWindow.bounded(
        start,
        datetime(2026, 7, 11, 6, 12, 20, tzinfo=zone),
    )

    assert window.datetime_for_clock(18, 47) is None
    assert window.datetime_for_clock(18, 48) == start
    assert window.datetime_for_clock(18, 49) == datetime(2026, 7, 10, 18, 49, tzinfo=zone)


def test_planner_does_not_replace_sunset_best_time_with_window_end() -> None:
    zone = ZoneInfo("Africa/Addis_Ababa")
    start = datetime(2026, 7, 10, 18, 48, 31, tzinfo=zone)
    window = ObservingNightWindow.bounded(
        start,
        datetime(2026, 7, 11, 6, 12, 20, tzinfo=zone),
    )
    target = SimpleNamespace(
        best_time="18:48",
        observing_window="18:48 - 20:48",
        visible=True,
    )

    assert NightPlannerService._observing_time(target, window) == start


def test_planner_uses_now_when_target_window_is_already_active() -> None:
    zone = ZoneInfo("Africa/Addis_Ababa")
    now = datetime(2026, 7, 10, 23, 17, 42, tzinfo=zone)
    window = ObservingNightWindow.bounded(
        datetime(2026, 7, 10, 18, 48, tzinfo=zone),
        datetime(2026, 7, 11, 6, 12, tzinfo=zone),
    )
    target = SimpleNamespace(
        best_time="22:00",
        observing_window="21:00 - 02:00",
        visible=True,
    )

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now if tz is None else now.astimezone(tz)

    with patch("astro_viewer.app.services.night_planner_service.datetime", FixedDatetime):
        observing_time = NightPlannerService._observing_time(target, window)

    assert observing_time == datetime(2026, 7, 10, 23, 17, tzinfo=zone)


def test_altitude_samples_always_include_the_exact_night_end() -> None:
    zone = ZoneInfo("Africa/Addis_Ababa")
    start = datetime(2026, 7, 10, 18, 48, tzinfo=zone)
    end = datetime(2026, 7, 11, 6, 12, tzinfo=zone)

    samples = SkyfieldAstronomyEngine._window_datetime_samples(start, end, step_minutes=30)

    assert samples[-2] == datetime(2026, 7, 11, 5, 48, tzinfo=zone)
    assert samples[-1] == end


def test_single_useful_sample_produces_an_interpolated_window(
    astronomy_engine: SkyfieldAstronomyEngine,
) -> None:
    zone = ZoneInfo("Africa/Addis_Ababa")
    start = datetime(2026, 7, 10, 18, 48, tzinfo=zone)
    samples = [
        (start, 25.0),
        (start + timedelta(minutes=30), 15.0),
    ]

    _maximum, best_time, window = astronomy_engine._sample_summary(samples, threshold=20.0)

    assert best_time == start
    assert window == "18:48 - 19:03"


def test_rising_target_window_extends_to_exact_sunrise(
    astronomy_engine: SkyfieldAstronomyEngine,
) -> None:
    zone = ZoneInfo("Africa/Addis_Ababa")
    first = datetime(2026, 7, 11, 5, 18, tzinfo=zone)
    sunrise = datetime(2026, 7, 11, 6, 12, tzinfo=zone)
    samples = [
        (first, 15.0),
        (first + timedelta(minutes=30), 25.0),
        (sunrise, 30.0),
    ]

    _maximum, best_time, window = astronomy_engine._sample_summary(samples, threshold=20.0)

    assert best_time == first + timedelta(minutes=30)
    assert window == "05:33 - 06:12"


def test_target_reaching_threshold_only_at_sunrise_is_not_useful(
    astronomy_engine: SkyfieldAstronomyEngine,
) -> None:
    zone = ZoneInfo("Africa/Addis_Ababa")
    first = datetime(2026, 7, 11, 5, 18, tzinfo=zone)
    samples = [
        (first, 15.0),
        (first + timedelta(minutes=30), 18.0),
        (datetime(2026, 7, 11, 6, 12, tzinfo=zone), 20.0),
    ]

    maximum, best_time, window = astronomy_engine._sample_summary(samples, threshold=20.0)

    assert maximum == 20.0
    assert best_time is None
    assert window == "Non sopra la soglia osservativa"


@pytest.mark.parametrize(
    ("reference", "expected_state"),
    (
        (datetime(2026, 6, 21, 12, 0, tzinfo=ZoneInfo("Europe/Oslo")), "no_night"),
        (
            datetime(2026, 12, 21, 12, 0, tzinfo=ZoneInfo("Europe/Oslo")),
            "continuous_night",
        ),
    ),
)
def test_polar_day_and_night_are_explicit(
    astronomy_engine: SkyfieldAstronomyEngine,
    reference: datetime,
    expected_state: str,
) -> None:
    location = ObserverLocation(
        "Tromso",
        "Norvegia",
        69.6492,
        18.9553,
        "Europe/Oslo",
    )

    window = astronomy_engine.observing_night_window(location, reference)

    assert window.state == expected_state
    assert window.has_observing_window is (expected_state == "continuous_night")
