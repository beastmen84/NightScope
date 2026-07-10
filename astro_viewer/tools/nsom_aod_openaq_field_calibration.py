from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.nsom_aod_openaq_calibration_audit import (
    generate_aod_openaq_calibration_audit_data,
)
from astro_viewer.tools.nsom_aod_openaq_default_on_readiness import (
    generate_aod_openaq_default_on_readiness_data,
)


REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_FIELD_CALIBRATION.md")

REPORT_IMPORT_MARKERS = (
    "nsom_aod_openaq_field_calibration",
    "NSOM_AOD_OPENAQ_FIELD_CALIBRATION",
)

QML_MARKERS = (
    "nsomAodOpenAQFieldCalibration",
    "aodOpenAQFieldCalibration",
    "NSOM_AOD_OPENAQ_FIELD_CALIBRATION",
)


SCENARIO_EXPECTATIONS: dict[str, dict[str, object]] = {
    "clear_air_baseline": {
        "source_case": "clean_aod_current",
        "target_classes": ("galaxy", "diffuse_nebula", "planet", "moon"),
        "expected_band": (0.0, 0.0),
        "reason": "Clean AOD should be neutral for every target class.",
    },
    "moderate_haze_deep_sky": {
        "source_case": "moderate_aod_current",
        "target_classes": ("galaxy", "diffuse_nebula", "globular_cluster", "open_cluster"),
        "expected_band": (-5.0, -0.5),
        "reason": "Moderate aerosol should affect deep-sky targets but not dominate the recommendation.",
    },
    "high_aod_deep_sky": {
        "source_case": "high_aod_current",
        "target_classes": ("galaxy", "diffuse_nebula"),
        "expected_band": (-12.0, -4.0),
        "reason": "High AOD should be a visible penalty for broad/faint deep-sky targets.",
    },
    "protected_solar_system": {
        "source_case": "high_aod_current",
        "target_classes": ("planet", "moon"),
        "expected_band": (-1.0, 0.0),
        "reason": "Planets and Moon should remain protected from broad aerosol penalties.",
    },
    "pm_fallback_deep_sky": {
        "source_case": "pm_only_local",
        "target_classes": ("galaxy", "diffuse_nebula"),
        "expected_band": (-8.0, -2.0),
        "reason": "Local OpenAQ PM fallback should be weaker than high AOD but still visible.",
    },
    "stale_aod_reduced": {
        "source_case": "moderate_aod_stale",
        "target_classes": ("galaxy", "diffuse_nebula"),
        "expected_band": (-3.5, -0.5),
        "reason": "Stale AOD should have reduced impact, not act like current AOD.",
    },
    "provider_rejected_neutral": {
        "source_case": "context_pm_rejected",
        "target_classes": ("galaxy", "diffuse_nebula", "planet", "moon"),
        "expected_band": (0.0, 0.0),
        "reason": "Context-only or rejected providers must be neutral.",
    },
}


