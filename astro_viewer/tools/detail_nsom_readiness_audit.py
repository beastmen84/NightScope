from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.detail_nsom_runtime import NSOM_DETAIL_OBJECT_ENABLED
from astro_viewer.tools.detail_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)
from astro_viewer.tools.detail_nsom_policy_contract import (
    POLICY_CONTRACT_PATH,
    generate_policy_contract_data,
)


READINESS_AUDIT_PATH = Path("docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "detail_nsom_readiness_audit",
    "DETAIL_OBJECT_NSOM_READINESS_AUDIT",
)

RUNTIME_SERVICE_MARKERS = (
    "NSOM_DETAIL_OBJECT_ENABLED = True",
    "DetailObjectNsomRuntimeService",
    "schemaVersion\": \"detail-object-nsom-runtime-v1",
)

RUNTIME_CONTROLLER_MARKERS = (
    "use_nsom_detail_object",
    "_selected_object_nsom_payload",
    "DetailObjectNsomRuntimeService",
)

QML_MARKERS = (
    "detailObjectNsom",
    "selectedObjectNsom",
    "DETAIL_OBJECT_NSOM_READINESS_AUDIT",
)

RUNTIME_DETAIL_MARKERS = (
    "DetailObjectNsomComparisonService",
    "detail_nsom_comparison",
    "detail_nsom_readiness_audit",
    "DETAIL_OBJECT_NSOM_READINESS_AUDIT",
)


