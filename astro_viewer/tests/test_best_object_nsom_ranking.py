from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from inspect import signature
from pathlib import Path
from unittest.mock import Mock

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.best_object_nsom_ranking import BestObjectNsomSelectionService
from astro_viewer.app.services.observation_conditions_read_model import ObservationConditionsReadModelBuilder
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionInputs,
)
from astro_viewer.app.services.nsom_category_score_service import NsomCategoryScoreService
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_best_object_has_no_legacy_rollback_parameter() -> None:
    assert "use_nsom_best_object" not in signature(AppController.__init__).parameters


def test_best_object_nsom_service_ranks_by_observation_opportunity() -> None:
    targets = _targets()

    service = BestObjectNsomSelectionService()
    ranked = service.ranked_candidates(
        targets,
        weather=_weather(90),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
    )

    assert ranked[0].target.id == "galaxy"
    assert service.best_object(
        targets,
        weather=_weather(90),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
    ).id == "galaxy"
    assert ranked[0].opportunity.context == ("best_object", "nsom_runtime")
    assert ranked[0].opportunity.value == pytest.approx(ranked[0].score)


def test_best_object_scores_each_target_id_once() -> None:
    first = _target("galaxy", "Galaxy", 80)
    duplicate = replace(first, id=" GALAXY ", name="Duplicate", score=100)

    ranked = BestObjectNsomSelectionService().ranked_candidates(
        [first, duplicate],
        weather=_weather(90),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
    )

    assert [candidate.target for candidate in ranked] == [first]


def test_best_object_nsom_score_formula_uses_practical_value_and_session_only() -> None:
    service = BestObjectNsomSelectionService()

    candidate = service.ranked_candidates(
        [_target("galaxy", "Galaxy", 90, difficulty="Media")],
        weather=_weather(73),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
    )[0]

    opportunity = candidate.opportunity
    assert opportunity.observing_window_quality == 1.0
    assert opportunity.chronology_fit == 1.0
    assert opportunity.practical_constraints == 1.0
    assert candidate.score == pytest.approx(
        candidate.practical_target_value.value * opportunity.session.value
    )


def test_best_object_nsom_observer_capability_uses_best_object_context() -> None:
    service = BestObjectNsomSelectionService()

    candidate = service.ranked_candidates(
        [_target("galaxy", "Galaxy", 90, difficulty="Media")],
        weather=_weather(90),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
    )[0]

    notes = candidate.practical_target_value.observer_capability.notes
    assert "nsom:best_object_observer_capability" in notes
    assert "nsom:planner_observer_capability" not in notes


def test_best_object_uses_target_specific_telescope_mapping() -> None:
    targets = [
        _target("galaxy", "Galaxy", 90, difficulty="Media"),
        _target("jupiter", "Pianeta", 86, difficulty="Facile", magnitude="-2.1"),
    ]
    fallback = _telescope()
    wide_field = Telescope("wide", "Wide Field", 100, 500, "Refractor", "Alt-az")
    planetary = Telescope("planetary", "Planetary", 220, 2200, "Reflector", "GoTo EQ")

    ranked = BestObjectNsomSelectionService().ranked_candidates(
        targets,
        weather=_weather(90),
        telescope=fallback,
        condition_inputs=_inputs(3, moon=10),
        telescope_by_object_id={"galaxy": wide_field, "jupiter": planetary},
    )
    by_id = {candidate.target.id: candidate for candidate in ranked}

    assert "telescope=Wide Field" in by_id["galaxy"].practical_target_value.observer_capability.notes
    assert "telescope=Planetary" in by_id["jupiter"].practical_target_value.observer_capability.notes


def test_best_object_nsom_blocked_session_is_non_actionable_with_preserved_order() -> None:
    targets = _targets()

    service = BestObjectNsomSelectionService()
    ranked = service.ranked_candidates(
        targets,
        weather=_weather(10, cloud_cover=95, precipitation_probability=80),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
    )

    assert service.best_object(
        targets,
        weather=_weather(10, cloud_cover=95, precipitation_probability=80),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
    ) is None
    assert {candidate.actionability for candidate in ranked} == {"non_actionable_hard_block"}
    assert {candidate.score for candidate in ranked} == {0.0}
    assert [candidate.target.id for candidate in ranked] == [target.id for target in targets]
    assert [candidate.practical_target_value.value for candidate in ranked] != [0.0] * len(ranked)


