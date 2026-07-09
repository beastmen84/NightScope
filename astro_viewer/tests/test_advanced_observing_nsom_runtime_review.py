from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.advanced_observing_nsom_runtime_review import (
    RUNTIME_REVIEW_PATH,
    generate_runtime_review_data,
    render_markdown_report,
)


def test_runtime_review_data_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_runtime_review_data()
    second = generate_runtime_review_data()

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
        "planner_changed_by_default": False,
        "sky_compass_changed": False,
        "source_report": "docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md",
        "policy_report": "docs/ADVANCED_OBSERVING_NSOM_POLICY_READINESS.md",
        "runtime_review_report": "docs/ADVANCED_OBSERVING_NSOM_RUNTIME_REVIEW.md",
        "scenario_count": 8,
    }


def test_runtime_review_keeps_flag_off_and_blocks_default_on_switch() -> None:
    data = generate_runtime_review_data()

    assert data["readiness"]["verdict"] == "not_ready_for_default_on_switch"
    assert data["readiness"]["default_flag"] == "NSOM_ADVANCED_OBSERVING_ENABLED = True"
    assert data["readiness"]["default_flag_enabled"] is True
    assert data["readiness"]["ready_for_default_on_switch"] is False
    assert data["readiness"]["forced_on_path_safe_to_keep"] is True
    assert data["readiness"]["runtime_behaviour_changed_by_this_review"] is False
    assert data["default_on_blockers"] == [
        "advanced-observing-downstream-consumer-policy",
        "advanced-observing-score-label-policy",
        "advanced-observing-blocked-session-display-policy",
    ]


def test_runtime_review_characterizes_forced_on_score_policy() -> None:
    data = generate_runtime_review_data()
    scenarios = {scenario["scenario_id"]: scenario for scenario in data["scenarios"]}
    dark = scenarios["A01_good_session"]
    blocked = scenarios["A03_blocked_session"]
    bright_moon = scenarios["A04_bright_moon"]
    high_lp = scenarios["A05_high_light_pollution"]
    low_confidence = scenarios["A08_low_confidence"]

    assert data["checks"]["forced_on_changes_scores"] is True
    assert data["checks"]["payload_shape_compatible"] is True
    assert data["checks"]["strict_confidence_neutrality"] is True
    assert data["checks"]["blocked_session_outside_category_values"] is True
    assert data["checks"]["planetary_background_protected"] is True
    assert data["checks"]["deep_sky_background_sensitive"] is True
    assert blocked["nsom_forced_on_scores"]["planetary_score"] == dark["nsom_forced_on_scores"][
        "planetary_score"
    ]
    assert blocked["legacy_scores"]["planetary_score"] < dark["legacy_scores"]["planetary_score"]
    assert bright_moon["nsom_forced_on_scores"]["planetary_score"] == dark["nsom_forced_on_scores"][
        "planetary_score"
    ]
    assert high_lp["nsom_forced_on_scores"]["planetary_score"] == dark["nsom_forced_on_scores"][
        "planetary_score"
    ]
    assert bright_moon["nsom_forced_on_scores"]["deep_sky_score"] < dark["nsom_forced_on_scores"][
        "deep_sky_score"
    ]
    assert low_confidence["confidence_value"] < dark["confidence_value"]
    assert low_confidence["nsom_forced_on_scores"]["planetary_score"] == dark["nsom_forced_on_scores"][
        "planetary_score"
    ]


def test_runtime_review_surfaces_downstream_advanced_score_consumers() -> None:
    data = generate_runtime_review_data()
    downstream = data["downstream_consumer_evidence"]

    assert downstream == {
        "qml_reads_advanced_scores": True,
        "controller_passes_advanced_scores_to_planner": True,
        "planner_consumes_advanced_scores": True,
        "controller_passes_advanced_scores_to_notifications": False,
        "notifications_consume_advanced_scores": False,
    }
    assert data["checks"]["downstream_consumers_share_advanced_scores"] is True
    assert "advanced-observing-downstream-consumer-policy" in data["default_on_blockers"]


def test_runtime_review_has_no_runtime_report_wiring_or_qml_exposure() -> None:
    data = generate_runtime_review_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_exposure_absent"] is True
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_advanced_observing_runtime_review_report_exists() -> None:
    report = Path(__file__).parents[2] / RUNTIME_REVIEW_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Advanced Observing NSOM Runtime Review" in text
    assert "not_ready_for_default_on_switch" in text
    assert "advanced-observing-downstream-consumer-policy" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
