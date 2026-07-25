from __future__ import annotations

import csv
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from astro_viewer.app.database.bootstrap import SCHEMA_VERSION, initialize_database
from astro_viewer.app.database.equipment_catalog_repository import (
    EquipmentCatalogRepository,
)
from astro_viewer.app.services.equipment_taxonomy import (
    ASTRONOMY_CAMERA_CLASS_LABELS,
    CAMERA_BODY_TYPE_LABELS,
    CAMERA_SENSOR_FORMAT_LABELS,
    MOUNT_TYPE_LABELS,
    SENSOR_COLOR_MODE_LABELS,
    canonical_mount_type,
    mount_tracking_capability,
)


APP_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = APP_DIR / "data" / "schema.sql"


def _database() -> tuple[TemporaryDirectory, Path, EquipmentCatalogRepository]:
    temporary_directory = TemporaryDirectory()
    database_path = Path(temporary_directory.name) / "nightscope.db"
    initialize_database(database_path, SCHEMA_PATH)
    return (
        temporary_directory,
        database_path,
        EquipmentCatalogRepository(database_path),
    )


def test_camera_seeds_are_structured_representative_and_source_linked() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        astronomy_cameras = repository.astronomy_cameras()
        camera_bodies = repository.camera_bodies()

        assert len(astronomy_cameras) == 17
        assert len(camera_bodies) == 15
        assert {item["brand"] for item in astronomy_cameras} == {
            "Atik",
            "Player One Astronomy",
            "QHYCCD",
            "ZWO",
        }
        assert {item["brand"] for item in camera_bodies} == {
            "Canon",
            "Fujifilm",
            "Nikon",
            "OM System",
            "Panasonic",
            "Pentax",
            "Sony",
        }
        assert {item["camera_class"] for item in astronomy_cameras} == set(
            ASTRONOMY_CAMERA_CLASS_LABELS
        )
        assert {item["color_mode"] for item in astronomy_cameras} == set(
            SENSOR_COLOR_MODE_LABELS
        )
        assert {item["body_type"] for item in camera_bodies} == set(
            CAMERA_BODY_TYPE_LABELS
        )
        assert {item["sensor_format"] for item in camera_bodies} == set(
            CAMERA_SENSOR_FORMAT_LABELS
        )
        assert any(item["cooled"] for item in astronomy_cameras)
        assert any(not item["cooled"] for item in astronomy_cameras)
        assert any(item["max_fps"] > 100 for item in astronomy_cameras)
        assert all(item["source_url"].startswith("https://") for item in astronomy_cameras)
        assert all(item["source_url"].startswith("https://") for item in camera_bodies)
        assert all(item["pixel_size_um"] > 0 for item in camera_bodies)

        with closing(sqlite3.connect(database_path)) as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        assert "AstronomyCameraCatalog" in tables
        assert "CameraBodyCatalog" in tables
        assert "EquipmentProfileAstronomyCamera" not in tables
        assert "EquipmentProfileCameraBody" not in tables
    finally:
        temporary_directory.cleanup()


def test_camera_seed_files_have_explicit_unique_keys_and_expected_fields() -> None:
    expectations = {
        "astronomy_camera_catalog_seed.csv": (
            "astro-camera::",
            [
                "seed_key",
                "brand",
                "model",
                "camera_class",
                "sensor_model",
                "sensor_technology",
                "color_mode",
                "sensor_width_mm",
                "sensor_height_mm",
                "resolution_width_px",
                "resolution_height_px",
                "pixel_size_um",
                "bit_depth",
                "max_fps",
                "cooled",
                "cooling_delta_c",
                "shutter_type",
                "backfocus_mm",
                "source_url",
            ],
        ),
        "camera_body_catalog_seed.csv": (
            "camera-body::",
            [
                "seed_key",
                "brand",
                "model",
                "body_type",
                "sensor_format",
                "lens_mount",
                "sensor_width_mm",
                "sensor_height_mm",
                "resolution_width_px",
                "resolution_height_px",
                "raw_bit_depth",
                "max_video_width_px",
                "max_video_height_px",
                "max_video_fps",
                "live_view",
                "bulb_mode",
                "source_url",
            ],
        ),
    }
    for filename, (prefix, fieldnames) in expectations.items():
        with (APP_DIR / "data" / filename).open(
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)
            rows = list(reader)
        assert reader.fieldnames == fieldnames
        seed_keys = [row["seed_key"] for row in rows]
        assert all(seed_key.startswith(prefix) for seed_key in seed_keys)
        assert len(seed_keys) == len(set(seed_keys))