def generate_readiness_audit_data() -> dict[str, object]:
    comparison = generate_report_data()
    contract = generate_policy_contract_data()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    runtime_path = _runtime_path_review(static_checks)
    source_policy = _source_policy_review(comparison, contract)
    display = _display_score_semantics(comparison, contract)
    payload = _payload_contract_review(contract)
    confidence = _confidence_review(comparison)
    runtime_safety = _runtime_safety(comparison, static_checks)
    blockers = _default_off_blockers(
        source_policy=source_policy,
        display=display,
        payload=payload,
        confidence=confidence,
        runtime_safety=runtime_safety,
    )
    ready = blockers == ()
    audit_data = {
        "metadata": {
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
            "source_report": str(COMPARISON_REPORT_PATH).replace("\\", "/"),
            "policy_contract_report": str(POLICY_CONTRACT_PATH).replace("\\", "/"),
            "audit_report_path": str(READINESS_AUDIT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": (
                "default_on_detail_nsom_runtime_path_enabled"
                if ready
                and runtime_path["runtime_path_exists"]
                and runtime_path["default_flag_enabled"]
                else "default_off_detail_nsom_runtime_path_available"
                if ready and runtime_path["runtime_path_exists"]
                else "ready_for_default_off_detail_nsom_path"
                if ready
                else "not_ready_for_default_off_detail_nsom_path"
            ),
            "ready_for_default_off_path": ready,
            "runtime_path_exists": runtime_path["runtime_path_exists"],
            "runtime_behaviour_changed_by_this_audit": False,
            "ready_for_visible_ui": False,
            "recommended_next_step": (
                "review 1.10.5, then close Detail/Object NSOM backend migration"
                if runtime_path["runtime_path_exists"]
                and runtime_path["default_flag_enabled"]
                else "review 1.10.4, then 1.10.5 Detail/Object default-on switch"
                if runtime_path["runtime_path_exists"]
                else "1.10.3 default-off Detail/Object NSOM runtime path"
                if ready
                else "resolve Detail/Object source/display policy contract blockers"
            ),
            "reason": _readiness_reason(ready),
        },
        "blockers": blockers,
        "source_policy_review": source_policy,
        "display_score_semantics": display,
        "payload_contract_review": payload,
        "confidence_review": confidence,
        "runtime_path_review": runtime_path,
        "runtime_safety": runtime_safety,
        "static_wiring_checks": static_checks,
        "comparison_summary": comparison["summary"],
        "policy_contract_summary": {
            "verdict": contract["readiness"]["verdict"],
            "ready_for_default_off_path_after_contract": contract["readiness"][
                "ready_for_default_off_path_after_contract"
            ],
            "default_off_blockers": contract["default_off_blockers"],
            "schema_version": contract["payload_contract_example"]["schemaVersion"],
        },
    }
    return nsom_to_json_compatible(audit_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_readiness_audit_data() if data is None else data
    readiness = audit["readiness"]
    source = audit["source_policy_review"]
    display = audit["display_score_semantics"]
    payload = audit["payload_contract_review"]
    confidence = audit["confidence_review"]
    runtime_path = audit["runtime_path_review"]
    contract_summary = audit["policy_contract_summary"]

    lines = [
        "# Detail/Object NSOM Readiness Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether the Detail/Object comparison "
            "evidence is ready for a default-off runtime path. It does not change "
            "`selectedObject`, QML, Home, Best Object, Planner, Sky Compass, logging, "
            "network behaviour or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-off path: `{readiness['ready_for_default_off_path']}`.",
        f"- Runtime path exists: `{readiness['runtime_path_exists']}`.",
        f"- Ready for visible UI: `{readiness['ready_for_visible_ui']}`.",
        f"- Runtime behaviour changed by this audit: `{readiness['runtime_behaviour_changed_by_this_audit']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}.",
        f"- Reason: {readiness['reason']}",
        "",
        "## Default-Off Blockers",
        "",
    ]
    if audit["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in audit["blockers"])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Source Policy Review",
            "",
            f"- Status: `{source['status']}`.",
            f"- Blocks default-off path: `{source['blocks_default_off_path']}`.",
            f"- Observing policy: `{source['observing_source_policy']}`.",
            f"- Catalogue policy: `{source['catalogue_source_policy']}`.",
            f"- Observing display score: `{source['observing_bright_moon_display_score']}`.",
            f"- Catalogue display score: `{source['catalogue_bright_moon_display_score']}`.",
            f"- Comparable observable values: `{source['comparable_observable_values']}`.",
            f"- Decision: {source['decision']}",
            "",
            "## Displayed Score Semantics",
            "",
            f"- Status: `{display['status']}`.",
            f"- Blocks default-off path: `{display['blocks_default_off_path']}`.",
            f"- Keep legacy displayed score for compatibility: `{display['keep_legacy_displayed_score_for_compatibility']}`.",
            f"- Score monotonic with NSOM values: `{display['score_monotonic_with_nsom_values']}`.",
            f"- Decision: {display['decision']}",
            "",
            "## Payload Contract Review",
            "",
            f"- Status: `{payload['status']}`.",
            f"- Blocks default-off path: `{payload['blocks_default_off_path']}`.",
            f"- Existing payload should remain unchanged: `{payload['preserve_existing_selected_object_payload']}`.",
            f"- Add NSOM fields now: `{payload['add_nsom_fields_now']}`.",
            f"- Future internal payload: `{payload['future_internal_payload']}`.",
            f"- Decision: {payload['decision']}",
            "",
            "## Confidence Review",
            "",
            f"- Status: `{confidence['status']}`.",
            f"- Blocks default-off path: `{confidence['blocks_default_off_path']}`.",
            f"- Score factor: `{confidence['score_factor']}`.",
            f"- Score effect: `{confidence['score_effect']}`.",
            "",
            "## Runtime Path Review",
            "",
            f"- Status: `{runtime_path['status']}`.",
            f"- Runtime path exists: `{runtime_path['runtime_path_exists']}`.",
            f"- Default flag: `{runtime_path['default_flag']}`.",
            f"- Default flag enabled: `{runtime_path['default_flag_enabled']}`.",
            f"- Rollback: `{runtime_path['rollback']}`.",
            f"- Controller rollback parameter present: `{runtime_path['controller_rollback_parameter_present']}`.",
            f"- Internal payload method present: `{runtime_path['internal_payload_method_present']}`.",
            f"- QML exposure approved: `{runtime_path['qml_exposure_approved']}`.",
            f"- SelectedObject payload changed: `{runtime_path['selected_object_payload_changed']}`.",
            "",
            "## Policy Contract Summary",
            "",
            f"- Contract report: `{audit['metadata']['policy_contract_report']}`.",
            f"- Contract verdict: `{contract_summary['verdict']}`.",
            f"- Ready after contract: `{contract_summary['ready_for_default_off_path_after_contract']}`.",
            f"- Contract blockers: `{contract_summary['default_off_blockers']}`.",
            f"- Schema version: `{contract_summary['schema_version']}`.",
            "",
            "## Runtime Safety",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["runtime_safety"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Recommended Next Steps",
            "",
            "1. Review the default-off Detail/Object NSOM runtime path.",
            "2. Review the Detail/Object default-on readiness audit before changing the default flag.",
            "3. Keep visible NSOM explanation UI as a later design step.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = READINESS_AUDIT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _source_policy_review(
    comparison: dict[str, object],
    contract: dict[str, object],
) -> dict[str, object]:
    observing = _scenario(comparison, "D01_observing_bright_moon")
    catalogue = _scenario(comparison, "D02_catalogue_bright_moon")
    observing_legacy = observing["legacy"]["selected_object_detail"]
    catalogue_legacy = catalogue["legacy"]["selected_object_detail"]
    contract_decision = _decision(contract, "source_specific_detail_policy")
    observable_equal = (
        float(observing["nsom"]["observable_target_value"]["value"])
        == float(catalogue["nsom"]["observable_target_value"]["value"])
    )
    return {
        "status": contract_decision["status"],
        "blocks_default_off_path": contract_decision["blocks_default_off_path"],
        "observing_source_policy": observing_legacy["policy"],
        "catalogue_source_policy": catalogue_legacy["policy"],
        "observing_bright_moon_display_score": observing_legacy["display_score"],
        "catalogue_bright_moon_display_score": catalogue_legacy["display_score"],
        "comparable_observable_values": observable_equal,
        "decision": contract_decision["summary"],
    }


def _display_score_semantics(
    comparison: dict[str, object],
    contract: dict[str, object],
) -> dict[str, object]:
    observing = _scenario(comparison, "D01_observing_bright_moon")
    catalogue = _scenario(comparison, "D02_catalogue_bright_moon")
    observing_legacy = observing["legacy"]["selected_object_detail"]
    catalogue_legacy = catalogue["legacy"]["selected_object_detail"]
    contract_decision = _decision(contract, "displayed_score_compatibility")
    score_monotonic = (
        float(observing_legacy["display_score"]) == float(catalogue_legacy["display_score"])
        if float(observing["nsom"]["observable_target_value"]["value"])
        == float(catalogue["nsom"]["observable_target_value"]["value"])
        else False
    )
    return {
        "status": contract_decision["status"],
        "blocks_default_off_path": contract_decision["blocks_default_off_path"],
        "keep_legacy_displayed_score_for_compatibility": True,
        "score_monotonic_with_nsom_values": score_monotonic,
        "observing_display_score": observing_legacy["display_score"],
        "catalogue_display_score": catalogue_legacy["display_score"],
        "observing_observable_value": observing["nsom"]["observable_target_value"]["value"],
        "catalogue_observable_value": catalogue["nsom"]["observable_target_value"]["value"],
        "decision": contract_decision["summary"],
    }


def _payload_contract_review(contract: dict[str, object]) -> dict[str, object]:
    contract_decision = _decision(contract, "separate_nsom_payload")
    payload = contract["payload_contract_example"]
    return {
        "status": contract_decision["status"],
        "blocks_default_off_path": contract_decision["blocks_default_off_path"],
        "preserve_existing_selected_object_payload": payload["selectedObjectCompatibility"]["preserveKeys"],
        "add_nsom_fields_now": payload["selectedObjectCompatibility"]["addNsomFields"],
        "qml_payload_shape_change_allowed": payload["visibleQmlExposureApproved"],
        "future_internal_payload": payload["futureInternalPayload"],
        "decision": contract_decision["summary"],
    }


def _confidence_review(comparison: dict[str, object]) -> dict[str, object]:
    control = comparison["confidence_control"]
    return {
        "status": "accepted",
        "blocks_default_off_path": False,
        "low_confidence_value": control["low_confidence_value"],
        "high_confidence_value": control["high_confidence_value"],
        "observable_delta": control["observable_delta"],
        "practical_delta": control["practical_delta"],
        "legacy_display_delta": control["legacy_display_delta"],
        "score_factor": control["score_factor"],
        "score_effect": control["score_effect"],
        "decision": "RecommendationConfidence remains metadata-only and does not modify Detail values.",
    }


def _runtime_safety(
    comparison: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    metadata = comparison["metadata"]
    return {
        "comparison_tooling_developer_only": metadata["developer_only"] is True,
        "comparison_tooling_has_no_runtime_writes": metadata["runtime_writes"] is False,
        "comparison_tooling_has_no_automatic_logging": metadata["automatic_logging"] is False,
        "comparison_tooling_has_no_network": metadata["network"] is False,
        "comparison_tooling_has_no_qml_exposure": metadata["qml_exposure"] is False,
        "selected_object_runtime_unchanged": metadata["selected_object_changed"] is False,
        "home_runtime_unchanged": metadata["home_changed"] is False,
        "best_object_runtime_unchanged": metadata["best_object_changed"] is False,
        "planner_runtime_unchanged": metadata["planner_changed"] is False,
        "sky_compass_runtime_unchanged": metadata["sky_compass_changed"] is False,
        "controller_runtime_wiring_absent": static_checks["controller_detail_comparison_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
    }


def _runtime_path_review(static_checks: dict[str, object]) -> dict[str, object]:
    service_markers = {
        item["marker"] for item in static_checks["runtime_service_matches"]
    }
    controller_markers = {
        item["marker"] for item in static_checks["controller_detail_runtime_matches"]
    }
    runtime_path_exists = (
        set(RUNTIME_SERVICE_MARKERS) <= service_markers
        and set(RUNTIME_CONTROLLER_MARKERS) <= controller_markers
    )
    return {
        "status": (
            "available_default_on"
            if runtime_path_exists and NSOM_DETAIL_OBJECT_ENABLED
            else "available_default_off"
            if runtime_path_exists
            else "not_implemented"
        ),
        "runtime_path_exists": runtime_path_exists,
        "default_flag": f"NSOM_DETAIL_OBJECT_ENABLED = {NSOM_DETAIL_OBJECT_ENABLED}",
        "default_flag_enabled": NSOM_DETAIL_OBJECT_ENABLED is True,
        "rollback": "AppController(use_nsom_detail_object=False)",
        "controller_rollback_parameter_present": "use_nsom_detail_object" in controller_markers,
        "internal_payload_method_present": "_selected_object_nsom_payload" in controller_markers,
        "service_present": "DetailObjectNsomRuntimeService" in service_markers,
        "qml_exposure_approved": False,
        "selected_object_payload_changed": False,
        "report_runtime_wiring": False,
    }


def _default_off_blockers(
    *,
    source_policy: dict[str, object],
    display: dict[str, object],
    payload: dict[str, object],
    confidence: dict[str, object],
    runtime_safety: dict[str, object],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if source_policy["blocks_default_off_path"] is True:
        blockers.append("detail-source-policy-unresolved")
    if display["blocks_default_off_path"] is True:
        blockers.append("detail-displayed-score-semantics-unresolved")
    if payload["blocks_default_off_path"] is True:
        blockers.append("detail-payload-contract-not-defined")
    if confidence["blocks_default_off_path"] is True:
        blockers.append("detail-confidence-policy-unresolved")
    if not all(value is True for value in runtime_safety.values()):
        blockers.append("detail-runtime-safety")
    return tuple(blockers)


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    return {
        "qml_matches": _scan_files(app_root / "ui", ("*.qml",), QML_MARKERS),
        "controller_detail_comparison_matches": _scan_files(
            app_root / "viewmodels",
            ("*.py",),
            RUNTIME_DETAIL_MARKERS,
        ),
        "controller_detail_runtime_matches": _scan_files(
            app_root / "viewmodels",
            ("*.py",),
            RUNTIME_CONTROLLER_MARKERS,
        ),
        "runtime_service_matches": _scan_files(
            app_root / "services",
            ("detail_nsom_runtime.py",),
            RUNTIME_SERVICE_MARKERS,
        ),
        "runtime_report_import_matches": _scan_files(
            app_root,
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
    }


def _scan_files(
    root: Path,
    patterns: tuple[str, ...],
    markers: tuple[str, ...],
    *,
    include_parts: tuple[str, ...] | None = None,
) -> tuple[dict[str, object], ...]:
    if not root.exists():
        return ()
    matches: list[dict[str, object]] = []
    for pattern in patterns:
        for path in sorted(root.rglob(pattern)):
            if include_parts and not any(part in path.parts for part in include_parts):
                continue
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                for marker in markers:
                    if marker in line:
                        matches.append(
                            {
                                "path": str(path.relative_to(root)).replace("\\", "/"),
                                "line": line_number,
                                "marker": marker,
                            }
                        )
    return tuple(matches)


def _scenario(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(scenario for scenario in data["scenarios"] if scenario["scenario_id"] == scenario_id)


def _decision(data: dict[str, object], decision_id: str) -> dict[str, object]:
    return next(decision for decision in data["contract_decisions"] if decision["decision_id"] == decision_id)


def _readiness_reason(ready: bool) -> str:
    if ready:
        return (
            "Detail source policy, displayed score semantics, separate payload "
            "contract, confidence neutrality and runtime safety are all documented."
        )
    return (
        "Detail has source-specific legacy display semantics and no defined NSOM "
        "payload/display contract yet. A default-off runtime path should wait "
        "until those policies are explicit."
    )


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
