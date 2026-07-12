from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace

from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionInputs,
)
from astro_viewer.app.services.nsom_target import unique_targets_by_id


class HomeRecommendedDeepSkyNsomRankingService:
    """Ranks Home recommendedDeepSky candidates by NSOM ObservableTargetValue.

    This service intentionally stays inside the Home object/sky layer. It does
    not use PracticalTargetValue, ObserverCapability,
    SessionViability, RecommendationConfidence or ObservationOpportunity.
    """

    def rank_by_observable_target_value(
        self,
        candidates: Iterable[CelestialObject],
        *,
        condition_inputs: ObservationConditionInputs,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None = None,
    ) -> list[CelestialObject]:
        scored = [
            (
                item,
                build_home_observable_target_value(
                    item,
                    condition_inputs=replace(
                        condition_inputs,
                        moon_geometry=(moon_geometry_by_object_id or {}).get(item.id),
                    ),
                ).value,
                index,
            )
            for index, item in enumerate(unique_targets_by_id(candidates))
        ]
        return [
            item
            for item, _score, _index in sorted(
                scored,
                key=lambda row: (-row[1], row[2]),
            )
        ]
