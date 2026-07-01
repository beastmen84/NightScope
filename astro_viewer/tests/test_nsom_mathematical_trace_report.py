from __future__ import annotations

import json
from pathlib import Path

import pytest

from astro_viewer.app.services.night_planner_service import NSOM_PLANNER_SCORING_ENABLED
from astro_viewer.tools.nsom_mathematical_trace_report import (
    PIPELINE_STAGE_NAMES,
    TRACE_REPORT_PATH,
    generate_trace_report_data,
    render_markdown_report,
)
from astro_viewer.tools.nsom_planner_comparison_report import UNAVAILABLE


def test_trace_report_data_is_deterministic_and_strict_json() -> None:
    first = generate_trace_report_data()
    second = generate_trace_report_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"]["developer_only"] is True
    assert first["metadata"]["scenario_count"] == 120
    assert first["metadata"]["scenario_group_count"] == 20
    assert first["metadata"]["confidence_role"] == "metadata_only_outside_mathematical_pipeline"
    assert first["metadata"]["nsom_planner_scoring_enabled"] is False
    assert first["observer_capability_review"]["metadata"]["developer_only"] is True
    assert first["observer_capability_review"]["metadata"]["legacy_score_used_as_expected_output"] is False


def test_every_trace_has_complete_pipeline_stage_details() -> None:
    data = generate_trace_report_data()

    for row in _rows(data):
        assert tuple(stage["stage"] for stage in row["pipeline"]) == PIPELINE_STAGE_NAMES
        assert "confidence" not in {stage["stage"].lower() for stage in row["pipeline"]}
        assert row["confidence_metadata"]["role"] == "metadata_only"
        assert row["confidence_metadata"]["score_effect"] == pytest.approx(0.0)

        for stage in row["pipeline"]:
            assert stage["inputs"]
            assert stage["formula"]
            assert stage["intermediate_calculation"]
            assert "sub_formulas" in stage
            for formula in stage["sub_formulas"]:
                assert "expected_output" in formula
                assert "matches_reported_output" in formula
            assert stage["outputs"]
            assert "dominant_positive_contributors" in stage
            assert "dominant_limiting_contributors" in stage


def test_trace_formula_arithmetic_matches_exported_nsom_values() -> None:
    data = generate_trace_report_data()
    row = _scenario(data, "G01:galaxy")

    effective = _stage(row, "EffectiveObservability")
    effective_inputs = effective["inputs"]
    expected_effective = (
        effective_inputs["geometric_visibility"]
        * effective_inputs["moon_background"]
        * effective_inputs["sky_background"]
        * effective_inputs["atmospheric_transparency"]
        * effective_inputs["horizon_context"]
    )
    assert effective["outputs"]["value"] == pytest.approx(expected_effective)

    observable = _stage(row, "ObservableTargetValue")
    assert observable["outputs"]["value"] == pytest.approx(
        observable["inputs"]["intrinsic_target_quality"]
        * observable["inputs"]["effective_observability"]
    )

    observer = _stage(row, "ObserverCapability")
    dimensions = observer["outputs"]["dimensions"]
    assert observer["outputs"]["summary_for_planning"] == pytest.approx(
        sum(dimensions.values()) / len(dimensions)
    )

    practical = _stage(row, "PracticalTargetValue")
    assert practical["outputs"]["value"] == pytest.approx(
        practical["inputs"]["observable_target_value"]
        * practical["inputs"]["observer_capability_summary"]
    )

    opportunity = _stage(row, "ObservationOpportunity")
    inputs = opportunity["inputs"]
    assert opportunity["outputs"]["value"] == pytest.approx(
        inputs["practical_target_value"]
        * inputs["observing_window_quality"]
        * inputs["chronology_fit"]
        * inputs["session_viability"]
        * inputs["practical_constraints"]
    )


def test_legacy_unavailable_components_remain_unavailable() -> None:
    data = generate_trace_report_data()

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


def test_all_zero_blocked_group_is_tied_non_actionable() -> None:
    data = generate_trace_report_data()
    blocked_rows = [row for row in _rows(data) if row["group_id"] == "G09"]

    assert blocked_rows
    assert all(_stage(row, "ObservationOpportunity")["outputs"]["value"] == pytest.approx(0.0) for row in blocked_rows)
    for row in blocked_rows:
        ranking = _stage(row, "FinalPlannerRanking")
        assert ranking["outputs"]["ranking_status"] == "tied_non_actionable"
        assert ranking["outputs"]["meaningful_recommendation_order"] is False
        assert ranking["outputs"]["stable_order_only"] is True
        assert not any(factor["factor"] == "rank" for factor in ranking["dominant_positive_contributors"])
        assert any(factor["factor"] == "all_zero_tie" for factor in ranking["dominant_limiting_contributors"])


