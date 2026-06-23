from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
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

            service = LightPollutionService(
                SkyQualityRepository(database_path),
                dataset_path=Path(__file__).resolve().parents[1] / "data" / "light_pollution_seed.csv",
            )
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

    def test_moon_penalty_is_object_dependent_for_deep_sky(self) -> None:
        new_moon = MoonSummary("Nuova", "0%", "", "", "", "")
        bright_moon = MoonSummary("Luna luminosa", "80%", "", "", "", "")
        full_moon = MoonSummary("Piena", "100%", "", "", "", "")
        open_cluster = _deep_sky_target("messier-11", "M11", "Open cluster")
        globular = _deep_sky_target("messier-13", "M13", "Globular cluster")
        galaxy = _deep_sky_target("messier-31", "M31", "Spiral galaxy")
        diffuse_nebula = _deep_sky_target("messier-78", "M78", "Diffuse nebula")

        self.assertEqual(NightPlannerService.moon_adjusted_score(galaxy, new_moon), 80)
        self.assertEqual(NightPlannerService.moon_adjusted_score(open_cluster, full_moon), 70)
        self.assertEqual(NightPlannerService.moon_adjusted_score(globular, full_moon), 62)
        self.assertEqual(NightPlannerService.moon_adjusted_score(galaxy, full_moon), 42)
        self.assertEqual(NightPlannerService.moon_adjusted_score(diffuse_nebula, full_moon), 38)

        self.assertGreater(
            NightPlannerService.moon_adjusted_score(open_cluster, bright_moon),
            NightPlannerService.moon_adjusted_score(globular, bright_moon),
        )
        self.assertGreater(
            NightPlannerService.moon_adjusted_score(globular, bright_moon),
            NightPlannerService.moon_adjusted_score(galaxy, bright_moon),
        )

    def test_moon_penalty_does_not_affect_planets(self) -> None:
        full_moon = MoonSummary("Piena", "100%", "", "", "", "")
        saturn = _deep_sky_target("saturn", "Saturno", "Pianeta")

        self.assertEqual(NightPlannerService.moon_penalty(saturn, full_moon), 0)
        self.assertEqual(NightPlannerService.moon_adjusted_score(saturn, full_moon), 80)

    def test_night_planner_reorders_deep_sky_under_bright_moon(self) -> None:
        objects = [
            _deep_sky_target("messier-31", "M31", "Spiral galaxy"),
            _deep_sky_target("messier-13", "M13", "Globular cluster"),
            _deep_sky_target("messier-11", "M11", "Open cluster"),
        ]
        weather = WeatherSummary("Ottima", 88, "Poche nuvole.", 10, 0, 8, 55, 18.0, "")
        scores = AdvancedObservingScores(92, 70, "Ottima", "Buona", "")
        sky_quality = type("SkyQualityStub", (), {"bortle_class": 4})()
        telescope = Telescope("scope", "Dobson 200", 200, 1200, "Newton", "Dobson")

        new_moon_plan = NightPlannerService().plan(objects, weather, scores, sky_quality, telescope, MoonSummary("Nuova", "0%", "", "", "", ""))
        full_moon_plan = NightPlannerService().plan(objects, weather, scores, sky_quality, telescope, MoonSummary("Piena", "100%", "", "", "", ""))

        self.assertEqual(new_moon_plan[0].name, "M31")
        self.assertEqual(full_moon_plan[0].name, "M11")
        self.assertLess([item.name for item in full_moon_plan].index("M13"), [item.name for item in full_moon_plan].index("M31"))


def _deep_sky_target(object_id: str, name: str, object_type: str) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="6.0",
        distance="",
        max_altitude="55 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="21:00 - 23:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="",
        visible=True,
        score=80,
        difficulty="Facile",
    )


if __name__ == "__main__":
    unittest.main()
