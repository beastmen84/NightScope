from __future__ import annotations

import math

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import ObserverCapability
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_observer_capability_profile_from_recommendation,
)


def build_observer_capability_for_target(
    item: CelestialObject,
    *,
    telescope: Telescope,
    context_note: str = "nsom:observer_capability",
) -> ObserverCapability:
    """Build the Observer-owned capability profile from runtime target/setup data."""

    base = build_observer_capability_profile_from_recommendation(item)
    aperture = _unit_from_range(telescope.aperture_mm, lower=50.0, upper=250.0)
    focal_length = _unit_from_range(telescope.focal_length_mm, lower=350.0, upper=2000.0)
    field_width = 1.0 - (0.75 * focal_length)
    tracking = max(base.tracking_or_goto, _tracking_capability(telescope.mount))
    return ObserverCapability(
        light_grasp=_clamp_unit((base.light_grasp + aperture) / 2.0),
        resolution=_clamp_unit((base.resolution + aperture) / 2.0),
        field_of_view=_clamp_unit((base.field_of_view + field_width) / 2.0),
        magnification_range=_clamp_unit((base.magnification_range + focal_length) / 2.0),
        tracking_or_goto=tracking,
        automation_or_eaa=base.automation_or_eaa,
        filters=base.filters,
        experience_level=base.experience_level,
        observing_style=base.observing_style,
        practical_comfort=base.practical_comfort,
        notes=(
            *base.notes,
            context_note,
            f"telescope={telescope.name}",
            f"aperture_mm={telescope.aperture_mm}",
            f"focal_length_mm={telescope.focal_length_mm}",
        ),
    )


def _unit_from_range(value: object, *, lower: float, upper: float) -> float:
    number = _finite_float(value, default=lower)
    if upper <= lower:
        return 0.0
    return _clamp_unit((number - lower) / (upper - lower))


def _finite_float(value: object, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _clamp_unit(value: object) -> float:
    return max(0.0, min(1.0, _finite_float(value, default=0.0)))


def _tracking_capability(value: object) -> float:
    text = str(value).lower()
    if any(token in text for token in ("goto", "go-to", "computer", "eq", "tracking", "motoriz")):
        return 0.8
    if any(token in text for token in ("dob", "altaz", "manual")):
        return 0.2
    return 0.4