def test_schema_19_upgrade_adds_camera_catalogs_without_changing_profiles() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        profile_snapshot = repository.profiles()
        with closing(sqlite3.connect(database_path)) as connection:
            connection.execute("DROP TABLE AstronomyCameraCatalog")
            connection.execute("DROP TABLE CameraBodyCatalog")
            connection.execute("PRAGMA user_version = 19")
            connection.commit()

        initialize_database(database_path, SCHEMA_PATH)
        upgraded = EquipmentCatalogRepository(database_path)

        assert len(upgraded.astronomy_cameras()) == 17
        assert len(upgraded.camera_bodies()) == 15
        assert upgraded.profiles() == profile_snapshot
        with closing(sqlite3.connect(database_path)) as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 20
    finally:
        temporary_directory.cleanup()


def test_custom_camera_crud_is_catalog_only() -> None:
    temporary_directory, _, repository = _database()
    try:
        profile_snapshot = repository.profiles()
        ok, _ = repository.add_astronomy_camera(
            "NightScope",
            "Deep Test",
            "DEEP_SKY",
            "Test CMOS",
            "CMOS",
            "MONO",
            12.0,
            8.0,
            3000,
            2000,
            4.0,
            16,
            12.5,
            True,
            35.0,
            "GLOBAL",
            17.5,
            "https://example.com/deep-test",
        )
        assert ok
        camera = next(
            item
            for item in repository.astronomy_cameras()
            if item["brand"] == "NightScope"
        )
        assert not camera["is_builtin"]
        assert camera["camera_class_label"] == "Cielo profondo"
        assert camera["cooling_delta_c"] == 35.0

        ok, _ = repository.update_astronomy_camera(
            camera["id"],
            "NightScope",
            "Planet Test",
            "PLANETARY",
            "Test CMOS",
            "CMOS",
            "COLOR",
            8.0,
            4.5,
            1920,
            1080,
            2.9,
            12,
            120.0,
            False,
            40.0,
            "ROLLING",
            12.5,
            "",
        )
        assert ok
        camera = next(
            item
            for item in repository.astronomy_cameras()
            if item["brand"] == "NightScope"
        )
        assert camera["model"] == "Planet Test"
        assert not camera["cooled"]
        assert camera["cooling_delta_c"] is None

        ok, _ = repository.add_camera_body(
            "NightScope",
            "Body Test",
            "MIRRORLESS",
            "APS_C",
            "Test mount",
            23.5,
            15.7,
            6000,
            4000,
            14,
            3840,
            2160,
            60.0,
            True,
            True,
            "https://example.com/body-test",
        )
        assert ok
        body = next(
            item
            for item in repository.camera_bodies()
            if item["brand"] == "NightScope"
        )
        assert not body["is_builtin"]
        assert 3.8 < body["pixel_size_um"] < 4.0

        ok, _ = repository.update_camera_body(
            body["id"],
            "NightScope",
            "Body Test II",
            "DSLR",
            "FULL_FRAME",
            "Test mount II",
            36.0,
            24.0,
            6000,
            4000,
            14,
            None,
            None,
            None,
            True,
            True,
            "",
        )
        assert ok
        body = next(
            item
            for item in repository.camera_bodies()
            if item["brand"] == "NightScope"
        )
        assert body["model"] == "Body Test II"
        assert body["max_video_label"] == ""

        assert repository.profiles() == profile_snapshot
        assert repository.delete_astronomy_camera(camera["id"])[0]
        assert repository.delete_camera_body(body["id"])[0]
    finally:
        temporary_directory.cleanup()


