from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping


class NsomTargetClass(Enum):
    """NSOM 1.0 target classes used for future observing-condition modeling."""

    MOON = "moon"
    PLANET = "planet"
    GLOBULAR_CLUSTER = "globular_cluster"
    OPEN_CLUSTER = "open_cluster"
    PLANETARY_NEBULA = "planetary_nebula"
    DIFFUSE_NEBULA = "diffuse_nebula"
    GALAXY = "galaxy"


@dataclass(frozen=True)
class NsomTargetClassProfile:
    target_class: NsomTargetClass
    label: str
    aod_sensitivity: str
    pm_role: str
    max_aod_pm_influence: float
    max_moon_influence: float
    max_sky_background_influence: float
    max_total_visibility_influence: float


NSOM_TARGET_CLASS_PROFILES: Mapping[NsomTargetClass, NsomTargetClassProfile] = MappingProxyType(
    {
        NsomTargetClass.MOON: NsomTargetClassProfile(
            target_class=NsomTargetClass.MOON,
            label="Moon",
            aod_sensitivity="very low",
            pm_role="none",
            max_aod_pm_influence=1.0,
            max_moon_influence=0.0,
            max_sky_background_influence=0.0,
            max_total_visibility_influence=5.0,
        ),
        NsomTargetClass.PLANET: NsomTargetClassProfile(
            target_class=NsomTargetClass.PLANET,
            label="Planets",
            aod_sensitivity="low",
            pm_role="none/minor",
            max_aod_pm_influence=3.0,
            max_moon_influence=0.0,
            max_sky_background_influence=0.0,
            max_total_visibility_influence=18.0,
        ),
        NsomTargetClass.GLOBULAR_CLUSTER: NsomTargetClassProfile(
            target_class=NsomTargetClass.GLOBULAR_CLUSTER,
            label="Globular clusters",
            aod_sensitivity="medium-low",
            pm_role="low fallback",
            max_aod_pm_influence=4.0,
            max_moon_influence=18.0,
            max_sky_background_influence=18.0,
            max_total_visibility_influence=35.0,
        ),
        NsomTargetClass.OPEN_CLUSTER: NsomTargetClassProfile(
            target_class=NsomTargetClass.OPEN_CLUSTER,
            label="Open clusters",
            aod_sensitivity="medium-low",
            pm_role="low/medium fallback",
            max_aod_pm_influence=3.0,
            max_moon_influence=10.0,
            max_sky_background_influence=12.0,
            max_total_visibility_influence=25.0,
        ),
        NsomTargetClass.PLANETARY_NEBULA: NsomTargetClassProfile(
            target_class=NsomTargetClass.PLANETARY_NEBULA,
            label="Planetary nebulae",
            aod_sensitivity="medium",
            pm_role="medium fallback",
            max_aod_pm_influence=5.0,
            max_moon_influence=18.0,
            max_sky_background_influence=22.0,
            max_total_visibility_influence=38.0,
        ),
        NsomTargetClass.DIFFUSE_NEBULA: NsomTargetClassProfile(
            target_class=NsomTargetClass.DIFFUSE_NEBULA,
            label="Diffuse nebulae",
            aod_sensitivity="high",
            pm_role="medium-high fallback",
            max_aod_pm_influence=8.0,
            max_moon_influence=35.0,
            max_sky_background_influence=30.0,
            max_total_visibility_influence=55.0,
        ),
        NsomTargetClass.GALAXY: NsomTargetClassProfile(
            target_class=NsomTargetClass.GALAXY,
            label="Galaxies",
            aod_sensitivity="very high",
            pm_role="high fallback",
            max_aod_pm_influence=12.0,
            max_moon_influence=40.0,
            max_sky_background_influence=35.0,
            max_total_visibility_influence=60.0,
        ),
    }
)


def _clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


@dataclass(frozen=True)
class EffectiveObservability:
    """Objective fraction of intrinsic target quality observable under the sky."""

    value: float
    geometric_visibility: float = 1.0
    lunar_sky_background: float = 1.0
    static_sky_background: float = 1.0
    atmospheric_transparency: float = 1.0
    horizon_context: float = 1.0
    notes: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_components(
        cls,
        *,
        geometric_visibility: float = 1.0,
        lunar_sky_background: float = 1.0,
        static_sky_background: float = 1.0,
        atmospheric_transparency: float = 1.0,
        horizon_context: float = 1.0,
        notes: tuple[str, ...] = (),
    ) -> EffectiveObservability:
        components = (
            _clamp_unit(geometric_visibility),
            _clamp_unit(lunar_sky_background),
            _clamp_unit(static_sky_background),
            _clamp_unit(atmospheric_transparency),
            _clamp_unit(horizon_context),
        )
        value = 1.0
        for component in components:
            value *= component
        return cls(
            value=value,
            geometric_visibility=components[0],
            lunar_sky_background=components[1],
            static_sky_background=components[2],
            atmospheric_transparency=components[3],
            horizon_context=components[4],
            notes=tuple(notes),
        )


