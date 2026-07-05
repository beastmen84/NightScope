from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.best_object_nsom_readiness_audit import (
    READINESS_AUDIT_PATH,
    generate_readiness_audit_data,
    render_markdown_report,
)


def test_best_object_readiness_audit_is_strict_json_and_developer_only() -> None:
    data = generate_readiness_audit_data()

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
        "audit_report_path": "docs/BEST_OBJECT_NSOM_READINESS_AUDIT.md",
    }


def test_best_object_readiness_accepts_policy_before_default_off_path() -> None:
    data = generate_readiness_audit_data()

    assert data["readiness"]["verdict"] == "ready_for_default_off_path"
    assert data["readiness"]["ready_for_default_off_path"] is True
    assert data["readiness"]["runtime_path_exists"] is False
    assert data["readiness"]["runtime_behaviour_changed"] is False
    assert data["readiness"]["recommendation"] == (
        "review_policy_decisions_then_add_default_off_best_object_nsom_path"
    )
    assert data["blockers"] == []


def test_blocked_session_is_non_actionable_and_diagnostic_orders_are_not_recommendations() -> None:
    data = generate_readiness_audit_data()
    blocked = data["policy_review"]["blocked_session_evidence"]
    policy = next(
        decision
        for decision in data["policy_review"]["decisions"]
        if decision["policy_id"] == "best-object-blocked-session-non-actionable-policy"
    )

    assert policy["status"] == "accepted"
    assert policy["blocks_default_off_path"] is False
    assert blocked["scenario_id"] == "B03_blocked_session"
    assert blocked["actionability"] == "non_actionable"
    assert blocked["legacy_weather_floor_still_ranks"] is True
    assert blocked["diagnostic_orders_are_recommendation_orders"] is False
    assert blocked["legacy_order"]
    assert blocked["observable_order"]
    assert blocked["practical_order"]


def test_semantic_target_rejects_pure_observable_and_pure_practical() -> None:
    data = generate_readiness_audit_data()
    semantic = data["semantic_migration_target"]

    assert semantic["recommended_future_nsom_concept"] == (
        "ObservationOpportunity with Home-specific presentation policy"
    )
    assert semantic["use_pure_observable_target_value"] is False
    assert semantic["use_pure_practical_target_value"] is False
    assert semantic["use_observation_opportunity_with_home_policy"] is True


def test_displayed_score_semantics_are_documented_for_default_off_path() -> None:
    data = generate_readiness_audit_data()
    display = data["display_score_semantics"]

    assert display["status"] == "accepted_for_default_off_experiment"
    assert display["keep_legacy_displayed_score_for_compatibility"] is True
    assert display["score_monotonic_with_proposed_nsom_order"] is False
    assert display["blocks_default_off_path"] is False
    assert "compatibility data" in display["future_runtime_policy"]


def test_confidence_remains_metadata_only_in_best_object_readiness_audit() -> None:
    data = generate_readiness_audit_data()

    assert data["policy_review"]["confidence_neutrality_verified"] is True
    confidence_policy = next(
        decision
        for decision in data["policy_review"]["decisions"]
        if decision["policy_id"] == "best-object-confidence-metadata-policy"
    )
    assert confidence_policy["status"] == "accepted"
    assert confidence_policy["blocks_default_off_path"] is False


def test_best_object_readiness_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_readiness_audit_data()

    assert data["runtime_safety"] == {
        "comparison_tooling_developer_only": True,
        "comparison_tooling_has_no_runtime_writes": True,
        "comparison_tooling_has_no_automatic_logging": True,
        "comparison_tooling_has_no_network": True,
        "comparison_tooling_has_no_qml_exposure": True,
        "best_object_runtime_unchanged": True,
        "recommended_deep_sky_runtime_unchanged": True,
        "planner_runtime_unchanged": True,
        "sky_compass_runtime_unchanged": True,
        "qml_exposure_absent": True,
        "runtime_report_imports_absent": True,
    }
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_best_object_readiness_audit_report_exists() -> None:
    report = Path(__file__).parents[2] / READINESS_AUDIT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Best Object NSOM Readiness Audit" in text
    assert "ready_for_default_off_path" in text
    assert "best-object-blocked-session-non-actionable-policy" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
