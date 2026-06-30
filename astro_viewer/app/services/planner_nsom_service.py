from __future__ import annotations

import math

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    ObservableTargetValue,
    ObservationEnvironment,
    ObservationOpportunity,
    PracticalTargetValue,
    RecommendationConfidence,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_effective_observability_from_breakdown,
    build_intrinsic_target_quality,
    build_observation_environment,
    build_observation_opportunity,
    build_observer_capability_profile_from_recommendation,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.planner_scoring_service import PlannerScoringService


class PlannerNsomScoringService:
    """Experimental Planner adapter that ranks first-class NSOM opportunities."""

    def __init__(self, planner_scoring_service: PlannerScoringService | None = None) -> None:
        self._planner_scoring_service = planner_scoring_service or PlannerScoringService()

    def opportunity(
        self,
        item: CelestialObject,
        *,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
        blocking_status: WeatherBlockingStatus | None = None,
        observing_window_quality: float = 1.0,
        chronology_fit: float = 1.0,
        practical_constraints: float | None = None,
    ) -> ObservationOpportunity:
        practical = self.practical_target_value(
            item,
            scores=scores,
            sky_quality=sky_quality,
            telescope=telescope,
            moon=moon,
        )
        return self.opportunity_from_practical_target_value(
            item,
            practical,
            weather=weather,
            sky_quality=sky_quality,
            moon=moon,
            blocking_status=blocking_status,
            observing_window_quality=observing_window_quality,
            chronology_fit=chronology_fit,
            practical_constraints=practical_constraints,
        )

    def practical_target_value(
        self,
        item: CelestialObject,
        *,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
    ) -> PracticalTargetValue:
        del telescope
        effective = self.effective_observability(item, scores=scores, sky_quality=sky_quality, moon=moon)
        intrinsic = build_intrinsic_target_quality(item)
        observable = ObservableTargetValue.from_intrinsic(
            intrinsic_target_quality=intrinsic,
            effective_observability=effective,
            target_class=intrinsic.target_class,
        )
        observer_capability = build_observer_capability_profile_from_recommendation(item)
        return build_practical_target_value(observable, observer_capability)

    def effective_observability(
        self,
        item: CelestialObject,
        *,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        moon: MoonSummary | None = None,
    ) -> EffectiveObservability:
        condition_breakdown = self._planner_scoring_service.condition_breakdown(item, sky_quality, moon)
        condition_effective = build_effective_observability_from_breakdown(condition_breakdown)
        runtime_environment = build_observation_environment(sky_quality=sky_quality)
        category_factor = self._category_factor(item, scores)
        environment = ObservationEnvironment.from_components(
            geometric_visibility=condition_effective.geometric_visibility,
            lunar_sky_background=condition_effective.lunar_sky_background,
            static_sky_background=condition_effective.static_sky_background,
            atmospheric_transparency=condition_effective.atmospheric_transparency * category_factor,
            horizon_context=condition_effective.horizon_context,
            sky_quality_source=runtime_environment.sky_quality_source,
            weather_source=runtime_environment.weather_source,
            atmosphere_source=runtime_environment.atmosphere_source,
            notes=(
                "nsom:planner_experimental",
                *runtime_environment.notes,
                *condition_effective.notes,
                f"advanced_score_factor={category_factor:.3f}",
            ),
        )
        return EffectiveObservability.from_environment(environment)

    def opportunity_from_practical_target_value(
        self,
        item: CelestialObject,
        practical_target_value: PracticalTargetValue,
        *,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        moon: MoonSummary | None = None,
        blocking_status: WeatherBlockingStatus | None = None,
        observing_window_quality: float = 1.0,
        chronology_fit: float = 1.0,
        practical_constraints: float | None = None,
        confidence: RecommendationConfidence | None = None,
    ) -> ObservationOpportunity:
        session = build_session_viability(weather_summary=weather, blocking_status=blocking_status)
        recommendation_confidence = confidence or self.recommendation_confidence(
            weather=weather,
            sky_quality=sky_quality,
            moon=moon,
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
            context=("planner", "nsom_experimental"),
        )

    @staticmethod
    def score(opportunity: ObservationOpportunity) -> float:
        return opportunity.value

    @staticmethod
    def recommendation_confidence(
        *,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
    ) -> RecommendationConfidence:
        return build_recommendation_confidence(
            weather_summary=weather,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon is not None,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:planner_experimental",),
        )

    @staticmethod
    def _category_factor(item: CelestialObject, scores: AdvancedObservingScores) -> float:
        score = scores.planetary_score if item.object_type == "Pianeta" else scores.deep_sky_score
        return _unit_from_score(score)

    @staticmethod
    def _planner_practical_constraints(item: CelestialObject) -> float:
        return min(1.0, PlannerScoringService.difficulty_factor(item))


def _unit_from_score(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return max(0.0, min(1.0, number / 100.0))
