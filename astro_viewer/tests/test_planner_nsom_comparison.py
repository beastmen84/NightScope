from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.night_planner_service import (
    NSOM_PLANNER_SCORING_ENABLED,
    NightPlannerService,
)
from astro_viewer.app.services.planner_nsom_comparison import PlannerNsomComparisonService
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService


def test_comparison_fixture_reports_legacy_and_nsom_rankings_as_strict_json() -> None:
    comparison = _compare(_representative_targets(), sky_quality=_sky_quality(8, radiance=35), moon=_moon(80))

    json.dumps(comparison, allow_nan=False)

    required_ids = {"planet", "galaxy", "diffuse-nebula", "open-cluster", "globular-cluster", "moon"}
    assert {item["object_id"] for item in comparison["items"]} == required_ids
    assert [item["rank"] for item in comparison["rankings"]["legacy"]] == [1, 2, 3, 4, 5, 6]
    assert [item["rank"] for item in comparison["rankings"]["nsom"]] == [1, 2, 3, 4, 5, 6]

    for item in comparison["items"]:
        assert isinstance(item["score_delta"], int | float)
        assert isinstance(item["rank_delta"], int)
        assert abs(item["score_delta"]) < 100.0
        assert abs(item["rank_delta"]) <= 5
        assert item["legacy"]["score"] >= 0.0
        assert 0.0 <= item["nsom"]["score"] <= 100.0
        components = item["nsom"]["components"]
        assert {
            "practical_target_value",
            "observable_target_value",
            "effective_observability",
            "session_viability",
            "observer_capability",
            "recommendation_confidence",
        } <= set(components)


def test_nsom_explanation_is_strict_json_compatible() -> None:
    targets = [
        _target("weak-planet", "Pianeta", 50, magnitude="-0.4", best_time="04:30"),
        _target("strong-galaxy", "Galaxy", 90, magnitude="8.2", best_time="21:00"),
    ]

    comparison = _compare(targets, sky_quality=_sky_quality(9, radiance=120), moon=_moon(95))
    explanation = _explanation(comparison, "strong-galaxy")

    json.dumps(explanation, allow_nan=False)

    assert explanation["target"]["object_id"] == "strong-galaxy"
    assert explanation["final_nsom_opportunity_score"] == pytest.approx(_nsom_score(comparison, "strong-galaxy"))
    assert {
        "practical_target_value",
        "observable_target_value",
        "effective_observability",
        "observer_capability_summary",
        "q_target",
        "flat_observer_capability_summary",
        "q_target_delta_vs_flat",
        "session_viability",
        "observing_window_quality",
        "chronology_fit",
        "practical_constraints",
    } <= set(explanation["score_components"])
    assert {
        "practical_target_value",
        "observable_target_value",
        "effective_observability",
        "observer_capability",
        "observer_capability_summary",
        "session_viability",
        "recommendation_confidence",
    } <= set(explanation["nsom_components"])


def test_strong_moon_and_light_pollution_affect_galaxies_and_nebulae_more_than_planets() -> None:
    targets = [_target("planet", "Pianeta", 82), _target("galaxy", "Galaxy", 82), _target("diffuse-nebula", "Nebula", 82)]
    dark = _compare(targets, sky_quality=_sky_quality(3), moon=_moon(10))
    bright = _compare(targets, sky_quality=_sky_quality(9, radiance=80), moon=_moon(95))

    planet_drop = _effective_value(dark, "planet") - _effective_value(bright, "planet")
    galaxy_drop = _effective_value(dark, "galaxy") - _effective_value(bright, "galaxy")
    nebula_drop = _effective_value(dark, "diffuse-nebula") - _effective_value(bright, "diffuse-nebula")

    assert planet_drop == pytest.approx(0.0)
    assert galaxy_drop > 0.30
    assert nebula_drop > 0.25
    assert galaxy_drop > planet_drop
    assert nebula_drop > planet_drop


def test_bright_sky_explanation_targets_galaxy_and_nebula_degradation_not_planets_or_moon() -> None:
    targets = [
        _target("planet", "Pianeta", 82, magnitude="-1.0"),
        _target("galaxy", "Galaxy", 82, magnitude="8.2"),
        _target("diffuse-nebula", "Nebula", 82, magnitude="7.0"),
        _target("moon", "Luna", 82, magnitude="-12.0"),
    ]

    comparison = _compare(targets, sky_quality=_sky_quality(9, radiance=120), moon=_moon(95))

    for object_id in ("galaxy", "diffuse-nebula"):
        explanation = _explanation(comparison, object_id)
        assert _has_factor(explanation, "sky", "moon_background")
        assert _has_factor(explanation, "sky", "sky_background")

    for object_id in ("planet", "moon"):
        explanation = _explanation(comparison, object_id)
        assert not _has_factor(explanation, "sky", "moon_background")
        assert not _has_factor(explanation, "sky", "sky_background")
        assert _has_factor(
            explanation,
            "sky",
            "moon_background_neutral",
            section="main_positive_factors",
        )
        assert _has_factor(
            explanation,
            "sky",
            "sky_background_neutral",
            section="main_positive_factors",
        )


