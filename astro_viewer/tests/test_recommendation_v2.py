"""Protect optical recommendation scoring, setup choices, and explanations."""

from __future__ import annotations

import pytest

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import SeeingTransparency
from astro_viewer.app.services.equipment_service import EquipmentService


TARGETS = {
    "M31": ("messier-M31", "Galaxy", "3.4", "190 arcmin", 3.17, "WideField"),
    "M45": ("messier-M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField"),
    "M44": ("messier-M44", "Open cluster", "3.7", "95 arcmin", 1.58, "WideField"),
    "M5": ("messier-M5", "Globular cluster", "5.6", "23 arcmin", 0.383, "General"),
    "M13": ("messier-M13", "Globular cluster", "5.8", "20 arcmin", 0.333, "General"),
    "M15": ("messier-M15", "Globular cluster", "6.2", "18 arcmin", 0.300, "General"),
    "M24": ("messier-M24", "Milky Way star cloud", "2.5", "2 deg", 2.0, "WideField"),
    "M27": ("messier-M27", "Planetary nebula", "7.4", "8 arcmin", 0.133, "General"),
    "M57": ("messier-M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification"),
    "M92": ("messier-M92", "Globular cluster", "6.4", "14 arcmin", 0.233, "General"),
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


def test_v2_planetary_zoom_recommendation_depends_on_seeing_quality() -> None:
    service = EquipmentService()
    target = _planet("mars", "Marte")

    unknown = service.suggest_for_profile(target, [_mak127()], [_hyperion_zoom()], [], seeing=None, binoculars=[])
    good = service.suggest_for_profile(target, [_mak127()], [_hyperion_zoom()], [], seeing=_seeing(82), binoculars=[])
    poor = service.suggest_for_profile(target, [_mak127()], [_hyperion_zoom()], [], seeing=_seeing(30), binoculars=[])

    assert unknown["setupText"] == "Mak 127 + Baader Hyperion Zoom 8-24 mm @ 16 mm"
    assert unknown["setupOptions"][0]["magnification"] == "94x"
    assert good["setupText"] == "Mak 127 + Baader Hyperion Zoom 8-24 mm @ 8 mm"
    assert good["setupOptions"][0]["magnification"] == "188x"
    assert poor["setupText"] == "Mak 127 + Baader Hyperion Zoom 8-24 mm @ 24 mm"
    assert poor["setupOptions"][0]["magnification"] == "62x"


def test_poor_seeing_uses_the_least_over_limit_owned_configuration() -> None:
    service = EquipmentService()
    target = _planet("mercury", "Mercurio", max_altitude="18 gradi")
    telescope = Telescope(
        "edgehd8",
        "Celestron EdgeHD 8 OTA",
        203,
        2032,
        "Schmidt-Cassegrain",
        "OTA",
    )

    poor = service.suggest_for_profile(
        target,
        [telescope],
        [
            Eyepiece("e18", "18 mm", 18, 52),
            Eyepiece("e9", "9 mm", 9, 62),
            Eyepiece("e5", "5 mm", 5, 60),
        ],
        [],
        seeing=_seeing(25),
        binoculars=[],
    )
    excellent = service.suggest_for_profile(
        target,
        [telescope],
        [
            Eyepiece("e18", "18 mm", 18, 52),
            Eyepiece("e9", "9 mm", 9, 62),
            Eyepiece("e5", "5 mm", 5, 60),
        ],
        [],
        seeing=_seeing(92),
        binoculars=[],
    )

    assert poor["setupText"] == "Celestron EdgeHD 8 OTA + 18 mm"
    assert poor["setupOptions"][0]["magnification"] == "113x"
    assert poor["recommendationState"] == "seeing_limited"
    assert "seeing lo permette" in poor["explanation"]
    assert excellent["setupOptions"][0]["magnification"] == "113x"
    assert excellent["recommendationState"] == "ready"


def test_poor_seeing_excludes_over_limit_options_when_one_is_available() -> None:
    service = EquipmentService()
    telescope = Telescope(
        "edgehd8",
        "Celestron EdgeHD 8 OTA",
        203,
        2032,
        "Schmidt-Cassegrain",
        "OTA",
    )
    suggestion = service.suggest_for_profile(
        _planet("mercury", "Mercurio"),
        [telescope],
        [
            Eyepiece("e25", "25 mm", 25, 52),
            Eyepiece("e18", "18 mm", 18, 52),
            Eyepiece("e9", "9 mm", 9, 62),
        ],
        [],
        seeing=_seeing(25),
        binoculars=[],
    )

    assert suggestion["setupOptions"][0]["magnification"] == "81x"
    assert suggestion["recommendationState"] == "ready"
    assert all(
        int(option["magnification"].removesuffix("x")) <= 85
        for option in suggestion["setupOptions"]
    )


def test_unknown_seeing_marks_a_planetary_fallback_above_the_conservative_cap() -> None:
    service = EquipmentService()
    suggestion = service.suggest_for_profile(
        _planet("jupiter", "Giove"),
        [
            Telescope(
                "long_focus",
                "Long-focus 200",
                200,
                3000,
                "Schmidt-Cassegrain",
                "OTA",
            )
        ],
        [
            Eyepiece("e20", "20 mm", 20, 52),
            Eyepiece("e10", "10 mm", 10, 62),
        ],
        [],
        seeing=None,
        binoculars=[],
    )

    assert suggestion["setupOptions"][0]["magnification"] == "150x"
    assert suggestion["recommendationState"] == "seeing_limited"
    assert "seeing lo permette" in suggestion["explanation"]


def test_target_profile_ideal_magnification_never_exceeds_seeing_cap() -> None:
    service = EquipmentService()
    telescope = Telescope(
        "fs60",
        "Takahashi FS-60CB",
        60,
        355,
        "Refractor",
        "OTA",
    )

    profile = service._target_profile(
        _planet("mercury", "Mercurio"),
        telescope,
        _seeing(25),
    )

    assert profile["maxUsefulMag"] == 36
    assert profile["idealMag"] == 36


@pytest.mark.parametrize("target_name", ["M5", "M92", "M15"])
def test_v2_medium_globular_zoom_prefers_medium_magnification(target_name: str) -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _target(target_name),
        [_mak127()],
        [_hyperion_zoom()],
        [],
        binoculars=[],
    )

    assert suggestion["setupText"] == "Mak 127 + Baader Hyperion Zoom 8-24 mm @ 20 mm"
    assert suggestion["setupOptions"][0]["magnification"] == "75x"


