from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.sky_compass_nsom_default_on_readiness_audit import (
    DEFAULT_ON_READINESS_AUDIT_PATH,
    generate_default_on_readiness_audit_data,
    render_markdown_report,
)


def test_sky_compass_default_on_readiness_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_default_on_readiness_audit_data()
    second = generate_default_on_readiness_audit_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "sky_compass_changed_by_this_audit": False,
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
        "source_report": "docs/SKY_COMPASS_NSOM_COMPARISON_REPORT.md",
        "default_off_policy_report": "docs/SKY_COMPASS_NSOM_POLICY_READINESS.md",
        "audit_report_path": "docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
    }


def test_sky_compass_default_on_readiness_verdict_records_enabled_flag() -> None:
    data = generate_default_on_readiness_audit_data()

    assert data["readiness"]["verdict"] == "sky_compass_nsom_default_on_enabled"
    assert data["readiness"]["ready_for_default_on_switch"] is True
    assert data["readiness"]["default_flag"] == "NSOM_SKY_COMPASS_ENABLED = True"
    assert data["readiness"]["default_flag_currently_enabled"] is True
    assert data["readiness"]["requires_separate_flag_change"] is False
    assert data["readiness"]["runtime_behaviour_changed_by_this_audit"] is False
    assert data["readiness"]["explicit_legacy_rollback"] == "removed: AppController(use_nsom_sky_compass=False)"
    assert data["readiness"]["recommended_switch_change"] == "already enabled"
    assert data["blockers"] == []
    assert data["checks"]["default_flag_enabled_for_switch"] is True
    assert data["checks"]["default_on_switch_complete"] is True


def test_audit_proves_default_nsom_path_and_removed_rollback() -> None:
    data = generate_default_on_readiness_audit_data()
    runtime = data["runtime_policy_evidence"]

    assert data["checks"]["constructor_rollback_removed"] is True
    assert data["checks"]["default_uses_nsom_path"] is True
    assert data["checks"]["high_light_pollution_direction_changes_as_expected"] is True
    assert runtime["removed_rollback"]["parameter_present"] is False
    assert runtime["removed_rollback"]["runtime_rollback_removed"] is True
    assert runtime["default_nsom"]["legacy_direction"] == "Sud"
    assert runtime["default_nsom"]["nsom_direction"] == "Nord-Est"
    assert runtime["default_nsom"]["matches_direct_service"] is True


def test_audit_preserves_payload_shape_and_display_score_semantics() -> None:
    data = generate_default_on_readiness_audit_data()

    assert data["checks"]["payload_shape_unchanged"] is True
    assert data["checks"]["no_nsom_fields_in_payload"] is True
    assert data["runtime_policy_evidence"]["payload"]["payload_keys_unchanged"] is True
    assert data["runtime_policy_evidence"]["payload"]["target_keys_unchanged"] is True
    assert data["runtime_policy_evidence"]["payload"]["nsom_fields_exposed"] is False
    assert data["display_score_semantics"]["keep_legacy_base_score_for_payload_compatibility"] is True
    assert data["display_score_semantics"]["score_monotonic_with_nsom_direction"] is False
    assert data["display_score_semantics"]["blocks_default_on_switch"] is False


def test_audit_keeps_ownership_boundaries_and_confidence_neutral() -> None:
    data = generate_default_on_readiness_audit_data()
    ownership = data["runtime_policy_evidence"]["ownership"]

    assert data["checks"]["candidate_base_is_observable"] is True
    assert data["checks"]["practical_target_value_not_used"] is True
    assert data["checks"]["observer_capability_not_used"] is True
    assert data["checks"]["session_viability_not_used"] is True
    assert data["checks"]["confidence_score_neutral"] is True
    assert data["checks"]["weather_and_equipment_not_in_direction_score"] is True
    assert ownership["uses_observable_target_value"] is True
    assert ownership["uses_practical_target_value"] is False
    assert ownership["uses_observer_capability"] is False
    assert ownership["uses_session_viability"] is False
    assert ownership["uses_recommendation_confidence"] is False
    assert ownership["accepts_confidence_parameter"] is False
    assert ownership["confidence_score_effect"] == 0.0


def test_audit_accepts_fallback_and_rollback_without_runtime_mutation() -> None:
    data = generate_default_on_readiness_audit_data()

    assert data["checks"]["fallback_policy_present"] is True
    assert data["fallback_policy"]["missing_sky_quality_fallback_present"] is True
    assert data["fallback_policy"]["service_failure_fallback_present"] is True
    assert data["fallback_policy"]["blocks_default_on_switch"] is False
    assert data["rollback_policy"]["constructor_rollback"] == "removed: AppController(use_nsom_sky_compass=False)"
    assert data["rollback_policy"]["legacy_path_preserved"] is False
    assert data["rollback_policy"]["rollback_parameter_present"] is False
    assert data["rollback_policy"]["runtime_rollback_removed"] is True
    assert data["runtime_policy_evidence"]["mutation"]["runtime_objects_mutated"] is False
    assert data["checks"]["runtime_objects_not_mutated"] is True


def test_sky_compass_default_on_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_default_on_readiness_audit_data()

    assert data["runtime_safety"] == {
        "current_flag_default_on": True,
        "default_off_policy_ready": True,
        "comparison_tooling_developer_only": True,
        "comparison_tooling_has_no_runtime_writes": True,
        "comparison_tooling_has_no_automatic_logging": True,
        "comparison_tooling_has_no_network": True,
        "comparison_tooling_has_no_qml_exposure": True,
        "sky_compass_runtime_unchanged_by_this_audit": True,
        "home_runtime_unchanged": True,
        "best_object_runtime_unchanged": True,
        "planner_runtime_unchanged": True,
        "qml_exposure_absent": True,
        "runtime_report_imports_absent": True,
        "runtime_objects_not_mutated": True,
    }
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_sky_compass_default_on_readiness_report_exists() -> None:
    report = Path(__file__).parents[2] / DEFAULT_ON_READINESS_AUDIT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Sky Compass NSOM Default-On Readiness Audit" in text
    assert "sky_compass_nsom_default_on_enabled" in text
    assert "NSOM_SKY_COMPASS_ENABLED = True" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
