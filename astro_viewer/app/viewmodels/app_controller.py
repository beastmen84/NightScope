"""Coordinate Qt signals, slots, asynchronous work, and QML-facing application state."""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock, Thread
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PySide6.QtCore import QCoreApplication, QObject, Property, QTimer, QUrl, Signal, Slot

from astro_viewer.app.application.dependencies import (
    AppControllerDependencies,
    build_app_controller_dependencies,
)
from astro_viewer.app.application.catalogue_recommendations import (
    apply_object_content_from_sources,
    home_visible_objects_for_window,
    moon_geometry_summary_to_condition_input,
    sky_compass_observable_target,
)
from astro_viewer.app.application.snapshots import (
    AstronomyRefreshSnapshot,
    CatalogueRecommendationPreparationContext,
    PreparedCatalogueRecommendationSnapshot,
    TransientEventRefreshSnapshot,
)
from astro_viewer.app.astronomy.engine import (
    MockAstronomyEngine,
    ObserverLocation,
    ObservingNightWindow,
    TransientCalendarEventSource,
)
from astro_viewer.app.models.condition_inputs import (
    AodConditionInput,
    MoonGeometryConditionInput,
    ObservationConditionInputs,
    ParticulateConditionInput,
)
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
)
from astro_viewer.app.models.imaging_runtime import (
    ImagingRuntimeInventory,
    ImagingRuntimeRecommendation,
)
from astro_viewer.app.models.imaging_recommendation import (
    ImagingCaptureMode,
    ImagingTargetClass,
)
from astro_viewer.app.models.observing import (
    AstronomicalEvent,
    CelestialObject,
    MoonGeometrySummary,
    MoonSummary,
)
from astro_viewer.app.models.sky import (
    ObservingCategoryScores,
    SeeingTransparency,
    SkyQuality,
)
from astro_viewer.app.models.weather import ObservingSessionDecision, WeatherBlockingStatus, WeatherHour, WeatherSummary
from astro_viewer.app.services.earthdata_credentials import (
    EARTHDATA_LAADS_AUTHORIZATION_URL,
)
from astro_viewer.app.services.equipment_taxonomy import (
    ASTRONOMY_CAMERA_CLASS_OPTIONS,
    CAMERA_BODY_TYPE_OPTIONS,
    CAMERA_SENSOR_FORMAT_OPTIONS,
    MOUNT_TYPE_OPTIONS,
    SENSOR_COLOR_MODE_OPTIONS,
    SENSOR_SHUTTER_OPTIONS,
    SENSOR_TECHNOLOGY_OPTIONS,
    TELESCOPE_CATEGORY_OPTIONS,
    TELESCOPE_OPTICAL_TYPE_OPTIONS,
)
from astro_viewer.app.services.equipment_setup_read_model import (
    EquipmentSetupReadModel,
)
from astro_viewer.app.services.light_pollution_service import LightPollutionService, ViirsCacheState
from astro_viewer.app.services.localization import (
    content_text,
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
    LocationUnavailableError,
)
from astro_viewer.app.services.nasa_aod_provider import NasaAodResult
from astro_viewer.app.services.best_object_nsom_ranking import (
    BestObjectNsomSelectionService,
)
from astro_viewer.app.services.catalogue_presentation import (
    catalogue_constellation_label,
    catalogue_object_type_label,
    catalogue_observation_type_label,
)
from astro_viewer.app.services.home_nsom_ranking import (
    HomeRecommendedDeepSkyNsomRankingService,
)
from astro_viewer.app.services.home_observing_overview import (
    bortle_observing_warning,
)
from astro_viewer.app.services.imaging_recommendation_presentation import (
    ImagingRecommendationPresenter,
)
from astro_viewer.app.services.imaging_runtime_assembler import (
    ImagingRuntimeAssembler,
)
from astro_viewer.app.services.imaging_runtime_conditions_adapter import (
    ImagingRuntimeConditionsAdapter,
)
from astro_viewer.app.services.imaging_target_traits import (
    ImagingTargetTraitsAdapter,
)
from astro_viewer.app.services.nsom_category_score_service import NsomCategoryScoreService
from astro_viewer.app.services.nsom_target import unique_targets_by_id
from astro_viewer.app.services.observation_conditions_read_model import (
    ObservationConditionedTargetReadModel,
    ObservationConditionsReadModelBuilder,
)
from astro_viewer.app.services.observation_log_service import (
    ObservationLogValidationError,
)
from astro_viewer.app.services.observing_night_service import (
    weather_hours_for_next_24,
    weather_hours_for_night,
)
from astro_viewer.app.services import (
    catalogue_detail_service,
    catalogue_query_service,
    catalogue_records,
    equipment_catalog_service,
    equipment_input,
    equipment_presentation,
    observing_presentation,
    observing_time,
    profile_equipment_service,
    weather_presentation,
)
from astro_viewer.app.services.catalogue_detail_service import CATALOGUE_SOURCE
from astro_viewer.app.services.catalogue_query_service import (
    CATALOGUE_ALL_FILTER,
    CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
)
from astro_viewer.app.services.openaq_atmosphere_service import LocalAtmosphere
from astro_viewer.app.services.refresh_lifecycle import RefreshDomain, RefreshManager, RefreshReason
from astro_viewer.app.services.sky_compass_service import SkyCompassService
from astro_viewer.app.services.weather_service import WEATHER_UNAVAILABLE_MESSAGE
from astro_viewer.app.viewmodels.catalogue_object_list_model import (
    CatalogueObjectListModel,
)


logger = logging.getLogger(__name__)

OBSERVING_SOURCE = "observing"
STARTUP_LOCATION_PENDING_MESSAGE = tr("Ricerca della posizione in corso...")
STARTUP_WEATHER_PENDING_MESSAGE = tr("Meteo in attesa della posizione.")
WEATHER_RETRY_DELAY_MS = 5 * 60 * 1000
CATALOGUE_RECOMMENDATION_REFRESH_DEBOUNCE_MS = 200
ASTRONOMY_REFRESH_FULL = "full_refresh"
ASTRONOMY_REFRESH_NIGHT_ROLLOVER = "night_rollover"
ASTRONOMY_REFRESH_VIIRS_DEEP_SKY = "viirs_deep_sky"
ASTRONOMY_REFRESH_CATALOGUE_RECOMMENDATION = (
    "catalogue_recommendation"
)


