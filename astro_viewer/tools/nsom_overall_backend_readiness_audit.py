from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.equipment_nsom_migration_closeout import (
    generate_equipment_nsom_migration_closeout_data,
)
from astro_viewer.tools.nsom_backend_migration_status_audit import (
    generate_backend_migration_status_audit_data,
)
from astro_viewer.tools.nsom_legacy_backend_surface_audit import (
    generate_legacy_backend_surface_audit_data,
)


REPORT_PATH = Path("docs/NSOM_OVERALL_BACKEND_READINESS_AUDIT.md")

SOURCE_REPORTS = (
    Path("docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md"),
    Path("docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md"),
    Path("docs/EQUIPMENT_NSOM_MIGRATION_CLOSEOUT.md"),
    Path("docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md"),
    Path("docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md"),
    Path("docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/HOME_NSOM_RECOMMENDED_DEEP_SKY_READINESS_AUDIT.md"),
    Path("docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/DETAIL_OBJECT_NSOM_MIGRATION_CLOSEOUT.md"),
)

REPORT_IMPORT_MARKERS = (
    "nsom_overall_backend_readiness_audit",
    "NSOM_OVERALL_BACKEND_READINESS_AUDIT",
    "NSOM_OVERALL_BACKEND_READINESS",
)

QML_MARKERS = (
    "nsomOverallBackendReadiness",
    "overallBackendReadiness",
    "NSOM_OVERALL_BACKEND_READINESS_AUDIT",
)