def test_intentional_rank_divergence_keeps_nsom_model_as_expected_answer() -> None:
    targets = [
        _target("weak-planet", "Pianeta", 50, magnitude="-0.4", best_time="04:30"),
        _target("strong-galaxy", "Galaxy", 90, magnitude="8.2", best_time="21:00"),
    ]

    comparison = _compare(targets, sky_quality=_sky_quality(9, radiance=120), moon=_moon(95))

    legacy_ranking = [item["object_id"] for item in comparison["rankings"]["legacy"]]
    nsom_ranking = [item["object_id"] for item in comparison["rankings"]["nsom"]]

    assert nsom_ranking[0] == "strong-galaxy"
    assert legacy_ranking != nsom_ranking
    assert _component(comparison, "weak-planet", "effective_observability")["lunar_sky_background"] == pytest.approx(1.0)
    assert _component(comparison, "weak-planet", "effective_observability")["static_sky_background"] == pytest.approx(1.0)
    assert _component(comparison, "strong-galaxy", "effective_observability")["value"] < _component(
        comparison,
        "weak-planet",
        "effective_observability",
    )["value"]
    assert _component(comparison, "strong-galaxy", "practical_target_value")["value"] < _component(
        comparison,
        "weak-planet",
        "practical_target_value",
    )["value"]
    assert _nsom_score(comparison, "strong-galaxy") > _nsom_score(comparison, "weak-planet")


def test_diffuse_nebula_loses_to_planet_under_bright_sky_by_nsom_components() -> None:
    targets = [
        _target("planet", "Pianeta", 82, magnitude="-1.0"),
        _target("diffuse-nebula", "Nebula", 82, magnitude="7.0"),
    ]

    comparison = _compare(targets, sky_quality=_sky_quality(9, radiance=120), moon=_moon(95))

    assert _component(comparison, "planet", "effective_observability")["value"] == pytest.approx(0.85)
    assert _component(comparison, "diffuse-nebula", "effective_observability")["value"] < _component(
        comparison,
        "planet",
        "effective_observability",
    )["value"]
    assert _nsom_score(comparison, "planet") > _nsom_score(comparison, "diffuse-nebula")


def test_clusters_are_present_and_less_sky_sensitive_than_galaxies() -> None:
    targets = [
        _target("galaxy", "Galaxy", 82),
        _target("open-cluster", "Open Cluster", 82),
        _target("globular-cluster", "Globular Cluster", 82),
    ]
    dark = _compare(targets, sky_quality=_sky_quality(3), moon=_moon(10))
    bright = _compare(targets, sky_quality=_sky_quality(9, radiance=80), moon=_moon(95))

    galaxy_drop = _effective_value(dark, "galaxy") - _effective_value(bright, "galaxy")
    open_cluster_drop = _effective_value(dark, "open-cluster") - _effective_value(bright, "open-cluster")
    globular_cluster_drop = _effective_value(dark, "globular-cluster") - _effective_value(bright, "globular-cluster")

    assert 0.0 < open_cluster_drop < galaxy_drop
    assert 0.0 < globular_cluster_drop < galaxy_drop


def test_moon_target_is_not_penalized_by_moon_or_light_pollution_components() -> None:
    target = _target("moon", "Luna", 82)
    dark = _compare([target], sky_quality=_sky_quality(3), moon=_moon(10))
    bright = _compare([target], sky_quality=_sky_quality(9, radiance=80), moon=_moon(95))

    assert _effective_value(bright, "moon") == pytest.approx(_effective_value(dark, "moon"))
    assert _component(bright, "moon", "effective_observability")["lunar_sky_background"] == pytest.approx(1.0)
    assert _component(bright, "moon", "effective_observability")["static_sky_background"] == pytest.approx(1.0)


