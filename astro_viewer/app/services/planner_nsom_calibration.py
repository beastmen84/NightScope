from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.night_planner_service import NSOM_PLANNER_SCORING_ENABLED
from astro_viewer.app.services.planner_nsom_comparison import PlannerNsomComparisonService

CALIBRATION_SCENARIO_NAMES = (
    "bright_sky",
    "blocked_session",
    "poor_session",
    "good_session",
    "small_telescope",
    "large_telescope",
    "planet_favouring_conditions",
    "deep_sky_favouring_conditions",
    "moon_target_case",
)

CALIBRATION_SCORE_COMPONENTS = (
    "practical_target_value",
    "observable_target_value",
    "effective_observability",
    "observer_capability_summary",
    "session_viability",
    "observing_window_quality",
    "chronology_fit",
    "practical_constraints",
)

CALIBRATION_REVIEW_STATUSES = ("expected", "review", "warning")

CALIBRATION_REVIEW_THRESHOLDS = {
    "large_rank_delta_review": 3,
    "large_rank_delta_warning": 5,
    "protected_target_min_effective_observability": 0.75,
    "deep_sky_bright_sky_max_effective_observability": 0.75,
    "observer_q_target_review": 0.65,
    "observer_q_target_warning": 0.50,
    "observer_dominance_review_share": 0.75,
    "observer_dominance_warning_share": 0.90,
    "missing_window_expected_quality": 0.50,
    "invisible_target_expected_quality": 0.0,
}

OPPORTUNITY_POLICY_TYPES = (
    "actionable_ranked_recommendation",
    "actionable_with_uncertain_timing",
    "non_actionable_hard_block",
    "non_actionable_invisible_target",
)

BRIGHT_SKY_PROFILES = {
    "bright_sky",
    "strong_moon",
    "high_moon",
    "high_light_pollution",
    "planet_favouring",
    "planet_favouring_conditions",
    "moon_target_case",
}

PROTECTED_TARGET_TYPES = {"planet", "moon"}
BRIGHT_SKY_SENSITIVE_TARGET_TYPES = {"galaxy", "diffuse_nebula"}


@dataclass(frozen=True)
class PlannerNsomCalibrationScenario:
    name: str
    intended_nsom_expectation: str
    targets: tuple[CelestialObject, ...]
    weather: WeatherSummary
    scores: AdvancedObservingScores
    sky_quality: SkyQuality
    telescope: Telescope
    moon: MoonSummary | None


class PlannerNsomCalibrationInspectionService:
    """Developer-only NSOM Planner calibration inspection helper.

    This service is passive: it evaluates fixed in-memory fixtures through the
    comparison/explanation layer and returns JSON-compatible dictionaries. It
    does not write files, log automatically, fetch data, emit signals or expose
    anything to QML.
    """

    def __init__(self, comparison_service: PlannerNsomComparisonService | None = None) -> None:
        self._comparison_service = comparison_service or PlannerNsomComparisonService()

    def inspect(self, scenario_names: Iterable[str] | None = None) -> dict[str, object]:
        scenarios = _calibration_scenarios()
        if scenario_names is not None:
            requested = tuple(scenario_names)
            available = {scenario.name for scenario in scenarios}
            unknown = tuple(name for name in requested if name not in available)
            if unknown:
                raise ValueError(f"Unknown NSOM calibration scenario: {', '.join(unknown)}")
            requested_set = set(requested)
            scenarios = tuple(scenario for scenario in scenarios if scenario.name in requested_set)

        scenario_outputs = tuple(self._inspect_scenario(scenario) for scenario in scenarios)
        return nsom_to_json_compatible(
            {
                "scenario_groups": scenario_outputs,
                "component_ranges": _aggregate_component_ranges(scenario_outputs),
                "factor_coverage": _factor_coverage(scenario_outputs),
                "dominant_limiting_factor_summary": _dominant_limiting_factor_summary(
                    scenario_outputs
                ),
                "calibration_review_summary": _aggregate_calibration_review(scenario_outputs),
                "calibration_review_thresholds": CALIBRATION_REVIEW_THRESHOLDS,
                "metadata": {
                    "developer_only": True,
                    "nsom_planner_scoring_enabled": NSOM_PLANNER_SCORING_ENABLED,
                    "scenario_count": len(scenario_outputs),
                    "scenario_names": tuple(scenario.name for scenario in scenarios),
                    "score_components": CALIBRATION_SCORE_COMPONENTS,
                    "side_effects": {
                        "file_writes": False,
                        "automatic_logging": False,
                        "network": False,
                        "qml_exposure": False,
                    },
                },
            }
        )

    def _inspect_scenario(self, scenario: PlannerNsomCalibrationScenario) -> dict[str, object]:
        comparison = self._comparison_service.compare(
            scenario.targets,
            weather=scenario.weather,
            scores=scenario.scores,
            sky_quality=scenario.sky_quality,
            telescope=scenario.telescope,
            moon=scenario.moon,
        )
        ranked = tuple(
            _inspection_row(item)
            for item in sorted(comparison["items"], key=lambda row: int(row["nsom"]["rank"]))
        )
        axes = _scenario_axes(scenario.name)
        ranked, review_summary, policy_review = annotate_calibration_review_group(
            ranked,
            axes=axes,
        )
        return {
            "name": scenario.name,
            "intended_nsom_expectation": scenario.intended_nsom_expectation,
            "ranked_nsom_opportunities": ranked,
            "component_ranges": _component_ranges(ranked),
            "dominant_limiting_factor": _dominant_limiting_factor(ranked),
            "legacy_reference_ranking": comparison["rankings"]["legacy"],
            "nsom_ranking": comparison["rankings"]["nsom"],
            "comparison_metadata": comparison["metadata"],
            "calibration_review_summary": review_summary,
            "opportunity_policy_review": policy_review,
            "blocked_session_policy_review": policy_review,
        }


