from __future__ import annotations

import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.city_repository import CityRepository
from astro_viewer.app.database.equipment_catalog_repository import EquipmentCatalogRepository
from astro_viewer.app.database.geonames_importer import import_geonames_cities
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.equipment import Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.light_pollution_service import LightPollutionService
from astro_viewer.app.services.seeing_service import SeeingTransparencyService
from astro_viewer.app.viewmodels.app_controller import AppController


class Phase6RealDataTests(unittest.TestCase):
    def test_expanded_seed_counts(self) -> None:
        with _temp_database() as database_path:
            equipment = EquipmentCatalogRepository(database_path)
            self.assertGreaterEqual(len(CityRepository(database_path).list_cities(limit=500)), 100)
            self.assertGreaterEqual(len(equipment.models()), 100)
            self.assertGreaterEqual(len(equipment.eyepieces()), 100)
            self.assertGreaterEqual(len(equipment.barlows()), 30)

    def test_city_search_aliases(self) -> None:
        with _temp_database() as database_path:
            repository = CityRepository(database_path)

            self.assertTrue(any(city["city"] == "Addis Ababa" for city in repository.search("Addis")))
            self.assertTrue(any(city["city"] == "Addis Ababa" for city in repository.search("Addis Ababa")))
            addis_results = [city for city in repository.search("Addis Abeba") if city["country_code"] == "ET"]
            self.assertTrue(any(city["city"] == "Addis Ababa" for city in addis_results))
            self.assertFalse(any(city["city"] == "Addis Abeba" for city in addis_results))
            self.assertTrue(any(city["city"] == "Milano" for city in repository.search("Milan")))
            self.assertTrue(any(city["city"] == "Roma" for city in repository.search("Rome")))

    def test_geonames_import_merges_translated_duplicate_names(self) -> None:
        with _temp_database() as database_path, tempfile.TemporaryDirectory() as temp_dir:
            geonames_path = Path(temp_dir) / "cities.txt"
            geonames_path.write_text(
                "\n".join(
                    [
                        _geonames_row("344979", "Addis Ababa", "Addis Ababa", "Addis Abeba,Finfinne", "9.03", "38.74", "ET", "AA", "3041002", "Africa/Addis_Ababa"),
                        _geonames_row("999001", "Addis Abeba", "Addis Abeba", "Addis Ababa,Finfinne", "9.0303", "38.7404", "ET", "AA", "3041002", "Africa/Addis_Ababa"),
                        _geonames_row("3169070", "Rome", "Rome", "Roma", "41.8919", "12.5113", "IT", "07", "2318895", "Europe/Rome"),
                        _geonames_row("3173435", "Milan", "Milan", "Milano", "45.4643", "9.1895", "IT", "09", "1371498", "Europe/Rome"),
                        _geonames_row("4250542", "Springfield", "Springfield", "", "39.8017", "-89.6437", "US", "IL", "114394", "America/Chicago"),
                        _geonames_row("4951788", "Springfield", "Springfield", "", "42.1015", "-72.5898", "US", "MA", "155929", "America/New_York"),
                        _geonames_row("123456", "No Timezone", "No Timezone", "", "10.0", "10.0", "ZZ", "00", "1", ""),
                    ]
                ),
                encoding="utf-8",
            )

            import sqlite3

            with closing(sqlite3.connect(database_path)) as connection:
                connection.row_factory = sqlite3.Row
                report = import_geonames_cities(connection, geonames_path)
                connection.commit()

            repository = CityRepository(database_path)
            addis_results = [city for city in repository.search("Addis Abeba") if city["country_code"] == "ET"]
            self.assertEqual({city["city"] for city in addis_results}, {"Addis Ababa"})
            self.assertTrue(any(city["city"] in {"Roma", "Rome"} for city in repository.search("Rome")))
            self.assertTrue(any(city["city"] in {"Milano", "Milan"} for city in repository.search("Milano")))
            springfield_results = [city for city in repository.search("Springfield") if city["country_code"] == "US"]
            self.assertGreaterEqual(len(springfield_results), 2)
            self.assertEqual(report.total_rows_read, 7)
            self.assertGreaterEqual(report.total_imported, 2)
            self.assertGreaterEqual(report.duplicates_merged, 4)
            self.assertGreater(report.aliases_added, 0)
            self.assertEqual(report.cities_missing_timezone, 1)

    def test_naked_eye_fallback_blocks_eyepiece_add(self) -> None:
        with _controller() as controller:
            self.assertEqual(controller.currentSetup["name"], "Occhio nudo")
            self.assertFalse(controller.canUseEyepieces)

            controller.addEyepiece("Test", "25", "52")

            self.assertEqual(controller.eyepieces, [])
            self.assertIn("prima di aggiungere oculari", controller.equipmentMessage)

    def test_suggestions_without_telescope_do_not_invent_eyepieces(self) -> None:
        service = EquipmentService()
        suggestion = service.suggest_for_object(
            _object("messier-M57", "Ring Nebula", "Planetary nebula", "8.8"),
            service.naked_eye_telescope(),
            [],
        )

        self.assertEqual(suggestion["bestEyepiece"], "")
        self.assertEqual(suggestion["barlow"], "No")
        self.assertIn("Serve almeno", suggestion["setupText"])

    def test_suggestions_with_telescope_but_no_eyepieces_are_limited(self) -> None:
        suggestion = EquipmentService().suggest_for_object(
            _object("jupiter", "Giove", "Pianeta", "-2.0"),
            Telescope("scope", "Newton 150/750", 150, 750, "Newton", "manuale"),
            [],
        )

        self.assertEqual(suggestion["bestEyepiece"], "")
        self.assertIn("Aggiungi oculari", suggestion["setupText"])

    def test_suggestions_with_telescope_use_available_eyepieces(self) -> None:
        suggestion = EquipmentService().suggest_for_object(
            _object("jupiter", "Giove", "Pianeta", "-2.0"),
            Telescope("scope", "Newton 150/750", 150, 750, "Newton", "manuale"),
            [Eyepiece("e1", "Solo 18 mm", 18, 60), Eyepiece("e2", "Solo 7 mm", 7, 60)],
        )

        self.assertIn(suggestion["bestEyepiece"], {"Solo 18 mm", "Solo 7 mm"})
        self.assertNotIn("Plossl 25", suggestion["setupText"])

    def test_weather_not_called_without_valid_location(self) -> None:
        with _controller() as controller:
            fake_weather = Mock()
            fake_weather.hourly_forecast.return_value = []
            controller._weather_service = fake_weather
            controller._location = None

            with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="WARNING"):
                controller._refresh_weather_and_conditions()

            fake_weather.hourly_forecast.assert_not_called()
            self.assertEqual(controller.weatherStatus, "Configura una posizione per verificare il meteo.")

    def test_weather_refreshes_after_valid_location(self) -> None:
        with _controller() as controller:
            fake_weather = Mock()
            fake_weather.hourly_forecast.return_value = [
                WeatherHour("2026-06-21T22:00", "22:00", 10, 0, 5, 55, 18.0, 20_000)
            ]
            fake_weather.last_error = ""
            controller._weather_service = fake_weather

            controller.setManualLocation("41.9028", "12.4964", "Roma")

            fake_weather.hourly_forecast.assert_called()

    def test_light_pollution_provider_fallback(self) -> None:
        with _temp_database() as database_path:
            service = LightPollutionService(
                SkyQualityRepository(database_path),
                dataset_path=Path("missing-light-pollution.csv"),
            )
            quality = service.sky_quality(ObserverLocation("Unknown", "", 1.0, 1.0, "UTC"))

            self.assertEqual(quality.source, "Fonte: stima offline NightScope")
            self.assertEqual(quality.confidence, "low")

    def test_seeing_provider_fallback(self) -> None:
        hours = [
            WeatherHour(
                "2026-06-21T22:00",
                "22:00",
                20,
                0,
                6,
                55,
                18.0,
                20_000,
                cloud_cover_low=5,
                cloud_cover_mid=10,
                cloud_cover_high=15,
                wind_gusts_kmh=10,
                dew_point_c=10.0,
            )
        ]
        estimate = SeeingTransparencyService().estimate(
            hours,
            SkyQuality(4, 6.1, 20.8, "test", "Rural Sky"),
        )

        self.assertEqual(estimate.source, "BasicForecastSeeingProvider")
        self.assertIn(estimate.confidence, {"medium", "low"})


