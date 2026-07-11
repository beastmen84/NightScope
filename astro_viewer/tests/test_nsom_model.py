from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from astro_viewer.app.models.nsom import (
    IntrinsicTargetQuality,
    OBSERVER_CAPABILITY_TARGET_WEIGHT_PROFILES,
    OPEN_CLUSTER_USABLE_FIELD_OF_VIEW_FLOOR,
    OPEN_CLUSTER_USABLE_FIELD_OF_VIEW_MIN_DIMENSION,
    OPEN_CLUSTER_USABLE_PRACTICAL_COMFORT_MIN_DIMENSION,
    NSOM_TARGET_CLASS_PROFILES,
    PLANET_OBSERVABLE_MIN_DIMENSION,
    PLANET_OBSERVABLE_Q_TARGET_FLOOR,
    EffectiveObservability,
    NsomTargetClass,
    NsomOwnershipBoundary,
    ObservableTargetValue,
    ObservationEnvironment,
    ObservationOpportunity,
    ObserverCapability,
    PracticalTargetValue,
    RecommendationConfidence,
    SessionViability,
    observer_capability_weight_profile_for_target,
    nsom_to_json_compatible,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import NightPlanItem


def test_target_class_profiles_match_nsom_table() -> None:
    expected = {
        NsomTargetClass.MOON: ("Moon", "very low", "none", 1.0, 0.0, 0.0, 5.0),
        NsomTargetClass.PLANET: ("Planets", "low", "none/minor", 3.0, 0.0, 0.0, 18.0),
        NsomTargetClass.GLOBULAR_CLUSTER: (
            "Globular clusters",
            "medium-low",
            "low fallback",
            4.0,
            18.0,
            18.0,
            35.0,
        ),
        NsomTargetClass.OPEN_CLUSTER: (
            "Open clusters",
            "medium-low",
            "low/medium fallback",
            3.0,
            10.0,
            12.0,
            25.0,
        ),
        NsomTargetClass.PLANETARY_NEBULA: (
            "Planetary nebulae",
            "medium",
            "medium fallback",
            5.0,
            18.0,
            22.0,
            38.0,
        ),
        NsomTargetClass.DIFFUSE_NEBULA: (
            "Diffuse nebulae",
            "high",
            "medium-high fallback",
            8.0,
            35.0,
            30.0,
            55.0,
        ),
        NsomTargetClass.GALAXY: (
            "Galaxies",
            "very high",
            "high fallback",
            12.0,
            40.0,
            35.0,
            60.0,
        ),
        NsomTargetClass.DOUBLE_STAR: (
            "Double stars",
            "low",
            "none/minor",
            2.0,
            0.0,
            0.0,
            18.0,
        ),
    }

    assert set(NSOM_TARGET_CLASS_PROFILES) == set(expected)
    for target_class, expected_values in expected.items():
        profile = NSOM_TARGET_CLASS_PROFILES[target_class]
        assert (
            profile.label,
            profile.aod_sensitivity,
            profile.pm_role,
            profile.max_aod_pm_influence,
            profile.max_moon_influence,
            profile.max_sky_background_influence,
            profile.max_total_visibility_influence,
        ) == expected_values


def test_core_dtos_are_immutable_and_owned_by_nsom_boundary() -> None:
    intrinsic = IntrinsicTargetQuality.from_score(
        82,
        object_id="messier-M31",
        name="M31",
        target_class=NsomTargetClass.GALAXY,
    )
    environment = ObservationEnvironment.from_components(static_sky_background=0.8)
    session = SessionViability.from_components(weather_suitability=0.7)

    assert IntrinsicTargetQuality.owner is NsomOwnershipBoundary.UNIVERSE
    assert ObservationEnvironment.owner is NsomOwnershipBoundary.SKY
    assert ObserverCapability.owner is NsomOwnershipBoundary.OBSERVER
    assert SessionViability.owner is NsomOwnershipBoundary.SESSION
    assert ObservationOpportunity.owner is NsomOwnershipBoundary.OPPORTUNITY
    assert RecommendationConfidence.owner is NsomOwnershipBoundary.CONFIDENCE

    with pytest.raises(FrozenInstanceError):
        intrinsic.value = 10  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        environment.static_sky_background = 1.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        session.value = 1.0  # type: ignore[misc]


def test_observable_target_value_is_independent_from_observer_capability() -> None:
    effective = EffectiveObservability.from_components(
        lunar_sky_background=0.8,
        static_sky_background=0.9,
        atmospheric_transparency=0.95,
    )
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=80.0,
        effective_observability=effective,
        target_class=NsomTargetClass.GALAXY,
    )

    binocular_profile = ObserverCapability(
        light_grasp=0.35,
        resolution=0.3,
        field_of_view=0.9,
        magnification_range=0.25,
        tracking_or_goto=0.1,
        experience_level=0.6,
        practical_comfort=0.8,
    )
    telescope_profile = ObserverCapability(
        light_grasp=0.95,
        resolution=0.9,
        field_of_view=0.55,
        magnification_range=0.9,
        tracking_or_goto=0.8,
        experience_level=0.8,
        practical_comfort=0.7,
    )

    binocular_value = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=binocular_profile,
    )
    telescope_value = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=telescope_profile,
    )

    assert observable.value == pytest.approx(54.72)
    assert binocular_value.observable_target_value is observable
    assert telescope_value.observable_target_value is observable
    assert observable.value == pytest.approx(54.72)
    assert binocular_value.value != telescope_value.value


