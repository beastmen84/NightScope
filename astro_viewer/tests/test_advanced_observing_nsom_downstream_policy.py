from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.advanced_observing_nsom_downstream_policy import (
    DOWNSTREAM_POLICY_PATH,
    generate_downstream_policy_data,
    render_markdown_report,
)


def test_downstream_policy_data_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_downstream_policy_data()
    second = generate_downstream_policy_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "advanced_scores_changed_by_default": False,
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
        "notifications_changed": False,
        "sky_compass_changed": False,
        "runtime_review_report": "docs/ADVANCED_OBSERVING_NSOM_RUNTIME_REVIEW.md",
        "downstream_policy_report": "docs/ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY.md",
    }


def test_downstream_policy_keeps_flag_off_and_blocks_default_on() -> None:
    data = generate_downstream_policy_data()

    assert data["readiness"]["verdict"] == "not_ready_for_advanced_observing_nsom_default_on"
    assert data["readiness"]["default_flag"] == "NSOM_ADVANCED_OBSERVING_ENABLED = False"
    assert data["readiness"]["ready_for_default_on_switch"] is False
    assert data["readiness"]["runtime_behaviour_changed_by_this_policy"] is False
    assert data["readiness"]["forced_on_path_safe_to_keep"] is True
    assert data["checks"]["default_flag_still_off"] is True
    assert data["checks"]["runtime_behaviour_unchanged"] is True


def test_downstream_policy_records_required_consumer_decisions() -> None:
    data = generate_downstream_policy_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert set(decisions) == {
        "shared_advanced_scores_contract",
        "planner_consumer_policy",
        "notification_consumer_policy",
        "qml_display_policy",
        "confidence_policy",
        "home_best_object_sky_compass_policy",
    }
    assert decisions["planner_consumer_policy"]["blocks_default_on"] is True
    assert decisions["notification_consumer_policy"]["blocks_default_on"] is True
    assert decisions["qml_display_policy"]["blocks_default_on"] is True
    assert decisions["confidence_policy"]["score_effect"] == 0.0
    assert decisions["home_best_object_sky_compass_policy"]["runtime_changed"] is False
    assert data["checks"]["required_decisions_recorded"] is True
    assert "advanced-observing-planner-consumer-policy" in data["default_on_blockers"]
    assert "advanced-observing-notification-consumer-policy" in data["default_on_blockers"]


def test_notification_policy_evidence_shows_blocked_session_risk() -> None:
    data = generate_downstream_policy_data()
    evidence = data["notification_evidence"]

    assert evidence["legacy_blocked_scores"]["planetary_score"] < 76
    assert evidence["legacy_blocked_scores"]["deep_sky_score"] < 76
    assert evidence["legacy_blocked_titles"] == []
    assert evidence["nsom_blocked_scores"]["planetary_score"] >= 76
    assert evidence["nsom_blocked_scores"]["deep_sky_score"] >= 76
    assert "Condizioni planetarie favorevoli" in evidence["nsom_blocked_titles"]
    assert "Finestra cielo profondo utile" in evidence["nsom_blocked_titles"]
    assert evidence["nsom_triggers_favourable_under_blocked_session"] is True
    assert data["checks"]["notification_blocked_session_risk_visible"] is True


def test_planner_policy_evidence_shows_advanced_score_factor_risk() -> None:
    data = generate_downstream_policy_data()
    evidence = data["planner_evidence"]

    assert evidence["planner_uses_advanced_scores_as_atmospheric_transparency"] is True
    assert evidence["poor_weather_legacy_category_factor"] != evidence[
        "poor_weather_nsom_category_factor"
    ]
    assert evidence["legacy_planner_score"] != evidence["nsom_planner_score"]
    assert evidence["planner_score_changes_with_forced_on_nsom_scores"] is True
    assert evidence["duplicate_sky_or_session_ownership_risk"] is True
    assert data["checks"]["planner_score_risk_visible"] is True


def test_downstream_policy_keeps_confidence_neutral_and_runtime_unwired() -> None:
    data = generate_downstream_policy_data()

    assert data["checks"]["confidence_score_neutral"] is True
    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_exposure_absent"] is True
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_advanced_observing_downstream_policy_report_exists() -> None:
    report = Path(__file__).parents[2] / DOWNSTREAM_POLICY_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Advanced Observing NSOM Downstream Policy" in text
    assert "not_ready_for_advanced_observing_nsom_default_on" in text
    assert "advanced-observing-planner-consumer-policy" in text
    assert "advanced-observing-notification-consumer-policy" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
