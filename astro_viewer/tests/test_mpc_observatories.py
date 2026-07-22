from __future__ import annotations

import csv
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from astro_viewer.app.database.location_repository import LocationRepository
from astro_viewer.app.database.bootstrap import (
    SCHEMA_VERSION,
    database_initialization_required,
    initialize_database,
)
from astro_viewer.app.database.mpc_observatory_importer import (
    import_mpc_observatories,
)
from astro_viewer.app.services.location_service import LocationService
from astro_viewer.tools.update_mpc_observatories import (
    DEFAULT_OUTPUT,
    geodetic_coordinates,
    snapshot_rows,
    validate_snapshot,
)


BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = BASE_DIR / "data" / "schema.sql"


class MpcSnapshotTests(unittest.TestCase):
    def test_packaged_snapshot_is_valid_and_contains_r50(self) -> None:
        rows = validate_snapshot(DEFAULT_OUTPUT)
        by_code = {row["mpc_code"]: row for row in rows}

        self.assertEqual(len(rows), 2683)
        self.assertIn("R50", by_code)
        self.assertNotIn("500", by_code)
        self.assertAlmostEqual(float(by_code["R50"]["latitude"]), 41.88417448)
        self.assertAlmostEqual(float(by_code["R50"]["longitude"]), -5.593425)
        self.assertIn("orion", by_code["R50"]["search_name"])

    def test_geodetic_conversion_matches_greenwich(self) -> None:
        latitude, elevation = geodetic_coordinates(0.62411, 0.77873)

        self.assertAlmostEqual(latitude, 51.477376, places=5)
        self.assertAlmostEqual(elevation, 65.8, places=1)

    def test_snapshot_filters_non_fixed_and_non_surface_records(self) -> None:
        payload = {
            "ABC": _api_record("ABC", "Fixed Observatory"),
            "SAT": _api_record("SAT", "Satellite", observations_type="satellite"),
            "500": _api_record("500", "Geocenter", rho_cos_phi="0", rho_sin_phi="0"),
        }

        rows = snapshot_rows(payload)

        self.assertEqual([row["mpc_code"] for row in rows], ["ABC"])


class MpcLocationRepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self._temporary_directory.name) / "nightscope.db"
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            imported = import_mpc_observatories(connection, DEFAULT_OUTPUT)
            connection.execute(
                """
                INSERT INTO City (
                    city_name, ascii_name, country, country_code, admin_region,
                    latitude, longitude, timezone, population, aliases, search_name
                )
                VALUES ('Roma', 'Rome', 'Italia', 'IT', 'Lazio',
                        41.8933, 12.4829, 'Europe/Rome', 2750000, 'Rome', 'roma rome italia')
                """
            )
            connection.commit()
        self.assertEqual(imported, 2683)
        self.repository = LocationRepository(self.database_path)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def test_exact_mpc_code_is_the_first_result(self) -> None:
        results = self.repository.search("r50")

        self.assertEqual(results[0]["kind"], "mpc_observatory")
        self.assertEqual(results[0]["selection_id"], "R50")

    def test_observatory_search_is_accent_insensitive(self) -> None:
        results = self.repository.search("San Agustín del Pozo")

        self.assertEqual(results[0]["selection_id"], "R50")

    def test_exact_city_name_keeps_normal_city_ranking(self) -> None:
        results = self.repository.search("Roma")

        self.assertEqual(results[0]["kind"], "city")
        self.assertEqual(results[0]["name"], "Roma")

    def test_ranking_happens_before_the_combined_result_limit(self) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("DELETE FROM MpcObservatory")
            connection.executemany(
                """
                INSERT INTO MpcObservatory (
                    mpc_code, name, short_name, latitude, longitude,
                    rho_cos_phi, rho_sin_phi, search_name
                )
                VALUES (?, ?, '', 0, 0, 1, 0, ?)
                """,
                [
                    (f"T{index:02d}", f"Site ranking probe {index}", f"t{index:02d} site ranking probe {index}")
                    for index in range(25)
                ]
                + [("ZZZ", "ranking probe", "zzz ranking probe")],
            )
            connection.commit()

        results = self.repository.search("ranking probe", limit=20)

        self.assertEqual(results[0]["selection_id"], "ZZZ")

    def test_get_observatory_returns_source_metadata(self) -> None:
        observatory = self.repository.get_observatory("r50")

        self.assertIsNotNone(observatory)
        assert observatory is not None
        self.assertEqual(observatory["mpc_code"], "R50")
        self.assertEqual(observatory["observations_type"], "optical")
        self.assertEqual(observatory["first_date"], "2025-07-20")

    def test_selected_observatory_uses_offline_coordinate_timezone(self) -> None:
        observatory = self.repository.get_observatory("R50")
        assert observatory is not None

        result = LocationService().from_mpc_observatory_result(observatory)

        self.assertEqual(result.provider, "mpc_observatory")
        self.assertEqual(result.location.city, observatory["name"])
        self.assertEqual(result.location.timezone, "Europe/Madrid")
        self.assertEqual(result.accuracy, "coordinate MPC")


class MpcBootstrapTests(unittest.TestCase):
    def test_existing_database_migrates_and_imports_packaged_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_dir = Path(temp_dir)
            database_path = runtime_dir / "nightscope.db"
            initialize_database(
                database_path,
                SCHEMA_PATH,
                geonames_data_dir=runtime_dir,
            )
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute("DROP TABLE MpcObservatory")
                connection.execute("DELETE FROM DataImportLog WHERE source_name = ?", (DEFAULT_OUTPUT.name,))
                connection.execute("PRAGMA user_version = 16")
                connection.commit()

            self.assertTrue(
                database_initialization_required(
                    database_path,
                    SCHEMA_PATH,
                    geonames_data_dir=runtime_dir,
                )
            )
            initialize_database(
                database_path,
                SCHEMA_PATH,
                geonames_data_dir=runtime_dir,
            )

            with closing(sqlite3.connect(database_path)) as connection:
                row_count = connection.execute(
                    "SELECT COUNT(*) FROM MpcObservatory"
                ).fetchone()[0]
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                import_log = connection.execute(
                    "SELECT report_json FROM DataImportLog WHERE source_name = ?",
                    (DEFAULT_OUTPUT.name,),
                ).fetchone()
            self.assertEqual(row_count, 2683)
            self.assertEqual(version, SCHEMA_VERSION)
            self.assertIsNotNone(import_log)
            self.assertFalse(
                database_initialization_required(
                    database_path,
                    SCHEMA_PATH,
                    geonames_data_dir=runtime_dir,
                )
            )


def _api_record(
    code: str,
    name: str,
    *,
    observations_type: str = "optical",
    rho_cos_phi: str = "0.62411",
    rho_sin_phi: str = "0.77873",
) -> dict:
    return {
        "obscode": code,
        "name": name,
        "name_utf8": name,
        "short_name": name,
        "longitude": "0",
        "rhocosphi": rho_cos_phi,
        "rhosinphi": rho_sin_phi,
        "observations_type": observations_type,
    }


def test_seed_has_expected_columns() -> None:
    with DEFAULT_OUTPUT.open("r", encoding="utf-8", newline="") as file:
        row = next(csv.DictReader(file))

    assert "mpc_code" in row
    assert "search_name" in row