def test_observable_target_value_keeps_intrinsic_and_practical_layers_separate() -> None:
    intrinsic = IntrinsicTargetQuality.from_score(
        84,
        object_id="messier-M42",
        name="M42",
        target_class=NsomTargetClass.DIFFUSE_NEBULA,
    )
    environment = ObservationEnvironment.from_components(
        lunar_sky_background=0.75,
        static_sky_background=0.85,
    )
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=intrinsic,
        effective_observability=EffectiveObservability.from_environment(environment),
    )
    practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=ObserverCapability(light_grasp=0.45, resolution=0.4),
        capability_summary=0.5,
    )

    assert observable.intrinsic_target is intrinsic
    assert observable.intrinsic_target_quality == pytest.approx(84.0)
    assert observable.value == pytest.approx(53.55)
    assert practical.value == pytest.approx(26.775)
    assert observable.value == pytest.approx(53.55)


def test_observer_capability_is_structured_not_only_scalar() -> None:
    profile = ObserverCapability(
        light_grasp=0.7,
        resolution=0.6,
        field_of_view=0.8,
        magnification_range=0.5,
        tracking_or_goto=0.2,
        filters=("UHC",),
        experience_level=0.9,
        observing_style="visual",
        practical_comfort=0.75,
    )

    assert profile.filters == ("UHC",)
    assert profile.observing_style == "visual"
    assert profile.summary_for_planning() == pytest.approx(0.6357142857)


def test_q_target_profiles_cover_required_classes_and_match_nsom_semantics() -> None:
    required = {
        NsomTargetClass.PLANET,
        NsomTargetClass.MOON,
        NsomTargetClass.GALAXY,
        NsomTargetClass.DIFFUSE_NEBULA,
        NsomTargetClass.OPEN_CLUSTER,
        NsomTargetClass.GLOBULAR_CLUSTER,
    }

    assert required.issubset(OBSERVER_CAPABILITY_TARGET_WEIGHT_PROFILES)

    planet = observer_capability_weight_profile_for_target(NsomTargetClass.PLANET)
    moon = observer_capability_weight_profile_for_target(NsomTargetClass.MOON)
    galaxy = observer_capability_weight_profile_for_target(NsomTargetClass.GALAXY)
    diffuse = observer_capability_weight_profile_for_target(NsomTargetClass.DIFFUSE_NEBULA)
    open_cluster = observer_capability_weight_profile_for_target(NsomTargetClass.OPEN_CLUSTER)
    globular = observer_capability_weight_profile_for_target(NsomTargetClass.GLOBULAR_CLUSTER)

    assert planet["resolution"] > planet["field_of_view"]
    assert planet["magnification_range"] > planet["field_of_view"]
    assert planet["tracking_or_goto"] > planet["field_of_view"]
    assert moon["resolution"] > moon["field_of_view"]
    assert moon["practical_comfort"] > moon["tracking_or_goto"]
    assert galaxy["light_grasp"] > galaxy["tracking_or_goto"]
    assert galaxy["field_of_view"] > galaxy["tracking_or_goto"]
    assert diffuse["light_grasp"] > diffuse["tracking_or_goto"]
    assert diffuse["field_of_view"] > diffuse["magnification_range"]
    assert open_cluster["field_of_view"] > open_cluster["magnification_range"]
    assert open_cluster["field_of_view"] > open_cluster["resolution"]
    assert open_cluster["practical_comfort"] > open_cluster["magnification_range"]
    assert open_cluster["practical_comfort"] > open_cluster["resolution"]
    assert globular["light_grasp"] > globular["field_of_view"]
    assert globular["resolution"] > globular["field_of_view"]


