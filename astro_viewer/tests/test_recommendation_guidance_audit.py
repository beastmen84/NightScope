"""Regressions for hourly planning, comet intervals and honest estimate display."""

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch
from zoneinfo import ZoneInfo

import numpy as np
import pytest

from astro_viewer.app.astronomy.comet_windows import CometWindowEventSource, _NightWindow, _PreparedComets
from astro_viewer.app.astronomy.engine import ObservingNightWindow, advance_time, as_utc
from astro_viewer.app.models.sky import ObservingCategoryScores
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.home_observing_overview import _deep_sky_payload, _moon_payload, _planetary_payload
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.observing_night_service import usable_weather_intervals
from astro_viewer.app.services.seeing_service import BasicForecastSeeingProvider, MeteoblueSeeingProviderPlaceholder
from astro_viewer.tests.test_planner_nsom_service import _inputs, _target, _telescope, _weather


START = datetime(2030, 9, 19, 20, tzinfo=UTC)
NIGHT = ObservingNightWindow.bounded(START, START + timedelta(hours=10))


def hour(instant, cloud=0, **kwargs):
    return WeatherHour(instant.isoformat(), instant.strftime("%H:%M"), cloud, 0, 5, 50, 15, **kwargs)


def target(object_id="galaxy", *, best=1, start=0, end=10):
    return replace(_target(object_id), night_eligible=True,
                   best_observing_at=(START + timedelta(hours=best)).isoformat(),
                   observing_start_at=(START + timedelta(hours=start)).isoformat(),
                   observing_end_at=(START + timedelta(hours=end)).isoformat())


def plan(targets, hours):
    return NightPlannerService().plan(targets, _weather(89), _telescope("scope"),
                                     condition_inputs=_inputs(), night_window=NIGHT, weather_hours=hours)


def test_plan_avoids_cloudy_peak_despite_good_nightly_average_without_mutating_inputs():
    value = target()
    before = asdict(value)
    hours = tuple(hour(START + timedelta(hours=i), 100 if i < 2 else 0) for i in range(10))
    result = plan([value], hours)
    assert len(result) == 1
    assert result[0].observing_at == (START + timedelta(hours=2)).isoformat()
    assert asdict(value) == before
    assert result[0].score == plan([value], None)[0].score  # Canonical NSOM unchanged.


@pytest.mark.parametrize("best", [0, 1, 2, 5, 9, 9.75])
def test_fully_usable_forecast_preserves_complete_legacy_plan(best):
    values = [target(best=best)]
    hours = [hour(START + timedelta(hours=i)) for i in range(10)]
    assert plan(values, hours) == plan(values, None)


@pytest.mark.parametrize("hours", [[], [hour(START, 100)], [replace(hour(START), timestamp="invalid")]])
def test_empty_bad_or_undated_forecast_never_creates_a_plan(hours):
    assert plan([target()], hours) == []


def test_targets_without_weather_overlap_do_not_consume_the_four_slots():
    values = [target(f"bad-{i}", end=2) for i in range(5)] + [target(f"good-{i}", start=3) for i in range(4)]
    result = plan(values, [hour(START + timedelta(hours=3))])
    assert {item.object_id for item in result} == {f"good-{i}" for i in range(4)}


def test_missing_hours_and_duplicate_conflicts_are_not_bridged():
    hours = [hour(START), hour(START + timedelta(hours=2)), hour(START + timedelta(hours=3))]
    assert usable_weather_intervals(hours, NIGHT) == ((START, START + timedelta(hours=1)),
                                                    (START + timedelta(hours=2), START + timedelta(hours=4)))
    hours.append(hour(START + timedelta(hours=2), 100))
    assert usable_weather_intervals(list(reversed(hours)), NIGHT) == (
        (START, START + timedelta(hours=1)), (START + timedelta(hours=3), START + timedelta(hours=4)),
    )


def test_partial_forecast_bin_is_clipped_at_start_and_next_bad_row():
    night = ObservingNightWindow.bounded(START + timedelta(minutes=15), START + timedelta(hours=2))
    assert usable_weather_intervals([hour(START), hour(START + timedelta(minutes=30), 100)], night) == (
        (START + timedelta(minutes=15), START + timedelta(minutes=30)),
    )


def test_nearest_earlier_minute_stays_before_exclusive_bad_weather_boundary():
    result = plan([target(best=2)], [hour(START), hour(START + timedelta(hours=1), 100)])
    assert result[0].observing_at == (START + timedelta(minutes=45)).isoformat()
    assert plan([target(start=1, best=1)], [hour(START)]) == []


