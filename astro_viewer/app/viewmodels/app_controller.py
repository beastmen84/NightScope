from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.database.city_repository import CityRepository
from astro_viewer.app.database.equipment_catalog_repository import EquipmentCatalogRepository
from astro_viewer.app.database.messier_repository import MessierRepository
from astro_viewer.app.database.object_image_repository import ObjectImageRepository
from astro_viewer.app.database.observation_repository import ObservationRepository
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.database.weather_cache_repository import WeatherCacheRepository
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.light_pollution_service import LightPollutionService
from astro_viewer.app.services.location_service import (
    LocationService,
    LocationUnavailableError,
    WINDOWS_LOCATION_UNAVAILABLE_MESSAGE,
)
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.notification_service import NotificationService
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.services.seeing_service import SeeingTransparencyService
from astro_viewer.app.services.sky_map_service import SkyMapService
from astro_viewer.app.services.weather_service import OpenMeteoWeatherService


class AppController(QObject):
    dataChanged = Signal()
    selectedObjectChanged = Signal()
    locationChanged = Signal()
    weatherChanged = Signal()
    equipmentChanged = Signal()
    observationChanged = Signal()

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
        self._location_service = LocationService()
        self._astronomy_engine = SkyfieldAstronomyEngine(base_dir / "data", self._messier_repository)
        self._weather_service = OpenMeteoWeatherService(self._weather_cache_repository)
        self._equipment_service = EquipmentService()
        self._score_service = ObservingScoreService()
        self._light_pollution_service = LightPollutionService(self._sky_quality_repository)
        self._seeing_service = SeeingTransparencyService()
        self._advanced_observing_service = AdvancedObservingService()
        self._night_planner_service = NightPlannerService()
        self._sky_map_service = SkyMapService()
        self._notification_service = NotificationService()

        self._city_results = self._city_repository.list_cities(limit=12)
        self._location = self._location_service.from_city(self._city_repository.get_default())
        self._location_message = "Pronto per posizione Windows, ricerca citta o coordinate manuali."

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
        self._telescopes: list[Telescope] = self._initial_telescopes()
        self._eyepieces = self._equipment_service.default_eyepieces()
        self._selected_telescope_index = self._initial_telescope_index()
        self._barlow = 1.0

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

    @Property("QVariant", notify=locationChanged)
    def cityResults(self) -> list[dict]:
        return self._city_results

    @Property("QVariant", notify=dataChanged)
    def visiblePlanets(self) -> list[dict]:
        return [planet.to_qml() for planet in self._visible_planets]

    @Property("QVariant", notify=dataChanged)
    def solarSystemObjects(self) -> list[dict]:
        return [item.to_qml() for item in self._solar_system_objects]

    @Property("QVariant", notify=dataChanged)
    def recommendedDeepSky(self) -> list[dict]:
        return [deep_sky.to_qml() for deep_sky in self._deep_sky]

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

    @Property("QVariant", notify=dataChanged)
    def bestObjectOfNight(self) -> dict:
        return self._best_object.to_qml() if self._best_object else {}

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
        objects = self._visible_planets[:2] + self._deep_sky[:2]
        return [
            {
                "name": item.name,
                "type": item.object_type,
                "bestTime": item.best_time,
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
        self._location = self._location_service.from_city(city)
        self._location_message = f"Posizione impostata su {city['city']}, {city['country']}."
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
        self._location = self._location_service.from_manual_coordinates(
            parsed_latitude,
            parsed_longitude,
            label=clean_label,
        )
        self._location_message = f"Coordinate impostate: {parsed_latitude:.4f}, {parsed_longitude:.4f}."
        self._refresh_all()
        self.locationChanged.emit()

    @Slot()
    def useWindowsLocation(self) -> None:
        try:
            self._location = self._location_service.from_windows_location()
        except LocationUnavailableError:
            self._location_message = WINDOWS_LOCATION_UNAVAILABLE_MESSAGE
            self.locationChanged.emit()
            return
        self._location_message = "Posizione Windows acquisita."
        self._refresh_all()
        self.locationChanged.emit()

    @Slot(int)
    def selectEquipmentSetup(self, index: int) -> None:
        if 0 <= index < len(self._telescopes):
            self._selected_telescope_index = index
            self._apply_equipment_to_current_objects()
            self.equipmentChanged.emit()
            self.dataChanged.emit()
            self.selectedObjectChanged.emit()

    @Slot(float)
    def setBarlow(self, barlow: float) -> None:
        self._barlow = barlow
        self.equipmentChanged.emit()

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
        self._solar_system_objects = self._apply_equipment(self._astronomy_engine.solar_system_objects(self._location))
        self._visible_planets = [item for item in self._solar_system_objects if item.object_type == "Pianeta" and item.visible]
        self._deep_sky = self._apply_equipment(self._astronomy_engine.recommended_deep_sky(self._location))
        self._moon = self._astronomy_engine.moon_summary(self._location)
        self._events = self._astronomy_engine.upcoming_events(self._location)
        self._weather_hours = self._weather_service.hourly_forecast(self._location)
        self._weather_summary = self._score_service.weather_score(self._weather_hours, self._moon)
        self._sky_quality = self._light_pollution_service.sky_quality(self._location)
        self._seeing_transparency = self._seeing_service.estimate(self._weather_hours, self._sky_quality)
        self._advanced_scores = self._advanced_observing_service.scores(
            self._weather_summary,
            self._seeing_transparency,
            self._sky_quality,
            self._moon,
        )
        self._best_object = self._score_service.best_object(self._visible_planets + self._deep_sky, self._weather_summary)
        self._night_plan = self._night_planner_service.plan(
            self._visible_planets + self._deep_sky,
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
        if self._selected_object:
            self.selectObject(self._selected_object.id)
        elif self._best_object:
            self._selected_object = self._best_object
        elif self._deep_sky:
            self._selected_object = self._deep_sky[0]
        self.dataChanged.emit()
        self.weatherChanged.emit()
        self.selectedObjectChanged.emit()

    def _apply_equipment_to_current_objects(self) -> None:
        selected_id = self._selected_object.id if self._selected_object else None
        self._solar_system_objects = self._apply_equipment(self._solar_system_objects)
        self._visible_planets = [item for item in self._solar_system_objects if item.object_type == "Pianeta" and item.visible]
        self._deep_sky = self._apply_equipment(self._deep_sky)
        if self._weather_summary:
            self._best_object = self._score_service.best_object(self._visible_planets + self._deep_sky, self._weather_summary)
        if self._weather_summary and self._advanced_scores and self._sky_quality:
            self._night_plan = self._night_planner_service.plan(
                self._visible_planets + self._deep_sky,
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

    def _apply_equipment(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        telescope = self._current_telescope()
        updated = []
        for item in objects:
            suggestion = self._equipment_service.suggest_for_object(item, telescope, self._eyepieces)
            updated.append(
                replace(
                    item,
                    recommended_setup=suggestion["setupText"],
                    best_eyepiece=suggestion["bestEyepiece"],
                    barlow=suggestion["barlow"],
                    difficulty=suggestion["difficulty"],
                )
            )
        return updated

    def _current_telescope(self) -> Telescope:
        return self._telescopes[self._selected_telescope_index]

    def _initial_telescopes(self) -> list[Telescope]:
        telescopes = self._equipment_service.default_telescopes()
        active_profile = self._equipment_catalog_repository.active_profile()
        if active_profile:
            telescope = self._telescope_from_profile(active_profile, telescopes)
            if telescope and all(existing.id != telescope.id for existing in telescopes):
                telescopes.insert(0, telescope)
        return telescopes

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

    def _zone(self) -> ZoneInfo:
        try:
            return ZoneInfo(self._location.timezone)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    @staticmethod
    def _location_to_qml(location: ObserverLocation) -> dict:
        return {
            "city": location.city,
            "country": location.country,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone,
        }
