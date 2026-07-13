from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

from astro_viewer.app.database.bootstrap import _migrate_filter_catalog, initialize_database
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

        assert len(filters) == 48
        assert len(reducers) == 24
        assert all(item["is_builtin"] for item in filters + reducers)
        seeded_classes = {item["filter_class"] for item in filters}
        assert set(FILTER_CLASS_LABELS) - {"COLOR_UNSPECIFIED"} == seeded_classes
        assert all("barrel_size" not in item for item in filters)
        assert any(
            item["brand"] == "Celestron"
            and item["model"] == "Variable Polarizing Filter"
            and item["filter_class"] == "POLARIZING"
            for item in filters
        )
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
        telescopes = repository.models()[:2]
        ok, _ = repository.add_filter(
            "NightScope",
            "Filtro prova",
            "OIII",
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
            compatible_telescope_ids=[telescopes[0]["catalog_id"]],
        )
        assert ok
        reducer = next(item for item in repository.reducers() if item["brand"] == "NightScope")
        assert not reducer["is_builtin"]
        assert reducer["optical_system_label"] == "Rifrattore"
        assert reducer["compatible_telescope_ids"] == [
            telescopes[0]["catalog_id"]
        ]

        ok, _ = repository.update_reducer(
            reducer["id"],
            "NightScope",
            "Riduttore prova aggiornato",
            0.75,
            "UNIVERSAL",
            visual_compatible=True,
            imaging_compatible=False,
            compatible_telescope_ids=[telescopes[1]["catalog_id"]],
        )
        assert ok
        reducer = next(item for item in repository.reducers() if item["brand"] == "NightScope")
        assert reducer["model"] == "Riduttore prova aggiornato"
        assert not reducer["is_builtin"]
        assert reducer["compatible_telescope_ids"] == [
            telescopes[1]["catalog_id"]
        ]

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


