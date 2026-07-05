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
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.services.observer_capability_adapter import build_observer_capability_for_target


class BestObjectNsomComparisonService:
    """Developer-only comparison between legacy Best Object and NSOM concepts.

    The service evaluates only caller-supplied runtime inputs and returns a
    JSON-compatible diagnostic dictionary. It does not select the runtime Best
    Object, alter Home/Planner/Sky Compass state, write files, log, fetch data
    or expose fields to QML.
    """

    def __init__(
        self,
        *,
        score_service: ObservingScoreService | None = None,
    ) -> None:
        self._score_service = score_service or ObservingScoreService()

    def compare(
        self,
        candidates: Iterable[CelestialObject],
        *,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
        confidence: RecommendationConfidence | None = None,
    ) -> dict[str, object]:
        items = tuple(candidates)
        blocking_status = NightPlannerService.weather_blocking_status(weather)
        session = build_session_viability(weather_summary=weather, blocking_status=blocking_status)
        recommendation_confidence = confidence or build_recommendation_confidence(
            weather_summary=weather,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon is not None,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:best_object_comparison",),
        )
        evaluated = tuple(
            self._evaluate_item(
                item,
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
        selected = self._score_service.best_object(list(items), weather)

        return nsom_to_json_compatible(
            {
                "items": evaluated,
                "rankings": {
                    "legacy_best_object": _ranking_projection(
                        evaluated,
                        _rank_by_score(
                            (
                                item["object_id"],
                                item["legacy"]["best_object"]["score"],
                            )
                            for item in evaluated
                            if item["legacy"]["best_object"]["available"]
                        ),
                        "legacy",
                        "best_object",
                    ),
                    "nsom_observable": _ranking_projection(
                        evaluated,
                        _rank_by_score(
                            (
                                item["object_id"],
                                _value_field(item["nsom"]["observable_target_value"]),
                            )
                            for item in evaluated
                        ),
                        "nsom",
                        "observable_target_value",
                    ),
                    "nsom_practical": _ranking_projection(
                        evaluated,
                        _rank_by_score(
                            (
                                item["object_id"],
                                _value_field(item["nsom"]["practical_target_value"]),
                            )
                            for item in evaluated
                        ),
                        "nsom",
                        "practical_target_value",
                    ),
                },
                "legacy_formula": {
                    "name": "Best Object",
                    "formula": "item.score * weather_factor * difficulty_factor",
                    "selected_object_id": selected.id if selected else None,
                    "visibility_policy": "visible_candidates_only",
                    "ownership_note": (
                        "Legacy Best Object multiplies a pre-existing target score, "
                        "session weather and difficulty in one final scalar."
                    ),
                },
                "metadata": {
                    "developer_only": True,
                    "runtime_wiring": False,
                    "side_effects": {
                        "file_writes": False,
                        "automatic_logging": False,
                        "network": False,
                        "qml_exposure": False,
                        "best_object_changed": False,
                        "recommended_deep_sky_changed": False,
                        "planner_changed": False,
                        "sky_compass_changed": False,
                    },
                    "blocking_status": blocking_status,
                    "object_count": len(evaluated),
                },
            }
        )

    def _evaluate_item(
        self,
        item: CelestialObject,
        *,
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
            context_note="nsom:best_object_observer_capability",
        )
        q_target = project_observer_capability_for_target(observer, observable.target_class)
        practical = build_practical_target_value(
            observable,
            observer,
            capability_summary=q_target,
        )
        legacy = self._legacy_best_object_projection(item, weather=weather)
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
            "target_class": intrinsic.target_class,
            "legacy": {
                "best_object": legacy,
            },
            "nsom": nsom,
            "deltas": {
                "observable_vs_legacy_best_object": _delta_if_available(
                    _value_field(nsom["observable_target_value"]),
                    legacy,
                ),
                "practical_vs_legacy_best_object": _delta_if_available(
                    _value_field(nsom["practical_target_value"]),
                    legacy,
                ),
            },
        }

    def _legacy_best_object_projection(
        self,
        item: CelestialObject,
        *,
        weather: WeatherSummary,
    ) -> dict[str, object]:
        if not item.visible:
            return {
                "available": False,
                "score": None,
                "reason": "not_visible",
                "formula": "item.score * weather_factor * difficulty_factor",
                "unavailable_components": (
                    "best_object_score:not_ranked_when_invisible",
                    "intrinsic_target_quality:not_exposed_separately",
                    "observation_environment:not_exposed",
                    "effective_observability:not_exposed",
                    "observer_capability:not_exposed",
                    "session_viability:not_exposed_as_policy",
                    "recommendation_confidence:not_exposed",
                ),
            }

        weather_factor = max(0.25, weather.score_value / 100.0)
        difficulty_factor = self._score_service._difficulty_factor(item.difficulty)
        score = item.score * weather_factor * difficulty_factor
        return {
            "available": True,
            "score": score,
            "formula": "item.score * weather_factor * difficulty_factor",
            "components": {
                "item_score": item.score,
                "weather_factor": weather_factor,
                "difficulty_factor": difficulty_factor,
            },
            "ownership_mixing": {
                "target_value": {
                    "source": "item.score",
                    "mixed_into_final_score": True,
                    "nsom_equivalent": "not_available_as_intrinsic_or_observable_component",
                },
                "weather_session": {
                    "source": "weather_factor",
                    "mixed_into_final_score": True,
                    "nsom_equivalent": "SessionViability metadata",
                },
                "difficulty": {
                    "source": "difficulty_factor",
                    "mixed_into_final_score": True,
                    "nsom_equivalent": "not_separated_from_target_or_observer_context",
                },
            },
            "unavailable_components": (
                "intrinsic_target_quality:not_exposed_separately",
                "observation_environment:not_exposed",
                "effective_observability:not_exposed",
                "sky_background_component:not_part_of_best_object_formula",
                "moon_background_component:not_part_of_best_object_formula",
                "observer_capability_profile:not_part_of_best_object_formula",
                "session_blocking_policy:not_part_of_best_object_formula",
                "recommendation_confidence:not_part_of_best_object_formula",
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
            },
            "session_weather_effects": {
                "weather_score": weather.score_value,
                "blocking_status": blocking_status,
                "used_in_observable_target_value": False,
                "used_in_practical_target_value": False,
                "legacy_best_object_uses_weather_factor": True,
            },
            "observer_equipment_effects": {
                "used_in_intrinsic_target_quality": False,
                "used_in_observable_target_value": False,
                "used_in_practical_target_value": True,
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


def _rank_by_score(scores: Iterable[tuple[object, object]]) -> dict[str, int]:
    ordered = sorted(
        (
            (str(object_id), float(score), index)
            for index, (object_id, score) in enumerate(scores)
            if score is not None
        ),
        key=lambda item: (-item[1], item[2]),
    )
    return {object_id: rank for rank, (object_id, _score, _index) in enumerate(ordered, start=1)}


def _ranking_projection(
    evaluated: tuple[dict[str, object], ...],
    ranks: dict[str, int],
    area: str,
    component: str,
) -> tuple[dict[str, object], ...]:
    rows = []
    for item in evaluated:
        object_id = str(item["object_id"])
        if object_id not in ranks:
            continue
        score = _value_field(item[area][component]) if area == "nsom" else item[area][component]["score"]
        rows.append(
            {
                "rank": ranks[object_id],
                "object_id": item["object_id"],
                "score": score,
            }
        )
    return tuple(sorted(rows, key=lambda row: int(row["rank"])))


def _delta_if_available(value: object, legacy_projection: object) -> float | None:
    if not isinstance(legacy_projection, dict) or not legacy_projection.get("available"):
        return None
    legacy_score = legacy_projection.get("score")
    if legacy_score is None:
        return None
    return float(value) - float(legacy_score)


def _value_field(value: object) -> object:
    if isinstance(value, dict):
        return value["value"]
    return getattr(value, "value")
