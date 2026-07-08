from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.detail_nsom_readiness_audit import (
    READINESS_AUDIT_PATH,
    generate_readiness_audit_data,
    render_markdown_report,
)


def test_detail_nsom_readiness_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_readiness_audit_data()
    second = generate_readiness_audit_data()

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
        "source_report": "docs/DETAIL_OBJECT_NSOM_COMPARISON_REPORT.md",
        "audit_report_path": "docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md",
    }


def test_detail_nsom_readiness_blocks_default_off_path_until_policy_contract_exists() -> None:
    data = generate_readiness_audit_data()

    assert data["readiness"]["verdict"] == "not_ready_for_default_off_detail_nsom_path"
    assert data["readiness"]["ready_for_default_off_path"] is False
    assert data["readiness"]["runtime_path_exists"] is False
    assert data["readiness"]["ready_for_visible_ui"] is False
    assert data["readiness"]["runtime_behaviour_changed_by_this_audit"] is False
    assert data["readiness"]["recommended_next_step"] == (
        "1.10.2 Detail/Object source and display policy contract"
    )
    assert data["blockers"] == [
        "detail-source-policy-unresolved",
        "detail-displayed-score-semantics-unresolved",
        "detail-payload-contract-not-defined",
    ]


def test_source_policy_review_captures_observing_and_catalogue_semantic_split() -> None:
    data = generate_readiness_audit_data()
    policy = data["source_policy_review"]

    assert policy["status"] == "needs_policy_decision"
    assert policy["blocks_default_off_path"] is True
    assert policy["observing_source_policy"] == "observing_detail_moon_adjusted_copy"
    assert policy["catalogue_source_policy"] == "catalogue_detail_raw_object"
    assert policy["observing_bright_moon_display_score"] < policy["catalogue_bright_moon_display_score"]
    assert policy["comparable_observable_values"] is True
    assert "source-specific legacy display score semantics" in policy["decision_needed"]


def test_displayed_score_and_payload_contract_are_explicit_blockers() -> None:
    data = generate_readiness_audit_data()
    display = data["display_score_semantics"]
    payload = data["payload_contract_review"]

    assert display["status"] == "needs_contract"
    assert display["blocks_default_off_path"] is True
    assert display["keep_legacy_displayed_score_for_compatibility"] is True
    assert display["score_monotonic_with_nsom_values"] is False
    assert display["observing_observable_value"] == display["catalogue_observable_value"]
    assert display["observing_display_score"] != display["catalogue_display_score"]

    assert payload["status"] == "not_defined"
    assert payload["blocks_default_off_path"] is True
    assert payload["preserve_existing_selected_object_payload"] is True
    assert payload["add_nsom_fields_now"] is False
    assert payload["qml_payload_shape_change_allowed"] is False


def test_confidence_is_accepted_as_metadata_only() -> None:
    data = generate_readiness_audit_data()
    confidence = data["confidence_review"]

    assert confidence["status"] == "accepted"
    assert confidence["blocks_default_off_path"] is False
    assert confidence["low_confidence_value"] < confidence["high_confidence_value"]
    assert confidence["observable_delta"] == 0.0
    assert confidence["practical_delta"] == 0.0
    assert confidence["legacy_display_delta"] == 0.0
    assert confidence["score_factor"] is False
    assert confidence["score_effect"] == 0.0


def test_detail_nsom_readiness_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_readiness_audit_data()

    assert data["runtime_safety"] == {
        "comparison_tooling_developer_only": True,
        "comparison_tooling_has_no_runtime_writes": True,
        "comparison_tooling_has_no_automatic_logging": True,
        "comparison_tooling_has_no_network": True,
        "comparison_tooling_has_no_qml_exposure": True,
        "selected_object_runtime_unchanged": True,
        "home_runtime_unchanged": True,
        "best_object_runtime_unchanged": True,
        "planner_runtime_unchanged": True,
        "sky_compass_runtime_unchanged": True,
        "controller_runtime_wiring_absent": True,
        "qml_exposure_absent": True,
        "runtime_report_imports_absent": True,
    }
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["controller_detail_comparison_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_detail_nsom_readiness_audit_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / READINESS_AUDIT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Detail/Object NSOM Readiness Audit" in text
    assert "not_ready_for_default_off_detail_nsom_path" in text
    assert "detail-source-policy-unresolved" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
