from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.observation_conditions_service import ObservationConditionFeatureFlags
from astro_viewer.tools.nsom_aod_openaq_default_on_switch import (
    generate_aod_openaq_default_on_switch_data,
)
from astro_viewer.tools.nsom_backend_migration_status_audit import (
    REPORT_PATH as STATUS_REPORT_PATH,
    generate_backend_migration_status_audit_data,
)


REPORT_PATH = Path("docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md")

REPORT_IMPORT_MARKERS = (
    "nsom_backend_migration_closeout",
    "NSOM_BACKEND_MIGRATION_CLOSEOUT",
)

QML_MARKERS = (
    "nsomBackendMigrationCloseout",
    "backendMigrationCloseout",
    "NSOM_BACKEND_MIGRATION_CLOSEOUT",
)


def generate_backend_migration_closeout_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    status = generate_backend_migration_status_audit_data()
    aod_switch = generate_aod_openaq_default_on_switch_data()
    remaining = tuple(status["remaining_non_blocking_items"])
    static_checks = _static_wiring_checks(root)
    checks = _checks(status, aod_switch, remaining, static_checks)

    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_closeout": False,
            "planner_changed": False,
            "home_recommended_deep_sky_changed": False,
            "best_object_changed": False,
            "advanced_observing_changed": False,
            "sky_compass_changed": False,
            "detail_object_changed": False,
            "equipment_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "status_report": str(STATUS_REPORT_PATH).replace("\\", "/"),
            "version": _read_text(root / "VERSION").strip(),
        },
        "closeout": {
            "verdict": (
                "backend_nsom_recommendation_surfaces_closed"
                if all(checks[key] for key in _blocking_check_names())
                else "backend_nsom_closeout_needs_review"
            ),
            "migration_status": "closed_for_backend_recommendation_surfaces",
            "runtime_behaviour_changed_by_closeout": False,
            "ready_for_visible_ui_redesign": False,
            "backend_default_on_blockers": status["blockers"],
            "recommended_next_step": (
                "Review this closeout, then monitor AOD/OpenAQ real observing "
                "feedback. Future work should treat Catalogue/Universe raw-score "
                "semantics and visible UI explanations as separate design steps."
            ),
            "reason": (
                "Planner, Home recommendedDeepSky, Best Object, Advanced Observing "
                "backend, Sky Compass and Detail/Object are default-on NSOM "
                "surfaces. AOD/OpenAQ condition scoring is also default-on after "
                "the 1.14.19 switch. Equipment remains intentionally setup-local, "
                "ObservationConditions remains an active raw/display compatibility "
                "boundary, and Catalogue raw scores remain upstream Universe input "
                "policy rather than a ranking hotfix."
            ),
        },
        "closed_surfaces": tuple(status["default_on_surfaces"]),
        "aod_openaq_switch": {
            "default_flag": aod_switch["switch"]["default_flag"],
            "rollback": aod_switch["switch"]["rollback"],
            "formula_changed": aod_switch["switch"]["formula_changed"],
            "weights_changed": aod_switch["switch"]["weights_changed"],
            "provider_calls_changed": aod_switch["switch"]["provider_calls_changed"],
            "confidence_metadata_does_not_scale_score": aod_switch["checks"][
                "confidence_metadata_does_not_scale_score"
            ],
        },
        "remaining_non_blocking_items": remaining,
        "future_work_policy": (
            {
                "area": "AOD/OpenAQ real observing feedback",
                "status": "monitor_before_tuning",
                "blocks_backend_closeout": False,
                "policy": "Do not tune weights until enough real observing outcomes are reviewed.",
            },
            {
                "area": "Catalogue / Universe raw score semantics",
                "status": "future_universe_policy",
                "blocks_backend_closeout": False,
                "policy": "Clarify intrinsic catalogue scores as Universe inputs, not as a ranking hotfix.",
            },
            {
                "area": "Visible UI explanations",
                "status": "future_design_step",
                "blocks_backend_closeout": False,
                "policy": "Keep UI unchanged until backend explanations and display semantics are designed explicitly.",
            },
        ),
        "static_wiring_checks": static_checks,
        "checks": checks,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report = generate_backend_migration_closeout_data() if data is None else data
    closeout = report["closeout"]
    aod = report["aod_openaq_switch"]

    lines = [
        "# NSOM Backend Migration Closeout",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only closeout records that the backend NSOM migration "
            "for recommendation surfaces is complete for the current scope. It "
            "does not change scoring, Planner, Home, Best Object, Advanced "
            "Observing, Sky Compass, Detail/Object, Equipment, QML, logging, "
            "network access or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{closeout['verdict']}`.",
        f"- Migration status: `{closeout['migration_status']}`.",
        f"- Runtime behaviour changed by closeout: `{closeout['runtime_behaviour_changed_by_closeout']}`.",
        f"- Ready for visible UI redesign: `{closeout['ready_for_visible_ui_redesign']}`.",
        f"- Backend default-on blockers: `{closeout['backend_default_on_blockers']}`.",
        f"- Recommended next step: {closeout['recommended_next_step']}",
        f"- Reason: {closeout['reason']}",
        "",
        "## Closed Backend Surfaces",
        "",
        "| Surface | Status | Default flag | NSOM role |",
        "| --- | --- | --- | --- |",
    ]
    for surface in report["closed_surfaces"]:
        lines.append(
            "| "
            f"`{surface['surface']}` | `{surface['status']}` | "
            f"`{surface['default_flag']}` | {surface['nsom_role']} |"
        )

    lines.extend(
        [
            "",
            "## AOD/OpenAQ Switch State",
            "",
            f"- Default flag: `{aod['default_flag']}`.",
            f"- Rollback: `{aod['rollback']}`.",
            f"- Formula changed: `{aod['formula_changed']}`.",
            f"- Weights changed: `{aod['weights_changed']}`.",
            f"- Provider calls changed: `{aod['provider_calls_changed']}`.",
            f"- Confidence metadata does not scale score: `{aod['confidence_metadata_does_not_scale_score']}`.",
            "",
            "## Remaining Non-Blocking Items",
            "",
            "| Area | Status | Recommended handling |",
            "| --- | --- | --- |",
        ]
    )
    for item in report["remaining_non_blocking_items"]:
        lines.append(
            "| "
            f"`{item['area']}` | `{item['status']}` | {item['recommended_handling']} |"
        )

    lines.extend(
        [
            "",
            "## Future Work Policy",
            "",
            "| Area | Status | Blocks backend closeout | Policy |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in report["future_work_policy"]:
        lines.append(
            "| "
            f"`{item['area']}` | `{item['status']}` | "
            f"`{item['blocks_backend_closeout']}` | {item['policy']} |"
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
    for key, value in report["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    return "\n".join(lines) + "\n"


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _checks(
    status: dict[str, object],
    aod_switch: dict[str, object],
    remaining: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "status": status["readiness"],
                "aod_switch": aod_switch["switch"],
                "remaining": remaining,
            }
        ),
        "backend_status_has_no_blockers": status["blockers"] == [],
        "all_current_default_on_surfaces_closed": status["readiness"][
            "all_current_default_on_surfaces_closed"
        ]
        is True,
        "aod_openaq_default_on": ObservationConditionFeatureFlags().experimental_aerosol_scoring is True,
        "aod_openaq_rollback_documented": (
            aod_switch["switch"]["rollback"]
            == "ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)"
        ),
        "aod_openaq_confidence_score_neutral": aod_switch["checks"][
            "confidence_metadata_does_not_scale_score"
        ]
        is True,
        "remaining_items_are_non_blocking": all(
            item["blocks_current_default_on_surfaces"] is False for item in remaining
        ),
        "visible_ui_redesign_not_started": status["readiness"]["ready_for_visible_ui_redesign"] is False,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
    }


def _blocking_check_names() -> tuple[str, ...]:
    return (
        "strict_json_compatible",
        "backend_status_has_no_blockers",
        "all_current_default_on_surfaces_closed",
        "aod_openaq_default_on",
        "aod_openaq_rollback_documented",
        "aod_openaq_confidence_score_neutral",
        "remaining_items_are_non_blocking",
        "runtime_report_imports_absent",
        "qml_report_exposure_absent",
    )


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    ui_root = app_root / "ui"
    return {
        "runtime_report_import_matches": _scan_files(app_root, ("*.py",), REPORT_IMPORT_MARKERS),
        "qml_report_exposure_matches": _scan_files(ui_root, ("*.qml",), QML_MARKERS),
    }


def _scan_files(root: Path, patterns: tuple[str, ...], markers: tuple[str, ...]) -> tuple[str, ...]:
    if not root.exists():
        return ()
    matches: list[str] = []
    for pattern in patterns:
        for path in root.rglob(pattern):
            if "__pycache__" in path.parts:
                continue
            text = _read_text(path)
            if any(marker in text for marker in markers):
                matches.append(str(path.relative_to(root.parents[1])).replace("\\", "/"))
    return tuple(sorted(set(matches)))


def _strict_json_compatible(payload: object) -> bool:
    try:
        json.dumps(nsom_to_json_compatible(payload), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
