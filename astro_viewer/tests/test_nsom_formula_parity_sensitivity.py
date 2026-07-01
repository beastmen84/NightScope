from __future__ import annotations

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import ObservableTargetValue, RecommendationConfidence
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_diagnostic_adapters import build_session_viability
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService
from astro_viewer.tools.nsom_mathematical_trace_report import generate_trace_report_data


REPRESENTATIVE_FORMULA_SCENARIOS = (
    "G03:galaxy",
    "G06:galaxy",
    "G14:planet",
    "G16:galaxy",
    "G19:galaxy",
    "G20:galaxy",
    "G09:galaxy",
)


def test_report_expanded_sub_formulas_match_reported_values_for_edge_scenarios() -> None:
    data = generate_trace_report_data()

    for scenario_id in REPRESENTATIVE_FORMULA_SCENARIOS:
        row = _scenario(data, scenario_id)
        for stage_name in ("ObservationEnvironment", "ObservationWindow", "SessionViability", "ObserverCapability"):
            stage = _stage(row, stage_name)
            for formula in stage["sub_formulas"]:
                if formula["status"] != "available":
                    assert formula["matches_reported_output"] is None
                    continue
                assert formula["matches_reported_output"] is True, (scenario_id, stage_name, formula["component"])
                assert formula["output"] == pytest.approx(formula["expected_output"])


@pytest.mark.parametrize(
    "scenario_id",
    ("G03:galaxy", "G06:galaxy", "G14:planet", "G16:galaxy", "G20:galaxy"),
)
def test_environment_formula_outputs_match_planner_nsom_service(scenario_id: str) -> None:
    row = _scenario(generate_trace_report_data(), scenario_id)
    target = _target_from_row(row)
    effective = PlannerNsomScoringService().effective_observability(
        target,
        scores=_scores_from_row(row),
        sky_quality=_sky_quality_from_row(row),
        moon=_moon_from_row(row),
    )
    environment = _stage(row, "ObservationEnvironment")
    formulas = _sub_formulas(environment)

    assert formulas["geometric_visibility"]["output"] == pytest.approx(effective.geometric_visibility)
    assert formulas["moon_background"]["output"] == pytest.approx(effective.lunar_sky_background)
    assert formulas["sky_background"]["output"] == pytest.approx(effective.static_sky_background)
    assert formulas["atmospheric_transparency"]["output"] == pytest.approx(effective.atmospheric_transparency)
    assert formulas["horizon_context"]["output"] == pytest.approx(effective.horizon_context)


@pytest.mark.parametrize("scenario_id", ("G01:galaxy", "G19:galaxy", "G20:galaxy"))
def test_observing_window_formula_matches_planner_runtime_helper(scenario_id: str) -> None:
    row = _scenario(generate_trace_report_data(), scenario_id)
    target = _target_from_row(row)
    formula = _sub_formulas(_stage(row, "ObservationWindow"))["observing_window_quality"]

    assert formula["output"] == pytest.approx(NightPlannerService._observing_window_quality(target))
    assert formula["matches_reported_output"] is True


@pytest.mark.parametrize("scenario_id", ("G01:galaxy", "G08:galaxy", "G09:galaxy"))
def test_session_viability_formula_matches_runtime_adapter(scenario_id: str) -> None:
    row = _scenario(generate_trace_report_data(), scenario_id)
    weather = _weather_from_row(row)
    blocking_status = NightPlannerService.weather_blocking_status(weather)
    session = build_session_viability(weather_summary=weather, blocking_status=blocking_status)
    stage = _stage(row, "SessionViability")
    formulas = _sub_formulas(stage)

    assert formulas["weather_suitability"]["output"] == pytest.approx(session.weather_suitability)
    assert formulas["blocking_factor"]["output"] == pytest.approx(session.blocking_factor)
    assert formulas["session_viability"]["output"] == pytest.approx(session.value)
    assert all(formula["matches_reported_output"] is True for formula in formulas.values())


def test_observer_capability_sub_formulas_mark_adapter_derived_dimensions() -> None:
    row = _scenario(generate_trace_report_data(), "G12:galaxy")
    target = _target_from_row(row)
    telescope = _telescope_from_row(row)
    observer = PlannerNsomScoringService().observer_capability(target, telescope=telescope)
    stage = _stage(row, "ObserverCapability")
    formulas = _sub_formulas(stage)

    for name in ("light_grasp", "resolution", "field_of_view", "magnification_range", "tracking_or_goto"):
        assert formulas[name]["status"] == "adapter-derived"
        assert formulas[name]["matches_reported_output"] is None
        assert formulas[name]["output"] == pytest.approx(getattr(observer, name))

    assert formulas["observer_capability_summary"]["status"] == "available"
    assert formulas["observer_capability_summary"]["matches_reported_output"] is True
    assert formulas["observer_capability_summary"]["output"] == pytest.approx(observer.summary_for_planning())
    assert formulas["q_target"]["status"] == "available"
    assert formulas["q_target"]["matches_reported_output"] is True
    assert formulas["q_target"]["output"] == pytest.approx(
        stage["outputs"]["q_target"]
    )