def _inspection_row(item: dict[str, object]) -> dict[str, object]:
    nsom = item["nsom"]
    legacy = item["legacy"]
    explanation = nsom["explanation"]
    return {
        "rank": nsom["rank"],
        "object_id": item["object_id"],
        "name": item["name"],
        "object_type": item["object_type"],
        "nsom_score": nsom["score"],
        "legacy_reference": {
            "rank": legacy["rank"],
            "score": legacy["score"],
        },
        "rank_delta": item["rank_delta"],
        "score_delta": item["score_delta"],
        "score_components": explanation["score_components"],
        "component_breakdown": nsom["components"],
        "explanation": explanation,
        "limiting_factors": explanation["main_limiting_factors"],
        "positive_factors": explanation["main_positive_factors"],
    }


def annotate_calibration_review_group(
    rows: tuple[dict[str, object], ...],
    *,
    axes: dict[str, object],
) -> tuple[tuple[dict[str, object], ...], dict[str, object], dict[str, object]]:
    policy_review = opportunity_policy_review(rows, axes=axes)
    annotated_rows = tuple(
        {
            **row,
            "ranking_actionable": policy_review["ranking_actionable"],
            "stable_order_is_deterministic_tie": policy_review[
                "stable_order_is_deterministic_tie"
            ],
            "stable_order_is_recommendation_order": policy_review[
                "stable_order_is_recommendation_order"
            ],
            "opportunity_policy_type": policy_review["policy_type"],
            "opportunity_policy_notes": policy_review["policy_notes"],
            "timing_uncertainty": policy_review["timing_uncertainty"],
            "non_actionable_reason": policy_review["non_actionable_reason"],
            "blocked_session_policy_notes": policy_review["policy_notes"],
            "calibration_review": calibration_review_for_row(
                row,
                axes=axes,
                policy_review=policy_review,
            ),
        }
        for row in rows
    )
    return (
        annotated_rows,
        _calibration_review_summary(annotated_rows),
        policy_review,
    )