@pytest.mark.parametrize("changes", [{"cloud_cover": -1}, {"cloud_cover": float("nan")},
                                     {"humidity": 101}, {"wind_kmh": float("inf")},
                                     {"precipitation_probability": None}])
def test_invalid_forecast_values_are_not_usable(changes):
    assert usable_weather_intervals([replace(hour(START), **changes)], NIGHT) == ()


@pytest.mark.parametrize("month,day", [(10, 25), (3, 29)])
def test_dst_offset_free_ambiguous_or_nonexistent_hours_are_not_invented(month, day):
    zone = ZoneInfo("Europe/Rome")
    start = datetime(2026, month, day, 1, tzinfo=zone)
    night = ObservingNightWindow.bounded(start, start.replace(hour=5))
    ambiguous = datetime(2026, month, day, 2)
    assert usable_weather_intervals([hour(ambiguous)], night) == ()
    # Explicit offsets remain unambiguous elapsed-hour bins across the fold.
    rows = [hour(advance_time(start, timedelta(hours=i))) for i in range(4)]
    result = usable_weather_intervals(rows, night)
    assert result == ((as_utc(start), min(as_utc(start) + timedelta(hours=4), as_utc(night.end))),)


def comet_context(altitudes):
    count = len(altitudes)
    times = [START + timedelta(minutes=30 * i) for i in range(count)]
    apparent = Mock()
    apparent.altaz.return_value = (SimpleNamespace(degrees=altitudes), None, SimpleNamespace(au=np.ones(count)))
    apparent.separation_from.return_value = SimpleNamespace(degrees=np.full(count, 80.))
    observer = Mock()
    observer.observe.return_value.apparent.return_value = apparent
    comet = MagicMock()
    (comet - "sun").at.return_value.distance.return_value = SimpleNamespace(au=np.ones(count))
    context = dict(times=None, observer_at=observer, sun="sun", sun_apparent="sun", moon_apparent="moon",
                   moon_illumination=np.full(count, .1), sun_altitudes=np.full(count, -20.),
                   moon_altitudes=np.full(count, -10.), datetimes=times, local_datetimes=times, end=times[-1])
    return comet, context


@pytest.mark.parametrize("altitudes,minutes", [([20.1, 20.1, 10, 0], 0),
                                             ([30, 35, 30, 10], 60), ([30, 35, 30], 60),
                                             ([30, 10, 30, 35], 0)])
def test_comet_window_ends_at_last_verified_sample(altitudes, minutes):
    comet, context = comet_context(altitudes)
    with patch("astro_viewer.app.astronomy.comet_windows._predicted_magnitude", return_value=np.full(len(altitudes), 8.)):
        windows = CometWindowEventSource(None)._night_windows(comet, None, context=context)
    if minutes:
        assert len(windows) == 1
        assert windows[0].duration == timedelta(minutes=minutes)
        assert windows[0].end == START + timedelta(minutes=minutes)
    else:
        assert windows == []


def test_comet_retains_nearby_short_group_and_anchors_instant_facts_to_it():
    source = CometWindowEventSource(None)
    record = SimpleNamespace(spk_id="123", designation="Test comet")
    prepared = _PreparedComets((record,), SimpleNamespace(fetched_at=START.isoformat()), "fresh")
    windows = [_NightWindow((START + timedelta(days=day)).date(), START + timedelta(days=day),
                           START + timedelta(days=day, hours=2), START + timedelta(days=day, hours=1),
                           8 + day / 10, 30 + day, 60 + day, 70 + day, .2 + day / 100)
               for day in (0, 1, 10, 11, 12)]
    with patch.object(source, "_sampling_context", return_value={}), \
            patch("astro_viewer.app.astronomy.comet_windows._comet_vector"), \
            patch.object(source, "_passes_coarse_magnitude_filter", return_value=True), \
            patch.object(source, "_night_windows", return_value=windows):
        events = source.build_events(None, now=START, timescale=Mock(), ephemeris={"sun": None, "earth": None},
                                     prepared_data=prepared)
    assert len(events) == 1
    result = events[0]
    assert result.starts_at == windows[0].start.isoformat()
    assert result.favorable_periods == ((windows[0].start.isoformat(), windows[1].end.isoformat()),
                                        (windows[2].start.isoformat(), windows[4].end.isoformat()))
    facts = {key: str(value) for key, _, value in result.event_facts}
    assert facts["useful_nights"] == "5"
    assert facts["solar_elongation"] == "60°"
    assert facts["moon_separation"] == "70°"
    assert facts["moon_illumination"] == "20%"
    assert "21:00" in facts["geometry_reference"]
    assert "20:00" in facts["next_window"] and "22:00" in facts["next_window"]
    assert result.peak_at == windows[-1].peak.isoformat()  # No longer the display reference.
    assert facts["predicted_magnitude"] == "circa 8-10"


