from __future__ import annotations

import math
import re

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    NSOM_TARGET_CLASS_PROFILES,
    NsomTargetClass,
    ObservableTargetValue,
    ObservationEnvironment,
    ObservationOpportunity,
    ObserverCapability,
    PracticalTargetValue,
    RecommendationConfidence,
    nsom_to_json_compatible,
    observer_capability_weight_profile_for_target,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_intrinsic_target_quality,
    build_observation_environment,
    build_observation_opportunity,
    build_observer_capability_profile_from_recommendation,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
    target_class_from_runtime_target,
)


class PlannerNsomScoringService:
    """Experimental Planner adapter that ranks first-class NSOM opportunities."""

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
        effective = self.effective_observability(item, scores=scores, sky_quality=sky_quality, moon=moon)
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
        base = build_observer_capability_profile_from_recommendation(item)
        aperture = _unit_from_range(telescope.aperture_mm, lower=50.0, upper=250.0)
        focal_length = _unit_from_range(telescope.focal_length_mm, lower=350.0, upper=2000.0)
        field_width = 1.0 - (0.75 * focal_length)
        tracking = max(base.tracking_or_goto, _tracking_capability(telescope.mount))
        return ObserverCapability(
            light_grasp=_clamp_unit((base.light_grasp + aperture) / 2.0),
            resolution=_clamp_unit((base.resolution + aperture) / 2.0),
            field_of_view=_clamp_unit((base.field_of_view + field_width) / 2.0),
            magnification_range=_clamp_unit((base.magnification_range + focal_length) / 2.0),
            tracking_or_goto=tracking,
            automation_or_eaa=base.automation_or_eaa,
            filters=base.filters,
            experience_level=base.experience_level,
            observing_style=base.observing_style,
            practical_comfort=base.practical_comfort,
            notes=(
                *base.notes,
                "nsom:planner_observer_capability",
                f"telescope={telescope.name}",
                f"aperture_mm={telescope.aperture_mm}",
                f"focal_length_mm={telescope.focal_length_mm}",
            ),
        )

    def effective_observability(
        self,
        item: CelestialObject,
        *,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        moon: MoonSummary | None = None,
    ) -> EffectiveObservability:
        runtime_environment = build_observation_environment(sky_quality=sky_quality)
        target_class = target_class_from_runtime_target(item)
        category_factor = self._category_factor(item, scores)
        moon_background = _moon_background_factor(target_class, moon)
        sky_background = _sky_background_factor(target_class, sky_quality)
        horizon_context = _horizon_context(item)
        environment = ObservationEnvironment.from_components(
            geometric_visibility=1.0 if item.visible else 0.0,
            lunar_sky_background=moon_background,
            static_sky_background=sky_background,
            atmospheric_transparency=category_factor,
            horizon_context=horizon_context,
            sky_quality_source=runtime_environment.sky_quality_source,
            weather_source=runtime_environment.weather_source,
            atmosphere_source=runtime_environment.atmosphere_source,
            notes=(
                "nsom:planner_experimental",
                "nsom:planner_runtime_environment",
                *runtime_environment.notes,
                f"target_class={target_class.value if target_class else 'unknown'}",
                f"moon_background_factor={moon_background:.3f}",
                f"sky_background_factor={sky_background:.3f}",
                f"advanced_score_factor={category_factor:.3f}",
                f"horizon_context={horizon_context:.3f}",
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


def _unit_from_score(value: object) -> float:
    return _clamp_unit(_finite_float(value, default=0.0) / 100.0)


def _unit_from_range(value: object, *, lower: float, upper: float) -> float:
    number = _finite_float(value, default=lower)
    if upper <= lower:
        return 0.0
    return _clamp_unit((number - lower) / (upper - lower))


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


def _profile_for_target_class(target_class: NsomTargetClass | None):
    if target_class is None:
        return None
    return NSOM_TARGET_CLASS_PROFILES.get(target_class)


def _moon_background_factor(target_class: NsomTargetClass | None, moon: MoonSummary | None) -> float:
    profile = _profile_for_target_class(target_class)
    if moon is None or profile is None:
        return 1.0
    max_influence = _clamp_unit(profile.max_moon_influence / 100.0)
    if max_influence <= 0.0:
        return 1.0
    illumination = _unit_from_percentage_text(getattr(moon, "illumination", ""))
    severity = _clamp_unit((illumination - 0.2) / 0.8)
    return _clamp_unit(1.0 - (severity * max_influence))


def _sky_background_factor(target_class: NsomTargetClass | None, sky_quality: SkyQuality) -> float:
    profile = _profile_for_target_class(target_class)
    if profile is None:
        return 1.0
    max_influence = _clamp_unit(profile.max_sky_background_influence / 100.0)
    if max_influence <= 0.0:
        return 1.0

    radiance = getattr(sky_quality, "viirs_radiance", None)
    if radiance is not None:
        radiance_value = max(0.0, _finite_float(radiance, default=0.0))
        severity = _clamp_unit(math.log10(radiance_value + 1.0) / 3.0)
    else:
        bortle = _finite_float(getattr(sky_quality, "bortle_class", None), default=4.0)
        severity = _clamp_unit((bortle - 3.0) / 6.0)
    return _clamp_unit(1.0 - (severity * max_influence))


def _horizon_context(item: CelestialObject) -> float:
    altitude = _first_number(getattr(item, "max_altitude", ""))
    if altitude is None:
        return 1.0 if item.visible else 0.0
    return _clamp_unit((altitude - 5.0) / 35.0)


def _unit_from_percentage_text(value: object) -> float:
    number = _first_number(value)
    return _clamp_unit((number or 0.0) / 100.0)


def _first_number(value: object) -> float | None:
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    return _finite_float(match.group(0).replace(",", "."), default=0.0)


def _tracking_capability(value: object) -> float:
    text = str(value).lower()
    if any(token in text for token in ("goto", "go-to", "computer", "eq", "tracking", "motoriz")):
        return 0.8
    if any(token in text for token in ("dob", "altaz", "manual")):
        return 0.2
    return 0.4