def test_lower_level_formulas_are_present_or_explicitly_marked() -> None:
    data = generate_trace_report_data()
    row = _scenario(data, "G02:galaxy")
    environment = _stage(row, "ObservationEnvironment")
    observer = _stage(row, "ObserverCapability")

    environment_components = {item["component"]: item for item in environment["sub_formulas"]}
    observer_components = {item["component"]: item for item in observer["sub_formulas"]}

    for component in (
        "geometric_visibility",
        "moon_background",
        "sky_background",
        "atmospheric_transparency",
        "horizon_context",
    ):
        assert component in environment_components
        assert environment_components[component]["status"] in {"available", "adapter-derived", "unavailable"}
        assert environment_components[component]["formula"]

    for component in (
        "telescope_aperture_unit",
        "telescope_focal_length_unit",
        "telescope_field_width",
        "tracking_capability",
        "light_grasp",
        "resolution",
        "field_of_view",
        "magnification_range",
        "tracking_or_goto",
        "observer_capability_summary",
    ):
        assert component in observer_components
        assert observer_components[component]["status"] in {"available", "adapter-derived", "unavailable"}
        assert observer_components[component]["formula"]


def test_observing_window_quality_varies_across_report_fixtures() -> None:
    data = generate_trace_report_data()
    values = {
        _stage(row, "ObservationWindow")["outputs"]["value"]
        for row in _rows(data)
    }

    assert values == {0.0, 0.5, 1.0}


def test_component_diagnostics_report_dominance_and_under_use() -> None:
    data = generate_trace_report_data()
    diagnostics = data["component_diagnostics"]

    assert diagnostics["most_common_limiting_factor"]["owner"] == "observer"
    assert diagnostics["most_common_limiting_factor"]["factor"] == "observer_capability_summary"
    assert diagnostics["dominance_interpretation"] == "frequency_only_not_weight_or_sensitivity"
    assert "ObserverCapability" in diagnostics["component_statistics"]
    assert "RecommendationConfidence" in diagnostics["component_statistics"]
    assert diagnostics["component_statistics"]["RecommendationConfidence"]["range"] > 0.0
    assert diagnostics["components_that_dominate_too_many_scenarios"]
    assert diagnostics["fixture_coverage_limitations"]


def test_trace_markdown_contains_required_sections_and_all_scenarios() -> None:
    data = generate_trace_report_data()
    markdown = render_markdown_report(data)

    assert "# NSOM Mathematical Trace Report" in markdown
    assert "## Executive Summary" in markdown
    assert "## Methodology" in markdown
    assert "## NSOM Mathematical Pipeline" in markdown
    assert "## One Complete Trace For Every Analysed Scenario" in markdown
    assert "## Legacy Comparison" in markdown
    assert "## Why The Two Systems Differ" in markdown
    assert "## Behaviour That Matches The NSOM Model" in markdown
    assert "## Behaviour That Deserves Review" in markdown
    assert "## Potential Calibration Concerns" in markdown
    assert "## Sensitivity Validation" in markdown
    assert "## ObserverCapability Target-Specific Review" in markdown
    assert "## Component Diagnostics" in markdown
    assert "## Final Recommendations" in markdown
    assert markdown.count("### G") >= data["metadata"]["scenario_count"]
    assert "Pipeline membership: outside mathematical pipeline" in markdown


def test_checked_in_trace_report_matches_generator() -> None:
    report = Path(__file__).parents[2] / TRACE_REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Mathematical Trace Report" in text
    assert "120 deterministic scenarios" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def test_trace_report_generation_is_not_wired_into_runtime_or_qml() -> None:
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
    )

    assert NSOM_PLANNER_SCORING_ENABLED is False
    assert "nsom_mathematical_trace_report" not in qml_text
    assert "NSOM_MATHEMATICAL_TRACE_REPORT" not in qml_text
    assert "nsom_mathematical_trace_report" not in runtime_text
    assert str(TRACE_REPORT_PATH).replace("\\", "/") == "docs/NSOM_MATHEMATICAL_TRACE_REPORT.md"


def _rows(data: dict[str, object]) -> list[dict[str, object]]:
    return [row for group in data["scenario_groups"] for row in group["scenarios"]]


def _scenario(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(row for row in _rows(data) if row["scenario_id"] == scenario_id)


def _stage(row: dict[str, object], stage_name: str) -> dict[str, object]:
    return next(stage for stage in row["pipeline"] if stage["stage"] == stage_name)