def test_q_target_differs_by_target_class_for_same_observer_profile() -> None:
    observer = ObserverCapability(
        light_grasp=0.9,
        resolution=0.75,
        field_of_view=0.25,
        magnification_range=0.85,
        tracking_or_goto=0.8,
        experience_level=0.6,
        practical_comfort=0.45,
    )

    projections = {
        target_class: project_observer_capability_for_target(observer, target_class)
        for target_class in (
            NsomTargetClass.PLANET,
            NsomTargetClass.MOON,
            NsomTargetClass.GALAXY,
            NsomTargetClass.DIFFUSE_NEBULA,
            NsomTargetClass.OPEN_CLUSTER,
            NsomTargetClass.GLOBULAR_CLUSTER,
        )
    }

    assert len({round(value, 6) for value in projections.values()}) > 3
    assert projections[NsomTargetClass.PLANET] > projections[NsomTargetClass.OPEN_CLUSTER]
    assert projections[NsomTargetClass.GALAXY] != pytest.approx(projections[NsomTargetClass.MOON])
    assert project_observer_capability_for_target(observer, None) == pytest.approx(
        observer.summary_for_planning()
    )


def test_planet_q_target_floor_preserves_observable_small_equipment_cases() -> None:
    observer = ObserverCapability(
        light_grasp=0.425,
        resolution=0.4,
        field_of_view=0.725,
        magnification_range=0.4,
        tracking_or_goto=0.4,
        experience_level=1.0,
        practical_comfort=0.7,
    )
    planet_weights = observer_capability_weight_profile_for_target(NsomTargetClass.PLANET)
    galaxy_weights = observer_capability_weight_profile_for_target(NsomTargetClass.GALAXY)
    raw_planet_q = observer.summary_for_planning(planet_weights)

    assert raw_planet_q < PLANET_OBSERVABLE_Q_TARGET_FLOOR
    assert project_observer_capability_for_target(observer, NsomTargetClass.PLANET) == pytest.approx(
        PLANET_OBSERVABLE_Q_TARGET_FLOOR
    )
    assert project_observer_capability_for_target(observer, NsomTargetClass.GALAXY) == pytest.approx(
        observer.summary_for_planning(galaxy_weights)
    )


def test_planet_q_target_floor_does_not_hide_genuinely_poor_capability() -> None:
    poor_observer = ObserverCapability(
        light_grasp=PLANET_OBSERVABLE_MIN_DIMENSION,
        resolution=0.2,
        field_of_view=0.8,
        magnification_range=0.2,
        tracking_or_goto=0.2,
        experience_level=0.6,
        practical_comfort=0.7,
    )
    planet_weights = observer_capability_weight_profile_for_target(NsomTargetClass.PLANET)
    raw_planet_q = poor_observer.summary_for_planning(planet_weights)

    assert raw_planet_q < PLANET_OBSERVABLE_Q_TARGET_FLOOR
    assert project_observer_capability_for_target(
        poor_observer,
        NsomTargetClass.PLANET,
    ) == pytest.approx(raw_planet_q)


