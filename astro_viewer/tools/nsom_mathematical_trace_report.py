from __future__ import annotations

from collections import Counter
from pathlib import Path
from statistics import mean

from astro_viewer.app.models.nsom import nsom_to_json_compatible
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
            "limiter in the current fixtures because the medium, small and binocular "
            "profiles intentionally have sub-perfect practical capability. Session viability "
            "correctly caps blocked or poor sessions without mutating target physics."
        ),
        "",
        "## Methodology",
        "",
        "- Reuses the existing deterministic NSOM comparison scenario matrix; no random scenarios are generated.",
        "- Builds trace rows from already exported NSOM opportunities and explanations.",
        "- Shows unavailable legacy concepts as unavailable instead of reconstructing or inventing values.",
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
    for item in diagnostics["components_that_dominate_too_many_scenarios"]:
        lines.append(f"- {_factor_count_sentence(item)}")

    lines.extend(["", "Components that almost never contribute:"])
    for item in diagnostics["components_that_almost_never_contribute"]:
        lines.append(f"- {_factor_count_sentence(item)}")

    lines.extend(["", "Opportunities for future calibration:"])
    for item in diagnostics["opportunities_for_future_calibration"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Final Recommendations",
            "",
            "1. Keep the trace report developer-only until the Planner NSOM path is ready for default-on evaluation.",
            "2. Review observer capability calibration before changing Planner rankings because it is the broadest limiter in this matrix.",
            "3. Add more varied chronology/window fixtures before tuning timing components.",
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
        _environment_stage(effective, environment),
        _effective_stage(effective),
        _observable_stage(observable, effective),
        _observer_stage(observer, score_components),
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
        "why_nsom_differs": _why_nsom_differs(row, component_values),
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
    positives = []
    limits = []
    if rank == 1:
        positives.append(_factor("opportunity", "FinalPlannerRanking", "rank", 1.0, "This opportunity ranks first in its scenario group."))
    else:
        limits.append(_factor("opportunity", "FinalPlannerRanking", "rank", rank / group_size, "Other opportunities rank higher in this scenario group."))
    return _stage(
        "FinalPlannerRanking",
        inputs={
            "group_id": group["group_id"],
            "candidate_count": group_size,
            "opportunity_score": score,
        },
        formula="Final Planner ranking = sort ObservationOpportunity scores descending within the scenario group",
        intermediate_calculation=f"{_fmt(score)} sorts to rank {rank} of {group_size}",
        outputs={"rank": rank, "score": score},
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
        "component_statistics": component_stats,
        "limiting_factor_counts": dict(sorted(limiting_counts.items())),
        "positive_factor_counts": dict(sorted(positive_counts.items())),
        "components_that_dominate_too_many_scenarios": dominant,
        "components_that_almost_never_contribute": under_used,
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
            "Blocked sessions impose a hard zero opportunity value; this is mathematically coherent but needs Planner policy review before default-on use.",
            "Legacy score and NSOM value remain different scales, so raw numeric equality is not a calibration target.",
        ),
        "potential_calibration_concerns": (
            "ObserverCapability summary uses a flat mean of seven dimensions; future calibration may need target-class-aware weights.",
            "Window and chronology components have limited variation in the current deterministic matrix.",
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
            f"Final NSOM rank {row['pipeline'][-1]['outputs']['rank']} with score "
            f"{_fmt(row['pipeline'][-1]['outputs']['score'])}; legacy rank "
            f"{row['legacy']['rank']} with score {_fmt(row['legacy']['score'])}."
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
) -> dict[str, object]:
    return {
        "stage": name,
        "inputs": inputs,
        "formula": formula,
        "intermediate_calculation": intermediate_calculation,
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
        "Review whether ObserverCapability should remain a flat mean or become target-class aware.",
        "Keep blocked-session handling explicit before enabling NSOM Planner by default.",
        "Use real observing logs later to calibrate sky-background and atmospheric transparency slopes.",
    ]
    if dominant:
        items.append(
            "Inspect dominant factors "
            + ", ".join(f"{item['owner']}:{item['factor']}" for item in dominant)
            + " before tuning any weights."
        )
    if under_used:
        items.append(
            "Add or expand fixtures for under-used factors "
            + ", ".join(f"{item['owner']}:{item['factor']}" for item in under_used)
            + "."
        )
    return tuple(items)


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
