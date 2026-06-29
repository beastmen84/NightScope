from __future__ import annotations

import pytest

from astro_viewer.app.models.nsom import (
    NSOM_TARGET_CLASS_PROFILES,
    EffectiveObservability,
    NsomTargetClass,
    ObservableTargetValue,
    ObservationOpportunity,
    ObserverCapabilityProfile,
    PracticalTargetValue,
    RecommendationConfidence,
)


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

    binocular_profile = ObserverCapabilityProfile(
        light_grasp=0.35,
        resolution=0.3,
        field_of_view=0.9,
        magnification_range=0.25,
        tracking_or_goto=0.1,
        experience_level=0.6,
        practical_comfort=0.8,
    )
    telescope_profile = ObserverCapabilityProfile(
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


def test_observer_capability_profile_is_structured_not_only_scalar() -> None:
    profile = ObserverCapabilityProfile(
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
    observer = ObserverCapabilityProfile(light_grasp=0.8, resolution=0.7)
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

    opportunity = ObservationOpportunity(
        practical_target_value=practical,
        observing_window_quality=0.9,
        chronology_fit=0.75,
        session_viability=0.5,
        practical_constraints=0.8,
        confidence=confidence,
        context=("after transit",),
    )

    assert observable.value == pytest.approx(67.5)
    assert practical.value == pytest.approx(54.0)
    assert opportunity.practical_target_value is practical
    assert opportunity.confidence is confidence
    assert opportunity.context == ("after transit",)
    assert opportunity.value == pytest.approx(14.58)


def test_recommendation_confidence_does_not_change_opportunity_score() -> None:
    effective = EffectiveObservability.from_components()
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=75.0,
        effective_observability=effective,
    )
    practical = PracticalTargetValue.from_observable(
        observable_target_value=observable,
        observer_capability=ObserverCapabilityProfile(),
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
