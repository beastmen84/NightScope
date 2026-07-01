from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from statistics import mean

from astro_viewer.app.models.nsom import NSOM_TARGET_CLASS_PROFILES, NsomTargetClass, nsom_to_json_compatible
from astro_viewer.tools.nsom_planner_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    UNAVAILABLE,
    generate_report_data,
)

TRACE_REPORT_PATH = Path("docs/NSOM_MATHEMATICAL_TRACE_REPORT.md")

PIPELINE_STAGE_NAMES = (
    "IntrinsicTargetQuality",
    "ObservationEnvironment",
    "EffectiveObservability",
    "ObservableTargetValue",
    "ObserverCapability",
    "PracticalTargetValue",
    "ObservationWindow",
    "Chronology",
    "SessionViability",
    "ObservationOpportunity",
    "FinalPlannerRanking",
)

AVERAGE_COMPONENTS = (
    "IntrinsicTargetQuality",
    "EffectiveObservability",
    "ObservableTargetValue",
    "ObserverCapability",
    "PracticalTargetValue",
    "SessionViability",
    "RecommendationConfidence",
)


def generate_trace_report_data() -> dict[str, object]:
    comparison = generate_report_data()
    traced_groups = []
    traced_rows = []
    for group in comparison["scenario_groups"]:
        scenarios = tuple(_trace_scenario(group, row) for row in group["scenarios"])
        traced_groups.append(
            {
                "group_id": group["group_id"],
                "label": group["label"],
                "axes": group["axes"],
                "intended_nsom_expectation": group["intended_nsom_expectation"],
                "scenarios": scenarios,
            }
        )
        traced_rows.extend(scenarios)

    report = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "nsom_planner_scoring_enabled": comparison["metadata"]["nsom_planner_scoring_enabled"],
            "scenario_group_count": len(traced_groups),
            "scenario_count": len(traced_rows),
            "source_matrix": str(COMPARISON_REPORT_PATH).replace("\\", "/"),
            "trace_report_path": str(TRACE_REPORT_PATH).replace("\\", "/"),
            "pipeline_stages": PIPELINE_STAGE_NAMES,
            "confidence_role": "metadata_only_outside_mathematical_pipeline",
        },
        "scenario_groups": tuple(traced_groups),
        "component_diagnostics": _component_diagnostics(traced_rows),
        "summary": _summary(traced_rows),
    }
    return nsom_to_json_compatible(report)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report = generate_trace_report_data() if data is None else data
    metadata = report["metadata"]
    rows = _rows(report)
    diagnostics = report["component_diagnostics"]
    summary = report["summary"]

    lines = [
        "# NSOM Mathematical Trace Report",
        "",
        "## Executive Summary",
        "",
        (
            f"This developer-facing report traces every stage of the experimental NSOM "
            f"Planner pipeline for {metadata['scenario_count']} deterministic scenarios "
            f"from `{metadata['source_matrix']}`. It explains why NSOM recommended each "
            "target; it is not a raw-score parity report."
        ),
        (
            "The trace keeps `RecommendationConfidence` outside the mathematical pipeline. "
            "Confidence appears as diagnostic metadata with zero score effect and is never "
            "used as a multiplier."
        ),
        (
            "The dominant mathematical review item is observer capability: it is a common "
            "limiter in the current fixtures because several profiles intentionally have "
            "sub-perfect practical capability. This is a frequency observation, not proof "
            "of an overweighted component. Session viability correctly caps blocked or "
            "poor sessions without mutating target physics."
        ),
        "",
        "## Methodology",
        "",
        "- Reuses the existing deterministic NSOM comparison scenario matrix; no random scenarios are generated.",
        "- Builds trace rows from already exported NSOM opportunities and explanations.",
        "- Shows unavailable legacy concepts as unavailable instead of reconstructing or inventing values.",
        "- Reports lower-level sub-formulas when their inputs are present; otherwise marks the value adapter-derived or unavailable.",
        "- Marks all-zero opportunity groups as tied/non-actionable so stable order is not treated as recommendation order.",
        "- Does not change Planner scoring, enable the NSOM Planner flag, write runtime files, log automatically, expose QML or perform network work.",
        "- The checked-in Markdown file is generated only by the explicit developer tool command.",
        "",
        "## NSOM Mathematical Pipeline",
        "",
        "The traced pipeline is:",
        "",
        "1. IntrinsicTargetQuality",
        "2. ObservationEnvironment",
        "3. EffectiveObservability",
        "4. ObservableTargetValue",
        "5. ObserverCapability",
        "6. PracticalTargetValue",
        "7. Observation Window",
        "8. Chronology",
        "9. SessionViability",
        "10. ObservationOpportunity",
        "11. Final Planner ranking",
        "",
        "`RecommendationConfidence` is reported beside the pipeline as trust metadata only.",
        "",
        "## One Complete Trace For Every Analysed Scenario",
        "",
    ]

    for row in rows:
        lines.extend(_scenario_markdown(row))

    lines.extend(
        [
            "## Legacy Comparison",
            "",
            "Legacy values below are limited to fields exposed by `PlannerScoringService.score_breakdown()`.",
            "",
            "| Scenario | Target | Legacy Rank | Legacy Score | Available Legacy Components | Unavailable Legacy Components |",
            "| --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in rows:
        legacy = row["legacy"]
        available = _legacy_component_labels(legacy["components"], unavailable=False)
        unavailable = _legacy_component_labels(legacy["components"], unavailable=True)
        lines.append(
            "| "
            + " | ".join(
                (
                    str(row["scenario_id"]),
                    str(row["target"]["name"]),
                    str(legacy["rank"]),
                    _fmt(legacy["score"]),
                    ", ".join(available),
                    ", ".join(unavailable),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Why The Two Systems Differ",
            "",
        ]
    )
    for row in rows:
        lines.append(f"### {row['scenario_id']}")
        for item in row["why_nsom_differs"]:
            lines.append(f"- {item}")
        lines.append("")

    lines.extend(
        [
            "## Behaviour That Matches The NSOM Model",
            "",
        ]
    )
    for item in summary["model_aligned_behaviours"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Behaviour That Deserves Review",
            "",
        ]
    )
    for item in summary["behaviour_requiring_review"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Potential Calibration Concerns",
            "",
        ]
    )
    for item in summary["potential_calibration_concerns"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Component Diagnostics",
            "",
            f"- Most common limiting factor: {_count_label(diagnostics['most_common_limiting_factor'])}.",
            f"- Most common positive factor: {_count_label(diagnostics['most_common_positive_factor'])}.",
            "",
            "| Component | Average | Min | Max | Range |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for name, stats in diagnostics["component_statistics"].items():
        lines.append(
            f"| {name} | {_fmt(stats['average'])} | {_fmt(stats['min'])} | "
            f"{_fmt(stats['max'])} | {_fmt(stats['range'])} |"
        )

    lines.extend(["", "Components that dominate too many scenarios:"])
    lines.append(
        "These are frequency counts across fixtures. They are not weight, sensitivity or elasticity measurements by themselves."
    )
    for item in diagnostics["components_that_dominate_too_many_scenarios"]:
        lines.append(f"- {_factor_count_sentence(item)}")

    lines.extend(["", "Components that almost never contribute:"])
    if diagnostics["components_that_almost_never_contribute"]:
        for item in diagnostics["components_that_almost_never_contribute"]:
            lines.append(f"- {_factor_count_sentence(item)}")
    else:
        lines.append("- none")

    lines.extend(["", "Fixture coverage limitations:"])
    for item in diagnostics["fixture_coverage_limitations"]:
        lines.append(f"- {item}")

    lines.extend(["", "Opportunities for future calibration:"])
    for item in diagnostics["opportunities_for_future_calibration"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Final Recommendations",
            "",
            "1. Keep the trace report developer-only until the Planner NSOM path is ready for default-on evaluation.",
            "2. Treat frequent limiter counts as triage signals; confirm with sensitivity fixtures before changing weights.",
            "3. Review all-zero tie handling before turning blocked-session NSOM Planner output into user-visible order.",
            "4. Continue treating confidence as metadata only; do not convert it into a score multiplier.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = TRACE_REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _trace_scenario(group: dict[str, object], row: dict[str, object]) -> dict[str, object]:
    nsom = row["nsom"]
    explanation = nsom["explanation"]
    score_components = explanation["score_components"]
    observable = nsom["observable_target_value"]
    effective = nsom["effective_observability"]
    environment = effective.get("environment") or {}
    observer = nsom["observer_capability"]
    session = nsom["session_viability"]
    confidence = nsom["recommendation_confidence"]
    intrinsic = observable.get("intrinsic_target") or {}
    component_values = _component_values(score_components, observable, confidence)
    pipeline = (
        _intrinsic_stage(row, intrinsic, observable),
        _environment_stage(row, effective, environment),
        _effective_stage(effective),
        _observable_stage(observable, effective),
        _observer_stage(row, observer, score_components),
        _practical_stage(score_components),
        _window_stage(row, score_components),
        _chronology_stage(row, score_components),
        _session_stage(session),
        _opportunity_stage(row, score_components),
        _ranking_stage(group, row),
    )
    return {
        "scenario_id": row["scenario_id"],
        "group_id": row["group_id"],
        "group_label": row["group_label"],
        "target_type": row["target_type"],
        "target": row["target"],
        "axes": row["axes"],
        "intended_nsom_expectation": group["intended_nsom_expectation"],
        "pipeline": pipeline,
        "component_values": component_values,
        "confidence_metadata": confidence,
        "legacy": row["legacy"],
        "main_positive_factors": nsom["main_positive_factors"],
        "main_limiting_factors": nsom["main_limiting_factors"],
        "why_nsom_differs": _why_nsom_differs(row, component_values, pipeline[-1]),
    }


def _intrinsic_stage(
    row: dict[str, object],
    intrinsic: dict[str, object],
    observable: dict[str, object],
) -> dict[str, object]:
    value = _number(observable["intrinsic_target_quality"])
    inputs = {
        "object_id": intrinsic.get("object_id") or row["target"]["object_id"],
        "name": intrinsic.get("name") or row["target"]["name"],
        "target_class": intrinsic.get("target_class") or observable.get("target_class"),
        "runtime_score": value,
        "magnitude": intrinsic.get("magnitude") or row["target"].get("magnitude"),
        "altitude": intrinsic.get("altitude") or row["target"].get("max_altitude"),
        "astronomical_visibility": intrinsic.get("astronomical_visibility"),
        "source_fields": intrinsic.get("source_fields", []),
    }
    positives = []
    limits = []
    if value >= 80.0:
        positives.append(_factor("universe", "IntrinsicTargetQuality", "runtime_score", value / 100.0, "Prepared target quality is high."))
    else:
        limits.append(_factor("universe", "IntrinsicTargetQuality", "runtime_score", value / 100.0, "Prepared target quality limits the starting value."))
    return _stage(
        "IntrinsicTargetQuality",
        inputs=inputs,
        formula="IntrinsicTargetQuality = clamp(runtime target quality score, 0, 100)",
        intermediate_calculation=f"clamp({_fmt(value)}, 0, 100) = {_fmt(value)}",
        outputs={"value": value},
        positives=positives,
        limits=limits,
    )


def _environment_stage(
    row: dict[str, object],
    effective: dict[str, object],
    environment: dict[str, object],
) -> dict[str, object]:
    components = _environment_components(effective)
    positives, limits = _unit_component_factors(
        components,
        owner="sky",
        component="ObservationEnvironment",
        reason_suffix="environment multiplier",
    )
    inputs = {
        "moon_background": components["moon_background"],
        "sky_background": components["sky_background"],
        "atmospheric_transparency": components["atmospheric_transparency"],
        "horizon_geometry": components["horizon_context"],
        "geometric_visibility": components["geometric_visibility"],
        "sky_quality_source": environment.get("sky_quality_source", ""),
        "weather_source": environment.get("weather_source", ""),
        "atmosphere_source": environment.get("atmosphere_source", ""),
        "other_active_environmental_components": environment.get("notes", []),
    }
    return _stage(
        "ObservationEnvironment",
        inputs=inputs,
        formula="ObservationEnvironment = prepared sky-owned component multipliers; no score is produced at this stage",
        intermediate_calculation=_component_formula("prepared multipliers", components),
        outputs=components,
        positives=positives,
        limits=limits,
        sub_formulas=_environment_sub_formulas(row, effective, environment),
    )


def _effective_stage(effective: dict[str, object]) -> dict[str, object]:
    components = _environment_components(effective)
    positives, limits = _unit_component_factors(
        components,
        owner="sky",
        component="EffectiveObservability",
        reason_suffix="observability multiplier",
    )
    return _stage(
        "EffectiveObservability",
        inputs=components,
        formula=(
            "EffectiveObservability = geometric_visibility * moon_background * "
            "sky_background * atmospheric_transparency * horizon_context"
        ),
        intermediate_calculation=_multiplication_calculation(components),
        outputs={"value": _number(effective["value"])},
        positives=positives,
        limits=limits,
    )


def _observable_stage(
    observable: dict[str, object],
    effective: dict[str, object],
) -> dict[str, object]:
    intrinsic = _number(observable["intrinsic_target_quality"])
    observability = _number(effective["value"])
    value = _number(observable["value"])
    limit_value = observability
    positives = []
    limits = []
    if limit_value >= 0.995:
        positives.append(_factor("sky", "ObservableTargetValue", "effective_observability", limit_value, "Sky allows the intrinsic target value to pass through unchanged."))
    else:
        limits.append(_factor("sky", "ObservableTargetValue", "effective_observability", limit_value, "Sky reduces the observable target value."))
    return _stage(
        "ObservableTargetValue",
        inputs={
            "intrinsic_target_quality": intrinsic,
            "effective_observability": observability,
            "target_class": observable.get("target_class"),
        },
        formula="ObservableTargetValue = IntrinsicTargetQuality * EffectiveObservability",
        intermediate_calculation=f"{_fmt(intrinsic)} * {_fmt(observability)} = {_fmt(value)}",
        outputs={"value": value},
        positives=positives,
        limits=limits,
    )


def _observer_stage(
    row: dict[str, object],
    observer: dict[str, object],
    score_components: dict[str, object],
) -> dict[str, object]:
    dimensions = _observer_dimensions(observer)
    summary = _number(score_components["observer_capability_summary"])
    positives, limits = _unit_component_factors(
        dimensions,
        owner="observer",
        component="ObserverCapability",
        reason_suffix="observer capability dimension",
        positive_threshold=0.75,
        limiting_threshold=0.65,
    )
    notes = [str(note) for note in observer.get("notes", [])]
    inputs = {
        "aperture": _note_value(notes, "aperture_mm"),
        "focal_length": _note_value(notes, "focal_length_mm"),
        "optical_capability": {
            "light_grasp": observer.get("light_grasp"),
            "resolution": observer.get("resolution"),
            "field_of_view": observer.get("field_of_view"),
            "magnification_range": observer.get("magnification_range"),
        },
        "tracking": observer.get("tracking_or_goto"),
        "filters": observer.get("filters", []),
        "setup_contribution": {
            "setup_type": _note_value(notes, "setup_type"),
            "telescope": _note_value(notes, "telescope"),
            "practical_comfort": observer.get("practical_comfort"),
        },
        "other_active_observer_components": {
            "automation_or_eaa": observer.get("automation_or_eaa"),
            "experience_level": observer.get("experience_level"),
            "observing_style": observer.get("observing_style"),
            "notes": notes,
        },
    }
    return _stage(
        "ObserverCapability",
        inputs=inputs,
        formula=(
            "ObserverCapability summary = mean(light_grasp, resolution, field_of_view, "
            "magnification_range, tracking_or_goto, experience_level, practical_comfort)"
        ),
        intermediate_calculation=f"mean({_format_values(dimensions.values())}) = {_fmt(summary)}",
        outputs={"summary_for_planning": summary, "dimensions": dimensions},
        positives=positives,
        limits=limits,
        sub_formulas=_observer_sub_formulas(row, observer, dimensions, summary),
    )


def _practical_stage(score_components: dict[str, object]) -> dict[str, object]:
    observable = _number(score_components["observable_target_value"])
    capability = _number(score_components["observer_capability_summary"])
    practical = _number(score_components["practical_target_value"])
    positives = []
    limits = []
    if capability >= 0.995:
        positives.append(_factor("observer", "PracticalTargetValue", "observer_capability_summary", capability, "Observer capability preserves observable target value."))
    else:
        limits.append(_factor("observer", "PracticalTargetValue", "observer_capability_summary", capability, "Observer capability reduces practical target value."))
    return _stage(
        "PracticalTargetValue",
        inputs={
            "observable_target_value": observable,
            "observer_capability_summary": capability,
        },
        formula="PracticalTargetValue = ObservableTargetValue * ObserverCapability summary",
        intermediate_calculation=f"{_fmt(observable)} * {_fmt(capability)} = {_fmt(practical)}",
        outputs={"value": practical},
        positives=positives,
        limits=limits,
    )


def _window_stage(row: dict[str, object], score_components: dict[str, object]) -> dict[str, object]:
    value = _number(score_components["observing_window_quality"])
    positives, limits = _single_multiplier_factors(
        value,
        owner="opportunity",
        component="ObservationWindow",
        factor="observing_window_quality",
        positive_reason="The target observing window is strong.",
        limiting_reason="The target observing window limits timing quality.",
    )
    return _stage(
        "ObservationWindow",
        inputs={
            "observing_window": row["target"].get("observing_window"),
            "best_time": row["target"].get("best_time"),
            "observing_window_quality": value,
        },
        formula="ObservationWindow = Planner-prepared observing_window_quality multiplier",
        intermediate_calculation=f"observing_window_quality = {_fmt(value)}",
        outputs={"value": value},
        positives=positives,
        limits=limits,
    )


def _chronology_stage(row: dict[str, object], score_components: dict[str, object]) -> dict[str, object]:
    value = _number(score_components["chronology_fit"])
    positives, limits = _single_multiplier_factors(
        value,
        owner="opportunity",
        component="Chronology",
        factor="chronology_fit",
        positive_reason="Planner chronology fit is strong.",
        limiting_reason="Planner chronology fit limits this opportunity.",
    )
    return _stage(
        "Chronology",
        inputs={
            "best_time": row["target"].get("best_time"),
            "chronology_fit": value,
        },
        formula="Chronology = Planner-prepared chronology_fit multiplier",
        intermediate_calculation=f"chronology_fit = {_fmt(value)}",
        outputs={"value": value},
        positives=positives,
        limits=limits,
    )


def _session_stage(session: dict[str, object]) -> dict[str, object]:
    weather = _number(session["weather_suitability"])
    blocking = _number(session["blocking_factor"])
    value = _number(session["value"])
    positives, limits = _single_multiplier_factors(
        value,
        owner="session",
        component="SessionViability",
        factor="session_viability",
        positive_reason="Session viability supports observation.",
        limiting_reason="Session viability reduces the final opportunity.",
    )
    return _stage(
        "SessionViability",
        inputs={
            "weather_suitability": weather,
            "blocking_factor": blocking,
            "state": session.get("state"),
            "reason": session.get("reason"),
            "notes": session.get("notes", []),
        },
        formula="SessionViability = weather_suitability * blocking_factor",
        intermediate_calculation=f"{_fmt(weather)} * {_fmt(blocking)} = {_fmt(value)}",
        outputs={"value": value},
        positives=positives,
        limits=limits,
    )


def _opportunity_stage(row: dict[str, object], score_components: dict[str, object]) -> dict[str, object]:
    practical = _number(score_components["practical_target_value"])
    window = _number(score_components["observing_window_quality"])
    chronology = _number(score_components["chronology_fit"])
    session = _number(score_components["session_viability"])
    constraints = _number(score_components["practical_constraints"])
    score = _number(row["nsom"]["score"])
    return _stage(
        "ObservationOpportunity",
        inputs={
            "practical_target_value": practical,
            "observing_window_quality": window,
            "chronology_fit": chronology,
            "session_viability": session,
            "practical_constraints": constraints,
        },
        formula=(
            "ObservationOpportunity = PracticalTargetValue * observing_window_quality "
            "* chronology_fit * SessionViability * practical_constraints"
        ),
        intermediate_calculation=(
            f"{_fmt(practical)} * {_fmt(window)} * {_fmt(chronology)} * "
            f"{_fmt(session)} * {_fmt(constraints)} = {_fmt(score)}"
        ),
        outputs={"value": score},
        positives=_without_confidence(row["nsom"]["main_positive_factors"]),
        limits=_without_confidence(row["nsom"]["main_limiting_factors"]),
    )


def _ranking_stage(group: dict[str, object], row: dict[str, object]) -> dict[str, object]:
    score = _number(row["nsom"]["score"])
    rank = int(row["nsom"]["rank"])
    group_size = len(group["scenarios"])
    group_scores = [_number(candidate["nsom"]["score"]) for candidate in group["scenarios"]]
    all_zero_group = bool(group_scores) and all(abs(value) <= 1e-12 for value in group_scores)
    positives = []
    limits = []
    if all_zero_group:
        limits.append(
            _factor(
                "opportunity",
                "FinalPlannerRanking",
                "all_zero_tie",
                0.0,
                "All candidate opportunity scores are zero; stable order is non-actionable.",
            )
        )
    elif rank == 1:
        positives.append(_factor("opportunity", "FinalPlannerRanking", "rank", 1.0, "This opportunity ranks first in its scenario group."))
    else:
        limits.append(_factor("opportunity", "FinalPlannerRanking", "rank", rank / group_size, "Other opportunities rank higher in this scenario group."))
    status = "tied_non_actionable" if all_zero_group else "ranked_actionable"
    calculation = (
        f"all {group_size} candidate scores are 0.0000; stable position {rank} is non-actionable"
        if all_zero_group
        else f"{_fmt(score)} sorts to rank {rank} of {group_size}"
    )
    return _stage(
        "FinalPlannerRanking",
        inputs={
            "group_id": group["group_id"],
            "candidate_count": group_size,
            "opportunity_score": score,
            "all_candidate_scores": group_scores,
        },
        formula=(
            "Final Planner ranking = sort ObservationOpportunity scores descending; "
            "if all scores are 0.0, order is a deterministic tie and not actionable"
        ),
        intermediate_calculation=calculation,
        outputs={
            "rank": rank,
            "score": score,
            "ranking_status": status,
            "meaningful_recommendation_order": not all_zero_group,
            "stable_order_only": all_zero_group,
        },
        positives=positives,
        limits=limits,
    )


def _component_values(
    score_components: dict[str, object],
    observable: dict[str, object],
    confidence: dict[str, object],
) -> dict[str, float | None]:
    return {
        "IntrinsicTargetQuality": _number(observable["intrinsic_target_quality"]),
        "EffectiveObservability": _number(score_components["effective_observability"]),
        "ObservableTargetValue": _number(score_components["observable_target_value"]),
        "ObserverCapability": _number(score_components["observer_capability_summary"]),
        "PracticalTargetValue": _number(score_components["practical_target_value"]),
        "SessionViability": _number(score_components["session_viability"]),
        "RecommendationConfidence": _maybe_number(confidence.get("value")),
    }


def _component_diagnostics(rows: list[dict[str, object]]) -> dict[str, object]:
    limiting_counts = _factor_counter(row["main_limiting_factors"] for row in rows)
    positive_counts = _factor_counter(row["main_positive_factors"] for row in rows)
    component_stats = {
        component: _stats(
            [
                row["component_values"][component]
                for row in rows
                if row["component_values"][component] is not None
            ]
        )
        for component in AVERAGE_COMPONENTS
    }
    total = len(rows)
    dominant = _dominant_factors(limiting_counts, total, threshold=0.35)
    under_used = _under_used_factors(rows, limiting_counts, positive_counts)
    return {
        "most_common_limiting_factor": _most_common(limiting_counts),
        "most_common_positive_factor": _most_common(positive_counts),
        "dominance_interpretation": "frequency_only_not_weight_or_sensitivity",
        "component_statistics": component_stats,
        "limiting_factor_counts": dict(sorted(limiting_counts.items())),
        "positive_factor_counts": dict(sorted(positive_counts.items())),
        "components_that_dominate_too_many_scenarios": dominant,
        "components_that_almost_never_contribute": under_used,
        "fixture_coverage_limitations": _fixture_coverage_limitations(rows),
        "opportunities_for_future_calibration": _future_calibration_items(dominant, under_used),
    }


def _summary(rows: list[dict[str, object]]) -> dict[str, object]:
    planet_or_moon = [row for row in rows if row["target_type"] in {"planet", "moon"}]
    deep_sky = [row for row in rows if row["target_type"] in {"galaxy", "diffuse_nebula"}]
    blocked = [row for row in rows if _number(row["component_values"]["SessionViability"]) == 0.0]
    confidence_score_effects = [
        _maybe_number(row["confidence_metadata"].get("score_effect"))
        for row in rows
        if isinstance(row.get("confidence_metadata"), dict)
    ]
    return {
        "model_aligned_behaviours": (
            f"{len(planet_or_moon)} planet/Moon scenarios keep sky-background handling in ObservationEnvironment.",
            f"{len(deep_sky)} galaxy/diffuse nebula scenarios expose sky-owned EffectiveObservability before observer capability.",
            f"{len(blocked)} blocked-session scenarios reach score zero through SessionViability while target values remain present.",
            "Equipment changes PracticalTargetValue through ObserverCapability rather than mutating ObservableTargetValue.",
            f"All confidence score effects are {sorted(set(confidence_score_effects))}; confidence remains metadata only.",
        ),
        "behaviour_requiring_review": (
            "ObserverCapability is frequently the broadest limiter; review whether fixture equipment baselines represent intended observing practice.",
            "All-zero opportunity groups are tied/non-actionable; stable order should not become user-visible recommendation order.",
            "Legacy score and NSOM value remain different scales, so raw numeric equality is not a calibration target.",
        ),
        "potential_calibration_concerns": (
            "ObserverCapability summary uses a flat mean of seven dimensions; future calibration may need target-class-aware weights.",
            "Window and chronology components now vary in fixtures, but the coverage is still synthetic and should not be tuned against alone.",
            "Deep-sky sky-background sensitivity is visible; future work should verify exact slopes against real observing expectations.",
        ),
    }


def _scenario_markdown(row: dict[str, object]) -> list[str]:
    lines = [
        f"### {row['scenario_id']} - {row['target']['name']}",
        "",
        (
            f"Axes: sky `{row['axes']['sky_profile']}`, session `{row['axes']['session_profile']}`, "
            f"equipment `{row['axes']['equipment_profile']}`, geometry `{row['axes']['target_geometry_profile']}`, "
            f"confidence `{row['axes']['confidence_profile']}`."
        ),
        (
            _ranking_summary(row)
            + f"; legacy rank {row['legacy']['rank']} with score {_fmt(row['legacy']['score'])}."
        ),
        f"Intended NSOM expectation: {row['intended_nsom_expectation']}.",
        "",
    ]
    for stage in row["pipeline"]:
        lines.extend(
            [
                f"#### {stage['stage']}",
                "",
                f"- Inputs: {_compact_mapping(stage['inputs'])}",
                f"- Formula: {stage['formula']}",
                f"- Intermediate calculation: {stage['intermediate_calculation']}",
                f"- Sub-formulas: {_sub_formula_list(stage['sub_formulas'])}",
                f"- Outputs: {_compact_mapping(stage['outputs'])}",
                f"- Dominant positive contributors: {_factor_list(stage['dominant_positive_contributors'])}",
                f"- Dominant limiting contributors: {_factor_list(stage['dominant_limiting_contributors'])}",
                "",
            ]
        )
    confidence = row["confidence_metadata"]
    lines.extend(
        [
            "#### RecommendationConfidence Metadata",
            "",
            f"- Confidence value: {_fmt(confidence.get('value'))}",
            f"- Role: {confidence.get('role')}",
            f"- Score effect: {_fmt(confidence.get('score_effect'))}",
            "- Pipeline membership: outside mathematical pipeline",
            "",
            "#### Legacy Comparison",
            "",
            f"- {row['legacy']['readable_explanation']}",
            f"- Unavailable legacy components: {', '.join(_legacy_component_labels(row['legacy']['components'], unavailable=True))}",
            "",
            "#### Why NSOM Differs",
            "",
        ]
    )
    for item in row["why_nsom_differs"]:
        lines.append(f"- {item}")
    lines.append("")
    return lines


def _why_nsom_differs(
    row: dict[str, object],
    component_values: dict[str, float | None],
    ranking_stage: dict[str, object],
) -> tuple[str, ...]:
    effective = row["nsom"]["effective_observability"]
    legacy_components = row["legacy"]["components"]
    confidence = row["nsom"]["recommendation_confidence"]
    moon_background = _number(effective["lunar_sky_background"])
    sky_background = _number(effective["static_sky_background"])
    legacy_moon = _legacy_value(legacy_components, "moon_penalty")
    legacy_pollution = _legacy_value(legacy_components, "pollution_penalty")
    observer = _number(component_values["ObserverCapability"])
    observable = _number(component_values["ObservableTargetValue"])
    practical = _number(component_values["PracticalTargetValue"])
    session = _number(component_values["SessionViability"])
    rank_delta = int(row["rank_delta"])
    if ranking_stage["outputs"]["ranking_status"] == "tied_non_actionable":
        rank_text = (
            "All NSOM opportunity scores in this group are 0.0; stable row order is "
            "non-actionable and not a meaningful recommendation order."
        )
    else:
        rank_text = (
            f"NSOM rank {row['nsom']['rank']} differs from legacy rank {row['legacy']['rank']} by {rank_delta}."
            if rank_delta
            else f"NSOM and legacy both rank this target at {row['nsom']['rank']} in this group."
        )
    return (
        rank_text,
        (
            f"Moon background is {_fmt(moon_background)} inside ObservationEnvironment; "
            f"legacy exposes moon_penalty {_fmt(legacy_moon)}."
        ),
        (
            f"Sky background is {_fmt(sky_background)} inside ObservationEnvironment; "
            f"legacy exposes pollution_penalty {_fmt(legacy_pollution)}."
        ),
        (
            f"ObserverCapability summary {_fmt(observer)} turns ObservableTargetValue "
            f"{_fmt(observable)} into PracticalTargetValue {_fmt(practical)}; legacy exposes "
            f"only aperture_bonus {_fmt(_legacy_value(legacy_components, 'aperture_bonus'))}."
        ),
        (
            f"SessionViability {_fmt(session)} affects ObservationOpportunity only; "
            f"ObservableTargetValue stays {_fmt(observable)} and PracticalTargetValue stays {_fmt(practical)}."
        ),
        (
            f"RecommendationConfidence value {_fmt(confidence.get('value'))} is metadata-only "
            f"with score_effect {_fmt(confidence.get('score_effect'))}."
        ),
    )


def _stage(
    name: str,
    *,
    inputs: dict[str, object],
    formula: str,
    intermediate_calculation: str,
    outputs: dict[str, object],
    positives: list[dict[str, object]],
    limits: list[dict[str, object]],
    sub_formulas: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    return {
        "stage": name,
        "inputs": inputs,
        "formula": formula,
        "intermediate_calculation": intermediate_calculation,
        "sub_formulas": sub_formulas,
        "outputs": outputs,
        "dominant_positive_contributors": tuple(positives),
        "dominant_limiting_contributors": tuple(limits),
    }


def _environment_components(effective: dict[str, object]) -> dict[str, float]:
    return {
        "geometric_visibility": _number(effective["geometric_visibility"]),
        "moon_background": _number(effective["lunar_sky_background"]),
        "sky_background": _number(effective["static_sky_background"]),
        "atmospheric_transparency": _number(effective["atmospheric_transparency"]),
        "horizon_context": _number(effective["horizon_context"]),
    }


def _observer_dimensions(observer: dict[str, object]) -> dict[str, float]:
    return {
        "light_grasp": _number(observer["light_grasp"]),
        "resolution": _number(observer["resolution"]),
        "field_of_view": _number(observer["field_of_view"]),
        "magnification_range": _number(observer["magnification_range"]),
        "tracking_or_goto": _number(observer["tracking_or_goto"]),
        "experience_level": _number(observer["experience_level"]),
        "practical_comfort": _number(observer["practical_comfort"]),
    }


def _environment_sub_formulas(
    row: dict[str, object],
    effective: dict[str, object],
    environment: dict[str, object],
) -> tuple[dict[str, object], ...]:
    return (
        _geometric_visibility_formula(row, effective),
        _moon_background_formula(row, effective),
        _sky_background_formula(row, effective),
        _atmospheric_transparency_formula(row, effective),
        _horizon_context_formula(row, effective),
        _sub_formula(
            component="environment_sources",
            status="adapter-derived",
            formula="ObservationEnvironment preserves source labels supplied by the runtime environment adapter",
            inputs={
                "sky_quality_source": environment.get("sky_quality_source", ""),
                "weather_source": environment.get("weather_source", ""),
                "atmosphere_source": environment.get("atmosphere_source", ""),
            },
            intermediate_calculation="source labels do not modify score",
            output=None,
        ),
    )


def _geometric_visibility_formula(row: dict[str, object], effective: dict[str, object]) -> dict[str, object]:
    visible = bool(row["target"].get("visible"))
    output = _number(effective["geometric_visibility"])
    return _sub_formula(
        component="geometric_visibility",
        status="available",
        formula="geometric_visibility = 1.0 if target.visible else 0.0",
        inputs={"target_visible": visible},
        intermediate_calculation=f"target_visible={visible} -> {_fmt(output)}",
        output=output,
    )


def _moon_background_formula(row: dict[str, object], effective: dict[str, object]) -> dict[str, object]:
    output = _number(effective["lunar_sky_background"])
    target_class = _target_class(row)
    profile = _target_profile(target_class)
    moon = row.get("runtime_inputs", {}).get("moon", {})
    illumination_text = moon.get("illumination") if isinstance(moon, dict) else None
    if profile is None or illumination_text is None:
        return _sub_formula(
            component="moon_background",
            status="adapter-derived",
            formula="PlannerNsomScoringService._moon_background_factor(); profile or Moon input not retained",
            inputs={"target_class": target_class, "moon_illumination": illumination_text},
            intermediate_calculation="not enough retained inputs to expand safely",
            output=output,
        )
    max_influence = _clamp_unit(profile.max_moon_influence / 100.0)
    illumination = _unit_from_percentage_text(illumination_text)
    severity = _clamp_unit((illumination - 0.2) / 0.8)
    expected = _clamp_unit(1.0 - (severity * max_influence))
    return _sub_formula(
        component="moon_background",
        status="available",
        formula=(
            "moon_background = 1.0 when max_moon_influence <= 0; otherwise "
            "1.0 - clamp((illumination - 0.2) / 0.8) * clamp(max_moon_influence / 100)"
        ),
        inputs={
            "target_class": target_class,
            "moon_illumination": illumination_text,
            "illumination_unit": illumination,
            "max_moon_influence": profile.max_moon_influence,
        },
        intermediate_calculation=(
            f"1.0 - ({_fmt(severity)} * {_fmt(max_influence)}) = {_fmt(expected)}; "
            f"reported {_fmt(output)}"
        ),
        output=output,
    )


def _sky_background_formula(row: dict[str, object], effective: dict[str, object]) -> dict[str, object]:
    output = _number(effective["static_sky_background"])
    target_class = _target_class(row)
    profile = _target_profile(target_class)
    sky_quality = row.get("runtime_inputs", {}).get("sky_quality", {})
    if profile is None or not isinstance(sky_quality, dict):
        return _sub_formula(
            component="sky_background",
            status="adapter-derived",
            formula="PlannerNsomScoringService._sky_background_factor(); profile or sky-quality input not retained",
            inputs={"target_class": target_class},
            intermediate_calculation="not enough retained inputs to expand safely",
            output=output,
        )
    max_influence = _clamp_unit(profile.max_sky_background_influence / 100.0)
    radiance = sky_quality.get("viirs_radiance")
    bortle = sky_quality.get("bortle_class")
    if radiance is not None:
        radiance_value = max(0.0, _number(radiance))
        severity = _clamp_unit(math.log10(radiance_value + 1.0) / 3.0)
        formula = (
            "severity = clamp(log10(max(0, viirs_radiance) + 1) / 3); "
            "sky_background = 1.0 - severity * clamp(max_sky_background_influence / 100)"
        )
        inputs = {
            "target_class": target_class,
            "viirs_radiance": radiance,
            "max_sky_background_influence": profile.max_sky_background_influence,
        }
    else:
        severity = _clamp_unit((_number(bortle) - 3.0) / 6.0)
        formula = (
            "severity = clamp((bortle_class - 3) / 6); "
            "sky_background = 1.0 - severity * clamp(max_sky_background_influence / 100)"
        )
        inputs = {
            "target_class": target_class,
            "bortle_class": bortle,
            "max_sky_background_influence": profile.max_sky_background_influence,
        }
    expected = _clamp_unit(1.0 - (severity * max_influence))
    return _sub_formula(
        component="sky_background",
        status="available",
        formula=formula,
        inputs=inputs,
        intermediate_calculation=(
            f"1.0 - ({_fmt(severity)} * {_fmt(max_influence)}) = {_fmt(expected)}; "
            f"reported {_fmt(output)}"
        ),
        output=output,
    )


def _atmospheric_transparency_formula(row: dict[str, object], effective: dict[str, object]) -> dict[str, object]:
    output = _number(effective["atmospheric_transparency"])
    scores = row.get("runtime_inputs", {}).get("advanced_scores", {})
    if not isinstance(scores, dict):
        return _sub_formula(
            component="atmospheric_transparency",
            status="adapter-derived",
            formula="PlannerNsomScoringService._category_factor(); advanced scores not retained",
            inputs={},
            intermediate_calculation="not enough retained inputs to expand safely",
            output=output,
        )
    object_type = str(row["target"].get("object_type", ""))
    score_name = "planetary_score" if object_type == "Pianeta" else "deep_sky_score"
    score = _number(scores.get(score_name))
    expected = _clamp_unit(score / 100.0)
    return _sub_formula(
        component="atmospheric_transparency",
        status="available",
        formula="atmospheric_transparency = selected AdvancedObservingScores category score / 100",
        inputs={"object_type": object_type, score_name: score},
        intermediate_calculation=f"{_fmt(score)} / 100 = {_fmt(expected)}; reported {_fmt(output)}",
        output=output,
    )


def _horizon_context_formula(row: dict[str, object], effective: dict[str, object]) -> dict[str, object]:
    output = _number(effective["horizon_context"])
    altitude_text = row["target"].get("max_altitude", "")
    altitude = _first_number(altitude_text)
    visible = bool(row["target"].get("visible"))
    if altitude is None:
        expected = 1.0 if visible else 0.0
        return _sub_formula(
            component="horizon_context",
            status="available",
            formula="horizon_context = 1.0 if target.visible else 0.0 when altitude is unavailable",
            inputs={"max_altitude": altitude_text, "target_visible": visible},
            intermediate_calculation=f"altitude unavailable, target_visible={visible} -> {_fmt(expected)}; reported {_fmt(output)}",
            output=output,
        )
    expected = _clamp_unit((altitude - 5.0) / 35.0)
    return _sub_formula(
        component="horizon_context",
        status="available",
        formula="horizon_context = clamp((max_altitude_degrees - 5) / 35)",
        inputs={"max_altitude": altitude_text, "max_altitude_degrees": altitude},
        intermediate_calculation=f"({_fmt(altitude)} - 5.0000) / 35.0000 = {_fmt(expected)}; reported {_fmt(output)}",
        output=output,
    )


def _observer_sub_formulas(
    row: dict[str, object],
    observer: dict[str, object],
    dimensions: dict[str, float],
    summary: float,
) -> tuple[dict[str, object], ...]:
    telescope = row.get("runtime_inputs", {}).get("telescope", {})
    aperture = _number(telescope.get("aperture_mm")) if isinstance(telescope, dict) else 0.0
    focal_length = _number(telescope.get("focal_length_mm")) if isinstance(telescope, dict) else 0.0
    mount = str(telescope.get("mount", "")) if isinstance(telescope, dict) else ""
    aperture_unit = _unit_from_range(aperture, lower=50.0, upper=250.0)
    focal_unit = _unit_from_range(focal_length, lower=350.0, upper=2000.0)
    field_width = _clamp_unit(1.0 - (0.75 * focal_unit))
    tracking = _tracking_capability(mount)
    formulas = [
        _sub_formula(
            component="telescope_aperture_unit",
            status="available",
            formula="aperture_unit = clamp((aperture_mm - 50) / (250 - 50))",
            inputs={"aperture_mm": aperture},
            intermediate_calculation=f"({_fmt(aperture)} - 50.0000) / 200.0000 = {_fmt(aperture_unit)}",
            output=aperture_unit,
        ),
        _sub_formula(
            component="telescope_focal_length_unit",
            status="available",
            formula="focal_length_unit = clamp((focal_length_mm - 350) / (2000 - 350))",
            inputs={"focal_length_mm": focal_length},
            intermediate_calculation=f"({_fmt(focal_length)} - 350.0000) / 1650.0000 = {_fmt(focal_unit)}",
            output=focal_unit,
        ),
        _sub_formula(
            component="telescope_field_width",
            status="available",
            formula="field_width = clamp(1.0 - 0.75 * focal_length_unit)",
            inputs={"focal_length_unit": focal_unit},
            intermediate_calculation=f"1.0000 - (0.7500 * {_fmt(focal_unit)}) = {_fmt(field_width)}",
            output=field_width,
        ),
        _sub_formula(
            component="tracking_capability",
            status="available",
            formula="tracking = 0.8 for GoTo/tracking/EQ mounts, 0.2 for manual/dob/altaz, otherwise 0.4",
            inputs={"mount": mount},
            intermediate_calculation=f"mount={mount} -> {_fmt(tracking)}",
            output=tracking,
        ),
    ]
    for name in ("light_grasp", "resolution", "field_of_view", "magnification_range", "tracking_or_goto"):
        formulas.append(
            _sub_formula(
                component=name,
                status="adapter-derived",
                formula=(
                    f"{name} is produced from recommendation-adapter base capability plus telescope inputs; "
                    "base capability is not retained separately in this report row"
                ),
                inputs={
                    "reported_dimension": dimensions[name],
                    "aperture_unit": aperture_unit,
                    "focal_length_unit": focal_unit,
                    "field_width": field_width,
                    "tracking_capability": tracking,
                },
                intermediate_calculation="reported final dimension is traced, base adapter input is unavailable",
                output=dimensions[name],
            )
        )
    formulas.append(
        _sub_formula(
            component="observer_capability_summary",
            status="available",
            formula=(
                "summary = mean(light_grasp, resolution, field_of_view, magnification_range, "
                "tracking_or_goto, experience_level, practical_comfort)"
            ),
            inputs=dimensions,
            intermediate_calculation=f"mean({_format_values(dimensions.values())}) = {_fmt(summary)}",
            output=summary,
        )
    )
    if observer.get("filters"):
        formulas.append(
            _sub_formula(
                component="filters",
                status="available",
                formula="filters are retained as observer metadata and do not enter the current summary formula",
                inputs={"filters": observer.get("filters", [])},
                intermediate_calculation="no score multiplier",
                output=None,
            )
        )
    else:
        formulas.append(
            _sub_formula(
                component="filters",
                status="unavailable",
                formula="no filter contribution is present in the current ObserverCapability summary formula",
                inputs={"filters": []},
                intermediate_calculation="no score multiplier",
                output=None,
            )
        )
    return tuple(formulas)


def _sub_formula(
    *,
    component: str,
    status: str,
    formula: str,
    inputs: dict[str, object],
    intermediate_calculation: str,
    output: object,
) -> dict[str, object]:
    return {
        "component": component,
        "status": status,
        "formula": formula,
        "inputs": inputs,
        "intermediate_calculation": intermediate_calculation,
        "output": output,
    }


def _unit_component_factors(
    components: dict[str, float],
    *,
    owner: str,
    component: str,
    reason_suffix: str,
    positive_threshold: float = 0.995,
    limiting_threshold: float = 0.995,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    positives = []
    limits = []
    for name, value in components.items():
        if value >= positive_threshold:
            positives.append(_factor(owner, component, name, value, f"{name} is a strong {reason_suffix}."))
        elif value < limiting_threshold:
            limits.append(_factor(owner, component, name, value, f"{name} limits the {reason_suffix}."))
    limits.sort(key=lambda factor: float(factor["value"]))
    return positives, limits


def _single_multiplier_factors(
    value: float,
    *,
    owner: str,
    component: str,
    factor: str,
    positive_reason: str,
    limiting_reason: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if value >= 0.995:
        return [_factor(owner, component, factor, value, positive_reason)], []
    return [], [_factor(owner, component, factor, value, limiting_reason)]


def _factor(owner: str, component: str, factor: str, value: object, reason: str) -> dict[str, object]:
    return {
        "owner": owner,
        "component": component,
        "factor": factor,
        "value": _number(value),
        "reason": reason,
    }


def _without_confidence(factors: list[dict[str, object]]) -> list[dict[str, object]]:
    return [factor for factor in factors if factor.get("owner") != "confidence"]


def _factor_counter(factor_groups: object) -> Counter[str]:
    counter: Counter[str] = Counter()
    for factors in factor_groups:
        for factor in factors:
            counter[_factor_key(factor)] += 1
    return counter


def _factor_key(factor: dict[str, object]) -> str:
    return f"{factor['owner']}:{factor['factor']}"


def _most_common(counter: Counter[str]) -> dict[str, object] | None:
    if not counter:
        return None
    factor, count = counter.most_common(1)[0]
    owner, name = factor.split(":", 1)
    return {"owner": owner, "factor": name, "count": count}


def _dominant_factors(counter: Counter[str], total: int, *, threshold: float) -> tuple[dict[str, object], ...]:
    dominant = []
    for factor, count in counter.most_common():
        share = count / total if total else 0.0
        if share >= threshold:
            owner, name = factor.split(":", 1)
            dominant.append({"owner": owner, "factor": name, "count": count, "share": share})
    return tuple(dominant)


def _under_used_factors(
    rows: list[dict[str, object]],
    limiting_counts: Counter[str],
    positive_counts: Counter[str],
) -> tuple[dict[str, object], ...]:
    candidate_factors = (
        ("sky", "moon_background"),
        ("sky", "sky_background"),
        ("sky", "atmospheric_transparency"),
        ("sky", "horizon_context"),
        ("observer", "observer_capability_summary"),
        ("session", "session_viability"),
        ("opportunity", "observing_window_quality"),
        ("opportunity", "chronology_fit"),
        ("opportunity", "practical_constraints"),
    )
    under_used = []
    for owner, factor in candidate_factors:
        key = f"{owner}:{factor}"
        total_count = limiting_counts.get(key, 0) + positive_counts.get(key, 0)
        values = [_factor_value(row, owner, factor) for row in rows]
        value_range = max(values) - min(values) if values else 0.0
        if total_count <= max(2, int(len(rows) * 0.04)) or value_range <= 0.02:
            under_used.append(
                {
                    "owner": owner,
                    "factor": factor,
                    "count": total_count,
                    "share": total_count / len(rows) if rows else 0.0,
                    "range": value_range,
                }
            )
    return tuple(under_used)


def _future_calibration_items(
    dominant: tuple[dict[str, object], ...],
    under_used: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    items = [
        "Review whether ObserverCapability should remain a flat mean or become target-class aware using sensitivity tests, not frequency counts alone.",
        "Keep blocked-session handling explicit before enabling NSOM Planner by default.",
        "Use real observing logs later to calibrate sky-background and atmospheric transparency slopes.",
    ]
    if dominant:
        items.append(
            "Inspect dominant factors "
            + ", ".join(f"{item['owner']}:{item['factor']}" for item in dominant)
            + " as high-frequency signals before tuning any weights."
        )
    if under_used:
        items.append(
            "Add or expand fixtures for under-used factors "
            + ", ".join(f"{item['owner']}:{item['factor']}" for item in under_used)
            + "."
        )
    return tuple(items)


def _fixture_coverage_limitations(rows: list[dict[str, object]]) -> tuple[str, ...]:
    equipment_counts = Counter(str(row["axes"]["equipment_profile"]) for row in rows)
    session_counts = Counter(str(row["axes"]["session_profile"]) for row in rows)
    window_values = sorted(
        {
            _factor_value(row, "opportunity", "observing_window_quality")
            for row in rows
        }
    )
    limitations = [
        "Dominance counts are frequency counts across deterministic fixtures, not direct sensitivity measurements.",
        "Component min/max/range is a fixture sensitivity proxy, not calibrated elasticity.",
        f"Equipment coverage is uneven: {dict(sorted(equipment_counts.items()))}.",
        f"Session coverage is uneven: {dict(sorted(session_counts.items()))}.",
        f"Observed observing_window_quality fixture values: {window_values}.",
    ]
    return tuple(limitations)


def _stats(values: list[float | None]) -> dict[str, float | None]:
    numbers = [_number(value) for value in values if value is not None]
    if not numbers:
        return {"average": None, "min": None, "max": None, "range": None}
    minimum = min(numbers)
    maximum = max(numbers)
    return {
        "average": mean(numbers),
        "min": minimum,
        "max": maximum,
        "range": maximum - minimum,
    }


def _legacy_component_labels(components: dict[str, object], *, unavailable: bool) -> list[str]:
    labels = []
    for name, component in components.items():
        status = component.get("status") if isinstance(component, dict) else None
        if unavailable and status == UNAVAILABLE:
            labels.append(name)
        elif not unavailable and status != UNAVAILABLE:
            labels.append(name)
    return labels


def _legacy_value(components: dict[str, object], key: str) -> object:
    component = components.get(key)
    if isinstance(component, dict) and component.get("status") != UNAVAILABLE:
        return component.get("value")
    return None


def _component_formula(prefix: str, components: dict[str, float]) -> str:
    return prefix + ": " + ", ".join(f"{name}={_fmt(value)}" for name, value in components.items())


def _multiplication_calculation(components: dict[str, float]) -> str:
    values = list(components.values())
    product = 1.0
    for value in values:
        product *= value
    return f"{_format_values(values, separator=' * ')} = {_fmt(product)}"


def _format_values(values: object, *, separator: str = ", ") -> str:
    return separator.join(_fmt(value) for value in values)


def _note_value(notes: list[str], key: str) -> str | None:
    prefix = f"{key}="
    for note in notes:
        if note.startswith(prefix):
            return note[len(prefix):]
    return None


def _rows(report: dict[str, object]) -> list[dict[str, object]]:
    return [row for group in report["scenario_groups"] for row in group["scenarios"]]


def _compact_mapping(value: object) -> str:
    if isinstance(value, dict):
        return "; ".join(f"{key}={_compact_mapping(item)}" for key, item in value.items())
    if isinstance(value, list):
        if len(value) > 4:
            return "[" + ", ".join(str(item) for item in value[:4]) + ", ...]"
        return "[" + ", ".join(str(item) for item in value) + "]"
    if isinstance(value, float):
        return _fmt(value)
    return str(value)


def _ranking_summary(row: dict[str, object]) -> str:
    ranking = row["pipeline"][-1]["outputs"]
    if ranking["ranking_status"] == "tied_non_actionable":
        return (
            f"NSOM ranking tied/non-actionable at score {_fmt(ranking['score'])} "
            f"(stable position {ranking['rank']}; not a recommendation order)"
        )
    return f"Final NSOM rank {ranking['rank']} with score {_fmt(ranking['score'])}"


def _sub_formula_list(formulas: list[dict[str, object]]) -> str:
    if not formulas:
        return "none"
    return "; ".join(
        (
            f"{item['component']}[{item['status']}]: {item['formula']} "
            f"=> {item['intermediate_calculation']}"
        )
        for item in formulas
    )


def _factor_list(factors: list[dict[str, object]]) -> str:
    if not factors:
        return "none"
    return "; ".join(
        f"{factor['owner']}:{factor['factor']}={_fmt(factor['value'])}"
        for factor in factors
    )


def _count_label(item: dict[str, object] | None) -> str:
    if not item:
        return "none"
    return f"{item['owner']}:{item['factor']} ({item['count']} scenarios)"


def _factor_count_sentence(item: dict[str, object]) -> str:
    sentence = (
        f"{item['owner']}:{item['factor']} appears in {item['count']} scenarios "
        f"({_fmt(_number(item['share']) * 100.0)}%)."
    )
    if "range" in item:
        sentence = sentence[:-1] + f" with value range {_fmt(item['range'])}."
    return sentence


def _target_class(row: dict[str, object]) -> str | None:
    observable = row["nsom"]["observable_target_value"]
    target_class = observable.get("target_class") if isinstance(observable, dict) else None
    return str(target_class) if target_class else None


def _target_profile(target_class: str | None):
    if not target_class:
        return None
    try:
        return NSOM_TARGET_CLASS_PROFILES.get(NsomTargetClass(target_class))
    except ValueError:
        return None


def _factor_value(row: dict[str, object], owner: str, factor: str) -> float:
    if owner == "sky":
        effective = next(stage for stage in row["pipeline"] if stage["stage"] == "EffectiveObservability")
        return _number(effective["inputs"].get(factor))
    if owner == "observer" and factor == "observer_capability_summary":
        return _number(row["component_values"]["ObserverCapability"])
    if owner == "session" and factor == "session_viability":
        return _number(row["component_values"]["SessionViability"])
    if owner == "opportunity" and factor == "observing_window_quality":
        stage = next(stage for stage in row["pipeline"] if stage["stage"] == "ObservationWindow")
        return _number(stage["outputs"]["value"])
    if owner == "opportunity" and factor == "chronology_fit":
        stage = next(stage for stage in row["pipeline"] if stage["stage"] == "Chronology")
        return _number(stage["outputs"]["value"])
    if owner == "opportunity" and factor == "practical_constraints":
        stage = next(stage for stage in row["pipeline"] if stage["stage"] == "ObservationOpportunity")
        return _number(stage["inputs"]["practical_constraints"])
    return 0.0


def _unit_from_percentage_text(value: object) -> float:
    number = _first_number(value)
    return _clamp_unit((number or 0.0) / 100.0)


def _first_number(value: object) -> float | None:
    text = str(value).replace(",", ".")
    current = ""
    found_digit = False
    for char in text:
        if char.isdigit() or char in ".-":
            current += char
            found_digit = found_digit or char.isdigit()
        elif current and found_digit:
            break
        else:
            current = ""
            found_digit = False
    if not current or not found_digit:
        return None
    return _maybe_number(current)


def _unit_from_range(value: object, *, lower: float, upper: float) -> float:
    number = _number(value)
    if upper <= lower:
        return 0.0
    return _clamp_unit((number - lower) / (upper - lower))


def _tracking_capability(value: object) -> float:
    text = str(value).lower()
    if any(token in text for token in ("goto", "go-to", "computer", "eq", "tracking", "motoriz")):
        return 0.8
    if any(token in text for token in ("dob", "altaz", "manual")):
        return 0.2
    return 0.4


def _clamp_unit(value: object) -> float:
    return max(0.0, min(1.0, _number(value)))


def _fmt(value: object) -> str:
    number = _maybe_number(value)
    if number is None:
        return "None"
    return f"{number:.4f}"


def _number(value: object) -> float:
    number = _maybe_number(value)
    return 0.0 if number is None else number


def _maybe_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
