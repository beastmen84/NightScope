from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.advanced_observing_nsom_qml_presentation_policy import (
    QML_PRESENTATION_POLICY_PATH,
    generate_qml_presentation_policy_data,
    render_markdown_report,
)


def test_qml_presentation_policy_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_qml_presentation_policy_data()
    second = generate_qml_presentation_policy_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": True,
        "visible_ui_exposure": False,
        "advanced_scores_changed_by_default": False,
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
        "notifications_changed": False,
        "sky_compass_changed": False,
        "runtime_behaviour_changed": False,
        "source_report": "docs/ADVANCED_OBSERVING_NSOM_QML_EXPOSURE_READINESS.md",
        "qml_presentation_policy_report": "docs/ADVANCED_OBSERVING_NSOM_QML_PRESENTATION_POLICY.md",
    }


def test_qml_presentation_policy_is_applied_to_read_only_property_without_visible_ui() -> None:
    data = generate_qml_presentation_policy_data()

    assert data["readiness"]["verdict"] == (
        "advanced_observing_nsom_qml_policy_applied_read_only_property"
    )
    assert data["readiness"]["policy_status"] == "applied_to_read_only_property"
    assert data["readiness"]["policy_covers_1_8_12_blockers"] is True
    assert data["readiness"]["ready_for_runtime_qml_exposure"] is True
    assert data["readiness"]["ready_for_user_visible_ui"] is False
    assert data["readiness"]["ready_for_separate_read_only_property_step"] is True
    assert data["readiness"]["default_flag"] == "NSOM_ADVANCED_OBSERVING_ENABLED = False"
    assert data["readiness"]["runtime_behaviour_changed_by_this_policy"] is False

    source_blockers = set(data["source_readiness_summary"]["default_on_blockers"])
    assert "advanced-observing-qml-property-missing" not in source_blockers
    assert data["checks"]["policy_covers_source_blockers"] is True
    assert "advanced-observing-read-only-qml-property-not-implemented" not in data[
        "remaining_items_before_runtime_qml_exposure"
    ]


def test_qml_policy_defines_future_property_lifecycle_without_new_signal() -> None:
    data = generate_qml_presentation_policy_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert decisions["future_qml_property_name"]["future_property"] == "advancedObservingNsom"
    assert decisions["future_qml_property_name"]["current_property"] == "advancedScores"
    assert decisions["future_qml_property_name"]["implemented_in_this_step"] is True
    assert decisions["notify_signal_lifecycle"]["notify_signal"] == "weatherChanged"
    assert decisions["notify_signal_lifecycle"]["new_signal_required"] is False
    assert decisions["notify_signal_lifecycle"]["runtime_source"] == "_advanced_observing_nsom_presentation"
    assert decisions["notify_signal_lifecycle"]["recompute_on_property_read"] is False

    assert data["checks"]["future_read_only_property_policy_defined"] is True
    assert data["checks"]["future_read_only_property_wired"] is True
    assert data["checks"]["existing_weather_changed_available"] is True
    assert data["checks"]["new_signal_not_wired"] is True
    assert data["static_wiring_checks"]["controller_public_signal_present"] is False


def test_qml_policy_keeps_copy_and_score_semantics_separate_from_legacy_scores() -> None:
    data = generate_qml_presentation_policy_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    copy = decisions["visible_ui_copy_policy"]
    label = decisions["score_label_semantics"]
    visual = decisions["visual_placement_policy"]
    confidence = decisions["confidence_metadata_policy"]

    assert copy["visible_ui_approved_now"] is False
    assert copy["copy_delivery"] == "localization_keys_or_existing_translation_layer"
    assert copy["title_key"] == "advanced_observing_nsom.title"
    assert label["display_label"] == "NSOM category diagnostic value"
    assert label["not_legacy_actionability"] is True
    assert label["not_planner_score"] is True
    assert label["not_notification_threshold"] is True
    assert label["confidence_score_effect"] == 0.0
    assert confidence["confidence_placement"] == "metadata_outside_category_value"
    assert confidence["confidence_score_effect"] == 0.0
    assert visual["replace_advanced_scores_cards"] is False
    assert visual["allowed_visible_surface"] == "separate_diagnostic_or_advanced_section"


def test_qml_policy_verifies_property_wiring_without_visible_qml_usage() -> None:
    data = generate_qml_presentation_policy_data()

    assert data["checks"]["visible_qml_usage_absent"] is True
    assert data["checks"]["future_property_wired"] is True
    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["private_projection_available"] is True
    assert data["checks"]["advanced_scores_remains_current_qml_contract"] is True
    assert data["checks"]["qml_reads_existing_advanced_scores"] is True
    assert data["checks"]["no_runtime_behaviour_change"] is True
    assert data["static_wiring_checks"]["qml_nsom_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["controller_public_property_present"] is True
    assert data["static_wiring_checks"]["controller_private_projection_present"] is True
    assert data["static_wiring_checks"]["advanced_scores_property_uses_weather_changed"] is True


def test_qml_policy_rollback_and_remaining_items_are_explicit() -> None:
    data = generate_qml_presentation_policy_data()
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert decisions["rollback_policy"]["constructor_rollback"] == (
        "AppController(use_nsom_advanced_observing=False)"
    )
    assert decisions["rollback_policy"]["future_property_when_disabled"] == {}
    assert data["remaining_items_before_runtime_qml_exposure"] == [
        "advanced-observing-visible-ui-design-not-approved",
        "advanced-observing-default-flag-still-off",
    ]


def test_checked_in_advanced_observing_qml_presentation_policy_report_exists() -> None:
    report = Path(__file__).parents[2] / QML_PRESENTATION_POLICY_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Advanced Observing NSOM QML Presentation Policy" in text
    assert "advanced_observing_nsom_qml_policy_applied_read_only_property" in text
    assert "advancedObservingNsom" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
