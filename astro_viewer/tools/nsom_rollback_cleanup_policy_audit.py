from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.nsom_legacy_backend_surface_audit import (
    generate_legacy_backend_surface_audit_data,
)
from astro_viewer.tools.nsom_overall_backend_readiness_audit import (
    generate_overall_backend_readiness_audit_data,
)


REPORT_PATH = Path("docs/NSOM_ROLLBACK_CLEANUP_POLICY_AUDIT.md")

SOURCE_REPORTS = (
    Path("docs/NSOM_OVERALL_BACKEND_READINESS_AUDIT.md"),
    Path("docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md"),
    Path("docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md"),
)

REPORT_IMPORT_MARKERS = (
    "nsom_rollback_cleanup_policy_audit",
    "NSOM_ROLLBACK_CLEANUP_POLICY_AUDIT",
    "NSOM_ROLLBACK_CLEANUP_POLICY",
)

QML_MARKERS = (
    "nsomRollbackCleanupPolicy",
    "rollbackCleanupPolicy",
    "NSOM_ROLLBACK_CLEANUP_POLICY_AUDIT",
)


def generate_rollback_cleanup_policy_audit_data() -> dict[str, object]:
    """Developer-only policy decision for internal NSOM rollback cleanup."""

    root = Path(__file__).parents[2]
    overall = generate_overall_backend_readiness_audit_data()
    legacy = generate_legacy_backend_surface_audit_data()
    rollback_surfaces = _rollback_surfaces(legacy)
    policy_decisions = _policy_decisions(rollback_surfaces, overall)
    implementation_plan = _implementation_plan(rollback_surfaces)
    static_checks = _static_wiring_checks(root)
    checks = _checks(overall, legacy, rollback_surfaces, policy_decisions, static_checks, root)
    blockers = _blockers(checks)
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "rollback_flags_removed_by_1_13_8": True,
            "planner_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "advanced_observing_changed": False,
            "sky_compass_changed": False,
            "detail_object_changed": False,
            "equipment_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "source_reports": tuple(str(path).replace("\\", "/") for path in SOURCE_REPORTS),
            "version": _read_text(root / "VERSION").strip(),
        },
        "readiness": {
            "verdict": (
                "rollback_cleanup_implemented_internal_rollbacks_removed"
                if not blockers
                else "rollback_cleanup_policy_needs_review"
            ),
            "rollback_cleanup_recommended": False,
            "rollback_cleanup_implemented": not blockers,
            "safe_to_implement_cleanup_next": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "public_compatibility_required": False,
            "recommended_next_step": (
                "Review 1.13.8, then proceed to visible explanation planning or "
                "Universe/catalogue policy work."
            ),
            "reason": (
                "All remaining rollback paths are internal constructor/service flags, "
                "the app is not distributed, and the default-on NSOM backend surfaces "
                "are closed. 1.13.8 removed those runtime rollback paths; Git history "
                "is the rollback mechanism for a reviewed revert."
            ),
        },
        "rollback_surfaces": rollback_surfaces,
        "policy_decisions": policy_decisions,
        "implementation_plan": implementation_plan,
        "checks": checks,
        "blockers": blockers,
        "static_wiring_checks": static_checks,
        "recommended_sequence": (
            {
                "step": "Review 1.13.7",
                "summary": "Confirm rollback cleanup policy before deleting any runtime branches.",
            },
            {
                "step": "1.13.8 Remove internal legacy rollback paths",
                "summary": (
                    "Remove constructor rollback flags and dead legacy branches in "
                    "a focused runtime cleanup commit with rollback via Git."
                ),
            },
            {
                "step": "Review 1.13.8",
                "summary": "Confirm default runtime behaviour and QML payloads remain stable.",
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_rollback_cleanup_policy_audit_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# NSOM Rollback Cleanup Policy Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit records the policy and closeout state for "
            "internal legacy rollback paths after the backend NSOM migration "
            "closeouts. It is not wired into runtime, QML, logging, network access "
            "or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Rollback cleanup recommended: `{readiness['rollback_cleanup_recommended']}`.",
        f"- Rollback cleanup implemented: `{readiness['rollback_cleanup_implemented']}`.",
        f"- Safe to implement cleanup next: `{readiness['safe_to_implement_cleanup_next']}`.",
        (
            "- Runtime behaviour changed by this audit: "
            f"`{readiness['runtime_behaviour_changed_by_this_audit']}`."
        ),
        f"- Public compatibility required: `{readiness['public_compatibility_required']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Rollback Surfaces",
        "",
        "| Surface | Default flag | Rollback | Recommendation | Reason |",
        "| --- | --- | --- | --- | --- |",
    ]
    for surface in audit["rollback_surfaces"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    surface["surface"],
                    f"`{surface['default_flag']}`",
                    f"`{surface['rollback']}`",
                    f"`{surface['recommendation']}`",
                    surface["reason"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Policy Decisions",
            "",
            "| Decision | Status | Blocks cleanup | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for decision in audit["policy_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_cleanup']}`",
                    decision["reason"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Implementation Plan",
            "",
            "| Phase | Scope | Runtime change allowed by this audit | Validation |",
            "| --- | --- | --- | --- |",
        ]
    )
    for phase in audit["implementation_plan"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{phase['phase']}`",
                    phase["scope"],
                    f"`{phase['runtime_change_allowed_by_this_audit']}`",
                    phase["validation"],
                )
            )
            + " |"
        )

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
            "## Static Wiring",
            "",
            f"- Runtime report imports: `{audit['static_wiring_checks']['runtime_report_import_matches']}`.",
            f"- QML report exposure: `{audit['static_wiring_checks']['qml_report_exposure_matches']}`.",
            "",
            "## Recommended Sequence",
            "",
        ]
    )
    for item in audit["recommended_sequence"]:
        lines.append(f"- `{item['step']}`: {item['summary']}")

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "The policy decision has been implemented by 1.13.8. Internal "
                "runtime rollback constructor parameters are removed; explicit "
                "developer reports can still compare legacy formulas where those "
                "formulas are available."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _rollback_surfaces(legacy: dict[str, object]) -> tuple[dict[str, object], ...]:
    surfaces = []
    for item in legacy["temporary_rollback_surfaces"]:
        surfaces.append(
            {
                "surface": item["surface"],
                "default_flag": item["default_flag"],
                "rollback": item["rollback"],
                "rollback_parameter_present": item["rollback_parameter_present"],
                "public_compatibility_contract": item["public_compatibility_contract"],
                "recommendation": "removed_internal_rollback",
                "reason": (
                    "The NSOM default path is closed and this internal rollback "
                    "constructor path was removed by 1.13.8."
                ),
            }
        )
    return tuple(surfaces)


def _policy_decisions(
    rollback_surfaces: tuple[dict[str, object], ...],
    overall: dict[str, object],
) -> tuple[dict[str, object], ...]:
    return (
        {
            "decision_id": "remove_internal_rollback_flags",
            "status": "implemented_in_1_13_8",
            "blocks_cleanup": False,
            "reason": (
                f"{len(rollback_surfaces)} internal rollback surfaces are recorded "
                "as removed. The runtime constructors no longer expose those "
                "rollback parameters."
            ),
        },
        {
            "decision_id": "public_compatibility_exception",
            "status": "not_required",
            "blocks_cleanup": False,
            "reason": (
                "The legacy audit marks every rollback as internal and the app is "
                "not distributed, so no public compatibility exception is required."
            ),
        },
        {
            "decision_id": "visible_ui_explanation_dependency",
            "status": "cleanup_completed_before_ui_explanation",
            "blocks_cleanup": False,
            "reason": (
                "Rollback cleanup is complete before visible UI/explanation work."
            ),
            "overall_verdict": overall["readiness"]["verdict"],
        },
        {
            "decision_id": "runtime_change_policy",
            "status": "implemented_by_followup",
            "blocks_cleanup": False,
            "reason": (
                "The original audit recorded policy only; 1.13.8 performed the "
                "runtime constructor and branch cleanup."
            ),
        },
    )


def _implementation_plan(
    rollback_surfaces: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    surface_names = ", ".join(surface["surface"] for surface in rollback_surfaces)
    return (
        {
            "phase": "1.13.8",
            "scope": (
                "Completed removal of rollback constructor parameters and runtime "
                f"legacy branches for: {surface_names}."
            ),
            "runtime_change_allowed_by_this_audit": False,
            "validation": (
                "Focused runtime tests must prove default paths, payload shapes and "
                "QML-visible data remain stable."
            ),
        },
        {
            "phase": "post-cleanup-review",
            "scope": "Review removed branches and remaining payload compatibility fields.",
            "runtime_change_allowed_by_this_audit": False,
            "validation": "Run compileall, focused NSOM/default path tests and full pytest if shared runtime changes are broad.",
        },
    )


def _checks(
    overall: dict[str, object],
    legacy: dict[str, object],
    rollback_surfaces: tuple[dict[str, object], ...],
    policy_decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
    root: Path,
) -> dict[str, object]:
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "rollback_surfaces": rollback_surfaces,
                "policy_decisions": policy_decisions,
            }
        ),
        "source_reports_present": all((root / path).exists() for path in SOURCE_REPORTS),
        "overall_backend_ready": overall["readiness"]["verdict"]
        == "overall_backend_nsom_ready_for_next_phase",
        "legacy_cleanup_complete": legacy["readiness"]["verdict"]
        == "legacy_backend_surface_cleanup_complete",
        "rollback_surfaces_recorded": len(rollback_surfaces) > 0,
        "all_rollback_surfaces_internal": all(
            surface["public_compatibility_contract"] is False for surface in rollback_surfaces
        ),
        "all_rollback_parameters_removed_after_cleanup": all(
            surface["rollback_parameter_present"] is False for surface in rollback_surfaces
        ),
        "all_rollback_surfaces_recommended_for_removal": all(
            surface["recommendation"] == "removed_internal_rollback"
            for surface in rollback_surfaces
        ),
        "policy_blocks_no_cleanup": all(
            decision["blocks_cleanup"] is False for decision in policy_decisions
        ),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blocker_names = {
        "strict_json_compatible": "rollback-policy-json-incompatible",
        "source_reports_present": "rollback-policy-source-report-missing",
        "overall_backend_ready": "rollback-policy-overall-backend-not-ready",
        "legacy_cleanup_complete": "rollback-policy-legacy-cleanup-incomplete",
        "rollback_surfaces_recorded": "rollback-policy-no-rollback-surfaces-found",
        "all_rollback_surfaces_internal": "rollback-policy-public-compatibility-risk",
        "all_rollback_parameters_removed_after_cleanup": "rollback-policy-rollback-state-drift",
        "all_rollback_surfaces_recommended_for_removal": "rollback-policy-removal-not-recommended",
        "policy_blocks_no_cleanup": "rollback-policy-decision-blocker",
        "runtime_report_imports_absent": "rollback-policy-runtime-wiring",
        "qml_report_exposure_absent": "rollback-policy-qml-exposure",
        "runtime_behaviour_unchanged_by_audit": "rollback-policy-runtime-change",
    }
    return tuple(name for key, name in blocker_names.items() if checks[key] is not True)


def _static_wiring_checks(root: Path) -> dict[str, object]:
    return {
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "qml_report_exposure_matches": _scan_files(
            root / "astro_viewer" / "app" / "ui",
            ("*.qml",),
            QML_MARKERS,
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


def _strict_json_compatible(payload: object) -> bool:
    try:
        json.dumps(nsom_to_json_compatible(payload), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    write_markdown_report()