def generate_overall_backend_readiness_audit_data() -> dict[str, object]:
    """Developer-only NSOM backend readiness roll-up after Equipment closeout."""

    root = Path(__file__).parents[2]
    backend = generate_backend_migration_status_audit_data()
    legacy = generate_legacy_backend_surface_audit_data()
    equipment = generate_equipment_nsom_migration_closeout_data()
    static_checks = _static_wiring_checks(root)
    closed_surfaces = _closed_backend_surfaces(backend, legacy, equipment)
    remaining_items = _remaining_non_blocking_items(backend, legacy)
    next_phase = _next_phase_decisions(remaining_items)
    checks = _checks(backend, legacy, equipment, static_checks, root, closed_surfaces, remaining_items)
    blockers = _blockers(checks)
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_audit": False,
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
                "overall_backend_nsom_ready_for_next_phase"
                if not blockers
                else "overall_backend_nsom_needs_review"
            ),
            "backend_recommendation_surfaces_closed": checks[
                "all_default_on_backend_surfaces_closed"
            ],
            "equipment_closed_setup_local": checks["equipment_closed_setup_local"],
            "dead_legacy_removed": checks["dead_legacy_removed"],
            "runtime_behaviour_changed_by_this_audit": False,
            "rollback_cleanup_completed": checks["all_internal_rollback_paths_removed"],
            "safe_to_start_visible_ui_explanation_design": not blockers,
            "visible_ui_explanation_recommended_now": False,
            "recommended_next_step": (
                "Review 1.13.8, then proceed to visible explanation planning or "
                "Universe/catalogue policy work."
            ),
            "reason": (
                "Planner, Home recommendedDeepSky, Best Object, Advanced Observing "
                "backend, Sky Compass and Detail/Object are closed on NSOM default-on "
                "paths; Equipment is closed as a setup-local NSOM-bounded service; "
                "Sky Map and Notifications are removed dead legacy. Internal "
                "runtime rollback constructor parameters were removed in 1.13.8. "
                "Remaining items are payload compatibility fields and "
                "Universe/catalogue input semantics, neither of which blocks the "
                "closed backend recommendation surfaces."
            ),
        },
        "closed_backend_surfaces": closed_surfaces,
        "remaining_non_blocking_items": remaining_items,
        "next_phase_decisions": next_phase,
        "checks": checks,
        "blockers": blockers,
        "static_wiring_checks": static_checks,
        "recommended_sequence": (
            {
                "step": "Review 1.13.6",
                "summary": "Confirm the overall backend readiness audit is accurate.",
            },
        {
            "step": "Review 1.13.7",
            "summary": "Confirmed rollback cleanup policy before 1.13.8 removed runtime branches.",
        },
            {
                "step": "1.13.8 Remove internal legacy rollback paths",
                "summary": "Completed: internal rollback flags and runtime legacy branches were removed.",
            },
            {
                "step": "Review 1.13.8",
                "summary": "Confirm rollback cleanup left QML payloads and fallback policies stable.",
            },
            {
                "step": "Visible UI/explanation or Universe/catalogue planning",
                "summary": (
                    "Choose the next non-runtime-cleanup NSOM area after the "
                    "backend recommendation surfaces and rollback cleanup are closed."
                ),
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_overall_backend_readiness_audit_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# NSOM Overall Backend Readiness Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit rolls up the backend NSOM migration state "
            "after the Equipment closeout. It does not change runtime behaviour, "
            "scoring, QML, logging, network access or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        (
            "- Backend recommendation surfaces closed: "
            f"`{readiness['backend_recommendation_surfaces_closed']}`."
        ),
        f"- Equipment closed setup-local: `{readiness['equipment_closed_setup_local']}`.",
        f"- Dead legacy removed: `{readiness['dead_legacy_removed']}`.",
        (
            "- Runtime behaviour changed by this audit: "
            f"`{readiness['runtime_behaviour_changed_by_this_audit']}`."
        ),
        (
            "- Rollback cleanup completed: "
            f"`{readiness['rollback_cleanup_completed']}`."
        ),
        (
            "- Safe to start visible UI/explanation design: "
            f"`{readiness['safe_to_start_visible_ui_explanation_design']}`."
        ),
        (
            "- Visible UI/explanation recommended now: "
            f"`{readiness['visible_ui_explanation_recommended_now']}`."
        ),
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Closed Backend Surfaces",
        "",
        "| Surface | Status | NSOM role | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for surface in audit["closed_backend_surfaces"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    surface["surface"],
                    f"`{surface['status']}`",
                    surface["nsom_role"],
                    surface["evidence"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Remaining Non-Blocking Items",
            "",
            "| Item | Classification | Why it remains | Recommended handling |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in audit["remaining_non_blocking_items"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["item"],
                    f"`{item['classification']}`",
                    item["why_it_remains"],
                    item["recommended_handling"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Next Phase Decisions",
            "",
            "| Decision | Priority | Status | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for decision in audit["next_phase_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['priority']}`",
                    f"`{decision['status']}`",
                    decision["reason"],
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
                "The backend NSOM recommendation migration is ready for the next "
                "phase. The rollback cleanup policy has been implemented: internal "
                "legacy rollback flags were removed in 1.13.8 because the application "
                "is not distributed and those branches created more maintenance "
                "surface than product value. Visible UI/explanation work remains a "
                "separate design step."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _closed_backend_surfaces(
    backend: dict[str, object],
    legacy: dict[str, object],
    equipment: dict[str, object],
) -> tuple[dict[str, object], ...]:
    surfaces = tuple(
        {
            "surface": surface["surface"],
            "status": surface["status"],
            "nsom_role": surface["nsom_role"],
            "evidence": surface["source_report"],
            "rollback": surface["rollback"],
            "rollback_parameter_present": surface["rollback_parameter_present"],
            "confidence_score_neutral": surface["confidence_score_neutral"],
        }
        for surface in backend["default_on_surfaces"]
    )
    dead_legacy = tuple(
        {
            "surface": item["surface"],
            "status": item["classification"],
            "nsom_role": "removed dead legacy, not an NSOM migration surface",
            "evidence": "; ".join(item["evidence"]),
            "rollback": "none",
            "rollback_parameter_present": False,
            "confidence_score_neutral": True,
        }
        for item in legacy["dead_legacy_surfaces"]
    )
    equipment_surface = (
        {
            "surface": "Equipment recommendations",
            "status": equipment["readiness"]["verdict"],
            "nsom_role": "setup-local service with explicit NSOM boundaries",
            "evidence": equipment["metadata"]["report_path"],
            "rollback": "not applicable",
            "rollback_parameter_present": False,
            "confidence_score_neutral": equipment["evidence"]["confidence_score_neutral"],
        },
    )
    observation_conditions_surface = (
        {
            "surface": "ObservationConditions consumers",
            "status": backend["observation_conditions_consumer_reroute_audit"]["verdict"],
            "nsom_role": "raw/display read-model compatibility boundary",
            "evidence": "docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md",
            "rollback": "not applicable",
            "rollback_parameter_present": False,
            "confidence_score_neutral": True,
        },
    )
    return surfaces + equipment_surface + observation_conditions_surface + dead_legacy


def _remaining_non_blocking_items(
    backend: dict[str, object],
    legacy: dict[str, object],
) -> tuple[dict[str, object], ...]:
    payload_compatibility = {
        "item": "Legacy/base payload compatibility fields",
        "classification": "presentation_compatibility",
        "why_it_remains": (
            "Existing QML payloads still contain score-shaped compatibility fields "
            "even when NSOM owns ranking."
        ),
        "recommended_handling": (
            "Keep until a separate UI/presentation design decides what to show."
        ),
        "blocks_backend_readiness": False,
        "source_count": len(legacy["payload_compatibility_surfaces"]),
    }
    catalogue_score = next(
        item
        for item in backend["remaining_non_blocking_items"]
        if item["area"] == "Catalogue / raw object score"
    )
    catalogue = {
        "item": "Catalogue / raw object score",
        "classification": catalogue_score["status"],
        "why_it_remains": catalogue_score["why_it_remains"],
        "recommended_handling": catalogue_score["recommended_handling"],
        "blocks_backend_readiness": catalogue_score["blocks_current_default_on_surfaces"],
        "source_count": 1,
    }
    observation_cache = next(
        item
        for item in backend["remaining_non_blocking_items"]
        if item["area"] == "ObservationConditions prepared-object cache"
    )
    observation = {
        "item": "ObservationConditions prepared-object cache",
        "classification": observation_cache["status"],
        "why_it_remains": observation_cache["why_it_remains"],
        "recommended_handling": observation_cache["recommended_handling"],
        "blocks_backend_readiness": observation_cache["blocks_current_default_on_surfaces"],
        "source_count": 1,
    }
    return (payload_compatibility, observation, catalogue)


def _next_phase_decisions(
    remaining_items: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    payload_item = next(item for item in remaining_items if item["item"] == "Legacy/base payload compatibility fields")
    catalogue_item = next(item for item in remaining_items if item["item"] == "Catalogue / raw object score")
    return (
        {
            "decision_id": "rollback_cleanup_closeout",
            "priority": 1,
            "status": "implemented_internal_rollbacks_removed",
            "reason": (
                "1.13.8 removed the internal runtime rollback constructor "
                "parameters; fallback policies now reflect missing inputs or "
                "service failures, not selectable legacy ranking paths."
            ),
            "runtime_change_allowed_by_this_audit": False,
        },
        {
            "decision_id": "visible_ui_explanation_policy",
            "priority": 2,
            "status": "available_after_backend_cleanup",
            "reason": (
                "Backend NSOM is ready for planning visible explanations, but score "
                "display semantics should be designed separately from this audit."
            ),
            "runtime_change_allowed_by_this_audit": False,
        },
        {
            "decision_id": "payload_score_semantics",
            "priority": 3,
            "status": "presentation_followup",
            "reason": (
                f"{payload_item['source_count']} payload compatibility surfaces still "
                "carry legacy/base score fields for QML compatibility."
            ),
            "runtime_change_allowed_by_this_audit": False,
        },
        {
            "decision_id": "catalogue_universe_score_boundary",
            "priority": 4,
            "status": "future_backend_audit",
            "reason": catalogue_item["recommended_handling"],
            "runtime_change_allowed_by_this_audit": False,
        },
    )


def _checks(
    backend: dict[str, object],
    legacy: dict[str, object],
    equipment: dict[str, object],
    static_checks: dict[str, object],
    root: Path,
    closed_surfaces: tuple[dict[str, object], ...],
    remaining_items: tuple[dict[str, object], ...],
) -> dict[str, object]:
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "closed_surfaces": closed_surfaces,
                "remaining_items": remaining_items,
            }
        ),
        "source_reports_present": all((root / path).exists() for path in SOURCE_REPORTS),
        "all_default_on_backend_surfaces_closed": backend["readiness"][
            "all_current_default_on_surfaces_closed"
        ]
        is True,
        "all_default_flags_enabled": backend["checks"]["all_default_flags_enabled"] is True,
        "all_internal_rollback_paths_removed": backend["checks"][
            "all_internal_rollback_paths_removed"
        ]
        is True,
        "equipment_closed_setup_local": equipment["readiness"]["verdict"]
        == "equipment_nsom_migration_closed_setup_local",
        "equipment_runtime_unchanged": equipment["readiness"][
            "runtime_behaviour_changed_by_closeout"
        ]
        is False,
        "legacy_surface_cleanup_complete": legacy["readiness"]["verdict"]
        == "legacy_backend_surface_cleanup_complete",
        "dead_legacy_removed": all(
            item["classification"] == "removed_dead_legacy"
            for item in legacy["dead_legacy_surfaces"]
        ),
        "remaining_items_non_blocking": all(
            item["blocks_backend_readiness"] is False for item in remaining_items
        ),
        "confidence_score_neutral": all(
            surface["confidence_score_neutral"] is True for surface in closed_surfaces
        ),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blocker_names = {
        "strict_json_compatible": "overall-backend-json-incompatible",
        "source_reports_present": "overall-backend-source-report-missing",
        "all_default_on_backend_surfaces_closed": "overall-backend-default-on-surface-open",
        "all_default_flags_enabled": "overall-backend-default-flag-disabled",
        "all_internal_rollback_paths_removed": "overall-backend-internal-rollback-still-present",
        "equipment_closed_setup_local": "overall-backend-equipment-not-closed",
        "equipment_runtime_unchanged": "overall-backend-equipment-runtime-change",
        "legacy_surface_cleanup_complete": "overall-backend-legacy-cleanup-incomplete",
        "dead_legacy_removed": "overall-backend-dead-legacy-present",
        "remaining_items_non_blocking": "overall-backend-blocking-remaining-item",
        "confidence_score_neutral": "overall-backend-confidence-score-effect",
        "runtime_report_imports_absent": "overall-backend-runtime-wiring",
        "qml_report_exposure_absent": "overall-backend-qml-exposure",
        "runtime_behaviour_unchanged_by_audit": "overall-backend-runtime-change",
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
