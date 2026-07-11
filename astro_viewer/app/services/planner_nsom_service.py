from __future__ import annotations

import math
from dataclasses import replace

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    ObservableTargetValue,
    ObservationOpportunity,
    ObserverCapability,
    PracticalTargetValue,
    RecommendationConfidence,
    nsom_to_json_compatible,
    observer_capability_weight_profile_for_target,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionFeatureFlags,
    ObservationConditionInputs,
)
from astro_viewer.app.services.nsom_observation_environment import (
    NsomObservationEnvironmentService,
)
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_intrinsic_target_quality,
    build_observation_opportunity,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.observer_capability_adapter import build_observer_capability_for_target


NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED = True


class PlannerNsomScoringService:
    """Experimental Planner adapter that ranks first-class NSOM opportunities."""

    def __init__(
        self,
        *,
        feature_flags: ObservationConditionFeatureFlags | None = None,
    ) -> None:
        self._feature_flags = feature_flags or ObservationConditionFeatureFlags(
            experimental_moon_geometry_scoring=NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED
        )

    @property
    def uses_moon_geometry_scoring(self) -> bool:
        return self._feature_flags.experimental_moon_geometry_scoring

    def opportunity(
        self,
        item: CelestialObject,
        *,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
        moon_geometry: MoonGeometryConditionInput | None = None,
        blocking_status: WeatherBlockingStatus | None = None,
        observing_window_quality: float = 1.0,
        chronology_fit: float = 1.0,
        practical_constraints: float | None = None,
        condition_inputs: ObservationConditionInputs | None = None,
    ) -> ObservationOpportunity:
        practical = self.practical_target_value(
            item,
            scores=scores,
            sky_quality=sky_quality,
            telescope=telescope,
            moon=moon,
            moon_geometry=moon_geometry,
            condition_inputs=condition_inputs,
        )
        return self.opportunity_from_practical_target_value(
            item,
            practical,
            weather=weather,
            sky_quality=sky_quality,
            moon=moon,
            moon_geometry_available=True if moon_geometry is not None else None,
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
        moon_geometry: MoonGeometryConditionInput | None = None,
        condition_inputs: ObservationConditionInputs | None = None,
    ) -> PracticalTargetValue:
        effective = self.effective_observability(
            item,
            scores=scores,
            sky_quality=sky_quality,
            moon=moon,
            moon_geometry=moon_geometry,
            condition_inputs=condition_inputs,
        )
        intrinsic = build_intrinsic_target_quality(item)
        observable = ObservableTargetValue.from_intrinsic(
            intrinsic_target_quality=intrinsic,
            effective_observability=effective,
            target_class=intrinsic.target_class,
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
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        moon: MoonSummary | None = None,
        moon_geometry: MoonGeometryConditionInput | None = None,
        condition_inputs: ObservationConditionInputs | None = None,
    ) -> EffectiveObservability:
        inputs = condition_inputs or self._compatibility_condition_inputs(
            item,
            scores=scores,
            sky_quality=sky_quality,
            moon=moon,
        )
        inputs = replace(
            inputs,
            moon_geometry=moon_geometry,
            feature_flags=self._feature_flags,
        )
        return NsomObservationEnvironmentService().effective_observability(item, inputs)

    @staticmethod
    def _compatibility_condition_inputs(
        item: CelestialObject,
        *,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
    ) -> ObservationConditionInputs:
        category_score = (
            scores.planetary_score
            if item.object_type == "Pianeta"
            else scores.deep_sky_score
        )
        seeing = SeeingTransparency(
            seeing="Compatibility",
            transparency="Compatibility",
            seeing_score=category_score,
            transparency_score=category_score,
            explanation="Planner compatibility input.",
            source="AdvancedObservingScoresCompatibility",
            confidence="low",
            atmospheric_transparency_score=category_score,
        )
        return ObservationConditionInputs(
            moon=moon,
            sky_quality=sky_quality,
            seeing=seeing,
        )

    def opportunity_from_practical_target_value(
        self,
        item: CelestialObject,
        practical_target_value: PracticalTargetValue,
        *,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        moon: MoonSummary | None = None,
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
            sky_quality=sky_quality,
            moon=moon,
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
            context=("planner", "nsom_experimental"),
        )

    @staticmethod
    def score(opportunity: ObservationOpportunity) -> float:
        return opportunity.value

    @staticmethod
    def explain_opportunity(
        item: CelestialObject,
        opportunity: ObservationOpportunity,
    ) -> dict[str, object]:
        """Return a developer-only JSON-compatible explanation for a NSOM score."""

        practical = opportunity.practical_target_value
        observable = practical.observable_target_value
        effective = observable.effective_observability
        observer = practical.observer_capability
        target_class = observable.target_class.value if observable.target_class else None
        flat_observer_summary = observer.summary_for_planning()
        q_target = practical.observer_capability_summary
        target_weighting = observer_capability_weight_profile_for_target(observable.target_class)
        explanation = {
            "target": {
                "object_id": item.id,
                "name": item.name,
                "object_type": item.object_type,
                "target_class": target_class,
            },
            "final_nsom_opportunity_score": opportunity.value,
            "score_components": {
                "practical_target_value": practical.value,
                "observable_target_value": observable.value,
                "effective_observability": effective.value,
                "observer_capability_summary": q_target,
                "q_target": q_target,
                "flat_observer_capability_summary": flat_observer_summary,
                "q_target_delta_vs_flat": q_target - flat_observer_summary,
                "session_viability": opportunity.session.value,
                "observing_window_quality": opportunity.observing_window_quality,
                "chronology_fit": opportunity.chronology_fit,
                "practical_constraints": opportunity.practical_constraints,
            },
            "nsom_components": {
                "practical_target_value": practical,
                "observable_target_value": observable,
                "effective_observability": effective,
                "observer_capability_summary": practical.observer_capability_summary,
                "observer_capability": {
                    **nsom_to_json_compatible(observer),
                    "summary_for_planning": flat_observer_summary,
                    "q_target": q_target,
                    "q_target_delta_vs_flat": q_target - flat_observer_summary,
                    "target_class_weighting_profile": target_weighting,
                },
                "session_viability": opportunity.session,
                "recommendation_confidence": _confidence_explanation(opportunity.confidence),
            },
            "main_limiting_factors": _main_limiting_factors(opportunity),
            "main_positive_factors": _main_positive_factors(opportunity),
            "confidence_explanation": _confidence_explanation(opportunity.confidence),
        }
        return nsom_to_json_compatible(explanation)

    @staticmethod
    def recommendation_confidence(
        *,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
        moon_geometry_available: bool | None = None,
    ) -> RecommendationConfidence:
        return build_recommendation_confidence(
            weather_summary=weather,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon_geometry_available,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:planner_experimental",),
        )

    @staticmethod
    def _planner_practical_constraints(item: CelestialObject) -> float:
        return min(1.0, _difficulty_factor(item))


