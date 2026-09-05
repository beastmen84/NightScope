"""Protect accessory catalogue CRUD, compatibility, and profile usage behavior."""

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
from astro_viewer.tests.database_fixture import prepare_database


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "data" / "schema.sql"


def _database() -> tuple[TemporaryDirectory, Path, EquipmentCatalogRepository]:
    temporary_directory = TemporaryDirectory()
    database_path = Path(temporary_directory.name) / "nightscope.db"
    prepare_database(database_path, SCHEMA_PATH)
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
        assert set(FILTER_CLASS_LABELS) == seeded_classes
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


def test_optics_catalog_omits_unmodeled_barrel_size() -> None:
    temporary_directory, _, repository = _database()
    try:
        eyepieces = repository.eyepieces()
        barlows = repository.barlows()

        assert eyepieces
        assert barlows
        assert all("barrel_size" not in item for item in eyepieces)
        assert all("barrel_size" not in item for item in barlows)
    finally:
        temporary_directory.cleanup()


def test_schema_23_retires_legacy_barrel_and_generic_reducer_fields() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        assert repository.add_eyepiece(
            "Custom",
            "Legacy eyepiece",
            "Fixed",
            10.0,
            60.0,
            notes="Nota utente",
        )[0]
        assert repository.add_barlow(
            "Custom",
            "Legacy Barlow",
            2.0,
        )[0]
        reducer = repository.reducers()[0]
        exact_ids = reducer["compatible_telescope_ids"]

        with closing(sqlite3.connect(database_path)) as connection:
            connection.execute(
                "ALTER TABLE EyepieceCatalog ADD COLUMN barrel_size TEXT"
            )
            connection.execute(
                "ALTER TABLE BarlowCatalog ADD COLUMN barrel_size TEXT"
            )
            connection.execute(
                "ALTER TABLE ReducerCatalog ADD COLUMN compatible_models TEXT"
            )
            connection.execute(
                """
                UPDATE EyepieceCatalog
                SET barrel_size = '1.25'
                WHERE brand = 'Custom' AND model = 'Legacy eyepiece'
                """
            )
            connection.execute(
                """
                UPDATE BarlowCatalog
                SET barrel_size = '1.25/2'
                WHERE brand = 'Custom' AND model = 'Legacy Barlow'
                """
            )
            connection.execute(
                "UPDATE ReducerCatalog SET compatible_models = 'Generic SCT'"
            )
            connection.execute("PRAGMA user_version = 22")
            connection.commit()

        initialize_database(database_path, SCHEMA_PATH)

        with closing(sqlite3.connect(database_path)) as connection:
            eyepiece = connection.execute(
                """
                SELECT barrel_size, notes
                FROM EyepieceCatalog
                WHERE brand = 'Custom' AND model = 'Legacy eyepiece'
                """
            ).fetchone()
            barlow = connection.execute(
                """
                SELECT barrel_size, notes
                FROM BarlowCatalog
                WHERE brand = 'Custom' AND model = 'Legacy Barlow'
                """
            ).fetchone()
            generic_values = connection.execute(
                "SELECT DISTINCT compatible_models FROM ReducerCatalog"
            ).fetchall()

        assert eyepiece == ("", "Nota utente · Ø 1.25″")
        assert barlow == ("", "Ø 1.25″ / 2″")
        assert generic_values == [("",)]
        refreshed = EquipmentCatalogRepository(database_path)
        refreshed_reducer = next(
            item
            for item in refreshed.reducers()
            if item["id"] == reducer["id"]
        )
        assert (
            refreshed_reducer["compatible_telescope_ids"] == exact_ids
        )
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


def test_non_finite_accessory_values_are_rejected_before_sqlite_write() -> None:
    temporary_directory, _, repository = _database()
    try:
        attempts = (
            repository.add_eyepiece(
                "NightScope",
                "Invalid eyepiece",
                "Fisso",
                10.0,
                float("nan"),
            ),
            repository.add_barlow(
                "NightScope",
                "Invalid Barlow",
                float("inf"),
            ),
            repository.add_filter(
                "NightScope",
                "Invalid filter",
                "OIII",
                central_wavelength_nm=float("nan"),
            ),
            repository.add_reducer(
                "NightScope",
                "Invalid reducer",
                0.8,
                "REFRACTOR",
                backfocus_mm=float("inf"),
                imaging_compatible=True,
            ),
        )

        assert all(not ok for ok, _message in attempts)
        assert not any(
            row["brand"] == "NightScope"
            for rows in (
                repository.eyepieces(),
                repository.barlows(),
                repository.filters(),
                repository.reducers(),
            )
            for row in rows
        )
    finally:
        temporary_directory.cleanup()


