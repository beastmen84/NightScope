from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.observation_conditions_service import ObservationConditionFeatureFlags
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService
from astro_viewer.tools.nsom_moon_geometry_planner_calibration import (
    REPORT_PATH as CALIBRATION_REPORT_PATH,
    generate_moon_geometry_planner_calibration_data,
)


REPORT_PATH = Path("docs/NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS.md")

SOURCE_REPORTS = (
    CALIBRATION_REPORT_PATH,
    Path("docs/NSOM_LOCAL_INPUT_MOON_GEOMETRY_READINESS.md"),
)

REPORT_IMPORT_MARKERS = (
    "nsom_moon_geometry_planner_default_on_readiness",
    "NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS",
)

QML_MARKERS = (
    "nsomMoonGeometryPlannerDefaultOnReadiness",
    "moonGeometryPlannerDefaultOnReadiness",
    "NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS",
    "experimental_moon_geometry_scoring",
)


def generate_moon_geometry_planner_default_on_readiness_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    calibration = generate_moon_geometry_planner_calibration_data()
    rows = tuple(calibration["scenario_rows"])
    static_checks = _static_wiring_checks(root)
    decisions = _decisions(calibration, rows)
    checks = _checks(calibration, rows, decisions, static_checks)
    blockers = _blockers(checks, decisions)
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "planner_scoring_changed_by_this_audit": False,
            "home_changed": False,
            "best_object_changed": False,
            "sky_compass_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "source_reports": tuple(str(path).replace("\\", "/") for path in SOURCE_REPORTS),
            "version": _read_text(root / "VERSION").strip(),
        },
        "readiness": {
            "verdict": (
                "moon_geometry_planner_ready_for_default_on_switch"
                if not blockers
                else "moon_geometry_planner_default_on_blocked"
            ),
            "ready_for_default_on_switch": not blockers,
            "default_on_switch_completed": False,
            "requires_separate_switch": True,
            "current_default_flag": (
                "ObservationConditionFeatureFlags.experimental_moon_geometry_scoring = "
                f"{ObservationConditionFeatureFlags().experimental_moon_geometry_scoring}"
            ),
            "night_planner_default_uses_moon_geometry": NightPlannerService().uses_moon_geometry_scoring,
            "opt_in_path_available": _opt_in_path_available(),
            "ready_for_aod_openaq_scoring": False,
            "recommended_next_step": (
                "Review 1.14.5, then implement a narrow default-on switch for "
                "Planner Moon geometry if accepted."
            ),
            "reason": (
                "The 1.14.4 calibration evidence is directionally coherent, "
                "score ownership stays in Sky/ObservationEnvironment, missing "
                "geometry falls back to the illumination-only baseline, and "
                "confidence remains score-neutral. The current runtime default "
                "is still off, so a separate switch is required."
            ),
        },
        "default_on_blockers": blockers,
        "remaining_non_blocking_items": _remaining_non_blocking_items(),
        "decisions": decisions,
        "calibration_summary": calibration["summary"],
        "representative_cases": _representative_cases(rows),
        "checks": checks,
        "static_wiring_checks": static_checks,
    }
    json.dumps(nsom_to_json_compatible(data), sort_keys=True, allow_nan=False)
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = (
        generate_moon_geometry_planner_default_on_readiness_data()
        if data is None
        else data
    )
    readiness = audit["readiness"]

    lines = [
        "# NSOM Moon Geometry Planner Default-On Readiness",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit decides whether the default-off Planner "
            "Moon geometry path has enough evidence for a separate default-on "
            "switch. It does not enable the switch, tune weights, alter Planner "
            "ranking, expose QML, log automatically, call the network or write "
            "runtime files."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-on switch: `{readiness['ready_for_default_on_switch']}`.",
        f"- Default-on switch completed: `{readiness['default_on_switch_completed']}`.",
        f"- Requires separate switch: `{readiness['requires_separate_switch']}`.",
        f"- Current default flag: `{readiness['current_default_flag']}`.",
        (
            "- NightPlannerService default uses Moon geometry: "
            f"`{readiness['night_planner_default_uses_moon_geometry']}`."
        ),
        f"- Opt-in path available: `{readiness['opt_in_path_available']}`.",
        f"- Ready for AOD/OpenAQ scoring: `{readiness['ready_for_aod_openaq_scoring']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Default-On Blockers",
        "",
    ]
    if audit["default_on_blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in audit["default_on_blockers"])
    else:
        lines.append("- None for a narrow Planner Moon geometry default-on switch.")

    lines.extend(
        [
            "",
            "## Decisions",
            "",
            "| Decision | Status | Blocks default-on | Summary | Evidence |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for decision in audit["decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_default_on']}`",
                    str(decision["summary"]),
                    str(decision["evidence"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Representative Cases",
            "",
            "| Case | Target | Score Delta | Lunar Background Delta | Confidence Effect | Interpretation |",
            "| --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for case in audit["representative_cases"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    str(case["geometry_case"]),
                    str(case["target_id"]),
                    f"{float(case['opportunity_score_delta']):+.4f}",
                    f"{float(case['lunar_sky_background_delta']):+.4f}",
                    f"{float(case['confidence_score_effect']):+.4f}",
                    str(case["interpretation"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Remaining Non-Blocking Items",
            "",
        ]
    )
    for item in audit["remaining_non_blocking_items"]:
        lines.append(f"- `{item['item']}`: {item['handling']}")

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
            "## Recommended Next Step",
            "",
            (
                "If review accepts this audit, implement the smallest possible "
                "default-on switch for Planner Moon geometry. Keep AOD/OpenAQ "
                "out of scope until after that switch is reviewed."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _decisions(
    calibration: dict[str, object],
    rows: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    summary = calibration["summary"]
    return (
        {
            "decision_id": "calibration_direction",
            "status": "accepted_for_default_on_review",
            "blocks_default_on": False,
            "summary": (
                "Moon geometry changes follow expected NSOM direction without "
                "legacy score matching."
            ),
            "evidence": (
                f"close_reduced={summary['deep_sky_close_rows_reduced']}; "
                f"set_before_window_improved={summary['deep_sky_set_before_window_rows_improved']}"
            ),
        },
        {
            "decision_id": "missing_geometry_fallback",
            "status": "accepted",
            "blocks_default_on": False,
            "summary": (
                "Missing geometry keeps the illumination-only baseline and leaves "
                "Moon-geometry confidence unknown."
            ),
            "evidence": f"missing_identity={_missing_geometry_identity(rows)}",
        },
        {
            "decision_id": "protected_targets",
            "status": "accepted",
            "blocks_default_on": False,
            "summary": "Planets and Moon remain protected from lunar sky-background damage.",
            "evidence": (
                f"protected_rows_without_delta={summary['protected_target_rows_without_lunar_delta']}"
            ),
        },
        {
            "decision_id": "ownership_boundary",
            "status": "accepted",
            "blocks_default_on": False,
            "summary": (
                "The experimental effect is confined to the Sky-owned "
                "lunar_sky_background component."
            ),
            "evidence": (
                f"only_lunar_rows={summary['rows_with_only_lunar_environment_delta']}"
            ),
        },
        {
            "decision_id": "confidence_metadata",
            "status": "accepted",
            "blocks_default_on": False,
            "summary": "RecommendationConfidence remains metadata and has zero score effect.",
            "evidence": (
                f"rows_with_confidence_score_effect={summary['rows_with_confidence_score_effect']}"
            ),
        },
        {
            "decision_id": "runtime_cost",
            "status": "monitor_after_switch",
            "blocks_default_on": False,
            "summary": (
                "Default-on would add bounded local ephemeris sampling for Planner "
                "targets only when location is available."
            ),
            "evidence": "no_network; app_controller_builds_geometry_only_when_service_flag_is_true",
        },
        {
            "decision_id": "aod_openaq_scope",
            "status": "deferred",
            "blocks_default_on": False,
            "summary": "AOD/OpenAQ provider scoring remains out of scope until Moon geometry is closed.",
            "evidence": "provider_inputs_not_evaluated_by_moon_geometry_audit",
        },
    )


def _checks(
    calibration: dict[str, object],
    rows: tuple[dict[str, object], ...],
    decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, bool]:
    summary = calibration["summary"]
    return {
        "strict_json_compatible": True,
        "calibration_report_developer_only": calibration["metadata"]["developer_only"] is True,
        "calibration_runtime_writes_absent": calibration["metadata"]["runtime_writes"] is False,
        "calibration_network_absent": calibration["metadata"]["network"] is False,
        "calibration_qml_exposure_absent": calibration["metadata"]["qml_exposure"] is False,
        "calibration_scenario_count_ok": calibration["metadata"]["scenario_count"] == 30,
        "deep_sky_close_moon_reduces_value": summary["deep_sky_close_rows_reduced"] == 4,
        "moon_set_before_window_improves_deep_sky": (
            summary["deep_sky_set_before_window_rows_improved"] == 4
        ),
        "planet_and_moon_protected": summary["protected_target_rows_without_lunar_delta"] == 10,
        "only_lunar_environment_component_changes": (
            summary["rows_with_only_lunar_environment_delta"]
            == calibration["metadata"]["scenario_count"]
        ),
        "confidence_zero_score_effect": summary["rows_with_confidence_score_effect"] == 0,
        "missing_geometry_keeps_baseline": _missing_geometry_identity(rows),
        "feature_flag_default_off_now": (
            ObservationConditionFeatureFlags().experimental_moon_geometry_scoring is False
        ),
        "night_planner_default_off_now": NightPlannerService().uses_moon_geometry_scoring is False,
        "opt_in_path_available": _opt_in_path_available(),
        "all_decisions_non_blocking": all(
            decision["blocks_default_on"] is False for decision in decisions
        ),
        "runtime_report_imports_absent": not static_checks["runtime_report_import_matches"],
        "qml_report_exposure_absent": not static_checks["qml_report_exposure_matches"],
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _blockers(
    checks: dict[str, bool],
    decisions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    blockers = [
        key
        for key, value in checks.items()
        if key
        not in {
            "feature_flag_default_off_now",
            "night_planner_default_off_now",
        }
        and value is not True
    ]
    blockers.extend(
        str(decision["decision_id"])
        for decision in decisions
        if decision["blocks_default_on"] is True
    )
    return tuple(blockers)


def _remaining_non_blocking_items() -> tuple[dict[str, str], ...]:
    return (
        {
            "item": "visible_moon_geometry_explanation",
            "handling": "Defer until a separate UI/explanation design step.",
        },
        {
            "item": "runtime_ephemeris_cost_monitoring",
            "handling": "Monitor after switch; calculations are local and bounded.",
        },
        {
            "item": "aod_openaq_provider_scoring",
            "handling": "Handle after Moon geometry default-on review is closed.",
        },
    )


def _representative_cases(rows: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    selections = (
        ("missing", "galaxy", "Missing geometry preserves the baseline."),
        ("set_before_window", "galaxy", "Moon outside the window removes deep-sky penalty."),
        ("high_altitude_close", "galaxy", "Close high Moon reduces deep-sky opportunity."),
        ("high_altitude_far", "galaxy", "Large separation softens deep-sky penalty."),
        ("high_altitude_close", "planet", "Planet remains protected from lunar background damage."),
    )
    return tuple(_case(rows, geometry_case, target_id, interpretation) for geometry_case, target_id, interpretation in selections)


def _case(
    rows: tuple[dict[str, object], ...],
    geometry_case: str,
    target_id: str,
    interpretation: str,
) -> dict[str, object]:
    row = next(
        item
        for item in rows
        if item["geometry_case"] == geometry_case and item["target_id"] == target_id
    )
    return {
        "geometry_case": geometry_case,
        "target_id": target_id,
        "opportunity_score_delta": row["deltas"]["opportunity_score_delta"],
        "lunar_sky_background_delta": row["deltas"]["lunar_sky_background_delta"],
        "confidence_score_effect": row["confidence"]["score_effect"],
        "interpretation": interpretation,
    }


def _missing_geometry_identity(rows: tuple[dict[str, object], ...]) -> bool:
    missing_rows = [row for row in rows if row["geometry_case"] == "missing"]
    return bool(missing_rows) and all(
        abs(row["deltas"]["opportunity_score_delta"]) < 1e-9
        and abs(row["deltas"]["lunar_sky_background_delta"]) < 1e-9
        and row["confidence"]["flag_on_moon_geometry_confidence"] is None
        for row in missing_rows
    )


def _opt_in_path_available() -> bool:
    service = PlannerNsomScoringService(
        feature_flags=ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=True)
    )
    planner = NightPlannerService(nsom_scoring_service=service)
    return service.uses_moon_geometry_scoring is True and planner.uses_moon_geometry_scoring is True


def _static_wiring_checks(root: Path) -> dict[str, object]:
    return {
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
            "*.py",
            REPORT_IMPORT_MARKERS,
        ),
        "qml_report_exposure_matches": _scan_files(
            root / "astro_viewer" / "app" / "ui",
            "*.qml",
            QML_MARKERS,
        ),
    }


def _scan_files(root: Path, pattern: str, markers: tuple[str, ...]) -> tuple[str, ...]:
    if not root.exists():
        return ()
    matches: list[str] = []
    for path in root.rglob(pattern):
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in markers):
            matches.append(str(path).replace("\\", "/"))
    return tuple(matches)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


if __name__ == "__main__":
    write_markdown_report()
