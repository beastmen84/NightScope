from __future__ import annotations

from astro_viewer.app.models.equipment import Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_service import EquipmentService


def test_binocular_only_wide_field_target_returns_binocular_recommendation() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _object("messier-M45", "M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField"),
        [],
        [],
        [],
        binoculars=[Binocular("bino", "Nikon Monarch M5", 10, 50)],
    )

    assert suggestion["equipmentType"] == "Binocular"
    assert suggestion["setupText"] == "Nikon Monarch M5 10×50"
    assert suggestion["bestEyepiece"] == "Non richiesto"
    assert suggestion["barlow"] == "No"
    assert suggestion["setupOptions"][0]["equipmentType"] == "Binocular"
    assert suggestion["setupOptions"][0]["trueField"] == "n/d"


def test_binocular_only_high_magnification_target_is_cautious() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification"),
        [],
        [],
        [],
        binoculars=[Binocular("bino", "Nikon Monarch M5", 10, 50)],
    )

    assert suggestion["equipmentType"] == "Binocular"
    assert suggestion["difficulty"] == "Difficile"
    assert suggestion["selectionScore"] < 35
    assert "non ideale" in suggestion["explanation"]


def test_mixed_profile_can_select_binocular_for_large_wide_field_target() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _object("messier-M31", "M31", "Galaxy", "3.4", "190 arcmin", 3.17, "WideField"),
        [Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")],
        [Eyepiece("e10", "10 mm", 10, 60)],
        [],
        binoculars=[Binocular("bino", "Nikon Monarch M5", 10, 50)],
    )

    assert suggestion["equipmentType"] == "Binocular"
    assert suggestion["setupText"] == "Nikon Monarch M5 10×50"


def test_mixed_profile_keeps_telescope_for_high_magnification_target() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification"),
        [Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")],
        [Eyepiece("e10", "10 mm", 10, 60), Eyepiece("e25", "25 mm", 25, 52)],
        [],
        binoculars=[Binocular("bino", "Nikon Monarch M5", 10, 50)],
    )

    assert suggestion["equipmentType"] == "Telescope"
    assert suggestion["setupText"].startswith("Maksutov 90/1250 +")


def test_general_planetary_nebula_prefers_telescope_when_available() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _object("messier-M27", "M27", "Planetary nebula", "7.4", "8 arcmin", 0.133, "General"),
        [Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")],
        [Eyepiece("e10", "10 mm", 10, 60), Eyepiece("e25", "25 mm", 25, 52)],
        [],
        binoculars=[Binocular("bino", "Nikon Monarch M5", 10, 50)],
    )

    assert suggestion["equipmentType"] == "Telescope"
    assert suggestion["setupText"].startswith("Maksutov 90/1250 +")


def test_unassigned_binoculars_are_not_considered() -> None:
    wide_field = _object("messier-M45", "M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField")
    service = EquipmentService()

    without_binocular = service.suggest_for_profile(
        wide_field,
        [Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")],
        [Eyepiece("e10", "10 mm", 10, 60)],
        [],
        binoculars=[],
    )
    with_binocular = service.suggest_for_profile(
        wide_field,
        [Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")],
        [Eyepiece("e10", "10 mm", 10, 60)],
        [],
        binoculars=[Binocular("bino", "Nikon Monarch M5", 10, 50)],
    )

    assert without_binocular.get("equipmentType", "Telescope") == "Telescope"
    assert with_binocular["equipmentType"] == "Binocular"


def _object(
    object_id: str,
    name: str,
    object_type: str,
    magnitude: str,
    apparent_size: str,
    max_angular_size_deg: float,
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
