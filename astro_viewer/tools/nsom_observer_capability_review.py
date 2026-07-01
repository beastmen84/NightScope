from __future__ import annotations

from dataclasses import replace
from statistics import mean

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    NsomTargetClass,
    PracticalTargetValue,
    RecommendationConfidence,
    nsom_to_json_compatible,
    observer_capability_weight_profile_for_target,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService


TARGET_CLASS_SPECS = (
    ("planet", "planet", "Pianeta", "Planet", "Facile"),
    ("moon", "moon", "Luna", "Moon", "Facile"),
    ("galaxy", "galaxy", "Galaxy", "Galaxy", "Media"),
    ("diffuse_nebula", "diffuse_nebula", "Nebula", "Diffuse Nebula", "Media"),
    ("open_cluster", "open_cluster", "Open Cluster", "Open Cluster", "Facile"),
    ("globular_cluster", "globular_cluster", "Globular Cluster", "Globular Cluster", "Media"),
)

OBSERVER_REVIEW_CASES = (
    "aperture_only",
    "focal_length_only",
    "mount_tracking_only",
    "field_of_view_only",
    "practical_comfort_setup_only",
)

OBSERVER_DIMENSIONS = (
    "light_grasp",
    "resolution",
    "field_of_view",
    "magnification_range",
    "tracking_or_goto",
    "experience_level",
    "practical_comfort",
)


def generate_observer_capability_review_data() -> dict[str, object]:
    """Return deterministic developer-only ObserverCapability sensitivity data."""

    service = PlannerNsomScoringService()
    scores = _scores()
    sky_quality = _sky_quality()
    moon = _moon()
    telescope = _baseline_telescope()
    cases = []

    for target_class, target in _target_cases():
        baseline = service.practical_target_value(
            target,
            scores=scores,
            sky_quality=sky_quality,
            telescope=telescope,
            moon=moon,
        )
        for case_name in OBSERVER_REVIEW_CASES:
            cases.append(
                _review_case(
                    service,
                    target_class=target_class,
                    nsom_target_class=_target_class_from_label(target_class),
                    target=target,
                    baseline=baseline,
                    baseline_telescope=telescope,
                    scores=scores,
                    sky_quality=sky_quality,
                    moon=moon,
                    case_name=case_name,
                )
            )

    report = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "planner_scoring_changed": False,
            "legacy_score_used_as_expected_output": False,
            "target_classes": tuple(spec[0] for spec in TARGET_CLASS_SPECS),
            "observer_sensitivity_cases": OBSERVER_REVIEW_CASES,
            "case_count": len(cases),
            "stable_sky_session_inputs": {
                "sky_quality": nsom_to_json_compatible(sky_quality),
                "moon": nsom_to_json_compatible(moon),
                "scores": nsom_to_json_compatible(scores),
            },
        },
        "cases": tuple(cases),
        "aggregate_review": _aggregate_review(cases),
        "confidence_neutrality": _confidence_neutrality_check(service, scores, sky_quality, moon, telescope),
    }
    return nsom_to_json_compatible(report)


