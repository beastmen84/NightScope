"""Protect equipment input, catalogue, profile, and presentation application services."""

from __future__ import annotations

from pathlib import Path

import pytest

from astro_viewer.app.database.equipment_catalog_repository import (
    EquipmentCatalogRepository,
)
from astro_viewer.app.models.equipment import (
    Barlow,
    Binocular,
    Eyepiece,
    FocalReducer,
    Telescope,
)
from astro_viewer.app.services.equipment_catalog_service import (
    EquipmentCatalogService,
    parse_zoom_click_positions,
)
from astro_viewer.app.services.equipment_input import (
    EquipmentInputError,
    parse_astronomy_camera_inputs,
    parse_eyepiece_inputs,
)
from astro_viewer.app.services.equipment_presentation import (
    EquipmentPresentationService,
)
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.profile_equipment_service import (
    PROFILE_EQUIPMENT_KEYS,
    active_profile_state,
    imaging_inventory,
)
from astro_viewer.tests.database_fixture import prepare_database


APP_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = APP_DIR / "data" / "schema.sql"


def test_equipment_catalog_service_loads_one_consistent_snapshot(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "nightscope.db"
    prepare_database(database_path, SCHEMA_PATH)
    repository = EquipmentCatalogRepository(database_path)

    snapshot = EquipmentCatalogService(
        repository,
        EquipmentService(),
    ).load()

    assert snapshot.telescopes[0].id == EquipmentService.NAKED_EYE_ID
    assert len(snapshot.telescopes) == len(snapshot.telescope_catalog_models) + 1
    assert len(snapshot.eyepieces) == len(snapshot.eyepiece_rows)
    assert len(snapshot.barlows) == len(snapshot.barlow_rows)
    assert len(snapshot.binoculars) == len(snapshot.binocular_rows)
    assert len(snapshot.filters) == len(snapshot.filter_rows)
    assert len(snapshot.reducers) == len(snapshot.reducer_rows)


def test_camera_input_parser_normalizes_numbers_without_ui_side_effects() -> None:
    parsed = parse_astronomy_camera_inputs(
        {
            "brand": "ZWO",
            "model": "ASI Test",
            "camera_class": "PLANETARY",
            "sensor_model": "IMX Test",
            "sensor_technology": "CMOS",
            "color_mode": "COLOR",
            "sensor_width_mm": "5,6",
            "sensor_height_mm": "3.2",
            "resolution_width_px": "1920",
            "resolution_height_px": "1080",
            "pixel_size_um": "2,9",
            "bit_depth": "12",
            "max_fps": "60,5",
            "cooled": False,
            "cooling_delta_c": "",
            "shutter_type": "ROLLING",
            "backfocus_mm": "6.5",
            "source_url": "https://example.test/camera",
        }
    )

    assert parsed[6:13] == (5.6, 3.2, 1920, 1080, 2.9, 12, 60.5)
    assert parsed[14] is None
    assert parsed[16] == 6.5


@pytest.mark.parametrize(
    ("values", "error_code"),
    (
        (("Fixed", "bad", "", "", "60", ""), "eyepiece_invalid"),
        (("Fixed", "10", "", "", "60", "70-60"), "eyepiece_afov_invalid"),
        (("Fixed", "0", "", "", "60", ""), "eyepiece_non_positive"),
    ),
)
def test_eyepiece_input_parser_keeps_distinct_validation_errors(
    values: tuple[str, ...],
    error_code: str,
) -> None:
    with pytest.raises(EquipmentInputError) as error:
        parse_eyepiece_inputs(*values)

    assert error.value.code == error_code


def test_zoom_click_parser_deduplicates_and_rejects_invalid_positions() -> None:
    assert parse_zoom_click_positions("24 / 16; 8; 16; 0; bad") == (
        24.0,
        16.0,
        8.0,
    )


def test_profile_state_is_completed_and_inventory_is_scoped_to_assignments() -> None:
    profiles = [{"id": 7, "profile_name": "Imaging", "active": 1}]
    equipment = {"7": {"telescope_ids": ["scope"]}}

    state = active_profile_state(profiles, equipment)
    inventory = imaging_inventory(
        profile=profiles[0],
        state=state,
        telescopes=[_scope()],
        astronomy_camera_rows=[],
        camera_body_rows=[],
        reducers=[_reducer()],
        barlows=[_barlow()],
    )

    assert set(state) == set(PROFILE_EQUIPMENT_KEYS)
    assert tuple(item.id for item in inventory.telescopes) == ("scope",)
    assert inventory.reducers == ()
    assert inventory.barlows == ()


def test_equipment_presentation_separates_catalogue_and_assignment_shapes() -> None:
    presenter = EquipmentPresentationService(EquipmentService())
    state = {
        key: [] for key in PROFILE_EQUIPMENT_KEYS
    }
    state.update(
        {
            "telescope_ids": ["scope"],
            "eyepiece_ids": ["eyepiece"],
            "barlow_ids": ["barlow"],
            "binocular_ids": ["binocular"],
            "full_aperture_solar_filter_telescope_ids": ["scope"],
        }
    )
    equipment = {
        "telescopes": [_scope()],
        "eyepieces": [Eyepiece("eyepiece", "Oculare", 10, 60)],
        "barlows": [_barlow()],
        "binoculars": [Binocular("binocular", "Binocolo", 10, 50)],
        "filter_rows": [],
        "reducer_rows": [],
        "astronomy_camera_rows": [],
        "camera_body_rows": [],
    }

    catalogue = presenter.catalog_items(**equipment)
    assigned = presenter.assigned_items(state=state, **equipment)

    assert all("type" in item for item in catalogue)
    assert all("type" not in item for item in assigned)
    assert assigned[0]["hasFullApertureSolarFilter"] is True
    assert presenter.status_message(
        telescope=_scope(),
        binoculars=[],
        eyepieces=equipment["eyepieces"],
        barlows=equipment["barlows"],
    ).startswith("Profilo attivo: Scope")


def _scope() -> Telescope:
    return Telescope("scope", "Scope", 100, 500, "Rifrattore", "manuale")


def _barlow() -> Barlow:
    return Barlow("barlow", "Barlow", 2.0)


def _reducer() -> FocalReducer:
    return FocalReducer("reducer", "Reducer", 0.8, "REFRACTOR")
