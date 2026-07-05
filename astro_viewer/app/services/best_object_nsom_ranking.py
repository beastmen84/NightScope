from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    ObservableTargetValue,
    ObservationOpportunity,
    PracticalTargetValue,
    RecommendationConfidence,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_observation_opportunity,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.observer_capability_adapter import build_observer_capability_for_target


NSOM_BEST_OBJECT_ENABLED = True


@dataclass(frozen=True)
class BestObjectNsomCandidate:
    """Internal NSOM projection for a Best Object candidate."""

    target: CelestialObject
    observable_target_value: ObservableTargetValue
    practical_target_value: PracticalTargetValue
    opportunity: ObservationOpportunity
    actionability: str
    stable_order_index: int

    @property
    def score(self) -> float:
        return self.opportunity.value

    @property
    def actionable(self) -> bool:
        return self.actionability == "actionable_ranked_recommendation"


class BestObjectNsomSelectionService:
    """Default-off NSOM Best Object selector.

    The service consumes caller-supplied runtime state only. It does not write
    files, log, fetch data, expose QML fields or mutate CelestialObject inputs.
    """

    def best_object(
        self,
        candidates: Iterable[CelestialObject],
        *,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
        confidence: RecommendationConfidence | None = None,
        blocking_status: WeatherBlockingStatus | None = None,
    ) -> CelestialObject | None:
        for candidate in self.ranked_candidates(
            candidates,
            weather=weather,
            sky_quality=sky_quality,
            telescope=telescope,
            moon=moon,
            confidence=confidence,
            blocking_status=blocking_status,
        ):
            if candidate.actionable:
                return candidate.target
        return None

    def ranked_candidates(
        self,
        candidates: Iterable[CelestialObject],
        *,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
        confidence: RecommendationConfidence | None = None,
        blocking_status: WeatherBlockingStatus | None = None,
    ) -> tuple[BestObjectNsomCandidate, ...]:
        items = tuple(candidates)
        blocking = blocking_status or NightPlannerService.weather_blocking_status(weather)
        recommendation_confidence = confidence or build_recommendation_confidence(
            weather_summary=weather,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon is not None,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:best_object_runtime", "confidence:metadata_only"),
        )
        projected = tuple(
            self._candidate(
                item,
                stable_order_index=index,
                weather=weather,
                sky_quality=sky_quality,
                telescope=telescope,
                moon=moon,
                blocking_status=blocking,
                confidence=recommendation_confidence,
            )
            for index, item in enumerate(items)
        )
        return tuple(sorted(projected, key=lambda item: (-item.score, item.stable_order_index)))

    def _candidate(
        self,
        item: CelestialObject,
        *,
        stable_order_index: int,
        weather: WeatherSummary,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None,
        blocking_status: WeatherBlockingStatus,
        confidence: RecommendationConfidence,
    ) -> BestObjectNsomCandidate:
        observable = build_home_observable_target_value(item, sky_quality=sky_quality, moon=moon)
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
        session = build_session_viability(weather_summary=weather, blocking_status=blocking_status)
        opportunity = build_observation_opportunity(
            practical,
            observing_window_quality=1.0,
            chronology_fit=1.0,
            session=session,
            practical_constraints=1.0,
            confidence=confidence,
            context=("best_object", "nsom_runtime"),
        )
        return BestObjectNsomCandidate(
            target=item,
            observable_target_value=observable,
            practical_target_value=practical,
            opportunity=opportunity,
            actionability=_actionability(item, blocking_status),
            stable_order_index=stable_order_index,
        )


def _actionability(item: CelestialObject, blocking_status: WeatherBlockingStatus) -> str:
    if not item.visible:
        return "non_actionable_invisible_target"
    if blocking_status.blocks_plan:
        return "non_actionable_hard_block"
    return "actionable_ranked_recommendation"
