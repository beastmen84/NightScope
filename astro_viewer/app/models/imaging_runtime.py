from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from astro_viewer.app.models.equipment import Barlow, FocalReducer, Telescope
from astro_viewer.app.models.imaging import ImagingCamera
from astro_viewer.app.models.imaging_exposure import (
    ImagingExposureAdvice,
    ImagingSessionConditions,
)
from astro_viewer.app.models.imaging_recommendation import (
    ImagingCaptureMode,
    ImagingRecommendationCandidate,
)
from astro_viewer.app.models.imaging_video_capture import (
    ImagingVideoCaptureAdvice,
    ImagingVideoSessionConditions,
)


IMAGING_RUNTIME_POLICY_VERSION = "imaging_runtime_v1"


class ImagingRuntimeStatus(StrEnum):
    """Stable backend states for the later photographic presentation layer."""

    READY = "ready"
    NO_ACTIVE_PROFILE = "no_active_profile"
    NO_TELESCOPES = "no_telescopes"
    NO_CAMERAS = "no_cameras"
    NO_VALID_CONFIGURATIONS = "no_valid_configurations"
    TARGET_UNSUPPORTED = "target_unsupported"
    ADVICE_UNAVAILABLE = "advice_unavailable"


@dataclass(frozen=True)
class ImagingRuntimeInventory:
    """One immutable snapshot of the active profile's photographic inventory."""

    profile_id: str = ""
    telescopes: tuple[Telescope, ...] = ()
    cameras: tuple[ImagingCamera, ...] = ()
    reducers: tuple[FocalReducer, ...] = ()
    barlows: tuple[Barlow, ...] = ()
    full_aperture_solar_filter_telescope_ids: tuple[str, ...] = ()

    @property
    def has_active_profile(self) -> bool:
        return bool(self.profile_id.strip())


@dataclass(frozen=True)
class ImagingRuntimeConditions:
    """Current condition snapshots for the mutually exclusive advisors."""

    still: ImagingSessionConditions = field(
        default_factory=ImagingSessionConditions
    )
    video: ImagingVideoSessionConditions = field(
        default_factory=ImagingVideoSessionConditions
    )


@dataclass(frozen=True)
class ImagingRuntimeRecommendation:
    """Best photographic candidate plus exactly one mode-specific plan."""

    target_id: str
    profile_id: str
    status: ImagingRuntimeStatus
    configuration_count: int = 0
    candidate_count: int = 0
    candidate: ImagingRecommendationCandidate | None = None
    exposure_advice: ImagingExposureAdvice | None = None
    video_advice: ImagingVideoCaptureAdvice | None = None
    unavailable_reason_code: str = ""
    policy_version: str = IMAGING_RUNTIME_POLICY_VERSION

    @property
    def ready(self) -> bool:
        return self.status is ImagingRuntimeStatus.READY

    @property
    def capture_mode(self) -> ImagingCaptureMode | None:
        if self.candidate is None:
            return None
        return self.candidate.capture_mode

    @property
    def advice(
        self,
    ) -> ImagingExposureAdvice | ImagingVideoCaptureAdvice | None:
        return self.exposure_advice or self.video_advice
