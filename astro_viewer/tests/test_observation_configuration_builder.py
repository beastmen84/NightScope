from __future__ import annotations

import pytest

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.services.observation_configuration_builder import ObservationConfigurationBuilder


def test_telescope_profile_generates_fixed_eyepiece_and_barlow_configurations() -> None:
    telescope = Telescope("scope-200", "Dobson 200", 200, 1000, "Newton", "Dobson")
    eyepieces = [
        Eyepiece("ep-25", "Plossl 25 mm", 25.0, 50.0),
        Eyepiece("ep-10", "Planetary 10 mm", 10.0, 60.0),
    ]
    barlows = [
        Barlow("barlow-2x", "Barlow 2x", 2.0),
        Barlow("barlow-3x", "Barlow 3x", 3.0),
    ]

    configurations = ObservationConfigurationBuilder().build([telescope], eyepieces, barlows)

    assert len(configurations) == 6
    assert {configuration.equipment_type for configuration in configurations} == {"Telescope"}
    assert any(configuration.barlow is None for configuration in configurations)
    assert any(configuration.barlow == barlows[0] for configuration in configurations)
    assert any(configuration.barlow == barlows[1] for configuration in configurations)


def test_telescope_configuration_reuses_existing_optical_calculations() -> None:
    telescope = Telescope("scope-200", "Dobson 200", 200, 1000, "Newton", "Dobson")
    eyepiece = Eyepiece("ep-25", "Plossl 25 mm", 25.0, 50.0)

    configuration = ObservationConfigurationBuilder().build([telescope], [eyepiece])[0]

    assert configuration.configuration_id == "telescope:scope-200:eyepiece:ep-25:focal:25 mm:barlow:none"
    assert configuration.magnification == pytest.approx(40.0)
    assert configuration.true_field_of_view_deg == pytest.approx(1.25)
    assert configuration.exit_pupil_mm == pytest.approx(5.0)
    assert configuration.limiting_magnitude_estimate == pytest.approx(13.505, abs=0.001)
    assert configuration.resolution_estimate == pytest.approx(0.58)
    assert configuration.telescope == telescope
    assert configuration.eyepiece == eyepiece


def test_telescope_without_eyepieces_generates_no_telescope_configurations() -> None:
    telescope = Telescope("scope-200", "Dobson 200", 200, 1000, "Newton", "Dobson")

    configurations = ObservationConfigurationBuilder().build([telescope], [])

    assert configurations == []


def test_zoom_eyepiece_generates_sampled_focal_positions() -> None:
    telescope = Telescope("scope-150", "SCT 150", 150, 1500, "SCT", "Altazimutale")
    zoom = Eyepiece(
        "zoom-8-24",
        "Zoom 8-24 mm",
        24.0,
        68.0,
        eyepiece_type="Zoom",
        min_focal_length_mm=8.0,
        max_focal_length_mm=24.0,
    )

    configurations = ObservationConfigurationBuilder().build([telescope], [zoom])

    assert len(configurations) == 3
    assert {configuration.focal_position_label for configuration in configurations} == {"8 mm", "16 mm", "24 mm"}
    assert {round(configuration.magnification) for configuration in configurations} == {62, 94, 188}


def test_zoom_eyepiece_with_click_positions_generates_only_selectable_positions() -> None:
    telescope = Telescope("scope-150", "SCT 150", 150, 1500, "SCT", "Altazimutale")
    zoom = Eyepiece(
        "hyperion-8-24",
        "Baader Hyperion Zoom 8-24 mm",
        24.0,
        60.0,
        eyepiece_type="Zoom",
        min_focal_length_mm=8.0,
        max_focal_length_mm=24.0,
        zoom_click_positions_mm=(24.0, 20.0, 16.0, 12.0, 8.0),
    )

    configurations = ObservationConfigurationBuilder().build([telescope], [zoom])

    assert {configuration.focal_position_label for configuration in configurations} == {"24 mm", "20 mm", "16 mm", "12 mm", "8 mm"}
    assert {round(configuration.magnification) for configuration in configurations} == {62, 75, 94, 125, 188}


def test_telescope_configuration_builder_accepts_external_focal_position_policy() -> None:
    telescope = Telescope("scope-150", "SCT 150", 150, 1500, "SCT", "Altazimutale")
    zoom = Eyepiece(
        "zoom-8-24",
        "Zoom 8-24 mm",
        24.0,
        68.0,
        eyepiece_type="Zoom",
        min_focal_length_mm=8.0,
        max_focal_length_mm=24.0,
    )

    configurations = ObservationConfigurationBuilder().build_telescope_configurations(
        [telescope],
        [zoom],
        [],
        lambda _telescope, _eyepiece, _barlow: [{"focal": 12.0, "position": "12 mm"}],
    )

    assert len(configurations) == 1
    assert configurations[0].focal_position_label == "12 mm"
    assert configurations[0].magnification == pytest.approx(125.0)


def test_binocular_only_profile_generates_binocular_configuration() -> None:
    binocular = Binocular("nikon-10x50", "Nikon 10x50", 10, 50, image_stabilized=True)

    configurations = ObservationConfigurationBuilder().build([], [], binoculars=[binocular])

    assert len(configurations) == 1
    configuration = configurations[0]
    assert configuration.configuration_id == "binocular:nikon-10x50"
    assert configuration.equipment_type == "Binocular"
    assert configuration.binocular == binocular
    assert configuration.magnification == pytest.approx(10.0)
    assert configuration.exit_pupil_mm == pytest.approx(5.0)
    assert configuration.true_field_of_view_deg is None
    assert configuration.limiting_magnitude_estimate is None
    assert configuration.resolution_estimate is None
    assert configuration.image_stabilized is True


def test_mixed_profile_includes_telescope_and_binocular_configurations() -> None:
    telescope = Telescope("scope-200", "Dobson 200", 200, 1000, "Newton", "Dobson")
    eyepiece = Eyepiece("ep-25", "Plossl 25 mm", 25.0, 50.0)
    barlow = Barlow("barlow-2x", "Barlow 2x", 2.0)
    binocular = Binocular("canon-15x50", "Canon 15x50 IS", 15, 50, image_stabilized=True)

    configurations = ObservationConfigurationBuilder().build(
        [telescope],
        [eyepiece],
        [barlow],
        [binocular],
    )

    assert len(configurations) == 3
    assert [configuration.equipment_type for configuration in configurations].count("Telescope") == 2
    assert [configuration.equipment_type for configuration in configurations].count("Binocular") == 1
    assert any(configuration.barlow == barlow for configuration in configurations)
    assert any(configuration.binocular == binocular for configuration in configurations)


def test_invalid_binocular_is_ignored() -> None:
    invalid = Binocular("broken", "Invalid", 0, 50)

    configurations = ObservationConfigurationBuilder().build([], [], binoculars=[invalid])

    assert configurations == []
