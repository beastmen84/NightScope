from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.advanced_observing_nsom_presentation_contract import (
    PRESENTATION_CONTRACT_PATH,
    SCHEMA_VERSION,
    generate_presentation_contract_data,
    render_markdown_report,
)


def test_presentation_contract_data_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_presentation_contract_data()
    second = generate_presentation_contract_data()

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
        "source_report": "docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_READINESS.md",
        "presentation_contract_report": "docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md",
    }


def test_presentation_contract_defines_separate_payload_without_default_on() -> None:
    data = generate_presentation_contract_data()
    readiness = data["readiness"]

    assert readiness["verdict"] == "advanced_observing_nsom_presentation_read_only_qml_property_wired"
    assert readiness["ready_for_default_on_switch"] is False
    assert readiness["default_flag"] == "NSOM_ADVANCED_OBSERVING_ENABLED = False"
    assert readiness["runtime_behaviour_changed_by_this_contract"] is False
    assert readiness["future_qml_property"] == "advancedObservingNsom"
    assert readiness["current_qml_property"] == "advancedScores"
    assert "advanced-observing-runtime-projection-not-implemented" not in data["default_on_blockers"]
    assert "advanced-observing-future-property-not-wired" not in data["default_on_blockers"]


def test_contract_payload_shape_and_consumer_policy_are_explicit() -> None:
    payload = generate_presentation_contract_data()["contract_payload_example"]

    assert payload["schemaVersion"] == SCHEMA_VERSION
    assert payload["currentQmlProperty"] == "advancedScores"
    assert payload["futureQmlProperty"] == "advancedObservingNsom"
    assert payload["consumerPolicy"] == {
        "replacesAdvancedScores": False,
        "plannerInput": False,
        "notificationInput": False,
        "homeBestObjectInput": False,
        "skyCompassInput": False,
    }
    assert payload["runtimeSafety"] == {
        "defaultOff": True,
        "noRuntimeFileWrites": True,
        "noAutomaticLogging": True,
        "noNetwork": True,
        "noMutationOfRuntimeObjects": True,
    }


def test_contract_uses_observable_value_only_for_categories() -> None:
    payload = generate_presentation_contract_data()["contract_payload_example"]

    assert {category["id"] for category in payload["categories"]} == {"planetary", "deepSky"}
    for category in payload["categories"]:
        assert category["scoreMeaning"] == "NSOM ObservableTargetValue category diagnostic"
        assert category["scoreRange"] == "0..100"
        assert category["mathPipeline"] == [
            "IntrinsicTargetQuality",
            "ObservationEnvironment",
            "EffectiveObservability",
            "ObservableTargetValue",
        ]
        assert "ObserverCapability" in category["excludedFromCategoryValue"]
        assert "PracticalTargetValue" in category["excludedFromCategoryValue"]
        assert "SessionViability" in category["excludedFromCategoryValue"]
        assert "RecommendationConfidence" in category["excludedFromCategoryValue"]
        assert "ObservationOpportunity" in category["excludedFromCategoryValue"]


def test_contract_keeps_session_and_confidence_as_score_neutral_metadata() -> None:
    payload = generate_presentation_contract_data()["contract_payload_example"]

    assert payload["session"] == {
        "included": True,
        "placement": "metadata_outside_category_value",
        "scoreEffect": 0.0,
        "state": "recommended",
        "semantics": "actionability and caution text only",
    }
    assert payload["confidence"] == {
        "included": True,
        "placement": "metadata_outside_category_value",
        "scoreEffect": 0.0,
        "value": 1.0,
        "semantics": "source trust only",
    }


def test_contract_decisions_resolve_design_but_keep_runtime_and_qml_blockers() -> None:
    data = generate_presentation_contract_data()
    decisions = {decision["decision_id"]: decision for decision in data["contract_decisions"]}

    assert decisions["separate_nsom_presentation_payload"]["status"] == "accepted_design"
    assert decisions["advanced_scores_legacy_compatibility"]["blocks_default_on"] is False
    assert decisions["observable_value_only"]["blocks_default_on"] is False
    assert decisions["session_and_confidence_metadata"]["confidence_score_effect"] == 0.0
    assert decisions["session_and_confidence_metadata"]["session_score_effect"] == 0.0
    assert decisions["runtime_projection_implemented_default_off"]["blocks_default_on"] is False
    assert decisions["qml_exposure_review_required"]["status"] == "read_only_property_implemented"
    assert decisions["qml_exposure_review_required"]["blocks_default_on"] is False
    assert decisions["previous_readiness_blocker_addressed"]["status"] == "accepted"


def test_presentation_contract_checks_runtime_safety_and_read_only_qml_wiring() -> None:
    data = generate_presentation_contract_data()

    assert data["checks"]["contract_schema_versioned"] is True
    assert data["checks"]["contract_defines_separate_future_property"] is True
    assert data["checks"]["contract_does_not_replace_advanced_scores"] is True
    assert data["checks"]["contract_excludes_planner_and_notifications"] is True
    assert data["checks"]["categories_use_observable_value_only"] is True
    assert data["checks"]["session_and_confidence_are_metadata"] is True
    assert data["checks"]["observer_and_opportunity_excluded"] is True
    assert data["checks"]["runtime_projection_available"] is True
    assert data["checks"]["read_only_qml_property_implemented"] is True
    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_exposure_absent"] is True
    assert data["checks"]["future_property_wired"] is True
    assert data["checks"]["runtime_behaviour_unchanged"] is True
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["future_property_already_wired"] is True


def test_checked_in_advanced_observing_presentation_contract_report_exists() -> None:
    report = Path(__file__).parents[2] / PRESENTATION_CONTRACT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Advanced Observing NSOM Presentation Contract" in text
    assert "advanced_observing_nsom_presentation_read_only_qml_property_wired" in text
    assert "advancedObservingNsom" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
