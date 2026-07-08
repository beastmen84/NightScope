from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.detail_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)


POLICY_CONTRACT_PATH = Path("docs/DETAIL_OBJECT_NSOM_POLICY_CONTRACT.md")

SCHEMA_VERSION = "detail-object-nsom-policy-v1"

REPORT_IMPORT_MARKERS = (
    "detail_nsom_policy_contract",
    "DETAIL_OBJECT_NSOM_POLICY_CONTRACT",
)

QML_MARKERS = (
    "detailObjectNsom",
    "selectedObjectNsom",
    "DETAIL_OBJECT_NSOM_POLICY_CONTRACT",
)


def generate_policy_contract_data() -> dict[str, object]:
    comparison = generate_report_data()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    decisions = _contract_decisions(comparison)
    payload = _payload_contract_example(comparison)
    checks = _checks(decisions, payload, static_checks)
    blockers = _blockers(checks, decisions)
    contract_data = {
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
        },
        "readiness": {
            "verdict": (
                "detail_object_nsom_policy_contract_defined"
                if not blockers
                else "detail_object_nsom_policy_contract_incomplete"
            ),
            "ready_for_default_off_path_after_contract": not blockers,
            "ready_for_visible_ui": False,
            "runtime_behaviour_changed_by_this_contract": False,
            "recommended_next_change": (
                "review the contract, then implement a default-off Detail/Object "
                "NSOM path behind explicit rollback"
                if not blockers
                else "resolve Detail/Object policy contract blockers"
            ),
            "reason": (
                "Source-specific Detail display semantics, displayed score "
                "compatibility and separate NSOM payload policy are now explicit."
            ),
        },
        "default_off_blockers": blockers,
        "contract_decisions": decisions,
        "payload_contract_example": payload,
        "checks": checks,
        "static_wiring_checks": static_checks,
        "comparison_summary": comparison["summary"],
    }
    return nsom_to_json_compatible(contract_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    contract = generate_policy_contract_data() if data is None else data
    readiness = contract["readiness"]
    payload = contract["payload_contract_example"]

    lines = [
        "# Detail/Object NSOM Policy Contract",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only contract resolves the policy questions raised by "
            "the Detail/Object comparison and readiness audit. It does not change "
            "`selectedObject`, QML, Home, Best Object, Planner, Sky Compass, "
            "logging, network behaviour or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-off path after contract: `{readiness['ready_for_default_off_path_after_contract']}`.",
        f"- Ready for visible UI: `{readiness['ready_for_visible_ui']}`.",
        f"- Runtime behaviour changed by this contract: `{readiness['runtime_behaviour_changed_by_this_contract']}`.",
        f"- Recommended next change: {readiness['recommended_next_change']}.",
        f"- Reason: {readiness['reason']}",
        "",
        "## Default-Off Blockers",
        "",
    ]
    if contract["default_off_blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in contract["default_off_blockers"])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Contract Decisions",
            "",
            "| Decision | Status | Blocks default-off | Summary |",
            "| --- | --- | --- | --- |",
        ]
    )
    for decision in contract["contract_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_default_off_path']}`",
                    str(decision["summary"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Payload Contract",
            "",
            f"- Schema version: `{payload['schemaVersion']}`.",
            f"- Current QML property: `{payload['currentQmlProperty']}`.",
            f"- Future internal payload: `{payload['futureInternalPayload']}`.",
            f"- Visible QML exposure approved: `{payload['visibleQmlExposureApproved']}`.",
            f"- Preserve selectedObject keys: `{payload['selectedObjectCompatibility']['preserveKeys']}`.",
            f"- `selectedObject.score` meaning: {payload['selectedObjectCompatibility']['scoreMeaning']}",
            f"- NSOM fields added to selectedObject: `{payload['selectedObjectCompatibility']['addNsomFields']}`.",
            "",
            "## Source Policies",
            "",
            "| Source | Legacy display policy | NSOM policy | Score policy |",
            "| --- | --- | --- | --- |",
        ]
    )
    for source in payload["sourcePolicies"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{source['source']}`",
                    source["legacyDisplayPolicy"],
                    source["futureNsomPolicy"],
                    source["scorePolicy"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## NSOM Separation",
            "",
            f"- ObservableTargetValue role: {payload['nsomSeparation']['observableTargetValueRole']}",
            f"- PracticalTargetValue role: {payload['nsomSeparation']['practicalTargetValueRole']}",
            f"- SessionViability role: {payload['nsomSeparation']['sessionViabilityRole']}",
            f"- RecommendationConfidence role: {payload['nsomSeparation']['recommendationConfidenceRole']}",
            "",
            "## Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in contract["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Runtime And QML Wiring",
            "",
            f"- QML matches: `{contract['static_wiring_checks']['qml_matches']}`.",
            f"- Runtime report imports: `{contract['static_wiring_checks']['runtime_report_import_matches']}`.",
            "",
            "## Recommended Next Steps",
            "",
            "1. Review this contract.",
            "2. Implement a default-off Detail/Object NSOM runtime path with explicit rollback.",
            "3. Keep visible NSOM explanation UI as a later design step.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = POLICY_CONTRACT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _contract_decisions(comparison: dict[str, object]) -> tuple[dict[str, object], ...]:
    confidence = comparison["confidence_control"]
    return (
        _decision(
            "source_specific_detail_policy",
            status="accepted",
            summary=(
                "Preserve source-specific legacy Detail display semantics in "
                "`selectedObject` during the first default-off NSOM runtime path."
            ),
            reason=(
                "Observing Detail currently shows a moon-adjusted replacement object, "
                "while catalogue Detail shows raw catalogue object fields."
            ),
            blocks_default_off_path=False,
        ),
        _decision(
            "displayed_score_compatibility",
            status="accepted",
            summary=(
                "`selectedObject.score` remains legacy/base compatibility data and "
                "is not an NSOM rationale."
            ),
            reason=(
                "The comparison shows equal NSOM observable values can still have "
                "different legacy displayed scores because source policies differ."
            ),
            blocks_default_off_path=False,
        ),
        _decision(
            "separate_nsom_payload",
            status="accepted",
            summary=(
                "Future Detail NSOM runtime data must be private or separately named; "
                "it must not add fields to `selectedObject` in the first runtime path."
            ),
            reason="This preserves QML payload shape and avoids score/rationale ambiguity.",
            blocks_default_off_path=False,
        ),
        _decision(
            "observable_target_value_role",
            status="accepted",
            summary="ObservableTargetValue explains objective target plus sky value only.",
            reason="Observer, session and confidence do not belong to objective target physics.",
            blocks_default_off_path=False,
        ),
        _decision(
            "practical_target_value_role",
            status="accepted",
            summary="PracticalTargetValue may explain equipment suitability separately from displayed score.",
            reason="Equipment affects observer capability, not objective Detail score compatibility.",
            blocks_default_off_path=False,
        ),
        _decision(
            "session_viability_metadata",
            status="accepted",
            summary="SessionViability is Detail metadata and does not mutate target values.",
            reason="Blocked sessions do not change target physics or current Detail display score.",
            blocks_default_off_path=False,
        ),
        _decision(
            "confidence_metadata",
            status="accepted",
            summary="RecommendationConfidence remains metadata-only with zero score effect.",
            reason="Confidence describes data trust and must not reduce score.",
            blocks_default_off_path=not (
                confidence["score_factor"] is False and float(confidence["score_effect"]) == 0.0
            ),
            extra={
                "score_factor": confidence["score_factor"],
                "score_effect": confidence["score_effect"],
            },
        ),
    )


def _payload_contract_example(comparison: dict[str, object]) -> dict[str, object]:
    observing = _scenario(comparison, "D01_observing_bright_moon")
    catalogue = _scenario(comparison, "D02_catalogue_bright_moon")
    return {
        "schemaVersion": SCHEMA_VERSION,
        "currentQmlProperty": "selectedObject",
        "futureInternalPayload": "detailObjectNsom",
        "visibleQmlExposureApproved": False,
        "selectedObjectCompatibility": {
            "preserveKeys": True,
            "addNsomFields": False,
            "scoreMeaning": "legacy/base compatibility data; not NSOM rationale",
            "scoreMayBeNonMonotonicWithNsom": True,
        },
        "sourcePolicies": (
            {
                "source": "observing",
                "legacyDisplayPolicy": observing["legacy"]["selected_object_detail"]["policy"],
                "futureNsomPolicy": "build parallel NSOM payload only; preserve selectedObject display semantics",
                "scorePolicy": "moon-adjusted compatibility display score remains in selectedObject",
            },
            {
                "source": "catalogue",
                "legacyDisplayPolicy": catalogue["legacy"]["selected_object_detail"]["policy"],
                "futureNsomPolicy": "build parallel NSOM payload only; preserve selectedObject display semantics",
                "scorePolicy": "raw catalogue compatibility display score remains in selectedObject",
            },
        ),
        "nsomSeparation": {
            "observableTargetValueRole": "objective target plus sky explanation",
            "practicalTargetValueRole": "observer/equipment explanation only",
            "sessionViabilityRole": "metadata/actionability context only",
            "recommendationConfidenceRole": "metadata/trust only, zero score effect",
        },
        "runtimeConstraints": {
            "defaultOffFirst": True,
            "explicitRollbackRequired": True,
            "noQmlExposureInFirstRuntimePath": True,
            "noReportRuntimeWiring": True,
            "noNetwork": True,
            "noRuntimeFileWrites": True,
        },
    }


def _checks(
    decisions: tuple[dict[str, object], ...],
    payload: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    decision_ids = {decision["decision_id"] for decision in decisions}
    return {
        "source_policy_decision_recorded": "source_specific_detail_policy" in decision_ids,
        "displayed_score_decision_recorded": "displayed_score_compatibility" in decision_ids,
        "separate_payload_decision_recorded": "separate_nsom_payload" in decision_ids,
        "observable_role_recorded": "observable_target_value_role" in decision_ids,
        "practical_role_recorded": "practical_target_value_role" in decision_ids,
        "session_metadata_recorded": "session_viability_metadata" in decision_ids,
        "confidence_metadata_recorded": "confidence_metadata" in decision_ids,
        "selected_object_payload_preserved": payload["selectedObjectCompatibility"]["preserveKeys"] is True
        and payload["selectedObjectCompatibility"]["addNsomFields"] is False,
        "future_payload_separate": payload["futureInternalPayload"] == "detailObjectNsom",
        "visible_qml_exposure_not_approved": payload["visibleQmlExposureApproved"] is False,
        "runtime_constraints_safe": all(payload["runtimeConstraints"].values()),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
    }


def _blockers(
    checks: dict[str, object],
    decisions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    blockers = [
        f"detail-policy-{decision['decision_id'].replace('_', '-')}"
        for decision in decisions
        if decision["blocks_default_off_path"] is True
    ]
    blockers.extend(f"detail-contract-{key.replace('_', '-')}" for key, value in checks.items() if value is not True)
    return tuple(dict.fromkeys(blockers))


def _decision(
    decision_id: str,
    *,
    status: str,
    summary: str,
    reason: str,
    blocks_default_off_path: bool,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "decision_id": decision_id,
        "status": status,
        "summary": summary,
        "reason": reason,
        "blocks_default_off_path": blocks_default_off_path,
        "runtime_changed": False,
    }
    if extra:
        payload.update(extra)
    return payload


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    return {
        "qml_matches": _scan_files(app_root / "ui", ("*.qml",), QML_MARKERS),
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


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
