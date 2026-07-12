from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import Mock

from PySide6.QtCore import QObject

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.models.equipment import Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonGeometrySummary, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.earthdata_credentials import EarthdataCredentialState
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.nasa_aod_provider import NasaAodResult
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_observation_environment import (
    NsomObservationEnvironmentService,
)
from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    MoonGeometryConditionInput,
    ObservationConditionInputs,
    ObservationConditionsService,
    ParticulateConditionInput,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.services.openaq_atmosphere_service import LocalAtmosphere
from astro_viewer.app.services.openaq_credentials import OpenAQCredentialState
from astro_viewer.app.services.refresh_lifecycle import RefreshDomain, RefreshManager
from astro_viewer.app.viewmodels.app_controller import AppController


def _moon_adjusted_score(target: CelestialObject, moon: MoonSummary | None) -> int:
    return ObservationConditionsService().moon_adjusted_score(target, moon).adjusted_score


def _moon_penalty(target: CelestialObject, moon: MoonSummary | None) -> float:
    return ObservationConditionsService().moon_penalty(target, moon)


def test_moon_adjustment_matches_existing_planner_formula_for_target_types() -> None:
    service = ObservationConditionsService()
    moon = _moon("82%")
    targets = [
        _target("mars", "Marte", "Pianeta", 78),
        _target("m31", "M31", "Galassia", 78),
        _target("m42", "M42", "Nebula", 78),
        _target("m13", "M13", "Globular Cluster", 78),
        _target("m45", "M45", "Open Cluster", 78),
    ]

    for target in targets:
        breakdown = service.moon_adjusted_score(target, moon)

        assert breakdown.adjusted_score == _moon_adjusted_score(target, moon)
        assert service.apply_moon_adjustment(target, moon).target.score == breakdown.adjusted_score
        if target.object_type == "Pianeta":
            assert breakdown.applied_components == ()
            assert breakdown.moon_penalty == 0.0
        else:
            assert breakdown.applied_components == ("moon",)
            assert breakdown.moon_penalty > 0.0


def test_condition_target_neutral_breakdown_uses_identity_placeholders() -> None:
    service = ObservationConditionsService()
    target = _target("m13", "M13", "Globular Cluster", 78)

    conditioned = service.condition_target(target)
    breakdown = conditioned.breakdown

    assert conditioned.target == target
    assert conditioned.original_target == target
    assert breakdown.object_id == target.id
    assert breakdown.base_score == target.score
    assert breakdown.adjusted_score == target.score
    assert breakdown.moon_penalty == 0.0
    assert breakdown.pollution_penalty == 0.0
    assert breakdown.weather_factor == 1.0
    assert breakdown.seeing_factor == 1.0
    assert breakdown.transparency_factor == 1.0
    assert breakdown.equipment_modifier == 0.0
    assert breakdown.aod_modifier == 0.0
    assert breakdown.pm25_modifier == 0.0
    assert breakdown.applied_components == ()
    assert "weather:identity_placeholder" in breakdown.diagnostic_notes
    assert "seeing:identity_placeholder" in breakdown.diagnostic_notes
    assert "transparency:identity_placeholder" in breakdown.diagnostic_notes
    assert "equipment:identity_placeholder" in breakdown.diagnostic_notes
    assert "aod:identity_placeholder" in breakdown.diagnostic_notes
    assert "pm25:identity_placeholder" in breakdown.diagnostic_notes
    assert "moon:not_requested" in breakdown.diagnostic_notes
    assert "light_pollution:not_requested" in breakdown.diagnostic_notes
    assert breakdown.already_adjusted_flags == ()


def test_moon_adjusted_score_diagnostics_include_illumination_when_applied() -> None:
    service = ObservationConditionsService()
    moon = _moon("86%")
    target = _target("m31", "M31", "Galaxy", 82)

    breakdown = service.moon_adjusted_score(target, moon)

    assert breakdown.adjusted_score == _moon_adjusted_score(target, moon)
    assert breakdown.applied_components == ("moon",)
    assert "moon:illumination=86" in breakdown.diagnostic_notes
    assert "light_pollution:not_requested" in breakdown.diagnostic_notes


def test_moon_adjusted_score_and_condition_target_have_consistent_moon_diagnostics() -> None:
    service = ObservationConditionsService()
    moon = _moon("86%")
    target = _target("m31", "M31", "Galaxy", 82)

    score_breakdown = service.moon_adjusted_score(target, moon)
    conditioned = service.condition_target(
        target,
        ObservationConditionInputs(moon=moon),
        apply_moon=True,
    )

    assert score_breakdown.adjusted_score == conditioned.breakdown.adjusted_score
    assert score_breakdown.moon_penalty == conditioned.breakdown.moon_penalty
    assert score_breakdown.applied_components == conditioned.breakdown.applied_components
    assert "moon:illumination=86" in score_breakdown.diagnostic_notes
    assert "moon:illumination=86" in conditioned.breakdown.diagnostic_notes


def test_aod_diagnostic_inputs_are_freshness_aware_and_score_neutral() -> None:
    service = ObservationConditionsService()
    target = _target("m13", "M13", "Globular Cluster", 78)

    for category in ("current", "recent", "stale", "historical"):
        conditioned = service.condition_target(
            target,
            ObservationConditionInputs(
                aod=AodConditionInput(
                    available=True,
                    freshness_category=category,
                    aod_550=0.18,
                    source="NASA MAIAC",
                    product="VNP19A2.002",
                    status="ok",
                    age_days=2.0,
                )
            ),
        )
        breakdown = conditioned.breakdown

        assert conditioned.target == target
        assert breakdown.adjusted_score == target.score
        assert breakdown.aod_modifier == 0.0
        assert breakdown.applied_components == ()
        assert f"aod:{category}" in breakdown.diagnostic_notes
        assert "aod:available" in breakdown.diagnostic_notes
        assert "aod:550=0.18" in breakdown.diagnostic_notes
        assert "aod:canonical_environment_only" in breakdown.diagnostic_notes
        assert "aerosol_scoring:no_policy_eligible_provider" in breakdown.diagnostic_notes
        assert "aerosol_scoring:score_neutral" in breakdown.diagnostic_notes


def test_particulate_diagnostic_inputs_are_freshness_aware_and_score_neutral() -> None:
    service = ObservationConditionsService()
    target = _target("m42", "M42", "Nebula", 82)

    for category in ("current", "recent", "stale", "historical"):
        conditioned = service.condition_target(
            target,
            ObservationConditionInputs(
                particulate=ParticulateConditionInput(
                    available=True,
                    freshness_category=category,
                    pm25=9.5,
                    pm10=22.0,
                    source="OpenAQ",
                    status="ok",
                    age_days=1.0,
                )
            ),
        )
        breakdown = conditioned.breakdown

        assert conditioned.target == target
        assert breakdown.adjusted_score == target.score
        assert breakdown.pm25_modifier == 0.0
        assert breakdown.applied_components == ()
        assert f"particulate:{category}" in breakdown.diagnostic_notes
        assert "particulate:available" in breakdown.diagnostic_notes
        assert "pm25=9.5" in breakdown.diagnostic_notes
        assert "pm10=22" in breakdown.diagnostic_notes
        assert "particulate:canonical_environment_only" in breakdown.diagnostic_notes
        assert "aerosol_scoring:no_policy_eligible_provider" in breakdown.diagnostic_notes
        assert "aerosol_scoring:score_neutral" in breakdown.diagnostic_notes


def test_unavailable_atmospheric_diagnostics_remain_score_neutral() -> None:
    service = ObservationConditionsService()
    target = _target("m31", "M31", "Galaxy", 82)

    conditioned = service.condition_target(
        target,
        ObservationConditionInputs(
            aod=AodConditionInput(available=False, freshness_category="unavailable", status="no_credentials"),
            particulate=ParticulateConditionInput(
                available=False,
                freshness_category="unavailable",
                status="no_measurements",
            ),
        ),
    )
    breakdown = conditioned.breakdown

    assert conditioned.target == target
    assert breakdown.adjusted_score == target.score
    assert breakdown.aod_modifier == 0.0
    assert breakdown.pm25_modifier == 0.0
    assert breakdown.applied_components == ()
    assert "aod:unavailable:no_credentials" in breakdown.diagnostic_notes
    assert "particulate:unavailable:no_measurements" in breakdown.diagnostic_notes
    assert "aod:canonical_environment_only" in breakdown.diagnostic_notes
    assert "particulate:canonical_environment_only" in breakdown.diagnostic_notes
    assert "aerosol_scoring:no_policy_eligible_provider" in breakdown.diagnostic_notes
    assert "aerosol_scoring:score_neutral" in breakdown.diagnostic_notes


