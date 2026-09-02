"""Protect NSOM planner scoring, selection limits, blocking, and time ordering."""

from __future__ import annotations

from copy import deepcopy

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionInputs,
    ParticulateConditionInput,
)
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService


def test_planner_selects_four_highest_opportunities_then_orders_by_time() -> None:
    targets = [
        _target("display-high", score=100, best_time="20:30"),
        _target("a", score=60, best_time="23:00"),
        _target("b", score=55, best_time="21:00"),
        _target("c", score=50, best_time="22:00"),
        _target("d", score=45, best_time="00:30"),
    ]
    scoring = _FixedOpportunityService(
        {"display-high": 1.0, "a": 96.0, "b": 91.0, "c": 86.0, "d": 81.0}
    )

    plan = NightPlannerService(nsom_scoring_service=scoring).plan(
        targets,
        _weather(85),
        _telescope("fallback"),
        condition_inputs=_inputs(),
    )

    assert [item.object_id for item in plan] == ["b", "c", "a", "d"]
    assert {item.object_id: item.score for item in plan} == {
        "a": 96,
        "b": 91,
        "c": 86,
        "d": 81,
    }


def test_planner_scores_each_target_id_once() -> None:
    scoring = _FixedOpportunityService({"same": 80.0})

    plan = NightPlannerService(nsom_scoring_service=scoring).plan(
        [_target("same"), _target("same")],
        _weather(85),
        _telescope("fallback"),
        condition_inputs=_inputs(),
    )

    assert [item.object_id for item in plan] == ["same"]
    assert scoring.calls == ["same"]


def test_planner_forwards_target_telescope_and_moon_geometry() -> None:
    targets = [_target("galaxy"), _target("planet", object_type="Pianeta")]
    geometry = MoonGeometryConditionInput(
        moon_altitude_deg=50.0,
        moon_target_separation_deg=12.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
    )
    scoring = _RecordingOpportunityService()

    NightPlannerService(nsom_scoring_service=scoring).plan(
        targets,
        _weather(85),
        _telescope("fallback"),
        condition_inputs=_inputs(),
        telescope_by_object_id={
            "galaxy": _telescope("deep"),
            "planet": _telescope("planetary"),
        },
        moon_geometry_by_object_id={"galaxy": geometry},
    )

    assert scoring.telescopes == {"galaxy": "deep", "planet": "planetary"}
    assert scoring.geometry == {"galaxy": geometry, "planet": None}


def test_planner_opportunity_uses_canonical_environment() -> None:
    target = _target("galaxy", score=82)
    service = PlannerNsomScoringService()

    opportunity = service.opportunity(
        target,
        weather=_weather(85),
        telescope=_telescope("scope"),
        condition_inputs=_inputs(moon=95, bortle=8, radiance=20.0),
        observing_window_quality=0.9,
        chronology_fit=0.8,
    )

    environment = opportunity.practical_target_value.observable_target_value.effective_observability.environment
    assert environment is not None
    assert "nsom:canonical_observation_environment" in environment.notes
    assert opportunity.context == ("planner", "nsom_runtime")
    assert opportunity.value == pytest.approx(service.score(opportunity))


def test_moon_geometry_changes_only_lunar_sky_component() -> None:
    target = _target("galaxy", score=82)
    service = PlannerNsomScoringService()
    inputs = _inputs(moon=95)
    geometry = MoonGeometryConditionInput(
        moon_altitude_deg=55.0,
        moon_target_separation_deg=10.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
    )

    baseline = service.effective_observability(target, condition_inputs=inputs)
    close = service.effective_observability(
        target,
        condition_inputs=inputs,
        moon_geometry=geometry,
    )

    assert close.lunar_sky_background < baseline.lunar_sky_background
    assert close.static_sky_background == baseline.static_sky_background
    assert close.atmospheric_transparency == baseline.atmospheric_transparency
    assert close.horizon_context == baseline.horizon_context