def opportunity_policy_review(
    rows: tuple[dict[str, object], ...],
    *,
    axes: dict[str, object],
) -> dict[str, object]:
    scores = tuple(_row_nsom_score(row) for row in rows)
    all_zero = bool(scores) and all(score == 0.0 for score in scores)
    blocked = str(axes.get("session_profile", "")) == "blocked" or any(
        _session_state(row) == "blocked" for row in rows
    )
    invisible = (
        str(axes.get("target_geometry_profile", "")) == "invisible_missing_window"
        or (bool(rows) and all(not _target_visible(row) for row in rows))
    )
    missing_window = str(axes.get("target_geometry_profile", "")) == "missing_window"
    if blocked:
        policy_type = "non_actionable_hard_block"
        current_runtime_policy = "hard_block"
        ranking_actionable = False
        timing_uncertainty = False
        non_actionable_reason = "blocked_session"
        notes = (
            "Current hard-block policy is accepted for now: all-zero NSOM "
            "opportunity scores are non-actionable, and stable order is not "
            "a recommendation order."
        )
    elif invisible:
        policy_type = "non_actionable_invisible_target"
        current_runtime_policy = "invisible_target_non_actionable"
        ranking_actionable = False
        timing_uncertainty = False
        non_actionable_reason = "invisible_target"
        notes = (
            "Invisible targets are non-actionable; all-zero stable order is "
            "not a recommendation order."
        )
    elif missing_window:
        policy_type = "actionable_with_uncertain_timing"
        current_runtime_policy = "missing_window_conservative_fallback"
        ranking_actionable = True
        timing_uncertainty = True
        non_actionable_reason = None
        notes = (
            "Visible targets with missing observing time keep the conservative "
            "0.5 observing-window fallback and are marked actionable with "
            "uncertain timing."
        )
    elif all_zero:
        policy_type = "non_actionable_invisible_target"
        current_runtime_policy = "all_zero_non_actionable"
        ranking_actionable = False
        timing_uncertainty = False
        non_actionable_reason = "all_zero_opportunity"
        notes = (
            "All NSOM opportunity scores are zero; stable order is deterministic "
            "tie order, not a recommendation order."
        )
    else:
        policy_type = "actionable_ranked_recommendation"
        current_runtime_policy = "normal_ranked_recommendation"
        ranking_actionable = True
        timing_uncertainty = False
        non_actionable_reason = None
        notes = "Current NSOM opportunity ranking is actionable for this review group."

    preserved_order = _preserved_practical_target_value_order(rows)
    stable_order_is_recommendation_order = ranking_actionable and not all_zero
    return {
        "applies": policy_type != "actionable_ranked_recommendation",
        "policy_type": policy_type,
        "current_runtime_policy": current_runtime_policy,
        "ranking_actionable": ranking_actionable,
        "stable_order_is_deterministic_tie": all_zero,
        "stable_order_is_recommendation_order": stable_order_is_recommendation_order,
        "policy_notes": notes,
        "timing_uncertainty": timing_uncertainty,
        "non_actionable_reason": non_actionable_reason,
        "non_actionable_preserved_order": preserved_order
        if not ranking_actionable
        else tuple(),
        "preserved_order_basis": "PracticalTargetValue",
        "preserved_order_is_diagnostic_only": True,
        "preserved_order_used_for_runtime_ranking": False,
        "preserved_order_qml_exposure": False,
        "interpretations": {
            "current_policy": {
                "policy_type": policy_type,
                "ranking_actionable": ranking_actionable,
                "stable_order_is_recommendation_order": stable_order_is_recommendation_order,
                "notes": notes,
            },
            "non_actionable_preserved_order": {
                "ranking_basis": "PracticalTargetValue",
                "ranking_actionable": False,
                "internal_order": preserved_order,
                "used_for_runtime_ranking": False,
                "qml_exposure": False,
                "notes": (
                    "Keeps target/equipment ordering visible for diagnostics only; "
                    "it is never a recommendation order."
                ),
            },
            "hard_block": {
                "observation_opportunity": 0.0
                if policy_type == "non_actionable_hard_block"
                else "not_applicable",
                "ranking_actionable": False
                if policy_type == "non_actionable_hard_block"
                else ranking_actionable,
                "notes": (
                    "ObservationOpportunity is capped at 0.0 when SessionViability "
                    "is blocked."
                    if policy_type == "non_actionable_hard_block"
                    else "Hard-block interpretation does not apply to this group."
                ),
            },
        },
    }


def blocked_session_policy_review(
    rows: tuple[dict[str, object], ...],
    *,
    axes: dict[str, object],
) -> dict[str, object]:
    return opportunity_policy_review(rows, axes=axes)


def _preserved_practical_target_value_order(
    rows: tuple[dict[str, object], ...],
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "rank": index,
            "scenario_id": _row_identifier(row),
            "object_id": row.get("object_id", row.get("target_type")),
            "target_type": _target_type(row),
            "practical_target_value": _score_component(row, "practical_target_value"),
        }
        for index, row in enumerate(
            sorted(
                rows,
                key=lambda item: (
                    -_score_component(item, "practical_target_value"),
                    str(_row_identifier(item)),
                ),
            ),
            start=1,
        )
    )


def calibration_review_for_row(
    row: dict[str, object],
    *,
    axes: dict[str, object],
    policy_review: dict[str, object],
) -> dict[str, object]:
    checks = [
        _rank_delta_check(row),
        _blocked_all_zero_check(policy_review),
        _protected_target_degradation_check(row, axes),
        _deep_sky_bright_sky_check(row, axes),
        _observer_dominance_check(row),
        _window_geometry_check(row, axes),
    ]
    status = _max_status(check["status"] for check in checks)
    review_reasons = tuple(
        check["reason"] for check in checks if check["status"] != "expected"
    )
    return {
        "status": status,
        "rank_delta_severity": checks[0]["status"],
        "checks": tuple(checks),
        "suggested_human_review_reason": (
            "; ".join(review_reasons)
            if review_reasons
            else "No calibration review threshold exceeded."
        ),
        "thresholds": CALIBRATION_REVIEW_THRESHOLDS,
    }


