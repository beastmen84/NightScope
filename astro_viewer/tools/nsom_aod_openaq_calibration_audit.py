from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.aerosol_provider_quality_policy import (
    AerosolProviderQualityPolicyService,
)
from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    ObservationConditionFeatureFlags,
    ObservationConditionInputs,
    ObservationConditionsService,
    ParticulateConditionInput,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService


REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_CALIBRATION_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "nsom_aod_openaq_calibration_audit",
    "NSOM_AOD_OPENAQ_CALIBRATION_AUDIT",
)

QML_MARKERS = (
    "nsomAodOpenAQCalibrationAudit",
    "aodOpenAQCalibrationAudit",
    "NSOM_AOD_OPENAQ_CALIBRATION_AUDIT",
)


def generate_aod_openaq_calibration_audit_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    service = ObservationConditionsService()
    policy_service = AerosolProviderQualityPolicyService()
    cases = _cases(service, policy_service)
    static_checks = _static_wiring_checks(root)
    review_items = _review_items(cases)
    checks = _checks(cases, static_checks, review_items)

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
            "verdict": "aod_openaq_targeted_transparency_calibration_applied",
            "default_flag": "ObservationConditionFeatureFlags.experimental_aerosol_scoring = False",
            "default_runtime_score_effect": 0.0,
            "formula_changed_by_calibration": True,
            "weights_tuned_by_calibration": False,
            "penalty_cap_transparency_shape_calibrated": True,
            "ready_for_default_on": False,
            "recommended_next_step": (
                "Review this targeted calibration, then run default-on readiness "
                "only after accepting the remaining aerosol score-scale risk."
            ),
        },
        "formula": {
            "score_modifier": (
                "-target_score * min(max_transparency_loss, "
                "max_transparency_loss * sensitivity * severity * freshness_weight * source_weight)"
            ),
            "max_transparency_loss": "penalty_cap / 100",
            "aod_source_weight": 1.0,
            "particulate_source_weight": 0.6,
            "confidence_role": (
                "Provider confidence and RecommendationConfidence remain metadata. "
                "They gate eligibility but do not scale target-specific score."
            ),
            "not_in_formula": (
                "provider_product_weight",
                "provider_confidence_weight",
                "recommendation_confidence",
                "weather_factor",
                "moon_geometry",
                "viirs_sky_background",
            ),
        },
        "case_count": len(cases),
        "cases": cases,
        "findings": _findings(cases),
        "review_items": review_items,
        "static_wiring_checks": static_checks,
        "checks": checks,
        "default_on_blockers": tuple(
            item["id"] for item in review_items if item["blocks_default_on"] is True
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report = generate_aod_openaq_calibration_audit_data() if data is None else data
    readiness = report["readiness"]
    formula = report["formula"]

    lines = [
        "# NSOM AOD/OpenAQ Calibration Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit reviews the 1.14.12 targeted calibration "
            "of the default-off AOD/OpenAQ scoring experiment across deterministic "
            "target classes, provider states and freshness cases. It converts the "
            "aerosol cap into an explicit transparency loss and derives the "
            "compatibility score modifier from target score. It does not enable "
            "the feature flag and does not change default runtime behaviour."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Default flag: `{readiness['default_flag']}`.",
        f"- Default runtime score effect: `{readiness['default_runtime_score_effect']}`.",
        f"- Formula changed by calibration: `{readiness['formula_changed_by_calibration']}`.",
        f"- Weights tuned by calibration: `{readiness['weights_tuned_by_calibration']}`.",
        f"- Penalty-cap/transparency shape calibrated: `{readiness['penalty_cap_transparency_shape_calibrated']}`.",
        f"- Ready for default-on: `{readiness['ready_for_default_on']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        "",
        "## Formula Under Review",
        "",
        f"- Score modifier: `{formula['score_modifier']}`.",
        f"- Max transparency loss: `{formula['max_transparency_loss']}`.",
        f"- AOD source weight: `{formula['aod_source_weight']}`.",
        f"- OpenAQ PM fallback source weight: `{formula['particulate_source_weight']}`.",
        f"- Confidence role: {formula['confidence_role']}",
        "- Not in formula: "
        + ", ".join(f"`{item}`" for item in formula["not_in_formula"])
        + ".",
        "",
        "## Calibration Matrix",
        "",
        "| Case | Target | Source | Severity | Freshness | Modifier | Score delta | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in report["cases"]:
        lines.append(
            "| "
            f"`{case['case_id']}` | `{case['target_class']}` | "
            f"`{case['primary_source']}` | `{case['severity']}` | "
            f"`{case['freshness_weight']}` | `{case['score_modifier']}` | "
            f"`{case['flag_on_adjusted_score_delta']}` | "
            f"{', '.join(case['notes'])} |"
        )

    lines.extend(
        [
            "",
            "## Findings",
            "",
        ]
    )
    for finding in report["findings"]:
        lines.append(f"- `{finding['id']}`: {finding['summary']}")

    lines.extend(
        [
            "",
            "## Review Items",
            "",
            "| Item | Severity | Blocks default-on | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in report["review_items"]:
        lines.append(
            "| "
            f"`{item['id']}` | `{item['severity']}` | "
            f"`{item['blocks_default_on']}` | {item['reason']} |"
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

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "The targeted calibration aligns the default-off formula with the "
                "NSOM transparency shape while keeping AOD/OpenAQ default-off. AOD "
                "and OpenAQ are not additive, local OpenAQ PM is a weaker fallback, "
                "stale data is reduced, rejected provider inputs are neutral and "
                "confidence remains metadata. The remaining default-on work is "
                "review of the absolute aerosol score scale."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _cases(
    service: ObservationConditionsService,
    policy_service: AerosolProviderQualityPolicyService,
) -> tuple[dict[str, object], ...]:
    flags_on = ObservationConditionFeatureFlags(experimental_aerosol_scoring=True)
    rows: list[dict[str, object]] = []
    for target in _targets():
        for source_case, aod, particulate, notes in _source_cases():
            policy = policy_service.policy(aod, particulate, flags_on)
            breakdown = service.experimental_aerosol_scoring_breakdown(
                target,
                aod,
                particulate,
                flags_on,
            )
            default_conditioned = service.condition_target(
                target,
                ObservationConditionInputs(aod=aod, particulate=particulate),
            )
            flag_on_conditioned = service.condition_target(
                target,
                ObservationConditionInputs(
                    aod=aod,
                    particulate=particulate,
                    feature_flags=flags_on,
                ),
            )
            rows.append(
                {
                    "case_id": f"{target.id}_{source_case}",
                    "target_id": target.id,
                    "target_class": breakdown.target_class,
                    "source_case": source_case,
                    "primary_source": breakdown.primary_source,
                    "policy_primary_source": policy.primary_source,
                    "policy_aod_reasons": policy.aod.reasons,
                    "policy_particulate_reasons": policy.particulate.reasons,
                    "sensitivity": breakdown.sensitivity,
                    "penalty_cap": breakdown.penalty_cap,
                    "max_transparency_loss": breakdown.max_transparency_loss,
                    "severity": breakdown.severity,
                    "freshness_weight": breakdown.freshness_weight,
                    "source_weight": breakdown.source_weight,
                    "transparency_loss": breakdown.transparency_loss,
                    "penalty_points": breakdown.penalty_points,
                    "score_modifier": breakdown.score_modifier,
                    "atmospheric_transparency_factor": breakdown.atmospheric_transparency_factor,
                    "formula": breakdown.formula,
                    "default_adjusted_score_delta": default_conditioned.breakdown.adjusted_score
                    - target.score,
                    "flag_on_adjusted_score_delta": flag_on_conditioned.breakdown.adjusted_score
                    - target.score,
                    "integer_score_change_visible": (
                        flag_on_conditioned.breakdown.adjusted_score != target.score
                    ),
                    "modifier_rounds_away": (
                        breakdown.score_modifier < 0.0
                        and flag_on_conditioned.breakdown.adjusted_score == target.score
                    ),
                    "confidence_score_role": "metadata_only",
                    "breakdown": asdict(breakdown),
                    "notes": notes,
                }
            )
    return tuple(rows)


def _findings(cases: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    by_key = _case_index(cases)
    galaxy_high = by_key[("galaxy", "high_aod_current")]
    galaxy_stale = by_key[("galaxy", "moderate_aod_stale")]
    galaxy_current = by_key[("galaxy", "moderate_aod_current")]
    galaxy_pm = by_key[("galaxy", "pm_only_local")]
    planet_high = by_key[("planet", "high_aod_current")]
    moon_high = by_key[("moon", "high_aod_current")]
    return (
        {
            "id": "deep_sky_directional_penalty",
            "summary": (
                "High AOD penalizes galaxies more than protected solar-system "
                f"targets: galaxy modifier {galaxy_high['score_modifier']}, "
                f"planet {planet_high['score_modifier']}, Moon {moon_high['score_modifier']}."
            ),
        },
        {
            "id": "freshness_reduces_aod_effect",
            "summary": (
                "Stale AOD keeps the same source ownership but halves the current "
                f"freshness effect in the representative galaxy case "
                f"({galaxy_current['score_modifier']} to {galaxy_stale['score_modifier']})."
            ),
        },
        {
            "id": "pm_fallback_weaker_than_aod",
            "summary": (
                "Local OpenAQ PM remains a weaker fallback than AOD for the same "
                f"target class ({galaxy_pm['score_modifier']} vs "
                f"{galaxy_high['score_modifier']})."
            ),
        },
        {
            "id": "protected_target_rounding_visibility",
            "summary": (
                "Planet and Moon aerosol modifiers are intentionally small and can "
                "round away in the integer score path, while remaining visible in "
                "developer breakdowns."
            ),
        },
    )


def _review_items(cases: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    rounded_cases = tuple(case["case_id"] for case in cases if case["modifier_rounds_away"])
    return (
        {
            "id": "aerosol-score-scale-field-validation",
            "severity": "review",
            "blocks_default_on": True,
            "affected_layer": "Sky/ObservationEnvironment",
            "reason": (
                "The formula shape is now transparency-based, but absolute aerosol "
                "score scale still needs human validation before default-on."
            ),
        },
        {
            "id": "penalty-cap-vs-transparency-shape",
            "severity": "calibrated",
            "blocks_default_on": False,
            "affected_layer": "Sky/ObservationEnvironment",
            "reason": (
                "Resolved in 1.14.12: target-class caps are interpreted as maximum "
                "transparency loss and score modifiers are derived from target score."
            ),
        },
        {
            "id": "protected-target-small-modifier-rounding",
            "severity": "note",
            "blocks_default_on": False,
            "affected_layer": "Presentation/score compatibility",
            "reason": (
                "Some protected-target modifiers do not move the rounded integer "
                "score. This is acceptable for default-off review but should be "
                f"known during calibration. Cases: {', '.join(rounded_cases)}."
            ),
        },
    )


def _checks(
    cases: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
    review_items: tuple[dict[str, object], ...],
) -> dict[str, object]:
    by_key = _case_index(cases)
    high_order = (
        by_key[("galaxy", "high_aod_current")]["penalty_points"]
        > by_key[("diffuse_nebula", "high_aod_current")]["penalty_points"]
        > by_key[("planetary_nebula", "high_aod_current")]["penalty_points"]
        > by_key[("globular_cluster", "high_aod_current")]["penalty_points"]
        > by_key[("open_cluster", "high_aod_current")]["penalty_points"]
        > by_key[("planet", "high_aod_current")]["penalty_points"]
        > by_key[("moon", "high_aod_current")]["penalty_points"]
    )
    return {
        "strict_json_compatible": _strict_json_compatible(cases),
        "default_runtime_neutral": all(case["default_adjusted_score_delta"] == 0 for case in cases),
        "feature_flag_default_off": ObservationConditionFeatureFlags().experimental_aerosol_scoring is False,
        "aod_primary_when_eligible": by_key[("galaxy", "high_aod_current")]["primary_source"] == "aod",
        "pm_fallback_when_aod_rejected": by_key[("galaxy", "local_pm_fallback")]["primary_source"]
        == "particulate",
        "pm_context_only_rejected": by_key[("galaxy", "context_pm_rejected")]["primary_source"] == "none",
        "historical_aod_without_pm_neutral": by_key[("galaxy", "historical_aod_no_pm")][
            "score_modifier"
        ]
        == 0.0,
        "high_aod_target_class_order_directional": high_order,
        "stale_aod_reduces_current_effect": (
            abs(by_key[("galaxy", "moderate_aod_stale")]["score_modifier"])
            < abs(by_key[("galaxy", "moderate_aod_current")]["score_modifier"])
        ),
        "pm_fallback_weaker_than_aod": (
            abs(by_key[("galaxy", "pm_only_local")]["score_modifier"])
            < abs(by_key[("galaxy", "high_aod_current")]["score_modifier"])
        ),
        "provider_product_confidence_not_in_score": (
            by_key[("galaxy", "high_aod_modis_confidence")]["score_modifier"]
            == by_key[("galaxy", "high_aod_current")]["score_modifier"]
        ),
        "confidence_not_in_formula": all(
            "confidence" not in str(case["formula"]).lower() for case in cases
        ),
        "protected_target_rounding_cases_identified": any(
            case["modifier_rounds_away"] for case in cases
        ),
        "default_on_blockers_explicit": any(
            item["blocks_default_on"] is True for item in review_items
        ),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
    }


def _targets() -> tuple[CelestialObject, ...]:
    return (
        _target("moon", "Luna", "Satellite naturale"),
        _target("mars", "Marte", "Pianeta"),
        _target("m31", "M31", "Galaxy"),
        _target("m42", "M42", "Diffuse Nebula"),
        _target("m57", "M57", "Planetary Nebula"),
        _target("m13", "M13", "Globular Cluster"),
        _target("m45", "M45", "Open Cluster"),
    )


def _source_cases() -> tuple[
    tuple[str, AodConditionInput | None, ParticulateConditionInput | None, tuple[str, ...]],
    ...,
]:
    return (
        ("no_providers", None, None, ("missing_provider_inputs", "neutral")),
        ("clean_aod_current", _aod(aod_550=0.08), None, ("aod_primary", "clean_aod")),
        ("moderate_aod_current", _aod(aod_550=0.24), None, ("aod_primary", "current")),
        (
            "moderate_aod_stale",
            _aod(aod_550=0.24, age_days=5.0, freshness_category="stale"),
            None,
            ("aod_primary", "stale_half_weight"),
        ),
        ("high_aod_current", _aod(aod_550=0.70), None, ("aod_primary", "high_aod")),
        (
            "high_aod_modis_confidence",
            _aod(aod_550=0.70, product="MCD19A2.061"),
            None,
            ("aod_primary", "product_confidence_metadata"),
        ),
        (
            "local_pm_fallback",
            _aod(aod_550=0.70, uncertainty=0.24),
            _pm(pm25=70.0, pm10=180.0),
            ("aod_rejected_high_uncertainty", "pm_local_fallback"),
        ),
        ("pm_only_local", None, _pm(pm25=70.0, pm10=180.0), ("pm_local_fallback",)),
        (
            "context_pm_rejected",
            _aod(aod_550=0.70, qa_raw=None),
            _pm(pm25=70.0, pm10=180.0, distance_km=35.0),
            ("aod_missing_qa", "pm_context_only_rejected"),
        ),
        (
            "historical_aod_no_pm",
            _aod(aod_550=0.70, age_days=9.0, freshness_category="historical"),
            None,
            ("aod_historical", "neutral"),
        ),
    )


def _target(object_id: str, name: str, object_type: str) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="7.8",
        distance="",
        max_altitude="48 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="22:00 - 02:00",
        notes="Nota.",
        recommended_setup="",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=82,
        score_label=ObservingScoreService.score_label(82),
        difficulty="Media",
        apparent_size="20 arcmin",
        max_angular_size_deg=0.33,
    )


def _aod(
    *,
    aod_550: float,
    uncertainty: float | None = 0.04,
    qa_raw: int | None = 1089,
    product: str = "VNP19A2.002",
    age_days: float = 1.0,
    freshness_category: str = "current",
) -> AodConditionInput:
    return AodConditionInput(
        available=True,
        freshness_category=freshness_category,
        aod_550=aod_550,
        source="NASA Earthdata",
        product=product,
        status="ok",
        age_days=age_days,
        uncertainty=uncertainty,
        qa_raw=qa_raw,
        method="direct_pixel",
    )


def _pm(
    *,
    pm25: float,
    pm10: float,
    distance_km: float = 5.0,
) -> ParticulateConditionInput:
    return ParticulateConditionInput(
        available=True,
        freshness_category="current",
        pm25=pm25,
        pm10=pm10,
        source="OpenAQ Local",
        status="ok",
        age_days=0.25,
        distance_km=distance_km,
    )


def _case_index(cases: tuple[dict[str, object], ...]) -> dict[tuple[str, str], dict[str, object]]:
    return {
        (str(case["target_class"]), str(case["source_case"])): case
        for case in cases
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
