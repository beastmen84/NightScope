from __future__ import annotations

from copy import deepcopy

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    IntrinsicTargetQuality,
    ObservableTargetValue,
    ObservationEnvironment,
    PracticalTargetValue,
    RecommendationConfidence,
    SessionViability,
    nsom_to_json_compatible,
    observer_capability_weight_profile_for_target,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.home_nsom_observable import build_home_observation_environment
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_intrinsic_target_quality,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionInputs,
    ObservationConditionsService,
)
from astro_viewer.app.services.observer_capability_adapter import build_observer_capability_for_target


DETAIL_SOURCE_OBSERVING = "observing"
DETAIL_SOURCE_CATALOGUE = "catalogue"


class DetailObjectNsomComparisonService:
    """Developer-only comparison between selected-object Detail legacy semantics and NSOM.

    The service only evaluates caller-supplied objects and runtime context. It
    does not select objects, update AppController state, write files, log, fetch
    data, emit signals or expose anything to QML.
    """

    def __init__(
        self,
        *,
        conditions_service: ObservationConditionsService | None = None,
    ) -> None:
        self._conditions_service = conditions_service or ObservationConditionsService()

    def compare(
        self,
        item: CelestialObject,
        *,
        source: str,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
        confidence: RecommendationConfidence | None = None,
    ) -> dict[str, object]:
        before = deepcopy(item)
        source_name = _normalize_source(source)
        blocking_status = NightPlannerService.weather_blocking_status(weather)
        session = build_session_viability(weather_summary=weather, blocking_status=blocking_status)
        recommendation_confidence = confidence or build_recommendation_confidence(
            weather_summary=weather,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon is not None,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:detail_object_comparison",),
        )

        intrinsic = build_intrinsic_target_quality(item)
        environment = build_home_observation_environment(item, intrinsic, sky_quality=sky_quality, moon=moon)
        effective = EffectiveObservability.from_environment(environment)
        observable = ObservableTargetValue.from_intrinsic(
            intrinsic_target_quality=intrinsic,
            effective_observability=effective,
            target_class=intrinsic.target_class,
        )
        observer = build_observer_capability_for_target(
            item,
            telescope=telescope,
            context_note="nsom:detail_object_observer_capability",
        )
        q_target = project_observer_capability_for_target(observer, observable.target_class)
        practical = build_practical_target_value(
            observable,
            observer,
            capability_summary=q_target,
        )
        legacy = self._legacy_detail_projection(item, source=source_name, moon=moon)
        nsom = _nsom_projection(
            intrinsic,
            environment,
            effective,
            observable,
            practical,
            session,
            recommendation_confidence,
            legacy_detail_uses_moon_adjustment=legacy["policy"] == "observing_detail_moon_adjusted_copy",
            weather=weather,
            blocking_status=blocking_status,
        )
        mutated = item != before

        return nsom_to_json_compatible(
            {
                "object_id": item.id,
                "name": item.name,
                "object_type": item.object_type,
                "target_class": intrinsic.target_class,
                "source": source_name,
                "legacy": {
                    "selected_object_detail": legacy,
                },
                "nsom": nsom,
                "deltas": {
                    "observable_vs_legacy_display_score": _delta(
                        _value_field(nsom["observable_target_value"]),
                        legacy["display_score"],
                    ),
                    "practical_vs_legacy_display_score": _delta(
                        _value_field(nsom["practical_target_value"]),
                        legacy["display_score"],
                    ),
                    "legacy_display_score_delta": legacy["score_delta"],
                },
                "metadata": {
                    "developer_only": True,
                    "runtime_wiring": False,
                    "runtime_object_mutated_by_comparison": mutated,
                    "side_effects": {
                        "file_writes": False,
                        "automatic_logging": False,
                        "network": False,
                        "qml_exposure": False,
                        "selected_object_changed": False,
                        "home_changed": False,
                        "best_object_changed": False,
                        "planner_changed": False,
                        "sky_compass_changed": False,
                    },
                },
            }
        )

    def _legacy_detail_projection(
        self,
        item: CelestialObject,
        *,
        source: str,
        moon: MoonSummary | None,
    ) -> dict[str, object]:
        if source == DETAIL_SOURCE_CATALOGUE:
            return {
                "available": True,
                "source": source,
                "runtime_property": "AppController.selectedObject",
                "policy": "catalogue_detail_raw_object",
                "formula": "_object_to_qml(selected_object)",
                "base_score": item.score,
                "display_score": item.score,
                "score_delta": 0,
                "display_object_replaced": False,
                "conditioned_copy_created": False,
                "components": {
                    "base_score": item.score,
                    "moon_adjustment": "not_applied_to_catalogue_detail",
                    "light_pollution": "not_requested",
                    "session_weather": "not_part_of_selected_object_detail",
                    "observer_equipment": "not_part_of_selected_object_detail_score",
                },
                "unavailable_components": (
                    "moon_condition_breakdown:not_available_for_catalogue_detail",
                    "sky_background_component:not_part_of_selected_object_detail",
                    "session_viability:not_part_of_selected_object_detail_score",
                    "observer_capability:not_part_of_selected_object_detail_score",
                    "recommendation_confidence:not_part_of_selected_object_detail_score",
                ),
            }

        conditioned = self._conditions_service.condition_target(
            item,
            ObservationConditionInputs(moon=moon),
            apply_moon=True,
        )
        breakdown = conditioned.breakdown
        return {
            "available": True,
            "source": source,
            "runtime_property": "AppController.selectedObject",
            "policy": "observing_detail_moon_adjusted_copy",
            "formula": "_object_to_qml(_moon_adjusted_object(selected_object))",
            "base_score": breakdown.base_score,
            "display_score": conditioned.target.score,
            "score_delta": conditioned.target.score - breakdown.base_score,
            "display_object_replaced": conditioned.target is not item,
            "conditioned_copy_created": conditioned.target != item,
            "components": {
                "base_score": breakdown.base_score,
                "moon_penalty": breakdown.moon_penalty,
                "moon_geometry_factor": breakdown.moon_geometry_factor,
                "adjusted_score": breakdown.adjusted_score,
                "light_pollution": "not_requested",
                "session_weather": "not_part_of_selected_object_detail",
                "observer_equipment": "not_part_of_selected_object_detail_score",
            },
            "breakdown": breakdown,
            "unavailable_components": (
                "sky_background_component:not_part_of_selected_object_detail",
                "session_viability:not_part_of_selected_object_detail_score",
                "observer_capability:not_part_of_selected_object_detail_score",
                "recommendation_confidence:not_part_of_selected_object_detail_score",
            ),
        }


