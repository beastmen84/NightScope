from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.equipment_catalog_repository import (
    FILTER_CLASS_LABELS,
    OPTICAL_SYSTEM_LABELS,
    EquipmentCatalogRepository,
)


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "data" / "schema.sql"


def _database() -> tuple[TemporaryDirectory, Path, EquipmentCatalogRepository]:
    temporary_directory = TemporaryDirectory()
    database_path = Path(temporary_directory.name) / "nightscope.db"
    initialize_database(database_path, SCHEMA_PATH)
    return temporary_directory, database_path, EquipmentCatalogRepository(database_path)


def test_filter_and_reducer_seeds_are_comprehensive_and_structured() -> None:
    temporary_directory, _, repository = _database()
    try:
        filters = repository.filters()
        reducers = repository.reducers()

        assert len(filters) == 77
        assert len(reducers) == 24
        assert all(item["is_builtin"] for item in filters + reducers)
        assert set(FILTER_CLASS_LABELS).issubset({item["filter_class"] for item in filters})
        assert {"SCT_CLASSIC", "EDGEHD", "REFRACTOR", "RC"}.issubset(
            {item["optical_system"] for item in reducers}
        )
        assert set(OPTICAL_SYSTEM_LABELS).issuperset(
            {item["optical_system"] for item in reducers}
        )
        assert any(item["visual_compatible"] for item in reducers)
        assert any(not item["visual_compatible"] for item in reducers)
        assert any(item["backfocus_mm"] for item in reducers)
        assert any(item["bandwidth_nm"] for item in filters)
    finally:
        temporary_directory.cleanup()


def test_custom_filter_and_reducer_crud_preserves_user_provenance() -> None:
    temporary_directory, _, repository = _database()
    try:
        ok, _ = repository.add_filter(
            "NightScope",
            "Filtro prova",
            "OIII",
            "1.25",
            central_wavelength_nm=500.7,
            bandwidth_nm=11,
            transmission_pct=92,
            minimum_aperture_mm=120,
            notes="Test",
        )
        assert ok
        optical_filter = next(item for item in repository.filters() if item["brand"] == "NightScope")
        assert not optical_filter["is_builtin"]
        assert optical_filter["filter_class_label"] == "OIII"

        ok, _ = repository.update_filter(
            optical_filter["id"],
            "NightScope",
            "Filtro prova aggiornato",
            "UHC",
            "2",
            bandwidth_nm=25,
        )
        assert ok
        optical_filter = next(item for item in repository.filters() if item["brand"] == "NightScope")
        assert optical_filter["model"] == "Filtro prova aggiornato"
        assert not optical_filter["is_builtin"]

        ok, _ = repository.add_reducer(
            "NightScope",
            "Riduttore prova",
            0.8,
            "REFRACTOR",
            compatible_models="Rifrattore prova",
            connection_name="M48",
            backfocus_mm=55,
            visual_compatible=True,
            imaging_compatible=True,
            corrected_field=True,
        )
        assert ok
        reducer = next(item for item in repository.reducers() if item["brand"] == "NightScope")
        assert not reducer["is_builtin"]
        assert reducer["optical_system_label"] == "Rifrattore"

        ok, _ = repository.update_reducer(
            reducer["id"],
            "NightScope",
            "Riduttore prova aggiornato",
            0.75,
            "UNIVERSAL",
            visual_compatible=True,
            imaging_compatible=False,
        )
        assert ok
        reducer = next(item for item in repository.reducers() if item["brand"] == "NightScope")
        assert reducer["model"] == "Riduttore prova aggiornato"
        assert not reducer["is_builtin"]

        assert repository.delete_filter(optical_filter["id"])[0]
        assert repository.delete_reducer(reducer["id"])[0]
        assert not any(item["brand"] == "NightScope" for item in repository.filters())
        assert not any(item["brand"] == "NightScope" for item in repository.reducers())
    finally:
        temporary_directory.cleanup()


def test_builtin_equipment_cannot_be_deleted_from_repository() -> None:
    temporary_directory, _, repository = _database()
    try:
        attempts = (
            repository.delete_telescope_model(repository.models()[0]["id"]),
            repository.delete_eyepiece(repository.eyepieces()[0]["id"]),
            repository.delete_barlow(repository.barlows()[0]["id"]),
            repository.delete_binocular(repository.binoculars()[0]["id"]),
            repository.delete_filter(repository.filters()[0]["id"]),
            repository.delete_reducer(repository.reducers()[0]["id"]),
        )
        for ok, message in attempts:
            assert not ok
            assert "integrati" in message
    finally:
        temporary_directory.cleanup()


def test_filter_and_reducer_profile_assignment_and_safe_deletion() -> None:
    temporary_directory, _, repository = _database()
    try:
        profile = repository.active_profile()
        assert profile is not None
        profile_id = int(profile["id"])
        assert repository.add_filter("Custom", "Filtro profilo", "UHC", "1.25")[0]
        assert repository.add_reducer(
            "Custom",
            "Riduttore profilo",
            0.8,
            "UNIVERSAL",
            visual_compatible=True,
            imaging_compatible=False,
        )[0]
        optical_filter = next(item for item in repository.filters() if item["brand"] == "Custom")
        reducer = next(item for item in repository.reducers() if item["brand"] == "Custom")

        repository.assign_profile_filter(profile_id, optical_filter["catalog_id"])
        repository.assign_profile_reducer(profile_id, reducer["catalog_id"])
        assert repository.profile_usage_count("filter", optical_filter["catalog_id"]) == 1
        assert repository.profile_usage_count("reducer", reducer["catalog_id"]) == 1
        assert not repository.delete_filter(optical_filter["id"])[0]
        assert not repository.delete_reducer(reducer["id"])[0]
        assert repository.delete_filter(optical_filter["id"], remove_from_profiles=True)[0]
        assert repository.delete_reducer(reducer["id"], remove_from_profiles=True)[0]
        assert repository.profile_filter_ids(profile_id) == []
        assert repository.profile_reducer_ids(profile_id) == []
    finally:
        temporary_directory.cleanup()


def test_reinitialization_marks_seed_rows_without_reclassifying_custom_rows() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        assert repository.add_filter("Custom", "Persistente", "CLS", "2")[0]
        initialize_database(database_path, SCHEMA_PATH)
        refreshed = EquipmentCatalogRepository(database_path)
        assert all(item["is_builtin"] for item in refreshed.filters() if item["brand"] != "Custom")
        custom = next(item for item in refreshed.filters() if item["brand"] == "Custom")
        assert not custom["is_builtin"]

        with closing(sqlite3.connect(database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        assert {
            "FilterCatalog",
            "ReducerCatalog",
            "EquipmentProfileFilter",
            "EquipmentProfileReducer",
        }.issubset(tables)
    finally:
        temporary_directory.cleanup()