def test_condition_inputs_prepare_runtime_aod_and_openaq_boundary() -> None:
    service = ObservationConditionsService()
    target = _target("m13", "M13", "Globular Cluster", 78)
    inputs = ObservationConditionInputs(
        aod=AodConditionInput(available=True, freshness_category="recent", aod_550=0.16),
        particulate=ParticulateConditionInput(available=True, freshness_category="current", pm25=7.0),
    )

    conditioned = service.condition_target(target, inputs)

    assert conditioned.target == target
    assert conditioned.breakdown.adjusted_score == target.score
    assert conditioned.breakdown.applied_components == ()
    assert conditioned.breakdown.aod_modifier == 0.0
    assert conditioned.breakdown.pm25_modifier == 0.0
    assert "aod:recent" in conditioned.breakdown.diagnostic_notes
    assert "particulate:current" in conditioned.breakdown.diagnostic_notes


def test_runtime_aod_and_particulate_diagnostics_include_status_source_and_values() -> None:
    service = ObservationConditionsService()
    target = _target("m13", "M13", "Globular Cluster", 78)
    inputs = ObservationConditionInputs(
        aod=AodConditionInput(
            available=True,
            freshness_category="current",
            aod_550=0.142,
            source="NASA Earthdata",
            product="VNP19A2.002",
            status="ok",
            age_days=1.0,
        ),
        particulate=ParticulateConditionInput(
            available=True,
            freshness_category="recent",
            pm25=12.5,
            pm10=31.0,
            source="OpenAQ Addis",
            status="ok",
            age_days=2.0,
        ),
    )

    conditioned = service.condition_target(target, inputs)
    notes = conditioned.breakdown.diagnostic_notes

    assert conditioned.target == target
    assert conditioned.breakdown.adjusted_score == target.score
    assert conditioned.breakdown.aod_modifier == 0.0
    assert conditioned.breakdown.pm25_modifier == 0.0
    assert "aod:status=ok" in notes
    assert "aod:source=NASA Earthdata" in notes
    assert "aod:product=VNP19A2.002" in notes
    assert "aod:value=0.142" in notes
    assert "particulate:status=ok" in notes
    assert "particulate:source=OpenAQ Addis" in notes
    assert "particulate:pm25=12.5" in notes
    assert "particulate:pm10=31" in notes


def test_atmospheric_diagnostic_inputs_do_not_change_adjusted_score() -> None:
    service = ObservationConditionsService()
    target = _target("m31", "M31", "Galaxy", 82)

    baseline = service.condition_target(target)
    with_atmosphere = service.condition_target(
        target,
        ObservationConditionInputs(
            aod=AodConditionInput(
                available=True,
                freshness_category="stale",
                aod_550=0.31,
                source="NASA Earthdata",
                product="MCD19A2.061",
                status="cache_hit",
                age_days=5.0,
            ),
            particulate=ParticulateConditionInput(
                available=True,
                freshness_category="stale",
                pm25=34.0,
                pm10=72.0,
                source="OpenAQ",
                status="ok",
                age_days=5.0,
            ),
        ),
    )

    assert with_atmosphere.target == baseline.target
    assert with_atmosphere.breakdown.adjusted_score == baseline.breakdown.adjusted_score
    assert with_atmosphere.breakdown.applied_components == ()
    assert with_atmosphere.breakdown.aod_modifier == 0.0
    assert with_atmosphere.breakdown.pm25_modifier == 0.0


def test_atmospheric_diagnostics_do_not_change_existing_moon_or_pollution_components() -> None:
    target = _target("m31", "M31", "Galaxy", 82)
    moon = _moon("86%")
    sky_quality = _sky_quality(bortle=8, radiance=120.0)
    service = ObservationConditionsService()

    conditioned = service.condition_target(
        target,
        ObservationConditionInputs(
            moon=moon,
            sky_quality=sky_quality,
            aod=AodConditionInput(available=True, freshness_category="current", aod_550=0.12),
            particulate=ParticulateConditionInput(available=True, freshness_category="current", pm25=8.0),
        ),
        apply_moon=True,
        apply_pollution=True,
    )
    breakdown = conditioned.breakdown
    moon_adjusted = _moon_adjusted_score(target, moon)
    expected_score = max(0, round(moon_adjusted - service.deep_sky_pollution_penalty(target, sky_quality)))

    assert breakdown.adjusted_score == expected_score
    assert conditioned.target.score == expected_score
    assert breakdown.applied_components == ("moon", "light_pollution")
    assert breakdown.aod_modifier == 0.0
    assert breakdown.pm25_modifier == 0.0
    assert "aod:canonical_environment_only" in breakdown.diagnostic_notes
    assert "particulate:canonical_environment_only" in breakdown.diagnostic_notes
    assert "aerosol_scoring:score_neutral" in breakdown.diagnostic_notes


def test_aod_freshness_weights_are_characterized() -> None:
    service = ObservationConditionsService()

    assert service.aod_freshness_weight(age_days=0.0) == 1.0
    assert service.aod_freshness_weight(age_days=3.0) == 1.0
    assert service.aod_freshness_weight(age_days=4.0) == 0.5
    assert service.aod_freshness_weight(age_days=7.0) == 0.5
    assert service.aod_freshness_weight(age_days=7.01) == 0.0
    assert service.aod_freshness_weight(freshness_category="current") == 1.0
    assert service.aod_freshness_weight(freshness_category="recent") == 1.0
    assert service.aod_freshness_weight(freshness_category="stale") == 0.5
    assert service.aod_freshness_weight(freshness_category="historical") == 0.0


def test_future_openaq_particulate_freshness_weights_are_characterized() -> None:
    service = ObservationConditionsService()

    assert service.particulate_freshness_weight(age_days=0.0) == 1.0
    assert service.particulate_freshness_weight(age_days=1.0) == 1.0
    assert service.particulate_freshness_weight(age_days=2.0) == 0.7
    assert service.particulate_freshness_weight(age_days=3.0) == 0.7
    assert service.particulate_freshness_weight(age_days=4.0) == 0.3
    assert service.particulate_freshness_weight(age_days=7.0) == 0.3
    assert service.particulate_freshness_weight(age_days=7.01) == 0.0
    assert service.particulate_freshness_weight(freshness_category="current") == 1.0
    assert service.particulate_freshness_weight(freshness_category="recent") == 0.7
    assert service.particulate_freshness_weight(freshness_category="stale") == 0.3
    assert service.particulate_freshness_weight(freshness_category="historical") == 0.0


def test_future_aerosol_target_sensitivity_order_and_caps_are_characterized() -> None:
    service = ObservationConditionsService()
    moon = service.atmospheric_sensitivity_profile(_target("moon", "Luna", "Satellite naturale", 90))
    planet = service.atmospheric_sensitivity_profile(_target("mars", "Marte", "Pianeta", 90))
    globular = service.atmospheric_sensitivity_profile(_target("m13", "M13", "Globular Cluster", 90))
    open_cluster = service.atmospheric_sensitivity_profile(_target("m45", "M45", "Open Cluster", 90))
    planetary = service.atmospheric_sensitivity_profile(_target("m57", "M57", "Planetary Nebula", 90))
    diffuse = service.atmospheric_sensitivity_profile(_target("m42", "M42", "Diffuse Nebula", 90))
    supernova_remnant = service.atmospheric_sensitivity_profile(
        _target("m1", "M1", "Supernova remnant", 90),
    )
    galaxy = service.atmospheric_sensitivity_profile(_target("m31", "M31", "Galaxy", 90))

    assert moon.target_class == "moon"
    assert planet.target_class == "planet"
    assert globular.target_class == "globular_cluster"
    assert open_cluster.target_class == "open_cluster"
    assert planetary.target_class == "planetary_nebula"
    assert diffuse.target_class == "diffuse_nebula"
    assert supernova_remnant.target_class == "diffuse_nebula"
    assert galaxy.target_class == "galaxy"

    assert galaxy.sensitivity > diffuse.sensitivity > open_cluster.sensitivity > planet.sensitivity > moon.sensitivity
    assert planetary.sensitivity > planet.sensitivity
    assert globular.sensitivity > planet.sensitivity
    assert moon.penalty_cap == 1.0
    assert planet.penalty_cap == 3.0
    assert open_cluster.penalty_cap == 3.0
    assert globular.penalty_cap == 4.0
    assert planetary.penalty_cap == 5.0
    assert diffuse.penalty_cap == 8.0
    assert supernova_remnant.penalty_cap == 8.0
    assert galaxy.penalty_cap == 12.0


