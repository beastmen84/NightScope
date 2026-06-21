from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import AdvancedObservingScores
from astro_viewer.app.models.weather import WeatherHour, WeatherSummary
from astro_viewer.app.services.light_pollution_service import LightPollutionService
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.seeing_service import SeeingTransparencyService


class Phase3ServiceTests(unittest.TestCase):
    def test_light_pollution_known_city(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "nightscope.db"
            schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
            initialize_database(database_path, schema_path)

            service = LightPollutionService(SkyQualityRepository(database_path))
            quality = service.sky_quality(ObserverLocation("Milano", "Italia", 45.46, 9.19, "Europe/Rome"))

            self.assertEqual(quality.bortle_class, 8)
            self.assertEqual(quality.description, "Urban Sky")

    def test_seeing_transparency_estimate(self) -> None:
        hours = [
            WeatherHour("2026-06-21T22:00", "22:00", 12, 0, 7, 54, 18.0, 20_000),
            WeatherHour("2026-06-21T23:00", "23:00", 15, 0, 8, 57, 17.5, 20_000),
        ]
        sky_quality = type("SkyQualityStub", (), {"bortle_class": 3})()

        estimate = SeeingTransparencyService().estimate(hours, sky_quality)

        self.assertIn(estimate.seeing, {"Good", "Excellent"})
        self.assertIn(estimate.transparency, {"Good", "Excellent"})

    def test_night_planner_returns_ranked_items(self) -> None:
        target = CelestialObject(
            id="saturn",
            name="Saturno",
            object_type="Pianeta",
            image="resources/images/saturn.svg",
            magnitude="0.8",
            distance="9 UA",
            max_altitude="45 gradi",
            direction="Sud",
            best_time="22:15",
            observing_window="21:30 - 00:40",
            notes="",
            recommended_setup="10 mm + Barlow 2x",
            visibility_class="Telescopio",
            azimuth="180 gradi",
            time_above_horizon="3 h",
            visible=True,
            score=88,
            difficulty="Facile",
        )
        weather = WeatherSummary("Ottima", 88, "Poche nuvole.", 10, 0, 8, 55, 18.0, "")
        scores = AdvancedObservingScores(92, 58, "Ottima", "Buona", "")
        sky_quality = type("SkyQualityStub", (), {"bortle_class": 5})()
        telescope = Telescope("scope", "Dobson 200", 200, 1200, "Newton", "Dobson")

        plan = NightPlannerService().plan([target], weather, scores, sky_quality, telescope)

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].name, "Saturno")
        self.assertGreaterEqual(plan[0].score, 70)


if __name__ == "__main__":
    unittest.main()

