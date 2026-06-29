from __future__ import annotations

import math
from dataclasses import dataclass
from dataclasses import replace

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.target_observation_traits import TargetObservationTraits
from astro_viewer.app.services.observing_score_service import ObservingScoreService


@dataclass(frozen=True)
class AodConditionInput:
    available: bool = False
    freshness_category: str = "unavailable"
    aod_550: float | None = None
    source: str = ""
    product: str = ""
    status: str = "unavailable"
    age_days: float | None = None


@dataclass(frozen=True)
class ParticulateConditionInput:
    available: bool = False
    freshness_category: str = "unavailable"
    pm25: float | None = None
    pm10: float | None = None
    source: str = ""
    status: str = "unavailable"
    age_days: float | None = None


@dataclass(frozen=True)
class ObservationConditionInputs:
    moon: MoonSummary | None = None
    sky_quality: SkyQuality | None = None
    aod: AodConditionInput | None = None
    particulate: ParticulateConditionInput | None = None


@dataclass(frozen=True)
class TargetConditionBreakdown:
    object_id: str
    base_score: int
    moon_penalty: float = 0.0
    pollution_penalty: float = 0.0
    weather_factor: float = 1.0
    seeing_factor: float = 1.0
    transparency_factor: float = 1.0
    equipment_modifier: float = 0.0
    aod_modifier: float = 0.0
    pm25_modifier: float = 0.0
    adjusted_score: int = 0
    applied_components: tuple[str, ...] = ()
    diagnostic_notes: tuple[str, ...] = ()
    already_adjusted_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConditionedTarget:
    target: CelestialObject
    breakdown: TargetConditionBreakdown
    original_target: CelestialObject | None = None


