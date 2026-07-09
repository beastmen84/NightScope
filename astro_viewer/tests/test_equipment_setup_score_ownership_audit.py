from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.equipment_setup_score_ownership_audit import (
    COMPONENT_WEIGHTS,
    REPORT_PATH,
    generate_equipment_setup_score_ownership_audit_data,
    render_markdown_report,
)


def test_equipment_setup_score_ownership_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_equipment_setup_score_ownership_audit_data()
    second = generate_equipment_setup_score_ownership_audit_data()

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
        "detail_object_changed": False,
        "runtime_behaviour_changed_by_this_audit": False,
        "source_reports": [
            "docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md",
            "docs/EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT.md",
        ],
        "report_path": "docs/EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT.md",
    }
    assert first["checks"]["strict_json_compatible"] is True


def test_audit_records_real_equipment_formula_and_component_weights() -> None:
    data = generate_equipment_setup_score_ownership_audit_data()

    assert data["readiness"]["verdict"] == "equipment_setup_score_ownership_audited"
    assert data["readiness"]["runtime_replacement_ready"] is False
    assert data["readiness"]["score_component_boundary_recommended"] is True
    assert data["formula"]["name"] == "EquipmentService._configuration_score"
    assert data["formula"]["component_weights"] == COMPONENT_WEIGHTS
    assert data["formula"]["total_weight"] == 100.0
    assert data["checks"]["formula_components_match_equipment_service"] is True
    assert data["checks"]["component_weights_sum_to_100"] is True


def test_component_ownership_blocks_runtime_replacement_without_tuning_scores() -> None:
    data = generate_equipment_setup_score_ownership_audit_data()
    policies = {policy["component"]: policy for policy in data["component_policies"]}

    assert set(policies) == set(COMPONENT_WEIGHTS)
    assert policies["angular_scale"]["nsom_layers"] == [
        "universe",
        "observer",
        "presentation/setup",
    ]
    assert "sky" in policies["light_gathering"]["nsom_layers"]
    assert "sky" in policies["seeing_compatibility"]["nsom_layers"]
    assert "presentation/setup" in policies["handling"]["nsom_layers"]
    assert all(policy["blocks_runtime_replacement"] is True for policy in policies.values())
    assert all(policy["score_tuning_recommended"] is False for policy in policies.values())
    assert data["checks"]["all_components_block_replacement_until_boundary"] is True


def test_scenario_evidence_uses_real_component_sums_and_preserves_nsom_boundaries() -> None:
    data = generate_equipment_setup_score_ownership_audit_data()

    assert data["scenario_evidence"]
    assert all(
        scenario["component_sums_match_scores"] is True
        for scenario in data["scenario_evidence"]
    )
    assert data["checks"]["all_component_sums_match_scores"] is True
    assert data["checks"]["sky_and_seeing_not_hidden_in_observer_capability"] is True
    assert data["checks"]["q_target_not_direct_replacement"] is True
    assert data["checks"]["confidence_score_neutral"] is True
    assert data["checks"]["setup_read_model_boundary_present"] is True


def test_decision_log_surfaces_replacement_blockers_without_recommending_runtime_change() -> None:
    data = generate_equipment_setup_score_ownership_audit_data()
    decisions = {decision["decision_id"]: decision for decision in data["decision_log"]}

    assert decisions["equipment_score_scalar_policy"]["status"] == "needs_component_boundary"
    assert decisions["sky_and_seeing_ownership"]["status"] == "needs_explicit_setup_context"
    assert decisions["q_target_replacement_policy"]["status"] == "rejected_as_direct_replacement"
    assert decisions["component_coverage"]["status"] == "covered"
    assert decisions["confidence_policy"]["status"] == "accepted_metadata_only"
    assert decisions["equipment_score_scalar_policy"]["blocks_runtime_replacement"] is True
    assert data["readiness"]["default_off_equipment_path_recommended_now"] is False
    assert data["readiness"]["runtime_behaviour_changed_by_this_audit"] is False


def test_equipment_setup_score_ownership_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_equipment_setup_score_ownership_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_audit"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_equipment_setup_score_ownership_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Equipment Setup Score Ownership Audit" in text
    assert "equipment_setup_score_ownership_audited" in text
    assert "EquipmentService._configuration_score" in text
    assert "setup-score component boundary is now explicit" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
