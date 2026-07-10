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


REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_DEFAULT_ON_SWITCH.md")

REPORT_IMPORT_MARKERS = (
    "nsom_aod_openaq_default_on_switch",
    "NSOM_AOD_OPENAQ_DEFAULT_ON_SWITCH",
)

QML_MARKERS = (
    "nsomAodOpenAQDefaultOnSwitch",
    "aodOpenAQDefaultOnSwitch",
    "NSOM_AOD_OPENAQ_DEFAULT_ON_SWITCH",
)


def generate_aod_openaq_default_on_switch_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    service = ObservationConditionsService()
    target = _target("m31", "M31", "Galaxy", 82)
    aod = _aod(aod_550=0.44, product="VNP19A2.002")
    modis_aod = _aod(aod_550=0.44, product="MCD19A2.061")
    particulate = _pm(pm25=40.0, pm10=90.0)
    forced_off_flags = ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)
    default_flags = ObservationConditionFeatureFlags()

    default_conditioned = service.condition_target(
        target,
        ObservationConditionInputs(aod=aod, particulate=particulate),
    )
    forced_off_conditioned = service.condition_target(
        target,
        ObservationConditionInputs(
            aod=aod,
            particulate=particulate,
            feature_flags=forced_off_flags,
        ),
    )
    default_breakdown = service.experimental_aerosol_scoring_breakdown(
        target,
        aod,
        particulate,
        default_flags,
    )
    modis_breakdown = service.experimental_aerosol_scoring_breakdown(
        target,
        modis_aod,
        particulate,
        default_flags,
    )
    static_checks = _static_wiring_checks(root)
    checks = _checks(
        target,
        default_conditioned,
        forced_off_conditioned,
        default_breakdown,
        modis_breakdown,
        static_checks,
    )

    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
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
        "review": {
            "reviewed_step": "1.14.18",
            "review_verdict": "safe_to_switch_default_on",
            "accepted_policy": "keep_stale_aod_weight_0_5",
            "reason": (
                "The stale/current replay accepted the score scale and protected "
                "target behaviour. The switch changes only the default feature "
                "flag; provider fetches, formulas, QML payloads and report wiring "
                "are unchanged."
            ),
        },
        "switch": {
            "default_flag": (
                "ObservationConditionFeatureFlags.experimental_aerosol_scoring = "
                f"{default_flags.experimental_aerosol_scoring}"
            ),
            "rollback": "ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)",
            "formula_changed": False,
            "weights_changed": False,
            "provider_calls_changed": False,
            "runtime_effect": (
                "Only condition targets with policy-eligible AOD/OpenAQ inputs can "
                "receive a target-specific aerosol modifier."
            ),
        },
        "example": {
            "target_id": target.id,
            "target_class": default_breakdown.target_class,
            "base_score": target.score,
            "default_adjusted_score": default_conditioned.breakdown.adjusted_score,
            "forced_off_adjusted_score": forced_off_conditioned.breakdown.adjusted_score,
            "default_breakdown": asdict(default_breakdown),
            "forced_off_components": forced_off_conditioned.breakdown.applied_components,
        },
        "static_wiring_checks": static_checks,
        "checks": checks,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report = generate_aod_openaq_default_on_switch_data() if data is None else data
    review = report["review"]
    switch = report["switch"]
    example = report["example"]

    lines = [
        "# NSOM AOD/OpenAQ Default-On Switch",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report records the 1.14.19 AOD/OpenAQ default-on "
            "switch. It changes only the default value of "
            "`ObservationConditionFeatureFlags.experimental_aerosol_scoring`, keeps "
            "the explicit rollback path, and does not add QML exposure, report "
            "runtime wiring, logging, network calls or runtime file writes."
        ),
        "",
        "## Review",
        "",
        f"- Reviewed step: `{review['reviewed_step']}`.",
        f"- Review verdict: `{review['review_verdict']}`.",
        f"- Accepted policy: `{review['accepted_policy']}`.",
        f"- Reason: {review['reason']}",
        "",
        "## Switch",
        "",
        f"- Default flag: `{switch['default_flag']}`.",
        f"- Rollback: `{switch['rollback']}`.",
        f"- Formula changed: `{switch['formula_changed']}`.",
        f"- Weights changed: `{switch['weights_changed']}`.",
        f"- Provider calls changed: `{switch['provider_calls_changed']}`.",
        f"- Runtime effect: {switch['runtime_effect']}",
        "",
        "## Example",
        "",
        f"- Target: `{example['target_id']}` / `{example['target_class']}`.",
        f"- Base score: `{example['base_score']}`.",
        f"- Default adjusted score: `{example['default_adjusted_score']}`.",
        f"- Forced-off adjusted score: `{example['forced_off_adjusted_score']}`.",
        f"- Default primary source: `{example['default_breakdown']['primary_source']}`.",
        f"- Default score modifier: `{example['default_breakdown']['score_modifier']}`.",
        f"- Forced-off components: `{example['forced_off_components']}`.",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    for key, value in report["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")
    return "\n".join(lines) + "\n"


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _checks(
    target: CelestialObject,
    default_conditioned,
    forced_off_conditioned,
    default_breakdown,
    modis_breakdown,
    static_checks: dict[str, object],
) -> dict[str, object]:
    payload = {
        "default_breakdown": asdict(default_breakdown),
        "forced_off_components": forced_off_conditioned.breakdown.applied_components,
    }
    return {
        "strict_json_compatible": _strict_json_compatible(payload),
        "default_flag_enabled": ObservationConditionFeatureFlags().experimental_aerosol_scoring is True,
        "default_path_uses_aod_openaq_when_policy_eligible": (
            default_conditioned.breakdown.aod_modifier < 0.0
            and default_breakdown.primary_source == "aod"
            and default_conditioned.breakdown.adjusted_score < target.score
        ),
        "forced_off_rollback_is_neutral": (
            forced_off_conditioned.breakdown.adjusted_score == target.score
            and forced_off_conditioned.breakdown.aod_modifier == 0.0
            and forced_off_conditioned.breakdown.pm25_modifier == 0.0
            and forced_off_conditioned.breakdown.applied_components == ()
        ),
        "confidence_metadata_does_not_scale_score": (
            default_breakdown.score_modifier == modis_breakdown.score_modifier
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
        notes="Default-on switch fixture.",
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


def _aod(*, aod_550: float, product: str) -> AodConditionInput:
    return AodConditionInput(
        available=True,
        freshness_category="current",
        aod_550=aod_550,
        source="NASA Earthdata",
        product=product,
        status="ok",
        age_days=1.0,
        uncertainty=0.04,
        qa_raw=1089,
        method="direct_pixel",
    )


def _pm(*, pm25: float, pm10: float) -> ParticulateConditionInput:
    return ParticulateConditionInput(
        available=True,
        freshness_category="current",
        pm25=pm25,
        pm10=pm10,
        source="OpenAQ Local",
        status="ok",
        age_days=0.25,
        distance_km=5.0,
    )


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""
