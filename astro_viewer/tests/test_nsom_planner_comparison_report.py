from __future__ import annotations

import json
from pathlib import Path

import pytest

from astro_viewer.app.services.night_planner_service import NSOM_PLANNER_SCORING_ENABLED
from astro_viewer.tools.nsom_planner_comparison_report import (
    REPORT_PATH,
    UNAVAILABLE,
    generate_report_data,
    render_markdown_report,
)


def test_report_data_generates_around_one_hundred_deterministic_scenarios() -> None:
    first = generate_report_data()
    second = generate_report_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"]["scenario_count"] == 120
    assert 95 <= first["metadata"]["scenario_count"] <= 125
    assert first["metadata"]["scenario_group_count"] == 20
    assert first["metadata"]["developer_only"] is True


def test_every_report_scenario_has_nsom_explanation_fields() -> None:
    data = generate_report_data()
    required_nsom_fields = {
        "score",
        "rank",
        "observable_target_value",
        "effective_observability",
        "practical_target_value",
        "session_viability",
        "observer_capability",
        "observing_window_quality",
        "chronology_fit",
        "practical_constraints",
        "recommendation_confidence",
        "main_positive_factors",
        "main_limiting_factors",
        "explanation",
    }
    required_explanation_fields = {
        "target",
        "final_nsom_opportunity_score",
        "score_components",
        "nsom_components",
        "main_limiting_factors",
        "main_positive_factors",
        "confidence_explanation",
    }

    for row in _rows(data):
        assert required_nsom_fields <= set(row["nsom"])
        assert required_explanation_fields <= set(row["nsom"]["explanation"])
        assert row["nsom"]["recommendation_confidence"]["role"] == "metadata_only"
        assert row["nsom"]["recommendation_confidence"]["score_factor"] is False
        assert row["calibration_review"]["status"] in {"expected", "review", "warning"}
        assert row["calibration_review"]["rank_delta_severity"] in {
            "expected",
            "review",
            "warning",
        }
        assert isinstance(row["ranking_actionable"], bool)
        assert isinstance(row["stable_order_is_deterministic_tie"], bool)
        assert row["opportunity_policy_type"] in {
            "actionable_ranked_recommendation",
            "actionable_with_uncertain_timing",
            "non_actionable_hard_block",
            "non_actionable_invisible_target",
        }
        assert row["calibration_review"]["suggested_human_review_reason"]


def test_blocked_and_all_zero_report_groups_are_non_actionable_ties() -> None:
    data = generate_report_data()
    blocked = _group(data, "G09")
    invisible = _group(data, "G20")

    for group in (blocked, invisible):
        policy = group["opportunity_policy_review"]
        assert policy["ranking_actionable"] is False
        assert policy["stable_order_is_deterministic_tie"] is True
        assert policy["stable_order_is_recommendation_order"] is False
        assert "not" in policy["policy_notes"]
        assert "recommendation order" in policy["policy_notes"]
        assert group["calibration_review_summary"]["status"] == "warning"
        assert policy["non_actionable_preserved_order"]
        assert policy["preserved_order_used_for_runtime_ranking"] is False
        assert policy["preserved_order_qml_exposure"] is False
        for row in group["scenarios"]:
            assert row["nsom"]["score"] == pytest.approx(0.0)
            assert row["ranking_actionable"] is False
            assert row["stable_order_is_deterministic_tie"] is True
            assert row["stable_order_is_recommendation_order"] is False
            assert row["calibration_review"]["status"] == "warning"

    assert blocked["opportunity_policy_review"]["policy_type"] == "non_actionable_hard_block"
    assert invisible["opportunity_policy_review"]["policy_type"] == (
        "non_actionable_invisible_target"
    )


