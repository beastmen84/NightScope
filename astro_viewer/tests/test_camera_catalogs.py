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

        assert len(astronomy_cameras) == 37
        assert len(camera_bodies) == 40
        assert {item["brand"] for item in astronomy_cameras} == {
            "Atik",
            "Player One Astronomy",
            "QHYCCD",
            "SVBONY",
            "ZWO",
        }
        assert {item["brand"] for item in camera_bodies} == {
            "Canon",
            "Fujifilm",
            "Nikon",
            "OM System",
            "Panasonic",
            "Pentax",
            "Sigma",
            "Sony",
        }
        assert sum(
            item["brand"] == "SVBONY" for item in astronomy_cameras
        ) == 7
        assert sum(
            item["body_type"] == "MIRRORLESS" for item in camera_bodies
        ) == 33
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
        for item in astronomy_cameras:
            expected_width = (
                item["resolution_width_px"] * item["pixel_size_um"] / 1000.0
            )
            expected_height = (
                item["resolution_height_px"] * item["pixel_size_um"] / 1000.0
            )
            assert abs(item["sensor_width_mm"] - expected_width) < 0.15
            assert abs(item["sensor_height_mm"] - expected_height) < 0.15

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
        assert "EquipmentProfileAstronomyCamera" in tables
        assert "EquipmentProfileCameraBody" in tables
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
        identities = [
            (row["brand"].casefold(), row["model"].casefold())
            for row in rows
        ]
        assert len(identities) == len(set(identities))


def test_schema_19_upgrade_adds_camera_catalogs_and_profile_links() -> None:
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

        assert len(upgraded.astronomy_cameras()) == 37
        assert len(upgraded.camera_bodies()) == 40
        assert upgraded.profiles() == profile_snapshot
        with closing(sqlite3.connect(database_path)) as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 21
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        assert "EquipmentProfileAstronomyCamera" in tables
        assert "EquipmentProfileCameraBody" in tables
    finally:
        temporary_directory.cleanup()


def test_schema_20_upgrade_preserves_profiles_and_adds_empty_camera_links() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        profile_snapshot = repository.profiles()
        with closing(sqlite3.connect(database_path)) as connection:
            connection.execute("DROP TABLE EquipmentProfileAstronomyCamera")
            connection.execute("DROP TABLE EquipmentProfileCameraBody")
            connection.execute("PRAGMA user_version = 20")
            connection.commit()

        initialize_database(database_path, SCHEMA_PATH)
        upgraded = EquipmentCatalogRepository(database_path)
        profile_id = int(upgraded.profiles()[0]["id"])

        assert upgraded.profiles() == profile_snapshot
        assert upgraded.profile_astronomy_camera_ids(profile_id) == []
        assert upgraded.profile_camera_body_ids(profile_id) == []
        with closing(sqlite3.connect(database_path)) as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 21
    finally:
        temporary_directory.cleanup()


def test_custom_camera_crud_preserves_unrelated_profiles() -> None:
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


def test_camera_profile_assignments_are_persistent_and_profile_scoped() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        active_profile = repository.active_profile()
        assert active_profile is not None
        active_profile_id = int(active_profile["id"])
        astronomy_camera = next(
            item
            for item in repository.astronomy_cameras()
            if item["brand"] == "SVBONY"
        )
        camera_body = next(
            item
            for item in repository.camera_bodies()
            if item["body_type"] == "MIRRORLESS"
        )

        repository.assign_profile_astronomy_camera(
            active_profile_id,
            astronomy_camera["catalog_id"],
        )
        repository.assign_profile_camera_body(
            active_profile_id,
            camera_body["catalog_id"],
        )
        repository.add_profile("Secondario", "preset:naked-eye")
        secondary = next(
            item
            for item in repository.profiles()
            if item["profile_name"] == "Secondario"
        )
        secondary_id = int(secondary["id"])

        reopened = EquipmentCatalogRepository(database_path)
        assert reopened.profile_astronomy_camera_ids(active_profile_id) == [
            astronomy_camera["catalog_id"]
        ]
        assert reopened.profile_camera_body_ids(active_profile_id) == [
            camera_body["catalog_id"]
        ]
        assert reopened.profile_astronomy_camera_ids(secondary_id) == []
        assert reopened.profile_camera_body_ids(secondary_id) == []
        assert reopened.profile_usage_count(
            "astronomy_camera",
            astronomy_camera["catalog_id"],
        ) == 1
        assert reopened.profile_usage_count(
            "camera_body",
            camera_body["catalog_id"],
        ) == 1

        reopened.remove_profile_astronomy_camera(
            active_profile_id,
            astronomy_camera["catalog_id"],
        )
        reopened.remove_profile_camera_body(
            active_profile_id,
            camera_body["catalog_id"],
        )
        assert reopened.profile_astronomy_camera_ids(active_profile_id) == []
        assert reopened.profile_camera_body_ids(active_profile_id) == []
    finally:
        temporary_directory.cleanup()


