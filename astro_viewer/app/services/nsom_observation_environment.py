from __future__ import annotations

import math
import re

from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    NSOM_TARGET_CLASS_PROFILES,
    NsomTargetClass,
    ObservableTargetValue,
    ObservationEnvironment,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.nsom_target import build_intrinsic_target_quality
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionInputs,
    ObservationConditionsService,
)


class NsomObservationEnvironmentService:
    """Build the canonical Sky layer from primitive runtime condition inputs."""

    def environment(
        self,
        target: CelestialObject,
        inputs: ObservationConditionInputs,
    ) -> ObservationEnvironment:
        intrinsic = build_intrinsic_target_quality(target)
        target_class = intrinsic.target_class
        moon_background = self._moon_background_factor(target_class, inputs)
        sky_background = self._static_sky_background_factor(target_class, inputs)
        atmospheric, atmosphere_source, atmosphere_notes = self._atmospheric_factor(
            target,
            target_class,
            inputs,
        )
        horizon_context = self._horizon_context(target)
        target_class_name = target_class.value if target_class is not None else "unknown"
        sky_quality = inputs.sky_quality
        seeing = inputs.seeing
        return ObservationEnvironment.from_components(
            geometric_visibility=1.0 if target.visible else 0.0,
            lunar_sky_background=moon_background,
            static_sky_background=sky_background,
            atmospheric_transparency=atmospheric,
            horizon_context=horizon_context,
            sky_quality_source=getattr(sky_quality, "source", "") if sky_quality else "",
            weather_source=getattr(seeing, "source", "") if seeing else "",
            atmosphere_source=atmosphere_source,
            notes=(
                "nsom:canonical_observation_environment",
                f"target_class={target_class_name}",
                f"moon_background_factor={moon_background:.5f}",
                "moon_geometry_scoring_enabled="
                f"{inputs.feature_flags.experimental_moon_geometry_scoring}",
                "moon_geometry_input="
                f"{'available' if inputs.moon_geometry is not None else 'missing'}",
                f"static_sky_background_factor={sky_background:.5f}",
                f"atmospheric_transparency_factor={atmospheric:.5f}",
                f"horizon_context={horizon_context:.5f}",
                *atmosphere_notes,
            ),
        )

    def effective_observability(
        self,
        target: CelestialObject,
        inputs: ObservationConditionInputs,
    ) -> EffectiveObservability:
        return EffectiveObservability.from_environment(self.environment(target, inputs))

    def observable_target_value(
        self,
        target: CelestialObject,
        inputs: ObservationConditionInputs,
    ) -> ObservableTargetValue:
        intrinsic = build_intrinsic_target_quality(target)
        return ObservableTargetValue.from_intrinsic(
            intrinsic_target_quality=intrinsic,
            effective_observability=self.effective_observability(target, inputs),
            target_class=intrinsic.target_class,
        )

    @staticmethod
    def _moon_background_factor(
        target_class: NsomTargetClass | None,
        inputs: ObservationConditionInputs,
    ) -> float:
        profile = NSOM_TARGET_CLASS_PROFILES.get(target_class) if target_class else None
        if inputs.moon is None or profile is None:
            return 1.0
        max_influence = _clamp_unit(profile.max_moon_influence / 100.0)
        if max_influence <= 0.0:
            return 1.0
        illumination = _unit_from_percentage_text(inputs.moon.illumination)
        geometry_factor = (
            ObservationConditionsService.intended_moon_geometry_factor(inputs.moon_geometry)
            if inputs.feature_flags.experimental_moon_geometry_scoring
            else 1.0
        )
        severity = _clamp_unit(((illumination - 0.2) / 0.8) * geometry_factor)
        return _clamp_unit(1.0 - (severity * max_influence))

    @staticmethod
    def _static_sky_background_factor(
        target_class: NsomTargetClass | None,
        inputs: ObservationConditionInputs,
    ) -> float:
        profile = NSOM_TARGET_CLASS_PROFILES.get(target_class) if target_class else None
        sky_quality = inputs.sky_quality
        if profile is None or sky_quality is None:
            return 1.0
        max_influence = _clamp_unit(profile.max_sky_background_influence / 100.0)
        if max_influence <= 0.0:
            return 1.0

        radiance = getattr(sky_quality, "viirs_radiance", None)
        if radiance is not None:
            severity = _clamp_unit(math.log10(max(0.0, _finite_float(radiance)) + 1.0) / 3.0)
        else:
            severity = _clamp_unit((_finite_float(sky_quality.bortle_class, default=4.0) - 3.0) / 6.0)
        return _clamp_unit(1.0 - (severity * max_influence))

    @staticmethod
    def _atmospheric_factor(
        target: CelestialObject,
        target_class: NsomTargetClass | None,
        inputs: ObservationConditionInputs,
    ) -> tuple[float, str, tuple[str, ...]]:
        seeing = inputs.seeing
        if seeing is None:
            base_factor = 1.0
            seeing_notes = ("atmosphere:seeing_unavailable_neutral",)
        else:
            seeing_factor = _unit_from_score(seeing.seeing_score)
            atmospheric_score = seeing.atmospheric_transparency_score
            if atmospheric_score is None:
                atmospheric_score = seeing.transparency_score
                fallback_note = "atmosphere:legacy_transparency_fallback"
            else:
                fallback_note = "atmosphere:static_sky_excluded"
            transparency_factor = _unit_from_score(atmospheric_score)
            seeing_weight = (
                0.65
                if target_class
                in {NsomTargetClass.MOON, NsomTargetClass.PLANET, NsomTargetClass.DOUBLE_STAR}
                else 0.15
            )
            base_factor = (seeing_factor * seeing_weight) + (
                transparency_factor * (1.0 - seeing_weight)
            )
            seeing_notes = (
                f"atmosphere:seeing_weight={seeing_weight:.2f}",
                f"atmosphere:seeing_factor={seeing_factor:.5f}",
                f"atmosphere:weather_transparency_factor={transparency_factor:.5f}",
                fallback_note,
            )

        aerosol = ObservationConditionsService.experimental_aerosol_scoring_breakdown(
            target,
            inputs.aod,
            inputs.particulate,
            inputs.feature_flags,
        )
        factor = _clamp_unit(base_factor * aerosol.atmospheric_transparency_factor)
        source = getattr(seeing, "source", "") if seeing else ""
        if aerosol.primary_source == "aod" and inputs.aod is not None:
            source = inputs.aod.source or source
        elif aerosol.primary_source == "particulate" and inputs.particulate is not None:
            source = inputs.particulate.source or source
        return (
            factor,
            source,
            (
                *seeing_notes,
                f"aerosol:source={aerosol.primary_source}",
                f"aerosol:factor={aerosol.atmospheric_transparency_factor:.5f}",
            ),
        )

    @staticmethod
    def _horizon_context(target: CelestialObject) -> float:
        altitude = _first_number(target.max_altitude)
        if altitude is None:
            return 1.0 if target.visible else 0.0
        return _clamp_unit((altitude - 5.0) / 35.0)


def _unit_from_percentage_text(value: object) -> float:
    number = _first_number(value)
    return _clamp_unit((number or 0.0) / 100.0)


def _unit_from_score(value: object) -> float:
    return _clamp_unit(_finite_float(value) / 100.0)


def _first_number(value: object) -> float | None:
    match = re.search(r"-?\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    return _finite_float(match.group(0).replace(",", "."))


def _finite_float(value: object, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _clamp_unit(value: object) -> float:
    return max(0.0, min(1.0, _finite_float(value)))