def _main_limiting_factors(opportunity: ObservationOpportunity) -> tuple[dict[str, object], ...]:
    practical = opportunity.practical_target_value
    effective = practical.observable_target_value.effective_observability
    session = opportunity.session
    factors: list[dict[str, object]] = []

    _append_factor_if_below(
        factors,
        owner="sky",
        component="EffectiveObservability",
        factor="geometric_visibility",
        value=effective.geometric_visibility,
        reason="Target geometry limits observable target value.",
    )
    _append_factor_if_below(
        factors,
        owner="sky",
        component="EffectiveObservability",
        factor="moon_background",
        value=effective.lunar_sky_background,
        reason="Moon sky background reduces effective observability for this target class.",
    )
    _append_factor_if_below(
        factors,
        owner="sky",
        component="EffectiveObservability",
        factor="sky_background",
        value=effective.static_sky_background,
        reason="Light-pollution sky background reduces effective observability for this target class.",
    )
    _append_factor_if_below(
        factors,
        owner="sky",
        component="EffectiveObservability",
        factor="atmospheric_transparency",
        value=effective.atmospheric_transparency,
        reason="Planner observing conditions reduce effective observability.",
    )
    _append_factor_if_below(
        factors,
        owner="sky",
        component="EffectiveObservability",
        factor="horizon_context",
        value=effective.horizon_context,
        reason="Low altitude or horizon context reduces effective observability.",
    )
    _append_factor_if_below(
        factors,
        owner="observer",
        component="PracticalTargetValue",
        factor="q_target",
        value=practical.observer_capability_summary,
        reason="Target-specific observer capability projection reduces practical target value.",
    )
    _append_factor_if_below(
        factors,
        owner="session",
        component="SessionViability",
        factor="weather_suitability",
        value=session.weather_suitability,
        reason="Weather/session suitability reduces session viability.",
    )
    _append_factor_if_below(
        factors,
        owner="session",
        component="SessionViability",
        factor="blocking_factor",
        value=session.blocking_factor,
        reason="A session blocker reduces session viability.",
    )
    _append_factor_if_below(
        factors,
        owner="session",
        component="SessionViability",
        factor="session_viability",
        value=session.value,
        reason="Session viability reduces the opportunity score.",
    )
    _append_factor_if_below(
        factors,
        owner="opportunity",
        component="ObservationOpportunity",
        factor="observing_window_quality",
        value=opportunity.observing_window_quality,
        reason="The observing window reduces opportunity timing quality.",
    )
    _append_factor_if_below(
        factors,
        owner="opportunity",
        component="ObservationOpportunity",
        factor="chronology_fit",
        value=opportunity.chronology_fit,
        reason="Planner chronology reduces opportunity fit.",
    )
    _append_factor_if_below(
        factors,
        owner="opportunity",
        component="ObservationOpportunity",
        factor="practical_constraints",
        value=opportunity.practical_constraints,
        reason="Planner practical constraints reduce opportunity value.",
    )

    return tuple(sorted(factors, key=lambda factor: float(factor["value"])))


