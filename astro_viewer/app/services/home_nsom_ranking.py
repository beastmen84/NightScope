from __future__ import annotations

from collections.abc import Iterable

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.home_nsom_observable import build_home_observable_target_value


NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED = False


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
    ) -> list[CelestialObject]:
        scored = [
            (
                item,
                build_home_observable_target_value(item, sky_quality=sky_quality, moon=moon).value,
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