def test_sensitivity_sky_background_changes_effective_and_observable_target_value() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy")
    scores = _scores()
    moon = _moon(10)

    dark = service.effective_observability(target, scores=scores, sky_quality=_sky_quality(2, radiance=1), moon=moon)
    bright = service.effective_observability(target, scores=scores, sky_quality=_sky_quality(9, radiance=140), moon=moon)
    dark_observable = ObservableTargetValue.from_intrinsic(intrinsic_target_quality=80.0, effective_observability=dark)
    bright_observable = ObservableTargetValue.from_intrinsic(intrinsic_target_quality=80.0, effective_observability=bright)

    assert dark.static_sky_background > bright.static_sky_background
    assert dark.value > bright.value
    assert dark_observable.value > bright_observable.value


def test_sensitivity_moon_background_changes_deep_sky_but_not_planet_target() -> None:
    service = PlannerNsomScoringService()
    scores = _scores(planetary=90, deep_sky=90)
    sky_quality = _sky_quality(2, radiance=1)

    galaxy_low_moon = service.effective_observability(_target("galaxy", "Galaxy"), scores=scores, sky_quality=sky_quality, moon=_moon(5))
    galaxy_high_moon = service.effective_observability(_target("galaxy", "Galaxy"), scores=scores, sky_quality=sky_quality, moon=_moon(95))
    planet_low_moon = service.effective_observability(_target("planet", "Pianeta"), scores=scores, sky_quality=sky_quality, moon=_moon(5))
    planet_high_moon = service.effective_observability(_target("planet", "Pianeta"), scores=scores, sky_quality=sky_quality, moon=_moon(95))

    assert galaxy_low_moon.lunar_sky_background > galaxy_high_moon.lunar_sky_background
    assert galaxy_low_moon.value > galaxy_high_moon.value
    assert planet_low_moon.lunar_sky_background == pytest.approx(1.0)
    assert planet_high_moon.lunar_sky_background == pytest.approx(1.0)
    assert planet_low_moon.value == pytest.approx(planet_high_moon.value)


def test_sensitivity_equipment_changes_practical_value_but_not_observable_value() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy")
    effective = service.effective_observability(target, scores=_scores(), sky_quality=_sky_quality(2, radiance=1), moon=_moon(10))
    observable = ObservableTargetValue.from_intrinsic(intrinsic_target_quality=80.0, effective_observability=effective)

    small = service.practical_target_value_from_observable(
        observable,
        target,
        telescope=_telescope(aperture_mm=60, focal_length_mm=400, mount="manual"),
    )
    large = service.practical_target_value_from_observable(
        observable,
        target,
        telescope=_telescope(aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
    )

    assert small.observable_target_value is observable
    assert large.observable_target_value is observable
    assert observable.value == pytest.approx(80.0 * effective.value)
    assert large.observer_capability_summary > small.observer_capability_summary
    assert large.value > small.value


def test_sensitivity_session_viability_lowers_opportunity_only() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy")
    practical = _practical(service, target)
    observable_value = practical.observable_target_value.value
    practical_value = practical.value

    good = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
    )
    poor = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(35),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
    )

    assert poor.session.value < good.session.value
    assert poor.value < good.value
    assert practical.observable_target_value.value == pytest.approx(observable_value)
    assert practical.value == pytest.approx(practical_value)


def test_sensitivity_observing_window_quality_lowers_opportunity_only() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy")
    practical = _practical(service, target)

    full = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
        observing_window_quality=1.0,
    )
    half = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
        observing_window_quality=0.5,
    )
    none = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
        observing_window_quality=0.0,
    )

    assert half.value == pytest.approx(full.value * 0.5)
    assert none.value == pytest.approx(0.0)
    assert half.practical_target_value is practical
    assert none.practical_target_value.observable_target_value.value == pytest.approx(
        full.practical_target_value.observable_target_value.value
    )


def test_sensitivity_horizon_context_lowers_effective_observability() -> None:
    service = PlannerNsomScoringService()
    scores = _scores()
    sky_quality = _sky_quality(2, radiance=1)
    moon = _moon(10)

    high = service.effective_observability(
        _target("galaxy", "Galaxy", max_altitude="45 gradi"),
        scores=scores,
        sky_quality=sky_quality,
        moon=moon,
    )
    low = service.effective_observability(
        _target("galaxy", "Galaxy", max_altitude="15 gradi"),
        scores=scores,
        sky_quality=sky_quality,
        moon=moon,
    )

    assert low.horizon_context < high.horizon_context
    assert low.value < high.value


