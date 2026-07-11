from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from astro_viewer.app.models.nsom import ObservableTargetValue
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.nsom_observation_environment import (
    NsomObservationEnvironmentService,
)
from astro_viewer.app.services.nsom_runtime_builders import (
    build_observation_opportunity,
    build_observer_capability_profile_from_recommendation,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionInputs,
)


def test_same_observable_value_produces_different_practical_values_by_observer() -> None:
    observable = _observable(score=80)
    binocular_profile = build_observer_capability_profile_from_recommendation(
        {"setupType": "binocular", "setupText": "Binocolo 10x50"}
    )
    telescope_profile = build_observer_capability_profile_from_recommendation(
        {
            "setupType": "telescope",
            "setupText": "Mak 127 + 16 mm",
            "telescopeName": "Mak 127",
            "setupOptions": [
                {"role": "Campo largo", "displayLabel": "24 mm"},
                {"role": "Alto ingrandimento", "displayLabel": "8 mm"},
            ],
        }
    )

    binocular_value = build_practical_target_value(observable, binocular_profile)
    telescope_value = build_practical_target_value(observable, telescope_profile)

    assert binocular_value.observable_target_value is observable
    assert telescope_value.observable_target_value is observable
    assert observable.value == pytest.approx(80.0)
    assert telescope_value.value > binocular_value.value


def test_confidence_changes_metadata_but_not_opportunity_score() -> None:
    observable = _observable(score=75)
    profile = build_observer_capability_profile_from_recommendation(
        {"setupType": "telescope"}
    )
    practical = build_practical_target_value(
        observable,
        profile,
        capability_summary=0.8,
    )
    low_confidence = build_recommendation_confidence(
        aod_result=SimpleNamespace(available=True, acquisition_date="2026-06-20"),
        local_atmosphere=SimpleNamespace(
            has_data=True,
            freshness_category="stale",
        ),
        today=date(2026, 6, 29),
    )
    high_confidence = build_recommendation_confidence(
        weather_summary=SimpleNamespace(score_value=88),
        aod_result=SimpleNamespace(available=True, acquisition_date="2026-06-28"),
        local_atmosphere=SimpleNamespace(
            has_data=True,
            freshness_category="current",
        ),
        viirs_available=True,
        today=date(2026, 6, 29),
    )

    low_opportunity = build_observation_opportunity(
        practical,
        confidence=low_confidence,
    )
    high_opportunity = build_observation_opportunity(
        practical,
        confidence=high_confidence,
    )

    assert low_confidence.value is not None
    assert high_confidence.value is not None
    assert low_confidence.value < high_confidence.value
    assert low_opportunity.value == high_opportunity.value
    assert low_opportunity.value == pytest.approx(60.0)


def test_opportunity_builder_does_not_mutate_source_values() -> None:
    observable = _observable(score=90)
    profile = build_observer_capability_profile_from_recommendation(
        {"setupType": "telescope"}
    )
    practical = build_practical_target_value(
        observable,
        profile,
        capability_summary=0.75,
    )
    confidence = build_recommendation_confidence(
        weather_summary=SimpleNamespace(score_value=70)
    )

    opportunity = build_observation_opportunity(
        practical,
        observing_window_quality=0.8,
        chronology_fit=0.9,
        session_viability=0.5,
        practical_constraints=0.7,
        confidence=confidence,
        context=("runtime_test",),
    )

    assert opportunity.practical_target_value is practical
    assert opportunity.confidence is confidence
    assert observable.value == pytest.approx(90.0)
    assert practical.value == pytest.approx(67.5)
    assert opportunity.session.value == pytest.approx(0.5)
    assert opportunity.value == pytest.approx(17.01)
    assert opportunity.context == ("runtime_test",)


def test_opportunity_builder_rejects_conflicting_session_inputs() -> None:
    observable = _observable(score=80)
    profile = build_observer_capability_profile_from_recommendation(
        {"setupType": "telescope"}
    )
    practical = build_practical_target_value(
        observable,
        profile,
        capability_summary=0.8,
    )

    with pytest.raises(ValueError, match="session_viability conflicts"):
        build_observation_opportunity(
            practical,
            session_viability=0.2,
            session=build_session_viability(value=0.8),
        )


def test_session_builder_uses_binary_weather_viability() -> None:
    usable = build_session_viability(
        weather_summary=SimpleNamespace(
            precipitation_probability=5,
            cloud_cover=20,
            score_value=80,
        )
    )
    blocked = build_session_viability(
        weather_summary=SimpleNamespace(
            precipitation_probability=70,
            cloud_cover=20,
            score_value=50,
        )
    )

    assert usable.value == 1.0
    assert usable.state == "usable"
    assert blocked.value == 0.0
    assert blocked.state == "blocked"


def _observable(*, score: int) -> ObservableTargetValue:
    return NsomObservationEnvironmentService().observable_target_value(
        _target(score=score),
        ObservationConditionInputs(),
    )


def _target(*, score: int) -> CelestialObject:
    return CelestialObject(
        id="m31",
        name="Andromeda Galaxy",
        object_type="Galaxy",
        image="",
        magnitude="3.4",
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="22:30",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="4 h",
        score=score,
        intrinsic_score=score,
    )
