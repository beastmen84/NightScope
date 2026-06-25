from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from astro_viewer.app.database.bootstrap import database_initialization_required, initialize_database
from astro_viewer.app.database.equipment_catalog_repository import EquipmentCatalogRepository
from astro_viewer.app.database.messier_repository import MessierRepository


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
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"

            initialize_database(database_path, schema_path)

            repository = EquipmentCatalogRepository(database_path)
            self.assertGreaterEqual(len(repository.brands()), 8)
            self.assertGreaterEqual(len(repository.models()), 12)
            self.assertGreaterEqual(len(repository.eyepieces()), 6)
            self.assertGreaterEqual(len(repository.barlows()), 4)
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
