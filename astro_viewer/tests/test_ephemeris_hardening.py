from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astro_viewer.app.astronomy.skyfield_engine import EphemerisUnavailableError, SkyfieldAstronomyEngine
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.messier_repository import MessierRepository


class EphemerisHardeningTests(unittest.TestCase):
    def test_missing_or_unreachable_ephemeris_raises_controlled_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(__file__).resolve().parents[1]
            database_path = Path(temp_dir) / "nightscope.db"
            initialize_database(database_path, base_dir / "data" / "schema.sql")

            with patch("astro_viewer.app.astronomy.skyfield_engine.Loader", BrokenLoader):
                with self.assertLogs("astro_viewer.app.astronomy.skyfield_engine", level="WARNING"):
                    with self.assertRaises(EphemerisUnavailableError):
                        SkyfieldAstronomyEngine(Path(temp_dir), MessierRepository(database_path))


class BrokenLoader:
    def __init__(self, directory: str):
        self.directory = directory

    def timescale(self):
        return object()

    def __call__(self, filename: str):
        raise OSError(f"{filename} unavailable")


if __name__ == "__main__":
    unittest.main()
