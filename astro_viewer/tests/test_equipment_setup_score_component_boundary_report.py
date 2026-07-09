from __future__ import annotations

import json
from pathlib import Path

import pytest

from astro_viewer.app.services.equipment_setup_score_read_model import (
    EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER,
    EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS,
)
from astro_viewer.tools.equipment_setup_score_component_boundary_report import (
    REPORT_PATH,
    generate_equipment_setup_score_component_boundary_data,
    render_markdown_report,
)


def test_equipment_setup_score_component_boundary_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_equipment_setup_score_component_boundary_data()
    second = generate_equipment_setup_score_component_boundary_data()

    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
        second,
        sort_keys=True,
        allow_nan=False,
    )
    assert first["metadata"]["developer_only"] is True
    assert first["metadata"]["runtime_writes"] is False
    assert first["metadata"]["automatic_logging"] is False
    assert first["metadata"]["network"] is False
    assert first["metadata"]["qml_exposure"] is False
    assert first["metadata"]["runtime_behaviour_changed_by_boundary"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_boundary_records_read_model_and_component_order() -> None:
    data = generate_equipment_setup_score_component_boundary_data()

    assert data["readiness"]["verdict"] == "equipment_setup_score_component_boundary_introduced"
    assert data["readiness"]["runtime_replacement_ready"] is False
    assert data["read_model"]["class"] == "EquipmentSetupScoreReadModel"
    assert data["read_model"]["builder"] == "EquipmentSetupScoreReadModelBuilder"
    assert data["read_model"]["component_order"] == list(EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER)
    assert data["read_model"]["component_weights"] == dict(EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS)
    assert data["checks"]["component_weights_sum_to_100"] is True
    assert data["checks"]["component_order_complete"] is True


def test_boundary_parity_matches_equipment_service_scores_and_components() -> None:
    data = generate_equipment_setup_score_component_boundary_data()
    parity = data["parity"]

    assert parity["candidate_row_count"] > 0
    assert parity["all_rows_expose_read_model"] is True
    assert parity["all_scores_match"] is True
    assert parity["all_component_values_match"] is True
    assert parity["max_score_delta"] == pytest.approx(0.0)
    assert data["checks"]["score_read_model_present_in_comparison"] is True
    assert data["checks"]["score_read_model_matches_candidate_scores"] is True
    assert data["checks"]["component_values_match_legacy_projection"] is True
    assert data["blockers"] == []


def test_boundary_keeps_confidence_metadata_only_and_has_no_runtime_or_qml_wiring() -> None:
    data = generate_equipment_setup_score_component_boundary_data()

    assert data["read_model"]["confidence_policy"] == "parallel_metadata_zero_score_effect"
    assert data["checks"]["confidence_score_neutral"] is True
    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_boundary"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_equipment_setup_score_component_boundary_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Equipment Setup Score Component Boundary" in text
    assert "equipment_setup_score_component_boundary_introduced" in text
    assert "EquipmentSetupScoreReadModel" in text
    assert "Review 1.13.5" in text
    assert "Next backend NSOM area selection audit" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
