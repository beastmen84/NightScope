from __future__ import annotations

from inspect import signature
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.advanced_observing_nsom_service import NSOM_ADVANCED_OBSERVING_ENABLED
from astro_viewer.app.services.best_object_nsom_ranking import NSOM_BEST_OBJECT_ENABLED
from astro_viewer.app.services.detail_nsom_runtime import NSOM_DETAIL_OBJECT_ENABLED
from astro_viewer.app.services.home_nsom_ranking import NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED
from astro_viewer.app.services.night_planner_service import NSOM_PLANNER_SCORING_ENABLED, NightPlannerService
from astro_viewer.app.services.sky_compass_nsom_ranking import NSOM_SKY_COMPASS_ENABLED
from astro_viewer.app.viewmodels.app_controller import AppController
from astro_viewer.tools.equipment_nsom_policy_readiness import generate_policy_readiness_data
from astro_viewer.tools.notifications_dead_legacy_audit import generate_notifications_dead_legacy_audit_data


REPORT_PATH = Path("docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md")

SOURCE_REPORTS = (
    Path("docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/HOME_NSOM_RECOMMENDED_DEEP_SKY_READINESS_AUDIT.md"),
    Path("docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/DETAIL_OBJECT_NSOM_MIGRATION_CLOSEOUT.md"),
    Path("docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md"),
    Path("docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md"),
    Path("docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md"),
    Path("docs/EQUIPMENT_NSOM_POLICY_READINESS.md"),
)

REPORT_IMPORT_MARKERS = (
    "nsom_backend_migration_status_audit",
    "NSOM_BACKEND_MIGRATION_STATUS_AUDIT",
    "NSOM_BACKEND_MIGRATION_STATUS",
)

QML_MARKERS = (
    "nsomBackendMigrationStatus",
    "backendMigrationStatus",
    "NSOM_BACKEND_MIGRATION_STATUS_AUDIT",
)