def test_builtin_equipment_edits_are_persistent_and_keep_delete_protection() -> None:
    temporary_directory, database_path, repository = _database()
    try:
        telescope = repository.models()[0]
        eyepiece = repository.eyepieces()[0]
        barlow = repository.barlows()[0]
        binocular = repository.binoculars()[0]
        optical_filter = repository.filters()[0]
        reducer = repository.reducers()[0]

        original_counts = (
            len(repository.models()),
            len(repository.eyepieces()),
            len(repository.barlows()),
            len(repository.binoculars()),
            len(repository.filters()),
            len(repository.reducers()),
        )
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
            ),
            repository.update_barlow(
                barlow["id"],
                barlow["brand"],
                f"{barlow['model']} modificato",
                barlow["multiplier"],
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
        assert all(ok for ok, _ in attempts)

        initialize_database(database_path, SCHEMA_PATH)
        refreshed = EquipmentCatalogRepository(database_path)
        refreshed_rows = (
            refreshed.models(),
            refreshed.eyepieces(),
            refreshed.barlows(),
            refreshed.binoculars(),
            refreshed.filters(),
            refreshed.reducers(),
        )
        assert tuple(map(len, refreshed_rows)) == original_counts
        for original, rows in zip(
            (telescope, eyepiece, barlow, binocular, optical_filter, reducer),
            refreshed_rows,
            strict=True,
        ):
            updated = next(item for item in rows if item["id"] == original["id"])
            assert updated["is_builtin"]
            assert updated["is_user_modified"]
            assert updated["seed_key"] == original["seed_key"]
            assert "modificato" in (updated.get("name") or updated.get("model") or "")

        updated_reducer = next(
            item for item in refreshed.reducers() if item["id"] == reducer["id"]
        )
        assert updated_reducer["compatible_telescope_ids"] == []
        assert not refreshed.delete_telescope_model(telescope["id"])[0]
        assert not refreshed.delete_reducer(reducer["id"])[0]
    finally:
        temporary_directory.cleanup()


def test_default_profile_name_is_distinct_from_naked_eye_mode() -> None:
    temporary_directory, _, repository = _database()
    try:
        profile = repository.active_profile()
        assert profile is not None
        assert profile["profile_name"] == "Default"
        assert profile["telescope_id"] == "preset:naked-eye"
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


def test_reducer_without_exact_compatibility_stays_unconfigured() -> None:
    temporary_directory, _, repository = _database()
    try:
        reducer = next(
            item
            for item in repository.reducers()
            if item["model"] == "Alan Gee Mark II Telecompressor"
        )
        assert reducer["compatible_telescope_ids"] == []
        assert reducer["compatibility_configured"] is False
        assert "compatible_models" not in reducer

        ok, _ = repository.update_reducer(
            reducer["id"],
            reducer["brand"],
            reducer["model"],
            reducer["reduction_factor"],
            reducer["optical_system"],
            connection_name=reducer["connection"],
            backfocus_mm=reducer["backfocus_mm"],
            visual_compatible=reducer["visual_compatible"],
            imaging_compatible=reducer["imaging_compatible"],
            corrected_field=reducer["corrected_field"],
            notes=reducer["notes"],
        )

        assert ok
        updated = next(
            item for item in repository.reducers() if item["id"] == reducer["id"]
        )
        assert updated["compatible_telescope_ids"] == []
        assert updated["compatibility_configured"] is False
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
            in {
                item["display_name"]
                for item in reducer["compatible_telescopes"]
            }
        )
    finally:
        temporary_directory.cleanup()


def test_user_telescope_is_available_for_exact_reducer_compatibility() -> None:
    temporary_directory, _, repository = _database()
    try:
        assert repository.add_telescope_model(
            "Custom",
            "My imaging scope",
            "Refractor",
            80,
            480,
            "EQUATORIAL_TRACKING",
        )[0]
        telescope = next(
            item
            for item in repository.models()
            if item["brand"] == "Custom"
            and item["name"] == "My imaging scope"
        )
        assert repository.add_reducer(
            "Custom",
            "My exact reducer",
            0.8,
            "REFRACTOR",
            imaging_compatible=True,
            compatible_telescope_ids=[telescope["catalog_id"]],
        )[0]

        reducer = next(
            item
            for item in repository.reducers()
            if item["model"] == "My exact reducer"
        )
        assert reducer["compatible_telescope_ids"] == [
            telescope["catalog_id"]
        ]
        assert reducer["compatible_telescopes"][0]["display_name"] == (
            "Custom My imaging scope"
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


def test_binocular_catalog_uses_natural_model_order_within_each_brand() -> None:
    temporary_directory, _, repository = _database()
    try:
        binoculars = repository.binoculars()
        canon = [item["model"] for item in binoculars if item["brand"] == "Canon"]
        celestron_ed = [
            item["model"]
            for item in binoculars
            if item["brand"] == "Celestron" and "Nature DX ED" in item["model"]
        ]

        assert canon == [
            "8x20 IS",
            "10x20 IS",
            "10x30 IS II",
            "10x42 L IS WP",
            "12x32 IS",
            "12x36 IS III",
            "15x50 IS All Weather",
            "18x50 IS All Weather",
        ]
        assert celestron_ed == ["Nature DX ED 8x42", "Nature DX ED 10x42"]
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
