from __future__ import annotations

from dataclasses import replace

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    ObservableTargetValue,
    ObservationOpportunity,
    ObserverCapability,
    PracticalTargetValue,
    RecommendationConfidence,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionInputs,
)
from astro_viewer.app.services.nsom_observation_environment import (
    NsomObservationEnvironmentService,
)
from astro_viewer.app.services.nsom_runtime_builders import (
    build_observation_opportunity,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.observer_capability_adapter import build_observer_capability_for_target


class PlannerNsomScoringService:
    """Ranks first-class NSOM Planner opportunities."""

    def opportunity(
        self,
        item: CelestialObject,
        *,
        weather: WeatherSummary,
        telescope: Telescope,
        condition_inputs: ObservationConditionInputs,
        moon_geometry: MoonGeometryConditionInput | None = None,
        blocking_status: WeatherBlockingStatus | None = None,
        observing_window_quality: float = 1.0,
        chronology_fit: float = 1.0,
        practical_constraints: float | None = None,
    ) -> ObservationOpportunity:
        practical = self.practical_target_value(
            item,
            telescope=telescope,
            condition_inputs=condition_inputs,
            moon_geometry=moon_geometry,
        )
        return self.opportunity_from_practical_target_value(
            item,
            practical,
            weather=weather,
            condition_inputs=condition_inputs,
            moon_geometry_available=(
                None if condition_inputs.moon is None else moon_geometry is not None
            ),
            blocking_status=blocking_status,
            observing_window_quality=observing_window_quality,
            chronology_fit=chronology_fit,
            practical_constraints=practical_constraints,
        )

    def practical_target_value(
        self,
        item: CelestialObject,
        *,
        telescope: Telescope,
        condition_inputs: ObservationConditionInputs,
        moon_geometry: MoonGeometryConditionInput | None = None,
    ) -> PracticalTargetValue:
        observable = NsomObservationEnvironmentService().observable_target_value(
            item,
            replace(condition_inputs, moon_geometry=moon_geometry),
        )
        return self.practical_target_value_from_observable(observable, item, telescope=telescope)

    def practical_target_value_from_observable(
        self,
        observable_target_value: ObservableTargetValue,
        item: CelestialObject,
        *,
        telescope: Telescope,
    ) -> PracticalTargetValue:
        observer_capability = self.observer_capability(item, telescope=telescope)
        q_target = project_observer_capability_for_target(
            observer_capability,
            observable_target_value.target_class,
        )
        return build_practical_target_value(
            observable_target_value,
            observer_capability,
            capability_summary=q_target,
        )

    @staticmethod
    def observer_capability(item: CelestialObject, *, telescope: Telescope) -> ObserverCapability:
        return build_observer_capability_for_target(
            item,
            telescope=telescope,
            context_note="nsom:planner_observer_capability",
        )

    def effective_observability(
        self,
        item: CelestialObject,
        *,
        condition_inputs: ObservationConditionInputs,
        moon_geometry: MoonGeometryConditionInput | None = None,
    ) -> EffectiveObservability:
        inputs = replace(
            condition_inputs,
            moon_geometry=moon_geometry,
        )
        return NsomObservationEnvironmentService().effective_observability(item, inputs)

    def opportunity_from_practical_target_value(
        self,
        item: CelestialObject,
        practical_target_value: PracticalTargetValue,
        *,
        weather: WeatherSummary,
        condition_inputs: ObservationConditionInputs,
        moon_geometry_available: bool | None = None,
        blocking_status: WeatherBlockingStatus | None = None,
        observing_window_quality: float = 1.0,
        chronology_fit: float = 1.0,
        practical_constraints: float | None = None,
        confidence: RecommendationConfidence | None = None,
    ) -> ObservationOpportunity:
        session = build_session_viability(weather_summary=weather, blocking_status=blocking_status)
        recommendation_confidence = confidence or self.recommendation_confidence(
            weather=weather,
            condition_inputs=condition_inputs,
            moon_geometry_available=moon_geometry_available,
        )
        constraints = (
            self._planner_practical_constraints(item)
            if practical_constraints is None
            else practical_constraints
        )
        return build_observation_opportunity(
            practical_target_value,
            observing_window_quality=observing_window_quality,
            chronology_fit=chronology_fit,
            session=session,
            practical_constraints=constraints,
            confidence=recommendation_confidence,
            context=("planner", "nsom_runtime"),
        )

    @staticmethod
    def score(opportunity: ObservationOpportunity) -> float:
        return opportunity.value

    @staticmethod
    def recommendation_confidence(
        *,
        weather: WeatherSummary,
        condition_inputs: ObservationConditionInputs,
        moon_geometry_available: bool | None = None,
    ) -> RecommendationConfidence:
        return build_recommendation_confidence(
            weather_summary=weather,
            aod_result=condition_inputs.aod,
            local_atmosphere=condition_inputs.particulate,
            viirs_available=(
                getattr(condition_inputs.sky_quality, "viirs_radiance", None) is not None
            ),
            moon_geometry_available=moon_geometry_available,
            notes=("nsom:planner_runtime",),
        )

    @staticmethod
    def _planner_practical_constraints(item: CelestialObject) -> float:
        return min(1.0, _difficulty_factor(item))


def _difficulty_factor(item: CelestialObject) -> float:
    return {"Facile": 1.08, "Media": 0.95, "Difficile": 0.75}.get(item.difficulty, 0.85)
