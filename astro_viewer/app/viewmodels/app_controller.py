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
from astro_viewer.app.models.equipment import Eyepiece, Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.weather import WeatherHour
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.light_pollution_service import LightPollutionService
from astro_viewer.app.services.location_service import (
    APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE,
    LocationDetectionResult,
    LocationService,
    LocationUnavailableError,
)
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
        self._location_service = LocationService(cache_path=base_dir / "data" / "location_cache.json")
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

        self._city_results = self._city_repository.list_cities(limit=12)
        self._location_detection_result = self._location_service.from_city_result(self._city_repository.get_default())
        self._location = self._location_detection_result.location
        self._location_message = "Pronto per posizione Windows, ricerca citta o coordinate manuali."
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
        self._selected_telescope_index = self._initial_telescope_index()
        self._eyepieces = (
            self._equipment_service.default_eyepieces()
            if self._equipment_service.can_use_eyepieces(self._current_telescope())
            else []
        )
        self._barlow = 1.0
        self._equipment_message = self._equipment_status_message()

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
        return [event.to_qml() for event in self._events]

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
        return self._selected_object.to_qml()

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
        return [telescope.to_qml() for telescope in self._telescopes]

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

    @Property("QVariant", notify=dataChanged)
    def objectImages(self) -> list[dict]:
        return self._object_images

    @Property("QVariant", notify=equipmentChanged)
    def eyepieces(self) -> list[dict]:
        return [eyepiece.to_qml() for eyepiece in self._eyepieces]

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
        return self._equipment_service.calculations(self._current_telescope(), self._eyepieces, self._barlow)

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
            self._city_results = self._city_repository.search(query, limit=20)
        else:
            self._city_results = self._city_repository.list_cities(limit=12)
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
        self._apply_location_result(result)
        self._refresh_all()
        self.locationChanged.emit()

    @Slot()
    def runWindowsLocationDiagnostics(self) -> None:
        report = self._location_service.windows_location_diagnostics()
        self._windows_location_diagnostics = report
        logger.info("Windows location diagnostics exposed to UI: %s", report.get("providerStatus", "n/d"))
        self._location_message = "Windows location diagnostics completed. Review the report below and nightscope.log."
        self.locationChanged.emit()

    @Slot(int)
    def selectEquipmentSetup(self, index: int) -> None:
        if 0 <= index < len(self._telescopes):
            self._selected_telescope_index = index
            if not self.canUseEyepieces:
                self._eyepieces = []
            elif not self._eyepieces:
                self._eyepieces = self._equipment_service.default_eyepieces()
            self._equipment_message = self._equipment_status_message()
            self._apply_equipment_to_current_objects()
            self.equipmentChanged.emit()
            self.dataChanged.emit()
            self.selectedObjectChanged.emit()

    @Slot(float)
    def setBarlow(self, barlow: float) -> None:
        if not self.canUseEyepieces:
            self._equipment_message = "Crea o seleziona un telescopio prima di usare oculari o Barlow."
            self.equipmentChanged.emit()
            return
        self._barlow = barlow
        self.equipmentChanged.emit()

    @Slot(str, str, str)
    def addEyepiece(self, name: str, focal: str, apparent_field: str) -> None:
        if not self.canUseEyepieces:
            self._equipment_message = "Crea o seleziona un telescopio prima di aggiungere oculari."
            self.equipmentChanged.emit()
            return
        try:
            focal_mm = float(focal.replace(",", "."))
            apparent_deg = float(apparent_field.replace(",", "."))
        except ValueError:
            self._equipment_message = "Dati oculare non validi."
            self.equipmentChanged.emit()
            return
        clean_name = name.strip() or f"Oculare {focal_mm:g} mm"
        if focal_mm <= 0 or apparent_deg <= 0:
            self._equipment_message = "Focale e campo apparente devono essere maggiori di zero."
            self.equipmentChanged.emit()
            return
        self._eyepieces.append(Eyepiece(f"custom-eyepiece-{len(self._eyepieces) + 1}", clean_name, focal_mm, apparent_deg))
        self._equipment_message = self._equipment_status_message()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()

    @Slot(str, str, str, str, str)
    def addTelescope(self, name: str, aperture: str, focal: str, optical_type: str, mount: str) -> None:
        clean_name = name.strip()
        try:
            aperture_mm = int(float(aperture.replace(",", ".")))
            focal_mm = int(float(focal.replace(",", ".")))
        except ValueError:
            return
        if not clean_name or aperture_mm <= 0 or focal_mm <= 0:
            return
        telescope = Telescope(
            id=f"custom-{len(self._telescopes) + 1}",
            name=clean_name,
            aperture_mm=aperture_mm,
            focal_length_mm=focal_mm,
            optical_type=optical_type,
            mount=mount.strip() or "manuale",
        )
        self._telescopes.append(telescope)
        self._selected_telescope_index = len(self._telescopes) - 1
        if not self._eyepieces:
            self._eyepieces = self._equipment_service.default_eyepieces()
        self._equipment_message = self._equipment_status_message()
        self._equipment_catalog_repository.add_profile(clean_name, telescope.id, active=True)
        self._equipment_profiles = self._equipment_catalog_repository.profiles()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()

    @Slot(str, str)
    def addCatalogProfile(self, catalog_id: str, profile_name: str) -> None:
        model = self._equipment_catalog_repository.model_by_catalog_id(catalog_id)
        if not model:
            return
        telescope = self._telescope_from_catalog_model(model)
        self._telescopes.append(telescope)
        self._selected_telescope_index = len(self._telescopes) - 1
        if not self._eyepieces:
            self._eyepieces = self._equipment_service.default_eyepieces()
        self._equipment_message = self._equipment_status_message()
        clean_name = profile_name.strip() or telescope.name
        self._equipment_catalog_repository.add_profile(clean_name, telescope.id, active=True)
        self._equipment_profiles = self._equipment_catalog_repository.profiles()
        self._apply_equipment_to_current_objects()
        self.equipmentChanged.emit()
        self.dataChanged.emit()
        self.selectedObjectChanged.emit()

    @Slot(int)
    def setActiveEquipmentProfile(self, profile_id: int) -> None:
        self._equipment_catalog_repository.set_active_profile(profile_id)
        self._equipment_profiles = self._equipment_catalog_repository.profiles()
        self._selected_telescope_index = self._initial_telescope_index()
        if self.canUseEyepieces and not self._eyepieces:
            self._eyepieces = self._equipment_service.default_eyepieces()
        if not self.canUseEyepieces:
            self._eyepieces = []
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
            self._refresh_astronomy()
            self._refresh_weather_and_conditions()
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
            self._weather_status = "Configura una posizione per verificare il meteo."
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

    def _apply_location_result(self, result: LocationDetectionResult) -> None:
        self._location_detection_result = result
        self._location = result.location
        self._location_message = result.message
        self._offer_online_location_fallback = False

    def _has_valid_location(self) -> bool:
        location = self._location
        if not isinstance(location, ObserverLocation):
            return False
        return -90 <= location.latitude <= 90 and -180 <= location.longitude <= 180

    def _apply_equipment(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        telescope = self._current_telescope()
        updated = []
        for item in objects:
            suggestion = self._equipment_service.suggest_for_object(item, telescope, self._eyepieces)
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
        return data

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
        return self._telescopes[self._selected_telescope_index]

    def _initial_telescopes(self) -> list[Telescope]:
        telescopes = self._equipment_service.default_telescopes()
        active_profile = self._equipment_catalog_repository.active_profile()
        if active_profile:
            telescope = self._telescope_from_profile(active_profile, telescopes)
            if telescope and all(existing.id != telescope.id for existing in telescopes):
                telescopes.insert(0, telescope)
        return telescopes or [self._equipment_service.naked_eye_telescope()]

    def _initial_telescope_index(self) -> int:
        active_profile = self._equipment_catalog_repository.active_profile()
        if not active_profile:
            return 0
        telescope = self._telescope_from_profile(active_profile, self._telescopes)
        if not telescope:
            return 0
        for index, existing in enumerate(self._telescopes):
            if existing.id == telescope.id:
                return index
        if all(existing.id != telescope.id for existing in self._telescopes):
            self._telescopes.insert(0, telescope)
        return 0

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

    def _equipment_status_message(self) -> str:
        telescope = self._current_telescope()
        if not self._equipment_service.has_optical_telescope(telescope):
            return "Modalita Occhio nudo: configura o seleziona un telescopio per usare oculari e Barlow."
        if not self._eyepieces:
            return "Telescopio attivo senza oculari: suggerimenti limitati. Aggiungi oculari per calcoli completi."
        return f"Profilo attivo: {telescope.name}. Oculari disponibili: {len(self._eyepieces)}."

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
                "latitude": 0.0,
                "longitude": 0.0,
                "timezone": "",
            }
        return {
            "city": location.city,
            "country": location.country,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone,
        }
