"""Protect valid photographic train enumeration and modifier compatibility."""

from __future__ import annotations

from pathlib import Path

import pytest

from astro_viewer.app.database.equipment_catalog_repository import (
    EquipmentCatalogRepository,
)
from astro_viewer.app.models.equipment import Barlow, FocalReducer, Telescope
from astro_viewer.app.models.imaging import (
    ImagingCamera,
    ImagingCameraKind,
    ImagingModifierKind,
)
from astro_viewer.app.services.imaging_camera_adapter import ImagingCameraAdapter
from astro_viewer.app.services.imaging_train_builder import ImagingTrainBuilder
from astro_viewer.tests.database_fixture import prepare_database


APP_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = APP_DIR / "data" / "schema.sql"


def _telescope() -> Telescope:
    return Telescope(
        id="scope-100",
        name="APO 100",
        aperture_mm=100,
        focal_length_mm=500,
        optical_type="Refractor",
        mount="EQUATORIAL_TRACKING",
    )


def _camera(
    *,
    camera_id: str = "camera-2600",
    kind: ImagingCameraKind = ImagingCameraKind.ASTRONOMY_CAMERA,
) -> ImagingCamera:
    return ImagingCamera(
        id=camera_id,
        name="Camera 2600",
        kind=kind,
        sensor_width_mm=23.5,
        sensor_height_mm=15.7,
        resolution_width_px=6248,
        resolution_height_px=4176,
        pixel_size_um=3.76,
        bit_depth=16,
        backfocus_mm=17.5,
    )


def _reducer(
    *,
    reducer_id: str = "reducer-08",
    imaging_compatible: bool = True,
    compatible_telescope_ids: tuple[str, ...] = ("scope-100",),
) -> FocalReducer:
    return FocalReducer(
        id=reducer_id,
        name="Reducer 0.8x",
        reduction_factor=0.8,
        optical_system="REFRACTOR",
        backfocus_mm=55.0,
        imaging_compatible=imaging_compatible,
        compatible_telescope_ids=compatible_telescope_ids,
    )


def test_astronomy_camera_adapter_preserves_photographic_semantics() -> None:
    camera = ImagingCameraAdapter.from_astronomy_catalogue(
        {
            "catalog_id": "catalog-astronomy-camera-1",
            "display_name": "ZWO ASI2600MC Pro",
            "camera_class": "DEEP_SKY",
            "sensor_technology": "CMOS",
            "color_mode": "COLOR",
            "sensor_width_mm": 23.5,
            "sensor_height_mm": 15.7,
            "resolution_width_px": 6248,
            "resolution_height_px": 4176,
            "pixel_size_um": 3.76,
            "bit_depth": 16,
            "max_fps": 3.51,
            "cooled": True,
            "cooling_delta_c": 35,
            "shutter_type": "ROLLING",
            "backfocus_mm": 17.5,
        }
    )

    assert camera.kind is ImagingCameraKind.ASTRONOMY_CAMERA
    assert camera.id == "catalog-astronomy-camera-1"
    assert camera.camera_class == "DEEP_SKY"
    assert camera.color_mode == "COLOR"
    assert camera.full_resolution_fps == pytest.approx(3.51)
    assert camera.cooled is True
    assert camera.cooling_delta_c == pytest.approx(35.0)
    assert camera.backfocus_mm == pytest.approx(17.5)
    assert camera.video_fps is None


def test_camera_body_adapter_derives_pixel_size_without_relabeling_video_fps() -> None:
    camera = ImagingCameraAdapter.from_camera_body_catalogue(
        {
            "catalog_id": "catalog-camera-body-1",
            "brand": "Sony",
            "model": "Alpha",
            "body_type": "MIRRORLESS",
            "sensor_format": "FULL_FRAME",
            "lens_mount": "Sony E",
            "sensor_width_mm": 36.0,
            "sensor_height_mm": 24.0,
            "resolution_width_px": 6000,
            "resolution_height_px": 4000,
            "raw_bit_depth": 14,
            "max_video_width_px": 3840,
            "max_video_height_px": 2160,
            "max_video_fps": 60,
            "live_view": 1,
            "bulb_mode": "1",
        }
    )

    assert camera.kind is ImagingCameraKind.CAMERA_BODY
    assert camera.name == "Sony Alpha"
    assert camera.pixel_size_um == pytest.approx(6.0)
    assert camera.bit_depth == 14
    assert camera.video_width_px == 3840
    assert camera.video_height_px == 2160
    assert camera.video_fps == pytest.approx(60.0)
    assert camera.full_resolution_fps is None
    assert camera.live_view is True
    assert camera.bulb_mode is True