def test_supernova_remnant_uses_nebula_pollution_and_moon_rules() -> None:
    service = ObservationConditionsService()
    remnant = _target("m1", "M1", "Supernova remnant", 80)
    nebula = _target("nebula", "Nebula", "Nebula", 80)
    sky_quality = _sky_quality(7, 80.0)
    moon = _moon("82%")

    assert service.deep_sky_pollution_penalty(remnant, sky_quality) == service.deep_sky_pollution_penalty(
        nebula,
        sky_quality,
    )
    assert service.moon_penalty(remnant, moon) == service.moon_penalty(nebula, moon)


def test_future_aod_dominates_pm_and_pm_is_fallback() -> None:
    service = ObservationConditionsService()
    aod = _scoring_aod(aod_550=0.22)
    historical_aod = _scoring_aod(aod_550=0.22)
    historical_aod = replace(historical_aod, freshness_category="historical", age_days=9.0)
    missing_qa_aod = _scoring_aod(aod_550=0.22, qa_raw=None)
    particulate = _scoring_pm(pm25=28.0, pm10=64.0)
    context_particulate = _scoring_pm(pm25=28.0, pm10=64.0, distance_km=35.0)

    assert service.aerosol_primary_source(aod, particulate) == "aod"
    assert service.aerosol_primary_source(historical_aod, particulate) == "particulate"
    assert service.aerosol_primary_source(missing_qa_aod, particulate) == "particulate"
    assert service.aerosol_primary_source(None, particulate) == "particulate"
    assert service.aerosol_primary_source(None, context_particulate) == "none"
    assert service.aerosol_primary_source(historical_aod, None) == "none"


def test_aerosol_modifier_is_canonical_and_display_score_remains_unchanged() -> None:
    service = ObservationConditionsService()
    target = _target("m31", "M31", "Galaxy", 82)
    aod = _scoring_aod(aod_550=0.44)
    particulate = ParticulateConditionInput(
        available=True,
        freshness_category="current",
        pm25=40.0,
        pm10=90.0,
        age_days=0.5,
        distance_km=5.0,
    )

    conditioned = service.condition_target(
        target,
        ObservationConditionInputs(aod=aod, particulate=particulate),
    )

    assert service.aerosol_modifier(target, aod, particulate) == -7.38
    assert conditioned.target == target
    assert conditioned.breakdown.adjusted_score == 82
    assert conditioned.breakdown.aod_modifier == 0.0
    assert conditioned.breakdown.pm25_modifier == 0.0
    assert conditioned.breakdown.applied_components == ()
    assert "aerosol:canonical_environment_only" in conditioned.breakdown.diagnostic_notes
    assert target.score == 82


def test_canonical_environment_uses_aod_when_policy_eligible() -> None:
    service = ObservationConditionsService()
    target = _target("m31", "M31", "Galaxy", 82)
    aod = _scoring_aod(aod_550=0.44)
    particulate = _scoring_pm(pm25=55.0, pm10=120.0)
    breakdown = service.aerosol_scoring_breakdown(target, aod, particulate)
    conditioned = service.condition_target(
        target,
        ObservationConditionInputs(
            aod=aod,
            particulate=particulate,
        ),
    )
    environment = NsomObservationEnvironmentService().environment(
        target,
        ObservationConditionInputs(
            aod=aod,
            particulate=particulate,
        ),
    )

    assert breakdown.primary_source == "aod"
    assert breakdown.severity == 0.75
    assert breakdown.source_weight == 1.0
    assert breakdown.max_transparency_loss == 0.12
    assert breakdown.transparency_loss == 0.09
    assert breakdown.penalty_points == 7.38
    assert breakdown.score_modifier == -7.38
    assert conditioned.breakdown.aod_modifier == 0.0
    assert conditioned.breakdown.pm25_modifier == 0.0
    assert conditioned.breakdown.adjusted_score == 82
    assert conditioned.breakdown.applied_components == ()
    assert "particulate" not in conditioned.breakdown.applied_components
    assert "aod:canonical_environment_only" in conditioned.breakdown.diagnostic_notes
    assert "aerosol_scoring:source=aod" in conditioned.breakdown.diagnostic_notes
    assert "aerosol_scoring:target_score_scaled_transparency_loss" in conditioned.breakdown.diagnostic_notes
    assert environment.atmospheric_transparency == 0.91
    assert target.score == 82


def test_canonical_environment_uses_local_pm_fallback_when_aod_rejected() -> None:
    service = ObservationConditionsService()
    target = _target("m42", "M42", "Diffuse Nebula", 82)
    rejected_aod = _scoring_aod(aod_550=0.44, uncertainty=0.24)
    particulate = _scoring_pm(pm25=55.0, pm10=120.0)
    breakdown = service.aerosol_scoring_breakdown(
        target,
        rejected_aod,
        particulate,
    )
    conditioned = service.condition_target(
        target,
        ObservationConditionInputs(
            aod=rejected_aod,
            particulate=particulate,
        ),
    )
    environment = NsomObservationEnvironmentService().environment(
        target,
        ObservationConditionInputs(
            aod=rejected_aod,
            particulate=particulate,
        ),
    )

    assert breakdown.primary_source == "particulate"
    assert breakdown.severity == 0.75
    assert breakdown.source_weight == 0.6
    assert breakdown.max_transparency_loss == 0.08
    assert breakdown.transparency_loss == 0.0306
    assert breakdown.score_modifier == -2.509
    assert conditioned.breakdown.aod_modifier == 0.0
    assert conditioned.breakdown.pm25_modifier == 0.0
    assert conditioned.breakdown.adjusted_score == 82
    assert conditioned.breakdown.applied_components == ()
    assert "aerosol_scoring:source=particulate" in conditioned.breakdown.diagnostic_notes
    assert environment.atmospheric_transparency == 0.9694


def test_aerosol_scoring_respects_target_class_caps_and_protection() -> None:
    service = ObservationConditionsService()
    aod = _scoring_aod(aod_550=0.75)
    particulate = _scoring_pm(pm25=70.0, pm10=180.0)

    galaxy = service.aerosol_scoring_breakdown(
        _target("m31", "M31", "Galaxy", 82),
        aod,
        particulate,
    )
    diffuse = service.aerosol_scoring_breakdown(
        _target("m42", "M42", "Diffuse Nebula", 82),
        aod,
        particulate,
    )
    planet = service.aerosol_scoring_breakdown(
        _target("mars", "Marte", "Pianeta", 82),
        aod,
        particulate,
    )
    moon = service.aerosol_scoring_breakdown(
        _target("moon", "Luna", "Satellite naturale", 82),
        aod,
        particulate,
    )

    assert galaxy.score_modifier == -9.84
    assert diffuse.score_modifier == -5.576
    assert planet.score_modifier == -0.369
    assert moon.score_modifier == -0.041
    assert galaxy.atmospheric_transparency_factor == 0.88
    assert diffuse.atmospheric_transparency_factor == 0.932
    assert planet.atmospheric_transparency_factor == 0.9955
    assert moon.atmospheric_transparency_factor == 0.9995
    assert galaxy.penalty_points > diffuse.penalty_points > planet.penalty_points > moon.penalty_points


def test_aerosol_scoring_uses_transparency_loss_shape() -> None:
    service = ObservationConditionsService()
    target = _target("m31", "M31", "Galaxy", 82)
    aod = _scoring_aod(aod_550=0.75)

    breakdown = service.aerosol_scoring_breakdown(target, aod, None)

    assert breakdown.max_transparency_loss == 0.12
    assert breakdown.transparency_loss == 0.12
    assert breakdown.atmospheric_transparency_factor == 0.88
    assert breakdown.penalty_points == round(target.score * breakdown.transparency_loss, 3)
    assert breakdown.score_modifier == -9.84
    assert "target_score * transparency_loss" in breakdown.formula


