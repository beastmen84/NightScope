from __future__ import annotations

import unittest

from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.viewmodels.app_controller import AppController


class DetailReasoningTests(unittest.TestCase):
    def test_window_duration_uses_actual_time_range(self) -> None:
        self.assertEqual(SkyfieldAstronomyEngine._window_duration("20:00 - 05:00"), "9 h")
        self.assertEqual(SkyfieldAstronomyEngine._window_duration("20:30 - 22:15"), "1 h 45 min")
        self.assertEqual(SkyfieldAstronomyEngine._window_duration("Non sopra la soglia osservativa"), "0 h")

    def test_seeing_labels_are_localized_for_detail_reasoning(self) -> None:
        self.assertEqual(AppController._localized_seeing("Excellent"), "Eccellente")
        self.assertEqual(AppController._localized_seeing("Good"), "Buono")
        self.assertEqual(AppController._localized_seeing("Average"), "Discreto")
        self.assertEqual(AppController._localized_seeing("Poor"), "Scarso")


if __name__ == "__main__":
    unittest.main()
