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
    assert first["metadata"]["scenario_count"] == 108
    assert 95 <= first["metadata"]["scenario_count"] <= 115
    assert first["metadata"]["scenario_group_count"] == 18
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

    assert NSOM_PLANNER_SCORING_ENABLED is False
    assert "nsom_planner_comparison_report" not in qml_text
    assert "NSOM_PLANNER_COMPARISON_REPORT" not in qml_text
    assert "nsom_planner_comparison_report" not in runtime_text
    assert str(REPORT_PATH).replace("\\", "/") == "docs/NSOM_PLANNER_COMPARISON_REPORT.md"


def test_checked_in_markdown_report_exists() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Planner Comparison Report" in text
    assert "108 deterministic scenario rows" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def _rows(data: dict[str, object]) -> list[dict[str, object]]:
    return [row for group in data["scenario_groups"] for row in group["scenarios"]]
