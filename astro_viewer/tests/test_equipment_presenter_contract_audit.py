from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.equipment_presenter_contract_audit import (
    REPORT_PATH,
    REQUIRED_PAYLOAD_KEYS,
    REQUIRED_SETUP_OPTION_KEYS,
    generate_equipment_presenter_contract_audit_data,
    render_markdown_report,
)


def test_equipment_presenter_contract_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_equipment_presenter_contract_audit_data()
    second = generate_equipment_presenter_contract_audit_data()

    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
        second,
        sort_keys=True,
        allow_nan=False,
    )
    assert first["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "equipment_recommendations_changed": False,
        "planner_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "sky_compass_changed": False,
        "runtime_behaviour_changed_by_this_audit": False,
        "source_reports": [
            "docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md",
            "docs/EQUIPMENT_NSOM_POLICY_READINESS.md",
        ],
        "report_path": "docs/EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT.md",
    }
    assert first["checks"]["strict_json_compatible"] is True


def test_presenter_contract_preserves_payload_and_setup_option_shape() -> None:
    data = generate_equipment_presenter_contract_audit_data()
    fixture = data["fixture"]
    contract = data["presenter_contract"]

    assert data["readiness"]["verdict"] == "equipment_presenter_contract_audited"
    assert data["readiness"]["runtime_replacement_ready"] is False
    assert data["readiness"]["runtime_read_model_boundary_recommended"] is True
    assert fixture["suggestion_payload_keys"] == list(REQUIRED_PAYLOAD_KEYS)
    assert fixture["setup_option_keys"] == list(REQUIRED_SETUP_OPTION_KEYS)
    assert "Consigliato" in fixture["setup_option_roles"]
    assert fixture["fallback_payloads_are_known_subsets"] is True
    assert "highMagnification" not in fixture["fallback_payload_key_variants"]["naked_eye"]
    assert contract["presentation_owned_output"] == "equipment_setup_payload_and_setupOptions"
    assert data["checks"]["payload_keys_preserved"] is True
    assert data["checks"]["setup_option_keys_preserved"] is True


def test_contract_decisions_keep_q_target_and_confidence_out_of_setup_score() -> None:
    data = generate_equipment_presenter_contract_audit_data()
    decisions = {decision["decision_id"]: decision for decision in data["contract_decisions"]}

    assert set(decisions) == {
        "equipment_runtime_role",
        "payload_shape_contract",
        "q_target_policy",
        "seeing_and_sky_boundary",
        "fallback_policy",
        "selection_score_policy",
        "confidence_policy",
    }
    assert decisions["equipment_runtime_role"]["blocks_runtime_replacement"] is True
    assert decisions["q_target_policy"]["q_target_replaces_selection_score"] is False
    assert decisions["selection_score_policy"]["affected_nsom_layer"] == "presentation"
    assert decisions["confidence_policy"]["score_path"] == "parallel_metadata"
    assert decisions["confidence_policy"]["score_effect"] == 0.0
    assert data["checks"]["q_target_reference_only"] is True
    assert data["checks"]["confidence_score_neutral"] is True


def test_contract_uses_existing_policy_and_comparison_evidence_without_runtime_replacement() -> None:
    data = generate_equipment_presenter_contract_audit_data()

    assert data["policy_readiness"]["ready_for_default_off_path"] is False
    assert data["policy_readiness"]["observer_capability_adapter_extracted"] is True
    assert data["comparison_summary"]["candidate_row_count"] > 0
    assert "equipment-presenter-equipment-runtime-role" in data["blockers"]
    assert "equipment-presenter-payload-shape-contract" in data["blockers"]
    assert data["checks"]["policy_runtime_replacement_deferred"] is True
    assert data["checks"]["observer_capability_adapter_extracted"] is True
    assert data["checks"]["comparison_evidence_available"] is True


def test_presenter_contract_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_equipment_presenter_contract_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["controller_projection_fields_present"] is True
    assert data["checks"]["qml_payload_consumers_present"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_equipment_presenter_contract_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Equipment NSOM Presenter Contract Audit" in text
    assert "equipment_presenter_contract_audited" in text
    assert "setup read-model/presenter boundary" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
