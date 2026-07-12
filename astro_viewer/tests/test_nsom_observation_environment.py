from __future__ import annotations

from dataclasses import replace

import pytest

import astro_viewer.app.services.nsom_observation_environment as environment_module

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.nsom_observation_environment import (
    NsomObservationEnvironmentService,
)
from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    MoonGeometryConditionInput,
    ObservationConditionInputs,
)


def test_canonical_environment_applies_aerosol_once_without_mutating_target() -> None:
    target = _target(intrinsic_score=80, score=92)
    inputs = ObservationConditionInputs(
        sky_quality=_sky_quality(),
        seeing=_seeing(),
        aod=AodConditionInput(
            available=True,
            freshness_category="current",
            aod_550=0.7,
            source="NASA AOD",
            product="VNP19A2.002",
            status="available",
            age_days=1.0,
            uncertainty=0.05,
            qa_raw=3,
            method="local_neighborhood",
            local_valid_pixel_count=9,
        ),
    )
    service = NsomObservationEnvironmentService()

    first = service.observable_target_value(target, inputs)
    second = service.observable_target_value(target, inputs)

    assert first == second
    assert first.intrinsic_target_quality == pytest.approx(80.0)
    assert first.effective_observability.atmospheric_transparency < 0.715
    assert target.score == 92
    assert target.intrinsic_score == 80


def test_observable_value_builds_intrinsic_target_once(monkeypatch: pytest.MonkeyPatch) -> None:
    original_builder = environment_module.build_intrinsic_target_quality
    calls = 0

    def recording_builder(target: CelestialObject):
        nonlocal calls
        calls += 1
        return original_builder(target)

    monkeypatch.setattr(environment_module, "build_intrinsic_target_quality", recording_builder)

    NsomObservationEnvironmentService().observable_target_value(
        _target(intrinsic_score=80, score=92),
        ObservationConditionInputs(sky_quality=_sky_quality(), seeing=_seeing()),
    )

    assert calls == 1


def test_intrinsic_value_is_independent_from_compatibility_score() -> None:
    service = NsomObservationEnvironmentService()
    inputs = ObservationConditionInputs(sky_quality=_sky_quality(), seeing=_seeing())
    target = _target(intrinsic_score=73, score=20)

    low_compatibility = service.observable_target_value(target, inputs)
    high_compatibility = service.observable_target_value(replace(target, score=99), inputs)

    assert low_compatibility.value == pytest.approx(high_compatibility.value)
    assert low_compatibility.intrinsic_target_quality == pytest.approx(73.0)


def test_moon_geometry_changes_only_lunar_environment_component() -> None:
    service = NsomObservationEnvironmentService()
    target = _target(intrinsic_score=80, score=80)
    common = ObservationConditionInputs(
        moon=MoonSummary("Piena", "95%", "18:00", "06:00", "", ""),
        sky_quality=_sky_quality(),
        seeing=_seeing(),
    )
    moon_set = replace(
        common,
        moon_geometry=MoonGeometryConditionInput(moon_set_before_target_window=True),
    )

    exposed = service.environment(target, common)
    clear_window = service.environment(target, moon_set)

    assert exposed.lunar_sky_background < 1.0
    assert clear_window.lunar_sky_background == pytest.approx(1.0)
    assert exposed.static_sky_background == clear_window.static_sky_background
    assert exposed.atmospheric_transparency == clear_window.atmospheric_transparency


def _target(*, intrinsic_score: int, score: int) -> CelestialObject:
    return CelestialObject(
        id="messier-M31",
        name="M31 Andromeda Galaxy",
        object_type="Galaxy",
        image="",
        magnitude="3.4",
        distance="",
        max_altitude="48 gradi",
        direction="Sud",
        best_time="23:00",
        observing_window="21:00 - 02:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        visible=True,
        score=score,
        intrinsic_score=intrinsic_score,
        azimuth="180 gradi",
        time_above_horizon="5 h",
    )


def _sky_quality() -> SkyQuality:
    return SkyQuality(
        bortle_class=4,
        limiting_magnitude=6.0,
        sky_brightness=21.0,
        source="VIIRS",
        description="",
        viirs_radiance=1.0,
    )


def _seeing() -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Good",
        transparency="Average",
        seeing_score=80,
        transparency_score=62,
        explanation="",
        atmospheric_transparency_score=70,
    )