def test_camera_validation_and_builtin_protection() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        invalid_astronomy_camera = repository.add_astronomy_camera(
            "NightScope",
            "Invalid",
            "UNKNOWN",
            "Sensor",
            "CMOS",
            "COLOR",
            10.0,
            10.0,
            1000,
            1000,
            3.0,
            12,
            None,
            False,
            None,
            "ROLLING",
            None,
        )
        invalid_camera_body = repository.add_camera_body(
            "NightScope",
            "Invalid",
            "MIRRORLESS",
            "APS_C",
            "Mount",
            20.0,
            15.0,
            4000,
            3000,
            14,
            3840,
            None,
            60.0,
            True,
            True,
        )
        assert not invalid_astronomy_camera[0]
        assert not invalid_camera_body[0]

        astronomy_camera = repository.astronomy_cameras()[0]
        camera_body = repository.camera_bodies()[0]
        assert not repository.delete_astronomy_camera(astronomy_camera["id"])[0]
        assert not repository.delete_camera_body(camera_body["id"])[0]

        ok, _ = repository.update_astronomy_camera(
            astronomy_camera["id"],
            astronomy_camera["brand"],
            f"{astronomy_camera['model']} personalizzata",
            astronomy_camera["camera_class"],
            astronomy_camera["sensor_model"],
            astronomy_camera["sensor_technology"],
            astronomy_camera["color_mode"],
            astronomy_camera["sensor_width_mm"],
            astronomy_camera["sensor_height_mm"],
            astronomy_camera["resolution_width_px"],
            astronomy_camera["resolution_height_px"],
            astronomy_camera["pixel_size_um"],
            astronomy_camera["bit_depth"],
            astronomy_camera["max_fps"],
            astronomy_camera["cooled"],
            astronomy_camera["cooling_delta_c"],
            astronomy_camera["shutter_type"],
            astronomy_camera["backfocus_mm"],
            astronomy_camera["source_url"],
        )
        assert ok
        initialize_database(database_path, SCHEMA_PATH)
        refreshed = EquipmentCatalogRepository(database_path)
        persisted = next(
            item
            for item in refreshed.astronomy_cameras()
            if item["id"] == astronomy_camera["id"]
        )
        assert persisted["model"].endswith("personalizzata")
        assert persisted["is_builtin"]
        assert persisted["is_user_modified"]
    finally:
        temporary_directory.cleanup()


def test_mount_taxonomy_normalizes_seed_aliases_without_visual_score_drift() -> None:
    temporary_directory, _, repository = _database()
    try:
        models = repository.models()
        assert {item["mount_type"] for item in models}.issubset(MOUNT_TYPE_LABELS)
        assert all(item["mount_type_label"] for item in models)

        aliases = {
            "OTA": "OTA",
            "manuale": "MANUAL_UNSPECIFIED",
            "altazimutale": "ALTAZ_MANUAL",
            "GoTo altazimutale": "ALTAZ_GOTO",
            "altazimutale PushTo": "ALTAZ_PUSHTO",
            "equatoriale": "EQUATORIAL_MANUAL",
            "equatoriale CG-4": "EQUATORIAL_MANUAL",
            "GoTo forcella": "FORK_GOTO",
            "Dobson": "DOBSONIAN_MANUAL",
            "Dobson tabletop": "DOBSONIAN_MANUAL",
            "Dobson collassabile": "DOBSONIAN_MANUAL",
            "Dobson PushTo": "DOBSONIAN_PUSHTO",
        }
        for legacy, canonical in aliases.items():
            assert canonical_mount_type(legacy) == canonical
            assert mount_tracking_capability(legacy) == mount_tracking_capability(
                canonical
            )

        ok, _ = repository.add_telescope_model(
            "NightScope",
            "Dobson test",
            "Newton",
            200,
            1200,
            "Dobson",
        )
        assert ok
        custom = next(item for item in repository.models() if item["brand"] == "NightScope")
        assert custom["mount_type"] == "DOBSONIAN_MANUAL"
        assert not repository.add_telescope_model(
            "NightScope",
            "Unknown mount",
            "Newton",
            200,
            1200,
            "testo libero",
        )[0]
    finally:
        temporary_directory.cleanup()


def test_camera_page_navigation_and_packaging_are_wired_without_profile_controls() -> None:
    cameras_qml = (
        APP_DIR / "app" / "ui" / "pages" / "EquipmentCamerasPage.qml"
    ).read_text(encoding="utf-8")
    telescopes_qml = (
        APP_DIR / "app" / "ui" / "pages" / "EquipmentTelescopesPage.qml"
    ).read_text(encoding="utf-8")
    main_qml = (APP_DIR / "app" / "ui" / "main.qml").read_text(encoding="utf-8")
    spec = (APP_DIR.parent / "packaging" / "NightScope.spec").read_text(
        encoding="utf-8"
    )

    assert "EquipmentCamerasPage" in main_qml
    assert 'window.currentPage === "equipmentCameras"' in main_qml
    assert "astronomyCameraCatalog" in cameras_qml
    assert "cameraBodyCatalog" in cameras_qml
    assert "assignEquipmentToActiveProfile" not in cameras_qml
    assert "activeEquipmentProfile" not in cameras_qml
    assert "telescopeMountTypeOptions" in telescopes_qml
    assert "DarkComboBox" in telescopes_qml
    assert "astronomy_camera_catalog_seed.csv" in spec
    assert "camera_body_catalog_seed.csv" in spec