def _rank_delta_check(row: dict[str, object]) -> dict[str, object]:
    rank_delta = abs(int(row.get("rank_delta", 0)))
    if rank_delta >= int(CALIBRATION_REVIEW_THRESHOLDS["large_rank_delta_warning"]):
        return _review_check(
            "large_rank_delta",
            "warning",
            f"Rank delta {rank_delta} reaches warning threshold.",
        )
    if rank_delta >= int(CALIBRATION_REVIEW_THRESHOLDS["large_rank_delta_review"]):
        return _review_check(
            "large_rank_delta",
            "review",
            f"Rank delta {rank_delta} reaches review threshold.",
        )
    return _review_check(
        "large_rank_delta",
        "expected",
        f"Rank delta {rank_delta} is within review threshold.",
    )


def _blocked_all_zero_check(policy_review: dict[str, object]) -> dict[str, object]:
    if policy_review["stable_order_is_deterministic_tie"]:
        return _review_check(
            "blocked_or_all_zero_group",
            "warning",
            "All scores are 0.0; stable order is deterministic tie order.",
        )
    return _review_check(
        "blocked_or_all_zero_group",
        "expected",
        "NSOM scores are not an all-zero tie group.",
    )


def _protected_target_degradation_check(
    row: dict[str, object],
    axes: dict[str, object],
) -> dict[str, object]:
    target_type = _target_type(row)
    if target_type not in PROTECTED_TARGET_TYPES or not _is_bright_sky_context(axes):
        return _review_check(
            "protected_target_degradation",
            "expected",
            "Protected planet/Moon bright-sky rule does not apply.",
        )
    effective = _score_component(row, "effective_observability")
    has_sky_limit = _has_factor(row, "sky", "moon_background") or _has_factor(
        row,
        "sky",
        "sky_background",
    )
    if (
        has_sky_limit
        or effective
        < float(CALIBRATION_REVIEW_THRESHOLDS["protected_target_min_effective_observability"])
    ):
        return _review_check(
            "protected_target_degradation",
            "warning",
            "Planet/Moon row degrades under bright sky or exposes sky-background limits.",
        )
    return _review_check(
        "protected_target_degradation",
        "expected",
        "Planet/Moon row remains protected from sky-background degradation.",
    )


def _deep_sky_bright_sky_check(
    row: dict[str, object],
    axes: dict[str, object],
) -> dict[str, object]:
    target_type = _target_type(row)
    if target_type not in BRIGHT_SKY_SENSITIVE_TARGET_TYPES or not _is_bright_sky_context(axes):
        return _review_check(
            "deep_sky_bright_sky_sensitivity",
            "expected",
            "Bright-sky deep-sky sensitivity rule does not apply.",
        )
    effective = _score_component(row, "effective_observability")
    has_sky_limit = _has_factor(row, "sky", "moon_background") or _has_factor(
        row,
        "sky",
        "sky_background",
    )
    if (
        effective
        > float(CALIBRATION_REVIEW_THRESHOLDS["deep_sky_bright_sky_max_effective_observability"])
        or not has_sky_limit
    ):
        return _review_check(
            "deep_sky_bright_sky_sensitivity",
            "warning",
            "Galaxy/nebula row appears over-protected under bright sky.",
        )
    return _review_check(
        "deep_sky_bright_sky_sensitivity",
        "expected",
        "Galaxy/nebula row shows bright-sky sensitivity.",
    )


def _observer_dominance_check(row: dict[str, object]) -> dict[str, object]:
    first = _first_limiting_factor(row)
    q_target = _score_component(row, "q_target")
    if first and first.get("owner") == "observer" and first.get("factor") == "q_target":
        if q_target <= float(CALIBRATION_REVIEW_THRESHOLDS["observer_q_target_warning"]):
            return _review_check(
                "observer_dominance",
                "warning",
                "Q_target is the strongest limiter and below warning threshold.",
            )
        if q_target <= float(CALIBRATION_REVIEW_THRESHOLDS["observer_q_target_review"]):
            return _review_check(
                "observer_dominance",
                "review",
                "Q_target is the strongest limiter and below review threshold.",
            )
    return _review_check(
        "observer_dominance",
        "expected",
        "Observer projection is not below dominance thresholds.",
    )


