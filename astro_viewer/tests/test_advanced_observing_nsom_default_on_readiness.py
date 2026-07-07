from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.advanced_observing_nsom_default_on_readiness import (
    DEFAULT_ON_READINESS_PATH,
    generate_default_on_readiness_data,
    render_markdown_report,
)


def test_default_on_readiness_data_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_default_on_readiness_data()
    second = generate_default_on_readiness_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "visible_ui_exposure": False,
        "advanced_scores_changed_by_default": False,
        "planner_changed": False,
        "notifications_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "sky_compass_changed": False,
        "runtime_behaviour_changed": False,
        "source_reports": [
            "docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md",
            "docs/ADVANCED_OBSERVING_NSOM_QML_EXPOSURE_READINESS.md",
            "docs/ADVANCED_OBSERVING_NSOM_QML_PRESENTATION_POLICY.md",
        ],
        "default_on_readiness_report": "docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
    }


def test_default_on_readiness_distinguishes_backend_switch_from_visible_ui() -> None:
    data = generate_default_on_readiness_data()

    assert data["readiness"]["verdict"] == "ready_for_advanced_observing_nsom_backend_default_on"
    assert data["readiness"]["ready_for_backend_default_on"] is True
    assert data["readiness"]["ready_for_visible_ui"] is False
    assert data["readiness"]["ready_to_replace_advanced_scores"] is False
    assert data["readiness"]["default_flag"] == "NSOM_ADVANCED_OBSERVING_ENABLED = False"
    assert data["readiness"]["requires_separate_flag_change"] is True
    assert data["default_on_blockers"] == []
    assert "advanced-observing-visible-ui-design-not-approved" in data["remaining_non_blocking_items"]


def test_default_on_decisions_keep_advanced_scores_legacy_and_confidence_metadata_only() -> None:
    data = generate_default_on_readiness_data()
    decisions = {decision["decision_id"]: decision for decision in data["decisions"]}

    assert decisions["backend_projection_default_on"]["blocks_backend_default_on"] is False
    assert decisions["visible_ui"]["blocks_backend_default_on"] is False
    assert decisions["visible_ui"]["blocks_visible_ui"] is True
    assert decisions["advanced_scores_replacement"]["status"] == "out_of_scope"
    assert decisions["consumer_split"]["blocks_backend_default_on"] is False
    assert decisions["confidence_metadata"]["score_effect"] == 0.0
    assert data["checks"]["advanced_scores_remains_current_qml_contract"] is True
    assert data["checks"]["advanced_scores_not_replaced"] is True
    assert data["checks"]["planner_notifications_keep_legacy_inputs"] is True
    assert data["checks"]["confidence_metadata_only"] is True


def test_default_on_readiness_verifies_property_safety_and_no_runtime_wiring() -> None:
    data = generate_default_on_readiness_data()

    assert data["checks"]["read_only_property_available"] is True
    assert data["checks"]["property_defensive_copy_hardened"] is True
    assert data["checks"]["visible_qml_usage_absent"] is True
    assert data["checks"]["report_tooling_developer_only"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_audit"] is True
    assert data["static_wiring_checks"]["visible_qml_nsom_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["controller_public_property_present"] is True
    assert data["static_wiring_checks"]["property_defensive_copy_present"] is True
    assert data["static_wiring_checks"]["new_nsom_signal_absent"] is True


def test_checked_in_default_on_readiness_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / DEFAULT_ON_READINESS_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Advanced Observing NSOM Default-On Readiness Audit" in text
    assert "ready_for_advanced_observing_nsom_backend_default_on" in text
    assert "None for backend/internal projection default-on" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