def test_review_thresholds_classify_known_large_deltas_and_window_cases() -> None:
    data = generate_report_data()
    large_delta = _row(data, "G15:globular_cluster")
    missing_window = _row(data, "G19:planet")
    invisible = _row(data, "G20:planet")

    assert abs(large_delta["rank_delta"]) >= data["metadata"]["calibration_review_thresholds"][
        "large_rank_delta_warning"
    ]
    assert large_delta["calibration_review"]["rank_delta_severity"] == "warning"
    assert large_delta["calibration_review"]["status"] == "warning"

    assert missing_window["nsom"]["observing_window_quality"] == pytest.approx(0.5)
    assert missing_window["ranking_actionable"] is True
    assert missing_window["opportunity_policy_type"] == "actionable_with_uncertain_timing"
    assert missing_window["timing_uncertainty"] is True
    missing_checks = {
        check["name"]: check
        for check in missing_window["calibration_review"]["checks"]
    }
    assert missing_checks["missing_window_handling"]["status"] == "expected"

    assert invisible["target"]["visible"] is False
    assert invisible["nsom"]["observing_window_quality"] == pytest.approx(0.0)
    assert invisible["ranking_actionable"] is False
    assert invisible["stable_order_is_deterministic_tie"] is True
    assert invisible["opportunity_policy_type"] == "non_actionable_invisible_target"


def test_open_clusters_are_no_longer_bottom_ranked_in_recurring_demotion_groups() -> None:
    data = generate_report_data()
    affected_groups = (
        "G01",
        "G04",
        "G07",
        "G08",
        "G12",
        "G15",
        "G16",
        "G17",
        "G18",
        "G19",
    )
    expected_q_targets = {
        "G01": 0.6399690909090909,
        "G04": 0.6399690909090909,
        "G07": 0.6399690909090909,
        "G08": 0.6399690909090909,
        "G12": 0.7159236363636363,
        "G15": 0.7159236363636363,
        "G16": 0.6399690909090909,
        "G17": 0.6399690909090909,
        "G18": 0.6399690909090909,
        "G19": 0.6399690909090909,
    }

    for group_id in affected_groups:
        row = _row(data, f"{group_id}:open_cluster")
        group_size = len(_group(data, group_id)["scenarios"])
        components = row["nsom"]["explanation"]["score_components"]

        assert row["nsom"]["rank"] < group_size
        assert row["calibration_review"]["status"] != "warning"
        assert row["rank_delta"] <= 3
        assert components["q_target"] == pytest.approx(expected_q_targets[group_id])

    assert _row(data, "G12:open_cluster")["nsom"]["rank"] == 5
    assert _row(data, "G15:open_cluster")["nsom"]["rank"] == 4


def test_open_cluster_q_target_calibration_preserves_observable_target_values() -> None:
    data = generate_report_data()
    expected_observable_values = {
        "G01:open_cluster": 69.35470777217554,
        "G12:open_cluster": 69.35470777217554,
        "G15:open_cluster": 73.97835495698725,
        "G16:open_cluster": 19.815630792050154,
        "G19:open_cluster": 69.35470777217554,
    }

    for scenario_id, expected in expected_observable_values.items():
        row = _row(data, scenario_id)
        components = row["nsom"]["explanation"]["score_components"]

        assert components["observable_target_value"] == pytest.approx(expected)


def test_open_cluster_calibration_does_not_change_other_deep_sky_q_target_scores() -> None:
    data = generate_report_data()
    expected = {
        "G01:galaxy": (0.6125787878787878, 40.02455205919594),
        "G01:diffuse_nebula": (0.6009803030303029, 38.57384490490017),
        "G01:globular_cluster": (0.6351787878787879, 39.35524482149254),
        "G12:galaxy": (0.7391515151515152, 48.294535957175945),
        "G12:diffuse_nebula": (0.6952121212121212, 44.622102262627465),
        "G12:globular_cluster": (0.8046515151515153, 49.85565950734474),
        "G15:galaxy": (0.7391515151515152, 51.51417168765435),
        "G15:diffuse_nebula": (0.6952121212121212, 47.596909080135966),
        "G15:globular_cluster": (0.8046515151515153, 53.17937014116772),
    }

    for scenario_id, (expected_q_target, expected_score) in expected.items():
        row = _row(data, scenario_id)
        components = row["nsom"]["explanation"]["score_components"]

        assert components["q_target"] == pytest.approx(expected_q_target)
        assert row["nsom"]["score"] == pytest.approx(expected_score)