def test_session_is_binary_and_confidence_is_score_neutral() -> None:
    target = _target("galaxy", score=82)
    service = PlannerNsomScoringService()
    practical = service.practical_target_value(
        target,
        telescope=_telescope("scope"),
        condition_inputs=_inputs(),
    )
    low_confidence = RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0)
    high_confidence = RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0)

    low = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(85),
        condition_inputs=_inputs(),
        confidence=low_confidence,
    )
    high = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(85),
        condition_inputs=_inputs(),
        confidence=high_confidence,
    )
    blocked = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(20),
        condition_inputs=_inputs(),
    )

    assert low.value == high.value
    assert low.confidence is not None and high.confidence is not None
    assert low.confidence.value < high.confidence.value
    assert blocked.session.value == 0.0
    assert blocked.value == 0.0


def test_planner_confidence_counts_each_runtime_source_once() -> None:
    inputs = _inputs(moon=70, radiance=None)
    inputs = ObservationConditionInputs(
        moon=inputs.moon,
        sky_quality=inputs.sky_quality,
        seeing=inputs.seeing,
        particulate=ParticulateConditionInput(
            available=True,
            freshness_category="current",
            pm25=7.0,
            source="OpenAQ",
        ),
    )

    opportunity = PlannerNsomScoringService().opportunity(
        _target("galaxy"),
        weather=_weather(85),
        telescope=_telescope("scope"),
        condition_inputs=inputs,
    )

    confidence = opportunity.confidence
    assert confidence is not None
    assert confidence.openaq_confidence == 1.0
    assert confidence.viirs_confidence == 0.0
    assert confidence.provider_fallback_confidence is None
    assert confidence.moon_geometry_confidence == 0.0


def test_planner_does_not_mutate_target_or_condition_inputs() -> None:
    target = _target("galaxy", score=82)
    inputs = _inputs(moon=70)
    before_target = deepcopy(target)
    before_inputs = deepcopy(inputs)

    PlannerNsomScoringService().opportunity(
        target,
        weather=_weather(85),
        telescope=_telescope("scope"),
        condition_inputs=inputs,
    )

    assert target == before_target
    assert inputs == before_inputs


class _FixedOpportunityService:
    def __init__(self, scores: dict[str, float]) -> None:
        self._scores = scores
        self.calls: list[str] = []

    def opportunity(self, item: CelestialObject, **_kwargs):
        self.calls.append(item.id)
        return self._scores[item.id]

    @staticmethod
    def score(opportunity: float) -> float:
        return opportunity


class _RecordingOpportunityService(_FixedOpportunityService):
    def __init__(self) -> None:
        super().__init__({"galaxy": 80.0, "planet": 80.0})
        self.telescopes: dict[str, str] = {}
        self.geometry: dict[str, MoonGeometryConditionInput | None] = {}

    def opportunity(
        self,
        item: CelestialObject,
        *,
        telescope: Telescope,
        moon_geometry: MoonGeometryConditionInput | None,
        **_kwargs,
    ) -> float:
        self.telescopes[item.id] = telescope.id
        self.geometry[item.id] = moon_geometry
        return self._scores[item.id]


def _target(
    object_id: str,
    *,
    object_type: str = "Galaxy",
    score: int = 80,
    best_time: str = "21:00",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.title(),
        object_type=object_type,
        image="",
        magnitude="8.0",
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time=best_time,
        observing_window=f"{best_time} - 02:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        intrinsic_score=score,
        difficulty="Media",
    )


def _inputs(
    *,
    moon: int = 10,
    bortle: int = 3,
    radiance: float | None = 1.0,
) -> ObservationConditionInputs:
    return ObservationConditionInputs(
        moon=MoonSummary("Fixture", f"{moon}%", "", "", "", ""),
        sky_quality=SkyQuality(
            bortle_class=bortle,
            limiting_magnitude=6.0,
            sky_brightness=21.0,
            source="Fixture",
            description="",
            viirs_radiance=radiance,
        ),
        seeing=SeeingTransparency(
            "Good",
            "Good",
            82,
            76,
            "",
            atmospheric_transparency_score=80,
        ),
    )


def _weather(score: int) -> WeatherSummary:
    return WeatherSummary("Fixture", score, "", 10, 0, 5, 50, 12.0, "")


def _telescope(telescope_id: str) -> Telescope:
    return Telescope(telescope_id, telescope_id.title(), 127, 1500, "Reflector", "GoTo")
