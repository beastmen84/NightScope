from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.advanced_observing_nsom_presentation_readiness import (
    PRESENTATION_READINESS_PATH,
    generate_presentation_readiness_data,
    render_markdown_report,
)


def test_presentation_readiness_data_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_presentation_readiness_data()
    second = generate_presentation_readiness_data()

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
        "source_report": "docs/ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY.md",
        "presentation_readiness_report": "docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_READINESS.md",
    }


def test_presentation_readiness_blocks_default_on_until_presentation_contract_exists() -> None:
    data = generate_presentation_readiness_data()

    assert data["readiness"]["verdict"] == "not_ready_for_advanced_observing_nsom_default_on"
    assert data["readiness"]["ready_for_default_on_switch"] is False
    assert data["readiness"]["default_flag"] == "NSOM_ADVANCED_OBSERVING_ENABLED = False"
    assert data["readiness"]["default_flag_currently_enabled"] is False
    assert data["readiness"]["requires_separate_flag_change"] is True
    assert data["readiness"]["consumer_split_resolved"] is True
    assert "advanced-observing-nsom-presentation-contract" in data["default_on_blockers"]
    assert "advanced-observing-score-label-semantics" in data["default_on_blockers"]


def test_presentation_decisions_keep_legacy_cards_and_hide_nsom_snapshot() -> None:
    data = generate_presentation_readiness_data()
    decisions = {decision["decision_id"]: decision for decision in data["presentation_decisions"]}

    assert decisions["legacy_advanced_scores_cards"]["blocks_default_on"] is False
    assert decisions["legacy_advanced_scores_cards"]["status"] == "accepted_current_runtime_contract"
    assert decisions["nsom_snapshot_visibility"]["status"] == "hidden_internal_only"
    assert decisions["nsom_snapshot_visibility"]["blocks_default_on"] is True
    assert decisions["nsom_presentation_contract"]["status"] == "needs_design_before_default_on"
    assert decisions["score_label_semantics"]["status"] == "needs_copy_policy_before_default_on"
    assert decisions["downstream_consumer_split"]["status"] == "resolved"
    assert decisions["confidence_policy"]["score_effect"] == 0.0


def test_presentation_evidence_shows_hidden_snapshot_has_no_qml_effect() -> None:
    data = generate_presentation_readiness_data()
    evidence = data["presentation_evidence"]

    assert evidence["qml_reads_existing_advanced_scores"] is True
    assert evidence["qml_reads_nsom_advanced_observing_snapshot"] is False
    assert evidence["forced_on_nsom_snapshot_differs_from_legacy"] is True
    assert evidence["forced_on_nsom_snapshot_has_presentation_effect"] is False
    assert evidence["hidden_snapshot_blocks_meaningful_default_on"] is True
    assert evidence["public_payload_shape_unchanged"] is True
    assert set(evidence["public_advanced_scores_payload_keys"]) == {
        "planetary_score",
        "deep_sky_score",
        "planetary_label",
        "deep_sky_label",
        "explanation",
        "planetaryScore",
        "deepSkyScore",
        "planetaryLabel",
        "deepSkyLabel",
    }


def test_presentation_readiness_keeps_consumer_split_and_confidence_neutral() -> None:
    data = generate_presentation_readiness_data()

    assert data["downstream_summary"]["consumer_split_implemented"] is True
    assert data["checks"]["downstream_consumer_split_resolved"] is True
    assert data["checks"]["confidence_score_neutral"] is True
    assert data["presentation_evidence"]["confidence_score_neutral"] is True
    assert data["presentation_evidence"]["confidence_score_effect"] == 0.0


def test_presentation_readiness_has_no_runtime_or_qml_wiring() -> None:
    data = generate_presentation_readiness_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_nsom_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged"] is True
    assert data["static_wiring_checks"]["qml_nsom_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["controller_internal_snapshot_present"] is True
    assert data["static_wiring_checks"]["controller_public_nsom_property_present"] is False


def test_checked_in_advanced_observing_presentation_readiness_report_exists() -> None:
    report = Path(__file__).parents[2] / PRESENTATION_READINESS_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Advanced Observing NSOM Presentation Readiness" in text
    assert "not_ready_for_advanced_observing_nsom_default_on" in text
    assert "advanced-observing-nsom-presentation-contract" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