def _window_geometry_check(row: dict[str, object], axes: dict[str, object]) -> dict[str, object]:
    geometry = str(axes.get("target_geometry_profile", "standard"))
    window_quality = _score_component(row, "observing_window_quality")
    visible = _target_visible(row)
    if geometry == "missing_window":
        expected = float(CALIBRATION_REVIEW_THRESHOLDS["missing_window_expected_quality"])
        if window_quality == expected and visible:
            return _review_check(
                "missing_window_handling",
                "expected",
                "Missing observing time uses the accepted conservative 0.5 fallback.",
            )
        return _review_check(
            "missing_window_handling",
            "warning",
            "Missing-window row does not match the expected 0.5 visible-target fallback.",
        )
    if geometry == "invisible_missing_window" or not visible:
        expected = float(CALIBRATION_REVIEW_THRESHOLDS["invisible_target_expected_quality"])
        if window_quality == expected and _row_nsom_score(row) == 0.0:
            return _review_check(
                "invisible_target_handling",
                "expected",
                "Invisible target with missing time is non-actionable with zero score.",
            )
        return _review_check(
            "invisible_target_handling",
            "warning",
            "Invisible target is not producing the expected non-actionable zero score.",
        )
    return _review_check(
        "missing_or_invisible_window_handling",
        "expected",
        "Missing-window and invisible-target rules do not apply.",
    )


def _calibration_review_summary(rows: tuple[dict[str, object], ...]) -> dict[str, object]:
    status_counts = {status: 0 for status in CALIBRATION_REVIEW_STATUSES}
    for row in rows:
        status_counts[row["calibration_review"]["status"]] += 1
    observer_share = _observer_dominance_share(rows)
    observer_status = _observer_share_status(observer_share)
    group_status = _max_status(
        (
            *(row["calibration_review"]["status"] for row in rows),
            observer_status,
        )
    )
    return {
        "status": group_status,
        "status_counts": status_counts,
        "warning_cases": tuple(
            _row_identifier(row)
            for row in rows
            if row["calibration_review"]["status"] == "warning"
        ),
        "review_cases": tuple(
            _row_identifier(row)
            for row in rows
            if row["calibration_review"]["status"] == "review"
        ),
        "observer_dominance": {
            "share": observer_share,
            "status": observer_status,
            "review_threshold": CALIBRATION_REVIEW_THRESHOLDS[
                "observer_dominance_review_share"
            ],
            "warning_threshold": CALIBRATION_REVIEW_THRESHOLDS[
                "observer_dominance_warning_share"
            ],
            "interpretation": (
                "Frequency of observer limiting factors is a review signal, not proof "
                "of weight dominance."
            ),
        },
    }


