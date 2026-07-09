from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.equipment_nsom_default_off_path_policy_audit import (
    REPORT_PATH,
    generate_equipment_default_off_path_policy_audit_data,
    render_markdown_report,
)


def test_equipment_default_off_path_policy_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_equipment_default_off_path_policy_audit_data()
    second = generate_equipment_default_off_path_policy_audit_data()

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
    assert first["metadata"]["runtime_behaviour_changed_by_policy"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_policy_rejects_default_off_equipment_path_and_accepts_setup_local_service() -> None:
    data = generate_equipment_default_off_path_policy_audit_data()
    options = {option["option_id"]: option for option in data["policy_options"]}
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert data["readiness"]["verdict"] == "equipment_default_off_path_policy_set_setup_local"
    assert data["readiness"]["default_off_equipment_path_recommended_now"] is False
    assert data["readiness"]["setup_local_service_recommended"] is True
    assert data["readiness"]["runtime_replacement_ready"] is False
    assert data["readiness"]["blocks_backend_migration_closeout"] is False

    assert options["add_default_off_nsom_equipment_path"]["status"] == "rejected_now"
    assert options["keep_equipment_setup_local_with_nsom_boundaries"]["status"] == "accepted"
    assert options["future_equipment_explanation_metadata"]["status"] == "deferred_non_blocking"
    assert decisions["equipment_runtime_policy"]["status"] == "setup_local_service_accepted"
    assert decisions["default_off_replacement_policy"]["status"] == "not_recommended_now"
    assert decisions["q_target_replacement_policy"]["status"] == "rejected_as_direct_replacement"
    assert decisions["confidence_policy"]["status"] == "accepted_metadata_only"
    assert all(
        decision["blocks_backend_migration_closeout"] is False
        for decision in data["policy_decisions"]
    )


def test_policy_uses_boundary_evidence_without_changing_scores_or_fabricating_legacy_components() -> None:
    data = generate_equipment_default_off_path_policy_audit_data()
    evidence = data["evidence"]

    assert evidence["scenario_count"] > 0
    assert evidence["candidate_row_count"] > 0
    assert evidence["component_boundary_parity_checked"] is True
    assert evidence["fallback_payload_preserved"] is True
    assert evidence["q_target_direct_replacement_rejected"] is True
    assert evidence["confidence_score_neutral"] is True
    assert evidence["legacy_unavailable_components_marked"] is True
    assert data["checks"]["component_boundary_parity_checked"] is True
    assert data["checks"]["presenter_contract_preserved"] is True
    assert data["checks"]["legacy_unavailable_components_marked"] is True
    assert data["blockers"] == []


def test_policy_has_no_runtime_or_qml_wiring() -> None:
    data = generate_equipment_default_off_path_policy_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_policy"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_equipment_default_off_path_policy_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Equipment NSOM Default-Off Path Policy Audit" in text
    assert "equipment_default_off_path_policy_set_setup_local" in text
    assert "add_default_off_nsom_equipment_path" in text
    assert "1.13.5 Equipment NSOM migration closeout" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
