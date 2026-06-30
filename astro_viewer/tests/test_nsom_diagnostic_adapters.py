from __future__ import annotations

import json
import math
from datetime import date
from types import SimpleNamespace

import pytest

from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    NsomDiagnosticSnapshot,
    NsomTargetDiagnostic,
    NsomTargetClass,
    ObservationOpportunity,
    nsom_to_json_compatible,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_effective_observability_from_breakdown,
    build_intrinsic_target_quality,
    build_observable_target_value,
    build_observation_environment,
    build_observation_opportunities_from_diagnostic_snapshot,
    build_observation_opportunity,
    build_observer_capability_profile_from_recommendation,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.observation_conditions_service import TargetConditionBreakdown


def _target(
    *,
    object_id: str = "m31",
    name: str = "Andromeda Galaxy",
    object_type: str = "Galaxy",
    score: int = 82,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="3.4",
        distance="",
        max_altitude="",
        direction="",
        best_time="22:30",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="",
        score=score,
        recommended_setup_type="",
        setup_options=[],
    )


def test_adapter_builds_effective_observability_from_condition_breakdown() -> None:
    breakdown = TargetConditionBreakdown(
        object_id="m31",
        base_score=80,
        moon_penalty=8,
        pollution_penalty=4,
        transparency_factor=0.9,
        adjusted_score=68,
        applied_components=("moon", "light_pollution"),
        diagnostic_notes=("moon:illumination=75",),
    )

    effective = build_effective_observability_from_breakdown(breakdown)

    assert effective.lunar_sky_background == pytest.approx(0.9)
    assert effective.static_sky_background == pytest.approx(0.95)
    assert effective.atmospheric_transparency == pytest.approx(0.9)
    assert effective.value == pytest.approx(0.7695)
    assert effective.notes == ("nsom:from_condition_breakdown", "moon:illumination=75")


def test_adapter_builds_universe_sky_and_session_core_from_runtime_data() -> None:
    target = _target(score=82)
    weather = WeatherSummary(
        score="Buono",
        score_value=72,
        explanation="",
        cloud_cover=20,
        precipitation_probability=5,
        wind_kmh=8,
        humidity=50,
        temperature_c=12.0,
        alert="",
    )
    sky_quality = SkyQuality(
        bortle_class=4,
        limiting_magnitude=6.1,
        sky_brightness=21.0,
        source="NASA Black Marble VNP46A3",
        description="",
        viirs_radiance=1.2,
    )

    intrinsic = build_intrinsic_target_quality(target)
    environment = build_observation_environment(
        weather_summary=weather,
        sky_quality=sky_quality,
        local_atmosphere=SimpleNamespace(source="OpenAQ", has_data=True),
        aod_result=SimpleNamespace(source="NASA AOD", available=True),
    )
    session = build_session_viability(weather_summary=weather)

    assert intrinsic.object_id == "m31"
    assert intrinsic.value == pytest.approx(82.0)
    assert intrinsic.target_class is NsomTargetClass.GALAXY
    assert environment.sky_quality_source == "NASA Black Marble VNP46A3"
    assert "weather_score=72" in environment.notes
    assert session.value == pytest.approx(0.72)
    assert session.state == "usable"


def test_adapter_builds_observable_target_value_from_existing_score_and_neutral_observability() -> None:
    target = _target(score=82)

    observable = build_observable_target_value(target, EffectiveObservability.from_components())

    assert observable.intrinsic_target_quality == pytest.approx(82.0)
    assert observable.intrinsic_target is not None
    assert observable.intrinsic_target.object_id == "m31"
    assert observable.effective_observability.value == pytest.approx(1.0)
    assert observable.value == pytest.approx(82.0)
    assert observable.target_class is NsomTargetClass.GALAXY


def test_same_observable_target_value_produces_different_practical_values_by_observer() -> None:
    observable = build_observable_target_value(_target(score=80), EffectiveObservability.from_components())
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
    assert binocular_value.value != telescope_value.value
    assert telescope_value.value > binocular_value.value


def test_confidence_adapter_changes_confidence_but_not_opportunity_score() -> None:
    observable = build_observable_target_value(_target(score=75), EffectiveObservability.from_components())
    profile = build_observer_capability_profile_from_recommendation({"setupType": "telescope"})
    practical = build_practical_target_value(observable, profile, capability_summary=0.8)
    low_confidence = build_recommendation_confidence(
        aod_result=SimpleNamespace(available=True, acquisition_date="2026-06-20"),
        local_atmosphere=SimpleNamespace(has_data=True, freshness_category="stale"),
        today=date(2026, 6, 29),
    )
    high_confidence = build_recommendation_confidence(
        weather_summary=SimpleNamespace(score_value=88),
        aod_result=SimpleNamespace(available=True, acquisition_date="2026-06-28"),
        local_atmosphere=SimpleNamespace(has_data=True, freshness_category="current"),
        viirs_available=True,
        today=date(2026, 6, 29),
    )

    low_opportunity = build_observation_opportunity(practical, confidence=low_confidence)
    high_opportunity = build_observation_opportunity(practical, confidence=high_confidence)

    assert low_confidence.value is not None
    assert high_confidence.value is not None
    assert low_confidence.value < high_confidence.value
    assert low_opportunity.value == high_opportunity.value
    assert low_opportunity.value == pytest.approx(60.0)