def test_aerosol_scoring_rejects_non_policy_eligible_sources() -> None:
    service = ObservationConditionsService()
    target = _target("m31", "M31", "Galaxy", 82)
    missing_qa = _scoring_aod(aod_550=0.44, qa_raw=None)
    context_only_pm = _scoring_pm(pm25=55.0, pm10=120.0, distance_km=35.0)

    breakdown = service.aerosol_scoring_breakdown(
        target,
        missing_qa,
        context_only_pm,
    )
    conditioned = service.condition_target(
        target,
        ObservationConditionInputs(
            aod=missing_qa,
            particulate=context_only_pm,
        ),
    )

    assert breakdown.primary_source == "none"
    assert breakdown.score_modifier == 0.0
    assert conditioned.target == target
    assert conditioned.breakdown.adjusted_score == target.score
    assert conditioned.breakdown.applied_components == ()
    assert "aerosol_scoring:no_policy_eligible_provider" in conditioned.breakdown.diagnostic_notes
    assert "aerosol_scoring:score_neutral" in conditioned.breakdown.diagnostic_notes


def test_aerosol_scoring_confidence_metadata_does_not_scale_score() -> None:
    service = ObservationConditionsService()
    target = _target("m31", "M31", "Galaxy", 82)
    viirs = _scoring_aod(aod_550=0.44, product="VNP19A2.002")
    modis = _scoring_aod(aod_550=0.44, product="MCD19A2.061")

    viirs_breakdown = service.aerosol_scoring_breakdown(target, viirs, None)
    modis_breakdown = service.aerosol_scoring_breakdown(target, modis, None)

    assert viirs_breakdown.score_modifier == modis_breakdown.score_modifier == -7.38


def test_aerosol_severity_steps_are_explicit() -> None:
    service = ObservationConditionsService()

    assert service.aod_severity(0.10) == 0.0
    assert service.aod_severity(0.20) == 0.25
    assert service.aod_severity(0.35) == 0.50
    assert service.aod_severity(0.60) == 0.75
    assert service.aod_severity(0.61) == 1.0
    assert service.particulate_severity(5.0, 20.0) == 0.0
    assert service.particulate_severity(15.0, 50.0) == 0.25
    assert service.particulate_severity(35.0, 100.0) == 0.50
    assert service.particulate_severity(55.0, 150.0) == 0.75
    assert service.particulate_severity(56.0, 151.0) == 1.0


def test_moon_geometry_fields_are_represented_diagnostically() -> None:
    service = ObservationConditionsService()
    target = _target("m31", "M31", "Galaxy", 82)
    geometry = MoonGeometryConditionInput(
        moon_altitude_deg=45.0,
        moon_target_separation_deg=12.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
        moon_set_before_target_window=False,
    )

    conditioned = service.condition_target(target, ObservationConditionInputs(moon_geometry=geometry))
    notes = conditioned.breakdown.diagnostic_notes

    assert conditioned.target == target
    assert conditioned.breakdown.adjusted_score == target.score
    assert conditioned.breakdown.moon_geometry_factor == 1.35
    assert "moon_geometry:available" in notes
    assert "moon_geometry:altitude=45" in notes
    assert "moon_geometry:separation=12" in notes
    assert "moon_geometry:above_horizon=true" in notes
    assert "moon_geometry:visible_during_window=true" in notes
    assert "moon_geometry:set_before_window=false" in notes
    assert "moon_geometry:factor=1.35" in notes
    assert "moon_geometry:canonical_environment_only" in notes


def test_moon_geometry_altitude_and_timing_factors_are_characterized() -> None:
    service = ObservationConditionsService()
    below_horizon = MoonGeometryConditionInput(
        moon_altitude_deg=-4.0,
        moon_above_horizon=False,
        moon_visible_during_target_window=False,
    )
    low_altitude = MoonGeometryConditionInput(
        moon_altitude_deg=8.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
    )
    high_altitude = MoonGeometryConditionInput(
        moon_altitude_deg=45.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
    )
    set_before_window = MoonGeometryConditionInput(
        moon_altitude_deg=45.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=False,
        moon_set_before_target_window=True,
    )

    assert service.moon_altitude_factor(below_horizon) == 0.0
    assert service.moon_altitude_factor(low_altitude) == 0.25
    assert service.moon_altitude_factor(high_altitude) == 1.0
    assert service.moon_geometry_factor(below_horizon) < service.moon_geometry_factor(high_altitude)
    assert service.moon_geometry_factor(set_before_window) == 0.0


def test_moon_geometry_separation_factors_are_characterized() -> None:
    service = ObservationConditionsService()
    close = MoonGeometryConditionInput(moon_target_separation_deg=12.0)
    mid = MoonGeometryConditionInput(moon_target_separation_deg=55.0)
    far = MoonGeometryConditionInput(moon_target_separation_deg=125.0)

    assert service.moon_separation_factor(close) == 1.35
    assert service.moon_separation_factor(mid) == 0.65
    assert service.moon_separation_factor(far) == 0.35
    assert service.moon_separation_factor(close) > service.moon_separation_factor(far)


def test_app_controller_builds_local_moon_geometry_diagnostic_input_score_neutrally() -> None:
    controller = AppController.__new__(AppController)
    controller._location = ObserverLocation("Test", "Earth", 0.0, 0.0, "UTC")
    controller._moon = _moon("86%")
    controller._sky_quality = None
    controller._nasa_aod_result = NasaAodResult.no_location()
    controller._local_atmosphere = LocalAtmosphere.not_configured()
    controller._moon_geometry_condition_cache = {}
    controller._astronomy_engine = _MoonGeometryEngine(
        MoonGeometrySummary(
            object_id="m31",
            moon_altitude_deg=37.0,
            moon_target_separation_deg=18.0,
            moon_above_horizon=True,
            moon_visible_during_target_window=True,
            moon_set_before_target_window=False,
            sample_count=3,
            sampled_at="2026-07-09T22:00:00+00:00",
            sample_times=("2026-07-09T18:00:00+00:00",),
        )
    )
    service = ObservationConditionsService()
    target = _target("m31", "M31", "Galaxy", 82)

    inputs = controller._build_observation_condition_inputs(include_sky_quality=False, target=target)
    conditioned = service.condition_target(target, inputs, apply_moon=True)

    assert inputs.moon_geometry == MoonGeometryConditionInput(
        moon_altitude_deg=37.0,
        moon_target_separation_deg=18.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
        moon_set_before_target_window=False,
    )
    assert conditioned.breakdown.moon_geometry_factor > 1.0
    assert conditioned.breakdown.adjusted_score == _moon_adjusted_score(target, controller._moon)
    assert conditioned.breakdown.applied_components == ("moon",)
    assert "moon_geometry:canonical_environment_only" in conditioned.breakdown.diagnostic_notes
    assert controller._astronomy_engine.calls == 1


def test_app_controller_builds_planner_moon_geometry_inputs() -> None:
    controller = AppController.__new__(AppController)
    controller._location = ObserverLocation("Test", "Earth", 0.0, 0.0, "UTC")
    controller._moon_geometry_condition_cache = {}
    controller._astronomy_engine = _MoonGeometryEngine(
        MoonGeometrySummary(
            object_id="m31",
            moon_altitude_deg=37.0,
            moon_target_separation_deg=18.0,
            moon_above_horizon=True,
            moon_visible_during_target_window=True,
            moon_set_before_target_window=False,
        )
    )
    target = _target("m31", "M31", "Galaxy", 82)

    geometry_by_id = controller._planner_moon_geometry_inputs([target])

    assert geometry_by_id == {
        "m31": MoonGeometryConditionInput(
            moon_altitude_deg=37.0,
            moon_target_separation_deg=18.0,
            moon_above_horizon=True,
            moon_visible_during_target_window=True,
            moon_set_before_target_window=False,
        )
    }
    assert controller._astronomy_engine.calls == 1


