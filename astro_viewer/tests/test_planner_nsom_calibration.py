from __future__ import annotations

import json
from pathlib import Path

import pytest

from astro_viewer.app.services.night_planner_service import NSOM_PLANNER_SCORING_ENABLED
from astro_viewer.app.services.planner_nsom_calibration import (
    CALIBRATION_SCENARIO_NAMES,
    CALIBRATION_REVIEW_THRESHOLDS,
    CALIBRATION_SCORE_COMPONENTS,
    OPPORTUNITY_POLICY_TYPES,
    PlannerNsomCalibrationInspectionService,
)


def test_calibration_inspection_exposes_named_scenarios_as_strict_json() -> None:
    inspection = PlannerNsomCalibrationInspectionService().inspect()

    json.dumps(inspection, allow_nan=False)

    assert inspection["metadata"]["developer_only"] is True
    assert inspection["metadata"]["nsom_planner_scoring_enabled"] is False
    assert tuple(inspection["metadata"]["scenario_names"]) == CALIBRATION_SCENARIO_NAMES
    assert {scenario["name"] for scenario in inspection["scenario_groups"]} == set(
        CALIBRATION_SCENARIO_NAMES
    )
    assert inspection["metadata"]["side_effects"] == {
        "file_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
    }

    for scenario in inspection["scenario_groups"]:
        assert scenario["intended_nsom_expectation"]
        assert scenario["ranked_nsom_opportunities"]
        assert scenario["legacy_reference_ranking"]
        for row in scenario["ranked_nsom_opportunities"]:
            assert set(CALIBRATION_SCORE_COMPONENTS) <= set(row["score_components"])
            assert row["explanation"]["target"]["object_id"] == row["object_id"]
            assert row["limiting_factors"] == row["explanation"]["main_limiting_factors"]
            assert row["positive_factors"] == row["explanation"]["main_positive_factors"]
            assert {"rank", "score"} <= set(row["legacy_reference"])
            assert row["calibration_review"]["status"] in {"expected", "review", "warning"}
            assert row["calibration_review"]["thresholds"] == CALIBRATION_REVIEW_THRESHOLDS
            assert row["opportunity_policy_type"] in OPPORTUNITY_POLICY_TYPES


def test_calibration_sky_rules_are_visible_in_bright_sky_and_moon_scenarios() -> None:
    inspection = PlannerNsomCalibrationInspectionService().inspect()
    bright_sky = _scenario(inspection, "bright_sky")
    moon_case = _scenario(inspection, "moon_target_case")

    for object_id in ("galaxy", "diffuse-nebula"):
        row = _row(bright_sky, object_id)
        assert _has_factor(row, "sky", "moon_background")
        assert _has_factor(row, "sky", "sky_background")

    for object_id in ("planet", "moon"):
        row = _row(bright_sky, object_id)
        assert not _has_factor(row, "sky", "moon_background")
        assert not _has_factor(row, "sky", "sky_background")
        assert _has_factor(row, "sky", "moon_background_neutral", section="positive_factors")
        assert _has_factor(row, "sky", "sky_background_neutral", section="positive_factors")

    moon = _row(moon_case, "moon")
    assert not _has_factor(moon, "sky", "moon_background")
    assert not _has_factor(moon, "sky", "sky_background")
    assert _component(moon, "effective_observability") >= _component(
        _row(moon_case, "galaxy"),
        "effective_observability",
    )


def test_calibration_session_and_equipment_rules_stay_on_their_owners() -> None:
    inspection = PlannerNsomCalibrationInspectionService().inspect()
    good_session = _scenario(inspection, "good_session")
    poor_session = _scenario(inspection, "poor_session")
    small_telescope = _scenario(inspection, "small_telescope")
    large_telescope = _scenario(inspection, "large_telescope")

    good_galaxy = _row(good_session, "galaxy")
    poor_galaxy = _row(poor_session, "galaxy")
    assert _component(poor_galaxy, "session_viability") < _component(good_galaxy, "session_viability")
    assert _component(poor_galaxy, "observable_target_value") == pytest.approx(
        _component(good_galaxy, "observable_target_value")
    )
    assert _component(poor_galaxy, "practical_target_value") == pytest.approx(
        _component(good_galaxy, "practical_target_value")
    )
    assert _has_factor(poor_galaxy, "session", "session_viability")

    small_galaxy = _row(small_telescope, "galaxy")
    large_galaxy = _row(large_telescope, "galaxy")
    assert _component(small_galaxy, "observable_target_value") == pytest.approx(
        _component(large_galaxy, "observable_target_value")
    )
    assert _component(large_galaxy, "practical_target_value") > _component(
        small_galaxy,
        "practical_target_value",
    )
    assert _component(large_galaxy, "q_target") > _component(small_galaxy, "q_target")
    assert _has_factor(small_galaxy, "observer", "q_target")


