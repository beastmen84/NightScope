from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.sky_compass_nsom_policy_readiness import (
    POLICY_READINESS_PATH,
    generate_policy_readiness_data,
    render_markdown_report,
)


def test_sky_compass_policy_readiness_data_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_policy_readiness_data()
    second = generate_policy_readiness_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "sky_compass_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
        "source_report": "docs/SKY_COMPASS_NSOM_COMPARISON_REPORT.md",
        "policy_report_path": "docs/SKY_COMPASS_NSOM_POLICY_READINESS.md",
    }


def test_policy_readiness_verdict_allows_default_off_path_but_not_default_on() -> None:
    data = generate_policy_readiness_data()

    assert data["readiness"]["verdict"] == "ready_for_default_off_sky_compass_nsom_path"
    assert data["readiness"]["ready_for_default_off_path"] is True
    assert data["readiness"]["ready_for_default_on"] is False
    assert data["readiness"]["runtime_behaviour_changed_by_this_review"] is False
    assert data["readiness"]["explicit_legacy_default"] == "SkyCompassService.compass(...) remains unchanged"
    assert data["blockers"] == []
    assert data["checks"]["runtime_behaviour_unchanged_by_review"] is True


def test_policy_decision_log_covers_required_sky_compass_policies() -> None:
    data = generate_policy_readiness_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert set(decisions) == {
        "sky_compass_role",
        "candidate_base_policy",
        "context_boost_policy",
        "direction_concentration_policy",
        "practical_target_value_policy",
        "session_caution_policy",
        "missing_location_direction_policy",
        "qml_payload_policy",
        "fallback_policy",
        "confidence_policy",
    }
    assert all(decision["blocks_default_off_path"] is False for decision in decisions.values())
    assert all(decision["tuning_required"] is False for decision in decisions.values())
    assert decisions["candidate_base_policy"]["candidate_base"] == "ObservableTargetValue"
    assert decisions["practical_target_value_policy"]["status"] == "deferred_non_blocking"
    assert decisions["practical_target_value_policy"]["practical_target_value_used_for_default_off_score"] is False
    assert decisions["confidence_policy"]["score_path"] == "parallel_metadata"
    assert decisions["confidence_policy"]["score_effect"] == 0.0


def test_recommended_default_off_policy_is_not_pure_target_ranking() -> None:
    data = generate_policy_readiness_data()
    policy = data["recommended_default_off_policy"]

    assert policy["candidate_base"] == "ObservableTargetValue.value"
    assert "in_plan_bonus" in policy["direction_formula"]
    assert "best_object_bonus" in policy["direction_formula"]
    assert "target_presence_bonus" in policy["direction_formula"]
    assert policy["practical_target_value_use"] == "reference_only_for_1.9.x"
    assert policy["session_use"] == "caution_or_non_actionable_metadata_only"
    assert policy["confidence_use"] == "metadata_only_zero_score_effect"
    assert policy["qml_payload_policy"] == "preserve_existing_skyCompass_keys_no_nsom_fields"
    assert data["checks"]["default_off_policy_is_not_pure_target_ranking"] is True
    assert data["checks"]["candidate_base_is_observable_not_practical"] is True


def test_policy_readiness_uses_comparison_report_evidence() -> None:
    data = generate_policy_readiness_data()
    evidence = data["comparison_evidence"]

    assert evidence["scenario_count"] == 8
    assert evidence["row_count"] == 48
    assert evidence["direction_difference_count"] >= 1
    assert "S08_plan_best_boost" in evidence["scenarios_with_direction_difference"]
    assert evidence["confidence_score_effect"] == 0.0
    assert data["checks"]["comparison_report_has_direction_differences"] is True


def test_policy_readiness_keeps_session_confidence_and_fallback_safe() -> None:
    data = generate_policy_readiness_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert decisions["session_caution_policy"]["affected_nsom_layer"] == "session"
    assert "metadata" in decisions["session_caution_policy"]["decision"]
    assert decisions["confidence_policy"]["affected_nsom_layer"] == "confidence"
    assert decisions["confidence_policy"]["score_effect"] == 0.0
    assert "legacy SkyCompassService" in decisions["fallback_policy"]["decision"]
    assert data["checks"]["session_and_confidence_are_metadata"] is True
    assert data["checks"]["fallback_policy_recorded"] is True


def test_policy_readiness_has_no_runtime_or_qml_wiring() -> None:
    data = generate_policy_readiness_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_exposure_absent"] is True
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_sky_compass_policy_readiness_report_exists() -> None:
    report = Path(__file__).parents[2] / POLICY_READINESS_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Sky Compass NSOM Policy Readiness" in text
    assert "ready_for_default_off_sky_compass_nsom_path" in text
    assert "ObservableTargetValue.value" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
