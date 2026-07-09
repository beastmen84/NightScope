from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.equipment_nsom_migration_closeout import (
    REPORT_PATH,
    generate_equipment_nsom_migration_closeout_data,
    render_markdown_report,
)


def test_equipment_nsom_migration_closeout_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_equipment_nsom_migration_closeout_data()
    second = generate_equipment_nsom_migration_closeout_data()

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
    assert first["metadata"]["runtime_behaviour_changed_by_closeout"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_equipment_nsom_migration_is_closed_as_setup_local_without_default_off_path() -> None:
    data = generate_equipment_nsom_migration_closeout_data()

    assert data["readiness"]["verdict"] == "equipment_nsom_migration_closed_setup_local"
    assert data["readiness"]["migration_closed"] is True
    assert data["readiness"]["setup_local_service"] is True
    assert data["readiness"]["default_off_equipment_path_added"] is False
    assert data["readiness"]["default_off_equipment_path_recommended_now"] is False
    assert data["readiness"]["runtime_replacement_ready"] is False
    assert data["readiness"]["ready_to_return_to_backend_planning"] is True
    assert data["readiness"]["runtime_behaviour_changed_by_closeout"] is False
    assert data["blockers"] == []


def test_equipment_nsom_closeout_records_all_required_decisions() -> None:
    data = generate_equipment_nsom_migration_closeout_data()
    decisions = {decision["decision_id"]: decision for decision in data["closed_decisions"]}

    assert set(decisions) == {
        "observer_capability_adapter",
        "presenter_contract_boundary",
        "setup_score_ownership",
        "setup_score_component_boundary",
        "default_off_replacement_policy",
        "confidence_policy",
    }
    assert decisions["observer_capability_adapter"]["status"] == (
        "closed_shared_adapter_available"
    )
    assert decisions["presenter_contract_boundary"]["status"] == (
        "closed_runtime_neutral_read_model"
    )
    assert decisions["setup_score_ownership"]["status"] == (
        "closed_owned_by_equipment_service"
    )
    assert decisions["setup_score_component_boundary"]["status"] == (
        "closed_with_parity_read_model"
    )
    assert decisions["default_off_replacement_policy"]["status"] == (
        "closed_no_default_off_path_now"
    )
    assert decisions["confidence_policy"]["status"] == "closed_metadata_only"
    assert all(
        decision["blocks_next_backend_planning"] is False
        for decision in data["closed_decisions"]
    )


def test_equipment_nsom_closeout_evidence_preserves_runtime_and_confidence_boundaries() -> None:
    data = generate_equipment_nsom_migration_closeout_data()
    evidence = data["evidence"]

    assert evidence["scenario_count"] > 0
    assert evidence["candidate_row_count"] > 0
    assert evidence["observer_adapter_extracted"] is True
    assert evidence["presenter_contract_audited"] is True
    assert evidence["runtime_setup_read_model_boundary_present"] is True
    assert evidence["score_ownership_audited"] is True
    assert evidence["score_component_boundary_introduced"] is True
    assert evidence["score_component_boundary_parity_checked"] is True
    assert evidence["default_off_policy_set"] is True
    assert evidence["default_off_path_recommended_now"] is False
    assert evidence["setup_local_service_recommended"] is True
    assert evidence["confidence_score_neutral"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_closeout"] is True


def test_equipment_nsom_closeout_has_no_runtime_or_qml_wiring() -> None:
    data = generate_equipment_nsom_migration_closeout_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_equipment_nsom_migration_closeout_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Equipment NSOM Migration Closeout" in text
    assert "equipment_nsom_migration_closed_setup_local" in text
    assert "closed_no_default_off_path_now" in text
    assert "Review 1.13.5" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