def _review_case(
    service: PlannerNsomScoringService,
    *,
    target_class: str,
    nsom_target_class: NsomTargetClass,
    target: CelestialObject,
    baseline: PracticalTargetValue,
    baseline_telescope: Telescope,
    scores: AdvancedObservingScores,
    sky_quality: SkyQuality,
    moon: MoonSummary,
    case_name: str,
) -> dict[str, object]:
    changed_target, changed_telescope, representability, case_note = _changed_inputs(
        target,
        baseline_telescope,
        case_name,
    )
    if case_name == "practical_comfort_setup_only":
        changed_observer = replace(
            baseline.observer_capability,
            practical_comfort=0.95,
            notes=(*baseline.observer_capability.notes, "observer_review:practical_comfort_only"),
        )
        changed_q_target = project_observer_capability_for_target(changed_observer, nsom_target_class)
        changed = PracticalTargetValue.from_observable(
            observable_target_value=baseline.observable_target_value,
            observer_capability=changed_observer,
            capability_summary=changed_q_target,
        )
    else:
        changed = service.practical_target_value(
            changed_target,
            scores=scores,
            sky_quality=sky_quality,
            telescope=changed_telescope,
            moon=moon,
        )

    baseline_dimensions = _observer_dimensions(baseline)
    changed_dimensions = _observer_dimensions(changed)
    dimension_delta = {
        name: changed_dimensions[name] - baseline_dimensions[name]
        for name in OBSERVER_DIMENSIONS
    }
    changed_dimensions_only = tuple(
        name
        for name, value in dimension_delta.items()
        if abs(value) > 1e-12
    )
    observable_unchanged = abs(
        changed.observable_target_value.value - baseline.observable_target_value.value
    ) <= 1e-12
    baseline_flat_summary = baseline.observer_capability.summary_for_planning()
    changed_flat_summary = changed.observer_capability.summary_for_planning()
    flat_summary_delta = changed_flat_summary - baseline_flat_summary
    baseline_q_target = project_observer_capability_for_target(
        baseline.observer_capability,
        nsom_target_class,
    )
    changed_q_target = project_observer_capability_for_target(
        changed.observer_capability,
        nsom_target_class,
    )
    q_target_delta = changed_q_target - baseline_q_target
    baseline_flat_practical = PracticalTargetValue.from_observable(
        observable_target_value=baseline.observable_target_value,
        observer_capability=baseline.observer_capability,
        capability_summary=baseline_flat_summary,
    )
    changed_flat_practical = PracticalTargetValue.from_observable(
        observable_target_value=changed.observable_target_value,
        observer_capability=changed.observer_capability,
        capability_summary=changed_flat_summary,
    )
    practical_delta = changed.value - baseline.value
    q_target_delta_vs_flat = changed_q_target - changed_flat_summary
    return {
        "target_class": target_class,
        "target_identity": {
            "object_id": target.id,
            "name": target.name,
            "object_type": target.object_type,
        },
        "changed_observer_dimension": case_name,
        "representability": representability,
        "target_class_weighting_profile": observer_capability_weight_profile_for_target(nsom_target_class),
        "baseline_flat_observer_capability_summary": baseline_flat_summary,
        "changed_flat_observer_capability_summary": changed_flat_summary,
        "flat_observer_capability_summary_delta": flat_summary_delta,
        "baseline_q_target": baseline_q_target,
        "changed_q_target": changed_q_target,
        "q_target_delta": q_target_delta,
        "q_target_delta_vs_flat": q_target_delta_vs_flat,
        "baseline_observer_capability_summary": baseline.observer_capability_summary,
        "changed_observer_capability_summary": changed.observer_capability_summary,
        "observer_capability_summary_delta": q_target_delta,
        "baseline_practical_target_value": baseline.value,
        "changed_practical_target_value": changed.value,
        "practical_target_value_delta": practical_delta,
        "baseline_practical_target_value_using_q_target": baseline.value,
        "changed_practical_target_value_using_q_target": changed.value,
        "baseline_practical_target_value_using_flat_summary": baseline_flat_practical.value,
        "changed_practical_target_value_using_flat_summary": changed_flat_practical.value,
        "practical_target_value_q_target_delta_vs_flat": changed.value - changed_flat_practical.value,
        "baseline_observable_target_value": baseline.observable_target_value.value,
        "changed_observable_target_value": changed.observable_target_value.value,
        "observable_target_value_unchanged": observable_unchanged,
        "baseline_dimensions": baseline_dimensions,
        "changed_dimensions": changed_dimensions,
        "dimension_delta": dimension_delta,
        "changed_dimensions_only": changed_dimensions_only,
        "direction_makes_nsom_sense": _direction_makes_nsom_sense(
            target_class,
            case_name,
            q_target_delta,
            observable_unchanged,
        ),
        "legacy_score_used_as_expected_output": False,
        "notes_for_future_target_specific_weighting": _target_specific_note(case_name),
        "case_note": case_note,
    }


