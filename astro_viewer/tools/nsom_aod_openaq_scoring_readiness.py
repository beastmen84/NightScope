from __future__ import annotations

import json
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


REPORT_PATH = Path("docs/NSOM_AOD_OPENAQ_SCORING_READINESS.md")

REPORT_IMPORT_MARKERS = (
    "nsom_aod_openaq_scoring_readiness",
    "NSOM_AOD_OPENAQ_SCORING_READINESS",
)

QML_MARKERS = (
    "nsomAodOpenAQScoringReadiness",
    "aodOpenAQScoringReadiness",
    "NSOM_AOD_OPENAQ_SCORING_READINESS",
)

SOURCE_MARKERS = (
    {
        "surface": "ObservationConditions aerosol inputs",
        "path": Path("astro_viewer/app/services/observation_conditions_service.py"),
        "markers": (
            "class AodConditionInput",
            "class ParticulateConditionInput",
            "experimental_aerosol_scoring: bool = False",
            "def aod_freshness_weight",
            "def particulate_freshness_weight",
            "def atmospheric_sensitivity_profile",
            "def aerosol_primary_source",
            "def intended_aerosol_modifier",
        ),
    },
    {
        "surface": "AOD/OpenAQ provider quality policy",
        "path": Path("astro_viewer/app/services/aerosol_provider_quality_policy.py"),
        "markers": (
            "class AerosolProviderQualityPolicyService",
            "class AodProviderQualityDecision",
            "class ParticulateProviderQualityDecision",
            "aod_and_particulate_are_not_additive",
            "viirs_sky_background_remains_separate",
            "weather_transparency_remains_separate",
            "moon_geometry_remains_separate",
        ),
    },
    {
        "surface": "NASA AOD provider",
        "path": Path("astro_viewer/app/services/nasa_aod_provider.py"),
        "markers": (
            "VIIRS_PRODUCT",
            "MODIS_PRODUCT",
            "AOD_QA bit decoding",
            "NASA_AOD_CACHE_TTL",
            "NASA_AOD_SEARCH_DAYS",
            "AOD is intentionally not used",
        ),
    },
    {
        "surface": "OpenAQ local atmosphere provider",
        "path": Path("astro_viewer/app/services/openaq_atmosphere_service.py"),
        "markers": (
            "OPENAQ_CACHE_TTL",
            "CURRENT_MAX_AGE",
            "RECENT_MAX_AGE",
            "STALE_MAX_AGE",
            "The result is not used",
        ),
    },
    {
        "surface": "AppController provider input adapters",
        "path": Path("astro_viewer/app/viewmodels/app_controller.py"),
        "markers": (
            "def _aod_condition_input",
            "def _particulate_condition_input",
            "def _aod_freshness_category",
            "def _freshness_age_days",
            "def _finish_local_atmosphere_refresh",
            "def _finish_nasa_aod_refresh",
        ),
    },
    {
        "surface": "NSOM target class AOD/PM limits",
        "path": Path("astro_viewer/app/models/nsom.py"),
        "markers": (
            "max_aod_pm_influence",
            "aod_sensitivity",
            "pm_role",
            "NsomTargetClassProfile",
        ),
    },
)


