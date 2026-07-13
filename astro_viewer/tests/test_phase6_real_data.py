from __future__ import annotations

import io
import os
import re
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import h5py
import numpy as np

from astro_viewer.app.astronomy.engine import ObserverLocation, ObservingNightWindow
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.city_repository import CityRepository
from astro_viewer.app.database.equipment_catalog_repository import EquipmentCatalogRepository
from astro_viewer.app.database.geonames_importer import import_geonames_cities
from astro_viewer.app.database.catalogue_repository import CatalogueRepository
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import AstronomicalEvent, CelestialObject
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherHour, WeatherSummary
from astro_viewer.app.services.earthdata_credentials import EarthdataCredentialState
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.equipment_setup_read_model import (
    EquipmentSetupReadModelBuilder,
)
from astro_viewer.app.services.light_pollution_service import LightPollutionService, NasaViirsBlackMarbleProvider
from astro_viewer.app.services.location_service import LocationDetectionResult
from astro_viewer.app.services.seeing_service import SeeingTransparencyService
from astro_viewer.app.viewmodels.app_controller import AppController
from astro_viewer.tests.geonames_fixture import write_small_geonames_fixture


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
            self.assertEqual(repository.search("Addis")[0]["city"], "Addis Ababa")
            self.assertTrue(any(city["city"] == "Addis Ababa" for city in repository.search("Addis Ababa")))
            addis_results = [city for city in repository.search("Addis Abeba") if city["country_code"] == "ET"]
            self.assertTrue(any(city["city"] == "Addis Ababa" for city in addis_results))
            self.assertFalse(any(city["city"] == "Addis Abeba" for city in addis_results))
            self.assertTrue(any(city["city"] in {"Milan", "Milano"} for city in repository.search("Milan")))
            self.assertTrue(any(city["city"] in {"Rome", "Roma"} for city in repository.search("Rome")))

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

    def test_geonames_import_keeps_context_out_of_city_aliases(self) -> None:
        with _temp_database() as database_path, tempfile.TemporaryDirectory() as temp_dir:
            geonames_path = Path(temp_dir) / "cities.txt"
            geonames_path.write_text(
                _geonames_row("1000", "Testville", "Testville", "US,CA,123,Alt Name", "34.0", "-118.0", "US", "CA", "15000", "America/Los_Angeles"),
                encoding="utf-8",
            )

            import sqlite3

            with closing(sqlite3.connect(database_path)) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("DELETE FROM CityAlias")
                connection.execute("DELETE FROM City")
                import_geonames_cities(connection, geonames_path)
                aliases = {
                    row["normalized_alias"]
                    for row in connection.execute("SELECT normalized_alias FROM CityAlias").fetchall()
                }
                search_name = connection.execute("SELECT search_name FROM City LIMIT 1").fetchone()["search_name"]

            self.assertIn("testville", aliases)
            self.assertIn("alt name", aliases)
            self.assertNotIn("us", aliases)
            self.assertNotIn("ca", aliases)
            self.assertNotIn("123", aliases)
            self.assertIn("us", search_name)
            self.assertIn("ca", search_name)

    def test_naked_eye_profile_keeps_recommendations_without_optics(self) -> None:
        with _controller() as controller:
            self.assertEqual(controller.currentSetup["name"], "Occhio nudo")
            self.assertFalse(controller.canUseEyepieces)

            controller.assignEquipmentToActiveProfile("eyepiece", controller.eyepieceCatalog[0]["catalog_id"])
            updated = controller._apply_equipment([_object("messier-M57", "Ring Nebula", "Planetary nebula", "8.8")])[0]

            self.assertEqual(updated.best_eyepiece, "")
            self.assertIn("Serve almeno", updated.recommended_setup)

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

    def test_suggestions_do_not_use_unowned_barlow(self) -> None:
        suggestion = EquipmentService().suggest_for_object(
            _object("saturn", "Saturno", "Pianeta", "0.8"),
            Telescope("scope", "Newton 150/750", 150, 750, "Newton", "manuale"),
            [Eyepiece("e1", "10 mm", 10, 60), Eyepiece("e2", "6 mm", 6, 58)],
            [],
        )

        self.assertEqual(suggestion["barlow"], "No")
        self.assertNotIn("Barlow", suggestion["setupText"])
        self.assertGreaterEqual(len(suggestion["setupOptions"]), 2)

    def test_suggestions_use_owned_barlow_when_it_improves_planetary_view(self) -> None:
        suggestion = EquipmentService().suggest_for_object(
            _object("saturn", "Saturno", "Pianeta", "0.8"),
            Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale"),
            [Eyepiece("e1", "25 mm", 25, 52)],
            [Barlow("b1", "Barlow 2x", 2.0, "1.25")],
        )

        self.assertIn("Barlow 2x", suggestion["setupText"])
        self.assertEqual(suggestion["barlow"], "Barlow 2x")

    def test_suggestions_prefer_wide_field_for_open_clusters(self) -> None:
        target = _object("messier-M45", "M45 Pleiadi", "Open cluster", "1.6")
        target = target.__class__(**{**target.__dict__, "apparent_size": "110 arcmin"})
        suggestion = EquipmentService().suggest_for_object(
            target,
            Telescope("scope", "Newton 130/650", 130, 650, "Newton", "manuale"),
            [Eyepiece("e1", "32 mm", 32, 68), Eyepiece("e2", "8 mm", 8, 60)],
            [Barlow("b1", "Barlow 2x", 2.0, "1.25")],
        )

        self.assertEqual(suggestion["bestEyepiece"], "32 mm")
        self.assertEqual(suggestion["barlow"], "No")

    def test_zoom_eyepiece_recommendation_uses_single_zoom(self) -> None:
        suggestion = EquipmentService().suggest_for_object(
            _object("saturn", "Saturno", "Pianeta", "0.8"),
            Telescope("scope", "Newton 130/650", 130, 650, "Newton", "manuale"),
            [
                Eyepiece(
                    "zoom",
                    "Baader Hyperion Zoom",
                    24,
                    60,
                    "1.25/2",
                    "Zoom",
                    8,
                    24,
                )
            ],
            [],
        )

        self.assertEqual(suggestion["bestEyepiece"], "Baader Hyperion Zoom")
        self.assertIn("mm", suggestion["suggestedPosition"])
        self.assertIn("@", suggestion["setupText"])

    def test_profile_suggestion_selects_best_telescope_for_deep_sky(self) -> None:
        target = _object("messier-M51", "M51", "Galaxy", "8.4")
        target = target.__class__(**{**target.__dict__, "apparent_size": "11 arcmin"})

        suggestion = EquipmentService().suggest_for_profile(
            target,
            [
                Telescope("small", "Maksutov 90", 90, 1250, "Maksutov", "manuale"),
                Telescope("large", "Dobson 200", 200, 1200, "Newton", "Dobson"),
            ],
            [Eyepiece("e1", "25 mm", 25, 52), Eyepiece("e2", "10 mm", 10, 60)],
            [],
            None,
            SkyQuality(7, 4.6, 18.8, "test", "Urban Sky", "high", 55.0, 18),
        )

        self.assertEqual(suggestion["telescopeName"], "Dobson 200")
        self.assertIn("Dobson 200 +", suggestion["setupText"])

    def test_poor_seeing_limits_planetary_magnification(self) -> None:
        suggestion = EquipmentService().suggest_for_object(
            _object("saturn", "Saturno", "Pianeta", "0.8"),
            Telescope("scope", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale"),
            [Eyepiece("e1", "25 mm", 25, 52)],
            [Barlow("b1", "Barlow 2x", 2.0, "1.25")],
            SeeingTransparency("Poor", "Average", 30, 50, "Seeing scarso."),
        )

        self.assertEqual(suggestion["barlow"], "No")
        self.assertNotIn("Barlow 2x", suggestion["setupText"])

    def test_catalog_telescope_add_does_not_assign_profile_implicitly(self) -> None:
        with _controller() as controller:
            self.assertFalse(controller.canUseEyepieces)
            controller.addTelescope("Newton 150/750", "150", "750", "Newton", "manuale")

            self.assertFalse(controller.canUseEyepieces)
            self.assertEqual(controller.eyepieces, [])
            self.assertIn("aggiunto", controller.equipmentMessage.lower())

    def test_controller_recommendations_use_only_active_profile_equipment(self) -> None:
        with _controller() as controller:
            telescope = controller.telescopeCatalogModels[0]
            eyepiece_assigned = controller.eyepieceCatalog[0]
            assigned_name = f"{eyepiece_assigned['brand']} {eyepiece_assigned['model']}"
            eyepiece_unassigned = next(
                row
                for row in controller.eyepieceCatalog
                if f"{row['brand']} {row['model']}" != assigned_name
            )
            controller.assignEquipmentToActiveProfile("telescope", telescope["catalog_id"])
            controller.assignEquipmentToActiveProfile("eyepiece", eyepiece_assigned["catalog_id"])
            controller.assignEquipmentToActiveProfile("eyepiece", eyepiece_unassigned["catalog_id"])
            controller.removeEquipmentFromActiveProfile("eyepiece", eyepiece_unassigned["catalog_id"])

            updated = controller._apply_equipment([_object("jupiter", "Giove", "Pianeta", "-2.0")])[0]
            active_names = {item["name"] for item in controller.eyepieces}

            self.assertIn(updated.best_eyepiece, active_names)
            self.assertNotEqual(updated.best_eyepiece, f"{eyepiece_unassigned['brand']} {eyepiece_unassigned['model']}")
            self.assertEqual(len(controller.eyepieces), 1)

    def test_empty_profile_equipment_assignment_refreshes_home_without_restart(self) -> None:
        with _controller() as controller:
            telescope = controller.telescopeCatalogModels[0]
            eyepiece = controller.eyepieceCatalog[0]
            target = _object("messier-M57-empty-refresh", "M57 refresh", "Planetary nebula", "8.8")
            controller._base_solar_system_objects = []
            controller._base_deep_sky = [target]
            controller._solar_system_objects = []
            controller._visible_planets = []
            controller._deep_sky = [target]
            controller._selected_object = target
            controller._observing_night_window = _test_night_window()
            controller._weather_hours = [
                WeatherHour("2026-06-21T22:00", "22:00", 8, 0, 4, 45, 14.0, 20_000)
            ]
            controller._weather_summary = controller._score_service.weather_score(
                controller._weather_hours,
                controller._moon,
            )
            controller._sky_quality = SkyQuality(3, 6.2, 21.4, "Fonte test", "Cielo rurale", "high")
            controller._seeing_service = Mock()
            seeing = SeeingTransparency(
                "Excellent",
                "Excellent",
                95,
                95,
                "Test seeing stabile.",
            )
            controller._seeing_service.estimate.return_value = seeing
            controller._seeing_transparency = seeing
            controller._refresh_active_profile_dependencies()

            blocked_home = next(
                item for item in controller.recommendedDeepSky if item["id"] == "messier-M57-empty-refresh"
            )
            self.assertIn("Serve almeno", blocked_home["recommended_setup"])
            self.assertFalse(controller._deep_sky[0].visible)

            controller.assignEquipmentToActiveProfile("telescope", telescope["catalog_id"])
            controller.assignEquipmentToActiveProfile("eyepiece", eyepiece["catalog_id"])

            refreshed_home = next(
                item for item in controller.recommendedDeepSky if item["id"] == "messier-M57-empty-refresh"
            )
            self.assertNotEqual(blocked_home["recommended_setup"], refreshed_home["recommended_setup"])
            self.assertNotIn("Serve almeno", refreshed_home["recommended_setup"])
            self.assertTrue(controller._deep_sky[0].visible)
            self.assertEqual(controller.selectedObject["recommended_setup"], refreshed_home["recommended_setup"])
            self.assertTrue(
                any(
                    item["objectId"] == "messier-M57-empty-refresh" and "Serve almeno" not in item["setup"]
                    for item in controller.nightPlan
                )
            )

    def test_active_profile_barlow_assignment_refreshes_home_and_detail_without_restart(self) -> None:
        with _controller() as controller:
            controller.addTelescopeModel("Refresh", "Maksutov 90/1250", "Maksutov", "90", "1250", "manuale", "")
            controller.addEyepieceModel("Refresh", "25 mm", "Plossl", "25", "", "", "52", "1.25", "", "")
            controller.addBarlowModel("Refresh", "Barlow 2x", "2", "1.25", "")
            telescope = next(
                row
                for row in controller.telescopeCatalogModels
                if row["brand"] == "Refresh" and row["name"] == "Maksutov 90/1250"
            )
            eyepiece = next(
                row
                for row in controller.eyepieceCatalog
                if row["brand"] == "Refresh" and row["model"] == "25 mm"
            )
            barlow = next(
                row
                for row in controller.barlowCatalog
                if row["brand"] == "Refresh" and row["model"] == "Barlow 2x"
            )
            controller.assignEquipmentToActiveProfile("telescope", telescope["catalog_id"])
            controller.assignEquipmentToActiveProfile("eyepiece", eyepiece["catalog_id"])
            controller._seeing_service = Mock()
            seeing = SeeingTransparency(
                "Excellent",
                "Excellent",
                95,
                95,
                "Test seeing stabile.",
            )
            controller._seeing_service.estimate.return_value = seeing
            controller._seeing_transparency = seeing
            controller._weather_hours = [
                WeatherHour("2026-06-21T22:00", "22:00", 8, 0, 4, 45, 14.0, 20_000)
            ]
            controller._weather_summary = controller._score_service.weather_score(
                controller._weather_hours,
                controller._moon,
            )
            controller._sky_quality = SkyQuality(3, 6.2, 21.4, "Fonte test", "Cielo rurale", "high")
            target = _object("saturn-refresh-test", "Saturno refresh", "Pianeta", "0.8")
            controller._solar_system_objects = [target]
            controller._visible_planets = [target]
            controller._deep_sky = []
            controller._selected_object = target
            controller._refresh_active_profile_dependencies()

            before_detail = controller.selectedObject
            events = {"equipment": 0, "data": 0, "weather": 0, "selected": 0}
            controller.equipmentChanged.connect(lambda: events.__setitem__("equipment", events["equipment"] + 1))
            controller.dataChanged.connect(lambda: events.__setitem__("data", events["data"] + 1))
            controller.weatherChanged.connect(lambda: events.__setitem__("weather", events["weather"] + 1))
            controller.selectedObjectChanged.connect(lambda: events.__setitem__("selected", events["selected"] + 1))

            controller.assignEquipmentToActiveProfile("barlow", barlow["catalog_id"])

            after_detail = controller.selectedObject
            self.assertEqual(before_detail["barlow"], "No")
            self.assertIn("Refresh Barlow 2x", after_detail["barlow"])
            self.assertIn("Refresh Barlow 2x", after_detail["recommended_setup"])
            self.assertTrue(
                any(
                    item["objectId"] == "saturn-refresh-test" and "Refresh Barlow 2x" in item["setup"]
                    for item in controller.nightPlan
                )
            )
            self.assertGreaterEqual(events["equipment"], 1)
            self.assertGreaterEqual(events["data"], 1)
            self.assertGreaterEqual(events["weather"], 1)
            self.assertGreaterEqual(events["selected"], 1)

    def test_active_profile_switch_emits_full_profile_refresh_chain(self) -> None:
        with _controller() as controller:
            controller.addEquipmentProfile("Profilo switch refresh")
            profile = next(
                item for item in controller.equipmentProfiles if item["profile_name"] == "Profilo switch refresh"
            )
            events = {"equipment": 0, "data": 0, "weather": 0, "selected": 0}
            controller.equipmentChanged.connect(lambda: events.__setitem__("equipment", events["equipment"] + 1))
            controller.dataChanged.connect(lambda: events.__setitem__("data", events["data"] + 1))
            controller.weatherChanged.connect(lambda: events.__setitem__("weather", events["weather"] + 1))
            controller.selectedObjectChanged.connect(lambda: events.__setitem__("selected", events["selected"] + 1))

            controller.setActiveEquipmentProfile(int(profile["id"]))

            self.assertGreaterEqual(events["equipment"], 1)
            self.assertGreaterEqual(events["data"], 1)
            self.assertGreaterEqual(events["weather"], 1)
            self.assertGreaterEqual(events["selected"], 1)

    def test_duplicate_profile_messages_are_localized(self) -> None:
        with _controller() as controller:
            existing_name = controller.equipmentProfiles[0]["profile_name"]

            controller.addEquipmentProfile(existing_name.upper())
            self.assertEqual(controller.equipmentMessage, "Questo profilo esiste già.")

            controller.addEquipmentProfile("Profilo secondario")
            secondary = next(
                item
                for item in controller.equipmentProfiles
                if item["profile_name"] == "Profilo secondario"
            )
            controller.renameEquipmentProfile(int(secondary["id"]), existing_name)
            self.assertEqual(controller.equipmentMessage, "Questo profilo esiste già.")

    def test_calendar_opposition_setup_uses_active_profile(self) -> None:
        with _controller() as controller:
            telescope = controller.telescopeCatalogModels[0]
            eyepiece = controller.eyepieceCatalog[0]
            controller.assignEquipmentToActiveProfile("telescope", telescope["catalog_id"])
            controller.assignEquipmentToActiveProfile("eyepiece", eyepiece["catalog_id"])
            controller._events = [
                AstronomicalEvent(
                    id="saturn-1-test",
                    title="Saturno in opposizione",
                    event_type="Opposizione",
                    date_label="28/08/2026",
                    best_time="23:30",
                    usefulness=92,
                    setup="Telescopio medio",
                    note="Test",
                )
            ]

            setup = controller.events[0]["setup"]

            self.assertIn(controller.currentSetup["name"], setup)
            self.assertNotEqual(setup, "Telescopio medio")

    def test_calendar_opposition_event_exposes_target_object_id(self) -> None:
        with _controller() as controller:
            event = AstronomicalEvent(
                id="saturn-1-test",
                title="Saturno in opposizione",
                event_type="Opposizione",
                date_label="28/08/2026",
                best_time="23:30",
                usefulness=92,
                setup="Telescopio medio",
                note="Test",
            )

            data = controller._event_to_qml(event)

            self.assertEqual(data["targetObjectId"], "saturn")

    def test_calendar_keeps_meteor_showers_naked_eye(self) -> None:
        with _controller() as controller:
            event = AstronomicalEvent(
                id="shower-perseids-test",
                title="Massimo Perseidi",
                event_type="Sciame meteorico",
                date_label="12/08/2026",
                best_time="02:00 - 04:30",
                usefulness=78,
                setup="Occhio nudo",
                note="Test",
            )

            self.assertEqual(controller._event_to_qml(event)["setup"], "Occhio nudo")

    def test_calendar_solar_conjunction_does_not_recommend_profile_equipment(self) -> None:
        with _controller() as controller:
            telescope = controller.telescopeCatalogModels[0]
            eyepiece = controller.eyepieceCatalog[0]
            controller.assignEquipmentToActiveProfile("telescope", telescope["catalog_id"])
            controller.assignEquipmentToActiveProfile("eyepiece", eyepiece["catalog_id"])
            event = AstronomicalEvent(
                id="jupiter-solar-conjunction-test",
                title="Giove in congiunzione con il Sole",
                event_type="Congiunzione solare",
                date_label="21/01/2027",
                best_time="07:00",
                usefulness=20,
                setup="Nessuna configurazione osservativa",
                note="Test",
            )

            setup = controller._event_to_qml(event)["setup"]

            self.assertEqual(setup, "Nessuna configurazione osservativa")
            self.assertNotIn(controller.currentSetup["name"], setup)

    def test_calendar_profile_setup_is_future_safe_for_telescope_only_profile(self) -> None:
        with _controller() as controller:
            _set_profile_equipment(
                controller,
                telescopes=[Telescope("test-mak-90", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")],
                eyepieces=[
                    Eyepiece("test-10", "10 mm", 10, 60),
                    Eyepiece("test-25", "25 mm", 25, 52),
                ],
            )
            target = _metadata_object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification")

            calendar_setup, home_setup, object_detail_setup = _calendar_home_detail_setups(controller, target)

            self.assertEqual(home_setup, object_detail_setup)
            self.assertIn("Maksutov 90/1250 +", calendar_setup)

    def test_calendar_profile_setup_supports_binocular_only_targets(self) -> None:
        with _controller() as controller:
            _set_profile_equipment(
                controller,
                binoculars=[Binocular("test-nikon-10x50", "Nikon Monarch M5", 10, 50)],
            )

            for target in (
                _metadata_object("messier-M31", "M31", "Galaxy", "3.4", "190 arcmin", 3.17, "WideField"),
                _metadata_object("messier-M45", "M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField"),
                _metadata_object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification"),
            ):
                with self.subTest(target=target.id):
                    calendar_setup, home_setup, object_detail_setup = _calendar_home_detail_setups(controller, target)

                    self.assertEqual(calendar_setup, home_setup)
                    self.assertEqual(calendar_setup, object_detail_setup)
                    self.assertIn("Nikon Monarch M5 10×50", calendar_setup)

    def test_calendar_profile_setup_is_future_safe_for_mixed_profile_targets(self) -> None:
        with _controller() as controller:
            _set_profile_equipment(
                controller,
                telescopes=[Telescope("test-mak-90", "Maksutov 90/1250", 90, 1250, "Maksutov", "manuale")],
                eyepieces=[
                    Eyepiece("test-10", "10 mm", 10, 60),
                    Eyepiece("test-25", "25 mm", 25, 52),
                ],
                binoculars=[Binocular("test-nikon-10x50", "Nikon Monarch M5", 10, 50)],
            )
            targets = [
                _metadata_object("messier-M31", "M31", "Galaxy", "3.4", "190 arcmin", 3.17, "WideField"),
                _metadata_object("messier-M45", "M45", "Open cluster", "1.6", "110 arcmin", 1.83, "WideField"),
                _metadata_object("messier-M57", "M57", "Planetary nebula", "8.8", "86 arcsec", 0.024, "HighMagnification"),
                _metadata_object("messier-M27", "M27", "Planetary nebula", "7.4", "8 arcmin", 0.133, "General"),
            ]

            setups = {}
            for target in targets:
                with self.subTest(target=target.id):
                    calendar_setup, home_setup, object_detail_setup = _calendar_home_detail_setups(controller, target)

                    self.assertEqual(home_setup, object_detail_setup)
                    setups[target.id] = calendar_setup

            self.assertIn("Nikon Monarch M5 10×50", setups["messier-M31"])
            self.assertIn("Nikon Monarch M5 10×50", setups["messier-M45"])
            self.assertIn("Maksutov 90/1250 +", setups["messier-M57"])
            self.assertIn("Maksutov 90/1250 +", setups["messier-M27"])

    def test_calendar_moon_events_hide_generic_setup(self) -> None:
        with _controller() as controller:
            event = AstronomicalEvent(
                id="moon-new-test",
                title="Luna nuova",
                event_type="Luna",
                date_label="14/07/2026",
                best_time="12:43",
                usefulness=95,
                setup="Qualsiasi setup",
                note="Test",
            )

            setup = controller._event_to_qml(event)["setup"]

            self.assertIn("notte migliore del mese", setup.lower())
            self.assertNotEqual(setup, "Qualsiasi setup")

    def test_calendar_moon_events_expose_target_object_id(self) -> None:
        with _controller() as controller:
            moon_event = AstronomicalEvent(
                id="moon-first-quarter-test",
                title="Primo quarto",
                event_type="Luna",
                date_label="21/07/2026",
                best_time="22:10",
                usefulness=68,
                setup="Qualsiasi setup",
                note="Test",
            )
            eclipse_event = AstronomicalEvent(
                id="lunar-eclipse-test",
                title="Eclissi lunare parziale",
                event_type="Eclissi",
                date_label="07/09/2026",
                best_time="21:35",
                usefulness=76,
                setup="Occhio nudo",
                note="Test",
            )

            self.assertEqual(controller._event_to_qml(moon_event)["targetObjectId"], "moon")
            self.assertEqual(controller._event_to_qml(eclipse_event)["targetObjectId"], "moon")

    def test_controller_blocks_duplicate_catalog_telescopes(self) -> None:
        with _controller() as controller:
            controller.addTelescopeModel("Custom", "Newton 150/750", "Newton", "150", "750", "manuale", "")
            count = len(controller.equipmentSetups)

            controller.addTelescopeModel("Custom", "Newton 150/750", "Newton", "150", "750", "manuale", "")

            self.assertEqual(len(controller.equipmentSetups), count)
            self.assertIn("già presente", controller.equipmentMessage)

    def test_binocular_catalog_crud_is_persistent_in_controller(self) -> None:
        with _controller() as controller:
            initial_count = len(controller.binocularCatalog)
            controller.addBinocularModel("NightScope", "Test 10x50", "10", "50", True)

            self.assertEqual(len(controller.binocularCatalog), initial_count + 1)
            item = next(
                row
                for row in controller.binocularCatalog
                if row["brand"] == "NightScope" and row["model"] == "Test 10x50"
            )
            self.assertEqual(item["display_name"], "NightScope Test 10x50")
            self.assertEqual(item["spec_label"], "10×50")
            self.assertTrue(item["image_stabilized"])
            self.assertIn("aggiunto", controller.equipmentMessage.lower())

            controller.updateBinocularModel(item["id"], "NightScope", "Test 8x42", "8", "42", False)

            updated = next(
                row
                for row in controller.binocularCatalog
                if row["brand"] == "NightScope" and row["model"] == "Test 8x42"
            )
            self.assertEqual(updated["display_name"], "NightScope Test 8x42")
            self.assertEqual(updated["spec_label"], "8×42")
            self.assertFalse(updated["image_stabilized"])
            self.assertIn("aggiornato", controller.equipmentMessage.lower())

            controller.deleteBinocularModel(updated["id"])

            self.assertEqual(len(controller.binocularCatalog), initial_count)
            self.assertIn("eliminato", controller.equipmentMessage.lower())

    def test_binocular_catalog_validates_required_numeric_fields(self) -> None:
        with _controller() as controller:
            initial_count = len(controller.binocularCatalog)
            controller.addBinocularModel("", "Monarch M5", "10", "50", False)
            self.assertEqual(len(controller.binocularCatalog), initial_count)
            self.assertIn("obbligatori", controller.equipmentMessage)

            controller.addBinocularModel("Nikon", "Monarch M5", "0", "50", False)
            self.assertEqual(len(controller.binocularCatalog), initial_count)
            self.assertIn("Dati binocolo non validi", controller.equipmentMessage)

            controller.addBinocularModel("Nikon", "Monarch M5", "10.5", "50", False)
            self.assertEqual(len(controller.binocularCatalog), initial_count)
            self.assertIn("Dati binocolo non validi", controller.equipmentMessage)

            controller.addBinocularModel("Nikon", "Monarch M5", "10", "0", False)
            self.assertEqual(len(controller.binocularCatalog), initial_count)
            self.assertIn("Dati binocolo non validi", controller.equipmentMessage)

    def test_binoculars_can_be_assigned_to_profiles_without_changing_capabilities(self) -> None:
        with _controller() as controller:
            binocular = next(item for item in controller.binocularCatalog if item["image_stabilized"])
            before_capabilities = dict(controller.telescopeCapabilities)

            controller.assignEquipmentToActiveProfile("binocular", binocular["catalog_id"])

            assigned_binocular = next(
                item
                for item in controller.profileAssignedEquipment
                if item["kind"] == "binocular" and item["id"] == binocular["catalog_id"]
            )
            catalog_item = next(
                item
                for item in controller.profileEquipmentCatalog
                if item["kind"] == "binocular" and item["id"] == binocular["catalog_id"]
            )
            self.assertEqual(assigned_binocular["name"], binocular["display_name"])
            self.assertEqual(assigned_binocular["details"], binocular["spec_label"])
            self.assertEqual(assigned_binocular["secondaryBadge"], "IS")
            self.assertTrue(catalog_item["assigned"])
            self.assertEqual(controller.profileBinoculars[0]["specLabel"], binocular["spec_label"])
            self.assertEqual(controller.telescopeCapabilities, before_capabilities)

            controller.removeEquipmentFromActiveProfile("binocular", binocular["catalog_id"])

            self.assertFalse(any(item["kind"] == "binocular" for item in controller.profileAssignedEquipment))
            self.assertTrue(any(item["catalog_id"] == binocular["catalog_id"] for item in controller.binocularCatalog))
            self.assertEqual(controller.telescopeCapabilities, before_capabilities)

    def test_filters_and_reducers_are_profile_accessories_without_scoring_refresh(self) -> None:
        with _controller() as controller:
            optical_filter = next(
                item for item in controller.filterCatalog if item["filter_class"] == "OIII"
            )
            reducer = next(
                item for item in controller.reducerCatalog if item["visual_compatible"]
            )
            before_capabilities = dict(controller.telescopeCapabilities)

            with patch.object(controller, "_refresh_active_profile_dependencies") as refresh:
                controller.assignEquipmentToActiveProfile("filter", optical_filter["catalog_id"])
                controller.assignEquipmentToActiveProfile("reducer", reducer["catalog_id"])

            refresh.assert_not_called()
            assigned = controller.profileAssignedEquipment
            assigned_filter = next(item for item in assigned if item["kind"] == "filter")
            assigned_reducer = next(item for item in assigned if item["kind"] == "reducer")
            self.assertEqual(assigned_filter["id"], optical_filter["catalog_id"])
            self.assertEqual(assigned_reducer["id"], reducer["catalog_id"])
            self.assertEqual(controller.profileFilters[0]["id"], optical_filter["catalog_id"])
            self.assertEqual(controller.profileReducers[0]["id"], reducer["catalog_id"])
            self.assertEqual(controller.telescopeCapabilities, before_capabilities)
            self.assertEqual(
                controller._equipment_catalog_repository.profile_usage_count(
                    "filter",
                    optical_filter["catalog_id"],
                ),
                1,
            )
            self.assertEqual(
                controller._equipment_catalog_repository.profile_usage_count(
                    "reducer",
                    reducer["catalog_id"],
                ),
                1,
            )

            controller.removeEquipmentFromActiveProfile("filter", optical_filter["catalog_id"])
            controller.removeEquipmentFromActiveProfile("reducer", reducer["catalog_id"])

            self.assertFalse(
                any(item["kind"] in {"filter", "reducer"} for item in controller.profileAssignedEquipment)
            )
            self.assertEqual(controller.telescopeCapabilities, before_capabilities)

    def test_owned_filter_recommendation_reaches_home_observing_detail(self) -> None:
        with _controller() as controller:
            optical_filter = next(
                item for item in controller.filterCatalog if item["filter_class"] == "OIII"
            )
            controller.assignEquipmentToActiveProfile(
                "filter",
                optical_filter["catalog_id"],
            )
            target = controller._apply_object_content(
                _object("messier-M27", "M27", "Planetary nebula", "7.4")
            )
            telescope = max(controller._telescopes, key=lambda item: item.aperture_mm)
            controller._equipment_setup_read_models_by_object_id[target.id] = (
                EquipmentSetupReadModelBuilder().from_suggestion(
                    target,
                    {
                        "setupText": telescope.name,
                        "setupOptions": [],
                        "telescopeId": telescope.id,
                        "telescopeName": telescope.name,
                        "equipmentType": "Telescope",
                        "setupType": "telescope",
                    },
                )
            )
            controller._selected_object = target
            controller._selected_object_source = "observing"
            controller._sky_compass_candidate_snapshot = [target]

            payload = controller.observingObjectDetail
            recommendation = payload["equipment"]["filterRecommendations"]["primary"]

            self.assertEqual(target.best_filter_class, "OIII")
            self.assertTrue(recommendation["available"])
            self.assertEqual(recommendation["filterClass"], "OIII")
            self.assertEqual(recommendation["filterId"], optical_filter["catalog_id"])
            self.assertEqual(
                recommendation["value"],
                optical_filter["display_name"],
            )

    def test_filter_recommendation_is_hidden_for_binocular_setup(self) -> None:
        with _controller() as controller:
            optical_filter = next(
                item for item in controller.filterCatalog if item["filter_class"] == "OIII"
            )
            controller.assignEquipmentToActiveProfile(
                "filter",
                optical_filter["catalog_id"],
            )
            target = controller._apply_object_content(
                _object("messier-M27", "M27", "Planetary nebula", "7.4")
            )
            controller._equipment_setup_read_models_by_object_id[target.id] = (
                EquipmentSetupReadModelBuilder().from_suggestion(
                    target,
                    {
                        "setupText": "Binocolo 10x50",
                        "setupOptions": [],
                        "equipmentType": "Binocular",
                        "setupType": "binocular",
                    },
                )
            )
            controller._selected_object = target
            controller._selected_object_source = "observing"
            controller._sky_compass_candidate_snapshot = [target]

            recommendations = controller.observingObjectDetail["equipment"][
                "filterRecommendations"
            ]

            self.assertEqual(recommendations, {"primary": {}, "optionalColor": {}})

    def test_reducer_recommendation_uses_target_setup_and_active_profile(self) -> None:
        with _controller() as controller:
            telescope = next(
                item
                for item in controller.telescopeCatalogModels
                if item["brand"] == "Celestron" and item["name"] == "NexStar 8SE"
            )
            reducer = next(
                item
                for item in controller.reducerCatalog
                if item["brand"] == "Celestron"
                and item["model"] == "Reducer-Corrector f/6.3"
            )
            target = controller._apply_object_content(
                _object("messier-M31", "M31", "Spiral galaxy", "3.4")
            )
            setup_model = EquipmentSetupReadModelBuilder().from_suggestion(
                target,
                {
                    "setupText": "Celestron NexStar 8SE",
                    "setupOptions": [],
                    "telescopeId": telescope["catalog_id"],
                    "telescopeName": "Celestron NexStar 8SE",
                    "equipmentType": "Telescope",
                    "setupType": "telescope",
                },
            )
            controller._equipment_setup_read_models_by_object_id[target.id] = setup_model
            controller._selected_object = target
            controller._selected_object_source = "observing"
            controller._sky_compass_candidate_snapshot = [target]

            suggested = controller.observingObjectDetail["equipment"][
                "reducerRecommendation"
            ]
            self.assertTrue(target.imaging_reducer_recommended)
            self.assertFalse(suggested["available"])
            self.assertIn(reducer["display_name"], suggested["value"])

            controller.assignEquipmentToActiveProfile(
                "reducer",
                reducer["catalog_id"],
            )

            available = controller.observingObjectDetail["equipment"][
                "reducerRecommendation"
            ]
            self.assertTrue(available["available"])
            self.assertEqual(
                available["items"][0]["reducerId"],
                reducer["catalog_id"],
            )

    def test_filter_and_reducer_controller_crud_keeps_custom_provenance(self) -> None:
        with _controller() as controller:
            initial_filter_count = len(controller.filterCatalog)
            initial_reducer_count = len(controller.reducerCatalog)

            with patch.object(controller, "_refresh_active_profile_dependencies") as refresh:
                controller.addFilterModel(
                    "NightScope",
                    "Filtro controller",
                    "UHC",
                    "",
                    "25",
                    "95",
                    "100",
                    "Test",
                )
                controller.addReducerModel(
                    "NightScope",
                    "Riduttore controller",
                    "0.8",
                    "REFRACTOR",
                    controller.telescopeCatalogModels[0]["catalog_id"],
                    "M48",
                    "55",
                    True,
                    True,
                    True,
                    "Test",
                )

            refresh.assert_not_called()
            self.assertEqual(len(controller.filterCatalog), initial_filter_count + 1)
            self.assertEqual(len(controller.reducerCatalog), initial_reducer_count + 1)
            optical_filter = next(
                item for item in controller.filterCatalog if item["brand"] == "NightScope"
            )
            reducer = next(
                item for item in controller.reducerCatalog if item["brand"] == "NightScope"
            )
            self.assertFalse(optical_filter["is_builtin"])
            self.assertFalse(reducer["is_builtin"])
            self.assertEqual(
                reducer["compatible_telescope_ids"],
                [controller.telescopeCatalogModels[0]["catalog_id"]],
            )

            controller.deleteFilterModel(optical_filter["id"], False)
            controller.deleteReducerModel(reducer["id"], False)

            self.assertEqual(len(controller.filterCatalog), initial_filter_count)
            self.assertEqual(len(controller.reducerCatalog), initial_reducer_count)

    def test_sidebar_navigation_groups_configuration_and_catalogs(self) -> None:
        ui_dir = Path(__file__).resolve().parents[1] / "app" / "ui"
        main_qml = (ui_dir / "main.qml").read_text(encoding="utf-8")
        binoculars_qml = (ui_dir / "pages" / "EquipmentBinocularsPage.qml").read_text(encoding="utf-8")
        telescopes_qml = (ui_dir / "pages" / "EquipmentTelescopesPage.qml").read_text(encoding="utf-8")
        optics_qml = (ui_dir / "pages" / "EquipmentOpticsPage.qml").read_text(encoding="utf-8")
        filters_reducers_qml = (
            ui_dir / "pages" / "EquipmentFiltersReducersPage.qml"
        ).read_text(encoding="utf-8")
        profiles_qml = (ui_dir / "pages" / "EquipmentProfilesPage.qml").read_text(encoding="utf-8")
        home_qml = (ui_dir / "pages" / "HomePage.qml").read_text(encoding="utf-8")
        object_catalogue_qml = (ui_dir / "pages" / "ObjectCataloguePage.qml").read_text(encoding="utf-8")
        object_detail_qml = (ui_dir / "pages" / "ObjectDetailPage.qml").read_text(encoding="utf-8")
        home_overview_service = (
            Path(__file__).resolve().parents[1] / "app" / "services" / "home_night_plan_overview.py"
        ).read_text(encoding="utf-8")

        expected_labels = [
            'text: qsTr("Home")',
            'text: qsTr("Calendario")',
            'text: qsTr("Log Osservazioni")',
            'text: qsTr("Meteo")',
            'text: qsTr("Configurazione")',
            'text: qsTr("Località")',
            'text: qsTr("Provider dati")',
            'text: qsTr("Profili")',
            'text: qsTr("Cataloghi")',
            'text: qsTr("Oggetti celesti")',
            'text: qsTr("Telescopi")',
            'text: qsTr("Oculari e Barlow")',
            'text: qsTr("Filtri e riduttori")',
            'text: qsTr("Binocoli")',
        ]
        positions = [main_qml.index(label) for label in expected_labels]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('text: qsTr("Strumenti")', main_qml)
        self.assertIn("dataProviders", main_qml)
        self.assertIn("observationLog", main_qml)
        self.assertIn("equipmentProfiles", main_qml)
        self.assertIn("objectCatalogue", main_qml)
        self.assertIn("equipmentTelescopes", main_qml)
        self.assertIn("equipmentOptics", main_qml)
        self.assertIn("equipmentFiltersReducers", main_qml)
        self.assertIn("equipmentBinoculars", main_qml)
        self.assertIn("DataProvidersPage", main_qml)
        self.assertIn("ObservationLogPage", main_qml)
        self.assertIn("EquipmentProfilesPage", main_qml)
        self.assertIn("ObjectCataloguePage", main_qml)

        self.assertIn("EquipmentTelescopesPage", main_qml)
        self.assertIn("EquipmentOpticsPage", main_qml)
        self.assertIn("EquipmentFiltersReducersPage", main_qml)
        self.assertIn("EquipmentBinocularsPage", main_qml)
        self.assertIn("appController.homeObservingOverview", main_qml)
        self.assertIn("sidebarSession", main_qml)
        self.assertIn("limitingFactor", main_qml)
        self.assertNotIn("appController.weatherSummary.scoreValue", main_qml)
        self.assertNotIn("appController.weatherSummary.alert", main_qml)
        self.assertIn('window.detailBackTarget === "objectCatalogue" ? qsTr("Torna al catalogo")', main_qml)
        self.assertIn("controller.catalogueObjects", object_catalogue_qml)
        self.assertIn("appController.selectCatalogueObject", main_qml)
        self.assertIn('text: qsTr("Esplora gli oggetti astronomici disponibili nel catalogo.")', object_catalogue_qml)
        self.assertIn('placeholderText: qsTr("Cerca ID o nome...")', object_catalogue_qml)
        for filter_label in (
            'text: qsTr("Ricerca")',
            'text: qsTr("Catalogo")',
            'text: qsTr("Tipo")',
            'text: qsTr("Costellazione")',
            'text: qsTr("Osservazione")',
            'text: qsTr("Visibilità")',
        ):
            self.assertIn(filter_label, object_catalogue_qml)
        self.assertIn("controller.catalogueMonthLabels", object_catalogue_qml)
        self.assertIn("enabled: controller.catalogueVisibleThisMonthFilter", object_catalogue_qml)
        self.assertIn("controller.setCatalogueMonth(currentIndex + 1)", object_catalogue_qml)
        self.assertIn("controller.setCatalogueVisibleThisMonthFilter(checked)", object_catalogue_qml)
        self.assertIn('text: qsTr("Visibili nel mese")', object_catalogue_qml)
        self.assertNotIn('FilterLabel { text: qsTr("Mese") }', object_catalogue_qml)
        self.assertLess(object_catalogue_qml.index("id: visibleThisMonthFilter"), object_catalogue_qml.index("id: monthFilter"))
        self.assertIn("Layout.preferredWidth: 170", object_catalogue_qml)
        self.assertIn('TableHeader { text: qsTr("Tipo"); Layout.preferredWidth: 164 }', object_catalogue_qml)
        self.assertIn("root.textOrDash(itemData.type_label)", object_catalogue_qml)
        self.assertIn('model: root.choiceModel("typeChoices")', object_catalogue_qml)
        self.assertIn('model: root.choiceModel("observationTypeChoices")', object_catalogue_qml)
        self.assertIn('valueRole: "value"', object_catalogue_qml)
        for table_header in (
            'TableHeader { text: qsTr("Costellazione")',
            'TableHeader { text: qsTr("Magnitudine")',
            'TableHeader { text: qsTr("Dimensione")',
            'TableHeader { text: qsTr("Osservazione")',
            'TableHeader { text: qsTr("Utile (≥15°)"); Layout.preferredWidth: 104 }',
        ):
            self.assertIn(table_header, object_catalogue_qml)
        self.assertNotIn('TableHeader { text: qsTr("Visibile nel mese")', object_catalogue_qml)
        self.assertNotIn('TableHeader { text: qsTr("Cost.")', object_catalogue_qml)
        self.assertNotIn('TableHeader { text: qsTr("Mag.")', object_catalogue_qml)
        self.assertNotIn('TableHeader { text: qsTr("Dim.")', object_catalogue_qml)
        self.assertNotIn('TableHeader { text: qsTr("Osserv.")', object_catalogue_qml)
        self.assertIn("root.textOrDash(itemData.constellation)", object_catalogue_qml)
        self.assertIn("is_usefully_observable_label", object_catalogue_qml)
        self.assertIn("root.usefulObservableText(itemData)", object_catalogue_qml)
        self.assertNotIn("visible_this_month_label", object_catalogue_qml)
        self.assertNotIn('controller.catalogueFilteredCount + " / " + controller.catalogueTotalCount', object_catalogue_qml)
        self.assertIn("backLabel", object_detail_qml)
        self.assertIn("property bool isCatalogueDetail", object_detail_qml)
        self.assertIn('root.isCatalogueDetail ? qsTr("Scheda catalogo")', object_detail_qml)
        self.assertIn("root.hasObject && !root.isCatalogueDetail", object_detail_qml)
        self.assertIn("label: root.originMetricLabel()", object_detail_qml)
        self.assertIn('"label": qsTr("Costellazione")', object_detail_qml)
        self.assertIn('text: qsTr("Catalogo binocoli")', binoculars_qml)
        self.assertIn('placeholderText: qsTr("Cerca binocolo...")', binoculars_qml)
        self.assertIn('placeholderText: qsTr("Diametro obiettivo (mm)")', binoculars_qml)
        self.assertIn("controller.binocularCatalog", binoculars_qml)
        self.assertIn("controller.addBinocularModel", binoculars_qml)
        self.assertIn("controller.updateBinocularModel", binoculars_qml)
        self.assertIn("controller.deleteBinocularModel", binoculars_qml)
        self.assertIn('text: qsTr("Stabilizzato")', binoculars_qml)
        self.assertIn("controller.equipmentUsage(\"binocular\"", binoculars_qml)
        for equipment_qml in (telescopes_qml, optics_qml, binoculars_qml, filters_reducers_qml):
            self.assertGreaterEqual(
                len(
                    re.findall(
                        r"visible:\s*![A-Za-z0-9_.]*itemData\.is_builtin",
                        equipment_qml,
                    )
                ),
                2,
            )
        self.assertIn('text: qsTr("Catalogo filtri e riduttori")', filters_reducers_qml)
        self.assertIn("controller.filterCatalog", filters_reducers_qml)
        self.assertIn("controller.reducerCatalog", filters_reducers_qml)
        self.assertIn("controller.filterClassOptions", filters_reducers_qml)
        self.assertNotIn("filterBarrel", filters_reducers_qml)
        self.assertIn("controller.addFilterModel", filters_reducers_qml)
        self.assertIn("controller.addReducerModel", filters_reducers_qml)
        self.assertIn("controller.deleteFilterModel", filters_reducers_qml)
        self.assertIn("controller.deleteReducerModel", filters_reducers_qml)
        self.assertIn("reducerTelescopeGrid", filters_reducers_qml)
        self.assertIn("compatible_telescope_ids", filters_reducers_qml)
        self.assertIn('"1 selezionato"', filters_reducers_qml)
        self.assertIn('" selezionati"', filters_reducers_qml)
        self.assertNotIn("reducerModels", filters_reducers_qml)
        self.assertIn('title: qsTr("Binocoli")', profiles_qml)
        self.assertIn('emptyText: qsTr("Nessun binocolo assegnato.")', profiles_qml)
        self.assertIn('title: qsTr("Filtri")', profiles_qml)
        self.assertIn('title: qsTr("Riduttori")', profiles_qml)
        self.assertIn("model: root.equipmentFilterOptions", profiles_qml)
        self.assertIn("homeNightPlanOverview", home_qml)
        self.assertNotIn('equipmentType === "Binocular"', home_qml)
        self.assertIn('setup_model.equipment_type == "Binocular"', home_overview_service)
        self.assertIn('equipmentType === "Binocular"', object_detail_qml)
        self.assertIn("setupDetailText()", object_detail_qml)
        self.assertIn("Pupilla d'uscita", object_detail_qml)
        self.assertIn("setupFilterRecommendations()", object_detail_qml)
        self.assertIn("filterRecommendationsData", object_detail_qml)
        self.assertIn("reducerRecommendationData", object_detail_qml)

    def test_observation_log_controller_supports_complete_crud(self) -> None:
        with _controller() as controller:
            defaults = controller.observationLogDefaults
            initial_count = len(controller.observationLog)

            self.assertTrue(
                controller.addObservation(
                    defaults["dateValue"],
                    defaults["timeValue"],
                    "M42",
                    "Addis Ababa",
                    "Dobson",
                    "10 mm",
                    4,
                    "Nebulosità evidente",
                )
            )
            self.assertEqual(len(controller.observationLog), initial_count + 1)
            observation_id = controller.observationLog[0]["id"]
            self.assertTrue(
                controller.updateObservation(
                    observation_id,
                    defaults["dateValue"],
                    defaults["timeValue"],
                    "M42",
                    "Addis Ababa",
                    "Dobson",
                    "8 mm",
                    5,
                    "Dettaglio aggiornato",
                )
            )
            self.assertEqual(controller.observationLog[0]["rating"], 5)
            self.assertEqual(controller.observationLogSummary["total"], initial_count + 1)
            self.assertTrue(controller.deleteObservation(observation_id))
            self.assertEqual(len(controller.observationLog), initial_count)
            self.assertFalse(
                controller.addObservation(
                    defaults["dateValue"],
                    defaults["timeValue"],
                    "",
                    "",
                    "",
                    "",
                    4,
                    "",
                )
            )
            self.assertIn("oggetto", controller.observationMessage.lower())

    def test_object_detail_catalogue_mode_uses_catalogue_layout(self) -> None:
        object_detail_qml = (
            Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "ObjectDetailPage.qml"
        ).read_text(encoding="utf-8")

        self.assertIn("function catalogueMetadataItems()", object_detail_qml)
        self.assertIn("function includeCatalogueMetric(value)", object_detail_qml)
        self.assertIn('return text !== "n/d"', object_detail_qml)
        self.assertIn("visible: root.isCatalogueDetail", object_detail_qml)
        self.assertIn('title: qsTr("Dati di catalogo")', object_detail_qml)
        self.assertIn("columns: root.width > 1160 ? 4 : root.width > 760 ? 2 : 1", object_detail_qml)
        self.assertIn("model: root.catalogueMetadataItems()", object_detail_qml)
        self.assertIn("text: root.catalogueBadgeText()", object_detail_qml)
        self.assertIn('title: qsTr("Descrizione")', object_detail_qml)
        self.assertNotIn("Oggetto di catalogo", object_detail_qml)

        for label in (
            '"label": qsTr("Catalogo")',
            '"label": qsTr("ID catalogo")',
            '"label": qsTr("Tipo")',
            '"label": qsTr("Costellazione")',
            '"label": qsTr("Magnitudine")',
            '"label": qsTr("Dimensione")',
            '"label": qsTr("Dim. max")',
            '"label": qsTr("Osservazione")',
            '"label": "A.R."',
            '"label": "Dec"',
            '"label": qsTr("Utile (≥15°)")',
            '"label": qsTr("Visibile nel mese corrente")',
        ):
            self.assertIn(label, object_detail_qml)
        self.assertIn("objectData.catalogueUsefullyObservableLabel", object_detail_qml)
        self.assertIn("objectData.catalogueUsefullyObservable", object_detail_qml)
        self.assertIn("objectData.catalogueVisibleCurrentMonthLabel", object_detail_qml)
        self.assertIn("objectData.catalogueVisibleCurrentMonth", object_detail_qml)
        self.assertIn("objectData.catalogueTypeLabel", object_detail_qml)
        self.assertIn("objectData.catalogueObservationTypeLabel", object_detail_qml)
        self.assertIn("objectData.catalogueIntroText", object_detail_qml)
        self.assertIn("controller.selectedObject", object_detail_qml)
        self.assertIn("controller.observingObjectDetail", object_detail_qml)

        for observing_section in (
            'title: qsTr("Finestra osservativa")',
            'title: qsTr("Configurazione consigliata")',
        ):
            self.assertIn(observing_section, object_detail_qml)
        self.assertIn('title: root.evaluationData.title || qsTr("Valutazione osservativa")', object_detail_qml)
        self.assertIn('label: qsTr("Momento migliore")', object_detail_qml)
        self.assertIn('label: qsTr("Inizio utile")', object_detail_qml)
        self.assertIn('label: qsTr("Fine utile")', object_detail_qml)
        self.assertIn("root.geometryData.showHorizonEvents === true", object_detail_qml)
        self.assertIn('title: qsTr("Ciclo lunare")', object_detail_qml)
        self.assertIn('objectData.id === "moon"', object_detail_qml)
        self.assertIn("objectData.moonPhase", object_detail_qml)
        self.assertIn("objectData.moonIllumination", object_detail_qml)
        self.assertNotIn("Storico osservazioni", object_detail_qml)
        self.assertNotIn("controller.observationHistory", object_detail_qml)
        self.assertNotIn("controller.saveObservation", object_detail_qml)
        description_start = object_detail_qml.index('title: qsTr("Descrizione")')
        configuration_start = object_detail_qml.index('title: qsTr("Configurazione consigliata")')
        self.assertNotIn("maximumLineCount", object_detail_qml[description_start:configuration_start])
        self.assertRegex(
            object_detail_qml,
            r"GridLayout \{\s+id: observingDetailGrid\s+"
            r"visible: root\.hasObject && !root\.isCatalogueDetail[\s\S]+"
            r'title: qsTr\("Finestra osservativa"\)',
        )
        self.assertIn("columns: root.width > 1180 ? 2 : 1", object_detail_qml)
        self.assertRegex(
            object_detail_qml,
            r"visible: root\.hasObject && !root\.isCatalogueDetail[\s\S]{0,180}"
            r'title: qsTr\("Configurazione consigliata"\)',
        )

    def test_catalogue_objects_expose_all_deep_sky_rows_sorted(self) -> None:
        with _controller() as controller:
            objects = controller.catalogueObjects
            messier_objects = [item for item in objects if item["catalogue"] == "Messier"]
            caldwell_objects = [item for item in objects if item["catalogue"] == "Caldwell"]

            self.assertEqual(len(objects), 228)
            self.assertEqual(len(messier_objects), 110)
            self.assertEqual(len(caldwell_objects), 109)
            self.assertEqual([item["catalogue_id"] for item in messier_objects[:5]], ["M1", "M2", "M3", "M4", "M5"])
            self.assertEqual(messier_objects[-1]["catalogue_id"], "M110")
            self.assertEqual([item["catalogue_id"] for item in caldwell_objects[:5]], ["C1", "C2", "C3", "C4", "C5"])
            self.assertEqual(caldwell_objects[-1]["catalogue_id"], "C109")
            self.assertEqual(caldwell_objects[22]["object_id"], "caldwell-C23")
            self.assertEqual(caldwell_objects[22]["name"], "NGC 891")
            self.assertEqual(messier_objects[0]["catalogue"], "Messier")
            self.assertEqual(messier_objects[0]["object_id"], "messier-M1")
            self.assertEqual(messier_objects[0]["name"], "Crab Nebula")
            self.assertEqual(messier_objects[0]["type"], "Supernova remnant")
            self.assertEqual(messier_objects[0]["type_label"], "Resto di supernova")
            self.assertEqual(messier_objects[0]["constellation"], "Taurus")
            self.assertEqual(messier_objects[0]["recommended_observation_type"], "General")
            self.assertEqual(messier_objects[0]["recommended_observation_type_label"], "Generale")
            self.assertTrue(all(item["type_label"] != item["type"] for item in messier_objects))
            self.assertTrue(
                all(
                    item["recommended_observation_type_label"] != item["recommended_observation_type"]
                    for item in messier_objects
                )
            )

            required_fields = {
                "catalogue",
                "object_id",
                "catalogue_id",
                "name",
                "type",
                "constellation",
                "magnitude",
                "apparent_size",
                "max_angular_size_deg",
                "recommended_observation_type",
                "recommended_observation_type_label",
                "type_label",
                "description",
            }
            self.assertTrue(required_fields.issubset(messier_objects[0]))

    def test_catalogue_includes_solar_system_objects(self) -> None:
        with _controller() as controller:
            objects = controller.catalogueObjects
            solar_objects = [item for item in objects if item["catalogue"] == "Sistema Solare"]

            self.assertEqual(len(solar_objects), 9)
            self.assertEqual(
                [item["name"] for item in solar_objects],
                ["Sole", "Luna", "Mercurio", "Venere", "Marte", "Giove", "Saturno", "Urano", "Nettuno"],
            )
            self.assertEqual([item["catalogue_id"] for item in solar_objects], [f"S{index}" for index in range(1, 10)])
            self.assertEqual(
                [item["object_id"] for item in solar_objects],
                ["sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"],
            )
            self.assertEqual(
                controller.catalogueFilterOptions["catalogues"],
                ["Caldwell", "Messier", "Sistema Solare"],
            )
            self.assertIn(
                {"value": "Open cluster", "label": "Ammasso aperto"},
                controller.catalogueFilterOptions["typeChoices"],
            )
            self.assertIn(
                {"value": "HighMagnification", "label": "Alto ingrandimento"},
                controller.catalogueFilterOptions["observationTypeChoices"],
            )
            self.assertEqual(
                [item["label"] for item in controller.catalogueFilterOptions["observationTypeChoices"]],
                ["Alto ingrandimento", "Campo largo", "Generale"],
            )
            self.assertTrue(all(item["constellation"] == "" for item in solar_objects))
            self.assertEqual(
                {item["type"] for item in solar_objects},
                {"Stella", "Satellite naturale", "Pianeta"},
            )

    def test_catalogue_search_by_catalogue_id_and_name(self) -> None:
        with _controller() as controller:
            controller.searchCatalogue("M31")
            by_id = controller.catalogueObjects
            self.assertEqual([item["catalogue_id"] for item in by_id], ["M31"])

            controller.searchCatalogue("Crab")
            by_name = controller.catalogueObjects
            self.assertEqual([item["catalogue_id"] for item in by_name], ["M1"])

            controller.searchCatalogue("Mars")
            mars_by_english_name = controller.catalogueObjects
            self.assertEqual([item["name"] for item in mars_by_english_name], ["Marte"])

            controller.searchCatalogue("Giove")
            jupiter_by_italian_name = controller.catalogueObjects
            self.assertEqual(
                [item["name"] for item in jupiter_by_italian_name],
                ["Giove", "NGC 3242 - Fantasma di Giove"],
            )

            controller.searchCatalogue("Jupiter")
            jupiter_by_english_name = controller.catalogueObjects
            self.assertEqual([item["name"] for item in jupiter_by_english_name], ["Giove"])

            controller.searchCatalogue("S5")
            mars_by_display_id = controller.catalogueObjects
            self.assertEqual([item["name"] for item in mars_by_display_id], ["Marte"])

            controller.searchCatalogue("C23")
            by_caldwell_id = controller.catalogueObjects
            self.assertEqual([item["object_id"] for item in by_caldwell_id], ["caldwell-C23"])

            controller.searchCatalogue("NGC 891")
            by_ngc_id = controller.catalogueObjects
            self.assertEqual([item["catalogue_id"] for item in by_ngc_id], ["C23"])

    def test_catalogue_filters_by_catalogue_type_constellation_and_observation_type(self) -> None:
        with _controller() as controller:
            self.assertEqual(
                controller.catalogueFilterOptions["catalogues"],
                ["Caldwell", "Messier", "Sistema Solare"],
            )

            controller.setCatalogueFilter("catalogue", "Caldwell")
            self.assertEqual(len(controller.catalogueObjects), 109)
            self.assertEqual(controller.catalogueObjects[0]["catalogue_id"], "C1")
            self.assertEqual(controller.catalogueObjects[-1]["catalogue_id"], "C109")

            controller.clearCatalogueFilters()
            controller.setCatalogueFilter("catalogue", "Messier")
            self.assertEqual(len(controller.catalogueObjects), 110)

            controller.clearCatalogueFilters()
            controller.setCatalogueFilter("catalogue", "Sistema Solare")
            solar_objects = controller.catalogueObjects
            self.assertEqual(len(solar_objects), 9)
            self.assertTrue(all(item["catalogue"] == "Sistema Solare" for item in solar_objects))

            controller.setCatalogueFilter("type", "Pianeta")
            planets = controller.catalogueObjects
            self.assertEqual([item["name"] for item in planets], ["Mercurio", "Venere", "Marte", "Giove", "Saturno", "Urano", "Nettuno"])

            controller.clearCatalogueFilters()
            controller.setCatalogueFilter("type", "Supernova remnant")
            self.assertEqual(
                [item["catalogue_id"] for item in controller.catalogueObjects],
                ["C33", "C34", "M1"],
            )

            controller.clearCatalogueFilters()
            controller.setCatalogueFilter("constellation", "Taurus")
            taurus_ids = {item["catalogue_id"] for item in controller.catalogueObjects}
            self.assertIn("M1", taurus_ids)
            self.assertTrue(all(item["constellation"] == "Taurus" for item in controller.catalogueObjects))

            controller.clearCatalogueFilters()
            controller.setCatalogueFilter("observation_type", "HighMagnification")
            self.assertGreater(len(controller.catalogueObjects), 0)
            self.assertTrue(
                all(
                    item["recommended_observation_type"] == "HighMagnification"
                    for item in controller.catalogueObjects
                )
            )

    def test_catalogue_month_selector_uses_current_year(self) -> None:
        with _controller() as controller:
            now = datetime.now(controller._zone())

            self.assertEqual(len(controller.catalogueMonthLabels), 12)
            self.assertEqual(controller.catalogueSelectedMonth, now.month)
            self.assertTrue(all(label.endswith(str(now.year)) for label in controller.catalogueMonthLabels))

    def test_skyfield_catalogue_month_visibility_uses_coordinates_location_and_solar_ephemeris(self) -> None:
        with _temp_database() as database_path:
            base_dir = Path(__file__).resolve().parents[1]
            repository = CatalogueRepository(database_path)
            engine = SkyfieldAstronomyEngine(base_dir / "data", repository)
            try:
                rows = []
                for messier_id in ("M13", "M1"):
                    row = repository.get_by_designation("Messier", messier_id)
                    self.assertIsNotNone(row)
                    rows.append(
                        {
                            "object_id": row["object_id"],
                            "right_ascension": row["ra"],
                            "declination": row["dec"],
                        }
                    )
                visibility = engine.catalogue_month_visibility(
                    rows,
                    ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa"),
                    2026,
                    6,
                    15.0,
                )
                solar_visibility = engine.catalogue_month_visibility(
                    [
                        {"object_id": "sun", "solar_system_body_id": "sun"},
                        {"object_id": "moon", "solar_system_body_id": "moon"},
                        {"object_id": "mercury", "solar_system_body_id": "mercury"},
                        {"object_id": "venus", "solar_system_body_id": "venus"},
                        {"object_id": "mars", "solar_system_body_id": "mars"},
                        {"object_id": "jupiter", "solar_system_body_id": "jupiter"},
                        {"object_id": "saturn", "solar_system_body_id": "saturn"},
                        {"object_id": "uranus", "solar_system_body_id": "uranus"},
                        {"object_id": "neptune", "solar_system_body_id": "neptune"},
                    ],
                    ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa"),
                    2026,
                    6,
                    15.0,
                )

                self.assertTrue(visibility["messier-M13"])
                self.assertFalse(visibility["messier-M1"])
                self.assertTrue(solar_visibility["sun"])
                self.assertTrue(solar_visibility["moon"])
                self.assertFalse(solar_visibility["mercury"])
                self.assertTrue(solar_visibility["venus"])
                self.assertFalse(solar_visibility["mars"])
                self.assertTrue(solar_visibility["jupiter"])
                self.assertTrue(solar_visibility["saturn"])
                self.assertFalse(solar_visibility["uranus"])
                self.assertTrue(solar_visibility["neptune"])
            finally:
                engine.close()

    def test_home_solar_system_candidates_respect_catalogue_month_visibility(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.catalogue_month_visibility.return_value = {
                "venus": True,
                "mars": False,
                "jupiter": True,
                "saturn": True,
                "uranus": False,
                "neptune": True,
            }
            controller._astronomy_engine = astronomy
            controller._location = ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa")
            controller._observing_night_window = _test_night_window()
            controller._catalogue_year = 2026
            controller._catalogue_selected_month = 6
            controller._invalidate_catalogue_visibility_cache()
            controller._base_solar_system_objects = [
                _planet("venus", "Venere"),
                _planet("mars", "Marte"),
                _planet("jupiter", "Giove"),
                _planet("saturn", "Saturno"),
                _planet("uranus", "Urano"),
                _planet("neptune", "Nettuno"),
            ]
            controller._deep_sky = []
            controller._base_deep_sky = []

            planner = Mock()
            planner.plan.return_value = []
            controller._night_planner_service = planner
            controller._weather_summary = WeatherSummary("Buono", 80, "", 10, 0, 5, 55, 18.0, "")
            controller._sky_quality = SkyQuality(4, 6.1, 20.8, "test", "Rural Sky")

            with patch.object(controller, "_apply_equipment", side_effect=lambda objects: objects):
                controller._refresh_equipment_recommendations_for_current_objects()
                controller._recalculate_observing_outputs()

            home_ids = [item["id"] for item in controller.visiblePlanets]
            self.assertEqual(home_ids, ["venus", "jupiter", "saturn", "neptune"])
            self.assertNotIn("mars", home_ids)
            self.assertNotIn("uranus", home_ids)

            planner_ids = [item.id for item in planner.plan.call_args.args[0]]
            self.assertEqual(planner_ids, ["venus", "jupiter", "saturn", "neptune"])
            astronomy.catalogue_month_visibility.assert_called_once()

    def test_solar_system_detail_can_be_above_horizon_without_monthly_useful_status(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.catalogue_month_visibility.return_value = {"mars": False}
            controller._astronomy_engine = astronomy
            controller._location = ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa")
            controller._catalogue_year = 2026
            controller._catalogue_selected_month = 6
            controller._invalidate_catalogue_visibility_cache()

            selected = controller._object_to_qml(
                _planet(
                    "mars",
                    "Marte",
                    current_altitude="62.0 gradi",
                    best_time="04:15",
                    observing_window="04:15 - 07:00",
                )
            )

            self.assertEqual(selected["observingStatus"], "Sopra l'orizzonte")
            self.assertIn("non utile per l'osservazione questo mese", selected["observingStatusDetail"])
            self.assertNotIn("Finestra migliore", selected["observingStatusDetail"])

    def test_catalogue_visible_this_month_filter_keeps_catalogue_complete_until_enabled(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.catalogue_month_visibility.return_value = {
                "messier-M13": True,
                "messier-M31": True,
            }
            controller._astronomy_engine = astronomy
            controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
            controller._invalidate_catalogue_visibility_cache()

            objects = controller.catalogueObjects
            self.assertEqual(len(objects), 228)
            self.assertEqual(astronomy.catalogue_month_visibility.call_count, 0)
            self.assertEqual(
                [item["visible_this_month_label"] for item in objects if item["catalogue_id"] in {"M13", "M31"}],
                ["—", "—"],
            )

            controller.setCatalogueVisibleThisMonthFilter(True)
            visible_objects = controller.catalogueObjects
            self.assertEqual([item["catalogue_id"] for item in visible_objects], ["M13", "M31"])
            self.assertTrue(all(item["visible_this_month"] for item in visible_objects))
            self.assertEqual(astronomy.catalogue_month_visibility.call_count, 1)

    def test_catalogue_detail_visibility_uses_current_month_independently_from_filter(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.catalogue_month_visibility.return_value = {"messier-M31": False}
            controller._astronomy_engine = astronomy
            controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
            controller._invalidate_catalogue_visibility_cache()
            current = datetime.now(controller._zone())
            controller._catalogue_selected_month = 1 if current.month != 1 else 2
            controller._catalogue_visible_this_month_only = False

            controller.selectCatalogueObject("messier-M31")
            selected = controller.selectedObject

            self.assertFalse(selected["catalogueVisibleCurrentMonth"])
            self.assertTrue(selected["catalogueVisibleCurrentMonthKnown"])
            self.assertEqual(selected["catalogueVisibleCurrentMonthLabel"], "No")
            self.assertEqual(selected["catalogueCurrentMonthLabel"], controller._catalogue_month_label(current.month))
            self.assertEqual(selected["catalogueVisibleThisMonthLabel"], "No")
            self.assertEqual(selected["catalogueTypeLabel"], "Galassia spirale")
            self.assertEqual(selected["catalogueObservationTypeLabel"], "Campo largo")
            self.assertTrue(selected["catalogueIntroText"])
            self.assertNotIn("Spiral galaxy", selected["catalogueIntroText"])

            call_args = astronomy.catalogue_month_visibility.call_args.args
            self.assertEqual([item["object_id"] for item in call_args[0]], ["messier-M31"])
            self.assertEqual(call_args[2:4], (current.year, current.month))

            controller.setCatalogueVisibleThisMonthFilter(True)
            controller._invalidate_catalogue_month_visibility_cache()
            self.assertEqual(controller.selectedObject["catalogueVisibleCurrentMonthLabel"], "No")
            astronomy.catalogue_month_visibility.assert_called_once()

    def test_catalogue_detail_current_month_visibility_is_unknown_without_location(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            controller._astronomy_engine = astronomy
            controller._location = None
            controller._invalidate_catalogue_visibility_cache()

            controller.selectCatalogueObject("messier-M31")
            selected = controller.selectedObject

            self.assertFalse(selected["catalogueVisibleCurrentMonth"])
            self.assertFalse(selected["catalogueVisibleCurrentMonthKnown"])
            self.assertEqual(selected["catalogueVisibleCurrentMonthLabel"], "—")
            astronomy.catalogue_month_visibility.assert_not_called()

    def test_catalogue_visibility_cache_invalidates_on_month_and_location_change(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.catalogue_month_visibility.return_value = {}
            controller._astronomy_engine = astronomy
            controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
            controller._invalidate_catalogue_visibility_cache()
            controller.setCatalogueVisibleThisMonthFilter(True)

            _ = controller.catalogueObjects
            _ = controller.catalogueObjects
            self.assertEqual(astronomy.catalogue_month_visibility.call_count, 1)

            next_month = 1 if controller.catalogueSelectedMonth == 12 else controller.catalogueSelectedMonth + 1
            controller.setCatalogueMonth(next_month)
            _ = controller.catalogueObjects
            self.assertEqual(astronomy.catalogue_month_visibility.call_count, 2)

            controller._apply_location_result(
                _location_result(ObserverLocation("Milano", "Italia", 45.46, 9.19, "Europe/Rome")),
                persist=False,
            )
            _ = controller.catalogueObjects
            self.assertEqual(astronomy.catalogue_month_visibility.call_count, 3)

    def test_catalogue_useful_observability_depends_on_location_not_month(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.catalogue_month_visibility.return_value = {}
            controller._astronomy_engine = astronomy
            controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
            controller._invalidate_catalogue_visibility_cache()
            controller.searchCatalogue("M4")

            rome_object = controller.catalogueObjects[0]
            self.assertTrue(rome_object["is_geometrically_observable"])
            self.assertTrue(rome_object["is_usefully_observable"])
            self.assertEqual(rome_object["is_usefully_observable_label"], "Sì")
            self.assertEqual(len(controller._catalogue_observability_cache), 1)

            next_month = 1 if controller.catalogueSelectedMonth == 12 else controller.catalogueSelectedMonth + 1
            controller.setCatalogueMonth(next_month)
            same_location_object = controller.catalogueObjects[0]
            self.assertTrue(same_location_object["is_geometrically_observable"])
            self.assertTrue(same_location_object["is_usefully_observable"])
            self.assertEqual(same_location_object["is_usefully_observable_label"], "Sì")
            self.assertEqual(len(controller._catalogue_observability_cache), 1)

            controller._location = ObserverLocation("Tromso", "Norway", 69.65, 18.96, "Europe/Oslo")
            controller._invalidate_catalogue_visibility_cache()
            tromso_object = controller.catalogueObjects[0]
            self.assertFalse(tromso_object["is_geometrically_observable"])
            self.assertFalse(tromso_object["is_usefully_observable"])
            self.assertEqual(tromso_object["is_usefully_observable_label"], "No")

    def test_catalogue_geometric_and_useful_observability_are_separate(self) -> None:
        with _controller() as controller:
            controller._location = ObserverLocation("Bologna", "Italia", 44.4938, 11.3387, "Europe/Rome")
            controller._invalidate_catalogue_visibility_cache()

            bologna_objects = {item["catalogue_id"]: item for item in controller.catalogueObjects}
            for messier_id in ("M6", "M7", "M55", "M69", "M70"):
                self.assertTrue(bologna_objects[messier_id]["is_geometrically_observable"])
                self.assertFalse(bologna_objects[messier_id]["is_usefully_observable"])
                self.assertEqual(bologna_objects[messier_id]["is_usefully_observable_label"], "No")
                self.assertEqual(bologna_objects[messier_id]["observable_label"], "No")

            controller._location = ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa")
            controller._invalidate_catalogue_visibility_cache()
            addis_messier = [item for item in controller.catalogueObjects if item["catalogue"] == "Messier"]
            self.assertEqual(len(addis_messier), 110)
            self.assertTrue(all(item["is_usefully_observable"] for item in addis_messier))

            solar_system = [item for item in controller.catalogueObjects if item["catalogue"] == "Sistema Solare"]
            self.assertEqual(len(solar_system), 9)
            self.assertTrue(all(item["is_usefully_observable_label"] == "—" for item in solar_system))

    def test_catalogue_visible_this_month_changes_with_month(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.catalogue_month_visibility.side_effect = [
                {"messier-M31": False},
                {"messier-M31": True},
            ]
            controller._astronomy_engine = astronomy
            controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
            controller._invalidate_catalogue_visibility_cache()
            controller.setCatalogueVisibleThisMonthFilter(True)
            controller.searchCatalogue("M31")

            self.assertEqual(controller.catalogueObjects, [])

            next_month = 1 if controller.catalogueSelectedMonth == 12 else controller.catalogueSelectedMonth + 1
            controller.setCatalogueMonth(next_month)
            next_month_object = controller.catalogueObjects[0]
            self.assertEqual(next_month_object["catalogue_id"], "M31")
            self.assertTrue(next_month_object["visible_this_month"])
            self.assertEqual(next_month_object["visible_this_month_label"], "Sì")
            self.assertEqual(astronomy.catalogue_month_visibility.call_count, 2)

    def test_catalogue_browsing_does_not_call_recommendation_code(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.recommended_deep_sky.side_effect = AssertionError("catalogue must not refresh recommendations")
            astronomy.catalogue_month_visibility.return_value = {"messier-M31": True}
            score_service = Mock()
            equipment_service = Mock()
            controller._astronomy_engine = astronomy
            controller._score_service = score_service
            controller._equipment_service = equipment_service
            controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
            controller._invalidate_catalogue_visibility_cache()

            self.assertEqual(len(controller.catalogueObjects), 228)
            controller.searchCatalogue("M31")
            self.assertEqual([item["catalogue_id"] for item in controller.catalogueObjects], ["M31"])
            controller.setCatalogueFilter("catalogue", "Messier")
            _ = controller.catalogueObjects
            controller.clearCatalogueFilters()

            astronomy.recommended_deep_sky.assert_not_called()
            astronomy.catalogue_month_visibility.assert_not_called()
            score_service.best_object.assert_not_called()
            equipment_service.suggest_for_profile.assert_not_called()

    def test_solar_system_catalogue_rows_do_not_show_messier_only_data(self) -> None:
        with _controller() as controller:
            controller.setCatalogueFilter("catalogue", "Sistema Solare")
            solar_objects = controller.catalogueObjects
            sun = next(item for item in solar_objects if item["object_id"] == "sun")
            mars = next(item for item in solar_objects if item["object_id"] == "mars")

            self.assertEqual(sun["catalogue_id"], "S1")
            self.assertEqual(sun["object_id"], "sun")
            self.assertEqual(sun["name"], "Sole")
            self.assertEqual(sun["type"], "Stella")
            self.assertEqual(sun["constellation"], "")
            self.assertEqual(sun["observable_label"], "—")
            self.assertEqual(sun["recommended_observation_type"], "")
            self.assertIsNone(sun["magnitude"])
            self.assertEqual(sun["apparent_size"], "")
            self.assertIsNone(sun["max_angular_size_deg"])
            self.assertEqual(sun["max_angular_size_label"], "")
            self.assertEqual(mars["catalogue_id"], "S5")
            self.assertEqual(mars["object_id"], "mars")
            self.assertEqual(mars["recommended_observation_type"], "HighMagnification")

    def test_select_solar_system_catalogue_object_opens_catalogue_detail(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.catalogue_month_visibility.return_value = {"mars": True}
            controller._astronomy_engine = astronomy
            controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
            controller._solar_system_objects = [
                CelestialObject(
                    id="mars",
                    name="Marte",
                    object_type="Pianeta",
                    image="resources/images/solar_system/mars.jpg",
                    magnitude="-1.2",
                    distance="0.80 UA",
                    max_altitude="42 gradi",
                    direction="Sud-est",
                    best_time="23:10",
                    observing_window="21:00 - 03:00",
                    notes="Dettaglio Skyfield esistente.",
                    recommended_setup="10 mm",
                    visibility_class="Occhio nudo",
                    azimuth="140 gradi",
                    time_above_horizon="6 h",
                    visible=True,
                    rise_time="20:10",
                    set_time="04:20",
                    culmination_time="00:15",
                    current_altitude="31.2 gradi",
                    current_azimuth="134.0 gradi",
                    score=80,
                )
            ]
            controller._invalidate_catalogue_visibility_cache()
            controller.setCatalogueVisibleThisMonthFilter(True)

            controller.selectCatalogueObject("mars")
            selected = controller.selectedObject

            self.assertEqual(selected["id"], "mars")
            self.assertEqual(selected["name"], "Marte")
            self.assertTrue(selected["catalogueObject"])
            self.assertEqual(selected["catalogue"], "Sistema Solare")
            self.assertEqual(selected["catalogueId"], "S5")
            self.assertEqual(selected["type"], "Pianeta")
            self.assertEqual(selected["constellation"], "—")
            self.assertEqual(selected["observingStatus"], "Catalogo Sistema Solare")
            self.assertEqual(selected["currentAltitude"], "31.2 gradi")
            self.assertEqual(selected["currentAzimuth"], "134.0 gradi")
            self.assertEqual(selected["riseTime"], "20:10")
            self.assertEqual(selected["culminationTime"], "00:15")
            self.assertEqual(selected["setTime"], "04:20")
            self.assertTrue(selected["catalogueVisibleThisMonth"])
            self.assertEqual(selected["catalogueVisibleThisMonthLabel"], "Sì")
            self.assertEqual(selected["catalogueUsefullyObservableLabel"], "—")
            self.assertEqual(selected["catalogueObservableLabel"], "—")
            self.assertNotEqual(selected["catalogue"], "Messier")
            self.assertNotIn("Messier", selected["observingStatus"])

    def test_catalogue_visibility_never_calls_recommendation_planner_or_weather_services(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.catalogue_month_visibility.return_value = {"messier-M31": True}
            astronomy.recommended_deep_sky.side_effect = AssertionError("catalogue visibility must not recommend")
            planner = Mock()
            weather = Mock()
            score_service = Mock()
            controller._astronomy_engine = astronomy
            controller._night_planner_service = planner
            controller._weather_service = weather
            controller._score_service = score_service
            controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
            controller._invalidate_catalogue_visibility_cache()

            controller.setCatalogueVisibleThisMonthFilter(True)
            _ = controller.catalogueObjects
            controller.selectCatalogueObject("messier-M31")
            selected = controller.selectedObject

            self.assertTrue(selected["catalogueVisibleThisMonth"])
            astronomy.catalogue_month_visibility.assert_called_once()
            astronomy.recommended_deep_sky.assert_not_called()
            planner.plan.assert_not_called()
            weather.hourly_forecast.assert_not_called()
            score_service.best_object.assert_not_called()

    def test_select_catalogue_object_works_outside_home_recommendations(self) -> None:
        with _controller() as controller:
            astronomy = Mock()
            astronomy.catalogue_month_visibility.return_value = {"messier-M110": True}
            controller._astronomy_engine = astronomy
            controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
            controller._invalidate_catalogue_visibility_cache()
            controller.setCatalogueVisibleThisMonthFilter(True)
            controller._solar_system_objects = []
            controller._deep_sky = []
            controller._selected_object = None
            controller._selected_object_source = ""

            controller.selectCatalogueObject("messier-M110")
            selected = controller.selectedObject

            self.assertEqual(selected["id"], "messier-M110")
            self.assertEqual(selected["catalogue"], "Messier")
            self.assertEqual(selected["catalogueId"], "M110")
            self.assertTrue(selected["catalogueObject"])
            self.assertEqual(selected["distance"], "n/d")
            self.assertTrue(selected["constellation"])
            self.assertTrue(selected["rightAscension"])
            self.assertTrue(selected["declination"])
            self.assertTrue(selected["maxAngularSizeLabel"])
            self.assertEqual(selected["catalogueUsefullyObservableLabel"], "Sì")
            self.assertEqual(selected["catalogueObservableLabel"], "Sì")
            self.assertTrue(selected["catalogueVisibleThisMonth"])
            self.assertEqual(selected["catalogueVisibleThisMonthLabel"], "Sì")
            self.assertEqual(selected["catalogueVisibilityLabel"], "Sì")
            self.assertIn("M110", selected["name"])
            self.assertEqual(selected["observingStatus"], "Catalogo Messier")

    def test_select_caldwell_object_resolves_identifier_and_localized_metadata(self) -> None:
        with _controller() as controller:
            controller.selectCatalogueObject("C23")
            selected = controller.selectedObject

            self.assertEqual(selected["id"], "caldwell-C23")
            self.assertEqual(selected["name"], "C23 NGC 891")
            self.assertEqual(selected["catalogue"], "Caldwell")
            self.assertEqual(selected["catalogueId"], "C23")
            self.assertEqual(selected["catalogueTypeLabel"], "Galassia spirale")
            self.assertEqual(selected["constellation"], "Andromeda")
            self.assertEqual(selected["rightAscension"], "02h 22.6m")
            self.assertEqual(selected["declination"], "+42° 21′")
            self.assertIn("NGC 891", selected["descriptionText"])
            self.assertIn("Via Lattea", selected["curiosityText"])
            self.assertEqual(selected["curiositySourceLabel"], "NASA Hubble")
            self.assertTrue(selected["curiositySourceUrl"].startswith("https://"))
            self.assertTrue(selected["curiosityVerified"])
            self.assertGreater(len(selected["catalogueIntroText"]), 40)
            self.assertEqual(selected["bestSeen"], "Inverno")
            self.assertEqual(selected["image"], "resources/images/catalogue/caldwell-C23.jpg")
            self.assertIn("2MASS", selected["imageAttribution"])
            self.assertIn("hips2fits", selected["imageSourceUrl"])
            self.assertIn("ODbL-1.0", selected["imageLicense"])
            self.assertTrue(selected["imageVerified"])
            self.assertEqual(selected["observingStatus"], "Catalogo Caldwell")

            controller.selectCatalogueObject("C33")
            self.assertEqual(controller.selectedObject["type"], "Supernova remnant")
            self.assertEqual(
                controller.selectedObject["image"],
                "resources/images/catalogue/caldwell-C33.jpg",
            )
            self.assertIn("Pan-STARRS1", controller.selectedObject["imageAttribution"])

    def test_weather_not_called_without_valid_location(self) -> None:
        with _controller() as controller:
            fake_weather = Mock()
            fake_weather.hourly_forecast.return_value = []
            controller._weather_service = fake_weather
            controller._location = None

            with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="WARNING"):
                controller._refresh_weather_and_conditions()

            fake_weather.hourly_forecast.assert_not_called()
            self.assertEqual(controller.weatherStatus, "Configura una posizione per visualizzare il meteo.")

    def test_weather_refreshes_after_valid_location(self) -> None:
        with _controller() as controller:
            fake_weather = Mock()
            fake_weather.hourly_forecast.return_value = [
                WeatherHour("2026-06-21T22:00", "22:00", 10, 0, 5, 55, 18.0, 20_000)
            ]
            fake_weather.last_error = ""
            controller._weather_service = fake_weather
            controller._start_background_task = lambda target: target()

            controller.setManualLocation("41.9028", "12.4964", "Roma")

            fake_weather.hourly_forecast.assert_called()

    def test_light_pollution_provider_fallback(self) -> None:
        with _temp_database() as database_path:
            service = LightPollutionService(
                SkyQualityRepository(database_path),
                dataset_path=Path("missing-light-pollution.csv"),
            )
            quality = service.sky_quality(ObserverLocation("Unknown", "", 1.0, 1.0, "UTC"))

            self.assertEqual(quality.source, "Fonte: stima offline NightScope (nessun dataset locale)")
            self.assertEqual(quality.confidence, "low")

    def test_light_pollution_world_atlas_csv_provider(self) -> None:
        with _temp_database() as database_path:
            data_dir = database_path.parent
            atlas_path = data_dir / "light_pollution_world_atlas.csv"
            atlas_path.write_text(
                "\n".join(
                    [
                        "latitude,longitude,radius_km,sky_brightness,source,confidence",
                        "44.4938,11.3387,10,21.05,World Atlas sample,high",
                    ]
                ),
                encoding="utf-8",
            )

            service = LightPollutionService(
                SkyQualityRepository(database_path),
                dataset_path=data_dir / "light_pollution_seed.csv",
            )
            quality = service.sky_quality(ObserverLocation("Bologna", "Italia", 44.4938, 11.3387, "Europe/Rome"))

            self.assertEqual(quality.source, "Fonte: World Atlas sample")
            self.assertEqual(quality.confidence, "high")
            self.assertEqual(quality.bortle_class, 3)

    def test_light_pollution_legacy_cache_is_refreshed(self) -> None:
        with _temp_database() as database_path:
            repository = SkyQualityRepository(database_path)
            repository.set(
                "9.030:38.740:addis ababa",
                7,
                4.6,
                18.8,
                "Fonte: Curated urban baseline pending World Atlas import",
                "medium",
                "2026-01-01T00:00:00+00:00",
            )
            service = LightPollutionService(
                repository,
                dataset_path=Path(__file__).resolve().parents[1] / "data" / "light_pollution_seed.csv",
            )

            quality = service.sky_quality(ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa"))

            self.assertEqual(quality.source, "Fonte: NightScope local urban baseline")

    def test_viirs_tile_mapping_for_bologna(self) -> None:
        tile = NasaViirsBlackMarbleProvider._tile_for_location(
            ObserverLocation("Bologna", "Italy", 44.4938, 11.3387, "Europe/Rome")
        )

        self.assertEqual(tile.identifier, "h19v04")
        self.assertEqual(tile.row, 1321)
        self.assertEqual(tile.col, 321)

    def test_viirs_provider_reads_opendap_nc4_subset(self) -> None:
        session = FakeViirsSession(_viirs_nc4_payload(radiance=63.448333740234375, observations=10, quality=0))
        provider = NasaViirsBlackMarbleProvider(FakeEarthdataCredentials(), months_to_search=1)

        with patch.object(NasaViirsBlackMarbleProvider, "_session", return_value=session):
            quality = provider.lookup(ObserverLocation("Bologna", "Italy", 44.4938, 11.3387, "Europe/Rome"))

        self.assertIsNotNone(quality)
        self.assertEqual(quality.bortle_class, 7)
        self.assertEqual(quality.confidence, "high")
        self.assertEqual(quality.viirs_radiance, 63.45)
        self.assertEqual(quality.viirs_observation_count, 10)
        self.assertIn("NASA Black Marble VNP46A3", quality.source)
        self.assertIn("[1320:1:1322][320:1:322]", session.last_constraint)

        qml = quality.to_qml()
        self.assertTrue(qml["hasViirsRadiance"])
        self.assertEqual(qml["viirsRadiance"], 63.45)
        self.assertEqual(qml["viirsObservationCount"], 10)
        self.assertEqual(qml["confidence"], "high")
        self.assertEqual(qml["confidenceLabel"], "alta")

    def test_viirs_session_uses_temporary_netrc_for_earthdata_redirects(self) -> None:
        with patch.dict(os.environ, {"NETRC": "existing-netrc"}, clear=False):
            with NasaViirsBlackMarbleProvider._session("astro-user", "secret-password") as session:
                netrc_path = Path(os.environ["NETRC"])
                self.assertTrue(netrc_path.exists())
                self.assertIn("machine urs.earthdata.nasa.gov", netrc_path.read_text(encoding="ascii"))
                self.assertTrue(session.trust_env)

            self.assertEqual(os.environ["NETRC"], "existing-netrc")

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


class FakeEarthdataCredentials:
    def state(self) -> EarthdataCredentialState:
        return EarthdataCredentialState(
            username="astro-user",
            configured=True,
            secure_store_available=True,
            connection_verified=True,
            message="Connessione Earthdata LAADS verificata.",
        )

    def password(self) -> str:
        return "secret-password"


class FakeViirsResponse:
    def __init__(self, status_code: int = 200, text: str = "", content: bytes = b"") -> None:
        self.status_code = status_code
        self.text = text
        self.content = content


class FakeViirsSession:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.last_constraint = ""

    def get(self, url: str, **kwargs) -> FakeViirsResponse:
        if url.endswith(".dap.nc4"):
            self.last_constraint = (kwargs.get("params") or {}).get("dap4.ce", "")
            return FakeViirsResponse(content=self._payload)
        match = re.search(r"/VNP46A3/(\d{4})/(\d{3})/$", url)
        if not match:
            return FakeViirsResponse(status_code=404)
        year, doy = match.groups()
        granule = f"VNP46A3.A{year}{doy}.h19v04.002.9999999999999.h5"
        return FakeViirsResponse(text=f'<a href="{granule}">{granule}</a>')


def _viirs_nc4_payload(radiance: float, observations: int, quality: int) -> bytes:
    payload = io.BytesIO()
    with h5py.File(payload, "w") as data:
        group = data.create_group("HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data_Fields")
        group.create_dataset(
            "AllAngle_Composite_Snow_Free",
            data=np.array([[radiance]], dtype=np.float32),
        )
        group.create_dataset(
            "AllAngle_Composite_Snow_Free_Num",
            data=np.array([[observations]], dtype=np.uint16),
        )
        group.create_dataset(
            "AllAngle_Composite_Snow_Free_Quality",
            data=np.array([[quality]], dtype=np.uint8),
        )
    return payload.getvalue()


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


def _test_night_window() -> ObservingNightWindow:
    zone = ZoneInfo("Africa/Addis_Ababa")
    now = datetime.now(zone)
    start_date = now.date() - timedelta(days=1) if now.hour < 8 else now.date()
    start = datetime.combine(start_date, datetime.min.time(), tzinfo=zone).replace(hour=18)
    return ObservingNightWindow.bounded(start, start + timedelta(hours=13))


def _planet(
    object_id: str,
    name: str,
    current_altitude: str = "42.0 gradi",
    best_time: str = "22:00",
    observing_window: str = "21:00 - 23:00",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type="Pianeta",
        image=f"resources/images/solar_system/{object_id}.jpg",
        magnitude="1.0",
        distance="n/d",
        max_altitude="45 gradi",
        direction="Sud",
        best_time=best_time,
        observing_window=observing_window,
        notes="",
        recommended_setup="",
        visibility_class="Occhio nudo",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        current_altitude=current_altitude,
        current_azimuth="180.0 gradi",
        score=80,
    )


def _metadata_object(
    object_id: str,
    name: str,
    object_type: str,
    magnitude: str,
    apparent_size: str,
    max_angular_size_deg: float,
    recommended_observation_type: str,
) -> CelestialObject:
    base = _object(object_id, name, object_type, magnitude)
    return base.__class__(
        **{
            **base.__dict__,
            "apparent_size": apparent_size,
            "max_angular_size_deg": max_angular_size_deg,
            "recommended_observation_type": recommended_observation_type,
        }
    )


def _set_profile_equipment(
    controller: AppController,
    telescopes: list[Telescope] | None = None,
    eyepieces: list[Eyepiece] | None = None,
    barlows: list[Barlow] | None = None,
    binoculars: list[Binocular] | None = None,
) -> None:
    telescopes = telescopes or []
    eyepieces = eyepieces or []
    barlows = barlows or []
    binoculars = binoculars or []
    controller._telescopes.extend(telescope for telescope in telescopes if not controller._find_telescope(telescope.id))
    controller._eyepieces.extend(eyepiece for eyepiece in eyepieces if not controller._find_eyepiece(eyepiece.id))
    controller._barlows.extend(barlow for barlow in barlows if not controller._find_barlow(barlow.id))
    controller._binoculars.extend(binocular for binocular in binoculars if not controller._find_binocular(binocular.id))
    state = controller._active_profile_state()
    state["telescope_ids"] = [telescope.id for telescope in telescopes]
    state["eyepiece_ids"] = [eyepiece.id for eyepiece in eyepieces]
    state["barlow_ids"] = [barlow.id for barlow in barlows]
    state["binocular_ids"] = [binocular.id for binocular in binoculars]


def _calendar_home_detail_setups(controller: AppController, target: CelestialObject) -> tuple[str, str, str]:
    calendar_setup = controller._calendar_profile_setup(target, "Telescopio medio")
    home_object = controller._apply_equipment([target])[0]
    object_detail = controller._object_to_qml(home_object)
    return calendar_setup, home_object.recommended_setup, object_detail["recommended_setup"]


def _location_result(location: ObserverLocation) -> LocationDetectionResult:
    return LocationDetectionResult(
        location=location,
        provider="manual",
        source="test",
        accuracy="test",
        message="Test location",
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
        temp_path = Path(self._temp_dir.name)
        write_small_geonames_fixture(temp_path)
        self.path = temp_path / "nightscope.db"
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
        weather_start = datetime.now(ZoneInfo("Africa/Addis_Ababa")).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=None,
        )
        response.json.return_value = {
            "hourly": {
                "time": [
                    (weather_start + timedelta(hours=index)).isoformat(timespec="minutes")
                    for index in range(48)
                ],
                "cloud_cover": [20] * 48,
                "precipitation_probability": [0] * 48,
                "temperature_2m": [18.0] * 48,
                "relative_humidity_2m": [55] * 48,
                "wind_speed_10m": [6] * 48,
                "wind_gusts_10m": [10] * 48,
                "visibility": [20_000] * 48,
                "dew_point_2m": [10.0] * 48,
                "cloud_cover_low": [5] * 48,
                "cloud_cover_mid": [10] * 48,
                "cloud_cover_high": [15] * 48,
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
