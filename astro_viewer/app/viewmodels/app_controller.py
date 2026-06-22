from __future__ import annotations

import logging
import re
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot

from astro_viewer.app.astronomy.engine import MockAstronomyEngine, ObserverLocation
from astro_viewer.app.astronomy.skyfield_engine import EphemerisUnavailableError, SkyfieldAstronomyEngine
from astro_viewer.app.database.city_repository import CityRepository
from astro_viewer.app.database.equipment_catalog_repository import EquipmentCatalogRepository
from astro_viewer.app.database.messier_repository import MessierRepository
from astro_viewer.app.database.object_image_repository import ObjectImageRepository
from astro_viewer.app.database.observation_repository import ObservationRepository
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.database.weather_cache_repository import WeatherCacheRepository
from astro_viewer.app.models.equipment import Barlow, Eyepiece, Telescope
from astro_viewer.app.models.observing import AstronomicalEvent, CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherHour, WeatherSummary
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.app.services.earthdata_credentials import EarthdataConnectionTester, EarthdataCredentialStore
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.light_pollution_service import LightPollutionService
from astro_viewer.app.services.location_service import (
    APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE,
    LocationDetectionResult,
    LocationService,
    LocationUnavailableError,
)
from astro_viewer.app.services.location_preferences import LocationPreferenceStore
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.notification_service import NotificationService
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.services.seeing_service import SeeingTransparencyService
from astro_viewer.app.services.sky_map_service import SkyMapService
from astro_viewer.app.services.weather_service import WEATHER_UNAVAILABLE_MESSAGE, OpenMeteoWeatherService


logger = logging.getLogger(__name__)


