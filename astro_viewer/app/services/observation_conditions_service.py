from __future__ import annotations

import math
from dataclasses import dataclass
from dataclasses import field
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
    uncertainty: float | None = None
    qa_raw: int | None = None
    method: str = ""
    local_valid_pixel_count: int | None = None


@dataclass(frozen=True)
class ParticulateConditionInput:
    available: bool = False
    freshness_category: str = "unavailable"
    pm25: float | None = None
    pm10: float | None = None
    source: str = ""
    status: str = "unavailable"
    age_days: float | None = None
    distance_km: float | None = None


@dataclass(frozen=True)
class ObservationConditionFeatureFlags:
    """Experimental condition modifiers, intentionally disabled by default."""

    experimental_aerosol_scoring: bool = False
    experimental_moon_geometry_scoring: bool = False


@dataclass(frozen=True)
class MoonGeometryConditionInput:
    """Future Moon geometry diagnostics for score-neutral characterization."""

    moon_altitude_deg: float | None = None
    moon_target_separation_deg: float | None = None
    moon_above_horizon: bool | None = None
    moon_visible_during_target_window: bool | None = None
    moon_set_before_target_window: bool | None = None


@dataclass(frozen=True)
class AtmosphericSensitivityProfile:
    """Intended future aerosol/particulate sensitivity for a target class."""

    target_class: str
    sensitivity: float
    penalty_cap: float


@dataclass(frozen=True)
class ObservationConditionInputs:
    moon: MoonSummary | None = None
    sky_quality: SkyQuality | None = None
    aod: AodConditionInput | None = None
    particulate: ParticulateConditionInput | None = None
    moon_geometry: MoonGeometryConditionInput | None = None
    feature_flags: ObservationConditionFeatureFlags = field(default_factory=ObservationConditionFeatureFlags)

    @classmethod
    def diagnostic_only(
        cls,
        *,
        aod: AodConditionInput | None = None,
        particulate: ParticulateConditionInput | None = None,
    ) -> ObservationConditionInputs:
        return cls(aod=aod, particulate=particulate)


