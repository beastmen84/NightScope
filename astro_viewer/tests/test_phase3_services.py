from __future__ import annotations

from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
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

    def test_seeing_transparency_tolerates_missing_optional_weather_fields(self) -> None:
        hours = [
            WeatherHour(
                "2026-06-21T22:00",
                "22:00",
                12,
                0,
                7,
                54,
                18.0,
                visibility_m=None,
                cloud_cover_low=None,
                cloud_cover_mid=None,
                cloud_cover_high=None,
                wind_gusts_kmh=None,
                dew_point_c=None,
            )
        ]
        sky_quality = type("SkyQualityStub", (), {"bortle_class": 3, "viirs_radiance": None})()

        estimate = SeeingTransparencyService().estimate(hours, sky_quality)

        self.assertEqual(estimate.source, "BasicForecastSeeingProvider")
        self.assertEqual(estimate.confidence, "low")
        self.assertGreaterEqual(estimate.seeing_score, 0)
        self.assertGreaterEqual(estimate.transparency_score, 0)

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

        plan = NightPlannerService().plan(
            [target],
            weather,
            scores,
            sky_quality,
            telescope,
        )

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].name, "Saturno")
        self.assertGreaterEqual(plan[0].score, 40)

    def test_night_planner_selects_by_score_then_displays_chronologically(self) -> None:
        objects = [
            _planned_target("saturn", "Saturno", "Pianeta", "01:30", 95),
            _planned_target("venus", "Venere", "Pianeta", "20:45", 92),
            _planned_target("messier-M24", "M24", "Star cloud", "00:30", 84),
            _planned_target("messier-M13", "M13", "Globular cluster", "22:15", 78),
            _planned_target("messier-M11", "M11", "Open cluster", "23:05", 76),
            _planned_target("messier-M31", "M31", "Spiral galaxy", "21:40", 74),
            _planned_target("mercury", "Mercurio", "Pianeta", "20:00", 12),
        ]
        weather = WeatherSummary("Ottima", 88, "Poche nuvole.", 10, 0, 8, 55, 18.0, "")
        scores = AdvancedObservingScores(90, 90, "Ottima", "Ottima", "")
        sky_quality = type("SkyQualityStub", (), {"bortle_class": 4})()
        telescope = Telescope("scope", "Dobson 200", 200, 1200, "Newton", "Dobson")

        plan = NightPlannerService().plan(objects, weather, scores, sky_quality, telescope)

        names = [item.name for item in plan]
        self.assertNotIn("Mercurio", names)
        self.assertCountEqual(names, ["Venere", "M11", "M24", "Saturno"])
        self.assertEqual(names, ["Venere", "M11", "M24", "Saturno"])
        self.assertEqual(
            [item.time_label for item in plan],
            ["20:45 sera", "23:05 sera", "00:30 notte", "01:30 notte"],
        )

    def test_home_plan_numbering_follows_display_order(self) -> None:
        qml = (Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "HomePage.qml").read_text(encoding="utf-8")

        self.assertIn("model: controller.nightPlan.slice(0, 4)", qml)
        self.assertIn('scoreText: "#" + (index + 1)', qml)

    def test_night_planner_display_order_uses_observing_night_boundary(self) -> None:
        labels = ["00:30 notte", "18:45 sera", "05:30 prima dell'alba", "20:45 sera"]

        ordered = sorted(labels, key=NightPlannerService._time_label_order)

        self.assertEqual(ordered, ["18:45 sera", "20:45 sera", "00:30 notte", "05:30 prima dell'alba"])

    def test_advanced_scores_are_capped_by_blocking_weather(self) -> None:
        weather = WeatherSummary("Pessima", 13, "Nuvolosità elevata.", 74, 99, 8, 78, 16.0, "")
        seeing = SeeingTransparency("Excellent", "Poor", 96, 20, "Vento debole.")
        sky_quality = type("SkyQualityStub", (), {"bortle_class": 6, "viirs_radiance": None})()
        moon = MoonSummary("Gibbosa crescente", "72%", "", "", "", "")

        scores = AdvancedObservingService().scores(weather, seeing, sky_quality, moon)

        self.assertLessEqual(scores.planetary_score, 25)
        self.assertEqual(scores.planetary_label, "Pessima")

    def test_night_planner_suspends_plan_when_weather_is_blocking(self) -> None:
        target = _deep_sky_target("saturn", "Saturno", "Pianeta")
        weather = WeatherSummary("Pessima", 13, "Nuvolosità elevata.", 74, 99, 8, 78, 16.0, "")
        scores = AdvancedObservingScores(23, 23, "Pessima", "Pessima", "")
        sky_quality = type("SkyQualityStub", (), {"bortle_class": 5})()
        telescope = Telescope("scope", "Dobson 200", 200, 1200, "Newton", "Dobson")

        plan = NightPlannerService().plan([target], weather, scores, sky_quality, telescope)

        self.assertEqual(plan, [])

    def test_weather_blocking_status_centralizes_plan_and_home_state(self) -> None:
        rain = WeatherSummary("Discreta", 66, "Pioggia possibile.", 20, 80, 8, 78, 16.0, "")
        poor_score = WeatherSummary("Pessima", 13, "Nuvolosità elevata.", 74, 20, 8, 78, 16.0, "")
        unavailable = WeatherSummary("Pessima", 0, "Previsioni non disponibili.", 0, 0, 0, 0, 0.0, "")

        rain_status = NightPlannerService.weather_blocking_status(rain)
        poor_score_status = NightPlannerService.weather_blocking_status(poor_score)
        unavailable_status = NightPlannerService.weather_blocking_status(unavailable)

        self.assertTrue(rain_status.blocks_plan)
        self.assertTrue(rain_status.show_warning)
        self.assertEqual(rain_status.reason, "rischio precipitazioni")
        self.assertEqual(rain_status.detail, "Rischio precipitazioni elevato.")
        self.assertTrue(poor_score_status.blocks_plan)
        self.assertTrue(poor_score_status.show_warning)
        self.assertEqual(poor_score_status.reason, "Nuvolosità elevata.")
        self.assertTrue(unavailable_status.blocks_plan)
        self.assertFalse(unavailable_status.show_warning)

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

        planner = NightPlannerService()
        new_moon_plan = planner.plan(
            objects,
            weather,
            scores,
            sky_quality,
            telescope,
            MoonSummary("Nuova", "0%", "", "", "", ""),
        )
        full_moon_plan = planner.plan(
            objects,
            weather,
            scores,
            sky_quality,
            telescope,
            MoonSummary("Piena", "100%", "", "", "", ""),
        )

        self.assertEqual(new_moon_plan[0].name, "M11")
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


def _planned_target(object_id: str, name: str, object_type: str, best_time: str, score: int) -> CelestialObject:
    return replace(
        _deep_sky_target(object_id, name, object_type),
        best_time=best_time,
        observing_window=f"{best_time} - {best_time}",
        score=score,
    )


if __name__ == "__main__":
    unittest.main()
