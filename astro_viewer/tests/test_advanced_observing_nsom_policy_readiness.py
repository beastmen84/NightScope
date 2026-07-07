from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.advanced_observing_nsom_policy_readiness import (
    POLICY_READINESS_PATH,
    generate_policy_readiness_data,
    render_markdown_report,
)


def test_policy_readiness_data_is_deterministic_strict_json_and_developer_only() -> None:
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
        "advanced_scores_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
        "sky_compass_changed": False,
        "source_report": "docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md",
        "policy_report_path": "docs/ADVANCED_OBSERVING_NSOM_POLICY_READINESS.md",
    }


def test_policy_readiness_verdict_allows_default_off_path_but_not_runtime_change() -> None:
    data = generate_policy_readiness_data()

    assert data["readiness"]["verdict"] == "ready_for_default_off_advanced_observing_nsom_path"
    assert data["readiness"]["ready_for_default_off_path"] is True
    assert data["readiness"]["runtime_behaviour_changed_by_this_review"] is False
    assert data["readiness"]["explicit_legacy_default"] == (
        "AdvancedObservingService.scores(...) remains unchanged"
    )
    assert data["blockers"] == []
    assert data["checks"]["runtime_scores_unchanged_by_review"] is True


def test_policy_decision_log_covers_required_advanced_observing_policies() -> None:
    data = generate_policy_readiness_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert set(decisions) == {
        "advanced_observing_role",
        "session_viability_policy",
        "planetary_seeing_policy",
        "planetary_moon_policy",
        "deep_sky_target_class_policy",
        "weather_cap_policy",
        "observer_capability_policy",
        "confidence_policy",
    }
    assert all(decision["blocks_default_off_path"] is False for decision in decisions.values())
    assert all(decision["tuning_required"] is False for decision in decisions.values())
    assert decisions["observer_capability_policy"]["status"] == "deferred_non_blocking"
    assert decisions["deep_sky_target_class_policy"]["preserve_target_class_components"] is True
    assert data["checks"]["required_policy_decisions_recorded"] is True
    assert data["checks"]["policy_decisions_do_not_block_default_off"] is True


def test_session_viability_and_confidence_remain_parallel_metadata() -> None:
    data = generate_policy_readiness_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    session = decisions["session_viability_policy"]
    confidence = decisions["confidence_policy"]

    assert session["affected_nsom_layer"] == "session"
    assert "separate" in session["decision"]
    assert confidence["affected_nsom_layer"] == "confidence"
    assert confidence["score_path"] == "parallel_metadata"
    assert confidence["score_effect"] == 0.0
    assert data["checks"]["confidence_score_neutral"] is True
    assert data["comparison_evidence"]["confidence_score_effect"] == 0.0


def test_policy_readiness_uses_comparison_report_as_evidence_without_score_replacement() -> None:
    data = generate_policy_readiness_data()
    evidence = data["comparison_evidence"]

    assert evidence["scenario_count"] == 8
    assert evidence["category_row_count"] == 16
    assert evidence["semantic_recommendation"] == "presentation diagnostic / category quality surface"
    assert evidence["runtime_score_replacement_ready"] is False
    assert any("weather/session" in item for item in data["comparison_summary"]["main_mismatches"])


def test_policy_readiness_has_no_runtime_or_qml_wiring() -> None:
    data = generate_policy_readiness_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_exposure_absent"] is True
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_advanced_observing_policy_readiness_report_exists() -> None:
    report = Path(__file__).parents[2] / POLICY_READINESS_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Advanced Observing NSOM Policy Readiness" in text
    assert "ready_for_default_off_advanced_observing_nsom_path" in text
    assert "NSOM_ADVANCED_OBSERVING_ENABLED = False" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