def _changed_inputs(
    target: CelestialObject,
    telescope: Telescope,
    case_name: str,
) -> tuple[CelestialObject, Telescope, str, str]:
    if case_name == "aperture_only":
        return (
            target,
            replace(telescope, name="Aperture variant", aperture_mm=220),
            "planner_runtime_telescope",
            "Only telescope aperture changes; sky, session, target identity, focal length and mount stay fixed.",
        )
    if case_name == "focal_length_only":
        return (
            target,
            replace(telescope, name="Focal length variant", focal_length_mm=1800),
            "planner_runtime_telescope",
            "Only telescope focal length changes; this currently moves field_of_view and magnification_range in opposite directions.",
        )
    if case_name == "mount_tracking_only":
        return (
            target,
            replace(telescope, name="Tracking mount variant", mount="GoTo EQ"),
            "planner_runtime_telescope",
            "Only telescope mount/tracking text changes.",
        )
    if case_name == "field_of_view_only":
        return (
            replace(
                target,
                setup_options=(
                    {
                        "role": "field_of_view",
                        "displayLabel": "wide field",
                    },
                ),
            ),
            telescope,
            "planner_runtime_setup_options",
            "Only setup option context changes; the current adapter can isolate a wide-field contribution.",
        )
    if case_name == "practical_comfort_setup_only":
        return (
            target,
            telescope,
            "core_observer_capability_only",
            "Practical comfort is isolated in the core DTO; the current Planner telescope adapter does not expose a runtime setup-only input for it.",
        )
    raise ValueError(f"Unknown ObserverCapability review case: {case_name}")


def _aggregate_review(cases: list[dict[str, object]]) -> dict[str, object]:
    by_dimension = {}
    for case_name in OBSERVER_REVIEW_CASES:
        rows = [row for row in cases if row["changed_observer_dimension"] == case_name]
        flat_summary_deltas = [float(row["flat_observer_capability_summary_delta"]) for row in rows]
        q_target_deltas = [float(row["q_target_delta"]) for row in rows]
        practical_deltas = [float(row["practical_target_value_delta"]) for row in rows]
        by_dimension[case_name] = {
            "target_class_count": len({row["target_class"] for row in rows}),
            "flat_summary_delta_min": min(flat_summary_deltas),
            "flat_summary_delta_max": max(flat_summary_deltas),
            "flat_summary_delta_average": mean(flat_summary_deltas),
            "flat_summary_delta_uniform_across_target_classes": _all_close(flat_summary_deltas),
            "q_target_delta_min": min(q_target_deltas),
            "q_target_delta_max": max(q_target_deltas),
            "q_target_delta_average": mean(q_target_deltas),
            "q_target_delta_uniform_across_target_classes": _all_close(q_target_deltas),
            "practical_delta_min": min(practical_deltas),
            "practical_delta_max": max(practical_deltas),
            "practical_delta_average": mean(practical_deltas),
            "changed_dimensions_observed": tuple(
                sorted({dimension for row in rows for dimension in row["changed_dimensions_only"]})
            ),
        }
    uniform_cases = [
        name
        for name, stats in by_dimension.items()
        if stats["flat_summary_delta_uniform_across_target_classes"]
    ]
    target_specific_cases = [
        name
        for name, stats in by_dimension.items()
        if not stats["q_target_delta_uniform_across_target_classes"]
    ]
    return {
        "by_changed_observer_dimension": by_dimension,
        "observer_projection_findings": (
            "The current flat mean produces the same ObserverCapability summary delta for each isolated observer change across all target classes.",
            "Experimental Q_target produces target-class-specific observer deltas while preserving the full ObserverCapability profile.",
            "Focal length remains mixed: it improves magnification_range while reducing field_of_view, so Q_target can improve compact targets and reduce wide-field targets.",
            "Practical comfort can be isolated in the core DTO but not through the current Planner telescope adapter.",
        ),
        "uniform_summary_delta_cases": tuple(uniform_cases),
        "q_target_class_specific_cases": tuple(target_specific_cases),
        "target_specific_weighting_review": "q_target_experimental_internal",
    }


def _confidence_neutrality_check(
    service: PlannerNsomScoringService,
    scores: AdvancedObservingScores,
    sky_quality: SkyQuality,
    moon: MoonSummary,
    telescope: Telescope,
) -> dict[str, object]:
    target = _target("galaxy", "Galaxy", "Galaxy", "Media")
    practical = service.practical_target_value(
        target,
        scores=scores,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
    )
    weather = _weather()
    low = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=weather,
        sky_quality=sky_quality,
        moon=moon,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=weather,
        sky_quality=sky_quality,
        moon=moon,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )
    return {
        "low_confidence_value": low.confidence.value if low.confidence else None,
        "high_confidence_value": high.confidence.value if high.confidence else None,
        "low_confidence_score": low.value,
        "high_confidence_score": high.value,
        "score_delta": high.value - low.value,
        "score_neutral": abs(high.value - low.value) <= 1e-12,
    }


