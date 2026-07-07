from __future__ import annotations

from collections.abc import Iterable

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
from astro_viewer.app.models.sky import NightPlanItem, SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.home_nsom_observable import build_home_observation_environment
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_intrinsic_target_quality,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.observer_capability_adapter import build_observer_capability_for_target
from astro_viewer.app.services.sky_compass_service import SkyCompassService, SkyCompassTarget


class SkyCompassNsomComparisonService:
    """Developer-only comparison between current Sky Compass and NSOM concepts.

    The helper is passive: it evaluates caller-supplied runtime objects and
    returns JSON-compatible diagnostics. It does not change Sky Compass output,
    write files, log, fetch data, emit signals or expose fields to QML.
    """

    def __init__(self, *, compass_service: SkyCompassService | None = None) -> None:
        self._compass_service = compass_service or SkyCompassService()

    def compare(
        self,
        candidates: Iterable[CelestialObject],
        night_plan: Iterable[NightPlanItem],
        best_object: CelestialObject | None,
        *,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
        confidence: RecommendationConfidence | None = None,
        has_location: bool = True,
        caution_text: str = "",
    ) -> dict[str, object]:
        items = tuple(candidates)
        plan_items = tuple(night_plan)
        plan_ids = {item.object_id for item in plan_items}
        best_id = best_object.id if best_object else ""
        blocking_status = NightPlannerService.weather_blocking_status(weather)
        session = build_session_viability(weather_summary=weather, blocking_status=blocking_status)
        recommendation_confidence = confidence or build_recommendation_confidence(
            weather_summary=weather,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon is not None,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:sky_compass_comparison", "confidence:metadata_only"),
        )

        legacy_compass = self._compass_service.compass(
            list(items),
            list(plan_items),
            best_object,
            has_location=has_location,
            caution_text=caution_text,
        )
        legacy_targets = (
            tuple(self._compass_service._targets(list(items), plan_ids, best_id))
            if has_location
            else ()
        )
        legacy_by_id = {target.id: target for target in legacy_targets}
        legacy_groups = (
            tuple(self._compass_service._group_targets(list(legacy_targets)))
            if has_location
            else ()
        )
        evaluated = tuple(
            self._evaluate_item(
                item,
                legacy_target=legacy_by_id.get(item.id),
                has_location=has_location,
                weather=weather,
                sky_quality=sky_quality,
                telescope=telescope,
                moon=moon,
                blocking_status=blocking_status,
                session=session,
                confidence=recommendation_confidence,
            )
            for item in items
        )
        evaluated_by_id = {str(item["object_id"]): item for item in evaluated}
        direction_groups = tuple(
            _direction_projection(group, evaluated_by_id, selected_direction=legacy_compass.get("direction", ""))
            for group in legacy_groups
        )

        return nsom_to_json_compatible(
            {
                "items": evaluated,
                "direction_groups": direction_groups,
                "rankings": {
                    "legacy_direction": _legacy_direction_ranking(direction_groups),
                    "nsom_observable_direction_reference": _direction_reference_ranking(
                        direction_groups,
                        "observable_direction_score",
                    ),
                    "nsom_practical_direction_reference": _direction_reference_ranking(
                        direction_groups,
                        "practical_direction_score",
                    ),
                    "legacy_target_priority": _target_ranking(
                        evaluated,
                        area="legacy",
                        component="direction_score_contribution",
                    ),
                    "nsom_observable_target_reference": _target_ranking(
                        evaluated,
                        area="nsom",
                        component="observable_target_value",
                    ),
                    "nsom_practical_target_reference": _target_ranking(
                        evaluated,
                        area="nsom",
                        component="practical_target_value",
                    ),
                },
                "legacy_formula": {
                    "name": "Sky Compass",
                    "direction_formula": (
                        "sum(item.score + in_plan_bonus + best_object_bonus + "
                        "target_presence_bonus) per normalized direction"
                    ),
                    "in_plan_bonus": 42,
                    "best_object_bonus": 58,
                    "target_presence_bonus": 10,
                    "selected_direction": legacy_compass.get("direction", ""),
                    "available": legacy_compass.get("available", False),
                    "reason": legacy_compass.get("reason", ""),
                    "ownership_note": (
                        "Legacy Sky Compass groups already prepared Home targets by "
                        "direction, then mixes candidate score, plan membership, best "
                        "object status and target concentration into one direction scalar."
                    ),
                },
                "metadata": {
                    "developer_only": True,
                    "runtime_wiring": False,
                    "reference_only": True,
                    "score_parity_expected": False,
                    "side_effects": {
                        "file_writes": False,
                        "automatic_logging": False,
                        "network": False,
                        "qml_exposure": False,
                        "sky_compass_changed": False,
                        "home_changed": False,
                        "best_object_changed": False,
                        "planner_changed": False,
                    },
                    "blocking_status": blocking_status,
                    "session_viability": _session_projection(
                        session,
                        weather=weather,
                        blocking_status=blocking_status,
                    ),
                    "candidate_count": len(evaluated),
                    "ranked_target_count": len(legacy_targets),
                    "direction_group_count": len(direction_groups),
                },
            }
        )

    def _evaluate_item(
        self,
        item: CelestialObject,
        *,
        legacy_target: SkyCompassTarget | None,
        has_location: bool,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None,
        blocking_status: WeatherBlockingStatus,
        session: SessionViability,
        confidence: RecommendationConfidence,
    ) -> dict[str, object]:
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
            context_note="nsom:sky_compass_observer_capability",
        )
        q_target = project_observer_capability_for_target(observer, observable.target_class)
        practical = build_practical_target_value(
            observable,
            observer,
            capability_summary=q_target,
        )
        legacy = _legacy_target_projection(item, legacy_target, has_location=has_location)
        nsom = _nsom_projection(
            intrinsic,
            environment,
            effective,
            observable,
            practical,
            session,
            confidence,
            weather=weather,
            blocking_status=blocking_status,
        )
        return {
            "object_id": item.id,
            "name": item.name,
            "object_type": item.object_type,
            "direction": item.direction,
            "target_class": intrinsic.target_class,
            "legacy": {
                "sky_compass_target": legacy,
            },
            "nsom": nsom,
            "deltas": {
                "observable_vs_legacy_direction_contribution": _delta_if_available(
                    _value_field(nsom["observable_target_value"]),
                    legacy,
                    "direction_score_contribution",
                ),
                "practical_vs_legacy_direction_contribution": _delta_if_available(
                    _value_field(nsom["practical_target_value"]),
                    legacy,
                    "direction_score_contribution",
                ),
            },
        }