def test_open_cluster_q_target_uses_fov_floor_for_usable_comfortable_fields() -> None:
    observer = ObserverCapability(
        light_grasp=0.6175,
        resolution=0.5925,
        field_of_view=0.4636363636363636,
        magnification_range=0.7484848484848485,
        tracking_or_goto=0.4,
        experience_level=1.0,
        practical_comfort=0.7,
    )
    weights = observer_capability_weight_profile_for_target(NsomTargetClass.OPEN_CLUSTER)
    raw_q = observer.summary_for_planning(weights)
    calibrated_q = project_observer_capability_for_target(
        observer,
        NsomTargetClass.OPEN_CLUSTER,
    )

    assert observer.field_of_view >= OPEN_CLUSTER_USABLE_FIELD_OF_VIEW_MIN_DIMENSION
    assert (
        observer.practical_comfort
        >= OPEN_CLUSTER_USABLE_PRACTICAL_COMFORT_MIN_DIMENSION
    )
    assert observer.field_of_view < OPEN_CLUSTER_USABLE_FIELD_OF_VIEW_FLOOR
    assert raw_q == pytest.approx(0.6160454545454546)
    assert calibrated_q == pytest.approx(0.6399690909090909)
    assert calibrated_q > raw_q


def test_open_cluster_q_target_keeps_genuinely_narrow_fields_limited() -> None:
    observer = ObserverCapability(
        light_grasp=0.85,
        resolution=0.825,
        field_of_view=0.2,
        magnification_range=0.8393939393939395,
        tracking_or_goto=0.8,
        experience_level=1.0,
        practical_comfort=0.7,
    )
    weights = observer_capability_weight_profile_for_target(NsomTargetClass.OPEN_CLUSTER)
    raw_q = observer.summary_for_planning(weights)

    assert observer.field_of_view < OPEN_CLUSTER_USABLE_FIELD_OF_VIEW_MIN_DIMENSION
    assert project_observer_capability_for_target(
        observer,
        NsomTargetClass.OPEN_CLUSTER,
    ) == pytest.approx(raw_q)


def test_open_cluster_q_target_fov_and_comfort_outweigh_resolution_and_magnification() -> None:
    base = ObserverCapability(
        light_grasp=0.6,
        resolution=0.6,
        field_of_view=0.6,
        magnification_range=0.6,
        tracking_or_goto=0.6,
        experience_level=0.7,
        practical_comfort=0.7,
    )

    def delta(**changes: float) -> float:
        changed = ObserverCapability(
            light_grasp=base.light_grasp,
            resolution=changes.get("resolution", base.resolution),
            field_of_view=changes.get("field_of_view", base.field_of_view),
            magnification_range=changes.get(
                "magnification_range",
                base.magnification_range,
            ),
            tracking_or_goto=base.tracking_or_goto,
            experience_level=base.experience_level,
            practical_comfort=changes.get("practical_comfort", base.practical_comfort),
        )
        return (
            project_observer_capability_for_target(changed, NsomTargetClass.OPEN_CLUSTER)
            - project_observer_capability_for_target(base, NsomTargetClass.OPEN_CLUSTER)
        )

    assert delta(field_of_view=0.8) > delta(resolution=0.8)
    assert delta(practical_comfort=0.9) > delta(magnification_range=0.8)


def test_open_cluster_q_target_changes_practical_value_without_mutating_observable_value() -> None:
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=78.0,
        effective_observability=EffectiveObservability.from_components(
            atmospheric_transparency=0.889162,
        ),
        target_class=NsomTargetClass.OPEN_CLUSTER,
    )
    observer = ObserverCapability(
        light_grasp=0.6175,
        resolution=0.5925,
        field_of_view=0.4636363636363636,
        magnification_range=0.7484848484848485,
        tracking_or_goto=0.4,
        experience_level=1.0,
        practical_comfort=0.7,
    )
    weights = observer_capability_weight_profile_for_target(NsomTargetClass.OPEN_CLUSTER)
    raw_q = observer.summary_for_planning(weights)
    calibrated_q = project_observer_capability_for_target(
        observer,
        NsomTargetClass.OPEN_CLUSTER,
    )

    raw_practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=observer,
        capability_summary=raw_q,
    )
    calibrated_practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=observer,
        capability_summary=calibrated_q,
    )

    assert calibrated_q > raw_q
    assert calibrated_practical.value > raw_practical.value
    assert calibrated_practical.observable_target_value is observable
    assert raw_practical.observable_target_value is observable
    assert observable.value == pytest.approx(69.354636)