def test_app_controller_builds_planner_moon_geometry_inputs_in_one_batch() -> None:
    controller = AppController.__new__(AppController)
    controller._night_planner_service = NightPlannerService()
    controller._location = ObserverLocation("Test", "Earth", 0.0, 0.0, "UTC")
    controller._moon_geometry_condition_cache = {}
    first = _target("m31", "M31", "Galaxy", 82)
    second = _target("m42", "M42", "Nebula", 88)
    controller._astronomy_engine = _BatchMoonGeometryEngine()

    geometry_by_id = controller._planner_moon_geometry_inputs([first, second])

    assert controller._astronomy_engine.batch_calls == 1
    assert controller._astronomy_engine.scalar_calls == 0
    assert set(geometry_by_id) == {"m31", "m42"}
    assert geometry_by_id["m31"].moon_target_separation_deg == 71.0
    assert geometry_by_id["m42"].moon_target_separation_deg == 72.0


def test_app_controller_default_planner_builds_moon_geometry_inputs() -> None:
    controller = AppController.__new__(AppController)
    controller._night_planner_service = NightPlannerService()
    controller._location = ObserverLocation("Test", "Earth", 0.0, 0.0, "UTC")
    controller._moon_geometry_condition_cache = {}
    controller._astronomy_engine = _MoonGeometryEngine(
        MoonGeometrySummary(
            object_id="m31",
            moon_altitude_deg=37.0,
            moon_target_separation_deg=18.0,
            moon_above_horizon=True,
            moon_visible_during_target_window=True,
            moon_set_before_target_window=False,
        )
    )
    target = _target("m31", "M31", "Galaxy", 82)

    geometry_by_id = controller._planner_moon_geometry_inputs([target])

    assert geometry_by_id["m31"].moon_target_separation_deg == 18.0
    assert controller._astronomy_engine.calls == 1


def test_app_controller_builds_runtime_condition_diagnostic_inputs() -> None:
    controller = AppController.__new__(AppController)
    controller._moon = _moon("42%")
    controller._sky_quality = _sky_quality(bortle=5, radiance=4.0)
    controller._nasa_aod_result = NasaAodResult(
        available=True,
        status="cache_hit",
        message="Dati NASA AOD disponibili.",
        provider="NASA Earthdata",
        product="VNP19A2.002",
        aod_550=0.173,
        uncertainty=0.041,
        qa_raw=1089,
        method="local_neighborhood",
        local_valid_pixel_count=7,
        acquisition_date=(datetime.now().date() - timedelta(days=5)).isoformat(),
    )
    controller._local_atmosphere = LocalAtmosphere(
        visible=True,
        has_data=True,
        message="",
        pm25="12.5 µg/m³",
        pm10="31 µg/m³",
        clarity="Discreta",
        source="Addis Ababa Central",
        freshness="Aggiornato 2 giorni fa",
        freshness_category="recent",
        source_distance_km=1.6,
    )

    inputs = controller._build_observation_condition_inputs()

    assert inputs.moon == controller._moon
    assert inputs.sky_quality == controller._sky_quality
    assert inputs.aod == AodConditionInput(
        available=True,
        freshness_category="stale",
        aod_550=0.173,
        source="NASA Earthdata",
        product="VNP19A2.002",
        status="cache_hit",
        age_days=5.0,
        uncertainty=0.041,
        qa_raw=1089,
        method="local_neighborhood",
        local_valid_pixel_count=7,
    )
    assert inputs.particulate == ParticulateConditionInput(
        available=True,
        freshness_category="recent",
        pm25=12.5,
        pm10=31.0,
        source="Addis Ababa Central",
        status="ok",
        age_days=2.0,
        distance_km=1.6,
    )


def test_app_controller_maps_stale_openaq_has_data_diagnostically() -> None:
    controller = AppController.__new__(AppController)
    controller._moon = None
    controller._sky_quality = None
    controller._nasa_aod_result = NasaAodResult.no_credentials()
    controller._local_atmosphere = LocalAtmosphere(
        visible=True,
        has_data=True,
        message="",
        pm25="34 µg/m³",
        pm10="72 µg/m³",
        clarity="Velata",
        source="OpenAQ",
        freshness="Aggiornato 5 giorni fa",
        freshness_category="stale",
        freshness_warning=True,
    )

    inputs = controller._build_observation_condition_inputs()

    assert inputs.aod is None
    assert inputs.particulate == ParticulateConditionInput(
        available=True,
        freshness_category="stale",
        pm25=34.0,
        pm10=72.0,
        source="OpenAQ",
        status="ok",
        age_days=5.0,
    )


def test_app_controller_stale_openaq_runtime_input_remains_score_neutral() -> None:
    controller = AppController.__new__(AppController)
    controller._moon = None
    controller._sky_quality = None
    controller._nasa_aod_result = NasaAodResult.no_credentials()
    controller._local_atmosphere = LocalAtmosphere(
        visible=True,
        has_data=True,
        message="",
        pm25="34 µg/m³",
        pm10="72 µg/m³",
        clarity="Velata",
        source="OpenAQ",
        freshness="Aggiornato 5 giorni fa",
        freshness_category="stale",
        freshness_warning=True,
    )
    service = ObservationConditionsService()
    target = _target("m42", "M42", "Nebula", 82)

    conditioned = service.condition_target(target, controller._build_observation_condition_inputs())

    assert conditioned.target == target
    assert conditioned.breakdown.adjusted_score == target.score
    assert conditioned.breakdown.pm25_modifier == 0.0
    assert conditioned.breakdown.applied_components == ()
    assert "particulate:stale" in conditioned.breakdown.diagnostic_notes
    assert "particulate:canonical_environment_only" in conditioned.breakdown.diagnostic_notes
    assert "aerosol_scoring:no_policy_eligible_provider" in conditioned.breakdown.diagnostic_notes
    assert "aerosol_scoring:score_neutral" in conditioned.breakdown.diagnostic_notes


def test_app_controller_skips_failed_unavailable_or_historical_diagnostic_inputs() -> None:
    controller = AppController.__new__(AppController)
    controller._moon = None
    controller._sky_quality = None
    controller._nasa_aod_result = NasaAodResult.failure("auth_error", "Autenticazione non riuscita.")
    controller._local_atmosphere = LocalAtmosphere.historical(
        "OpenAQ",
        "OpenAQ · Ultima misura 38 giorni fa",
        "Ultima misura 38 giorni fa",
        "2026-05-21",
    )

    inputs = controller._build_observation_condition_inputs()

    assert inputs.aod is None
    assert inputs.particulate is None


def test_app_controller_skips_failed_and_unavailable_openaq_runtime_input() -> None:
    controller = AppController.__new__(AppController)
    controller._moon = None
    controller._sky_quality = None
    controller._nasa_aod_result = NasaAodResult.no_credentials()

    for atmosphere in (
        LocalAtmosphere.failure("Dati OpenAQ non disponibili al momento."),
        LocalAtmosphere.no_data(),
        LocalAtmosphere.not_configured(),
    ):
        controller._local_atmosphere = atmosphere

        inputs = controller._build_observation_condition_inputs()

        assert inputs.aod is None
        assert inputs.particulate is None


def test_app_controller_skips_historical_aod_runtime_input() -> None:
    controller = AppController.__new__(AppController)
    controller._moon = None
    controller._sky_quality = None
    controller._nasa_aod_result = NasaAodResult(
        available=True,
        status="ok",
        message="Dati NASA AOD disponibili.",
        product="VNP19A2.002",
        aod_550=0.24,
        acquisition_date=(datetime.now().date() - timedelta(days=9)).isoformat(),
    )
    controller._local_atmosphere = LocalAtmosphere.not_configured()

    inputs = controller._build_observation_condition_inputs()

    assert inputs.aod is None
    assert inputs.particulate is None


def test_app_controller_air_quality_and_aod_completions_do_not_dirty_observing_domains() -> None:
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._location = ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa")
    controller._refresh_manager = RefreshManager()
    controller._local_atmosphere_refresh_running = True
    controller._nasa_aod_refresh_running = True
    controller._earthdata_credentials_state = EarthdataCredentialState(
        username="earth-user",
        configured=True,
        secure_store_available=True,
        connection_verified=True,
    )
    controller._openaq_credential_store = Mock()
    controller._openaq_credential_store.api_key.return_value = "openaq-secret"
    controller._openaq_credentials_state = OpenAQCredentialState(
        configured=True,
        secure_store_available=True,
        connection_verified=True,
    )
    controller._local_atmosphere = LocalAtmosphere.not_configured()
    controller._nasa_aod_result = NasaAodResult.no_location()

    controller._finish_local_atmosphere_refresh(
        "9.030:38.740:addis ababa",
        LocalAtmosphere.no_data(),
    )
    controller._finish_nasa_aod_refresh(
        "9.030:38.740:addis ababa",
        NasaAodResult.failure("no_valid_pixel", "Nessun pixel AOD valido."),
    )

    for domain in (RefreshDomain.PLANNER, RefreshDomain.COMPASS, RefreshDomain.EQUIPMENT):
        assert not controller._refresh_manager.is_dirty(domain)
    assert not controller._refresh_manager.is_dirty(RefreshDomain.AIR_QUALITY)
    assert not controller._refresh_manager.is_dirty(RefreshDomain.AOD)