def test_small_equipment_planets_are_not_bottom_ranked_by_q_target_floor() -> None:
    data = generate_report_data()

    for scenario_id, group_id in (("G10:planet", "G10"), ("G11:planet", "G11")):
        row = _row(data, scenario_id)
        group_size = len(_group(data, group_id)["scenarios"])
        components = row["nsom"]["explanation"]["score_components"]

        assert row["nsom"]["rank"] < group_size
        assert row["nsom"]["rank"] == 4
        assert row["rank_delta"] == 3
        assert row["calibration_review"]["rank_delta_severity"] == "review"
        assert components["q_target"] == pytest.approx(0.55)
        assert components["observable_target_value"] == pytest.approx(72.24)
        assert components["practical_target_value"] == pytest.approx(39.732)


def test_planet_q_target_calibration_does_not_change_deep_sky_q_target_rows() -> None:
    data = generate_report_data()
    expected_q_targets = {
        "G10:galaxy": 0.5575000000000002,
        "G10:diffuse_nebula": 0.6000000000000001,
        "G10:open_cluster": 0.6455,
        "G11:galaxy": 0.5672121212121213,
        "G11:diffuse_nebula": 0.6056969696969698,
        "G11:open_cluster": 0.6475454545454544,
    }

    for scenario_id, expected in expected_q_targets.items():
        row = _row(data, scenario_id)
        components = row["nsom"]["explanation"]["score_components"]

        assert components["q_target"] == pytest.approx(expected)


def test_unavailable_legacy_components_are_marked_not_fabricated() -> None:
    data = generate_report_data()

    for row in _rows(data):
        components = row["legacy"]["components"]
        for component in (
            "observing_window_quality",
            "chronology_fit",
            "observer_capability",
            "recommendation_confidence",
        ):
            assert components[component]["status"] == UNAVAILABLE
            assert "value" not in components[component]
            assert components[component]["reason"]

        assert components["base_score"]["status"] == "available"
        assert "value" in components["base_score"]
        assert row["legacy"]["readable_explanation"]


def test_confidence_control_does_not_affect_nsom_score() -> None:
    data = generate_report_data()
    confidence = data["confidence_control"]

    assert confidence["low_confidence_value"] < confidence["high_confidence_value"]
    assert confidence["low_confidence_score"] == pytest.approx(confidence["high_confidence_score"])
    assert confidence["score_delta"] == pytest.approx(0.0)


def test_report_markdown_contains_required_sections_and_matrix() -> None:
    data = generate_report_data()
    markdown = render_markdown_report(data)

    assert "# NSOM Planner Comparison Report" in markdown
    assert "## Executive Summary" in markdown
    assert "## Methodology" in markdown
    assert "## Scenario Matrix Overview" in markdown
    assert "## Score And Rank Comparison" in markdown
    assert "## Intentional NSOM Differences From Legacy" in markdown
    assert "## Cases Where NSOM Better Follows The Model" in markdown
    assert "## Cases Requiring Further Review" in markdown
    assert "## Calibration Review Thresholds" in markdown
    assert "## Opportunity Policy Review" in markdown
    assert "## Recommended Next Steps" in markdown
    assert markdown.count("| G") >= data["metadata"]["scenario_count"]


def test_report_generation_is_not_wired_into_runtime_or_qml() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    runtime_roots = [
        Path(__file__).parents[1] / "app" / "viewmodels",
        Path(__file__).parents[1] / "app" / "services",
    ]
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in runtime_roots
        for path in root.rglob("*.py")
        if path.name != "planner_nsom_calibration.py"
    )

    assert NSOM_PLANNER_SCORING_ENABLED is True
    assert "nsom_planner_comparison_report" not in qml_text
    assert "NSOM_PLANNER_COMPARISON_REPORT" not in qml_text
    assert "nsom_planner_comparison_report" not in runtime_text
    assert str(REPORT_PATH).replace("\\", "/") == "docs/NSOM_PLANNER_COMPARISON_REPORT.md"


def test_checked_in_markdown_report_exists() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Planner Comparison Report" in text
    assert "120 deterministic scenario rows" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def _rows(data: dict[str, object]) -> list[dict[str, object]]:
    return [row for group in data["scenario_groups"] for row in group["scenarios"]]


def _group(data: dict[str, object], group_id: str) -> dict[str, object]:
    return next(group for group in data["scenario_groups"] if group["group_id"] == group_id)


def _row(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(row for row in _rows(data) if row["scenario_id"] == scenario_id)
