from __future__ import annotations

import logging
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock, Thread
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PySide6.QtCore import QCoreApplication, QObject, Property, QTimer, QUrl, Signal, Slot

from astro_viewer.app.astronomy.coordinates import parse_dec_degrees
from astro_viewer.app.astronomy.engine import (
    MockAstronomyEngine,
    ObserverLocation,
    ObservingNightWindow,
    TransientCalendarEventSource,
)
from astro_viewer.app.astronomy.skyfield_engine import (
    DEEP_SKY_USEFUL_ALTITUDE_DEG,
    EphemerisUnavailableError,
    SkyfieldAstronomyEngine,
)
from astro_viewer.app.database.catalogue_repository import CatalogueRepository
from astro_viewer.app.database.city_repository import CityRepository
from astro_viewer.app.database.location_repository import LocationRepository
from astro_viewer.app.database.equipment_catalog_repository import EquipmentCatalogRepository
from astro_viewer.app.database.object_image_repository import ObjectImageRepository
from astro_viewer.app.database.observation_repository import ObservationRepository
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.database.weather_cache_repository import WeatherCacheRepository
from astro_viewer.app.models.equipment import (
    Barlow,
    Binocular,
    Eyepiece,
    FocalReducer,
    OpticalFilter,
    Telescope,
)
from astro_viewer.app.models.filtering import (
    FILTER_CLASS_OPTIONS,
    SOLAR_SYSTEM_FILTER_PREFERENCES,
)
from astro_viewer.app.models.observing import (
    AstronomicalEvent,
    CelestialObject,
    MoonGeometrySummary,
    MoonSummary,
)
from astro_viewer.app.models.sky import ObservingCategoryScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import ObservingSessionDecision, WeatherBlockingStatus, WeatherHour, WeatherSummary
from astro_viewer.app.services.earthdata_credentials import (
    EARTHDATA_LAADS_AUTHORIZATION_URL,
    EarthdataConnectionTester,
    EarthdataCredentialStore,
)
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.equipment_setup_read_model import (
    EquipmentSetupReadModel,
    EquipmentSetupReadModelBuilder,
)
from astro_viewer.app.services.filter_recommendation_service import (
    FilterRecommendationService,
)
from astro_viewer.app.services.reducer_recommendation_service import (
    ReducerRecommendationService,
)
from astro_viewer.app.services.light_pollution_service import LightPollutionService, ViirsCacheState
from astro_viewer.app.services.localization import (
    content_key,
    content_text,
    format_compact_number,
    format_month_year,
    format_number,
    join_text,
    presentation_text,
    render_payload,
    render_text,
    tr,
)
from astro_viewer.app.services.location_service import (
    APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE,
    LocationDetectionResult,
    LocationService,
    LocationUnavailableError,
)
from astro_viewer.app.services.location_preferences import LocationPreferenceStore
from astro_viewer.app.services.nasa_aod_provider import NasaAodProvider, NasaAodResult
from astro_viewer.app.services.best_object_nsom_ranking import (
    BestObjectNsomSelectionService,
)
from astro_viewer.app.services.calendar_overview import CalendarOverviewService
from astro_viewer.app.services.catalogue_presentation import (
    catalogue_constellation_label,
    catalogue_display_name,
    catalogue_object_type_label,
    catalogue_observation_type_label,
)
from astro_viewer.app.services.home_nsom_ranking import (
    HomeRecommendedDeepSkyNsomRankingService,
)
from astro_viewer.app.services.home_night_plan_overview import HomeNightPlanOverviewService
from astro_viewer.app.services.home_observing_overview import (
    HomeObservingOverviewService,
    bortle_observing_warning,
)
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_category_score_service import NsomCategoryScoreService
from astro_viewer.app.services.nsom_target import unique_targets_by_id
from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    MoonGeometryConditionInput,
    ObservationConditionInputs,
    ObservationConditionsService,
    ParticulateConditionInput,
)
from astro_viewer.app.services.observation_conditions_read_model import (
    ObservationConditionedTargetReadModel,
    ObservationConditionsReadModelBuilder,
)
from astro_viewer.app.services.observation_log_service import (
    ObservationLogService,
    ObservationLogValidationError,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.services.observing_night_service import (
    consecutive_weather_groups,
    weather_hour_datetime,
    weather_hours_for_next_24,
    weather_hours_for_night,
)
from astro_viewer.app.services.observing_object_detail import ObservingObjectDetailService
from astro_viewer.app.services.openaq_atmosphere_service import LocalAtmosphere, OpenAQLocalAtmosphereService
from astro_viewer.app.services.openaq_credentials import OpenAQConnectionTester, OpenAQCredentialStore
from astro_viewer.app.services.refresh_lifecycle import RefreshDomain, RefreshManager, RefreshReason
from astro_viewer.app.services.seeing_service import SeeingTransparencyService
from astro_viewer.app.services.sky_compass_service import SkyCompassService
from astro_viewer.app.services.weather_service import WEATHER_UNAVAILABLE_MESSAGE, OpenMeteoWeatherService


logger = logging.getLogger(__name__)

CATALOGUE_ALL_FILTER = "__all__"
CATALOGUE_SOURCE = "catalogue"
OBSERVING_SOURCE = "observing"
SOLAR_SYSTEM_CATALOGUE = "Sistema Solare"
RECOMMENDATION_EDITABLE_CATALOGUES = frozenset(
    {"Messier", "Caldwell", "NGC"}
)
STARTUP_LOCATION_PENDING_MESSAGE = tr("Ricerca della posizione in corso...")
STARTUP_WEATHER_PENDING_MESSAGE = tr("Meteo in attesa della posizione.")
WEATHER_RETRY_DELAY_MS = 5 * 60 * 1000
CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG = DEEP_SKY_USEFUL_ALTITUDE_DEG
ASTRONOMY_REFRESH_FULL = "full_refresh"
ASTRONOMY_REFRESH_NIGHT_ROLLOVER = "night_rollover"
ASTRONOMY_REFRESH_VIIRS_DEEP_SKY = "viirs_deep_sky"


@dataclass(frozen=True)
class AstronomyRefreshSnapshot:
    observing_night_window: ObservingNightWindow | None = None
    solar_system_objects: tuple[CelestialObject, ...] = ()
    deep_sky: tuple[CelestialObject, ...] = ()
    moon: MoonSummary | None = None
    events: tuple[AstronomicalEvent, ...] = ()
    moon_geometry: tuple[tuple[str, MoonGeometrySummary | None], ...] = ()
    catalogue_visibility_cache_key: tuple[float, float, str, int, int, float] | None = None
    catalogue_visibility: tuple[tuple[str, bool], ...] = ()
    failed: bool = False


@dataclass(frozen=True)
class TransientEventRefreshSnapshot:
    events: tuple[AstronomicalEvent, ...] = ()
    failed: bool = False


class AppController(QObject):
    dataChanged = Signal()
    selectedObjectChanged = Signal()
    observingObjectDetailChanged = Signal()
    catalogueChanged = Signal()
    locationChanged = Signal()
    weatherChanged = Signal()
    equipmentChanged = Signal()
    observationChanged = Signal()
    skyCompassChanged = Signal()
    homeNightPlanChanged = Signal()
    statusChanged = Signal()
    earthdataCredentialsChanged = Signal()
    openaqCredentialsChanged = Signal()
    _earthdataConnectionTestFinished = Signal(bool, object, bool)
    _openaqConnectionTestFinished = Signal(bool, object)
    _viirsSkyQualityFinished = Signal(int, str, object, object)
    _startupLocationDetectionFinished = Signal(int, object, bool, object)
    _weatherRefreshFinished = Signal(int, str, object, object, bool)
    _localAtmosphereRefreshFinished = Signal(int, str, object)
    _nasaAodRefreshFinished = Signal(int, str, object)
    _skyCompassLiveRefreshFinished = Signal(int, str, object)
    _astronomyRefreshFinished = Signal(int, str, str, object, object)
    _transientEventsRefreshFinished = Signal(int, str, object)

    def __init__(
        self,
        base_dir: Path,
        database_path: Path,
        *,
        preferences_path: Path | None = None,
        location_cache_path: Path | None = None,
        nasa_aod_cache_path: Path | None = None,
        best_object_nsom_selection_service: BestObjectNsomSelectionService | None = None,
        home_recommended_deep_sky_nsom_ranking_service: HomeRecommendedDeepSkyNsomRankingService | None = None,
        nsom_category_score_service: NsomCategoryScoreService | None = None,
        sky_compass_service: SkyCompassService | None = None,
        transient_event_sources: Sequence[TransientCalendarEventSource] = (),
    ):
        super().__init__()
        self._earthdataConnectionTestFinished.connect(self._finish_earthdata_connection_test)
        self._openaqConnectionTestFinished.connect(self._finish_openaq_connection_test)
        self._viirsSkyQualityFinished.connect(self._finish_viirs_sky_quality_refresh)
        self._startupLocationDetectionFinished.connect(self._finish_startup_location_detection)
        self._weatherRefreshFinished.connect(self._finish_weather_refresh)
        self._localAtmosphereRefreshFinished.connect(self._finish_local_atmosphere_refresh)
        self._nasaAodRefreshFinished.connect(self._finish_nasa_aod_refresh)
        self._skyCompassLiveRefreshFinished.connect(self._finish_sky_compass_live_refresh)
        self._astronomyRefreshFinished.connect(self._finish_astronomy_refresh)
        self._transientEventsRefreshFinished.connect(self._finish_transient_event_refresh)
        self.dataChanged.connect(self.homeNightPlanChanged.emit)
        self.weatherChanged.connect(self.homeNightPlanChanged.emit)
        self.equipmentChanged.connect(self.homeNightPlanChanged.emit)
        self.selectedObjectChanged.connect(self.observingObjectDetailChanged.emit)
        self.weatherChanged.connect(self.observingObjectDetailChanged.emit)
        self.equipmentChanged.connect(self.observingObjectDetailChanged.emit)
        self.skyCompassChanged.connect(self.observingObjectDetailChanged.emit)
        self._base_dir = base_dir
        preferences_path = preferences_path or database_path.parent / "user_preferences.json"
        location_cache_path = location_cache_path or database_path.parent / "location_cache.json"
        nasa_aod_cache_path = nasa_aod_cache_path or database_path.parent / "nasa_aod_cache.json"
        self._city_repository = CityRepository(database_path)
        self._location_repository = LocationRepository(database_path)
        self._catalogue_repository = CatalogueRepository(database_path)
        self._equipment_catalog_repository = EquipmentCatalogRepository(database_path)
        self._sky_quality_repository = SkyQualityRepository(database_path)
        self._object_image_repository = ObjectImageRepository(database_path)
        self._weather_cache_repository = WeatherCacheRepository(database_path)
        self._observation_repository = ObservationRepository(database_path)
        self._location_preferences = LocationPreferenceStore(
            preferences_path=preferences_path,
            cache_path=location_cache_path,
        )
        self._earthdata_credential_store = EarthdataCredentialStore(
            preferences_path=preferences_path,
        )
        self._earthdata_connection_tester = EarthdataConnectionTester()
        self._earthdata_credentials_state = self._earthdata_credential_store.state()
        self._earthdata_connection_test_running = False
        self._openaq_credential_store = OpenAQCredentialStore(
            preferences_path=preferences_path,
        )
        self._openaq_connection_tester = OpenAQConnectionTester()
        self._local_atmosphere_service = OpenAQLocalAtmosphereService()
        self._openaq_credentials_state = self._openaq_credential_store.state()
        self._openaq_connection_test_running = False
        self._local_atmosphere_refresh_running = False
        self._local_atmosphere_refresh_request_id = 0
        self._nasa_aod_refresh_running = False
        self._nasa_aod_refresh_request_id = 0
        self._viirs_sky_quality_running = False
        self._viirs_sky_quality_request_id = 0
        self._light_pollution_status = ""
        self._startup_location_detection_running = False
        self._startup_location_detection_request_id = 0
        self._startup_location_preferences = self._location_preferences.preferences()
        self._location_service = LocationService(
            city_resolver=self._city_repository,
            cache_path=location_cache_path,
        )
        self._is_loading = False
        self._service_status = ""
        self._weather_status = ""
        self._weather_refresh_running = False
        self._weather_refresh_request_id = 0
        self._weather_full_refresh_request_id: int | None = None
        self._weather_retry_pending = False
        self._astronomy_engine_lock = RLock()
        self._astronomy_refresh_running = False
        self._astronomy_refresh_request_id = 0
        self._transient_event_refresh_running = False
        self._transient_event_refresh_request_id = 0
        self._transient_events_location_key = ""
        self._weather_refresh_timer = QTimer(self)
        self._weather_refresh_timer.setSingleShot(True)
        self._weather_refresh_timer.timeout.connect(self._refresh_weather_from_timer)
        self._transient_event_refresh_timer = QTimer(self)
        self._transient_event_refresh_timer.setSingleShot(True)
        self._transient_event_refresh_timer.timeout.connect(
            self._refresh_transient_events_from_timer
        )
        self._sky_compass_live_timer = QTimer(self)
        self._sky_compass_live_timer.setInterval(60_000)
        self._sky_compass_live_timer.timeout.connect(self._refresh_sky_compass_live)
        self._sky_compass_live_refresh_running = False
        self._sky_compass_live_refresh_request_id = 0
        try:
            self._astronomy_engine = SkyfieldAstronomyEngine(
                base_dir / "data",
                self._catalogue_repository,
                transient_event_sources,
            )
        except EphemerisUnavailableError:
            logger.error("Skyfield engine unavailable; using fallback astronomy data.", exc_info=True)
            self._astronomy_engine = MockAstronomyEngine()
            self._service_status = tr(
                "Effemeridi astronomiche non disponibili. Uso i dati cielo di fallback."
            )
        self._weather_service = OpenMeteoWeatherService(self._weather_cache_repository)
        self._equipment_service = EquipmentService()
        self._equipment_setup_read_model_builder = EquipmentSetupReadModelBuilder()
        self._filter_recommendation_service = FilterRecommendationService()
        self._reducer_recommendation_service = ReducerRecommendationService()
        self._score_service = ObservingScoreService()
        self._light_pollution_service = LightPollutionService(
            self._sky_quality_repository,
            data_dir=base_dir / "data",
            earthdata_credentials=self._earthdata_credential_store,
        )
        self._nasa_aod_provider = NasaAodProvider(
            self._earthdata_credential_store,
            cache_path=nasa_aod_cache_path,
        )
        self._seeing_service = SeeingTransparencyService()
        self._nsom_category_score_service = nsom_category_score_service or NsomCategoryScoreService()
        self._conditions_service = ObservationConditionsService()
        self._conditions_read_model_builder = ObservationConditionsReadModelBuilder()
        self._observation_log_service = ObservationLogService()
        self._best_object_nsom_selection_service = (
            best_object_nsom_selection_service or BestObjectNsomSelectionService()
        )
        self._home_recommended_deep_sky_nsom_ranking_service = (
            home_recommended_deep_sky_nsom_ranking_service or HomeRecommendedDeepSkyNsomRankingService()
        )
        self._home_observing_overview_service = HomeObservingOverviewService()
        self._home_night_plan_overview_service = HomeNightPlanOverviewService()
        self._calendar_overview_service = CalendarOverviewService()
        self._night_planner_service = NightPlannerService()
        self._sky_compass_service = sky_compass_service or SkyCompassService()
        self._observing_object_detail_service = ObservingObjectDetailService()
        self._refresh_manager = RefreshManager()

        self._city_results = []
        self._city_search_has_query = False
        self._location_detection_result: LocationDetectionResult | None = None
        self._location: ObserverLocation | None = None
        self._observing_night_window = ObservingNightWindow.unavailable()
        self._location_message = tr(
            "Configura una località per ottenere meteo e cielo locale."
        )
        self._offer_online_location_fallback = False

        self._visible_planets: list[CelestialObject] = []
        self._solar_system_objects: list[CelestialObject] = []
        self._deep_sky: list[CelestialObject] = []
        self._conditioned_deep_sky: list[CelestialObject] = []
        self._conditioned_home_objects: list[CelestialObject] = []
        self._conditioned_deep_sky_read_model: list[ObservationConditionedTargetReadModel] = []
        self._conditioned_home_read_model: list[ObservationConditionedTargetReadModel] = []
        self._equipment_setup_read_models_by_object_id: dict[str, EquipmentSetupReadModel] = {}
        self._deep_sky_pollution_read_model: list[ObservationConditionedTargetReadModel] = []
        self._deep_sky_raw_condition_input_by_id: dict[str, CelestialObject] = {}
        self._base_solar_system_objects: list[CelestialObject] = []
        self._base_deep_sky: list[CelestialObject] = []
        self._moon = None
        self._moon_geometry_condition_cache: dict[str, MoonGeometryConditionInput | None] = {}
        self._events = []
        self._observing_night_window = ObservingNightWindow.unavailable()
        self._weather_hours = []
        self._weather_summary = None
        self._sky_quality = None
        self._local_atmosphere = LocalAtmosphere.not_configured()
        self._nasa_aod_result = NasaAodResult.no_location()
        self._seeing_transparency = None
        self._category_scores = None
        self._night_plan = []
        self._sky_compass = SkyCompassService.empty(
            "no_location",
            tr("Configura una località per usare Sky Compass."),
        )
        self._sky_compass_candidate_snapshot: list[CelestialObject] = []
        self._selected_object: CelestialObject | None = None
        self._selected_object_source = ""
        self._best_object: CelestialObject | None = None
        self._observation_rows = self._observation_repository.list_all()
        self._observation_log = self._observation_log_service.build_entries(self._observation_rows)
        self._observation_log_summary = self._observation_log_service.build_summary(self._observation_rows)
        self._observation_message = ""

        self._beginner_presets = self._equipment_service.beginner_presets()
        self._telescope_brands = self._equipment_catalog_repository.brands()
        self._telescope_catalog_models = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.models(), "telescopes"
        )
        self._catalog_eyepieces = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.eyepieces(), "eyepieces"
        )
        self._catalog_barlows = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.barlows(), "barlows"
        )
        self._catalog_binoculars = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.binoculars(), "binoculars"
        )
        self._catalog_filters = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.filters(), "filters"
        )
        self._catalog_reducers = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.reducers(), "reducers"
        )
        self._equipment_profiles = self._equipment_catalog_repository.profiles()
        self._object_images = self._object_image_repository.all()
        self._object_image_map = {item["object_id"]: item for item in self._object_images}
        self._object_descriptions = self._localized_object_content(
            self._object_image_repository.descriptions()
        )
        self._object_curiosities = self._localized_object_content(
            self._object_image_repository.curiosities()
        )
        self._catalogue_objects = self._load_catalogue_objects()
        self._recommendation_enabled_by_object_id = {
            str(item["object_id"]).casefold(): bool(
                item.get("recommendation_enabled", True)
            )
            for item in self._catalogue_objects
        }
        self._catalogue_identifier_index = self._build_catalogue_identifier_index(
            self._catalogue_objects
        )
        self._catalogue_search_query = ""
        self._catalogue_filters = {
            "catalogue": CATALOGUE_ALL_FILTER,
            "type": CATALOGUE_ALL_FILTER,
            "constellation": CATALOGUE_ALL_FILTER,
            "observation_type": CATALOGUE_ALL_FILTER,
        }
        self._catalogue_year = self._catalogue_current_year()
        self._catalogue_selected_month = self._catalogue_current_month()
        self._catalogue_month_user_selected = False
        self._catalogue_visible_this_month_only = False
        self._catalogue_visibility_cache: dict[tuple[float, float, str, int, int, float], dict[str, bool]] = {}
        self._catalogue_current_month_visibility_cache: dict[
            tuple[float, float, str, int, int, float, str], bool | None
        ] = {}
        self._catalogue_observability_cache: dict[
            tuple[float, float, str, float],
            dict[str, dict[str, bool | None]],
        ] = {}
        self._telescopes: list[Telescope] = self._initial_telescopes()
        self._eyepieces: list[Eyepiece] = [self._eyepiece_from_catalog_row(row) for row in self._catalog_eyepieces]
        self._barlows: list[Barlow] = [self._barlow_from_catalog_row(row) for row in self._catalog_barlows]
        self._binoculars: list[Binocular] = [self._binocular_from_catalog_row(row) for row in self._catalog_binoculars]
        self._filters: list[OpticalFilter] = [
            self._filter_from_catalog_row(row) for row in self._catalog_filters
        ]
        self._reducers: list[FocalReducer] = [
            self._reducer_from_catalog_row(row) for row in self._catalog_reducers
        ]
        self._profile_equipment = self._initial_profile_equipment()
        self._selected_telescope_index = self._initial_telescope_index()
        self._barlow = 1.0
        self._equipment_message = self._equipment_status_message()

        self._refresh_manager.mark_dirty(RefreshReason.STARTUP)
        self._initialize_startup_location()
        self._align_catalogue_month_to_location()
        self._refresh_all()
        self._update_sky_compass_live_timer()

    @Property(str, constant=True)
    def assetBaseUrl(self) -> str:
        return QUrl.fromLocalFile(str(self._base_dir)).toString()

    @Property(str, constant=True)
    def manualUrl(self) -> str:
        return QUrl.fromLocalFile(str(self._base_dir.parent / "manuale.html")).toString()

    @Property("QVariant", notify=locationChanged)
    def location(self) -> dict:
        return render_payload(self._location_to_qml(self._location))

    @Property(str, notify=locationChanged)
    def locationMessage(self) -> str:
        return render_text(self._location_message)

    @Property(bool, notify=locationChanged)
    def canUseApproximateOnlineLocation(self) -> bool:
        return self._offer_online_location_fallback

    @Property("QVariant", notify=locationChanged)
    def locationDetails(self) -> dict:
        if not self._location_detection_result:
            return {}
        payload = self._location_detection_result.to_qml()
        payload["rawSource"] = payload.get("source", "")
        payload["source"] = self._location_source_label(
            self._location_detection_result.provider
        )
        payload["accuracy"] = self._location_accuracy_label(
            self._location_detection_result
        )
        return render_payload(payload)

    @Property(str, notify=locationChanged)
    def activeLocationLabel(self) -> str:
        if self._startup_location_detection_running:
            return render_text(tr("Posizione in aggiornamento"))
        if not self._has_valid_location():
            return render_text(tr("Nessuna località configurata"))
        return render_text(
            tr(
                "{city} — {timezone}",
                city=self._location.city,
                timezone=self._location.timezone,
            )
        )

    @Property(str, notify=locationChanged)
    def activeLocationSource(self) -> str:
        if self._startup_location_detection_running:
            return render_text(tr("Rilevamento automatico"))
        if not self._location_detection_result:
            return render_text(tr("Nessuna posizione"))
        return render_text(self._location_source_label(self._location_detection_result.provider))

    @Property(bool, notify=locationChanged)
    def autoDetectLocationOnStartup(self) -> bool:
        return self._startup_location_preferences.auto_detect_location_on_startup

    @Property(bool, notify=locationChanged)
    def allowApproximateOnlineLocation(self) -> bool:
        return self._startup_location_preferences.allow_approximate_online_location

    @Property(bool, notify=locationChanged)
    def useSystemLocationOnStartup(self) -> bool:
        return self._startup_location_preferences.use_system_location_on_startup

    @Property(bool, notify=locationChanged)
    def useWindowsLocationOnStartup(self) -> bool:
        return self._startup_location_preferences.use_windows_location_on_startup

    @Property(bool, notify=locationChanged)
    def startupLocationDetectionRunning(self) -> bool:
        return self._startup_location_detection_running

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
        return render_text(self._earthdata_credentials_state.message)

    @Property(bool, notify=earthdataCredentialsChanged)
    def earthdataConnectionTestRunning(self) -> bool:
        return self._earthdata_connection_test_running

    @Property(bool, notify=earthdataCredentialsChanged)
    def earthdataConnectionVerified(self) -> bool:
        return self._earthdata_credentials_state.connection_verified

    @Property(bool, notify=earthdataCredentialsChanged)
    def earthdataAuthorizationRequired(self) -> bool:
        return self._earthdata_credentials_state.authorization_required

    @Property(str, constant=True)
    def earthdataAuthorizationUrl(self) -> str:
        return EARTHDATA_LAADS_AUTHORIZATION_URL

    @Property(bool, notify=openaqCredentialsChanged)
    def openaqCredentialsConfigured(self) -> bool:
        return self._openaq_credentials_state.configured

    @Property(bool, notify=openaqCredentialsChanged)
    def openaqSecureStorageAvailable(self) -> bool:
        return self._openaq_credentials_state.secure_store_available

    @Property(str, notify=openaqCredentialsChanged)
    def openaqCredentialMessage(self) -> str:
        return render_text(self._openaq_credentials_state.message)

    @Property(bool, notify=openaqCredentialsChanged)
    def openaqConnectionTestRunning(self) -> bool:
        return self._openaq_connection_test_running

    @Property(bool, notify=openaqCredentialsChanged)
    def openaqConnectionVerified(self) -> bool:
        return self._openaq_credentials_state.connection_verified

    @Property(bool, notify=locationChanged)
    def hasValidLocation(self) -> bool:
        return self._has_valid_location()

    @Property(bool, notify=statusChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=statusChanged)
    def serviceStatus(self) -> str:
        return render_text(self._service_status)

    @Property(str, notify=weatherChanged)
    def weatherStatus(self) -> str:
        if self._weather_status == tr("Dati meteo non disponibili al momento.") and self._weather_hours:
            return ""
        return render_text(self._weather_status)

    @Property(bool, notify=weatherChanged)
    def weatherRefreshRunning(self) -> bool:
        return self._weather_refresh_running

    @Property(bool, notify=dataChanged)
    def hasVisibleObjects(self) -> bool:
        return bool(self._visible_planets or self._deep_sky)

    @Property("QVariant", notify=locationChanged)
    def locationResults(self) -> list[dict]:
        return render_payload(
            [
                {
                    **item,
                    "displayName": (
                        tr(
                            "{city}, {country}",
                            city=item["name"],
                            country=item["context"],
                        )
                        if item["kind"] == "city"
                        else item["name"]
                    ),
                    "kindLabel": (
                        tr("Città")
                        if item["kind"] == "city"
                        else tr("Osservatorio")
                    ),
                    "coordinatesLabel": tr(
                        "{latitude}, {longitude}",
                        latitude=format_number(item["latitude"], decimals=2),
                        longitude=format_number(item["longitude"], decimals=2),
                    ),
                }
                for item in self._city_results
            ]
        )

    @Property(bool, notify=locationChanged)
    def hasLocationSearchQuery(self) -> bool:
        return self._city_search_has_query

    @Property("QVariant", notify=locationChanged)
    def cityResults(self) -> list[dict]:
        return self.locationResults

    @Property(bool, notify=locationChanged)
    def hasCitySearchQuery(self) -> bool:
        return self.hasLocationSearchQuery

    @Property("QVariant", notify=locationChanged)
    def recentLocations(self) -> list[dict]:
        return self._recent_locations()

    @Property("QVariant", notify=dataChanged)
    def visiblePlanets(self) -> list[dict]:
        return render_payload(
            [self._object_to_qml(planet) for planet in self._home_visible_objects(self._visible_planets)]
        )

    @Property("QVariant", notify=dataChanged)
    def solarSystemObjects(self) -> list[dict]:
        return render_payload([item.to_qml() for item in self._solar_system_objects])

    @Property("QVariant", notify=dataChanged)
    def recommendedDeepSky(self) -> list[dict]:
        return render_payload(
            [self._object_to_qml(deep_sky) for deep_sky in self._conditioned_deep_sky_candidates()]
        )

    @Property("QVariant", notify=dataChanged)
    def homeVisibleAlternatives(self) -> list[dict]:
        return render_payload(self._home_visible_alternative_payloads())

    @Property("QVariant", notify=catalogueChanged)
    def catalogueObjects(self) -> list[dict]:
        return render_payload(self._filtered_catalogue_objects())

    @Property("QVariant", notify=catalogueChanged)
    def catalogueFilterOptions(self) -> dict:
        object_types = self._catalogue_option_values("type")
        constellations = self._catalogue_option_values("constellation")
        observation_types = self._catalogue_option_values("recommended_observation_type")
        type_choices = [
            {"value": value, "label": catalogue_object_type_label(value)}
            for value in object_types
        ]
        observation_type_choices = [
            {"value": value, "label": catalogue_observation_type_label(value)}
            for value in observation_types
        ]
        constellation_choices = [
            {"value": value, "label": catalogue_constellation_label(value)}
            for value in constellations
        ]
        catalogue_choices = [
            {"value": value, "label": self._catalogue_label(value)}
            for value in self._catalogue_option_values("catalogue")
        ]
        options = render_payload({
            "catalogues": self._catalogue_option_values("catalogue"),
            "catalogueChoices": catalogue_choices,
            "types": object_types,
            "typeChoices": type_choices,
            "constellations": constellations,
            "constellationChoices": constellation_choices,
            "observationTypes": observation_types,
            "observationTypeChoices": observation_type_choices,
        })
        for key in (
            "catalogueChoices",
            "typeChoices",
            "constellationChoices",
            "observationTypeChoices",
        ):
            options[key].sort(key=lambda item: str(item["label"]).casefold())
        return options

    @Property("QVariant", notify=catalogueChanged)
    def catalogueFilterState(self) -> dict:
        return {
            "search": self._catalogue_search_query,
            **self._catalogue_filters,
            "visible_this_month": self._catalogue_visible_this_month_only,
        }

    @Property("QVariant", notify=catalogueChanged)
    def catalogueMonthLabels(self) -> list[str]:
        return [render_text(self._catalogue_month_label(index + 1)) for index in range(12)]

    @Property(int, notify=catalogueChanged)
    def catalogueSelectedMonth(self) -> int:
        return self._catalogue_selected_month

    @Property(str, notify=catalogueChanged)
    def catalogueSelectedMonthLabel(self) -> str:
        return render_text(self._catalogue_month_label(self._catalogue_selected_month))

    @Property(bool, notify=catalogueChanged)
    def catalogueVisibleThisMonthFilter(self) -> bool:
        return self._catalogue_visible_this_month_only

    @Property(int, notify=catalogueChanged)
    def catalogueTotalCount(self) -> int:
        return len(self._catalogue_objects)

    @Property(int, notify=catalogueChanged)
    def catalogueFilteredCount(self) -> int:
        return len(self._filtered_catalogue_objects())

    @Property("QVariant", notify=dataChanged)
    def moonSummary(self) -> dict:
        return render_payload(self._moon.to_qml() if self._moon else {})

    @Property("QVariant", notify=dataChanged)
    def events(self) -> list[dict]:
        return render_payload([self._event_to_qml(event) for event in self._events])

    @Property("QVariant", notify=dataChanged)
    def calendarOverview(self) -> dict:
        assigned_equipment = self._profile_assigned_equipment()
        return render_payload(self._calendar_overview_service.build(
            events=[self._event_to_qml(event) for event in self._events],
            now=datetime.now(self._zone()),
            has_configured_equipment=any(
                str(item.get("id", "")) != "preset:naked-eye"
                for item in assigned_equipment
            ),
        ))

    @Property("QVariant", notify=dataChanged)
    def upcomingHighlights(self) -> list[dict]:
        return list(self.calendarOverview.get("highlights", []))

    @Property("QVariant", notify=weatherChanged)
    def weatherHourly(self) -> list[dict]:
        return render_payload([hour.to_qml() for hour in self._weather_hours])

    @Property("QVariant", notify=weatherChanged)
    def observingWeatherHourly(self) -> list[dict]:
        return render_payload([hour.to_qml() for hour in self._observing_weather_hours()])

    @Property("QVariant", notify=weatherChanged)
    def weatherNext24Hours(self) -> list[dict]:
        night_hours = set(self._observing_weather_hours())
        payload = []
        for hour in self._next_24_weather_hours():
            item = hour.to_qml()
            item["isObservingNight"] = hour in night_hours
            payload.append(item)
        return render_payload(payload)

    @Property("QVariant", notify=weatherChanged)
    def weatherSummary(self) -> dict:
        return render_payload(self._weather_summary.to_qml() if self._weather_summary else {})

    @Property("QVariant", notify=weatherChanged)
    def observingQuality(self) -> dict:
        return render_payload(self._weather_summary.to_qml() if self._weather_summary else {})

    @Property("QVariant", notify=weatherChanged)
    def homeObservingOverview(self) -> dict:
        return render_payload(self._home_observing_overview_payload())

    def _home_observing_overview_payload(self) -> dict:
        digest = self._weather_digest()
        return self._home_observing_overview_service.build(
            location_available=self._has_valid_location(),
            location_pending=self._startup_location_detection_running,
            weather=self._weather_summary,
            weather_available=bool(self._weather_hours),
            seeing=self._seeing_transparency,
            sky_quality=self._sky_quality,
            moon=self._moon,
            category_scores=self._category_scores,
            session=self._observing_session_decision(),
            blocking=self._weather_blocking_status(),
            suggested_window=self._suggested_observing_window(),
            wind_label=presentation_text(digest.get("windLabel") or tr("n/d")),
            category_source="nsom_canonical_environment",
        )

    @Property("QVariant", notify=homeNightPlanChanged)
    def homeNightPlanOverview(self) -> dict:
        target_pool = self._tonight_target_pool()
        target_payloads_by_id = {
            item.id: self._object_to_qml(item)
            for item in target_pool
        }
        return render_payload(self._home_night_plan_overview_service.build(
            session=self._home_observing_overview_payload().get("session", {}),
            night_plan=self._night_plan,
            target_payloads_by_id=target_payloads_by_id,
            setup_models_by_object_id=self._equipment_setup_read_models_by_object_id,
            alternatives=self._home_visible_alternative_payloads(target_pool),
            active_profile=self._active_profile_payload(),
            assigned_equipment=self._profile_assigned_equipment(),
            loading=self._is_loading,
            sky_quality_warning=(
                bortle_observing_warning(self._sky_quality.bortle_class)
                if self._sky_quality
                else tr(
                    "Inquinamento luminoso non disponibile: visibilità locale da verificare."
                )
                if self._has_valid_location()
                else ""
            ),
        ))

    @Property("QVariant", notify=weatherChanged)
    def skyQuality(self) -> dict:
        return render_payload(self._sky_quality.to_qml() if self._sky_quality else {})

    @Property(bool, notify=weatherChanged)
    def hasSkyQuality(self) -> bool:
        return self._sky_quality is not None

    @Property("QVariant", notify=weatherChanged)
    def localAtmosphere(self) -> dict:
        return render_payload(self._local_atmosphere.to_qml())

    @Property("QVariant", notify=weatherChanged)
    def atmosphericTransparency(self) -> dict:
        if not self._earthdata_credentials_state.connection_verified:
            result = NasaAodResult.no_credentials().to_qml()
        else:
            result = self._nasa_aod_result.to_qml()
        result["running"] = self._nasa_aod_refresh_running
        if self._nasa_aod_refresh_running:
            result["visible"] = True
        return render_payload(result)

    @Property(bool, notify=weatherChanged)
    def nasaAodRefreshRunning(self) -> bool:
        return self._nasa_aod_refresh_running

    @Property(bool, notify=weatherChanged)
    def viirsSkyQualityRunning(self) -> bool:
        return self._viirs_sky_quality_running

    @Property(str, notify=weatherChanged)
    def lightPollutionStatus(self) -> str:
        return render_text(self._light_pollution_status)

    @Property("QVariant", notify=weatherChanged)
    def seeingTransparency(self) -> dict:
        return render_payload(self._seeing_transparency.to_qml() if self._seeing_transparency else {})

    @Property("QVariant", notify=weatherChanged)
    def weatherDigest(self) -> dict:
        return render_payload(self._weather_digest())

    @Property(bool, notify=weatherChanged)
    def isObservingSessionBlocked(self) -> bool:
        return self._observing_session_decision().state != "recommended"

    @Property(str, notify=weatherChanged)
    def blockingReason(self) -> str:
        return render_text(self._weather_blocking_status().reason)

    @Property(str, notify=weatherChanged)
    def blockingDetail(self) -> str:
        return render_text(self._weather_blocking_status().detail)

    @Property(str, notify=weatherChanged)
    def suggestedObservingWindow(self) -> str:
        return render_text(self._suggested_observing_window())

    @Property(str, notify=weatherChanged)
    def observingSessionState(self) -> str:
        return self._observing_session_decision().state

    @Property(str, notify=weatherChanged)
    def observingSessionTitle(self) -> str:
        return render_text(self._observing_session_decision().title)

    @Property(str, notify=weatherChanged)
    def observingSessionIcon(self) -> str:
        return self._observing_session_decision().icon

    @Property(str, notify=weatherChanged)
    def observingSessionDetail(self) -> str:
        return render_text(self._observing_session_decision().detail)

    @Property(str, notify=weatherChanged)
    def observingSessionDescription(self) -> str:
        return render_text(self._observing_session_decision().description)

    @Property(bool, notify=weatherChanged)
    def showObservingSessionOpportunity(self) -> bool:
        return self._observing_session_decision().show_opportunity

    @Property(str, notify=weatherChanged)
    def skyQualityWarning(self) -> str:
        if not self._sky_quality:
            return ""
        return render_text(bortle_observing_warning(self._sky_quality.bortle_class))

    @Property("QVariant", notify=dataChanged)
    def bestObjectOfNight(self) -> dict:
        return render_payload(self._object_to_qml(self._best_object) if self._best_object else {})

    @Property("QVariant", notify=dataChanged)
    def nightPlan(self) -> list[dict]:
        return render_payload([item.to_qml() for item in self._night_plan])

    @Property("QVariant", notify=skyCompassChanged)
    def skyCompass(self) -> dict:
        return render_payload(self._sky_compass)

    @Property("QVariant", notify=selectedObjectChanged)
    def selectedObject(self) -> dict:
        if not self._selected_object:
            return {}
        if self._selected_object_source == CATALOGUE_SOURCE:
            return render_payload(self._object_to_qml(self._selected_object))
        return render_payload(self._object_to_qml(self._moon_adjusted_object(self._selected_object)))

    @Property("QVariant", notify=observingObjectDetailChanged)
    def observingObjectDetail(self) -> dict:
        target = self._observing_detail_display_target()
        if target is None:
            return {}
        adjusted_target = self._moon_adjusted_object(target)
        payload = self._object_to_qml(adjusted_target)
        geometry_state = str(payload.get("observingStatusState", "unavailable"))
        setup_model = getattr(self, "_equipment_setup_read_models_by_object_id", {}).get(target.id)
        filter_recommendations = None
        setup_telescope_id = ""
        if (
            setup_model is not None
            and setup_model.equipment_type == "Telescope"
        ):
            setup_telescope_id = setup_model.telescope_id
            telescope = self._find_telescope(setup_telescope_id)
            if telescope is not None:
                filter_recommendations = self._filter_recommendation_service.recommend(
                    adjusted_target,
                    self._active_profile_filters(),
                    self._filters,
                    telescope_aperture_mm=telescope.aperture_mm,
                )
        reducer_recommendation = self._reducer_recommendation_service.recommend(
            adjusted_target,
            setup_telescope_id,
            self._active_profile_reducers(),
            self._reducers,
        )
        session = self._home_observing_overview_payload().get("session", {})
        is_deep_sky = not self._is_planetary_or_lunar_target(target)
        return render_payload(self._observing_object_detail_service.build(
            object_payload=payload,
            geometry_state=geometry_state,
            session=session,
            setup_model=setup_model,
            filter_recommendations=(
                filter_recommendations.to_payload()
                if filter_recommendations is not None
                else None
            ),
            reducer_recommendation=reducer_recommendation.to_payload(),
            altitude_threshold_deg=self._observing_altitude_threshold(target),
            is_deep_sky=is_deep_sky,
        ))

    def _observing_detail_display_target(self) -> CelestialObject | None:
        if not self._selected_object or self._selected_object_source == CATALOGUE_SOURCE:
            return None
        object_id = self._selected_object.id
        live_target = next(
            (
                item
                for item in getattr(self, "_sky_compass_candidate_snapshot", [])
                if item.id == object_id
            ),
            None,
        )
        if live_target is not None:
            return live_target
        read_model = self._observing_detail_read_model(object_id)
        return read_model.qml_display_target if read_model is not None else self._selected_object

    def _observing_detail_read_model(
        self, object_id: str
    ) -> ObservationConditionedTargetReadModel | None:
        return next(
            (
                model
                for model in getattr(self, "_conditioned_home_read_model", [])
                if model.object_id == object_id
            ),
            None,
        )

    def _detail_telescope_for_target(self, object_id: str) -> Telescope:
        setup_model = getattr(self, "_equipment_setup_read_models_by_object_id", {}).get(object_id)
        if setup_model is not None and setup_model.equipment_type == "Telescope" and setup_model.telescope_id:
            telescope = self._find_telescope(setup_model.telescope_id)
            if telescope is not None:
                return telescope
        return self._current_telescope()

    @Property("QVariant", notify=dataChanged)
    def tonightHighlights(self) -> list[dict]:
        objects = self._home_visible_objects(self._visible_planets)[:2] + self._conditioned_deep_sky_candidates()[:2]
        return render_payload([
            {
                "name": item.name,
                "type": item.object_type,
                "bestTime": self._home_time_label(item),
                "setup": item.recommended_setup,
            }
            for item in objects
        ])

    @Property("QVariant", notify=equipmentChanged)
    def beginnerPresets(self) -> list[dict]:
        return render_payload([preset.to_qml() for preset in self._beginner_presets])

    @Property("QVariant", notify=equipmentChanged)
    def equipmentSetups(self) -> list[dict]:
        return render_payload([telescope.to_qml() for telescope in self._catalog_telescopes()])

    @Property("QVariant", notify=equipmentChanged)
    def profileTelescopes(self) -> list[dict]:
        return render_payload([telescope.to_qml() for telescope in self._active_profile_telescopes()])

    @Property("QVariant", notify=equipmentChanged)
    def availableProfileTelescopes(self) -> list[dict]:
        assigned = {telescope.id for telescope in self._active_profile_telescopes()}
        return render_payload(
            [telescope.to_qml() for telescope in self._catalog_telescopes() if telescope.id not in assigned]
        )

    @Property("QVariant", notify=equipmentChanged)
    def telescopeBrands(self) -> list[dict]:
        return render_payload(self._telescope_brands)

    @Property("QVariant", notify=equipmentChanged)
    def telescopeCatalogModels(self) -> list[dict]:
        return render_payload(self._telescope_catalog_models)

    @Property("QVariant", notify=equipmentChanged)
    def eyepieceCatalog(self) -> list[dict]:
        return render_payload(self._catalog_eyepieces)

    @Property("QVariant", notify=equipmentChanged)
    def barlowCatalog(self) -> list[dict]:
        return render_payload(self._catalog_barlows)

    @Property("QVariant", notify=equipmentChanged)
    def binocularCatalog(self) -> list[dict]:
        return render_payload(self._catalog_binoculars)

    @Property("QVariant", notify=equipmentChanged)
    def filterCatalog(self) -> list[dict]:
        return render_payload(self._catalog_filters)

    @Property("QVariant", notify=equipmentChanged)
    def filterClassOptions(self) -> list[dict[str, str]]:
        return render_payload([
            {"code": code, "label": label}
            for code, label in FILTER_CLASS_OPTIONS
        ])

    @Property("QVariant", notify=equipmentChanged)
    def reducerCatalog(self) -> list[dict]:
        return render_payload(self._catalog_reducers)

    @Property("QVariant", notify=equipmentChanged)
    def equipmentProfiles(self) -> list[dict]:
        return render_payload(self._presented_equipment_profiles())

    @Property("QVariant", notify=equipmentChanged)
    def activeEquipmentProfile(self) -> dict:
        return render_payload(self._active_profile_payload())

    def _active_profile_payload(self) -> dict:
        return self._active_profile() or {
            "id": 0,
            "profile_name": "Default",
            "active": 1,
            "telescope_id": "preset:naked-eye",
        }

    @Property("QVariant", notify=dataChanged)
    def objectImages(self) -> list[dict]:
        return self._object_images

    @Property("QVariant", notify=equipmentChanged)
    def eyepieces(self) -> list[dict]:
        return render_payload([eyepiece.to_qml() for eyepiece in self._active_profile_eyepieces()])

    @Property("QVariant", notify=equipmentChanged)
    def ownedEyepieces(self) -> list[dict]:
        return render_payload([eyepiece.to_qml() for eyepiece in self._eyepieces])

    @Property("QVariant", notify=equipmentChanged)
    def availableProfileEyepieces(self) -> list[dict]:
        assigned = {eyepiece.id for eyepiece in self._active_profile_eyepieces()}
        return render_payload(
            [eyepiece.to_qml() for eyepiece in self._eyepieces if eyepiece.id not in assigned]
        )

    @Property("QVariant", notify=equipmentChanged)
    def ownedBarlows(self) -> list[dict]:
        return render_payload([barlow.to_qml() for barlow in self._barlows])

    @Property("QVariant", notify=equipmentChanged)
    def profileEquipmentCatalog(self) -> list[dict]:
        assigned_ids = {item["id"] for item in self._profile_assigned_equipment()}
        items = self._equipment_catalog_items()
        for item in items:
            item["assigned"] = item["id"] in assigned_ids
        return render_payload(items)

    @Property("QVariant", notify=equipmentChanged)
    def profileAssignedEquipment(self) -> list[dict]:
        return render_payload(self._profile_assigned_equipment())

    @Property("QVariant", notify=equipmentChanged)
    def profileBarlows(self) -> list[dict]:
        return render_payload([barlow.to_qml() for barlow in self._active_profile_barlows()])

    @Property("QVariant", notify=equipmentChanged)
    def availableProfileBarlows(self) -> list[dict]:
        assigned = {barlow.id for barlow in self._active_profile_barlows()}
        return render_payload([barlow.to_qml() for barlow in self._barlows if barlow.id not in assigned])

    @Property("QVariant", notify=equipmentChanged)
    def profileBinoculars(self) -> list[dict]:
        return render_payload([binocular.to_qml() for binocular in self._active_profile_binoculars()])

    @Property("QVariant", notify=equipmentChanged)
    def availableProfileBinoculars(self) -> list[dict]:
        assigned = {binocular.id for binocular in self._active_profile_binoculars()}
        return render_payload(
            [binocular.to_qml() for binocular in self._binoculars if binocular.id not in assigned]
        )

    @Property("QVariant", notify=equipmentChanged)
    def profileFilters(self) -> list[dict]:
        return render_payload([optical_filter.to_qml() for optical_filter in self._active_profile_filters()])

    @Property("QVariant", notify=equipmentChanged)
    def profileReducers(self) -> list[dict]:
        return render_payload([reducer.to_qml() for reducer in self._active_profile_reducers()])

    @Property(bool, notify=equipmentChanged)
    def canUseEyepieces(self) -> bool:
        return self._equipment_service.can_use_eyepieces(self._current_telescope())

    @Property(str, notify=equipmentChanged)
    def equipmentMessage(self) -> str:
        return render_text(self._equipment_message)

    @Slot()
    def clearEquipmentMessage(self) -> None:
        if self._equipment_message:
            self._equipment_message = ""
            self.equipmentChanged.emit()

    @Property("QVariant", notify=equipmentChanged)
    def currentSetup(self) -> dict:
        return render_payload(self._current_telescope().to_qml())

    @Property("QVariant", notify=equipmentChanged)
    def telescopeCalculations(self) -> list[dict]:
        return render_payload(
            self._equipment_service.calculations(
                self._current_telescope(), self._active_profile_eyepieces(), self._barlow
            )
        )

    @Property("QVariant", notify=equipmentChanged)
    def telescopeCapabilities(self) -> dict:
        return render_payload(self._equipment_service.profile_capabilities(
            self._current_telescope(),
            self._active_profile_eyepieces(),
            self._active_profile_barlows(),
        ))

    @Property(float, notify=equipmentChanged)
    def selectedBarlow(self) -> float:
        return self._barlow

    @Property("QVariant", notify=observationChanged)
    def observationLog(self) -> list[dict]:
        return render_payload(self._observation_log)

    @Property("QVariant", notify=observationChanged)
    def observationLogSummary(self) -> dict:
        return render_payload(self._observation_log_summary)

    @Property("QVariant", notify=observationChanged)
    def observationLogDefaults(self) -> dict:
        now = datetime.now(self._zone())
        telescope = self._current_telescope()
        eyepieces = self._active_profile_eyepieces()
        return {
            "dateValue": now.strftime("%Y-%m-%d"),
            "timeValue": now.strftime("%H:%M"),
            "location": self._observation_location_label(),
            "telescope": telescope.name,
            "eyepiece": eyepieces[0].name if eyepieces else "",
        }

    @Property(str, notify=observationChanged)
    def observationMessage(self) -> str:
        return render_text(self._observation_message)

    @Slot()
    def retranslatePresentation(self) -> None:
        """Refreshes localized payloads without recomputing astronomy or NSOM."""

        self._observation_log = self._observation_log_service.build_entries(
            self._observation_rows
        )
        self._observation_log_summary = self._observation_log_service.build_summary(
            self._observation_rows
        )
        self._equipment_message = self._equipment_status_message()

        self.locationChanged.emit()
        self.statusChanged.emit()
        self.earthdataCredentialsChanged.emit()
        self.openaqCredentialsChanged.emit()
        self.catalogueChanged.emit()
        self.equipmentChanged.emit()
        self.observationChanged.emit()
        self.dataChanged.emit()
        self.weatherChanged.emit()
        self.skyCompassChanged.emit()
        self.selectedObjectChanged.emit()

    @Slot(str)
    def selectObject(self, object_id: str) -> None:
        for item in self._solar_system_objects + self._deep_sky:
            if item.id == object_id:
                self._selected_object = item
                self._selected_object_source = OBSERVING_SOURCE
                self.selectedObjectChanged.emit()
                return

    @Slot(str)
    def selectCatalogueObject(self, object_id: str) -> None:
        item = self._catalogue_item_for_object_id(object_id)
        if not item:
            return
        item = self._catalogue_item_for_active_filter(item)
        self._selected_object = self._catalogue_item_to_detail_object(item)
        self._selected_object_source = CATALOGUE_SOURCE
        self.selectedObjectChanged.emit()

    @Slot(str, bool)
    def setCatalogueRecommendationEnabled(
        self,
        object_id: str,
        enabled: bool,
    ) -> None:
        item = self._catalogue_item_for_object_id(object_id)
        if not item:
            return
        if not bool(item.get("recommendation_editable", False)):
            return
        canonical_id = str(item.get("object_id") or "").strip()
        if not canonical_id:
            return
        enabled = bool(enabled)
        if bool(item.get("recommendation_enabled", True)) == enabled:
            return

        self._catalogue_repository.set_recommendation_enabled(
            canonical_id,
            enabled,
        )
        normalized_id = canonical_id.casefold()
        self._recommendation_enabled_by_object_id[normalized_id] = enabled
        item["recommendation_enabled"] = enabled

        self._refresh_after_catalogue_recommendation_change()
        self.catalogueChanged.emit()
        self.dataChanged.emit()
        self.selectedObjectChanged.emit()

    @Slot(str)
    def searchCatalogue(self, query: str) -> None:
        self._catalogue_search_query = query.strip()
        self.catalogueChanged.emit()

    @Slot(str, str)
    def setCatalogueFilter(self, filter_name: str, value: str) -> None:
        normalized_name = self._normalize_catalogue_filter_name(filter_name)
        if not normalized_name:
            return
        clean_value = value.strip() or CATALOGUE_ALL_FILTER
        if self._catalogue_filters.get(normalized_name) == clean_value:
            return
        self._catalogue_filters[normalized_name] = clean_value
        self.catalogueChanged.emit()

    @Slot(int)
    def setCatalogueMonth(self, month: int) -> None:
        if month < 1 or month > 12:
            return
        self._catalogue_month_user_selected = True
        if self._catalogue_selected_month == month:
            return
        self._catalogue_selected_month = month
        self._invalidate_catalogue_month_visibility_cache()
        self._refresh_equipment_recommendations_for_current_objects()
        self._recalculate_observing_outputs()
        self.dataChanged.emit()
        self.catalogueChanged.emit()
        if self._selected_object and self._selected_object_source == CATALOGUE_SOURCE:
            self.selectedObjectChanged.emit()

    @Slot(bool)
    def setCatalogueVisibleThisMonthFilter(self, enabled: bool) -> None:
        enabled = bool(enabled and self._has_valid_location())
        if self._catalogue_visible_this_month_only == enabled:
            return
        self._catalogue_visible_this_month_only = enabled
        self.catalogueChanged.emit()
        if self._selected_object and self._selected_object_source == CATALOGUE_SOURCE:
            self.selectedObjectChanged.emit()

    @Slot()
    def clearCatalogueFilters(self) -> None:
        self._catalogue_search_query = ""
        self._catalogue_filters = {
            "catalogue": CATALOGUE_ALL_FILTER,
            "type": CATALOGUE_ALL_FILTER,
            "constellation": CATALOGUE_ALL_FILTER,
            "observation_type": CATALOGUE_ALL_FILTER,
        }
        self._catalogue_visible_this_month_only = False
        self.catalogueChanged.emit()
        if self._selected_object and self._selected_object_source == CATALOGUE_SOURCE:
            self.selectedObjectChanged.emit()

    @Slot(str)
    def searchLocations(self, query: str) -> None:
        if query.strip():
            self._city_search_has_query = True
            self._city_results = self._location_repository.search(query, limit=20)
        else:
            self._city_search_has_query = False
            self._city_results = []
        self.locationChanged.emit()

    @Slot(str)
    def searchCities(self, query: str) -> None:
        self.searchLocations(query)

    @Slot(int)
    def selectRecentLocation(self, index: int) -> None:
        recent = self._recent_location_results()
        if 0 <= index < len(recent):
            self._cancel_startup_location_detection()
            self._apply_location_result(recent[index])
            self._refresh_all()
            self.locationChanged.emit()

    @Slot(int)
    def selectCity(self, city_id: int) -> None:
        city = self._location_repository.get_city(city_id)
        if not city:
            return
        self._cancel_startup_location_detection()
        result = self._location_service.from_city_result(city)
        self._apply_location_result(result)
        self._refresh_all()
        self.locationChanged.emit()

    @Slot(str)
    def selectMpcObservatory(self, mpc_code: str) -> None:
        observatory = self._location_repository.get_observatory(mpc_code)
        if not observatory:
            return
        self._cancel_startup_location_detection()
        result = self._location_service.from_mpc_observatory_result(observatory)
        self._apply_location_result(result)
        self._refresh_all()
        self.locationChanged.emit()

    @Slot(str, str)
    def selectLocation(self, kind: str, selection_id: str) -> None:
        if kind == "city":
            try:
                city_id = int(selection_id)
            except ValueError:
                return
            self.selectCity(city_id)
        elif kind == "mpc_observatory":
            self.selectMpcObservatory(selection_id)

    @Slot(str, str, str)
    def setManualLocation(self, latitude: str, longitude: str, label: str) -> None:
        try:
            parsed_latitude = float(latitude.replace(",", "."))
            parsed_longitude = float(longitude.replace(",", "."))
        except ValueError:
            self._location_message = tr("Coordinate non valide.")
            self.locationChanged.emit()
            return

        if not -90 <= parsed_latitude <= 90 or not -180 <= parsed_longitude <= 180:
            self._location_message = tr("Coordinate fuori intervallo.")
            self.locationChanged.emit()
            return

        clean_label = label.strip() or tr("Coordinate manuali")
        self._cancel_startup_location_detection()
        result = self._location_service.from_manual_coordinates_result(
            parsed_latitude,
            parsed_longitude,
            label=clean_label,
        )
        self._apply_location_result(result)
        self._refresh_all()
        self.locationChanged.emit()

    @Slot()
    def useSystemLocation(self) -> None:
        self._cancel_startup_location_detection()
        try:
            result = self._location_service.detect_system_location()
        except LocationUnavailableError as exc:
            logger.warning("System location unavailable in AppController: %s", exc.reason)
            self._location_message = tr(
                "La posizione di sistema non è disponibile. Provare la posizione approssimata online?"
            )
            self._offer_online_location_fallback = True
            self.locationChanged.emit()
            return
        self._apply_location_result(result)
        self._refresh_all()
        self.locationChanged.emit()

    @Slot()
    def useWindowsLocation(self) -> None:
        self.useSystemLocation()

    @Slot()
    def useApproximateOnlineLocation(self) -> None:
        self._cancel_startup_location_detection()
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

    @Slot()
    def refreshWeatherNow(self) -> None:
        self._start_weather_refresh(force_refresh=True)
        self._schedule_viirs_sky_quality_refresh()
        self._schedule_nasa_aod_refresh()

    @Slot(bool)
    def setAutoDetectLocationOnStartup(self, enabled: bool) -> None:
        self._update_startup_preferences(auto_detect_location_on_startup=enabled)
        if not enabled:
            self._cancel_startup_location_detection()
        self.locationChanged.emit()

    @Slot(bool)
    def setAllowApproximateOnlineLocation(self, enabled: bool) -> None:
        self._update_startup_preferences(allow_approximate_online_location=enabled)
        self.locationChanged.emit()

    @Slot(bool)
    def setUseSystemLocationOnStartup(self, enabled: bool) -> None:
        self._update_startup_preferences(use_system_location_on_startup=enabled)
        self.locationChanged.emit()

    @Slot(bool)
    def setUseWindowsLocationOnStartup(self, enabled: bool) -> None:
        self.setUseSystemLocationOnStartup(enabled)

    @Slot(str, str)
    def saveEarthdataCredentials(self, username: str, password: str) -> None:
        self._mark_refresh_dirty(
            RefreshReason.API_KEY_CHANGED,
            (RefreshDomain.SKY_QUALITY, RefreshDomain.AOD),
        )
        try:
            self._earthdata_credentials_state = self._earthdata_credential_store.save(username, password)
        except (RuntimeError, ValueError) as exc:
            self._earthdata_credentials_state = self._earthdata_credential_store.state()
            self._earthdata_credentials_state = replace(
                self._earthdata_credentials_state,
                message=exc.args[0],
            )
        self._invalidate_earthdata_provider_refreshes()
        self._nasa_aod_result = NasaAodResult.no_credentials()
        self._nasa_aod_provider.clear_cache()
        self.earthdataCredentialsChanged.emit()
        self.weatherChanged.emit()

    @Slot()
    def removeEarthdataCredentials(self) -> None:
        self._mark_refresh_dirty(
            RefreshReason.API_KEY_CHANGED,
            (RefreshDomain.SKY_QUALITY, RefreshDomain.AOD),
        )
        self._earthdata_credentials_state = self._earthdata_credential_store.remove()
        self._invalidate_earthdata_provider_refreshes()
        self._nasa_aod_result = NasaAodResult.no_credentials()
        self._nasa_aod_provider.clear_cache()
        self.earthdataCredentialsChanged.emit()
        self.weatherChanged.emit()

    @Slot()
    def testEarthdataConnection(self) -> None:
        if self._earthdata_connection_test_running:
            return
        if self._earthdata_credentials_state.connection_verified:
            return
        username = self._earthdata_credential_store.username()
        password = self._earthdata_credential_store.password()
        if not username or not password:
            self._earthdata_credentials_state = replace(
                self._earthdata_credential_store.state(),
                message=tr("Salva le credenziali Earthdata prima del test."),
            )
            self.earthdataCredentialsChanged.emit()
            return
        self._earthdata_connection_test_running = True
        self._earthdata_credentials_state = replace(
            self._earthdata_credentials_state,
            message=tr("Verifica connessione Earthdata in corso..."),
        )
        self.earthdataCredentialsChanged.emit()

        def run_test() -> None:
            try:
                result = self._earthdata_connection_tester.test(username, password)
                self._earthdataConnectionTestFinished.emit(result.ok, result.message, result.authorization_required)
            except Exception:
                logger.warning("Unexpected Earthdata connection test failure.", exc_info=True)
                self._earthdataConnectionTestFinished.emit(
                    False,
                    tr("Connessione Earthdata non riuscita."),
                    False,
                )

        Thread(target=run_test, daemon=True).start()

    @Slot(bool, object, bool)
    def _finish_earthdata_connection_test(self, ok: bool, message: object, authorization_required: bool) -> None:
        self._earthdata_connection_test_running = False
        if ok:
            self._mark_refresh_dirty(
                RefreshReason.API_KEY_CHANGED,
                (RefreshDomain.SKY_QUALITY, RefreshDomain.AOD),
            )
            self._earthdata_credentials_state = self._earthdata_credential_store.mark_connection_verified(message)
        elif authorization_required:
            self._earthdata_credentials_state = self._earthdata_credential_store.mark_authorization_required(message)
        else:
            self._earthdata_credentials_state = self._earthdata_credential_store.clear_connection_status(message)
        self.earthdataCredentialsChanged.emit()
        if ok:
            self._schedule_viirs_sky_quality_refresh()
            self._schedule_nasa_aod_refresh()
        else:
            self._clear_refresh_domains(RefreshDomain.SKY_QUALITY, RefreshDomain.AOD)
            self._invalidate_earthdata_provider_refreshes()
            self._nasa_aod_result = NasaAodResult.no_credentials()
            self.weatherChanged.emit()

    @Slot(str)
    def saveOpenAQApiKey(self, api_key: str) -> None:
        self._mark_refresh_dirty(RefreshReason.API_KEY_CHANGED, (RefreshDomain.AIR_QUALITY,))
        try:
            self._openaq_credentials_state = self._openaq_credential_store.save(api_key)
        except (RuntimeError, ValueError) as exc:
            self._openaq_credentials_state = self._openaq_credential_store.state()
            self._openaq_credentials_state = replace(
                self._openaq_credentials_state,
                message=exc.args[0],
            )
        self._invalidate_local_atmosphere_refresh()
        self._refresh_local_atmosphere()
        self.openaqCredentialsChanged.emit()
        self.weatherChanged.emit()

    @Slot()
    def removeOpenAQCredentials(self) -> None:
        self._mark_refresh_dirty(RefreshReason.API_KEY_CHANGED, (RefreshDomain.AIR_QUALITY,))
        self._openaq_credentials_state = self._openaq_credential_store.remove()
        self._invalidate_local_atmosphere_refresh()
        self._local_atmosphere_service.clear_cache()
        self._local_atmosphere = LocalAtmosphere.not_configured()
        self.openaqCredentialsChanged.emit()
        self.weatherChanged.emit()

    @Slot()
    def testOpenAQConnection(self) -> None:
        if self._openaq_connection_test_running:
            return
        api_key = self._openaq_credential_store.api_key()
        if not api_key:
            self._openaq_credentials_state = replace(
                self._openaq_credential_store.state(),
                message=tr("Salva la API key OpenAQ prima del test."),
            )
            self.openaqCredentialsChanged.emit()
            return
        self._openaq_connection_test_running = True
        self._openaq_credentials_state = replace(
            self._openaq_credentials_state,
            connection_verified=False,
            message=tr("Verifica connessione OpenAQ in corso..."),
        )
        self.openaqCredentialsChanged.emit()

        def run_test() -> None:
            try:
                result = self._openaq_connection_tester.test(api_key)
                self._openaqConnectionTestFinished.emit(result.ok, result.message)
            except Exception:
                logger.warning("Unexpected OpenAQ connection test failure.", exc_info=True)
                self._openaqConnectionTestFinished.emit(
                    False,
                    tr("Connessione OpenAQ non riuscita."),
                )

        Thread(target=run_test, daemon=True).start()

    @Slot(bool, object)
    def _finish_openaq_connection_test(self, ok: bool, message: object) -> None:
        self._openaq_connection_test_running = False
        self._openaq_credentials_state = self._openaq_credential_store.with_connection_result(ok, message)
        if ok:
            self._mark_refresh_dirty(RefreshReason.API_KEY_CHANGED, (RefreshDomain.AIR_QUALITY,))
            self._local_atmosphere_service.clear_cache()
            self._refresh_local_atmosphere()
        else:
            self._local_atmosphere = LocalAtmosphere.not_configured()
            self._clear_refresh_domains(RefreshDomain.AIR_QUALITY)
        self.openaqCredentialsChanged.emit()
        self.weatherChanged.emit()

    @Slot(int)
    def selectEquipmentSetup(self, index: int) -> None:
        telescopes = self._catalog_telescopes()
        if 0 <= index < len(telescopes):
            self.assignTelescopeToActiveProfile(telescopes[index].id)

    @Slot(str)
    def addEquipmentProfile(self, profile_name: str) -> None:
        clean_name = profile_name.strip()
        if not clean_name:
            self._equipment_message = tr("Inserisci un nome profilo.")
            self.equipmentChanged.emit()
            return
        if any(profile["profile_name"].strip().lower() == clean_name.lower() for profile in self._equipment_profiles):
            self._equipment_message = tr("Questo profilo esiste già.")
            self.equipmentChanged.emit()
            return
        self._equipment_catalog_repository.add_profile(clean_name, self._equipment_service.NAKED_EYE_ID, active=False)
        self._refresh_profiles_from_repository()
        self._profile_equipment.setdefault(self._profile_key_by_name(clean_name), self._empty_profile_equipment_state())
        self._equipment_message = tr("Profilo creato: {name}.", name=clean_name)
        self.equipmentChanged.emit()

    @Slot(int, str)
    def renameEquipmentProfile(self, profile_id: int, profile_name: str) -> None:
        clean_name = profile_name.strip()
        if not clean_name:
            self._equipment_message = tr("Inserisci un nome profilo.")
            self.equipmentChanged.emit()
            return
        if any(int(profile["id"]) != profile_id and profile["profile_name"].strip().lower() == clean_name.lower() for profile in self._equipment_profiles):
            self._equipment_message = tr("Questo profilo esiste già.")
            self.equipmentChanged.emit()
            return
        was_active = any(
            int(profile["id"]) == profile_id and int(profile.get("active", 0)) == 1
            for profile in self._equipment_profiles
        )
        self._equipment_catalog_repository.rename_profile(profile_id, clean_name)
        self._refresh_profiles_from_repository()
        self._equipment_message = tr("Profilo rinominato: {name}.", name=clean_name)
        if was_active:
            self._refresh_active_profile_dependencies(reload_profile_equipment=True)
            self._emit_profile_dependent_changes()
        else:
            self.equipmentChanged.emit()

    @Slot(int)
    def deleteEquipmentProfile(self, profile_id: int) -> None:
        if len(self._equipment_profiles) <= 1:
            self._equipment_message = tr("Mantieni almeno un profilo attrezzatura.")
            self.equipmentChanged.emit()
            return
        self._equipment_catalog_repository.delete_profile(profile_id)
        self._profile_equipment.pop(str(profile_id), None)
        self._refresh_profiles_from_repository()
        self._equipment_message = tr("Profilo eliminato.")
        self._refresh_active_profile_dependencies(reload_profile_equipment=True)
        self._emit_profile_dependent_changes()

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
        self._equipment_message = self._equipment_status_message()
        self._refresh_active_profile_dependencies(reload_profile_equipment=True)
        self._selected_telescope_index = self._index_for_telescope(telescope.id)
        self._emit_profile_dependent_changes()

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
        self._equipment_message = self._equipment_status_message()
        self._refresh_active_profile_dependencies(reload_profile_equipment=True)
        self._emit_profile_dependent_changes()

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
        self._refresh_active_profile_dependencies(reload_profile_equipment=True)
        self._emit_profile_dependent_changes()

    @Slot(str)
    def removeEyepieceFromActiveProfile(self, eyepiece_id: str) -> None:
        state = self._active_profile_state()
        state["eyepiece_ids"] = [item for item in state["eyepiece_ids"] if item != eyepiece_id]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_eyepiece(int(profile["id"]), eyepiece_id)
        self._equipment_message = self._equipment_status_message()
        self._refresh_active_profile_dependencies(reload_profile_equipment=True)
        self._emit_profile_dependent_changes()

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
        self._refresh_active_profile_dependencies(reload_profile_equipment=True)
        self._emit_profile_dependent_changes()

    @Slot(str)
    def removeBarlowFromActiveProfile(self, barlow_id: str) -> None:
        state = self._active_profile_state()
        state["barlow_ids"] = [item for item in state["barlow_ids"] if item != barlow_id]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_barlow(int(profile["id"]), barlow_id)
        self._equipment_message = self._equipment_status_message()
        self._refresh_active_profile_dependencies(reload_profile_equipment=True)
        self._emit_profile_dependent_changes()

    @Slot(str)
    def assignBinocularToActiveProfile(self, binocular_id: str) -> None:
        if not self._find_binocular(binocular_id):
            return
        state = self._active_profile_state()
        if binocular_id not in state["binocular_ids"]:
            state["binocular_ids"].append(binocular_id)
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.assign_profile_binocular(int(profile["id"]), binocular_id)
        self._equipment_message = self._equipment_status_message()
        self.equipmentChanged.emit()

    @Slot(str)
    def removeBinocularFromActiveProfile(self, binocular_id: str) -> None:
        state = self._active_profile_state()
        state["binocular_ids"] = [item for item in state["binocular_ids"] if item != binocular_id]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_binocular(int(profile["id"]), binocular_id)
        self._equipment_message = self._equipment_status_message()
        self.equipmentChanged.emit()

    @Slot(str)
    def assignFilterToActiveProfile(self, filter_id: str) -> None:
        if not self._find_filter(filter_id):
            return
        state = self._active_profile_state()
        if filter_id not in state["filter_ids"]:
            state["filter_ids"].append(filter_id)
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.assign_profile_filter(
                int(profile["id"]),
                filter_id,
            )
        self._equipment_message = self._equipment_status_message()
        self.equipmentChanged.emit()

    @Slot(str)
    def removeFilterFromActiveProfile(self, filter_id: str) -> None:
        state = self._active_profile_state()
        state["filter_ids"] = [item for item in state["filter_ids"] if item != filter_id]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_filter(
                int(profile["id"]),
                filter_id,
            )
        self._equipment_message = self._equipment_status_message()
        self.equipmentChanged.emit()

    @Slot(str)
    def assignReducerToActiveProfile(self, reducer_id: str) -> None:
        if not self._find_reducer(reducer_id):
            return
        state = self._active_profile_state()
        if reducer_id not in state["reducer_ids"]:
            state["reducer_ids"].append(reducer_id)
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.assign_profile_reducer(
                int(profile["id"]),
                reducer_id,
            )
        self._equipment_message = self._equipment_status_message()
        self.equipmentChanged.emit()

    @Slot(str)
    def removeReducerFromActiveProfile(self, reducer_id: str) -> None:
        state = self._active_profile_state()
        state["reducer_ids"] = [item for item in state["reducer_ids"] if item != reducer_id]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_reducer(
                int(profile["id"]),
                reducer_id,
            )
        self._equipment_message = self._equipment_status_message()
        self.equipmentChanged.emit()

    @Slot(float)
    def setBarlow(self, barlow: float) -> None:
        if not self.canUseEyepieces:
            self._equipment_message = tr(
                "Crea o seleziona un telescopio prima di usare oculari o Barlow."
            )
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
        elif kind == "binocular":
            self.assignBinocularToActiveProfile(item_id)
        elif kind == "filter":
            self.assignFilterToActiveProfile(item_id)
        elif kind == "reducer":
            self.assignReducerToActiveProfile(item_id)

    @Slot(str, str)
    def removeEquipmentFromActiveProfile(self, kind: str, item_id: str) -> None:
        if kind == "telescope":
            self.removeTelescopeFromActiveProfile(item_id)
        elif kind == "eyepiece":
            self.removeEyepieceFromActiveProfile(item_id)
        elif kind == "barlow":
            self.removeBarlowFromActiveProfile(item_id)
        elif kind == "binocular":
            self.removeBinocularFromActiveProfile(item_id)
        elif kind == "filter":
            self.removeFilterFromActiveProfile(item_id)
        elif kind == "reducer":
            self.removeReducerFromActiveProfile(item_id)

    @Slot(str, str, result=int)
    def equipmentUsage(self, kind: str, item_id: str) -> int:
        return self._equipment_catalog_repository.profile_usage_count(kind, item_id)

    @Slot(str, str, str, str, str, str, str, result=bool)
    def addTelescopeModel(self, brand: str, name: str, optical_type: str, aperture: str, focal: str, mount: str, notes: str) -> bool:
        try:
            aperture_mm = self._positive_int(aperture)
            focal_mm = self._positive_int(focal)
        except ValueError:
            self._equipment_message = tr("Dati telescopio non validi.")
            self.equipmentChanged.emit()
            return False
        ok, message = self._equipment_catalog_repository.add_telescope_model(brand, name, optical_type, aperture_mm, focal_mm, mount, notes)
        self._after_catalog_change(message, ok)
        return ok

    @Slot(int, str, str, str, str, str, str, str, result=bool)
    def updateTelescopeModel(self, model_id: int, brand: str, name: str, optical_type: str, aperture: str, focal: str, mount: str, notes: str) -> bool:
        try:
            aperture_mm = self._positive_int(aperture)
            focal_mm = self._positive_int(focal)
        except ValueError:
            self._equipment_message = tr("Dati telescopio non validi.")
            self.equipmentChanged.emit()
            return False
        ok, message = self._equipment_catalog_repository.update_telescope_model(model_id, brand, name, optical_type, aperture_mm, focal_mm, mount, notes)
        self._after_catalog_change(message, ok)
        return ok

    @Slot(int, bool)
    def deleteTelescopeModel(self, model_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_telescope_model(model_id, remove_from_profiles=force)
        self._after_catalog_change(message, ok)

    @Slot(str, str, str, str, str, str, str, str, str, str, result=bool)
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
    ) -> bool:
        parsed = self._parse_eyepiece_inputs(eyepiece_type, focal, min_focal, max_focal, apparent_field, afov_range)
        if not parsed:
            return False
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
        return ok

    @Slot(int, str, str, str, str, str, str, str, str, str, str, result=bool)
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
    ) -> bool:
        parsed = self._parse_eyepiece_inputs(eyepiece_type, focal, min_focal, max_focal, apparent_field, afov_range)
        if not parsed:
            return False
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
        return ok

    @Slot(int, bool)
    def deleteEyepieceModel(self, eyepiece_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_eyepiece(eyepiece_id, remove_from_profiles=force)
        self._after_catalog_change(message, ok)

    @Slot(str, str, str, str, str, result=bool)
    def addBarlowModel(self, brand: str, model: str, multiplier: str, barrel_size: str, notes: str) -> bool:
        try:
            parsed_multiplier = float(multiplier.replace(",", "."))
            if not math.isfinite(parsed_multiplier):
                raise ValueError
        except ValueError:
            self._equipment_message = tr("Moltiplicatore Barlow non valido.")
            self.equipmentChanged.emit()
            return False
        ok, message = self._equipment_catalog_repository.add_barlow(brand, model, parsed_multiplier, barrel_size, notes)
        self._after_catalog_change(message, ok)
        return ok

    @Slot(int, str, str, str, str, str, result=bool)
    def updateBarlowModel(self, barlow_id: int, brand: str, model: str, multiplier: str, barrel_size: str, notes: str) -> bool:
        try:
            parsed_multiplier = float(multiplier.replace(",", "."))
            if not math.isfinite(parsed_multiplier):
                raise ValueError
        except ValueError:
            self._equipment_message = tr("Moltiplicatore Barlow non valido.")
            self.equipmentChanged.emit()
            return False
        ok, message = self._equipment_catalog_repository.update_barlow(barlow_id, brand, model, parsed_multiplier, barrel_size, notes)
        self._after_catalog_change(message, ok)
        return ok

    @Slot(int, bool)
    def deleteBarlowModel(self, barlow_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_barlow(barlow_id, remove_from_profiles=force)
        self._after_catalog_change(message, ok)

    @Slot(str, str, str, str, bool, result=bool)
    def addBinocularModel(
        self,
        brand: str,
        model: str,
        magnification: str,
        objective_diameter: str,
        image_stabilized: bool,
    ) -> bool:
        parsed = self._parse_binocular_inputs(magnification, objective_diameter)
        if not parsed:
            return False
        magnification_value, objective_value = parsed
        ok, message = self._equipment_catalog_repository.add_binocular(
            brand,
            model,
            magnification_value,
            objective_value,
            image_stabilized,
        )
        self._after_binocular_catalog_change(message, ok)
        return ok

    @Slot(int, str, str, str, str, bool, result=bool)
    def updateBinocularModel(
        self,
        binocular_id: int,
        brand: str,
        model: str,
        magnification: str,
        objective_diameter: str,
        image_stabilized: bool,
    ) -> bool:
        parsed = self._parse_binocular_inputs(magnification, objective_diameter)
        if not parsed:
            return False
        magnification_value, objective_value = parsed
        ok, message = self._equipment_catalog_repository.update_binocular(
            binocular_id,
            brand,
            model,
            magnification_value,
            objective_value,
            image_stabilized,
        )
        self._after_binocular_catalog_change(message, ok)
        return ok

    @Slot(int)
    @Slot(int, bool)
    def deleteBinocularModel(self, binocular_id: int, force: bool = False) -> None:
        ok, message = self._equipment_catalog_repository.delete_binocular(
            binocular_id,
            remove_from_profiles=force,
        )
        self._after_binocular_catalog_change(message, ok)

    @Slot(str, str, str, str, str, str, str, str, result=bool)
    def addFilterModel(
        self,
        brand: str,
        model: str,
        filter_class: str,
        central_wavelength: str,
        bandwidth: str,
        transmission: str,
        minimum_aperture: str,
        notes: str,
    ) -> bool:
        parsed = self._parse_filter_inputs(
            central_wavelength,
            bandwidth,
            transmission,
            minimum_aperture,
        )
        if parsed is None:
            return False
        central, width, transmission_pct, aperture = parsed
        ok, message = self._equipment_catalog_repository.add_filter(
            brand,
            model,
            filter_class,
            central_wavelength_nm=central,
            bandwidth_nm=width,
            transmission_pct=transmission_pct,
            minimum_aperture_mm=aperture,
            notes=notes,
        )
        self._after_passive_accessory_catalog_change(message, ok)
        return ok

    @Slot(int, str, str, str, str, str, str, str, str, result=bool)
    def updateFilterModel(
        self,
        filter_id: int,
        brand: str,
        model: str,
        filter_class: str,
        central_wavelength: str,
        bandwidth: str,
        transmission: str,
        minimum_aperture: str,
        notes: str,
    ) -> bool:
        parsed = self._parse_filter_inputs(
            central_wavelength,
            bandwidth,
            transmission,
            minimum_aperture,
        )
        if parsed is None:
            return False
        central, width, transmission_pct, aperture = parsed
        ok, message = self._equipment_catalog_repository.update_filter(
            filter_id,
            brand,
            model,
            filter_class,
            central_wavelength_nm=central,
            bandwidth_nm=width,
            transmission_pct=transmission_pct,
            minimum_aperture_mm=aperture,
            notes=notes,
        )
        self._after_passive_accessory_catalog_change(message, ok)
        return ok

    @Slot(int, bool)
    def deleteFilterModel(self, filter_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_filter(
            filter_id,
            remove_from_profiles=force,
        )
        self._after_passive_accessory_catalog_change(message, ok)

    @Slot(str, str, str, str, str, str, str, bool, bool, bool, str, result=bool)
    def addReducerModel(
        self,
        brand: str,
        model: str,
        reduction_factor: str,
        optical_system: str,
        compatible_telescope_ids: str,
        connection_name: str,
        backfocus: str,
        visual_compatible: bool,
        imaging_compatible: bool,
        corrected_field: bool,
        notes: str,
    ) -> bool:
        parsed = self._parse_reducer_inputs(reduction_factor, backfocus)
        if parsed is None:
            return False
        factor, backfocus_mm = parsed
        ok, message = self._equipment_catalog_repository.add_reducer(
            brand,
            model,
            factor,
            optical_system,
            connection_name=connection_name,
            backfocus_mm=backfocus_mm,
            visual_compatible=visual_compatible,
            imaging_compatible=imaging_compatible,
            corrected_field=corrected_field,
            notes=notes,
            compatible_telescope_ids=self._catalog_id_list(
                compatible_telescope_ids
            ),
        )
        self._after_passive_accessory_catalog_change(message, ok)
        return ok

    @Slot(int, str, str, str, str, str, str, str, bool, bool, bool, str, result=bool)
    def updateReducerModel(
        self,
        reducer_id: int,
        brand: str,
        model: str,
        reduction_factor: str,
        optical_system: str,
        compatible_telescope_ids: str,
        connection_name: str,
        backfocus: str,
        visual_compatible: bool,
        imaging_compatible: bool,
        corrected_field: bool,
        notes: str,
    ) -> bool:
        parsed = self._parse_reducer_inputs(reduction_factor, backfocus)
        if parsed is None:
            return False
        factor, backfocus_mm = parsed
        ok, message = self._equipment_catalog_repository.update_reducer(
            reducer_id,
            brand,
            model,
            factor,
            optical_system,
            connection_name=connection_name,
            backfocus_mm=backfocus_mm,
            visual_compatible=visual_compatible,
            imaging_compatible=imaging_compatible,
            corrected_field=corrected_field,
            notes=notes,
            compatible_telescope_ids=self._catalog_id_list(
                compatible_telescope_ids
            ),
        )
        self._after_passive_accessory_catalog_change(message, ok)
        return ok

    @Slot(int, bool)
    def deleteReducerModel(self, reducer_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_reducer(
            reducer_id,
            remove_from_profiles=force,
        )
        self._after_passive_accessory_catalog_change(message, ok)

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
        clean_name = profile_name.strip() or tr("Nuovo profilo")
        self._equipment_catalog_repository.add_profile(clean_name, catalog_id, active=True)
        self._refresh_profiles_from_repository()
        self._equipment_message = self._equipment_status_message()
        self._refresh_active_profile_dependencies(reload_profile_equipment=True)
        self._emit_profile_dependent_changes()

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
        self._equipment_message = self._equipment_status_message()
        self._refresh_active_profile_dependencies(reload_profile_equipment=True)
        self._emit_profile_dependent_changes()

    @Slot(str, str, str, str, str, str, int, str, result=bool)
    def addObservation(
        self,
        date_text: str,
        time_text: str,
        object_name: str,
        location: str,
        telescope: str,
        eyepiece: str,
        rating: int,
        notes: str,
    ) -> bool:
        try:
            values = self._normalize_observation(
                date_text,
                time_text,
                object_name,
                location,
                telescope,
                eyepiece,
                rating,
                notes,
            )
        except ObservationLogValidationError as error:
            self._set_observation_message(error.args[0])
            return False
        self._observation_repository.add(**values)
        self._reload_observation_log(tr("Osservazione aggiunta al log."))
        return True

    @Slot(int, str, str, str, str, str, str, int, str, result=bool)
    def updateObservation(
        self,
        observation_id: int,
        date_text: str,
        time_text: str,
        object_name: str,
        location: str,
        telescope: str,
        eyepiece: str,
        rating: int,
        notes: str,
    ) -> bool:
        try:
            values = self._normalize_observation(
                date_text,
                time_text,
                object_name,
                location,
                telescope,
                eyepiece,
                rating,
                notes,
            )
        except ObservationLogValidationError as error:
            self._set_observation_message(error.args[0])
            return False
        if not self._observation_repository.update(observation_id, **values):
            self._set_observation_message(
                tr("L'osservazione selezionata non esiste più.")
            )
            return False
        self._reload_observation_log(tr("Osservazione aggiornata."))
        return True

    @Slot(int, result=bool)
    def deleteObservation(self, observation_id: int) -> bool:
        if not self._observation_repository.delete(observation_id):
            self._set_observation_message(
                tr("L'osservazione selezionata non esiste più.")
            )
            return False
        self._reload_observation_log(tr("Osservazione eliminata."))
        return True

    @Slot()
    def clearObservationMessage(self) -> None:
        if self._observation_message:
            self._set_observation_message("")

    def _normalize_observation(
        self,
        date_text: str,
        time_text: str,
        object_name: str,
        location: str,
        telescope: str,
        eyepiece: str,
        rating: int,
        notes: str,
    ) -> dict:
        return self._observation_log_service.normalize(
            date_text=date_text,
            time_text=time_text,
            object_name=object_name,
            location=location,
            telescope=telescope,
            eyepiece=eyepiece,
            rating=rating,
            notes=notes,
            now=datetime.now(self._zone()),
        )

    def _reload_observation_log(self, message: str) -> None:
        self._observation_rows = self._observation_repository.list_all()
        self._observation_log = self._observation_log_service.build_entries(self._observation_rows)
        self._observation_log_summary = self._observation_log_service.build_summary(self._observation_rows)
        self._observation_message = message
        self.observationChanged.emit()

    def _set_observation_message(self, message: str) -> None:
        self._observation_message = message
        self.observationChanged.emit()

    def _observation_location_label(self) -> str:
        if not self._has_valid_location():
            return ""
        if self._location.country:
            return f"{self._location.city}, {self._location.country}"
        return self._location.city

    def _refresh_all(self) -> None:
        self._set_loading(True)
        previous_status = self._service_status
        self._service_status = (
            previous_status
            if isinstance(self._astronomy_engine, MockAstronomyEngine)
            else ""
        )
        try:
            if self._startup_location_detection_running:
                self._refresh_startup_location_pending_context()
            elif self._has_valid_location():
                if self._start_astronomy_refresh(ASTRONOMY_REFRESH_FULL):
                    return
                self._refresh_astronomy()
                if self._refresh_weather_and_conditions():
                    return
            else:
                self._refresh_no_location_context()
        except Exception:
            logger.exception("Unexpected refresh failure.")
            self._append_service_status(
                tr(
                    "NightScope non ha potuto aggiornare tutti i dati. I dati esistenti restano disponibili."
                )
            )

        self._complete_refresh_all()

    def _complete_refresh_all(self) -> None:
        self._set_loading(False)
        if self._selected_object and self._selected_object_source == CATALOGUE_SOURCE:
            pass
        elif self._selected_object:
            self.selectObject(self._selected_object.id)
        elif self._best_object:
            self._selected_object = self._best_object
            self._selected_object_source = OBSERVING_SOURCE
        elif self._deep_sky:
            self._selected_object = self._deep_sky[0]
            self._selected_object_source = OBSERVING_SOURCE
        self.dataChanged.emit()
        self.weatherChanged.emit()
        self.selectedObjectChanged.emit()
        self.statusChanged.emit()

    def _refresh_startup_location_pending_context(self) -> None:
        self._weather_refresh_timer.stop()
        self._refresh_no_location_context()
        self._location_message = STARTUP_LOCATION_PENDING_MESSAGE
        self._weather_status = STARTUP_WEATHER_PENDING_MESSAGE
        self._service_status = tr("Ricerca della posizione in corso.")

    def _refresh_no_location_context(self) -> None:
        self._cancel_astronomy_refresh()
        self._cancel_transient_event_refresh()
        self._weather_refresh_timer.stop()
        self._weather_retry_pending = False
        self._weather_refresh_running = False
        self._base_solar_system_objects = []
        self._base_deep_sky = []
        self._solar_system_objects = []
        self._visible_planets = []
        self._deep_sky = []
        self._conditioned_deep_sky = []
        self._conditioned_home_objects = []
        self._conditioned_deep_sky_read_model = []
        self._conditioned_home_read_model = []
        self._equipment_setup_read_models_by_object_id = {}
        self._deep_sky_pollution_read_model = []
        self._deep_sky_raw_condition_input_by_id = {}
        self._moon_geometry_condition_cache = {}
        self._moon = MoonSummary(
            phase=tr("n/d"),
            illumination=tr("n/d"),
            rise_time=tr("n/d"),
            set_time=tr("n/d"),
            best_note=tr("Configura una località per calcolare i dati lunari locali."),
            image="",
        )
        self._events = []
        self._transient_events_location_key = ""
        self._weather_hours = []
        self._weather_status = tr("Configura una località per visualizzare il meteo.")
        self._light_pollution_status = ""
        self._invalidate_condition_provider_refreshes()
        self._nasa_aod_result = NasaAodResult.no_location()
        self._refresh_local_atmosphere()
        self._weather_summary = WeatherSummary(
            tr("n/d"),
            0,
            tr("Configura una località per ottenere meteo e cielo locale."),
            0,
            0,
            0,
            0,
            0.0,
            tr("Configura una località per ottenere meteo e cielo locale."),
        )
        self._sky_quality = None
        self._seeing_transparency = SeeingTransparency(
            "",
            "",
            0,
            0,
            tr("Configura una località."),
            "unavailable",
            "unavailable",
        )
        self._category_scores = ObservingCategoryScores(
            0,
            0,
            tr("n/d"),
            tr("n/d"),
            tr("Configura una località."),
        )
        self._best_object = None
        self._night_plan = []
        self._sky_compass_candidate_snapshot = []
        self._cancel_sky_compass_live_refresh()
        self._set_sky_compass(
            SkyCompassService.empty(
                "no_location",
                tr("Configura una località per usare Sky Compass."),
            )
        )
        self._service_status = tr(
            "Configura la posizione per ottenere meteo e cielo locale."
        )
        self._catalogue_visible_this_month_only = False
        self._invalidate_catalogue_visibility_cache()
        self._refresh_lifecycle().clear_all()
        self.catalogueChanged.emit()

    def _refresh_astronomy(self) -> None:
        self._cancel_transient_event_refresh()
        self._mark_refresh_dirty(
            RefreshReason.LOCATION_CHANGED,
            (RefreshDomain.ASTRONOMY, RefreshDomain.EQUIPMENT),
        )
        self._moon_geometry_condition_cache = {}
        snapshot = self._calculate_astronomy_snapshot(
            self._location,
            ASTRONOMY_REFRESH_FULL,
            catalogue_objects=tuple(dict(item) for item in self._catalogue_objects),
            catalogue_year=self._catalogue_year,
            catalogue_month=self._catalogue_selected_month,
            catalogue_visibility_cache_key=self._catalogue_visibility_cache_key(),
        )
        self._apply_astronomy_snapshot(snapshot)
        self._start_transient_event_refresh()
        self._clear_refresh_domains(RefreshDomain.ASTRONOMY, RefreshDomain.EQUIPMENT)

    def _start_astronomy_refresh(
        self,
        purpose: str,
        context: object = None,
    ) -> bool:
        if not self._has_valid_location():
            return False
        location = self._location
        location_key = LightPollutionService._location_key(location)
        catalogue_objects: tuple[dict, ...] = ()
        catalogue_year = 0
        catalogue_month = 0
        catalogue_visibility_cache_key = None
        if purpose == ASTRONOMY_REFRESH_FULL:
            catalogue_objects = tuple(dict(item) for item in self._catalogue_objects)
            catalogue_year = self._catalogue_year
            catalogue_month = self._catalogue_selected_month
            catalogue_visibility_cache_key = self._catalogue_visibility_cache_key()

        self._cancel_sky_compass_live_refresh()
        if purpose in {ASTRONOMY_REFRESH_FULL, ASTRONOMY_REFRESH_NIGHT_ROLLOVER}:
            self._cancel_transient_event_refresh()
            self._mark_refresh_dirty(
                RefreshReason.LOCATION_CHANGED,
                (RefreshDomain.ASTRONOMY, RefreshDomain.EQUIPMENT),
            )
            self._moon_geometry_condition_cache = {}
        self._astronomy_refresh_request_id += 1
        request_id = self._astronomy_refresh_request_id
        self._astronomy_refresh_running = True

        def run_refresh() -> None:
            snapshot = self._calculate_astronomy_snapshot(
                location,
                purpose,
                catalogue_objects=catalogue_objects,
                catalogue_year=catalogue_year,
                catalogue_month=catalogue_month,
                catalogue_visibility_cache_key=catalogue_visibility_cache_key,
            )
            self._astronomyRefreshFinished.emit(
                request_id,
                location_key,
                purpose,
                snapshot,
                context,
            )

        try:
            self._start_background_task(run_refresh)
        except Exception:
            self._astronomy_refresh_running = False
            self._clear_refresh_domains(RefreshDomain.ASTRONOMY, RefreshDomain.EQUIPMENT)
            logger.warning("Astronomy worker could not start.", exc_info=True)
            return False
        return True

    def _calculate_astronomy_snapshot(
        self,
        location: ObserverLocation,
        purpose: str,
        *,
        catalogue_objects: tuple[dict, ...] = (),
        catalogue_year: int = 0,
        catalogue_month: int = 0,
        catalogue_visibility_cache_key: tuple[float, float, str, int, int, float] | None = None,
    ) -> AstronomyRefreshSnapshot:
        try:
            with self._astronomy_engine_lock_instance():
                if purpose == ASTRONOMY_REFRESH_VIIRS_DEEP_SKY:
                    return AstronomyRefreshSnapshot(
                        deep_sky=tuple(self._astronomy_engine.recommended_deep_sky(location)),
                    )

                night_method = getattr(self._astronomy_engine, "observing_night_window", None)
                night_window = (
                    night_method(location)
                    if callable(night_method)
                    else ObservingNightWindow.unavailable()
                )
                solar_system_objects = tuple(self._astronomy_engine.solar_system_objects(location))
                deep_sky = tuple(self._astronomy_engine.recommended_deep_sky(location))
                moon = self._astronomy_engine.moon_summary(location)
                annual_events_method = getattr(
                    self._astronomy_engine,
                    "upcoming_annual_events",
                    None,
                )
                events = tuple(
                    annual_events_method(location)
                    if callable(annual_events_method)
                    else self._astronomy_engine.upcoming_events(location)
                )
                geometry_targets = tuple(
                    item for item in solar_system_objects if item.id not in {"sun", "moon"}
                ) + deep_sky
                geometry_method = getattr(self._astronomy_engine, "moon_geometry_batch", None)
                moon_geometry = (
                    geometry_method(location, list(geometry_targets))
                    if callable(geometry_method)
                    else {}
                )
                catalogue_visibility = {}
                visibility_method = getattr(self._astronomy_engine, "catalogue_month_visibility", None)
                if (
                    purpose == ASTRONOMY_REFRESH_FULL
                    and catalogue_objects
                    and callable(visibility_method)
                ):
                    catalogue_visibility = visibility_method(
                        list(catalogue_objects),
                        location,
                        catalogue_year,
                        catalogue_month,
                        CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
                    )
            return AstronomyRefreshSnapshot(
                observing_night_window=night_window,
                solar_system_objects=solar_system_objects,
                deep_sky=deep_sky,
                moon=moon,
                events=events,
                moon_geometry=tuple(
                    (target.id, moon_geometry.get(target.id)) for target in geometry_targets
                ),
                catalogue_visibility_cache_key=catalogue_visibility_cache_key,
                catalogue_visibility=tuple(
                    (str(object_id), bool(visible))
                    for object_id, visible in catalogue_visibility.items()
                ),
            )
        except Exception:
            logger.exception("Astronomy snapshot calculation failed.")
            return AstronomyRefreshSnapshot(failed=True)

    @Slot(int, str, str, object, object)
    def _finish_astronomy_refresh(
        self,
        request_id: int,
        location_key: str,
        purpose: str,
        snapshot: object,
        context: object,
    ) -> None:
        if request_id != self._astronomy_refresh_request_id:
            return
        self._astronomy_refresh_running = False
        if not self._has_valid_location() or location_key != LightPollutionService._location_key(self._location):
            self._clear_refresh_domains(RefreshDomain.ASTRONOMY, RefreshDomain.EQUIPMENT)
            return
        if not isinstance(snapshot, AstronomyRefreshSnapshot):
            snapshot = AstronomyRefreshSnapshot(failed=True)

        if purpose == ASTRONOMY_REFRESH_VIIRS_DEEP_SKY:
            self._finish_viirs_deep_sky_refresh(snapshot, context or "")
            return

        self._apply_astronomy_snapshot(snapshot)
        self._start_transient_event_refresh()
        self._clear_refresh_domains(RefreshDomain.ASTRONOMY, RefreshDomain.EQUIPMENT)
        if purpose == ASTRONOMY_REFRESH_FULL:
            try:
                if self._refresh_weather_and_conditions():
                    return
            except Exception:
                logger.exception("Unexpected refresh failure after astronomy completion.")
                self._append_service_status(
                    tr(
                        "NightScope non ha potuto aggiornare tutti i dati. "
                        "I dati esistenti restano disponibili."
                    )
                )
            self._complete_refresh_all()
            return
        if purpose == ASTRONOMY_REFRESH_NIGHT_ROLLOVER:
            values = context if isinstance(context, tuple) else ("", False, False)
            error = values[0] if len(values) >= 1 else ""
            retry_recommended = bool(values[1]) if len(values) >= 2 else False
            complete_full_refresh = bool(values[2]) if len(values) >= 3 else False
            self._complete_weather_refresh(error, bool(retry_recommended))
            if complete_full_refresh:
                self._complete_refresh_all()

    def _apply_astronomy_snapshot(self, snapshot: AstronomyRefreshSnapshot) -> None:
        self._moon_geometry_condition_cache = {}
        if snapshot.failed:
            self._base_solar_system_objects = []
            self._base_deep_sky = []
            self._solar_system_objects = []
            self._visible_planets = []
            self._deep_sky = []
            self._events = []
            self._observing_night_window = ObservingNightWindow.unavailable()
            self._append_service_status(
                tr("Dati astronomici temporaneamente non disponibili.")
            )
            return

        self._observing_night_window = snapshot.observing_night_window or ObservingNightWindow.unavailable()
        self._base_solar_system_objects = list(snapshot.solar_system_objects)
        self._base_deep_sky = list(snapshot.deep_sky)
        self._moon = snapshot.moon
        current_location_key = (
            LightPollutionService._location_key(self._location)
            if self._has_valid_location()
            else ""
        )
        retained_transient_events = []
        if current_location_key == getattr(self, "_transient_events_location_key", ""):
            retained_transient_events = [
                event
                for event in getattr(self, "_events", [])
                if event.source_code != "annual_astronomy"
            ]
        self._events = self._sorted_events(
            list(snapshot.events) + retained_transient_events
        )
        for object_id, summary in snapshot.moon_geometry:
            self._moon_geometry_condition_cache[object_id] = self._moon_geometry_summary_to_condition_input(summary)
        if snapshot.catalogue_visibility_cache_key is not None:
            self._catalogue_visibility_cache[snapshot.catalogue_visibility_cache_key] = dict(
                snapshot.catalogue_visibility
            )
        self._refresh_equipment_recommendations_for_current_objects()

    def _cancel_astronomy_refresh(self) -> None:
        if not getattr(self, "_astronomy_refresh_running", False):
            return
        self._astronomy_refresh_request_id += 1
        self._astronomy_refresh_running = False
        self._clear_refresh_domains(RefreshDomain.ASTRONOMY, RefreshDomain.EQUIPMENT)

    def _start_transient_event_refresh(self) -> bool:
        prepare_method = getattr(self._astronomy_engine, "prepare_transient_events", None)
        build_method = getattr(self._astronomy_engine, "upcoming_transient_events", None)
        if (
            not self._has_valid_location()
            or not callable(prepare_method)
            or not callable(build_method)
        ):
            self._schedule_next_transient_event_refresh()
            return False
        if getattr(self, "_transient_event_refresh_running", False):
            return False

        timer = getattr(self, "_transient_event_refresh_timer", None)
        if timer is not None:
            timer.stop()
        location = self._location
        location_key = LightPollutionService._location_key(location)
        self._transient_event_refresh_request_id = (
            getattr(self, "_transient_event_refresh_request_id", 0) + 1
        )
        request_id = self._transient_event_refresh_request_id
        self._transient_event_refresh_running = True

        def run_refresh() -> None:
            try:
                prepared = prepare_method(location)
                with self._astronomy_engine_lock_instance():
                    events = tuple(build_method(location, prepared))
                snapshot = TransientEventRefreshSnapshot(events=events)
            except Exception:
                logger.exception("Transient calendar event refresh failed.")
                snapshot = TransientEventRefreshSnapshot(failed=True)
            self._transientEventsRefreshFinished.emit(
                request_id,
                location_key,
                snapshot,
            )

        try:
            self._start_background_task(run_refresh)
        except Exception:
            self._transient_event_refresh_running = False
            logger.warning("Transient calendar event worker could not start.", exc_info=True)
            self._schedule_next_transient_event_refresh()
            return False
        return True

    @Slot(int, str, object)
    def _finish_transient_event_refresh(
        self,
        request_id: int,
        location_key: str,
        snapshot: object,
    ) -> None:
        if request_id != getattr(self, "_transient_event_refresh_request_id", 0):
            return
        self._transient_event_refresh_running = False
        if (
            not self._has_valid_location()
            or location_key != LightPollutionService._location_key(self._location)
        ):
            return

        if isinstance(snapshot, TransientEventRefreshSnapshot) and not snapshot.failed:
            annual_events = [
                event
                for event in getattr(self, "_events", [])
                if event.source_code == "annual_astronomy"
            ]
            self._events = self._sorted_events(annual_events + list(snapshot.events))
            self._transient_events_location_key = location_key
            self.dataChanged.emit()
        self._schedule_next_transient_event_refresh()

    def _refresh_transient_events_from_timer(self) -> None:
        if not self._start_transient_event_refresh():
            self._schedule_next_transient_event_refresh()

    def _schedule_next_transient_event_refresh(self) -> None:
        timer = getattr(self, "_transient_event_refresh_timer", None)
        interval_method = getattr(
            self._astronomy_engine,
            "transient_event_refresh_interval",
            None,
        )
        if (
            timer is None
            or not QCoreApplication.instance()
            or not self._has_valid_location()
            or not callable(interval_method)
        ):
            if timer is not None:
                timer.stop()
            return
        try:
            interval = interval_method()
        except Exception:
            logger.warning("Transient event refresh interval is unavailable.", exc_info=True)
            timer.stop()
            return
        if not isinstance(interval, timedelta) or interval.total_seconds() <= 0:
            timer.stop()
            return
        delay_ms = max(60_000, int(interval.total_seconds() * 1000))
        timer.start(delay_ms)

    def _cancel_transient_event_refresh(self) -> None:
        timer = getattr(self, "_transient_event_refresh_timer", None)
        if timer is not None:
            timer.stop()
        if not getattr(self, "_transient_event_refresh_running", False):
            return
        self._transient_event_refresh_request_id += 1
        self._transient_event_refresh_running = False

    @staticmethod
    def _sorted_events(events: list[AstronomicalEvent]) -> list[AstronomicalEvent]:
        def sort_key(event: AstronomicalEvent) -> float:
            try:
                return datetime.fromisoformat(event.event_at).timestamp()
            except (OSError, TypeError, ValueError):
                return float("inf")

        return sorted(events, key=sort_key)

    def _refresh_weather_and_conditions(self) -> bool:
        self._mark_refresh_dirty(
            RefreshReason.LOCATION_CHANGED,
            (
                RefreshDomain.WEATHER,
                RefreshDomain.SKY_QUALITY,
                RefreshDomain.AIR_QUALITY,
                RefreshDomain.AOD,
                RefreshDomain.EQUIPMENT,
                RefreshDomain.PLANNER,
                RefreshDomain.COMPASS,
            ),
        )
        self._weather_refresh_request_id += 1
        self._weather_refresh_running = False
        if not self._has_valid_location():
            logger.warning("Weather refresh skipped because no valid location is available.")
            self._weather_hours = []
            self._weather_status = tr("Configura una località per visualizzare il meteo.")
            self._weather_summary = self._score_service.weather_score([], self._moon)
            self._refresh_local_atmosphere()
            self._schedule_next_weather_refresh()
            self._clear_refresh_domains(
                RefreshDomain.WEATHER,
                RefreshDomain.SKY_QUALITY,
                RefreshDomain.AOD,
                RefreshDomain.EQUIPMENT,
                RefreshDomain.PLANNER,
                RefreshDomain.COMPASS,
            )
            return False
        self._weather_hours = []
        self._weather_status = ""
        self._weather_summary = self._score_service.weather_score([], self._moon)
        self._sky_quality = self._light_pollution_service.sky_quality(self._location)
        self._seeing_transparency = self._seeing_service.estimate([], self._sky_quality)
        self._refresh_local_atmosphere()
        self._schedule_viirs_sky_quality_refresh()
        self._schedule_nasa_aod_refresh()
        return self._start_weather_refresh(
            force_refresh=False,
            complete_full_refresh=True,
        )

    def _start_weather_refresh(
        self,
        force_refresh: bool = True,
        *,
        retry_attempt: bool = False,
        complete_full_refresh: bool = False,
    ) -> bool:
        if force_refresh:
            self._weather_retry_pending = False
            self._weather_refresh_timer.stop()
        if self._startup_location_detection_running:
            self._schedule_next_weather_refresh()
            return False
        if not self._has_valid_location():
            self._weather_refresh_request_id += 1
            self._weather_status = tr("Dati meteo non disponibili al momento.")
            self._weather_refresh_running = False
            self._weather_refresh_timer.stop()
            self._weather_retry_pending = False
            self._refresh_local_atmosphere()
            self.weatherChanged.emit()
            self._clear_refresh_domains(
                RefreshDomain.WEATHER,
                RefreshDomain.AIR_QUALITY,
                RefreshDomain.EQUIPMENT,
                RefreshDomain.PLANNER,
                RefreshDomain.COMPASS,
            )
            return False
        if self._weather_refresh_running:
            return False

        self._mark_refresh_dirty(
            RefreshReason.MANUAL
            if force_refresh and not retry_attempt
            else RefreshReason.WEATHER_TTL_EXPIRED,
            (
                RefreshDomain.WEATHER,
                RefreshDomain.EQUIPMENT,
                RefreshDomain.PLANNER,
                RefreshDomain.COMPASS,
            ),
        )
        location = self._location
        location_key = LightPollutionService._location_key(location)
        self._weather_refresh_request_id += 1
        request_id = self._weather_refresh_request_id
        self._weather_refresh_running = True
        if complete_full_refresh:
            self._weather_full_refresh_request_id = request_id
        self.weatherChanged.emit()

        def run_refresh() -> None:
            try:
                hours = self._weather_service.hourly_forecast(location, force_refresh=force_refresh)
                error = getattr(self._weather_service, "last_error", "") or ""
                retry_recommended = bool(getattr(self._weather_service, "retry_recommended", False))
                self._weatherRefreshFinished.emit(
                    request_id,
                    location_key,
                    hours,
                    error,
                    retry_recommended,
                )
            except Exception:
                logger.warning("Unexpected weather refresh failure.", exc_info=True)
                self._weatherRefreshFinished.emit(
                    request_id,
                    location_key,
                    [],
                    WEATHER_UNAVAILABLE_MESSAGE,
                    True,
                )

        try:
            self._start_background_task(run_refresh)
        except Exception:
            self._weather_refresh_running = False
            if self._weather_full_refresh_request_id == request_id:
                self._weather_full_refresh_request_id = None
            self._clear_refresh_domains(
                RefreshDomain.WEATHER,
                RefreshDomain.EQUIPMENT,
                RefreshDomain.PLANNER,
                RefreshDomain.COMPASS,
            )
            logger.warning("Weather worker could not start.", exc_info=True)
            return False
        return True

    def _refresh_weather_from_timer(self) -> None:
        retry_attempt = self._weather_retry_pending
        self._weather_retry_pending = False
        self._start_weather_refresh(
            force_refresh=retry_attempt,
            retry_attempt=retry_attempt,
        )

    @Slot(int, str, object, object, bool)
    def _finish_weather_refresh(
        self,
        request_id: int,
        location_key: str,
        hours: object,
        error: object,
        retry_recommended: bool = False,
    ) -> None:
        if request_id != self._weather_refresh_request_id:
            if request_id == getattr(self, "_weather_full_refresh_request_id", None):
                self._weather_full_refresh_request_id = None
            return
        complete_full_refresh = request_id == getattr(self, "_weather_full_refresh_request_id", None)
        if complete_full_refresh:
            self._weather_full_refresh_request_id = None
        self._weather_refresh_running = False
        if not self._has_valid_location() or location_key != LightPollutionService._location_key(self._location):
            self.weatherChanged.emit()
            self._schedule_next_weather_refresh()
            self._clear_refresh_domains(RefreshDomain.WEATHER)
            return

        self._mark_refresh_dirty(
            RefreshReason.WEATHER_COMPLETED,
            (
                RefreshDomain.WEATHER,
                RefreshDomain.EQUIPMENT,
                RefreshDomain.PLANNER,
                RefreshDomain.COMPASS,
            ),
        )
        refreshed_hours = hours if isinstance(hours, list) else []
        if refreshed_hours:
            self._weather_hours = refreshed_hours
        elif self._weather_hours:
            error = error or WEATHER_UNAVAILABLE_MESSAGE
        else:
            self._weather_hours = []

        night_changed = self._update_observing_night_window()
        if night_changed:
            if self._start_astronomy_refresh(
                ASTRONOMY_REFRESH_NIGHT_ROLLOVER,
                context=(error, retry_recommended, complete_full_refresh),
            ):
                return
            self._refresh_astronomy()

        self._complete_weather_refresh(error, retry_recommended)
        if complete_full_refresh:
            self._complete_refresh_all()

    def _complete_weather_refresh(
        self,
        error: object,
        retry_recommended: bool,
    ) -> None:
        observing_hours = self._observing_weather_hours()
        self._weather_status = self._weather_status_from_error(error, self._weather_hours)
        self._weather_summary = self._score_service.weather_score(observing_hours, self._moon)
        self._seeing_transparency = self._seeing_service.estimate(
            observing_hours,
            self._sky_quality,
        )
        self._refresh_equipment_recommendations_for_current_objects()
        self._recalculate_observing_outputs()
        self._refresh_local_atmosphere()
        self.weatherChanged.emit()
        self.dataChanged.emit()
        self.selectedObjectChanged.emit()
        self._schedule_next_weather_refresh(
            retry_soon=bool(error) and retry_recommended,
        )
        self._clear_refresh_domains(
            RefreshDomain.WEATHER,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        )

    def _schedule_next_weather_refresh(self, *, retry_soon: bool = False) -> None:
        if not QCoreApplication.instance() or not self._has_valid_location() or self._startup_location_detection_running:
            self._weather_refresh_timer.stop()
            self._weather_retry_pending = False
            return
        if retry_soon:
            self._weather_retry_pending = True
            self._weather_refresh_timer.start(WEATHER_RETRY_DELAY_MS)
            logger.info("Weather refresh retry scheduled in 5 minutes.")
            return
        self._weather_retry_pending = False
        now = datetime.now(self._zone())
        next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        delay_ms = max(60_000, int((next_hour - now).total_seconds() * 1000))
        self._weather_refresh_timer.start(delay_ms)

    @staticmethod
    def _weather_status_from_error(error: object, hours: list[WeatherHour]) -> str:
        if error != WEATHER_UNAVAILABLE_MESSAGE:
            return error
        if hours:
            return tr(
                "Tentativo di aggiornamento meteo fallito; uso ultimi dati disponibili."
            )
        return tr("Dati meteo non disponibili al momento.")

    def _recalculate_observing_outputs(self) -> None:
        self._category_scores = self._nsom_category_score_service.scores(
            self._build_observation_condition_inputs()
        )
        self._refresh_conditioned_observing_candidates()
        planning_objects = self._home_visible_objects(self._visible_planets + self._deep_sky)
        planning_objects = planning_objects or list(
            unique_targets_by_id(self._visible_planets + self._deep_sky)
        )
        planner_moon_geometry = self._planner_moon_geometry_inputs(planning_objects)
        planner_telescopes = self._planner_telescopes_by_object_id(planning_objects)
        condition_inputs = self._build_observation_condition_inputs()
        self._best_object = self._select_best_object(
            planning_objects,
            condition_inputs=condition_inputs,
            moon_geometry_by_object_id=planner_moon_geometry,
            telescope_by_object_id=planner_telescopes,
        )
        planner_kwargs = {}
        if planner_moon_geometry is not None:
            planner_kwargs["moon_geometry_by_object_id"] = planner_moon_geometry
        if getattr(self._night_planner_service, "uses_target_equipment", False):
            planner_kwargs["telescope_by_object_id"] = planner_telescopes
        planner_kwargs["condition_inputs"] = condition_inputs
        night_window = getattr(self, "_observing_night_window", None)
        if isinstance(night_window, ObservingNightWindow) and night_window.has_observing_window:
            planner_kwargs["night_window"] = night_window
        self._night_plan = self._night_planner_service.plan(
            planning_objects,
            self._weather_summary,
            self._current_telescope(),
            **planner_kwargs,
        )
        self._refresh_sky_compass()

    def _planner_telescopes_by_object_id(
        self,
        targets: list[CelestialObject],
    ) -> dict[str, Telescope]:
        setup_models = getattr(self, "_equipment_setup_read_models_by_object_id", {})
        telescopes: dict[str, Telescope] = {}
        for target in targets:
            setup = setup_models.get(target.id)
            if setup is None or setup.equipment_type != "Telescope" or not setup.telescope_id:
                continue
            telescope = self._find_telescope(setup.telescope_id)
            if telescope is not None:
                telescopes[target.id] = telescope
        return telescopes

    def _planner_moon_geometry_inputs(
        self,
        targets: list[CelestialObject],
    ) -> dict[str, MoonGeometryConditionInput]:
        self._populate_moon_geometry_condition_cache(targets)
        geometry_by_id: dict[str, MoonGeometryConditionInput] = {}
        for target in targets:
            geometry = self._moon_geometry_condition_input(target)
            if geometry is not None:
                geometry_by_id[target.id] = geometry
        return geometry_by_id

    def _populate_moon_geometry_condition_cache(self, targets: list[CelestialObject]) -> None:
        cache = getattr(self, "_moon_geometry_condition_cache", None)
        if cache is None:
            cache = {}
            self._moon_geometry_condition_cache = cache
        missing = [target for target in targets if target.id not in cache]
        batch_method = getattr(getattr(self, "_astronomy_engine", None), "moon_geometry_batch", None)
        if not missing or not callable(batch_method):
            return
        try:
            with self._astronomy_engine_lock_instance():
                summaries = batch_method(self._location, missing)
        except Exception:
            logger.debug("Moon geometry batch failed; using per-target fallback.", exc_info=True)
            return
        if not isinstance(summaries, Mapping):
            return
        for target in missing:
            if target.id not in summaries:
                continue
            summary = summaries[target.id]
            cache[target.id] = self._moon_geometry_summary_to_condition_input(
                summary if isinstance(summary, MoonGeometrySummary) else None
            )

    def _select_best_object(
        self,
        planning_objects: list[CelestialObject],
        *,
        condition_inputs: ObservationConditionInputs | None = None,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None = None,
        telescope_by_object_id: Mapping[str, Telescope] | None = None,
    ) -> CelestialObject | None:
        if not self._weather_summary:
            return None
        candidate_read_models = self._best_object_read_models(planning_objects)
        selected_raw_target = self._best_object_nsom_selection_service.best_object(
            [model.nsom_target_input for model in candidate_read_models],
            weather=self._weather_summary,
            telescope=self._current_telescope(),
            condition_inputs=condition_inputs or self._build_observation_condition_inputs(),
            moon_geometry_by_object_id=moon_geometry_by_object_id,
            telescope_by_object_id=telescope_by_object_id,
        )
        if selected_raw_target is None:
            return None
        display_targets_by_raw_id = {
            model.nsom_target_input.id: model.qml_display_target
            for model in candidate_read_models
        }
        return display_targets_by_raw_id.get(selected_raw_target.id, selected_raw_target)

    def _best_object_read_models(
        self,
        planning_objects: list[CelestialObject],
    ) -> tuple[ObservationConditionedTargetReadModel, ...]:
        existing_models = {
            model.object_id: model
            for model in getattr(self, "_conditioned_home_read_model", [])
        }
        missing_objects = [
            item
            for item in planning_objects
            if item.id not in existing_models
        ]
        if missing_objects:
            fallback_models = self._conditions_read_model_builder_instance().from_display_targets(
                missing_objects,
                source="best_object_nsom_raw_observable_order_fallback",
                raw_targets_by_id=self._conditioned_raw_targets_by_id(),
            )
            existing_models.update({model.object_id: model for model in fallback_models})
        return tuple(
            existing_models[item.id]
            for item in planning_objects
            if item.id in existing_models
        )

    def _moon_geometry_condition_input(self, target: object | None = None) -> MoonGeometryConditionInput | None:
        if target is None:
            return None
        geometry_target = self._moon_geometry_runtime_target(target)
        if geometry_target is None:
            return None
        cache = getattr(self, "_moon_geometry_condition_cache", None)
        if cache is None:
            cache = {}
            self._moon_geometry_condition_cache = cache
        if geometry_target.id in cache:
            return cache[geometry_target.id]
        summary = self._moon_geometry_summary(geometry_target)
        condition_input = self._moon_geometry_summary_to_condition_input(summary)
        cache[geometry_target.id] = condition_input
        return condition_input

    def _moon_geometry_runtime_target(self, target: object) -> CelestialObject | None:
        if isinstance(target, CelestialObject):
            return target
        object_id = self._nsom_runtime_target_text(target, "id", "object_id")
        if not object_id:
            return None
        return self._nsom_prepared_object_by_id().get(object_id)

    def _moon_geometry_summary(self, target: CelestialObject) -> MoonGeometrySummary | None:
        location = getattr(self, "_location", None)
        if location is None:
            return None
        method = getattr(getattr(self, "_astronomy_engine", None), "moon_geometry", None)
        if not callable(method):
            return None
        try:
            with self._astronomy_engine_lock_instance():
                summary = method(location, target)
        except Exception:
            return None
        return summary if isinstance(summary, MoonGeometrySummary) else None

    @staticmethod
    def _moon_geometry_summary_to_condition_input(
        summary: MoonGeometrySummary | None,
    ) -> MoonGeometryConditionInput | None:
        if summary is None:
            return None
        return MoonGeometryConditionInput(
            moon_altitude_deg=summary.moon_altitude_deg,
            moon_target_separation_deg=summary.moon_target_separation_deg,
            moon_above_horizon=summary.moon_above_horizon,
            moon_visible_during_target_window=summary.moon_visible_during_target_window,
            moon_set_before_target_window=summary.moon_set_before_target_window,
        )

    def _refresh_sky_compass(self) -> None:
        self._cancel_sky_compass_live_refresh()
        candidates = self._sky_compass_candidates()
        self._sky_compass_candidate_snapshot = list(candidates)
        self._set_sky_compass(
            self._select_sky_compass_payload(
                candidates,
                has_location=self._has_valid_location(),
                caution_text=self._sky_compass_caution_text(),
            )
        )

    def _refresh_sky_compass_live(self) -> None:
        if getattr(self, "_sky_compass_live_refresh_running", False):
            return
        if not self._has_valid_location():
            self._update_sky_compass_live_timer()
            return
        candidates = list(getattr(self, "_sky_compass_candidate_snapshot", []))
        if not candidates:
            self._update_sky_compass_live_timer()
            return
        position_method = getattr(self._astronomy_engine, "refresh_current_positions", None)
        if not callable(position_method):
            self._update_sky_compass_live_timer()
            return

        location = self._location
        location_key = LightPollutionService._location_key(location)
        self._sky_compass_live_refresh_request_id += 1
        request_id = self._sky_compass_live_refresh_request_id
        self._sky_compass_live_refresh_running = True
        self._mark_refresh_dirty(RefreshReason.LIVE_TICK)

        def run_refresh() -> None:
            try:
                with self._astronomy_engine_lock_instance():
                    updated_candidates = position_method(candidates, location)
                self._skyCompassLiveRefreshFinished.emit(
                    request_id,
                    location_key,
                    updated_candidates,
                )
            except Exception:
                logger.warning("Sky Compass live refresh failed.", exc_info=True)
                self._skyCompassLiveRefreshFinished.emit(request_id, location_key, None)

        try:
            self._start_background_task(run_refresh)
        except Exception:
            self._sky_compass_live_refresh_running = False
            self._clear_refresh_domains(RefreshDomain.COMPASS_LIVE)
            logger.warning("Sky Compass live worker could not start.", exc_info=True)

    @Slot(int, str, object)
    def _finish_sky_compass_live_refresh(
        self,
        request_id: int,
        location_key: str,
        updated_candidates: object,
    ) -> None:
        if request_id != self._sky_compass_live_refresh_request_id:
            return
        self._sky_compass_live_refresh_running = False
        try:
            if (
                not self._has_valid_location()
                or location_key != LightPollutionService._location_key(self._location)
                or not isinstance(updated_candidates, list)
            ):
                return
            self._sky_compass_candidate_snapshot = list(updated_candidates)
            self._set_sky_compass(
                self._select_sky_compass_payload(
                    updated_candidates,
                    has_location=True,
                    caution_text=self._sky_compass_caution_text(),
                )
            )
        finally:
            self._clear_refresh_domains(RefreshDomain.COMPASS_LIVE)
            self._update_sky_compass_live_timer()

    def _cancel_sky_compass_live_refresh(self) -> None:
        if not getattr(self, "_sky_compass_live_refresh_running", False):
            return
        self._sky_compass_live_refresh_request_id += 1
        self._sky_compass_live_refresh_running = False
        self._clear_refresh_domains(RefreshDomain.COMPASS_LIVE)

    @staticmethod
    def _start_background_task(target: Callable[[], None]) -> None:
        Thread(target=target, daemon=True).start()

    def _astronomy_engine_lock_instance(self):
        lock = getattr(self, "_astronomy_engine_lock", None)
        if lock is None:
            lock = RLock()
            self._astronomy_engine_lock = lock
        return lock

    def _set_sky_compass(self, value: dict) -> None:
        self._sky_compass = value
        self.skyCompassChanged.emit()
        self._update_sky_compass_live_timer()

    def _select_sky_compass_payload(
        self,
        candidates: list[CelestialObject],
        *,
        has_location: bool,
        caution_text: str,
    ) -> dict:
        try:
            return self._sky_compass_service.compass(
                candidates,
                self._night_plan,
                self._best_object,
                has_location=has_location,
                caution_text=caution_text,
                observable_objects_by_id=self._sky_compass_observable_targets_by_id(candidates),
                condition_inputs=self._build_observation_condition_inputs(),
                moon_geometry_by_object_id=self._planner_moon_geometry_inputs(candidates),
            )
        except Exception:
            logger.warning(
                "NSOM Sky Compass selection failed; using geometry fallback.",
                exc_info=True,
            )
        return self._sky_compass_service.compass(
            candidates,
            self._night_plan,
            self._best_object,
            has_location=has_location,
            caution_text=caution_text,
        )

    def _update_sky_compass_live_timer(self) -> None:
        timer = getattr(self, "_sky_compass_live_timer", None)
        if timer is None:
            return
        should_run = (
            self._has_valid_location()
            and bool(getattr(self, "_sky_compass_candidate_snapshot", []))
        )
        if should_run:
            if not timer.isActive():
                timer.start()
            return
        if timer.isActive():
            timer.stop()

    def _sky_compass_candidates(self) -> list[CelestialObject]:
        return self._tonight_target_pool()

    def _sky_compass_observable_targets_by_id(
        self,
        candidates: list[CelestialObject],
    ) -> dict[str, CelestialObject]:
        read_models = {
            model.object_id: model
            for model in getattr(self, "_conditioned_home_read_model", [])
        }
        raw_targets_by_id = self._conditioned_raw_targets_by_id()
        observable_targets = {}
        for display_target in candidates:
            model = read_models.get(display_target.id)
            raw_target = model.nsom_target_input if model else raw_targets_by_id.get(display_target.id, display_target)
            observable_targets[display_target.id] = self._sky_compass_observable_target(
                raw_target,
                display_target,
            )
        return observable_targets

    @staticmethod
    def _sky_compass_observable_target(
        raw_target: CelestialObject,
        display_target: CelestialObject,
    ) -> CelestialObject:
        return replace(
            raw_target,
            direction=display_target.direction,
            visible=display_target.visible,
            max_altitude=display_target.max_altitude,
            azimuth=display_target.azimuth,
            current_altitude=display_target.current_altitude,
            current_azimuth=display_target.current_azimuth,
            observable_now=display_target.observable_now,
            current_altitude_degrees=display_target.current_altitude_degrees,
            current_azimuth_degrees=display_target.current_azimuth_degrees,
            time_above_horizon=display_target.time_above_horizon,
            rise_time=display_target.rise_time,
            set_time=display_target.set_time,
            culmination_time=display_target.culmination_time,
        )

    def _sky_compass_caution_text(self) -> str:
        if not self._weather_hours:
            return tr("Condizioni meteo non disponibili: usa la direzione come orientamento, non come invito a osservare.")
        if self._observing_session_decision().state == "recommended":
            return ""
        return tr("Condizioni non ideali: usa la direzione come orientamento, non come invito a osservare.")

    def _refresh_local_atmosphere(self) -> None:
        api_key = self._openaq_credential_store.api_key()
        if not api_key or not self._openaq_credentials_state.connection_verified:
            self._local_atmosphere = LocalAtmosphere.not_configured()
            self._clear_refresh_domains(RefreshDomain.AIR_QUALITY)
            return
        if not self._has_valid_location():
            self._local_atmosphere = LocalAtmosphere.location_required()
            self._clear_refresh_domains(RefreshDomain.AIR_QUALITY)
            return
        if self._local_atmosphere_refresh_running:
            return

        self._mark_refresh_dirty(
            RefreshReason.AIR_QUALITY_TTL_EXPIRED,
            (RefreshDomain.AIR_QUALITY,),
        )
        location = self._location
        location_key = LightPollutionService._location_key(location)
        self._local_atmosphere_refresh_request_id = (
            getattr(self, "_local_atmosphere_refresh_request_id", 0) + 1
        )
        request_id = self._local_atmosphere_refresh_request_id
        self._local_atmosphere_refresh_running = True

        def run_lookup() -> None:
            try:
                atmosphere = self._local_atmosphere_service.atmosphere(api_key, location)
                self._localAtmosphereRefreshFinished.emit(
                    request_id,
                    location_key,
                    atmosphere,
                )
            except Exception:
                logger.warning("Unexpected OpenAQ local atmosphere refresh failure.", exc_info=True)
                self._localAtmosphereRefreshFinished.emit(
                    request_id,
                    location_key,
                    LocalAtmosphere.failure(
                        tr("Dati OpenAQ non disponibili al momento.")
                    ),
                )

        Thread(target=run_lookup, daemon=True).start()

    @Slot(int, str, object)
    def _finish_local_atmosphere_refresh(
        self,
        request_id: int | str,
        location_key: str | object,
        atmosphere: object = None,
    ) -> None:
        if not isinstance(request_id, int):
            atmosphere = location_key
            location_key = request_id
            request_id = getattr(self, "_local_atmosphere_refresh_request_id", 0)
        if request_id != getattr(self, "_local_atmosphere_refresh_request_id", 0):
            return
        self._local_atmosphere_refresh_running = False
        if not self._has_valid_location() or location_key != LightPollutionService._location_key(self._location):
            self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.AIR_QUALITY)
            if self._has_valid_location():
                self._refresh_local_atmosphere()
            return
        if (
            not self._openaq_credential_store.api_key()
            or not self._openaq_credentials_state.connection_verified
        ):
            self._local_atmosphere = LocalAtmosphere.not_configured()
            self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.AIR_QUALITY)
            return
        self._mark_refresh_dirty(
            RefreshReason.AIR_QUALITY_COMPLETED,
            (RefreshDomain.AIR_QUALITY,),
        )
        previous_atmosphere = self._local_atmosphere
        if isinstance(atmosphere, LocalAtmosphere):
            self._local_atmosphere = atmosphere
        else:
            self._local_atmosphere = LocalAtmosphere.failure(
                tr("Dati OpenAQ non disponibili al momento.")
            )
        if self._local_atmosphere != previous_atmosphere:
            self._recalculate_after_condition_provider_refresh()
        self.weatherChanged.emit()
        self._clear_refresh_domains(RefreshDomain.AIR_QUALITY)

    def _schedule_viirs_sky_quality_refresh(self) -> None:
        if not self._has_valid_location():
            self._clear_refresh_domains(RefreshDomain.SKY_QUALITY)
            return
        if self._viirs_sky_quality_running:
            return
        location = self._location
        if location is None:
            self._clear_refresh_domains(RefreshDomain.SKY_QUALITY)
            return
        cache_state = self._light_pollution_service.viirs_cache_state(location)
        if cache_state is ViirsCacheState.FRESH:
            status_changed = bool(self._light_pollution_status)
            self._light_pollution_status = ""
            if status_changed:
                self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.SKY_QUALITY)
            return
        if not self._earthdata_credentials_state.connection_verified:
            status = (
                tr(
                    "Dati VIIRS in cache da aggiornare; configura o verifica "
                    "l'account Earthdata."
                )
                if cache_state is ViirsCacheState.STALE
                else ""
            )
            status_changed = status != self._light_pollution_status
            self._light_pollution_status = status
            if status_changed:
                self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.SKY_QUALITY)
            return

        unavailable_message = (
            tr("Dati VIIRS NASA non disponibili; mantengo il dataset locale.")
            if self._sky_quality is not None
            else tr("Dati VIIRS NASA non disponibili; qualità cielo locale n/d.")
        )

        self._mark_refresh_dirty(
            RefreshReason.SKY_QUALITY_TTL_EXPIRED,
            (RefreshDomain.SKY_QUALITY,),
        )
        location_key = LightPollutionService._location_key(location)
        self._viirs_sky_quality_request_id = (
            getattr(self, "_viirs_sky_quality_request_id", 0) + 1
        )
        request_id = self._viirs_sky_quality_request_id
        self._viirs_sky_quality_running = True
        self._light_pollution_status = (
            tr("Verifica aggiornamenti VIIRS NASA...")
            if cache_state is ViirsCacheState.STALE
            else tr("Recupero dati VIIRS NASA...")
        )
        self.weatherChanged.emit()

        def run_lookup() -> None:
            try:
                quality = self._light_pollution_service.remote_sky_quality(location)
                provider_error = getattr(
                    self._light_pollution_service,
                    "last_remote_error",
                    "",
                )
                if not isinstance(provider_error, str):
                    provider_error = ""
                if quality:
                    message = tr("Dati VIIRS NASA aggiornati.")
                elif provider_error:
                    message = provider_error
                elif cache_state is ViirsCacheState.STALE:
                    message = tr(
                        "Aggiornamento VIIRS non disponibile; uso dati in cache."
                    )
                else:
                    message = unavailable_message
                self._viirsSkyQualityFinished.emit(
                    request_id,
                    location_key,
                    quality,
                    message,
                )
            except Exception:
                logger.warning("Unexpected VIIRS sky-quality refresh failure.", exc_info=True)
                self._viirsSkyQualityFinished.emit(
                    request_id,
                    location_key,
                    None,
                    (
                        tr("Aggiornamento VIIRS non disponibile; uso dati in cache.")
                        if cache_state is ViirsCacheState.STALE
                        else unavailable_message
                    ),
                )

        Thread(target=run_lookup, daemon=True).start()

    @Slot(int, str, object, object)
    def _finish_viirs_sky_quality_refresh(
        self,
        request_id: int | str,
        location_key: str | object,
        quality: object,
        message: object = None,
    ) -> None:
        if not isinstance(request_id, int):
            message = quality
            quality = location_key
            location_key = request_id
            request_id = getattr(self, "_viirs_sky_quality_request_id", 0)
        if request_id != getattr(self, "_viirs_sky_quality_request_id", 0):
            return
        self._viirs_sky_quality_running = False
        if not self._has_valid_location() or location_key != LightPollutionService._location_key(self._location):
            self._light_pollution_status = ""
            self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.SKY_QUALITY)
            self._schedule_viirs_sky_quality_refresh()
            return

        if isinstance(quality, SkyQuality):
            self._mark_refresh_dirty(
                RefreshReason.SKY_QUALITY_COMPLETED,
                (
                    RefreshDomain.SKY_QUALITY,
                    RefreshDomain.EQUIPMENT,
                    RefreshDomain.PLANNER,
                    RefreshDomain.COMPASS,
                ),
            )
            self._sky_quality = quality
            if self._start_astronomy_refresh(
                ASTRONOMY_REFRESH_VIIRS_DEEP_SKY,
                context=message,
            ):
                return
            snapshot = self._calculate_astronomy_snapshot(
                self._location,
                ASTRONOMY_REFRESH_VIIRS_DEEP_SKY,
            )
            self._finish_viirs_deep_sky_refresh(snapshot, message)
            return

        self._light_pollution_status = message
        self.weatherChanged.emit()
        self._clear_refresh_domains(RefreshDomain.SKY_QUALITY)

    def _finish_viirs_deep_sky_refresh(
        self,
        snapshot: AstronomyRefreshSnapshot,
        message: object,
    ) -> None:
        self._seeing_transparency = self._seeing_service.estimate(
            self._observing_weather_hours(),
            self._sky_quality,
        )
        if not snapshot.failed:
            try:
                self._base_deep_sky = list(snapshot.deep_sky)
                self._refresh_equipment_recommendations_for_current_objects()
                self._deep_sky = self._apply_deep_sky_pollution_context(self._deep_sky)
            except Exception:
                logger.warning("Deep-sky refresh after VIIRS update failed.", exc_info=True)
        self._light_pollution_status = message
        self._recalculate_observing_outputs()
        self.dataChanged.emit()
        self.weatherChanged.emit()
        self.selectedObjectChanged.emit()
        self._clear_refresh_domains(
            RefreshDomain.SKY_QUALITY,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        )

    def _schedule_nasa_aod_refresh(self) -> None:
        if not self._has_valid_location():
            self._nasa_aod_result = NasaAodResult.no_location()
            logger.info("NASA AOD refresh skipped: no valid observing location.")
            self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.AOD)
            return
        if self._nasa_aod_refresh_running:
            logger.info("NASA AOD refresh skipped: refresh already running.")
            return
        if not self._earthdata_credentials_state.connection_verified:
            self._nasa_aod_result = NasaAodResult.no_credentials()
            logger.info("NASA AOD refresh skipped: Earthdata credentials are not verified.")
            self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.AOD)
            return

        location = self._location
        if location is None:
            self._nasa_aod_result = NasaAodResult.no_location()
            logger.info("NASA AOD refresh skipped: no valid observing location.")
            self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.AOD)
            return

        cached = self._nasa_aod_provider.cached_aod(location)
        if cached is not None:
            previous_result = self._nasa_aod_result
            self._nasa_aod_result = cached
            self._log_nasa_aod_result(cached)
            if cached != previous_result:
                self._recalculate_after_condition_provider_refresh()
            self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.AOD)
            return

        self._mark_refresh_dirty(RefreshReason.AOD_TTL_EXPIRED, (RefreshDomain.AOD,))
        location_key = LightPollutionService._location_key(location)
        self._nasa_aod_refresh_request_id = (
            getattr(self, "_nasa_aod_refresh_request_id", 0) + 1
        )
        request_id = self._nasa_aod_refresh_request_id
        self._nasa_aod_refresh_running = True
        self.weatherChanged.emit()
        logger.info("NASA AOD refresh started for the active location.")

        def run_lookup() -> None:
            try:
                result = self._nasa_aod_provider.aod(location)
                self._nasaAodRefreshFinished.emit(request_id, location_key, result)
            except Exception:
                logger.warning("Unexpected NASA AOD refresh failure.", exc_info=True)
                self._nasaAodRefreshFinished.emit(
                    request_id,
                    location_key,
                    NasaAodResult.failure(
                        "parse_error",
                        tr("Dati NASA AOD non disponibili al momento."),
                    ),
                )

        Thread(target=run_lookup, daemon=True).start()

    @Slot(int, str, object)
    def _finish_nasa_aod_refresh(
        self,
        request_id: int | str,
        location_key: str | object,
        result: object = None,
    ) -> None:
        if not isinstance(request_id, int):
            result = location_key
            location_key = request_id
            request_id = getattr(self, "_nasa_aod_refresh_request_id", 0)
        if request_id != getattr(self, "_nasa_aod_refresh_request_id", 0):
            return
        self._nasa_aod_refresh_running = False
        if not self._has_valid_location() or location_key != LightPollutionService._location_key(self._location):
            logger.info("NASA AOD refresh result discarded for a stale location.")
            self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.AOD)
            if self._has_valid_location():
                self._schedule_nasa_aod_refresh()
            return
        if not self._earthdata_credentials_state.connection_verified:
            logger.info("NASA AOD refresh result discarded because Earthdata credentials are no longer verified.")
            self.weatherChanged.emit()
            self._clear_refresh_domains(RefreshDomain.AOD)
            return

        self._mark_refresh_dirty(RefreshReason.AOD_COMPLETED, (RefreshDomain.AOD,))
        previous_result = self._nasa_aod_result
        if isinstance(result, NasaAodResult):
            self._nasa_aod_result = result
        else:
            self._nasa_aod_result = NasaAodResult.failure(
                "parse_error",
                tr("Dati NASA AOD non disponibili al momento."),
            )
        self._log_nasa_aod_result(self._nasa_aod_result)
        if self._nasa_aod_result != previous_result:
            self._recalculate_after_condition_provider_refresh()
        self.weatherChanged.emit()
        self._clear_refresh_domains(RefreshDomain.AOD)

    @staticmethod
    def _log_nasa_aod_result(result: NasaAodResult) -> None:
        if result.available:
            logger.info(
                "NASA AOD refresh ok: product=%s acquisition_date=%s aod_550=%s uncertainty=%s "
                "qa_raw=%s granule=%s method=%s local_valid_pixel_count=%s "
                "neighborhood_radius_pixels=%s nearest_valid_pixel_distance_km=%s cache_hit=%s.",
                result.product,
                result.acquisition_date,
                result.aod_550,
                result.uncertainty,
                result.qa_raw,
                result.granule_id,
                result.method,
                result.local_valid_pixel_count,
                result.neighborhood_radius_pixels,
                result.nearest_valid_pixel_distance_km,
                result.cache_hit,
            )
            return

        logger.info(
            "NASA AOD refresh finished without usable data: status=%s message=%s cache_hit=%s.",
            result.status,
            result.message,
            result.cache_hit,
        )

    def _set_loading(self, value: bool) -> None:
        if self._is_loading == value:
            return
        self._is_loading = value
        self.statusChanged.emit()

    def _recalculate_after_condition_provider_refresh(self) -> None:
        if getattr(self, "_weather_refresh_running", False):
            return
        if getattr(self, "_weather_summary", None) is None:
            return
        self._recalculate_observing_outputs()
        self.dataChanged.emit()
        self.selectedObjectChanged.emit()

    def _append_service_status(self, message: object) -> None:
        if not message:
            return
        if self._service_status:
            if message not in self._service_status:
                self._service_status = join_text([self._service_status, message], " ")
        else:
            self._service_status = message
        self.statusChanged.emit()

    def _mark_refresh_dirty(
        self,
        reason: RefreshReason,
        domains: tuple[RefreshDomain, ...] | None = None,
    ) -> None:
        self._refresh_lifecycle().mark_dirty(reason, domains)

    def _clear_refresh_domains(self, *domains: RefreshDomain) -> None:
        self._refresh_lifecycle().clear_domains(domains)

    def _refresh_lifecycle(self) -> RefreshManager:
        manager = getattr(self, "_refresh_manager", None)
        if manager is None:
            manager = RefreshManager()
            self._refresh_manager = manager
        return manager

    def _apply_equipment_to_current_objects(self) -> None:
        self._refresh_active_profile_dependencies()

    def _refresh_active_profile_dependencies(self, reload_profile_equipment: bool = False) -> None:
        self._mark_refresh_dirty(RefreshReason.EQUIPMENT_CHANGED)
        selected_id = self._selected_object.id if self._selected_object else None
        if reload_profile_equipment:
            self._profile_equipment = self._initial_profile_equipment()
        self._selected_telescope_index = self._initial_telescope_index()
        self._refresh_equipment_recommendations_for_current_objects()
        self._deep_sky = self._apply_deep_sky_pollution_context(self._deep_sky)
        if self._weather_summary:
            self._recalculate_observing_outputs()
        else:
            self._refresh_conditioned_observing_candidates()
            planning_objects = self._home_visible_objects(self._visible_planets + self._deep_sky)
            planning_objects = planning_objects or list(
                unique_targets_by_id(self._visible_planets + self._deep_sky)
            )
            self._best_object = (
                self._select_best_object(planning_objects) if self._weather_summary else None
            )
            self._night_plan = []
            self._refresh_sky_compass()
        if selected_id:
            for item in self._solar_system_objects + self._deep_sky:
                if item.id == selected_id:
                    self._selected_object = item
                    break
        self._clear_refresh_domains(
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        )

    def _refresh_after_catalogue_recommendation_change(self) -> None:
        self._mark_refresh_dirty(RefreshReason.CATALOGUE_RECOMMENDATION_CHANGED)
        selected_id = self._selected_object.id if self._selected_object else None
        selected_source = self._selected_object_source
        self._refresh_equipment_recommendations_for_current_objects()
        self._deep_sky = self._apply_deep_sky_pollution_context(self._deep_sky)
        if self._weather_summary:
            self._recalculate_observing_outputs()
        else:
            self._refresh_conditioned_observing_candidates()
            self._best_object = None
            self._night_plan = []
            self._refresh_sky_compass()

        if selected_id and selected_source == OBSERVING_SOURCE:
            observing_objects = self._solar_system_objects + self._deep_sky
            replacement = next(
                (candidate for candidate in observing_objects if candidate.id == selected_id),
                None,
            )
            if replacement is None:
                suggestion_pool = self._visible_planets + self._deep_sky
                replacement = self._best_object or next(iter(suggestion_pool), None)
            self._selected_object = replacement
            self._selected_object_source = (
                OBSERVING_SOURCE if replacement is not None else ""
            )

        self._clear_refresh_domains(
            RefreshDomain.CATALOG,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        )

    def _emit_profile_dependent_changes(self) -> None:
        self.equipmentChanged.emit()
        self.dataChanged.emit()
        self.weatherChanged.emit()
        self.selectedObjectChanged.emit()

    def _refresh_equipment_recommendations_for_current_objects(self) -> None:
        solar_system_source = self._base_solar_system_objects or self._solar_system_objects
        deep_sky_source = self._base_deep_sky or self._deep_sky
        deep_sky_source = self._recommendation_eligible_objects(deep_sky_source)
        self._equipment_setup_read_models_by_object_id = {}
        self._solar_system_objects = self._apply_equipment(solar_system_source)
        self._visible_planets = [
            item
            for item in self._solar_system_objects
            if item.object_type == "Pianeta"
            and item.visible
            and self._solar_system_monthly_visible_for_home(item)
        ]
        self._deep_sky = self._apply_equipment(deep_sky_source)
        self._refresh_conditioned_observing_candidates()

    def _recommendation_eligible_objects(
        self,
        objects: list[CelestialObject],
    ) -> list[CelestialObject]:
        enabled_by_id = getattr(
            self,
            "_recommendation_enabled_by_object_id",
            {},
        )
        return [
            item
            for item in objects
            if enabled_by_id.get(item.id.strip().casefold(), True)
        ]

    def _apply_location_result(self, result: LocationDetectionResult, persist: bool = True) -> None:
        self._mark_refresh_dirty(RefreshReason.LOCATION_CHANGED)
        self._cancel_astronomy_refresh()
        self._cancel_sky_compass_live_refresh()
        previous_location = self._location
        self._location_detection_result = result
        self._location = result.location
        self._location_message = self._location_result_message(result)
        self._offer_online_location_fallback = False
        if (
            not isinstance(previous_location, ObserverLocation)
            or LightPollutionService._location_key(previous_location)
            != LightPollutionService._location_key(result.location)
        ):
            self._invalidate_condition_provider_refreshes()
            self._reset_location_provider_presentations()
        self._invalidate_catalogue_visibility_cache()
        self._align_catalogue_month_to_location()
        if persist:
            self._location_preferences.save_location(result)
        self.catalogueChanged.emit()
        self._clear_refresh_domains(RefreshDomain.LOCATION)

    @staticmethod
    def _location_result_message(result: LocationDetectionResult) -> str:
        location = result.location
        if result.provider == "manual_city":
            return tr(
                "Posizione impostata su {city}, {country}.",
                city=location.city,
                country=location.country,
            )
        if result.provider == "manual_coordinates":
            return tr(
                "Coordinate impostate: {latitude}, {longitude}.",
                latitude=format_number(location.latitude, decimals=4),
                longitude=format_number(location.longitude, decimals=4),
            )
        if result.provider == "mpc_observatory":
            return result.message or tr("Osservatorio MPC selezionato.")
        if result.provider == "ip_geolocation":
            if result.source.endswith(" cached"):
                return tr(
                    "Ultima posizione caricata: {city}.",
                    city=location.city,
                )
            return tr(
                "Posizione approssimata rilevata tramite connessione internet: {city}, {country}. La precisione può essere limitata.",
                city=location.city,
                country=location.country or tr("sconosciuto"),
            )
        if result.provider in {"windows_precise", "windows_coarse", "geoclue2"}:
            if location.country:
                return tr(
                    "Posizione di sistema acquisita: {city}, {country}.",
                    city=location.city,
                    country=location.country,
                )
            return tr("Posizione di sistema acquisita.")
        return result.message or tr("Posizione caricata.")

    def _reset_location_provider_presentations(self) -> None:
        if self._earthdata_credentials_state.connection_verified:
            self._nasa_aod_result = NasaAodResult.failure(
                "pending",
                tr("Aggiornamento dati NASA AOD per la nuova posizione."),
            )
        else:
            self._nasa_aod_result = NasaAodResult.no_credentials()
        if (
            self._openaq_credentials_state.connection_verified
            and self._openaq_credential_store.api_key()
        ):
            self._local_atmosphere = LocalAtmosphere.failure(
                tr("Aggiornamento dati OpenAQ per la nuova posizione.")
            )
        else:
            self._local_atmosphere = LocalAtmosphere.not_configured()

    def _invalidate_local_atmosphere_refresh(self) -> None:
        self._local_atmosphere_refresh_request_id = (
            getattr(self, "_local_atmosphere_refresh_request_id", 0) + 1
        )
        self._local_atmosphere_refresh_running = False

    def _invalidate_earthdata_provider_refreshes(self) -> None:
        self._viirs_sky_quality_request_id = (
            getattr(self, "_viirs_sky_quality_request_id", 0) + 1
        )
        self._nasa_aod_refresh_request_id = (
            getattr(self, "_nasa_aod_refresh_request_id", 0) + 1
        )
        self._viirs_sky_quality_running = False
        self._nasa_aod_refresh_running = False
        self._light_pollution_status = ""

    def _invalidate_condition_provider_refreshes(self) -> None:
        self._invalidate_local_atmosphere_refresh()
        self._invalidate_earthdata_provider_refreshes()

    def _has_valid_location(self) -> bool:
        location = self._location
        if not isinstance(location, ObserverLocation):
            return False
        return -90 <= location.latitude <= 90 and -180 <= location.longitude <= 180

    def _initialize_startup_location(self) -> None:
        preferences = self._startup_location_preferences
        if preferences.auto_detect_location_on_startup:
            self._start_startup_location_detection()
            return
        elif self._apply_stored_startup_location():
            return

        self._location_detection_result = None
        self._location = None

    def _start_startup_location_detection(self) -> None:
        self._startup_location_detection_request_id += 1
        request_id = self._startup_location_detection_request_id
        preferences = self._startup_location_preferences
        self._startup_location_detection_running = True
        self._location_detection_result = None
        self._location = None
        self._location_message = STARTUP_LOCATION_PENDING_MESSAGE

        def run_detection() -> None:
            result, persist, message = self._resolve_startup_location(preferences)
            self._startupLocationDetectionFinished.emit(request_id, result, persist, message)

        Thread(target=run_detection, daemon=True).start()

    def _resolve_startup_location(self, preferences) -> tuple[LocationDetectionResult | None, bool, str]:
        if preferences.use_system_location_on_startup:
            try:
                return self._location_service.detect_system_location(), True, ""
            except LocationUnavailableError as exc:
                logger.info("System startup location detection unavailable: %s", exc.reason)

        if preferences.allow_approximate_online_location:
            try:
                return self._location_service.detect_ip_location(allow_online=True), True, ""
            except LocationUnavailableError as exc:
                logger.info("Approximate startup location detection unavailable: %s", exc.reason)

        stored = self._stored_startup_location_result()
        if stored:
            return stored
        return (
            None,
            False,
            tr("Configura una località per ottenere meteo e cielo locale."),
        )

    @Slot(int, object, bool, object)
    def _finish_startup_location_detection(
        self,
        request_id: int,
        result: object,
        persist: bool,
        message: object,
    ) -> None:
        if request_id != self._startup_location_detection_request_id:
            return

        self._startup_location_detection_running = False
        if isinstance(result, LocationDetectionResult) and self._result_has_valid_location(result):
            self._apply_location_result(result, persist=persist)
            if message:
                self._location_message = message
        else:
            self._location_detection_result = None
            self._location = None
            self._location_message = message or tr(
                "Configura una località per ottenere meteo e cielo locale."
            )

        self._refresh_all()
        self.locationChanged.emit()

    def _cancel_startup_location_detection(self) -> None:
        if not self._startup_location_detection_running:
            return
        self._startup_location_detection_running = False
        self._startup_location_detection_request_id += 1
        self._light_pollution_status = ""

    def _apply_stored_startup_location(self) -> bool:
        stored = self._stored_startup_location_result()
        if stored:
            result, persist, message = stored
            self._apply_location_result(result, persist=persist)
            self._location_message = message
            return True

        return False

    def _stored_startup_location_result(self) -> tuple[LocationDetectionResult, bool, str] | None:
        saved = self._location_preferences.saved_location()
        if saved and self._result_has_valid_location(saved):
            return (
                saved,
                False,
                tr(
                    "Posizione salvata caricata: {city}.",
                    city=saved.location.city,
                ),
            )

        cached = self._location_preferences.cached_location()
        if cached and self._result_has_valid_location(cached):
            return (
                cached,
                False,
                tr(
                    "Ultima posizione caricata: {city}.",
                    city=cached.location.city,
                ),
            )

        return None

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
        use_system_location_on_startup: bool | None = None,
        use_windows_location_on_startup: bool | None = None,
    ) -> None:
        self._startup_location_preferences = self._location_preferences.update_preferences(
            auto_detect_location_on_startup=auto_detect_location_on_startup,
            allow_approximate_online_location=allow_approximate_online_location,
            use_system_location_on_startup=use_system_location_on_startup,
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
            "windows_precise": tr("Posizione di sistema"),
            "windows_coarse": tr("Posizione di sistema approssimata"),
            "geoclue2": tr("Posizione di sistema"),
            "ip_geolocation": tr("Online approssimata"),
            "manual_city": tr("Città manuale"),
            "mpc_observatory": tr("Osservatorio MPC"),
            "manual_coordinates": tr("Coordinate manuali"),
            "cached": tr("Posizione salvata"),
        }
        return labels.get(provider, provider or tr("Nessuna posizione"))

    @staticmethod
    def _location_accuracy_label(result: LocationDetectionResult) -> str:
        raw = presentation_text(result.accuracy, strip=True)
        if re.fullmatch(r"\d+(?:[.,]\d+)?\s*m", raw):
            return raw
        labels = {
            "windows_precise": tr("precisa"),
            "windows_coarse": tr("approssimata"),
            "geoclue2": tr("fornita dal sistema"),
            "ip_geolocation": tr("livello città"),
            "manual_city": tr("coordinate della città"),
            "mpc_observatory": tr("coordinate MPC"),
            "manual_coordinates": tr("fornita dall'utente"),
            "cached": tr("salvata"),
        }
        return labels.get(result.provider, result.accuracy or tr("n/d"))

    def _apply_equipment(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        telescopes = self._active_profile_telescopes()
        eyepieces = self._active_profile_eyepieces()
        barlows = self._active_profile_barlows()
        binoculars = self._active_profile_binoculars()
        updated = []
        for item in objects:
            suggestion = self._equipment_service.suggest_for_profile(
                item,
                telescopes,
                eyepieces,
                barlows,
                self._seeing_transparency,
                self._sky_quality,
                binoculars,
            )
            setup_read_model = self._equipment_setup_read_model_builder.from_suggestion(item, suggestion)
            setup_models = getattr(self, "_equipment_setup_read_models_by_object_id", None)
            if setup_models is None:
                setup_models = {}
                self._equipment_setup_read_models_by_object_id = setup_models
            setup_models[item.id] = setup_read_model
            naked_eye_blocked = (
                not telescopes
                and not binoculars
                and setup_read_model.requires_optical_instrument
            )
            setup_updates = setup_read_model.to_celestial_object_updates()
            updated.append(
                self._apply_object_content(
                    replace(
                        item,
                        visible=item.visible and not naked_eye_blocked,
                        score=max(0, item.score - 45) if naked_eye_blocked else item.score,
                        **setup_updates,
                    )
                )
            )
        return updated

    def _apply_object_content(self, item: CelestialObject) -> CelestialObject:
        image = self._object_image_map.get(item.id)
        description = self._object_descriptions.get(item.id)
        catalogue_item = self._catalogue_item_for_object_id(item.id)
        if not image and catalogue_item and not self._is_solar_system_catalogue_item(catalogue_item):
            if "galaxy" in item.object_type.lower() or "galassia" in item.object_type.lower():
                image = self._object_image_map.get("messier-default-galaxy")
            elif any(
                fragment in item.object_type.lower()
                for fragment in ("nebula", "nebul", "remnant")
            ):
                image = self._object_image_map.get("messier-default-nebula")
            else:
                image = self._object_image_map.get("messier-default-cluster")
        notes = item.notes
        if description:
            observing_notes = presentation_text(
                description["observing_notes"], strip=True
            )
            if observing_notes and observing_notes not in notes:
                notes = join_text([observing_notes, item.notes], " ")
        return replace(
            item,
            image=image["image_path"] if image else item.image,
            notes=notes,
            best_filter_class=(
                item.best_filter_class
                or str((catalogue_item or {}).get("best_filter_class") or "")
            ),
            fallback_filter_class=(
                item.fallback_filter_class
                or str((catalogue_item or {}).get("fallback_filter_class") or "")
            ),
            optional_color_filter_class=(
                item.optional_color_filter_class
                or str((catalogue_item or {}).get("optional_color_filter_class") or "")
            ),
            imaging_reducer_recommended=(
                item.imaging_reducer_recommended
                or bool(
                    (catalogue_item or {}).get("imaging_reducer_recommended")
                )
            ),
        )

    def _apply_deep_sky_pollution_context(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        self._deep_sky_raw_condition_input_by_id = {item.id: item for item in objects}
        conditioned = self._conditions_service.condition_deep_sky_pollution_context(
            objects,
            self._sky_quality,
            self._build_observation_condition_inputs(include_moon=False),
        )
        builder = self._conditions_read_model_builder_instance()
        self._deep_sky_pollution_read_model = list(
            builder.from_conditioned_targets(
                conditioned,
                source="deep_sky_pollution_context",
                raw_targets_by_id=self._deep_sky_raw_condition_input_by_id,
            )
        )
        return [model.display_target for model in self._deep_sky_pollution_read_model]

    def _conditions_read_model_builder_instance(self) -> ObservationConditionsReadModelBuilder:
        builder = getattr(self, "_conditions_read_model_builder", None)
        if builder is None:
            builder = ObservationConditionsReadModelBuilder()
            self._conditions_read_model_builder = builder
        return builder

    def _deep_sky_pollution_base_penalty(self) -> float:
        return self._conditions_service.deep_sky_pollution_base_penalty(self._sky_quality)

    def _home_visible_objects(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        return list(
            unique_targets_by_id(
                item
                for item in objects
                if self._first_observing_datetime(item.best_time)
                or self._first_observing_datetime(item.observing_window)
            )
        )

    def _tonight_target_pool(self) -> list[CelestialObject]:
        candidates = self._home_visible_objects(self._visible_planets)
        candidates.extend(self._conditioned_deep_sky_candidates())
        return list(unique_targets_by_id(candidates))

    def _home_visible_alternative_payloads(
        self,
        target_pool: list[CelestialObject] | None = None,
    ) -> list[dict]:
        plan_ids = {item.object_id for item in self._night_plan}
        alternatives = [
            item
            for item in (target_pool if target_pool is not None else self._tonight_target_pool())
            if item.id not in plan_ids
        ]
        payload = []
        for item in sorted(alternatives, key=self._home_alternative_sort_key):
            data = self._object_to_qml(item)
            is_planet = item.object_type == "Pianeta"
            data["homeCategory"] = "planet" if is_planet else "deep_sky"
            data["homeCategoryLabel"] = (
                tr("Pianeta") if is_planet else tr("Cielo profondo")
            )
            payload.append(data)
        return payload

    def _home_alternative_sort_key(
        self, item: CelestialObject
    ) -> tuple[int, int, int, tuple[tuple[int, int | str], ...]]:
        window_start = self._first_observing_datetime(item.observing_window)
        best_time = self._first_observing_datetime(item.best_time)
        window_order = self._home_alternative_time_order(window_start or best_time)
        best_time_order = self._home_alternative_time_order(best_time)
        category_order = 0 if item.object_type == "Pianeta" else 1
        return (
            window_order,
            best_time_order,
            category_order,
            self._natural_name_sort_key(item.name),
        )

    @staticmethod
    def _natural_name_sort_key(value: str) -> tuple[tuple[int, int | str], ...]:
        return tuple(
            (1, int(part)) if part.isdigit() else (0, part.casefold())
            for part in re.split(r"(\d+)", value)
            if part
        )

    def _home_alternative_time_order(self, target_time: datetime | None) -> int:
        if target_time is None:
            return 10_000
        window = getattr(self, "_observing_night_window", None)
        if window is not None and window.start is not None:
            return round((target_time - window.start).total_seconds() / 60)
        hour = (target_time.hour + 24) if target_time.hour < 12 else target_time.hour
        return hour * 60 + target_time.minute

    def _solar_system_monthly_visible_for_home(self, item: CelestialObject) -> bool:
        visibility = self._catalogue_month_visible_for_object(item.id)
        return visibility is not False

    def _catalogue_month_visible_for_object(self, object_id: str) -> bool | None:
        item = self._catalogue_item_for_object_id(object_id)
        if not item or not self._has_valid_location():
            return None
        visibility = self._catalogue_visibility_map()
        catalogue_object_id = str(item.get("object_id", ""))
        if catalogue_object_id not in visibility:
            return None
        return bool(visibility[catalogue_object_id])

    def _load_catalogue_objects(self) -> list[dict]:
        objects = [
            self._catalogue_item_from_record(row)
            for row in self._catalogue_repository.list_objects()
        ]
        objects.extend(self._solar_system_catalogue_objects())
        return sorted(objects, key=self._catalogue_sort_key)

    @staticmethod
    def _catalogue_item_from_record(row: dict) -> dict:
        object_id = str(row["object_id"])
        recommendation_enabled_by_default = bool(
            row.get("recommendation_enabled_by_default", True)
        )
        primary_catalogue = str(row.get("primary_catalogue") or "")
        primary_designation = str(row.get("primary_designation") or object_id)
        designations = [dict(item) for item in row.get("designations", [])]
        catalogues = [str(item) for item in row.get("catalogues", [])]
        recommendation_editable = bool(
            RECOMMENDATION_EDITABLE_CATALOGUES.intersection(catalogues)
        )
        designation_labels = [
            f"{item['catalogue']} {item['designation']}".strip()
            for item in designations
        ]
        search_terms = " ".join(
            (
                object_id,
                str(row.get("name") or ""),
                *designation_labels,
                *(str(item.get("designation") or "") for item in designations),
            )
        ).strip()
        return {
            "catalogue": primary_catalogue,
            "object_id": object_id,
            "id": object_id,
            "catalogue_id": primary_designation,
            "catalogues": catalogues,
            "designations": designations,
            "designation_labels": designation_labels,
            "name": row["name"] or "",
            "type": row["object_type"] or "",
            "constellation": row["constellation"] or "",
            "magnitude": row["magnitude"],
            "magnitude_label": AppController._format_catalogue_number(row["magnitude"]),
            "right_ascension": row["ra"] or "",
            "declination": row["dec"] or "",
            "apparent_size": row["apparent_size"] or "",
            "max_angular_size_deg": row["max_angular_size_deg"],
            "max_angular_size_label": AppController._format_catalogue_angle(row["max_angular_size_deg"]),
            "recommended_observation_type": row["recommended_observation_type"] or "",
            "best_filter_class": row.get("best_filter_class") or "",
            "fallback_filter_class": row.get("fallback_filter_class") or "",
            "optional_color_filter_class": row.get("optional_color_filter_class") or "",
            "imaging_reducer_recommended": bool(
                row.get("imaging_reducer_recommended")
            ),
            "recommendation_enabled_by_default": recommendation_enabled_by_default,
            "recommendation_enabled": bool(
                row.get(
                    "recommendation_enabled",
                    recommendation_enabled_by_default,
                )
            ),
            "recommendation_editable": recommendation_editable,
            "description": row["description"] or "",
            "search_terms": search_terms,
            "catalogue_sort_index": row.get("primary_sort_index"),
        }

    def _solar_system_catalogue_objects(self) -> list[dict]:
        return [
            self._catalogue_item_from_solar_system(config, sort_index)
            for sort_index, config in enumerate(SkyfieldAstronomyEngine.BODY_CONFIGS, start=1)
        ]

    def _catalogue_item_from_solar_system(self, config, sort_index: int) -> dict:
        observation_type = ""
        if config.object_id == "moon":
            observation_type = "General"
        elif config.object_type == "Pianeta":
            observation_type = "HighMagnification"
        description = self._object_descriptions.get(config.object_id, {})
        best_filter_class, fallback_filter_class, optional_color_filter_class = (
            SOLAR_SYSTEM_FILTER_PREFERENCES.get(config.object_id, ("", "", ""))
        )
        display_id = f"S{sort_index}"
        return {
            "catalogue": SOLAR_SYSTEM_CATALOGUE,
            "object_id": config.object_id,
            "id": config.object_id,
            "catalogue_id": display_id,
            "catalogues": [SOLAR_SYSTEM_CATALOGUE],
            "designations": [
                {
                    "catalogue": SOLAR_SYSTEM_CATALOGUE,
                    "designation": display_id,
                    "sort_index": sort_index,
                    "is_primary": True,
                }
            ],
            "designation_labels": [f"{SOLAR_SYSTEM_CATALOGUE} {display_id}"],
            "name": config.name,
            "type": config.object_type,
            "constellation": "",
            "magnitude": None,
            "magnitude_label": "",
            "right_ascension": "",
            "declination": "",
            "apparent_size": "",
            "max_angular_size_deg": None,
            "max_angular_size_label": "",
            "recommended_observation_type": observation_type,
            "best_filter_class": best_filter_class,
            "fallback_filter_class": fallback_filter_class,
            "optional_color_filter_class": optional_color_filter_class,
            "imaging_reducer_recommended": False,
            "recommendation_enabled_by_default": True,
            "recommendation_enabled": True,
            "recommendation_editable": False,
            "description": presentation_text(
                description.get("short_description", ""), strip=True
            ),
            "image": config.image,
            "solar_system_body_id": config.object_id,
            "search_terms": self._solar_system_search_terms(config.object_id, config.name, display_id),
            "catalogue_sort_index": sort_index,
        }

    @staticmethod
    def _solar_system_search_terms(object_id: str, name: str, display_id: str) -> str:
        english_names = {
            "sun": "Sun",
            "moon": "Moon",
            "mercury": "Mercury",
            "venus": "Venus",
            "mars": "Mars",
            "jupiter": "Jupiter",
            "saturn": "Saturn",
            "uranus": "Uranus",
            "neptune": "Neptune",
        }
        return " ".join((display_id, f"solar-{object_id}", object_id, name, english_names.get(object_id, ""))).strip()

    @staticmethod
    def _catalogue_sort_key(item: dict) -> tuple[str, int, str]:
        catalogue_id = str(item.get("catalogue_id", ""))
        match = re.search(r"\d+", catalogue_id)
        explicit_sort_index = item.get("catalogue_sort_index")
        if explicit_sort_index is not None:
            numeric_id = int(explicit_sort_index)
        elif match:
            numeric_id = int(match.group(0))
        else:
            numeric_id = 999_999
        return (str(item.get("catalogue", "")).casefold(), numeric_id, catalogue_id.casefold())

    def _filtered_catalogue_objects(self) -> list[dict]:
        query = self._catalogue_search_query.casefold()
        objects = self._catalogue_objects
        if query:
            objects = [
                item
                for item in objects
                if query in item["catalogue_id"].casefold()
                or query in render_text(item["name"]).casefold()
                or query
                in render_text(
                    content_text(
                        "catalogue_objects",
                        str(item.get("object_id", "")),
                        "name",
                        item.get("name", ""),
                    )
                ).casefold()
                or query in str(item.get("search_terms", "")).casefold()
            ]

        catalogue_filter = self._catalogue_filters.get("catalogue", CATALOGUE_ALL_FILTER)
        if catalogue_filter != CATALOGUE_ALL_FILTER:
            objects = [
                projected
                for item in objects
                if (projected := self._catalogue_item_for_catalogue(item, catalogue_filter))
                is not None
            ]

        for filter_name, field_name in (
            ("type", "type"),
            ("constellation", "constellation"),
            ("observation_type", "recommended_observation_type"),
        ):
            value = self._catalogue_filters.get(filter_name, CATALOGUE_ALL_FILTER)
            if value != CATALOGUE_ALL_FILTER:
                objects = [item for item in objects if item[field_name] == value]

        visibility = self._catalogue_visibility_map() if self._catalogue_visible_this_month_only else {}
        observability = self._catalogue_observability_map()
        visible_objects = [self._catalogue_item_with_visibility(item, visibility, observability) for item in objects]
        if self._catalogue_visible_this_month_only:
            visible_objects = [item for item in visible_objects if item["visible_this_month"]]
        if query:
            return sorted(
                visible_objects,
                key=lambda item: self._catalogue_search_sort_key(item, query),
            )
        return sorted(visible_objects, key=self._catalogue_sort_key)

    @classmethod
    def _catalogue_search_sort_key(cls, item: dict, query: str) -> tuple[int, str, int, str]:
        candidates = [
            str(item.get("catalogue_id") or ""),
            str(item.get("name") or ""),
            str(item.get("object_id") or ""),
            *(
                str(designation.get("designation") or "")
                for designation in item.get("designations", [])
            ),
        ]
        normalized = [candidate.casefold() for candidate in candidates if candidate]
        if query in normalized:
            match_rank = 0
        elif any(candidate.startswith(query) for candidate in normalized):
            match_rank = 1
        else:
            match_rank = 2
        catalogue, numeric_id, catalogue_id = cls._catalogue_sort_key(item)
        return match_rank, catalogue, numeric_id, catalogue_id

    @staticmethod
    def _catalogue_item_for_catalogue(item: dict, catalogue: str) -> dict | None:
        normalized = catalogue.strip().casefold()
        designation = next(
            (
                candidate
                for candidate in item.get("designations", [])
                if str(candidate.get("catalogue", "")).strip().casefold() == normalized
            ),
            None,
        )
        if designation is None:
            return None
        projected = dict(item)
        projected["catalogue"] = str(designation.get("catalogue") or "")
        projected["catalogue_id"] = str(designation.get("designation") or "")
        projected["catalogue_sort_index"] = designation.get("sort_index")
        return projected

    def _catalogue_item_with_visibility(
        self,
        item: dict,
        visibility: dict[str, bool],
        observability: dict[str, dict[str, bool | None]],
    ) -> dict:
        object_id = str(item.get("object_id", ""))
        has_location = self._has_valid_location()
        visible_value: bool | None = (
            bool(visibility[object_id])
            if self._catalogue_visible_this_month_only and has_location and object_id in visibility
            else None
        )
        observability_values = observability.get(object_id, {}) if has_location else {}
        geometric_value = observability_values.get("is_geometrically_observable")
        useful_value = observability_values.get("is_usefully_observable")
        data = dict(item)
        data["catalogue_label"] = self._catalogue_label(
            str(item.get("catalogue", ""))
        )
        if item.get("solar_system_body_id"):
            data["name"] = presentation_text(item.get("name", ""), strip=True)
            data["description"] = presentation_text(
                item.get("description", ""), strip=True
            )
        else:
            data["name"] = content_text(
                "catalogue_objects",
                object_id,
                "name",
                item.get("name", ""),
            )
            data["description"] = content_text(
                "catalogue_objects",
                object_id,
                "description",
                item.get("description", ""),
            )
        data["constellation_label"] = catalogue_constellation_label(
            str(item.get("constellation", ""))
        )
        data["is_geometrically_observable"] = geometric_value is True
        data["is_geometrically_observable_known"] = geometric_value is not None
        data["is_geometrically_observable_label"] = self._catalogue_boolean_label(geometric_value)
        data["is_usefully_observable"] = useful_value is True
        data["is_usefully_observable_known"] = useful_value is not None
        data["is_usefully_observable_label"] = self._catalogue_boolean_label(useful_value)
        data["observable"] = data["is_usefully_observable"]
        data["observable_known"] = data["is_usefully_observable_known"]
        data["observable_label"] = data["is_usefully_observable_label"]
        data["visible_this_month"] = visible_value is True
        data["visible_this_month_label"] = self._catalogue_boolean_label(visible_value)
        data["visibility_month_label"] = self._catalogue_month_label(self._catalogue_selected_month)
        data["type_label"] = catalogue_object_type_label(str(item.get("type", "")))
        data["recommended_observation_type_label"] = catalogue_observation_type_label(
            str(item.get("recommended_observation_type", ""))
        )
        return data

    def _catalogue_visibility_map(self) -> dict[str, bool]:
        if not self._has_valid_location():
            return {}
        cache_key = self._catalogue_visibility_cache_key()
        cached = self._catalogue_visibility_cache.get(cache_key)
        if cached is not None:
            return cached

        visibility_method = getattr(self._astronomy_engine, "catalogue_month_visibility", None)
        if not callable(visibility_method):
            self._catalogue_visibility_cache[cache_key] = {}
            return {}
        try:
            with self._astronomy_engine_lock_instance():
                visibility = visibility_method(
                    self._catalogue_objects,
                    self._location,
                    self._catalogue_year,
                    self._catalogue_selected_month,
                    CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
                )
        except Exception:
            logger.warning("Catalogue monthly visibility calculation failed.", exc_info=True)
            visibility = {}
        normalized_visibility = {str(object_id): bool(visible) for object_id, visible in visibility.items()}
        self._catalogue_visibility_cache[cache_key] = normalized_visibility
        return normalized_visibility

    def _catalogue_visibility_cache_key(self) -> tuple[float, float, str, int, int, float]:
        location = self._location
        if not isinstance(location, ObserverLocation):
            return (0.0, 0.0, "", self._catalogue_year, self._catalogue_selected_month, CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG)
        return (
            round(location.latitude, 5),
            round(location.longitude, 5),
            location.timezone,
            self._catalogue_year,
            self._catalogue_selected_month,
            CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
        )

    def _catalogue_observability_map(self) -> dict[str, dict[str, bool | None]]:
        if not self._has_valid_location():
            return {}
        cache_key = self._catalogue_observability_cache_key()
        cached = self._catalogue_observability_cache.get(cache_key)
        if cached is not None:
            return cached

        location = self._location
        observability: dict[str, dict[str, bool | None]] = {}
        for item in self._catalogue_objects:
            object_id = str(item.get("object_id", ""))
            if not object_id:
                continue
            observability[object_id] = self._catalogue_item_observability(item, location)
        self._catalogue_observability_cache[cache_key] = observability
        return observability

    def _catalogue_observability_cache_key(self) -> tuple[float, float, str, float]:
        location = self._location
        if not isinstance(location, ObserverLocation):
            return (0.0, 0.0, "", CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG)
        return (
            round(location.latitude, 5),
            round(location.longitude, 5),
            location.timezone,
            CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
        )

    @staticmethod
    def _catalogue_item_observability(
        item: dict,
        location: ObserverLocation | None,
    ) -> dict[str, bool | None]:
        if not isinstance(location, ObserverLocation):
            return {"is_geometrically_observable": None, "is_usefully_observable": None}
        if item.get("solar_system_body_id"):
            return {"is_geometrically_observable": None, "is_usefully_observable": None}
        try:
            dec_degrees = parse_dec_degrees(str(item.get("dec") or item.get("declination") or ""))
        except ValueError:
            return {"is_geometrically_observable": None, "is_usefully_observable": None}
        theoretical_max_altitude = 90.0 - abs(location.latitude - dec_degrees)
        return {
            "is_geometrically_observable": theoretical_max_altitude > 0.0,
            "is_usefully_observable": theoretical_max_altitude >= CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
        }

    @staticmethod
    def _catalogue_boolean_label(value: bool | None) -> str:
        if value is True:
            return tr("Sì")
        if value is False:
            return tr("No")
        return "—"

    def _invalidate_catalogue_visibility_cache(self) -> None:
        self._invalidate_catalogue_month_visibility_cache()
        self._catalogue_current_month_visibility_cache.clear()
        self._invalidate_catalogue_observability_cache()
        self._clear_refresh_domains(RefreshDomain.CATALOG)

    def _invalidate_catalogue_month_visibility_cache(self) -> None:
        self._catalogue_visibility_cache.clear()

    def _invalidate_catalogue_observability_cache(self) -> None:
        self._catalogue_observability_cache.clear()

    def _catalogue_option_values(self, field_name: str) -> list[str]:
        if field_name == "catalogue":
            values = {
                str(catalogue).strip()
                for item in self._catalogue_objects
                for catalogue in item.get("catalogues", [])
            }
        else:
            values = {str(item.get(field_name, "")).strip() for item in self._catalogue_objects}
        return sorted((value for value in values if value), key=str.casefold)

    def _catalogue_current_year(self) -> int:
        return datetime.now(self._zone()).year

    def _catalogue_current_month(self) -> int:
        return datetime.now(self._zone()).month

    def _align_catalogue_month_to_location(self) -> None:
        now = datetime.now(self._zone())
        selected_month = self._catalogue_selected_month
        if not getattr(self, "_catalogue_month_user_selected", False):
            selected_month = now.month
        if self._catalogue_year == now.year and self._catalogue_selected_month == selected_month:
            return
        self._catalogue_year = now.year
        self._catalogue_selected_month = selected_month
        self._invalidate_catalogue_month_visibility_cache()

    def _catalogue_month_label(self, month: int) -> str:
        if month < 1 or month > 12:
            month = self._catalogue_selected_month
        return format_month_year(month, self._catalogue_year)

    @staticmethod
    def _catalogue_label(value: str) -> str:
        return tr("Sistema Solare") if value == SOLAR_SYSTEM_CATALOGUE else value

    @staticmethod
    def _normalize_catalogue_filter_name(filter_name: str) -> str:
        normalized = filter_name.strip().casefold()
        aliases = {
            "catalogue": "catalogue",
            "catalog": "catalogue",
            "type": "type",
            "object_type": "type",
            "constellation": "constellation",
            "observation_type": "observation_type",
            "recommended_observation_type": "observation_type",
        }
        return aliases.get(normalized, "")

    def _catalogue_item_for_object_id(self, object_id: str) -> dict | None:
        normalized = object_id.strip()
        if not normalized:
            return None
        index = getattr(self, "_catalogue_identifier_index", None)
        if index is None:
            index = self._build_catalogue_identifier_index(
                list(getattr(self, "_catalogue_objects", []))
            )
            self._catalogue_identifier_index = index
        return index.get(normalized.casefold())

    def _catalogue_item_for_active_filter(self, item: dict) -> dict:
        catalogue = self._catalogue_filters.get("catalogue", CATALOGUE_ALL_FILTER)
        if catalogue == CATALOGUE_ALL_FILTER:
            return item
        return self._catalogue_item_for_catalogue(item, catalogue) or item

    @staticmethod
    def _build_catalogue_identifier_index(objects: list[dict]) -> dict[str, dict]:
        index: dict[str, dict] = {}
        for item in objects:
            identifiers = {
                str(item.get("object_id") or "").strip(),
                str(item.get("id") or "").strip(),
                str(item.get("catalogue_id") or "").strip(),
            }
            for designation in item.get("designations", []):
                catalogue = str(designation.get("catalogue") or "").strip()
                value = str(designation.get("designation") or "").strip()
                identifiers.add(value)
                if catalogue and value:
                    identifiers.add(f"{catalogue}-{value}")
            for identifier in identifiers:
                if identifier:
                    index.setdefault(identifier.casefold(), item)
        return index

    def _catalogue_item_to_detail_object(self, item: dict) -> CelestialObject:
        if self._is_solar_system_catalogue_item(item):
            return self._solar_system_catalogue_detail_object(item)
        name = content_text(
            "catalogue_objects",
            str(item["object_id"]),
            "name",
            item["name"],
        )
        display_name = catalogue_display_name(str(item["catalogue_id"]), name)
        catalogue_label = tr(
            "Catalogo {catalogue}",
            catalogue=self._catalogue_label(str(item["catalogue"])),
        )
        return self._apply_object_content(
            CelestialObject(
                id=item["object_id"],
                name=display_name,
                object_type=item["type"],
                image="resources/images/m13.svg",
                magnitude=self._format_catalogue_number(item["magnitude"]),
                distance=tr("n/d"),
                max_altitude=tr("n/d"),
                direction=tr("n/d"),
                best_time=tr("n/d"),
                observing_window=tr("n/d"),
                notes=content_text(
                    "catalogue_objects",
                    str(item["object_id"]),
                    "description",
                    item["description"],
                ),
                recommended_setup="",
                visibility_class=catalogue_label,
                azimuth=tr("n/d"),
                time_above_horizon=tr("n/d"),
                visible=True,
                score=0,
                score_label=tr("n/d"),
                difficulty=tr("n/d"),
                apparent_size=item["apparent_size"],
                max_angular_size_deg=item["max_angular_size_deg"],
                recommended_observation_type=item["recommended_observation_type"],
                best_filter_class=item.get("best_filter_class", ""),
                fallback_filter_class=item.get("fallback_filter_class", ""),
                optional_color_filter_class=item.get("optional_color_filter_class", ""),
                imaging_reducer_recommended=bool(
                    item.get("imaging_reducer_recommended")
                ),
                detail_source=CATALOGUE_SOURCE,
            )
        )

    @staticmethod
    def _is_solar_system_catalogue_item(item: dict) -> bool:
        return str(item.get("catalogue", "")) == SOLAR_SYSTEM_CATALOGUE

    def _solar_system_catalogue_detail_object(self, item: dict) -> CelestialObject:
        catalogue_label = tr(
            "Catalogo {catalogue}",
            catalogue=self._catalogue_label(str(item["catalogue"])),
        )
        existing = self._solar_system_detail_source(str(item["object_id"]))
        if existing:
            return replace(
                existing,
                visibility_class=catalogue_label,
                recommended_setup="",
                score=0,
                score_label=tr("n/d"),
                difficulty=tr("n/d"),
                setup_options=[],
                equipment_explanation="",
                best_filter_class=item.get("best_filter_class", ""),
                fallback_filter_class=item.get("fallback_filter_class", ""),
                optional_color_filter_class=item.get("optional_color_filter_class", ""),
                imaging_reducer_recommended=False,
                detail_source=CATALOGUE_SOURCE,
            )
        return self._apply_object_content(
            CelestialObject(
                id=item["object_id"],
                name=presentation_text(item["name"], strip=True),
                object_type=item["type"],
                image=str(item.get("image") or "resources/images/m13.svg"),
                magnitude="",
                distance=tr("n/d"),
                max_altitude=tr("n/d"),
                direction=tr("n/d"),
                best_time=tr("n/d"),
                observing_window=tr("n/d"),
                notes=item["description"],
                recommended_setup="",
                visibility_class=catalogue_label,
                azimuth=tr("n/d"),
                time_above_horizon=tr("n/d"),
                visible=True,
                score=0,
                score_label=tr("n/d"),
                difficulty=tr("n/d"),
                apparent_size="",
                max_angular_size_deg=None,
                recommended_observation_type=item["recommended_observation_type"],
                best_filter_class=item.get("best_filter_class", ""),
                fallback_filter_class=item.get("fallback_filter_class", ""),
                optional_color_filter_class=item.get("optional_color_filter_class", ""),
                imaging_reducer_recommended=False,
                detail_source=CATALOGUE_SOURCE,
            )
        )

    def _solar_system_detail_source(self, object_id: str) -> CelestialObject | None:
        for candidates in (
            self._solar_system_objects,
            self._base_solar_system_objects,
        ):
            for candidate in candidates:
                if candidate.id == object_id:
                    return candidate
        return None

    @staticmethod
    def _format_catalogue_number(value: object) -> str:
        if value is None:
            return tr("n/d")
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        normalized = f"{number:g}"
        decimals = len(normalized.partition(".")[2]) if "e" not in normalized.lower() else 2
        return format_number(number, decimals=decimals)

    @staticmethod
    def _format_catalogue_angle(value: object) -> str:
        if value is None:
            return tr("n/d")
        try:
            number = float(value)
        except (TypeError, ValueError):
            return str(value)
        normalized = f"{number:g}"
        decimals = len(normalized.partition(".")[2]) if "e" not in normalized.lower() else 2
        return tr(
            "{value}°",
            value=format_number(number, decimals=decimals),
        )

    @staticmethod
    def _is_catalogue_detail_object(item: CelestialObject) -> bool:
        return item.detail_source == CATALOGUE_SOURCE

    def _refresh_conditioned_observing_candidates(self) -> None:
        conditioned_deep_sky_read_model = self._recommended_deep_sky_read_models(
            self._home_visible_objects(self._deep_sky)
        )
        conditioned_deep_sky = [
            model.qml_display_target for model in conditioned_deep_sky_read_model
        ]
        self._conditioned_deep_sky = conditioned_deep_sky
        self._conditioned_deep_sky_read_model = list(conditioned_deep_sky_read_model)
        visible_planets = self._home_visible_objects(self._visible_planets)
        self._conditioned_home_objects = list(
            unique_targets_by_id(visible_planets + conditioned_deep_sky)
        )
        visible_planet_read_model = self._conditions_read_model_builder_instance().from_display_targets(
            visible_planets,
            source="home_observing_candidates_planets",
            raw_targets_by_id=self._conditioned_raw_targets_by_id(),
        )
        self._conditioned_home_read_model = list(
            unique_targets_by_id(
                (*visible_planet_read_model, *conditioned_deep_sky_read_model)
            )
        )

    def _recommended_deep_sky_candidates(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        return [
            model.qml_display_target
            for model in self._recommended_deep_sky_read_models(objects)
        ]

    def _recommended_deep_sky_read_models(
        self,
        objects: list[CelestialObject],
    ) -> tuple[ObservationConditionedTargetReadModel, ...]:
        raw_targets_by_id = self._conditioned_raw_targets_by_id()
        builder = self._conditions_read_model_builder_instance()
        candidate_read_models = builder.from_display_targets(
            objects,
            source="home_recommended_deep_sky_nsom_raw_observable_order",
            raw_targets_by_id=raw_targets_by_id,
        )
        ranked_nsom_targets = self._home_recommended_deep_sky_nsom_ranking_service.rank_by_observable_target_value(
            [model.nsom_target_input for model in candidate_read_models],
            condition_inputs=self._build_observation_condition_inputs(),
            moon_geometry_by_object_id=self._planner_moon_geometry_inputs(
                [model.nsom_target_input for model in candidate_read_models]
            ),
        )
        models_by_raw_id = {model.nsom_target_input.id: model for model in candidate_read_models}
        return tuple(
            models_by_raw_id[target.id]
            for target in ranked_nsom_targets
            if target.id in models_by_raw_id
        )

    def _conditioned_deep_sky_candidates(self) -> list[CelestialObject]:
        if not hasattr(self, "_conditioned_deep_sky"):
            self._refresh_conditioned_observing_candidates()
        if not self._conditioned_deep_sky and self._home_visible_objects(self._deep_sky):
            self._refresh_conditioned_observing_candidates()
        return list(self._conditioned_deep_sky)

    def _conditioned_deep_sky_nsom_targets(self) -> list[CelestialObject]:
        if not hasattr(self, "_conditioned_deep_sky_read_model"):
            self._refresh_conditioned_observing_candidates()
        return [model.nsom_target_input for model in self._conditioned_deep_sky_read_model]

    def _conditioned_raw_targets_by_id(self) -> dict[str, CelestialObject]:
        raw_targets = dict(getattr(self, "_deep_sky_raw_condition_input_by_id", {}))
        raw_targets.update({item.id: item for item in getattr(self, "_visible_planets", [])})
        return raw_targets

    def _moon_adjusted_objects(self, objects: list[CelestialObject]) -> list[CelestialObject]:
        conditioned = self._conditions_service.condition_targets(
            objects,
            self._build_observation_condition_inputs(include_sky_quality=False),
            apply_moon=True,
        )
        return sorted((item.target for item in conditioned), key=lambda item: item.score, reverse=True)

    def _moon_adjusted_object(self, item: CelestialObject) -> CelestialObject:
        return self._conditions_service.condition_target(
            item,
            self._build_observation_condition_inputs(include_sky_quality=False),
            apply_moon=True,
        ).target

    def _build_observation_condition_inputs(
        self,
        *,
        include_moon: bool = True,
        include_sky_quality: bool = True,
        target: object | None = None,
    ) -> ObservationConditionInputs:
        return ObservationConditionInputs(
            moon=getattr(self, "_moon", None) if include_moon else None,
            sky_quality=getattr(self, "_sky_quality", None) if include_sky_quality else None,
            seeing=getattr(self, "_seeing_transparency", None),
            aod=self._aod_condition_input(),
            particulate=self._particulate_condition_input(),
            moon_geometry=self._moon_geometry_condition_input(target),
        )

    def _aod_condition_input(self) -> AodConditionInput | None:
        result = getattr(self, "_nasa_aod_result", None)
        if not isinstance(result, NasaAodResult) or not result.available or result.aod_550 is None:
            return None
        age_days = self._aod_age_days(result)
        freshness_category = self._aod_freshness_category(age_days)
        if freshness_category == "historical":
            return None
        return AodConditionInput(
            available=True,
            freshness_category=freshness_category,
            aod_550=result.aod_550,
            source=result.provider,
            product=result.product,
            status=result.status,
            age_days=age_days,
            uncertainty=result.uncertainty,
            qa_raw=result.qa_raw,
            method=result.method,
            local_valid_pixel_count=result.local_valid_pixel_count,
            neighborhood_radius_pixels=result.neighborhood_radius_pixels,
            nearest_valid_pixel_distance_km=result.nearest_valid_pixel_distance_km,
        )

    def _particulate_condition_input(self) -> ParticulateConditionInput | None:
        atmosphere = getattr(self, "_local_atmosphere", None)
        if not isinstance(atmosphere, LocalAtmosphere) or not atmosphere.has_data:
            return None
        return ParticulateConditionInput(
            available=True,
            freshness_category=atmosphere.freshness_category,
            pm25=self._condition_numeric_value(atmosphere.pm25),
            pm10=self._condition_numeric_value(atmosphere.pm10),
            source=atmosphere.source if atmosphere.source != "—" else "",
            status="ok",
            age_days=self._freshness_age_days(atmosphere.freshness),
            distance_km=atmosphere.source_distance_km,
        )

    @staticmethod
    def _aod_age_days(result: NasaAodResult) -> float | None:
        if not result.acquisition_date:
            return None
        try:
            acquisition_date = datetime.fromisoformat(result.acquisition_date).date()
        except ValueError:
            return None
        return float(max(0, (datetime.now().date() - acquisition_date).days))

    @staticmethod
    def _aod_freshness_category(age_days: float | None) -> str:
        if age_days is None:
            return "unavailable"
        if age_days < 3:
            return "current"
        if age_days <= 7:
            return "stale"
        return "historical"

    @staticmethod
    def _condition_numeric_value(value: str) -> float | None:
        match = re.search(r"-?\d+(?:[.,]\d+)?", value or "")
        if not match:
            return None
        try:
            return float(match.group(0).replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _freshness_age_days(label: str) -> float | None:
        normalized = (label or "").strip().lower()
        if not normalized:
            return None
        if "oggi" in normalized:
            return 0.0
        if "ieri" in normalized:
            return 1.0
        match = re.search(r"(\d+)\s+giorni", normalized)
        if match:
            return float(match.group(1))
        return None

    def _object_to_qml(self, item: CelestialObject) -> dict:
        data = item.to_qml()
        description = self._object_descriptions.get(item.id) or {}
        curiosity = getattr(self, "_object_curiosities", {}).get(item.id) or {}
        image_metadata = getattr(self, "_object_image_map", {}).get(item.id) or {}
        if self._is_catalogue_detail_object(item):
            metadata = self._catalogue_detail_metadata(item)
            data["catalogueObject"] = True
            data["catalogue"] = metadata.get("catalogue", "")
            data["catalogueLabel"] = metadata.get("catalogueLabel") or self._catalogue_label(
                str(data["catalogue"])
            )
            data["catalogueId"] = metadata.get("catalogueId") or (item.id.split("-", 1)[1] if "-" in item.id else item.id)
            data["constellation"] = metadata.get("constellation", "")
            data["constellationLabel"] = metadata.get("constellationLabel", "")
            data["rightAscension"] = metadata.get("rightAscension", "")
            data["declination"] = metadata.get("declination", "")
            data["maxAngularSizeLabel"] = metadata.get("maxAngularSizeLabel") or self._format_catalogue_angle(item.max_angular_size_deg)
            visible_current_month, current_month_label = self._catalogue_object_visible_current_month(item.id)
            observability = self._catalogue_object_observability(item.id)
            geometric_observable = observability.get("is_geometrically_observable")
            useful_observable = observability.get("is_usefully_observable")
            data["catalogueGeometricallyObservable"] = geometric_observable is True
            data["catalogueGeometricallyObservableKnown"] = geometric_observable is not None
            data["catalogueGeometricallyObservableLabel"] = self._catalogue_boolean_label(geometric_observable)
            data["catalogueUsefullyObservable"] = useful_observable is True
            data["catalogueUsefullyObservableKnown"] = useful_observable is not None
            data["catalogueUsefullyObservableLabel"] = self._catalogue_boolean_label(useful_observable)
            data["catalogueObservable"] = data["catalogueUsefullyObservable"]
            data["catalogueObservableKnown"] = data["catalogueUsefullyObservableKnown"]
            data["catalogueObservableLabel"] = data["catalogueUsefullyObservableLabel"]
            data["catalogueTypeLabel"] = catalogue_object_type_label(item.object_type)
            data["catalogueObservationTypeLabel"] = catalogue_observation_type_label(
                item.recommended_observation_type
            )
            data["catalogueIntroText"] = presentation_text(
                description.get("observing_notes", ""), strip=True
            )
            data["catalogueVisibleCurrentMonth"] = visible_current_month is True
            data["catalogueVisibleCurrentMonthKnown"] = visible_current_month is not None
            data["catalogueVisibleCurrentMonthLabel"] = self._catalogue_boolean_label(visible_current_month)
            data["catalogueCurrentMonthLabel"] = current_month_label
        data["homeTimeLabel"] = self._home_time_label(item)
        data["homeWindowLabel"] = self._home_window_label(item)
        status_state, status, detail = self._observing_status_data(item)
        data["observingStatusState"] = status_state
        data["observingStatus"] = status
        data["observingStatusDetail"] = detail
        data["observingReasons"] = self._observing_reasons(item)
        data["descriptionText"] = presentation_text(
            description.get("short_description", ""), strip=True
        ) or item.notes
        data["bestSeen"] = presentation_text(
            description.get("best_seen", ""), strip=True
        )
        data["curiosityText"] = presentation_text(
            curiosity.get("curiosity_text", ""), strip=True
        )
        data["curiositySourceLabel"] = curiosity.get("source_label", "").strip()
        data["curiositySourceUrl"] = curiosity.get("source_url", "").strip()
        data["curiosityVerified"] = bool(curiosity.get("verified", False))
        data["imageAttribution"] = self._localized_image_attribution(
            image_metadata.get("attribution", "")
        )
        data["imageSourceUrl"] = image_metadata.get("source_url", "").strip()
        data["imageLicense"] = image_metadata.get("license", "").strip()
        data["imageVerified"] = bool(image_metadata.get("verified", False))
        data["setupReason"] = self._setup_reason(item)
        if item.id == "moon" and self._moon:
            data["moonPhase"] = self._moon.phase
            data["moonIllumination"] = self._moon.illumination
            data["moonPhaseAngle"] = self._moon.phase_angle
            data["moonCycleFraction"] = self._moon_cycle_fraction(self._moon.phase_angle)
            data["moonCycleDay"] = self._moon_cycle_day_label(self._moon.phase_angle)
        return data

    @staticmethod
    def _localized_image_attribution(value: object) -> str:
        attribution = presentation_text(value, strip=True)
        hips_credit = "HiPS a colori e ritaglio: CDS"
        if attribution.endswith(hips_credit):
            source = attribution[: -len(hips_credit)].rstrip("; ")
            return join_text(
                (source, tr("HiPS a colori e ritaglio: CDS")),
                separator="; ",
            )
        if attribution == "NightScope generated local SVG":
            return tr("SVG locale generato da NightScope")
        return attribution

    def _catalogue_object_visible_current_month(self, object_id: str) -> tuple[bool | None, str]:
        now = datetime.now(self._zone())
        month_label = format_month_year(now.month, now.year)
        item = self._catalogue_item_for_object_id(object_id)
        if not item or not self._has_valid_location():
            return None, month_label

        location = self._location
        if not isinstance(location, ObserverLocation):
            return None, month_label
        catalogue_object_id = str(item.get("object_id", ""))
        cache_key = (
            round(location.latitude, 5),
            round(location.longitude, 5),
            location.timezone,
            now.year,
            now.month,
            CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
            catalogue_object_id,
        )
        if cache_key in self._catalogue_current_month_visibility_cache:
            return self._catalogue_current_month_visibility_cache[cache_key], month_label

        if self._catalogue_year == now.year and self._catalogue_selected_month == now.month:
            full_cache = self._catalogue_visibility_cache.get(self._catalogue_visibility_cache_key())
            if full_cache is not None and catalogue_object_id in full_cache:
                value = bool(full_cache[catalogue_object_id])
                self._catalogue_current_month_visibility_cache[cache_key] = value
                return value, month_label

        visibility_method = getattr(self._astronomy_engine, "catalogue_month_visibility", None)
        if not callable(visibility_method):
            self._catalogue_current_month_visibility_cache[cache_key] = None
            return None, month_label
        try:
            with self._astronomy_engine_lock_instance():
                visibility = visibility_method(
                    [item],
                    location,
                    now.year,
                    now.month,
                    CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
                )
        except Exception:
            logger.warning("Current-month catalogue detail visibility calculation failed.", exc_info=True)
            value = None
        else:
            value = bool(visibility[catalogue_object_id]) if catalogue_object_id in visibility else None
        self._catalogue_current_month_visibility_cache[cache_key] = value
        return value, month_label

    def _catalogue_object_observability(self, object_id: str) -> dict[str, bool | None]:
        item = self._catalogue_item_for_object_id(object_id)
        if not item or not self._has_valid_location():
            return {"is_geometrically_observable": None, "is_usefully_observable": None}
        return self._catalogue_observability_map().get(
            str(item.get("object_id", "")),
            {"is_geometrically_observable": None, "is_usefully_observable": None},
        )

    def _catalogue_detail_metadata(self, item: CelestialObject) -> dict:
        metadata = {}
        catalogue_item = self._catalogue_item_for_object_id(item.id)
        if catalogue_item:
            if getattr(self, "_selected_object_source", "") == CATALOGUE_SOURCE:
                catalogue_item = self._catalogue_item_for_active_filter(catalogue_item)
            constellation = str(catalogue_item.get("constellation") or "")
            if self._is_solar_system_catalogue_item(catalogue_item) and not constellation:
                constellation = "—"
            metadata.update(
                {
                    "catalogue": str(catalogue_item.get("catalogue") or ""),
                    "catalogueLabel": self._catalogue_label(
                        str(catalogue_item.get("catalogue") or "")
                    ),
                    "catalogueId": str(catalogue_item.get("catalogue_id") or ""),
                    "constellation": constellation,
                    "constellationLabel": (
                        constellation
                        if constellation == "—"
                        else catalogue_constellation_label(constellation)
                    ),
                    "rightAscension": str(catalogue_item.get("right_ascension") or ""),
                    "declination": str(catalogue_item.get("declination") or ""),
                    "maxAngularSizeLabel": presentation_text(
                        catalogue_item.get("max_angular_size_label", "")
                    ),
                    "catalogueDesignations": list(catalogue_item.get("designations", [])),
                    "catalogueDesignationLabels": list(
                        catalogue_item.get("designation_labels", [])
                    ),
                }
            )
        return metadata

    def _catalogue_name_for_detail(self, item: CelestialObject) -> str:
        catalogue_item = self._catalogue_item_for_object_id(item.id)
        if catalogue_item is None:
            return tr("locale")
        if getattr(self, "_selected_object_source", "") == CATALOGUE_SOURCE:
            catalogue_item = self._catalogue_item_for_active_filter(catalogue_item)
        return self._catalogue_label(str(catalogue_item.get("catalogue") or "")) or tr(
            "locale"
        )

    def _event_to_qml(self, event: AstronomicalEvent) -> dict:
        data = event.to_qml()
        data["setup"] = self._calendar_event_setup(event)
        targets = self._calendar_event_targets(event)
        data["targetObjectId"] = targets[0].id if targets else ""
        data["targetObjectIds"] = [target.id for target in targets]
        data["targetObjects"] = [
            {"id": target.id, "name": target.name}
            for target in targets
        ]
        return data

    def _calendar_event_setup(self, event: AstronomicalEvent) -> str:
        event_type = event.event_type.strip().lower()
        if event_type == "sciame meteorico":
            return tr("Occhio nudo")
        if event_type == "luna":
            return self._calendar_moon_setup(event)
        if event_type == "eclissi":
            return tr("Occhio nudo; binocolo o basso ingrandimento")
        if event_type == "congiunzione solare":
            return tr("Nessuna configurazione osservativa")
        if event_type in {"congiunzione", "congiunzione planetaria"}:
            return self._calendar_clean_setup(event.setup)
        if event_type in {"opposizione", "pianeti"}:
            target = self._calendar_event_target(event)
            if target:
                return self._calendar_profile_setup(target, event.setup)
        return self._calendar_clean_setup(event.setup)

    def _calendar_moon_setup(self, event: AstronomicalEvent) -> str:
        title = event.title.strip().lower()
        if "nuova" in title:
            return tr(
                "Notte migliore del mese per il cielo profondo: usa il setup più adatto "
                "al singolo oggetto del tuo profilo."
            )
        target = self._calendar_event_target(event) or self._calendar_moon_target(event)
        return self._calendar_profile_setup(target, tr("Osservazione lunare"))

    @staticmethod
    def _calendar_moon_target(event: AstronomicalEvent) -> CelestialObject:
        return CelestialObject(
            id="moon",
            name=tr("Luna"),
            object_type=tr("Luna"),
            image="resources/images/solar_system/moon.jpg",
            magnitude="-12.0",
            distance=tr(
                "{value} km",
                value=format_number(384_000),
            ),
            max_altitude=tr("45°"),
            direction=tr("Sud"),
            best_time=event.best_time,
            observing_window=event.best_time,
            notes=event.note,
            recommended_setup="",
            visibility_class=tr("Luna"),
            azimuth=tr("180°"),
            time_above_horizon=tr("n/d"),
            apparent_size="30 arcmin",
            score=event.usefulness,
        )

    def _calendar_event_target(self, event: AstronomicalEvent) -> CelestialObject | None:
        event_type = event.event_type.strip().lower()
        title = event.title.strip().lower()
        target_id = event.target_object_id.strip()
        if target_id:
            target = self._calendar_target_by_id(event, target_id)
            if target:
                return target
        if event_type == "luna" or (event_type == "eclissi" and "lunare" in title):
            return self._calendar_moon_target(event)
        body_tokens = {
            "mercury": "mercury",
            "mercurio": "mercury",
            "venus": "venus",
            "venere": "venus",
            "mars": "mars",
            "marte": "mars",
            "jupiter": "jupiter",
            "giove": "jupiter",
            "saturn": "saturn",
            "saturno": "saturn",
            "uranus": "uranus",
            "urano": "uranus",
            "neptune": "neptune",
            "nettuno": "neptune",
        }
        search_text = f"{event.id} {event.title}".lower()
        for token, object_id in body_tokens.items():
            if token in search_text:
                return self._calendar_target_by_id(event, object_id)
        return None

    def _calendar_event_targets(self, event: AstronomicalEvent) -> list[CelestialObject]:
        target_ids = list(event.target_object_ids)
        if event.target_object_id and event.target_object_id not in target_ids:
            target_ids.insert(0, event.target_object_id)
        if not target_ids:
            target = self._calendar_event_target(event)
            return [target] if target else []

        targets: list[CelestialObject] = []
        for target_id in target_ids:
            target = self._calendar_target_by_id(event, target_id)
            if target and all(existing.id != target.id for existing in targets):
                targets.append(target)
        return targets

    def _calendar_target_by_id(
        self,
        event: AstronomicalEvent,
        target_id: str,
    ) -> CelestialObject | None:
        target_id = target_id.strip().lower()
        if target_id == "moon":
            return self._calendar_moon_target(event)

        targets = list(getattr(self, "_base_solar_system_objects", []))
        targets.extend(getattr(self, "_solar_system_objects", []))
        for target in targets:
            if target.id == target_id:
                return replace(
                    target,
                    best_time=event.best_time,
                    observing_window=event.observing_window or event.best_time,
                )

        bodies = {
            "mercury": (tr("Mercurio"), "-0.2"),
            "venus": (tr("Venere"), "-4.0"),
            "mars": (tr("Marte"), "-1.2"),
            "jupiter": (tr("Giove"), "-2.3"),
            "saturn": (tr("Saturno"), "0.7"),
            "uranus": (tr("Urano"), "5.7"),
            "neptune": (tr("Nettuno"), "7.8"),
        }
        body = bodies.get(target_id)
        if not body:
            return None
        name, magnitude = body
        return CelestialObject(
            id=target_id,
            name=name,
            object_type=tr("Pianeta"),
            image=f"resources/images/solar_system/{target_id}.jpg",
            magnitude=magnitude,
            distance=tr("n/d"),
            max_altitude=tr("45°"),
            direction=tr("Sud"),
            best_time=event.best_time,
            observing_window=event.observing_window or event.best_time,
            notes=event.note,
            recommended_setup="",
            visibility_class=tr("Pianeta"),
            azimuth=tr("180°"),
            time_above_horizon=tr("n/d"),
            score=event.usefulness,
        )

    def _calendar_profile_setup(self, target: CelestialObject, fallback: str) -> str:
        telescopes = self._active_profile_telescopes()
        binoculars = self._active_profile_binoculars()
        if not telescopes and not binoculars:
            return self._calendar_clean_setup(fallback)

        suggestion = self._equipment_service.suggest_for_profile(
            target,
            telescopes,
            self._active_profile_eyepieces(),
            self._active_profile_barlows(),
            None,
            self._sky_quality,
            binoculars,
        )
        setup_text = presentation_text(suggestion.get("setupText", ""), strip=True)
        if not setup_text:
            return self._calendar_clean_setup(fallback)
        recommendation_state = str(suggestion.get("recommendationState", ""))
        if recommendation_state == "requires_optical_instrument":
            return self._calendar_clean_setup(fallback)
        if recommendation_state == "missing_eyepieces":
            telescope_name = presentation_text(
                suggestion.get("telescopeName", ""), strip=True
            )
            return (
                tr("{telescope}: aggiungi oculari", telescope=telescope_name)
                if telescope_name
                else self._calendar_clean_setup(fallback)
            )
        return setup_text

    @staticmethod
    def _calendar_clean_setup(setup: str) -> str:
        clean = presentation_text(setup, strip=True)
        if clean == "Qualsiasi setup":
            return tr("Nota osservativa")
        if clean == "Telescopio medio":
            return tr("Telescopio consigliato")
        if clean == "Non prioritario":
            return tr("Bassa priorità osservativa")
        return clean

    def _observing_status(self, item: CelestialObject) -> tuple[str, str]:
        _, status, detail = self._observing_status_data(item)
        return status, detail

    def _observing_status_data(self, item: CelestialObject) -> tuple[str, str, str]:
        if self._is_catalogue_detail_object(item):
            catalogue = self._catalogue_name_for_detail(item)
            return (
                "catalogue",
                tr("Catalogo {catalogue}", catalogue=catalogue),
                tr("Scheda informativa caricata dal catalogo locale."),
            )
        current_altitude = self._parse_degrees(item.current_altitude)
        useful_datetime = self._first_observing_datetime(item.best_time) or self._first_observing_datetime(
            item.observing_window
        )
        window = self._home_window_label(item)
        now = datetime.now(self._zone())
        night_window = getattr(self, "_observing_night_window", ObservingNightWindow.unavailable())
        is_observing_time = night_window.contains(now)
        altitude_threshold = self._observing_altitude_threshold(item)
        observable_now = item.observable_now
        if observable_now is None:
            observable_now = bool(
                is_observing_time
                and current_altitude is not None
                and current_altitude >= altitude_threshold
            )
        if self._is_solar_system_monthly_visibility_blocked(item):
            if current_altitude is not None and current_altitude > 0:
                return (
                    "above_horizon",
                    tr("Sopra l'orizzonte"),
                    tr("Sopra l'orizzonte, ma non utile per l'osservazione questo mese."),
                )
            if useful_datetime:
                return (
                    "limited",
                    tr("Finestra marginale"),
                    tr("Finestra marginale: l'oggetto non raggiunge la visibilità utile mensile."),
                )
            return (
                "limited",
                tr("Non utile questo mese"),
                tr("Non raggiunge una finestra utile questo mese secondo il criterio di visibilità mensile."),
            )
        if observable_now:
            altitude = (
                tr("{value}°", value=format_number(current_altitude))
                if current_altitude is not None
                else tr("quota utile")
            )
            return (
                "observable_now",
                tr("Osservabile ora"),
                tr("Attualmente a {altitude}. Finestra utile: {window}.", altitude=altitude, window=window),
            )
        if current_altitude is not None and current_altitude > 0 and not is_observing_time:
            return (
                "above_horizon",
                tr("Sopra l'orizzonte"),
                tr(
                    "Attualmente a {altitude}°, ma fuori dalla notte osservativa. Finestra utile: {window}.",
                    altitude=format_number(current_altitude),
                    window=window,
                ),
            )
        if useful_datetime:
            if self._home_time_period_code(useful_datetime) == "before_dawn":
                return (
                    "later",
                    tr("Meglio prima dell'alba"),
                    tr("Attualmente sotto la soglia utile. Finestra prima dell'alba: {window}.", window=window),
                )
            if useful_datetime > now:
                return (
                    "later",
                    tr("Meglio più tardi"),
                    tr("Attualmente sotto la soglia utile. Finestra più tardi: {window}.", window=window),
                )
        if current_altitude is not None and current_altitude > 0:
            return (
                "limited",
                tr("Troppo basso ora"),
                tr(
                    "Attualmente a {altitude}°, sotto la soglia utile di {threshold}°. Finestra utile: {window}.",
                    altitude=format_number(current_altitude),
                    threshold=format_number(altitude_threshold),
                    window=window,
                ),
            )
        if useful_datetime:
            return (
                "unavailable",
                tr("Finestra conclusa"),
                tr("La finestra utile di questa notte era {window}.", window=window),
            )
        if item.visible:
            return (
                "later",
                tr("Finestra utile"),
                tr("Finestra osservativa: {window}.", window=item.observing_window),
            )
        return (
            "unavailable",
            tr("Non osservabile"),
            tr("Nessuna finestra notturna utile per questa posizione."),
        )

    @staticmethod
    def _is_planetary_or_lunar_target(item: CelestialObject) -> bool:
        return item.id in {
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
        } or item.object_type == "Pianeta"

    @classmethod
    def _observing_altitude_threshold(cls, item: CelestialObject) -> float:
        return 8.0 if cls._is_planetary_or_lunar_target(item) else DEEP_SKY_USEFUL_ALTITUDE_DEG

    def _is_solar_system_monthly_visibility_blocked(self, item: CelestialObject) -> bool:
        if item.object_type != "Pianeta":
            return False
        return self._catalogue_month_visible_for_object(item.id) is False

    def _observing_reasons(self, item: CelestialObject) -> list[str]:
        if self._is_catalogue_detail_object(item):
            return []
        reasons = []
        max_altitude = self._parse_degrees(item.max_altitude)
        if max_altitude is not None and max_altitude > 0:
            reasons.append(self._altitude_reason(max_altitude))
        if item.time_above_horizon and item.time_above_horizon not in {"n/d", "0 h"}:
            reasons.append(
                tr(
                    "Finestra utile sopra soglia: {duration}.",
                    duration=item.time_above_horizon,
                )
            )
        if item.id == "moon" and self._moon:
            reasons.append(
                tr(
                    "Fase lunare: {phase}, illuminazione {illumination}.",
                    phase=self._moon.phase,
                    illumination=self._moon.illumination,
                )
            )
        elif self._seeing_transparency and item.object_type == "Pianeta":
            seeing = self._localized_seeing(self._seeing_transparency.seeing)
            reasons.append(
                tr(
                    "Seeing previsto: {seeing}. Adatto a valutare dettagli planetari.",
                    seeing=seeing,
                )
            )
        elif self._sky_quality and item.object_type != "Pianeta":
            reasons.append(self._sky_quality_reason(item))
        return reasons[:4]

    @staticmethod
    def _altitude_reason(max_altitude: float) -> str:
        altitude = format_number(max_altitude)
        if max_altitude >= 65:
            return tr(
                "Culmina molto alto ({altitude}°): meno atmosfera e immagine più stabile.",
                altitude=altitude,
            )
        if max_altitude >= 35:
            return tr(
                "Raggiunge una buona altezza ({altitude}°): osservazione realistica.",
                altitude=altitude,
            )
        if max_altitude >= 15:
            return tr(
                "Resta basso ({altitude}°): serve orizzonte libero e cielo stabile.",
                altitude=altitude,
            )
        return tr(
            "Altezza massima critica ({altitude}°): oggetto difficile da sfruttare.",
            altitude=altitude,
        )

    @staticmethod
    def _localized_seeing(value: str) -> str:
        labels = {
            "Excellent": tr("Eccellente"),
            "Good": tr("Buono"),
            "Average": tr("Discreto"),
            "Poor": tr("Scarso"),
        }
        return labels.get(value, value or tr("n/d"))

    def _sky_quality_reason(self, item: CelestialObject) -> str:
        bortle = self._sky_quality.bortle_class
        difficulty = item.difficulty if item.difficulty and item.difficulty != "n/d" else "da valutare"
        if difficulty == "Facile":
            return tr(
                "Cielo Bortle {bortle}: oggetto ancora gestibile, difficoltà stimata facile.",
                bortle=bortle,
            )
        if difficulty == "Media":
            return tr(
                "Cielo Bortle {bortle}: richiede adattamento al buio, difficoltà media.",
                bortle=bortle,
            )
        if difficulty == "Difficile":
            return tr(
                "Cielo Bortle {bortle}: oggetto penalizzato, meglio trasparenza alta e luci schermate.",
                bortle=bortle,
            )
        return tr(
            "Cielo Bortle {bortle}: difficoltà stimata {difficulty}.",
            bortle=bortle,
            difficulty=(tr("da valutare") if difficulty == "da valutare" else difficulty),
        )

    def _setup_reason(self, item: CelestialObject) -> str:
        if not item.recommended_setup:
            return ""
        option = self._recommended_setup_option(item)
        magnification = option.get("magnification", "") if option else ""
        true_field = option.get("trueField", "") if option else ""
        exit_pupil = option.get("exitPupil", "") if option else ""
        barlow = option.get("barlow", "") if option else item.barlow
        lower_type = item.object_type.lower()
        if option.get("equipmentType") == "Binocular":
            if "open" in lower_type or "ammasso aperto" in lower_type or "star cloud" in lower_type:
                return tr("{magnification} e pupilla {exit_pupil}: campo ampio e visione naturale dell'ammasso.", magnification=magnification, exit_pupil=exit_pupil)
            if "galaxy" in lower_type or "galassia" in lower_type:
                return tr("{magnification} e pupilla {exit_pupil}: adatto a oggetti molto estesi e a basso contrasto.", magnification=magnification, exit_pupil=exit_pupil)
            if "nebula" in lower_type or "nebul" in lower_type:
                return tr("{magnification} e pupilla {exit_pupil}: utile per individuare l'oggetto senza stringere troppo il campo.", magnification=magnification, exit_pupil=exit_pupil)
            return item.equipment_explanation or tr("{magnification} e pupilla {exit_pupil}: configurazione binoculare a basso ingrandimento.", magnification=magnification, exit_pupil=exit_pupil)
        if magnification and exit_pupil:
            if item.id == "moon":
                return tr("{magnification} e pupilla {exit_pupil}: dettaglio lunare leggibile senza spingere troppo l'immagine.", magnification=magnification, exit_pupil=exit_pupil)
            if item.object_type == "Pianeta":
                return tr("{magnification} e pupilla {exit_pupil}: compromesso tra dettaglio planetario e seeing previsto.", magnification=magnification, exit_pupil=exit_pupil)
            if "open" in lower_type or "ammasso aperto" in lower_type or "star cloud" in lower_type:
                return tr("Campo reale {true_field}: mantiene l'oggetto nel suo contesto stellare.", true_field=true_field)
            if "globular" in lower_type or "ammasso globulare" in lower_type:
                return tr("{magnification} e pupilla {exit_pupil}: aiuta a separare il nucleo senza scurire troppo.", magnification=magnification, exit_pupil=exit_pupil)
            if "galaxy" in lower_type or "galassia" in lower_type:
                return tr("Pupilla {exit_pupil} e campo {true_field}: privilegia contrasto e orientamento della galassia.", exit_pupil=exit_pupil, true_field=true_field)
            if "nebula" in lower_type or "nebul" in lower_type:
                return tr("Pupilla {exit_pupil} e campo {true_field}: equilibrio utile per oggetti diffusi.", exit_pupil=exit_pupil, true_field=true_field)
        if item.equipment_explanation:
            return item.equipment_explanation
        if barlow and barlow != "No":
            return tr("Barlow inclusa per raggiungere un ingrandimento più utile.")
        return tr("Configurazione scelta in base al profilo attivo e al tipo di oggetto.")

    @staticmethod
    def _recommended_setup_option(item: CelestialObject) -> dict:
        for option in item.setup_options:
            if option.get("roleCode") == "recommended":
                return option
        return item.setup_options[0] if item.setup_options else {}

    @staticmethod
    def _recommendation_setup_type(suggestion: dict) -> str:
        setup_type = suggestion.get("setupType", "")
        if setup_type:
            return setup_type
        equipment_type = suggestion.get("equipmentType", "")
        if equipment_type == "Binocular":
            return "binocular"
        if equipment_type == "Telescope":
            return "telescope"
        for option in suggestion.get("setupOptions", []):
            if option.get("roleCode") == "recommended":
                option_type = option.get("equipmentType", "")
                if option_type == "Binocular":
                    return "binocular"
                if option_type == "Telescope":
                    return "telescope"
        return ""

    @staticmethod
    def _moon_cycle_fraction(phase_angle: float) -> float:
        return round((phase_angle % 360.0) / 360.0, 4)

    @staticmethod
    def _moon_cycle_day_label(phase_angle: float) -> str:
        cycle_day = AppController._moon_cycle_fraction(phase_angle) * 29.53
        return tr(
            "Giorno {day} di {cycle}",
            day=format_number(cycle_day, decimals=1),
            cycle=format_number(29.5, decimals=1),
        )

    def _update_observing_night_window(self) -> bool:
        previous = getattr(self, "_observing_night_window", ObservingNightWindow.unavailable())
        if not self._has_valid_location():
            current = ObservingNightWindow.unavailable()
        else:
            method = getattr(self._astronomy_engine, "observing_night_window", None)
            try:
                if callable(method):
                    with self._astronomy_engine_lock_instance():
                        current = method(self._location)
                else:
                    current = ObservingNightWindow.unavailable()
            except Exception:
                logger.warning("Observing night window refresh failed.", exc_info=True)
                current = ObservingNightWindow.unavailable()
        if not isinstance(current, ObservingNightWindow):
            current = ObservingNightWindow.unavailable()
        self._observing_night_window = current
        return not self._same_observing_night(previous, current)

    @staticmethod
    def _same_observing_night(
        left: ObservingNightWindow,
        right: ObservingNightWindow,
    ) -> bool:
        if left.state != right.state:
            return False
        if left.start is None or left.end is None or right.start is None or right.end is None:
            return left.start == right.start and left.end == right.end
        return (
            abs((left.start - right.start).total_seconds()) < 60
            and abs((left.end - right.end).total_seconds()) < 60
        )

    def _observing_weather_hours(self) -> list[WeatherHour]:
        if not hasattr(self, "_location") or not hasattr(self, "_observing_night_window"):
            return list(getattr(self, "_weather_hours", []))
        if not self._has_valid_location():
            return []
        return weather_hours_for_night(
            self._weather_hours,
            self._observing_night_window,
            self._location.timezone,
        )

    def _next_24_weather_hours(self) -> list[WeatherHour]:
        timezone = self._location.timezone if getattr(self, "_location", None) else "UTC"
        return weather_hours_for_next_24(
            list(getattr(self, "_weather_hours", [])),
            timezone,
            self._weather_display_now(),
        )

    def _weather_display_now(self) -> datetime:
        return datetime.now(self._zone())

    def _weather_digest(self) -> dict:
        night_hours = self._observing_weather_hours()
        if not night_hours:
            return {
                "bestWindow": tr("n/d"),
                "cloudAverage": 0,
                "cloudAverageLabel": tr("n/d"),
                "windLabel": tr("n/d"),
                "rainProbability": 0,
                "rainProbabilityLabel": tr("n/d"),
                "bestHours": [],
            }
        average_cloud = round(sum(hour.cloud_cover for hour in night_hours) / len(night_hours))
        max_rain = max(hour.precipitation_probability for hour in night_hours)
        average_wind = round(sum(hour.wind_kmh for hour in night_hours) / len(night_hours))
        best_hours = self._best_weather_hours(night_hours)
        return {
            "bestWindow": self._weather_window_label(
                best_hours,
                self._observing_night_window,
                self._location.timezone,
            ),
            "cloudAverage": average_cloud,
            "cloudAverageLabel": tr(
                "{value}%", value=format_number(average_cloud)
            ),
            "windLabel": self._wind_label(average_wind),
            "rainProbability": max_rain,
            "rainProbabilityLabel": tr(
                "{value}%", value=format_number(max_rain)
            ),
            "bestHours": [
                {
                    "time": hour.time,
                    "cloudCover": hour.cloud_cover,
                    "cloudCoverLabel": tr(
                        "{value}%", value=format_number(hour.cloud_cover)
                    ),
                    "windKmh": hour.wind_kmh,
                    "windLabel": tr(
                        "{value} km/h", value=format_number(hour.wind_kmh)
                    ),
                    "rainProbability": hour.precipitation_probability,
                    "rainProbabilityLabel": tr(
                        "{value}%",
                        value=format_number(hour.precipitation_probability),
                    ),
                }
                for hour in self._selected_weather_hours(night_hours)
            ],
        }

    def _weather_blocking_status(self) -> WeatherBlockingStatus:
        if not self._weather_summary:
            return WeatherBlockingStatus(blocks_plan=False, show_warning=False)
        return self._night_planner_service.weather_blocking_status(self._weather_summary)

    def _observing_session_decision(self) -> ObservingSessionDecision:
        blocking = self._weather_blocking_status()
        if not blocking.show_warning:
            return ObservingSessionDecision(state="recommended")

        if self._best_usable_observing_window():
            return ObservingSessionDecision(
                state="monitor",
                title=tr("Sessione da monitorare"),
                icon="⚠",
                detail=tr("Le condizioni attuali non sono ancora favorevoli."),
                description=tr(
                    "Le condizioni migliorano in una finestra osservativa successiva.\n"
                    "Ricontrolla il meteo prima di preparare la sessione."
                ),
                show_opportunity=True,
            )

        return ObservingSessionDecision(
            state="discouraged",
            title=tr("Sessione sconsigliata"),
            icon="🚫",
            detail=tr("Le condizioni previste rimangono sfavorevoli per tutta la notte."),
            description=tr("Non è consigliabile preparare una sessione osservativa."),
            show_opportunity=False,
        )

    def _suggested_observing_window(self) -> str:
        decision = self._observing_session_decision()
        if decision.state == "discouraged":
            return ""
        if decision.state == "monitor":
            return self._weather_window_label(
                self._best_usable_observing_window(),
                self._observing_night_window,
                self._location.timezone,
            ).replace(" - ", "–")
        best_window = self._weather_digest().get("bestWindow", "")
        if not best_window or best_window == "n/d":
            return ""
        return best_window.replace(" - ", "–")

    @staticmethod
    def _best_weather_hours(hours: list[WeatherHour]) -> list[WeatherHour]:
        groups = consecutive_weather_groups(hours)
        full_groups = [group for group in groups if len(group) >= 3]
        if full_groups:
            candidates = [
                group[index : index + 3]
                for group in full_groups
                for index in range(len(group) - 2)
            ]
        else:
            longest = max((len(group) for group in groups), default=0)
            candidates = [group for group in groups if len(group) == longest]
        if not candidates:
            return []
        return min(candidates, key=AppController._weather_slice_score)

    def _best_usable_observing_window(self) -> list[WeatherHour]:
        night_hours = self._observing_weather_hours()
        best_group: list[WeatherHour] = []
        for forecast_group in consecutive_weather_groups(night_hours):
            current_group: list[WeatherHour] = []
            for hour in forecast_group:
                if self._is_usable_weather_hour(hour):
                    current_group.append(hour)
                    if len(current_group) > len(best_group):
                        best_group = list(current_group)
                else:
                    current_group = []

        return best_group if len(best_group) >= 2 else []

    @staticmethod
    def _is_usable_weather_hour(hour: WeatherHour) -> bool:
        return (
            hour.precipitation_probability <= 35
            and hour.cloud_cover <= 65
            and hour.wind_kmh <= 28
            and AppController._weather_hour_observing_score(hour) >= 45
        )

    @staticmethod
    def _weather_hour_observing_score(hour: WeatherHour) -> int:
        score = 100
        score -= min(55, round(hour.cloud_cover * 0.55))
        score -= min(30, round(hour.precipitation_probability * 0.45))
        score -= max(0, hour.wind_kmh - 10)
        score -= max(0, round((hour.humidity - 70) * 0.25))
        return max(0, min(100, score))

    @staticmethod
    def _weather_slice_score(hours: list[WeatherHour]) -> float:
        cloud = sum(hour.cloud_cover for hour in hours) / len(hours)
        rain = max(hour.precipitation_probability for hour in hours)
        wind = sum(hour.wind_kmh for hour in hours) / len(hours)
        return cloud + rain * 1.3 + max(0.0, wind - 10.0) * 1.8

    @staticmethod
    def _selected_weather_hours(hours: list[WeatherHour]) -> list[WeatherHour]:
        if len(hours) <= 5:
            return list(hours)
        last_index = len(hours) - 1
        indices = [round(position * last_index / 4) for position in range(5)]
        return [hours[index] for index in dict.fromkeys(indices)]

    @staticmethod
    def _weather_window_label(
        hours: list[WeatherHour],
        night_window: ObservingNightWindow | None = None,
        timezone: str = "UTC",
    ) -> str:
        if not hours:
            return tr("n/d")
        contiguous = consecutive_weather_groups(hours)
        selected = max(contiguous, key=len, default=[])
        if not selected:
            return tr("n/d")
        start = selected[0].time
        last_timestamp = weather_hour_datetime(selected[-1], timezone)
        if last_timestamp is not None:
            end_dt = last_timestamp + timedelta(hours=1)
            if night_window is not None and night_window.end is not None:
                end_dt = min(end_dt, night_window.end)
        else:
            parsed_end = AppController._parse_hour_minute(selected[-1].time)
            if not parsed_end:
                return start
            end_dt = datetime(2000, 1, 1, parsed_end[0], parsed_end[1]) + timedelta(hours=1)
        return f"{start} - {end_dt.strftime('%H:%M')}"

    @staticmethod
    def _wind_label(wind_kmh: int) -> str:
        if wind_kmh <= 12:
            return tr("debole")
        if wind_kmh <= 24:
            return tr("moderato")
        return tr("sostenuto")

    def _home_time_label(self, item: CelestialObject) -> str:
        useful_best = self._first_observing_datetime(item.best_time)
        if useful_best:
            return self._format_home_datetime(useful_best)
        useful_window = self._first_observing_datetime(item.observing_window)
        if useful_window:
            return self._format_home_datetime(useful_window)
        return tr("Non in finestra notturna")

    def _home_window_label(self, item: CelestialObject) -> str:
        useful_times = [
            candidate
            for hour, minute in self._all_times(item.observing_window)
            if (candidate := self._observing_datetime_for_clock(hour, minute)) is not None
        ]
        if len(useful_times) >= 2:
            return f"{useful_times[0].strftime('%H:%M')} - {useful_times[-1].strftime('%H:%M')}"
        if useful_times:
            return self._format_home_datetime(useful_times[0])
        return item.observing_window

    def _first_useful_time(self, value: str) -> tuple[int, int] | None:
        candidate = self._first_observing_datetime(value)
        if candidate is not None:
            return candidate.hour, candidate.minute
        return None

    def _first_observing_datetime(self, value: str) -> datetime | None:
        for hour, minute in self._all_times(value):
            candidate = self._observing_datetime_for_clock(hour, minute)
            if candidate is not None:
                return candidate
        return None

    def _observing_datetime_for_clock(self, hour: int, minute: int) -> datetime | None:
        night_window = getattr(self, "_observing_night_window", None)
        if night_window is None:
            day = 2 if hour < 12 else 1
            return datetime(2000, 1, day, hour, minute, tzinfo=ZoneInfo("UTC"))
        return night_window.datetime_for_clock(hour, minute)

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

    def _format_home_datetime(self, value: datetime) -> str:
        return value.strftime("%H:%M")

    def _home_time_period_code(self, value: datetime) -> str:
        night_window = getattr(self, "_observing_night_window", None)
        if night_window is not None and night_window.state == "bounded":
            if night_window.start is not None and value.date() == night_window.start.date():
                return "evening"
            if night_window.end is not None and night_window.end - value <= timedelta(hours=3):
                return "before_dawn"
        return "night"

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
            return Telescope(
                "preset:binoculars",
                tr("Binocolo 10x50"),
                50,
                500,
                tr("Binocolo"),
                "manuale",
            )
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

    @staticmethod
    def _localized_object_content(rows: Mapping[str, dict]) -> dict[str, dict]:
        localized: dict[str, dict] = {}
        non_content_fields = {
            "object_id",
            "is_builtin",
            "source_label",
            "source_url",
            "verified",
        }
        for object_id, source_row in rows.items():
            row = dict(source_row)
            if bool(row.get("is_builtin")):
                for field, value in tuple(row.items()):
                    if field not in non_content_fields:
                        row[field] = content_text("objects", object_id, field, value)
            localized[object_id] = row
        return localized

    @staticmethod
    def _localized_equipment_catalog_rows(
        rows: list[dict],
        section_name: str,
    ) -> list[dict]:
        identity_fields = {
            "telescopes": ("brand", "name"),
            "eyepieces": (
                "brand",
                "model",
                "eyepiece_type",
                "focal_length_mm",
                "min_focal_length_mm",
                "max_focal_length_mm",
            ),
            "barlows": ("brand", "model", "multiplier"),
            "binoculars": ("brand", "model"),
            "filters": ("brand", "model"),
            "reducers": ("brand", "model", "reduction_factor"),
        }
        content_fields = {
            "telescopes": ("optical_type", "mount_type", "notes"),
            "eyepieces": ("notes",),
            "barlows": ("notes",),
            "binoculars": (),
            "filters": ("notes",),
            "reducers": ("compatible_models", "connection", "notes"),
        }
        fields = identity_fields[section_name]
        translated_fields = content_fields[section_name]
        localized = []
        for source_row in rows:
            row = dict(source_row)
            if bool(row.get("is_builtin")) and not bool(row.get("is_user_modified")):
                item_key = content_key(*(row.get(field) for field in fields))
                for field in translated_fields:
                    row[field] = content_text(
                        f"equipment_{section_name}",
                        item_key,
                        field,
                        row.get(field, ""),
                    )
            localized.append(row)
        return localized

    def _refresh_equipment_catalogs(self) -> None:
        self._telescope_brands = self._equipment_catalog_repository.brands()
        self._telescope_catalog_models = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.models(), "telescopes"
        )
        self._catalog_eyepieces = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.eyepieces(), "eyepieces"
        )
        self._catalog_barlows = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.barlows(), "barlows"
        )
        self._catalog_binoculars = self._equipment_catalog_repository.binoculars()
        self._catalog_filters = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.filters(), "filters"
        )
        self._catalog_reducers = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.reducers(), "reducers"
        )
        self._telescopes = self._initial_telescopes()
        self._eyepieces = [self._eyepiece_from_catalog_row(row) for row in self._catalog_eyepieces]
        self._barlows = [self._barlow_from_catalog_row(row) for row in self._catalog_barlows]
        self._binoculars = [self._binocular_from_catalog_row(row) for row in self._catalog_binoculars]
        self._filters = [self._filter_from_catalog_row(row) for row in self._catalog_filters]
        self._reducers = [self._reducer_from_catalog_row(row) for row in self._catalog_reducers]
        self._profile_equipment = self._initial_profile_equipment()
        self._selected_telescope_index = self._initial_telescope_index()

    def _refresh_binocular_catalog(self) -> None:
        self._catalog_binoculars = self._localized_equipment_catalog_rows(
            self._equipment_catalog_repository.binoculars(), "binoculars"
        )
        self._binoculars = [self._binocular_from_catalog_row(row) for row in self._catalog_binoculars]
        self._profile_equipment = self._initial_profile_equipment()

    def _after_catalog_change(self, message: str, ok: bool) -> None:
        self._equipment_message = message
        if ok:
            self._refresh_equipment_catalogs()
            self._refresh_active_profile_dependencies(reload_profile_equipment=True)
            self._emit_profile_dependent_changes()
        else:
            self.equipmentChanged.emit()

    def _after_binocular_catalog_change(self, message: str, ok: bool) -> None:
        self._equipment_message = message
        if ok:
            self._refresh_binocular_catalog()
        self.equipmentChanged.emit()

    def _after_passive_accessory_catalog_change(self, message: str, ok: bool) -> None:
        self._equipment_message = message
        if ok:
            self._refresh_equipment_catalogs()
        self.equipmentChanged.emit()

    def _parse_filter_inputs(
        self,
        central_wavelength: str,
        bandwidth: str,
        transmission: str,
        minimum_aperture: str,
    ) -> tuple[float | None, float | None, float | None, int | None] | None:
        try:
            central = self._optional_float_input(central_wavelength)
            width = self._optional_float_input(bandwidth)
            transmission_pct = self._optional_float_input(transmission)
            aperture_value = self._optional_float_input(minimum_aperture)
            if aperture_value is not None and not aperture_value.is_integer():
                raise ValueError
            aperture = int(aperture_value) if aperture_value is not None else None
        except ValueError:
            self._equipment_message = tr("Dati filtro non validi.")
            self.equipmentChanged.emit()
            return None
        return central, width, transmission_pct, aperture

    def _parse_reducer_inputs(
        self,
        reduction_factor: str,
        backfocus: str,
    ) -> tuple[float, float | None] | None:
        try:
            factor = float(reduction_factor.replace(",", "."))
            if not math.isfinite(factor):
                raise ValueError
            backfocus_mm = self._optional_float_input(backfocus)
        except ValueError:
            self._equipment_message = tr("Dati riduttore non validi.")
            self.equipmentChanged.emit()
            return None
        return factor, backfocus_mm

    @staticmethod
    def _catalog_id_list(value: str) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                item.strip()
                for item in str(value or "").split(",")
                if item.strip()
            )
        )

    @staticmethod
    def _optional_float_input(value: str) -> float | None:
        clean_value = value.strip()
        if not clean_value:
            return None
        parsed = float(clean_value.replace(",", "."))
        if not math.isfinite(parsed):
            raise ValueError
        return parsed

    def _parse_binocular_inputs(
        self,
        magnification: str,
        objective_diameter: str,
    ) -> tuple[int, int] | None:
        try:
            magnification_value = self._positive_int(magnification)
            objective_value = self._positive_int(objective_diameter)
        except ValueError:
            self._equipment_message = tr("Dati binocolo non validi.")
            self.equipmentChanged.emit()
            return None
        return magnification_value, objective_value

    @staticmethod
    def _positive_int(value: str) -> int:
        parsed = float(value.strip().replace(",", "."))
        if not math.isfinite(parsed) or parsed <= 0 or not parsed.is_integer():
            raise ValueError
        return int(parsed)

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
                if (
                    not all(math.isfinite(value) for value in (apparent, min_value, max_value))
                    or min_value <= 0
                    or max_value <= 0
                    or min_value >= max_value
                ):
                    raise ValueError
            else:
                focal_value = float(focal.replace(",", "."))
                min_value = None
                max_value = None
                if not all(math.isfinite(value) for value in (apparent, focal_value)):
                    raise ValueError
        except ValueError:
            self._equipment_message = tr("Dati oculare non validi.")
            self.equipmentChanged.emit()
            return None
        afov_min = None
        afov_max = None
        if afov_range.strip():
            parts = [
                part.strip()
                for part in afov_range.replace(",", ".").replace("-", " ").split()
                if part.strip()
            ]
            try:
                if len(parts) != 2:
                    raise ValueError
                afov_min = float(parts[0])
                afov_max = float(parts[1])
                if (
                    not all(math.isfinite(value) for value in (afov_min, afov_max))
                    or afov_min <= 0
                    or afov_min > afov_max
                    or afov_max > 180
                ):
                    raise ValueError
            except ValueError:
                self._equipment_message = tr("Intervallo AFOV non valido.")
                self.equipmentChanged.emit()
                return None
        if focal_value <= 0 or apparent <= 0:
            self._equipment_message = tr(
                "Focale e campo apparente devono essere maggiori di zero."
            )
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
            zoom_click_positions_mm=AppController._parse_zoom_click_positions(row.get("zoom_click_positions_mm", "")),
        )

    @staticmethod
    def _parse_zoom_click_positions(value: str) -> tuple[float, ...]:
        positions = []
        seen = set()
        for part in str(value or "").replace(",", ".").replace("/", ";").split(";"):
            token = part.strip()
            if not token:
                continue
            try:
                position = float(token)
            except ValueError:
                continue
            key = round(position, 3)
            if position <= 0 or key in seen:
                continue
            seen.add(key)
            positions.append(position)
        return tuple(positions)

    @staticmethod
    def _barlow_from_catalog_row(row: dict) -> Barlow:
        return Barlow(
            id=row["catalog_id"],
            name=f"{row['brand']} {row['model']} {float(row['multiplier']):g}x",
            multiplier=float(row["multiplier"]),
            barrel_size=str(row.get("barrel_size") or ""),
        )

    @staticmethod
    def _binocular_from_catalog_row(row: dict) -> Binocular:
        return Binocular(
            id=row["catalog_id"],
            name=f"{row['brand']} {row['model']}",
            magnification=int(row["magnification"]),
            objective_diameter_mm=int(row["objective_diameter_mm"]),
            image_stabilized=bool(row["image_stabilized"]),
        )

    @staticmethod
    def _filter_from_catalog_row(row: dict) -> OpticalFilter:
        return OpticalFilter(
            id=row["catalog_id"],
            name=f"{row['brand']} {row['model']}",
            filter_class=str(row["filter_class"]),
            central_wavelength_nm=(
                float(row["central_wavelength_nm"])
                if row.get("central_wavelength_nm") is not None
                else None
            ),
            bandwidth_nm=(
                float(row["bandwidth_nm"])
                if row.get("bandwidth_nm") is not None
                else None
            ),
            transmission_pct=(
                float(row["transmission_pct"])
                if row.get("transmission_pct") is not None
                else None
            ),
            minimum_aperture_mm=(
                int(row["minimum_aperture_mm"])
                if row.get("minimum_aperture_mm") is not None
                else None
            ),
        )

    @staticmethod
    def _reducer_from_catalog_row(row: dict) -> FocalReducer:
        return FocalReducer(
            id=row["catalog_id"],
            name=f"{row['brand']} {row['model']}",
            reduction_factor=float(row["reduction_factor"]),
            optical_system=str(row["optical_system"]),
            compatible_models=str(row.get("compatible_models") or ""),
            connection=str(row.get("connection") or ""),
            backfocus_mm=(
                float(row["backfocus_mm"])
                if row.get("backfocus_mm") is not None
                else None
            ),
            visual_compatible=bool(row.get("visual_compatible")),
            imaging_compatible=bool(row.get("imaging_compatible")),
            corrected_field=bool(row.get("corrected_field")),
            compatible_telescope_ids=tuple(row.get("compatible_telescope_ids") or ()),
            compatible_telescope_names=tuple(
                item.get("display_name", "")
                for item in row.get("compatible_telescopes", [])
                if item.get("display_name")
            ),
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
                "binocular_ids": self._equipment_catalog_repository.profile_binocular_ids(profile_id),
                "filter_ids": self._equipment_catalog_repository.profile_filter_ids(profile_id),
                "reducer_ids": self._equipment_catalog_repository.profile_reducer_ids(profile_id),
            }
        return equipment

    def _refresh_profiles_from_repository(self) -> None:
        self._equipment_profiles = self._equipment_catalog_repository.profiles()
        for profile in self._equipment_profiles:
            state = self._profile_equipment.setdefault(
                str(profile["id"]),
                self._empty_profile_equipment_state(),
            )
            self._ensure_profile_equipment_state(state)

    def _active_profile(self) -> dict | None:
        return next((profile for profile in self._equipment_profiles if int(profile.get("active", 0)) == 1), None)

    def _presented_equipment_profiles(self) -> list[dict]:
        return [dict(profile) for profile in self._equipment_profiles]

    def _active_profile_state(self) -> dict[str, list[str]]:
        profile = self._active_profile()
        if not profile:
            return self._empty_profile_equipment_state()
        state = self._profile_equipment.setdefault(
            str(profile["id"]),
            self._empty_profile_equipment_state(),
        )
        self._ensure_profile_equipment_state(state)
        return state

    @staticmethod
    def _empty_profile_equipment_state() -> dict[str, list[str]]:
        return {
            "telescope_ids": [],
            "eyepiece_ids": [],
            "barlow_ids": [],
            "binocular_ids": [],
            "filter_ids": [],
            "reducer_ids": [],
        }

    @staticmethod
    def _ensure_profile_equipment_state(state: dict[str, list[str]]) -> None:
        for key in (
            "telescope_ids",
            "eyepiece_ids",
            "barlow_ids",
            "binocular_ids",
            "filter_ids",
            "reducer_ids",
        ):
            state.setdefault(key, [])

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

    def _active_profile_binoculars(self) -> list[Binocular]:
        state = self._active_profile_state()
        return [binocular for binocular_id in state["binocular_ids"] if (binocular := self._find_binocular(binocular_id))]

    def _active_profile_filters(self) -> list[OpticalFilter]:
        state = self._active_profile_state()
        return [
            optical_filter
            for filter_id in state["filter_ids"]
            if (optical_filter := self._find_filter(filter_id))
        ]

    def _active_profile_reducers(self) -> list[FocalReducer]:
        state = self._active_profile_state()
        return [
            reducer
            for reducer_id in state["reducer_ids"]
            if (reducer := self._find_reducer(reducer_id))
        ]

    def _find_telescope(self, telescope_id: str) -> Telescope | None:
        return next((telescope for telescope in self._telescopes if telescope.id == telescope_id), None)

    def _find_eyepiece(self, eyepiece_id: str) -> Eyepiece | None:
        return next((eyepiece for eyepiece in self._eyepieces if eyepiece.id == eyepiece_id), None)

    def _find_barlow(self, barlow_id: str) -> Barlow | None:
        return next((barlow for barlow in self._barlows if barlow.id == barlow_id), None)

    def _find_binocular(self, binocular_id: str) -> Binocular | None:
        return next((binocular for binocular in self._binoculars if binocular.id == binocular_id), None)

    def _find_filter(self, filter_id: str) -> OpticalFilter | None:
        return next((item for item in self._filters if item.id == filter_id), None)

    def _find_reducer(self, reducer_id: str) -> FocalReducer | None:
        return next((item for item in self._reducers if item.id == reducer_id), None)

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
                    "badge": tr("Telescopio"),
                    "details": tr(
                        "{aperture} mm / {focal_length} mm",
                        aperture=format_number(telescope.aperture_mm),
                        focal_length=format_number(telescope.focal_length_mm),
                    ),
                    "type": telescope.optical_type,
                }
            )
        for eyepiece in self._eyepieces:
            badge = tr("Zoom") if eyepiece.eyepiece_type == "Zoom" else tr("Oculare")
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
                    "badge": tr("Barlow"),
                    "details": tr(
                        "{value}x",
                        value=format_compact_number(barlow.multiplier),
                    ),
                    "type": tr("Barlow"),
                }
            )
        for binocular in self._binoculars:
            items.append(
                {
                    "kind": "binocular",
                    "id": binocular.id,
                    "name": binocular.name,
                    "badge": tr("Binocolo"),
                    "details": binocular.to_qml()["specLabel"],
                    "type": tr("Binocolo stabilizzato") if binocular.image_stabilized else tr("Binocolo"),
                    "secondaryBadge": "IS" if binocular.image_stabilized else "",
                }
            )
        for optical_filter in self._catalog_filters:
            items.append(
                {
                    "kind": "filter",
                    "id": optical_filter["catalog_id"],
                    "name": optical_filter["display_name"],
                    "badge": tr("Filtro"),
                    "details": optical_filter["filter_class_label"],
                    "type": optical_filter["filter_class_label"],
                }
            )
        for reducer in self._catalog_reducers:
            items.append(
                {
                    "kind": "reducer",
                    "id": reducer["catalog_id"],
                    "name": reducer["display_name"],
                    "badge": tr("Riduttore"),
                    "details": join_text(
                        [
                            tr(
                                "{value}x",
                                value=format_compact_number(
                                    float(reducer["reduction_factor"])
                                ),
                            ),
                            reducer["optical_system_label"],
                        ]
                    ),
                    "type": reducer["optical_system_label"],
                    "secondaryBadge": self._reducer_use_label(reducer),
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
                    "badge": tr("Telescopio"),
                    "details": tr(
                        "{aperture} mm / {focal_length} mm",
                        aperture=format_number(telescope.aperture_mm),
                        focal_length=format_number(telescope.focal_length_mm),
                    ),
                }
            )
        for eyepiece in self._active_profile_eyepieces():
            items.append(
                {
                    "kind": "eyepiece",
                    "id": eyepiece.id,
                    "name": eyepiece.name,
                    "badge": tr("Zoom") if eyepiece.eyepiece_type == "Zoom" else tr("Oculare"),
                    "details": eyepiece.to_qml()["focalRangeLabel"],
                }
            )
        for barlow in self._active_profile_barlows():
            items.append(
                {
                    "kind": "barlow",
                    "id": barlow.id,
                    "name": barlow.name,
                    "badge": tr("Barlow"),
                    "details": tr(
                        "{value}x",
                        value=format_compact_number(barlow.multiplier),
                    ),
                }
            )
        for binocular in self._active_profile_binoculars():
            items.append(
                {
                    "kind": "binocular",
                    "id": binocular.id,
                    "name": binocular.name,
                    "badge": tr("Binocolo"),
                    "details": binocular.to_qml()["specLabel"],
                    "secondaryBadge": "IS" if binocular.image_stabilized else "",
                }
            )
        assigned_filter_ids = set(self._active_profile_state()["filter_ids"])
        for optical_filter in self._catalog_filters:
            if optical_filter["catalog_id"] not in assigned_filter_ids:
                continue
            items.append(
                {
                    "kind": "filter",
                    "id": optical_filter["catalog_id"],
                    "name": optical_filter["display_name"],
                    "badge": tr("Filtro"),
                    "details": optical_filter["filter_class_label"],
                }
            )
        assigned_reducer_ids = set(self._active_profile_state()["reducer_ids"])
        for reducer in self._catalog_reducers:
            if reducer["catalog_id"] not in assigned_reducer_ids:
                continue
            items.append(
                {
                    "kind": "reducer",
                    "id": reducer["catalog_id"],
                    "name": reducer["display_name"],
                    "badge": tr("Riduttore"),
                    "details": join_text(
                        [
                            tr(
                                "{value}x",
                                value=format_compact_number(
                                    float(reducer["reduction_factor"])
                                ),
                            ),
                            reducer["optical_system_label"],
                        ]
                    ),
                    "secondaryBadge": self._reducer_use_label(reducer),
                }
            )
        return items

    @staticmethod
    def _reducer_use_label(reducer: Mapping[str, object]) -> str:
        visual = bool(reducer.get("visual_compatible"))
        imaging = bool(reducer.get("imaging_compatible"))
        if visual and imaging:
            return tr("Visuale + foto")
        if visual:
            return tr("Visuale")
        return tr("Fotografico")

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
            if self._active_profile_binoculars():
                return tr(
                    "Profilo con binocolo: configura o seleziona un telescopio "
                    "per usare oculari e Barlow."
                )
            return tr("Modalità Occhio nudo: configura o seleziona un telescopio per usare oculari e Barlow.")
        eyepieces = self._active_profile_eyepieces()
        barlows = self._active_profile_barlows()
        if not eyepieces:
            return tr("Telescopio attivo senza oculari: suggerimenti limitati. Aggiungi oculari per calcoli completi.")
        barlow_count = len(barlows)
        barlow_text = (
            tr("1 Barlow")
            if barlow_count == 1
            else tr("{count} Barlow", count=barlow_count)
            if barlow_count > 1
            else tr("nessuna Barlow")
        )
        eyepiece_text = (
            tr("1 oculare")
            if len(eyepieces) == 1
            else tr("{count} oculari", count=len(eyepieces))
        )
        return tr(
            "Profilo attivo: {telescope}. Opzioni di ingrandimento: {eyepieces}, {barlows}.",
            telescope=telescope.name,
            eyepieces=eyepiece_text,
            barlows=barlow_text,
        )

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
                "coordinatesLabel": "",
            }
        return {
            "city": location.city,
            "country": location.country,
            "country_code": "",
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone,
            "coordinatesLabel": tr(
                "{latitude} / {longitude}",
                latitude=format_number(location.latitude, decimals=4),
                longitude=format_number(location.longitude, decimals=4),
            ),
        }