def _object(object_id: str, name: str, object_type: str, magnitude: str) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 deg",
        direction="Sud",
        best_time="22:00",
        observing_window="21:00 - 23:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="",
        score=80,
    )


def _geonames_row(
    geoname_id: str,
    name: str,
    ascii_name: str,
    alternate_names: str,
    latitude: str,
    longitude: str,
    country_code: str,
    admin1_code: str,
    population: str,
    timezone: str,
) -> str:
    columns = [
        geoname_id,
        name,
        ascii_name,
        alternate_names,
        latitude,
        longitude,
        "P",
        "PPLC",
        country_code,
        "",
        admin1_code,
        "",
        "",
        "",
        population,
        "",
        "",
        timezone,
        "2026-01-01",
    ]
    return "\t".join(columns)


class _temp_database:
    def __enter__(self) -> Path:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self._temp_dir.name) / "nightscope.db"
        base_dir = Path(__file__).resolve().parents[1]
        initialize_database(self.path, base_dir / "data" / "schema.sql")
        return self.path

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._temp_dir.cleanup()


class _controller:
    def __enter__(self) -> AppController:
        self._db_context = _temp_database()
        database_path = self._db_context.__enter__()
        base_dir = Path(__file__).resolve().parents[1]
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "hourly": {
                "time": [f"2026-06-21T{hour:02d}:00" for hour in range(24)],
                "cloud_cover": [20] * 24,
                "precipitation_probability": [0] * 24,
                "temperature_2m": [18.0] * 24,
                "relative_humidity_2m": [55] * 24,
                "wind_speed_10m": [6] * 24,
                "wind_gusts_10m": [10] * 24,
                "visibility": [20_000] * 24,
                "dew_point_2m": [10.0] * 24,
                "cloud_cover_low": [5] * 24,
                "cloud_cover_mid": [10] * 24,
                "cloud_cover_high": [15] * 24,
            }
        }
        self._weather_patch = patch("astro_viewer.app.services.weather_service.requests.get", return_value=response)
        self._weather_patch.start()
        self.controller = AppController(base_dir=base_dir, database_path=database_path)
        return self.controller

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if hasattr(self.controller._astronomy_engine, "close"):
            self.controller._astronomy_engine.close()
        self._weather_patch.stop()
        self._db_context.__exit__(exc_type, exc_value, traceback)


if __name__ == "__main__":
    unittest.main()
