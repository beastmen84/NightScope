from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    ObservableTargetValue,
    ObservationOpportunity,
    ObserverCapability,
    PracticalTargetValue,
    RecommendationConfidence,
    SessionViability,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.night_planner_service import (
    NSOM_PLANNER_SCORING_ENABLED,
    NightPlannerService,
)
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService


def test_nsom_planner_feature_flag_is_default_off_and_preserves_legacy_output() -> None:
    class FailingNsomService:
        def opportunity(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("NSOM planner path should stay disabled.")

        def score(self, opportunity: ObservationOpportunity) -> float:
            raise AssertionError("NSOM planner path should stay disabled.")

    objects = _planner_fixture_objects()
    weather = _weather(85)
    scores = _scores()
    sky_quality = _sky_quality(3)
    telescope = _telescope()
    moon = _moon(10)

    assert NSOM_PLANNER_SCORING_ENABLED is False
    legacy_plan = NightPlannerService().plan(objects, weather, scores, sky_quality, telescope, moon)
    flag_off_plan = NightPlannerService(nsom_scoring_service=FailingNsomService()).plan(
        objects,
        weather,
        scores,
        sky_quality,
        telescope,
        moon,
    )

    assert _plan_summary(flag_off_plan) == _plan_summary(legacy_plan)


def test_nsom_planner_feature_flag_uses_observation_opportunity_ranking() -> None:
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

    plan = NightPlannerService(
        use_nsom_planner_scoring=True,
        nsom_scoring_service=nsom_service,
    ).plan(
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
        "astro_viewer.app.services.planner_nsom_service.build_observer_capability_profile_from_recommendation",
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


def _opportunity(value: float) -> ObservationOpportunity:
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=value,
        effective_observability=EffectiveObservability.from_components(),
    )
    practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=ObserverCapability(),
        capability_summary=1.0,
    )
    return ObservationOpportunity(
        practical_target_value=practical,
        session=SessionViability.from_components(value=1.0),
    )


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


def _telescope() -> Telescope:
    return Telescope(
        id="test-scope",
        name="Test Scope",
        aperture_mm=127,
        focal_length_mm=1500,
        optical_type="Mak",
        mount="",
    )


def _plan_summary(plan):
    return [(item.object_id, item.score, item.time_label) for item in plan]
