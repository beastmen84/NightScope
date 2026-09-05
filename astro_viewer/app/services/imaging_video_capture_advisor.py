"""Produce heuristic planetary-video duration, FPS, and frame guidance.

Clip durations and mount caps are policy ranges in seconds, not a calculation
of resolved rotational smear or time-dependent field rotation. FPS is declared
camera capability or user-supplied achievable rate, not an exposure prediction;
frame counts do not imply usable/stackable frames. Seeing/altitude add context
and warnings without certifying a particular achievable image resolution.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from astro_viewer.app.models.imaging import ImagingCameraKind
from astro_viewer.app.models.imaging_recommendation import (
    ImagingCaptureMode,
    ImagingRecommendationCandidate,
    ImagingTargetClass,
)
from astro_viewer.app.models.imaging_video_capture import (
    ImagingVideoCaptureAdvice,
    ImagingVideoConfidence,
    ImagingVideoFpsSource,
    ImagingVideoSessionConditions,
)
from astro_viewer.app.services.equipment_taxonomy import (
    MOUNT_TYPE_LABELS,
    canonical_mount_type,
)


IMAGING_VIDEO_CAPTURE_POLICY_VERSION = "imaging_video_capture_v2"
_MIN_VALID_FPS = 0.5
_MAX_VALID_FPS = 1000.0
_MIN_CLIP_DURATION_SECONDS = 10
_MAX_CLIP_DURATION_SECONDS = 600


@dataclass(frozen=True)
class _VideoTargetPolicy:
    profile: str
    duration_min_seconds: int
    duration_max_seconds: int
    target_fps_min: float
    target_fps_max: float


_TARGET_POLICIES: Mapping[str, _VideoTargetPolicy] = MappingProxyType(
    {
        "sun": _VideoTargetPolicy(
            "solar_whole_disc",
            15,
            45,
            30.0,
            120.0,
        ),
        "moon": _VideoTargetPolicy(
            "lunar_whole_disc",
            20,
            60,
            30.0,
            120.0,
        ),
        "mercury": _VideoTargetPolicy(
            "mercury",
            120,
            180,
            30.0,
            120.0,
        ),
        "venus": _VideoTargetPolicy(
            "venus",
            180,
            300,
            30.0,
            120.0,
        ),
        "mars": _VideoTargetPolicy(
            "mars",
            120,
            180,
            30.0,
            120.0,
        ),
        "jupiter": _VideoTargetPolicy(
            "jupiter",
            90,
            120,
            30.0,
            120.0,
        ),
        "saturn": _VideoTargetPolicy(
            "saturn",
            120,
            180,
            30.0,
            60.0,
        ),
        "uranus": _VideoTargetPolicy(
            "uranus",
            180,
            300,
            10.0,
            30.0,
        ),
        "neptune": _VideoTargetPolicy(
            "neptune",
            180,
            300,
            10.0,
            30.0,
        ),
    }
)
_GENERIC_PLANET_POLICY = _VideoTargetPolicy(
    "generic_planet",
    90,
    180,
    30.0,
    60.0,
)
_TARGET_ALIASES: Mapping[str, str] = MappingProxyType(
    {
        "sole": "sun",
        "sol": "sun",
        "luna": "moon",
        "mercurio": "mercury",
        "venere": "venus",
        "marte": "mars",
        "giove": "jupiter",
        "saturno": "saturn",
        "urano": "uranus",
        "nettuno": "neptune",
        "neptuno": "neptune",
    }
)
_MOUNT_CLIP_CAP_SECONDS: Mapping[str, int] = MappingProxyType(
    {
        "EQUATORIAL_TRACKING": 600,
        "FORK_GOTO": 240,
        "ALTAZ_GOTO": 240,
        "DOBSONIAN_GOTO": 180,
        "EQUATORIAL_MANUAL": 90,
        "ALTAZ_PUSHTO": 60,
        "DOBSONIAN_PUSHTO": 60,
        "MANUAL_UNSPECIFIED": 60,
        "ALTAZ_MANUAL": 60,
        "DOBSONIAN_MANUAL": 60,
        "OTA": 60,
        "OTHER": 60,
    }
)
_FIELD_ROTATION_MOUNTS = frozenset(
    {
        "ALTAZ_GOTO",
        "DOBSONIAN_GOTO",
    }
)
_MANUAL_MOUNTS = frozenset(
    {
        "EQUATORIAL_MANUAL",
        "ALTAZ_PUSHTO",
        "DOBSONIAN_PUSHTO",
        "MANUAL_UNSPECIFIED",
        "ALTAZ_MANUAL",
        "DOBSONIAN_MANUAL",
    }
)
_ROTATION_LIMITED_PLANETS = frozenset(
    {
        "mars",
        "jupiter",
        "saturn",
        "uranus",
        "neptune",
    }
)
_FAINT_PLANETS = frozenset({"uranus", "neptune"})
_INHERENT_LIMITATIONS = (
    "frame_exposure_gain_and_histogram_unmodeled",
    "roi_and_sensor_readout_mode_unmodeled",
    "actual_usb_and_storage_throughput_unmodeled",
    "video_codec_or_raw_format_unmodeled",
    "atmospheric_dispersion_correction_unmodeled",
    "target_apparent_diameter_and_phase_unmodeled",
    "lucky_frame_selection_fraction_unmodeled",
    "image_derotation_unmodeled",
)


class ImagingVideoCaptureAdvisor:
    """Builds score-neutral single-clip guidance for video candidates."""

    def advise(
        self,
        candidate: ImagingRecommendationCandidate,
        conditions: ImagingVideoSessionConditions | None = None,
    ) -> ImagingVideoCaptureAdvice | None:
        if candidate.capture_mode is not ImagingCaptureMode.VIDEO:
            return None
        if candidate.target.target_class not in {
            ImagingTargetClass.SUN,
            ImagingTargetClass.MOON,
            ImagingTargetClass.PLANET,
        }:
            return None
        configuration = candidate.configuration
        if not self._positive_finite(
            configuration.effective_focal_ratio
        ) or not self._positive_finite(
            configuration.pixel_scale_arcsec_per_pixel
        ):
            return None

        conditions = conditions or ImagingVideoSessionConditions()
        assumptions = ["single_clip_without_image_derotation"]
        warnings = ["planning_range_not_capture_calibration"]
        missing: list[str] = []

        target_id, policy, target_is_known = self._target_policy(
            candidate,
            assumptions,
            missing,
        )
        mount_type = canonical_mount_type(configuration.mount_type)
        mount_is_known = (
            mount_type in MOUNT_TYPE_LABELS
            and mount_type not in {"OTA", "OTHER"}
        )
        duration_min, duration_max = self._duration_range(
            policy,
            mount_type,
            warnings,
            assumptions,
            missing,
        )
        (
            fps_min,
            fps_max,
            fps_source,
            camera_fps_is_known,
            achievable_fps_is_known,
        ) = self._fps_range(
            candidate,
            policy,
            conditions,
            assumptions,
            warnings,
            missing,
        )
        seeing_is_known = self._apply_seeing_context(
            conditions,
            assumptions,
            warnings,
            missing,
        )
        altitude_is_known = self._apply_altitude_context(
            conditions,
            assumptions,
            warnings,
            missing,
        )
        video_geometry_is_known = self._apply_camera_context(
            candidate,
            warnings,
            assumptions,
            missing,
        )
        self._apply_target_context(target_id, warnings)

        frame_count_min = max(
            1,
            math.floor(duration_min * fps_min),
        )
        frame_count_max = max(
            frame_count_min,
            math.ceil(duration_max * fps_max),
        )
        checks = (
            target_is_known,
            camera_fps_is_known or achievable_fps_is_known,
            achievable_fps_is_known,
            seeing_is_known,
            altitude_is_known,
            mount_is_known,
            video_geometry_is_known,
        )
        completeness = sum(checks) / len(checks)
        confidence = (
            ImagingVideoConfidence.MEDIUM
            if completeness >= 0.67
            else ImagingVideoConfidence.LOW
        )
        return ImagingVideoCaptureAdvice(
            candidate=candidate,
            target_profile=policy.profile,
            clip_duration_min_seconds=duration_min,
            clip_duration_max_seconds=duration_max,
            planned_fps_min=fps_min,
            planned_fps_max=fps_max,
            estimated_frame_count_min=frame_count_min,
            estimated_frame_count_max=frame_count_max,
            fps_source=fps_source,
            confidence=confidence,
            data_completeness=round(completeness, 6),
            missing_inputs=self._unique(missing),
            assumption_codes=self._unique(assumptions),
            warning_codes=self._unique(warnings),
            limitation_codes=_INHERENT_LIMITATIONS,
            policy_version=IMAGING_VIDEO_CAPTURE_POLICY_VERSION,
        )

    @staticmethod
    def _target_policy(
        candidate: ImagingRecommendationCandidate,
        assumptions: list[str],
        missing: list[str],
    ) -> tuple[str, _VideoTargetPolicy, bool]:
        raw_target_id = candidate.target.target_id.strip().casefold()
        target_id = _TARGET_ALIASES.get(raw_target_id, raw_target_id)
        policy = _TARGET_POLICIES.get(target_id)
        if policy is not None:
            return target_id, policy, True
        if candidate.target.target_class is ImagingTargetClass.SUN:
            return "sun", _TARGET_POLICIES["sun"], True
        if candidate.target.target_class is ImagingTargetClass.MOON:
            return "moon", _TARGET_POLICIES["moon"], True
        assumptions.append("generic_planet_capture_profile")
        missing.append("planet_capture_profile")
        return target_id, _GENERIC_PLANET_POLICY, False

    @classmethod
    def _duration_range(
        cls,
        policy: _VideoTargetPolicy,
        mount_type: str,
        warnings: list[str],
        assumptions: list[str],
        missing: list[str],
    ) -> tuple[int, int]:
        mount_cap = _MOUNT_CLIP_CAP_SECONDS.get(mount_type, 60)
        if mount_type in _FIELD_ROTATION_MOUNTS:
            warnings.append("field_rotation_limits_long_video")
        elif mount_type == "FORK_GOTO":
            warnings.append("fork_orientation_unmodeled")
        elif mount_type in _MANUAL_MOUNTS:
            warnings.append("manual_tracking_may_fragment_video")
        elif mount_type not in MOUNT_TYPE_LABELS or mount_type in {
            "OTA",
            "OTHER",
        }:
            missing.append("mount_type")
            assumptions.append("unknown_mount_short_video_limit")
            warnings.append("mount_type_unverified")

        upper = min(policy.duration_max_seconds, mount_cap)
        if policy.duration_min_seconds < upper:
            lower = policy.duration_min_seconds
        elif policy.duration_min_seconds == upper:
            lower = max(
                _MIN_CLIP_DURATION_SECONDS,
                int(round(upper * 0.67)),
            )
        else:
            lower = max(
                _MIN_CLIP_DURATION_SECONDS,
                int(round(upper * 0.50)),
            )
        return (
            cls._round_duration(lower),
            cls._round_duration(upper),
        )

    @classmethod
    def _fps_range(
        cls,
        candidate: ImagingRecommendationCandidate,
        policy: _VideoTargetPolicy,
        conditions: ImagingVideoSessionConditions,
        assumptions: list[str],
        warnings: list[str],
        missing: list[str],
    ) -> tuple[
        float,
        float,
        ImagingVideoFpsSource,
        bool,
        bool,
    ]:
        achievable = cls._bounded_float(
            conditions.achievable_fps,
            _MIN_VALID_FPS,
            _MAX_VALID_FPS,
        )
        if achievable is not None:
            planned = min(achievable, policy.target_fps_max)
            if achievable > policy.target_fps_max:
                assumptions.append(
                    "achievable_fps_capped_to_target_goal"
                )
            if planned < policy.target_fps_min:
                warnings.append("frame_rate_below_target_goal")
            rounded = cls._round_measured_fps(planned)
            return (
                rounded,
                rounded,
                ImagingVideoFpsSource.ACHIEVABLE,
                cls._catalog_fps(candidate) is not None,
                True,
            )
        if conditions.achievable_fps is not None:
            warnings.append("achievable_fps_invalid")
        missing.append("achievable_fps")

        catalog_fps = cls._catalog_fps(candidate)
        if catalog_fps is not None:
            upper_raw = min(catalog_fps, policy.target_fps_max)
            if catalog_fps > policy.target_fps_max:
                assumptions.append(
                    "catalog_fps_capped_to_target_goal"
                )
            lower_raw = (
                policy.target_fps_min
                if upper_raw >= policy.target_fps_min
                else max(5.0, upper_raw * 0.60)
            )
            upper = cls._round_fps(upper_raw, round_down=True)
            lower = cls._round_fps(
                min(lower_raw, upper),
                round_down=True,
            )
            if upper < policy.target_fps_min:
                warnings.append("frame_rate_below_target_goal")
            assumptions.append("catalog_max_fps_is_upper_bound")
            warnings.append("catalog_fps_not_guaranteed")
            return (
                lower,
                upper,
                ImagingVideoFpsSource.CATALOG_MAXIMUM,
                True,
                False,
            )

        missing.append("camera_fps")
        assumptions.append("target_fps_goal_without_camera_limit")
        warnings.append("camera_fps_unknown")
        return (
            policy.target_fps_min,
            policy.target_fps_max,
            ImagingVideoFpsSource.TARGET_GOAL,
            False,
            False,
        )

    @classmethod
    def _catalog_fps(
        cls,
        candidate: ImagingRecommendationCandidate,
    ) -> float | None:
        camera = candidate.camera
        value = (
            camera.full_resolution_fps
            if camera.is_dedicated_astronomy_camera
            else camera.video_fps
        )
        return cls._bounded_float(
            value,
            _MIN_VALID_FPS,
            _MAX_VALID_FPS,
        )

    @classmethod
    def _apply_seeing_context(
        cls,
        conditions: ImagingVideoSessionConditions,
        assumptions: list[str],
        warnings: list[str],
        missing: list[str],
    ) -> bool:
        seeing = cls._bounded_float(
            conditions.seeing_score,
            0.0,
            100.0,
        )
        if seeing is None or isinstance(conditions.seeing_score, bool):
            assumptions.append("seeing_not_used_for_clip_duration")
            missing.append("seeing_score")
            return False
        if seeing < 40.0:
            warnings.append("poor_seeing_limits_planetary_detail")
        elif seeing < 65.0:
            warnings.append("variable_seeing_capture_multiple_clips")
        return True

    @classmethod
    def _apply_altitude_context(
        cls,
        conditions: ImagingVideoSessionConditions,
        assumptions: list[str],
        warnings: list[str],
        missing: list[str],
    ) -> bool:
        altitude = cls._bounded_float(
            conditions.target_altitude_deg,
            -90.0,
            90.0,
        )
        if altitude is None:
            assumptions.append("target_altitude_not_used")
            missing.append("target_altitude")
            return False
        if altitude <= 0.0:
            warnings.append("target_below_horizon")
        elif altitude < 25.0:
            warnings.append("low_target_altitude")
        elif altitude < 40.0:
            warnings.append("atmospheric_dispersion_risk")
        return True

    @staticmethod
    def _apply_camera_context(
        candidate: ImagingRecommendationCandidate,
        warnings: list[str],
        assumptions: list[str],
        missing: list[str],
    ) -> bool:
        camera = candidate.camera
        if camera.kind is ImagingCameraKind.CAMERA_BODY:
            warnings.append("camera_body_video_may_be_compressed")
            assumptions.append("camera_body_video_geometry_not_assumed")
            missing.extend(
                (
                    "video_active_sensor_area",
                    "video_pixel_scale",
                )
            )
            video_geometry_is_known = False
        else:
            video_geometry_is_known = True
        if camera.color_mode == "MONO":
            warnings.append(
                "monochrome_filter_sequence_must_fit_capture_window"
            )
        return video_geometry_is_known

    @staticmethod
    def _apply_target_context(
        target_id: str,
        warnings: list[str],
    ) -> None:
        if target_id in _ROTATION_LIMITED_PLANETS:
            warnings.append("planet_rotation_limits_single_clip")
        if target_id in _FAINT_PLANETS:
            warnings.append(
                "faint_planet_requires_exposure_gain_tradeoff"
            )
        if target_id == "mercury":
            warnings.append("solar_proximity_requires_safe_pointing")
        elif target_id == "sun":
            warnings.append(
                "solar_filter_integrity_must_be_verified"
            )

    @staticmethod
    def _round_duration(value: int) -> int:
        bounded = max(
            _MIN_CLIP_DURATION_SECONDS,
            min(_MAX_CLIP_DURATION_SECONDS, int(value)),
        )
        return max(
            _MIN_CLIP_DURATION_SECONDS,
            int(round(bounded / 5.0) * 5),
        )

    @staticmethod
    def _round_fps(
        value: float,
        *,
        round_down: bool,
    ) -> float:
        bounded = max(_MIN_VALID_FPS, float(value))
        step = 1.0 if bounded < 15.0 else 5.0
        scaled = bounded / step
        rounded = (
            math.floor(scaled) * step
            if round_down
            else round(scaled) * step
        )
        return max(_MIN_VALID_FPS, float(rounded))

    @staticmethod
    def _round_measured_fps(value: float) -> float:
        return round(max(_MIN_VALID_FPS, float(value)), 2)

    @staticmethod
    def _bounded_float(
        value: object,
        minimum: float,
        maximum: float,
    ) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return None
        if (
            not math.isfinite(normalized)
            or normalized < minimum
            or normalized > maximum
        ):
            return None
        return normalized

    @staticmethod
    def _positive_finite(value: object) -> bool:
        if isinstance(value, bool):
            return False
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return False
        return math.isfinite(normalized) and normalized > 0

    @staticmethod
    def _unique(values: list[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(values))