class ObservationConditionsService:
    """Applies existing observing-condition adjustments without changing formulas."""

    POLLUTION_CONTEXT_NOTE = "Cielo luminoso: visibilità limitata, serve trasparenza buona e schermare luci dirette."

    def apply_moon_adjustment(
        self,
        target: CelestialObject,
        moon: MoonSummary | None,
    ) -> ConditionedTarget:
        return self.condition_target(
            target,
            ObservationConditionInputs(moon=moon),
            apply_moon=True,
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
        return self._breakdown(
            object_id=target.id,
            base_score=base_score,
            moon_penalty=penalty,
            adjusted_score=adjusted_score,
            applied_components=components,
            diagnostic_notes=self._neutral_condition_diagnostics(ObservationConditionInputs()),
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
        return self.condition_target(
            target,
            ObservationConditionInputs(sky_quality=sky_quality),
            apply_pollution=True,
        )

    def condition_target(
        self,
        target: CelestialObject,
        inputs: ObservationConditionInputs | None = None,
        *,
        apply_moon: bool = False,
        apply_pollution: bool = False,
    ) -> ConditionedTarget:
        inputs = inputs or ObservationConditionInputs()
        score = target.score
        visible = target.visible
        notes = target.notes
        moon_penalty = 0.0
        pollution_penalty = 0.0
        applied_components: list[str] = []
        diagnostic_notes = list(self._neutral_condition_diagnostics(inputs))
        already_adjusted_flags: list[str] = []

        if apply_moon:
            moon_penalty = self.moon_penalty(target, inputs.moon)
            if moon_penalty > 0:
                applied_components.append("moon")
                diagnostic_notes.append(f"moon:illumination={self._moon_illumination(inputs.moon):g}")
            else:
                diagnostic_notes.append("moon:neutral")
            score = max(0, min(100, round(score - moon_penalty)))
        else:
            diagnostic_notes.append("moon:not_requested")

        if apply_pollution:
            if not self.is_pollution_context_active(inputs.sky_quality):
                diagnostic_notes.extend(self._sky_quality_diagnostics(inputs.sky_quality))
                diagnostic_notes.append("light_pollution:inactive")
            elif self.has_deep_sky_pollution_context(target):
                already_adjusted_flags.append("light_pollution")
                diagnostic_notes.extend(self._sky_quality_diagnostics(inputs.sky_quality))
                diagnostic_notes.append("light_pollution:already_applied")
            else:
                pollution_penalty = self.deep_sky_pollution_penalty(target, inputs.sky_quality)
                if pollution_penalty > 0:
                    applied_components.append("light_pollution")
                diagnostic_notes.extend(self._sky_quality_diagnostics(inputs.sky_quality))
                score = max(0, round(score - pollution_penalty))
                urban_note = self.POLLUTION_CONTEXT_NOTE
                if urban_note not in notes:
                    notes = f"{urban_note} {target.notes}"
                visible = visible and score > 10
        else:
            diagnostic_notes.append("light_pollution:not_requested")

        breakdown = self._breakdown(
            object_id=target.id,
            base_score=target.score,
            moon_penalty=moon_penalty,
            pollution_penalty=pollution_penalty,
            adjusted_score=score,
            applied_components=tuple(applied_components),
            diagnostic_notes=tuple(diagnostic_notes),
            already_adjusted_flags=tuple(already_adjusted_flags),
        )

        if score == target.score and visible == target.visible and notes == target.notes:
            return ConditionedTarget(target, breakdown, original_target=target)
        return ConditionedTarget(
            replace(
                target,
                score=score,
                score_label=ObservingScoreService.score_label(score),
                visible=visible,
                notes=notes,
            ),
            breakdown,
            original_target=target,
        )

    def condition_targets(
        self,
        targets: list[CelestialObject],
        inputs: ObservationConditionInputs | None = None,
        *,
        apply_moon: bool = False,
        apply_pollution: bool = False,
    ) -> list[ConditionedTarget]:
        return [
            self.condition_target(
                target,
                inputs,
                apply_moon=apply_moon,
                apply_pollution=apply_pollution,
            )
            for target in targets
        ]

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
    def _breakdown(
        *,
        object_id: str,
        base_score: int,
        moon_penalty: float = 0.0,
        pollution_penalty: float = 0.0,
        adjusted_score: int,
        applied_components: tuple[str, ...] = (),
        diagnostic_notes: tuple[str, ...] = (),
        already_adjusted_flags: tuple[str, ...] = (),
    ) -> TargetConditionBreakdown:
        return TargetConditionBreakdown(
            object_id=object_id,
            base_score=base_score,
            moon_penalty=moon_penalty,
            pollution_penalty=pollution_penalty,
            weather_factor=1.0,
            seeing_factor=1.0,
            transparency_factor=1.0,
            equipment_modifier=0.0,
            aod_modifier=0.0,
            pm25_modifier=0.0,
            adjusted_score=adjusted_score,
            applied_components=applied_components,
            diagnostic_notes=diagnostic_notes,
            already_adjusted_flags=already_adjusted_flags,
        )

    @classmethod
    def _neutral_condition_diagnostics(cls, inputs: ObservationConditionInputs) -> tuple[str, ...]:
        return (
            "weather:identity_placeholder",
            "seeing:identity_placeholder",
            "transparency:identity_placeholder",
            "equipment:identity_placeholder",
            *cls._aod_diagnostics(inputs.aod),
            *cls._particulate_diagnostics(inputs.particulate),
        )

    @staticmethod
    def _aod_diagnostics(aod: AodConditionInput | None) -> tuple[str, ...]:
        if aod is None:
            return ("aod:identity_placeholder",)
        category = ObservationConditionsService._freshness_category(aod.freshness_category)
        notes = [f"aod:{category}"]
        notes.append("aod:available" if aod.available else f"aod:unavailable:{aod.status}")
        if aod.product:
            notes.append(f"aod:product={aod.product}")
        if aod.source:
            notes.append(f"aod:source={aod.source}")
        if aod.aod_550 is not None:
            notes.append(f"aod:550={aod.aod_550:g}")
        if aod.age_days is not None:
            notes.append(f"aod:age_days={aod.age_days:g}")
        notes.append("aod:score_neutral")
        return tuple(notes)

    @staticmethod
    def _particulate_diagnostics(particulate: ParticulateConditionInput | None) -> tuple[str, ...]:
        if particulate is None:
            return ("pm25:identity_placeholder",)
        category = ObservationConditionsService._freshness_category(particulate.freshness_category)
        notes = [f"particulate:{category}"]
        notes.append("particulate:available" if particulate.available else f"particulate:unavailable:{particulate.status}")
        if particulate.source:
            notes.append(f"particulate:source={particulate.source}")
        if particulate.pm25 is not None:
            notes.append(f"pm25={particulate.pm25:g}")
        if particulate.pm10 is not None:
            notes.append(f"pm10={particulate.pm10:g}")
        if particulate.age_days is not None:
            notes.append(f"particulate:age_days={particulate.age_days:g}")
        notes.append("particulate:score_neutral")
        return tuple(notes)

    @staticmethod
    def _freshness_category(category: str) -> str:
        normalized = category.strip().lower().replace(" ", "_")
        return normalized or "unavailable"

    @classmethod
    def sky_quality_diagnostics(cls, sky_quality: SkyQuality | None) -> tuple[str, ...]:
        return cls._sky_quality_diagnostics(sky_quality)

    @staticmethod
    def _sky_quality_diagnostics(sky_quality: SkyQuality | None) -> tuple[str, ...]:
        if not sky_quality:
            return ("sky_quality:missing",)
        radiance = getattr(sky_quality, "viirs_radiance", None)
        viirs = "missing" if radiance is None else f"{radiance:g}"
        return (f"sky_quality:bortle={sky_quality.bortle_class}", f"sky_quality:viirs={viirs}")

    @classmethod
    def moon_illumination(cls, moon: MoonSummary | None) -> float:
        return cls._moon_illumination(moon)

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
