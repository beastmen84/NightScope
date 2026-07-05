from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.best_object_nsom_default_on_readiness_audit import (
    DEFAULT_ON_READINESS_AUDIT_PATH,
    generate_default_on_readiness_audit_data,
    render_markdown_report,
)


def test_best_object_default_on_readiness_audit_is_strict_json_and_developer_only() -> None:
    data = generate_default_on_readiness_audit_data()

    json.dumps(data, sort_keys=True, allow_nan=False)

    assert data["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "best_object_changed": False,
        "recommended_deep_sky_changed": False,
        "planner_changed": False,
        "sky_compass_changed": False,
        "source_report": "docs/BEST_OBJECT_NSOM_COMPARISON_REPORT.md",
        "default_off_readiness_report": "docs/BEST_OBJECT_NSOM_READINESS_AUDIT.md",
        "audit_report_path": "docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
    }


def test_best_object_default_on_readiness_verdict_requires_separate_flag_change() -> None:
    data = generate_default_on_readiness_audit_data()

    assert data["readiness"]["verdict"] == "ready_for_default_on_switch_pr"
    assert data["readiness"]["ready_for_default_on_switch"] is True
    assert data["readiness"]["default_flag"] == "NSOM_BEST_OBJECT_ENABLED = False"
    assert data["readiness"]["default_flag_currently_enabled"] is False
    assert data["readiness"]["requires_separate_flag_change"] is True
    assert data["readiness"]["runtime_behaviour_changed_by_this_audit"] is False
    assert data["readiness"]["explicit_legacy_rollback"] == "AppController(use_nsom_best_object=False)"
    assert data["readiness"]["recommended_switch_change"] == "set NSOM_BEST_OBJECT_ENABLED = True"
    assert data["blockers"] == []
    assert data["checks"]["default_flag_still_off_for_audit"] is True


def test_default_on_audit_accepts_blocked_session_as_non_actionable() -> None:
    data = generate_default_on_readiness_audit_data()
    blocked = data["runtime_policy_evidence"]["blocked_session"]

    assert data["checks"]["blocked_sessions_non_actionable"] is True
    assert data["checks"]["blocked_stable_order_not_recommendation"] is True
    assert blocked["selected_object_id"] is None
    assert blocked["all_scores_zero"] is True
    assert set(blocked["actionabilities"]) == {"non_actionable_hard_block"}
    assert blocked["stable_order_is_recommendation_order"] is False
    assert blocked["non_actionable_preserved_order"]
    assert blocked["preserved_order_is_recommendation_order"] is False


def test_default_on_audit_accepts_invisible_target_policy() -> None:
    data = generate_default_on_readiness_audit_data()
    invisible = data["runtime_policy_evidence"]["invisible_target"]

    assert data["checks"]["invisible_targets_non_actionable"] is True
    assert invisible["invisible_object_id"] == "hidden_galaxy"
    assert invisible["invisible_actionability"] == "non_actionable_invisible_target"
    assert invisible["invisible_selected"] is False
    assert invisible["selected_object_id"] == "open_cluster"


def test_default_on_audit_keeps_confidence_score_neutral() -> None:
    data = generate_default_on_readiness_audit_data()
    confidence = data["runtime_policy_evidence"]["confidence"]

    assert data["checks"]["confidence_score_neutral"] is True
    assert confidence["scores_equal"] is True
    assert confidence["confidence_values_differ"] is True
    assert confidence["score_effect"] == 0.0
    assert confidence["low_order"] == confidence["high_order"]
    assert confidence["low_scores"] == confidence["high_scores"]


def test_default_on_audit_documents_display_fallback_and_rollback_as_non_blocking() -> None:
    data = generate_default_on_readiness_audit_data()

    assert data["display_score_semantics"]["blocks_default_on_switch"] is False
    assert data["display_score_semantics"]["keep_legacy_base_score_for_payload_compatibility"] is True
    assert data["display_score_semantics"]["score_monotonic_with_nsom_order"] is False
    assert data["missing_sky_quality_policy"]["fallback_present"] is True
    assert data["missing_sky_quality_policy"]["blocks_default_on_switch"] is False
    assert data["rollback_policy"]["constructor_rollback"] == "AppController(use_nsom_best_object=False)"
    assert data["rollback_policy"]["legacy_path_preserved"] is True
    assert data["rollback_policy"]["blocks_default_on_switch"] is False


def test_default_on_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_default_on_readiness_audit_data()

    assert data["runtime_safety"] == {
        "current_flag_remains_default_off": True,
        "default_off_audit_ready": True,
        "comparison_tooling_developer_only": True,
        "comparison_tooling_has_no_runtime_writes": True,
        "comparison_tooling_has_no_automatic_logging": True,
        "comparison_tooling_has_no_network": True,
        "comparison_tooling_has_no_qml_exposure": True,
        "best_object_runtime_unchanged_by_this_audit": True,
        "recommended_deep_sky_runtime_unchanged": True,
        "planner_runtime_unchanged": True,
        "sky_compass_runtime_unchanged": True,
        "qml_exposure_absent": True,
        "runtime_report_imports_absent": True,
        "runtime_objects_not_mutated": True,
    }
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["runtime_policy_evidence"]["mutation"]["runtime_objects_mutated"] is False


def test_checked_in_best_object_default_on_readiness_report_exists() -> None:
    report = Path(__file__).parents[2] / DEFAULT_ON_READINESS_AUDIT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Best Object NSOM Default-On Readiness Audit" in text
    assert "ready_for_default_on_switch_pr" in text
    assert "NSOM_BEST_OBJECT_ENABLED = False" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
