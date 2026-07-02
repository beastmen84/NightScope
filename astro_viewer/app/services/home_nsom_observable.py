from __future__ import annotations

import math

from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    IntrinsicTargetQuality,
    NSOM_TARGET_CLASS_PROFILES,
    NsomTargetClass,
    ObservableTargetValue,
    ObservationEnvironment,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.nsom_diagnostic_adapters import build_intrinsic_target_quality


def build_home_observable_target_value(
    item: CelestialObject,
    *,
    sky_quality: SkyQuality,
    moon: MoonSummary | None,
) -> ObservableTargetValue:
    intrinsic = build_intrinsic_target_quality(item)
    environment = build_home_observation_environment(item, intrinsic, sky_quality=sky_quality, moon=moon)
    effective = EffectiveObservability.from_environment(environment)
    return ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=intrinsic,
        effective_observability=effective,
        target_class=intrinsic.target_class,
    )


def build_home_observation_environment(
    item: CelestialObject,
    intrinsic: IntrinsicTargetQuality,
    *,
    sky_quality: SkyQuality,
    moon: MoonSummary | None,
) -> ObservationEnvironment:
    moon_background = _moon_background_factor(intrinsic.target_class, moon)
    sky_background = _sky_background_factor(intrinsic.target_class, sky_quality)
    horizon_context = _horizon_context(item)
    return ObservationEnvironment.from_components(
        geometric_visibility=1.0 if item.visible else 0.0,
        lunar_sky_background=moon_background,
        static_sky_background=sky_background,
        atmospheric_transparency=1.0,
        horizon_context=horizon_context,
        sky_quality_source=sky_quality.source,
        notes=(
            "nsom:home_observable",
            "home:session_weather_excluded",
            "home:observer_equipment_excluded",
            "home:atmospheric_transparency_unavailable",
            f"target_class={intrinsic.target_class.value if intrinsic.target_class else 'unknown'}",
            f"moon_background_factor={moon_background:.3f}",
            f"sky_background_factor={sky_background:.3f}",
            f"horizon_context={horizon_context:.3f}",
        ),
    )


def _moon_background_factor(target_class: NsomTargetClass | None, moon: MoonSummary | None) -> float:
    profile = NSOM_TARGET_CLASS_PROFILES.get(target_class) if target_class else None
    if moon is None or profile is None:
        return 1.0
    max_influence = _clamp_unit(profile.max_moon_influence / 100.0)
    if max_influence <= 0.0:
        return 1.0
    illumination = _unit_from_percentage_text(getattr(moon, "illumination", ""))
    severity = _clamp_unit((illumination - 0.2) / 0.8)
    return _clamp_unit(1.0 - (severity * max_influence))


def _sky_background_factor(target_class: NsomTargetClass | None, sky_quality: SkyQuality) -> float:
    profile = NSOM_TARGET_CLASS_PROFILES.get(target_class) if target_class else None
    if profile is None:
        return 1.0
    max_influence = _clamp_unit(profile.max_sky_background_influence / 100.0)
    if max_influence <= 0.0:
        return 1.0

    radiance = getattr(sky_quality, "viirs_radiance", None)
    if radiance is not None:
        radiance_value = max(0.0, _finite_float(radiance, default=0.0))
        severity = _clamp_unit(math.log10(radiance_value + 1.0) / 3.0)
    else:
        bortle = _finite_float(getattr(sky_quality, "bortle_class", None), default=4.0)
        severity = _clamp_unit((bortle - 3.0) / 6.0)
    return _clamp_unit(1.0 - (severity * max_influence))


def _horizon_context(item: CelestialObject) -> float:
    altitude = _first_number(getattr(item, "max_altitude", ""))
    if altitude is None:
        return 1.0 if item.visible else 0.0
    return _clamp_unit((altitude - 5.0) / 35.0)


def _unit_from_percentage_text(value: str) -> float:
    cleaned = value.strip().replace("%", "")
    try:
        number = float(cleaned)
    except ValueError:
        return 0.5
    return _clamp_unit(number / 100.0)


def _first_number(value: str) -> float | None:
    match = None
    for candidate in value.replace(",", ".").split():
        try:
            return float(candidate)
        except ValueError:
            continue
    return match


def _finite_float(value: object, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _clamp_unit(value: object) -> float:
    return max(0.0, min(1.0, _finite_float(value)))