def test_camera_body_adapter_rejects_non_physical_sensor_geometry() -> None:
    with pytest.raises(ValueError, match="geometry"):
        ImagingCameraAdapter.from_camera_body_catalogue(
            {
                "catalog_id": "invalid",
                "brand": "Invalid",
                "model": "Body",
                "sensor_width_mm": 36,
                "sensor_height_mm": 24,
                "resolution_width_px": 0,
                "resolution_height_px": 4000,
                "raw_bit_depth": 14,
            }
        )


def test_adapter_normalizes_every_seeded_camera(tmp_path: Path) -> None:
    database_path = tmp_path / "nightscope.db"
    prepare_database(database_path, SCHEMA_PATH)
    repository = EquipmentCatalogRepository(database_path)

    cameras = ImagingCameraAdapter.from_catalogues(
        repository.astronomy_cameras(),
        repository.camera_bodies(),
    )

    assert len(cameras) == 77
    assert len({camera.id for camera in cameras}) == 77
    assert sum(
        camera.kind is ImagingCameraKind.ASTRONOMY_CAMERA
        for camera in cameras
    ) == 37
    assert sum(
        camera.kind is ImagingCameraKind.CAMERA_BODY
        for camera in cameras
    ) == 40
    assert all(camera.sensor_diagonal_mm > 0 for camera in cameras)
    assert all(camera.pixel_size_um > 0 for camera in cameras)


def test_prime_focus_configuration_calculates_exact_sensor_geometry() -> None:
    configuration = ImagingTrainBuilder().build(
        [_telescope()],
        [_camera()],
    )[0]

    assert configuration.configuration_id == (
        "imaging:telescope:scope-100:camera:camera-2600:modifier:none"
    )
    assert configuration.modifier_kind is ImagingModifierKind.NONE
    assert configuration.mount_type == "EQUATORIAL_TRACKING"
    assert configuration.focal_length_factor == pytest.approx(1.0)
    assert configuration.effective_focal_length_mm == pytest.approx(500.0)
    assert configuration.effective_focal_ratio == pytest.approx(5.0)
    assert configuration.pixel_scale_arcsec_per_pixel == pytest.approx(
        1.551111343
    )
    assert configuration.field_width_deg == pytest.approx(2.692406083)
    assert configuration.field_height_deg == pytest.approx(1.798939680)
    assert configuration.field_diagonal_deg == pytest.approx(3.237723486)
    assert configuration.reducer is None
    assert configuration.barlow is None
    assert configuration.required_backfocus_mm is None
    assert configuration.additional_backfocus_spacing_mm is None


def test_reducer_configuration_recalculates_scale_field_and_backfocus() -> None:
    configurations = ImagingTrainBuilder().build(
        [_telescope()],
        [_camera()],
        [_reducer()],
    )

    assert len(configurations) == 2
    prime, reduced = configurations
    assert reduced.modifier_kind is ImagingModifierKind.FOCAL_REDUCER
    assert reduced.reducer == _reducer()
    assert reduced.barlow is None
    assert reduced.focal_length_factor == pytest.approx(0.8)
    assert reduced.effective_focal_length_mm == pytest.approx(400.0)
    assert reduced.effective_focal_ratio == pytest.approx(4.0)
    assert reduced.pixel_scale_arcsec_per_pixel == pytest.approx(1.938889179)
    assert reduced.field_width_deg == pytest.approx(3.365159348)
    assert reduced.field_width_deg > prime.field_width_deg
    assert reduced.pixel_scale_arcsec_per_pixel > (
        prime.pixel_scale_arcsec_per_pixel
    )
    assert reduced.required_backfocus_mm == pytest.approx(55.0)
    assert reduced.additional_backfocus_spacing_mm == pytest.approx(37.5)


