from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.detail_nsom_default_on_readiness_audit import (
    DEFAULT_ON_READINESS_AUDIT_PATH,
    generate_default_on_readiness_audit_data,
    render_markdown_report,
)


def test_detail_nsom_default_on_readiness_audit_is_deterministic_strict_json_and_developer_only() -> None:
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
        "selected_object_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
        "sky_compass_changed": False,
        "source_report": "docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md",
        "audit_report_path": "docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
    }


def test_detail_nsom_default_on_readiness_verdict_confirms_default_on_enabled() -> None:
    data = generate_default_on_readiness_audit_data()

    assert data["readiness"] == {
        "verdict": "detail_object_nsom_default_on_enabled",
        "ready_for_default_on_switch": True,
        "default_flag": "NSOM_DETAIL_OBJECT_ENABLED = True",
        "default_flag_currently_enabled": True,
        "default_flag_enabled_by_this_commit": True,
        "requires_separate_flag_change": False,
        "runtime_behaviour_changed_by_this_audit": False,
        "explicit_legacy_rollback": "removed: AppController(use_nsom_detail_object=False)",
        "explicit_nsom_path": "default AppController()",
        "recommended_switch_change": "already enabled",
        "reason": (
            "The Detail/Object NSOM default-on switch is active with runtime rollback removed, "
            "preserves `selectedObject`, keeps session/confidence metadata-only "
            "and has no QML or report runtime wiring."
        ),
    }
    assert data["blockers"] == []
    assert all(value is True for value in data["checks"].values())


def test_detail_nsom_default_on_runtime_policy_preserves_selected_object() -> None:
    data = generate_default_on_readiness_audit_data()
    runtime = data["runtime_policy_evidence"]

    assert runtime["constructor"]["runtime_rollback_removed"] is True

    observing = runtime["observing_source"]
    assert observing["schema_version"] == "detail-object-nsom-runtime-v1"
    assert observing["legacy_display_policy"] == "observing_detail_moon_adjusted_copy"
    assert observing["selected_object_formula"] == "_object_to_qml(_moon_adjusted_object(selected_object))"
    assert observing["selected_object_unchanged"] is True
    assert observing["selected_object_keys_unchanged"] is True
    assert observing["nsom_fields_in_selected_object"] == []
    assert observing["observable_value"] != observing["selected_score"]

    catalogue = runtime["catalogue_source"]
    assert catalogue["schema_version"] == "detail-object-nsom-runtime-v1"
    assert catalogue["legacy_display_policy"] == "catalogue_detail_raw_object"
    assert catalogue["selected_object_formula"] == "_object_to_qml(selected_object)"
    assert catalogue["selected_object_unchanged"] is True
    assert catalogue["selected_object_keys_unchanged"] is True
    assert catalogue["nsom_fields_in_selected_object"] == []


def test_detail_nsom_default_on_keeps_session_and_confidence_metadata_only() -> None:
    data = generate_default_on_readiness_audit_data()
    session = data["runtime_policy_evidence"]["session"]
    confidence = data["runtime_policy_evidence"]["confidence"]

    assert session["blocked_state"] == "blocked"
    assert session["blocked_value"] == 0.0
    assert session["score_factor"] is False
    assert session["observable_unchanged"] is True
    assert session["practical_unchanged"] is True

    assert confidence["low_value"] < confidence["high_value"]
    assert confidence["score_factor"] is False
    assert confidence["score_effect"] == 0.0
    assert confidence["observable_unchanged"] is True
    assert confidence["practical_unchanged"] is True


def test_detail_nsom_default_on_missing_input_and_display_policies_are_non_blocking() -> None:
    data = generate_default_on_readiness_audit_data()
    missing = data["missing_input_policy"]
    display = data["display_score_semantics"]
    rollback = data["rollback_policy"]

    assert missing["status"] == "accepted"
    assert missing["missing_sky_quality_returns_empty_payload"] is True
    assert missing["missing_weather_returns_empty_payload"] is True
    assert missing["blocks_default_on_switch"] is False

    assert display["status"] == "accepted"
    assert display["keep_legacy_displayed_score_for_payload_compatibility"] is True
    assert display["score_monotonic_with_nsom_payload"] is False
    assert display["blocks_default_on_switch"] is False

    assert rollback["constructor_rollback"] == "removed: AppController(use_nsom_detail_object=False)"
    assert rollback["legacy_path_preserved"] is False
    assert rollback["rollback_parameter_present"] is False
    assert rollback["default_kwarg_is_flag"] is False
    assert rollback["runtime_rollback_removed"] is True
    assert rollback["blocks_default_on_switch"] is False


def test_detail_nsom_default_on_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_default_on_readiness_audit_data()

    assert data["runtime_safety"] == {
        "developer_only_audit": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure_absent": True,
        "runtime_report_imports_absent": True,
        "selected_object_payload_preserved": True,
        "nsom_fields_absent_from_selected_object": True,
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
        "sky_compass_changed": False,
        "default_off_readiness_has_no_blockers": True,
    }
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_detail_nsom_default_on_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / DEFAULT_ON_READINESS_AUDIT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Detail/Object NSOM Default-On Readiness Audit" in text
    assert "detail_object_nsom_default_on_enabled" in text
    assert "NSOM_DETAIL_OBJECT_ENABLED = True" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