class AppController(QObject):
    dataChanged = Signal()
    selectedObjectChanged = Signal()
    locationChanged = Signal()
    weatherChanged = Signal()
    equipmentChanged = Signal()
    observationChanged = Signal()
    statusChanged = Signal()
    earthdataCredentialsChanged = Signal()

    def __init__(self, base_dir: Path, database_path: Path):
        super().__init__()
        self._base_dir = base_dir
        self._city_repository = CityRepository(database_path)
        self._messier_repository = MessierRepository(database_path)
        self._equipment_catalog_repository = EquipmentCatalogRepository(database_path)
        self._sky_quality_repository = SkyQualityRepository(database_path)
        self._object_image_repository = ObjectImageRepository(database_path)
        self._weather_cache_repository = WeatherCacheRepository(database_path)
        self._observation_repository = ObservationRepository(database_path)
        self._location_preferences = LocationPreferenceStore(
            preferences_path=database_path.parent / "user_preferences.json",
            cache_path=database_path.parent / "location_cache.json",
        )
        self._earthdata_credential_store = EarthdataCredentialStore(
            preferences_path=database_path.parent / "user_preferences.json",
        )
        self._earthdata_connection_tester = EarthdataConnectionTester()
        self._earthdata_credentials_state = self._earthdata_credential_store.state()
        self._startup_location_preferences = self._location_preferences.preferences()
        self._location_service = LocationService(
            city_resolver=self._city_repository,
            cache_path=database_path.parent / "location_cache.json",
        )
        self._is_loading = False
        self._service_status = ""
        self._weather_status = ""
        try:
            self._astronomy_engine = SkyfieldAstronomyEngine(base_dir / "data", self._messier_repository)
        except EphemerisUnavailableError:
            logger.error("Skyfield engine unavailable; using fallback astronomy data.", exc_info=True)
            self._astronomy_engine = MockAstronomyEngine()
            self._service_status = "Astronomical ephemeris unavailable. Using fallback sky data."
        self._weather_service = OpenMeteoWeatherService(self._weather_cache_repository)
        self._equipment_service = EquipmentService()
        self._score_service = ObservingScoreService()
        self._light_pollution_service = LightPollutionService(
            self._sky_quality_repository,
            dataset_path=base_dir / "data" / "light_pollution_seed.csv",
        )
        self._seeing_service = SeeingTransparencyService()
        self._advanced_observing_service = AdvancedObservingService()
        self._night_planner_service = NightPlannerService()
        self._sky_map_service = SkyMapService()
        self._notification_service = NotificationService()

        self._city_results = []
        self._city_search_has_query = False
        self._location_detection_result: LocationDetectionResult | None = None
        self._location: ObserverLocation | None = None
        self._location_message = "Configura una posizione per ottenere meteo e cielo locale."
        self._offer_online_location_fallback = False
        self._windows_location_diagnostics = self._empty_windows_diagnostics()

        self._visible_planets: list[CelestialObject] = []
        self._solar_system_objects: list[CelestialObject] = []
        self._deep_sky: list[CelestialObject] = []
        self._moon = None
        self._events = []
        self._weather_hours = []
        self._weather_summary = None
        self._sky_quality = None
        self._seeing_transparency = None
        self._advanced_scores = None
        self._night_plan = []
        self._sky_map = []
        self._notifications = []
        self._selected_object: CelestialObject | None = None
        self._best_object: CelestialObject | None = None
        self._observation_history = self._observation_repository.recent(limit=10)

        self._beginner_presets = self._equipment_service.beginner_presets()
        self._telescope_brands = self._equipment_catalog_repository.brands()
        self._telescope_catalog_models = self._equipment_catalog_repository.models()
        self._catalog_eyepieces = self._equipment_catalog_repository.eyepieces()
        self._catalog_barlows = self._equipment_catalog_repository.barlows()
        self._equipment_profiles = self._equipment_catalog_repository.profiles()
        self._object_images = self._object_image_repository.all()
        self._object_image_map = {item["object_id"]: item for item in self._object_images}
        self._object_descriptions = self._object_image_repository.descriptions()
        self._telescopes: list[Telescope] = self._initial_telescopes()
        self._eyepieces: list[Eyepiece] = [self._eyepiece_from_catalog_row(row) for row in self._catalog_eyepieces]
        self._barlows: list[Barlow] = [self._barlow_from_catalog_row(row) for row in self._catalog_barlows]
        self._profile_equipment = self._initial_profile_equipment()
        self._selected_telescope_index = self._initial_telescope_index()
        self._barlow = 1.0
        self._equipment_message = self._equipment_status_message()

        self._initialize_startup_location()
        self._refresh_all()

    @Property(str, constant=True)
    def assetBaseUrl(self) -> str:
        return QUrl.fromLocalFile(str(self._base_dir)).toString()

    @Property("QVariant", notify=locationChanged)
    def location(self) -> dict:
        return self._location_to_qml(self._location)

    @Property(str, notify=locationChanged)
    def locationMessage(self) -> str:
        return self._location_message

    @Property(bool, notify=locationChanged)
    def canUseApproximateOnlineLocation(self) -> bool:
        return self._offer_online_location_fallback

    @Property("QVariant", notify=locationChanged)
    def locationDetails(self) -> dict:
        return self._location_detection_result.to_qml() if self._location_detection_result else {}

    @Property(str, notify=locationChanged)
    def activeLocationLabel(self) -> str:
        if not self._has_valid_location():
            return "Nessuna posizione configurata"
        return f"{self._location.city} — {self._location.timezone}"

    @Property(str, notify=locationChanged)
    def activeLocationSource(self) -> str:
        if not self._location_detection_result:
            return "Nessuna posizione"
        return self._location_source_label(self._location_detection_result.provider)

    @Property(bool, notify=locationChanged)
    def autoDetectLocationOnStartup(self) -> bool:
        return self._startup_location_preferences.auto_detect_location_on_startup

    @Property(bool, notify=locationChanged)
    def allowApproximateOnlineLocation(self) -> bool:
        return self._startup_location_preferences.allow_approximate_online_location

    @Property(bool, notify=locationChanged)
    def useWindowsLocationOnStartup(self) -> bool:
        return self._startup_location_preferences.use_windows_location_on_startup

    @Property(str, notify=earthdataCredentialsChanged)
    def earthdataUsername(self) -> str:
        return self._earthdata_credentials_state.username

    @Property(bool, notify=earthdataCredentialsChanged)
    def earthdataCredentialsConfigured(self) -> bool:
        return self._earthdata_credentials_state.configured

    @Property(bool, notify=earthdataCredentialsChanged)
    def earthdataSecureStorageAvailable(self) -> bool:
        return self._earthdata_credentials_state.secure_store_available

    @Property(str, notify=earthdataCredentialsChanged)
    def earthdataCredentialMessage(self) -> str:
        return self._earthdata_credentials_state.message

    @Property("QVariant", notify=locationChanged)
    def windowsLocationDiagnostics(self) -> dict:
        return self._windows_location_diagnostics

    @Property(bool, notify=locationChanged)
    def hasValidLocation(self) -> bool:
        return self._has_valid_location()

    @Property(bool, notify=statusChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=statusChanged)
    def serviceStatus(self) -> str:
        return self._service_status

    @Property(str, notify=weatherChanged)
    def weatherStatus(self) -> str:
        return self._weather_status

    @Property(bool, notify=dataChanged)
    def hasVisibleObjects(self) -> bool:
        return bool(self._visible_planets or self._deep_sky)

    @Property("QVariant", notify=locationChanged)
    def cityResults(self) -> list[dict]:
        return self._city_results

    @Property(bool, notify=locationChanged)
    def hasCitySearchQuery(self) -> bool:
        return self._city_search_has_query

    @Property("QVariant", notify=locationChanged)
    def recentLocations(self) -> list[dict]:
        return self._recent_locations()

    @Property("QVariant", notify=dataChanged)
    def visiblePlanets(self) -> list[dict]:
        return [self._object_to_qml(planet) for planet in self._home_visible_objects(self._visible_planets)]

    @Property("QVariant", notify=dataChanged)
    def solarSystemObjects(self) -> list[dict]:
        return [item.to_qml() for item in self._solar_system_objects]

    @Property("QVariant", notify=dataChanged)
    def recommendedDeepSky(self) -> list[dict]:
        return [self._object_to_qml(deep_sky) for deep_sky in self._home_visible_objects(self._deep_sky)]

    @Property("QVariant", notify=dataChanged)
    def moonSummary(self) -> dict:
        return self._moon.to_qml() if self._moon else {}

    @Property("QVariant", notify=dataChanged)
    def events(self) -> list[dict]:
        return [self._event_to_qml(event) for event in self._events]

    @Property("QVariant", notify=dataChanged)
    def upcomingHighlights(self) -> list[dict]:
        now = datetime.now(self._zone())
        limit = now + timedelta(days=30)
        upcoming = []
        for event in self._events:
            event_date = self._parse_event_date(event.date_label, now)
            if event_date and now.date() <= event_date.date() <= limit.date():
                upcoming.append((event_date, event))
        upcoming.sort(key=lambda item: (-item[1].usefulness, item[0]))
        return [self._event_to_qml(event) for _, event in upcoming[:3]]

    @Property("QVariant", notify=weatherChanged)
    def weatherHourly(self) -> list[dict]:
        return [hour.to_qml() for hour in self._weather_hours]

    @Property("QVariant", notify=weatherChanged)
    def weatherSummary(self) -> dict:
        return self._weather_summary.to_qml() if self._weather_summary else {}

    @Property("QVariant", notify=weatherChanged)
    def observingQuality(self) -> dict:
        return self._weather_summary.to_qml() if self._weather_summary else {}

    @Property("QVariant", notify=weatherChanged)
    def skyQuality(self) -> dict:
        return self._sky_quality.to_qml() if self._sky_quality else {}

    @Property("QVariant", notify=weatherChanged)
    def seeingTransparency(self) -> dict:
        return self._seeing_transparency.to_qml() if self._seeing_transparency else {}

    @Property("QVariant", notify=weatherChanged)
    def advancedScores(self) -> dict:
        return self._advanced_scores.to_qml() if self._advanced_scores else {}

    @Property("QVariant", notify=weatherChanged)
    def weatherDigest(self) -> dict:
        return self._weather_digest()

    @Property(str, notify=weatherChanged)
    def skyQualityWarning(self) -> str:
        if not self._sky_quality:
            return ""
        if self._sky_quality.bortle_class >= 8:
            return "Cielo urbano: oggetti cielo profondo limitati. Preferire ammassi aperti, pianeti e Luna."
        if self._sky_quality.bortle_class >= 7:
            return "Cielo suburbano luminoso: privilegiare oggetti brillanti e pianeti."
        return ""

    @Property("QVariant", notify=dataChanged)
    def bestObjectOfNight(self) -> dict:
        return self._object_to_qml(self._best_object) if self._best_object else {}

    @Property("QVariant", notify=dataChanged)
    def nightPlan(self) -> list[dict]:
        return [item.to_qml() for item in self._night_plan]

    @Property("QVariant", notify=dataChanged)
    def skyMap(self) -> list[dict]:
        return self._sky_map

    @Property("QVariant", notify=dataChanged)
    def notifications(self) -> list[dict]:
        return [item.to_qml() for item in self._notifications]

    @Property("QVariant", notify=selectedObjectChanged)
    def selectedObject(self) -> dict:
        if not self._selected_object:
            return {}
        return self._object_to_qml(self._selected_object)

    @Property("QVariant", notify=dataChanged)
    def tonightHighlights(self) -> list[dict]:
        objects = self._home_visible_objects(self._visible_planets)[:2] + self._home_visible_objects(self._deep_sky)[:2]
        return [
            {
                "name": item.name,
                "type": item.object_type,
                "bestTime": self._home_time_label(item),
                "setup": item.recommended_setup,
            }
            for item in objects
        ]

    @Property("QVariant", notify=equipmentChanged)
    def beginnerPresets(self) -> list[dict]:
        return [preset.to_qml() for preset in self._beginner_presets]

    @Property("QVariant", notify=equipmentChanged)
    def equipmentSetups(self) -> list[dict]:
        return [telescope.to_qml() for telescope in self._catalog_telescopes()]

    @Property("QVariant", notify=equipmentChanged)
    def profileTelescopes(self) -> list[dict]:
        return [telescope.to_qml() for telescope in self._active_profile_telescopes()]

    @Property("QVariant", notify=equipmentChanged)
    def availableProfileTelescopes(self) -> list[dict]:
        assigned = {telescope.id for telescope in self._active_profile_telescopes()}
        return [telescope.to_qml() for telescope in self._catalog_telescopes() if telescope.id not in assigned]

    @Property("QVariant", notify=equipmentChanged)
    def telescopeBrands(self) -> list[dict]:
        return self._telescope_brands

    @Property("QVariant", notify=equipmentChanged)
    def telescopeCatalogModels(self) -> list[dict]:
        return self._telescope_catalog_models

    @Property("QVariant", notify=equipmentChanged)
    def eyepieceCatalog(self) -> list[dict]:
        return self._catalog_eyepieces

    @Property("QVariant", notify=equipmentChanged)
    def barlowCatalog(self) -> list[dict]:
        return self._catalog_barlows

    @Property("QVariant", notify=equipmentChanged)
    def equipmentProfiles(self) -> list[dict]:
        return self._equipment_profiles

    @Property("QVariant", notify=equipmentChanged)
    def activeEquipmentProfile(self) -> dict:
        return self._active_profile() or {"id": 0, "profile_name": "Occhio nudo", "active": 1, "telescope_id": "preset:naked-eye"}

    @Property("QVariant", notify=dataChanged)
    def objectImages(self) -> list[dict]:
        return self._object_images

    @Property("QVariant", notify=equipmentChanged)
    def eyepieces(self) -> list[dict]:
        return [eyepiece.to_qml() for eyepiece in self._active_profile_eyepieces()]

    @Property("QVariant", notify=equipmentChanged)
    def ownedEyepieces(self) -> list[dict]:
        return [eyepiece.to_qml() for eyepiece in self._eyepieces]

    @Property("QVariant", notify=equipmentChanged)
    def availableProfileEyepieces(self) -> list[dict]:
        assigned = {eyepiece.id for eyepiece in self._active_profile_eyepieces()}
        return [eyepiece.to_qml() for eyepiece in self._eyepieces if eyepiece.id not in assigned]

    @Property("QVariant", notify=equipmentChanged)
    def ownedBarlows(self) -> list[dict]:
        return [barlow.to_qml() for barlow in self._barlows]

    @Property("QVariant", notify=equipmentChanged)
    def profileEquipmentCatalog(self) -> list[dict]:
        assigned_ids = {item["id"] for item in self._profile_assigned_equipment()}
        items = self._equipment_catalog_items()
        for item in items:
            item["assigned"] = item["id"] in assigned_ids
        return items

    @Property("QVariant", notify=equipmentChanged)
    def profileAssignedEquipment(self) -> list[dict]:
        return self._profile_assigned_equipment()

    @Property("QVariant", notify=equipmentChanged)
    def profileBarlows(self) -> list[dict]:
        return [barlow.to_qml() for barlow in self._active_profile_barlows()]

    @Property("QVariant", notify=equipmentChanged)
    def availableProfileBarlows(self) -> list[dict]:
        assigned = {barlow.id for barlow in self._active_profile_barlows()}
        return [barlow.to_qml() for barlow in self._barlows if barlow.id not in assigned]

    @Property(bool, notify=equipmentChanged)
    def canUseEyepieces(self) -> bool:
        return self._equipment_service.can_use_eyepieces(self._current_telescope())

    @Property(str, notify=equipmentChanged)
    def equipmentMessage(self) -> str:
        return self._equipment_message

    @Property("QVariant", notify=equipmentChanged)
    def currentSetup(self) -> dict:
        return self._current_telescope().to_qml()

    @Property("QVariant", notify=equipmentChanged)
    def telescopeCalculations(self) -> list[dict]:
        return self._equipment_service.calculations(self._current_telescope(), self._active_profile_eyepieces(), self._barlow)

    @Property("QVariant", notify=equipmentChanged)
    def telescopeCapabilities(self) -> dict:
        return self._equipment_service.profile_capabilities(
            self._current_telescope(),
            self._active_profile_eyepieces(),
            self._active_profile_barlows(),
        )

    @Property(float, notify=equipmentChanged)
    def selectedBarlow(self) -> float:
        return self._barlow

    @Property("QVariant", notify=observationChanged)
    def observationHistory(self) -> list[dict]:
        return self._observation_history

    @Slot(str)
    def selectObject(self, object_id: str) -> None:
        for item in self._solar_system_objects + self._deep_sky:
            if item.id == object_id:
                self._selected_object = item
                self.selectedObjectChanged.emit()
                return

    @Slot(str)
    def searchCities(self, query: str) -> None:
        if query.strip():
            self._city_search_has_query = True
            self._city_results = self._city_repository.search(query, limit=20)
        else:
            self._city_search_has_query = False
            self._city_results = []
        self.locationChanged.emit()

    @Slot(int)
    def selectRecentLocation(self, index: int) -> None:
        recent = self._recent_location_results()
        if 0 <= index < len(recent):
            self._apply_location_result(recent[index])
            self._refresh_all()
            self.locationChanged.emit()

    @Slot(int)
    def selectCity(self, city_id: int) -> None:
        city = self._city_repository.get_by_id(city_id)
        if not city:
            return
        result = self._location_service.from_city_result(city)
        self._apply_location_result(result)
        self._refresh_all()
        self.locationChanged.emit()

    @Slot(str, str, str)
    def setManualLocation(self, latitude: str, longitude: str, label: str) -> None:
        try:
            parsed_latitude = float(latitude.replace(",", "."))
            parsed_longitude = float(longitude.replace(",", "."))
        except ValueError:
            self._location_message = "Coordinate non valide."
            self.locationChanged.emit()
            return

        if not -90 <= parsed_latitude <= 90 or not -180 <= parsed_longitude <= 180:
            self._location_message = "Coordinate fuori intervallo."
            self.locationChanged.emit()
            return

        clean_label = label.strip() or "Coordinate manuali"
        result = self._location_service.from_manual_coordinates_result(
            parsed_latitude,
            parsed_longitude,
            label=clean_label,
        )
        self._apply_location_result(result)
        self._refresh_all()
        self.locationChanged.emit()

    @Slot()
    def useWindowsLocation(self) -> None:
        try:
            result = self._location_service.detect_windows_location()
        except LocationUnavailableError as exc:
            logger.warning("Windows location unavailable in AppController: %s", exc.reason)
            self._location_message = "Windows location is unavailable. Try approximate online location?"
            self._offer_online_location_fallback = True
            self.locationChanged.emit()
            return
        self._apply_location_result(result)
        self._refresh_all()
        self.locationChanged.emit()

    @Slot()
    def useApproximateOnlineLocation(self) -> None:
        try:
            result = self._location_service.detect_ip_location(allow_online=True)
        except LocationUnavailableError as exc:
            logger.warning("Approximate online location unavailable: %s", exc.reason)
            self._location_message = APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE
            self.locationChanged.emit()
            return
        self._update_startup_preferences(allow_approximate_online_location=True)
        self._apply_location_result(result)
        self._refresh_all()
        self.locationChanged.emit()

    @Slot(bool)
    def setAutoDetectLocationOnStartup(self, enabled: bool) -> None:
        self._update_startup_preferences(auto_detect_location_on_startup=enabled)
        self.locationChanged.emit()

    @Slot(bool)
    def setAllowApproximateOnlineLocation(self, enabled: bool) -> None:
        self._update_startup_preferences(allow_approximate_online_location=enabled)
        self.locationChanged.emit()

    @Slot(bool)
    def setUseWindowsLocationOnStartup(self, enabled: bool) -> None:
        self._update_startup_preferences(use_windows_location_on_startup=enabled)
        self.locationChanged.emit()

    @Slot(str, str)
    def saveEarthdataCredentials(self, username: str, password: str) -> None:
        try:
            self._earthdata_credentials_state = self._earthdata_credential_store.save(username, password)
        except (RuntimeError, ValueError) as exc:
            self._earthdata_credentials_state = self._earthdata_credential_store.state()
            self._earthdata_credentials_state = replace(self._earthdata_credentials_state, message=str(exc))
        self.earthdataCredentialsChanged.emit()

    @Slot()
    def removeEarthdataCredentials(self) -> None:
        self._earthdata_credentials_state = self._earthdata_credential_store.remove()
        self.earthdataCredentialsChanged.emit()

    @Slot()
    def testEarthdataConnection(self) -> None:
        username = self._earthdata_credential_store.username()
        password = self._earthdata_credential_store.password()
        if not username or not password:
            self._earthdata_credentials_state = replace(
                self._earthdata_credential_store.state(),
                message="Salva le credenziali Earthdata prima del test.",
            )
            self.earthdataCredentialsChanged.emit()
            return
        self._earthdata_credentials_state = replace(
            self._earthdata_credentials_state,
            message="Verifica connessione Earthdata in corso...",
        )
        self.earthdataCredentialsChanged.emit()
        result = self._earthdata_connection_tester.test(username, password)
        self._earthdata_credentials_state = replace(
            self._earthdata_credential_store.state(),
            message=result.message,
        )
        self.earthdataCredentialsChanged.emit()

    @Slot()
    def runWindowsLocationDiagnostics(self) -> None:
        report = self._location_service.windows_location_diagnostics()
        self._windows_location_diagnostics = report
        logger.info("Windows location diagnostics exposed to UI: %s", report.get("providerStatus", "n/d"))
        self._location_message = "Windows location diagnostics completed. Review the report below and nightscope.log."
        self.locationChanged.emit()

    @Slot(int)
    def selectEquipmentSetup(self, index: int) -> None:
        telescopes = self._catalog_telescopes()
        if 0 <= index < len(telescopes):
            self.assignTelescopeToActiveProfile(telescopes[index].id)

    @Slot(str)
    def addEquipmentProfile(self, profile_name: str) -> None:
        clean_name = profile_name.strip()
        if not clean_name:
            self._equipment_message = "Inserisci un nome profilo."
            self.equipmentChanged.emit()
            return
        if any(profile["profile_name"].strip().lower() == clean_name.lower() for profile in self._equipment_profiles):
            self._equipment_message = "This profile already exists."
            self.equipmentChanged.emit()
            return
        self._equipment_catalog_repository.add_profile(clean_name, self._equipment_service.NAKED_EYE_ID, active=False)
        self._refresh_profiles_from_repository()
        self._profile_equipment.setdefault(self._profile_key_by_name(clean_name), {"telescope_ids": [], "eyepiece_ids": [], "barlow_ids": []})
        self._equipment_message = f"Profilo creato: {clean_name}."
        self.equipmentChanged.emit()

    @Slot(int, str)
    def renameEquipmentProfile(self, profile_id: int, profile_name: str) -> None:
        clean_name = profile_name.strip()
        if not clean_name:
            self._equipment_message = "Inserisci un nome profilo."
            self.equipmentChanged.emit()
            return
        if any(int(profile["id"]) != profile_id and profile["profile_name"].strip().lower() == clean_name.lower() for profile in self._equipment_profiles):
            self._equipment_message = "This profile already exists."
            self.equipmentChanged.emit()
            return
        self._equipment_catalog_repository.rename_profile(profile_id, clean_name)
        self._refresh_profiles_from_repository()
        self._equipment_message = f"Profilo rinominato: {clean_name}."
        self.equipmentChanged.emit()

    @Slot(int)
    def deleteEquipmentProfile(self, profile_id: int) -> None:
        if len(self._equipment_profiles) <= 1:
            self._equipment_message = "Mantieni almeno un profilo attrezzatura."
            self.equipmentChanged.emit()
            return
        self._equipment_catalog_repository.delete_profile(profile_id)
        self._profile_equipment.pop(str(profile_id), None)
        self._refresh_profiles_from_repository()
        self._equipment_message = "Profilo eliminato."
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()

    @Slot(str)
    def assignTelescopeToActiveProfile(self, telescope_id: str) -> None:
        telescope = self._find_telescope(telescope_id)
        if not telescope:
            return
        state = self._active_profile_state()
        if telescope.id not in state["telescope_ids"]:
            state["telescope_ids"].append(telescope.id)
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.assign_profile_telescope(int(profile["id"]), telescope.id)
            self._equipment_catalog_repository.update_profile_telescope(int(profile["id"]), telescope.id)
            self._refresh_profiles_from_repository()
        self._selected_telescope_index = self._index_for_telescope(telescope.id)
        self._equipment_message = self._equipment_status_message()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()
        self.selectedObjectChanged.emit()

    @Slot(str)
    def removeTelescopeFromActiveProfile(self, telescope_id: str) -> None:
        state = self._active_profile_state()
        state["telescope_ids"] = [item for item in state["telescope_ids"] if item != telescope_id]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_telescope(int(profile["id"]), telescope_id)
            replacement = state["telescope_ids"][0] if state["telescope_ids"] else self._equipment_service.NAKED_EYE_ID
            self._equipment_catalog_repository.update_profile_telescope(int(profile["id"]), replacement)
            self._refresh_profiles_from_repository()
        self._selected_telescope_index = self._initial_telescope_index()
        self._equipment_message = self._equipment_status_message()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()

    @Slot(str)
    def assignEyepieceToActiveProfile(self, eyepiece_id: str) -> None:
        if not self._find_eyepiece(eyepiece_id):
            return
        state = self._active_profile_state()
        if eyepiece_id not in state["eyepiece_ids"]:
            state["eyepiece_ids"].append(eyepiece_id)
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.assign_profile_eyepiece(int(profile["id"]), eyepiece_id)
        self._equipment_message = self._equipment_status_message()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()

    @Slot(str)
    def removeEyepieceFromActiveProfile(self, eyepiece_id: str) -> None:
        state = self._active_profile_state()
        state["eyepiece_ids"] = [item for item in state["eyepiece_ids"] if item != eyepiece_id]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_eyepiece(int(profile["id"]), eyepiece_id)
        self._equipment_message = self._equipment_status_message()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()

    @Slot(str)
    def assignBarlowToActiveProfile(self, barlow_id: str) -> None:
        if not self._find_barlow(barlow_id):
            return
        state = self._active_profile_state()
        if barlow_id not in state["barlow_ids"]:
            state["barlow_ids"].append(barlow_id)
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.assign_profile_barlow(int(profile["id"]), barlow_id)
        self._equipment_message = self._equipment_status_message()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()

    @Slot(str)
    def removeBarlowFromActiveProfile(self, barlow_id: str) -> None:
        state = self._active_profile_state()
        state["barlow_ids"] = [item for item in state["barlow_ids"] if item != barlow_id]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_barlow(int(profile["id"]), barlow_id)
        self._equipment_message = self._equipment_status_message()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()

    @Slot(float)
    def setBarlow(self, barlow: float) -> None:
        if not self.canUseEyepieces:
            self._equipment_message = "Crea o seleziona un telescopio prima di usare oculari o Barlow."
            self.equipmentChanged.emit()
            return
        self._barlow = barlow
        self.equipmentChanged.emit()

    @Slot(str, str)
    def assignEquipmentToActiveProfile(self, kind: str, item_id: str) -> None:
        if kind == "telescope":
            self.assignTelescopeToActiveProfile(item_id)
        elif kind == "eyepiece":
            self.assignEyepieceToActiveProfile(item_id)
        elif kind == "barlow":
            self.assignBarlowToActiveProfile(item_id)

    @Slot(str, str)
    def removeEquipmentFromActiveProfile(self, kind: str, item_id: str) -> None:
        if kind == "telescope":
            self.removeTelescopeFromActiveProfile(item_id)
        elif kind == "eyepiece":
            self.removeEyepieceFromActiveProfile(item_id)
        elif kind == "barlow":
            self.removeBarlowFromActiveProfile(item_id)

    @Slot(str, str, result=int)
    def equipmentUsage(self, kind: str, item_id: str) -> int:
        return self._equipment_catalog_repository.profile_usage_count(kind, item_id)

    @Slot(str, str, str, str, str, str, str)
    def addTelescopeModel(self, brand: str, name: str, optical_type: str, aperture: str, focal: str, mount: str, notes: str) -> None:
        try:
            aperture_mm = int(float(aperture.replace(",", ".")))
            focal_mm = int(float(focal.replace(",", ".")))
        except ValueError:
            self._equipment_message = "Dati telescopio non validi."
            self.equipmentChanged.emit()
            return
        ok, message = self._equipment_catalog_repository.add_telescope_model(brand, name, optical_type, aperture_mm, focal_mm, mount, notes)
        self._after_catalog_change(message, ok)

    @Slot(int, str, str, str, str, str, str, str)
    def updateTelescopeModel(self, model_id: int, brand: str, name: str, optical_type: str, aperture: str, focal: str, mount: str, notes: str) -> None:
        try:
            aperture_mm = int(float(aperture.replace(",", ".")))
            focal_mm = int(float(focal.replace(",", ".")))
        except ValueError:
            self._equipment_message = "Dati telescopio non validi."
            self.equipmentChanged.emit()
            return
        ok, message = self._equipment_catalog_repository.update_telescope_model(model_id, brand, name, optical_type, aperture_mm, focal_mm, mount, notes)
        self._after_catalog_change(message, ok)

    @Slot(int, bool)
    def deleteTelescopeModel(self, model_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_telescope_model(model_id, remove_from_profiles=force)
        self._after_catalog_change(message, ok)

    @Slot(str, str, str, str, str, str, str, str, str, str)
    def addEyepieceModel(
        self,
        brand: str,
        model: str,
        eyepiece_type: str,
        focal: str,
        min_focal: str,
        max_focal: str,
        apparent_field: str,
        barrel_size: str,
        afov_range: str,
        notes: str,
    ) -> None:
        parsed = self._parse_eyepiece_inputs(eyepiece_type, focal, min_focal, max_focal, apparent_field, afov_range)
        if not parsed:
            return
        focal_value, apparent, min_value, max_value, afov_min, afov_max = parsed
        ok, message = self._equipment_catalog_repository.add_eyepiece(
            brand,
            model,
            eyepiece_type,
            focal_value,
            apparent,
            barrel_size,
            min_focal_length_mm=min_value,
            max_focal_length_mm=max_value,
            afov_min=afov_min,
            afov_max=afov_max,
            notes=notes,
        )
        self._after_catalog_change(message, ok)

    @Slot(int, str, str, str, str, str, str, str, str, str, str)
    def updateEyepieceModel(
        self,
        eyepiece_id: int,
        brand: str,
        model: str,
        eyepiece_type: str,
        focal: str,
        min_focal: str,
        max_focal: str,
        apparent_field: str,
        barrel_size: str,
        afov_range: str,
        notes: str,
    ) -> None:
        parsed = self._parse_eyepiece_inputs(eyepiece_type, focal, min_focal, max_focal, apparent_field, afov_range)
        if not parsed:
            return
        focal_value, apparent, min_value, max_value, afov_min, afov_max = parsed
        ok, message = self._equipment_catalog_repository.update_eyepiece(
            eyepiece_id,
            brand,
            model,
            eyepiece_type,
            focal_value,
            apparent,
            barrel_size,
            min_focal_length_mm=min_value,
            max_focal_length_mm=max_value,
            afov_min=afov_min,
            afov_max=afov_max,
            notes=notes,
        )
        self._after_catalog_change(message, ok)

    @Slot(int, bool)
    def deleteEyepieceModel(self, eyepiece_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_eyepiece(eyepiece_id, remove_from_profiles=force)
        self._after_catalog_change(message, ok)

    @Slot(str, str, str, str, str)
    def addBarlowModel(self, brand: str, model: str, multiplier: str, barrel_size: str, notes: str) -> None:
        try:
            parsed_multiplier = float(multiplier.replace(",", "."))
        except ValueError:
            self._equipment_message = "Moltiplicatore Barlow non valido."
            self.equipmentChanged.emit()
            return
        ok, message = self._equipment_catalog_repository.add_barlow(brand, model, parsed_multiplier, barrel_size, notes)
        self._after_catalog_change(message, ok)

    @Slot(int, str, str, str, str, str)
    def updateBarlowModel(self, barlow_id: int, brand: str, model: str, multiplier: str, barrel_size: str, notes: str) -> None:
        try:
            parsed_multiplier = float(multiplier.replace(",", "."))
        except ValueError:
            self._equipment_message = "Moltiplicatore Barlow non valido."
            self.equipmentChanged.emit()
            return
        ok, message = self._equipment_catalog_repository.update_barlow(barlow_id, brand, model, parsed_multiplier, barrel_size, notes)
        self._after_catalog_change(message, ok)

    @Slot(int, bool)
    def deleteBarlowModel(self, barlow_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_barlow(barlow_id, remove_from_profiles=force)
        self._after_catalog_change(message, ok)

    @Slot(str, str, str)
    def addEyepiece(self, name: str, focal: str, apparent_field: str) -> None:
        self.addEyepieceModel("Custom", name, "Fixed", focal, "", "", apparent_field, "", "", "")

    @Slot(str, str, str, str)
    def addCustomEyepiece(self, name: str, focal: str, apparent_field: str, barrel_size: str) -> None:
        self.addEyepieceModel("Custom", name, "Fixed", focal, "", "", apparent_field, barrel_size, "", "")

    @Slot(str, str, str, str, str)
    def addZoomEyepiece(self, name: str, min_focal: str, max_focal: str, apparent_field: str, barrel_size: str) -> None:
        self.addEyepieceModel("Custom", name, "Zoom", max_focal, min_focal, max_focal, apparent_field, barrel_size, "", "")

    @Slot(int)
    def addCatalogEyepiece(self, catalog_id: int) -> None:
        self.assignEyepieceToActiveProfile(f"catalog-eyepiece-{catalog_id}")

    @Slot(str)
    def removeEyepiece(self, eyepiece_id: str) -> None:
        if eyepiece_id.startswith("catalog-eyepiece-"):
            self.deleteEyepieceModel(int(eyepiece_id.removeprefix("catalog-eyepiece-")), False)

    @Slot(int)
    def addCatalogBarlow(self, catalog_id: int) -> None:
        self.assignBarlowToActiveProfile(f"catalog-barlow-{catalog_id}")

    @Slot(str, str, str)
    def addBarlow(self, name: str, multiplier: str, barrel_size: str) -> None:
        self.addBarlowModel("Custom", name, multiplier, barrel_size, "")

    @Slot(str)
    def removeBarlow(self, barlow_id: str) -> None:
        if barlow_id.startswith("catalog-barlow-"):
            self.deleteBarlowModel(int(barlow_id.removeprefix("catalog-barlow-")), False)

    @Slot(str, str, str, str, str)
    def addTelescope(self, name: str, aperture: str, focal: str, optical_type: str, mount: str) -> None:
        self.addTelescopeModel("Custom", name, optical_type, aperture, focal, mount, "")

    @Slot(str, str)
    def addCatalogProfile(self, catalog_id: str, profile_name: str) -> None:
        clean_name = profile_name.strip() or "Nuovo profilo"
        self._equipment_catalog_repository.add_profile(clean_name, catalog_id, active=True)
        self._refresh_profiles_from_repository()
        self._profile_equipment = self._initial_profile_equipment()
        self._selected_telescope_index = self._initial_telescope_index()
        self._equipment_message = self._equipment_status_message()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()
        self.selectedObjectChanged.emit()

    @Slot(str)
    def addCatalogTelescope(self, catalog_id: str) -> None:
        self.assignTelescopeToActiveProfile(catalog_id)

    @Slot(str)
    def removeTelescope(self, telescope_id: str) -> None:
        if telescope_id.startswith("catalog-telescope-"):
            self.deleteTelescopeModel(int(telescope_id.removeprefix("catalog-telescope-")), False)

    @Slot(str, str, str, str, str, str)
    def updateTelescope(self, telescope_id: str, name: str, aperture: str, focal: str, optical_type: str, mount: str) -> None:
        if telescope_id.startswith("catalog-telescope-"):
            existing = self._equipment_catalog_repository.model_by_catalog_id(telescope_id)
            self.updateTelescopeModel(int(telescope_id.removeprefix("catalog-telescope-")), existing["brand"] if existing else "Custom", name, optical_type, aperture, focal, mount, "")

    @Slot(int)
    def setActiveEquipmentProfile(self, profile_id: int) -> None:
        self._equipment_catalog_repository.set_active_profile(profile_id)
        self._refresh_profiles_from_repository()
        self._selected_telescope_index = self._initial_telescope_index()
        self._equipment_message = self._equipment_status_message()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()
        self.selectedObjectChanged.emit()

    @Slot(str, str)
    def saveObservation(self, rating: str, notes: str) -> None:
        if not self._selected_object:
            return
        try:
            parsed_rating = int(rating)
        except ValueError:
            parsed_rating = 0
        parsed_rating = max(0, min(5, parsed_rating))
        location_label = self._location.city
        if self._location.country:
            location_label = f"{location_label}, {self._location.country}"
        self._observation_repository.add(
            date=datetime.now(self._zone()).isoformat(timespec="minutes"),
            object_name=self._selected_object.name,
            location=location_label,
            telescope=self._current_telescope().name,
            eyepiece=self._selected_object.best_eyepiece,
            rating=parsed_rating,
            notes=notes.strip(),
        )
        self._observation_history = self._observation_repository.recent(limit=10)
        self.observationChanged.emit()

    def _refresh_all(self) -> None:
        self._set_loading(True)
        previous_status = self._service_status
        self._service_status = previous_status if "ephemeris unavailable" in previous_status.lower() else ""
        try:
            if self._has_valid_location():
                self._refresh_astronomy()
                self._refresh_weather_and_conditions()
            else:
                self._refresh_no_location_context()
        except Exception:
            logger.exception("Unexpected refresh failure.")
            self._append_service_status("NightScope could not update all data. Existing data remains available.")
        finally:
            self._set_loading(False)

        if self._selected_object:
            self.selectObject(self._selected_object.id)
        elif self._best_object:
            self._selected_object = self._best_object
        elif self._deep_sky:
            self._selected_object = self._deep_sky[0]
        self.dataChanged.emit()
        self.weatherChanged.emit()
        self.selectedObjectChanged.emit()
        self.statusChanged.emit()

    def _refresh_no_location_context(self) -> None:
        self._solar_system_objects = []
        self._visible_planets = []
        self._deep_sky = []
        self._moon = MoonSummary(
            phase="n/d",
            illumination="n/d",
            rise_time="n/d",
            set_time="n/d",
            best_note="Configura una posizione per calcolare i dati lunari locali.",
            image="resources/images/moon.svg",
        )
        self._events = []
        self._weather_hours = []
        self._weather_status = "Configura una posizione per visualizzare il meteo."
        self._weather_summary = WeatherSummary(
            "n/d",
            0,
            "Configura una posizione per ottenere meteo e cielo locale.",
            0,
            0,
            0,
            0,
            0.0,
            "Configura una posizione per ottenere meteo e cielo locale.",
        )
        self._sky_quality = SkyQuality(0, 0.0, 0.0, "Nessuna fonte", "n/d", "n/d")
        self._seeing_transparency = SeeingTransparency("n/d", "n/d", 0, 0, "Configura una posizione.", "n/d", "n/d")
        self._advanced_scores = AdvancedObservingScores(0, 0, "n/d", "n/d", "Configura una posizione.")
        self._best_object = None
        self._night_plan = []
        self._sky_map = []
        self._notifications = []
        self._service_status = "Configura la posizione per ottenere meteo e cielo locale."

    def _refresh_astronomy(self) -> None:
        try:
            self._solar_system_objects = self._apply_equipment(self._astronomy_engine.solar_system_objects(self._location))
            self._visible_planets = [
                item for item in self._solar_system_objects if item.object_type == "Pianeta" and item.visible
            ]
            self._deep_sky = self._apply_equipment(self._astronomy_engine.recommended_deep_sky(self._location))
            self._moon = self._astronomy_engine.moon_summary(self._location)
            self._events = self._astronomy_engine.upcoming_events(self._location)
        except Exception:
            logger.exception("Astronomy refresh failed.")
            self._solar_system_objects = []
            self._visible_planets = []
            self._deep_sky = []
            self._events = []
            self._append_service_status("Astronomical data temporarily unavailable.")

    def _refresh_weather_and_conditions(self) -> None:
        if not self._has_valid_location():
            logger.warning("Weather refresh skipped because no valid location is available.")
            self._weather_hours = []
            self._weather_status = "Configura una posizione per visualizzare il meteo."
            self._weather_summary = self._score_service.weather_score(self._weather_hours, self._moon)
            return
        self._weather_hours = self._weather_service.hourly_forecast(self._location)
        self._weather_status = getattr(self._weather_service, "last_error", "") or ""
        if self._weather_status == WEATHER_UNAVAILABLE_MESSAGE:
            self._append_service_status(WEATHER_UNAVAILABLE_MESSAGE)
        self._weather_summary = self._score_service.weather_score(self._weather_hours, self._moon)
        self._sky_quality = self._light_pollution_service.sky_quality(self._location)
        self._deep_sky = self._apply_deep_sky_pollution_context(self._deep_sky)
        self._seeing_transparency = self._seeing_service.estimate(self._weather_hours, self._sky_quality)
        self._advanced_scores = self._advanced_observing_service.scores(
            self._weather_summary,
            self._seeing_transparency,
            self._sky_quality,
            self._moon,
        )
        planning_objects = self._home_visible_objects(self._visible_planets + self._deep_sky)
        planning_objects = planning_objects or self._visible_planets + self._deep_sky
        self._best_object = self._score_service.best_object(planning_objects, self._weather_summary)
        self._night_plan = self._night_planner_service.plan(
            planning_objects,
            self._weather_summary,
            self._advanced_scores,
            self._sky_quality,
            self._current_telescope(),
        )
        self._sky_map = self._sky_map_service.map_targets(self._visible_planets + self._deep_sky)
        self._notifications = self._notification_service.notifications(
            self._best_object,
            self._night_plan,
            self._events,
            self._advanced_scores,
            self._moon,
        )

    def _set_loading(self, value: bool) -> None:
        if self._is_loading == value:
            return
        self._is_loading = value
        self.statusChanged.emit()

    def _append_service_status(self, message: str) -> None:
        if not message:
            return
        if self._service_status:
            if message not in self._service_status:
                self._service_status = f"{self._service_status} {message}"
        else:
            self._service_status = message
        self.statusChanged.emit()

    def _apply_equipment_to_current_objects(self) -> None:
        selected_id = self._selected_object.id if self._selected_object else None
        self._solar_system_objects = self._apply_equipment(self._solar_system_objects)
        self._visible_planets = [item for item in self._solar_system_objects if item.object_type == "Pianeta" and item.visible]
        self._deep_sky = self._apply_equipment(self._deep_sky)
        self._deep_sky = self._apply_deep_sky_pollution_context(self._deep_sky)
        if self._weather_summary:
            planning_objects = self._home_visible_objects(self._visible_planets + self._deep_sky)
            planning_objects = planning_objects or self._visible_planets + self._deep_sky
            self._best_object = self._score_service.best_object(planning_objects, self._weather_summary)
        if self._weather_summary and self._advanced_scores and self._sky_quality:
            planning_objects = self._home_visible_objects(self._visible_planets + self._deep_sky)
            planning_objects = planning_objects or self._visible_planets + self._deep_sky
            self._night_plan = self._night_planner_service.plan(
                planning_objects,
                self._weather_summary,
                self._advanced_scores,
                self._sky_quality,
                self._current_telescope(),
            )
            self._sky_map = self._sky_map_service.map_targets(self._visible_planets + self._deep_sky)
            self._notifications = self._notification_service.notifications(
                self._best_object,
                self._night_plan,
                self._events,
                self._advanced_scores,
                self._moon,
            )
        if selected_id:
            for item in self._solar_system_objects + self._deep_sky:
                if item.id == selected_id:
                    self._selected_object = item
                    break

    def _apply_location_result(self, result: LocationDetectionResult, persist: bool = True) -> None:
        self._location_detection_result = result
        self._location = result.location
        self._location_message = result.message
        self._offer_online_location_fallback = False
        if persist:
            self._location_preferences.save_location(result)

    def _has_valid_location(self) -> bool:
        location = self._location
        if not isinstance(location, ObserverLocation):
            return False
        return -90 <= location.latitude <= 90 and -180 <= location.longitude <= 180

    def _initialize_startup_location(self) -> None:
        preferences = self._startup_location_preferences
        if preferences.auto_detect_location_on_startup:
            if preferences.use_windows_location_on_startup:
                try:
                    result = self._location_service.detect_windows_location()
                except LocationUnavailableError as exc:
                    logger.info("Windows startup location detection unavailable: %s", exc.reason)
                else:
                    self._apply_location_result(result)
                    return

            if preferences.allow_approximate_online_location:
                try:
                    result = self._location_service.detect_ip_location(allow_online=True)
                except LocationUnavailableError as exc:
                    logger.info("Approximate startup location detection unavailable: %s", exc.reason)
                else:
                    self._apply_location_result(result)
                    return

            if self._apply_stored_startup_location():
                return

            self._location_message = "Configura una posizione per ottenere meteo e cielo locale."
        elif self._apply_stored_startup_location():
            return

        self._location_detection_result = None
        self._location = None

    def _apply_stored_startup_location(self) -> bool:
        saved = self._location_preferences.saved_location()
        if saved and self._result_has_valid_location(saved):
            self._apply_location_result(saved, persist=False)
            self._location_message = f"Posizione salvata caricata: {saved.location.city}."
            return True

        cached = self._location_preferences.cached_location()
        if cached and self._result_has_valid_location(cached):
            self._apply_location_result(cached, persist=False)
            self._location_message = f"Ultima posizione caricata: {cached.location.city}."
            return True

        return False

    @staticmethod
    def _result_has_valid_location(result: LocationDetectionResult | None) -> bool:
        if not result:
            return False
        location = result.location
        return bool(
            location.timezone
            and -90 <= location.latitude <= 90
            and -180 <= location.longitude <= 180
        )

    def _update_startup_preferences(
        self,
        *,
        auto_detect_location_on_startup: bool | None = None,
        allow_approximate_online_location: bool | None = None,
        use_windows_location_on_startup: bool | None = None,
    ) -> None:
        self._startup_location_preferences = self._location_preferences.update_preferences(
            auto_detect_location_on_startup=auto_detect_location_on_startup,
            allow_approximate_online_location=allow_approximate_online_location,
            use_windows_location_on_startup=use_windows_location_on_startup,
        )

    def _recent_locations(self) -> list[dict]:
        return [result.to_qml() for result in self._recent_location_results()]

    def _recent_location_results(self) -> list[LocationDetectionResult]:
        candidates: list[LocationDetectionResult] = []
        if self._location_detection_result and self._result_has_valid_location(self._location_detection_result):
            candidates.append(self._location_detection_result)
        saved = self._location_preferences.saved_location()
        if saved and self._result_has_valid_location(saved):
            candidates.append(saved)
        cached = self._location_preferences.cached_location()
        if cached and self._result_has_valid_location(cached):
            candidates.append(cached)
        unique = []
        seen = set()
        for result in candidates:
            key = (
                result.location.city,
                result.location.country,
                round(result.location.latitude, 3),
                round(result.location.longitude, 3),
                result.location.timezone,
            )
            if key in seen:
                continue
            seen.add(key)
            unique.append(result)
        return unique[:5]

    @staticmethod
    def _location_source_label(provider: str) -> str:
        labels = {
            "windows_precise": "Windows precise",
            "windows_coarse": "Windows approximate",
            "ip_geolocation": "Approximate online",
            "manual_city": "Manual city",
            "manual_coordinates": "Manual coordinates",
            "cached": "Cached location",
        }
        return labels.get(provider, provider or "Nessuna posizione")

    def _apply_equipment(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        telescope = self._current_telescope()
        eyepieces = self._active_profile_eyepieces()
        barlows = self._active_profile_barlows()
        updated = []
        for item in objects:
            suggestion = self._equipment_service.suggest_for_object(item, telescope, eyepieces, barlows)
            naked_eye_blocked = (
                not self._equipment_service.has_optical_telescope(telescope)
                and suggestion["setupText"].startswith("Serve almeno")
            )
            updated.append(
                self._apply_object_content(
                    replace(
                        item,
                        visible=item.visible and not naked_eye_blocked,
                        score=max(0, item.score - 45) if naked_eye_blocked else item.score,
                        recommended_setup=suggestion["setupText"],
                        best_eyepiece=suggestion["bestEyepiece"],
                        barlow=suggestion["barlow"],
                        difficulty=suggestion["difficulty"],
                        setup_options=suggestion.get("setupOptions", []),
                        equipment_explanation=suggestion.get("explanation", ""),
                    )
                )
            )
        return updated

    def _apply_object_content(self, item: CelestialObject) -> CelestialObject:
        image = self._object_image_map.get(item.id)
        description = self._object_descriptions.get(item.id)
        if not image and item.id.startswith("messier-"):
            if "galaxy" in item.object_type.lower() or "galassia" in item.object_type.lower():
                image = self._object_image_map.get("messier-default-galaxy")
            elif "nebula" in item.object_type.lower() or "nebul" in item.object_type.lower():
                image = self._object_image_map.get("messier-default-nebula")
            else:
                image = self._object_image_map.get("messier-default-cluster")
        notes = item.notes
        if description:
            notes = f"{description['observing_notes']} {item.notes}".strip()
        return replace(
            item,
            image=image["image_path"] if image else item.image,
            notes=notes,
        )

    def _apply_deep_sky_pollution_context(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        if not self._sky_quality or self._sky_quality.bortle_class < 8:
            return objects
        updated = []
        for item in objects:
            lower_type = item.object_type.lower()
            penalty = 8
            if "galaxy" in lower_type:
                penalty = 34
            elif "nebula" in lower_type and "cluster" not in lower_type:
                penalty = 26
            elif "globular" in lower_type:
                penalty = 14
            elif "open" in lower_type or "cluster" in lower_type:
                penalty = 6
            try:
                magnitude = float(item.magnitude)
            except ValueError:
                magnitude = 10.0
            if magnitude >= 8.5:
                penalty += 12
            score = max(0, item.score - penalty)
            note = item.notes
            urban_note = "Cielo urbano: visibilita limitata, serve trasparenza buona e schermare luci dirette."
            if urban_note not in note:
                note = f"{urban_note} {note}"
            updated.append(
                replace(
                    item,
                    score=score,
                    score_label=self._score_service.score_label(score),
                    visible=item.visible and score > 10,
                    notes=note,
                )
            )
        return sorted([item for item in updated if item.visible], key=lambda item: item.score, reverse=True)[:10]

    @staticmethod
    def _home_visible_objects(objects: list[CelestialObject]) -> list[CelestialObject]:
        return [item for item in objects if AppController._first_useful_time(item.best_time) or AppController._first_useful_time(item.observing_window)]

    def _object_to_qml(self, item: CelestialObject) -> dict:
        data = item.to_qml()
        data["homeTimeLabel"] = self._home_time_label(item)
        data["homeWindowLabel"] = self._home_window_label(item)
        status, detail = self._observing_status(item)
        data["observingStatus"] = status
        data["observingStatusDetail"] = detail
        data["observingReasons"] = self._observing_reasons(item)
        return data

    def _event_to_qml(self, event: AstronomicalEvent) -> dict:
        data = event.to_qml()
        data["setup"] = self._calendar_event_setup(event)
        return data

    def _calendar_event_setup(self, event: AstronomicalEvent) -> str:
        event_type = event.event_type.strip().lower()
        title = event.title.strip().lower()
        if event_type == "sciame meteorico":
            return "Occhio nudo"
        if event_type == "luna":
            return self._calendar_moon_setup(title)
        if event_type == "eclissi":
            return "Occhio nudo; profilo attivo per dettagli lunari"
        if event_type == "congiunzione":
            target = self._calendar_event_target(event)
            if target:
                setup = self._calendar_profile_setup(target, event.setup)
                if setup != "Bassa priorita osservativa":
                    return f"Bassa priorita: {setup}"
            return "Bassa priorita osservativa"
        if event_type in {"opposizione", "pianeti"}:
            target = self._calendar_event_target(event)
            if target:
                return self._calendar_profile_setup(target, event.setup)
        return self._calendar_clean_setup(event.setup)

    def _calendar_moon_setup(self, title: str) -> str:
        if "nuova" in title:
            return "Finestra deep-sky"
        target = CelestialObject(
            id="moon",
            name="Luna",
            object_type="Luna",
            image="resources/images/moon.svg",
            magnitude="-12.0",
            distance="384.000 km",
            max_altitude="45 gradi",
            direction="Sud",
            best_time="22:00",
            observing_window="Sera",
            notes="",
            recommended_setup="",
            visibility_class="Luna",
            azimuth="180 gradi",
            time_above_horizon="n/d",
            apparent_size="30 arcmin",
            score=70,
        )
        return self._calendar_profile_setup(target, "Osservazione lunare")

    def _calendar_event_target(self, event: AstronomicalEvent) -> CelestialObject | None:
        bodies = {
            "mercury": ("Mercurio", "-0.2"),
            "mercurio": ("Mercurio", "-0.2"),
            "venus": ("Venere", "-4.0"),
            "venere": ("Venere", "-4.0"),
            "mars": ("Marte", "-1.2"),
            "marte": ("Marte", "-1.2"),
            "jupiter": ("Giove", "-2.3"),
            "giove": ("Giove", "-2.3"),
            "saturn": ("Saturno", "0.7"),
            "saturno": ("Saturno", "0.7"),
            "uranus": ("Urano", "5.7"),
            "urano": ("Urano", "5.7"),
            "neptune": ("Nettuno", "7.8"),
            "nettuno": ("Nettuno", "7.8"),
        }
        search_text = f"{event.id} {event.title}".lower()
        for token, (name, magnitude) in bodies.items():
            if token in search_text:
                object_id = {
                    "mercurio": "mercury",
                    "venere": "venus",
                    "marte": "mars",
                    "giove": "jupiter",
                    "saturno": "saturn",
                    "urano": "uranus",
                    "nettuno": "neptune",
                }.get(token, token)
                return CelestialObject(
                    id=object_id,
                    name=name,
                    object_type="Pianeta",
                    image=f"resources/images/{object_id}.svg",
                    magnitude=magnitude,
                    distance="n/d",
                    max_altitude="45 gradi",
                    direction="Sud",
                    best_time=event.best_time,
                    observing_window=event.best_time,
                    notes=event.note,
                    recommended_setup="",
                    visibility_class="Pianeta",
                    azimuth="180 gradi",
                    time_above_horizon="n/d",
                    score=event.usefulness,
                )
        return None

    def _calendar_profile_setup(self, target: CelestialObject, fallback: str) -> str:
        telescope = self._current_telescope()
        if not self._equipment_service.has_optical_telescope(telescope):
            return self._calendar_clean_setup(fallback)

        suggestion = self._equipment_service.suggest_for_object(
            target,
            telescope,
            self._active_profile_eyepieces(),
            self._active_profile_barlows(),
        )
        setup_text = suggestion.get("setupText", "").strip()
        if not setup_text:
            return telescope.name
        if setup_text.startswith("Serve almeno"):
            return telescope.name
        if setup_text.startswith("Aggiungi oculari"):
            return f"{telescope.name}: aggiungi oculari"
        return f"{telescope.name} + {setup_text}"

    @staticmethod
    def _calendar_clean_setup(setup: str) -> str:
        clean = setup.strip()
        if clean == "Qualsiasi setup":
            return "Nota osservativa"
        if clean == "Telescopio medio":
            return "Telescopio consigliato"
        if clean == "Non prioritario":
            return "Bassa priorita osservativa"
        return clean

    def _observing_status(self, item: CelestialObject) -> tuple[str, str]:
        current_altitude = self._parse_degrees(item.current_altitude)
        useful_time = self._first_useful_time(item.best_time) or self._first_useful_time(item.observing_window)
        window = self._home_window_label(item)
        if current_altitude is not None and current_altitude >= 10:
            return "Visible now", f"Attualmente a {current_altitude:.0f} gradi. Finestra migliore: {window}."
        if useful_time:
            label = self._format_home_time(*useful_time)
            if useful_time[0] <= 5:
                return "Best before dawn", f"Attualmente sotto orizzonte o basso. Migliore prima dell'alba: {window}."
            if useful_time[0] >= 20:
                return "Visible later tonight", f"Non prioritario ora. Migliore piu tardi: {window}."
            return "Best after sunset", f"Finestra utile dopo il tramonto: {label}."
        if item.visible:
            return "Visible later tonight", f"Finestra osservativa: {item.observing_window}."
        return "Below horizon", "Nessuna finestra notturna utile per questa posizione."

    def _observing_reasons(self, item: CelestialObject) -> list[str]:
        reasons = []
        max_altitude = self._parse_degrees(item.max_altitude)
        if max_altitude is not None and max_altitude > 0:
            reasons.append(f"Raggiunge {max_altitude:.0f} gradi di altezza massima")
        if item.time_above_horizon and item.time_above_horizon != "n/d":
            reasons.append(f"Resta sopra soglia per {item.time_above_horizon}")
        if self._seeing_transparency and item.object_type == "Pianeta":
            reasons.append(f"Seeing previsto: {self._seeing_transparency.seeing}")
        if self._sky_quality and item.object_type != "Pianeta":
            reasons.append(f"Compatibile con Bortle {self._sky_quality.bortle_class}: {item.difficulty}")
        if item.equipment_explanation:
            reasons.append(item.equipment_explanation)
        elif item.recommended_setup:
            reasons.append(f"Setup consigliato: {item.recommended_setup}")
        return reasons[:4]

    def _weather_digest(self) -> dict:
        night_hours = self._home_weather_hours(self._weather_hours)
        if not night_hours:
            return {
                "bestWindow": "n/d",
                "cloudAverage": 0,
                "windLabel": "n/d",
                "rainProbability": 0,
                "bestHours": [],
            }
        average_cloud = round(sum(hour.cloud_cover for hour in night_hours) / len(night_hours))
        max_rain = max(hour.precipitation_probability for hour in night_hours)
        average_wind = round(sum(hour.wind_kmh for hour in night_hours) / len(night_hours))
        best_hours = self._best_weather_hours(night_hours)
        return {
            "bestWindow": self._weather_window_label(best_hours),
            "cloudAverage": average_cloud,
            "windLabel": self._wind_label(average_wind),
            "rainProbability": max_rain,
            "bestHours": [
                {
                    "time": hour.time,
                    "cloudCover": hour.cloud_cover,
                    "windKmh": hour.wind_kmh,
                    "rainProbability": hour.precipitation_probability,
                }
                for hour in self._selected_weather_hours(night_hours)
            ],
        }

    @staticmethod
    def _home_weather_hours(hours: list[WeatherHour]) -> list[WeatherHour]:
        selected = []
        for hour in hours:
            parsed = AppController._parse_hour_minute(hour.time)
            if parsed and AppController._is_home_observing_time(*parsed):
                selected.append(hour)
        return selected or hours[:6]

    @staticmethod
    def _best_weather_hours(hours: list[WeatherHour]) -> list[WeatherHour]:
        if len(hours) <= 3:
            return hours
        best_slice = hours[:3]
        best_score = AppController._weather_slice_score(best_slice)
        for index in range(1, len(hours) - 2):
            candidate = hours[index : index + 3]
            score = AppController._weather_slice_score(candidate)
            if score < best_score:
                best_score = score
                best_slice = candidate
        return best_slice

    @staticmethod
    def _weather_slice_score(hours: list[WeatherHour]) -> float:
        cloud = sum(hour.cloud_cover for hour in hours) / len(hours)
        rain = max(hour.precipitation_probability for hour in hours)
        wind = sum(hour.wind_kmh for hour in hours) / len(hours)
        return cloud + rain * 1.3 + max(0.0, wind - 10.0) * 1.8

    @staticmethod
    def _selected_weather_hours(hours: list[WeatherHour]) -> list[WeatherHour]:
        preferred = [20, 22, 0, 2, 4]
        selected = []
        for target in preferred:
            match = next((hour for hour in hours if AppController._parse_hour_minute(hour.time) and AppController._parse_hour_minute(hour.time)[0] == target), None)
            if match and match not in selected:
                selected.append(match)
        return selected or hours[:5]

    @staticmethod
    def _weather_window_label(hours: list[WeatherHour]) -> str:
        if not hours:
            return "n/d"
        start = hours[0].time
        parsed_end = AppController._parse_hour_minute(hours[-1].time)
        if not parsed_end:
            return start
        end_dt = datetime(2000, 1, 1, parsed_end[0], parsed_end[1]) + timedelta(hours=1)
        return f"{start} - {end_dt.strftime('%H:%M')}"

    @staticmethod
    def _wind_label(wind_kmh: int) -> str:
        if wind_kmh <= 12:
            return "debole"
        if wind_kmh <= 24:
            return "moderato"
        return "sostenuto"

    @staticmethod
    def _home_time_label(item: CelestialObject) -> str:
        useful_best = AppController._first_useful_time(item.best_time)
        if useful_best:
            return AppController._format_home_time(*useful_best)
        useful_window = AppController._first_useful_time(item.observing_window)
        if useful_window:
            return AppController._format_home_time(*useful_window)
        return "Non in finestra notturna"

    @staticmethod
    def _home_window_label(item: CelestialObject) -> str:
        times = AppController._all_times(item.observing_window)
        useful_times = [time_value for time_value in times if AppController._is_home_observing_time(*time_value)]
        if len(useful_times) >= 2:
            return f"{AppController._format_clock(*useful_times[0])} - {AppController._format_clock(*useful_times[-1])}"
        if useful_times:
            return AppController._format_home_time(*useful_times[0])
        return item.observing_window

    @staticmethod
    def _first_useful_time(value: str) -> tuple[int, int] | None:
        for hour, minute in AppController._all_times(value):
            if AppController._is_home_observing_time(hour, minute):
                return hour, minute
        return None

    @staticmethod
    def _all_times(value: str) -> list[tuple[int, int]]:
        return [
            (int(hour), int(minute))
            for hour, minute in re.findall(r"\b([0-2]?\d):([0-5]\d)\b", value or "")
            if 0 <= int(hour) <= 23
        ]

    @staticmethod
    def _parse_hour_minute(value: str) -> tuple[int, int] | None:
        match = re.search(r"\b([0-2]?\d):([0-5]\d)\b", value or "")
        if not match:
            return None
        hour = int(match.group(1))
        minute = int(match.group(2))
        if hour > 23:
            return None
        return hour, minute

    @staticmethod
    def _parse_degrees(value: str) -> float | None:
        match = re.search(r"-?\d+(?:[\.,]\d+)?", value or "")
        if not match:
            return None
        try:
            return float(match.group(0).replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _parse_event_date(value: str, now: datetime) -> datetime | None:
        for fmt in ("%d/%m/%Y", "%d/%m"):
            try:
                parsed = datetime.strptime(value, fmt)
            except ValueError:
                continue
            year = parsed.year if "%Y" in fmt else now.year
            candidate = datetime(year, parsed.month, parsed.day, tzinfo=now.tzinfo)
            if candidate < now - timedelta(days=1) and "%Y" not in fmt:
                candidate = datetime(now.year + 1, parsed.month, parsed.day, tzinfo=now.tzinfo)
            return candidate
        return None

    @staticmethod
    def _is_home_observing_time(hour: int, minute: int) -> bool:
        return hour >= 20 or hour <= 5

    @staticmethod
    def _format_home_time(hour: int, minute: int) -> str:
        label = "sera"
        if 0 <= hour <= 2:
            label = "notte"
        elif 3 <= hour <= 5:
            label = "prima dell'alba"
        return f"{AppController._format_clock(hour, minute)} {label}"

    @staticmethod
    def _format_clock(hour: int, minute: int) -> str:
        return f"{hour:02d}:{minute:02d}"

    def _current_telescope(self) -> Telescope:
        for telescope in self._active_profile_telescopes():
            return telescope
        return self._equipment_service.naked_eye_telescope()

    def _initial_telescopes(self) -> list[Telescope]:
        return [self._equipment_service.naked_eye_telescope(), *self._catalog_telescopes()]

    def _initial_telescope_index(self) -> int:
        current = self._current_telescope()
        return self._index_for_telescope(current.id)

    def _telescope_from_profile(self, profile: dict, existing_telescopes: list[Telescope]) -> Telescope | None:
        telescope_id = profile["telescope_id"]
        if telescope_id == "preset:naked-eye":
            return self._equipment_service.naked_eye_telescope()
        if telescope_id == "preset:binoculars":
            return Telescope("preset:binoculars", "Binocolo 10x50", 50, 500, "Binocolo", "manuale")
        if telescope_id.startswith("custom-"):
            for telescope in existing_telescopes:
                if telescope.id == telescope_id:
                    return telescope
            return None
        model = self._equipment_catalog_repository.model_by_catalog_id(telescope_id)
        return self._telescope_from_catalog_model(model) if model else None

    @staticmethod
    def _telescope_from_catalog_model(model: dict) -> Telescope:
        return Telescope(
            id=model["catalog_id"],
            name=f"{model['brand']} {model['name']}",
            aperture_mm=int(model["aperture_mm"]),
            focal_length_mm=int(model["focal_length_mm"]),
            optical_type=model["optical_type"],
            mount=model["mount_type"],
        )

    def _refresh_equipment_catalogs(self) -> None:
        self._telescope_brands = self._equipment_catalog_repository.brands()
        self._telescope_catalog_models = self._equipment_catalog_repository.models()
        self._catalog_eyepieces = self._equipment_catalog_repository.eyepieces()
        self._catalog_barlows = self._equipment_catalog_repository.barlows()
        self._telescopes = self._initial_telescopes()
        self._eyepieces = [self._eyepiece_from_catalog_row(row) for row in self._catalog_eyepieces]
        self._barlows = [self._barlow_from_catalog_row(row) for row in self._catalog_barlows]
        self._profile_equipment = self._initial_profile_equipment()
        self._selected_telescope_index = self._initial_telescope_index()

    def _after_catalog_change(self, message: str, ok: bool) -> None:
        self._equipment_message = message
        if ok:
            self._refresh_equipment_catalogs()
            self._apply_equipment_to_current_objects()
            self.dataChanged.emit()
            self.selectedObjectChanged.emit()
        self.equipmentChanged.emit()

    def _parse_eyepiece_inputs(
        self,
        eyepiece_type: str,
        focal: str,
        min_focal: str,
        max_focal: str,
        apparent_field: str,
        afov_range: str,
    ) -> tuple[float, float, float | None, float | None, float | None, float | None] | None:
        try:
            apparent = float(apparent_field.replace(",", "."))
            if eyepiece_type == "Zoom":
                min_value = float(min_focal.replace(",", "."))
                max_value = float(max_focal.replace(",", "."))
                focal_value = max_value
                if min_value <= 0 or max_value <= 0 or min_value >= max_value:
                    raise ValueError
            else:
                focal_value = float(focal.replace(",", "."))
                min_value = None
                max_value = None
        except ValueError:
            self._equipment_message = "Dati oculare non validi."
            self.equipmentChanged.emit()
            return None
        afov_min = None
        afov_max = None
        if afov_range.strip():
            parts = [part.strip() for part in afov_range.replace(",", ".").replace("-", " ").split() if part.strip()]
            if len(parts) >= 2:
                try:
                    afov_min = float(parts[0])
                    afov_max = float(parts[1])
                except ValueError:
                    afov_min = None
                    afov_max = None
        if focal_value <= 0 or apparent <= 0:
            self._equipment_message = "Focale e campo apparente devono essere maggiori di zero."
            self.equipmentChanged.emit()
            return None
        return focal_value, apparent, min_value, max_value, afov_min, afov_max

    def _catalog_telescopes(self) -> list[Telescope]:
        return [self._telescope_from_catalog_model(model) for model in self._telescope_catalog_models]

    @staticmethod
    def _eyepiece_from_catalog_row(row: dict) -> Eyepiece:
        return Eyepiece(
            id=row["catalog_id"],
            name=f"{row['brand']} {row['model']}",
            focal_length_mm=float(row.get("focal_length_mm") or row.get("max_focal_length_mm") or 0),
            apparent_field_deg=float(row["apparent_field_deg"]),
            barrel_size=str(row.get("barrel_size") or ""),
            eyepiece_type=str(row.get("eyepiece_type") or row.get("type") or "Fixed"),
            min_focal_length_mm=float(row["min_focal_length_mm"]) if row.get("min_focal_length_mm") else None,
            max_focal_length_mm=float(row["max_focal_length_mm"]) if row.get("max_focal_length_mm") else None,
        )

    @staticmethod
    def _barlow_from_catalog_row(row: dict) -> Barlow:
        return Barlow(
            id=row["catalog_id"],
            name=f"{row['brand']} {row['model']} {float(row['multiplier']):g}x",
            multiplier=float(row["multiplier"]),
            barrel_size=str(row.get("barrel_size") or ""),
        )

    def _initial_profile_equipment(self) -> dict[str, dict[str, list[str]]]:
        equipment: dict[str, dict[str, list[str]]] = {}
        for profile in self._equipment_profiles:
            profile_id = int(profile["id"])
            telescope_ids = [
                self._normalize_telescope_catalog_id(telescope_id)
                for telescope_id in self._equipment_catalog_repository.profile_telescope_ids(profile_id)
            ]
            telescope_ids = [telescope_id for telescope_id in telescope_ids if telescope_id]
            legacy_telescope_id = profile.get("telescope_id") or self._equipment_service.NAKED_EYE_ID
            normalized_legacy_id = self._normalize_telescope_catalog_id(legacy_telescope_id)
            if normalized_legacy_id and normalized_legacy_id != self._equipment_service.NAKED_EYE_ID and normalized_legacy_id not in telescope_ids:
                telescope_ids.append(normalized_legacy_id)
                self._equipment_catalog_repository.assign_profile_telescope(profile_id, normalized_legacy_id)
                self._equipment_catalog_repository.update_profile_telescope(profile_id, normalized_legacy_id)
            equipment[str(profile_id)] = {
                "telescope_ids": telescope_ids,
                "eyepiece_ids": self._equipment_catalog_repository.profile_eyepiece_ids(profile_id),
                "barlow_ids": self._equipment_catalog_repository.profile_barlow_ids(profile_id),
            }
        return equipment

    def _refresh_profiles_from_repository(self) -> None:
        self._equipment_profiles = self._equipment_catalog_repository.profiles()
        for profile in self._equipment_profiles:
            self._profile_equipment.setdefault(
                str(profile["id"]),
                {"telescope_ids": [], "eyepiece_ids": [], "barlow_ids": []},
            )

    def _active_profile(self) -> dict | None:
        return next((profile for profile in self._equipment_profiles if int(profile.get("active", 0)) == 1), None)

    def _active_profile_state(self) -> dict[str, list[str]]:
        profile = self._active_profile()
        if not profile:
            return {"telescope_ids": [], "eyepiece_ids": [], "barlow_ids": []}
        return self._profile_equipment.setdefault(
            str(profile["id"]),
            {"telescope_ids": [], "eyepiece_ids": [], "barlow_ids": []},
        )

    def _profile_key_by_name(self, profile_name: str) -> str:
        for profile in self._equipment_profiles:
            if profile["profile_name"].strip().lower() == profile_name.strip().lower():
                return str(profile["id"])
        return profile_name.strip().lower()

    def _owned_telescopes(self) -> list[Telescope]:
        return self._catalog_telescopes()

    def _active_profile_telescopes(self) -> list[Telescope]:
        state = self._active_profile_state()
        telescopes = [telescope for telescope_id in state["telescope_ids"] if (telescope := self._find_telescope(telescope_id))]
        return telescopes

    def _active_profile_eyepieces(self) -> list[Eyepiece]:
        state = self._active_profile_state()
        return [eyepiece for eyepiece_id in state["eyepiece_ids"] if (eyepiece := self._find_eyepiece(eyepiece_id))]

    def _active_profile_barlows(self) -> list[Barlow]:
        state = self._active_profile_state()
        return [barlow for barlow_id in state["barlow_ids"] if (barlow := self._find_barlow(barlow_id))]

    def _find_telescope(self, telescope_id: str) -> Telescope | None:
        return next((telescope for telescope in self._telescopes if telescope.id == telescope_id), None)

    def _find_eyepiece(self, eyepiece_id: str) -> Eyepiece | None:
        return next((eyepiece for eyepiece in self._eyepieces if eyepiece.id == eyepiece_id), None)

    def _find_barlow(self, barlow_id: str) -> Barlow | None:
        return next((barlow for barlow in self._barlows if barlow.id == barlow_id), None)

    def _index_for_telescope(self, telescope_id: str) -> int:
        for index, telescope in enumerate(self._telescopes):
            if telescope.id == telescope_id:
                return index
        return 0

    def _normalize_telescope_catalog_id(self, telescope_id: str) -> str:
        if not telescope_id or telescope_id == self._equipment_service.NAKED_EYE_ID:
            return self._equipment_service.NAKED_EYE_ID
        if telescope_id.startswith("catalog-telescope-"):
            return telescope_id
        model = self._equipment_catalog_repository.model_by_catalog_id(telescope_id)
        return model["catalog_id"] if model else ""

    def _equipment_catalog_items(self) -> list[dict]:
        items = []
        for telescope in self._catalog_telescopes():
            items.append(
                {
                    "kind": "telescope",
                    "id": telescope.id,
                    "name": telescope.name,
                    "badge": "Telescopio",
                    "details": f"{telescope.aperture_mm} mm / {telescope.focal_length_mm} mm",
                    "type": telescope.optical_type,
                }
            )
        for eyepiece in self._eyepieces:
            badge = "Zoom" if eyepiece.eyepiece_type == "Zoom" else "Oculare"
            items.append(
                {
                    "kind": "eyepiece",
                    "id": eyepiece.id,
                    "name": eyepiece.name,
                    "badge": badge,
                    "details": eyepiece.to_qml()["focalRangeLabel"],
                    "type": eyepiece.eyepiece_type,
                }
            )
        for barlow in self._barlows:
            items.append(
                {
                    "kind": "barlow",
                    "id": barlow.id,
                    "name": barlow.name,
                    "badge": "Barlow",
                    "details": f"{barlow.multiplier:g}x",
                    "type": "Barlow",
                }
            )
        return items

    def _profile_assigned_equipment(self) -> list[dict]:
        items = []
        for telescope in self._active_profile_telescopes():
            items.append(
                {
                    "kind": "telescope",
                    "id": telescope.id,
                    "name": telescope.name,
                    "badge": "Telescopio",
                    "details": f"{telescope.aperture_mm} mm / {telescope.focal_length_mm} mm",
                }
            )
        for eyepiece in self._active_profile_eyepieces():
            items.append(
                {
                    "kind": "eyepiece",
                    "id": eyepiece.id,
                    "name": eyepiece.name,
                    "badge": "Zoom" if eyepiece.eyepiece_type == "Zoom" else "Oculare",
                    "details": eyepiece.to_qml()["focalRangeLabel"],
                }
            )
        for barlow in self._active_profile_barlows():
            items.append(
                {
                    "kind": "barlow",
                    "id": barlow.id,
                    "name": barlow.name,
                    "badge": "Barlow",
                    "details": f"{barlow.multiplier:g}x",
                }
            )
        return items

    def _telescope_exists(self, telescope: Telescope, ignore_id: str = "") -> bool:
        return any(
            existing.id != ignore_id
            and existing.id != self._equipment_service.NAKED_EYE_ID
            and existing.name.strip().lower() == telescope.name.strip().lower()
            and existing.aperture_mm == telescope.aperture_mm
            and existing.focal_length_mm == telescope.focal_length_mm
            and existing.optical_type.strip().lower() == telescope.optical_type.strip().lower()
            and existing.mount.strip().lower() == telescope.mount.strip().lower()
            for existing in self._telescopes
        )

    def _eyepiece_exists(self, eyepiece: Eyepiece, ignore_id: str = "") -> bool:
        return any(
            existing.id != ignore_id
            and existing.name.strip().lower() == eyepiece.name.strip().lower()
            and round(existing.focal_length_mm, 3) == round(eyepiece.focal_length_mm, 3)
            and round(existing.apparent_field_deg, 3) == round(eyepiece.apparent_field_deg, 3)
            and existing.barrel_size.strip().lower() == eyepiece.barrel_size.strip().lower()
            and existing.eyepiece_type == eyepiece.eyepiece_type
            and round(existing.min_focal_length_mm or 0.0, 3) == round(eyepiece.min_focal_length_mm or 0.0, 3)
            and round(existing.max_focal_length_mm or 0.0, 3) == round(eyepiece.max_focal_length_mm or 0.0, 3)
            for existing in self._eyepieces
        )

    def _barlow_exists(self, barlow: Barlow, ignore_id: str = "") -> bool:
        return any(
            existing.id != ignore_id
            and existing.name.strip().lower() == barlow.name.strip().lower()
            and round(existing.multiplier, 3) == round(barlow.multiplier, 3)
            and existing.barrel_size.strip().lower() == barlow.barrel_size.strip().lower()
            for existing in self._barlows
        )

    @staticmethod
    def _next_custom_id(prefix: str, existing_ids: list[str]) -> str:
        highest = 0
        for item_id in existing_ids:
            if not item_id.startswith(prefix):
                continue
            try:
                highest = max(highest, int(item_id.removeprefix(prefix)))
            except ValueError:
                continue
        return f"{prefix}{highest + 1}"

    def _equipment_status_message(self) -> str:
        telescope = self._current_telescope()
        if not self._equipment_service.has_optical_telescope(telescope):
            return "Modalita Occhio nudo: configura o seleziona un telescopio per usare oculari e Barlow."
        eyepieces = self._active_profile_eyepieces()
        barlows = self._active_profile_barlows()
        if not eyepieces:
            return "Telescopio attivo senza oculari: suggerimenti limitati. Aggiungi oculari per calcoli completi."
        barlow_count = len(barlows)
        barlow_text = f"{barlow_count} Barlow" if barlow_count else "nessuna Barlow"
        return f"Profilo attivo: {telescope.name}. Oculari disponibili: {len(eyepieces)}, {barlow_text}."

    @staticmethod
    def _empty_windows_diagnostics() -> dict:
        return {
            "ok": False,
            "provider": "windows_precise",
            "providerStatus": "not run",
            "accessStatus": "not run",
            "requestAccessResult": "not run",
            "coordinatesReceived": False,
            "coordinates": {},
            "errorDetails": {},
            "thread": {},
            "winrt": {},
            "steps": [],
            "rawProviderResponse": "",
            "rawProviderError": "",
            "process": {},
        }

    def _zone(self) -> ZoneInfo:
        if not self._location:
            return ZoneInfo("UTC")
        try:
            return ZoneInfo(self._location.timezone)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    @staticmethod
    def _location_to_qml(location: ObserverLocation | None) -> dict:
        if not location:
            return {
                "city": "",
                "country": "",
                "country_code": "",
                "latitude": 0.0,
                "longitude": 0.0,
                "timezone": "",
            }
        return {
            "city": location.city,
            "country": location.country,
            "country_code": "",
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone,
        }
