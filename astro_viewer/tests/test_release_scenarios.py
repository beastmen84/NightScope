from __future__ import annotations

import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from PySide6.QtCore import QCoreApplication

import requests

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.location_service import (
    LocationDetectionResult,
    LocationUnavailableError,
    WINDOWS_LOCATION_UNAVAILABLE_MESSAGE,
)
from astro_viewer.app.services.location_preferences import LocationPreferenceStore
from astro_viewer.app.services.weather_service import WEATHER_UNAVAILABLE_MESSAGE
from astro_viewer.app.viewmodels.app_controller import WEATHER_RETRY_DELAY_MS, AppController


class ReleaseScenarioTests(unittest.TestCase):
    def test_addis_ababa_with_available_weather_keeps_app_usable(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            controller.setManualLocation("9.03", "38.74", "Addis Ababa")

            self.assertEqual(controller.location["city"], "Addis Ababa")
            self.assertGreater(len(controller.solarSystemObjects), 0)
            self.assertGreater(len(controller.weatherHourly), 0)
            self.assertNotIn("NightScope could not update all data", controller.serviceStatus)
            self.assertEqual(controller.homeObservingOverview["planetary"]["state"], "available")
            self.assertEqual(controller.homeObservingOverview["deepSky"]["state"], "available")

    def test_home_overview_separates_session_weather_and_category_diagnostics(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            controller.setManualLocation("9.03", "38.74", "Addis Ababa")

            overview = controller.homeObservingOverview
            night_overview = controller.homeNightPlanOverview

            self.assertEqual(overview["schemaVersion"], "home_observing_overview_v1")
            self.assertIn(overview["session"]["state"], {"recommended", "monitor", "discouraged"})
            self.assertEqual(overview["weather"]["scoreValue"], controller.weatherSummary["scoreValue"])
            self.assertEqual(overview["planetary"]["source"], "nsom_canonical_environment")
            self.assertEqual(overview["deepSky"]["source"], "nsom_canonical_environment")
            self.assertEqual(night_overview["schemaVersion"], "home_night_plan_overview_v1")
            self.assertEqual(night_overview["plan"]["state"], overview["session"]["state"])
            self.assertTrue(night_overview["profile"]["summary"].startswith("Profilo attivo:"))
            self.assertLessEqual(len(night_overview["plan"]["items"]), 4)
            self.assertTrue(
                all("score" not in item for item in night_overview["alternatives"]["items"])
            )

    def test_offline_weather_keeps_app_usable(self) -> None:
        with self.assertLogs("astro_viewer.app.services.weather_service", level="WARNING"):
            with self._controller_with_weather(side_effect=requests.Timeout, saved_location=True) as controller:
                self.assertEqual(controller.weatherStatus, "Dati meteo non disponibili al momento.")
                self.assertGreater(len(controller.solarSystemObjects), 0)
                self.assertIn("Meteo non disponibile", controller.weatherSummary["alert"])
                self.assertFalse(controller.isObservingSessionBlocked)
                self.assertEqual(controller.blockingReason, "")
                self.assertEqual(controller.homeObservingOverview["session"]["state"], "unavailable")
                self.assertIn("meteo non disponibili", controller.skyCompass["cautionText"].lower())

    def test_blocking_weather_state_is_exposed_by_controller(self) -> None:
        with self._controller_with_weather(_rainy_weather_response(), saved_location=True) as controller:
            self.assertTrue(controller.isObservingSessionBlocked)
            self.assertEqual(controller.blockingReason, "rischio precipitazioni")
            self.assertEqual(controller.blockingDetail, "Rischio precipitazioni elevato.")
            self.assertEqual(controller.observingSessionState, "discouraged")
            self.assertEqual(controller.observingSessionTitle, "Sessione sconsigliata")
            self.assertEqual(controller.observingSessionIcon, "🚫")
            self.assertEqual(
                controller.observingSessionDetail,
                "Le condizioni previste rimangono sfavorevoli per tutta la notte.",
            )
            self.assertFalse(controller.showObservingSessionOpportunity)
            self.assertEqual(controller.suggestedObservingWindow, "")
            self.assertEqual(controller.nightPlan, [])
            self.assertEqual(controller.homeNightPlanOverview["plan"]["title"], "Sessione sconsigliata")
            self.assertEqual(controller.homeNightPlanOverview["plan"]["items"], [])

    def test_blocking_weather_with_later_window_is_monitor_state(self) -> None:
        with self._controller_with_weather(_monitoring_weather_response(), saved_location=True) as controller:
            self.assertTrue(controller.isObservingSessionBlocked)
            self.assertEqual(controller.observingSessionState, "monitor")
            self.assertEqual(controller.observingSessionTitle, "Sessione da monitorare")
            self.assertEqual(controller.observingSessionIcon, "⚠")
            self.assertEqual(controller.observingSessionDetail, "Le condizioni attuali non sono ancora favorevoli.")
            self.assertIn("finestra osservativa promettente", controller.observingSessionDescription)
            self.assertTrue(controller.showObservingSessionOpportunity)
            self.assertEqual(controller.suggestedObservingWindow, "03:00–06:00")
            self.assertEqual(controller.nightPlan, [])
            self.assertEqual(controller.homeNightPlanOverview["plan"]["title"], "Finestra da monitorare")
            self.assertEqual(controller.homeNightPlanOverview["plan"]["items"], [])

    def test_app_starts_with_saved_location_and_refreshes_weather(self) -> None:
        with self._controller_with_weather(_valid_weather_response(), saved_location=True) as controller:
            self.assertEqual(controller.location["city"], "Addis Ababa")
            self.assertEqual(controller.location["timezone"], "Africa/Addis_Ababa")
            self.assertGreater(len(controller.weatherHourly), 0)
            self.assertEqual(controller.activeLocationLabel, "Addis Ababa — Africa/Addis_Ababa")

    def test_app_starts_without_location_and_no_consent(self) -> None:
        context = self._controller_with_weather(_valid_weather_response())
        with context as controller:
            self.assertFalse(controller.hasValidLocation)
            self.assertEqual(controller.location["city"], "")
            self.assertEqual(controller.weatherStatus, "Configura una località per visualizzare il meteo.")
            self.assertEqual(controller.weatherHourly, [])
            self.assertEqual(controller.activeLocationLabel, "Nessuna località configurata")
            self.assertEqual(controller.homeObservingOverview["session"]["state"], "unavailable")
            self.assertEqual(controller.homeObservingOverview["weather"]["scoreLabel"], "n/d")
            self.assertEqual(controller.homeObservingOverview["moon"]["impact"], "unavailable")
            context.weather_requests.assert_not_called()

    def test_app_starts_with_approximate_online_consent(self) -> None:
        ip_response = Mock()
        ip_response.raise_for_status.return_value = None
        ip_response.json.return_value = {
            "city": "Addis Ababa",
            "region": "Addis Ababa",
            "country_name": "Ethiopia",
            "latitude": 9.03,
            "longitude": 38.74,
            "timezone": "Africa/Addis_Ababa",
            "accuracy_radius": 25,
        }
        weather_response = _valid_weather_response()

        def response_for_url(url, *args, **kwargs):
            if "ipapi" in url or "ipwho" in url:
                return ip_response
            return weather_response

        with self._controller_with_weather(
            side_effect=response_for_url,
            preferences={
                "auto_detect_location_on_startup": True,
                "allow_approximate_online_location": True,
            },
            patch_location_requests=True,
        ) as controller:
            self.assertTrue(_wait_for_startup_location(controller))
            self.assertEqual(controller.location["city"], "Addis Ababa")
            self.assertEqual(controller.location["timezone"], "Africa/Addis_Ababa")
            self.assertEqual(controller.activeLocationSource, "Online approssimata")
            self.assertGreater(len(controller.weatherHourly), 0)

    def test_startup_auto_detection_does_not_refresh_weather_until_location_is_ready(self) -> None:
        ip_response = Mock()
        ip_response.raise_for_status.return_value = None
        ip_response.json.return_value = {
            "city": "Addis Ababa",
            "region": "Addis Ababa",
            "country_name": "Ethiopia",
            "latitude": 9.03,
            "longitude": 38.74,
            "timezone": "Africa/Addis_Ababa",
            "accuracy_radius": 25,
        }
        weather_response = _valid_weather_response()

        def response_for_url(url, *args, **kwargs):
            if "ipapi" in url or "ipwho" in url:
                time.sleep(0.2)
                return ip_response
            return weather_response

        context = self._controller_with_weather(
            side_effect=response_for_url,
            preferences={
                "auto_detect_location_on_startup": True,
                "allow_approximate_online_location": True,
            },
            patch_location_requests=True,
        )
        with context as controller:
            self.assertTrue(controller.startupLocationDetectionRunning)
            self.assertFalse(controller.hasValidLocation)
            self.assertEqual(controller.weatherHourly, [])
            self.assertEqual(controller.activeLocationLabel, "Posizione in aggiornamento")
            self.assertEqual(controller.activeLocationSource, "Rilevamento automatico")
            self.assertEqual(controller.weatherStatus, "Meteo in attesa della posizione.")
            overview = controller.homeObservingOverview
            self.assertEqual(overview["session"]["state"], "pending")
            self.assertEqual(overview["weather"]["badge"], "In attesa")
            self.assertEqual(overview["planetary"]["state"], "pending")
            self.assertEqual(overview["deepSky"]["state"], "pending")
            context.weather_requests.assert_not_called()

            self.assertTrue(_wait_for_startup_location(controller))
            self.assertEqual(controller.location["city"], "Addis Ababa")
            self.assertGreater(len(controller.weatherHourly), 0)

    def test_startup_auto_detection_overrides_saved_location(self) -> None:
        ip_response = Mock()
        ip_response.raise_for_status.return_value = None
        ip_response.json.return_value = {
            "city": "Bologna",
            "region": "Emilia-Romagna",
            "country_name": "Italy",
            "latitude": 44.4938,
            "longitude": 11.3387,
            "timezone": "Europe/Rome",
            "accuracy_radius": 25,
        }
        weather_response = _valid_weather_response()

        def response_for_url(url, *args, **kwargs):
            if "ipapi" in url or "ipwho" in url:
                return ip_response
            return weather_response

        with self._controller_with_weather(
            side_effect=response_for_url,
            saved_location=True,
            preferences={
                "auto_detect_location_on_startup": True,
                "allow_approximate_online_location": True,
                "use_windows_location_on_startup": False,
            },
            patch_location_requests=True,
        ) as controller:
            self.assertTrue(_wait_for_startup_location(controller))
            self.assertEqual(controller.location["city"], "Bologna")
            self.assertEqual(controller.location["timezone"], "Europe/Rome")
            self.assertEqual(controller.activeLocationSource, "Online approssimata")

    def test_windows_location_unavailable_keeps_current_location(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            previous_location = controller.location["city"]
            with patch.object(
                controller._location_service,
                "detect_windows_location",
                side_effect=LocationUnavailableError(WINDOWS_LOCATION_UNAVAILABLE_MESSAGE),
            ):
                with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="WARNING"):
                    controller.useWindowsLocation()

            self.assertEqual(controller.location["city"], previous_location)
            self.assertEqual(controller.locationMessage, "La posizione Windows non è disponibile. Provare la posizione approssimata online?")
            self.assertTrue(controller.canUseApproximateOnlineLocation)

    def test_weather_not_called_without_valid_location(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            fake_weather_service = Mock()
            fake_weather_service.hourly_forecast.return_value = []
            fake_weather_service.last_error = ""
            controller._weather_service = fake_weather_service
            controller._location = None

            with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="WARNING"):
                controller._refresh_weather_and_conditions()

            fake_weather_service.hourly_forecast.assert_not_called()

    def test_weather_refreshes_after_valid_location(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            fake_weather_service = Mock()
            fake_weather_service.hourly_forecast.return_value = [
                WeatherHour("2026-06-21T22:00", "22:00", 20, 0, 6, 55, 18.0, 18_000)
            ]
            fake_weather_service.last_error = ""
            controller._weather_service = fake_weather_service

            controller.setManualLocation("41.9028", "12.4964", "Roma")

            fake_weather_service.hourly_forecast.assert_called()

    def test_manual_weather_refresh_forces_network_and_keeps_existing_data_on_failure(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            fake_weather_service = _ForceRefreshFailingWeatherService()
            controller._weather_service = fake_weather_service

            controller.setManualLocation("41.9028", "12.4964", "Roma")
            self.assertEqual(len(controller.weatherHourly), 1)
            fake_weather_service.force_refresh_values.clear()

            controller._schedule_viirs_sky_quality_refresh = Mock()
            controller._schedule_nasa_aod_refresh = Mock()
            controller.refreshWeatherNow()

            self.assertTrue(_wait_for_weather_refresh(controller))
            self.assertEqual(fake_weather_service.force_refresh_values, [True])
            self.assertEqual(len(controller.weatherHourly), 1)
            self.assertEqual(
                controller.weatherStatus,
                "Tentativo di aggiornamento meteo fallito; uso ultimi dati disponibili.",
            )
            controller._schedule_viirs_sky_quality_refresh.assert_called_once_with()
            controller._schedule_nasa_aod_refresh.assert_called_once_with()

    def test_automatic_weather_refresh_uses_cache_friendly_mode_and_clears_failure(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            fake_weather_service = _ForceRefreshFailingWeatherService()
            controller._weather_service = fake_weather_service

            controller.setManualLocation("41.9028", "12.4964", "Roma")
            fake_weather_service.force_refresh_values.clear()
            controller._weather_status = WEATHER_UNAVAILABLE_MESSAGE
            controller._schedule_viirs_sky_quality_refresh = Mock()

            controller._refresh_weather_from_timer()

            self.assertTrue(_wait_for_weather_refresh(controller))
            self.assertEqual(fake_weather_service.force_refresh_values, [False])
            self.assertEqual(len(controller.weatherHourly), 1)
            self.assertEqual(controller.weatherStatus, "")
            self.assertTrue(controller._weather_refresh_timer.isActive())
            controller._schedule_viirs_sky_quality_refresh.assert_not_called()

    def test_manual_weather_refresh_clears_unavailable_status_after_initial_failure(self) -> None:
        app = QCoreApplication.instance() or QCoreApplication([])
        with self._controller_with_weather(
            side_effect=[requests.Timeout(), requests.Timeout(), _valid_weather_response()]
        ) as controller:
            controller.setManualLocation("41.9028", "12.4964", "Roma")
            self.assertEqual(controller.weatherHourly, [])
            self.assertEqual(controller.weatherStatus, "Dati meteo non disponibili al momento.")
            self.assertTrue(controller._weather_retry_pending)

            controller.refreshWeatherNow()

            self.assertTrue(_wait_for_weather_refresh(controller))
            self.assertGreater(len(controller.weatherHourly), 0)
            self.assertEqual(controller.weatherStatus, "")
            self.assertFalse(controller._weather_retry_pending)
            self.assertNotIn("Meteo non disponibile", controller.weatherSummary["alert"])
            self.assertNotEqual(controller.weatherDigest["bestWindow"], "n/d")
        app.processEvents()

    def test_stale_weather_refresh_result_does_not_override_current_weather_state(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            controller.setManualLocation("41.9028", "12.4964", "Roma")
            current_weather = controller.weatherHourly
            stale_request_id = controller._weather_refresh_request_id
            controller._weather_refresh_request_id += 1
            controller._weather_status = "Dati meteo non disponibili al momento."

            controller._finish_weather_refresh(stale_request_id, "stale-location", [], WEATHER_UNAVAILABLE_MESSAGE)

            self.assertEqual(controller.weatherHourly, current_weather)
            self.assertEqual(controller.weatherStatus, "")
            self.assertGreater(len(controller.weatherHourly), 0)

    def test_automatic_weather_refresh_failure_keeps_data_and_schedules_forced_retry(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            controller.setManualLocation("41.9028", "12.4964", "Roma")
            existing_weather = controller.weatherHourly

            fake_weather_service = _AutomaticRefreshFailingWeatherService()
            controller._weather_service = fake_weather_service
            fake_weather_service.force_refresh_values.clear()
            controller._schedule_viirs_sky_quality_refresh = Mock()

            controller._refresh_weather_from_timer()

            self.assertTrue(_wait_for_weather_refresh(controller))
            self.assertEqual(fake_weather_service.force_refresh_values, [False])
            self.assertEqual(controller.weatherHourly, existing_weather)
            self.assertEqual(
                controller.weatherStatus,
                "Tentativo di aggiornamento meteo fallito; uso ultimi dati disponibili.",
            )
            self.assertTrue(controller._weather_refresh_timer.isActive())
            self.assertTrue(controller._weather_retry_pending)
            self.assertGreater(controller._weather_refresh_timer.remainingTime(), 0)
            self.assertLessEqual(controller._weather_refresh_timer.remainingTime(), WEATHER_RETRY_DELAY_MS)

            controller._refresh_weather_from_timer()

            self.assertTrue(_wait_for_weather_refresh(controller))
            self.assertEqual(fake_weather_service.force_refresh_values, [False, True])
            controller._schedule_viirs_sky_quality_refresh.assert_not_called()

    def test_approximate_online_location_refreshes_weather(self) -> None:
        with self._controller_with_weather(_valid_weather_response()) as controller:
            fake_weather_service = Mock()
            fake_weather_service.hourly_forecast.return_value = [
                WeatherHour("2026-06-21T22:00", "22:00", 20, 0, 6, 55, 18.0, 18_000)
            ]
            fake_weather_service.last_error = ""
            controller._weather_service = fake_weather_service
            result = LocationDetectionResult(
                location=ObserverLocation("Rome", "Italy", 41.9, 12.5, "Europe/Rome"),
                provider="ip_geolocation",
                source="test",
                accuracy="city-level",
                approximate=True,
                message="Posizione approssimata rilevata tramite connessione internet: Rome, Italy. La precisione può essere limitata.",
            )
            with patch.object(controller._location_service, "detect_ip_location", return_value=result):
                controller.useApproximateOnlineLocation()

            self.assertEqual(controller.location["city"], "Rome")
            self.assertIn("Posizione approssimata rilevata", controller.locationMessage)
            fake_weather_service.hourly_forecast.assert_called()

    def test_weather_page_displays_active_location_context(self) -> None:
        qml = (Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "WeatherPage.qml").read_text(encoding="utf-8")
        self.assertIn("Meteo per: ", qml)
        self.assertEqual(qml.count("Meteo per: "), 1)
        self.assertIn("controller.activeLocationLabel", qml)
        self.assertIn("controller.activeLocationSource", qml)
        self.assertIn("Nessuna località configurata", qml)
        self.assertIn('text: !controller.hasValidLocation', qml)
        self.assertIn('qsTr("Configura località")', qml)
        self.assertIn("root.openLocation()", qml)
        self.assertGreaterEqual(qml.count("value: !controller.hasValidLocation"), 2)
        self.assertIn(
            "visible: controller.hasValidLocation && controller.skyQuality.hasViirsRadiance",
            qml,
        )
        self.assertIn("ListView.Horizontal", qml)
        self.assertIn("selectedWeatherHourIndex", qml)
        self.assertIn("selectedWeatherHourTimestamp", qml)
        self.assertIn("controller.refreshWeatherNow()", qml)
        self.assertIn("controller.weatherRefreshRunning", qml)
        self.assertIn("controller.weatherNext24Hours", qml)
        self.assertIn("root.displayWeatherHours", qml)
        self.assertIn("isObservingNight", qml)
        self.assertIn("Previsione mobile delle prossime 24 ore", qml)
        self.assertIn("Notte osservativa", qml)
        self.assertIn('text: qsTr("Sintesi notte osservativa")', qml)
        self.assertIn('label: qsTr("Nuvolosità media")', qml)
        self.assertIn('label: qsTr("Precipitazioni max")', qml)
        self.assertIn('label: qsTr("Seeing notturno")', qml)
        self.assertIn('label: qsTr("Bortle locale")', qml)
        cloud_card_start = qml.index('title: qsTr("Copertura nuvolosa oraria")')
        weather_bars_start = qml.index("WeatherBars {", cloud_card_start)
        cloud_header = qml[cloud_card_start:weather_bars_start]
        self.assertIn("headerContent: [", cloud_header)
        self.assertIn('text: qsTr("Notte osservativa")', cloud_header)
        self.assertEqual(qml.count('text: qsTr("Notte osservativa")'), 1)
        self.assertIn("? theme.cyan", qml)
        self.assertNotIn("ScrollBar.horizontal", qml)
        self.assertNotIn("controller.observingWeatherHourly", qml)
        self.assertNotIn("controller.weatherHourly", qml)
        self.assertIn("Radianza VIIRS", qml)
        self.assertIn("Osservazioni VIIRS", qml)
        self.assertIn("SQM stimato", qml)
        self.assertIn('title: qsTr("Aerosol atmosferico")', qml)
        self.assertIn("visible: controller.atmosphericTransparency.visible", qml)
        self.assertIn('subtitle: qsTr("NASA MAIAC AOD")', qml)
        self.assertIn('MetricTile { label: qsTr("AOD 550 nm")', qml)
        self.assertIn('MetricTile { label: qsTr("Effetto aerosol")', qml)
        self.assertIn('MetricTile { label: qsTr("Freschezza")', qml)
        self.assertIn("Recupero dati NASA AOD...", qml)
        self.assertIn('title: qsTr("Particolato locale")', qml)
        self.assertIn("visible: controller.localAtmosphere.visible", qml)
        self.assertIn('MetricTile { label: qsTr("PM2.5")', qml)
        self.assertIn('MetricTile { label: qsTr("PM10")', qml)
        self.assertIn('MetricTile { label: qsTr("Aria locale")', qml)
        self.assertIn('MetricTile { label: qsTr("Fonte")', qml)
        self.assertIn("controller.localAtmosphere.sourceDetail", qml)
        self.assertNotIn("weatherLocationLayout", qml)

        weather_bars = (
            Path(__file__).resolve().parents[1] / "app" / "ui" / "components" / "WeatherBars.qml"
        ).read_text(encoding="utf-8")
        self.assertIn("nightBarColor", weather_bars)
        self.assertIn("minimumColumnWidth", weather_bars)
        self.assertIn("Flickable.HorizontalFlick", weather_bars)

    def test_home_page_displays_active_location_context(self) -> None:
        qml = (Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "HomePage.qml").read_text(encoding="utf-8")
        self.assertIn("controller.activeLocationLabel", qml)
        self.assertIn("controller.activeLocationSource", qml)
        self.assertIn("controller.homeNightPlanOverview", qml)
        self.assertIn("root.nightProfileOverview.summary", qml)
        self.assertIn('title: root.nightPlanOverview.title || qsTr("Piano osservativo")', qml)
        self.assertIn('title: root.nightAlternativesOverview.title || qsTr("Altri oggetti visibili stasera")', qml)
        self.assertIn("delegate: HomePlanStepRow", qml)
        self.assertIn("delegate: HomeVisibleTargetRow", qml)
        plan_step_qml = (
            Path(__file__).resolve().parents[1] / "app" / "ui" / "components" / "HomePlanStepRow.qml"
        ).read_text(encoding="utf-8")
        image_start = plan_step_qml.index("Layout.preferredWidth: 52")
        text_start = plan_step_qml.index("ColumnLayout {", image_start)
        self.assertIn("Layout.alignment: Qt.AlignVCenter", plan_step_qml[image_start:text_start])
        self.assertIn("model: root.filteredNightAlternatives()", qml)
        self.assertIn("Finestra", qml)
        self.assertIn("Direzione", qml)
        self.assertNotIn("Pianeti potenzialmente visibili", qml)
        self.assertNotIn("Oggetti cielo profondo potenzialmente visibili", qml)
        self.assertNotIn("Layout.minimumHeight: controller.nightPlan.length > 0 ? 286 : 0", qml)
        self.assertNotIn("controller.isObservingSessionBlocked ? \"Pianeti potenzialmente visibili\"", qml)
        self.assertNotIn("controller.observingSessionIcon", qml)
        self.assertNotIn("Target potenzialmente interessanti", qml)
        self.assertNotIn("function hasBlockingWeather", qml)
        self.assertNotIn("function blockingWeatherReason", qml)
        self.assertNotIn("function blockingWeatherDetail", qml)

    def test_calendar_event_cards_open_inline_detail_view(self) -> None:
        base_dir = Path(__file__).resolve().parents[1] / "app" / "ui"
        calendar_qml = (base_dir / "pages" / "CalendarPage.qml").read_text(encoding="utf-8")
        detail_qml = (base_dir / "pages" / "EventDetailPage.qml").read_text(encoding="utf-8")
        row_qml = (base_dir / "components" / "EventRow.qml").read_text(encoding="utf-8")
        main_qml = (base_dir / "main.qml").read_text(encoding="utf-8")

        self.assertIn("property string selectedEventId", calendar_qml)
        self.assertIn("property var selectedEventData: selectedEventById(selectedEventId)", calendar_qml)
        self.assertIn("function selectedEventById(eventId)", calendar_qml)
        self.assertIn("EventDetailPage", calendar_qml)
        self.assertIn("visible: root.hasSelectedEvent()", calendar_qml)
        self.assertIn("controller.calendarOverview", calendar_qml)
        self.assertIn("onClicked: root.showEvent(modelData.id)", calendar_qml)
        self.assertIn("signal clicked()", row_qml)
        self.assertIn("MouseArea", row_qml)
        self.assertIn("root.eventData.visibilityLabel", row_qml)
        self.assertNotIn("root.eventData.usefulness", row_qml)
        self.assertIn("Torna al Calendario", detail_qml)
        self.assertIn("Quando osservare l'evento", detail_qml)
        self.assertIn("Con il tuo profilo", detail_qml)
        self.assertIn("Consigli osservativi", detail_qml)
        self.assertIn('text: qsTr("Apri %1").arg(modelData.name)', detail_qml)
        self.assertIn("root.eventData.whyText", detail_qml)
        self.assertIn("root.eventData.setupText", detail_qml)
        self.assertIn("root.eventData.tips", detail_qml)
        self.assertIn("property string calendarEventId", main_qml)
        self.assertIn("onOpenEvent: function(eventId)", main_qml)
        self.assertIn("onOpenCalendar:", main_qml)
        self.assertIn("onOpenObject: function(objectId)", main_qml)
        self.assertIn('window.currentPage = "detail"', main_qml)

    def test_data_providers_page_exposes_earthdata_configuration(self) -> None:
        ui_pages = Path(__file__).resolve().parents[1] / "app" / "ui" / "pages"
        location_qml = (ui_pages / "LocationPage.qml").read_text(encoding="utf-8")
        qml = (ui_pages / "DataProvidersPage.qml").read_text(encoding="utf-8")
        self.assertIn('title: qsTr("Posizioni recenti")', location_qml)
        self.assertIn('text: qsTr("Nessuna posizione recente.")', location_qml)
        self.assertNotIn("visible: controller.recentLocations.length > 0", location_qml)
        self.assertNotIn('title: qsTr("Earthdata NASA")', location_qml)
        self.assertIn('text: qsTr("Provider dati")', qml)
        self.assertIn('title: qsTr("Earthdata NASA")', qml)
        self.assertIn('earthdataRegistrationUrl: "https://urs.earthdata.nasa.gov/users/new"', qml)
        self.assertIn('headerActionText: qsTr("Crea account")', qml)
        self.assertIn("headerActionWidth: 148", qml)
        self.assertIn("!controller.earthdataConnectionTestRunning && !controller.earthdataConnectionVerified", qml)
        self.assertIn("&& !controller.earthdataAuthorizationRequired", qml)
        self.assertIn(
            'headerActionToolTip: controller.earthdataConnectionVerified || controller.earthdataAuthorizationRequired',
            qml,
        )
        self.assertIn("onHeaderActionClicked: Qt.openUrlExternally(root.earthdataRegistrationUrl)", qml)
        self.assertIn('openAQRegistrationUrl: "https://explore.openaq.org/register"', qml)
        self.assertIn('title: qsTr("OpenAQ")', qml)
        self.assertIn(
            'placeholderText: controller.openaqCredentialsConfigured ? qsTr("Nuova API key OpenAQ") : qsTr("API key OpenAQ")',
            qml,
        )
        self.assertIn("controller.saveOpenAQApiKey(openaqApiKey.text)", qml)
        self.assertIn("controller.testOpenAQConnection()", qml)
        self.assertIn("controller.removeOpenAQCredentials()", qml)
        openaq_card = qml[qml.index('title: qsTr("OpenAQ")') :]
        self.assertNotIn("Autorizza app", openaq_card)

    def test_location_page_prioritizes_city_search_layout(self) -> None:
        qml = (Path(__file__).resolve().parents[1] / "app" / "ui" / "pages" / "LocationPage.qml").read_text(encoding="utf-8")
        self.assertLess(
            qml.index('title: qsTr("Posizione attuale")'),
            qml.index('title: qsTr("Ricerca città")'),
        )
        self.assertLess(
            qml.index('title: qsTr("Ricerca città")'),
            qml.index('title: qsTr("Posizioni recenti")'),
        )
        self.assertLess(
            qml.index("title: qsTr(\"Rilevamento posizione all'avvio\")"),
            qml.index('title: qsTr("Posizione Windows")'),
        )
        self.assertLess(
            qml.index('title: qsTr("Posizione Windows")'),
            qml.index('title: qsTr("Località IP (ipapi/ipwho)")'),
        )
        self.assertLess(
            qml.index('title: qsTr("Località IP (ipapi/ipwho)")'),
            qml.index('title: qsTr("Coordinate manuali")'),
        )
        self.assertIn("Layout.rowSpan: root.width > 1040 ? 2 : 1", qml)
        self.assertIn("clip: true", qml)
        city_card = qml[
            qml.index('title: qsTr("Ricerca città")') : qml.index(
                'title: qsTr("Posizione Windows")'
            )
        ]
        self.assertIn("contentFillsHeight: true", city_card)
        self.assertIn("Layout.fillHeight: true", city_card)
        self.assertNotIn("Layout.preferredHeight: root.width > 1040 ? 252 : 168", city_card)
        self.assertIn('subtitle: qsTr("Geolocalizzazione IP")', qml)
        self.assertIn('placeholderText: qsTr("Nome luogo (facoltativo)")', qml)
        self.assertIn('placeholderText: qsTr("Latitudine *")', qml)
        self.assertIn('placeholderText: qsTr("Longitudine *")', qml)
        self.assertIn("enabled: manualLatitude.text.trim().length > 0", qml)

    def _controller_with_weather(self, response: Mock | None = None, side_effect=None, **kwargs):
        return _ControllerContext(response=response, side_effect=side_effect, **kwargs)


class _ControllerContext:
    def __init__(
        self,
        response: Mock | None = None,
        side_effect=None,
        saved_location: bool = False,
        preferences: dict | None = None,
        patch_location_requests: bool = False,
    ):
        self._response = response
        self._side_effect = side_effect
        self._saved_location = saved_location
        self._preferences = preferences or {}
        self._patch_location_requests = patch_location_requests
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self._patcher = None
        self._location_patcher = None
        self._background_patcher = None
        self.weather_requests = None
        self.location_requests = None
        self._app = None
        self._controller: AppController | None = None

    def __enter__(self) -> AppController:
        self._app = QCoreApplication.instance() or QCoreApplication([])
        self._temp_dir = tempfile.TemporaryDirectory()
        base_dir = Path(__file__).resolve().parents[1]
        database_path = Path(self._temp_dir.name) / "nightscope.db"
        initialize_database(database_path, base_dir / "data" / "schema.sql")
        self._seed_preferences(database_path)
        self._patcher = patch(
            "astro_viewer.app.services.weather_service.requests.get",
            return_value=self._response,
            side_effect=self._side_effect,
        )
        self.weather_requests = self._patcher.start()
        if self._patch_location_requests:
            self._location_patcher = patch(
                "astro_viewer.app.services.location_service.requests.get",
                return_value=self._response,
                side_effect=self._side_effect,
            )
            self.location_requests = self._location_patcher.start()
        self._background_patcher = patch.object(
            AppController,
            "_start_background_task",
            new=staticmethod(lambda target: target()),
        )
        self._background_patcher.start()
        self._controller = AppController(base_dir=base_dir, database_path=database_path)
        return self._controller

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self._controller:
            _wait_for_startup_location(self._controller)
        if self._controller and hasattr(self._controller._astronomy_engine, "close"):
            self._controller._astronomy_engine.close()
        if self._patcher:
            self._patcher.stop()
        if self._location_patcher:
            self._location_patcher.stop()
        if self._background_patcher:
            self._background_patcher.stop()
        if self._temp_dir:
            self._temp_dir.cleanup()

    def _seed_preferences(self, database_path: Path) -> None:
        store = LocationPreferenceStore(
            database_path.parent / "user_preferences.json",
            database_path.parent / "location_cache.json",
        )
        if self._preferences:
            store.update_preferences(
                auto_detect_location_on_startup=self._preferences.get("auto_detect_location_on_startup"),
                allow_approximate_online_location=self._preferences.get("allow_approximate_online_location"),
                use_windows_location_on_startup=self._preferences.get("use_windows_location_on_startup"),
            )
        if self._saved_location:
            store.save_location(
                LocationDetectionResult(
                    location=ObserverLocation("Addis Ababa", "Etiopia", 9.03, 38.74, "Africa/Addis_Ababa"),
                    provider="manual_city",
                    source="SQLite City",
                    accuracy="city coordinates",
                    approximate=False,
                    country_code="ET",
                    message="Posizione impostata su Addis Ababa, Etiopia.",
                )
            )


class _ForceRefreshFailingWeatherService:
    def __init__(self) -> None:
        self.last_error = ""
        self.force_refresh_values: list[bool] = []

    def hourly_forecast(self, location: ObserverLocation, force_refresh: bool = False) -> list[WeatherHour]:
        self.force_refresh_values.append(force_refresh)
        if force_refresh:
            self.last_error = WEATHER_UNAVAILABLE_MESSAGE
            return []
        self.last_error = ""
        return [WeatherHour("2026-06-21T22:00", "22:00", 20, 0, 6, 55, 18.0, 18_000)]


class _AutomaticRefreshFailingWeatherService:
    def __init__(self) -> None:
        self.last_error = ""
        self.retry_recommended = True
        self.force_refresh_values: list[bool] = []

    def hourly_forecast(self, location: ObserverLocation, force_refresh: bool = False) -> list[WeatherHour]:
        self.force_refresh_values.append(force_refresh)
        self.last_error = WEATHER_UNAVAILABLE_MESSAGE
        return []


def _wait_for_startup_location(controller: AppController, timeout_seconds: float = 3.0) -> bool:
    app = QCoreApplication.instance() or QCoreApplication([])
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if not controller.startupLocationDetectionRunning:
            app.processEvents()
            return True
        time.sleep(0.01)
    app.processEvents()
    return not controller.startupLocationDetectionRunning


def _wait_for_weather_refresh(controller: AppController, timeout_seconds: float = 3.0) -> bool:
    app = QCoreApplication.instance() or QCoreApplication([])
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if not controller.weatherRefreshRunning:
            app.processEvents()
            return True
        time.sleep(0.01)
    app.processEvents()
    return not controller.weatherRefreshRunning


def _valid_weather_response() -> Mock:
    response = Mock()
    response.raise_for_status.return_value = None
    start = datetime.now(ZoneInfo("Africa/Addis_Ababa")).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
        tzinfo=None,
    )
    timestamps = [(start + timedelta(hours=index)).isoformat(timespec="minutes") for index in range(48)]
    response.json.return_value = {
        "hourly": {
            "time": timestamps,
            "cloud_cover": [18] * 48,
            "precipitation_probability": [0] * 48,
            "temperature_2m": [17.5] * 48,
            "relative_humidity_2m": [56] * 48,
            "wind_speed_10m": [7] * 48,
            "visibility": [18000] * 48,
        }
    }
    return response


def _rainy_weather_response() -> Mock:
    response = _valid_weather_response()
    response.json.return_value["hourly"]["precipitation_probability"] = [80] * 48
    return response


def _monitoring_weather_response() -> Mock:
    response = _valid_weather_response()
    hourly = response.json.return_value["hourly"]
    hourly["cloud_cover"] = [88] * 48
    hourly["precipitation_probability"] = [80] * 48
    hourly["wind_speed_10m"] = [9] * 48
    hourly["relative_humidity_2m"] = [64] * 48
    for index, timestamp in enumerate(hourly["time"]):
        if datetime.fromisoformat(timestamp).hour in {3, 4, 5}:
            hourly["cloud_cover"][index] = 24
            hourly["precipitation_probability"][index] = 0
    return response


if __name__ == "__main__":
    unittest.main()
