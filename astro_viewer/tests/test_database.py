from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from astro_viewer.app.database.bootstrap import initialize_database
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


if __name__ == "__main__":
    unittest.main()