def test_barlow_configuration_recalculates_scale_and_field_inversely() -> None:
    barlow = Barlow("barlow-2", "Barlow 2x", 2.0)
    configurations = ImagingTrainBuilder().build(
        [_telescope()],
        [_camera()],
        barlows=[barlow],
    )

    assert len(configurations) == 2
    prime, amplified = configurations
    assert amplified.modifier_kind is ImagingModifierKind.BARLOW
    assert amplified.barlow == barlow
    assert amplified.reducer is None
    assert amplified.focal_length_factor == pytest.approx(2.0)
    assert amplified.effective_focal_length_mm == pytest.approx(1000.0)
    assert amplified.effective_focal_ratio == pytest.approx(10.0)
    assert amplified.pixel_scale_arcsec_per_pixel == pytest.approx(0.775555671)
    assert amplified.field_width_deg == pytest.approx(1.346388859)
    assert amplified.field_width_deg < prime.field_width_deg
    assert amplified.pixel_scale_arcsec_per_pixel < (
        prime.pixel_scale_arcsec_per_pixel
    )


def test_equal_multiplier_barlows_form_one_optically_distinct_train() -> None:
    configurations = ImagingTrainBuilder().build(
        [_telescope()],
        [_camera()],
        barlows=[
            Barlow("barlow-a", "Barlow A 2x", 2.0),
            Barlow("barlow-b", "Barlow B 2x", 2.0),
        ],
    )

    amplified = [
        configuration
        for configuration in configurations
        if configuration.barlow is not None
    ]
    assert len(configurations) == 2
    assert len(amplified) == 1
    assert amplified[0].barlow is not None
    assert amplified[0].barlow.id == "equivalent-barlow:2"
    assert amplified[0].barlow.multiplier == pytest.approx(2.0)
    assert "2 opzioni equivalenti" in amplified[0].barlow.name


def test_builder_never_stacks_reducer_and_barlow() -> None:
    configurations = ImagingTrainBuilder().build(
        [_telescope()],
        [_camera()],
        [_reducer()],
        [Barlow("barlow-2", "Barlow 2x", 2.0)],
    )

    assert len(configurations) == 3
    assert {
        configuration.modifier_kind
        for configuration in configurations
    } == {
        ImagingModifierKind.NONE,
        ImagingModifierKind.FOCAL_REDUCER,
        ImagingModifierKind.BARLOW,
    }
    assert all(
        not (configuration.reducer and configuration.barlow)
        for configuration in configurations
    )


def test_reducer_requires_imaging_flag_and_exact_telescope_link() -> None:
    reducers = [
        _reducer(reducer_id="compatible"),
        _reducer(
            reducer_id="visual-only",
            imaging_compatible=False,
        ),
        _reducer(
            reducer_id="descriptive-only",
            compatible_telescope_ids=(),
        ),
        _reducer(
            reducer_id="other-scope",
            compatible_telescope_ids=("scope-200",),
        ),
    ]

    configurations = ImagingTrainBuilder().build(
        [_telescope()],
        [_camera()],
        reducers,
    )

    assert len(configurations) == 2
    assert [
        configuration.reducer.id
        for configuration in configurations
        if configuration.reducer is not None
    ] == ["compatible"]


def test_builder_filters_invalid_rows_and_deduplicates_stable_ids() -> None:
    invalid_telescope = Telescope(
        "invalid-scope",
        "Invalid",
        0,
        500,
        "Refractor",
        "OTA",
    )
    invalid_camera = ImagingCamera(
        id="invalid-camera",
        name="Invalid",
        kind=ImagingCameraKind.ASTRONOMY_CAMERA,
        sensor_width_mm=0,
        sensor_height_mm=10,
        resolution_width_px=1000,
        resolution_height_px=1000,
        pixel_size_um=3,
        bit_depth=12,
    )
    valid_camera = _camera()
    duplicate_camera = _camera(kind=ImagingCameraKind.CAMERA_BODY)

    configurations = ImagingTrainBuilder().build(
        [_telescope(), _telescope(), invalid_telescope],
        [valid_camera, duplicate_camera, invalid_camera],
        [_reducer(), _reducer()],
        [
            Barlow("barlow-2", "Barlow 2x", 2.0),
            Barlow("barlow-2", "Duplicate", 3.0),
            Barlow("barlow-invalid", "Invalid", 1.0),
        ],
    )

    assert len(configurations) == 3
    assert len(
        {configuration.configuration_id for configuration in configurations}
    ) == 3
    assert all(
        configuration.telescope.id == "scope-100"
        for configuration in configurations
    )
    assert all(
        configuration.camera.kind is ImagingCameraKind.ASTRONOMY_CAMERA
        for configuration in configurations
    )
