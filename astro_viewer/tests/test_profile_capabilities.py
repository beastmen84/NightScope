from __future__ import annotations

import pytest

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.observation_configuration_builder import ObservationConfigurationBuilder


def test_profile_capabilities_with_multiple_eyepieces_preserve_display_values() -> None:
    capabilities = EquipmentService().profile_capabilities(
        _newton(),
        [_eyepiece_32(), _eyepiece_10()],
        [],
    )

    assert capabilities["availableMagnificationMin"] == "20x"
    assert capabilities["availableMagnificationMax"] == "65x"
    assert capabilities["exitPupilMin"] == "2,0 mm"
    assert capabilities["exitPupilMax"] == "6,5 mm"
    assert capabilities["trueFieldMin"] == "0,92°"
    assert capabilities["trueFieldMax"] == "3,40°"
    assert capabilities["availableConfigurationsText"] == "20x, 65x"
    assert capabilities["availableConfigurations"] == [
        {
            "label": "32 mm",
            "magnification": "20x",
            "magnificationValue": 20.0,
            "trueFieldValue": 3.4,
            "exitPupilValue": 6.5,
            "barlow": "No",
        },
        {
            "label": "10 mm",
            "magnification": "65x",
            "magnificationValue": 65.0,
            "trueFieldValue": pytest.approx(0.9230769231),
            "exitPupilValue": 2.0,
            "barlow": "No",
        },
    ]


def test_profile_capabilities_include_barlow_and_no_barlow_configurations() -> None:
    capabilities = EquipmentService().profile_capabilities(
        _newton(),
        [_eyepiece_32(), _eyepiece_10()],
        [_barlow()],
    )

    assert capabilities["availableMagnificationMax"] == "130x"
    assert capabilities["exitPupilMin"] == "1,0 mm"
    assert capabilities["trueFieldMin"] == "0,46°"
    assert capabilities["availableConfigurationsText"] == "20x, 41x, 65x, 130x"
    assert [(item["label"], item["magnification"], item["barlow"]) for item in capabilities["availableConfigurations"]] == [
        ("32 mm", "20x", "No"),
        ("32 mm", "41x", "Barlow 2x"),
        ("10 mm", "65x", "No"),
        ("10 mm", "130x", "Barlow 2x"),
    ]


def test_profile_capabilities_preserve_zoom_sampling() -> None:
    capabilities = EquipmentService().profile_capabilities(
        _newton(),
        [_zoom()],
        [_barlow()],
    )

    assert capabilities["availableMagnificationMin"] == "27x"
    assert capabilities["availableMagnificationMax"] == "162x"
    assert capabilities["availableConfigurationsText"] == "27x, 41x, 54x, 81x, 81x, 162x"
    assert [(item["label"], item["magnification"], item["barlow"]) for item in capabilities["availableConfigurations"]] == [
        ("Baader Hyperion Zoom @ 24 mm", "27x", "No"),
        ("Baader Hyperion Zoom @ 16 mm", "41x", "No"),
        ("Baader Hyperion Zoom @ 24 mm", "54x", "Barlow 2x"),
        ("Baader Hyperion Zoom @ 8 mm", "81x", "No"),
        ("Baader Hyperion Zoom @ 16 mm", "81x", "Barlow 2x"),
        ("Baader Hyperion Zoom @ 8 mm", "162x", "Barlow 2x"),
    ]


def test_profile_capabilities_use_telescope_configurations_only_when_binoculars_exist() -> None:
    telescope = _newton()
    eyepieces = [_eyepiece_32()]
    barlows = [_barlow()]
    binocular = Binocular("bino", "Nikon Monarch M5", 10, 50)

    builder_configurations = ObservationConfigurationBuilder().build(
        [telescope],
        eyepieces,
        barlows,
        [binocular],
    )
    capabilities = EquipmentService().profile_capabilities(telescope, eyepieces, barlows)

    assert {configuration.equipment_type for configuration in builder_configurations} == {"Telescope", "Binocular"}
    assert all(item["label"] == "32 mm" for item in capabilities["availableConfigurations"])
    assert all("Nikon" not in str(item) for item in capabilities["availableConfigurations"])


def test_profile_capabilities_match_builder_telescope_configuration_count() -> None:
    telescope = _newton()
    eyepieces = [_eyepiece_32(), _zoom()]
    barlows = [_barlow()]

    builder_configurations = ObservationConfigurationBuilder().build_telescope_configurations(
        [telescope],
        eyepieces,
        barlows,
    )
    capabilities = EquipmentService().profile_capabilities(telescope, eyepieces, barlows)

    assert len(capabilities["availableConfigurations"]) == len(builder_configurations)


def _newton() -> Telescope:
    return Telescope("scope", "Newton 130/650", 130, 650, "Newton", "manuale")


def _eyepiece_32() -> Eyepiece:
    return Eyepiece("e32", "32 mm", 32, 68)


def _eyepiece_10() -> Eyepiece:
    return Eyepiece("e10", "10 mm", 10, 60)


def _zoom() -> Eyepiece:
    return Eyepiece(
        "zoom",
        "Baader Hyperion Zoom",
        24,
        60,
        "Zoom",
        8,
        24,
    )


def _barlow() -> Barlow:
    return Barlow("b2", "Barlow 2x", 2.0)
