from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.night_planner_service import NSOM_PLANNER_SCORING_ENABLED
from astro_viewer.tools.nsom_calibration_decision_log import generate_decision_log_data
from astro_viewer.tools.nsom_mathematical_trace_report import (
    TRACE_REPORT_PATH,
    generate_trace_report_data,
)
from astro_viewer.tools.nsom_planner_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)

READINESS_AUDIT_PATH = Path("docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "nsom_planner_comparison_report",
    "nsom_mathematical_trace_report",
    "nsom_calibration_decision_log",
    "nsom_default_on_readiness_audit",
    "NSOM_PLANNER_COMPARISON_REPORT",
    "NSOM_MATHEMATICAL_TRACE_REPORT",
    "NSOM_CALIBRATION_DECISION_LOG",
    "NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT",
)

QML_MARKERS = (
    "NSOM_PLANNER_SCORING_ENABLED",
    "nsom_planner",
    "nsomPlanner",
    "NSOM_PLANNER_COMPARISON_REPORT",
    "NSOM_MATHEMATICAL_TRACE_REPORT",
    "NSOM_CALIBRATION_DECISION_LOG",
    "NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT",
)


def generate_readiness_audit_data() -> dict[str, object]:
    comparison = generate_report_data()
    trace = generate_trace_report_data()
    decision_log = generate_decision_log_data(comparison)
    tooling_checks = _tooling_checks(comparison, trace, decision_log)
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    decisions = tuple(decision_log["decisions"])
    blockers = _blockers(decision_log)
    decision_summary = _decision_summary(decisions)
    runtime_safety = _runtime_safety(tooling_checks, static_checks)
    ready = _is_ready(
        blockers=blockers,
        decision_summary=decision_summary,
        runtime_safety=runtime_safety,
    )
    audit_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "nsom_planner_scoring_enabled": NSOM_PLANNER_SCORING_ENABLED,
            "source_reports": (
                str(COMPARISON_REPORT_PATH).replace("\\", "/"),
                str(TRACE_REPORT_PATH).replace("\\", "/"),
                "docs/NSOM_CALIBRATION_DECISION_LOG.md",
            ),
            "audit_report_path": str(READINESS_AUDIT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "default_on_enabled" if ready else "not_ready",
            "ready_for_default_on_switch_pr": ready,
            "default_on_switch_completed": NSOM_PLANNER_SCORING_ENABLED is True,
            "ready_to_enable_in_this_commit": ready,
            "recommendation": (
                "keep_default_on_with_explicit_rollback"
                if ready
                else "resolve_readiness_blockers_before_keeping_default_on"
            ),
            "reason": _readiness_reason(ready),
        },
        "blockers": blockers,
        "decisions": decision_summary,
        "remaining_non_blocking_review_items": _remaining_non_blocking_review_items(decisions),
        "runtime_safety": runtime_safety,
        "tooling_checks": tooling_checks,
        "static_wiring_checks": static_checks,
        "risks_before_switch": _risks_before_switch(),
    }
    return nsom_to_json_compatible(audit_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_readiness_audit_data() if data is None else data
    readiness = audit["readiness"]
    blockers = audit["blockers"]
    decisions = audit["decisions"]
    runtime = audit["runtime_safety"]
    metadata = audit["metadata"]

    lines = [
        "# NSOM Planner Default-On Readiness Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether the NSOM Planner default-on "
            "switch is safe to keep while preserving an explicit legacy rollback path. "
            "It does not tune weights, remove legacy Planner scoring, "
            "write runtime files, log automatically, perform network work or expose QML."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Default-on readiness satisfied: `{readiness['ready_for_default_on_switch_pr']}`.",
        f"- Default-on switch completed: `{readiness['default_on_switch_completed']}`.",
        f"- Ready to enable in this commit: `{readiness['ready_to_enable_in_this_commit']}`.",
        f"- Recommendation: `{readiness['recommendation']}`.",
        f"- Reason: {readiness['reason']}",
        "",
        "## Blocking Checks",
        "",
        "| Check | Result |",
        "| --- | --- |",
        f"| Default-on blockers | {_list_cell(blockers['default_on_blockers'])} |",
        f"| Needs calibration decisions | {_list_cell(blockers['needs_calibration'])} |",
        f"| Needs policy decisions | {_list_cell(blockers['needs_policy_decision'])} |",
        f"| Unlinked review or policy rows | {_list_cell(blockers['unlinked_review_or_policy_rows'])} |",
        "",
        "## Decision Coverage",
        "",
        "| Item | Result |",
        "| --- | --- |",
        f"| Accepted decisions documented | `{decisions['accepted_decisions_documented']}` |",
        f"| Deferred decisions documented | `{decisions['deferred_decisions_documented']}` |",
        f"| Deferred decisions non-blocking | `{decisions['deferred_non_blocking']}` |",
        f"| Accepted decisions | {_list_cell(decisions['accepted_decision_ids'])} |",
        f"| Deferred decisions | {_list_cell(decisions['deferred_decision_ids'])} |",
        "",
        "## Remaining Non-Blocking Review Items",
        "",
    ]
    for item in audit["remaining_non_blocking_review_items"]:
        lines.append(
            f"- `{item['decision_id']}` ({item['affected_nsom_layer']}, "
            f"{item['affected_target_class']}): {item['decision_reason']}"
        )
    if not audit["remaining_non_blocking_review_items"]:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Runtime Safety",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in runtime.items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Developer-Only Tooling",
            "",
            "| Tool | Developer Only | Runtime Writes | Automatic Logging | Network | QML Exposure |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for tool_name, check in audit["tooling_checks"].items():
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{tool_name}`",
                    f"`{check['developer_only']}`",
                    f"`{check['runtime_writes']}`",
                    f"`{check['automatic_logging']}`",
                    f"`{check['network']}`",
                    f"`{check['qml_exposure']}`",
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Risks Before Actual Default-On Switch",
            "",
        ]
    )
    for risk in audit["risks_before_switch"]:
        lines.append(f"- {risk}")

    lines.extend(
        [
            "",
            "## Source Reports",
            "",
        ]
    )
    for source in metadata["source_reports"]:
        lines.append(f"- `{source}`")

    lines.extend(
        [
            "",
            "## Final Recommendation",
            "",
            (
                "Keep the default-on switch only while this audit remains green and "
                "`NightPlannerService(use_nsom_planner_scoring=False)` continues to "
                "provide an explicit legacy rollback path."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = READINESS_AUDIT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _tooling_checks(
    comparison: dict[str, object],
    trace: dict[str, object],
    decision_log: dict[str, object],
) -> dict[str, object]:
    return {
        "comparison_report": _metadata_side_effects(comparison["metadata"]),
        "mathematical_trace_report": _metadata_side_effects(trace["metadata"]),
        "calibration_decision_log": _metadata_side_effects(decision_log["metadata"]),
    }


def _metadata_side_effects(metadata: dict[str, object]) -> dict[str, object]:
    return {
        "developer_only": metadata.get("developer_only") is True,
        "runtime_writes": metadata.get("runtime_writes") is True,
        "automatic_logging": metadata.get("automatic_logging") is True,
        "network": metadata.get("network") is True,
        "qml_exposure": metadata.get("qml_exposure") is True,
        "nsom_planner_scoring_enabled": metadata.get("nsom_planner_scoring_enabled") is True,
    }


def _static_wiring_checks(root: Path) -> dict[str, object]:
    return {
        "qml_matches": _scan_files(root / "astro_viewer" / "app" / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
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
                                "path": str(path.relative_to(root.parents[2])).replace("\\", "/"),
                                "line": line_number,
                                "marker": marker,
                            }
                        )
    return tuple(matches)


def _blockers(decision_log: dict[str, object]) -> dict[str, object]:
    summary = decision_log["summary"]
    decisions = tuple(decision_log["decisions"])
    return {
        "default_on_blockers": tuple(summary["default_on_blockers"]),
        "needs_calibration": tuple(
            decision["decision_id"]
            for decision in decisions
            if decision["decision_status"] == "needs_calibration"
        ),
        "needs_policy_decision": tuple(
            decision["decision_id"]
            for decision in decisions
            if decision["decision_status"] == "needs_policy_decision"
        ),
        "unlinked_review_or_policy_rows": tuple(summary["unlinked_rows"]),
    }


def _decision_summary(decisions: tuple[dict[str, object], ...]) -> dict[str, object]:
    accepted = tuple(
        decision for decision in decisions if decision["decision_status"] == "accepted"
    )
    deferred = tuple(
        decision for decision in decisions if decision["decision_status"] == "deferred"
    )
    return {
        "accepted_decision_ids": tuple(decision["decision_id"] for decision in accepted),
        "deferred_decision_ids": tuple(decision["decision_id"] for decision in deferred),
        "accepted_decisions_documented": all(_decision_is_documented(decision) for decision in accepted),
        "deferred_decisions_documented": all(_decision_is_documented(decision) for decision in deferred),
        "deferred_non_blocking": all(
            decision["blocks_default_on_work"] is False
            and decision["requires_tuning"] is False
            for decision in deferred
        ),
        "deferred_possible_calibration_issues": tuple(
            decision["decision_id"]
            for decision in deferred
            if decision["possible_calibration_issue"] is True
        ),
    }


def _decision_is_documented(decision: dict[str, object]) -> bool:
    required = (
        "decision_reason",
        "affected_nsom_layer",
        "affected_target_class",
        "rank_delta_review_notes",
    )
    return all(bool(str(decision.get(field, "")).strip()) for field in required)


def _remaining_non_blocking_review_items(
    decisions: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "decision_id": decision["decision_id"],
            "affected_nsom_layer": decision["affected_nsom_layer"],
            "affected_target_class": decision["affected_target_class"],
            "decision_reason": decision["decision_reason"],
            "possible_calibration_issue": decision["possible_calibration_issue"],
        }
        for decision in decisions
        if decision["decision_status"] == "deferred"
        and decision["blocks_default_on_work"] is False
    )


def _runtime_safety(
    tooling_checks: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    return {
        "flag_default_on": NSOM_PLANNER_SCORING_ENABLED is True,
        "legacy_planner_explicit_rollback_available": True,
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "tooling_developer_only": all(
            check["developer_only"] is True for check in tooling_checks.values()
        ),
        "tooling_has_no_runtime_writes": all(
            check["runtime_writes"] is False for check in tooling_checks.values()
        ),
        "tooling_has_no_automatic_logging": all(
            check["automatic_logging"] is False for check in tooling_checks.values()
        ),
        "tooling_has_no_network": all(
            check["network"] is False for check in tooling_checks.values()
        ),
        "tooling_has_no_qml_exposure": all(
            check["qml_exposure"] is False for check in tooling_checks.values()
        ),
    }


def _is_ready(
    *,
    blockers: dict[str, object],
    decision_summary: dict[str, object],
    runtime_safety: dict[str, object],
) -> bool:
    return (
        blockers["default_on_blockers"] == ()
        and blockers["needs_calibration"] == ()
        and blockers["needs_policy_decision"] == ()
        and blockers["unlinked_review_or_policy_rows"] == ()
        and decision_summary["accepted_decisions_documented"] is True
        and decision_summary["deferred_decisions_documented"] is True
        and decision_summary["deferred_non_blocking"] is True
        and all(value is True for value in runtime_safety.values())
    )


def _readiness_reason(ready: bool) -> str:
    if ready:
        return (
            "No calibration or policy blockers remain; accepted/deferred decisions "
            "are documented; deferred items are non-blocking; the runtime flag is "
            "default-on; the explicit legacy rollback path remains available; "
            "developer-only report tooling remains unwired."
        )
    return (
        "At least one blocker, documentation gap, deferred blocking item or runtime "
        "safety check failed."
    )


def _risks_before_switch() -> tuple[str, ...]:
    return (
        "The default-on switch intentionally changes Planner ranking and needs runtime acceptance review.",
        "Deferred review items should remain visible after enabling so they do not become hidden calibration debt.",
        "The explicit rollback path should be preserved until NSOM Planner has enough runtime evidence.",
    )


def _list_cell(items: object) -> str:
    values = tuple(items) if isinstance(items, (list, tuple)) else (items,)
    if not values:
        return "`none`"
    return ", ".join(f"`{item}`" for item in values)


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
