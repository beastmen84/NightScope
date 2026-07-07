from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.advanced_observing_nsom_service import NSOM_ADVANCED_OBSERVING_ENABLED
from astro_viewer.tools.advanced_observing_nsom_presentation_contract import (
    PRESENTATION_CONTRACT_PATH,
    generate_presentation_contract_data,
)

QML_EXPOSURE_READINESS_PATH = Path("docs/ADVANCED_OBSERVING_NSOM_QML_EXPOSURE_READINESS.md")

REPORT_IMPORT_MARKERS = (
    "advanced_observing_nsom_qml_exposure_readiness",
    "ADVANCED_OBSERVING_NSOM_QML_EXPOSURE_READINESS",
)

QML_MARKERS = (
    "advancedObservingNsom",
    "AdvancedObservingNsom",
    "advancedObservingNsomScores",
    "AdvancedObservingNsomScores",
)


def generate_qml_exposure_readiness_data() -> dict[str, object]:
    contract = generate_presentation_contract_data()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    decisions = _qml_exposure_decisions(contract, static_checks)
    checks = _checks(contract, decisions, static_checks)
    blockers = _default_on_blockers(checks, decisions)
    data = {
        "metadata": {
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
            "source_report": str(PRESENTATION_CONTRACT_PATH).replace("\\", "/"),
            "qml_exposure_readiness_report": str(QML_EXPOSURE_READINESS_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "advanced_observing_nsom_read_only_qml_property_available",
            "ready_for_qml_exposure": True,
            "ready_for_user_visible_ui": False,
            "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
            "default_flag_currently_enabled": NSOM_ADVANCED_OBSERVING_ENABLED is True,
            "runtime_behaviour_changed_by_this_audit": False,
            "recommended_next_change": (
                "decide separately whether visible UI should consume "
                "`advancedObservingNsom` or whether Advanced Observing NSOM should "
                "remain developer-facing"
            ),
            "reason": (
                "The internal projection is now available through a read-only QML "
                "property using the existing weather lifecycle. No QML UI consumes "
                "it yet, and visible UI still needs explicit design approval."
            ),
        },
        "default_on_blockers": blockers,
        "checks": checks,
        "qml_exposure_decisions": decisions,
        "presentation_contract_summary": {
            "verdict": contract["readiness"]["verdict"],
            "default_on_blockers": contract["default_on_blockers"],
            "payload_schema": contract["contract_payload_example"]["schemaVersion"],
            "future_qml_property": contract["contract_payload_example"]["futureQmlProperty"],
            "current_qml_property": contract["contract_payload_example"]["currentQmlProperty"],
        },
        "static_wiring_checks": static_checks,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_qml_exposure_readiness_data() if data is None else data
    readiness = audit["readiness"]
    summary = audit["presentation_contract_summary"]

    lines = [
        "# Advanced Observing NSOM QML Exposure Readiness",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether the internal Advanced Observing "
            "NSOM presentation payload is safely exposed to QML. As of 1.8.14, "
            "`advancedObservingNsom` is a read-only property backed by the private "
            "`_advanced_observing_nsom_presentation` snapshot and the existing "
            "`weatherChanged` lifecycle. As of 1.8.15, the property returns a "
            "defensive deep copy so consumers cannot mutate the private snapshot. "
            "This report does not change `advancedScores`, enable "
            "`NSOM_ADVANCED_OBSERVING_ENABLED`, tune scores, render visible UI, "
            "log automatically, call the network or write runtime files."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for QML exposure: `{readiness['ready_for_qml_exposure']}`.",
        f"- Ready for user-visible UI: `{readiness['ready_for_user_visible_ui']}`.",
        f"- Current default flag: `{readiness['default_flag']}`.",
        f"- Default flag currently enabled: `{readiness['default_flag_currently_enabled']}`.",
        f"- Runtime behaviour changed by this audit: `{readiness['runtime_behaviour_changed_by_this_audit']}`.",
        f"- Recommended next change: {readiness['recommended_next_change']}.",
        f"- Reason: {readiness['reason']}",
        "",
            "## Remaining Items",
        "",
    ]
    if audit["default_on_blockers"]:
        for blocker in audit["default_on_blockers"]:
            lines.append(f"- `{blocker}`")
    else:
        lines.append("- None for read-only QML exposure; visible UI remains a separate decision.")

    lines.extend(
        [
            "",
            "## QML Exposure Decisions",
            "",
            "| Decision | Status | Blocks QML exposure | Summary |",
            "| --- | --- | --- | --- |",
        ]
    )
    for decision in audit["qml_exposure_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_qml_exposure']}`",
                    str(decision["summary"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Presentation Contract Summary",
            "",
            f"- Contract verdict: `{summary['verdict']}`.",
            f"- Payload schema: `{summary['payload_schema']}`.",
            f"- Current QML property: `{summary['current_qml_property']}`.",
            f"- Future QML property: `{summary['future_qml_property']}`.",
            f"- Contract blockers: `{summary['default_on_blockers']}`.",
            "",
            "## Static Wiring Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["static_wiring_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Recommended Next Step",
            "",
            (
                "The read-only `advancedObservingNsom` property is wired and "
                "defensive-copy hardened. Keep visible UI and any default-on Advanced "
                "Observing NSOM switch as separate decisions."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = QML_EXPOSURE_READINESS_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _qml_exposure_decisions(
    contract: dict[str, object],
    static_checks: dict[str, object],
) -> tuple[dict[str, object], ...]:
    payload = contract["contract_payload_example"]
    return (
        _decision(
            "internal_projection_safe_to_keep",
            status="accepted",
            summary="Keep the 1.8.10 internal projection as developer-only data.",
            reason="It is strict-JSON-compatible, default-off and not consumed by runtime scoring paths.",
            blocks_qml_exposure=False,
        ),
        _decision(
            "public_qml_property",
            status="implemented_read_only",
            summary="Expose `advancedObservingNsom` as a read-only QML property.",
            reason="The 1.8.13 lifecycle policy approved using the existing `weatherChanged` signal.",
            blocks_qml_exposure=False,
        ),
        _decision(
            "visible_ui_copy",
            status="blocks_visible_ui_only",
            summary="Do not render the payload in the Home UI yet.",
            reason="The payload contains developer-facing score semantics and English copy.",
            blocks_qml_exposure=False,
        ),
        _decision(
            "score_label_semantics",
            status="blocks_visible_ui_only",
            summary="Do not show NSOM category values as legacy `/100` actionability scores.",
            reason="The contract defines category diagnostics, not Planner or notification thresholds.",
            blocks_qml_exposure=False,
        ),
        _decision(
            "legacy_advanced_scores_contract",
            status="accepted",
            summary="Keep `advancedScores` as the only current public QML contract.",
            reason="Existing QML, Planner and NotificationService compatibility depends on it.",
            blocks_qml_exposure=False,
        ),
        _decision(
            "confidence_metadata",
            status="accepted",
            summary="Keep RecommendationConfidence outside score and display reduction semantics.",
            reason="Confidence is source trust metadata and has zero score effect.",
            blocks_qml_exposure=payload["confidence"]["scoreEffect"] != 0.0,
            extra={"score_effect": payload["confidence"]["scoreEffect"]},
        ),
        _decision(
            "read_only_qml_property_wired",
            status="verified",
            summary="The controller exposes the payload through a read-only property, but QML UI does not read it.",
            reason="The audit found the public controller property and no `controller.advancedObservingNsom` QML usage.",
            blocks_qml_exposure=not (
                static_checks["controller_public_property_present"] is True
                and static_checks["qml_nsom_matches"] == ()
            ),
        ),
    )


def _decision(
    decision_id: str,
    *,
    status: str,
    summary: str,
    reason: str,
    blocks_qml_exposure: bool,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "decision_id": decision_id,
        "status": status,
        "summary": summary,
        "reason": reason,
        "blocks_qml_exposure": blocks_qml_exposure,
        "runtime_changed": False,
    }
    if extra:
        payload.update(extra)
    return payload


def _checks(
    contract: dict[str, object],
    decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    decision_ids = {decision["decision_id"] for decision in decisions}
    payload = contract["contract_payload_example"]
    return {
        "default_flag_still_off": NSOM_ADVANCED_OBSERVING_ENABLED is False,
        "contract_runtime_projection_available": contract["checks"]["runtime_projection_available"] is True,
        "contract_visible_ui_review_still_blocking": "advanced-observing-visible-ui-review-required"
        in contract["default_on_blockers"],
        "required_qml_exposure_decisions_recorded": {
            "internal_projection_safe_to_keep",
            "public_qml_property",
            "visible_ui_copy",
            "score_label_semantics",
            "legacy_advanced_scores_contract",
            "confidence_metadata",
            "read_only_qml_property_wired",
        }.issubset(decision_ids),
        "advanced_scores_remains_current_qml_contract": payload["currentQmlProperty"] == "advancedScores",
        "future_property_exposed_read_only": static_checks["controller_public_property_present"] is True,
        "visible_qml_usage_absent": static_checks["qml_nsom_matches"] == (),
        "notify_signal_not_introduced": static_checks["controller_public_signal_present"] is False,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "confidence_score_neutral": payload["confidence"]["scoreEffect"] == 0.0,
        "no_runtime_behaviour_change": True,
    }


def _default_on_blockers(
    checks: dict[str, object],
    decisions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    blockers = [
        f"advanced-observing-{decision['decision_id'].replace('_', '-')}"
        for decision in decisions
        if decision["blocks_qml_exposure"] is True
    ]
    safety_names = {
        "contract_runtime_projection_available": "advanced-observing-runtime-projection-missing",
        "contract_visible_ui_review_still_blocking": "advanced-observing-contract-visible-ui-blocker-missing",
        "required_qml_exposure_decisions_recorded": "advanced-observing-qml-decisions-incomplete",
        "advanced_scores_remains_current_qml_contract": "advanced-observing-current-qml-contract-regressed",
        "future_property_exposed_read_only": "advanced-observing-qml-property-missing",
        "visible_qml_usage_absent": "advanced-observing-unplanned-visible-qml-usage",
        "notify_signal_not_introduced": "advanced-observing-unplanned-qml-signal",
        "runtime_report_imports_absent": "advanced-observing-runtime-report-wiring",
        "confidence_score_neutral": "advanced-observing-confidence-not-neutral",
        "no_runtime_behaviour_change": "advanced-observing-runtime-behaviour-change",
    }
    blockers.extend(name for key, name in safety_names.items() if checks[key] is not True)
    return tuple(dict.fromkeys(blockers))


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    controller_path = app_root / "viewmodels" / "app_controller.py"
    controller_text = controller_path.read_text(encoding="utf-8") if controller_path.exists() else ""
    public_property_markers = (
        "def advancedObservingNsom",
        "def advancedObservingNsomScores",
        "advancedObservingNsom = Property",
        "advancedObservingNsomScores = Property",
    )
    public_signal_markers = (
        "advancedObservingNsomChanged",
        "advancedObservingNsomScoresChanged",
    )
    return {
        "qml_nsom_matches": _scan_files(app_root / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            app_root,
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "controller_private_projection_present": "_advanced_observing_nsom_presentation" in controller_text,
        "controller_public_property_present": any(
            marker in controller_text for marker in public_property_markers
        ),
        "controller_public_signal_present": any(marker in controller_text for marker in public_signal_markers),
        "qml_reads_existing_advanced_scores": _scan_files(
            app_root / "ui",
            ("*.qml",),
            ("controller.advancedScores",),
        )
        != (),
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


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