def generate_aod_openaq_scoring_readiness_data() -> dict[str, object]:
    """Developer-only audit for provider-dependent AOD/OpenAQ scoring readiness."""

    root = Path(__file__).parents[2]
    source_checks = _source_marker_checks(root)
    static_checks = _static_wiring_checks(root)
    provider_contracts = _provider_contracts()
    freshness_policy = _freshness_policy()
    sensitivity_rows = _target_sensitivity_rows()
    source_precedence_rows = _source_precedence_rows()
    score_neutrality_rows = _score_neutrality_rows()
    policy_decisions = _policy_decisions()
    checks = _checks(
        source_checks,
        static_checks,
        provider_contracts,
        freshness_policy,
        sensitivity_rows,
        source_precedence_rows,
        score_neutrality_rows,
        policy_decisions,
    )
    blockers = _blockers(checks, policy_decisions)

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
                "aod_openaq_readiness_needs_review"
                if blockers
                else "aod_openaq_policy_hardened_ready_for_default_off_experiment"
            ),
            "experimental_aerosol_scoring_default": ObservationConditionFeatureFlags().experimental_aerosol_scoring,
            "current_runtime_score_effect": 0.0,
            "ready_for_default_on": False,
            "ready_for_default_off_experiment": not blockers,
            "provider_inputs_available_diagnostically": True,
            "score_formula_implemented": False,
            "recommended_next_step": (
                "Review 1.14.8, then implement a default-off aerosol scoring "
                "experiment if the provider-quality policy is accepted."
            ),
            "reason": (
                "NASA AOD and OpenAQ PM inputs are already adapted as diagnostic "
                "Sky/Confidence data. AOD QA/uncertainty, OpenAQ locality and "
                "double-counting now have explicit policy gates, but the scoring "
                "formula remains intentionally unimplemented and disabled."
            ),
        },
        "provider_contracts": provider_contracts,
        "freshness_policy": freshness_policy,
        "target_sensitivity_rows": sensitivity_rows,
        "source_precedence_rows": source_precedence_rows,
        "score_neutrality_rows": score_neutrality_rows,
        "policy_decisions": policy_decisions,
        "source_marker_checks": source_checks,
        "static_wiring_checks": static_checks,
        "checks": checks,
        "blockers": blockers,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_aod_openaq_scoring_readiness_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# NSOM AOD/OpenAQ Scoring Readiness",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit reviews whether provider-dependent NASA AOD "
            "and OpenAQ particulate inputs are ready to affect NSOM scores. They "
            "are not enabled for scoring in this step. The current runtime keeps "
            "AOD and PM score-neutral, does not change Planner, Home, Best Object, "
            "Advanced Observing, Sky Compass, Detail/Object, Equipment or QML, and "
            "does not add network calls, logging or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Experimental aerosol scoring default: `{readiness['experimental_aerosol_scoring_default']}`.",
        f"- Current runtime score effect: `{readiness['current_runtime_score_effect']}`.",
        f"- Ready for default-on: `{readiness['ready_for_default_on']}`.",
        f"- Ready for default-off experiment: `{readiness['ready_for_default_off_experiment']}`.",
        f"- Score formula implemented: `{readiness['score_formula_implemented']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Provider Contracts",
        "",
        "| Provider | Source | Runtime role | Freshness policy | Scoring status | Blocker |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in audit["provider_contracts"]:
        lines.append(
            "| "
            f"`{row['provider']}` | {row['source']} | {row['runtime_role']} | "
            f"{row['freshness_policy']} | {row['scoring_status']} | {row['blocker']} |"
        )

    lines.extend(
        [
            "",
            "## Freshness Policy",
            "",
            "| Input | Age/category | Weight | Current scoring role |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in audit["freshness_policy"]:
        lines.append(
            f"| `{row['input']}` | `{row['age_or_category']}` | `{row['weight']}` | "
            f"{row['current_scoring_role']} |"
        )

    lines.extend(
        [
            "",
            "## Target Sensitivity Characterization",
            "",
            "| Target class | Sensitivity | Penalty cap | AOD role | PM role | Scoring status |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in audit["target_sensitivity_rows"]:
        lines.append(
            f"| `{row['target_class']}` | `{row['sensitivity']}` | "
            f"`{row['penalty_cap']}` | {row['aod_role']} | {row['pm_role']} | "
            f"{row['scoring_status']} |"
        )

    lines.extend(
        [
            "",
            "## Source Precedence",
            "",
            "| Case | AOD freshness | PM freshness | Primary source | Reason |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in audit["source_precedence_rows"]:
        lines.append(
            f"| `{row['case']}` | `{row['aod_freshness']}` | `{row['pm_freshness']}` | "
            f"`{row['primary_source']}` | {row['reason']} |"
        )

    lines.extend(
        [
            "",
            "## Score Neutrality",
            "",
            "| Case | Target | AOD | PM | Flag off modifier | Flag on modifier | Adjusted score delta |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in audit["score_neutrality_rows"]:
        lines.append(
            f"| `{row['case']}` | `{row['target_class']}` | `{row['aod']}` | `{row['pm']}` | "
            f"`{row['flag_off_modifier']}` | `{row['flag_on_modifier']}` | "
            f"`{row['adjusted_score_delta']}` |"
        )

    lines.extend(
        [
            "",
            "## Policy Decisions",
            "",
            "| Decision | Status | Blocks scoring | Affected layer | Reason |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for decision in audit["policy_decisions"]:
        lines.append(
            f"| `{decision['decision_id']}` | `{decision['status']}` | "
            f"`{decision['blocks_scoring']}` | {decision['affected_layer']} | "
            f"{decision['reason']} |"
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
            "## Blockers",
            "",
        ]
    )
    blockers = audit["blockers"]
    if blockers:
        for blocker in blockers:
            lines.append(f"- `{blocker}`")
    else:
        lines.append("- None.")

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "AOD/OpenAQ should remain score-neutral until a separate default-off "
                "experiment introduces a formula. The provider-quality blockers from "
                "1.14.7 now have explicit policy gates: AOD QA/uncertainty, OpenAQ "
                "locality and freshness, and non-overlap with VIIRS sky background, "
                "weather transparency and Moon geometry."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _provider_contracts() -> tuple[dict[str, object], ...]:
    return (
        {
            "provider": "nasa_aod",
            "source": "NASA Earthdata MAIAC AOD; VIIRS primary, MODIS fallback",
            "runtime_role": "Weather page display plus diagnostic AodConditionInput",
            "freshness_policy": "include current/stale inputs up to seven days; omit historical",
            "scoring_status": "policy-hardened and score-neutral; modifier remains 0.0",
            "blocker": "none for default-off experiment; formula still not implemented",
        },
        {
            "provider": "openaq_particulate",
            "source": "OpenAQ PM2.5/PM10 nearest local stations",
            "runtime_role": "Weather page display plus diagnostic ParticulateConditionInput",
            "freshness_policy": "current <=1 day, recent <=3 days, stale <=7 days, historical omitted",
            "scoring_status": "policy-hardened fallback/context and score-neutral; modifier remains 0.0",
            "blocker": "none for default-off experiment; formula still not implemented",
        },
    )


def _freshness_policy() -> tuple[dict[str, object], ...]:
    service = ObservationConditionsService()
    rows: list[dict[str, object]] = []
    for label, value in (
        ("0 days", service.aod_freshness_weight(age_days=0.0)),
        ("3 days", service.aod_freshness_weight(age_days=3.0)),
        ("4 days", service.aod_freshness_weight(age_days=4.0)),
        ("7 days", service.aod_freshness_weight(age_days=7.0)),
        ("7.01 days", service.aod_freshness_weight(age_days=7.01)),
        ("historical", service.aod_freshness_weight(freshness_category="historical")),
    ):
        rows.append(
            {
                "input": "nasa_aod",
                "age_or_category": label,
                "weight": value,
                "current_scoring_role": "diagnostic confidence only",
            }
        )
    for label, value in (
        ("0 days", service.particulate_freshness_weight(age_days=0.0)),
        ("1 day", service.particulate_freshness_weight(age_days=1.0)),
        ("2 days", service.particulate_freshness_weight(age_days=2.0)),
        ("4 days", service.particulate_freshness_weight(age_days=4.0)),
        ("7 days", service.particulate_freshness_weight(age_days=7.0)),
        ("7.01 days", service.particulate_freshness_weight(age_days=7.01)),
        ("historical", service.particulate_freshness_weight(freshness_category="historical")),
    ):
        rows.append(
            {
                "input": "openaq_particulate",
                "age_or_category": label,
                "weight": value,
                "current_scoring_role": "diagnostic confidence only",
            }
        )
    return tuple(rows)


def _target_sensitivity_rows() -> tuple[dict[str, object], ...]:
    service = ObservationConditionsService()
    rows = []
    for target in _targets():
        profile = service.atmospheric_sensitivity_profile(target)
        rows.append(
            {
                "target_id": target.id,
                "target_class": profile.target_class,
                "sensitivity": profile.sensitivity,
                "penalty_cap": profile.penalty_cap,
                "aod_role": _aod_role(profile.target_class),
                "pm_role": _pm_role(profile.target_class),
                "scoring_status": "characterized only; no score effect",
            }
        )
    return tuple(rows)


def _source_precedence_rows() -> tuple[dict[str, object], ...]:
    service = ObservationConditionsService()
    cases = (
        (
            "fresh_aod_and_pm",
            AodConditionInput(available=True, freshness_category="current", aod_550=0.22, age_days=1.0),
            ParticulateConditionInput(
                available=True,
                freshness_category="current",
                pm25=28.0,
                pm10=64.0,
                age_days=0.2,
            ),
            "fresh AOD is the column aerosol source; PM remains fallback/context",
        ),
        (
            "historical_aod_fresh_pm",
            AodConditionInput(available=True, freshness_category="historical", aod_550=0.22, age_days=9.0),
            ParticulateConditionInput(
                available=True,
                freshness_category="current",
                pm25=28.0,
                pm10=64.0,
                age_days=0.2,
            ),
            "historical AOD is not eligible; PM can be the fallback source",
        ),
        (
            "fresh_aod_missing_pm",
            AodConditionInput(available=True, freshness_category="current", aod_550=0.22, age_days=1.0),
            None,
            "AOD can stand alone when fresh enough",
        ),
        (
            "no_eligible_provider",
            AodConditionInput(available=True, freshness_category="historical", aod_550=0.22, age_days=9.0),
            ParticulateConditionInput(
                available=True,
                freshness_category="historical",
                pm25=28.0,
                pm10=64.0,
                age_days=9.0,
            ),
            "historical provider data remains metadata only",
        ),
    )
    rows = []
    for case, aod, particulate, reason in cases:
        rows.append(
            {
                "case": case,
                "aod_freshness": getattr(aod, "freshness_category", "missing") if aod is not None else "missing",
                "pm_freshness": (
                    getattr(particulate, "freshness_category", "missing")
                    if particulate is not None
                    else "missing"
                ),
                "primary_source": service.aerosol_primary_source(aod, particulate),
                "reason": reason,
            }
        )
    return tuple(rows)


def _score_neutrality_rows() -> tuple[dict[str, object], ...]:
    service = ObservationConditionsService()
    flags_off = ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)
    flags_on = ObservationConditionFeatureFlags(experimental_aerosol_scoring=True)
    aod = AodConditionInput(available=True, freshness_category="current", aod_550=0.44, age_days=1.0)
    particulate = ParticulateConditionInput(
        available=True,
        freshness_category="current",
        pm25=40.0,
        pm10=90.0,
        age_days=0.5,
    )
    cases = (
        ("galaxy_high_aerosol", _target("m31", "M31", "Galaxy", 82), aod, particulate),
        ("diffuse_nebula_high_aerosol", _target("m42", "M42", "Diffuse Nebula", 82), aod, particulate),
        ("planet_protected", _target("mars", "Marte", "Pianeta", 82), aod, particulate),
        ("moon_protected", _target("moon", "Luna", "Satellite naturale", 82), aod, particulate),
        ("missing_providers", _target("m13", "M13", "Globular Cluster", 82), None, None),
    )
    rows = []
    for case, target, case_aod, case_pm in cases:
        conditioned = service.condition_target(
            target,
            ObservationConditionInputs.diagnostic_only(
                aod=case_aod,
                particulate=case_pm,
            ),
        )
        rows.append(
            {
                "case": case,
                "target_class": service.atmospheric_sensitivity_profile(target).target_class,
                "aod": "available" if case_aod is not None else "missing",
                "pm": "available" if case_pm is not None else "missing",
                "flag_off_modifier": service.intended_aerosol_modifier(target, case_aod, case_pm, flags_off),
                "flag_on_modifier": service.intended_aerosol_modifier(target, case_aod, case_pm, flags_on),
                "adjusted_score_delta": conditioned.breakdown.adjusted_score - target.score,
            }
        )
    return tuple(rows)


def _policy_decisions() -> tuple[dict[str, object], ...]:
    return (
        {
            "decision_id": "aod_qa_policy",
            "status": "accepted_for_default_off_experiment",
            "blocks_scoring": False,
            "affected_layer": "Sky / ObservationEnvironment",
            "reason": "AOD requires finite value, freshness, QA raw traceability, uncertainty threshold and pixel support.",
        },
        {
            "decision_id": "aod_pm_source_precedence",
            "status": "accepted_for_readiness",
            "blocks_scoring": False,
            "affected_layer": "Sky / Confidence",
            "reason": "Fresh AOD is primary; PM is fallback/context when AOD is unavailable or historical.",
        },
        {
            "decision_id": "openaq_locality_policy",
            "status": "accepted_for_default_off_experiment",
            "blocks_scoring": False,
            "affected_layer": "Sky / Confidence",
            "reason": "OpenAQ PM is eligible only as local fallback within 25 km; 25-50 km remains context only.",
        },
        {
            "decision_id": "double_counting_policy",
            "status": "accepted_for_default_off_experiment",
            "blocks_scoring": False,
            "affected_layer": "Sky / Session",
            "reason": "AOD and PM are not additive; VIIRS, weather transparency and Moon geometry keep separate ownership.",
        },
        {
            "decision_id": "confidence_metadata_policy",
            "status": "accepted",
            "blocks_scoring": False,
            "affected_layer": "Confidence",
            "reason": "Provider freshness and availability remain metadata and do not change score.",
        },
    )


def _checks(
    source_checks: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
    provider_contracts: tuple[dict[str, object], ...],
    freshness_policy: tuple[dict[str, object], ...],
    sensitivity_rows: tuple[dict[str, object], ...],
    source_precedence_rows: tuple[dict[str, object], ...],
    score_neutrality_rows: tuple[dict[str, object], ...],
    policy_decisions: tuple[dict[str, object], ...],
) -> dict[str, object]:
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "provider_contracts": provider_contracts,
                "freshness_policy": freshness_policy,
                "sensitivity_rows": sensitivity_rows,
                "source_precedence_rows": source_precedence_rows,
                "score_neutrality_rows": score_neutrality_rows,
                "policy_decisions": policy_decisions,
            }
        ),
        "source_markers_all_found": all(item["all_markers_found"] is True for item in source_checks),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "aod_and_openaq_are_external": all(
            row["provider"] in {"nasa_aod", "openaq_particulate"}
            for row in provider_contracts
        ),
        "freshness_policy_has_historical_zero": all(
            row["weight"] == 0.0
            for row in freshness_policy
            if row["age_or_category"] in {"7.01 days", "historical"}
        ),
        "target_sensitivity_order_characterized": _target_sensitivity_order_is_characterized(
            sensitivity_rows
        ),
        "aod_primary_pm_fallback": _source_precedence_is_characterized(source_precedence_rows),
        "aerosol_modifier_score_neutral": all(
            row["flag_off_modifier"] == 0.0
            and row["flag_on_modifier"] == 0.0
            and row["adjusted_score_delta"] == 0
            for row in score_neutrality_rows
        ),
        "provider_quality_policy_accepted": any(
            decision["decision_id"] == "aod_qa_policy"
            and decision["status"] == "accepted_for_default_off_experiment"
            and decision["blocks_scoring"] is False
            for decision in policy_decisions
        ),
        "double_counting_policy_accepted": any(
            decision["decision_id"] == "double_counting_policy"
            and decision["status"] == "accepted_for_default_off_experiment"
            and decision["blocks_scoring"] is False
            for decision in policy_decisions
        ),
        "confidence_metadata_policy_accepted": any(
            decision["decision_id"] == "confidence_metadata_policy"
            and decision["blocks_scoring"] is False
            for decision in policy_decisions
        ),
    }


def _blockers(
    checks: dict[str, object],
    policy_decisions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    blockers = [
        decision["decision_id"]
        for decision in policy_decisions
        if decision["blocks_scoring"] is True
    ]
    blocker_names = {
        "strict_json_compatible": "aod-openaq-json-incompatible",
        "source_markers_all_found": "aod-openaq-source-marker-missing",
        "runtime_report_imports_absent": "aod-openaq-report-runtime-wired",
        "qml_report_exposure_absent": "aod-openaq-report-qml-exposed",
        "aod_and_openaq_are_external": "aod-openaq-provider-boundary-wrong",
        "freshness_policy_has_historical_zero": "aod-openaq-freshness-policy-wrong",
        "target_sensitivity_order_characterized": "aod-openaq-target-sensitivity-not-characterized",
        "aod_primary_pm_fallback": "aod-openaq-source-precedence-wrong",
        "aerosol_modifier_score_neutral": "aod-openaq-score-effect-present",
        "provider_quality_policy_accepted": "aod-openaq-quality-policy-not-accepted",
        "double_counting_policy_accepted": "aod-openaq-double-counting-policy-not-accepted",
        "confidence_metadata_policy_accepted": "aod-openaq-confidence-policy-missing",
    }
    blockers.extend(
        blocker_name
        for check, blocker_name in blocker_names.items()
        if checks.get(check) is not True
    )
    return tuple(dict.fromkeys(blockers))


def _target_sensitivity_order_is_characterized(rows: tuple[dict[str, object], ...]) -> bool:
    by_class = {row["target_class"]: row for row in rows}
    return (
        by_class["galaxy"]["sensitivity"]
        > by_class["diffuse_nebula"]["sensitivity"]
        > by_class["open_cluster"]["sensitivity"]
        > by_class["planet"]["sensitivity"]
        > by_class["moon"]["sensitivity"]
    )


def _source_precedence_is_characterized(rows: tuple[dict[str, object], ...]) -> bool:
    by_case = {row["case"]: row["primary_source"] for row in rows}
    return (
        by_case["fresh_aod_and_pm"] == "aod"
        and by_case["historical_aod_fresh_pm"] == "particulate"
        and by_case["fresh_aod_missing_pm"] == "aod"
        and by_case["no_eligible_provider"] == "none"
    )


def _source_marker_checks(root: Path) -> tuple[dict[str, object], ...]:
    checks = []
    for spec in SOURCE_MARKERS:
        path = root / spec["path"]
        text = _read_text(path)
        missing = tuple(marker for marker in spec["markers"] if marker not in text)
        checks.append(
            {
                "surface": spec["surface"],
                "path": str(spec["path"]).replace("\\", "/"),
                "all_markers_found": not missing,
                "missing_markers": missing,
            }
        )
    return tuple(checks)


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


def _targets() -> tuple[CelestialObject, ...]:
    return (
        _target("moon", "Luna", "Satellite naturale", 92),
        _target("mars", "Marte", "Pianeta", 86),
        _target("m13", "M13", "Globular Cluster", 78),
        _target("m45", "M45", "Open Cluster", 76),
        _target("m57", "M57", "Planetary Nebula", 80),
        _target("m42", "M42", "Diffuse Nebula", 84),
        _target("m31", "M31", "Galaxy", 88),
    )


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


def _aod_role(target_class: str) -> str:
    if target_class in {"galaxy", "diffuse_nebula"}:
        return "primary aerosol/transparency candidate"
    if target_class in {"planet", "moon"}:
        return "minor/protected candidate"
    return "secondary aerosol/transparency candidate"


def _pm_role(target_class: str) -> str:
    if target_class in {"galaxy", "diffuse_nebula"}:
        return "fallback/context when fresh AOD is unavailable"
    if target_class in {"planet", "moon"}:
        return "metadata/context only"
    return "low/medium fallback when fresh AOD is unavailable"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


if __name__ == "__main__":
    write_markdown_report()