def _aggregate_calibration_review(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    status_counts = {status: 0 for status in CALIBRATION_REVIEW_STATUSES}
    non_actionable = []
    uncertain_timing = []
    for scenario in scenarios:
        status_counts[scenario["calibration_review_summary"]["status"]] += 1
        policy = scenario["opportunity_policy_review"]
        if not policy["ranking_actionable"]:
            non_actionable.append(scenario["name"])
        if policy["policy_type"] == "actionable_with_uncertain_timing":
            uncertain_timing.append(scenario["name"])
    return {
        "status_counts": status_counts,
        "non_actionable_groups": tuple(non_actionable),
        "uncertain_timing_groups": tuple(uncertain_timing),
        "blocked_policy_groups": tuple(
            scenario["name"]
            for scenario in scenarios
            if scenario["opportunity_policy_review"]["policy_type"]
            == "non_actionable_hard_block"
        ),
        "invisible_policy_groups": tuple(
            scenario["name"]
            for scenario in scenarios
            if scenario["opportunity_policy_review"]["policy_type"]
            == "non_actionable_invisible_target"
        ),
    }


def _scenario_axes(name: str) -> dict[str, object]:
    return {
        "sky_profile": {
            "bright_sky": "bright_sky",
            "moon_target_case": "moon_target_case",
            "planet_favouring_conditions": "planet_favouring",
            "deep_sky_favouring_conditions": "deep_sky_favouring",
        }.get(name, "dark_sky"),
        "session_profile": {
            "blocked_session": "blocked",
            "poor_session": "poor",
            "good_session": "good",
        }.get(name, "good"),
        "equipment_profile": {
            "small_telescope": "small_telescope",
            "large_telescope": "large_telescope",
        }.get(name, "medium_telescope"),
        "target_geometry_profile": "standard",
        "confidence_profile": "high",
    }


def _calibration_scenarios() -> tuple[PlannerNsomCalibrationScenario, ...]:
    return (
        PlannerNsomCalibrationScenario(
            name="bright_sky",
            intended_nsom_expectation=(
                "Planets and the Moon keep neutral sky-background factors; galaxies and "
                "diffuse nebulae show sky-owned degradation."
            ),
            targets=_mixed_targets(include_moon=True),
            weather=_weather(85),
            scores=_scores(planetary=86, deep_sky=88),
            sky_quality=_sky_quality(9, radiance=120),
            telescope=_telescope(),
            moon=_moon(95),
        ),
        PlannerNsomCalibrationScenario(
            name="blocked_session",
            intended_nsom_expectation=(
                "Blocked sessions hard-cap current NSOM opportunity scores at zero; "
                "preserved PracticalTargetValue ranking is reported only as a "
                "non-actionable policy alternative."
            ),
            targets=_mixed_targets(include_moon=True),
            weather=_weather(10),
            scores=_scores(planetary=86, deep_sky=88),
            sky_quality=_sky_quality(3, radiance=2),
            telescope=_telescope(),
            moon=_moon(10),
        ),
        PlannerNsomCalibrationScenario(
            name="poor_session",
            intended_nsom_expectation=(
                "Poor session viability lowers opportunity value without changing "
                "observable or practical target values."
            ),
            targets=_mixed_targets(),
            weather=_weather(20),
            scores=_scores(planetary=86, deep_sky=88),
            sky_quality=_sky_quality(3, radiance=2),
            telescope=_telescope(),
            moon=_moon(10),
        ),
        PlannerNsomCalibrationScenario(
            name="good_session",
            intended_nsom_expectation=(
                "Good session conditions keep session viability high while timing and "
                "practical constraints remain visible as opportunity components."
            ),
            targets=_mixed_targets(include_timing_variants=True),
            weather=_weather(95),
            scores=_scores(planetary=86, deep_sky=88),
            sky_quality=_sky_quality(3, radiance=2),
            telescope=_telescope(),
            moon=_moon(10),
        ),
        PlannerNsomCalibrationScenario(
            name="small_telescope",
            intended_nsom_expectation=(
                "Small manual equipment reduces observer capability and practical "
                "target value while leaving observable target value unchanged."
            ),
            targets=_deep_sky_targets(),
            weather=_weather(85),
            scores=_scores(planetary=82, deep_sky=90),
            sky_quality=_sky_quality(3, radiance=2),
            telescope=_telescope(
                name="Small Manual",
                aperture_mm=60,
                focal_length_mm=400,
                mount="manual",
            ),
            moon=_moon(10),
        ),
        PlannerNsomCalibrationScenario(
            name="large_telescope",
            intended_nsom_expectation=(
                "Large GoTo equipment improves practical target value while preserving "
                "the same observable target value for the same sky."
            ),
            targets=_deep_sky_targets(),
            weather=_weather(85),
            scores=_scores(planetary=82, deep_sky=90),
            sky_quality=_sky_quality(3, radiance=2),
            telescope=_telescope(
                name="Large GoTo",
                aperture_mm=220,
                focal_length_mm=1800,
                mount="GoTo EQ",
            ),
            moon=_moon(10),
        ),
        PlannerNsomCalibrationScenario(
            name="planet_favouring_conditions",
            intended_nsom_expectation=(
                "Bright sky and strong Moon favour compact planetary targets over "
                "sky-background-sensitive galaxies and diffuse nebulae."
            ),
            targets=_mixed_targets(include_moon=True),
            weather=_weather(88),
            scores=_scores(planetary=95, deep_sky=70),
            sky_quality=_sky_quality(9, radiance=140),
            telescope=_telescope(),
            moon=_moon(98),
        ),
        PlannerNsomCalibrationScenario(
            name="deep_sky_favouring_conditions",
            intended_nsom_expectation=(
                "Dark sky, low Moon and strong deep-sky conditions preserve high "
                "effective observability for galaxies, nebulae and clusters."
            ),
            targets=_mixed_targets(include_timing_variants=True),
            weather=_weather(92),
            scores=_scores(planetary=76, deep_sky=96),
            sky_quality=_sky_quality(2, radiance=1),
            telescope=_telescope(
                name="Large GoTo",
                aperture_mm=220,
                focal_length_mm=1800,
                mount="GoTo EQ",
            ),
            moon=_moon(5),
        ),
        PlannerNsomCalibrationScenario(
            name="moon_target_case",
            intended_nsom_expectation=(
                "Moon target explanations keep Moon and light-pollution background "
                "neutral even under bright Moon conditions."
            ),
            targets=(
                _target("moon", "Luna", 82, magnitude="-12.0", best_time="22:00"),
                _target("planet", "Pianeta", 80, magnitude="-1.0", best_time="21:00"),
                _target("galaxy", "Galaxy", 84, magnitude="8.2", best_time="21:30"),
            ),
            weather=_weather(88),
            scores=_scores(planetary=90, deep_sky=80),
            sky_quality=_sky_quality(9, radiance=120),
            telescope=_telescope(),
            moon=_moon(95),
        ),
    )


def _component_ranges(rows: tuple[dict[str, object], ...]) -> dict[str, object]:
    ranges: dict[str, object] = {}
    for component in CALIBRATION_SCORE_COMPONENTS:
        values = [float(row["score_components"][component]) for row in rows]
        minimum = min(values) if values else None
        maximum = max(values) if values else None
        ranges[component] = {
            "min": minimum,
            "max": maximum,
            "range": None if minimum is None or maximum is None else maximum - minimum,
        }
    return ranges


def _aggregate_component_ranges(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    rows = tuple(
        row
        for scenario in scenarios
        for row in scenario["ranked_nsom_opportunities"]
    )
    return _component_ranges(rows)


def _dominant_limiting_factor(rows: tuple[dict[str, object], ...]) -> object:
    factors = tuple(factor for row in rows for factor in row["limiting_factors"])
    if not factors:
        return None
    factor = min(factors, key=lambda item: float(item["value"]))
    return {
        "owner": factor["owner"],
        "component": factor["component"],
        "factor": factor["factor"],
        "value": factor["value"],
    }


def _factor_coverage(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    limiting = set()
    positive = set()
    owners = set()
    for scenario in scenarios:
        for row in scenario["ranked_nsom_opportunities"]:
            for factor in row["limiting_factors"]:
                owners.add(factor["owner"])
                limiting.add(f"{factor['owner']}:{factor['factor']}")
            for factor in row["positive_factors"]:
                owners.add(factor["owner"])
                positive.add(f"{factor['owner']}:{factor['factor']}")
    return {
        "owners": tuple(sorted(owners)),
        "limiting_factors": tuple(sorted(limiting)),
        "positive_factors": tuple(sorted(positive)),
    }


def _dominant_limiting_factor_summary(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    factor_counts: dict[str, int] = {}
    owner_counts: dict[str, int] = {}
    for scenario in scenarios:
        dominant = scenario["dominant_limiting_factor"]
        if dominant is None:
            continue
        factor_key = f"{dominant['owner']}:{dominant['factor']}"
        factor_counts[factor_key] = factor_counts.get(factor_key, 0) + 1
        owner = str(dominant["owner"])
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
    return {
        "by_factor": dict(sorted(factor_counts.items())),
        "by_owner": dict(sorted(owner_counts.items())),
    }


def _review_check(name: str, status: str, reason: str) -> dict[str, object]:
    return {"name": name, "status": status, "reason": reason}


def _max_status(statuses: Iterable[str]) -> str:
    severity = {"expected": 0, "review": 1, "warning": 2}
    return max(statuses, key=lambda status: severity[str(status)])


def _observer_dominance_share(rows: tuple[dict[str, object], ...]) -> float:
    if not rows:
        return 0.0
    observer_limited = sum(
        1
        for row in rows
        if (factor := _first_limiting_factor(row))
        and factor.get("owner") == "observer"
        and factor.get("factor") == "q_target"
    )
    return observer_limited / len(rows)


def _observer_share_status(share: float) -> str:
    if share >= float(CALIBRATION_REVIEW_THRESHOLDS["observer_dominance_warning_share"]):
        return "warning"
    if share >= float(CALIBRATION_REVIEW_THRESHOLDS["observer_dominance_review_share"]):
        return "review"
    return "expected"


def _is_bright_sky_context(axes: dict[str, object]) -> bool:
    return str(axes.get("sky_profile", "")) in BRIGHT_SKY_PROFILES


def _row_identifier(row: dict[str, object]) -> object:
    return row.get("scenario_id", row.get("object_id", row.get("target_type", "unknown")))


def _row_nsom_score(row: dict[str, object]) -> float:
    if "nsom_score" in row:
        return float(row["nsom_score"])
    nsom = row.get("nsom", {})
    return float(nsom.get("score", 0.0)) if isinstance(nsom, dict) else 0.0


def _target_type(row: dict[str, object]) -> str:
    value = row.get("target_type") or row.get("object_id") or row.get("object_type", "")
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


def _target_visible(row: dict[str, object]) -> bool:
    target = row.get("target")
    if isinstance(target, dict) and "visible" in target:
        return bool(target["visible"])
    return True


def _score_component(row: dict[str, object], component: str) -> float:
    components = row.get("score_components")
    if isinstance(components, dict) and component in components:
        return _float_value(components[component])
    nsom = row.get("nsom")
    if isinstance(nsom, dict):
        explanation = nsom.get("explanation")
        if isinstance(explanation, dict):
            score_components = explanation.get("score_components")
            if isinstance(score_components, dict) and component in score_components:
                return _float_value(score_components[component])
        if component in nsom:
            return _float_value(nsom[component])
    return 0.0


def _float_value(value: object) -> float:
    if isinstance(value, dict) and "value" in value:
        return float(value["value"])
    if hasattr(value, "value"):
        return float(value.value)
    return float(value)


def _has_factor(
    row: dict[str, object],
    owner: str,
    factor: str,
    *,
    section: str = "limiting_factors",
) -> bool:
    factors = row.get(section)
    if factors is None and isinstance(row.get("nsom"), dict):
        factors = row["nsom"].get(
            "main_limiting_factors" if section == "limiting_factors" else "main_positive_factors"
        )
    if factors is None:
        return False
    return any(item.get("owner") == owner and item.get("factor") == factor for item in factors)


def _first_limiting_factor(row: dict[str, object]) -> dict[str, object] | None:
    factors = row.get("limiting_factors")
    if factors is None and isinstance(row.get("nsom"), dict):
        factors = row["nsom"].get("main_limiting_factors")
    if not factors:
        return None
    return factors[0]


def _session_state(row: dict[str, object]) -> str | None:
    component_breakdown = row.get("component_breakdown")
    if isinstance(component_breakdown, dict):
        state = _state_from_session(component_breakdown.get("session_viability"))
        if state is not None:
            return state
    nsom = row.get("nsom")
    if isinstance(nsom, dict):
        return _state_from_session(nsom.get("session_viability"))
    return None


def _state_from_session(session: object) -> str | None:
    if isinstance(session, dict):
        state = session.get("state")
        return str(state) if state is not None else None
    state = getattr(session, "state", None)
    return str(state) if state is not None else None


def _mixed_targets(
    *,
    include_moon: bool = False,
    include_timing_variants: bool = False,
) -> tuple[CelestialObject, ...]:
    targets = [
        _target("planet", "Pianeta", 84, magnitude="-1.7", best_time="21:00", difficulty="Facile"),
        _target("galaxy", "Galaxy", 88, magnitude="8.2", best_time="21:30", difficulty="Media"),
        _target("diffuse-nebula", "Nebula", 86, magnitude="7.0", best_time="22:00", difficulty="Media"),
        _target("open-cluster", "Open Cluster", 78, magnitude="5.2", best_time="23:00", difficulty="Facile"),
    ]
    if include_moon:
        targets.append(
            _target("moon", "Luna", 78, magnitude="-12.0", best_time="22:30", difficulty="Facile")
        )
    if include_timing_variants:
        targets.extend(
            (
                _target("late-galaxy", "Galaxy", 82, magnitude="9.0", best_time="04:30", difficulty="Difficile"),
                _target(
                    "unknown-window-cluster",
                    "Open Cluster",
                    74,
                    magnitude="6.0",
                    best_time="not available",
                    difficulty="Facile",
                    observing_window="",
                ),
            )
        )
    return tuple(targets)


def _deep_sky_targets() -> tuple[CelestialObject, ...]:
    return (
        _target("galaxy", "Galaxy", 88, magnitude="8.2", best_time="21:30", difficulty="Media"),
        _target("diffuse-nebula", "Nebula", 86, magnitude="7.0", best_time="22:00", difficulty="Media"),
        _target("open-cluster", "Open Cluster", 78, magnitude="5.2", best_time="23:00", difficulty="Facile"),
    )


def _target(
    object_id: str,
    object_type: str,
    score: int,
    *,
    magnitude: str = "8.0",
    best_time: str = "21:00",
    difficulty: str = "Media",
    observing_window: str | None = None,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.title(),
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time=best_time,
        observing_window=observing_window if observing_window is not None else f"{best_time} - 02:00",
        notes="NSOM calibration fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type="telescope",
    )


def _weather(score: int) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=10,
        precipitation_probability=0,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _scores(planetary: int, deep_sky: int) -> AdvancedObservingScores:
    return AdvancedObservingScores(
        planetary_score=planetary,
        deep_sky_score=deep_sky,
        planetary_label="Fixture",
        deep_sky_label="Fixture",
        explanation="Fixture",
    )


def _sky_quality(bortle: int, *, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="Fixture",
        description="Fixture",
        viirs_radiance=radiance,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="18:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
        phase_angle=0.0,
    )


def _telescope(
    *,
    name: str = "Test Scope",
    aperture_mm: int = 127,
    focal_length_mm: int = 1500,
    mount: str = "",
) -> Telescope:
    return Telescope(
        id=name.lower().replace(" ", "-"),
        name=name,
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Mak",
        mount=mount,
    )