def test_app_controller_home_detail_output_unchanged_with_runtime_diagnostics() -> None:
    controller = AppController.__new__(AppController)
    controller._conditions_service = ObservationConditionsService()
    controller._moon = _moon("86%")
    controller._sky_quality = _sky_quality(bortle=5, radiance=4.0)
    controller._nasa_aod_result = NasaAodResult(
        available=True,
        status="ok",
        message="Dati NASA AOD disponibili.",
        product="VNP19A2.002",
        aod_550=0.12,
        acquisition_date=datetime.now().date().isoformat(),
    )
    controller._local_atmosphere = LocalAtmosphere(
        visible=True,
        has_data=True,
        message="",
        pm25="7 µg/m³",
        pm10="18 µg/m³",
        clarity="Aria limpida",
        source="OpenAQ",
        freshness="Aggiornato oggi",
        freshness_category="current",
    )
    target = _target("m31", "M31", "Galassia", 82)

    conditioned = controller._moon_adjusted_object(target)
    expected_score = _moon_adjusted_score(target, controller._moon)

    assert conditioned == replace(
        target,
        score=expected_score,
        score_label=ObservingScoreService.score_label(expected_score),
    )


def test_condition_diagnostic_notes_are_not_exposed_in_object_qml_output() -> None:
    controller = AppController.__new__(AppController)
    controller._object_descriptions = {}
    controller._moon = None
    controller._seeing_transparency = None
    controller._sky_quality = None
    controller._location = ObserverLocation("Test", "Earth", 0.0, 0.0, "UTC")
    target = _target(
        "m13",
        "M13",
        "Globular Cluster",
        78,
        best_time="22:00",
    )

    data = controller._object_to_qml(target)

    assert "diagnostic_notes" not in data
    assert "diagnosticNotes" not in data
    assert "conditionBreakdown" not in data
    assert "aod" not in data
    assert "particulate" not in data


def test_condition_target_moon_breakdown_matches_previous_implementation() -> None:
    service = ObservationConditionsService()
    moon = _moon("86%")
    target = _target("m31", "M31", "Galaxy", 82)

    conditioned = service.condition_target(
        target,
        ObservationConditionInputs(moon=moon),
        apply_moon=True,
    )
    breakdown = conditioned.breakdown

    assert breakdown.moon_penalty == _moon_penalty(target, moon)
    assert breakdown.adjusted_score == _moon_adjusted_score(target, moon)
    assert conditioned.target == service.apply_moon_adjustment(target, moon).target
    assert breakdown.applied_components == ("moon",)
    assert "moon:illumination=86" in breakdown.diagnostic_notes
    assert "light_pollution:not_requested" in breakdown.diagnostic_notes


def test_pollution_context_matches_legacy_high_bortle_behaviour() -> None:
    targets = _deep_sky_targets()
    sky_quality = _sky_quality(bortle=8)
    service = ObservationConditionsService()

    assert service.apply_deep_sky_pollution_context(targets, sky_quality) == _legacy_pollution_context(
        targets,
        sky_quality,
    )


def test_pollution_context_matches_legacy_high_viirs_behaviour() -> None:
    targets = _deep_sky_targets()
    sky_quality = _sky_quality(bortle=5, radiance=180.0)
    service = ObservationConditionsService()

    assert service.apply_deep_sky_pollution_context(targets, sky_quality) == _legacy_pollution_context(
        targets,
        sky_quality,
    )


def test_condition_target_pollution_breakdown_matches_previous_implementation() -> None:
    target = _target("m101", "M101", "Galaxy", 72, magnitude="9.0")
    sky_quality = _sky_quality(bortle=5, radiance=180.0)
    service = ObservationConditionsService()

    conditioned = service.condition_target(
        target,
        ObservationConditionInputs(sky_quality=sky_quality),
        apply_pollution=True,
    )
    breakdown = conditioned.breakdown

    assert breakdown.pollution_penalty == service.deep_sky_pollution_penalty(target, sky_quality)
    assert conditioned.target == _legacy_pollution_context([target], sky_quality)[0]
    assert breakdown.adjusted_score == conditioned.target.score
    assert breakdown.applied_components == ("light_pollution",)
    assert "sky_quality:bortle=5" in breakdown.diagnostic_notes
    assert "sky_quality:viirs=180" in breakdown.diagnostic_notes
    assert "moon:not_requested" in breakdown.diagnostic_notes


def test_condition_target_combined_breakdown_records_existing_components_without_new_penalties() -> None:
    target = _target("m31", "M31", "Galaxy", 82)
    moon = _moon("86%")
    sky_quality = _sky_quality(bortle=8, radiance=120.0)
    service = ObservationConditionsService()

    conditioned = service.condition_target(
        target,
        ObservationConditionInputs(moon=moon, sky_quality=sky_quality),
        apply_moon=True,
        apply_pollution=True,
    )
    breakdown = conditioned.breakdown
    moon_adjusted = _moon_adjusted_score(target, moon)
    expected_score = max(0, round(moon_adjusted - service.deep_sky_pollution_penalty(target, sky_quality)))

    assert breakdown.moon_penalty == _moon_penalty(target, moon)
    assert breakdown.pollution_penalty == service.deep_sky_pollution_penalty(target, sky_quality)
    assert breakdown.adjusted_score == expected_score
    assert conditioned.target.score == expected_score
    assert breakdown.applied_components == ("moon", "light_pollution")
    assert breakdown.weather_factor == 1.0
    assert breakdown.seeing_factor == 1.0
    assert breakdown.transparency_factor == 1.0
    assert breakdown.equipment_modifier == 0.0
    assert breakdown.aod_modifier == 0.0
    assert breakdown.pm25_modifier == 0.0


def test_condition_targets_batch_matches_individual_conditioning() -> None:
    targets = [
        _target("m31", "M31", "Galaxy", 82),
        _target("m13", "M13", "Globular Cluster", 78),
        _target("mars", "Marte", "Pianeta", 83),
    ]
    inputs = ObservationConditionInputs(moon=_moon("86%"), sky_quality=_sky_quality(bortle=8, radiance=120.0))
    service = ObservationConditionsService()

    batch = service.condition_targets(
        targets,
        inputs,
        apply_moon=True,
        apply_pollution=True,
    )
    individual = [
        service.condition_target(
            target,
            inputs,
            apply_moon=True,
            apply_pollution=True,
        )
        for target in targets
    ]

    assert batch == individual
    assert [item.original_target for item in batch] == targets
    assert [item.breakdown.object_id for item in batch] == ["m31", "m13", "mars"]


def test_pollution_context_preserves_good_low_radiance_sky() -> None:
    targets = _deep_sky_targets()
    sky_quality = _sky_quality(bortle=4, radiance=8.0)
    service = ObservationConditionsService()

    assert service.apply_deep_sky_pollution_context(targets, sky_quality) == targets


def test_pollution_context_preserves_missing_sky_quality_context() -> None:
    targets = _deep_sky_targets()
    service = ObservationConditionsService()

    assert service.apply_deep_sky_pollution_context(targets, None) == targets


def test_pollution_context_boundary_bortle_seven_is_active() -> None:
    targets = _deep_sky_targets()
    sky_quality = _sky_quality(bortle=7, radiance=None)
    service = ObservationConditionsService()

    updated = service.apply_deep_sky_pollution_context(targets, sky_quality)

    assert service.is_pollution_context_active(sky_quality) is True
    assert updated == _legacy_pollution_context(targets, sky_quality)
    assert updated[0].score < targets[0].score


