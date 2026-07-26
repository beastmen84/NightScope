from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from astro_viewer.app.models.imaging import (
    ImagingCamera,
    ImagingTrainConfiguration,
)


class ImagingCaptureMode(StrEnum):
    STILL = "still"
    VIDEO = "video"


class ImagingTargetClass(StrEnum):
    SUN = "sun"
    MOON = "moon"
    PLANET = "planet"
    COMET = "comet"
    GALAXY = "galaxy"
    DIFFUSE_NEBULA = "diffuse_nebula"
    PLANETARY_NEBULA = "planetary_nebula"
    OPEN_CLUSTER = "open_cluster"
    GLOBULAR_CLUSTER = "globular_cluster"
    STELLAR = "stellar"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ImagingTargetTraits:
    """Photographic target facts without observing-condition or UI state."""

    target_id: str
    name: str
    target_class: ImagingTargetClass
    recommended_capture_mode: ImagingCaptureMode | None
    magnitude: float | None
    angular_size_major_deg: float | None
    angular_size_minor_deg: float | None
    surface_brightness_proxy: float | None
    reducer_preferred: bool
    recommendation_supported: bool = True
    unsupported_reason_code: str = ""

    @property
    def has_known_angular_size(self) -> bool:
        return (
            self.angular_size_major_deg is not None
            and self.angular_size_minor_deg is not None
        )

    @property
    def is_extended(self) -> bool:
        if self.angular_size_major_deg is not None:
            return self.angular_size_major_deg >= 0.5
        return self.target_class in {
                ImagingTargetClass.COMET,
                ImagingTargetClass.DIFFUSE_NEBULA,
                ImagingTargetClass.OPEN_CLUSTER,
        }

    @property
    def is_compact(self) -> bool:
        return (
            self.target_class
            in {
                ImagingTargetClass.PLANET,
                ImagingTargetClass.PLANETARY_NEBULA,
                ImagingTargetClass.GLOBULAR_CLUSTER,
                ImagingTargetClass.STELLAR,
            }
            or (
                self.angular_size_major_deg is not None
                and self.angular_size_major_deg <= 0.15
            )
        )


@dataclass(frozen=True)
class ImagingScoreComponent:
    name: str
    value: float
    weight: float

    @property
    def weighted_points(self) -> float:
        return self.value * self.weight


@dataclass(frozen=True)
class ImagingRecommendationCandidate:
    """One scored photographic train; confidence never modifies its score."""

    target: ImagingTargetTraits
    configuration: ImagingTrainConfiguration
    capture_mode: ImagingCaptureMode
    components: tuple[ImagingScoreComponent, ...]
    score: float
    data_completeness: float
    missing_inputs: tuple[str, ...] = ()

    @property
    def candidate_id(self) -> str:
        return (
            f"imaging-target:{self.target.target_id}:"
            f"mode:{self.capture_mode.value}:"
            f"{self.configuration.configuration_id}"
        )

    @property
    def camera(self) -> ImagingCamera:
        return self.configuration.camera

    def component_values(self) -> dict[str, float]:
        return {
            component.name: component.value
            for component in self.components
        }

    def component_points(self) -> dict[str, float]:
        return {
            component.name: component.weighted_points
            for component in self.components
        }
