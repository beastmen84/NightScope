from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from astro_viewer.app.astronomy.skyfield_engine import _italian_lunar_eclipse_kind
from astro_viewer.tools.generate_validation_report import validate_astronomy


class AstronomyValidationTests(unittest.TestCase):
    def test_lunar_eclipse_kind_is_localized(self) -> None:
        self.assertEqual(_italian_lunar_eclipse_kind("Partial"), "parziale")
        self.assertEqual(_italian_lunar_eclipse_kind("Total"), "totale")
        self.assertEqual(_italian_lunar_eclipse_kind("Penumbral"), "penombrale")

    def test_solar_system_values_are_coherent_for_reference_locations(self) -> None:
        base_dir = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp_dir:
            results = validate_astronomy(base_dir, Path(temp_dir) / "nightscope.db")

        self.assertEqual(len(results), 25)
        failures = [result for result in results if not result.passed]
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