def test_poor_session_viability_lowers_opportunity_without_mutating_target_values() -> None:
    target = _target("galaxy", "Galaxy", 82)
    good = _compare([target], weather=_weather(85), sky_quality=_sky_quality(3), moon=_moon(10))
    poor = _compare([target], weather=_weather(20), sky_quality=_sky_quality(3), moon=_moon(10))

    assert _component(poor, "galaxy", "session_viability")["value"] < _component(good, "galaxy", "session_viability")["value"]
    assert _nsom_score(poor, "galaxy") < _nsom_score(good, "galaxy")
    assert _component(poor, "galaxy", "observable_target_value")["value"] == pytest.approx(
        _component(good, "galaxy", "observable_target_value")["value"]
    )
    assert _component(poor, "galaxy", "practical_target_value")["value"] == pytest.approx(
        _component(good, "galaxy", "practical_target_value")["value"]
    )


def test_poor_session_explanation_accounts_for_session_reduction_without_target_mutation() -> None:
    target = _target("galaxy", "Galaxy", 82)
    good = _compare([target], weather=_weather(85), sky_quality=_sky_quality(3), moon=_moon(10))
    poor = _compare([target], weather=_weather(20), sky_quality=_sky_quality(3), moon=_moon(10))
    poor_explanation = _explanation(poor, "galaxy")

    assert _has_factor(poor_explanation, "session", "session_viability")
    assert _has_factor(poor_explanation, "session", "weather_suitability")
    assert not _has_factor(poor_explanation, "confidence", "confidence")
    assert _component(poor, "galaxy", "observable_target_value")["value"] == pytest.approx(
        _component(good, "galaxy", "observable_target_value")["value"]
    )
    assert _component(poor, "galaxy", "practical_target_value")["value"] == pytest.approx(
        _component(good, "galaxy", "practical_target_value")["value"]
    )
    assert _nsom_score(poor, "galaxy") < _nsom_score(good, "galaxy")


