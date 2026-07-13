from __future__ import annotations

from astro_viewer.app.models.equipment import Barlow, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_service import EquipmentService


def test_wide_field_m45_keeps_low_power_no_barlow_telescope_setup() -> None:
    suggestion = _suggest(_object("messier-M45", "M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField"))

    assert suggestion["setupText"] == "25 mm"
    assert suggestion["barlow"] == "No"
    assert suggestion["setupOptions"][0]["magnification"] == "26x"


def test_very_large_m31_uses_wider_telescope_setup_from_metadata() -> None:
    suggestion = _suggest(_object("messier-M31", "M31", "Galaxy", "3.4", "190 arcmin", 3.17, "WideField"))

    assert suggestion["setupText"] == "32 mm"
    assert suggestion["barlow"] == "No"
    assert suggestion["setupOptions"][0]["trueField"] == "3,35 gradi"


def test_high_magnification_m57_still_prefers_compact_telescope_setup() -> None:
    suggestion = _suggest(_object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification"))

    assert suggestion["setupText"] == "6 mm"
    assert suggestion["barlow"] == "No"
    assert suggestion["setupOptions"][0]["magnification"] == "108x"


def test_general_m27_planetary_nebula_uses_medium_telescope_magnification() -> None:
    suggestion = _suggest(_object("messier-M27", "M27", "Planetary nebula", "7.4", "8 arcmin", 0.133, "General"))

    assert suggestion["setupText"] == "10 mm"
    assert suggestion["barlow"] == "No"
    assert suggestion["setupOptions"][0]["magnification"] == "65x"


def test_general_m97_planetary_nebula_avoids_over_pushing_magnification() -> None:
    suggestion = _suggest(_object("messier-M97", "M97", "Planetary nebula", "9.9", "3 arcmin", 0.050, "General"))

    assert suggestion["setupText"] == "10 mm"
    assert suggestion["barlow"] == "No"
    assert suggestion["setupOptions"][0]["magnification"] == "65x"


def test_general_m107_globular_uses_medium_telescope_magnification() -> None:
    suggestion = _suggest(_object("messier-M107", "M107", "Globular cluster", "8.9", "10 arcmin", 0.167, "General"))

    assert suggestion["setupText"] == "10 mm"
    assert suggestion["barlow"] == "No"
    assert suggestion["setupOptions"][0]["magnification"] == "65x"


def test_unenriched_planetary_nebula_keeps_legacy_object_type_fallback() -> None:
    suggestion = _suggest(_object("custom-pn", "Fallback PN", "Planetary nebula", "8.8", "86 arcsec"))

    assert suggestion["setupText"] == "6 mm"
    assert suggestion["setupOptions"][0]["magnification"] == "108x"


def _suggest(celestial_object: CelestialObject) -> dict:
    return EquipmentService().suggest_for_object(
        celestial_object,
        Telescope("scope", "Newton 130/650", 130, 650, "Newton", "manuale"),
        [
            Eyepiece("e32", "32 mm", 32, 68),
            Eyepiece("e25", "25 mm", 25, 52),
            Eyepiece("e10", "10 mm", 10, 60),
            Eyepiece("e6", "6 mm", 6, 58),
        ],
        [Barlow("b2", "Barlow 2x", 2.0)],
    )


def _object(
    object_id: str,
    name: str,
    object_type: str,
    magnitude: str,
    apparent_size: str,
    max_angular_size_deg: float | None = None,
    recommended_observation_type: str = "",
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