@pytest.mark.parametrize("target_name", ["M24", "M31"])
def test_v2_wide_field_zoom_targets_remain_low_power(target_name: str) -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _target(target_name),
        [_mak127()],
        [_hyperion_zoom()],
        [],
        binoculars=[],
    )

    assert suggestion["setupText"] == "Mak 127 + Baader Hyperion Zoom 8-24 mm @ 24 mm"
    assert suggestion["setupOptions"][0]["magnification"] == "62x"


def test_seeing_limit_does_not_reclassify_wide_field_recommendations() -> None:
    service = EquipmentService()
    poor = service.suggest_for_profile(
        _target("M31"),
        [_newton()],
        _newton_eyepieces(),
        [_barlow()],
        seeing=_seeing(25),
        binoculars=[],
    )
    excellent = service.suggest_for_profile(
        _target("M31"),
        [_newton()],
        _newton_eyepieces(),
        [_barlow()],
        seeing=_seeing(92),
        binoculars=[],
    )

    assert poor["setupText"] == excellent["setupText"] == "Newton 130/650 + 32 mm"
    assert poor["recommendationState"] == "ready"
    assert excellent["recommendationState"] == "ready"


def test_v2_zoom_recommendations_use_click_positions_without_duplicate_options() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _target("M5"),
        [_mak127()],
        [_hyperion_zoom()],
        [],
        binoculars=[],
    )
    positions = [option["suggestedPosition"] for option in suggestion["setupOptions"]]
    labels = [option["detailLabel"] for option in suggestion["setupOptions"]]

    assert set(positions) <= {"24 mm", "20 mm", "16 mm", "12 mm", "8 mm"}
    assert {"23.8 mm", "15.7 mm", "11.9 mm"}.isdisjoint(positions)
    assert len(labels) == len(set(labels))


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


def _mak127() -> Telescope:
    return Telescope("mak127", "Mak 127", 127, 1500, "Maksutov", "manuale")


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


def _hyperion_zoom() -> Eyepiece:
    return Eyepiece(
        "hyperion-zoom",
        "Baader Hyperion Zoom 8-24 mm",
        24,
        60,
        "Zoom",
        8,
        24,
        (24, 20, 16, 12, 8),
    )


def _barlow() -> Barlow:
    return Barlow("b2", "Barlow 2x", 2.0)


def _binocular() -> Binocular:
    return Binocular("bino", "Nikon Monarch M5", 10, 50)


def _planet(
    object_id: str,
    name: str,
    *,
    max_altitude: str = "62 gradi",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type="Pianeta",
        image="",
        magnitude="-1.2",
        distance="",
        max_altitude=max_altitude,
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
        recommended_observation_type="HighMagnification",
    )


def _seeing(score: int) -> SeeingTransparency:
    label = "Excellent" if score >= 82 else "Good" if score >= 65 else "Average" if score >= 42 else "Poor"
    return SeeingTransparency(label, "Average", score, 60, "")