def test_builtin_equipment_cannot_be_modified_in_repository() -> None:
    temporary_directory, _, repository = _database()
    try:
        telescope = repository.models()[0]
        eyepiece = repository.eyepieces()[0]
        barlow = repository.barlows()[0]
        binocular = repository.binoculars()[0]
        optical_filter = repository.filters()[0]
        reducer = repository.reducers()[0]

        attempts = (
            repository.update_telescope_model(
                telescope["id"],
                telescope["brand"],
                f"{telescope['name']} modificato",
                telescope["optical_type"],
                telescope["aperture_mm"],
                telescope["focal_length_mm"],
                telescope["mount_type"],
            ),
            repository.update_eyepiece(
                eyepiece["id"],
                eyepiece["brand"],
                f"{eyepiece['model']} modificato",
                eyepiece["eyepiece_type"],
                eyepiece["focal_length_mm"],
                eyepiece["apparent_field_deg"],
                eyepiece["barrel_size"],
            ),
            repository.update_barlow(
                barlow["id"],
                barlow["brand"],
                f"{barlow['model']} modificato",
                barlow["multiplier"],
                barlow["barrel_size"],
            ),
            repository.update_binocular(
                binocular["id"],
                binocular["brand"],
                f"{binocular['model']} modificato",
                binocular["magnification"],
                binocular["objective_diameter_mm"],
                binocular["image_stabilized"],
            ),
            repository.update_filter(
                optical_filter["id"],
                optical_filter["brand"],
                f"{optical_filter['model']} modificato",
                optical_filter["filter_class"],
            ),
            repository.update_reducer(
                reducer["id"],
                reducer["brand"],
                f"{reducer['model']} modificato",
                reducer["reduction_factor"],
                reducer["optical_system"],
                visual_compatible=reducer["visual_compatible"],
                imaging_compatible=reducer["imaging_compatible"],
            ),
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
        assert repository.add_filter("Custom", "Filtro profilo", "UHC")[0]
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


def test_profile_deletion_cascades_assignments_and_counts_distinct_profiles() -> None:
    temporary_directory, _, repository = _database()
    try:
        telescope = repository.models()[0]
        eyepiece = repository.eyepieces()[0]
        barlow = repository.barlows()[0]
        binocular = repository.binoculars()[0]
        optical_filter = repository.filters()[0]
        reducer = repository.reducers()[0]
        repository.add_profile("Profilo eliminabile", telescope["catalog_id"], active=False)
        profile = next(
            item
            for item in repository.profiles()
            if item["profile_name"] == "Profilo eliminabile"
        )
        profile_id = int(profile["id"])
        assignments = (
            (repository.assign_profile_eyepiece, eyepiece["catalog_id"]),
            (repository.assign_profile_barlow, barlow["catalog_id"]),
            (repository.assign_profile_binocular, binocular["catalog_id"]),
            (repository.assign_profile_filter, optical_filter["catalog_id"]),
            (repository.assign_profile_reducer, reducer["catalog_id"]),
        )
        for assign, item_id in assignments:
            assign(profile_id, item_id)

        assert repository.profile_usage_count("telescope", telescope["catalog_id"]) == 1
        for kind, item_id in (
            ("eyepiece", eyepiece["catalog_id"]),
            ("barlow", barlow["catalog_id"]),
            ("binocular", binocular["catalog_id"]),
            ("filter", optical_filter["catalog_id"]),
            ("reducer", reducer["catalog_id"]),
        ):
            assert repository.profile_usage_count(kind, item_id) == 1

        repository.delete_profile(profile_id)

        assert repository.profile_telescope_ids(profile_id) == []
        assert repository.profile_eyepiece_ids(profile_id) == []
        assert repository.profile_barlow_ids(profile_id) == []
        assert repository.profile_binocular_ids(profile_id) == []
        assert repository.profile_filter_ids(profile_id) == []
        assert repository.profile_reducer_ids(profile_id) == []
        assert repository.profile_usage_count("telescope", telescope["catalog_id"]) == 0
        for kind, item_id in (
            ("eyepiece", eyepiece["catalog_id"]),
            ("barlow", barlow["catalog_id"]),
            ("binocular", binocular["catalog_id"]),
            ("filter", optical_filter["catalog_id"]),
            ("reducer", reducer["catalog_id"]),
        ):
            assert repository.profile_usage_count(kind, item_id) == 0
    finally:
        temporary_directory.cleanup()


def test_reinitialization_removes_legacy_orphan_profile_assignments() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        optical_filter = repository.filters()[0]
        with closing(sqlite3.connect(database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute(
                """
                INSERT INTO EquipmentProfileFilter (profile_id, filter_id)
                VALUES (?, ?)
                """,
                (999_999, optical_filter["catalog_id"]),
            )
            connection.commit()

        initialize_database(database_path, SCHEMA_PATH)

        with closing(sqlite3.connect(database_path)) as connection:
            orphan_count = connection.execute(
                "SELECT COUNT(*) FROM EquipmentProfileFilter WHERE profile_id = ?",
                (999_999,),
            ).fetchone()[0]
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        assert orphan_count == 0
        assert violations == []
    finally:
        temporary_directory.cleanup()


def test_reducer_compatibility_uses_catalog_telescope_ids() -> None:
    temporary_directory, _, repository = _database()
    try:
        edgehd = next(
            item
            for item in repository.reducers()
            if item["model"] == "Reducer Lens 0.7x EdgeHD 8"
        )
        assert len(edgehd["compatible_telescopes"]) == 1
        telescope = edgehd["compatible_telescopes"][0]
        assert telescope["display_name"] == "Celestron EdgeHD 8 OTA"
        assert edgehd["compatible_telescope_ids"] == [telescope["catalog_id"]]
        assert telescope["catalog_id"].startswith("catalog-telescope-")
    finally:
        temporary_directory.cleanup()


def test_custom_reducer_compatibility_survives_seed_refresh() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        telescope = repository.models()[0]
        assert repository.add_reducer(
            "Custom",
            "Riduttore persistente",
            0.8,
            "REFRACTOR",
            imaging_compatible=True,
            compatible_telescope_ids=[telescope["catalog_id"]],
        )[0]

        initialize_database(database_path, SCHEMA_PATH)

        refreshed = EquipmentCatalogRepository(database_path)
        reducer = next(
            item
            for item in refreshed.reducers()
            if item["model"] == "Riduttore persistente"
        )
        assert reducer["compatible_telescope_ids"] == [telescope["catalog_id"]]
        assert (
            f"{telescope['brand']} {telescope['name']}"
            in reducer["compatible_models"]
        )
    finally:
        temporary_directory.cleanup()


def test_custom_reducer_rejects_unknown_telescope_compatibility() -> None:
    temporary_directory, _, repository = _database()
    try:
        ok, message = repository.add_reducer(
            "Custom",
            "Riduttore non valido",
            0.8,
            "REFRACTOR",
            compatible_telescope_ids=["catalog-telescope-999999"],
        )

        assert not ok
        assert "non esistono" in message
        assert not any(
            item["model"] == "Riduttore non valido"
            for item in repository.reducers()
        )
    finally:
        temporary_directory.cleanup()


def test_reinitialization_marks_seed_rows_without_reclassifying_custom_rows() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        assert repository.add_filter("Custom", "Persistente", "CLS")[0]
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


def test_filter_catalog_migration_collapses_barrel_duplicates_without_losing_profiles() -> None:
    with closing(sqlite3.connect(":memory:")) as connection:
        connection.row_factory = sqlite3.Row
        connection.executescript(
            """
            CREATE TABLE FilterCatalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                filter_class TEXT NOT NULL,
                barrel_size TEXT,
                central_wavelength_nm REAL,
                bandwidth_nm REAL,
                transmission_pct REAL,
                minimum_aperture_mm INTEGER,
                notes TEXT,
                is_builtin INTEGER NOT NULL DEFAULT 0,
                UNIQUE (brand, model, barrel_size)
            );
            CREATE TABLE EquipmentProfileFilter (
                profile_id INTEGER NOT NULL,
                filter_id TEXT NOT NULL,
                PRIMARY KEY (profile_id, filter_id)
            );
            INSERT INTO FilterCatalog (
                id, brand, model, filter_class, barrel_size, is_builtin
            ) VALUES
                (10, 'Example', 'OIII', 'OIII', '1.25', 1),
                (11, 'Example', 'OIII', 'OIII', '2', 1),
                (12, 'Example', 'Red', 'COLOR', '1.25', 0);
            INSERT INTO EquipmentProfileFilter (profile_id, filter_id)
            VALUES (7, 'catalog-filter-11');
            """
        )

        _migrate_filter_catalog(connection)

        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(FilterCatalog)")
        }
        filters = connection.execute(
            "SELECT id, model, filter_class FROM FilterCatalog ORDER BY id"
        ).fetchall()
        assignments = connection.execute(
            "SELECT profile_id, filter_id FROM EquipmentProfileFilter"
        ).fetchall()

    assert "barrel_size" not in columns
    assert [tuple(row) for row in filters] == [
        (10, "OIII", "OIII"),
        (12, "Red", "COLOR_RED"),
    ]
    assert [tuple(row) for row in assignments] == [(7, "catalog-filter-10")]
