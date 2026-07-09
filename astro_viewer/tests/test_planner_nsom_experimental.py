from __future__ import annotations

from copy import deepcopy
from inspect import signature
from pathlib import Path
from unittest.mock import patch

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    NsomTargetClass,
    ObservableTargetValue,
    ObservationOpportunity,
    ObserverCapability,
    PracticalTargetValue,
    RecommendationConfidence,
    SessionViability,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionFeatureFlags,
)
from astro_viewer.app.services.night_planner_service import (
    NSOM_PLANNER_SCORING_ENABLED,
    NightPlannerService,
)
from astro_viewer.app.services.planner_nsom_service import (
    NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED,
    PlannerNsomScoringService,
)
from astro_viewer.app.services.planner_scoring_service import PlannerScoringService


def test_legacy_planner_constructor_rollback_is_removed() -> None:
    objects = _planner_fixture_objects()
    weather = _weather(85)
    scores = _scores()
    sky_quality = _sky_quality(3)
    telescope = _telescope()
    moon = _moon(10)

    assert NSOM_PLANNER_SCORING_ENABLED is True
    assert "use_nsom_planner_scoring" not in signature(NightPlannerService.__init__).parameters
    plan = NightPlannerService().plan(
        objects,
        weather,
        scores,
        sky_quality,
        telescope,
        moon,
    )

    assert plan


def test_default_planner_path_uses_observation_opportunity_ranking() -> None:
    objects = [
        _target("legacy-high", "Galaxy", 100, "Facile", "21:00", "4.0"),
        _target("nsom-a", "Galaxy", 60, "Facile", "21:15", "4.0"),
        _target("nsom-b", "Galaxy", 55, "Facile", "21:30", "4.0"),
        _target("nsom-c", "Galaxy", 50, "Facile", "21:45", "4.0"),
        _target("nsom-d", "Galaxy", 45, "Facile", "22:00", "4.0"),
        _target("nsom-e", "Galaxy", 40, "Facile", "22:15", "4.0"),
        _target("nsom-f", "Galaxy", 35, "Facile", "22:30", "4.0"),
    ]
    nsom_service = FixedNsomOpportunityService(
        {
            "legacy-high": 1.0,
            "nsom-a": 96.0,
            "nsom-b": 91.0,
            "nsom-c": 86.0,
            "nsom-d": 81.0,
            "nsom-e": 76.0,
            "nsom-f": 71.0,
        }
    )

    plan = NightPlannerService(nsom_scoring_service=nsom_service).plan(
        objects,
        _weather(85),
        _scores(),
        _sky_quality(3),
        _telescope(),
        _moon(10),
    )

    planned_scores = {item.object_id: item.score for item in plan}

    assert nsom_service.calls == [item.id for item in objects]
    assert "legacy-high" not in planned_scores
    assert planned_scores == {
        "nsom-a": 96,
        "nsom-b": 91,
        "nsom-c": 86,
        "nsom-d": 81,
        "nsom-e": 76,
        "nsom-f": 71,
    }


def test_night_planner_forwards_moon_geometry_to_nsom_service_when_supplied() -> None:
    objects = [
        _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5"),
        _target("cluster", "Open Cluster", 76, "Facile", "22:00", "5.0"),
    ]
    geometry = _close_moon_geometry()
    nsom_service = RecordingMoonGeometryNsomService()

    NightPlannerService(nsom_scoring_service=nsom_service).plan(
        objects,
        _weather(85),
        _scores(),
        _sky_quality(3),
        _telescope(),
        _moon(70),
        moon_geometry_by_object_id={"galaxy": geometry},
    )

    assert nsom_service.received_moon_geometry["galaxy"] is geometry
    assert nsom_service.received_moon_geometry["cluster"] is None


def test_planner_nsom_service_builds_full_observation_opportunity_from_candidate() -> None:
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    service = PlannerNsomScoringService()

    opportunity = service.opportunity(
        target,
        weather=_weather(85),
        scores=_scores(deep_sky=70),
        sky_quality=_sky_quality(8, radiance=20),
        telescope=_telescope(),
        moon=_moon(95),
        blocking_status=NightPlannerService.weather_blocking_status(_weather(85)),
        observing_window_quality=0.9,
        chronology_fit=0.8,
    )

    observable = opportunity.practical_target_value.observable_target_value

    assert isinstance(opportunity, ObservationOpportunity)
    assert observable.intrinsic_target is not None
    assert observable.intrinsic_target.object_id == "galaxy"
    assert observable.effective_observability.environment is not None
    assert "nsom:planner_experimental" in observable.effective_observability.environment.notes
    assert opportunity.practical_target_value.observer_capability is not None
    assert opportunity.session.state == "usable"
    assert opportunity.confidence is not None
    assert opportunity.confidence.viirs_confidence == 1.0
    assert opportunity.context == ("planner", "nsom_experimental")
    assert opportunity.value == pytest.approx(service.score(opportunity))