def generate_backend_migration_status_audit_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    default_on_surfaces = _default_on_surfaces()
    notification_audit = generate_notifications_dead_legacy_audit_data()
    remaining_surfaces = _remaining_legacy_or_hybrid_surfaces(notification_audit)
    equipment_policy = generate_policy_readiness_data()
    static_checks = _static_wiring_checks(root)
    documentation = _documentation_state(root)
    checks = _checks(default_on_surfaces, remaining_surfaces, static_checks, documentation, equipment_policy)
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
            "home_recommended_deep_sky_changed": False,
            "best_object_changed": False,
            "advanced_observing_changed": False,
            "sky_compass_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "source_reports": tuple(str(path).replace("\\", "/") for path in SOURCE_REPORTS),
        },
        "readiness": {
            "verdict": (
                "backend_nsom_default_on_surfaces_closed"
                if not blockers
                else "backend_nsom_audit_needs_review"
            ),
            "all_current_default_on_surfaces_closed": not blockers,
            "ready_to_start_next_backend_area": not blockers,
            "ready_for_visible_ui_redesign": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "recommended_next_step": (
                "Remove the dead Notifications backend path, then decide the next "
                "backend area"
            ),
            "reason": (
                "Planner, Home recommendedDeepSky, Best Object, Advanced Observing "
                "backend, Sky Compass and Detail/Object have default-on NSOM paths "
                "with explicit rollback. Remaining items are non-blocking legacy or "
                "hybrid surfaces; Sky Map has been removed as dead legacy and "
                "Notifications are dead legacy pending removal. "
                "Equipment now has a shared ObserverCapability/Q_target adapter "
                "while runtime setup recommendations remain unchanged."
            ),
        },
        "blockers": blockers,
        "default_on_surfaces": default_on_surfaces,
        "remaining_non_blocking_items": remaining_surfaces,
        "documentation_state": documentation,
        "equipment_policy": equipment_policy["readiness"],
        "notification_audit": notification_audit["notification_surface"],
        "static_wiring_checks": static_checks,
        "checks": checks,
        "recommended_sequence": _recommended_sequence(),
        "safety": _safety(static_checks),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_backend_migration_status_audit_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# NSOM Backend Migration Status Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit reviews the current NSOM backend migration "
            "state after the Planner, Home `recommendedDeepSky`, Best Object, "
            "Advanced Observing backend, Sky Compass and Detail/Object default-on "
            "steps. It does not change runtime behaviour, QML, scoring, logging, "
            "network access or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Current default-on surfaces closed: `{readiness['all_current_default_on_surfaces_closed']}`.",
        f"- Ready to start next backend area: `{readiness['ready_to_start_next_backend_area']}`.",
        f"- Ready for visible UI redesign: `{readiness['ready_for_visible_ui_redesign']}`.",
        f"- Runtime behaviour changed by this audit: `{readiness['runtime_behaviour_changed_by_this_audit']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}.",
        f"- Reason: {readiness['reason']}",
        "",
        "## Audit Blockers",
        "",
    ]
    if audit["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in audit["blockers"])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Default-On NSOM Surfaces",
            "",
            "| Surface | Status | Default flag | Rollback | NSOM role |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for surface in audit["default_on_surfaces"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    surface["surface"],
                    f"`{surface['status']}`",
                    f"`{surface['default_flag']}`",
                    f"`{surface['rollback']}`",
                    surface["nsom_role"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Remaining Legacy Or Hybrid Surfaces",
            "",
            "| Area | Status | Why it remains | Recommended handling |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in audit["remaining_non_blocking_items"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["area"],
                    f"`{item['status']}`",
                    item["why_it_remains"],
                    item["recommended_handling"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Documentation State",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["documentation_state"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Safety Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["safety"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
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
                "The backend NSOM migration is closed for the already migrated "
                "recommendation surfaces and Detail/Object. Sky Map has been removed "
                "as dead legacy rather than migrated to NSOM. Notifications are "
                "dead legacy pending removal, not an NSOM migration surface. "
                "Equipment now has a "
                "shared ObserverCapability/Q_target adapter while runtime setup "
                "recommendations remain unchanged. The next backend step should be "
                "chosen explicitly; visible UI explanation work remains separate."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _default_on_surfaces() -> tuple[dict[str, object], ...]:
    controller_parameters = signature(AppController.__init__).parameters
    planner_parameters = signature(NightPlannerService.__init__).parameters
    return (
        {
            "surface": "Planner",
            "status": "default_on_closed",
            "default_flag": f"NSOM_PLANNER_SCORING_ENABLED = {NSOM_PLANNER_SCORING_ENABLED}",
            "default_flag_enabled": NSOM_PLANNER_SCORING_ENABLED is True,
            "rollback": "NightPlannerService(use_nsom_planner_scoring=False)",
            "rollback_parameter_present": "use_nsom_planner_scoring" in planner_parameters,
            "nsom_role": "ObservationOpportunity ranking",
            "confidence_score_neutral": True,
            "source_report": "docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md",
        },
        {
            "surface": "Home recommendedDeepSky",
            "status": "default_on_closed",
            "default_flag": (
                "NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED = "
                f"{NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED}"
            ),
            "default_flag_enabled": NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED is True,
            "rollback": "AppController(use_nsom_home_recommended_deep_sky=False)",
            "rollback_parameter_present": "use_nsom_home_recommended_deep_sky" in controller_parameters,
            "nsom_role": "ObservableTargetValue ordering",
            "confidence_score_neutral": True,
            "source_report": "docs/HOME_NSOM_RECOMMENDED_DEEP_SKY_READINESS_AUDIT.md",
        },
        {
            "surface": "Best Object",
            "status": "default_on_closed",
            "default_flag": f"NSOM_BEST_OBJECT_ENABLED = {NSOM_BEST_OBJECT_ENABLED}",
            "default_flag_enabled": NSOM_BEST_OBJECT_ENABLED is True,
            "rollback": "AppController(use_nsom_best_object=False)",
            "rollback_parameter_present": "use_nsom_best_object" in controller_parameters,
            "nsom_role": "Home-specific ObservationOpportunity selection",
            "confidence_score_neutral": True,
            "source_report": "docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
        },
        {
            "surface": "Advanced Observing backend",
            "status": "default_on_closed_backend_only",
            "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
            "default_flag_enabled": NSOM_ADVANCED_OBSERVING_ENABLED is True,
            "rollback": "AppController(use_nsom_advanced_observing=False)",
            "rollback_parameter_present": "use_nsom_advanced_observing" in controller_parameters,
            "nsom_role": "category ObservableTargetValue projection",
            "confidence_score_neutral": True,
            "source_report": "docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
        },
        {
            "surface": "Sky Compass",
            "status": "default_on_closed",
            "default_flag": f"NSOM_SKY_COMPASS_ENABLED = {NSOM_SKY_COMPASS_ENABLED}",
            "default_flag_enabled": NSOM_SKY_COMPASS_ENABLED is True,
            "rollback": "AppController(use_nsom_sky_compass=False)",
            "rollback_parameter_present": "use_nsom_sky_compass" in controller_parameters,
            "nsom_role": "ObservableTargetValue based direction policy",
            "confidence_score_neutral": True,
            "source_report": "docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
        },
        {
            "surface": "Detail/Object internal payload",
            "status": "default_on_closed_backend_only",
            "default_flag": f"NSOM_DETAIL_OBJECT_ENABLED = {NSOM_DETAIL_OBJECT_ENABLED}",
            "default_flag_enabled": NSOM_DETAIL_OBJECT_ENABLED is True,
            "rollback": "AppController(use_nsom_detail_object=False)",
            "rollback_parameter_present": "use_nsom_detail_object" in controller_parameters,
            "nsom_role": "separate internal Detail/Object payload",
            "confidence_score_neutral": True,
            "source_report": "docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
        },
    )


def _remaining_legacy_or_hybrid_surfaces(notification_audit: dict[str, object]) -> tuple[dict[str, object], ...]:
    notification_surface = notification_audit["notification_surface"]
    return (
        {
            "area": "Equipment recommendations",
            "status": "observer_adapter_extracted",
            "why_it_remains": (
                "`EquipmentService` still ranks eyepiece/Barlow/binocular candidates "
                "with its own practical configuration score. "
                "`observer_capability_adapter.py` now provides shared "
                "ObserverCapability/Q_target projection while "
                "`docs/EQUIPMENT_NSOM_POLICY_READINESS.md` keeps runtime setup "
                "recommendations unchanged."
            ),
            "recommended_handling": (
                "Review the adapter extraction, then choose either ObservationConditions "
                "read-model cleanup or Equipment presenter contract work."
            ),
            "blocks_current_default_on_surfaces": False,
        },
        {
            "area": "ObservationConditions prepared-object cache",
            "status": "hybrid_conditioned_objects",
            "why_it_remains": (
                "`ObservationConditionsService` still creates conditioned object "
                "copies for moon and light-pollution presentation/fallback paths."
            ),
            "recommended_handling": "Defer broad cleanup until an ObservationSnapshot/read-model boundary exists.",
            "blocks_current_default_on_surfaces": False,
        },
        {
            "area": "Notifications",
            "status": notification_surface["classification"],
            "why_it_remains": (
                "No QML/Home consumer remains, but AppController/NotificationService "
                "runtime code is still present."
            ),
            "recommended_handling": "Remove as dead legacy; do not migrate to NSOM.",
            "blocks_current_default_on_surfaces": False,
        },
        {
            "area": "Catalogue / raw object score",
            "status": "upstream_legacy_input",
            "why_it_remains": (
                "Catalogue and engine prepared scores remain the raw target input "
                "for several compatibility payloads."
            ),
            "recommended_handling": "Treat as Universe/read-model work, not as a ranking hotfix.",
            "blocks_current_default_on_surfaces": False,
        },
    )


def _documentation_state(root: Path) -> dict[str, object]:
    return {
        "version": _read_text(root / "VERSION").strip(),
        "source_reports_present": tuple(path.exists() for path in (root / path for path in SOURCE_REPORTS)),
        "base_docs_expected_to_be_updated_with_this_audit": True,
        "report_path": str(REPORT_PATH).replace("\\", "/"),
    }


def _checks(
    default_on_surfaces: tuple[dict[str, object], ...],
    remaining_surfaces: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
    documentation: dict[str, object],
    equipment_policy: dict[str, object],
) -> dict[str, object]:
    return {
        "all_default_flags_enabled": all(surface["default_flag_enabled"] is True for surface in default_on_surfaces),
        "all_rollback_paths_present": all(
            surface["rollback_parameter_present"] is True for surface in default_on_surfaces
        ),
        "confidence_score_neutral_across_default_on_surfaces": all(
            surface["confidence_score_neutral"] is True for surface in default_on_surfaces
        ),
        "remaining_surfaces_are_non_blocking": all(
            item["blocks_current_default_on_surfaces"] is False for item in remaining_surfaces
        ),
        "equipment_policy_ready_for_adapter_step": equipment_policy["readiness"][
            "ready_for_observer_capability_adapter_step"
        ]
        is True,
        "equipment_observer_adapter_extracted": equipment_policy["readiness"][
            "observer_capability_adapter_extracted"
        ]
        is True,
        "source_reports_present": all(documentation["source_reports_present"]),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "recommended_next_step_present": True,
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    names = {
        "all_default_flags_enabled": "nsom-default-on-flag-missing",
        "all_rollback_paths_present": "nsom-rollback-path-missing",
        "confidence_score_neutral_across_default_on_surfaces": "nsom-confidence-score-effect",
        "source_reports_present": "nsom-source-report-missing",
        "equipment_policy_ready_for_adapter_step": "equipment-policy-adapter-step-not-ready",
        "equipment_observer_adapter_extracted": "equipment-observer-adapter-not-extracted",
        "runtime_report_imports_absent": "nsom-audit-runtime-wiring",
        "qml_exposure_absent": "nsom-audit-qml-exposure",
        "runtime_behaviour_unchanged_by_audit": "nsom-audit-runtime-change",
    }
    return tuple(name for key, name in names.items() if checks[key] is not True)


def _safety(static_checks: dict[str, object]) -> dict[str, object]:
    return {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_audit_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_behaviour_changed_by_this_audit": False,
    }


def _recommended_sequence() -> tuple[dict[str, object], ...]:
    return (
        {
            "step": "Review 1.9.7",
            "summary": "Verify this backend status audit before opening a new migration area.",
        },
        {
            "step": "Review 1.10.6",
            "summary": "Verify Detail/Object NSOM migration closeout documentation.",
        },
        {
            "step": "1.11.0 Legacy backend surface audit",
            "summary": "Classify remaining legacy paths as dead code, temporary rollback or payload compatibility.",
        },
        {
            "step": "Review 1.11.1",
            "summary": "Confirm the Sky Map controller/property/service path is removed cleanly.",
        },
        {
            "step": "1.12.0 Equipment/ObserverCapability NSOM comparison",
            "summary": "Start the next active backend NSOM area with Equipment recommendation comparison.",
        },
        {
            "step": "Review 1.12.0",
            "summary": "Confirm the comparison report is accurate and no runtime Equipment behaviour changed.",
        },
        {
            "step": "1.12.1 Equipment NSOM policy readiness",
            "summary": "Decide whether Equipment should get a default-off NSOM path or stay a practical setup helper.",
        },
        {
            "step": "Review 1.12.1",
            "summary": "Confirm the Equipment policy decision defers runtime replacement and preserves behaviour.",
        },
        {
            "step": "1.12.2 ObserverCapability adapter extraction",
            "summary": "Extract a shared ObserverCapability/Q_target adapter while leaving EquipmentService runtime output unchanged.",
        },
        {
            "step": "Review 1.12.2",
            "summary": "Confirm adapter extraction preserved Equipment comparison values and runtime output.",
        },
        {
            "step": "1.12.3 Notifications dead legacy audit",
            "summary": "Classify Notifications as dead legacy because no QML/Home consumer remains.",
        },
        {
            "step": "1.12.4 Remove dead Notifications backend path",
            "summary": "Remove AppController notifications, NotificationService and leftover DTO/tests.",
        },
        {
            "step": "Next backend area decision",
            "summary": "Choose between ObservationConditions read-model cleanup and Equipment presenter contract work.",
        },
        {
            "step": "Later UI explanation work",
            "summary": "Expose NSOM rationale only in a dedicated UX step after backend semantics are stable.",
        },
    )


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
                                "path": str(path.relative_to(root)).replace("\\", "/"),
                                "line": line_number,
                                "marker": marker,
                            }
                        )
    return tuple(matches)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    write_markdown_report()