class AppController(QObject):
    dataChanged = Signal()
    selectedObjectChanged = Signal()
    observingObjectDetailChanged = Signal()
    catalogueChanged = Signal()
    catalogueFilteredCountChanged = Signal()
    catalogueRecommendationStateChanged = Signal()
    locationChanged = Signal()
    weatherChanged = Signal()
    equipmentChanged = Signal()
    profileInventoryChanged = Signal()
    photographicRecommendationChanged = Signal()
    cameraCatalogChanged = Signal()
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
    _catalogueRecommendationRefreshFinished = Signal(int, str, object)
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
        dependencies: AppControllerDependencies | None = None,
    ):
        super().__init__()
        self._photographic_recommendation_input_state: object | None = None
        self._earthdataConnectionTestFinished.connect(self._finish_earthdata_connection_test)
        self._openaqConnectionTestFinished.connect(self._finish_openaq_connection_test)
        self._viirsSkyQualityFinished.connect(self._finish_viirs_sky_quality_refresh)
        self._startupLocationDetectionFinished.connect(self._finish_startup_location_detection)
        self._weatherRefreshFinished.connect(self._finish_weather_refresh)
        self._localAtmosphereRefreshFinished.connect(self._finish_local_atmosphere_refresh)
        self._nasaAodRefreshFinished.connect(self._finish_nasa_aod_refresh)
        self._skyCompassLiveRefreshFinished.connect(self._finish_sky_compass_live_refresh)
        self._astronomyRefreshFinished.connect(self._finish_astronomy_refresh)
        self._catalogueRecommendationRefreshFinished.connect(
            self._finish_catalogue_recommendation_worker
        )
        self._transientEventsRefreshFinished.connect(self._finish_transient_event_refresh)
        self.dataChanged.connect(self.homeNightPlanChanged.emit)
        self.weatherChanged.connect(self.homeNightPlanChanged.emit)
        self.equipmentChanged.connect(self.homeNightPlanChanged.emit)
        self.equipmentChanged.connect(self.profileInventoryChanged.emit)
        self.selectedObjectChanged.connect(self.observingObjectDetailChanged.emit)
        self.weatherChanged.connect(self.observingObjectDetailChanged.emit)
        self.equipmentChanged.connect(self.observingObjectDetailChanged.emit)
        self.skyCompassChanged.connect(self.observingObjectDetailChanged.emit)
        self.selectedObjectChanged.connect(
            self._notify_photographic_recommendation_if_changed
        )
        self.profileInventoryChanged.connect(
            self._notify_photographic_recommendation_if_changed
        )
        self.weatherChanged.connect(
            self._notify_photographic_recommendation_if_changed
        )
        self.skyCompassChanged.connect(
            self._notify_photographic_recommendation_if_changed
        )
        self._base_dir = base_dir
        controller_dependencies = dependencies or build_app_controller_dependencies(
            base_dir=base_dir,
            database_path=database_path,
            preferences_path=preferences_path,
            location_cache_path=location_cache_path,
            nasa_aod_cache_path=nasa_aod_cache_path,
            best_object_nsom_selection_service=best_object_nsom_selection_service,
            home_recommended_deep_sky_nsom_ranking_service=(
                home_recommended_deep_sky_nsom_ranking_service
            ),
            nsom_category_score_service=nsom_category_score_service,
            sky_compass_service=sky_compass_service,
            transient_event_sources=transient_event_sources,
        )
        self._city_repository = controller_dependencies.city_repository
        self._location_repository = controller_dependencies.location_repository
        self._catalogue_repository = controller_dependencies.catalogue_repository
        self._equipment_catalog_repository = (
            controller_dependencies.equipment_catalog_repository
        )
        self._sky_quality_repository = controller_dependencies.sky_quality_repository
        self._object_image_repository = controller_dependencies.object_image_repository
        self._weather_cache_repository = controller_dependencies.weather_cache_repository
        self._observation_repository = controller_dependencies.observation_repository
        self._location_preferences = controller_dependencies.location_preferences
        self._earthdata_credential_store = (
            controller_dependencies.earthdata_credential_store
        )
        self._earthdata_connection_tester = (
            controller_dependencies.earthdata_connection_tester
        )
        self._earthdata_credentials_state = self._earthdata_credential_store.state()
        self._earthdata_connection_test_running = False
        self._openaq_credential_store = controller_dependencies.openaq_credential_store
        self._openaq_connection_tester = (
            controller_dependencies.openaq_connection_tester
        )
        self._local_atmosphere_service = (
            controller_dependencies.local_atmosphere_service
        )
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
        self._location_service = controller_dependencies.location_service
        self._is_loading = False
        self._service_status = controller_dependencies.startup_service_status
        self._weather_status = ""
        self._weather_refresh_running = False
        self._weather_refresh_request_id = 0
        self._weather_full_refresh_request_id: int | None = None
        self._weather_retry_pending = False
        self._astronomy_engine_lock = RLock()
        self._astronomy_refresh_running = False
        self._astronomy_refresh_request_id = 0
        self._catalogue_recommendation_refresh_generation = 0
        self._catalogue_recommendation_refresh_active_generation = 0
        self._catalogue_recommendation_refresh_running = False
        self._catalogue_recommendation_refresh_pending = False
        self._transient_event_refresh_running = False
        self._transient_event_refresh_request_id = 0
        self._transient_events_location_key = ""
        self._weather_refresh_timer = QTimer(self)
        self._weather_refresh_timer.setSingleShot(True)
        self._weather_refresh_timer.timeout.connect(self._refresh_weather_from_timer)
        self._catalogue_recommendation_refresh_timer = QTimer(self)
        self._catalogue_recommendation_refresh_timer.setSingleShot(True)
        self._catalogue_recommendation_refresh_timer.timeout.connect(
            self._start_pending_catalogue_recommendation_refresh
        )
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
        self._astronomy_engine = controller_dependencies.astronomy_engine
        self._weather_service = controller_dependencies.weather_service
        self._equipment_service = controller_dependencies.equipment_service
        self._equipment_catalog_service = (
            controller_dependencies.equipment_catalog_service
        )
        self._profile_equipment_service = (
            controller_dependencies.profile_equipment_service
        )
        self._equipment_presentation_service = (
            controller_dependencies.equipment_presentation_service
        )
        self._equipment_setup_read_model_builder = (
            controller_dependencies.equipment_setup_read_model_builder
        )
        self._filter_recommendation_service = (
            controller_dependencies.filter_recommendation_service
        )
        self._reducer_recommendation_service = (
            controller_dependencies.reducer_recommendation_service
        )
        self._score_service = controller_dependencies.score_service
        self._light_pollution_service = controller_dependencies.light_pollution_service
        self._nasa_aod_provider = controller_dependencies.nasa_aod_provider
        self._seeing_service = controller_dependencies.seeing_service
        self._nsom_category_score_service = (
            controller_dependencies.nsom_category_score_service
        )
        self._conditions_service = controller_dependencies.conditions_service
        self._conditions_read_model_builder = (
            controller_dependencies.conditions_read_model_builder
        )
        self._observation_log_service = controller_dependencies.observation_log_service
        self._best_object_nsom_selection_service = (
            controller_dependencies.best_object_nsom_selection_service
        )
        self._home_recommended_deep_sky_nsom_ranking_service = (
            controller_dependencies.home_recommended_deep_sky_nsom_ranking_service
        )
        self._home_observing_overview_service = (
            controller_dependencies.home_observing_overview_service
        )
        self._home_night_plan_overview_service = (
            controller_dependencies.home_night_plan_overview_service
        )
        self._calendar_overview_service = (
            controller_dependencies.calendar_overview_service
        )
        self._night_planner_service = controller_dependencies.night_planner_service
        self._sky_compass_service = controller_dependencies.sky_compass_service
        self._observing_object_detail_service = (
            controller_dependencies.observing_object_detail_service
        )
        self._imaging_runtime_assembler = (
            controller_dependencies.imaging_runtime_assembler
        )
        self._imaging_recommendation_presenter = (
            controller_dependencies.imaging_recommendation_presenter
        )
        self._refresh_manager = controller_dependencies.refresh_manager
        self._catalogue_recommendation_workflow = (
            controller_dependencies.catalogue_recommendation_workflow
        )
        self._observing_presentation_service = (
            controller_dependencies.observing_presentation_service
        )
        self._weather_presentation_service = (
            controller_dependencies.weather_presentation_service
        )
        self._catalogue_query_service = (
            controller_dependencies.catalogue_query_service
        )
        self._catalogue_detail_service = (
            controller_dependencies.catalogue_detail_service
        )

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
        self._selected_catalogue_item: dict | None = None
        self._best_object: CelestialObject | None = None
        self._observation_rows = self._observation_repository.list_all()
        self._observation_log = self._observation_log_service.build_entries(self._observation_rows)
        self._observation_log_summary = self._observation_log_service.build_summary(self._observation_rows)
        self._observation_message = ""

        self._beginner_presets = self._equipment_service.beginner_presets()
        equipment_catalog = self._equipment_catalog_service.load()
        self._apply_equipment_catalog_snapshot(equipment_catalog)
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
        self._catalogue_object_model = CatalogueObjectListModel(self)
        self.catalogueChanged.connect(self._refresh_catalogue_object_model)
        self._refresh_catalogue_object_model()
        self._profile_equipment = self._initial_profile_equipment()
        self._selected_telescope_index = self._initial_telescope_index()
        self._barlow = 1.0
        self._equipment_message = self._equipment_status_message()
        self._camera_catalog_message: object = ""

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

    @Property(QObject, constant=True)
    def catalogueObjectModel(self) -> CatalogueObjectListModel:
        return self._catalogue_object_model

    @Property(int, notify=catalogueRecommendationStateChanged)
    def catalogueBulkEnableCount(self) -> int:
        model = getattr(self, "_catalogue_object_model", None)
        return (
            model.recommendation_change_count(True)
            if model is not None
            else 0
        )

    @Property(int, notify=catalogueRecommendationStateChanged)
    def catalogueBulkDisableCount(self) -> int:
        model = getattr(self, "_catalogue_object_model", None)
        return (
            model.recommendation_change_count(False)
            if model is not None
            else 0
        )

    @Property(bool, notify=catalogueRecommendationStateChanged)
    def catalogueRecommendationRefreshActive(self) -> bool:
        return bool(
            getattr(
                self,
                "_catalogue_recommendation_refresh_pending",
                False,
            )
            or getattr(
                self,
                "_catalogue_recommendation_refresh_running",
                False,
            )
        )

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
        catalogue = self._catalogue_filters.get(
            "catalogue",
            CATALOGUE_ALL_FILTER,
        )
        if catalogue == CATALOGUE_ALL_FILTER:
            return len(self._catalogue_objects)
        return sum(
            len(self._catalogue_items_for_catalogue(item, catalogue))
            for item in self._catalogue_objects
        )

    @Property(int, notify=catalogueFilteredCountChanged)
    def catalogueFilteredCount(self) -> int:
        model = getattr(self, "_catalogue_object_model", None)
        if model is not None:
            return model.rowCount()
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

    @Property("QVariant", notify=photographicRecommendationChanged)
    def photographicRecommendation(self) -> dict:
        target = self._photographic_detail_target()
        if target is None:
            return {}
        presenter = getattr(
            self,
            "_imaging_recommendation_presenter",
            None,
        )
        if presenter is None:
            presenter = ImagingRecommendationPresenter()
            self._imaging_recommendation_presenter = presenter
        presentation = presenter.present(
            self._imaging_runtime_recommendation(target)
        )
        signature = self._photographic_recommendation_input_signature(
            target
        )
        if signature is not None:
            self._photographic_recommendation_input_state = signature
        return render_payload(presentation.to_payload())

    def _photographic_detail_target(self) -> CelestialObject | None:
        target = self._observing_detail_display_target()
        if target is None:
            target = self._selected_object
        if target is None:
            return None
        return self._moon_adjusted_object(target)

    @Slot()
    def _notify_photographic_recommendation_if_changed(self) -> None:
        signature = self._photographic_recommendation_input_signature()
        if signature is None or signature == getattr(
            self,
            "_photographic_recommendation_input_state",
            None,
        ):
            return
        self._photographic_recommendation_input_state = signature
        self.photographicRecommendationChanged.emit()

    def _photographic_recommendation_input_signature(
        self,
        target: CelestialObject | None = None,
    ) -> tuple[object, ...] | None:
        if not all(
            hasattr(self, attribute)
            for attribute in (
                "_equipment_profiles",
                "_profile_equipment",
                "_telescopes",
                "_reducers",
                "_barlows",
                "_astronomy_camera_catalog",
                "_camera_body_catalog",
            )
        ):
            return None
        target = target or self._photographic_detail_target()
        if target is None:
            return ("no_target",)
        traits = ImagingTargetTraitsAdapter.from_object(
            target,
            full_aperture_solar_filter_available=True,
        )
        conditions = ImagingRuntimeConditionsAdapter.from_runtime(
            target,
            sky_quality=getattr(self, "_sky_quality", None),
            seeing_transparency=getattr(
                self,
                "_seeing_transparency",
                None,
            ),
            moon=getattr(self, "_moon", None),
            moon_geometry=self._moon_geometry_condition_input(target),
        )
        target_signature = (
            target.id,
            target.name,
            target.object_type,
            target.magnitude,
            target.apparent_size,
            target.max_angular_size_deg,
            target.max_altitude,
            target.imaging_reducer_recommended,
            target.current_altitude_degrees,
        )
        condition_signature = (
            conditions.video
            if traits.recommended_capture_mode is ImagingCaptureMode.VIDEO
            else conditions.still
        )
        return (
            target_signature,
            AppController._photographic_inventory_signature(
                self._active_profile_imaging_inventory(),
                include_solar_filter_ids=(
                    traits.target_class is ImagingTargetClass.SUN
                ),
            ),
            condition_signature,
        )

    @staticmethod
    def _photographic_inventory_signature(
        inventory: ImagingRuntimeInventory,
        *,
        include_solar_filter_ids: bool,
    ) -> tuple[object, ...]:
        telescopes = tuple(
            sorted(
                (
                    telescope.id,
                    telescope.name,
                    telescope.aperture_mm,
                    telescope.focal_length_mm,
                    telescope.mount,
                    telescope.instrument_category,
                    telescope.supports_optical_visual,
                    telescope.supports_interchangeable_eyepieces,
                    telescope.supports_external_cameras,
                    telescope.supports_external_optical_modifiers,
                    telescope.integrated_imaging,
                )
                for telescope in inventory.telescopes
            )
        )
        reducers = tuple(
            sorted(
                (
                    reducer.id,
                    reducer.name,
                    reducer.reduction_factor,
                    reducer.backfocus_mm,
                    reducer.imaging_compatible,
                    tuple(sorted(reducer.compatible_telescope_ids)),
                )
                for reducer in inventory.reducers
            )
        )
        barlows = tuple(
            sorted(
                (
                    barlow.id,
                    barlow.name,
                    barlow.multiplier,
                )
                for barlow in inventory.barlows
            )
        )
        cameras = tuple(
            sorted(
                inventory.cameras,
                key=lambda camera: camera.id,
            )
        )
        solar_filter_ids = (
            tuple(
                sorted(
                    inventory.full_aperture_solar_filter_telescope_ids
                )
            )
            if include_solar_filter_ids
            else ()
        )
        return (
            inventory.profile_id,
            telescopes,
            cameras,
            reducers,
            barlows,
            solar_filter_ids,
        )

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
    def telescopeMountTypeOptions(self) -> list[dict[str, str]]:
        return render_payload(
            [{"code": code, "label": label} for code, label in MOUNT_TYPE_OPTIONS]
        )

    @Property("QVariant", notify=equipmentChanged)
    def telescopeCategoryOptions(self) -> list[dict[str, str]]:
        return render_payload(
            [
                {"code": code, "label": label}
                for code, label in TELESCOPE_CATEGORY_OPTIONS
            ]
        )

    @Property("QVariant", notify=equipmentChanged)
    def telescopeOpticalTypeOptions(self) -> list[dict[str, str]]:
        return render_payload(
            [
                {"code": code, "label": label}
                for code, label in TELESCOPE_OPTICAL_TYPE_OPTIONS
            ]
        )

    @Property("QVariant", notify=equipmentChanged)
    def eyepieceCatalog(self) -> list[dict]:
        return render_payload(self._catalog_eyepieces)

    @Property("QVariant", notify=equipmentChanged)
    def barlowCatalog(self) -> list[dict]:
        return render_payload(self._catalog_barlows)

    @Property("QVariant", notify=equipmentChanged)
    def binocularCatalog(self) -> list[dict]:
        return render_payload(self._catalog_binoculars)

    @Property("QVariant", notify=cameraCatalogChanged)
    def astronomyCameraCatalog(self) -> list[dict]:
        return render_payload(self._astronomy_camera_catalog)

    @Property("QVariant", notify=cameraCatalogChanged)
    def cameraBodyCatalog(self) -> list[dict]:
        return render_payload(self._camera_body_catalog)

    @Property("QVariant", notify=cameraCatalogChanged)
    def astronomyCameraClassOptions(self) -> list[dict[str, str]]:
        return render_payload(
            [
                {"code": code, "label": label}
                for code, label in ASTRONOMY_CAMERA_CLASS_OPTIONS
            ]
        )

    @Property("QVariant", notify=cameraCatalogChanged)
    def sensorTechnologyOptions(self) -> list[dict[str, str]]:
        return render_payload(
            [
                {"code": code, "label": label}
                for code, label in SENSOR_TECHNOLOGY_OPTIONS
            ]
        )

    @Property("QVariant", notify=cameraCatalogChanged)
    def sensorColorModeOptions(self) -> list[dict[str, str]]:
        return render_payload(
            [
                {"code": code, "label": label}
                for code, label in SENSOR_COLOR_MODE_OPTIONS
            ]
        )

    @Property("QVariant", notify=cameraCatalogChanged)
    def sensorShutterOptions(self) -> list[dict[str, str]]:
        return render_payload(
            [
                {"code": code, "label": label}
                for code, label in SENSOR_SHUTTER_OPTIONS
            ]
        )

    @Property("QVariant", notify=cameraCatalogChanged)
    def cameraBodyTypeOptions(self) -> list[dict[str, str]]:
        return render_payload(
            [
                {"code": code, "label": label}
                for code, label in CAMERA_BODY_TYPE_OPTIONS
            ]
        )

    @Property("QVariant", notify=cameraCatalogChanged)
    def cameraSensorFormatOptions(self) -> list[dict[str, str]]:
        return render_payload(
            [
                {"code": code, "label": label}
                for code, label in CAMERA_SENSOR_FORMAT_OPTIONS
            ]
        )

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

    @Property("QVariant", notify=profileInventoryChanged)
    def profileEquipmentCatalog(self) -> list[dict]:
        assigned_ids = {item["id"] for item in self._profile_assigned_equipment()}
        items = self._equipment_catalog_items()
        for item in items:
            item["assigned"] = item["id"] in assigned_ids
        return render_payload(items)

    @Property("QVariant", notify=profileInventoryChanged)
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

    @Property(str, notify=profileInventoryChanged)
    def equipmentMessage(self) -> str:
        return render_text(self._equipment_message)

    @Slot()
    def clearEquipmentMessage(self) -> None:
        if self._equipment_message:
            self._equipment_message = ""
            self.profileInventoryChanged.emit()

    @Property(str, notify=cameraCatalogChanged)
    def cameraCatalogMessage(self) -> str:
        return render_text(self._camera_catalog_message)

    @Slot()
    def clearCameraCatalogMessage(self) -> None:
        if self._camera_catalog_message:
            self._camera_catalog_message = ""
            self.cameraCatalogChanged.emit()

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
        self._photographic_recommendation_input_state = None

        self.locationChanged.emit()
        self.statusChanged.emit()
        self.earthdataCredentialsChanged.emit()
        self.openaqCredentialsChanged.emit()
        self.catalogueChanged.emit()
        self.equipmentChanged.emit()
        self.cameraCatalogChanged.emit()
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
                self._selected_catalogue_item = None
                self.selectedObjectChanged.emit()
                return

    @Slot(str)
    def selectCatalogueObject(self, object_id: str) -> None:
        item = self._catalogue_item_for_object_id(object_id)
        if not item:
            return
        item = self._catalogue_item_for_active_filter(item)
        self._selected_catalogue_item = dict(item)
        self._selected_object = self._catalogue_item_to_detail_object(item)
        self._selected_object_source = CATALOGUE_SOURCE
        self.selectedObjectChanged.emit()

    @Slot(str, str, str)
    def selectCatalogueDesignation(
        self,
        object_id: str,
        catalogue: str,
        designation: str,
    ) -> None:
        item = self._catalogue_item_for_object_id(object_id)
        if not item:
            return
        projected = self._catalogue_item_for_designation(
            item,
            catalogue,
            designation,
        )
        if projected is None:
            projected = self._catalogue_item_for_active_filter(item)
        self._selected_catalogue_item = dict(projected)
        self._selected_object = self._catalogue_item_to_detail_object(
            projected
        )
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
        self._apply_catalogue_recommendation_changes(
            (canonical_id,),
            enabled,
        )

    @Slot(bool)
    def setFilteredCatalogueRecommendationsEnabled(
        self,
        enabled: bool,
    ) -> None:
        enabled = bool(enabled)
        object_ids = (
            self._catalogue_object_model.recommendation_object_ids_requiring(
                enabled
            )
        )
        if not object_ids:
            return
        self._catalogue_repository.set_recommendations_enabled(
            object_ids,
            enabled,
        )
        self._apply_catalogue_recommendation_changes(
            object_ids,
            enabled,
        )

    def _apply_catalogue_recommendation_changes(
        self,
        object_ids: Sequence[str],
        enabled: bool,
    ) -> None:
        canonical_ids = []
        applied_ids = set()
        for object_id in object_ids:
            if not object_id.strip():
                continue
            item = self._catalogue_item_for_object_id(object_id)
            if item is None:
                continue
            canonical_id = str(item.get("object_id") or "").strip()
            normalized_id = canonical_id.casefold()
            if (
                not normalized_id
                or normalized_id in applied_ids
                or not bool(item.get("recommendation_editable", False))
            ):
                continue
            applied_ids.add(normalized_id)
            item["recommendation_enabled"] = enabled
            self._recommendation_enabled_by_object_id[
                normalized_id
            ] = enabled
            canonical_ids.append(canonical_id)
        if not canonical_ids:
            return

        self._catalogue_object_model.update_recommendations_enabled(
            canonical_ids,
            enabled,
        )
        self._refresh_after_catalogue_recommendation_changes(
            canonical_ids,
            enabled,
        )
        self._queue_catalogue_recommendation_refresh()
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
        state["full_aperture_solar_filter_telescope_ids"] = [
            item
            for item in state["full_aperture_solar_filter_telescope_ids"]
            if item != telescope_id
        ]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_telescope(int(profile["id"]), telescope_id)
            replacement = state["telescope_ids"][0] if state["telescope_ids"] else self._equipment_service.NAKED_EYE_ID
            self._equipment_catalog_repository.update_profile_telescope(int(profile["id"]), replacement)
            self._refresh_profiles_from_repository()
        self._equipment_message = self._equipment_status_message()
        self._refresh_active_profile_dependencies(reload_profile_equipment=True)
        self._emit_profile_dependent_changes()

    @Slot(str, bool)
    def setTelescopeSolarFilterAvailable(
        self,
        telescope_id: str,
        available: bool,
    ) -> None:
        telescope = self._find_telescope(telescope_id)
        state = self._active_profile_state()
        if telescope is None or telescope_id not in state["telescope_ids"]:
            return
        solar_filter_ids = state[
            "full_aperture_solar_filter_telescope_ids"
        ]
        if (telescope_id in solar_filter_ids) == available:
            return
        profile = self._active_profile()
        if profile is None:
            return
        updated = (
            self._equipment_catalog_repository
            .set_profile_full_aperture_solar_filter(
                int(profile["id"]),
                telescope_id,
                available,
            )
        )
        if not updated:
            return
        if available:
            solar_filter_ids.append(telescope_id)
            self._equipment_message = tr(
                "Filtro solare a tutta apertura disponibile per {name}. "
                "Le raccomandazioni visuali restano invariate.",
                name=telescope.name,
            )
        else:
            state["full_aperture_solar_filter_telescope_ids"] = [
                item for item in solar_filter_ids if item != telescope_id
            ]
            self._equipment_message = tr(
                "Filtro solare a tutta apertura non disponibile per {name}. "
                "Le raccomandazioni visuali restano invariate.",
                name=telescope.name,
            )
        self.profileInventoryChanged.emit()

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
        reducer = self._find_reducer(reducer_id)
        if reducer is None:
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
        active_telescope_ids = {
            telescope.id
            for telescope in self._active_profile_telescopes()
        }
        if not reducer.compatible_telescope_ids:
            self._equipment_message = tr(
                "Riduttore assegnato, ma compatibilità non configurata: "
                "resterà escluso dalle raccomandazioni visuali e "
                "fotografiche finché non colleghi almeno un telescopio."
            )
        elif active_telescope_ids.isdisjoint(
            reducer.compatible_telescope_ids
        ):
            self._equipment_message = tr(
                "Riduttore assegnato, ma non collegato a un telescopio del "
                "profilo attivo: resterà escluso dalle raccomandazioni "
                "visuali e fotografiche per questo profilo."
            )
        else:
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

    @Slot(str)
    def assignAstronomyCameraToActiveProfile(self, camera_id: str) -> None:
        if not self._find_astronomy_camera(camera_id):
            return
        state = self._active_profile_state()
        if camera_id not in state["astronomy_camera_ids"]:
            state["astronomy_camera_ids"].append(camera_id)
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.assign_profile_astronomy_camera(
                int(profile["id"]),
                camera_id,
            )
        self._equipment_message = tr(
            "Camera assegnata al profilo. "
            "Le raccomandazioni visuali restano invariate."
        )
        self.profileInventoryChanged.emit()

    @Slot(str)
    def removeAstronomyCameraFromActiveProfile(self, camera_id: str) -> None:
        state = self._active_profile_state()
        state["astronomy_camera_ids"] = [
            item
            for item in state["astronomy_camera_ids"]
            if item != camera_id
        ]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_astronomy_camera(
                int(profile["id"]),
                camera_id,
            )
        self._equipment_message = tr(
            "Camera rimossa dal profilo. "
            "Le raccomandazioni visuali restano invariate."
        )
        self.profileInventoryChanged.emit()

    @Slot(str)
    def assignCameraBodyToActiveProfile(self, camera_id: str) -> None:
        if not self._find_camera_body(camera_id):
            return
        state = self._active_profile_state()
        if camera_id not in state["camera_body_ids"]:
            state["camera_body_ids"].append(camera_id)
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.assign_profile_camera_body(
                int(profile["id"]),
                camera_id,
            )
        self._equipment_message = tr(
            "Camera assegnata al profilo. "
            "Le raccomandazioni visuali restano invariate."
        )
        self.profileInventoryChanged.emit()

    @Slot(str)
    def removeCameraBodyFromActiveProfile(self, camera_id: str) -> None:
        state = self._active_profile_state()
        state["camera_body_ids"] = [
            item for item in state["camera_body_ids"] if item != camera_id
        ]
        profile = self._active_profile()
        if profile:
            self._equipment_catalog_repository.remove_profile_camera_body(
                int(profile["id"]),
                camera_id,
            )
        self._equipment_message = tr(
            "Camera rimossa dal profilo. "
            "Le raccomandazioni visuali restano invariate."
        )
        self.profileInventoryChanged.emit()

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
        elif kind == "astronomy_camera":
            self.assignAstronomyCameraToActiveProfile(item_id)
        elif kind == "camera_body":
            self.assignCameraBodyToActiveProfile(item_id)

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
        elif kind == "astronomy_camera":
            self.removeAstronomyCameraFromActiveProfile(item_id)
        elif kind == "camera_body":
            self.removeCameraBodyFromActiveProfile(item_id)

    @Slot(str, str, result=int)
    def equipmentUsage(self, kind: str, item_id: str) -> int:
        return self._equipment_catalog_repository.profile_usage_count(kind, item_id)

    @Slot(
        str,
        str,
        str,
        str,
        str,
        str,
        str,
        str,
        "QVariantMap",
        result=bool,
    )
    def addTelescopeModel(
        self,
        brand: str,
        name: str,
        optical_type: str,
        aperture: str,
        focal: str,
        mount: str,
        notes: str,
        instrument_category: str = "TRADITIONAL",
        smart_capabilities: Mapping[str, object] | None = None,
    ) -> bool:
        try:
            aperture_mm = self._positive_int(aperture)
            focal_mm = self._positive_int(focal)
        except ValueError:
            self._equipment_message = tr("Dati telescopio non validi.")
            self.equipmentChanged.emit()
            return False
        ok, message = self._equipment_catalog_repository.add_telescope_model(
            brand,
            name,
            optical_type,
            aperture_mm,
            focal_mm,
            mount,
            notes,
            instrument_category,
            smart_capabilities,
        )
        self._after_catalog_change(message, ok)
        return ok

    @Slot(
        int,
        str,
        str,
        str,
        str,
        str,
        str,
        str,
        str,
        "QVariantMap",
        result=bool,
    )
    def updateTelescopeModel(
        self,
        model_id: int,
        brand: str,
        name: str,
        optical_type: str,
        aperture: str,
        focal: str,
        mount: str,
        notes: str,
        instrument_category: str = "TRADITIONAL",
        smart_capabilities: Mapping[str, object] | None = None,
    ) -> bool:
        try:
            aperture_mm = self._positive_int(aperture)
            focal_mm = self._positive_int(focal)
        except ValueError:
            self._equipment_message = tr("Dati telescopio non validi.")
            self.equipmentChanged.emit()
            return False
        ok, message = self._equipment_catalog_repository.update_telescope_model(
            model_id,
            brand,
            name,
            optical_type,
            aperture_mm,
            focal_mm,
            mount,
            notes,
            instrument_category,
            smart_capabilities,
        )
        self._after_catalog_change(message, ok)
        return ok

    @Slot(int, bool)
    def deleteTelescopeModel(self, model_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_telescope_model(model_id, remove_from_profiles=force)
        self._after_catalog_change(message, ok)

    @Slot("QVariantMap", result=bool)
    def addAstronomyCameraModel(self, payload: Mapping[str, object]) -> bool:
        parsed = self._parse_astronomy_camera_inputs(payload)
        if parsed is None:
            return False
        ok, message = self._equipment_catalog_repository.add_astronomy_camera(
            *parsed
        )
        self._after_camera_catalog_change(message, ok)
        return ok

    @Slot(int, "QVariantMap", result=bool)
    def updateAstronomyCameraModel(
        self,
        camera_id: int,
        payload: Mapping[str, object],
    ) -> bool:
        parsed = self._parse_astronomy_camera_inputs(payload)
        if parsed is None:
            return False
        ok, message = self._equipment_catalog_repository.update_astronomy_camera(
            camera_id,
            *parsed,
        )
        self._after_camera_catalog_change(message, ok)
        return ok

    @Slot(int, bool)
    def deleteAstronomyCameraModel(self, camera_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_astronomy_camera(
            camera_id,
            remove_from_profiles=force,
        )
        self._after_camera_catalog_change(message, ok)

    @Slot("QVariantMap", result=bool)
    def addCameraBodyModel(self, payload: Mapping[str, object]) -> bool:
        parsed = self._parse_camera_body_inputs(payload)
        if parsed is None:
            return False
        ok, message = self._equipment_catalog_repository.add_camera_body(*parsed)
        self._after_camera_catalog_change(message, ok)
        return ok

    @Slot(int, "QVariantMap", result=bool)
    def updateCameraBodyModel(
        self,
        camera_id: int,
        payload: Mapping[str, object],
    ) -> bool:
        parsed = self._parse_camera_body_inputs(payload)
        if parsed is None:
            return False
        ok, message = self._equipment_catalog_repository.update_camera_body(
            camera_id,
            *parsed,
        )
        self._after_camera_catalog_change(message, ok)
        return ok

    @Slot(int, bool)
    def deleteCameraBodyModel(self, camera_id: int, force: bool) -> None:
        ok, message = self._equipment_catalog_repository.delete_camera_body(
            camera_id,
            remove_from_profiles=force,
        )
        self._after_camera_catalog_change(message, ok)

    @Slot(str, str, str, str, str, str, str, str, str, result=bool)
    def addEyepieceModel(
        self,
        brand: str,
        model: str,
        eyepiece_type: str,
        focal: str,
        min_focal: str,
        max_focal: str,
        apparent_field: str,
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
            min_focal_length_mm=min_value,
            max_focal_length_mm=max_value,
            afov_min=afov_min,
            afov_max=afov_max,
            notes=notes,
        )
        self._after_catalog_change(message, ok)
        return ok

    @Slot(int, str, str, str, str, str, str, str, str, str, result=bool)
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

    @Slot(str, str, str, str, result=bool)
    def addBarlowModel(
        self,
        brand: str,
        model: str,
        multiplier: str,
        notes: str,
    ) -> bool:
        try:
            parsed_multiplier = float(multiplier.replace(",", "."))
            if not math.isfinite(parsed_multiplier):
                raise ValueError
        except ValueError:
            self._equipment_message = tr("Moltiplicatore Barlow non valido.")
            self.equipmentChanged.emit()
            return False
        ok, message = self._equipment_catalog_repository.add_barlow(
            brand,
            model,
            parsed_multiplier,
            notes,
        )
        self._after_catalog_change(message, ok)
        return ok

    @Slot(int, str, str, str, str, result=bool)
    def updateBarlowModel(
        self,
        barlow_id: int,
        brand: str,
        model: str,
        multiplier: str,
        notes: str,
    ) -> bool:
        try:
            parsed_multiplier = float(multiplier.replace(",", "."))
            if not math.isfinite(parsed_multiplier):
                raise ValueError
        except ValueError:
            self._equipment_message = tr("Moltiplicatore Barlow non valido.")
            self.equipmentChanged.emit()
            return False
        ok, message = self._equipment_catalog_repository.update_barlow(
            barlow_id,
            brand,
            model,
            parsed_multiplier,
            notes,
        )
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
        self.addEyepieceModel(
            "Custom",
            name,
            "Fixed",
            focal,
            "",
            "",
            apparent_field,
            "",
            "",
        )

    @Slot(str, str, str, str)
    def addZoomEyepiece(
        self,
        name: str,
        min_focal: str,
        max_focal: str,
        apparent_field: str,
    ) -> None:
        self.addEyepieceModel(
            "Custom",
            name,
            "Zoom",
            max_focal,
            min_focal,
            max_focal,
            apparent_field,
            "",
            "",
        )

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

    @Slot(str, str)
    def addBarlow(self, name: str, multiplier: str) -> None:
        self.addBarlowModel("Custom", name, multiplier, "")

    @Slot(str)
    def removeBarlow(self, barlow_id: str) -> None:
        if barlow_id.startswith("catalog-barlow-"):
            self.deleteBarlowModel(int(barlow_id.removeprefix("catalog-barlow-")), False)

    @Slot(str, str, str, str, str)
    def addTelescope(self, name: str, aperture: str, focal: str, optical_type: str, mount: str) -> None:
        self.addTelescopeModel(
            "Custom",
            name,
            optical_type,
            aperture,
            focal,
            mount,
            "",
            "TRADITIONAL",
        )

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
            self.updateTelescopeModel(
                int(telescope_id.removeprefix("catalog-telescope-")),
                existing["brand"] if existing else "Custom",
                name,
                optical_type,
                aperture,
                focal,
                mount,
                "",
                (
                    str(existing.get("instrument_category") or "TRADITIONAL")
                    if existing
                    else "TRADITIONAL"
                ),
            )

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
        self._cancel_catalogue_recommendation_refresh()
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

    def _queue_catalogue_recommendation_refresh(self) -> None:
        self._catalogue_recommendation_refresh_generation += 1
        if not self._has_valid_location():
            self._catalogue_recommendation_refresh_pending = False
            self.catalogueRecommendationStateChanged.emit()
            return
        self._catalogue_recommendation_refresh_pending = True
        self._catalogue_recommendation_refresh_timer.start(
            CATALOGUE_RECOMMENDATION_REFRESH_DEBOUNCE_MS
        )
        self.catalogueRecommendationStateChanged.emit()

    @Slot()
    def _start_pending_catalogue_recommendation_refresh(self) -> None:
        if (
            not self._catalogue_recommendation_refresh_pending
            or self._catalogue_recommendation_refresh_running
        ):
            return
        if not self._has_valid_location():
            self._catalogue_recommendation_refresh_pending = False
            self.catalogueRecommendationStateChanged.emit()
            return

        generation = self._catalogue_recommendation_refresh_generation
        location = self._location
        location_key = LightPollutionService._location_key(location)
        preparation_context = (
            self._catalogue_recommendation_preparation_context()
        )
        self._catalogue_recommendation_refresh_pending = False
        self._catalogue_recommendation_refresh_running = True
        self._catalogue_recommendation_refresh_active_generation = generation
        self.catalogueRecommendationStateChanged.emit()

        def run_refresh() -> None:
            snapshot = self._calculate_prepared_catalogue_recommendation_snapshot(
                location,
                preparation_context,
            )
            self._catalogueRecommendationRefreshFinished.emit(
                generation,
                location_key,
                snapshot,
            )

        try:
            self._start_background_task(run_refresh)
        except Exception:
            self._catalogue_recommendation_refresh_running = False
            self.catalogueRecommendationStateChanged.emit()
            logger.warning(
                "Catalogue recommendation worker could not start.",
                exc_info=True,
            )
            self._clear_refresh_domains(
                RefreshDomain.ASTRONOMY,
                RefreshDomain.EQUIPMENT,
            )

    @Slot(int, str, object)
    def _finish_catalogue_recommendation_worker(
        self,
        generation: int,
        location_key: str,
        snapshot: object,
    ) -> None:
        if generation != self._catalogue_recommendation_refresh_active_generation:
            return

        self._catalogue_recommendation_refresh_running = False
        is_current = (
            generation == self._catalogue_recommendation_refresh_generation
            and self._has_valid_location()
            and location_key
            == LightPollutionService._location_key(self._location)
        )
        if is_current:
            if not isinstance(
                snapshot,
                PreparedCatalogueRecommendationSnapshot,
            ):
                snapshot = PreparedCatalogueRecommendationSnapshot(
                    failed=True
                )
            elif (
                snapshot.runtime_signature
                != self._catalogue_recommendation_runtime_signature()
            ):
                self._queue_catalogue_recommendation_refresh()
                is_current = False
        if is_current:
            self._finish_catalogue_recommendation_refresh(snapshot)

        if self._catalogue_recommendation_refresh_pending:
            if not self._catalogue_recommendation_refresh_timer.isActive():
                self._catalogue_recommendation_refresh_timer.start(0)
            self.catalogueRecommendationStateChanged.emit()
            return
        if not is_current:
            self._clear_refresh_domains(
                RefreshDomain.ASTRONOMY,
                RefreshDomain.EQUIPMENT,
            )
        self.catalogueRecommendationStateChanged.emit()

    def _cancel_catalogue_recommendation_refresh(self) -> None:
        self._catalogue_recommendation_refresh_generation += 1
        self._catalogue_recommendation_refresh_pending = False
        timer = getattr(self, "_catalogue_recommendation_refresh_timer", None)
        if timer is not None:
            timer.stop()
        self.catalogueRecommendationStateChanged.emit()

    def _catalogue_recommendation_preparation_context(
        self,
    ) -> CatalogueRecommendationPreparationContext:
        solar_system_ids = {
            item.id
            for item in self._solar_system_objects
        }
        setup_models = tuple(
            (object_id, model)
            for object_id, model in self._equipment_setup_read_models_by_object_id.items()
            if object_id in solar_system_ids
        )
        return CatalogueRecommendationPreparationContext(
            runtime_signature=(
                self._catalogue_recommendation_runtime_signature()
            ),
            telescopes=tuple(self._active_profile_telescopes()),
            eyepieces=tuple(self._active_profile_eyepieces()),
            barlows=tuple(self._active_profile_barlows()),
            binoculars=tuple(self._active_profile_binoculars()),
            seeing_transparency=self._seeing_transparency,
            sky_quality=self._sky_quality,
            object_image_map=dict(self._object_image_map),
            object_descriptions=dict(self._object_descriptions),
            catalogue_identifier_index=dict(
                self._catalogue_identifier_index
            ),
            visible_planets=tuple(self._visible_planets),
            solar_setup_models=setup_models,
            moon_geometry_by_object_id=tuple(
                self._moon_geometry_condition_cache.items()
            ),
            condition_inputs=self._build_observation_condition_inputs(),
            pollution_condition_inputs=(
                self._build_observation_condition_inputs(
                    include_moon=False
                )
            ),
            weather_summary=self._weather_summary,
            current_telescope=self._current_telescope(),
            observing_night_window=self._observing_night_window,
            telescopes_by_id=tuple(
                (telescope.id, telescope)
                for telescope in self._telescopes
            ),
            use_target_equipment=bool(
                getattr(
                    self._night_planner_service,
                    "uses_target_equipment",
                    False,
                )
            ),
            sky_compass_caution_text=self._sky_compass_caution_text(),
        )

    def _catalogue_recommendation_runtime_signature(
        self,
    ) -> tuple[object, ...]:
        night_window = getattr(
            self,
            "_observing_night_window",
            ObservingNightWindow.unavailable(),
        )
        return (
            tuple(self._active_profile_telescopes()),
            tuple(self._active_profile_eyepieces()),
            tuple(self._active_profile_barlows()),
            tuple(self._active_profile_binoculars()),
            id(getattr(self, "_seeing_transparency", None)),
            id(getattr(self, "_sky_quality", None)),
            id(getattr(self, "_weather_summary", None)),
            id(getattr(self, "_moon", None)),
            id(getattr(self, "_nasa_aod_result", None)),
            id(getattr(self, "_local_atmosphere", None)),
            night_window.start,
            night_window.end,
            tuple(getattr(self, "_solar_system_objects", ())),
            tuple(getattr(self, "_visible_planets", ())),
        )

    def _calculate_prepared_catalogue_recommendation_snapshot(
        self,
        location: ObserverLocation,
        context: CatalogueRecommendationPreparationContext,
    ) -> PreparedCatalogueRecommendationSnapshot:
        astronomy = self._calculate_astronomy_snapshot(
            location,
            ASTRONOMY_REFRESH_CATALOGUE_RECOMMENDATION,
        )
        if astronomy.failed:
            return PreparedCatalogueRecommendationSnapshot(
                runtime_signature=context.runtime_signature,
                astronomy=astronomy,
                failed=True,
            )
        try:
            return self._prepare_catalogue_recommendation_snapshot(
                astronomy,
                context,
            )
        except Exception:
            logger.exception(
                "Catalogue recommendation preparation failed."
            )
            return PreparedCatalogueRecommendationSnapshot(
                runtime_signature=context.runtime_signature,
                astronomy=astronomy,
                failed=True,
            )

    def _prepare_catalogue_recommendation_snapshot(
        self,
        astronomy: AstronomyRefreshSnapshot,
        context: CatalogueRecommendationPreparationContext,
    ) -> PreparedCatalogueRecommendationSnapshot:
        return self._catalogue_recommendation_workflow.prepare(
            astronomy,
            context,
        )

    @classmethod
    def _home_visible_objects_for_window(
        cls,
        objects: Sequence[CelestialObject],
        night_window: ObservingNightWindow | None,
    ) -> tuple[CelestialObject, ...]:
        return home_visible_objects_for_window(objects, night_window)

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
                if purpose == ASTRONOMY_REFRESH_CATALOGUE_RECOMMENDATION:
                    deep_sky = tuple(
                        self._astronomy_engine.recommended_deep_sky(location)
                    )
                    geometry_method = getattr(
                        self._astronomy_engine,
                        "moon_geometry_batch",
                        None,
                    )
                    moon_geometry = (
                        geometry_method(location, list(deep_sky))
                        if callable(geometry_method)
                        else {}
                    )
                    return AstronomyRefreshSnapshot(
                        deep_sky=deep_sky,
                        moon_geometry=tuple(
                            (target.id, moon_geometry.get(target.id))
                            for target in deep_sky
                        ),
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
        if purpose == ASTRONOMY_REFRESH_CATALOGUE_RECOMMENDATION:
            self._finish_catalogue_recommendation_refresh_fallback(
                snapshot
            )
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
        return moon_geometry_summary_to_condition_input(summary)

    def _refresh_sky_compass(self) -> None:
        self._cancel_sky_compass_live_refresh()
        self._sky_compass_service.reset_live_direction_stability()
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
            return self._sky_compass_service.live_compass(
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
        return self._sky_compass_service.live_compass(
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
        return sky_compass_observable_target(raw_target, display_target)

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

    def _finish_catalogue_recommendation_refresh(
        self,
        snapshot: PreparedCatalogueRecommendationSnapshot,
    ) -> None:
        if snapshot.failed:
            self._finish_catalogue_recommendation_refresh_fallback(
                snapshot.astronomy
            )
            return

        astronomy = snapshot.astronomy
        selected_id = (
            self._selected_object.id
            if self._selected_object
            and self._selected_object_source == OBSERVING_SOURCE
            else ""
        )
        self._base_deep_sky = list(astronomy.deep_sky)
        for object_id, summary in astronomy.moon_geometry:
            self._moon_geometry_condition_cache[object_id] = (
                self._moon_geometry_summary_to_condition_input(summary)
            )
        self._deep_sky = list(snapshot.deep_sky)
        self._equipment_setup_read_models_by_object_id = dict(
            snapshot.equipment_setup_models
        )
        self._deep_sky_pollution_read_model = list(
            snapshot.deep_sky_pollution_read_model
        )
        self._deep_sky_raw_condition_input_by_id = dict(
            snapshot.deep_sky_raw_condition_inputs
        )
        self._conditioned_deep_sky = list(
            snapshot.conditioned_deep_sky
        )
        self._conditioned_home_objects = list(
            snapshot.conditioned_home_objects
        )
        self._conditioned_deep_sky_read_model = list(
            snapshot.conditioned_deep_sky_read_model
        )
        self._conditioned_home_read_model = list(
            snapshot.conditioned_home_read_model
        )
        self._category_scores = snapshot.category_scores
        self._best_object = snapshot.best_object
        self._night_plan = list(snapshot.night_plan)
        self._cancel_sky_compass_live_refresh()
        self._sky_compass_candidate_snapshot = list(
            snapshot.sky_compass_candidates
        )
        self._set_sky_compass(
            snapshot.sky_compass
            or SkyCompassService.empty(
                "no_targets",
                tr("Nessun oggetto osservabile in questo momento."),
            )
        )

        if selected_id:
            observing_objects = (
                self._solar_system_objects + self._deep_sky
            )
            replacement = next(
                (
                    candidate
                    for candidate in observing_objects
                    if candidate.id == selected_id
                ),
                None,
            )
            if replacement is None:
                suggestion_pool = (
                    self._visible_planets + self._deep_sky
                )
                replacement = self._best_object or next(
                    iter(suggestion_pool),
                    None,
                )
            self._selected_object = replacement
            self._selected_object_source = (
                OBSERVING_SOURCE
                if replacement is not None
                else ""
            )

        self.dataChanged.emit()
        self.weatherChanged.emit()
        self.selectedObjectChanged.emit()
        self._clear_refresh_domains(
            RefreshDomain.ASTRONOMY,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.COMPASS,
        )

    def _finish_catalogue_recommendation_refresh_fallback(
        self,
        astronomy: AstronomyRefreshSnapshot,
    ) -> None:
        if not astronomy.failed:
            try:
                self._base_deep_sky = list(astronomy.deep_sky)
                for object_id, summary in astronomy.moon_geometry:
                    self._moon_geometry_condition_cache[object_id] = (
                        self._moon_geometry_summary_to_condition_input(
                            summary
                        )
                    )
                self._refresh_equipment_recommendations_for_current_objects(
                    refresh_conditioned=False
                )
                self._deep_sky = (
                    self._apply_deep_sky_pollution_context(
                        self._deep_sky
                    )
                )
            except Exception:
                logger.warning(
                    "Deep-sky refresh after catalogue eligibility change "
                    "failed.",
                    exc_info=True,
                )
        self._recalculate_observing_outputs()
        self.dataChanged.emit()
        self.weatherChanged.emit()
        self.selectedObjectChanged.emit()
        self._clear_refresh_domains(
            RefreshDomain.ASTRONOMY,
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

    def _refresh_after_catalogue_recommendation_changes(
        self,
        object_ids: Sequence[str],
        enabled: bool,
    ) -> None:
        self._mark_refresh_dirty(RefreshReason.CATALOGUE_RECOMMENDATION_CHANGED)
        if self._has_valid_location():
            if not enabled:
                self._remove_catalogue_objects_from_current_recommendations(
                    object_ids
                )
            return

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

    def _remove_catalogue_objects_from_current_recommendations(
        self,
        object_ids: Sequence[str],
    ) -> None:
        normalized_ids = {
            object_id.strip().casefold()
            for object_id in object_ids
            if object_id.strip()
        }
        if not normalized_ids:
            return

        def keep_target(target: object) -> bool:
            target_id = str(
                getattr(target, "id", None)
                or getattr(target, "object_id", "")
            ).strip().casefold()
            return target_id not in normalized_ids

        self._deep_sky = [
            target for target in self._deep_sky if keep_target(target)
        ]
        self._conditioned_deep_sky = [
            target
            for target in self._conditioned_deep_sky
            if keep_target(target)
        ]
        self._conditioned_home_objects = [
            target
            for target in self._conditioned_home_objects
            if keep_target(target)
        ]
        self._conditioned_deep_sky_read_model = [
            model
            for model in self._conditioned_deep_sky_read_model
            if keep_target(model)
        ]
        self._conditioned_home_read_model = [
            model
            for model in self._conditioned_home_read_model
            if keep_target(model)
        ]
        self._deep_sky_pollution_read_model = [
            model
            for model in self._deep_sky_pollution_read_model
            if keep_target(model)
        ]
        self._sky_compass_candidate_snapshot = []
        self._night_plan = [
            step for step in self._night_plan if keep_target(step)
        ]
        self._equipment_setup_read_models_by_object_id = {
            object_id: model
            for object_id, model in (
                self._equipment_setup_read_models_by_object_id.items()
            )
            if object_id.strip().casefold() not in normalized_ids
        }
        self._deep_sky_raw_condition_input_by_id = {
            object_id: target
            for object_id, target in (
                self._deep_sky_raw_condition_input_by_id.items()
            )
            if object_id.strip().casefold() not in normalized_ids
        }

        if self._best_object and not keep_target(self._best_object):
            self._best_object = None

        if (
            self._selected_object
            and self._selected_object_source == OBSERVING_SOURCE
            and not keep_target(self._selected_object)
        ):
            suggestion_pool = self._visible_planets + self._deep_sky
            self._selected_object = self._best_object or next(
                iter(suggestion_pool),
                None,
            )
            self._selected_object_source = (
                OBSERVING_SOURCE if self._selected_object is not None else ""
            )

        self._cancel_sky_compass_live_refresh()
        self._set_sky_compass(
            SkyCompassService.empty(
                "catalogue_refresh_pending",
                tr("Aggiornamento suggerimenti in corso."),
            )
        )

    def _emit_profile_dependent_changes(self) -> None:
        self.equipmentChanged.emit()
        self.dataChanged.emit()
        self.weatherChanged.emit()
        self.selectedObjectChanged.emit()

    def _refresh_equipment_recommendations_for_current_objects(
        self,
        *,
        refresh_conditioned: bool = True,
    ) -> None:
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
        if refresh_conditioned:
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
        self._cancel_catalogue_recommendation_refresh()
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
        return self._apply_object_content_from_sources(
            item,
            self._object_image_map,
            self._object_descriptions,
            getattr(self, "_catalogue_identifier_index", {}),
        )

    @staticmethod
    def _apply_object_content_from_sources(
        item: CelestialObject,
        object_image_map: Mapping[str, dict],
        object_descriptions: Mapping[str, dict],
        catalogue_identifier_index: Mapping[str, dict],
    ) -> CelestialObject:
        return apply_object_content_from_sources(
            item,
            object_image_map,
            object_descriptions,
            catalogue_identifier_index,
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

    def _catalogue_query_service_instance(
        self,
    ) -> catalogue_query_service.CatalogueQueryService:
        service = getattr(self, "_catalogue_query_service", None)
        if service is None:
            service = catalogue_query_service.CatalogueQueryService(
                getattr(self, "_catalogue_repository", None)
            )
        return service

    def _catalogue_detail_service_instance(
        self,
    ) -> catalogue_detail_service.CatalogueDetailService:
        service = getattr(self, "_catalogue_detail_service", None)
        if service is None:
            service = catalogue_detail_service.CatalogueDetailService()
        return service

    def _load_catalogue_objects(self) -> list[dict]:
        return self._catalogue_query_service_instance().load_objects(
            self._object_descriptions
        )

    @staticmethod
    def _catalogue_item_from_record(row: dict) -> dict:
        return catalogue_records.catalogue_item_from_record(row)

    def _solar_system_catalogue_objects(self) -> list[dict]:
        return catalogue_records.solar_system_catalogue_objects(
            self._object_descriptions
        )

    def _catalogue_item_from_solar_system(
        self,
        config,
        sort_index: int,
    ) -> dict:
        return catalogue_records.catalogue_item_from_solar_system(
            config,
            sort_index,
            self._object_descriptions,
        )

    @staticmethod
    def _solar_system_search_terms(
        object_id: str,
        name: str,
        display_id: str,
    ) -> str:
        return catalogue_records.solar_system_search_terms(
            object_id,
            name,
            display_id,
        )

    @staticmethod
    def _catalogue_sort_key(item: dict) -> tuple[str, int, str]:
        return catalogue_records.catalogue_sort_key(item)

    def _refresh_catalogue_object_model(self) -> None:
        model = getattr(self, "_catalogue_object_model", None)
        if model is None:
            return
        model.replace_items(self._filtered_catalogue_objects())
        self.catalogueFilteredCountChanged.emit()
        self.catalogueRecommendationStateChanged.emit()

    def _filtered_catalogue_objects(self) -> list[dict]:
        visibility = (
            self._catalogue_visibility_map()
            if self._catalogue_visible_this_month_only
            else {}
        )
        return self._catalogue_query_service_instance().filtered_objects(
            self._catalogue_objects,
            search_query=self._catalogue_search_query,
            filters=self._catalogue_filters,
            visible_this_month_only=self._catalogue_visible_this_month_only,
            visibility=visibility,
            observability=self._catalogue_observability_map(),
            has_location=self._has_valid_location(),
            selected_month=self._catalogue_selected_month,
            year=self._catalogue_year,
        )

    @classmethod
    def _catalogue_search_sort_key(
        cls,
        item: dict,
        query: str,
    ) -> tuple[int, str, int, str]:
        return catalogue_query_service.catalogue_search_sort_key(item, query)

    @classmethod
    def _catalogue_query_matches_designation(
        cls,
        item: dict,
        query: str,
    ) -> bool:
        return catalogue_query_service.catalogue_query_matches_designation(
            item,
            query,
        )

    @staticmethod
    def _compact_catalogue_designation(value: str) -> str:
        return catalogue_query_service.compact_catalogue_designation(value)

    @staticmethod
    def _catalogue_item_for_catalogue(
        item: dict,
        catalogue: str,
    ) -> dict | None:
        return catalogue_query_service.catalogue_item_for_catalogue(
            item,
            catalogue,
        )

    @staticmethod
    def _catalogue_items_for_catalogue(
        item: dict,
        catalogue: str,
    ) -> list[dict]:
        return catalogue_query_service.catalogue_items_for_catalogue(
            item,
            catalogue,
        )

    @staticmethod
    def _catalogue_item_for_designation(
        item: dict,
        catalogue: str,
        designation: str,
    ) -> dict | None:
        return catalogue_query_service.catalogue_item_for_designation(
            item,
            catalogue,
            designation,
        )

    def _catalogue_item_with_visibility(
        self,
        item: dict,
        visibility: dict[str, bool],
        observability: dict[str, dict[str, bool | None]],
    ) -> dict:
        return catalogue_query_service.catalogue_item_with_visibility(
            item,
            visibility=visibility,
            observability=observability,
            visible_this_month_only=self._catalogue_visible_this_month_only,
            has_location=self._has_valid_location(),
            selected_month=self._catalogue_selected_month,
            year=self._catalogue_year,
        )

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

    def _catalogue_visibility_cache_key(
        self,
    ) -> tuple[float, float, str, int, int, float]:
        return catalogue_query_service.catalogue_visibility_cache_key(
            getattr(self, "_location", None),
            self._catalogue_year,
            self._catalogue_selected_month,
        )

    def _catalogue_observability_map(
        self,
    ) -> dict[str, dict[str, bool | None]]:
        if not self._has_valid_location():
            return {}
        cache_key = self._catalogue_observability_cache_key()
        cached = self._catalogue_observability_cache.get(cache_key)
        if cached is not None:
            return cached
        observability = catalogue_query_service.catalogue_observability_map(
            self._catalogue_objects,
            self._location,
        )
        self._catalogue_observability_cache[cache_key] = observability
        return observability

    def _catalogue_observability_cache_key(
        self,
    ) -> tuple[float, float, str, float]:
        return catalogue_query_service.catalogue_observability_cache_key(
            getattr(self, "_location", None)
        )

    @staticmethod
    def _catalogue_item_observability(
        item: dict,
        location: ObserverLocation | None,
    ) -> dict[str, bool | None]:
        return catalogue_query_service.catalogue_item_observability(
            item,
            location,
        )

    @staticmethod
    def _catalogue_boolean_label(value: bool | None) -> str:
        return catalogue_query_service.catalogue_boolean_label(value)

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
        return catalogue_query_service.catalogue_option_values(
            self._catalogue_objects,
            field_name,
        )

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
        return catalogue_query_service.catalogue_label(value)

    @staticmethod
    def _normalize_catalogue_filter_name(filter_name: str) -> str:
        return catalogue_query_service.normalize_catalogue_filter_name(
            filter_name
        )

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
    def _build_catalogue_identifier_index(
        objects: list[dict],
    ) -> dict[str, dict]:
        return catalogue_query_service.build_catalogue_identifier_index(
            objects
        )

    def _catalogue_item_to_detail_object(
        self,
        item: dict,
    ) -> CelestialObject:
        solar_system_source = (
            self._solar_system_detail_source(str(item["object_id"]))
            if self._is_solar_system_catalogue_item(item)
            else None
        )
        return self._catalogue_detail_service_instance().detail_object(
            item,
            solar_system_source=solar_system_source,
            apply_content=self._apply_object_content,
        )

    @staticmethod
    def _is_solar_system_catalogue_item(item: dict) -> bool:
        return catalogue_records.is_solar_system_catalogue_item(item)

    def _solar_system_catalogue_detail_object(
        self,
        item: dict,
    ) -> CelestialObject:
        return self._catalogue_detail_service_instance().detail_object(
            item,
            solar_system_source=self._solar_system_detail_source(
                str(item["object_id"])
            ),
            apply_content=self._apply_object_content,
        )

    def _solar_system_detail_source(
        self,
        object_id: str,
    ) -> CelestialObject | None:
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
        return catalogue_records.format_catalogue_number(value)

    @staticmethod
    def _format_catalogue_angle(value: object) -> str:
        return catalogue_records.format_catalogue_angle(value)

    @staticmethod
    def _is_catalogue_detail_object(item: CelestialObject) -> bool:
        return catalogue_detail_service.is_catalogue_detail_object(item)

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
        curiosity_text = presentation_text(
            curiosity.get("curiosity_text", ""), strip=True
        )
        if (
            not curiosity_text
            and item.id.startswith("ngc-")
            and self._is_catalogue_detail_object(item)
        ):
            curiosity_text = tr("Work in progress")
        data["curiosityText"] = curiosity_text
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
        catalogue_item = self._catalogue_item_for_object_id(item.id)
        if (
            catalogue_item
            and getattr(self, "_selected_object_source", "")
            == CATALOGUE_SOURCE
        ):
            selected_catalogue_item = getattr(
                self,
                "_selected_catalogue_item",
                None,
            )
            if (
                selected_catalogue_item
                and str(selected_catalogue_item.get("object_id", ""))
                == item.id
            ):
                catalogue_item = selected_catalogue_item
            else:
                catalogue_item = self._catalogue_item_for_active_filter(
                    catalogue_item
                )
        return self._catalogue_detail_service_instance().metadata(
            catalogue_item
        )

    def _catalogue_name_for_detail(self, item: CelestialObject) -> str:
        catalogue_item = self._catalogue_item_for_object_id(item.id)
        active_filter = (
            self._catalogue_filters.get(
                "catalogue",
                CATALOGUE_ALL_FILTER,
            )
            if getattr(self, "_selected_object_source", "")
            == CATALOGUE_SOURCE
            else CATALOGUE_ALL_FILTER
        )
        return self._catalogue_detail_service_instance().name_for_detail(
            catalogue_item,
            active_catalogue_filter=active_filter,
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

    def _observing_presentation_service_instance(
        self,
    ) -> observing_presentation.ObservingPresentationService:
        service = getattr(self, "_observing_presentation_service", None)
        if service is None:
            service = observing_presentation.ObservingPresentationService()
        return service

    def _weather_presentation_service_instance(
        self,
    ) -> weather_presentation.WeatherPresentationService:
        service = getattr(self, "_weather_presentation_service", None)
        if service is None:
            night_planner_service = getattr(
                self,
                "_night_planner_service",
                None,
            ) or weather_presentation.NightPlannerService()
            service = weather_presentation.WeatherPresentationService(
                night_planner_service
            )
        return service

    def _observing_status(self, item: CelestialObject) -> tuple[str, str]:
        _, status, detail = self._observing_status_data(item)
        return status, detail

    def _observing_status_data(self, item: CelestialObject) -> tuple[str, str, str]:
        if self._is_catalogue_detail_object(item):
            return self._observing_presentation_service_instance().status_data(
                item,
                catalogue_name=self._catalogue_name_for_detail(item),
                now=datetime.now(ZoneInfo("UTC")),
                night_window=ObservingNightWindow.unavailable(),
                monthly_visibility_blocked=False,
                useful_datetime=None,
                window="",
                altitude_threshold=self._observing_altitude_threshold(item),
            )
        useful_datetime = self._first_observing_datetime(
            item.best_time
        ) or self._first_observing_datetime(item.observing_window)
        return self._observing_presentation_service_instance().status_data(
            item,
            catalogue_name=None,
            now=datetime.now(self._zone()),
            night_window=getattr(
                self,
                "_observing_night_window",
                ObservingNightWindow.unavailable(),
            ),
            monthly_visibility_blocked=(
                self._is_solar_system_monthly_visibility_blocked(item)
            ),
            useful_datetime=useful_datetime,
            window=self._home_window_label(item),
            altitude_threshold=self._observing_altitude_threshold(item),
        )

    @staticmethod
    def _is_planetary_or_lunar_target(item: CelestialObject) -> bool:
        return observing_presentation.is_planetary_or_lunar_target(item)

    @classmethod
    def _observing_altitude_threshold(cls, item: CelestialObject) -> float:
        return observing_presentation.observing_altitude_threshold(item)

    def _is_solar_system_monthly_visibility_blocked(
        self,
        item: CelestialObject,
    ) -> bool:
        if item.object_type != "Pianeta":
            return False
        return self._catalogue_month_visible_for_object(item.id) is False

    def _observing_reasons(self, item: CelestialObject) -> list[str]:
        return self._observing_presentation_service_instance().reasons(
            item,
            is_catalogue_detail=self._is_catalogue_detail_object(item),
            moon=getattr(self, "_moon", None),
            seeing_transparency=getattr(self, "_seeing_transparency", None),
            sky_quality=getattr(self, "_sky_quality", None),
        )

    @staticmethod
    def _altitude_reason(max_altitude: float) -> str:
        return observing_presentation.altitude_reason(max_altitude)

    @staticmethod
    def _localized_seeing(value: str) -> str:
        return observing_presentation.localized_seeing(value)

    def _sky_quality_reason(self, item: CelestialObject) -> str:
        return observing_presentation.sky_quality_reason(
            item,
            self._sky_quality,
        )

    def _setup_reason(self, item: CelestialObject) -> str:
        return self._observing_presentation_service_instance().setup_reason(item)

    @staticmethod
    def _recommended_setup_option(item: CelestialObject) -> dict:
        return observing_presentation.recommended_setup_option(item)

    @staticmethod
    def _recommendation_setup_type(suggestion: dict) -> str:
        return observing_presentation.recommendation_setup_type(suggestion)

    @staticmethod
    def _moon_cycle_fraction(phase_angle: float) -> float:
        return observing_presentation.moon_cycle_fraction(phase_angle)

    @staticmethod
    def _moon_cycle_day_label(phase_angle: float) -> str:
        return observing_presentation.moon_cycle_day_label(phase_angle)

    def _update_observing_night_window(self) -> bool:
        previous = getattr(
            self,
            "_observing_night_window",
            ObservingNightWindow.unavailable(),
        )
        if not self._has_valid_location():
            current = ObservingNightWindow.unavailable()
        else:
            method = getattr(
                self._astronomy_engine,
                "observing_night_window",
                None,
            )
            try:
                if callable(method):
                    with self._astronomy_engine_lock_instance():
                        current = method(self._location)
                else:
                    current = ObservingNightWindow.unavailable()
            except Exception:
                logger.warning(
                    "Observing night window refresh failed.",
                    exc_info=True,
                )
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
        return observing_time.same_observing_night(left, right)

    def _observing_weather_hours(self) -> list[WeatherHour]:
        if not hasattr(self, "_location") or not hasattr(
            self,
            "_observing_night_window",
        ):
            return list(getattr(self, "_weather_hours", []))
        if not self._has_valid_location():
            return []
        return weather_hours_for_night(
            self._weather_hours,
            self._observing_night_window,
            self._location.timezone,
        )

    def _next_24_weather_hours(self) -> list[WeatherHour]:
        timezone = (
            self._location.timezone
            if getattr(self, "_location", None)
            else "UTC"
        )
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
            return self._weather_presentation_service_instance().digest(
                [],
                ObservingNightWindow.unavailable(),
                "UTC",
            )
        return self._weather_presentation_service_instance().digest(
            night_hours,
            self._observing_night_window,
            self._location.timezone,
        )

    def _weather_blocking_status(self) -> WeatherBlockingStatus:
        return self._weather_presentation_service_instance().blocking_status(
            self._weather_summary
        )

    def _observing_session_decision(self) -> ObservingSessionDecision:
        return self._weather_presentation_service_instance().session_decision(
            self._weather_summary,
            self._observing_weather_hours(),
        )

    def _suggested_observing_window(self) -> str:
        night_hours = self._observing_weather_hours()
        return self._weather_presentation_service_instance().suggested_observing_window(
            self._weather_summary,
            night_hours,
            getattr(
                self,
                "_observing_night_window",
                ObservingNightWindow.unavailable(),
            ),
            (
                self._location.timezone
                if getattr(self, "_location", None)
                else "UTC"
            ),
        )

    @staticmethod
    def _best_weather_hours(hours: list[WeatherHour]) -> list[WeatherHour]:
        return weather_presentation.best_weather_hours(hours)

    def _best_usable_observing_window(self) -> list[WeatherHour]:
        return weather_presentation.best_usable_observing_window(
            self._observing_weather_hours()
        )

    @staticmethod
    def _is_usable_weather_hour(hour: WeatherHour) -> bool:
        return weather_presentation.is_usable_weather_hour(hour)

    @staticmethod
    def _weather_hour_observing_score(hour: WeatherHour) -> int:
        return weather_presentation.weather_hour_observing_score(hour)

    @staticmethod
    def _weather_slice_score(hours: list[WeatherHour]) -> float:
        return weather_presentation.weather_slice_score(hours)

    @staticmethod
    def _selected_weather_hours(hours: list[WeatherHour]) -> list[WeatherHour]:
        return weather_presentation.selected_weather_hours(hours)

    @staticmethod
    def _weather_window_label(
        hours: list[WeatherHour],
        night_window: ObservingNightWindow | None = None,
        timezone: str = "UTC",
    ) -> str:
        return weather_presentation.weather_window_label(
            hours,
            night_window,
            timezone,
        )

    @staticmethod
    def _wind_label(wind_kmh: int) -> str:
        return weather_presentation.wind_label(wind_kmh)

    def _home_time_label(self, item: CelestialObject) -> str:
        return observing_time.home_time_label(
            item,
            getattr(self, "_observing_night_window", None),
        )

    def _home_window_label(self, item: CelestialObject) -> str:
        return observing_time.home_window_label(
            item,
            getattr(self, "_observing_night_window", None),
        )

    def _first_useful_time(self, value: str) -> tuple[int, int] | None:
        return observing_time.first_useful_time(
            value,
            getattr(self, "_observing_night_window", None),
        )

    def _first_observing_datetime(self, value: str) -> datetime | None:
        return observing_time.first_observing_datetime(
            value,
            getattr(self, "_observing_night_window", None),
        )

    def _observing_datetime_for_clock(
        self,
        hour: int,
        minute: int,
    ) -> datetime | None:
        return observing_time.observing_datetime_for_clock(
            getattr(self, "_observing_night_window", None),
            hour,
            minute,
        )

    @staticmethod
    def _all_times(value: str) -> list[tuple[int, int]]:
        return observing_time.all_times(value)

    @staticmethod
    def _parse_hour_minute(value: str) -> tuple[int, int] | None:
        return observing_time.parse_hour_minute(value)

    @staticmethod
    def _parse_degrees(value: str) -> float | None:
        return observing_presentation.parse_degrees(value)

    @staticmethod
    def _parse_event_date(value: str, now: datetime) -> datetime | None:
        return observing_time.parse_event_date(value, now)

    def _format_home_datetime(self, value: datetime) -> str:
        return observing_time.format_home_datetime(value)

    def _home_time_period_code(self, value: datetime) -> str:
        return observing_time.home_time_period_code(
            value,
            getattr(self, "_observing_night_window", None),
        )

    @staticmethod
    def _format_clock(hour: int, minute: int) -> str:
        return observing_time.format_clock(hour, minute)

    def _equipment_catalog_manager(
        self,
    ) -> equipment_catalog_service.EquipmentCatalogService:
        service = getattr(self, "_equipment_catalog_service", None)
        if service is None:
            service = equipment_catalog_service.EquipmentCatalogService(
                self._equipment_catalog_repository,
                self._equipment_service,
            )
            self._equipment_catalog_service = service
        return service

    def _profile_equipment_manager(
        self,
    ) -> profile_equipment_service.ProfileEquipmentService:
        service = getattr(self, "_profile_equipment_service", None)
        if service is None:
            service = profile_equipment_service.ProfileEquipmentService(
                self._equipment_catalog_repository,
                self._equipment_service,
                self._equipment_catalog_manager(),
            )
            self._profile_equipment_service = service
        return service

    def _equipment_presenter(
        self,
    ) -> equipment_presentation.EquipmentPresentationService:
        service = getattr(self, "_equipment_presentation_service", None)
        if service is None:
            service = equipment_presentation.EquipmentPresentationService(
                self._equipment_service
            )
            self._equipment_presentation_service = service
        return service

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
        return self._equipment_catalog_manager().telescope_from_profile(
            profile,
            existing_telescopes,
        )

    @staticmethod
    def _telescope_from_catalog_model(model: dict) -> Telescope:
        return equipment_catalog_service.telescope_from_catalog_model(model)

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
        return equipment_catalog_service.localized_equipment_catalog_rows(
            rows,
            section_name,
        )

    def _apply_equipment_catalog_snapshot(
        self,
        snapshot: equipment_catalog_service.EquipmentCatalogSnapshot,
    ) -> None:
        self._telescope_brands = list(snapshot.telescope_brands)
        self._telescope_catalog_models = list(snapshot.telescope_catalog_models)
        self._catalog_eyepieces = list(snapshot.eyepiece_rows)
        self._catalog_barlows = list(snapshot.barlow_rows)
        self._catalog_binoculars = list(snapshot.binocular_rows)
        self._astronomy_camera_catalog = list(snapshot.astronomy_camera_rows)
        self._camera_body_catalog = list(snapshot.camera_body_rows)
        self._catalog_filters = list(snapshot.filter_rows)
        self._catalog_reducers = list(snapshot.reducer_rows)
        self._telescopes = list(snapshot.telescopes)
        self._eyepieces = list(snapshot.eyepieces)
        self._barlows = list(snapshot.barlows)
        self._binoculars = list(snapshot.binoculars)
        self._filters = list(snapshot.filters)
        self._reducers = list(snapshot.reducers)

    def _refresh_equipment_catalogs(self) -> None:
        self._apply_equipment_catalog_snapshot(
            self._equipment_catalog_manager().load()
        )
        self._profile_equipment = self._initial_profile_equipment()
        self._selected_telescope_index = self._initial_telescope_index()

    def _refresh_binocular_catalog(self) -> None:
        rows, binoculars = self._equipment_catalog_manager().load_binoculars()
        self._catalog_binoculars = list(rows)
        self._binoculars = list(binoculars)
        self._profile_equipment = self._initial_profile_equipment()

    def _refresh_camera_catalogs(self) -> None:
        astronomy_cameras, camera_bodies = (
            self._equipment_catalog_manager().load_cameras()
        )
        self._astronomy_camera_catalog = list(astronomy_cameras)
        self._camera_body_catalog = list(camera_bodies)

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

    def _after_camera_catalog_change(self, message: str, ok: bool) -> None:
        self._camera_catalog_message = message
        if ok:
            self._refresh_camera_catalogs()
            self._profile_equipment = self._initial_profile_equipment()
        self.cameraCatalogChanged.emit()
        if ok:
            self.profileInventoryChanged.emit()

    def _parse_astronomy_camera_inputs(
        self,
        payload: Mapping[str, object],
    ) -> tuple | None:
        try:
            return equipment_input.parse_astronomy_camera_inputs(payload)
        except equipment_input.EquipmentInputError:
            self._camera_catalog_message = tr(
                "Dati della camera astronomica non validi."
            )
            self.cameraCatalogChanged.emit()
            return None

    def _parse_camera_body_inputs(
        self,
        payload: Mapping[str, object],
    ) -> tuple | None:
        try:
            return equipment_input.parse_camera_body_inputs(payload)
        except equipment_input.EquipmentInputError:
            self._camera_catalog_message = tr("Dati del corpo macchina non validi.")
            self.cameraCatalogChanged.emit()
            return None

    def _parse_filter_inputs(
        self,
        central_wavelength: str,
        bandwidth: str,
        transmission: str,
        minimum_aperture: str,
    ) -> tuple[float | None, float | None, float | None, int | None] | None:
        try:
            return equipment_input.parse_filter_inputs(
                central_wavelength,
                bandwidth,
                transmission,
                minimum_aperture,
            )
        except equipment_input.EquipmentInputError:
            self._equipment_message = tr("Dati filtro non validi.")
            self.equipmentChanged.emit()
            return None

    def _parse_reducer_inputs(
        self,
        reduction_factor: str,
        backfocus: str,
    ) -> tuple[float, float | None] | None:
        try:
            return equipment_input.parse_reducer_inputs(
                reduction_factor,
                backfocus,
            )
        except equipment_input.EquipmentInputError:
            self._equipment_message = tr("Dati riduttore non validi.")
            self.equipmentChanged.emit()
            return None

    @staticmethod
    def _catalog_id_list(value: str) -> tuple[str, ...]:
        return equipment_input.catalog_id_list(value)

    @staticmethod
    def _optional_float_input(value: str) -> float | None:
        return equipment_input.optional_float_input(value)

    @staticmethod
    def _required_float_input(value: object) -> float:
        return equipment_input.required_float_input(value)

    @classmethod
    def _optional_positive_int_input(cls, value: object) -> int | None:
        return equipment_input.optional_positive_int_input(value)

    def _parse_binocular_inputs(
        self,
        magnification: str,
        objective_diameter: str,
    ) -> tuple[int, int] | None:
        try:
            return equipment_input.parse_binocular_inputs(
                magnification,
                objective_diameter,
            )
        except equipment_input.EquipmentInputError:
            self._equipment_message = tr("Dati binocolo non validi.")
            self.equipmentChanged.emit()
            return None

    @staticmethod
    def _positive_int(value: str) -> int:
        return equipment_input.positive_int(value)

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
            return equipment_input.parse_eyepiece_inputs(
                eyepiece_type,
                focal,
                min_focal,
                max_focal,
                apparent_field,
                afov_range,
            )
        except equipment_input.EquipmentInputError as exc:
            messages = {
                "eyepiece_afov_invalid": tr("Intervallo AFOV non valido."),
                "eyepiece_non_positive": tr(
                    "Focale e campo apparente devono essere maggiori di zero."
                ),
            }
            self._equipment_message = messages.get(
                exc.code,
                tr("Dati oculare non validi."),
            )
            self.equipmentChanged.emit()
            return None

    def _catalog_telescopes(self) -> list[Telescope]:
        return [
            equipment_catalog_service.telescope_from_catalog_model(model)
            for model in self._telescope_catalog_models
        ]

    @staticmethod
    def _eyepiece_from_catalog_row(row: dict) -> Eyepiece:
        return equipment_catalog_service.eyepiece_from_catalog_row(row)

    @staticmethod
    def _parse_zoom_click_positions(value: str) -> tuple[float, ...]:
        return equipment_catalog_service.parse_zoom_click_positions(value)

    @staticmethod
    def _barlow_from_catalog_row(row: dict) -> Barlow:
        return equipment_catalog_service.barlow_from_catalog_row(row)

    @staticmethod
    def _binocular_from_catalog_row(row: dict) -> Binocular:
        return equipment_catalog_service.binocular_from_catalog_row(row)

    @staticmethod
    def _filter_from_catalog_row(row: dict) -> OpticalFilter:
        return equipment_catalog_service.filter_from_catalog_row(row)

    @staticmethod
    def _reducer_from_catalog_row(row: dict) -> FocalReducer:
        return equipment_catalog_service.reducer_from_catalog_row(row)

    def _initial_profile_equipment(self) -> dict[str, dict[str, list[str]]]:
        return self._profile_equipment_manager().initial_profile_equipment(
            self._equipment_profiles
        )

    def _refresh_profiles_from_repository(self) -> None:
        self._equipment_profiles = (
            self._profile_equipment_manager().refresh_profiles(
                self._profile_equipment
            )
        )

    def _active_profile(self) -> dict | None:
        return profile_equipment_service.active_profile(
            self._equipment_profiles
        )

    def _presented_equipment_profiles(self) -> list[dict]:
        return profile_equipment_service.presented_equipment_profiles(
            self._equipment_profiles
        )

    def _active_profile_state(self) -> dict[str, list[str]]:
        return profile_equipment_service.active_profile_state(
            self._equipment_profiles,
            self._profile_equipment,
        )

    @staticmethod
    def _empty_profile_equipment_state() -> dict[str, list[str]]:
        return profile_equipment_service.empty_profile_equipment_state()

    @staticmethod
    def _ensure_profile_equipment_state(state: dict[str, list[str]]) -> None:
        profile_equipment_service.ensure_profile_equipment_state(state)

    def _profile_key_by_name(self, profile_name: str) -> str:
        return profile_equipment_service.profile_key_by_name(
            self._equipment_profiles,
            profile_name,
        )

    def _owned_telescopes(self) -> list[Telescope]:
        return self._catalog_telescopes()

    def _active_profile_telescopes(self) -> list[Telescope]:
        state = self._active_profile_state()
        return profile_equipment_service.select_by_ids(
            self._telescopes,
            state["telescope_ids"],
        )

    def _active_profile_has_full_aperture_solar_filter(
        self,
        telescope_id: str,
    ) -> bool:
        return (
            telescope_id
            in self._active_profile_state()[
                "full_aperture_solar_filter_telescope_ids"
            ]
        )

    def _active_profile_eyepieces(self) -> list[Eyepiece]:
        state = self._active_profile_state()
        return profile_equipment_service.select_by_ids(
            self._eyepieces,
            state["eyepiece_ids"],
        )

    def _active_profile_barlows(self) -> list[Barlow]:
        state = self._active_profile_state()
        return profile_equipment_service.select_by_ids(
            self._barlows,
            state["barlow_ids"],
        )

    def _active_profile_binoculars(self) -> list[Binocular]:
        state = self._active_profile_state()
        return profile_equipment_service.select_by_ids(
            self._binoculars,
            state["binocular_ids"],
        )

    def _active_profile_filters(self) -> list[OpticalFilter]:
        state = self._active_profile_state()
        return profile_equipment_service.select_by_ids(
            self._filters,
            state["filter_ids"],
        )

    def _active_profile_reducers(self) -> list[FocalReducer]:
        state = self._active_profile_state()
        return profile_equipment_service.select_by_ids(
            self._reducers,
            state["reducer_ids"],
        )

    def _active_profile_imaging_inventory(
        self,
    ) -> ImagingRuntimeInventory:
        profile = self._active_profile()
        return profile_equipment_service.imaging_inventory(
            profile=profile,
            state=self._active_profile_state(),
            telescopes=self._telescopes,
            astronomy_camera_rows=self._astronomy_camera_catalog,
            camera_body_rows=self._camera_body_catalog,
            reducers=self._reducers,
            barlows=self._barlows,
        )

    def _imaging_runtime_recommendation(
        self,
        target: CelestialObject,
    ) -> ImagingRuntimeRecommendation:
        """Build a current photographic plan only when a caller requests it."""

        conditions = ImagingRuntimeConditionsAdapter.from_runtime(
            target,
            sky_quality=getattr(self, "_sky_quality", None),
            seeing_transparency=getattr(
                self,
                "_seeing_transparency",
                None,
            ),
            moon=getattr(self, "_moon", None),
            moon_geometry=self._moon_geometry_condition_input(target),
        )
        assembler = getattr(self, "_imaging_runtime_assembler", None)
        if assembler is None:
            assembler = ImagingRuntimeAssembler()
            self._imaging_runtime_assembler = assembler
        return assembler.assemble(
            target,
            self._active_profile_imaging_inventory(),
            conditions,
        )

    def _find_telescope(self, telescope_id: str) -> Telescope | None:
        return profile_equipment_service.find_by_id(
            self._telescopes,
            telescope_id,
        )

    def _find_eyepiece(self, eyepiece_id: str) -> Eyepiece | None:
        return profile_equipment_service.find_by_id(
            self._eyepieces,
            eyepiece_id,
        )

    def _find_barlow(self, barlow_id: str) -> Barlow | None:
        return profile_equipment_service.find_by_id(
            self._barlows,
            barlow_id,
        )

    def _find_binocular(self, binocular_id: str) -> Binocular | None:
        return profile_equipment_service.find_by_id(
            self._binoculars,
            binocular_id,
        )

    def _find_filter(self, filter_id: str) -> OpticalFilter | None:
        return profile_equipment_service.find_by_id(self._filters, filter_id)

    def _find_reducer(self, reducer_id: str) -> FocalReducer | None:
        return profile_equipment_service.find_by_id(self._reducers, reducer_id)

    def _find_astronomy_camera(self, camera_id: str) -> dict | None:
        return profile_equipment_service.find_row_by_catalog_id(
            self._astronomy_camera_catalog,
            camera_id,
        )

    def _find_camera_body(self, camera_id: str) -> dict | None:
        return profile_equipment_service.find_row_by_catalog_id(
            self._camera_body_catalog,
            camera_id,
        )

    def _index_for_telescope(self, telescope_id: str) -> int:
        return profile_equipment_service.index_for_telescope(
            self._telescopes,
            telescope_id,
        )

    def _normalize_telescope_catalog_id(self, telescope_id: str) -> str:
        return self._equipment_catalog_manager().normalize_telescope_catalog_id(
            telescope_id
        )

    def _equipment_catalog_items(self) -> list[dict]:
        return self._equipment_presenter().catalog_items(
            telescopes=self._catalog_telescopes(),
            eyepieces=self._eyepieces,
            barlows=self._barlows,
            binoculars=self._binoculars,
            filter_rows=self._catalog_filters,
            reducer_rows=self._catalog_reducers,
            astronomy_camera_rows=self._astronomy_camera_catalog,
            camera_body_rows=self._camera_body_catalog,
        )
    def _profile_assigned_equipment(self) -> list[dict]:
        return self._equipment_presenter().assigned_items(
            state=self._active_profile_state(),
            telescopes=self._telescopes,
            eyepieces=self._eyepieces,
            barlows=self._barlows,
            binoculars=self._binoculars,
            filter_rows=self._catalog_filters,
            reducer_rows=self._catalog_reducers,
            astronomy_camera_rows=self._astronomy_camera_catalog,
            camera_body_rows=self._camera_body_catalog,
        )
    @staticmethod
    def _reducer_use_label(reducer: Mapping[str, object]) -> str:
        return equipment_presentation.reducer_use_label(reducer)

    def _telescope_exists(self, telescope: Telescope, ignore_id: str = "") -> bool:
        return profile_equipment_service.telescope_exists(
            self._telescopes,
            telescope,
            self._equipment_service.NAKED_EYE_ID,
            ignore_id,
        )

    def _eyepiece_exists(self, eyepiece: Eyepiece, ignore_id: str = "") -> bool:
        return profile_equipment_service.eyepiece_exists(
            self._eyepieces,
            eyepiece,
            ignore_id,
        )

    def _barlow_exists(self, barlow: Barlow, ignore_id: str = "") -> bool:
        return profile_equipment_service.barlow_exists(
            self._barlows,
            barlow,
            ignore_id,
        )

    @staticmethod
    def _next_custom_id(prefix: str, existing_ids: list[str]) -> str:
        return profile_equipment_service.next_custom_id(prefix, existing_ids)

    def _equipment_status_message(self) -> str:
        return self._equipment_presenter().status_message(
            telescope=self._current_telescope(),
            binoculars=self._active_profile_binoculars(),
            eyepieces=self._active_profile_eyepieces(),
            barlows=self._active_profile_barlows(),
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
