from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionInputs,
)


NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED = True


class HomeRecommendedDeepSkyNsomRankingService:
    """Ranks Home recommendedDeepSky candidates by NSOM ObservableTargetValue.

    This default-off service intentionally stays inside the Home object/sky
    layer. It does not use PracticalTargetValue, ObserverCapability,
    SessionViability, RecommendationConfidence or ObservationOpportunity.
    """

    def rank_by_observable_target_value(
        self,
        candidates: Iterable[CelestialObject],
        *,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
        condition_inputs: ObservationConditionInputs | None = None,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None = None,
    ) -> list[CelestialObject]:
        common_inputs = condition_inputs or ObservationConditionInputs(
            moon=moon,
            sky_quality=sky_quality,
        )
        scored = [
            (
                item,
                build_home_observable_target_value(
                    item,
                    condition_inputs=replace(
                        common_inputs,
                        moon_geometry=(moon_geometry_by_object_id or {}).get(item.id),
                    ),
                ).value,
                index,
            )
            for index, item in enumerate(candidates)
        ]
        return [
            item
            for item, _score, _index in sorted(
                scored,
                key=lambda row: (-row[1], row[2]),
            )
        ]
