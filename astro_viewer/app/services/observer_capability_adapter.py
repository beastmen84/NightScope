from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, replace
from types import MappingProxyType

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import (
    NsomTargetClass,
    ObserverCapability,
    observer_capability_weight_profile_for_target,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observation_configuration import ObservationConfiguration
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.recommendation_candidate import RecommendationCandidate
from astro_viewer.app.services.nsom_runtime_builders import (
    build_observer_capability_profile_from_recommendation,
)
from astro_viewer.app.services.equipment_taxonomy import mount_tracking_capability


@dataclass(frozen=True)
class ObserverCapabilityProjection:
    """Observer-layer projection from an equipment configuration to Q_target."""

    observer_capability: ObserverCapability
    target_class: NsomTargetClass | str | None
    summary_for_planning: float
    q_target: float
    target_class_weighting_profile: Mapping[str, float]
    derivation: str = "configuration_derived_adapter"


def build_observer_capability_for_target(
    item: CelestialObject,
    *,
    telescope: Telescope,
    context_note: str = "nsom:observer_capability",
) -> ObserverCapability:
    """Build the Observer-owned capability profile from runtime target/setup data."""

    base = build_observer_capability_profile_from_recommendation(item)
    setup_type = (item.recommended_setup_type or "").strip().lower().replace("-", "_")
    if setup_type in {"binocular", "naked_eye", "nakedeye"}:
        return replace(
            base,
            notes=(
                *base.notes,
                context_note,
                f"equipment_type={setup_type}",
                "adapter:recommended_non_telescope_setup",
            ),
        )
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


def build_observer_capability_from_candidate(
    candidate: RecommendationCandidate,
    *,
    context_note: str = "nsom:equipment_observer_capability",
) -> ObserverCapability:
    """Build ObserverCapability from a concrete EquipmentService candidate."""

    return build_observer_capability_from_configuration(
        candidate.configuration,
        context_note=context_note,
    )


def build_observer_capability_from_configuration(
    configuration: ObservationConfiguration,
    *,
    context_note: str = "nsom:equipment_observer_capability",
) -> ObserverCapability:
    """Project a concrete observation configuration into Observer-owned capability.

    The adapter intentionally uses configuration/equipment inputs only. Sky
    quality, seeing and confidence must stay outside ObserverCapability.
    """

    objective = _configuration_objective_mm(configuration)
    true_field = configuration.true_field_of_view_deg
    if configuration.binocular:
        binocular = configuration.binocular
        tracking = 0.35 if binocular.image_stabilized else 0.15
        practical_comfort = _binocular_comfort(configuration.magnification, binocular.image_stabilized)
        field_of_view = 0.78 if configuration.magnification <= 12.0 else 0.55
        notes = (
            context_note,
            "adapter:configuration_derived",
            f"binocular={binocular.name}",
            f"magnification={configuration.magnification:.1f}",
        )
    else:
        telescope = configuration.telescope
        tracking = _tracking_capability(telescope.mount if telescope else "")
        practical_comfort = _telescope_comfort(configuration)
        field_of_view = _clamp_unit((true_field or 0.0) / 3.0)
        notes = (
            context_note,
            "adapter:configuration_derived",
            f"telescope={telescope.name if telescope else ''}",
            f"magnification={configuration.magnification:.1f}",
            f"true_field={true_field:.3f}" if true_field is not None else "true_field=unavailable",
        )

    return ObserverCapability(
        light_grasp=_unit_from_range(objective, lower=35.0, upper=250.0),
        resolution=_unit_from_range(objective, lower=50.0, upper=250.0),
        field_of_view=field_of_view,
        magnification_range=_clamp_unit(configuration.magnification / 180.0),
        tracking_or_goto=tracking,
        automation_or_eaa=0.0,
        filters=(),
        experience_level=0.75,
        observing_style="visual",
        practical_comfort=practical_comfort,
        notes=notes,
    )


def build_observer_capability_projection_from_candidate(
    candidate: RecommendationCandidate,
    target_class: NsomTargetClass | str | None,
    *,
    context_note: str = "nsom:equipment_observer_capability",
) -> ObserverCapabilityProjection:
    """Build ObserverCapability plus the target-specific Q_target projection."""

    observer = build_observer_capability_from_candidate(candidate, context_note=context_note)
    return project_observer_capability_profile(observer, target_class)


def project_observer_capability_profile(
    observer_capability: ObserverCapability,
    target_class: NsomTargetClass | str | None,
) -> ObserverCapabilityProjection:
    """Project an existing ObserverCapability profile to summary and Q_target."""

    return ObserverCapabilityProjection(
        observer_capability=observer_capability,
        target_class=target_class,
        summary_for_planning=observer_capability.summary_for_planning(),
        q_target=project_observer_capability_for_target(observer_capability, target_class),
        target_class_weighting_profile=MappingProxyType(
            dict(observer_capability_weight_profile_for_target(target_class))
        ),
    )


def _configuration_objective_mm(configuration: ObservationConfiguration) -> float:
    if configuration.telescope:
        return float(configuration.telescope.aperture_mm)
    if configuration.binocular:
        return float(configuration.binocular.objective_diameter_mm)
    return 7.0


def _telescope_comfort(configuration: ObservationConfiguration) -> float:
    comfort = 0.82
    if configuration.barlow:
        comfort -= 0.18
    if configuration.magnification > 180.0:
        comfort -= 0.22
    elif configuration.magnification > 120.0:
        comfort -= 0.10
    if configuration.exit_pupil_mm < 0.5:
        comfort -= 0.20
    return _clamp_unit(comfort)


def _binocular_comfort(magnification: float, image_stabilized: bool) -> float:
    if magnification <= 10.0:
        comfort = 0.92
    elif magnification <= 12.0:
        comfort = 0.80
    elif magnification <= 15.0:
        comfort = 0.62
    else:
        comfort = 0.42
    if image_stabilized:
        comfort += 0.18
    return _clamp_unit(comfort)


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
    return mount_tracking_capability(value)