def test_moon_geometry_scoring_is_default_on_for_planner_and_changes_lunar_background() -> None:
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    service = PlannerNsomScoringService()
    geometry = _close_moon_geometry()

    without_geometry = service.effective_observability(
        target,
        scores=_scores(deep_sky=90),
        sky_quality=_sky_quality(3, radiance=1),
        moon=_moon(95),
    )
    with_geometry = service.effective_observability(
        target,
        scores=_scores(deep_sky=90),
        sky_quality=_sky_quality(3, radiance=1),
        moon=_moon(95),
        moon_geometry=geometry,
    )

    assert NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED is True
    assert ObservationConditionFeatureFlags().experimental_moon_geometry_scoring is False
    assert service.uses_moon_geometry_scoring is True
    assert NightPlannerService().uses_moon_geometry_scoring is True
    assert with_geometry.value < without_geometry.value
    assert with_geometry.lunar_sky_background < without_geometry.lunar_sky_background
    assert with_geometry.static_sky_background == pytest.approx(without_geometry.static_sky_background)
    assert with_geometry.atmospheric_transparency == pytest.approx(without_geometry.atmospheric_transparency)
    assert with_geometry.horizon_context == pytest.approx(without_geometry.horizon_context)
    assert "moon_geometry_scoring_enabled=True" in with_geometry.notes


def test_moon_geometry_scoring_can_be_forced_off_for_planner_rollback() -> None:
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    service = PlannerNsomScoringService(
        feature_flags=ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=False)
    )
    planner = NightPlannerService(nsom_scoring_service=service)
    geometry = _close_moon_geometry()

    without_geometry = service.effective_observability(
        target,
        scores=_scores(deep_sky=90),
        sky_quality=_sky_quality(3, radiance=1),
        moon=_moon(95),
    )
    with_geometry = service.effective_observability(
        target,
        scores=_scores(deep_sky=90),
        sky_quality=_sky_quality(3, radiance=1),
        moon=_moon(95),
        moon_geometry=geometry,
    )

    assert service.uses_moon_geometry_scoring is False
    assert planner.uses_moon_geometry_scoring is False
    assert with_geometry.value == pytest.approx(without_geometry.value)
    assert with_geometry.lunar_sky_background == pytest.approx(without_geometry.lunar_sky_background)
    assert "moon_geometry_scoring_enabled=False" in with_geometry.notes


def test_moon_geometry_scoring_flag_modifies_planner_lunar_sky_background_only() -> None:
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    service = PlannerNsomScoringService(
        feature_flags=ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=True)
    )

    close_geometry = _close_moon_geometry()
    far_geometry = MoonGeometryConditionInput(
        moon_altitude_deg=55.0,
        moon_target_separation_deg=125.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
        moon_set_before_target_window=False,
    )
    close = service.effective_observability(
        target,
        scores=_scores(deep_sky=90),
        sky_quality=_sky_quality(3, radiance=1),
        moon=_moon(70),
        moon_geometry=close_geometry,
    )
    far = service.effective_observability(
        target,
        scores=_scores(deep_sky=90),
        sky_quality=_sky_quality(3, radiance=1),
        moon=_moon(70),
        moon_geometry=far_geometry,
    )

    assert service.uses_moon_geometry_scoring is True
    assert close.geometric_visibility == pytest.approx(far.geometric_visibility)
    assert close.static_sky_background == pytest.approx(far.static_sky_background)
    assert close.atmospheric_transparency == pytest.approx(far.atmospheric_transparency)
    assert close.horizon_context == pytest.approx(far.horizon_context)
    assert close.lunar_sky_background < far.lunar_sky_background
    assert close.value < far.value
    assert "moon_geometry_scoring_enabled=True" in close.notes
    assert "moon_geometry_input=available" in close.notes


