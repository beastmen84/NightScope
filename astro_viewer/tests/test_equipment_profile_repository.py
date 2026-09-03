"""Protect profile persistence, legacy access, and cross-repository atomicity."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from astro_viewer.app.database.bootstrap import SCHEMA_VERSION, initialize_database
from astro_viewer.app.database.equipment_catalog_repository import (
    EquipmentCatalogRepository,
)
from astro_viewer.app.database.equipment_profile_repository import (
    EquipmentProfileRepository,
)

APP_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = APP_DIR / "data" / "schema.sql"


def _initialized_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "nightscope.db"
    initialize_database(database_path, SCHEMA_PATH)
    return database_path


def test_existing_profile_and_all_assignments_survive_repository_split(
        tmp_path: Path,
) -> None:
    database_path = _initialized_database(tmp_path)
    legacy_repository = EquipmentCatalogRepository(database_path)

    telescope_id = legacy_repository.models()[0]["catalog_id"]
    eyepiece_id = legacy_repository.eyepieces()[0]["catalog_id"]
    barlow_id = legacy_repository.barlows()[0]["catalog_id"]
    binocular_id = legacy_repository.binoculars()[0]["catalog_id"]
    filter_id = legacy_repository.filters()[0]["catalog_id"]
    reducer_id = legacy_repository.reducers()[0]["catalog_id"]
    astronomy_camera_id = legacy_repository.astronomy_cameras()[0]["catalog_id"]
    camera_body_id = legacy_repository.camera_bodies()[0]["catalog_id"]

    legacy_repository.add_profile(
        "Profilo installazione esistente",
        telescope_id,
        active=True,
    )
    profile = legacy_repository.active_profile()
    assert profile is not None
    profile_id = int(profile["id"])
    legacy_repository.assign_profile_eyepiece(profile_id, eyepiece_id)
    legacy_repository.assign_profile_barlow(profile_id, barlow_id)
    legacy_repository.assign_profile_binocular(profile_id, binocular_id)
    legacy_repository.assign_profile_filter(profile_id, filter_id)
    legacy_repository.assign_profile_reducer(profile_id, reducer_id)
    legacy_repository.assign_profile_astronomy_camera(
        profile_id,
        astronomy_camera_id,
    )
    legacy_repository.assign_profile_camera_body(profile_id, camera_body_id)
    assert legacy_repository.set_profile_full_aperture_solar_filter(
        profile_id,
        telescope_id,
        True,
    )

    with closing(sqlite3.connect(database_path)) as connection:
        version_before = int(connection.execute("PRAGMA user_version").fetchone()[0])
        rows_before = _profile_row_counts(connection)

    initialize_database(database_path, SCHEMA_PATH)
    profile_repository = EquipmentProfileRepository(database_path)

    active = profile_repository.active_profile()
    assert active is not None
    assert int(active["id"]) == profile_id
    assert active["profile_name"] == "Profilo installazione esistente"
    assert telescope_id in profile_repository.profile_telescope_ids(profile_id)
    assert telescope_id in (
        profile_repository.profile_full_aperture_solar_filter_telescope_ids(
            profile_id
        )
    )
    assert eyepiece_id in profile_repository.profile_eyepiece_ids(profile_id)
    assert barlow_id in profile_repository.profile_barlow_ids(profile_id)
    assert binocular_id in profile_repository.profile_binocular_ids(profile_id)
    assert filter_id in profile_repository.profile_filter_ids(profile_id)
    assert reducer_id in profile_repository.profile_reducer_ids(profile_id)
    assert astronomy_camera_id in (
        profile_repository.profile_astronomy_camera_ids(profile_id)
    )
    assert camera_body_id in profile_repository.profile_camera_body_ids(profile_id)

    with closing(sqlite3.connect(database_path)) as connection:
        assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == (
            version_before
        )
        assert version_before == SCHEMA_VERSION
        assert _profile_row_counts(connection) == rows_before

    compatibility_repository = EquipmentCatalogRepository(database_path)
    assert compatibility_repository.active_profile() == active
    assert compatibility_repository.profile_eyepiece_ids(profile_id) == (
        profile_repository.profile_eyepiece_ids(profile_id)
    )


def test_forced_catalogue_delete_and_profile_detach_are_one_transaction(
        tmp_path: Path,
) -> None:
    database_path = _initialized_database(tmp_path)
    catalogue_repository = EquipmentCatalogRepository(database_path)
    profile_repository = EquipmentProfileRepository(database_path)
    profile = profile_repository.active_profile()
    assert profile is not None
    profile_id = int(profile["id"])

    ok, message = catalogue_repository.add_eyepiece(
        "NightScope",
        "Rollback test",
        "Fixed",
        12.0,
        60.0,
    )
    assert ok, message
    eyepiece = next(
        item
        for item in catalogue_repository.eyepieces()
        if item["brand"] == "NightScope" and item["model"] == "Rollback test"
    )
    eyepiece_id = int(eyepiece["id"])
    catalogue_id = str(eyepiece["catalog_id"])
    profile_repository.assign_profile_eyepiece(profile_id, catalogue_id)

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            f"""
            CREATE TRIGGER reject_test_eyepiece_delete
            BEFORE DELETE ON EyepieceCatalog
            WHEN OLD.id = {eyepiece_id}
            BEGIN
                SELECT RAISE(ABORT, 'test delete rejected');
            END
            """
        )
        connection.commit()

    with pytest.raises(sqlite3.IntegrityError, match="test delete rejected"):
        catalogue_repository.delete_eyepiece(
            eyepiece_id,
            remove_from_profiles=True,
        )

    assert catalogue_id in profile_repository.profile_eyepiece_ids(profile_id)
    assert any(
        int(item["id"]) == eyepiece_id
        for item in catalogue_repository.eyepieces()
    )


def _profile_row_counts(connection: sqlite3.Connection) -> dict[str, int]:
    tables = (
        "EquipmentProfile",
        "EquipmentProfileTelescope",
        "EquipmentProfileEyepiece",
        "EquipmentProfileBarlow",
        "EquipmentProfileBinocular",
        "EquipmentProfileFilter",
        "EquipmentProfileReducer",
        "EquipmentProfileAstronomyCamera",
        "EquipmentProfileCameraBody",
    )
    return {
        table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in tables
    }
