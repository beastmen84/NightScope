from __future__ import annotations

from astro_viewer.app.models.imaging_recommendation import ImagingCaptureMode
from astro_viewer.app.models.imaging_runtime import (
    ImagingRuntimeConditions,
    ImagingRuntimeInventory,
    ImagingRuntimeRecommendation,
    ImagingRuntimeStatus,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.imaging_exposure_advisor import (
    ImagingExposureAdvisor,
)
from astro_viewer.app.services.imaging_recommendation_service import (
    ImagingRecommendationService,
)
from astro_viewer.app.services.imaging_target_traits import (
    ImagingTargetTraitsAdapter,
)
from astro_viewer.app.services.imaging_train_builder import ImagingTrainBuilder
from astro_viewer.app.services.imaging_video_capture_advisor import (
    ImagingVideoCaptureAdvisor,
)


class ImagingRuntimeAssembler:
    """Builds one on-demand photographic plan from explicit runtime snapshots."""

    def __init__(
        self,
        *,
        train_builder: ImagingTrainBuilder | None = None,
        recommendation_service: ImagingRecommendationService | None = None,
        exposure_advisor: ImagingExposureAdvisor | None = None,
        video_advisor: ImagingVideoCaptureAdvisor | None = None,
    ) -> None:
        self._train_builder = train_builder or ImagingTrainBuilder()
        self._recommendation_service = (
            recommendation_service or ImagingRecommendationService()
        )
        self._exposure_advisor = exposure_advisor or ImagingExposureAdvisor()
        self._video_advisor = video_advisor or ImagingVideoCaptureAdvisor()

    def assemble(
        self,
        target: CelestialObject,
        inventory: ImagingRuntimeInventory,
        conditions: ImagingRuntimeConditions | None = None,
    ) -> ImagingRuntimeRecommendation:
        target_id = target.id.strip()
        if not inventory.has_active_profile:
            return self._unavailable(
                target_id,
                inventory,
                ImagingRuntimeStatus.NO_ACTIVE_PROFILE,
                "active_profile_required",
            )
        if not inventory.telescopes:
            return self._unavailable(
                target_id,
                inventory,
                ImagingRuntimeStatus.NO_TELESCOPES,
                "profile_telescope_required",
            )
        if not inventory.cameras:
            return self._unavailable(
                target_id,
                inventory,
                ImagingRuntimeStatus.NO_CAMERAS,
                "profile_camera_required",
            )

        configurations = self._train_builder.build(
            inventory.telescopes,
            inventory.cameras,
            reducers=inventory.reducers,
            barlows=inventory.barlows,
        )
        if not configurations:
            return self._unavailable(
                target_id,
                inventory,
                ImagingRuntimeStatus.NO_VALID_CONFIGURATIONS,
                "valid_imaging_train_required",
            )

        solar_filter_ids = self._solar_filter_ids(inventory)
        candidates = self._recommendation_service.rank(
            target,
            configurations,
            full_aperture_solar_filter_telescope_ids=solar_filter_ids,
        )
        if not candidates:
            solar_filter_available = any(
                configuration.telescope.id in solar_filter_ids
                for configuration in configurations
            )
            traits = ImagingTargetTraitsAdapter.from_object(
                target,
                full_aperture_solar_filter_available=(
                    solar_filter_available
                ),
            )
            return self._unavailable(
                target_id,
                inventory,
                ImagingRuntimeStatus.TARGET_UNSUPPORTED,
                (
                    traits.unsupported_reason_code
                    or "photographic_target_unsupported"
                ),
                configuration_count=len(configurations),
            )

        conditions = conditions or ImagingRuntimeConditions()
        candidate = candidates[0]
        exposure_advice = None
        video_advice = None
        if candidate.capture_mode is ImagingCaptureMode.STILL:
            exposure_advice = self._exposure_advisor.advise(
                candidate,
                conditions.still,
            )
        elif candidate.capture_mode is ImagingCaptureMode.VIDEO:
            video_advice = self._video_advisor.advise(
                candidate,
                conditions.video,
            )

        if exposure_advice is None and video_advice is None:
            return ImagingRuntimeRecommendation(
                target_id=target_id,
                profile_id=inventory.profile_id,
                status=ImagingRuntimeStatus.ADVICE_UNAVAILABLE,
                configuration_count=len(configurations),
                candidate_count=len(candidates),
                candidate=candidate,
                unavailable_reason_code="capture_advice_unavailable",
            )

        return ImagingRuntimeRecommendation(
            target_id=target_id,
            profile_id=inventory.profile_id,
            status=ImagingRuntimeStatus.READY,
            configuration_count=len(configurations),
            candidate_count=len(candidates),
            candidate=candidate,
            exposure_advice=exposure_advice,
            video_advice=video_advice,
        )

    @staticmethod
    def _solar_filter_ids(
        inventory: ImagingRuntimeInventory,
    ) -> frozenset[str]:
        assigned_telescope_ids = {
            telescope.id
            for telescope in inventory.telescopes
        }
        return frozenset(
            telescope_id
            for value in inventory.full_aperture_solar_filter_telescope_ids
            if (telescope_id := str(value).strip())
            and telescope_id in assigned_telescope_ids
        )

    @staticmethod
    def _unavailable(
        target_id: str,
        inventory: ImagingRuntimeInventory,
        status: ImagingRuntimeStatus,
        reason_code: str,
        *,
        configuration_count: int = 0,
    ) -> ImagingRuntimeRecommendation:
        return ImagingRuntimeRecommendation(
            target_id=target_id,
            profile_id=inventory.profile_id,
            status=status,
            configuration_count=configuration_count,
            unavailable_reason_code=reason_code,
        )