def test_moon_geometry_scoring_protects_planets_from_lunar_background_penalty() -> None:
    service = PlannerNsomScoringService(
        feature_flags=ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=True)
    )
    planet = _target("planet", "Pianeta", 82, "Facile", "21:00", "-1.0")

    no_geometry = service.effective_observability(
        planet,
        scores=_scores(planetary=90),
        sky_quality=_sky_quality(3, radiance=1),
        moon=_moon(95),
    )
    close_geometry = service.effective_observability(
        planet,
        scores=_scores(planetary=90),
        sky_quality=_sky_quality(3, radiance=1),
        moon=_moon(95),
        moon_geometry=_close_moon_geometry(),
    )

    assert no_geometry.lunar_sky_background == pytest.approx(1.0)
    assert close_geometry.lunar_sky_background == pytest.approx(1.0)
    assert close_geometry.value == pytest.approx(no_geometry.value)


def test_moon_geometry_scoring_changes_observable_and_confidence_metadata_not_observer_session() -> None:
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    service = PlannerNsomScoringService(
        feature_flags=ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=True)
    )
    weather = _weather(85)
    sky_quality = _sky_quality(3, radiance=1)
    telescope = _telescope()

    baseline = service.opportunity(
        target,
        weather=weather,
        scores=_scores(deep_sky=90),
        sky_quality=sky_quality,
        telescope=telescope,
        moon=_moon(70),
        blocking_status=NightPlannerService.weather_blocking_status(weather),
    )
    close_geometry = service.opportunity(
        target,
        weather=weather,
        scores=_scores(deep_sky=90),
        sky_quality=sky_quality,
        telescope=telescope,
        moon=_moon(70),
        moon_geometry=_close_moon_geometry(),
        blocking_status=NightPlannerService.weather_blocking_status(weather),
    )

    baseline_practical = baseline.practical_target_value
    close_practical = close_geometry.practical_target_value

    assert baseline_practical.observable_target_value.intrinsic_target == close_practical.observable_target_value.intrinsic_target
    assert baseline_practical.observer_capability == close_practical.observer_capability
    assert baseline.session == close_geometry.session
    assert baseline.confidence is not None
    assert close_geometry.confidence is not None
    assert baseline.confidence.weather_confidence == close_geometry.confidence.weather_confidence
    assert baseline.confidence.viirs_confidence == close_geometry.confidence.viirs_confidence
    assert baseline.confidence.provider_fallback_confidence == close_geometry.confidence.provider_fallback_confidence
    assert baseline.confidence.moon_geometry_confidence is None
    assert close_geometry.confidence.moon_geometry_confidence == pytest.approx(1.0)
    assert close_geometry.value == pytest.approx(
        close_practical.value
        * close_geometry.observing_window_quality
        * close_geometry.chronology_fit
        * close_geometry.session.value
        * close_geometry.practical_constraints
    )
    assert baseline_practical.observable_target_value.effective_observability.lunar_sky_background > (
        close_practical.observable_target_value.effective_observability.lunar_sky_background
    )
    assert baseline_practical.observable_target_value.value > close_practical.observable_target_value.value
    assert baseline.value > close_geometry.value


def test_nsom_planner_does_not_use_legacy_condition_breakdown(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_condition_breakdown(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        raise AssertionError("NSOM Planner should own its environment adaptation")

    monkeypatch.setattr(PlannerScoringService, "condition_breakdown", fail_condition_breakdown)
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")

    opportunity = PlannerNsomScoringService().opportunity(
        target,
        weather=_weather(85),
        scores=_scores(deep_sky=70),
        sky_quality=_sky_quality(8, radiance=20),
        telescope=_telescope(),
        moon=_moon(95),
        blocking_status=NightPlannerService.weather_blocking_status(_weather(85)),
    )

    assert opportunity.practical_target_value.observable_target_value.effective_observability.environment is not None


def test_nsom_planner_score_matches_observation_opportunity_formula() -> None:
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=80.0,
        effective_observability=EffectiveObservability.from_components(),
    )
    practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=ObserverCapability(),
        capability_summary=0.7,
    )
    opportunity = ObservationOpportunity(
        practical_target_value=practical,
        observing_window_quality=0.8,
        chronology_fit=0.75,
        session=SessionViability.from_components(value=0.5),
        practical_constraints=0.6,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )

    expected = practical.value * 0.8 * 0.75 * 0.5 * 0.6

    assert PlannerNsomScoringService.score(opportunity) == pytest.approx(expected)


