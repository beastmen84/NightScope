from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.advanced_observing_nsom_qml_exposure_readiness import (
    QML_EXPOSURE_READINESS_PATH,
    generate_qml_exposure_readiness_data,
    render_markdown_report,
)


def test_qml_exposure_readiness_data_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_qml_exposure_readiness_data()
    second = generate_qml_exposure_readiness_data()

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
        "runtime_behaviour_changed": False,
        "source_report": "docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md",
        "qml_exposure_readiness_report": "docs/ADVANCED_OBSERVING_NSOM_QML_EXPOSURE_READINESS.md",
    }


def test_qml_exposure_readiness_keeps_public_qml_exposure_blocked() -> None:
    data = generate_qml_exposure_readiness_data()

    assert data["readiness"]["verdict"] == "advanced_observing_nsom_qml_exposure_not_ready"
    assert data["readiness"]["ready_for_qml_exposure"] is False
    assert data["readiness"]["ready_for_user_visible_ui"] is False
    assert data["readiness"]["default_flag"] == "NSOM_ADVANCED_OBSERVING_ENABLED = False"
    assert data["readiness"]["runtime_behaviour_changed_by_this_audit"] is False
    assert "advanced-observing-public-qml-property" in data["default_on_blockers"]
    assert "advanced-observing-visible-ui-copy" in data["default_on_blockers"]
    assert "advanced-observing-score-label-semantics" in data["default_on_blockers"]


def test_qml_exposure_decisions_record_copy_lifecycle_and_score_policy() -> None:
    data = generate_qml_exposure_readiness_data()
    decisions = {decision["decision_id"]: decision for decision in data["qml_exposure_decisions"]}

    assert decisions["internal_projection_safe_to_keep"]["blocks_qml_exposure"] is False
    assert decisions["public_qml_property"]["status"] == "blocked_until_lifecycle_policy"
    assert decisions["public_qml_property"]["blocks_qml_exposure"] is True
    assert decisions["visible_ui_copy"]["status"] == "blocked_until_copy_policy"
    assert decisions["score_label_semantics"]["status"] == "blocked_until_score_display_policy"
    assert decisions["legacy_advanced_scores_contract"]["blocks_qml_exposure"] is False
    assert decisions["confidence_metadata"]["score_effect"] == 0.0
    assert decisions["no_current_qml_wiring"]["status"] == "verified"


def test_qml_exposure_readiness_verifies_no_runtime_or_qml_wiring() -> None:
    data = generate_qml_exposure_readiness_data()

    assert data["checks"]["future_property_not_exposed"] is True
    assert data["checks"]["notify_signal_not_introduced"] is True
    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["no_runtime_behaviour_change"] is True
    assert data["static_wiring_checks"]["qml_nsom_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["controller_private_projection_present"] is True
    assert data["static_wiring_checks"]["controller_public_property_present"] is False
    assert data["static_wiring_checks"]["controller_public_signal_present"] is False
    assert data["static_wiring_checks"]["qml_reads_existing_advanced_scores"] is True


def test_qml_exposure_readiness_uses_contract_without_changing_confidence_or_consumers() -> None:
    data = generate_qml_exposure_readiness_data()
    summary = data["presentation_contract_summary"]

    assert summary["verdict"] == "advanced_observing_nsom_presentation_runtime_projected_not_qml_exposed"
    assert summary["payload_schema"] == "advanced_observing_nsom_presentation_v1"
    assert summary["future_qml_property"] == "advancedObservingNsom"
    assert summary["current_qml_property"] == "advancedScores"
    assert data["checks"]["contract_runtime_projection_available"] is True
    assert data["checks"]["advanced_scores_remains_current_qml_contract"] is True
    assert data["checks"]["confidence_score_neutral"] is True


def test_checked_in_advanced_observing_qml_exposure_readiness_report_exists() -> None:
    report = Path(__file__).parents[2] / QML_EXPOSURE_READINESS_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Advanced Observing NSOM QML Exposure Readiness" in text
    assert "advanced_observing_nsom_qml_exposure_not_ready" in text
    assert "advanced-observing-public-qml-property" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
