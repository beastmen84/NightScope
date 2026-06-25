from __future__ import annotations

import io
import os
import re
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

import h5py
import numpy as np

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.city_repository import CityRepository
from astro_viewer.app.database.equipment_catalog_repository import EquipmentCatalogRepository
from astro_viewer.app.database.geonames_importer import import_geonames_cities
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import AstronomicalEvent, CelestialObject
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.earthdata_credentials import EarthdataCredentialState
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.light_pollution_service import LightPollutionService, NasaViirsBlackMarbleProvider
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
            controller._weather_hours = [
                WeatherHour("2026-06-21T22:00", "22:00", 8, 0, 4, 45, 14.0, 20_000)
            ]
            controller._weather_summary = controller._score_service.weather_score(
                controller._weather_hours,
                controller._moon,
            )
            controller._sky_quality = SkyQuality(3, 6.2, 21.4, "Fonte test", "Cielo rurale", "high")
            controller._seeing_service = Mock()
            controller._seeing_service.estimate.return_value = SeeingTransparency(
                "Excellent",
                "Excellent",
                95,
                95,
                "Test seeing stabile.",
            )
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
            controller._seeing_service.estimate.return_value = SeeingTransparency(
                "Excellent",
                "Excellent",
                95,
                95,
                "Test seeing stabile.",
            )
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

    def test_calendar_conjunction_keeps_low_priority_but_uses_profile(self) -> None:
        with _controller() as controller:
            telescope = controller.telescopeCatalogModels[0]
            eyepiece = controller.eyepieceCatalog[0]
            controller.assignEquipmentToActiveProfile("telescope", telescope["catalog_id"])
            controller.assignEquipmentToActiveProfile("eyepiece", eyepiece["catalog_id"])
            event = AstronomicalEvent(
                id="jupiter-0-test",
                title="Giove in congiunzione",
                event_type="Congiunzione",
                date_label="21/01/2027",
                best_time="07:00",
                usefulness=38,
                setup="Non prioritario",
                note="Test",
            )

            setup = controller._event_to_qml(event)["setup"]

            self.assertTrue(setup.startswith("Bassa priorità: "))
            self.assertIn(controller.currentSetup["name"], setup)

    def test_calendar_profile_setup_matches_home_for_telescope_only_profile(self) -> None:
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

            self.assertEqual(calendar_setup, home_setup)
            self.assertEqual(calendar_setup, object_detail_setup)
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

    def test_calendar_profile_setup_matches_home_for_mixed_profile_targets(self) -> None:
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

                    self.assertEqual(calendar_setup, home_setup)
                    self.assertEqual(calendar_setup, object_detail_setup)
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

    def test_sidebar_navigation_groups_configuration_and_catalogs(self) -> None:
        ui_dir = Path(__file__).resolve().parents[1] / "app" / "ui"
        main_qml = (ui_dir / "main.qml").read_text(encoding="utf-8")
        binoculars_qml = (ui_dir / "pages" / "EquipmentBinocularsPage.qml").read_text(encoding="utf-8")
        profiles_qml = (ui_dir / "pages" / "EquipmentProfilesPage.qml").read_text(encoding="utf-8")
        home_qml = (ui_dir / "pages" / "HomePage.qml").read_text(encoding="utf-8")
        object_detail_qml = (ui_dir / "pages" / "ObjectDetailPage.qml").read_text(encoding="utf-8")

        expected_labels = [
            'text: "Home"',
            'text: "Calendario"',
            'text: "Meteo"',
            'text: "Configurazione"',
            'text: "Località"',
            'text: "Profili"',
            'text: "Cataloghi"',
            'text: "Telescopi"',
            'text: "Oculari e Barlow"',
            'text: "Binocoli"',
        ]
        positions = [main_qml.index(label) for label in expected_labels]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('text: "Strumenti"', main_qml)
        self.assertIn("equipmentProfiles", main_qml)
        self.assertIn("equipmentTelescopes", main_qml)
        self.assertIn("equipmentOptics", main_qml)
        self.assertIn("equipmentBinoculars", main_qml)
        self.assertIn("EquipmentProfilesPage", main_qml)
        self.assertIn("EquipmentTelescopesPage", main_qml)
        self.assertIn("EquipmentOpticsPage", main_qml)
        self.assertIn("EquipmentBinocularsPage", main_qml)
        self.assertIn('text: "Catalogo binocoli"', binoculars_qml)
        self.assertIn('placeholderText: "Cerca binocolo..."', binoculars_qml)
        self.assertIn('placeholderText: "Diametro obiettivo (mm)"', binoculars_qml)
        self.assertIn("controller.binocularCatalog", binoculars_qml)
        self.assertIn("controller.addBinocularModel", binoculars_qml)
        self.assertIn("controller.updateBinocularModel", binoculars_qml)
        self.assertIn("controller.deleteBinocularModel", binoculars_qml)
        self.assertIn('text: "Stabilizzato"', binoculars_qml)
        self.assertIn('title: "Binocoli"', profiles_qml)
        self.assertIn('emptyText: "Nessun binocolo assegnato."', profiles_qml)
        self.assertIn('model: ["Tutti", "Telescopi", "Oculari", "Barlow", "Binocoli"]', profiles_qml)
        self.assertIn('equipmentType === "Binocular"', home_qml)
        self.assertIn('equipmentType === "Binocular"', object_detail_qml)
        self.assertIn("setupDetailText()", object_detail_qml)
        self.assertIn("Pupilla d'uscita", object_detail_qml)

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
