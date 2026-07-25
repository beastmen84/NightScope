from __future__ import annotations

from dataclasses import replace

import pytest

from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.models.equipment import Binocular
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.target_observation_traits import TargetObservationTraits
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.recommendation_presenter import RecommendationPresenter


def test_traits_prefer_messier_max_angular_size_metadata() -> None:
    traits = TargetObservationTraits.from_object(
        _object("messier-M45", "M45", "Open cluster", "1.6", "malformed", 1.83, ""),
    )

    assert traits.max_angular_size_deg == pytest.approx(1.83)
    assert traits.angular_size_deg == pytest.approx(1.83)
    assert traits.recommended_observation_type == "WideField"
    assert traits.is_wide_field


def test_traits_prefer_configured_observation_type() -> None:
    traits = TargetObservationTraits.from_object(
        _object("messier-test", "Test", "Planetary nebula", "8.8", "86 arcsec", 0.024, "WideField"),
    )

    assert traits.recommended_observation_type == "WideField"
    assert traits.is_wide_field
    assert not traits.is_high_magnification


def test_traits_identify_general_target() -> None:
    traits = TargetObservationTraits.from_object(
        _object("messier-M27", "M27", "Planetary nebula", "7.4", "8 arcmin", 0.133, "General"),
    )

    assert traits.recommended_observation_type == "General"
    assert traits.is_general
    assert traits.magnitude == pytest.approx(7.4)
    assert traits.angular_size_deg == pytest.approx(0.133)


def test_traits_identify_high_magnification_target() -> None:
    traits = TargetObservationTraits.from_object(
        _object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", None, ""),
    )

    assert traits.recommended_observation_type == "HighMagnification"
    assert traits.is_high_magnification
    assert traits.angular_size_deg == pytest.approx(86 / 3600)


def test_traits_identify_supernova_remnant_as_deep_sky() -> None:
    traits = TargetObservationTraits.from_object(
        _object("caldwell-C34", "C34", "Supernova remnant", "7.0", "8 deg", 8.0, "WideField"),
    )

    assert traits.is_deep_sky
    assert not traits.is_planetary_or_lunar
    assert traits.is_wide_field


def test_traits_identify_ngc_stellar_and_unclassified_targets_as_deep_sky() -> None:
    for object_type in ("Star", "Optical double", "Unclassified object"):
        traits = TargetObservationTraits.from_object(
            _object(
                "ngc-test",
                "NGC test",
                object_type,
                "n/d",
                "",
                None,
                "General",
            ),
        )

        assert traits.is_deep_sky
        assert not traits.is_planetary_or_lunar


def test_traits_fallback_to_object_type_and_textual_size() -> None:
    traits = TargetObservationTraits.from_object(
        _object("messier-M44", "M44", "Open cluster", "3.1", "95 arcmin", None, ""),
    )

    assert traits.recommended_observation_type == "WideField"
    assert traits.angular_size_deg == pytest.approx(95 / 60)
    assert traits.profile_size_arcmin == pytest.approx(95)


def test_traits_handle_malformed_or_missing_size() -> None:
    traits = TargetObservationTraits.from_object(
        _object("custom", "Custom", "Galaxy", "n/d", "unknown", None, ""),
    )

    assert traits.magnitude is None
    assert traits.angular_size_deg is None
    assert traits.apparent_size_arcmin is None
    assert traits.recommended_observation_type == "General"


@pytest.mark.parametrize(
    ("max_altitude", "expected"),
    (
        ("49°", 49.0),
        ("49 gradi", 49.0),
        ("-4,5°", -4.5),
        ("n/d", 0.0),
    ),
)
def test_traits_parse_runtime_altitude_formats(max_altitude: str, expected: float) -> None:
    target = _object("messier-M31", "M31", "Galaxy", "3.4", "178 arcmin", 2.97, "WideField")
    target = replace(target, max_altitude=max_altitude)

    assert TargetObservationTraits.from_object(target).max_altitude_deg == pytest.approx(expected)


def test_traits_consume_skyfield_altitude_label_contract() -> None:
    target = _object("messier-M31", "M31", "Galaxy", "3.4", "178 arcmin", 2.97, "WideField")
    target = replace(target, max_altitude=SkyfieldAstronomyEngine._degrees_label(49.25, decimals=2))

    assert TargetObservationTraits.from_object(target).max_altitude_deg == pytest.approx(49.25)


def test_scoring_and_presenter_consume_same_observation_type_traits() -> None:
    target = _object("messier-M45", "M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField")
    service = EquipmentService()
    candidates = service._ranked_profile_candidates(
        target,
        [],
        [],
        [],
        [Binocular("canon", "Canon 15x50 IS All Weather", 15, 50, True)],
    )
    dto = RecommendationPresenter().from_candidates(target, candidates, service._recommended_candidate(candidates))

    assert TargetObservationTraits.from_object(target).is_wide_field
    assert candidates[0].score >= 70
    assert "Oggetto esteso" in dto["explanation"]


def _object(
    object_id: str,
    name: str,
    object_type: str,
    magnitude: str,
    apparent_size: str,
    max_angular_size_deg: float | None,
    recommended_observation_type: str,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="3 h",
        visible=True,
        score=80,
        difficulty="Media",
        apparent_size=apparent_size,
        max_angular_size_deg=max_angular_size_deg,
        recommended_observation_type=recommended_observation_type,
    )
