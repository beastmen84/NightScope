from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from astro_viewer.app.models.imaging_recommendation import (
    ImagingRecommendationCandidate,
)


class ImagingVideoConfidence(StrEnum):
    """Planning confidence; it never changes photographic suitability."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImagingVideoFpsSource(StrEnum):
    """Provenance of the frame-rate range used for frame counts."""

    ACHIEVABLE = "achievable"
    CATALOG_MAXIMUM = "catalog_maximum"
    TARGET_GOAL = "target_goal"


@dataclass(frozen=True)
class ImagingVideoSessionConditions:
    """Optional facts supplied by a future runtime or user adapter."""

    achievable_fps: float | None = None
    seeing_score: int | None = None
    target_altitude_deg: float | None = None


@dataclass(frozen=True)
class ImagingVideoCaptureAdvice:
    """Conservative single-clip guidance for one video candidate."""

    candidate: ImagingRecommendationCandidate
    target_profile: str
    clip_duration_min_seconds: int
    clip_duration_max_seconds: int
    planned_fps_min: float
    planned_fps_max: float
    estimated_frame_count_min: int
    estimated_frame_count_max: int
    fps_source: ImagingVideoFpsSource
    confidence: ImagingVideoConfidence
    data_completeness: float
    missing_inputs: tuple[str, ...] = ()
    assumption_codes: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()
    limitation_codes: tuple[str, ...] = ()
    policy_version: str = "imaging_video_capture_v2"