def test_sensitivity_confidence_does_not_change_opportunity_score() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy")
    practical = _practical(service, target)

    low = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    assert low.confidence is not None
    assert high.confidence is not None
    assert low.confidence.value < high.confidence.value
    assert low.value == pytest.approx(high.value)


def _practical(service: PlannerNsomScoringService, target: CelestialObject):
    return service.practical_target_value(
        target,
        scores=_scores(),
        sky_quality=_sky_quality(2, radiance=1),
        telescope=_telescope(),
        moon=_moon(10),
    )


def _rows(data: dict[str, object]) -> list[dict[str, object]]:
    return [row for group in data["scenario_groups"] for row in group["scenarios"]]


def _scenario(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(row for row in _rows(data) if row["scenario_id"] == scenario_id)


def _stage(row: dict[str, object], stage_name: str) -> dict[str, object]:
    return next(stage for stage in row["pipeline"] if stage["stage"] == stage_name)


def _sub_formulas(stage: dict[str, object]) -> dict[str, dict[str, object]]:
    return {item["component"]: item for item in stage["sub_formulas"]}


def _target_from_row(row: dict[str, object]) -> CelestialObject:
    target = row["target"]
    return _target(
        str(target["object_id"]),
        str(target["object_type"]),
        max_altitude=str(target["max_altitude"]),
        best_time=str(target["best_time"]),
        observing_window=str(target["observing_window"]),
        difficulty=str(target["difficulty"]),
        visible=bool(target["visible"]),
    )


def _scores_from_row(row: dict[str, object]) -> AdvancedObservingScores:
    scores = row["runtime_inputs"]["advanced_scores"]
    return _scores(
        planetary=float(scores["planetary_score"]),
        deep_sky=float(scores["deep_sky_score"]),
    )


def _sky_quality_from_row(row: dict[str, object]) -> SkyQuality:
    sky_quality = row["runtime_inputs"]["sky_quality"]
    return _sky_quality(
        int(sky_quality["bortle_class"]),
        radiance=sky_quality["viirs_radiance"],
        source=str(sky_quality["source"]),
    )


def _moon_from_row(row: dict[str, object]) -> MoonSummary | None:
    moon = row["runtime_inputs"]["moon"]
    illumination = moon["illumination"]
    if illumination is None:
        return None
    return MoonSummary(
        phase=str(moon["phase"]),
        illumination=str(illumination),
        rise_time="18:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
        phase_angle=0.0,
    )


def _weather_from_row(row: dict[str, object]) -> WeatherSummary:
    weather = row["runtime_inputs"]["weather"]
    return _weather(
        int(weather["score_value"]),
        cloud_cover=int(weather["cloud_cover"]),
        precipitation=int(weather["precipitation_probability"]),
    )


def _telescope_from_row(row: dict[str, object]) -> Telescope:
    telescope = row["runtime_inputs"]["telescope"]
    return _telescope(
        name=str(telescope["name"]),
        aperture_mm=int(telescope["aperture_mm"]),
        focal_length_mm=int(telescope["focal_length_mm"]),
        mount=str(telescope["mount"]),
    )


def _target(
    object_id: str,
    object_type: str,
    *,
    score: float = 82,
    max_altitude: str = "45 gradi",
    best_time: str = "21:00",
    observing_window: str | None = None,
    difficulty: str = "Media",
    visible: bool = True,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.title(),
        object_type=object_type,
        image="",
        magnitude="8.5",
        distance="",
        max_altitude=max_altitude,
        direction="Sud",
        best_time=best_time,
        observing_window=observing_window or f"{best_time} - 02:00",
        notes="Fixture",
        recommended_setup="Fixture setup",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=visible,
        score=round(score),
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type="telescope",
    )


def _scores(planetary: float = 85, deep_sky: float = 88) -> AdvancedObservingScores:
    return AdvancedObservingScores(
        planetary_score=planetary,
        deep_sky_score=deep_sky,
        planetary_label="Good",
        deep_sky_label="Good",
        explanation="Fixture",
    )


def _sky_quality(bortle: int, *, radiance: float | None, source: str = "Fixture") -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source=source,
        description="Fixture",
        viirs_radiance=radiance,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="18:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
        phase_angle=0.0,
    )


def _weather(score: int, *, cloud_cover: int = 10, precipitation: int = 0) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _telescope(
    *,
    name: str = "Test Scope",
    aperture_mm: int = 127,
    focal_length_mm: int = 1500,
    mount: str = "",
) -> Telescope:
    return Telescope(
        id="test-scope",
        name=name,
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Mak",
        mount=mount,
    )
