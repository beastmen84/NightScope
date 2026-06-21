from __future__ import annotations

import unittest

from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.observing_score_service import ObservingScoreService


class ObservingScoreTests(unittest.TestCase):
    def test_good_weather_scores_high(self) -> None:
        hours = [
            WeatherHour("2026-06-21T22:00", "22:00", 10, 0, 8, 55, 18.5),
            WeatherHour("2026-06-21T23:00", "23:00", 12, 0, 7, 58, 17.9),
        ]
        moon = MoonSummary("Nuova", "8%", "05:00", "20:00", "", "resources/images/moon.svg")

        summary = ObservingScoreService().weather_score(hours, moon)

        self.assertGreaterEqual(summary.score_value, 76)
        self.assertEqual(summary.score, "Ottima")

    def test_clouds_and_rain_score_low(self) -> None:
        hours = [
            WeatherHour("2026-06-21T22:00", "22:00", 90, 65, 31, 88, 16.0),
            WeatherHour("2026-06-21T23:00", "23:00", 85, 50, 28, 85, 15.6),
        ]
        moon = MoonSummary("Piena", "98%", "19:00", "05:00", "", "resources/images/moon.svg")

        summary = ObservingScoreService().weather_score(hours, moon)

        self.assertLessEqual(summary.score_value, 25)
        self.assertEqual(summary.score, "Pessima")


if __name__ == "__main__":
    unittest.main()