def test_observer_equipment_changes_practical_value_without_changing_observable() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=80.0,
        effective_observability=EffectiveObservability.from_components(),
    )

    small_scope_practical = service.practical_target_value_from_observable(
        observable,
        target,
        telescope=_telescope(name="Small Scope", aperture_mm=60, focal_length_mm=400, mount="manual"),
    )
    large_scope_practical = service.practical_target_value_from_observable(
        observable,
        target,
        telescope=_telescope(name="Large GoTo Scope", aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
    )

    assert small_scope_practical.observable_target_value is observable
    assert large_scope_practical.observable_target_value is observable
    assert observable.value == pytest.approx(80.0)
    assert large_scope_practical.value > small_scope_practical.value


def test_planner_nsom_uses_q_target_projection_for_practical_value() -> None:
    service = PlannerNsomScoringService()
    galaxy_target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    open_cluster_target = _target("open-cluster", "Open Cluster", 82, "Facile", "21:00", "5.0")
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=80.0,
        effective_observability=EffectiveObservability.from_components(),
        target_class=NsomTargetClass.GALAXY,
    )
    telescope = _telescope(aperture_mm=127, focal_length_mm=1500, mount="manual")

    galaxy_practical = service.practical_target_value_from_observable(
        observable,
        galaxy_target,
        telescope=telescope,
    )
    open_cluster_observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=80.0,
        effective_observability=EffectiveObservability.from_components(),
        target_class=NsomTargetClass.OPEN_CLUSTER,
    )
    open_cluster_practical = service.practical_target_value_from_observable(
        open_cluster_observable,
        open_cluster_target,
        telescope=telescope,
    )
    observer = galaxy_practical.observer_capability

    assert galaxy_practical.observer_capability_summary == pytest.approx(
        project_observer_capability_for_target(observer, NsomTargetClass.GALAXY)
    )
    assert open_cluster_practical.observer_capability_summary == pytest.approx(
        project_observer_capability_for_target(observer, NsomTargetClass.OPEN_CLUSTER)
    )
    assert galaxy_practical.observer_capability_summary != pytest.approx(
        open_cluster_practical.observer_capability_summary
    )
    assert galaxy_practical.observable_target_value.value == pytest.approx(
        open_cluster_practical.observable_target_value.value
    )


def test_confidence_does_not_affect_nsom_planner_score() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    practical = service.practical_target_value(
        target,
        scores=_scores(),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
    )

    low_confidence = RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0)
    high_confidence = RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0)
    low_opportunity = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(85),
        sky_quality=_sky_quality(3),
        moon=_moon(10),
        confidence=low_confidence,
    )
    high_opportunity = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(85),
        sky_quality=_sky_quality(3),
        moon=_moon(10),
        confidence=high_confidence,
    )

    assert low_confidence.value < high_confidence.value
    assert service.score(low_opportunity) == service.score(high_opportunity)


def test_changing_confidence_alone_does_not_change_nsom_planner_formula_score() -> None:
    practical = _practical_value(70.0)
    low_confidence = ObservationOpportunity(
        practical_target_value=practical,
        observing_window_quality=0.9,
        chronology_fit=0.8,
        session=SessionViability.from_components(value=0.7),
        practical_constraints=0.6,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high_confidence = ObservationOpportunity(
        practical_target_value=practical,
        observing_window_quality=0.9,
        chronology_fit=0.8,
        session=SessionViability.from_components(value=0.7),
        practical_constraints=0.6,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    assert low_confidence.confidence is not None
    assert high_confidence.confidence is not None
    assert low_confidence.confidence.value < high_confidence.confidence.value
    assert PlannerNsomScoringService.score(low_confidence) == PlannerNsomScoringService.score(high_confidence)


def test_session_viability_changes_opportunity_without_mutating_target_values() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    practical = service.practical_target_value(
        target,
        scores=_scores(),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
    )
    observable = practical.observable_target_value
    practical_before = deepcopy(practical)

    poor_session = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(35),
        sky_quality=_sky_quality(3),
        moon=_moon(10),
    )
    good_session = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(85),
        sky_quality=_sky_quality(3),
        moon=_moon(10),
    )

    assert poor_session.session.value < good_session.session.value
    assert poor_session.value < good_session.value
    assert practical == practical_before
    assert practical.observable_target_value is observable
    assert observable.value == practical_before.observable_target_value.value