def test_equipment_changes_practical_value_but_not_observable_value() -> None:
    target = _target("galaxy", "Galaxy", 82)
    small = _compare(
        [target],
        telescope=_telescope(name="Small Manual", aperture_mm=60, focal_length_mm=400, mount="manual"),
    )
    large = _compare(
        [target],
        telescope=_telescope(name="Large GoTo", aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
    )

    assert _component(small, "galaxy", "observable_target_value")["value"] == pytest.approx(
        _component(large, "galaxy", "observable_target_value")["value"]
    )
    assert _component(large, "galaxy", "practical_target_value")["value"] > _component(
        small,
        "galaxy",
        "practical_target_value",
    )["value"]


def test_equipment_explanation_accounts_for_practical_target_value_change() -> None:
    target = _target("galaxy", "Galaxy", 82)
    small = _compare(
        [target],
        telescope=_telescope(name="Small Manual", aperture_mm=60, focal_length_mm=400, mount="manual"),
    )
    large = _compare(
        [target],
        telescope=_telescope(name="Large GoTo", aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
    )
    small_explanation = _explanation(small, "galaxy")
    large_explanation = _explanation(large, "galaxy")

    assert _component(small, "galaxy", "observable_target_value")["value"] == pytest.approx(
        _component(large, "galaxy", "observable_target_value")["value"]
    )
    assert _component(large, "galaxy", "practical_target_value")["value"] > _component(
        small,
        "galaxy",
        "practical_target_value",
    )["value"]
    assert small_explanation["score_components"]["q_target"] < large_explanation["score_components"]["q_target"]
    assert small_explanation["score_components"]["observer_capability_summary"] == pytest.approx(
        small_explanation["score_components"]["q_target"]
    )
    assert "target_class_weighting_profile" in small_explanation["nsom_components"]["observer_capability"]
    assert _has_factor(small_explanation, "observer", "q_target")


def test_confidence_does_not_change_nsom_planner_score() -> None:
    target = _target("galaxy", "Galaxy", 82)
    service = PlannerNsomScoringService()
    opportunity = service.opportunity(
        target,
        weather=_weather(85),
        scores=_scores(),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
        blocking_status=NightPlannerService.weather_blocking_status(_weather(85)),
    )

    low_confidence = replace(
        opportunity,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high_confidence = replace(
        opportunity,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    assert low_confidence.confidence is not None
    assert high_confidence.confidence is not None
    assert low_confidence.confidence.value < high_confidence.confidence.value
    assert service.score(low_confidence) == pytest.approx(service.score(high_confidence))


def test_confidence_explanation_is_trust_metadata_not_score_reduction() -> None:
    target = _target("galaxy", "Galaxy", 82)
    service = PlannerNsomScoringService()
    opportunity = service.opportunity(
        target,
        weather=_weather(85),
        scores=_scores(),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(10),
        blocking_status=NightPlannerService.weather_blocking_status(_weather(85)),
    )
    low_confidence = replace(
        opportunity,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high_confidence = replace(
        opportunity,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    low_explanation = service.explain_opportunity(target, low_confidence)
    high_explanation = service.explain_opportunity(target, high_confidence)

    assert low_explanation["final_nsom_opportunity_score"] == pytest.approx(
        high_explanation["final_nsom_opportunity_score"]
    )
    assert low_explanation["confidence_explanation"]["role"] == "metadata_only"
    assert low_explanation["confidence_explanation"]["score_effect"] == pytest.approx(0.0)
    assert low_explanation["confidence_explanation"]["score_factor"] is False
    assert low_explanation["confidence_explanation"]["value"] < high_explanation["confidence_explanation"]["value"]
    assert not _has_owner(low_explanation, "confidence", section="main_limiting_factors")
    assert not _has_owner(low_explanation, "confidence", section="main_positive_factors")


def test_flag_off_runtime_planner_remains_unchanged_with_explanation_service_present() -> None:
    class FailingNsomService:
        def opportunity(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("NSOM planner path should stay disabled.")

        def score(self, opportunity):  # noqa: ANN001
            raise AssertionError("NSOM planner path should stay disabled.")

        def explain_opportunity(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("NSOM explanations should stay off the runtime Planner path.")

    objects = _representative_targets()
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


def test_comparison_helper_is_not_exposed_to_qml() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))

    assert NSOM_PLANNER_SCORING_ENABLED is False
    assert "PlannerNsomComparisonService" not in qml_text
    assert "planner_nsom_comparison" not in qml_text


def _compare(
    targets: list[CelestialObject],
    *,
    weather: WeatherSummary | None = None,
    scores: AdvancedObservingScores | None = None,
    sky_quality: SkyQuality | None = None,
    telescope: Telescope | None = None,
    moon: MoonSummary | None = None,
) -> dict[str, object]:
    return PlannerNsomComparisonService().compare(
        targets,
        weather=weather or _weather(85),
        scores=scores or _scores(),
        sky_quality=sky_quality or _sky_quality(3),
        telescope=telescope or _telescope(),
        moon=moon or _moon(10),
    )


def _entry(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return next(item for item in comparison["items"] if item["object_id"] == object_id)


def _component(comparison: dict[str, object], object_id: str, component: str) -> dict[str, object]:
    return _entry(comparison, object_id)["nsom"]["components"][component]


def _explanation(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return _entry(comparison, object_id)["nsom"]["explanation"]


def _has_factor(
    explanation: dict[str, object],
    owner: str,
    factor: str,
    *,
    section: str = "main_limiting_factors",
) -> bool:
    return any(item["owner"] == owner and item["factor"] == factor for item in explanation[section])


def _has_owner(
    explanation: dict[str, object],
    owner: str,
    *,
    section: str,
) -> bool:
    return any(item["owner"] == owner for item in explanation[section])


def _effective_value(comparison: dict[str, object], object_id: str) -> float:
    return float(_component(comparison, object_id, "effective_observability")["value"])


def _nsom_score(comparison: dict[str, object], object_id: str) -> float:
    return float(_entry(comparison, object_id)["nsom"]["score"])


def _representative_targets() -> list[CelestialObject]:
    return [
        _target("planet", "Pianeta", 84, magnitude="-1.7", best_time="21:00"),
        _target("galaxy", "Galaxy", 83, magnitude="8.5", best_time="21:30", difficulty="Media"),
        _target("diffuse-nebula", "Nebula", 82, magnitude="7.0", best_time="22:00", difficulty="Media"),
        _target("open-cluster", "Open Cluster", 78, magnitude="5.2", best_time="22:30", difficulty="Facile"),
        _target("globular-cluster", "Globular Cluster", 80, magnitude="6.8", best_time="23:00", difficulty="Media"),
        _target("moon", "Luna", 76, magnitude="-12.0", best_time="23:30", difficulty="Facile"),
    ]


def _target(
    object_id: str,
    object_type: str,
    score: int,
    *,
    magnitude: str = "8.0",
    best_time: str = "21:00",
    difficulty: str = "Media",
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
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type="telescope",
    )


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


def _scores(planetary: int = 85, deep_sky: int = 88) -> AdvancedObservingScores:
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


def _telescope(
    *,
    name: str = "Test Scope",
    aperture_mm: int = 127,
    focal_length_mm: int = 1500,
    mount: str = "",
) -> Telescope:
    return Telescope(
        id=name.lower().replace(" ", "-"),
        name=name,
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Mak",
        mount=mount,
    )


def _plan_summary(plan):
    return [(item.object_id, item.score, item.time_label) for item in plan]