def _legacy_target_projection(
    item: CelestialObject,
    legacy_target: SkyCompassTarget | None,
    *,
    has_location: bool,
) -> dict[str, object]:
    if not has_location:
        return {
            "available": False,
            "score": None,
            "direction_score_contribution": None,
            "reason": "no_location",
            "unavailable_components": _legacy_unavailable_components(),
        }
    if not item.visible:
        return {
            "available": False,
            "score": None,
            "direction_score_contribution": None,
            "reason": "not_visible",
            "unavailable_components": _legacy_unavailable_components(),
        }
    if not SkyCompassService.normalize_direction(item.direction):
        return {
            "available": False,
            "score": None,
            "direction_score_contribution": None,
            "reason": "missing_direction",
            "unavailable_components": _legacy_unavailable_components(),
        }
    if legacy_target is None:
        return {
            "available": False,
            "score": None,
            "direction_score_contribution": None,
            "reason": "not_ranked_by_sky_compass",
            "unavailable_components": _legacy_unavailable_components(),
        }

    in_plan_bonus = 42 if legacy_target.in_plan else 0
    best_object_bonus = 58 if legacy_target.is_best else 0
    target_presence_bonus = 10
    direction_score_contribution = legacy_target.priority + target_presence_bonus
    return {
        "available": True,
        "score": legacy_target.score,
        "direction": legacy_target.direction,
        "priority": legacy_target.priority,
        "direction_score_contribution": direction_score_contribution,
        "formula": "item.score + in_plan_bonus + best_object_bonus + target_presence_bonus",
        "components": {
            "item_score": legacy_target.score,
            "in_plan_bonus": in_plan_bonus,
            "best_object_bonus": best_object_bonus,
            "target_presence_bonus": target_presence_bonus,
        },
        "ownership_mixing": {
            "target_value": {
                "source": "prepared CelestialObject.score",
                "mixed_into_direction_score": True,
                "nsom_equivalent": "not_available_as_separate_intrinsic_or_observable_component",
            },
            "planner_state": {
                "source": "NightPlanItem membership",
                "mixed_into_direction_score": legacy_target.in_plan,
                "nsom_equivalent": "presentation/context boost, not target physics",
            },
            "best_object_state": {
                "source": "current Best Object identity",
                "mixed_into_direction_score": legacy_target.is_best,
                "nsom_equivalent": "presentation/context boost, not target physics",
            },
            "direction_concentration": {
                "source": "one fixed target_presence_bonus per ranked target",
                "mixed_into_direction_score": True,
                "nsom_equivalent": "direction aggregation policy",
            },
        },
        "unavailable_components": _legacy_unavailable_components(),
    }


def _legacy_unavailable_components() -> tuple[str, ...]:
    return (
        "intrinsic_target_quality:not_exposed_separately",
        "observation_environment:not_exposed",
        "effective_observability:not_exposed",
        "observer_capability:not_part_of_sky_compass_formula",
        "session_viability:not_part_of_sky_compass_formula",
        "recommendation_confidence:not_part_of_sky_compass_formula",
        "upstream_score_breakdown:not_available_from_sky_compass_candidate",
    )