def test_pollution_context_boundary_viirs_twenty_is_active() -> None:
    targets = _deep_sky_targets()
    sky_quality = _sky_quality(bortle=4, radiance=20.0)
    service = ObservationConditionsService()

    updated = service.apply_deep_sky_pollution_context(targets, sky_quality)

    assert service.is_pollution_context_active(sky_quality) is True
    assert updated == _legacy_pollution_context(targets, sky_quality)
    assert updated[0].score < targets[0].score


def test_pollution_context_boundary_viirs_below_twenty_is_inactive() -> None:
    targets = _deep_sky_targets()
    sky_quality = _sky_quality(bortle=4, radiance=19.99)
    service = ObservationConditionsService()

    assert service.is_pollution_context_active(sky_quality) is False
    assert service.apply_deep_sky_pollution_context(targets, sky_quality) == targets


def test_non_numeric_magnitude_is_safe_for_pollution_and_moon_adjustment() -> None:
    service = ObservationConditionsService()
    sky_quality = _sky_quality(bortle=8, radiance=120.0)
    target = _target("m101", "M101", "Galaxy", 72, magnitude="n/d")

    polluted = service.apply_deep_sky_pollution_to_target(target, sky_quality)
    moon_adjusted = service.apply_moon_adjustment(target, _moon("91%"))

    assert polluted.target.score < target.score
    assert polluted.target.score_label == ObservingScoreService.score_label(polluted.target.score)
    assert moon_adjusted.target.score == _moon_adjusted_score(target, _moon("91%"))


def test_deep_sky_pollution_context_is_not_applied_twice_to_same_target() -> None:
    service = ObservationConditionsService()
    sky_quality = _sky_quality(bortle=8, radiance=120.0)
    target = _target("m31", "M31", "Galaxy", 82)

    first = service.apply_deep_sky_pollution_to_target(target, sky_quality)
    second = service.apply_deep_sky_pollution_to_target(first.target, sky_quality)

    assert first.target.score < target.score
    assert second.target == first.target
    assert second.breakdown.adjusted_score == first.target.score
    assert second.breakdown.applied_components == ()
    assert second.breakdown.already_adjusted_flags == ("light_pollution",)
    assert "light_pollution:already_applied" in second.breakdown.diagnostic_notes


def test_deep_sky_pollution_context_sets_internal_flag_hidden_from_qml() -> None:
    service = ObservationConditionsService()
    sky_quality = _sky_quality(bortle=8, radiance=120.0)
    target = _target("m31", "M31", "Galaxy", 82)

    polluted = service.apply_deep_sky_pollution_to_target(target, sky_quality)

    assert "light_pollution" in polluted.target.condition_flags
    assert "condition_flags" not in polluted.target.to_qml()


def test_deep_sky_pollution_context_flag_prevents_reapply_without_text_note() -> None:
    service = ObservationConditionsService()
    sky_quality = _sky_quality(bortle=8, radiance=120.0)
    target = _target("m31", "M31", "Galaxy", 82)

    polluted = service.apply_deep_sky_pollution_to_target(target, sky_quality)
    translated_note_target = replace(polluted.target, notes="Localized observing note.")
    second = service.apply_deep_sky_pollution_to_target(translated_note_target, sky_quality)

    assert second.target == translated_note_target
    assert second.breakdown.adjusted_score == translated_note_target.score
    assert second.breakdown.applied_components == ()
    assert second.breakdown.already_adjusted_flags == ("light_pollution",)
    assert "light_pollution:already_applied" in second.breakdown.diagnostic_notes


def test_legacy_pollution_note_guard_still_prevents_reapply_and_adds_internal_flag() -> None:
    service = ObservationConditionsService()
    sky_quality = _sky_quality(bortle=8, radiance=120.0)
    target = _target("m31", "M31", "Galaxy", 62)
    legacy_target = replace(
        target,
        notes=f"{ObservationConditionsService.POLLUTION_CONTEXT_NOTE} Local note.",
    )

    conditioned = service.apply_deep_sky_pollution_to_target(legacy_target, sky_quality)

    assert conditioned.target.score == legacy_target.score
    assert "light_pollution" in conditioned.target.condition_flags
    assert conditioned.breakdown.applied_components == ()
    assert conditioned.breakdown.already_adjusted_flags == ("light_pollution",)
    assert "light_pollution:already_applied" in conditioned.breakdown.diagnostic_notes


def test_condition_target_applies_moon_but_not_pollution_when_pollution_already_applied() -> None:
    service = ObservationConditionsService()
    sky_quality = _sky_quality(bortle=8, radiance=120.0)
    moon = _moon("86%")
    target = _target("m31", "M31", "Galaxy", 82)

    polluted = service.condition_target(
        target,
        ObservationConditionInputs(sky_quality=sky_quality),
        apply_pollution=True,
    )
    conditioned = service.condition_target(
        polluted.target,
        ObservationConditionInputs(moon=moon, sky_quality=sky_quality),
        apply_moon=True,
        apply_pollution=True,
    )

    assert conditioned.breakdown.moon_penalty == _moon_penalty(polluted.target, moon)
    assert conditioned.breakdown.pollution_penalty == 0.0
    assert conditioned.breakdown.applied_components == ("moon",)
    assert conditioned.breakdown.already_adjusted_flags == ("light_pollution",)
    assert conditioned.target.score == _moon_adjusted_score(polluted.target, moon)
    assert "light_pollution:already_applied" in conditioned.breakdown.diagnostic_notes


def test_condition_target_double_moon_application_is_currently_not_guarded() -> None:
    service = ObservationConditionsService()
    moon = _moon("86%")
    target = _target("m31", "M31", "Galaxy", 82)

    first = service.condition_target(target, ObservationConditionInputs(moon=moon), apply_moon=True)
    second = service.condition_target(first.target, ObservationConditionInputs(moon=moon), apply_moon=True)

    assert second.breakdown.already_adjusted_flags == ()
    assert second.breakdown.applied_components == ("moon",)
    assert second.target.score == _moon_adjusted_score(first.target, moon)
    assert second.target.score < first.target.score


def test_deep_sky_pollution_context_keeps_every_visible_target_in_score_order() -> None:
    targets = [_target(f"m{i}", f"M{i}", "Galaxy", 95 - i * 3, magnitude="8.8") for i in range(12)]
    sky_quality = _sky_quality(bortle=8, radiance=140.0)
    service = ObservationConditionsService()

    updated = service.apply_deep_sky_pollution_context(targets, sky_quality)
    legacy_top_ten = _legacy_pollution_context(targets, sky_quality)

    assert [item.id for item in updated[:10]] == [item.id for item in legacy_top_ten]
    assert [item.id for item in updated] == [f"m{i}" for i in range(11)]


def test_app_controller_home_detail_conditioned_object_output_matches_legacy_formula() -> None:
    controller = AppController.__new__(AppController)
    controller._conditions_service = ObservationConditionsService()
    controller._moon = _moon("86%")
    target = _target("m31", "M31", "Galassia", 82)

    conditioned = controller._moon_adjusted_object(target)
    expected_score = _moon_adjusted_score(target, controller._moon)
    expected = replace(
        target,
        score=expected_score,
        score_label=ObservingScoreService.score_label(expected_score),
    )

    assert conditioned == expected


def test_app_controller_deep_sky_pollution_context_matches_legacy_formula() -> None:
    controller = AppController.__new__(AppController)
    controller._conditions_service = ObservationConditionsService()
    controller._sky_quality = _sky_quality(bortle=8, radiance=120.0)
    targets = _deep_sky_targets()

    assert controller._apply_deep_sky_pollution_context(targets) == _legacy_pollution_context(
        targets,
        controller._sky_quality,
    )


def test_planner_output_characterization_is_unchanged_on_fixture() -> None:
    planner = NightPlannerService()
    objects = [
        _target("venus", "Venere", "Pianeta", 83, best_time="20:45", difficulty="Facile"),
        _target("m24", "M24", "Open Cluster", 74, best_time="00:30", difficulty="Media"),
        _target("saturn", "Saturno", "Pianeta", 88, best_time="01:30", difficulty="Facile"),
    ]

    sky_quality = _sky_quality(bortle=5)
    plan = planner.plan(
        objects,
        _weather_summary(score=82),
        _telescope(),
        condition_inputs=ObservationConditionInputs(
            moon=_moon("24%"),
            sky_quality=sky_quality,
            seeing=SeeingTransparency(
                "Buona",
                "Buona",
                80,
                76,
                "fixture",
                atmospheric_transparency_score=76,
            ),
        ),
    )

    assert [item.object_id for item in plan] == ["venus", "m24", "saturn"]
    assert [item.time_label for item in plan] == ["20:45 sera", "00:30 notte", "01:30 notte"]