def test_q_target_changes_practical_value_without_mutating_observable_value() -> None:
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=80.0,
        effective_observability=EffectiveObservability.from_components(),
        target_class=NsomTargetClass.GALAXY,
    )
    observer = ObserverCapability(
        light_grasp=0.9,
        resolution=0.75,
        field_of_view=0.25,
        magnification_range=0.85,
        tracking_or_goto=0.8,
        experience_level=0.6,
        practical_comfort=0.45,
    )

    galaxy_q = project_observer_capability_for_target(observer, NsomTargetClass.GALAXY)
    open_cluster_q = project_observer_capability_for_target(observer, NsomTargetClass.OPEN_CLUSTER)
    galaxy_practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=observer,
        capability_summary=galaxy_q,
    )
    open_cluster_practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=observer,
        capability_summary=open_cluster_q,
    )

    assert galaxy_q != pytest.approx(open_cluster_q)
    assert galaxy_practical.value != pytest.approx(open_cluster_practical.value)
    assert galaxy_practical.observable_target_value is observable
    assert open_cluster_practical.observable_target_value is observable
    assert observable.value == pytest.approx(80.0)


def test_q_target_dimension_sensitivity_is_target_specific() -> None:
    base = ObserverCapability(
        light_grasp=0.7,
        resolution=0.7,
        field_of_view=0.7,
        magnification_range=0.7,
        tracking_or_goto=0.7,
        experience_level=0.7,
        practical_comfort=0.7,
    )

    def delta(target_class: NsomTargetClass, **changes: float) -> float:
        changed = ObserverCapability(
            light_grasp=changes.get("light_grasp", base.light_grasp),
            resolution=changes.get("resolution", base.resolution),
            field_of_view=changes.get("field_of_view", base.field_of_view),
            magnification_range=changes.get("magnification_range", base.magnification_range),
            tracking_or_goto=changes.get("tracking_or_goto", base.tracking_or_goto),
            experience_level=base.experience_level,
            practical_comfort=changes.get("practical_comfort", base.practical_comfort),
        )
        return (
            project_observer_capability_for_target(changed, target_class)
            - project_observer_capability_for_target(base, target_class)
        )

    planet_fov = delta(NsomTargetClass.PLANET, field_of_view=0.9)
    planet_mag = delta(NsomTargetClass.PLANET, magnification_range=0.9)
    planet_tracking = delta(NsomTargetClass.PLANET, tracking_or_goto=0.9)
    galaxy_fov = delta(NsomTargetClass.GALAXY, field_of_view=0.9)
    galaxy_tracking = delta(NsomTargetClass.GALAXY, tracking_or_goto=0.9)
    diffuse_light = delta(NsomTargetClass.DIFFUSE_NEBULA, light_grasp=0.9)
    diffuse_tracking = delta(NsomTargetClass.DIFFUSE_NEBULA, tracking_or_goto=0.9)
    open_fov = delta(NsomTargetClass.OPEN_CLUSTER, field_of_view=0.9)
    open_mag = delta(NsomTargetClass.OPEN_CLUSTER, magnification_range=0.9)
    globular_aperture = delta(NsomTargetClass.GLOBULAR_CLUSTER, light_grasp=0.9, resolution=0.9)

    assert planet_mag > planet_fov
    assert planet_tracking > planet_fov
    assert galaxy_fov > galaxy_tracking
    assert diffuse_light > diffuse_tracking
    assert open_fov > open_mag
    assert globular_aperture > planet_fov


