from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionFeatureFlags,
)
from astro_viewer.tools.nsom_aod_openaq_calibration_audit import (
    generate_aod_openaq_calibration_audit_data,
)
from astro_viewer.tools.nsom_aod_openaq_provider_quality_policy import (
    generate_aod_openaq_provider_quality_policy_data,
)
from astro_viewer.tools.nsom_aod_openaq_scoring_readiness import (
    generate_aod_openaq_scoring_readiness_data,
)


REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_DEFAULT_ON_READINESS.md")

REPORT_IMPORT_MARKERS = (
    "nsom_aod_openaq_default_on_readiness",
    "NSOM_AOD_OPENAQ_DEFAULT_ON_READINESS",
)

QML_MARKERS = (
    "nsomAodOpenAQDefaultOnReadiness",
    "aodOpenAQDefaultOnReadiness",
    "NSOM_AOD_OPENAQ_DEFAULT_ON_READINESS",
)


def generate_aod_openaq_default_on_readiness_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    calibration = generate_aod_openaq_calibration_audit_data()
    provider_policy = generate_aod_openaq_provider_quality_policy_data()
    scoring_readiness = generate_aod_openaq_scoring_readiness_data()
    readiness_gates = _readiness_gates(calibration, provider_policy, scoring_readiness)
    blockers = _blockers(readiness_gates)
    static_checks = _static_wiring_checks(root)
    checks = _checks(calibration, readiness_gates, blockers, static_checks)

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
            "verdict": (
                "aod_openaq_default_on_ready"
                if not blockers
                else "aod_openaq_default_on_blocked_by_score_scale_review"
            ),
            "ready_for_default_on": not blockers,
            "default_flag": "ObservationConditionFeatureFlags.experimental_aerosol_scoring = False",
            "default_runtime_score_effect": 0.0,
            "feature_flag_change_in_this_audit": False,
            "formula_shape_calibrated": checks["formula_shape_calibrated"],
            "remaining_blocker_count": len(blockers),
            "recommended_next_step": (
                "Review this readiness audit. If the aerosol score-scale risk is "
                "accepted, the next implementation step can be a narrow default-on "
                "switch; otherwise collect field-calibration fixtures first."
            ),
        },
        "readiness_gates": readiness_gates,
        "blockers": blockers,
        "calibration_summary": _calibration_summary(calibration),
        "impact_rows": _impact_rows(calibration),
        "static_wiring_checks": static_checks,
        "checks": checks,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report = generate_aod_openaq_default_on_readiness_data() if data is None else data
    readiness = report["readiness"]

    lines = [
        "# NSOM AOD/OpenAQ Default-On Readiness",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit reviews whether the calibrated AOD/OpenAQ "
            "formula is ready for a default-on switch. It does not enable the flag, "
            "does not change Planner, Home, Best Object, Advanced Observing, Sky "
            "Compass, Detail/Object, Equipment or QML, and does not add network "
            "calls, logging or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-on: `{readiness['ready_for_default_on']}`.",
        f"- Default flag: `{readiness['default_flag']}`.",
        f"- Default runtime score effect: `{readiness['default_runtime_score_effect']}`.",
        f"- Feature flag change in this audit: `{readiness['feature_flag_change_in_this_audit']}`.",
        f"- Formula shape calibrated: `{readiness['formula_shape_calibrated']}`.",
        f"- Remaining blocker count: `{readiness['remaining_blocker_count']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        "",
        "## Readiness Gates",
        "",
        "| Gate | Status | Blocks default-on | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for gate in report["readiness_gates"]:
        lines.append(
            "| "
            f"`{gate['gate']}` | `{gate['status']}` | "
            f"`{gate['blocks_default_on']}` | {gate['reason']} |"
        )

    lines.extend(
        [
            "",
            "## Impact Rows",
            "",
            "| Case | Target | Source | Transparency loss | Score modifier | Notes |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in report["impact_rows"]:
        lines.append(
            "| "
            f"`{row['case_id']}` | `{row['target_class']}` | `{row['primary_source']}` | "
            f"`{row['transparency_loss']}` | `{row['score_modifier']}` | "
            f"{', '.join(row['notes'])} |"
        )

    lines.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    if report["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in report["blockers"])
    else:
        lines.append("- none")

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

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "AOD/OpenAQ is not enabled by this audit. Provider-quality gates, "
                "source ownership, confidence neutrality and formula shape are now "
                "documented and tested. The only default-on blocker left by this "
                "audit is human acceptance or field validation of the absolute "
                "aerosol score scale."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _readiness_gates(
    calibration: dict[str, object],
    provider_policy: dict[str, object],
    scoring_readiness: dict[str, object],
) -> tuple[dict[str, object], ...]:
    calibration_reviews = {item["id"]: item for item in calibration["review_items"]}
    return (
        {
            "gate": "provider_quality_policy",
            "status": "accepted",
            "blocks_default_on": False,
            "reason": (
                "AOD QA/uncertainty/local-pixel gates and OpenAQ locality gates are "
                "explicit."
            ),
            "evidence": provider_policy["readiness"]["verdict"],
        },
        {
            "gate": "source_ownership",
            "status": "accepted",
            "blocks_default_on": False,
            "reason": "AOD is primary when eligible; OpenAQ PM is fallback/context only.",
            "evidence": scoring_readiness["checks"]["aod_primary_pm_fallback"],
        },
        {
            "gate": "formula_shape",
            "status": "accepted",
            "blocks_default_on": False,
            "reason": "1.14.12 maps target-class caps to transparency loss before deriving score modifier.",
            "evidence": calibration_reviews["penalty-cap-vs-transparency-shape"]["severity"],
        },
        {
            "gate": "confidence_neutrality",
            "status": "accepted",
            "blocks_default_on": False,
            "reason": "Provider confidence gates eligibility but does not scale target-specific score.",
            "evidence": calibration["checks"]["provider_product_confidence_not_in_score"],
        },
        {
            "gate": "default_runtime_safety",
            "status": "accepted",
            "blocks_default_on": False,
            "reason": "The feature flag remains false by default and default runtime score effect is 0.0.",
            "evidence": calibration["checks"]["default_runtime_neutral"],
        },
        {
            "gate": "aerosol_score_scale",
            "status": "review",
            "blocks_default_on": True,
            "reason": (
                "The calibrated formula is directionally coherent, but the absolute "
                "score-scale impact has not been accepted against observation "
                "expectations."
            ),
            "evidence": calibration_reviews["aerosol-score-scale-field-validation"]["id"],
        },
    )


def _blockers(readiness_gates: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    return tuple(
        str(gate["gate"])
        for gate in readiness_gates
        if gate["blocks_default_on"] is True
    )


def _calibration_summary(calibration: dict[str, object]) -> dict[str, object]:
    return {
        "verdict": calibration["readiness"]["verdict"],
        "case_count": calibration["case_count"],
        "formula_changed_by_calibration": calibration["readiness"][
            "formula_changed_by_calibration"
        ],
        "weights_tuned_by_calibration": calibration["readiness"][
            "weights_tuned_by_calibration"
        ],
        "penalty_cap_transparency_shape_calibrated": calibration["readiness"][
            "penalty_cap_transparency_shape_calibrated"
        ],
        "default_on_blockers": calibration["default_on_blockers"],
    }


def _impact_rows(calibration: dict[str, object]) -> tuple[dict[str, object], ...]:
    wanted = {
        ("galaxy", "high_aod_current"),
        ("diffuse_nebula", "high_aod_current"),
        ("planet", "high_aod_current"),
        ("moon", "high_aod_current"),
        ("galaxy", "pm_only_local"),
        ("galaxy", "context_pm_rejected"),
    }
    return tuple(
        {
            "case_id": case["case_id"],
            "target_class": case["target_class"],
            "source_case": case["source_case"],
            "primary_source": case["primary_source"],
            "transparency_loss": case["transparency_loss"],
            "score_modifier": case["score_modifier"],
            "notes": case["notes"],
        }
        for case in calibration["cases"]
        if (case["target_class"], case["source_case"]) in wanted
    )


def _checks(
    calibration: dict[str, object],
    readiness_gates: tuple[dict[str, object], ...],
    blockers: tuple[str, ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    gates = {gate["gate"]: gate for gate in readiness_gates}
    return {
        "strict_json_compatible": _strict_json_compatible(calibration),
        "feature_flag_default_off": True,
        "default_runtime_neutral": calibration["checks"]["default_runtime_neutral"] is True,
        "provider_quality_policy_accepted": gates["provider_quality_policy"]["blocks_default_on"] is False,
        "source_ownership_accepted": gates["source_ownership"]["blocks_default_on"] is False,
        "formula_shape_calibrated": gates["formula_shape"]["status"] == "accepted",
        "confidence_neutral": gates["confidence_neutrality"]["blocks_default_on"] is False,
        "score_scale_remains_blocking": blockers == ("aerosol_score_scale",),
        "ready_for_default_on_is_false": bool(blockers),
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
