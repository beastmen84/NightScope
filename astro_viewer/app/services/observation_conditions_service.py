from __future__ import annotations

import math
from dataclasses import dataclass
from dataclasses import replace

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.target_observation_traits import TargetObservationTraits
from astro_viewer.app.services.observing_score_service import ObservingScoreService


@dataclass(frozen=True)
class ObservationConditionInputs:
    moon: MoonSummary | None = None
    sky_quality: SkyQuality | None = None


@dataclass(frozen=True)
class TargetConditionBreakdown:
    object_id: str
    base_score: int
    moon_penalty: float = 0.0
    pollution_penalty: float = 0.0
    adjusted_score: int = 0
    applied_components: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConditionedTarget:
    target: CelestialObject
    breakdown: TargetConditionBreakdown


class ObservationConditionsService:
    """Applies existing observing-condition adjustments without changing formulas."""

    POLLUTION_CONTEXT_NOTE = "Cielo luminoso: visibilità limitata, serve trasparenza buona e schermare luci dirette."

    def apply_moon_adjustment(
        self,
        target: CelestialObject,
        moon: MoonSummary | None,
    ) -> ConditionedTarget:
        breakdown = self.moon_adjusted_score(target, moon)
        if breakdown.adjusted_score == target.score:
            return ConditionedTarget(target, breakdown)
        return ConditionedTarget(
            replace(
                target,
                score=breakdown.adjusted_score,
                score_label=ObservingScoreService.score_label(breakdown.adjusted_score),
            ),
            breakdown,
        )

    def moon_adjusted_score(
        self,
        target: CelestialObject,
        moon: MoonSummary | None,
        current_score: int | None = None,
    ) -> TargetConditionBreakdown:
        base_score = target.score if current_score is None else current_score
        penalty = self.moon_penalty(target, moon)
        adjusted_score = max(0, min(100, round(base_score - penalty)))
        components = ("moon",) if penalty > 0 else ()
        return TargetConditionBreakdown(
            object_id=target.id,
            base_score=base_score,
            moon_penalty=penalty,
            adjusted_score=adjusted_score,
            applied_components=components,
        )

    def apply_deep_sky_pollution_context(
        self,
        targets: list[CelestialObject],
        sky_quality: SkyQuality | None,
    ) -> list[CelestialObject]:
        if not self.is_pollution_context_active(sky_quality):
            return targets

        updated = [self.apply_deep_sky_pollution_to_target(item, sky_quality).target for item in targets]
        return sorted([item for item in updated if item.visible], key=lambda item: item.score, reverse=True)[:10]

    def apply_deep_sky_pollution_to_target(
        self,
        target: CelestialObject,
        sky_quality: SkyQuality | None,
    ) -> ConditionedTarget:
        if not self.is_pollution_context_active(sky_quality):
            return ConditionedTarget(
                target,
                TargetConditionBreakdown(
                    object_id=target.id,
                    base_score=target.score,
                    adjusted_score=target.score,
                ),
            )
        if self.has_deep_sky_pollution_context(target):
            return ConditionedTarget(
                target,
                TargetConditionBreakdown(
                    object_id=target.id,
                    base_score=target.score,
                    adjusted_score=target.score,
                    applied_components=("light_pollution_already_applied",),
                ),
            )

        penalty = self.deep_sky_pollution_penalty(target, sky_quality)
        score = max(0, round(target.score - penalty))
        note = target.notes
        urban_note = self.POLLUTION_CONTEXT_NOTE
        if urban_note not in note:
            note = f"{urban_note} {target.notes}"
        breakdown = TargetConditionBreakdown(
            object_id=target.id,
            base_score=target.score,
            pollution_penalty=penalty,
            adjusted_score=score,
            applied_components=("light_pollution",) if penalty > 0 else (),
        )
        return ConditionedTarget(
            replace(
                target,
                score=score,
                score_label=ObservingScoreService.score_label(score),
                visible=target.visible and score > 10,
                notes=note,
            ),
            breakdown,
        )

    @classmethod
    def deep_sky_pollution_penalty(
        cls,
        target: CelestialObject,
        sky_quality: SkyQuality | None,
    ) -> float:
        if not sky_quality:
            return 0.0
        lower_type = target.object_type.lower()
        penalty = cls.deep_sky_pollution_base_penalty(sky_quality)
        if "galaxy" in lower_type or "galassia" in lower_type:
            penalty *= 2.0
        elif "nebula" in lower_type and "cluster" not in lower_type:
            penalty *= 1.6
        elif "globular" in lower_type:
            penalty *= 1.15
        elif "open" in lower_type or "cluster" in lower_type:
            penalty *= 0.55
        try:
            magnitude = float(target.magnitude)
        except ValueError:
            magnitude = 10.0
        if magnitude >= 8.5:
            penalty += 12
        surface_brightness = TargetObservationTraits.from_object(target).surface_brightness_proxy
        if surface_brightness and surface_brightness >= 13.5:
            penalty += 8
        return penalty

    @staticmethod
    def deep_sky_pollution_base_penalty(sky_quality: SkyQuality | None) -> float:
        if not sky_quality:
            return 0.0
        radiance = sky_quality.viirs_radiance
        bortle_penalty = max(0.0, (sky_quality.bortle_class - 6) * 8.0)
        if radiance is None:
            return max(6.0, bortle_penalty)
        radiance_penalty = min(24.0, math.log10(max(0.0, radiance) + 1.0) * 6.0)
        return max(6.0, bortle_penalty, radiance_penalty)

    @staticmethod
    def is_pollution_context_active(sky_quality: SkyQuality | None) -> bool:
        if not sky_quality:
            return False
        radiance = sky_quality.viirs_radiance
        if radiance is None and sky_quality.bortle_class < 7:
            return False
        return not (radiance is not None and radiance < 20 and sky_quality.bortle_class < 7)

    @classmethod
    def has_deep_sky_pollution_context(cls, target: CelestialObject) -> bool:
        return cls.POLLUTION_CONTEXT_NOTE in target.notes

    @classmethod
    def moon_penalty(cls, target: CelestialObject, moon: MoonSummary | None) -> float:
        sensitivity = cls._moon_sensitivity(target)
        if sensitivity <= 0:
            return 0.0
        illumination = cls._moon_illumination(moon)
        illumination_factor = max(0.0, min(1.0, (illumination - 25.0) / 75.0))
        return sensitivity * illumination_factor

    @staticmethod
    def _moon_illumination(moon: MoonSummary | None) -> float:
        if moon is None:
            return 0.0
        try:
            return float(moon.illumination.strip().replace("%", "").replace(",", "."))
        except ValueError:
            return 0.0

    @staticmethod
    def _moon_sensitivity(target: CelestialObject) -> float:
        lower_type = target.object_type.lower()
        if target.object_type == "Pianeta" or target.id in {
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
        }:
            return 0.0
        if "diffuse" in lower_type:
            return 42.0
        if "galaxy" in lower_type or "galassia" in lower_type:
            return 38.0
        if "planetary nebula" in lower_type or "nebulosa planetaria" in lower_type:
            return 18.0
        if "h ii" in lower_type or "emission" in lower_type or "supernova" in lower_type or "nebula" in lower_type or "nebul" in lower_type:
            return 26.0
        if "globular" in lower_type or "ammasso globulare" in lower_type:
            return 18.0
        if "open" in lower_type or "cluster" in lower_type or "star cloud" in lower_type or "asterism" in lower_type:
            return 10.0
        return 14.0
