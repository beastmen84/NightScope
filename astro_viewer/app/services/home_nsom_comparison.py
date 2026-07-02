from __future__ import annotations

from typing import Iterable

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    IntrinsicTargetQuality,
    NsomTargetClass,
    ObservableTargetValue,
    ObservationEnvironment,
    PracticalTargetValue,
    RecommendationConfidence,
    nsom_to_json_compatible,
    observer_capability_weight_profile_for_target,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_intrinsic_target_quality,
    build_practical_target_value,
    build_recommendation_confidence,
    target_class_from_runtime_target,
)
from astro_viewer.app.services.home_nsom_observable import build_home_observation_environment
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionInputs,
    ObservationConditionsService,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService


class HomeNsomComparisonService:
    """Developer-only Home/Best Object legacy-vs-NSOM comparison helper.

    The helper is intentionally passive: it evaluates only caller-supplied
    runtime objects and returns JSON-compatible dictionaries. It does not write,
    log, emit signals, fetch data, recompute Home output or expose anything to
    QML.
    """

    def __init__(
        self,
        *,
        conditions_service: ObservationConditionsService | None = None,
        score_service: ObservingScoreService | None = None,
        nsom_scoring_service: PlannerNsomScoringService | None = None,
    ) -> None:
        self._conditions_service = conditions_service or ObservationConditionsService()
        self._score_service = score_service or ObservingScoreService()
        self._nsom_scoring_service = nsom_scoring_service or PlannerNsomScoringService()

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
        recommendation_confidence = confidence or build_recommendation_confidence(
            weather_summary=weather,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon is not None,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:home_comparison",),
        )
        evaluated = tuple(
            self._evaluate_item(
                item,
                weather=weather,
                sky_quality=sky_quality,
                telescope=telescope,
                moon=moon,
                blocking_status=blocking_status,
                confidence=recommendation_confidence,
            )
            for item in items
        )

        rankings = {
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
            "legacy_home_deep_sky": _ranking_projection(
                evaluated,
                _rank_by_score(
                    (
                        item["object_id"],
                        item["legacy"]["home_deep_sky_adjusted"]["score"],
                    )
                    for item in evaluated
                    if item["legacy"]["home_deep_sky_adjusted"]["available"]
                ),
                "legacy",
                "home_deep_sky_adjusted",
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
        }

        return nsom_to_json_compatible(
            {
                "items": evaluated,
                "rankings": rankings,
                "metadata": {
                    "developer_only": True,
                    "runtime_wiring": False,
                    "side_effects": {
                        "file_writes": False,
                        "automatic_logging": False,
                        "network": False,
                        "qml_exposure": False,
                        "home_ranking_changed": False,
                        "best_object_changed": False,
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
        observer = self._nsom_scoring_service.observer_capability(item, telescope=telescope)
        q_target = project_observer_capability_for_target(observer, observable.target_class)
        practical = build_practical_target_value(
            observable,
            observer,
            capability_summary=q_target,
        )
        legacy = {
            "home_deep_sky_adjusted": self._legacy_home_deep_sky_projection(item, moon=moon),
            "best_object": self._legacy_best_object_projection(item, weather=weather),
        }
        nsom = _nsom_projection(
            intrinsic,
            environment,
            effective,
            observable,
            practical,
            confidence,
            weather=weather,
            blocking_status=blocking_status,
        )

        return {
            "object_id": item.id,
            "name": item.name,
            "object_type": item.object_type,
            "target_class": intrinsic.target_class,
            "legacy": legacy,
            "nsom": nsom,
            "deltas": _deltas(legacy, nsom),
        }

    def _legacy_home_deep_sky_projection(
        self,
        item: CelestialObject,
        *,
        moon: MoonSummary | None,
    ) -> dict[str, object]:
        target_class = target_class_from_runtime_target(item)
        if not _is_home_deep_sky_target(target_class):
            return {
                "available": False,
                "score": None,
                "reason": "not_home_deep_sky_candidate",
                "unavailable_components": (
                    "home_deep_sky_adjusted_score:not_applied_to_planets_or_moon",
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
            "score": conditioned.target.score,
            "components": {
                "base_score": breakdown.base_score,
                "moon_penalty": breakdown.moon_penalty,
                "adjusted_score": breakdown.adjusted_score,
                "light_pollution": "not_requested",
                "session_weather": "not_part_of_home_deep_sky_adjustment",
                "observer_equipment": "not_part_of_home_deep_sky_adjustment",
            },
            "breakdown": breakdown,
            "unavailable_components": (
                "weather_session_component:not_part_of_home_deep_sky_adjustment",
                "observer_capability_component:not_part_of_home_deep_sky_adjustment",
            ),
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
                "unavailable_components": ("best_object_score:not_ranked_when_invisible",),
            }

        weather_factor = max(0.25, weather.score_value / 100.0)
        difficulty_factor = self._score_service._difficulty_factor(item.difficulty)
        score = item.score * weather_factor * difficulty_factor
        return {
            "available": True,
            "score": score,
            "components": {
                "base_score": item.score,
                "weather_factor": weather_factor,
                "difficulty_factor": difficulty_factor,
            },
            "formula": "target.score * weather_factor * difficulty_factor",
            "unavailable_components": (
                "weather_moon_penalty_breakout:not_exposed_by_weather_summary",
                "sky_background_component:not_part_of_best_object_formula",
                "observer_capability_profile:not_part_of_best_object_formula",
                "session_blocking_policy:not_part_of_best_object_formula",
            ),
        }


def _nsom_projection(
    intrinsic: IntrinsicTargetQuality,
    environment: ObservationEnvironment,
    effective: EffectiveObservability,
    observable: ObservableTargetValue,
    practical: PracticalTargetValue,
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
        "recommendation_confidence": _confidence_projection(confidence),
        "ownership": {
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
                "used_in_intrinsic_target_quality": False,
                "used_in_observable_target_value": False,
                "used_in_practical_target_value": False,
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


def _confidence_projection(confidence: RecommendationConfidence) -> dict[str, object]:
    return {
        **nsom_to_json_compatible(confidence),
        "value": confidence.value,
        "role": "metadata_only",
        "score_factor": False,
        "score_effect": 0.0,
    }


def _deltas(legacy: dict[str, object], nsom: dict[str, object]) -> dict[str, object]:
    home_adjusted = legacy["home_deep_sky_adjusted"]
    best_object = legacy["best_object"]
    observable_score = _value_field(nsom["observable_target_value"])
    practical_score = _value_field(nsom["practical_target_value"])
    return {
        "observable_vs_home_deep_sky_adjusted": _delta_if_available(
            observable_score,
            home_adjusted,
        ),
        "practical_vs_best_object_legacy": _delta_if_available(
            practical_score,
            best_object,
        ),
    }


def _delta_if_available(value: object, legacy_projection: object) -> float | None:
    if not isinstance(legacy_projection, dict) or not legacy_projection.get("available"):
        return None
    legacy_score = legacy_projection.get("score")
    if legacy_score is None:
        return None
    return float(value) - float(legacy_score)


def _is_home_deep_sky_target(target_class: NsomTargetClass | None) -> bool:
    return target_class not in (None, NsomTargetClass.PLANET, NsomTargetClass.MOON)


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


def _value_field(value: object) -> object:
    if isinstance(value, dict):
        return value["value"]
    return getattr(value, "value")