def test_opportunity_adapter_does_not_mutate_source_values() -> None:
    observable = build_observable_target_value(_target(score=90), EffectiveObservability.from_components())
    profile = build_observer_capability_profile_from_recommendation({"setupType": "telescope"})
    practical = build_practical_target_value(observable, profile, capability_summary=0.75)
    confidence = build_recommendation_confidence(weather_summary=SimpleNamespace(score_value=70))

    opportunity = build_observation_opportunity(
        practical,
        observing_window_quality=0.8,
        chronology_fit=0.9,
        session_viability=0.5,
        practical_constraints=0.7,
        confidence=confidence,
        context=("diagnostic",),
    )

    assert opportunity.practical_target_value is practical
    assert opportunity.confidence is confidence
    assert observable.value == pytest.approx(90.0)
    assert practical.value == pytest.approx(67.5)
    assert opportunity.session.value == pytest.approx(0.5)
    assert opportunity.session_viability == pytest.approx(0.5)
    assert opportunity.value == pytest.approx(17.01)
    assert opportunity.context == ("diagnostic",)


def test_opportunity_adapter_rejects_conflicting_session_inputs() -> None:
    observable = build_observable_target_value(_target(score=80), EffectiveObservability.from_components())
    profile = build_observer_capability_profile_from_recommendation({"setupType": "telescope"})
    practical = build_practical_target_value(observable, profile, capability_summary=0.8)

    with pytest.raises(ValueError, match="session_viability conflicts"):
        build_observation_opportunity(
            practical,
            session_viability=0.2,
            session=build_session_viability(value=0.8),
        )


def test_adapter_sanitizes_non_finite_runtime_values() -> None:
    target = SimpleNamespace(
        id="malformed",
        name="Malformed Galaxy",
        object_type="Galaxy",
        score=float("inf"),
        magnitude=float("nan"),
        max_altitude="45",
        apparent_size="",
        visible=True,
    )

    intrinsic = build_intrinsic_target_quality(target)
    observable = build_observable_target_value(target)

    json.dumps(nsom_to_json_compatible(intrinsic), allow_nan=False)
    json.dumps(nsom_to_json_compatible(observable), allow_nan=False)
    assert intrinsic.value == pytest.approx(0.0)
    assert observable.value == pytest.approx(0.0)
    assert all(not (isinstance(value, float) and not math.isfinite(value)) for _, value in intrinsic.source_fields)


def test_diagnostic_snapshot_adapts_to_core_observation_opportunities() -> None:
    observable = build_observable_target_value(_target(score=88), EffectiveObservability.from_components())
    profile = build_observer_capability_profile_from_recommendation({"setupType": "telescope"})
    practical = build_practical_target_value(observable, profile, capability_summary=0.8)
    opportunity = build_observation_opportunity(
        practical,
        session=build_session_viability(value=0.75),
        confidence=build_recommendation_confidence(viirs_available=True),
        context=("diagnostic_snapshot",),
    )
    diagnostic = NsomTargetDiagnostic(
        object_id="m31",
        name="Andromeda Galaxy",
        source="planner",
        observable_target_value=observable,
        observer_capability=profile,
        practical_target_value=practical,
        observation_opportunity=opportunity,
    )
    snapshot = NsomDiagnosticSnapshot(
        generated_at="2026-06-29T00:00:00+00:00",
        targets=(diagnostic,),
    )

    opportunities = build_observation_opportunities_from_diagnostic_snapshot(snapshot)

    assert opportunities == (opportunity,)
    assert isinstance(opportunities[0], ObservationOpportunity)
    assert opportunities[0].practical_target_value.observable_target_value is observable
    assert opportunities[0].value == pytest.approx(52.8)


def test_adapters_do_not_mutate_existing_application_dto_or_qml_output() -> None:
    target = _target(score=77)
    before = target.to_qml()

    observable = build_observable_target_value(target)
    profile = build_observer_capability_profile_from_recommendation(target)
    practical = build_practical_target_value(observable, profile)
    build_observation_opportunity(
        practical,
        confidence=build_recommendation_confidence(weather_summary=SimpleNamespace(score_value=70)),
    )

    assert target.to_qml() == before
    assert "condition_flags" not in target.to_qml()
