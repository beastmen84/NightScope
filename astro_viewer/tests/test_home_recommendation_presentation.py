from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.equipment import Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_service import EquipmentService


HOME_PAGE = Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "HomePage.qml"


def test_home_setup_option_uses_backend_recommended_role() -> None:
    body = _qml_function_body("displaySetupOption")

    assert 'optionByRole(item, "Consigliato")' in body
    assert 'optionByRole(item, "Alternativa")' not in body
    assert 'optionByRole(item, "Campo largo")' not in body
    assert "item.type" not in body
    assert "item.name" not in body
    assert "venus" not in body
    assert "mercury" not in body


def test_home_reason_uses_backend_equipment_explanation() -> None:
    body = _qml_function_body("recommendationReason")

    assert "item.equipmentExplanation" in body
    assert "typeText" not in body
    assert "item.type" not in body
    assert "Campo largo" not in body
    assert "globular" not in body
    assert "galaxy" not in body
    assert "nebula" not in body
    assert "Pianeta" not in body


def test_home_visibility_label_uses_observable_wording() -> None:
    body = _qml_function_body("visibilityLabel")

    assert "Visibile a occhio nudo" in body
    assert "Visibile con binocolo" in body
    assert "Visibile con telescopio" in body
    assert "Visibilità: telescopio" not in body


def test_home_backend_data_for_telescope_recommendation() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification"),
        [Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")],
        [Eyepiece("e10", "10 mm", 10, 60), Eyepiece("e25", "25 mm", 25, 52)],
        [],
        binoculars=[],
    )

    recommended = suggestion["setupOptions"][0]

    assert recommended["role"] == "Consigliato"
    assert recommended["equipmentType"] == "Telescope"
    assert suggestion["setupText"].startswith("Maksutov 90/1250 +")
    assert suggestion["explanation"]


def test_home_backend_data_for_binocular_recommendation() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _object("messier-M45", "M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField"),
        [],
        [],
        [],
        binoculars=[Binocular("bino", "Nikon Monarch M5", 10, 50)],
    )

    recommended = suggestion["setupOptions"][0]

    assert recommended["role"] == "Consigliato"
    assert recommended["equipmentType"] == "Binocular"
    assert suggestion["setupText"] == "Nikon Monarch M5 10×50"
    assert "Oggetto esteso" in suggestion["explanation"]


def test_home_backend_data_for_wide_field_target() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _object("messier-M31", "M31", "Galaxy", "3.4", "190 arcmin", 3.17, "WideField"),
        [Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")],
        [Eyepiece("e10", "10 mm", 10, 60)],
        [],
        binoculars=[Binocular("bino", "Nikon Monarch M5", 10, 50)],
    )

    assert suggestion["setupOptions"][0]["role"] == "Consigliato"
    assert suggestion["equipmentType"] == "Binocular"
    assert suggestion["setupText"] == "Nikon Monarch M5 10×50"


def test_home_backend_data_for_high_magnification_target() -> None:
    suggestion = EquipmentService().suggest_for_profile(
        _object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification"),
        [Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")],
        [Eyepiece("e10", "10 mm", 10, 60), Eyepiece("e25", "25 mm", 25, 52)],
        [],
        binoculars=[Binocular("bino", "Nikon Monarch M5", 10, 50)],
    )

    assert suggestion["setupOptions"][0]["role"] == "Consigliato"
    assert suggestion["equipmentType"] == "Telescope"
    assert suggestion["setupText"].startswith("Maksutov 90/1250 +")


def _qml_function_body(name: str) -> str:
    source = HOME_PAGE.read_text(encoding="utf-8")
    marker = f"function {name}"
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : index]
    raise AssertionError(f"Function {name} body not found")


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