@dataclass(frozen=True)
class TargetConditionBreakdown:
    object_id: str
    base_score: int
    moon_penalty: float = 0.0
    moon_geometry_factor: float = 1.0
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
    POLLUTION_CONTEXT_FLAG = "light_pollution"
    SOLAR_SYSTEM_IDS = frozenset(
        {
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
        }
    )

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
        diagnostic_notes = list(self._neutral_condition_diagnostics(ObservationConditionInputs(moon=moon)))
        if penalty > 0:
            diagnostic_notes.append(f"moon:illumination={self._moon_illumination(moon):g}")
        else:
            diagnostic_notes.append("moon:neutral")
        diagnostic_notes.append("light_pollution:not_requested")
        return self._breakdown(
            object_id=target.id,
            base_score=base_score,
            moon_penalty=penalty,
            adjusted_score=adjusted_score,
            applied_components=components,
            diagnostic_notes=tuple(diagnostic_notes),
        )

    def apply_deep_sky_pollution_context(
        self,
        targets: list[CelestialObject],
        sky_quality: SkyQuality | None,
        inputs: ObservationConditionInputs | None = None,
    ) -> list[CelestialObject]:
        return [
            conditioned.target
            for conditioned in self.condition_deep_sky_pollution_context(targets, sky_quality, inputs)
        ]

    def condition_deep_sky_pollution_context(
        self,
        targets: list[CelestialObject],
        sky_quality: SkyQuality | None,
        inputs: ObservationConditionInputs | None = None,
    ) -> list[ConditionedTarget]:
        condition_inputs = self._pollution_inputs(sky_quality, inputs)
        if not self.is_pollution_context_active(condition_inputs.sky_quality):
            return [
                self.condition_target(item, condition_inputs, apply_pollution=False)
                for item in targets
            ]

        updated = [
            self.condition_target(item, condition_inputs, apply_pollution=True)
            for item in targets
        ]
        return sorted(
            [item for item in updated if item.target.visible],
            key=lambda item: item.target.score,
            reverse=True,
        )[:10]

    def apply_deep_sky_pollution_to_target(
        self,
        target: CelestialObject,
        sky_quality: SkyQuality | None,
        inputs: ObservationConditionInputs | None = None,
    ) -> ConditionedTarget:
        return self.condition_target(
            target,
            self._pollution_inputs(sky_quality, inputs),
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
        condition_flags = target.condition_flags
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
                already_adjusted_flags.append(self.POLLUTION_CONTEXT_FLAG)
                diagnostic_notes.extend(self._sky_quality_diagnostics(inputs.sky_quality))
                diagnostic_notes.append("light_pollution:already_applied")
                if self.POLLUTION_CONTEXT_FLAG not in condition_flags:
                    condition_flags = (*condition_flags, self.POLLUTION_CONTEXT_FLAG)
            else:
                pollution_penalty = self.deep_sky_pollution_penalty(target, inputs.sky_quality)
                if pollution_penalty > 0:
                    applied_components.append(self.POLLUTION_CONTEXT_FLAG)
                diagnostic_notes.extend(self._sky_quality_diagnostics(inputs.sky_quality))
                score = max(0, round(score - pollution_penalty))
                urban_note = self.POLLUTION_CONTEXT_NOTE
                if urban_note not in notes:
                    notes = f"{urban_note} {target.notes}"
                visible = visible and score > 10
                if pollution_penalty > 0 and self.POLLUTION_CONTEXT_FLAG not in condition_flags:
                    condition_flags = (*condition_flags, self.POLLUTION_CONTEXT_FLAG)
        else:
            diagnostic_notes.append("light_pollution:not_requested")

        breakdown = self._breakdown(
            object_id=target.id,
            base_score=target.score,
            moon_penalty=moon_penalty,
            moon_geometry_factor=self.intended_moon_geometry_factor(inputs.moon_geometry),
            pollution_penalty=pollution_penalty,
            adjusted_score=score,
            applied_components=tuple(applied_components),
            diagnostic_notes=tuple(diagnostic_notes),
            already_adjusted_flags=tuple(already_adjusted_flags),
        )

        if (
            score == target.score
            and visible == target.visible
            and notes == target.notes
            and condition_flags == target.condition_flags
        ):
            return ConditionedTarget(target, breakdown, original_target=target)
        return ConditionedTarget(
            replace(
                target,
                score=score,
                score_label=ObservingScoreService.score_label(score),
                visible=visible,
                notes=notes,
                condition_flags=condition_flags,
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
        return cls.POLLUTION_CONTEXT_FLAG in target.condition_flags or cls.POLLUTION_CONTEXT_NOTE in target.notes

    @classmethod
    def moon_penalty(cls, target: CelestialObject, moon: MoonSummary | None) -> float:
        sensitivity = cls._moon_sensitivity(target)
        if sensitivity <= 0:
            return 0.0
        illumination = cls._moon_illumination(moon)
        illumination_factor = max(0.0, min(1.0, (illumination - 25.0) / 75.0))
        return sensitivity * illumination_factor

    @staticmethod
    def aod_freshness_weight(age_days: float | None = None, freshness_category: str | None = None) -> float:
        """Intended future NASA AOD confidence weight; score-neutral in 1.3.7a."""

        if age_days is not None:
            age = max(0.0, age_days)
            if age <= 3.0:
                return 1.0
            if age <= 7.0:
                return 0.5
            return 0.0
        category = ObservationConditionsService._freshness_category(freshness_category or "")
        return {
            "current": 1.0,
            "recent": 1.0,
            "stale": 0.5,
            "historical": 0.0,
        }.get(category, 0.0)

    @staticmethod
    def particulate_freshness_weight(age_days: float | None = None, freshness_category: str | None = None) -> float:
        """Intended future OpenAQ/PM confidence weight; score-neutral in 1.3.7a."""

        if age_days is not None:
            age = max(0.0, age_days)
            if age <= 1.0:
                return 1.0
            if age <= 3.0:
                return 0.7
            if age <= 7.0:
                return 0.3
            return 0.0
        category = ObservationConditionsService._freshness_category(freshness_category or "")
        return {
            "current": 1.0,
            "recent": 0.7,
            "stale": 0.3,
            "historical": 0.0,
        }.get(category, 0.0)

    @classmethod
    def atmospheric_sensitivity_profile(cls, target: CelestialObject) -> AtmosphericSensitivityProfile:
        """Return the intended future aerosol sensitivity without applying it."""

        lower_type = target.object_type.lower()
        if target.id == "moon" or "luna" in lower_type:
            return AtmosphericSensitivityProfile("moon", 0.05, 1.0)
        if target.object_type == "Pianeta" or target.id in cls.SOLAR_SYSTEM_IDS:
            return AtmosphericSensitivityProfile("planet", 0.15, 3.0)
        if "galaxy" in lower_type or "galassia" in lower_type:
            return AtmosphericSensitivityProfile("galaxy", 1.0, 12.0)
        if "diffuse" in lower_type:
            return AtmosphericSensitivityProfile("diffuse_nebula", 0.85, 8.0)
        if "planetary nebula" in lower_type or "nebulosa planetaria" in lower_type:
            return AtmosphericSensitivityProfile("planetary_nebula", 0.55, 5.0)
        if "nebula" in lower_type or "nebul" in lower_type:
            return AtmosphericSensitivityProfile("diffuse_nebula", 0.75, 8.0)
        if "globular" in lower_type or "ammasso globulare" in lower_type:
            return AtmosphericSensitivityProfile("globular_cluster", 0.45, 4.0)
        if "open" in lower_type or "cluster" in lower_type or "star cloud" in lower_type:
            return AtmosphericSensitivityProfile("open_cluster", 0.5, 3.0)
        return AtmosphericSensitivityProfile("general", 0.35, 4.0)

    @classmethod
    def aerosol_primary_source(
        cls,
        aod: AodConditionInput | None,
        particulate: ParticulateConditionInput | None,
    ) -> str:
        """AOD dominates PM; PM is fallback when AOD has no useful value."""

        aod_available = (
            aod is not None
            and aod.available
            and aod.aod_550 is not None
            and cls.aod_freshness_weight(aod.age_days, aod.freshness_category) > 0.0
        )
        particulate_available = (
            particulate is not None
            and particulate.available
            and (particulate.pm25 is not None or particulate.pm10 is not None)
            and cls.particulate_freshness_weight(particulate.age_days, particulate.freshness_category) > 0.0
        )
        if aod_available:
            return "aod"
        if particulate_available:
            return "particulate"
        return "none"

    @staticmethod
    def intended_aerosol_modifier(
        target: CelestialObject,
        aod: AodConditionInput | None,
        particulate: ParticulateConditionInput | None,
        feature_flags: ObservationConditionFeatureFlags | None = None,
    ) -> float:
        """Future scoring hook; intentionally neutral until an experimental flag is wired."""

        del target, aod, particulate
        flags = feature_flags or ObservationConditionFeatureFlags()
        if not flags.experimental_aerosol_scoring:
            return 0.0
        return 0.0

    @classmethod
    def intended_moon_geometry_factor(cls, geometry: MoonGeometryConditionInput | None) -> float:
        """Future Moon geometry factor used for diagnostics only in this milestone."""

        if geometry is None:
            return 1.0
        if geometry.moon_set_before_target_window is True:
            return 0.0
        altitude_factor = cls.moon_altitude_future_factor(geometry)
        separation_factor = cls.moon_separation_future_factor(geometry)
        return altitude_factor * separation_factor

    @staticmethod
    def moon_altitude_future_factor(geometry: MoonGeometryConditionInput | None) -> float:
        if geometry is None:
            return 1.0
        if geometry.moon_set_before_target_window is True:
            return 0.0
        if geometry.moon_visible_during_target_window is False or geometry.moon_above_horizon is False:
            return 0.0
        altitude = geometry.moon_altitude_deg
        if altitude is None:
            return 1.0
        if altitude <= 0.0:
            return 0.0
        if altitude < 10.0:
            return 0.25
        if altitude < 30.0:
            return 0.6
        return 1.0

    @staticmethod
    def moon_separation_future_factor(geometry: MoonGeometryConditionInput | None) -> float:
        if geometry is None or geometry.moon_target_separation_deg is None:
            return 1.0
        separation = max(0.0, geometry.moon_target_separation_deg)
        if separation < 20.0:
            return 1.35
        if separation < 45.0:
            return 1.0
        if separation < 90.0:
            return 0.65
        return 0.35

    @staticmethod
    def intended_moon_geometry_modifier(
        geometry: MoonGeometryConditionInput | None,
        feature_flags: ObservationConditionFeatureFlags | None = None,
    ) -> float:
        """Future scoring hook; intentionally neutral until an experimental flag is wired."""

        del geometry
        flags = feature_flags or ObservationConditionFeatureFlags()
        if not flags.experimental_moon_geometry_scoring:
            return 0.0
        return 0.0

    @staticmethod
    def _breakdown(
        *,
        object_id: str,
        base_score: int,
        moon_penalty: float = 0.0,
        moon_geometry_factor: float = 1.0,
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
            moon_geometry_factor=moon_geometry_factor,
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

    @staticmethod
    def _pollution_inputs(
        sky_quality: SkyQuality | None,
        inputs: ObservationConditionInputs | None,
    ) -> ObservationConditionInputs:
        if inputs is None:
            return ObservationConditionInputs(sky_quality=sky_quality)
        if inputs.sky_quality is None and sky_quality is not None:
            return replace(inputs, sky_quality=sky_quality)
        return inputs

    @classmethod
    def _neutral_condition_diagnostics(cls, inputs: ObservationConditionInputs) -> tuple[str, ...]:
        return (
            "weather:identity_placeholder",
            "seeing:identity_placeholder",
            "transparency:identity_placeholder",
            "equipment:identity_placeholder",
            *cls._aod_diagnostics(inputs.aod),
            *cls._particulate_diagnostics(inputs.particulate),
            *cls._moon_geometry_diagnostics(inputs.moon_geometry),
        )

    @classmethod
    def _moon_geometry_diagnostics(cls, geometry: MoonGeometryConditionInput | None) -> tuple[str, ...]:
        if geometry is None:
            return ("moon_geometry:identity_placeholder",)
        notes = ["moon_geometry:available"]
        if geometry.moon_altitude_deg is not None:
            notes.append(f"moon_geometry:altitude={geometry.moon_altitude_deg:g}")
        if geometry.moon_target_separation_deg is not None:
            notes.append(f"moon_geometry:separation={geometry.moon_target_separation_deg:g}")
        if geometry.moon_above_horizon is not None:
            notes.append(f"moon_geometry:above_horizon={str(geometry.moon_above_horizon).lower()}")
        if geometry.moon_visible_during_target_window is not None:
            notes.append(
                "moon_geometry:visible_during_window="
                f"{str(geometry.moon_visible_during_target_window).lower()}"
            )
        if geometry.moon_set_before_target_window is not None:
            notes.append(f"moon_geometry:set_before_window={str(geometry.moon_set_before_target_window).lower()}")
        notes.append(f"moon_geometry:future_factor={cls.intended_moon_geometry_factor(geometry):g}")
        notes.append("moon_geometry:score_neutral")
        return tuple(notes)

    @staticmethod
    def _aod_diagnostics(aod: AodConditionInput | None) -> tuple[str, ...]:
        if aod is None:
            return ("aod:identity_placeholder",)
        category = ObservationConditionsService._freshness_category(aod.freshness_category)
        notes = [f"aod:{category}"]
        notes.append("aod:available" if aod.available else f"aod:unavailable:{aod.status}")
        if aod.status:
            notes.append(f"aod:status={aod.status}")
        if aod.product:
            notes.append(f"aod:product={aod.product}")
        if aod.source:
            notes.append(f"aod:source={aod.source}")
        if aod.aod_550 is not None:
            notes.append(f"aod:550={aod.aod_550:g}")
            notes.append(f"aod:value={aod.aod_550:g}")
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
        if particulate.status:
            notes.append(f"particulate:status={particulate.status}")
        if particulate.source:
            notes.append(f"particulate:source={particulate.source}")
        if particulate.pm25 is not None:
            notes.append(f"pm25={particulate.pm25:g}")
            notes.append(f"particulate:pm25={particulate.pm25:g}")
        if particulate.pm10 is not None:
            notes.append(f"pm10={particulate.pm10:g}")
            notes.append(f"particulate:pm10={particulate.pm10:g}")
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
        if target.object_type == "Pianeta" or target.id in ObservationConditionsService.SOLAR_SYSTEM_IDS:
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
