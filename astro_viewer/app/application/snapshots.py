"""Define immutable snapshots exchanged across worker and Qt boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.condition_inputs import (
    MoonGeometryConditionInput,
    ObservationConditionInputs,
)
from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observing import (
    AstronomicalEvent,
    CelestialObject,
    MoonGeometrySummary,
    MoonSummary,
)
from astro_viewer.app.models.sky import (
    NightPlanItem,
    ObservingCategoryScores,
    SeeingTransparency,
    SkyQuality,
)
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.equipment_setup_read_model import (
    EquipmentSetupReadModel,
)
from astro_viewer.app.services.observation_conditions_read_model import (
    ObservationConditionedTargetReadModel,
)


@dataclass(frozen=True)
class AstronomyRefreshSnapshot:
    observing_night_window: ObservingNightWindow | None = None
    solar_system_objects: tuple[CelestialObject, ...] = ()
    deep_sky: tuple[CelestialObject, ...] = ()
    moon: MoonSummary | None = None
    events: tuple[AstronomicalEvent, ...] = ()
    moon_geometry: tuple[tuple[str, MoonGeometrySummary | None], ...] = ()
    catalogue_visibility_cache_key: (
        tuple[float, float, str, int, int, float] | None
    ) = None
    catalogue_visibility: tuple[tuple[str, bool], ...] = ()
    failed: bool = False


@dataclass(frozen=True)
class TransientEventRefreshSnapshot:
    events: tuple[AstronomicalEvent, ...] = ()
    failed: bool = False


@dataclass(frozen=True)
class CatalogueRecommendationPreparationContext:
    runtime_signature: tuple[object, ...]
    telescopes: tuple[Telescope, ...]
    eyepieces: tuple[Eyepiece, ...]
    barlows: tuple[Barlow, ...]
    binoculars: tuple[Binocular, ...]
    seeing_transparency: SeeingTransparency | None
    sky_quality: SkyQuality | None
    object_image_map: dict[str, dict]
    object_descriptions: dict[str, dict]
    catalogue_identifier_index: dict[str, dict]
    visible_planets: tuple[CelestialObject, ...]
    solar_setup_models: tuple[tuple[str, EquipmentSetupReadModel], ...]
    moon_geometry_by_object_id: tuple[
        tuple[str, MoonGeometryConditionInput | None],
        ...,
    ]
    condition_inputs: ObservationConditionInputs
    pollution_condition_inputs: ObservationConditionInputs
    weather_summary: WeatherSummary | None
    current_telescope: Telescope
    observing_night_window: ObservingNightWindow
    telescopes_by_id: tuple[tuple[str, Telescope], ...]
    use_target_equipment: bool
    sky_compass_caution_text: str


@dataclass(frozen=True)
class PreparedCatalogueRecommendationSnapshot:
    runtime_signature: tuple[object, ...] = ()
    astronomy: AstronomyRefreshSnapshot = AstronomyRefreshSnapshot()
    deep_sky: tuple[CelestialObject, ...] = ()
    equipment_setup_models: tuple[
        tuple[str, EquipmentSetupReadModel],
        ...,
    ] = ()
    deep_sky_pollution_read_model: tuple[
        ObservationConditionedTargetReadModel,
        ...,
    ] = ()
    deep_sky_raw_condition_inputs: tuple[
        tuple[str, CelestialObject],
        ...,
    ] = ()
    conditioned_deep_sky: tuple[CelestialObject, ...] = ()
    conditioned_home_objects: tuple[CelestialObject, ...] = ()
    conditioned_deep_sky_read_model: tuple[
        ObservationConditionedTargetReadModel,
        ...,
    ] = ()
    conditioned_home_read_model: tuple[
        ObservationConditionedTargetReadModel,
        ...,
    ] = ()
    category_scores: ObservingCategoryScores | None = None
    best_object: CelestialObject | None = None
    night_plan: tuple[NightPlanItem, ...] = ()
    sky_compass: dict | None = None
    sky_compass_candidates: tuple[CelestialObject, ...] = ()
    failed: bool = False
