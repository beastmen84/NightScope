from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.detail_nsom_policy_contract import (
    POLICY_CONTRACT_PATH,
    generate_policy_contract_data,
    render_markdown_report,
)


def test_detail_nsom_policy_contract_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_policy_contract_data()
    second = generate_policy_contract_data()

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
        "policy_contract_report": "docs/DETAIL_OBJECT_NSOM_POLICY_CONTRACT.md",
    }


def test_policy_contract_resolves_default_off_policy_blockers_without_runtime_change() -> None:
    data = generate_policy_contract_data()

    assert data["readiness"]["verdict"] == "detail_object_nsom_policy_contract_defined"
    assert data["readiness"]["ready_for_default_off_path_after_contract"] is True
    assert data["readiness"]["ready_for_visible_ui"] is False
    assert data["readiness"]["runtime_behaviour_changed_by_this_contract"] is False
    assert data["default_off_blockers"] == []
    assert all(decision["blocks_default_off_path"] is False for decision in data["contract_decisions"])


def test_policy_contract_accepts_source_split_and_displayed_score_compatibility() -> None:
    data = generate_policy_contract_data()
    decisions = {decision["decision_id"]: decision for decision in data["contract_decisions"]}
    payload = data["payload_contract_example"]

    assert decisions["source_specific_detail_policy"]["status"] == "accepted"
    assert decisions["displayed_score_compatibility"]["status"] == "accepted"
    assert payload["sourcePolicies"][0]["source"] == "observing"
    assert payload["sourcePolicies"][0]["legacyDisplayPolicy"] == "observing_detail_moon_adjusted_copy"
    assert payload["sourcePolicies"][1]["source"] == "catalogue"
    assert payload["sourcePolicies"][1]["legacyDisplayPolicy"] == "catalogue_detail_raw_object"
    assert payload["selectedObjectCompatibility"]["scoreMeaning"] == (
        "legacy/base compatibility data; not NSOM rationale"
    )
    assert payload["selectedObjectCompatibility"]["scoreMayBeNonMonotonicWithNsom"] is True


def test_policy_contract_keeps_nsom_payload_separate_from_selected_object_and_qml() -> None:
    data = generate_policy_contract_data()
    decisions = {decision["decision_id"]: decision for decision in data["contract_decisions"]}
    payload = data["payload_contract_example"]

    assert decisions["separate_nsom_payload"]["status"] == "accepted"
    assert payload["currentQmlProperty"] == "selectedObject"
    assert payload["futureInternalPayload"] == "detailObjectNsom"
    assert payload["visibleQmlExposureApproved"] is False
    assert payload["selectedObjectCompatibility"]["preserveKeys"] is True
    assert payload["selectedObjectCompatibility"]["addNsomFields"] is False
    assert payload["runtimeConstraints"] == {
        "defaultOffFirst": True,
        "explicitRollbackRequired": True,
        "noQmlExposureInFirstRuntimePath": True,
        "noReportRuntimeWiring": True,
        "noNetwork": True,
        "noRuntimeFileWrites": True,
    }


def test_policy_contract_preserves_nsom_ownership_and_confidence_neutrality() -> None:
    data = generate_policy_contract_data()
    decisions = {decision["decision_id"]: decision for decision in data["contract_decisions"]}
    separation = data["payload_contract_example"]["nsomSeparation"]

    assert decisions["observable_target_value_role"]["status"] == "accepted"
    assert decisions["practical_target_value_role"]["status"] == "accepted"
    assert decisions["session_viability_metadata"]["status"] == "accepted"
    assert decisions["confidence_metadata"]["status"] == "accepted"
    assert decisions["confidence_metadata"]["score_factor"] is False
    assert decisions["confidence_metadata"]["score_effect"] == 0.0
    assert separation["observableTargetValueRole"] == "objective target plus sky explanation"
    assert separation["practicalTargetValueRole"] == "observer/equipment explanation only"
    assert separation["sessionViabilityRole"] == "metadata/actionability context only"
    assert separation["recommendationConfidenceRole"] == "metadata/trust only, zero score effect"


def test_detail_nsom_policy_contract_has_no_runtime_or_qml_wiring() -> None:
    data = generate_policy_contract_data()

    assert data["checks"]["qml_exposure_absent"] is True
    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_detail_nsom_policy_contract_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / POLICY_CONTRACT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Detail/Object NSOM Policy Contract" in text
    assert "detail_object_nsom_policy_contract_defined" in text
    assert "detail-object-nsom-policy-v1" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