def test_custom_camera_delete_requires_explicit_profile_cleanup() -> None:
    temporary_directory, _, repository = _database()
    try:
        profile = repository.active_profile()
        assert profile is not None
        profile_id = int(profile["id"])
        assert repository.add_astronomy_camera(
            "NightScope",
            "Profile camera",
            "DEEP_SKY",
            "Test CMOS",
            "CMOS",
            "COLOR",
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
        )[0]
        assert repository.add_camera_body(
            "NightScope",
            "Profile body",
            "MIRRORLESS",
            "APS_C",
            "Test mount",
            23.5,
            15.7,
            6000,
            4000,
            14,
            None,
            None,
            None,
            True,
            True,
        )[0]
        astronomy_camera = next(
            item
            for item in repository.astronomy_cameras()
            if item["model"] == "Profile camera"
        )
        camera_body = next(
            item
            for item in repository.camera_bodies()
            if item["model"] == "Profile body"
        )
        repository.assign_profile_astronomy_camera(
            profile_id,
            astronomy_camera["catalog_id"],
        )
        repository.assign_profile_camera_body(
            profile_id,
            camera_body["catalog_id"],
        )

        assert not repository.delete_astronomy_camera(astronomy_camera["id"])[0]
        assert not repository.delete_camera_body(camera_body["id"])[0]
        assert repository.delete_astronomy_camera(
            astronomy_camera["id"],
            remove_from_profiles=True,
        )[0]
        assert repository.delete_camera_body(
            camera_body["id"],
            remove_from_profiles=True,
        )[0]
        assert repository.profile_astronomy_camera_ids(profile_id) == []
        assert repository.profile_camera_body_ids(profile_id) == []
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


def test_camera_navigation_profile_ui_and_packaging_are_wired() -> None:
    cameras_qml = (
        APP_DIR / "app" / "ui" / "pages" / "EquipmentCamerasPage.qml"
    ).read_text(encoding="utf-8")
    telescopes_qml = (
        APP_DIR / "app" / "ui" / "pages" / "EquipmentTelescopesPage.qml"
    ).read_text(encoding="utf-8")
    profiles_qml = (
        APP_DIR / "app" / "ui" / "pages" / "EquipmentProfilesPage.qml"
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
    assert '"astronomy_camera"' in profiles_qml
    assert '"camera_body"' in profiles_qml
    assert "Capacità visuali del profilo" in profiles_qml
    assert "root.width > 1500 ? 4" in profiles_qml
    assert "Layout.alignment: Qt.AlignTop" in profiles_qml
    assert "cameraTagsInline" in profiles_qml
    assert cameras_qml.count("uniformCellWidths: true") == 2
    assert "Larghezza sensore (mm) *" in cameras_qml
    assert "Altezza sensore (mm) *" in cameras_qml
    assert "Passo pixel (µm) *" in cameras_qml
    assert "Modello sensore *" in cameras_qml
    assert "Tecnologia sensore *" in cameras_qml
    assert "Modalità colore *" in cameras_qml
    assert "Risoluzione orizzontale (px) *" in cameras_qml
    assert "Risoluzione verticale (px) *" in cameras_qml
    assert "FPS a piena risoluzione (facoltativo)" in cameras_qml
    assert "ΔT massimo sotto ambiente (°C)" in cameras_qml
    assert "FPS alla risoluzione video indicata" in cameras_qml
    assert "Modalità Bulb" in cameras_qml
    assert "telescopeMountTypeOptions" in telescopes_qml
    assert "DarkComboBox" in telescopes_qml
    assert "astronomy_camera_catalog_seed.csv" in spec
    assert "camera_body_catalog_seed.csv" in spec
