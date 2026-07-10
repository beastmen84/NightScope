from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    ObservationConditionFeatureFlags,
    ObservationConditionInputs,
    ObservationConditionsService,
    ParticulateConditionInput,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService


REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_DEFAULT_OFF_SCORING_EXPERIMENT.md")

REPORT_IMPORT_MARKERS = (
    "nsom_aod_openaq_default_off_scoring_experiment",
    "NSOM_AOD_OPENAQ_DEFAULT_OFF_SCORING_EXPERIMENT",
)

QML_MARKERS = (
    "nsomAodOpenAQDefaultOffScoringExperiment",
    "aodOpenAQDefaultOffScoringExperiment",
    "NSOM_AOD_OPENAQ_DEFAULT_OFF_SCORING_EXPERIMENT",
)


def generate_aod_openaq_default_off_scoring_experiment_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    service = ObservationConditionsService()
    cases = _cases(service)
    static_checks = _static_wiring_checks(root)
    checks = _checks(cases, static_checks)

    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_report": False,
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
            "verdict": "aod_openaq_default_off_scoring_experiment_implemented",
            "default_flag": "ObservationConditionFeatureFlags.experimental_aerosol_scoring = False",
            "default_runtime_score_effect": 0.0,
            "ready_for_default_on": False,
            "recommended_next_step": (
                "Review 1.14.9, then audit calibration and default-on readiness "
                "for provider-backed aerosol scoring."
            ),
        },
        "formula": {
            "aod_severity": (
                "0.0 if AOD <= 0.10; 0.25 if <= 0.20; 0.50 if <= 0.35; "
                "0.75 if <= 0.60; 1.00 otherwise"
            ),
            "pm_severity": "max(PM2.5 severity, PM10 severity)",
            "source_policy": "policy-eligible AOD primary; local policy-eligible OpenAQ PM fallback only",
            "score_modifier": (
                "-target_score * min(max_transparency_loss, "
                "max_transparency_loss * sensitivity * severity * freshness_weight * source_weight)"
            ),
            "max_transparency_loss": "penalty_cap / 100",
            "source_weights": {
                "aod": 1.0,
                "particulate": 0.6,
            },
            "confidence_role": "RecommendationConfidence and provider confidence remain outside the score formula.",
        },
        "cases": cases,
        "static_wiring_checks": static_checks,
        "checks": checks,
        "blockers": (),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report = generate_aod_openaq_default_off_scoring_experiment_data() if data is None else data
    readiness = report["readiness"]
    formula = report["formula"]

    lines = [
        "# NSOM AOD/OpenAQ Default-Off Scoring Experiment",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report documents the 1.14.9 default-off AOD/OpenAQ "
            "scoring experiment. The implementation adds a target-specific aerosol "
            "modifier only when `ObservationConditionFeatureFlags.experimental_aerosol_scoring` "
            "is explicitly enabled. The default runtime keeps the flag off, so Planner, "
            "Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment "
            "and QML behaviour remain unchanged."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Default flag: `{readiness['default_flag']}`.",
        f"- Default runtime score effect: `{readiness['default_runtime_score_effect']}`.",
        f"- Ready for default-on: `{readiness['ready_for_default_on']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        "",
        "## Formula",
        "",
        f"- AOD severity: {formula['aod_severity']}.",
        f"- PM severity: {formula['pm_severity']}.",
        f"- Source policy: {formula['source_policy']}.",
        f"- Score modifier: `{formula['score_modifier']}`.",
        f"- Max transparency loss: `{formula['max_transparency_loss']}`.",
        f"- Source weights: AOD `{formula['source_weights']['aod']}`, PM `{formula['source_weights']['particulate']}`.",
        f"- Confidence role: {formula['confidence_role']}",
        "",
        "## Cases",
        "",
        "| Case | Target class | Default delta | Experimental source | Experimental modifier | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for case in report["cases"]:
        breakdown = case["experimental_breakdown"]
        lines.append(
            "| "
            f"`{case['case']}` | `{breakdown['target_class']}` | "
            f"`{case['default_adjusted_score_delta']}` | `{breakdown['primary_source']}` | "
            f"`{breakdown['score_modifier']}` | {', '.join(case['notes'])} |"
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
                "The experiment is implemented but intentionally default-off. AOD owns "
                "the aerosol-column contribution when provider-quality gates pass; "
                "OpenAQ PM is a weaker local fallback only. VIIRS sky brightness, Moon "
                "geometry, weather/session state and RecommendationConfidence remain "
                "separate NSOM owners."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _cases(service: ObservationConditionsService) -> tuple[dict[str, object], ...]:
    flags_on = ObservationConditionFeatureFlags(experimental_aerosol_scoring=True)
    rows = []
    for name, target, aod, particulate, notes in (
        (
            "fresh_aod_galaxy",
            _target("m31", "M31", "Galaxy", 82),
            _aod(aod_550=0.44),
            _pm(pm25=55.0, pm10=120.0),
            ("aod_primary", "deep_sky_sensitive"),
        ),
        (
            "fresh_aod_diffuse_nebula",
            _target("m42", "M42", "Diffuse Nebula", 82),
            _aod(aod_550=0.44),
            _pm(pm25=55.0, pm10=120.0),
            ("aod_primary", "nebula_sensitive"),
        ),
        (
            "fresh_aod_planet",
            _target("mars", "Marte", "Pianeta", 82),
            _aod(aod_550=0.44),
            _pm(pm25=55.0, pm10=120.0),
            ("aod_primary", "planet_protected"),
        ),
        (
            "fresh_aod_moon",
            _target("moon", "Luna", "Satellite naturale", 82),
            _aod(aod_550=0.44),
            _pm(pm25=55.0, pm10=120.0),
            ("aod_primary", "moon_protected"),
        ),
        (
            "pm_fallback_galaxy",
            _target("m31", "M31", "Galaxy", 82),
            _aod(aod_550=0.44, uncertainty=0.24),
            _pm(pm25=55.0, pm10=120.0),
            ("aod_rejected", "pm_local_fallback"),
        ),
        (
            "rejected_sources_neutral",
            _target("m31", "M31", "Galaxy", 82),
            _aod(aod_550=0.44, qa_raw=None),
            _pm(pm25=55.0, pm10=120.0, distance_km=35.0),
            ("aod_missing_qa", "pm_context_only"),
        ),
        (
            "confidence_product_neutral",
            _target("m31", "M31", "Galaxy", 82),
            _aod(aod_550=0.44, product="MCD19A2.061"),
            None,
            ("modis_product_confidence_not_score_modifier",),
        ),
    ):
        default = service.condition_target(
            target,
            ObservationConditionInputs(aod=aod, particulate=particulate),
        )
        experimental = service.experimental_aerosol_scoring_breakdown(
            target,
            aod,
            particulate,
            flags_on,
        )
        rows.append(
            {
                "case": name,
                "default_adjusted_score_delta": default.breakdown.adjusted_score - target.score,
                "experimental_breakdown": asdict(experimental),
                "notes": notes,
            }
        )
    return tuple(rows)


def _target(object_id: str, name: str, object_type: str, score: int) -> CelestialObject:
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
        score=score,
        score_label=ObservingScoreService.score_label(score),
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
) -> AodConditionInput:
    return AodConditionInput(
        available=True,
        freshness_category="current",
        aod_550=aod_550,
        source="NASA Earthdata",
        product=product,
        status="ok",
        age_days=1.0,
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


def _checks(
    cases: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    by_case = {case["case"]: case for case in cases}
    return {
        "strict_json_compatible": _strict_json_compatible(cases),
        "default_runtime_neutral": all(case["default_adjusted_score_delta"] == 0 for case in cases),
        "aod_is_primary_when_eligible": by_case["fresh_aod_galaxy"]["experimental_breakdown"]["primary_source"]
        == "aod",
        "pm_is_fallback_when_aod_rejected": by_case["pm_fallback_galaxy"]["experimental_breakdown"]["primary_source"]
        == "particulate",
        "rejected_sources_remain_neutral": by_case["rejected_sources_neutral"]["experimental_breakdown"]["score_modifier"]
        == 0.0,
        "deep_sky_more_sensitive_than_planet_moon": (
            by_case["fresh_aod_galaxy"]["experimental_breakdown"]["penalty_points"]
            > by_case["fresh_aod_planet"]["experimental_breakdown"]["penalty_points"]
            > by_case["fresh_aod_moon"]["experimental_breakdown"]["penalty_points"]
        ),
        "confidence_not_in_formula": all(
            "confidence" not in case["experimental_breakdown"]["formula"].lower()
            for case in cases
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
