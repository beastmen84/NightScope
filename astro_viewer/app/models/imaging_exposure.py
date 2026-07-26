from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from astro_viewer.app.models.imaging_recommendation import (
    ImagingRecommendationCandidate,
)


class ImagingExposureConfidence(StrEnum):
    """Planning confidence; it never changes photographic suitability."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ImagingSessionConditions:
    """Photographic session facts supplied by a future runtime adapter."""

    sky_brightness_mag_arcsec2: float | None = None
    bortle_class: int | None = None
    transparency_score: int | None = None
    target_current_altitude_deg: float | None = None
    target_maximum_altitude_deg: float | None = None
    moon_illumination_fraction: float | None = None
    moon_altitude_deg: float | None = None
    moon_target_separation_deg: float | None = None
    moon_visible_during_target_window: bool | None = None


@dataclass(frozen=True)
class ImagingExposureFactor:
    """One inspectable multiplier used by the exposure-planning policy."""

    name: str
    sub_exposure_multiplier: float = 1.0
    total_integration_multiplier: float = 1.0


@dataclass(frozen=True)
class ImagingExposureAdvice:
    """Conservative broadband stacking ranges for one still candidate."""

    candidate: ImagingRecommendationCandidate
    sub_exposure_min_seconds: float
    sub_exposure_max_seconds: float
    total_integration_min_minutes: int
    total_integration_max_minutes: int
    estimated_frame_count_min: int
    estimated_frame_count_max: int
    tracking_limit_seconds: float
    factors: tuple[ImagingExposureFactor, ...]
    confidence: ImagingExposureConfidence
    data_completeness: float
    total_integration_min_is_lower_bound: bool = False
    total_integration_max_is_lower_bound: bool = False
    missing_inputs: tuple[str, ...] = ()
    assumption_codes: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()
    limitation_codes: tuple[str, ...] = ()
    policy_version: str = "imaging_exposure_v2"

    def factor_values(self) -> dict[str, tuple[float, float]]:
        return {
            factor.name: (
                factor.sub_exposure_multiplier,
                factor.total_integration_multiplier,
            )
            for factor in self.factors
        }
