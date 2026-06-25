from __future__ import annotations

import csv
import sqlite3
import shutil
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from astro_viewer.app.database.bootstrap import SCHEMA_VERSION, database_initialization_required, initialize_database
from astro_viewer.app.database.equipment_catalog_repository import EquipmentCatalogRepository
from astro_viewer.app.database.messier_repository import MessierRepository
from astro_viewer.app.database.observation_repository import ObservationRepository
from astro_viewer.app.services.location_preferences import LocationPreferenceStore
from astro_viewer.tests.geonames_fixture import write_small_geonames_fixture


class DatabaseBootstrapTests(unittest.TestCase):
    def test_messier_seed_contains_all_objects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"

            initialize_database(database_path, schema_path)

            repository = MessierRepository(database_path)
            objects = repository.list_objects()
            self.assertEqual(len(objects), 110)
            self.assertEqual(objects[0]["messier_id"], "M1")
            self.assertEqual(objects[-1]["messier_id"], "M110")

    def test_equipment_catalog_seed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            data_dir = Path(__file__).resolve().parents[1] / "data"
            schema_path = data_dir / "schema.sql"

            initialize_database(database_path, schema_path)

            repository = EquipmentCatalogRepository(database_path)
            binoculars = repository.binoculars()
            with (data_dir / "binocular_catalog_seed.csv").open("r", encoding="utf-8", newline="") as file:
                binocular_seed_count = sum(1 for _ in csv.DictReader(file))
            self.assertGreaterEqual(len(repository.brands()), 8)
            self.assertGreaterEqual(len(repository.models()), 12)
            self.assertGreaterEqual(len(repository.eyepieces()), 6)
            self.assertGreaterEqual(len(repository.barlows()), 4)
            self.assertEqual(len(binoculars), binocular_seed_count)
            self.assertGreaterEqual(len(binoculars), 60)
            self.assertTrue(any(item["image_stabilized"] for item in binoculars))
            binocular_classes = {
                (item["magnification"], item["objective_diameter_mm"])
                for item in binoculars
            }
            for binocular_class in {
                (7, 50),
                (8, 42),
                (8, 56),
                (10, 42),
                (10, 50),
                (12, 50),
                (15, 56),
                (15, 70),
                (16, 70),
                (20, 80),
                (25, 100),
            }:
                self.assertIn(binocular_class, binocular_classes)
            self.assertIsNotNone(repository.active_profile())

    def test_missing_database_is_bootstrapped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "missing.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"

            initialize_database(database_path, schema_path)

            self.assertTrue(database_path.exists())
            self.assertEqual(len(MessierRepository(database_path).list_objects()), 110)

    def test_initialization_preflight_detects_first_launch_and_ready_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"

            self.assertTrue(database_initialization_required(database_path, schema_path))

            initialize_database(database_path, schema_path)

            self.assertFalse(database_initialization_required(database_path, schema_path))

    def test_initialization_preflight_detects_empty_seeded_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("DELETE FROM MessierObject")
                connection.commit()

            self.assertTrue(database_initialization_required(database_path, schema_path))

    def test_database_initialization_reports_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            messages = []

            initialize_database(database_path, schema_path, progress_callback=messages.append)

            self.assertIn("Creazione database...", messages)
            self.assertIn("Importazione cataloghi...", messages)
            self.assertIn("Finalizzazione...", messages)

    def test_geonames_initialization_reports_incremental_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            write_small_geonames_fixture(runtime_dir, extra_rows=2)
            database_path = runtime_dir / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            messages = []

            initialize_database(
                database_path,
                schema_path,
                progress_callback=messages.append,
                geonames_data_dir=runtime_dir,
            )

            self.assertTrue(any(message.startswith("Importazione catalogo città...") for message in messages))

    def test_database_uses_sqlite_user_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                version = connection.execute("PRAGMA user_version").fetchone()[0]
            self.assertEqual(version, SCHEMA_VERSION)

    def test_seed_data_is_inserted_only_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    """
                    UPDATE TelescopeModel
                    SET notes = ?
                    WHERE id = (SELECT MIN(id) FROM TelescopeModel)
                    """,
                    ("modifica utente",),
                )
                telescope_count = connection.execute("SELECT COUNT(*) FROM TelescopeModel").fetchone()[0]
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                preserved_note = connection.execute(
                    "SELECT notes FROM TelescopeModel WHERE id = (SELECT MIN(id) FROM TelescopeModel)"
                ).fetchone()[0]
                preserved_count = connection.execute("SELECT COUNT(*) FROM TelescopeModel").fetchone()[0]
            self.assertEqual(preserved_note, "modifica utente")
            self.assertEqual(preserved_count, telescope_count)

    def test_binocular_catalog_persists_across_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            repository = EquipmentCatalogRepository(database_path)
            initial_count = len(repository.binoculars())
            ok, message = repository.add_binocular(
                "NightScope",
                "Test 10x50",
                10,
                50,
                true_fov_deg=6.5,
                weight_g=920,
                image_stabilized=True,
                notes="Stabilizzato",
            )

            self.assertTrue(ok, message)

            initialize_database(database_path, schema_path)
            binoculars = EquipmentCatalogRepository(database_path).binoculars()
            saved = next(
                item
                for item in binoculars
                if item["brand"] == "NightScope" and item["model"] == "Test 10x50"
            )

            self.assertEqual(len(binoculars), initial_count + 1)
            self.assertEqual(saved["display_name"], "NightScope Test 10x50")
            self.assertEqual(saved["spec_label"], "10×50")
            self.assertEqual(saved["fov_label"], "FOV 6.5°")
            self.assertEqual(saved["weight_label"], "920 g")
            self.assertTrue(saved["image_stabilized"])

    def test_binocular_catalog_is_added_to_existing_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("DROP TABLE BinocularCatalog")
                connection.execute("PRAGMA user_version = 1")
                connection.commit()

            self.assertTrue(database_initialization_required(database_path, schema_path))

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                table = connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name = 'BinocularCatalog'
                    """
                ).fetchone()
                version = connection.execute("PRAGMA user_version").fetchone()[0]
            self.assertIsNotNone(table)
            self.assertEqual(version, SCHEMA_VERSION)

    def test_messier_seed_restores_missing_rows_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    "UPDATE MessierObject SET descrizione = ? WHERE messier_id = ?",
                    ("nota locale", "M1"),
                )
                connection.execute("DELETE FROM MessierObject WHERE messier_id = ?", ("M110",))
                connection.commit()

            initialize_database(database_path, schema_path)

            with closing(sqlite3.connect(database_path)) as connection:
                row_count = connection.execute("SELECT COUNT(*) FROM MessierObject").fetchone()[0]
                preserved_description = connection.execute(
                    "SELECT descrizione FROM MessierObject WHERE messier_id = ?",
                    ("M1",),
                ).fetchone()[0]
                restored_object = connection.execute(
                    "SELECT messier_id FROM MessierObject WHERE messier_id = ?",
                    ("M110",),
                ).fetchone()
            self.assertEqual(row_count, 110)
            self.assertEqual(preserved_description, "nota locale")
            self.assertIsNotNone(restored_object)

    def test_existing_user_data_survives_update_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            database_path = runtime_dir / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)
            equipment = EquipmentCatalogRepository(database_path)
            equipment.add_profile("Profilo portabile", "preset:naked-eye", active=True)
            ObservationRepository(database_path).add("2026-06-25", "Saturno", "Roma", "", "", 5, "Test")
            preferences = LocationPreferenceStore(runtime_dir / "user_preferences.json", runtime_dir / "location_cache.json")
            preferences.update_preferences(auto_detect_location_on_startup=False)

            initialize_database(database_path, schema_path)

            equipment_after_update = EquipmentCatalogRepository(database_path)
            profile_names = [profile["profile_name"] for profile in equipment_after_update.profiles()]
            observations = ObservationRepository(database_path).recent(limit=10)
            preferences_after_update = LocationPreferenceStore(runtime_dir / "user_preferences.json", runtime_dir / "location_cache.json")
            self.assertIn("Profilo portabile", profile_names)
            self.assertTrue(any(row["object_name"] == "Saturno" for row in observations))
            self.assertFalse(preferences_after_update.preferences().auto_detect_location_on_startup)

    def test_runtime_folder_can_be_copied_with_user_data(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_dir = root / "NightScope"
            runtime_dir.mkdir()
            database_path = runtime_dir / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)
            EquipmentCatalogRepository(database_path).add_profile("Profilo copiato", "preset:naked-eye", active=True)
            ObservationRepository(database_path).add("2026-06-25", "M13", "Roma", "", "", 4, "Portability")
            LocationPreferenceStore(
                runtime_dir / "user_preferences.json",
                runtime_dir / "location_cache.json",
            ).update_preferences(auto_detect_location_on_startup=False)

            copied_runtime_dir = root / "NightScopeCopy"
            shutil.copytree(runtime_dir, copied_runtime_dir)
            copied_database_path = copied_runtime_dir / "nightscope.db"

            copied_profiles = EquipmentCatalogRepository(copied_database_path).profiles()
            copied_observations = ObservationRepository(copied_database_path).recent(limit=10)
            copied_preferences = LocationPreferenceStore(
                copied_runtime_dir / "user_preferences.json",
                copied_runtime_dir / "location_cache.json",
            ).preferences()
            self.assertIn("Profilo copiato", [profile["profile_name"] for profile in copied_profiles])
            self.assertTrue(any(row["object_name"] == "M13" for row in copied_observations))
            self.assertFalse(copied_preferences.auto_detect_location_on_startup)

    def test_pyinstaller_spec_does_not_package_runtime_database(self) -> None:
        spec = (Path(__file__).resolve().parents[2] / "packaging" / "NightScope.spec").read_text(encoding="utf-8")
        self.assertNotIn("nightscope.db", spec)
        self.assertIn("schema.sql", spec)
        self.assertIn("messier_seed.csv", spec)
        self.assertIn("binocular_catalog_seed.csv", spec)

    def test_runtime_database_path_is_portable_and_copies_legacy_database(self) -> None:
        from astro_viewer import main as main_module

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            runtime_dir = temp_path / "NightScope"
            base_dir = temp_path / "_internal" / "astro_viewer"
            legacy_data_dir = base_dir / "data"
            legacy_data_dir.mkdir(parents=True)
            legacy_database = legacy_data_dir / "nightscope.db"
            legacy_database.write_bytes(b"legacy-db")
            (legacy_data_dir / "user_preferences.json").write_text('{"saved": true}', encoding="utf-8")
            (legacy_data_dir / "location_cache.json").write_text('{"cached": true}', encoding="utf-8")

            with patch.object(main_module, "RUNTIME_DIR", runtime_dir), patch.object(main_module, "BASE_DIR", base_dir):
                database_path, schema_path = main_module._database_paths()

            self.assertEqual(database_path, runtime_dir / "nightscope.db")
            self.assertEqual(schema_path, base_dir / "data" / "schema.sql")
            self.assertEqual(database_path.read_bytes(), b"legacy-db")
            self.assertTrue((runtime_dir / "user_preferences.json").exists())
            self.assertTrue((runtime_dir / "location_cache.json").exists())

    def test_corrupt_database_is_quarantined_and_rebuilt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            database_path.write_text("not a sqlite database", encoding="utf-8")

            with self.assertLogs("astro_viewer.app.database.bootstrap", level="WARNING"):
                initialize_database(database_path, schema_path)

            quarantined = list(Path(temp_dir).glob("nightscope.db.corrupt-*.bak"))
            self.assertEqual(len(quarantined), 1)
            self.assertEqual(len(MessierRepository(database_path).list_objects()), 110)


if __name__ == "__main__":
    unittest.main()