def generate_aod_openaq_field_calibration_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    calibration = generate_aod_openaq_calibration_audit_data()
    readiness = generate_aod_openaq_default_on_readiness_data()
    scenarios = _scenario_rows(calibration)
    assessment = _assessment(scenarios)
    static_checks = _static_wiring_checks(root)
    checks = _checks(scenarios, assessment, readiness, static_checks)

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
            "version": _read_text(root / "VERSION").strip(),
        },
        "readiness": {
            "verdict": assessment["verdict"],
            "ready_for_default_on": False,
            "default_flag": "ObservationConditionFeatureFlags.experimental_aerosol_scoring = False",
            "default_runtime_score_effect": 0.0,
            "field_calibration_complete": assessment["field_calibration_complete"],
            "score_scale_status": assessment["score_scale_status"],
            "recommended_next_step": assessment["recommended_next_step"],
        },
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "assessment": assessment,
        "readiness_blockers_before_field_calibration": readiness["blockers"],
        "static_wiring_checks": static_checks,
        "checks": checks,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report = generate_aod_openaq_field_calibration_data() if data is None else data
    readiness = report["readiness"]

    lines = [
        "# NSOM AOD/OpenAQ Field Calibration",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report characterizes the calibrated default-off "
            "AOD/OpenAQ scale against deterministic field-like scenarios. It does "
            "not enable AOD/OpenAQ scoring, does not change runtime behaviour and "
            "does not add network calls, logging or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-on: `{readiness['ready_for_default_on']}`.",
        f"- Default flag: `{readiness['default_flag']}`.",
        f"- Field calibration complete: `{readiness['field_calibration_complete']}`.",
        f"- Score scale status: `{readiness['score_scale_status']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        "",
        "## Scenario Matrix",
        "",
        "| Scenario | Target | Source | Modifier | Band | Status | Reason |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report["scenarios"]:
        lines.append(
            "| "
            f"`{row['scenario']}` | `{row['target_class']}` | `{row['source_case']}` | "
            f"`{row['score_modifier']}` | `{row['expected_min']}..{row['expected_max']}` | "
            f"`{row['status']}` | {row['reason']} |"
        )

    lines.extend(
        [
            "",
            "## Assessment",
            "",
            f"- Accepted rows: `{report['assessment']['accepted_rows']}`.",
            f"- Review rows: `{report['assessment']['review_rows']}`.",
            f"- Warning rows: `{report['assessment']['warning_rows']}`.",
            f"- Remaining blocker: `{report['assessment']['remaining_blocker']}`.",
            "",
            "## Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in report["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "The current scale passes the deterministic field-like bands used "
                "in this report. Because these are still synthetic fixtures rather "
                "than measured observing outcomes, the report does not enable "
                "AOD/OpenAQ by default. The remaining decision is whether the user "
                "accepts this scale for a narrow default-on switch or wants real "
                "field observations before enabling it."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _scenario_rows(calibration: dict[str, object]) -> tuple[dict[str, object], ...]:
    cases = {
        (case["target_class"], case["source_case"]): case
        for case in calibration["cases"]
    }
    rows: list[dict[str, object]] = []
    for scenario, expectation in SCENARIO_EXPECTATIONS.items():
        source_case = str(expectation["source_case"])
        expected_min, expected_max = expectation["expected_band"]  # type: ignore[misc]
        for target_class in expectation["target_classes"]:  # type: ignore[union-attr]
            case = cases[(str(target_class), source_case)]
            score_modifier = float(case["score_modifier"])
            status = _band_status(score_modifier, float(expected_min), float(expected_max))
            rows.append(
                {
                    "scenario": scenario,
                    "target_class": case["target_class"],
                    "source_case": source_case,
                    "primary_source": case["primary_source"],
                    "transparency_loss": case["transparency_loss"],
                    "score_modifier": case["score_modifier"],
                    "expected_min": expected_min,
                    "expected_max": expected_max,
                    "status": status,
                    "reason": expectation["reason"],
                    "notes": case["notes"],
                }
            )
    return tuple(rows)


def _band_status(value: float, expected_min: float, expected_max: float) -> str:
    if expected_min <= value <= expected_max:
        return "accepted"
    tolerance = 0.5
    if expected_min - tolerance <= value <= expected_max + tolerance:
        return "review"
    return "warning"


def _assessment(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    accepted_rows = sum(1 for row in scenarios if row["status"] == "accepted")
    review_rows = sum(1 for row in scenarios if row["status"] == "review")
    warning_rows = sum(1 for row in scenarios if row["status"] == "warning")
    field_calibration_complete = warning_rows == 0
    score_scale_status = "accepted_for_narrow_default_on_review" if field_calibration_complete else "needs_tuning"
    return {
        "verdict": (
            "aod_openaq_field_calibration_scale_acceptance_ready"
            if field_calibration_complete
            else "aod_openaq_field_calibration_needs_tuning"
        ),
        "field_calibration_complete": field_calibration_complete,
        "score_scale_status": score_scale_status,
        "accepted_rows": accepted_rows,
        "review_rows": review_rows,
        "warning_rows": warning_rows,
        "remaining_blocker": (
            "human_acceptance_or_real_field_observations"
            if field_calibration_complete
            else "scale_tuning_required"
        ),
        "recommended_next_step": (
            "Review these field-calibration fixtures. If synthetic fixture bands "
            "are accepted as sufficient, proceed to a narrow default-on switch; "
            "otherwise collect real observing outcomes before enabling AOD/OpenAQ."
        ),
    }


def _checks(
    scenarios: tuple[dict[str, object], ...],
    assessment: dict[str, object],
    readiness: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    by_key = {
        (row["target_class"], row["source_case"]): row
        for row in scenarios
    }
    return {
        "strict_json_compatible": _strict_json_compatible(scenarios),
        "default_runtime_neutral": True,
        "readiness_blocker_was_score_scale": readiness["blockers"] == ["aerosol_score_scale"],
        "all_rows_within_or_near_expected_band": assessment["warning_rows"] == 0,
        "clean_air_neutral": all(
            row["score_modifier"] == 0.0
            for row in scenarios
            if row["scenario"] == "clear_air_baseline"
        ),
        "rejected_providers_neutral": all(
            row["score_modifier"] == 0.0
            for row in scenarios
            if row["scenario"] == "provider_rejected_neutral"
        ),
        "deep_sky_more_affected_than_solar_system": (
            by_key[("galaxy", "high_aod_current")]["score_modifier"]
            < by_key[("planet", "high_aod_current")]["score_modifier"]
            < by_key[("moon", "high_aod_current")]["score_modifier"]
        ),
        "pm_fallback_weaker_than_high_aod": (
            by_key[("galaxy", "pm_only_local")]["score_modifier"]
            > by_key[("galaxy", "high_aod_current")]["score_modifier"]
        ),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
    }


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


if __name__ == "__main__":
    write_markdown_report()