def test_best_object_nsom_invisible_targets_are_non_actionable() -> None:
    targets = [
        _target("hidden_galaxy", "Galaxy", 100, difficulty="Media", visible=False),
        _target("open_cluster", "Open Cluster", 78, difficulty="Facile", recommended_setup_type="binoculars"),
    ]
    service = BestObjectNsomSelectionService()

    ranked = service.ranked_candidates(
        targets,
        weather=_weather(90),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
    )

    hidden = next(candidate for candidate in ranked if candidate.target.id == "hidden_galaxy")
    assert hidden.actionability == "non_actionable_invisible_target"
    assert service.best_object(
        targets,
        weather=_weather(90),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
    ).id == "open_cluster"


def test_best_object_nsom_confidence_is_score_neutral() -> None:
    targets = _targets()
    service = BestObjectNsomSelectionService()

    low = service.ranked_candidates(
        targets,
        weather=_weather(90),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = service.ranked_candidates(
        targets,
        weather=_weather(90),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=10),
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    assert [candidate.target.id for candidate in low] == [candidate.target.id for candidate in high]
    assert [candidate.score for candidate in low] == pytest.approx([candidate.score for candidate in high])
    assert low[0].opportunity.confidence.value < high[0].opportunity.confidence.value


def test_best_object_confidence_uses_target_specific_moon_geometry() -> None:
    geometry = MoonGeometryConditionInput(moon_set_before_target_window=True)
    ranked = BestObjectNsomSelectionService().ranked_candidates(
        _targets(),
        weather=_weather(90),
        telescope=_telescope(),
        condition_inputs=_inputs(3, moon=70, radiance=1.0),
        moon_geometry_by_object_id={"galaxy": geometry},
    )
    confidence_by_id = {
        candidate.target.id: candidate.opportunity.confidence for candidate in ranked
    }

    assert confidence_by_id["galaxy"] is not None
    assert confidence_by_id["galaxy"].moon_geometry_confidence == 1.0
    assert confidence_by_id["jupiter"] is not None
    assert confidence_by_id["jupiter"].moon_geometry_confidence == 0.0
    assert confidence_by_id["galaxy"].provider_fallback_confidence is None


def test_best_object_nsom_does_not_mutate_runtime_objects() -> None:
    targets = _targets()
    before = deepcopy(targets)

    BestObjectNsomSelectionService().best_object(
        targets,
        weather=_weather(90),
        telescope=_telescope(aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
        condition_inputs=_inputs(8, moon=85, radiance=45.0),
    )

    assert targets == before


def test_app_controller_runtime_uses_canonical_nsom() -> None:
    controller = _controller()

    selected = controller._select_best_object(_targets())

    assert selected.id == "galaxy"

def test_app_controller_nsom_path_scores_raw_read_model_targets_and_returns_display_target() -> None:
    controller = _controller()
    raw_low = _target("raw_low", "Galaxy", 30, difficulty="Media")
    raw_high = _target("raw_high", "Open Cluster", 90, difficulty="Facile")
    display_low = replace(raw_low, score=99, condition_flags=("light_pollution",))
    display_high = replace(raw_high, score=10, condition_flags=("light_pollution",))
    selection = _CapturingBestObjectSelectionService(selected_id="raw_high")
    controller._best_object_nsom_selection_service = selection
    controller._deep_sky_raw_condition_input_by_id = {
        raw_low.id: raw_low,
        raw_high.id: raw_high,
    }
    controller._conditioned_home_read_model = list(
        ObservationConditionsReadModelBuilder().from_display_targets(
            [display_low, display_high],
            source="test_best_object_read_model",
            raw_targets_by_id=controller._deep_sky_raw_condition_input_by_id,
        )
    )

    selected = controller._select_best_object([display_low, display_high])

    assert selection.candidates == [raw_low, raw_high]
    assert selected is display_high
    assert selected.score == 10


def test_app_controller_nsom_path_stays_active_without_sky_quality() -> None:
    controller = _controller()
    controller._sky_quality = None

    selected = controller._select_best_object(_targets())

    assert selected.id == "galaxy"


def test_app_controller_nsom_blocked_session_returns_no_best_object() -> None:
    controller = _controller()
    controller._weather_summary = _weather(10, cloud_cover=95, precipitation_probability=80)

    selected = controller._select_best_object(_targets())

    assert selected is None


def test_app_controller_recalculate_outputs_uses_nsom_best_object_path() -> None:
    controller = _controller()
    controller._visible_planets = [_targets()[0]]
    controller._deep_sky = _targets()[1:]
    controller._home_visible_objects = lambda objects: list(objects)
    controller._refresh_conditioned_observing_candidates = Mock()
    controller._weather_hours = []
    controller._seeing_service = Mock()
    controller._seeing_service.estimate.return_value = SeeingTransparency(
        "Good",
        "Good",
        80,
        80,
        "Fixture",
    )
    controller._nsom_category_score_service = NsomCategoryScoreService()
    controller._night_planner_service = Mock()
    controller._night_planner_service.plan.return_value = []
    controller._refresh_sky_compass = Mock()
    controller._events = []

    controller._recalculate_observing_outputs()

    controller._seeing_service.estimate.assert_not_called()
    assert controller._best_object.id == "galaxy"
    assert AppController.bestObjectOfNight.fget(controller)["id"] == "galaxy"
    controller._night_planner_service.plan.assert_called_once()
    controller._refresh_sky_compass.assert_called_once()


def test_best_object_qml_payload_keeps_public_contract() -> None:
    controller = _controller()
    selected = controller._select_best_object(_targets())
    controller._best_object = selected

    payload = AppController.bestObjectOfNight.fget(controller)

    assert payload["id"] == "galaxy"
    assert "score" in payload
    assert "scoreLabel" in payload
    assert "type" in payload
    assert "observableTargetValue" not in payload
    assert "practicalTargetValue" not in payload
    assert "observationOpportunity" not in payload
    assert "recommendationConfidence" not in payload


def test_best_object_nsom_runtime_path_has_no_qml_or_report_wiring() -> None:
    app_controller = (Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )
    ranking_service = (
        Path(__file__).parents[1] / "app" / "services" / "best_object_nsom_ranking.py"
    ).read_text(encoding="utf-8")
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).parents[1] / "app" / "ui").rglob("*.qml")
    )

    assert "BEST_OBJECT_NSOM_COMPARISON_REPORT" not in app_controller
    assert "BEST_OBJECT_NSOM_READINESS_AUDIT" not in app_controller
    assert "NSOM_BEST_OBJECT_ENABLED" not in qml_text
    assert "BestObjectNsomSelectionService" not in qml_text
    assert "best_object_nsom" not in qml_text
    assert "PlannerNsomScoringService" not in ranking_service
    assert "nsom:planner_observer_capability" not in ranking_service