@dataclass(frozen=True)
class ObservableTargetValue:
    """Target value after intrinsic quality meets the observation environment."""

    intrinsic_target_quality: float
    effective_observability: EffectiveObservability
    value: float
    target_class: NsomTargetClass | None = None

    @classmethod
    def from_intrinsic(
        cls,
        *,
        intrinsic_target_quality: float,
        effective_observability: EffectiveObservability,
        target_class: NsomTargetClass | None = None,
    ) -> ObservableTargetValue:
        intrinsic = _clamp_score(intrinsic_target_quality)
        return cls(
            intrinsic_target_quality=intrinsic,
            effective_observability=effective_observability,
            value=_clamp_score(intrinsic * _clamp_unit(effective_observability.value)),
            target_class=target_class,
        )


@dataclass(frozen=True)
class ObserverCapabilityProfile:
    """Multidimensional capability profile for a specific observer."""

    light_grasp: float = 1.0
    resolution: float = 1.0
    field_of_view: float = 1.0
    magnification_range: float = 1.0
    tracking_or_goto: float = 1.0
    automation_or_eaa: float = 0.0
    filters: tuple[str, ...] = field(default_factory=tuple)
    experience_level: float = 1.0
    observing_style: str = "visual"
    practical_comfort: float = 1.0
    notes: tuple[str, ...] = field(default_factory=tuple)

    def summary_for_planning(self, weights: Mapping[str, float] | None = None) -> float:
        dimensions = {
            "light_grasp": _clamp_unit(self.light_grasp),
            "resolution": _clamp_unit(self.resolution),
            "field_of_view": _clamp_unit(self.field_of_view),
            "magnification_range": _clamp_unit(self.magnification_range),
            "tracking_or_goto": _clamp_unit(self.tracking_or_goto),
            "experience_level": _clamp_unit(self.experience_level),
            "practical_comfort": _clamp_unit(self.practical_comfort),
        }
        if not weights:
            return sum(dimensions.values()) / len(dimensions)

        weighted_total = 0.0
        weight_sum = 0.0
        for name, value in dimensions.items():
            weight = max(0.0, float(weights.get(name, 0.0)))
            weighted_total += value * weight
            weight_sum += weight
        if weight_sum <= 0.0:
            return sum(dimensions.values()) / len(dimensions)
        return _clamp_unit(weighted_total / weight_sum)


@dataclass(frozen=True)
class PracticalTargetValue:
    """Value a specific observer can realistically exploit."""

    observable_target_value: ObservableTargetValue
    observer_capability: ObserverCapabilityProfile
    observer_capability_summary: float
    value: float

    @classmethod
    def from_observable(
        cls,
        *,
        observable_target_value: ObservableTargetValue,
        observer_capability: ObserverCapabilityProfile,
        capability_summary: float | None = None,
    ) -> PracticalTargetValue:
        summary = (
            observer_capability.summary_for_planning()
            if capability_summary is None
            else _clamp_unit(capability_summary)
        )
        return cls(
            observable_target_value=observable_target_value,
            observer_capability=observer_capability,
            observer_capability_summary=summary,
            value=_clamp_score(observable_target_value.value * summary),
        )


@dataclass(frozen=True)
class RecommendationConfidence:
    """Parallel confidence dimension; it does not modify target value."""

    weather_confidence: float | None = None
    aod_confidence: float | None = None
    openaq_confidence: float | None = None
    viirs_confidence: float | None = None
    moon_geometry_confidence: float | None = None
    provider_fallback_confidence: float | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def value(self) -> float | None:
        components = [
            component
            for component in (
                self.weather_confidence,
                self.aod_confidence,
                self.openaq_confidence,
                self.viirs_confidence,
                self.moon_geometry_confidence,
                self.provider_fallback_confidence,
            )
            if component is not None
        ]
        if not components:
            return None
        return sum(_clamp_unit(component) for component in components) / len(components)


@dataclass(frozen=True)
class ObservationOpportunity:
    """Concrete planning candidate built from target, observer, time and session."""

    practical_target_value: PracticalTargetValue
    observing_window_quality: float = 1.0
    chronology_fit: float = 1.0
    session_viability: float = 1.0
    practical_constraints: float = 1.0
    confidence: RecommendationConfidence | None = None
    context: tuple[str, ...] = field(default_factory=tuple)

    @property
    def value(self) -> float:
        return _clamp_score(
            self.practical_target_value.value
            * _clamp_unit(self.observing_window_quality)
            * _clamp_unit(self.chronology_fit)
            * _clamp_unit(self.session_viability)
            * _clamp_unit(self.practical_constraints)
        )
