from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.equipment_nsom_policy_readiness import (
    POLICY_READINESS_PATH,
    generate_policy_readiness_data,
    render_markdown_report,
)


def test_equipment_policy_readiness_data_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_policy_readiness_data()
    second = generate_policy_readiness_data()

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
        "source_report": "docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md",
        "policy_report_path": "docs/EQUIPMENT_NSOM_POLICY_READINESS.md",
    }


def test_equipment_policy_defers_default_off_replacement_but_allows_adapter_step() -> None:
    data = generate_policy_readiness_data()

    assert data["readiness"]["verdict"] == "equipment_nsom_policy_set_runtime_replacement_deferred"
    assert data["readiness"]["ready_for_default_off_path"] is False
    assert data["readiness"]["ready_for_observer_capability_adapter_step"] is True
    assert data["readiness"]["runtime_behaviour_changed_by_this_review"] is False
    assert data["readiness"]["explicit_legacy_default"] == (
        "EquipmentService.suggest_for_profile(...) remains unchanged"
    )
    assert data["checks"]["default_off_runtime_replacement_deferred"] is True
    assert data["checks"]["observer_capability_adapter_ready_next"] is True
    assert "equipment-equipment-runtime-role" in data["blockers"]


def test_policy_decision_log_covers_required_equipment_boundaries() -> None:
    data = generate_policy_readiness_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert set(decisions) == {
        "equipment_runtime_role",
        "observer_capability_adapter_policy",
        "q_target_runtime_policy",
        "seeing_policy",
        "sky_quality_policy",
        "payload_policy",
        "fallback_policy",
        "confidence_policy",
    }
    assert decisions["equipment_runtime_role"]["blocks_default_off_path"] is True
    assert decisions["observer_capability_adapter_policy"]["adapter_extraction_ready"] is True
    assert decisions["q_target_runtime_policy"]["q_target_replaces_equipment_score"] is False
    assert decisions["sky_quality_policy"]["affected_nsom_layer"] == "sky"
    assert decisions["payload_policy"]["affected_nsom_layer"] == "presentation"
    assert data["checks"]["required_policy_decisions_recorded"] is True
    assert data["checks"]["q_target_does_not_replace_setup_score"] is True


def test_comparison_evidence_supports_policy_without_calibrating_to_legacy() -> None:
    data = generate_policy_readiness_data()
    evidence = data["comparison_evidence"]

    assert evidence["scenario_count"] == 5
    assert evidence["candidate_row_count"] == 34
    assert set(evidence["ranking_disagreement_scenarios"]) >= {
        "E02_open_cluster_wide_field",
        "E03_galaxy_high_light_pollution",
    }
    assert evidence["legacy_ownership_mixing_observed"] is True
    assert evidence["observer_isolated_from_observable"] is True
    assert data["checks"]["legacy_ownership_mixing_documented"] is True
    assert data["recommended_policy"]["default_off_replacement_policy"] == (
        "defer_until_payload_and_environment_boundaries_exist"
    )


def test_confidence_remains_metadata_only_and_runtime_safety_is_clean() -> None:
    data = generate_policy_readiness_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert decisions["confidence_policy"]["affected_nsom_layer"] == "confidence"
    assert decisions["confidence_policy"]["score_path"] == "parallel_metadata"
    assert decisions["confidence_policy"]["score_effect"] == 0.0
    assert data["comparison_evidence"]["confidence_score_effect"] == 0.0
    assert data["checks"]["confidence_score_neutral"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_review"] is True


def test_equipment_policy_readiness_has_no_runtime_or_qml_wiring() -> None:
    data = generate_policy_readiness_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_exposure_absent"] is True
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_equipment_policy_readiness_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / POLICY_READINESS_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Equipment NSOM Policy Readiness" in text
    assert "equipment_nsom_policy_set_runtime_replacement_deferred" in text
    assert "ObserverCapability/Q_target adapter" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
