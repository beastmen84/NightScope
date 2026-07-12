from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.equipment import Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_service import EquipmentService


HOME_PAGE = Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "HomePage.qml"


def test_home_lower_surface_uses_backend_overview_contract() -> None:
    source = HOME_PAGE.read_text(encoding="utf-8")

    assert "controller.homeNightPlanOverview" in source
    assert "controller.calendarOverview" in source
    assert "model: root.filteredNightPlanItems()" in source
    assert "return root.skyCompassScopedItems(root.nightPlanOverview.items || [])" in source
    assert "model: root.filteredNightAlternatives()" in source
    assert "HomePlanStepRow" in source
    assert "HomeVisibleTargetRow" in source
    assert "function displaySetupOption" not in source
    assert "function recommendationReason" not in source
    assert "function visibilityLabel" not in source
    assert "controller.nightPlan.slice" not in source
    assert "scoreText:" not in source
    assert "equipmentExplanation" not in source
    assert "controller.events" not in source
    assert "signal openEvent(string eventId)" in source
    assert "signal openCalendar()" in source
    assert 'headerActionText: "Vedi tutti"' in source


def test_home_alternatives_capture_wheel_events_while_the_list_can_scroll() -> None:
    source = HOME_PAGE.read_text(encoding="utf-8")
    visible_target_list = source.split("id: visibleTargetList", 1)[1].split(
        "ScrollBar.vertical:", 1
    )[0]

    assert "WheelHandler {" in visible_target_list
    assert "enabled: visibleTargetList.interactive" in visible_target_list
    assert "acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad" in visible_target_list
    assert "blocking: true" in visible_target_list
    assert "visibleTargetList.contentY - delta" in visible_target_list
    assert "event.accepted = true" in visible_target_list


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