def test_planner_nsom_does_not_rebuild_observer_capability_from_existing_practical_value() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    practical = service.practical_target_value(
        target,
        scores=_scores(),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
    )

    with patch(
        "astro_viewer.app.services.observer_capability_adapter.build_observer_capability_profile_from_recommendation",
        side_effect=AssertionError("observer capability should already be part of PracticalTargetValue"),
    ):
        opportunity = service.opportunity_from_practical_target_value(
            target,
            practical,
            weather=_weather(85),
            sky_quality=_sky_quality(3),
            moon=_moon(10),
        )

    assert opportunity.practical_target_value is practical


def test_nsom_planner_does_not_mutate_nsom_dtos() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5")
    practical = service.practical_target_value(
        target,
        scores=_scores(),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
    )
    before = deepcopy(practical)

    opportunity = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(85),
        sky_quality=_sky_quality(3),
        moon=_moon(10),
    )

    assert practical == before
    assert opportunity.practical_target_value is practical


def test_nsom_planner_has_no_qml_exposure() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))

    assert "use_nsom_planner_scoring" not in qml_text
    assert "NSOM_PLANNER_SCORING_ENABLED" not in qml_text
    assert "nsom_planner" not in qml_text.lower()
    assert "experimental_moon_geometry_scoring" not in qml_text
    assert "moon_geometry" not in qml_text.lower()


class FixedNsomOpportunityService:
    def __init__(self, values: dict[str, float]) -> None:
        self._values = values
        self.calls: list[str] = []

    def opportunity(self, item, **kwargs) -> ObservationOpportunity:  # noqa: ANN001, ANN003
        del kwargs
        self.calls.append(item.id)
        return _opportunity(self._values[item.id])

    @staticmethod
    def score(opportunity: ObservationOpportunity) -> float:
        return opportunity.value


class RecordingMoonGeometryNsomService:
    uses_moon_geometry_scoring = True

    def __init__(self) -> None:
        self.received_moon_geometry: dict[str, MoonGeometryConditionInput | None] = {}

    def opportunity(self, item, **kwargs) -> ObservationOpportunity:  # noqa: ANN001, ANN003
        self.received_moon_geometry[item.id] = kwargs.get("moon_geometry")
        return _opportunity(50.0)

    @staticmethod
    def score(opportunity: ObservationOpportunity) -> float:
        return opportunity.value


def _opportunity(value: float) -> ObservationOpportunity:
    practical = _practical_value(value)
    return ObservationOpportunity(
        practical_target_value=practical,
        session=SessionViability.from_components(value=1.0),
    )


def _practical_value(value: float) -> PracticalTargetValue:
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=value,
        effective_observability=EffectiveObservability.from_components(),
    )
    practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=ObserverCapability(),
        capability_summary=1.0,
    )
    return practical


def _target(
    object_id: str,
    object_type: str,
    score: float,
    difficulty: str,
    best_time: str,
    magnitude: str,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.title(),
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time=best_time,
        observing_window=f"{best_time} - 02:00",
        notes="Fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=round(score),
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type="telescope",
    )


def _planner_fixture_objects() -> list[CelestialObject]:
    return [
        _target("galaxy", "Galaxy", 82, "Media", "21:00", "8.5"),
        _target("cluster", "Open Cluster", 76, "Facile", "22:00", "5.0"),
        _target("planet", "Pianeta", 79, "Facile", "23:00", "-1.0"),
        _target("nebula", "Nebula", 78, "Media", "00:30", "7.0"),
    ]


def _weather(score: int) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=10,
        precipitation_probability=0,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _scores(planetary: float = 85, deep_sky: float = 88) -> AdvancedObservingScores:
    return AdvancedObservingScores(
        planetary_score=planetary,
        deep_sky_score=deep_sky,
        planetary_label="Good",
        deep_sky_label="Good",
        explanation="Fixture",
    )


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="Fixture",
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


def _close_moon_geometry() -> MoonGeometryConditionInput:
    return MoonGeometryConditionInput(
        moon_altitude_deg=55.0,
        moon_target_separation_deg=12.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
        moon_set_before_target_window=False,
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


def _plan_summary(plan):
    return [(item.object_id, item.score, item.time_label) for item in plan]