def test_observation_opportunity_combines_context_without_mutating_upstream_values() -> None:
    effective = EffectiveObservability.from_components(atmospheric_transparency=0.75)
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=90.0,
        effective_observability=effective,
    )
    observer = ObserverCapability(light_grasp=0.8, resolution=0.7)
    practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=observer,
        capability_summary=0.8,
    )
    confidence = RecommendationConfidence(
        weather_confidence=0.9,
        aod_confidence=0.8,
        notes=("fresh providers",),
    )
    session = SessionViability.from_components(
        weather_suitability=0.5,
        state="discouraged",
        reason="rain",
    )

    opportunity = ObservationOpportunity(
        practical_target_value=practical,
        observing_window_quality=0.9,
        chronology_fit=0.75,
        session=session,
        practical_constraints=0.8,
        confidence=confidence,
        context=("after transit",),
    )

    assert observable.value == pytest.approx(67.5)
    assert practical.value == pytest.approx(54.0)
    assert opportunity.practical_target_value is practical
    assert opportunity.confidence is confidence
    assert opportunity.session is session
    assert opportunity.context == ("after transit",)
    assert opportunity.value == pytest.approx(14.58)


def test_observation_opportunity_rejects_duplicate_session_viability_field() -> None:
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=70.0,
        effective_observability=EffectiveObservability.from_components(),
    )
    practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=ObserverCapability(),
    )

    with pytest.raises(TypeError):
        ObservationOpportunity(  # type: ignore[call-arg]
            practical_target_value=practical,
            session_viability=0.2,
            session=SessionViability.from_components(value=0.8),
        )


def test_recommendation_confidence_does_not_change_opportunity_score() -> None:
    effective = EffectiveObservability.from_components()
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=75.0,
        effective_observability=effective,
    )
    practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=ObserverCapability(),
        capability_summary=0.8,
    )

    low_confidence = RecommendationConfidence(
        weather_confidence=0.35,
        aod_confidence=0.4,
        openaq_confidence=0.25,
    )
    high_confidence = RecommendationConfidence(
        weather_confidence=0.95,
        aod_confidence=0.9,
        openaq_confidence=0.85,
    )

    low_confidence_opportunity = ObservationOpportunity(
        practical_target_value=practical,
        confidence=low_confidence,
    )
    high_confidence_opportunity = ObservationOpportunity(
        practical_target_value=practical,
        confidence=high_confidence,
    )

    assert low_confidence.value < high_confidence.value
    assert low_confidence_opportunity.value == high_confidence_opportunity.value
    assert low_confidence_opportunity.value == pytest.approx(60.0)


def test_core_model_exports_to_strict_json_compatible_shape() -> None:
    intrinsic = IntrinsicTargetQuality.from_score(
        float("nan"),
        object_id="messier-M13",
        name="M13",
        target_class=NsomTargetClass.GLOBULAR_CLUSTER,
    )
    environment = ObservationEnvironment.from_components(
        static_sky_background=float("inf"),
        notes=("strict-json",),
    )
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=intrinsic,
        effective_observability=EffectiveObservability.from_environment(environment),
    )
    practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=ObserverCapability(),
    )
    opportunity = ObservationOpportunity(
        practical_target_value=practical,
        session=SessionViability.from_components(value=0.8),
        confidence=RecommendationConfidence(viirs_confidence=1.0),
    )

    exported = nsom_to_json_compatible(
        {
            "intrinsic": intrinsic,
            "environment": environment,
            "opportunity": opportunity,
        }
    )

    json.dumps(exported, allow_nan=False)
    assert exported["intrinsic"]["value"] == 0.0
    assert exported["environment"]["static_sky_background"] == 0.0
    assert exported["opportunity"]["confidence"]["viirs_confidence"] == 1.0


def test_nsom_core_is_not_exposed_to_qml_or_runtime_qml_payloads() -> None:
    target = CelestialObject(
        id="messier-M13",
        name="M13",
        object_type="Ammasso globulare",
        image="",
        magnitude="5.8",
        distance="",
        max_altitude="70",
        direction="S",
        best_time="22:00",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="",
        score=82,
    )
    plan_item = NightPlanItem(
        time_label="22:00",
        object_id="messier-M13",
        name="M13",
        score=82,
        difficulty="Media",
        setup="Mak 127",
        direction="S",
        image="",
    )
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))

    assert "nsom" not in qml_text.lower()
    assert all("nsom" not in key.lower() for key in target.to_qml())
    assert all("nsom" not in key.lower() for key in plan_item.to_qml())