def _nsom_projection(
    intrinsic: IntrinsicTargetQuality,
    environment: ObservationEnvironment,
    effective: EffectiveObservability,
    observable: ObservableTargetValue,
    practical: PracticalTargetValue,
    session: SessionViability,
    confidence: RecommendationConfidence,
    *,
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
            "target_effects": {
                "intrinsic_target_quality_used": True,
                "observable_target_value_used": True,
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
                "used_in_legacy_sky_compass_formula": False,
            },
            "session_weather_effects": {
                "weather_score": weather.score_value,
                "blocking_status": blocking_status,
                "used_in_observable_target_value": False,
                "used_in_practical_target_value": False,
                "used_in_legacy_sky_compass_formula": False,
                "legacy_role": "caution_text_only_when_controller_supplies_it",
            },
            "observer_equipment_effects": {
                "used_in_intrinsic_target_quality": False,
                "used_in_observable_target_value": False,
                "used_in_practical_target_value": True,
                "used_in_legacy_sky_compass_formula": False,
                "q_target": practical.observer_capability_summary,
            },
            "direction_presentation_effects": {
                "used_in_legacy_sky_compass_formula": True,
                "used_in_intrinsic_target_quality": False,
                "used_in_observable_target_value": False,
                "used_in_practical_target_value": False,
                "nsom_layer": "presentation_policy",
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


def _direction_projection(
    group: dict[str, object],
    evaluated_by_id: dict[str, dict[str, object]],
    *,
    selected_direction: object,
) -> dict[str, object]:
    target_ids = tuple(str(item["id"]) for item in group["targets"])
    observable_score = sum(
        float(_value_field(evaluated_by_id[object_id]["nsom"]["observable_target_value"]))
        for object_id in target_ids
        if object_id in evaluated_by_id
    )
    practical_score = sum(
        float(_value_field(evaluated_by_id[object_id]["nsom"]["practical_target_value"]))
        for object_id in target_ids
        if object_id in evaluated_by_id
    )
    return {
        "direction": group["direction"],
        "selected_by_runtime": group["direction"] == selected_direction,
        "legacy": {
            "direction_score": group["directionScore"],
            "target_count": group["targetCount"],
            "target_ids": target_ids,
            "formula": "sum(target.direction_score_contribution)",
            "available_components": (
                "prepared_target_score",
                "plan_membership_bonus",
                "best_object_bonus",
                "target_presence_bonus",
            ),
            "unavailable_components": _legacy_unavailable_components(),
        },
        "nsom_reference": {
            "reference_only": True,
            "observable_direction_score": observable_score,
            "practical_direction_score": practical_score,
            "target_ids": target_ids,
            "runtime_ranking": False,
        },
    }


def _legacy_direction_ranking(direction_groups: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "rank": rank,
            "direction": group["direction"],
            "score": group["legacy"]["direction_score"],
            "runtime_ranking": True,
        }
        for rank, group in enumerate(
            sorted(
                direction_groups,
                key=lambda item: (
                    -float(item["legacy"]["direction_score"]),
                    -int(item["legacy"]["target_count"]),
                    _direction_index(str(item["direction"])),
                ),
            ),
            start=1,
        )
    )


def _direction_reference_ranking(
    direction_groups: tuple[dict[str, object], ...],
    component: str,
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "rank": rank,
            "direction": group["direction"],
            "score": group["nsom_reference"][component],
            "reference_only": True,
            "runtime_ranking": False,
        }
        for rank, group in enumerate(
            sorted(
                direction_groups,
                key=lambda item: (
                    -float(item["nsom_reference"][component]),
                    _direction_index(str(item["direction"])),
                ),
            ),
            start=1,
        )
    )


def _target_ranking(
    evaluated: tuple[dict[str, object], ...],
    *,
    area: str,
    component: str,
) -> tuple[dict[str, object], ...]:
    rows = []
    for index, item in enumerate(evaluated):
        score = _target_score(item, area=area, component=component)
        if score is None:
            continue
        rows.append((item, float(score), index))
    return tuple(
        {
            "rank": rank,
            "object_id": item["object_id"],
            "score": score,
            "reference_only": area == "nsom",
            "runtime_ranking": False,
        }
        for rank, (item, score, _index) in enumerate(
            sorted(rows, key=lambda row: (-row[1], row[2])),
            start=1,
        )
    )


def _target_score(item: dict[str, object], *, area: str, component: str) -> object:
    if area == "legacy":
        legacy = item["legacy"]["sky_compass_target"]
        if not legacy["available"]:
            return None
        return legacy[component]
    return _value_field(item[area][component])


def _delta_if_available(
    value: object,
    legacy_projection: object,
    component: str,
) -> float | None:
    if not isinstance(legacy_projection, dict) or not legacy_projection.get("available"):
        return None
    legacy_score = legacy_projection.get(component)
    if legacy_score is None:
        return None
    return float(value) - float(legacy_score)


def _value_field(value: object) -> object:
    if isinstance(value, dict):
        return value["value"]
    return getattr(value, "value")


def _direction_index(direction: str) -> int:
    try:
        return SkyCompassService.DIRECTIONS.index(direction)
    except ValueError:
        return len(SkyCompassService.DIRECTIONS)
