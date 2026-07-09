from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_rollback_cleanup_policy_audit import (
    REPORT_PATH,
    generate_rollback_cleanup_policy_audit_data,
    render_markdown_report,
)


def test_rollback_cleanup_policy_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_rollback_cleanup_policy_audit_data()
    second = generate_rollback_cleanup_policy_audit_data()

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
    assert first["metadata"]["runtime_behaviour_changed_by_this_audit"] is False
    assert first["metadata"]["rollback_flags_removed_by_this_audit"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_rollback_cleanup_policy_recommends_removing_internal_rollbacks_next() -> None:
    data = generate_rollback_cleanup_policy_audit_data()
    surfaces = {surface["surface"]: surface for surface in data["rollback_surfaces"]}

    assert data["readiness"]["verdict"] == (
        "rollback_cleanup_policy_set_remove_internal_rollbacks"
    )
    assert data["readiness"]["rollback_cleanup_recommended"] is True
    assert data["readiness"]["remove_rollbacks_in_this_audit"] is False
    assert data["readiness"]["safe_to_implement_cleanup_next"] is True
    assert data["readiness"]["public_compatibility_required"] is False
    assert data["blockers"] == []

    assert set(surfaces) == {
        "Planner",
        "Home recommendedDeepSky",
        "Best Object",
        "Advanced Observing backend",
        "Sky Compass",
        "Detail/Object internal payload",
    }
    assert all(
        surface["recommendation"] == "remove_internal_rollback_next"
        for surface in surfaces.values()
    )
    assert all(
        surface["public_compatibility_contract"] is False
        for surface in surfaces.values()
    )
    assert all(surface["rollback_parameter_present"] is True for surface in surfaces.values())


def test_rollback_cleanup_policy_records_required_decisions() -> None:
    data = generate_rollback_cleanup_policy_audit_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert decisions["remove_internal_rollback_flags"]["status"] == (
        "accepted_for_next_implementation"
    )
    assert decisions["public_compatibility_exception"]["status"] == "not_required"
    assert decisions["visible_ui_explanation_dependency"]["status"] == (
        "cleanup_before_ui_explanation"
    )
    assert decisions["runtime_change_policy"]["status"] == "not_in_this_audit"
    assert all(decision["blocks_cleanup"] is False for decision in data["policy_decisions"])
    assert data["checks"]["policy_blocks_no_cleanup"] is True


def test_rollback_cleanup_policy_plan_defers_runtime_changes_to_followup() -> None:
    data = generate_rollback_cleanup_policy_audit_data()
    phases = {phase["phase"]: phase for phase in data["implementation_plan"]}
    sequence = [item["step"] for item in data["recommended_sequence"]]

    assert phases["1.13.8"]["runtime_change_allowed_by_this_audit"] is False
    assert "Remove rollback constructor parameters" in phases["1.13.8"]["scope"]
    assert phases["post-cleanup-review"]["runtime_change_allowed_by_this_audit"] is False
    assert data["checks"]["all_rollback_surfaces_recommended_for_removal"] is True
    assert sequence == [
        "Review 1.13.7",
        "1.13.8 Remove internal legacy rollback paths",
        "Review 1.13.8",
    ]


def test_rollback_cleanup_policy_has_no_runtime_or_qml_wiring() -> None:
    data = generate_rollback_cleanup_policy_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_audit"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_rollback_cleanup_policy_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Rollback Cleanup Policy Audit" in text
    assert "rollback_cleanup_policy_set_remove_internal_rollbacks" in text
    assert "1.13.8 Remove internal legacy rollback paths" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
