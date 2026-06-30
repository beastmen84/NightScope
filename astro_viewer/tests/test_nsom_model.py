from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from astro_viewer.app.models.nsom import (
    IntrinsicTargetQuality,
    NSOM_TARGET_CLASS_PROFILES,
    EffectiveObservability,
    NsomDiagnosticSnapshot,
    NsomTargetDiagnostic,
    NsomTargetClass,
    NsomOwnershipBoundary,
    ObservableTargetValue,
    ObservationEnvironment,
    ObservationOpportunity,
    ObserverCapability,
    PracticalTargetValue,
    RecommendationConfidence,
    SessionViability,
    nsom_to_json_compatible,
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


def test_full_nsom_diagnostic_snapshot_exports_to_strict_json() -> None:
    intrinsic = IntrinsicTargetQuality.from_score(
        81,
        object_id="messier-M31",
        name="M31",
        target_class=NsomTargetClass.GALAXY,
        source_fields=(("raw_score", float("inf")),),
    )
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=intrinsic,
        effective_observability=EffectiveObservability.from_components(),
    )
    observer = ObserverCapability(light_grasp=0.8, resolution=0.7)
    practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=observer,
        capability_summary=0.75,
    )
    confidence = RecommendationConfidence(
        weather_confidence=0.9,
        aod_confidence=float("nan"),
        notes=("strict-json",),
    )
    opportunity = ObservationOpportunity(
        practical_target_value=practical,
        session=SessionViability.from_components(value=0.6),
        confidence=confidence,
    )
    diagnostic = NsomTargetDiagnostic(
        object_id="messier-M31",
        name="M31",
        source="planner",
        observable_target_value=observable,
        observer_capability=observer,
        practical_target_value=practical,
        observation_opportunity=opportunity,
        runtime_fields=(("score", float("-inf")),),
    )
    snapshot = NsomDiagnosticSnapshot(
        generated_at="2026-06-30T00:00:00+03:00",
        targets=(diagnostic,),
        confidence=confidence,
        metadata=(("schema", "nsom_diagnostic_snapshot"), ("invalid", float("inf"))),
        notes=("diagnostic_only",),
    )

    exported = nsom_to_json_compatible(snapshot)

    json.dumps(exported, allow_nan=False)
    assert exported["targets"][0]["runtime_fields"][0][1] is None
    assert exported["targets"][0]["observable_target_value"]["intrinsic_target"]["source_fields"][0][1] is None
    assert exported["confidence"]["aod_confidence"] is None
    assert exported["metadata"][1][1] is None


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