def _target_cases() -> tuple[tuple[str, CelestialObject], ...]:
    return tuple(
        (target_class, _target(object_id, object_type, name, difficulty))
        for target_class, object_id, object_type, name, difficulty in TARGET_CLASS_SPECS
    )


def _target_class_from_label(target_class: str) -> NsomTargetClass:
    mapping = {
        "planet": NsomTargetClass.PLANET,
        "moon": NsomTargetClass.MOON,
        "galaxy": NsomTargetClass.GALAXY,
        "diffuse_nebula": NsomTargetClass.DIFFUSE_NEBULA,
        "open_cluster": NsomTargetClass.OPEN_CLUSTER,
        "globular_cluster": NsomTargetClass.GLOBULAR_CLUSTER,
    }
    return mapping[target_class]


def _target(object_id: str, object_type: str, name: str, difficulty: str) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="8.5",
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="22:00 - 02:00",
        notes="NSOM ObserverCapability review fixture",
        recommended_setup="Telescope visual setup",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=84,
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type="telescope",
    )


def _baseline_telescope() -> Telescope:
    return Telescope(
        id="observer-review-baseline",
        name="Observer Review Baseline",
        aperture_mm=127,
        focal_length_mm=1000,
        optical_type="Reflector",
        mount="manual",
    )


def _scores() -> AdvancedObservingScores:
    return AdvancedObservingScores(
        planetary_score=90,
        deep_sky_score=90,
        planetary_label="Stable",
        deep_sky_label="Stable",
        explanation="Stable ObserverCapability review scores",
    )


def _sky_quality() -> SkyQuality:
    return SkyQuality(
        bortle_class=2,
        limiting_magnitude=6.0,
        sky_brightness=21.2,
        source="Observer review fixture",
        description="Stable dark sky",
        viirs_radiance=1.0,
    )


def _moon() -> MoonSummary:
    return MoonSummary(
        phase="Observer review fixture",
        illumination="10%",
        rise_time="18:00",
        set_time="06:00",
        best_note="Stable low Moon",
        image="",
        phase_angle=0.0,
    )


def _weather() -> WeatherSummary:
    return WeatherSummary(
        score="Stable",
        score_value=90,
        explanation="Stable ObserverCapability review weather",
        cloud_cover=10,
        precipitation_probability=0,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _observer_dimensions(practical: PracticalTargetValue) -> dict[str, float]:
    observer = practical.observer_capability
    return {
        name: float(getattr(observer, name))
        for name in OBSERVER_DIMENSIONS
    }


def _target_specific_note(case_name: str) -> str:
    notes = {
        "aperture_only": "Review whether light grasp and resolution should have the same target-class weight for planets, Moon and deep-sky targets.",
        "focal_length_only": "Review whether field_of_view and magnification_range should offset each other equally for extended targets and compact targets.",
        "mount_tracking_only": "Review whether tracking should matter uniformly across bright solar-system targets and faint deep-sky targets.",
        "field_of_view_only": "Review whether wide-field setup should matter more for diffuse nebulae and open clusters than for planets.",
        "practical_comfort_setup_only": "Review whether setup comfort should remain a general practicality factor or vary by target workflow.",
    }
    return notes[case_name]


def _direction_makes_nsom_sense(
    target_class: str,
    case_name: str,
    q_target_delta: float,
    observable_unchanged: bool,
) -> bool:
    if not observable_unchanged or abs(q_target_delta) <= 1e-12:
        return False
    if case_name == "focal_length_only":
        compact_classes = {"planet", "moon", "globular_cluster"}
        return q_target_delta > 0 if target_class in compact_classes else q_target_delta < 0
    return q_target_delta > 0


def _all_close(values: list[float], *, tolerance: float = 1e-12) -> bool:
    if not values:
        return True
    first = values[0]
    return all(abs(value - first) <= tolerance for value in values)