def _main_positive_factors(opportunity: ObservationOpportunity) -> tuple[dict[str, object], ...]:
    practical = opportunity.practical_target_value
    effective = practical.observable_target_value.effective_observability
    session = opportunity.session
    factors: list[dict[str, object]] = []

    _append_factor_if_at_least(
        factors,
        owner="sky",
        component="EffectiveObservability",
        factor="moon_background_neutral",
        value=effective.lunar_sky_background,
        reason="Moon sky background is neutral for this target class or condition.",
    )
    _append_factor_if_at_least(
        factors,
        owner="sky",
        component="EffectiveObservability",
        factor="sky_background_neutral",
        value=effective.static_sky_background,
        reason="Light-pollution sky background is neutral for this target class or condition.",
    )
    _append_factor_if_at_least(
        factors,
        owner="observer",
        component="PracticalTargetValue",
        factor="q_target",
        value=practical.observer_capability_summary,
        reason="Target-specific observer capability projection supports practical target value.",
        threshold=0.65,
    )
    _append_factor_if_at_least(
        factors,
        owner="session",
        component="SessionViability",
        factor="session_viability",
        value=session.value,
        reason="Session viability supports the opportunity score.",
        threshold=0.95,
    )
    _append_factor_if_at_least(
        factors,
        owner="opportunity",
        component="ObservationOpportunity",
        factor="observing_window_quality",
        value=opportunity.observing_window_quality,
        reason="The target has a strong observing window.",
        threshold=0.95,
    )

    return tuple(factors)


def _append_factor_if_below(
    factors: list[dict[str, object]],
    *,
    owner: str,
    component: str,
    factor: str,
    value: object,
    reason: str,
    threshold: float = 0.995,
) -> None:
    factor_value = _clamp_unit(value)
    if factor_value >= threshold:
        return
    factors.append(_explanation_factor(owner, component, factor, factor_value, reason))


def _append_factor_if_at_least(
    factors: list[dict[str, object]],
    *,
    owner: str,
    component: str,
    factor: str,
    value: object,
    reason: str,
    threshold: float = 0.995,
) -> None:
    factor_value = _clamp_unit(value)
    if factor_value < threshold:
        return
    factors.append(_explanation_factor(owner, component, factor, factor_value, reason))


def _explanation_factor(
    owner: str,
    component: str,
    factor: str,
    value: float,
    reason: str,
) -> dict[str, object]:
    return {
        "owner": owner,
        "component": component,
        "factor": factor,
        "value": value,
        "reason": reason,
    }


def _confidence_explanation(confidence: RecommendationConfidence | None) -> object:
    if confidence is None:
        return None
    return {
        **nsom_to_json_compatible(confidence),
        "value": confidence.value,
        "role": "metadata_only",
        "score_effect": 0.0,
        "score_factor": False,
        "explanation": "RecommendationConfidence describes data trust and is not a score multiplier.",
    }


def _finite_float(value: object, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _clamp_unit(value: object) -> float:
    return max(0.0, min(1.0, _finite_float(value, default=0.0)))


def _difficulty_factor(item: CelestialObject) -> float:
    return {"Facile": 1.08, "Media": 0.95, "Difficile": 0.75}.get(item.difficulty, 0.85)
