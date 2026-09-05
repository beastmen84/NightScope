"""Regress reproduced astronomy-audit failures using adverse and positive controls."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
import math
import re
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from zoneinfo import ZoneInfo

import pytest
import numpy as np

from astro_viewer.app.astronomy.engine import (
    ObserverLocation,
    ObservingNightWindow,
    as_utc,
)
from astro_viewer.app.astronomy.catalog import mock_planets
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.application.catalogue_recommendations import (
    home_visible_objects_for_window,
)
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.models.sky import NightPlanItem
from astro_viewer.app.models.condition_inputs import ObservationConditionInputs
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.openaq_atmosphere_service import (
    OpenAQLocalAtmosphereService,
)
from astro_viewer.app.services.observing_night_service import weather_hours_for_next_24
from astro_viewer.app.services.observing_time import format_observing_clock
from astro_viewer.app.astronomy.comet_windows import CometWindowEventSource
from astro_viewer.app.services.seeing_service import BasicForecastSeeingProvider
from astro_viewer.app.services.weather_service import (
    OpenMeteoWeatherService,
    score_observability,
)


def weather_payload() -> dict:
    """Supply genuine clear/calm zero measurements, not omitted fields."""
    return {
        "hourly": {
            "time": ["2026-09-05T22:00"],
            "cloud_cover": [0],
            "precipitation_probability": [0],
            "wind_speed_10m": [0],
            "relative_humidity_2m": [50],
            "temperature_2m": [15],
            "visibility": [20000],
            "cloud_cover_low": [0],
            "cloud_cover_mid": [0],
            "cloud_cover_high": [0],
            "wind_gusts_10m": [0],
            "dew_point_2m": [5],
        }
    }


@pytest.mark.parametrize(
    "field",
    [
        "cloud_cover",
        "precipitation_probability",
        "wind_speed_10m",
        "relative_humidity_2m",
        "temperature_2m",
    ],
)
@pytest.mark.parametrize(
    "invalid", [None, [], [None], [float("nan")], [float("inf")], ["bad"], [True]]
)
def test_partial_weather_never_becomes_clear_sky(field, invalid):
    payload = weather_payload()
    if invalid is None:
        del payload["hourly"][field]
    else:
        payload["hourly"][field] = invalid
    hours = OpenMeteoWeatherService._parse_payload(payload)
    assert hours == []
    assert score_observability(hours).score_value == 0
    assert BasicForecastSeeingProvider().estimate(hours, None).seeing_score != 100


@pytest.mark.parametrize(
    "payload", [None, [], {}, {"hourly": None}, {"hourly": []}, {"hourly": {"time": 3}}]
)
def test_malformed_weather_shape_is_unavailable(payload):
    assert OpenMeteoWeatherService._parse_payload(payload) == []


def test_valid_zero_weather_and_missing_optional_seeing_are_distinct():
    payload = weather_payload()
    hours = OpenMeteoWeatherService._parse_payload(payload)
    assert len(hours) == 1 and hours[0].wind_kmh == 0
    assert score_observability(hours).score_value == 100
    assert BasicForecastSeeingProvider().estimate(hours, None).seeing_score == 100
    del payload["hourly"]["cloud_cover_low"]
    partial = OpenMeteoWeatherService._parse_payload(payload)
    assert len(partial) == 1 and partial[0].cloud_cover_low is None
    seeing = BasicForecastSeeingProvider().estimate(partial, None)
    assert seeing.confidence == "low" and seeing.seeing_score != 100


def test_invalid_fresh_weather_uses_valid_cache():
    service = OpenMeteoWeatherService()
    cached = (datetime.now(UTC) - timedelta(hours=2), weather_payload())
    response = Mock()
    response.json.return_value = {"hourly": {"time": ["2026-09-05T22:00"]}}
    location = ObserverLocation("Roma", "IT", 41.9, 12.5, "Europe/Rome")
    with (
        patch.object(service, "_read_cache", return_value=cached),
        patch.object(
            service,
            "_get_with_timeout_retry",
            return_value=response,
        ),
    ):
        hours = service.hourly_forecast(location)
    assert len(hours) == 1 and service.retry_recommended and service.last_error


def test_forecast_unix_timestamps_preserve_both_autumn_hours():
    payload = weather_payload()
    first = datetime(2026, 10, 25, 0, tzinfo=UTC)
    payload["timezone"] = "Europe/Rome"
    payload["hourly"]["time"] = [
        first.timestamp(),
        (first + timedelta(hours=1)).timestamp(),
    ]
    for key, value in payload["hourly"].items():
        if key != "time":
            value.append(value[0])
    hours = OpenMeteoWeatherService._parse_payload(payload)
    assert [hour.time for hour in hours] == ["02:00", "02:00"]
    assert [datetime.fromisoformat(hour.timestamp).utcoffset() for hour in hours] == [
        timedelta(hours=2),
        timedelta(hours=1),
    ]
    legacy = deepcopy(payload)
    legacy["hourly"]["time"] = ["2026-10-25T02:00", "2026-03-29T02:00"]
    assert OpenMeteoWeatherService._parse_payload(legacy) == []


@pytest.fixture(scope="module")
def engine():
    service = SkyfieldAstronomyEngine(
        Path(__file__).resolve().parents[1] / "data", None
    )
    yield service
    service.close()


@pytest.mark.parametrize(
    "kind",
    ["Planetary Nebula", "Nebulosa planetaria", "Nebulosa planetaria ES", "Galaxy"],
)
def test_deep_sky_threshold_does_not_match_planet_substring(kind):
    target = replace(mock_planets()[0], id="NGC7009", object_type=kind)
    assert SkyfieldAstronomyEngine._geometry_altitude_threshold(target) == 15
    assert (
        SkyfieldAstronomyEngine._geometry_altitude_threshold(
            replace(target, id="mercury")
        )
        == 8
    )


@pytest.mark.parametrize("month, day, elapsed_hours", [(3, 29, 4), (10, 25, 6)])
def test_dst_samples_are_unique_monotonic_elapsed_instants(month, day, elapsed_hours):
    zone = ZoneInfo("Europe/Rome")
    start = datetime(2026, month, day, tzinfo=zone)
    end = start.replace(hour=5)
    samples = SkyfieldAstronomyEngine._window_datetime_samples(
        start, end, step_minutes=30
    )
    utc = [as_utc(value) for value in samples]
    assert len(utc) == elapsed_hours * 2 + 1
    assert len(set(utc)) == len(utc)
    assert all(
        right - left == timedelta(minutes=30) for left, right in zip(utc, utc[1:])
    )


def test_repeated_clock_window_and_nonexistent_clock():
    zone = ZoneInfo("Europe/Rome")
    first = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0)
    second = first.replace(fold=1)
    window = ObservingNightWindow.bounded(first, second)
    assert (
        window.has_observing_window
        and window.contains(first)
        and not window.contains(second)
    )
    assert window.datetime_for_clock(2, 30, fold=1) is None
    assert as_utc(window.datetime_for_clock(2, 30, fold=1, include_end=True)) == as_utc(
        second
    )
    spring = ObservingNightWindow.bounded(
        datetime(2026, 3, 29, 0, tzinfo=zone),
        datetime(2026, 3, 29, 5, tzinfo=zone),
    )
    assert spring.datetime_for_clock(2, 30) is None


def test_final_segment_positive_window_is_retained(engine):
    start = datetime(2026, 9, 6, 5, 30, tzinfo=UTC)
    end = start + timedelta(minutes=30)
    maximum, best, left, right = engine._sample_window([(start, 10), (end, 20)], 15)
    assert maximum == 20 and left == start + timedelta(minutes=15) and right == end
    assert left <= best < right
    assert engine._sample_summary([(start, 10), (end, 15)], 15)[1] is None


def test_interpolation_and_duration_use_elapsed_time_at_dst(engine):
    zone = ZoneInfo("Europe/Rome")
    start = datetime(2026, 10, 25, 2, 30, tzinfo=zone, fold=0)
    end = start.replace(fold=1)
    crossing = engine._threshold_crossing((start, 10), (end, 20), 15)
    assert as_utc(crossing) == as_utc(start) + timedelta(minutes=30)
    assert engine._window_duration("02:30 - 02:30", start, end) == "1 h"


def test_planner_sorts_repeated_hours_by_timestamp():
    zone = ZoneInfo("Europe/Rome")
    start = datetime(2026, 10, 25, 0, tzinfo=zone)
    window = ObservingNightWindow.bounded(start, start.replace(hour=5))
    first = NightPlanItem(
        "02:45", "first", "first", 80, "", "", "", "", "2026-10-25T02:45:00+02:00"
    )
    second = replace(
        first,
        object_id="second",
        time_label="02:15",
        observing_at="2026-10-25T02:15:00+01:00",
    )
    assert NightPlannerService._sort_plan_items([second, first], window) == [
        first,
        second,
    ]
    assert (
        format_observing_clock(datetime.fromisoformat(first.observing_at), window)
        == "02:45 (UTC+02:00)"
    )
    assert (
        format_observing_clock(datetime.fromisoformat(second.observing_at), window)
        == "02:15 (UTC+01:00)"
    )


def test_daytime_mercury_does_not_enter_home_or_night_eligibility(engine):
    location = ObserverLocation("Roma", "IT", 41.9, 12.5, "Europe/Rome")
    now = datetime(2026, 9, 5, 12, tzinfo=UTC)
    window = engine.observing_night_window(location, now)
    config = next(
        value for value in engine.BODY_CONFIGS if value.object_id == "mercury"
    )
    target = engine._body_details(config, location, now=now, night_window=window)
    assert target.current_altitude_degrees > 50 and target.visible
    assert target.night_eligible is False and not target.observing_start_at
    assert home_visible_objects_for_window([target], window) == ()
    assert NightPlannerService._observing_time(target, window) is None


def test_twilight_month_admits_bright_planets_without_astronomical_darkness(engine):
    location = ObserverLocation("Edinburgh", "UK", 55.95, -3.19, "Europe/London")
    rows = [
        {"object_id": name, "solar_system_body_id": name}
        for name in ("moon", "venus", "jupiter", "uranus", "neptune")
    ]
    rows.append({"object_id": "north", "ra": "12:00:00", "dec": "+80:00:00"})
    visible = engine.catalogue_month_visibility(rows, location, 2026, 6)
    assert visible == {
        "moon": True,
        "venus": True,
        "jupiter": True,
        "uranus": False,
        "neptune": False,
        "north": False,
    }
    night = engine.observing_night_window(
        location, datetime(2026, 6, 20, 12, tzinfo=UTC)
    )
    assert night.has_observing_window
    assert not engine._deep_sky_night_window(location, night).has_observing_window


def test_live_and_moon_geometry_keep_planetary_nebula_threshold(engine):
    target = replace(mock_planets()[0], id="NGC7009", object_type="Planetary Nebula")
    now = datetime(2026, 9, 5, 22, tzinfo=UTC)
    night = ObservingNightWindow.bounded(now, now + timedelta(hours=5))
    location = ObserverLocation("Roma", "IT", 41.9, 12.5, "Europe/Rome")
    with (
        patch.object(engine, "_now", return_value=now),
        patch.object(
            engine,
            "observing_night_window",
            return_value=night,
        ),
        patch.object(engine, "_deep_sky_night_window", return_value=night),
        patch.object(
            engine,
            "_current_position",
            return_value=(10, 90),
        ),
    ):
        updated = engine.refresh_current_positions(
            [target, replace(target, id="jupiter")], location
        )
    assert updated[0].observable_now is False and updated[1].observable_now is True
    summary = engine._moon_geometry_summary_from_samples(
        target, [now], {now: 20}, {now: 10}, {now: 30}
    )
    assert summary.moon_visible_during_target_window is False


def test_batch_prefilter_keeps_interpolated_final_segment(engine):
    start = datetime(2026, 9, 6, 5, 30, tzinfo=UTC)
    night = ObservingNightWindow.bounded(start, start + timedelta(minutes=30))
    row = {
        "object_id": "NGC7009",
        "name": "Saturn Nebula",
        "magnitude": 8,
        "object_type": "Planetary Nebula",
        "description": "test",
    }
    observer = Mock()
    observer.at.return_value.observe.return_value.apparent.return_value.altaz.side_effect = [
        (
            SimpleNamespace(degrees=np.array([alt])),
            SimpleNamespace(degrees=np.array([90])),
            None,
        )
        for alt in (5, 10, 20)
    ]
    with patch.object(engine, "_observer", return_value=observer):
        objects = engine._catalogue_details_batch(
            [(90, row, 21, -11)],
            ObserverLocation("Roma", "IT", 41.9, 12.5, "Europe/Rome"),
            now=start,
            night_window=night,
        )
    assert len(objects) == 1 and objects[0].night_eligible
    assert objects[0].observing_window == "05:45 - 06:00"


def test_zero_opportunity_not_offered_and_positive_control_is_preserved():
    scoring = Mock()
    planner = NightPlannerService(nsom_scoring_service=scoring)
    target = replace(mock_planets()[0], score=90, visible=True)
    telescope = Telescope("test", "200/1000", 200, 1000, "Newton", "manual")
    weather = WeatherSummary("Good", 100, "", 0, 0, 0, 50, 15, "")
    scoring.score.return_value = 0
    assert (
        planner.plan(
            [target], weather, telescope, condition_inputs=ObservationConditionInputs()
        )
        == []
    )
    scoring.score.return_value = 50
    assert (
        len(
            planner.plan(
                [target],
                weather,
                telescope,
                condition_inputs=ObservationConditionInputs(),
            )
        )
        == 1
    )


def test_real_target_expiring_during_scoring_never_gets_a_fallback_time():
    scoring = Mock()
    scoring.score.return_value = 50
    planner = NightPlannerService(nsom_scoring_service=scoring)
    target = replace(mock_planets()[0], score=90, visible=True, night_eligible=True)
    telescope = Telescope("test", "200/1000", 200, 1000, "Newton", "manual")
    weather = WeatherSummary("Good", 100, "", 0, 0, 0, 50, 15, "")
    with (
        patch.object(planner, "_has_useful_window", return_value=True),
        patch.object(planner, "_observing_time", return_value=None),
    ):
        assert planner.plan(
            [target], weather, telescope, condition_inputs=ObservationConditionInputs()
        ) == []


def test_openaq_equator_and_prime_meridian_are_coordinates_not_missing_values():
    location = ObserverLocation("Origin", "", 0, 0, "UTC")
    assert (
        OpenAQLocalAtmosphereService._distance_km(
            {"coordinates": {"latitude": 0, "longitude": 0}}, location
        )
        == 0
    )
    assert (
        OpenAQLocalAtmosphereService._distance_km(
            {"coordinates": {"latitude": 91, "longitude": 0}}, location
        )
        is None
    )


@pytest.mark.parametrize(
    "start",
    [datetime(2026, 3, 28, 23, tzinfo=UTC), datetime(2026, 10, 24, 22, tzinfo=UTC)],
)
def test_weather_next_24_hours_is_elapsed_not_wall_time(start):
    payload = weather_payload()
    for key, values in payload["hourly"].items():
        payload["hourly"][key] = values * 48
    payload["timezone"] = "Europe/Rome"
    payload["hourly"]["time"] = [
        (start + timedelta(hours=index)).timestamp() for index in range(48)
    ]
    hours = OpenMeteoWeatherService._parse_payload(payload)
    selected = weather_hours_for_next_24(list(reversed(hours)), "Europe/Rome", start)
    assert selected == hours[:24]


def test_future_dated_cache_is_not_a_valid_weather_fallback():
    service = OpenMeteoWeatherService()
    response = Mock()
    response.json.return_value = {"hourly": None}
    with (
        patch.object(
            service,
            "_read_cache",
            return_value=(datetime.now(UTC) + timedelta(days=1), weather_payload()),
        ),
        patch.object(
            service,
            "_get_with_timeout_retry",
            return_value=response,
        ),
    ):
        assert service.hourly_forecast(ObserverLocation("Test", "", 0, 0, "UTC")) == []


def test_below_horizon_moon_does_not_veto_comet_window():
    source = CometWindowEventSource(Mock())
    dates = [
        datetime(2026, 9, 5, 22, tzinfo=UTC) + timedelta(minutes=30 * index)
        for index in range(4)
    ]
    apparent = Mock()
    apparent.altaz.return_value = (
        SimpleNamespace(degrees=np.full(4, 30)),
        None,
        SimpleNamespace(au=np.ones(4)),
    )
    apparent.separation_from.side_effect = [
        SimpleNamespace(degrees=np.full(4, value)) for value in (45, 5, 45, 5)
    ]
    observer_at = Mock()
    observer_at.observe.return_value.apparent.return_value = apparent
    comet = MagicMock()
    comet.__sub__.return_value.at.return_value.distance.return_value.au = np.ones(4)
    context = {
        "times": object(),
        "observer_at": observer_at,
        "sun": object(),
        "sun_apparent": object(),
        "moon_apparent": object(),
        "sun_altitudes": np.full(4, -20),
        "moon_altitudes": np.full(4, -10),
        "moon_illumination": np.ones(4),
        "datetimes": dates,
        "local_datetimes": dates,
        "end": dates[-1] + timedelta(minutes=30),
    }
    record = SimpleNamespace(absolute_magnitude=5, magnitude_slope=4)
    assert len(source._night_windows(comet, record, context=context)) == 1
    context["moon_altitudes"] = np.full(4, 20)
    assert source._night_windows(comet, record, context=context) == []


def test_ephemeris_failure_warning_survives_location_transitions():
    from astro_viewer.app.astronomy.skyfield_engine import EphemerisUnavailableError
    from astro_viewer.tests.test_phase6_real_data import _controller

    with patch(
        "astro_viewer.app.application.dependencies.SkyfieldAstronomyEngine",
        side_effect=EphemerisUnavailableError("fixture"),
    ):
        with _controller() as controller:
            warning = controller.astronomyStatus
            assert warning and controller.astronomyAvailable is False
            controller._refresh_no_location_context()
            assert warning in controller.serviceStatus
            controller._refresh_startup_location_pending_context()
            assert warning in controller.serviceStatus
            controller._location = ObserverLocation(
                "Roma", "IT", 41.9, 12.5, "Europe/Rome"
            )
            controller._startup_location_detection_running = False
            controller._refresh_astronomy()
            assert warning in controller.serviceStatus
            assert controller._solar_system_objects == [] and controller._events == []
            assert controller._deep_sky == [] and controller._night_plan == []
            assert controller._moon.illumination == "n/d"


@pytest.mark.parametrize("angle", [0, 45, 90, 135, 180, 225, 270, 315])
@pytest.mark.parametrize("size", [44, 88, 206])
def test_actual_qml_moon_clipping_geometry_matches_spherical_phase(angle, size):
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtQml import QJSEngine

    app = QCoreApplication.instance() or QCoreApplication([])
    script_engine = QJSEngine()
    qml = (
        Path(__file__).resolve().parents[1] / "app/ui/pages/ObjectDetailPage.qml"
    ).read_text(encoding="utf-8")
    function = re.search(
        r"    function drawMoonPhase[\s\S]*?(?=\n    AppTheme)", qml
    ).group(0)
    result = script_engine.evaluate(
        """
        var points = [], clips = [], circles = [], clears = [];
        var theme = {withAlpha: function() { return 'black'; }};
        var ctx = {
            clearRect: function(x,y,w,h){clears.push([x,y,w,h]);},
            createRadialGradient: function(){return {addColorStop: function(){}};},
            beginPath: function(){points = [];},
            arc: function(x,y,r){circles.push([x,y,r]);}, fill: function(){},
            save: function(){}, restore: function(){}, fillRect: function(){}, stroke: function(){},
            closePath: function(){}, clip: function(){if (points.length) clips.push(points.slice());},
            moveTo: function(x,y){points.push([x,y]);}, lineTo: function(x,y){points.push([x,y]);}
        };
    """
        + function
        + f"\ndrawMoonPhase(ctx, {size}, {size}, {angle});"
        + "({clips: clips, circles: circles, clears: clears});"
    )
    assert not result.isError(), result.toString()
    drawing = result.toVariant()
    clips = drawing["clips"]
    center = size / 2
    radius = center - 3
    assert drawing["clears"] == [[0, 0, size, size]]
    # Keep the opaque dark disc, but no oversized halo clipped by the canvas.
    assert drawing["circles"][0] == [center, center, radius]
    assert all(
        math.hypot(x - center, y - center) + r <= radius + 1e-10
        for x, y, r in drawing["circles"]
    )
    area = 0.0
    if clips:
        vertices = clips[-1]
        area = (
            abs(
                sum(
                    x1 * y2 - x2 * y1
                    for (x1, y1), (x2, y2) in zip(vertices, vertices[1:] + vertices[:1])
                )
            )
            / 2
        )
        if angle in (90, 270):
            assert all(abs(point[0] - center) < 1e-10 for point in vertices[97:])
    assert area / (math.pi * radius**2) == pytest.approx(
        (1 - math.cos(math.radians(angle))) / 2, abs=0.0002
    )
    assert app is QCoreApplication.instance()
