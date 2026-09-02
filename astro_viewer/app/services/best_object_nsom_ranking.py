"""Select the canonical Best Object from actionable NSOM opportunities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace

from astro_viewer.app.models.condition_inputs import (
    MoonGeometryConditionInput,
    ObservationConditionInputs,
)
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    ObservableTargetValue,
    ObservationOpportunity,
    PracticalTargetValue,
    RecommendationConfidence,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_runtime_builders import (
    build_observation_opportunity,
    build_practical_target_value,
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.nsom_target import unique_targets_by_id
from astro_viewer.app.services.observer_capability_adapter import build_observer_capability_for_target


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
    """Canonical NSOM Best Object selector.

    The service consumes caller-supplied runtime state only. It does not write
    files, log, fetch data, expose QML fields or mutate CelestialObject inputs.
    """

    def best_object(
        self,
        candidates: Iterable[CelestialObject],
        *,
        weather: WeatherSummary,
        telescope: Telescope,
        condition_inputs: ObservationConditionInputs,
        confidence: RecommendationConfidence | None = None,
        blocking_status: WeatherBlockingStatus | None = None,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None = None,
        telescope_by_object_id: Mapping[str, Telescope] | None = None,
    ) -> CelestialObject | None:
        for candidate in self.ranked_candidates(
            candidates,
            weather=weather,
            telescope=telescope,
            condition_inputs=condition_inputs,
            confidence=confidence,
            blocking_status=blocking_status,
            moon_geometry_by_object_id=moon_geometry_by_object_id,
            telescope_by_object_id=telescope_by_object_id,
        ):
            if candidate.actionable:
                return candidate.target
        return None

    def ranked_candidates(
        self,
        candidates: Iterable[CelestialObject],
        *,
        weather: WeatherSummary,
        telescope: Telescope,
        condition_inputs: ObservationConditionInputs,
        confidence: RecommendationConfidence | None = None,
        blocking_status: WeatherBlockingStatus | None = None,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None = None,
        telescope_by_object_id: Mapping[str, Telescope] | None = None,
    ) -> tuple[BestObjectNsomCandidate, ...]:
        items = unique_targets_by_id(candidates)
        blocking = blocking_status or NightPlannerService.weather_blocking_status(weather)
        projected = tuple(
            self._candidate(
                item,
                stable_order_index=index,
                weather=weather,
                telescope=(telescope_by_object_id or {}).get(item.id, telescope),
                blocking_status=blocking,
                confidence=confidence,
                condition_inputs=condition_inputs,
                moon_geometry=(moon_geometry_by_object_id or {}).get(item.id),
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
        telescope: Telescope,
        blocking_status: WeatherBlockingStatus,
        confidence: RecommendationConfidence | None,
        condition_inputs: ObservationConditionInputs,
        moon_geometry: MoonGeometryConditionInput | None,
    ) -> BestObjectNsomCandidate:
        observable = build_home_observable_target_value(
            item,
            condition_inputs=replace(condition_inputs, moon_geometry=moon_geometry),
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
        session = build_session_viability(weather_summary=weather, blocking_status=blocking_status)
        recommendation_confidence = confidence or build_recommendation_confidence(
            weather_summary=weather,
            aod_result=condition_inputs.aod,
            local_atmosphere=condition_inputs.particulate,
            viirs_available=(
                getattr(condition_inputs.sky_quality, "viirs_radiance", None) is not None
            ),
            moon_geometry_available=(
                None if condition_inputs.moon is None else moon_geometry is not None
            ),
            notes=("nsom:best_object_runtime", "confidence:metadata_only"),
        )
        opportunity = build_observation_opportunity(
            practical,
            observing_window_quality=1.0,
            chronology_fit=1.0,
            session=session,
            practical_constraints=1.0,
            confidence=recommendation_confidence,
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
