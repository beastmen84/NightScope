from __future__ import annotations

from typing import Iterable

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    ObservationOpportunity,
    RecommendationConfidence,
    nsom_to_json_compatible,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService
from astro_viewer.app.services.planner_scoring_service import (
    PlannerScoreBreakdown,
    PlannerScoringService,
)


class PlannerNsomComparisonService:
    """Developer-only legacy-vs-NSOM Planner comparison helper.

    The helper is intentionally passive: it only evaluates the objects supplied
    by the caller and returns JSON-compatible dictionaries. It does not write,
    log, emit signals, fetch data or expose anything to QML.
    """

    def __init__(
        self,
        *,
        legacy_scoring_service: PlannerScoringService | None = None,
        nsom_scoring_service: PlannerNsomScoringService | None = None,
    ) -> None:
        self._legacy_scoring_service = legacy_scoring_service or PlannerScoringService()
        self._nsom_scoring_service = nsom_scoring_service or PlannerNsomScoringService()

    def compare(
        self,
        objects: Iterable[CelestialObject],
        *,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
    ) -> dict[str, object]:
        items = tuple(objects)
        blocking_status = NightPlannerService.weather_blocking_status(weather)
        evaluated = tuple(
            self._evaluate_item(
                item,
                weather=weather,
                scores=scores,
                sky_quality=sky_quality,
                telescope=telescope,
                moon=moon,
                blocking_status=blocking_status,
            )
            for item in items
        )
        legacy_ranks = _rank_by_score(
            (item["object_id"], item["legacy"]["score"]) for item in evaluated
        )
        nsom_ranks = _rank_by_score(
            (item["object_id"], item["nsom"]["score"]) for item in evaluated
        )

        comparison_items = []
        for item in evaluated:
            object_id = str(item["object_id"])
            legacy_rank = legacy_ranks[object_id]
            nsom_rank = nsom_ranks[object_id]
            legacy_score = float(item["legacy"]["score"])
            nsom_score = float(item["nsom"]["score"])
            comparison_items.append(
                {
                    **item,
                    "legacy": {
                        **item["legacy"],
                        "rank": legacy_rank,
                    },
                    "nsom": {
                        **item["nsom"],
                        "rank": nsom_rank,
                    },
                    "score_delta": nsom_score - legacy_score,
                    "rank_delta": nsom_rank - legacy_rank,
                }
            )

        return nsom_to_json_compatible(
            {
                "items": tuple(comparison_items),
                "rankings": {
                    "legacy": _ranking_projection(evaluated, legacy_ranks, "legacy"),
                    "nsom": _ranking_projection(evaluated, nsom_ranks, "nsom"),
                },
                "metadata": {
                    "nsom_planner_scoring_enabled": False,
                    "blocking_status": blocking_status,
                    "object_count": len(comparison_items),
                },
            }
        )

    def _evaluate_item(
        self,
        item: CelestialObject,
        *,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None,
        blocking_status: WeatherBlockingStatus,
    ) -> dict[str, object]:
        legacy_breakdown = self._legacy_scoring_service.score_breakdown(
            item,
            weather,
            scores,
            sky_quality,
            telescope,
            moon,
        )
        opportunity = self._nsom_scoring_service.opportunity(
            item,
            weather=weather,
            scores=scores,
            sky_quality=sky_quality,
            telescope=telescope,
            moon=moon,
            blocking_status=blocking_status,
            observing_window_quality=NightPlannerService._observing_window_quality(item),
            chronology_fit=NightPlannerService._chronology_fit(item),
            practical_constraints=NightPlannerService._practical_constraints(item),
        )
        return {
            "object_id": item.id,
            "name": item.name,
            "object_type": item.object_type,
            "legacy": _legacy_projection(legacy_breakdown),
            "nsom": _nsom_projection(opportunity),
        }


def _legacy_projection(breakdown: PlannerScoreBreakdown) -> dict[str, object]:
    return {
        "score": breakdown.final_score,
        "breakdown": breakdown,
    }


def _nsom_projection(opportunity: ObservationOpportunity) -> dict[str, object]:
    practical = opportunity.practical_target_value
    observable = practical.observable_target_value
    effective = observable.effective_observability
    observer = practical.observer_capability
    confidence = opportunity.confidence
    return {
        "score": opportunity.value,
        "components": {
            "practical_target_value": practical,
            "observable_target_value": observable,
            "effective_observability": effective,
            "session_viability": opportunity.session,
            "observer_capability": {
                **nsom_to_json_compatible(observer),
                "summary_for_planning": observer.summary_for_planning(),
            },
            "recommendation_confidence": _confidence_projection(confidence),
        },
    }


def _confidence_projection(confidence: RecommendationConfidence | None) -> object:
    if confidence is None:
        return None
    return {
        **nsom_to_json_compatible(confidence),
        "value": confidence.value,
    }


def _rank_by_score(scores: Iterable[tuple[object, object]]) -> dict[str, int]:
    ordered = sorted(
        ((str(object_id), float(score), index) for index, (object_id, score) in enumerate(scores)),
        key=lambda item: (-item[1], item[2]),
    )
    return {object_id: rank for rank, (object_id, _score, _index) in enumerate(ordered, start=1)}


def _ranking_projection(
    evaluated: tuple[dict[str, object], ...],
    ranks: dict[str, int],
    path: str,
) -> tuple[dict[str, object], ...]:
    rows = tuple(
        {
            "rank": ranks[str(item["object_id"])],
            "object_id": item["object_id"],
            "score": item[path]["score"],
        }
        for item in evaluated
    )
    return tuple(sorted(rows, key=lambda row: int(row["rank"])))