def test_calibration_blocked_session_policy_marks_all_zero_ranking_non_actionable() -> None:
    inspection = PlannerNsomCalibrationInspectionService().inspect()
    blocked = _scenario(inspection, "blocked_session")
    policy = blocked["opportunity_policy_review"]

    assert policy["applies"] is True
    assert policy["policy_type"] == "non_actionable_hard_block"
    assert policy["current_runtime_policy"] == "hard_block"
    assert policy["ranking_actionable"] is False
    assert policy["stable_order_is_deterministic_tie"] is True
    assert policy["stable_order_is_recommendation_order"] is False
    assert "not a recommendation order" in policy["policy_notes"]
    assert policy["interpretations"]["hard_block"]["observation_opportunity"] == pytest.approx(0.0)
    preserved = policy["interpretations"]["non_actionable_preserved_order"]
    assert preserved["ranking_basis"] == "PracticalTargetValue"
    assert preserved["ranking_actionable"] is False
    assert preserved["used_for_runtime_ranking"] is False
    assert preserved["qml_exposure"] is False
    assert preserved["internal_order"][0]["practical_target_value"] > preserved["internal_order"][-1][
        "practical_target_value"
    ]
    assert policy["non_actionable_preserved_order"] == preserved["internal_order"]
    assert policy["preserved_order_used_for_runtime_ranking"] is False
    assert policy["preserved_order_qml_exposure"] is False

    for row in blocked["ranked_nsom_opportunities"]:
        assert row["nsom_score"] == pytest.approx(0.0)
        assert row["ranking_actionable"] is False
        assert row["stable_order_is_deterministic_tie"] is True
        assert row["stable_order_is_recommendation_order"] is False
        assert row["opportunity_policy_type"] == "non_actionable_hard_block"
        assert row["calibration_review"]["status"] == "warning"


def test_calibration_condition_groups_match_intended_direction() -> None:
    inspection = PlannerNsomCalibrationInspectionService().inspect()
    planet_conditions = _scenario(inspection, "planet_favouring_conditions")
    deep_sky_conditions = _scenario(inspection, "deep_sky_favouring_conditions")
    bright_sky = _scenario(inspection, "bright_sky")

    planet_score = _row(planet_conditions, "planet")["nsom_score"]
    assert planet_score > _row(planet_conditions, "galaxy")["nsom_score"]
    assert planet_score > _row(planet_conditions, "diffuse-nebula")["nsom_score"]

    deep_sky_scores = [
        _row(deep_sky_conditions, "galaxy")["nsom_score"],
        _row(deep_sky_conditions, "diffuse-nebula")["nsom_score"],
        _row(deep_sky_conditions, "open-cluster")["nsom_score"],
    ]
    assert max(deep_sky_scores) > _row(deep_sky_conditions, "planet")["nsom_score"]
    assert _component(_row(deep_sky_conditions, "galaxy"), "effective_observability") > _component(
        _row(bright_sky, "galaxy"),
        "effective_observability",
    )


def test_calibration_confidence_remains_metadata_for_every_row() -> None:
    inspection = PlannerNsomCalibrationInspectionService().inspect()

    for scenario in inspection["scenario_groups"]:
        for row in scenario["ranked_nsom_opportunities"]:
            confidence = row["explanation"]["confidence_explanation"]
            assert confidence["role"] == "metadata_only"
            assert confidence["score_factor"] is False
            assert confidence["score_effect"] == pytest.approx(0.0)
            assert not _has_owner(row, "confidence")
            assert not _has_owner(row, "confidence", section="positive_factors")


def test_calibration_components_are_not_ignored_or_globally_dominated() -> None:
    inspection = PlannerNsomCalibrationInspectionService().inspect()

    for component in CALIBRATION_SCORE_COMPONENTS:
        component_range = inspection["component_ranges"][component]["range"]
        assert component_range is not None
        assert component_range > 0.0

    dominant_summary = inspection["dominant_limiting_factor_summary"]
    dominant_counts = dominant_summary["by_factor"]
    assert dominant_counts
    assert max(dominant_counts.values()) < len(inspection["scenario_groups"])
    assert len(dominant_summary["by_owner"]) >= 3

    coverage = inspection["factor_coverage"]
    assert {"sky", "observer", "session", "opportunity"} <= set(coverage["owners"])


def test_calibration_inspection_is_not_exposed_to_qml() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))

    assert NSOM_PLANNER_SCORING_ENABLED is False
    assert "PlannerNsomCalibrationInspectionService" not in qml_text
    assert "planner_nsom_calibration" not in qml_text


def _scenario(inspection: dict[str, object], name: str) -> dict[str, object]:
    return next(scenario for scenario in inspection["scenario_groups"] if scenario["name"] == name)


def _row(scenario: dict[str, object], object_id: str) -> dict[str, object]:
    return next(row for row in scenario["ranked_nsom_opportunities"] if row["object_id"] == object_id)


def _component(row: dict[str, object], component: str) -> float:
    return float(row["score_components"][component])


def _has_factor(
    row: dict[str, object],
    owner: str,
    factor: str,
    *,
    section: str = "limiting_factors",
) -> bool:
    return any(item["owner"] == owner and item["factor"] == factor for item in row[section])


def _has_owner(
    row: dict[str, object],
    owner: str,
    *,
    section: str = "limiting_factors",
) -> bool:
    return any(item["owner"] == owner for item in row[section])
