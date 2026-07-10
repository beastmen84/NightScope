from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.aerosol_provider_quality_policy import (
    AEROSOL_SCORING_FORMULA_IMPLEMENTED,
    AOD_LOCAL_NEIGHBORHOOD_MIN_PIXELS,
    AOD_MAX_UNCERTAINTY_FOR_POLICY,
    AOD_MAX_VALUE_FOR_POLICY,
    OPENAQ_CONTEXT_ONLY_KM,
    OPENAQ_LOCAL_REPRESENTATIVE_KM,
    AerosolProviderQualityPolicyService,
)
from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    ObservationConditionFeatureFlags,
    ParticulateConditionInput,
)


REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_PROVIDER_QUALITY_POLICY.md")

REPORT_IMPORT_MARKERS = (
    "nsom_aod_openaq_provider_quality_policy",
    "NSOM_AOD_OPENAQ_PROVIDER_QUALITY_POLICY",
)

QML_MARKERS = (
    "nsomAodOpenAQProviderQualityPolicy",
    "aodOpenAQProviderQualityPolicy",
    "NSOM_AOD_OPENAQ_PROVIDER_QUALITY_POLICY",
)


def generate_aod_openaq_provider_quality_policy_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    service = AerosolProviderQualityPolicyService()
    cases = _policy_cases(service)
    static_checks = _static_wiring_checks(root)
    checks = _checks(cases, static_checks)

    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_policy": False,
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
            "verdict": "aod_openaq_provider_quality_policy_hardened",
            "ready_for_default_off_experiment": True,
            "ready_for_default_on": False,
            "scoring_formula_implemented": AEROSOL_SCORING_FORMULA_IMPLEMENTED,
            "scoring_formula_enabled": AEROSOL_SCORING_FORMULA_IMPLEMENTED
            and ObservationConditionFeatureFlags().experimental_aerosol_scoring,
            "current_runtime_score_effect": 0.0,
            "experimental_aerosol_scoring_default": ObservationConditionFeatureFlags().experimental_aerosol_scoring,
            "recommended_next_step": (
                "Review 1.14.9, then audit/calibrate the default-off aerosol "
                "scoring experiment before any default-on switch."
            ),
            "reason": (
                "AOD QA/uncertainty, OpenAQ locality and source double-counting "
                "have explicit policy gates. Target-specific AOD/OpenAQ scoring "
                "now exists only behind the default-off experimental flag, while "
                "the provider-quality policy itself remains target-neutral."
            ),
        },
        "thresholds": {
            "aod_max_value": AOD_MAX_VALUE_FOR_POLICY,
            "aod_max_uncertainty": AOD_MAX_UNCERTAINTY_FOR_POLICY,
            "aod_local_neighborhood_min_pixels": AOD_LOCAL_NEIGHBORHOOD_MIN_PIXELS,
            "openaq_local_representative_km": OPENAQ_LOCAL_REPRESENTATIVE_KM,
            "openaq_context_only_km": OPENAQ_CONTEXT_ONLY_KM,
        },
        "cases": cases,
        "double_counting_policy": tuple(cases[0]["policy"]["double_counting_rules"]),
        "confidence_policy": tuple(cases[0]["policy"]["confidence_notes"]),
        "static_wiring_checks": static_checks,
        "checks": checks,
        "blockers": (),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report = generate_aod_openaq_provider_quality_policy_data() if data is None else data
    readiness = report["readiness"]
    thresholds = report["thresholds"]

    lines = [
        "# NSOM AOD/OpenAQ Provider Quality Policy",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only policy hardening step resolves the AOD/OpenAQ "
            "provider-quality decisions that blocked a future default-off aerosol "
            "scoring experiment. It does not enable scoring by default, does not "
            "change Planner, Home, Best Object, Advanced Observing, Sky Compass, "
            "Detail/Object, Equipment or QML, and does not add network calls, "
            "automatic logging or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-off experiment: `{readiness['ready_for_default_off_experiment']}`.",
        f"- Ready for default-on: `{readiness['ready_for_default_on']}`.",
        f"- Scoring formula implemented: `{readiness['scoring_formula_implemented']}`.",
        f"- Scoring formula enabled: `{readiness['scoring_formula_enabled']}`.",
        f"- Current runtime score effect: `{readiness['current_runtime_score_effect']}`.",
        f"- Experimental aerosol scoring default: `{readiness['experimental_aerosol_scoring_default']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Policy Thresholds",
        "",
        "| Threshold | Value |",
        "| --- | --- |",
    ]
    for key, value in thresholds.items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Scenario Decisions",
            "",
            "| Case | Primary source | AOD role | AOD eligible | PM role | PM eligible | Score modifier | Notes |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for case in report["cases"]:
        policy = case["policy"]
        aod = policy["aod"]
        particulate = policy["particulate"]
        notes = ", ".join(
            tuple(aod["reasons"])
            + tuple(particulate["reasons"])
            + tuple(case["expectation_notes"])
        )
        lines.append(
            "| "
            f"`{case['case']}` | `{policy['primary_source']}` | `{aod['role']}` | "
            f"`{aod['eligible_for_future_scoring']}` | `{particulate['role']}` | "
            f"`{particulate['eligible_for_future_fallback']}` | "
            f"`{policy['score_modifier']}` | {notes or 'accepted'} |"
        )

    lines.extend(
        [
            "",
            "## Double-Counting Policy",
            "",
        ]
    )
    for rule in report["double_counting_policy"]:
        lines.append(f"- `{rule}`")

    lines.extend(
        [
            "",
            "## Confidence Policy",
            "",
        ]
    )
    for note in report["confidence_policy"]:
        lines.append(f"- `{note}`")

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
                "The provider-quality blockers are now explicit policy gates. "
                "Fresh, QA-traceable, low-uncertainty AOD is the only primary "
                "aerosol-column source for a future experiment; OpenAQ PM can "
                "only be local fallback/context when AOD is not policy-eligible. "
                "VIIRS sky background, weather transparency and Moon geometry "
                "remain separate owners. The target-specific formula is available "
                "only through the explicit default-off experiment flag."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _policy_cases(service: AerosolProviderQualityPolicyService) -> tuple[dict[str, object], ...]:
    rows = []
    for case, aod, particulate, expectation_notes in (
        (
            "fresh_viirs_aod_local_pm",
            _aod(),
            _pm(distance_km=4.0),
            ("aod_primary_pm_context_only",),
        ),
        (
            "aod_high_uncertainty_pm_local_fallback",
            _aod(uncertainty=0.22),
            _pm(distance_km=4.0),
            ("aod_rejected_pm_fallback",),
        ),
        (
            "aod_missing_qa_pm_local_fallback",
            _aod(qa_raw=None),
            _pm(distance_km=4.0),
            ("aod_rejected_missing_qa",),
        ),
        (
            "aod_sparse_neighborhood_pm_local_fallback",
            _aod(method="local_neighborhood", local_valid_pixel_count=1),
            _pm(distance_km=4.0),
            ("aod_rejected_sparse_local_pixels",),
        ),
        (
            "historical_aod_local_pm",
            _aod(freshness_category="historical", age_days=9.0),
            _pm(distance_km=4.0),
            ("historical_aod_not_primary",),
        ),
        (
            "missing_aod_local_pm",
            None,
            _pm(distance_km=4.0),
            ("pm_fallback_when_aod_missing",),
        ),
        (
            "missing_aod_context_distance_pm",
            None,
            _pm(distance_km=35.0),
            ("pm_context_only_not_scoring_representative",),
        ),
        (
            "missing_aod_distant_pm",
            None,
            _pm(distance_km=75.0),
            ("pm_rejected_too_distant",),
        ),
        (
            "missing_aod_unknown_distance_pm",
            None,
            _pm(distance_km=None),
            ("pm_rejected_unknown_distance",),
        ),
        (
            "no_provider_data",
            None,
            None,
            ("no_aerosol_provider_for_scoring",),
        ),
    ):
        policy = service.policy(
            aod,
            particulate,
            ObservationConditionFeatureFlags(experimental_aerosol_scoring=True),
        )
        rows.append(
            {
                "case": case,
                "policy": asdict(policy),
                "expectation_notes": expectation_notes,
            }
        )
    return tuple(rows)