def test_equipment_recommendation_characterization_is_unchanged_on_fixture() -> None:
    service = EquipmentService()

    suggestion = service.suggest_for_profile(
        _target(
            "mars",
            "Marte",
            "Pianeta",
            82,
            magnitude="-1.0",
            max_altitude="55 gradi",
            recommended_observation_type="HighMagnification",
        ),
        [_telescope()],
        [
            Eyepiece(
                "zoom",
                "Baader Hyperion Zoom",
                24.0,
                68.0,
                eyepiece_type="Zoom",
                min_focal_length_mm=8.0,
                max_focal_length_mm=24.0,
                zoom_click_positions_mm=(24.0, 20.0, 16.0, 12.0, 8.0),
            )
        ],
        [],
        _seeing(score=50),
        _sky_quality(bortle=5),
        [],
    )

    assert suggestion["setupText"] == "Mak 127 + Baader Hyperion Zoom @ 16 mm"
    assert suggestion["bestEyepiece"] == "Baader Hyperion Zoom"
    assert suggestion["selectionScore"] > 70


def test_observation_conditions_service_does_not_import_openaq_or_nasa_aod() -> None:
    import astro_viewer.app.services.observation_conditions_service as module

    names = set(module.__dict__)

    assert "OpenAQLocalAtmosphereService" not in names
    assert "NasaAodProvider" not in names
    assert "LocalAtmosphere" not in names
    assert "NasaAodResult" not in names


def _scoring_aod(
    *,
    aod_550: float,
    uncertainty: float | None = 0.04,
    qa_raw: int | None = 1089,
    product: str = "VNP19A2.002",
) -> AodConditionInput:
    return AodConditionInput(
        available=True,
        freshness_category="current",
        aod_550=aod_550,
        source="NASA Earthdata",
        product=product,
        status="ok",
        age_days=1.0,
        uncertainty=uncertainty,
        qa_raw=qa_raw,
        method="direct_pixel",
    )


def _scoring_pm(
    *,
    pm25: float,
    pm10: float,
    distance_km: float = 5.0,
) -> ParticulateConditionInput:
    return ParticulateConditionInput(
        available=True,
        freshness_category="current",
        pm25=pm25,
        pm10=pm10,
        source="OpenAQ Local",
        status="ok",
        age_days=0.25,
        distance_km=distance_km,
    )


def _target(
    object_id: str,
    name: str,
    object_type: str,
    score: int,
    *,
    magnitude: str = "7.8",
    max_altitude: str = "48 gradi",
    best_time: str = "22:00",
    difficulty: str = "Media",
    recommended_observation_type: str = "General",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude=max_altitude,
        direction="Sud",
        best_time=best_time,
        observing_window=f"{best_time} - 02:00",
        notes="Nota.",
        recommended_setup="",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label=ObservingScoreService.score_label(score),
        difficulty=difficulty,
        apparent_size="20 arcmin",
        max_angular_size_deg=0.33,
        recommended_observation_type=recommended_observation_type,
    )


def _deep_sky_targets() -> list[CelestialObject]:
    return [
        _target("m31", "M31", "Galaxy", 88, magnitude="3.4", recommended_observation_type="WideField"),
        _target("m42", "M42", "Nebula", 84, magnitude="4.0", recommended_observation_type="General"),
        _target("m13", "M13", "Globular Cluster", 79, magnitude="5.8"),
        _target("m45", "M45", "Open Cluster", 75, magnitude="1.6", recommended_observation_type="WideField"),
        _target("m101", "M101", "Galaxy", 64, magnitude="9.0"),
    ]


def _moon(illumination: str) -> MoonSummary:
    return MoonSummary("Gibbosa", illumination, "18:00", "05:00", "Luna luminosa.", "", 0.0)


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.0,
        sky_brightness=19.0,
        source="fixture",
        description="fixture",
        viirs_radiance=radiance,
    )


def _weather_summary(score: int) -> WeatherSummary:
    return WeatherSummary(
        score=ObservingScoreService.score_label(score),
        score_value=score,
        explanation="fixture",
        cloud_cover=20,
        precipitation_probability=5,
        wind_kmh=8,
        humidity=55,
        temperature_c=14.0,
        alert="fixture",
    )


def _telescope() -> Telescope:
    return Telescope("mak127", "Mak 127", 127, 1500, "Maksutov", "planetary")


def _seeing(score: int) -> SeeingTransparency:
    return SeeingTransparency("Average", "Average", score, 60, "fixture")


def _legacy_pollution_context(
    targets: list[CelestialObject],
    sky_quality: SkyQuality | None,
) -> list[CelestialObject]:
    if not sky_quality:
        return targets
    radiance = sky_quality.viirs_radiance
    if radiance is None and sky_quality.bortle_class < 7:
        return targets
    if radiance is not None and radiance < 20 and sky_quality.bortle_class < 7:
        return targets

    updated = []
    for item in targets:
        lower_type = item.object_type.lower()
        penalty = _legacy_pollution_base_penalty(sky_quality)
        if "galaxy" in lower_type or "galassia" in lower_type:
            penalty *= 2.0
        elif "nebula" in lower_type and "cluster" not in lower_type:
            penalty *= 1.6
        elif "globular" in lower_type:
            penalty *= 1.15
        elif "open" in lower_type or "cluster" in lower_type:
            penalty *= 0.55
        try:
            magnitude = float(item.magnitude)
        except ValueError:
            magnitude = 10.0
        if magnitude >= 8.5:
            penalty += 12
        surface_brightness = _surface_brightness_proxy(item)
        if surface_brightness and surface_brightness >= 13.5:
            penalty += 8
        score = max(0, round(item.score - penalty))
        note = item.notes
        urban_note = "Cielo luminoso: visibilità limitata, serve trasparenza buona e schermare luci dirette."
        if urban_note not in note:
            note = f"{urban_note} {note}"
        updated.append(
            replace(
                item,
                score=score,
                score_label=ObservingScoreService.score_label(score),
                visible=item.visible and score > 10,
                notes=note,
            )
        )
    return sorted([item for item in updated if item.visible], key=lambda item: item.score, reverse=True)[:10]


def _legacy_pollution_base_penalty(sky_quality: SkyQuality) -> float:
    radiance = sky_quality.viirs_radiance
    bortle_penalty = max(0.0, (sky_quality.bortle_class - 6) * 8.0)
    if radiance is None:
        return max(6.0, bortle_penalty)
    radiance_penalty = min(24.0, math.log10(max(0.0, radiance) + 1.0) * 6.0)
    return max(6.0, bortle_penalty, radiance_penalty)


def _surface_brightness_proxy(item: CelestialObject) -> float | None:
    try:
        magnitude = float(item.magnitude)
    except ValueError:
        return None
    size_arcmin = 20.0
    return magnitude + 2.5 * math.log10(max(size_arcmin * size_arcmin, 1.0))


class _MoonGeometryEngine:
    def __init__(self, summary: MoonGeometrySummary | None) -> None:
        self._summary = summary
        self.calls = 0

    def moon_geometry(
        self,
        location: ObserverLocation,
        target: CelestialObject,
    ) -> MoonGeometrySummary | None:
        del location, target
        self.calls += 1
        return self._summary


class _BatchMoonGeometryEngine:
    def __init__(self) -> None:
        self.batch_calls = 0
        self.scalar_calls = 0

    def moon_geometry_batch(
        self,
        location: ObserverLocation,
        targets: list[CelestialObject],
    ) -> dict[str, MoonGeometrySummary]:
        del location
        self.batch_calls += 1
        return {
            target.id: MoonGeometrySummary(
                object_id=target.id,
                moon_altitude_deg=30.0,
                moon_target_separation_deg=70.0 + index,
                moon_above_horizon=True,
                moon_visible_during_target_window=True,
                moon_set_before_target_window=False,
            )
            for index, target in enumerate(targets, start=1)
        }

    def moon_geometry(
        self,
        location: ObserverLocation,
        target: CelestialObject,
    ) -> MoonGeometrySummary | None:
        del location, target
        self.scalar_calls += 1
        raise AssertionError("scalar fallback should not run")
