from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.best_object_nsom_ranking import (
    NSOM_BEST_OBJECT_ENABLED,
    BestObjectNsomSelectionService,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_best_object_nsom_flag_is_default_on() -> None:
    assert NSOM_BEST_OBJECT_ENABLED is True
    assert AppController.__init__.__kwdefaults__["use_nsom_best_object"] is NSOM_BEST_OBJECT_ENABLED


def test_best_object_nsom_service_ranks_by_observation_opportunity() -> None:
    targets = _targets()

    service = BestObjectNsomSelectionService()
    ranked = service.ranked_candidates(
        targets,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
    )

    assert ranked[0].target.id == "galaxy"
    assert service.best_object(
        targets,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
    ).id == "galaxy"
    assert ObservingScoreService().best_object(targets, _weather(90)).id == "jupiter"
    assert ranked[0].opportunity.context == ("best_object", "nsom_runtime")
    assert ranked[0].opportunity.value == pytest.approx(ranked[0].score)


def test_best_object_nsom_score_formula_uses_practical_value_and_session_only() -> None:
    service = BestObjectNsomSelectionService()

    candidate = service.ranked_candidates(
        [_target("galaxy", "Galaxy", 90, difficulty="Media")],
        weather=_weather(73),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
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
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
    )[0]

    notes = candidate.practical_target_value.observer_capability.notes
    assert "nsom:best_object_observer_capability" in notes
    assert "nsom:planner_observer_capability" not in notes


def test_best_object_nsom_blocked_session_is_non_actionable_with_preserved_order() -> None:
    targets = _targets()

    service = BestObjectNsomSelectionService()
    ranked = service.ranked_candidates(
        targets,
        weather=_weather(10, cloud_cover=95, precipitation_probability=80),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
    )

    assert service.best_object(
        targets,
        weather=_weather(10, cloud_cover=95, precipitation_probability=80),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
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
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
    )

    hidden = next(candidate for candidate in ranked if candidate.target.id == "hidden_galaxy")
    assert hidden.actionability == "non_actionable_invisible_target"
    assert service.best_object(
        targets,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
    ).id == "open_cluster"


def test_best_object_nsom_confidence_is_score_neutral() -> None:
    targets = _targets()
    service = BestObjectNsomSelectionService()

    low = service.ranked_candidates(
        targets,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = service.ranked_candidates(
        targets,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    assert [candidate.target.id for candidate in low] == [candidate.target.id for candidate in high]
    assert [candidate.score for candidate in low] == pytest.approx([candidate.score for candidate in high])
    assert low[0].opportunity.confidence.value < high[0].opportunity.confidence.value


def test_best_object_nsom_does_not_mutate_runtime_objects() -> None:
    targets = _targets()
    before = deepcopy(targets)

    BestObjectNsomSelectionService().best_object(
        targets,
        weather=_weather(90),
        sky_quality=_sky_quality(8, radiance=45.0),
        telescope=_telescope(aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
        moon=_moon(85),
    )

    assert targets == before


def test_app_controller_forced_legacy_rollback_preserves_best_object_order() -> None:
    controller = _controller(use_nsom_best_object=False)

    selected = controller._select_best_object(_targets())

    assert selected.id == "jupiter"


def test_app_controller_default_flag_uses_nsom_best_object_path() -> None:
    controller = _controller(use_nsom_best_object=NSOM_BEST_OBJECT_ENABLED)

    selected = controller._select_best_object(_targets())

    assert selected.id == "galaxy"


def test_app_controller_forced_nsom_path_selects_nsom_best_object() -> None:
    controller = _controller(use_nsom_best_object=True)

    selected = controller._select_best_object(_targets())

    assert selected.id == "galaxy"


def test_app_controller_forced_nsom_path_falls_back_without_sky_quality() -> None:
    controller = _controller(use_nsom_best_object=True)
    controller._sky_quality = None

    selected = controller._select_best_object(_targets())

    assert selected.id == "jupiter"


def test_app_controller_forced_nsom_blocked_session_returns_no_best_object() -> None:
    controller = _controller(use_nsom_best_object=True)
    controller._weather_summary = _weather(10, cloud_cover=95, precipitation_probability=80)

    selected = controller._select_best_object(_targets())

    assert selected is None


def test_app_controller_recalculate_outputs_uses_forced_nsom_best_object_path() -> None:
    controller = _controller(use_nsom_best_object=True)
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
    controller._advanced_observing_service = Mock()
    controller._advanced_observing_service.scores.return_value = AdvancedObservingScores(
        planetary_score=80,
        deep_sky_score=80,
        planetary_label="Fixture",
        deep_sky_label="Fixture",
        explanation="Fixture",
    )
    controller._night_planner_service = Mock()
    controller._night_planner_service.plan.return_value = []
    controller._refresh_sky_compass = Mock()
    controller._events = []
    controller._refresh_nsom_diagnostics = Mock()

    controller._recalculate_observing_outputs()

    assert controller._best_object.id == "galaxy"
    assert AppController.bestObjectOfNight.fget(controller)["id"] == "galaxy"
    controller._night_planner_service.plan.assert_called_once()
    controller._refresh_sky_compass.assert_called_once()
    controller._refresh_nsom_diagnostics.assert_called_once()


def test_best_object_qml_payload_shape_stays_legacy_compatible() -> None:
    controller = _controller(use_nsom_best_object=True)
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


def _controller(*, use_nsom_best_object: bool) -> AppController:
    controller = AppController.__new__(AppController)
    controller._use_nsom_best_object = use_nsom_best_object
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
    controller._observing_status = lambda _item: ("", "")
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