def _aod(
    *,
    freshness_category: str = "current",
    age_days: float = 1.0,
    uncertainty: float | None = 0.04,
    qa_raw: int | None = 1089,
    method: str = "direct_pixel",
    local_valid_pixel_count: int | None = None,
) -> AodConditionInput:
    return AodConditionInput(
        available=True,
        freshness_category=freshness_category,
        aod_550=0.24,
        source="NASA Earthdata",
        product="VNP19A2.002",
        status="ok",
        age_days=age_days,
        uncertainty=uncertainty,
        qa_raw=qa_raw,
        method=method,
        local_valid_pixel_count=local_valid_pixel_count,
    )


def _pm(*, distance_km: float | None) -> ParticulateConditionInput:
    return ParticulateConditionInput(
        available=True,
        freshness_category="current",
        pm25=18.0,
        pm10=42.0,
        source="OpenAQ Local",
        status="ok",
        age_days=0.25,
        distance_km=distance_km,
    )


def _checks(cases: tuple[dict[str, object], ...], static_checks: dict[str, object]) -> dict[str, object]:
    by_case = {case["case"]: case["policy"] for case in cases}
    return {
        "strict_json_compatible": _strict_json_compatible(cases),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "fresh_aod_is_primary": by_case["fresh_viirs_aod_local_pm"]["primary_source"] == "aod",
        "pm_is_fallback_when_aod_rejected": by_case["aod_high_uncertainty_pm_local_fallback"]["primary_source"]
        == "particulate",
        "pm_context_distance_not_fallback": by_case["missing_aod_context_distance_pm"]["primary_source"] == "none",
        "distant_pm_rejected": by_case["missing_aod_distant_pm"]["primary_source"] == "none",
        "unknown_distance_pm_rejected": by_case["missing_aod_unknown_distance_pm"]["primary_source"] == "none",
        "targetless_policy_score_modifier_neutral": all(
            case["policy"]["score_modifier"] == 0.0
            for case in cases
        ),
        "forced_flag_marks_formula_enabled": all(
            case["policy"]["scoring_formula_enabled"] is True
            for case in cases
        ),
        "double_counting_policy_present": all(
            rule in by_case["fresh_viirs_aod_local_pm"]["double_counting_rules"]
            for rule in (
                "aod_and_particulate_are_not_additive",
                "viirs_sky_background_remains_separate",
                "weather_transparency_remains_separate",
                "moon_geometry_remains_separate",
            )
        ),
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