@pytest.mark.parametrize("provider", [BasicForecastSeeingProvider, MeteoblueSeeingProviderPlaceholder])
@pytest.mark.parametrize("hours", [[], [hour(START, seeing_inputs_complete=False)]])
def test_unknown_seeing_is_not_a_discreet_forecast_but_keeps_numeric_compatibility(provider, hours):
    value = provider().estimate(hours, None)
    assert not value.available
    assert value.seeing_score == value.transparency_score == 50
    qml = value.to_qml()
    assert qml["seeing"] == qml["transparency"] == qml["atmosphericTransparency"] == "n/d"
    assert qml["seeingScore"] is qml["transparencyScore"] is None
    inputs = _inputs()
    scores = ObservingCategoryScores(50, 50, "Discreta", "Discreta", "")
    planetary = _planetary_payload(value, scores, "debole", "nsom")
    assert planetary["state"] == "unavailable" and planetary["scoreValue"] is None
    assert planetary["primaryMetric"] == "Seeing non disponibile"
    deep_sky = _deep_sky_payload(value, inputs.sky_quality, scores, "nsom")
    assert deep_sky["state"] == "partial" and deep_sky["scoreValue"] is None
    assert deep_sky["primaryMetric"] == "Trasparenza n/d"
    assert "solo buio del sito" in deep_sky["hint"]


def test_available_seeing_and_optical_nsom_calculations_are_unchanged_by_display_metadata():
    value = BasicForecastSeeingProvider().estimate([hour(START)], None)
    assert value.available and value.to_qml()["seeingScore"] == value.seeing_score
    planner = NightPlannerService()
    kwargs = dict(night_window=NIGHT, weather_hours=[hour(START + timedelta(hours=i)) for i in range(10)])
    known = planner.plan([target()], _weather(89), _telescope("scope"),
                         condition_inputs=replace(_inputs(), seeing=value), **kwargs)
    hidden = planner.plan([target()], _weather(89), _telescope("scope"),
                          condition_inputs=replace(_inputs(), seeing=replace(value, available=False)), **kwargs)
    assert known == hidden


def test_bright_moon_does_not_claim_actual_all_night_interference_from_phase_alone():
    result = _moon_payload(_inputs(moon=95).moon)
    assert result["impactLabel"] == "Disturbo potenziale elevato"
    assert "se sopra l'orizzonte" in result["summary"]
    assert "bersaglio" in result["summary"]


@pytest.mark.parametrize("illumination", ["NaN%", "-1%", "101%", "n/d"])
def test_invalid_moon_illumination_is_not_a_low_impact_claim(illumination):
    assert _moon_payload(replace(_inputs().moon, illumination=illumination))["impact"] == "unavailable"


def test_no_atmosphere_or_site_data_is_unavailable_not_a_partial_diagnosis():
    scores = ObservingCategoryScores(50, 50, "Discreta", "Discreta", "")
    result = _deep_sky_payload(BasicForecastSeeingProvider().estimate([], None), None, scores, "nsom")
    assert result["state"] == "unavailable" and result["label"] == "n/d"
    assert result["scoreValue"] is None


@pytest.mark.parametrize("legacy", [False, True])
def test_target_expiring_during_scoring_does_not_receive_a_fabricated_weather_time(legacy):
    clock = SimpleNamespace(now=START)

    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.now.astimezone(tz)

    value = _target("legacy") if legacy else target(end=1, best=.5)
    planner = NightPlannerService()

    def scoring(*args, **kwargs):
        clock.now = START + timedelta(hours=7)
        return [(value, 80)]

    with patch("astro_viewer.app.services.night_planner_service.datetime", FrozenDatetime), \
            patch.object(planner, "_scored_visible", side_effect=scoring):
        assert planner.plan([value], _weather(89), _telescope("scope"), condition_inputs=_inputs(),
                            night_window=NIGHT, weather_hours=[hour(START), hour(START + timedelta(hours=1))]) == []
