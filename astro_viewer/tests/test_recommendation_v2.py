from __future__ import annotations

import pytest

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_service import EquipmentService


TARGETS = {
    "M31": ("messier-M31", "Galaxy", "3.4", "190 arcmin", 3.17, "WideField"),
    "M45": ("messier-M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField"),
    "M44": ("messier-M44", "Open cluster", "3.7", "95 arcmin", 1.58, "WideField"),
    "M13": ("messier-M13", "Globular cluster", "5.8", "20 arcmin", 0.333, "General"),
    "M27": ("messier-M27", "Planetary nebula", "7.4", "8 arcmin", 0.133, "General"),
    "M57": ("messier-M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification"),
    "M97": ("messier-M97", "Planetary nebula", "9.9", "3 arcmin", 0.050, "General"),
    "M107": ("messier-M107", "Globular cluster", "8.9", "10 arcmin", 0.167, "General"),
}


@pytest.mark.parametrize(
    ("target_name", "expected_setup", "expected_magnification"),
    [
        ("M31", "32 mm", "20x"),
        ("M45", "25 mm", "26x"),
        ("M44", "25 mm", "26x"),
        ("M13", "10 mm", "65x"),
        ("M27", "10 mm", "65x"),
        ("M57", "6 mm", "108x"),
        ("M97", "10 mm", "65x"),
        ("M107", "10 mm", "65x"),
    ],
)
def test_v2_telescope_only_matches_target_observing_scale(
    target_name: str,
    expected_setup: str,
    expected_magnification: str,
) -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _target(target_name),
        [_newton()],
        _newton_eyepieces(),
        [_barlow()],
        binoculars=[],
    )

    assert suggestion["equipmentType"] == "Telescope"
    assert suggestion["setupText"] == f"Newton 130/650 + {expected_setup}"
    assert suggestion["barlow"] == "No"
    assert suggestion["setupOptions"][0]["magnification"] == expected_magnification


@pytest.mark.parametrize("target_name", TARGETS)
def test_v2_binocular_only_returns_binocular_recommendation_for_every_target(target_name: str) -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _target(target_name),
        [],
        [],
        [],
        binoculars=[_binocular()],
    )

    assert suggestion["equipmentType"] == "Binocular"
    assert suggestion["setupText"] == "Nikon Monarch M5 10×50"


@pytest.mark.parametrize("target_name", ["M31", "M45", "M44"])
def test_v2_binocular_only_scores_wide_field_targets_as_strong_matches(target_name: str) -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _target(target_name),
        [],
        [],
        [],
        binoculars=[_binocular()],
    )

    assert suggestion["selectionScore"] >= 85
    assert "Oggetto esteso" in suggestion["explanation"]


def test_v2_binocular_only_keeps_high_magnification_target_cautious() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _target("M57"),
        [],
        [],
        [],
        binoculars=[_binocular()],
    )

    assert suggestion["selectionScore"] < 35
    assert suggestion["difficulty"] == "Difficile"
    assert "non è ideale" in suggestion["explanation"]


@pytest.mark.parametrize(
    ("target_name", "expected_equipment", "expected_setup_fragment"),
    [
        ("M31", "Binocular", "Nikon Monarch M5 10×50"),
        ("M45", "Binocular", "Nikon Monarch M5 10×50"),
        ("M44", "Binocular", "Nikon Monarch M5 10×50"),
        ("M13", "Telescope", "Maksutov 90/1250 + 25 mm"),
        ("M27", "Telescope", "Maksutov 90/1250 + 25 mm"),
        ("M57", "Telescope", "Maksutov 90/1250 + 10 mm"),
        ("M97", "Telescope", "Maksutov 90/1250 + 25 mm"),
        ("M107", "Telescope", "Maksutov 90/1250 + 25 mm"),
    ],
)
def test_v2_mixed_profile_selects_configuration_that_matches_observing_need(
    target_name: str,
    expected_equipment: str,
    expected_setup_fragment: str,
) -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _target(target_name),
        [_maksutov()],
        _maksutov_eyepieces(),
        [],
        binoculars=[_binocular()],
    )

    assert suggestion["equipmentType"] == expected_equipment
    assert suggestion["setupText"] == expected_setup_fragment


def _target(name: str) -> CelestialObject:
    object_id, object_type, magnitude, apparent_size, max_angular_size_deg, observation_type = TARGETS[name]
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
        recommended_observation_type=observation_type,
    )


def _newton() -> Telescope:
    return Telescope("newton", "Newton 130/650", 130, 650, "Newton", "manuale")


def _maksutov() -> Telescope:
    return Telescope("mak", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")


def _newton_eyepieces() -> list[Eyepiece]:
    return [
        Eyepiece("e32", "32 mm", 32, 68),
        Eyepiece("e25", "25 mm", 25, 52),
        Eyepiece("e10", "10 mm", 10, 60),
        Eyepiece("e6", "6 mm", 6, 58),
    ]


def _maksutov_eyepieces() -> list[Eyepiece]:
    return [
        Eyepiece("e25", "25 mm", 25, 52),
        Eyepiece("e10", "10 mm", 10, 60),
    ]


def _barlow() -> Barlow:
    return Barlow("b2", "Barlow 2x", 2.0)


def _binocular() -> Binocular:
    return Binocular("bino", "Nikon Monarch M5", 10, 50)
