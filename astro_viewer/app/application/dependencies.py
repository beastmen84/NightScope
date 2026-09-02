"""Assemble the concrete dependency graph injected into the Qt controller."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.application.catalogue_recommendations import (
    CatalogueRecommendationWorkflow,
)
from astro_viewer.app.astronomy.engine import (
    AstronomyEngine,
    MockAstronomyEngine,
    TransientCalendarEventSource,
)
from astro_viewer.app.astronomy.skyfield_engine import (
    EphemerisUnavailableError,
    SkyfieldAstronomyEngine,
)
from astro_viewer.app.database.catalogue_repository import CatalogueRepository
from astro_viewer.app.database.city_repository import CityRepository
from astro_viewer.app.database.equipment_catalog_repository import (
    EquipmentCatalogRepository,
)
from astro_viewer.app.database.location_repository import LocationRepository
from astro_viewer.app.database.object_image_repository import ObjectImageRepository
from astro_viewer.app.database.observation_repository import ObservationRepository
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.database.weather_cache_repository import WeatherCacheRepository
from astro_viewer.app.services.best_object_nsom_ranking import (
    BestObjectNsomSelectionService,
)
from astro_viewer.app.services.calendar_overview import CalendarOverviewService
from astro_viewer.app.services.catalogue_detail_service import CatalogueDetailService
from astro_viewer.app.services.catalogue_query_service import CatalogueQueryService
from astro_viewer.app.services.earthdata_credentials import (
    EarthdataConnectionTester,
    EarthdataCredentialStore,
)
from astro_viewer.app.services.equipment_catalog_service import (
    EquipmentCatalogService,
)
from astro_viewer.app.services.equipment_presentation import (
    EquipmentPresentationService,
)
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.equipment_setup_read_model import (
    EquipmentSetupReadModelBuilder,
)
from astro_viewer.app.services.filter_recommendation_service import (
    FilterRecommendationService,
)
from astro_viewer.app.services.home_night_plan_overview import (
    HomeNightPlanOverviewService,
)
from astro_viewer.app.services.home_nsom_ranking import (
    HomeRecommendedDeepSkyNsomRankingService,
)
from astro_viewer.app.services.home_observing_overview import (
    HomeObservingOverviewService,
)
from astro_viewer.app.services.imaging_recommendation_presentation import (
    ImagingRecommendationPresenter,
)
from astro_viewer.app.services.imaging_runtime_assembler import (
    ImagingRuntimeAssembler,
)
from astro_viewer.app.services.light_pollution_service import LightPollutionService
from astro_viewer.app.services.localization import tr
from astro_viewer.app.services.location_preferences import LocationPreferenceStore
from astro_viewer.app.services.location_service import LocationService
from astro_viewer.app.services.nasa_aod_provider import NasaAodProvider
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_category_score_service import (
    NsomCategoryScoreService,
)
from astro_viewer.app.services.observation_conditions_read_model import (
    ObservationConditionsReadModelBuilder,
)
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionsService,
)
from astro_viewer.app.services.observation_log_service import ObservationLogService
from astro_viewer.app.services.observing_object_detail import (
    ObservingObjectDetailService,
)
from astro_viewer.app.services.observing_presentation import (
    ObservingPresentationService,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.services.openaq_atmosphere_service import (
    OpenAQLocalAtmosphereService,
)
from astro_viewer.app.services.openaq_credentials import (
    OpenAQConnectionTester,
    OpenAQCredentialStore,
)
from astro_viewer.app.services.profile_equipment_service import (
    ProfileEquipmentService,
)
from astro_viewer.app.services.reducer_recommendation_service import (
    ReducerRecommendationService,
)
from astro_viewer.app.services.refresh_lifecycle import RefreshManager
from astro_viewer.app.services.seeing_service import SeeingTransparencyService
from astro_viewer.app.services.sky_compass_service import SkyCompassService
from astro_viewer.app.services.weather_service import OpenMeteoWeatherService
from astro_viewer.app.services.weather_presentation import WeatherPresentationService


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppControllerDependencies:
    """Concrete collaborators consumed by the Qt-facing application controller."""

    city_repository: CityRepository
    location_repository: LocationRepository
    catalogue_repository: CatalogueRepository
    equipment_catalog_repository: EquipmentCatalogRepository
    sky_quality_repository: SkyQualityRepository
    object_image_repository: ObjectImageRepository
    weather_cache_repository: WeatherCacheRepository
    observation_repository: ObservationRepository
    location_preferences: LocationPreferenceStore
    earthdata_credential_store: EarthdataCredentialStore
    earthdata_connection_tester: EarthdataConnectionTester
    openaq_credential_store: OpenAQCredentialStore
    openaq_connection_tester: OpenAQConnectionTester
    local_atmosphere_service: OpenAQLocalAtmosphereService
    location_service: LocationService
    astronomy_engine: AstronomyEngine
    startup_service_status: object
    weather_service: OpenMeteoWeatherService
    equipment_service: EquipmentService
    equipment_catalog_service: EquipmentCatalogService
    profile_equipment_service: ProfileEquipmentService
    equipment_presentation_service: EquipmentPresentationService
    equipment_setup_read_model_builder: EquipmentSetupReadModelBuilder
    filter_recommendation_service: FilterRecommendationService
    reducer_recommendation_service: ReducerRecommendationService
    score_service: ObservingScoreService
    light_pollution_service: LightPollutionService
    nasa_aod_provider: NasaAodProvider
    seeing_service: SeeingTransparencyService
    nsom_category_score_service: NsomCategoryScoreService
    conditions_service: ObservationConditionsService
    conditions_read_model_builder: ObservationConditionsReadModelBuilder
    observation_log_service: ObservationLogService
    best_object_nsom_selection_service: BestObjectNsomSelectionService
    home_recommended_deep_sky_nsom_ranking_service: (
        HomeRecommendedDeepSkyNsomRankingService
    )
    home_observing_overview_service: HomeObservingOverviewService
    home_night_plan_overview_service: HomeNightPlanOverviewService
    calendar_overview_service: CalendarOverviewService
    night_planner_service: NightPlannerService
    sky_compass_service: SkyCompassService
    observing_object_detail_service: ObservingObjectDetailService
    imaging_runtime_assembler: ImagingRuntimeAssembler
    imaging_recommendation_presenter: ImagingRecommendationPresenter
    refresh_manager: RefreshManager
    catalogue_recommendation_workflow: CatalogueRecommendationWorkflow
    observing_presentation_service: ObservingPresentationService
    weather_presentation_service: WeatherPresentationService
    catalogue_query_service: CatalogueQueryService
    catalogue_detail_service: CatalogueDetailService


def build_app_controller_dependencies(
    *,
    base_dir: Path,
    database_path: Path,
    preferences_path: Path | None = None,
    location_cache_path: Path | None = None,
    nasa_aod_cache_path: Path | None = None,
    best_object_nsom_selection_service: BestObjectNsomSelectionService | None = None,
    home_recommended_deep_sky_nsom_ranking_service: (
        HomeRecommendedDeepSkyNsomRankingService | None
    ) = None,
    nsom_category_score_service: NsomCategoryScoreService | None = None,
    sky_compass_service: SkyCompassService | None = None,
    transient_event_sources: Sequence[TransientCalendarEventSource] = (),
) -> AppControllerDependencies:
    """Build the application graph without coupling it to the Qt controller."""

    resolved_preferences_path = (
        preferences_path or database_path.parent / "user_preferences.json"
    )
    resolved_location_cache_path = (
        location_cache_path or database_path.parent / "location_cache.json"
    )
    resolved_nasa_aod_cache_path = (
        nasa_aod_cache_path or database_path.parent / "nasa_aod_cache.json"
    )

    city_repository = CityRepository(database_path)
    location_repository = LocationRepository(database_path)
    catalogue_repository = CatalogueRepository(database_path)
    equipment_catalog_repository = EquipmentCatalogRepository(database_path)
    sky_quality_repository = SkyQualityRepository(database_path)
    object_image_repository = ObjectImageRepository(database_path)
    weather_cache_repository = WeatherCacheRepository(database_path)
    observation_repository = ObservationRepository(database_path)

    location_preferences = LocationPreferenceStore(
        preferences_path=resolved_preferences_path,
        cache_path=resolved_location_cache_path,
    )
    earthdata_credential_store = EarthdataCredentialStore(
        preferences_path=resolved_preferences_path,
    )
    openaq_credential_store = OpenAQCredentialStore(
        preferences_path=resolved_preferences_path,
    )
    location_service = LocationService(
        city_resolver=city_repository,
        cache_path=resolved_location_cache_path,
    )

    startup_service_status: object = ""
    try:
        astronomy_engine: AstronomyEngine = SkyfieldAstronomyEngine(
            base_dir / "data",
            catalogue_repository,
            transient_event_sources,
        )
    except EphemerisUnavailableError:
        logger.error(
            "Skyfield engine unavailable; using fallback astronomy data.",
            exc_info=True,
        )
        astronomy_engine = MockAstronomyEngine()
        startup_service_status = tr(
            "Effemeridi astronomiche non disponibili. Uso i dati cielo di fallback."
        )

    equipment_service = EquipmentService()
    equipment_catalog_service = EquipmentCatalogService(
        equipment_catalog_repository,
        equipment_service,
    )
    profile_equipment_service = ProfileEquipmentService(
        equipment_catalog_repository,
        equipment_service,
        equipment_catalog_service,
    )
    equipment_presentation_service = EquipmentPresentationService(
        equipment_service
    )
    equipment_setup_read_model_builder = EquipmentSetupReadModelBuilder()
    conditions_service = ObservationConditionsService()
    conditions_read_model_builder = ObservationConditionsReadModelBuilder()
    resolved_category_score_service = (
        nsom_category_score_service or NsomCategoryScoreService()
    )
    resolved_best_object_service = (
        best_object_nsom_selection_service or BestObjectNsomSelectionService()
    )
    resolved_home_ranking_service = (
        home_recommended_deep_sky_nsom_ranking_service
        or HomeRecommendedDeepSkyNsomRankingService()
    )
    night_planner_service = NightPlannerService()
    observing_presentation_service = ObservingPresentationService()
    weather_presentation_service = WeatherPresentationService(
        night_planner_service
    )
    resolved_sky_compass_service = sky_compass_service or SkyCompassService()
    catalogue_recommendation_workflow = CatalogueRecommendationWorkflow(
        equipment_service=equipment_service,
        equipment_setup_read_model_builder=equipment_setup_read_model_builder,
        conditions_service=conditions_service,
        conditions_read_model_builder=conditions_read_model_builder,
        home_ranking_service=resolved_home_ranking_service,
        category_score_service=resolved_category_score_service,
        best_object_service=resolved_best_object_service,
        night_planner_service=night_planner_service,
        sky_compass_service=resolved_sky_compass_service,
    )
    catalogue_query_service = CatalogueQueryService(catalogue_repository)
    catalogue_detail_service = CatalogueDetailService()
    return AppControllerDependencies(
        city_repository=city_repository,
        location_repository=location_repository,
        catalogue_repository=catalogue_repository,
        equipment_catalog_repository=equipment_catalog_repository,
        sky_quality_repository=sky_quality_repository,
        object_image_repository=object_image_repository,
        weather_cache_repository=weather_cache_repository,
        observation_repository=observation_repository,
        location_preferences=location_preferences,
        earthdata_credential_store=earthdata_credential_store,
        earthdata_connection_tester=EarthdataConnectionTester(),
        openaq_credential_store=openaq_credential_store,
        openaq_connection_tester=OpenAQConnectionTester(),
        local_atmosphere_service=OpenAQLocalAtmosphereService(),
        location_service=location_service,
        astronomy_engine=astronomy_engine,
        startup_service_status=startup_service_status,
        weather_service=OpenMeteoWeatherService(weather_cache_repository),
        equipment_service=equipment_service,
        equipment_catalog_service=equipment_catalog_service,
        profile_equipment_service=profile_equipment_service,
        equipment_presentation_service=equipment_presentation_service,
        equipment_setup_read_model_builder=equipment_setup_read_model_builder,
        filter_recommendation_service=FilterRecommendationService(),
        reducer_recommendation_service=ReducerRecommendationService(),
        score_service=ObservingScoreService(),
        light_pollution_service=LightPollutionService(
            sky_quality_repository,
            data_dir=base_dir / "data",
            earthdata_credentials=earthdata_credential_store,
        ),
        nasa_aod_provider=NasaAodProvider(
            earthdata_credential_store,
            cache_path=resolved_nasa_aod_cache_path,
        ),
        seeing_service=SeeingTransparencyService(),
        nsom_category_score_service=resolved_category_score_service,
        conditions_service=conditions_service,
        conditions_read_model_builder=conditions_read_model_builder,
        observation_log_service=ObservationLogService(),
        best_object_nsom_selection_service=resolved_best_object_service,
        home_recommended_deep_sky_nsom_ranking_service=resolved_home_ranking_service,
        home_observing_overview_service=HomeObservingOverviewService(),
        home_night_plan_overview_service=HomeNightPlanOverviewService(),
        calendar_overview_service=CalendarOverviewService(),
        night_planner_service=night_planner_service,
        sky_compass_service=resolved_sky_compass_service,
        observing_object_detail_service=ObservingObjectDetailService(),
        imaging_runtime_assembler=ImagingRuntimeAssembler(),
        imaging_recommendation_presenter=ImagingRecommendationPresenter(),
        refresh_manager=RefreshManager(),
        catalogue_recommendation_workflow=catalogue_recommendation_workflow,
        observing_presentation_service=observing_presentation_service,
        weather_presentation_service=weather_presentation_service,
        catalogue_query_service=catalogue_query_service,
        catalogue_detail_service=catalogue_detail_service,
    )