def _nsom_projection(
    intrinsic: IntrinsicTargetQuality,
    environment: ObservationEnvironment,
    effective: EffectiveObservability,
    observable: ObservableTargetValue,
    practical: PracticalTargetValue,
    session: SessionViability,
    confidence: RecommendationConfidence,
    *,
    legacy_detail_uses_moon_adjustment: bool,
    weather: WeatherSummary,
    blocking_status: WeatherBlockingStatus,
) -> dict[str, object]:
    observer = practical.observer_capability
    return {
        "intrinsic_target_quality": intrinsic,
        "observation_environment": environment,
        "effective_observability": effective,
        "observable_target_value": observable,
        "observer_capability": {
            **nsom_to_json_compatible(observer),
            "summary_for_planning": observer.summary_for_planning(),
            "q_target": practical.observer_capability_summary,
            "target_class_weighting_profile": observer_capability_weight_profile_for_target(observable.target_class),
        },
        "practical_target_value": practical,
        "session_viability": _session_projection(session, weather=weather, blocking_status=blocking_status),
        "recommendation_confidence": _confidence_projection(confidence),
        "ownership": {
            "detail_runtime_payload": {
                "uses_nsom_fields": False,
                "payload_shape_changed": False,
            },
            "sky_effects": {
                "components": {
                    "geometric_visibility": environment.geometric_visibility,
                    "lunar_sky_background": environment.lunar_sky_background,
                    "static_sky_background": environment.static_sky_background,
                    "atmospheric_transparency": environment.atmospheric_transparency,
                    "horizon_context": environment.horizon_context,
                },
                "used_in_observable_target_value": True,
                "used_in_practical_target_value": True,
                "legacy_detail_uses_moon_adjustment": legacy_detail_uses_moon_adjustment,
                "legacy_detail_uses_static_sky_background": False,
            },
            "session_weather_effects": {
                "weather_score": weather.score_value,
                "blocking_status": blocking_status,
                "used_in_intrinsic_target_quality": False,
                "used_in_observable_target_value": False,
                "used_in_practical_target_value": False,
                "legacy_detail_uses_session_weather": False,
            },
            "observer_equipment_effects": {
                "used_in_intrinsic_target_quality": False,
                "used_in_observable_target_value": False,
                "used_in_practical_target_value": True,
                "legacy_detail_score_uses_equipment": False,
                "q_target": practical.observer_capability_summary,
            },
            "confidence_effects": {
                "role": "metadata_only",
                "score_factor": False,
                "score_effect": 0.0,
            },
        },
    }


def _session_projection(
    session: SessionViability,
    *,
    weather: WeatherSummary,
    blocking_status: WeatherBlockingStatus,
) -> dict[str, object]:
    return {
        **nsom_to_json_compatible(session),
        "role": "session_metadata",
        "score_factor": False,
        "score_effect_on_observable_target_value": 0.0,
        "score_effect_on_practical_target_value": 0.0,
        "weather_score": weather.score_value,
        "blocking_status": blocking_status,
    }


def _confidence_projection(confidence: RecommendationConfidence) -> dict[str, object]:
    return {
        **nsom_to_json_compatible(confidence),
        "value": confidence.value,
        "role": "metadata_only",
        "score_factor": False,
        "score_effect": 0.0,
    }


def _normalize_source(source: str) -> str:
    normalized = source.strip().casefold()
    if normalized == DETAIL_SOURCE_CATALOGUE:
        return DETAIL_SOURCE_CATALOGUE
    return DETAIL_SOURCE_OBSERVING


def _value_field(value: object) -> float:
    if isinstance(value, dict):
        return float(value["value"])
    return float(getattr(value, "value"))


def _delta(left: object, right: object) -> float:
    return float(left) - float(right)