def _controller() -> AppController:
    controller = AppController.__new__(AppController)
    controller._best_object_nsom_selection_service = BestObjectNsomSelectionService()
    controller._score_service = ObservingScoreService()
    controller._weather_summary = _weather(90)
    controller._sky_quality = _sky_quality(3)
    controller._moon = _moon(10)
    controller._current_telescope = lambda: _telescope()
    controller._object_descriptions = {}
    controller._is_catalogue_detail_object = lambda _item: False
    controller._home_time_label = lambda item: item.best_time
    controller._home_window_label = lambda item: item.observing_window
    controller._observing_status_data = lambda _item: ("", "", "")
    controller._observing_reasons = lambda _item: []
    controller._setup_reason = lambda _item: ""
    return controller


def _targets() -> list[CelestialObject]:
    return [
        _target("jupiter", "Pianeta", 86, difficulty="Facile", magnitude="-2.1"),
        _target("open_cluster", "Open Cluster", 78, difficulty="Facile", recommended_setup_type="binoculars"),
        _target("galaxy", "Galaxy", 90, difficulty="Media"),
        _target("diffuse_nebula", "Nebula diffusa", 88, difficulty="Media"),
    ]


def _target(
    object_id: str,
    object_type: str,
    score: int,
    *,
    magnitude: str = "8.0",
    difficulty: str = "Media",
    recommended_setup_type: str = "telescope",
    visible: bool = True,
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
        best_time="21:00",
        observing_window="21:00 - 02:00",
        notes="Fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=visible,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type=recommended_setup_type,
    )


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
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
        rise_time="20:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
    )


def _inputs(
    bortle: int | None,
    *,
    moon: int,
    radiance: float | None = None,
) -> ObservationConditionInputs:
    return ObservationConditionInputs(
        moon=_moon(moon),
        sky_quality=_sky_quality(bortle, radiance) if bortle is not None else None,
    )


def _telescope(
    *,
    aperture_mm: int = 127,
    focal_length_mm: int = 1500,
    mount: str = "manual",
) -> Telescope:
    return Telescope(
        id="test-scope",
        name="Test Scope",
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Reflector",
        mount=mount,
    )


class _CapturingBestObjectSelectionService:
    def __init__(self, *, selected_id: str) -> None:
        self.selected_id = selected_id
        self.candidates: list[CelestialObject] = []

    def best_object(
        self,
        candidates: list[CelestialObject],
        *,
        weather: WeatherSummary,
        telescope: Telescope,
        condition_inputs: ObservationConditionInputs,
        **_kwargs: object,
    ) -> CelestialObject | None:
        del weather, telescope, condition_inputs
        self.candidates = list(candidates)
        return next((item for item in self.candidates if item.id == self.selected_id), None)
