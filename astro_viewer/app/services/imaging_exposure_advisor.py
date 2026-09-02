"""Produce conservative still-exposure ranges from candidate and sky facts."""

from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType

from astro_viewer.app.models.imaging import ImagingCameraKind
from astro_viewer.app.models.imaging_exposure import (
    ImagingExposureAdvice,
    ImagingExposureConfidence,
    ImagingExposureFactor,
    ImagingSessionConditions,
)
from astro_viewer.app.models.imaging_recommendation import (
    ImagingCaptureMode,
    ImagingRecommendationCandidate,
    ImagingTargetClass,
)
from astro_viewer.app.services.equipment_taxonomy import (
    MOUNT_TYPE_LABELS,
    canonical_mount_type,
)


IMAGING_EXPOSURE_POLICY_VERSION = "imaging_exposure_v2"
_REFERENCE_FOCAL_RATIO = 5.0
_REFERENCE_SKY_BRIGHTNESS = 21.2
_REFERENCE_TRANSPARENCY_SCORE = 75.0
_DEFAULT_SKY_BRIGHTNESS = 20.5
_DEFAULT_TRANSPARENCY_SCORE = 75.0
_MIN_SUB_EXPOSURE_SECONDS = 0.25
_MAX_SUB_EXPOSURE_SECONDS = 600.0
_MIN_TOTAL_INTEGRATION_MINUTES = 15
_MAX_TOTAL_INTEGRATION_MINUTES = 900

_BORTLE_SKY_BRIGHTNESS: Mapping[int, float] = MappingProxyType(
    {
        1: 21.9,
        2: 21.7,
        3: 21.5,
        4: 20.9,
        5: 20.3,
        6: 19.5,
        7: 18.9,
        8: 18.3,
        9: 17.8,
    }
)
_TOTAL_INTEGRATION_BASE_MINUTES: Mapping[
    ImagingTargetClass,
    tuple[int, int],
] = MappingProxyType(
    {
        ImagingTargetClass.COMET: (30, 60),
        ImagingTargetClass.GALAXY: (120, 240),
        ImagingTargetClass.DIFFUSE_NEBULA: (150, 300),
        ImagingTargetClass.PLANETARY_NEBULA: (60, 150),
        ImagingTargetClass.OPEN_CLUSTER: (45, 90),
        ImagingTargetClass.GLOBULAR_CLUSTER: (60, 120),
        ImagingTargetClass.STELLAR: (20, 60),
        ImagingTargetClass.UNKNOWN: (90, 180),
    }
)
_TARGET_SUB_EXPOSURE_FACTORS: Mapping[ImagingTargetClass, float] = (
    MappingProxyType(
        {
            ImagingTargetClass.COMET: 0.35,
            ImagingTargetClass.PLANETARY_NEBULA: 0.75,
            ImagingTargetClass.OPEN_CLUSTER: 0.55,
            ImagingTargetClass.GLOBULAR_CLUSTER: 0.70,
            ImagingTargetClass.STELLAR: 0.45,
        }
    )
)
_MOUNT_BASE_LIMIT_SECONDS: Mapping[str, float] = MappingProxyType(
    {
        "EQUATORIAL_TRACKING": 90.0,
        "FORK_GOTO": 30.0,
        "ALTAZ_GOTO": 20.0,
        "DOBSONIAN_GOTO": 12.0,
        "EQUATORIAL_MANUAL": 3.0,
        "ALTAZ_PUSHTO": 2.0,
        "DOBSONIAN_PUSHTO": 1.0,
        "MANUAL_UNSPECIFIED": 1.0,
        "ALTAZ_MANUAL": 1.0,
        "DOBSONIAN_MANUAL": 1.0,
        "OTA": 1.0,
        "OTHER": 5.0,
    }
)
_EXTENDED_TARGET_CLASSES = frozenset(
    {
        ImagingTargetClass.COMET,
        ImagingTargetClass.GALAXY,
        ImagingTargetClass.DIFFUSE_NEBULA,
        ImagingTargetClass.PLANETARY_NEBULA,
    }
)
_TARGET_MAGNITUDE_REFERENCES: Mapping[ImagingTargetClass, float] = (
    MappingProxyType(
        {
            ImagingTargetClass.COMET: 8.0,
            ImagingTargetClass.GALAXY: 10.0,
            ImagingTargetClass.DIFFUSE_NEBULA: 8.0,
            ImagingTargetClass.PLANETARY_NEBULA: 10.0,
            ImagingTargetClass.OPEN_CLUSTER: 6.0,
            ImagingTargetClass.GLOBULAR_CLUSTER: 7.0,
            ImagingTargetClass.STELLAR: 8.0,
            ImagingTargetClass.UNKNOWN: 10.0,
        }
    )
)
_FIELD_ROTATION_MOUNTS = frozenset(
    {
        "FORK_GOTO",
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
_INHERENT_LIMITATIONS = (
    "camera_gain_or_iso_unmodeled",
    "camera_read_noise_unmodeled",
    "autoguiding_unmodeled",
    "tracking_accuracy_unmodeled",
    "filter_passband_unmodeled",
)


class ImagingExposureAdvisor:
    """Builds score-neutral still-exposure ranges from explicit inputs."""

    def advise(
        self,
        candidate: ImagingRecommendationCandidate,
        conditions: ImagingSessionConditions | None = None,
    ) -> ImagingExposureAdvice | None:
        if candidate.capture_mode is not ImagingCaptureMode.STILL:
            return None
        configuration = candidate.configuration
        if not self._positive_finite(
            configuration.effective_focal_ratio
        ) or not self._positive_finite(
            configuration.pixel_scale_arcsec_per_pixel
        ):
            return None

        conditions = conditions or ImagingSessionConditions()
        assumptions = ["broadband_unfiltered_reference"]
        warnings = ["planning_range_not_camera_calibration"]
        missing: list[str] = []
        self._append_target_altitude_warnings(conditions, warnings)

        sky_brightness, sky_is_available = self._sky_brightness(
            conditions,
            assumptions,
            missing,
        )
        transparency_score, transparency_is_available = (
            self._transparency_score(
                conditions,
                assumptions,
                missing,
            )
        )
        moon_severity, moon_is_known = self._moon_severity(
            conditions,
            assumptions,
            warnings,
            missing,
        )
        target_factor, target_brightness_is_known = (
            self._target_brightness_factor(
                candidate,
                assumptions,
                missing,
            )
        )

        optical_factor = self._clamp(
            (
                configuration.effective_focal_ratio
                / _REFERENCE_FOCAL_RATIO
            )
            ** 2,
            0.25,
            4.0,
        )
        sky_sub_factor = self._clamp(
            10.0
            ** (
                0.4
                * (
                    sky_brightness
                    - _REFERENCE_SKY_BRIGHTNESS
                )
            ),
            0.15,
            2.5,
        )
        sky_total_factor = self._clamp(
            10.0
            ** (
                0.2
                * (
                    _REFERENCE_SKY_BRIGHTNESS
                    - sky_brightness
                )
            ),
            0.55,
            3.0,
        )
        transparency_factor = self._clamp(
            _REFERENCE_TRANSPARENCY_SCORE
            / max(30.0, transparency_score),
            0.75,
            2.0,
        )
        moon_sub_factor = 1.0 / (1.0 + 2.0 * moon_severity)
        moon_total_factor = 1.0 + 1.5 * moon_severity

        factors = (
            ImagingExposureFactor(
                "optical_speed",
                sub_exposure_multiplier=optical_factor,
                total_integration_multiplier=optical_factor,
            ),
            ImagingExposureFactor(
                "sky_background",
                sub_exposure_multiplier=sky_sub_factor,
                total_integration_multiplier=sky_total_factor,
            ),
            ImagingExposureFactor(
                "transparency",
                total_integration_multiplier=transparency_factor,
            ),
            ImagingExposureFactor(
                "moonlight",
                sub_exposure_multiplier=moon_sub_factor,
                total_integration_multiplier=moon_total_factor,
            ),
            ImagingExposureFactor(
                "target_brightness",
                total_integration_multiplier=target_factor,
            ),
        )

        mount_type = canonical_mount_type(configuration.mount_type)
        mount_is_known = (
            mount_type in MOUNT_TYPE_LABELS
            and mount_type not in {"OTA", "OTHER"}
        )
        if not mount_is_known:
            missing.append("mount_type")
            assumptions.append("unknown_mount_short_exposure_limit")
            warnings.append("mount_type_unverified")
        tracking_limit = self._tracking_limit(
            candidate,
            mount_type,
            warnings,
        )
        reference_sub_exposure = self._reference_sub_exposure(
            candidate,
            warnings,
        )
        raw_sub_exposure = (
            reference_sub_exposure
            * self._target_sub_exposure_factor(candidate)
            * optical_factor
            * sky_sub_factor
            * moon_sub_factor
        )
        sub_min, sub_max = self._sub_exposure_range(
            raw_sub_exposure,
            tracking_limit,
        )

        base_total_min, base_total_max = (
            _TOTAL_INTEGRATION_BASE_MINUTES.get(
                candidate.target.target_class,
                _TOTAL_INTEGRATION_BASE_MINUTES[
                    ImagingTargetClass.UNKNOWN
                ],
            )
        )
        total_multiplier = (
            optical_factor
            * sky_total_factor
            * transparency_factor
            * moon_total_factor
            * target_factor
        )
        raw_total_min = base_total_min * total_multiplier
        raw_total_max = base_total_max * total_multiplier
        total_min_is_lower_bound = (
            raw_total_min > _MAX_TOTAL_INTEGRATION_MINUTES
        )
        total_max_is_lower_bound = (
            raw_total_max > _MAX_TOTAL_INTEGRATION_MINUTES
        )
        if total_max_is_lower_bound:
            warnings.append("total_integration_limit_reached")
        total_min = self._round_integration_minutes(raw_total_min)
        total_max = self._round_integration_minutes(raw_total_max)
        total_max = max(total_min, total_max)

        frame_count_min = max(
            1,
            math.ceil(total_min * 60.0 / sub_max),
        )
        frame_count_max = max(
            frame_count_min,
            math.ceil(total_max * 60.0 / sub_min),
        )
        long_exposure_capability_is_known = (
            self._long_exposure_capability_is_known(candidate)
        )
        if not long_exposure_capability_is_known:
            missing.append("camera_long_exposure_mode")
        checks = (
            target_brightness_is_known,
            sky_is_available,
            transparency_is_available,
            moon_is_known,
            mount_is_known,
            long_exposure_capability_is_known,
        )
        completeness = sum(checks) / len(checks)
        confidence = (
            ImagingExposureConfidence.MEDIUM
            if completeness >= 0.60
            else ImagingExposureConfidence.LOW
        )
        return ImagingExposureAdvice(
            candidate=candidate,
            sub_exposure_min_seconds=sub_min,
            sub_exposure_max_seconds=sub_max,
            total_integration_min_minutes=total_min,
            total_integration_max_minutes=total_max,
            estimated_frame_count_min=frame_count_min,
            estimated_frame_count_max=frame_count_max,
            tracking_limit_seconds=tracking_limit,
            factors=factors,
            confidence=confidence,
            data_completeness=round(completeness, 6),
            total_integration_min_is_lower_bound=(
                total_min_is_lower_bound
            ),
            total_integration_max_is_lower_bound=(
                total_max_is_lower_bound
            ),
            missing_inputs=self._unique(missing),
            assumption_codes=self._unique(assumptions),
            warning_codes=self._unique(warnings),
            limitation_codes=_INHERENT_LIMITATIONS,
            policy_version=IMAGING_EXPOSURE_POLICY_VERSION,
        )

    @classmethod
    def _append_target_altitude_warnings(
        cls,
        conditions: ImagingSessionConditions,
        warnings: list[str],
    ) -> None:
        current_altitude = cls._bounded_float(
            conditions.target_current_altitude_deg,
            -90.0,
            90.0,
        )
        maximum_altitude = cls._bounded_float(
            conditions.target_maximum_altitude_deg,
            -90.0,
            90.0,
        )
        if current_altitude is not None and current_altitude < 0:
            warnings.append("target_below_horizon")
        if maximum_altitude is not None and maximum_altitude < 30.0:
            warnings.append(
                "target_stays_below_preferred_imaging_altitude"
            )
        elif (
            current_altitude is not None
            and 0.0 <= current_altitude < 30.0
        ):
            warnings.append("low_target_altitude")

    @staticmethod
    def _sky_brightness(
        conditions: ImagingSessionConditions,
        assumptions: list[str],
        missing: list[str],
    ) -> tuple[float, bool]:
        value = ImagingExposureAdvisor._bounded_float(
            conditions.sky_brightness_mag_arcsec2,
            16.0,
            23.5,
        )
        if value is not None:
            return value, True
        bortle = conditions.bortle_class
        if (
            not isinstance(bortle, bool)
            and bortle in _BORTLE_SKY_BRIGHTNESS
        ):
            assumptions.append("sky_brightness_estimated_from_bortle")
            return _BORTLE_SKY_BRIGHTNESS[int(bortle)], True
        assumptions.append("neutral_sky_background")
        missing.append("sky_background")
        return _DEFAULT_SKY_BRIGHTNESS, False

    @staticmethod
    def _transparency_score(
        conditions: ImagingSessionConditions,
        assumptions: list[str],
        missing: list[str],
    ) -> tuple[float, bool]:
        value = ImagingExposureAdvisor._bounded_float(
            conditions.transparency_score,
            0.0,
            100.0,
        )
        if value is not None and not isinstance(
            conditions.transparency_score,
            bool,
        ):
            return value, True
        assumptions.append("neutral_transparency")
        missing.append("transparency")
        return _DEFAULT_TRANSPARENCY_SCORE, False

    @classmethod
    def _moon_severity(
        cls,
        conditions: ImagingSessionConditions,
        assumptions: list[str],
        warnings: list[str],
        missing: list[str],
    ) -> tuple[float, bool]:
        visible = conditions.moon_visible_during_target_window
        altitude = cls._bounded_float(
            conditions.moon_altitude_deg,
            -90.0,
            90.0,
        )
        if visible is False or altitude is not None and altitude <= 0:
            return 0.0, True

        illumination = cls._bounded_float(
            conditions.moon_illumination_fraction,
            0.0,
            1.0,
        )
        if illumination == 0.0:
            return 0.0, True
        separation = cls._bounded_float(
            conditions.moon_target_separation_deg,
            0.0,
            180.0,
        )
        missing_values = []
        if illumination is None:
            missing_values.append("moon_illumination")
        if altitude is None:
            missing_values.append("moon_altitude")
        if separation is None:
            missing_values.append("moon_target_separation")
        if visible is None:
            missing_values.append("moon_window_visibility")
        if missing_values:
            missing.extend(missing_values)
            assumptions.append("neutral_moonlight_without_complete_geometry")
            return 0.0, False

        altitude_factor = cls._clamp((altitude + 5.0) / 60.0)
        separation_factor = cls._clamp(
            (120.0 - separation) / 100.0
        )
        severity = cls._clamp(
            illumination
            * altitude_factor
            * (0.25 + 0.75 * separation_factor)
        )
        if severity >= 0.65:
            warnings.append("strong_moonlight")
        elif severity >= 0.30:
            warnings.append("moonlight_present")
        return severity, True

    @staticmethod
    def _target_brightness_factor(
        candidate: ImagingRecommendationCandidate,
        assumptions: list[str],
        missing: list[str],
    ) -> tuple[float, bool]:
        target_class = candidate.target.target_class
        surface_brightness = candidate.target.surface_brightness_proxy
        if (
            target_class in _EXTENDED_TARGET_CLASSES
            and surface_brightness is not None
            and math.isfinite(surface_brightness)
        ):
            assumptions.append("target_surface_brightness_proxy")
            return (
                ImagingExposureAdvisor._clamp(
                    10.0 ** (0.10 * (surface_brightness - 13.5)),
                    0.60,
                    2.50,
                ),
                True,
            )

        magnitude = candidate.target.magnitude
        reference_magnitude = _TARGET_MAGNITUDE_REFERENCES.get(
            target_class,
            10.0,
        )
        if magnitude is not None and math.isfinite(magnitude):
            if target_class in _EXTENDED_TARGET_CLASSES:
                assumptions.append(
                    "target_integrated_magnitude_fallback"
                )
                missing.append("target_surface_brightness")
                complete = False
            else:
                assumptions.append("target_integrated_magnitude_proxy")
                complete = True
            return (
                ImagingExposureAdvisor._clamp(
                    10.0
                    ** (
                        0.08
                        * (magnitude - reference_magnitude)
                    ),
                    0.60,
                    2.50,
                ),
                complete,
            )

        if target_class in _EXTENDED_TARGET_CLASSES:
            missing.append("target_surface_brightness")
        else:
            missing.append("target_magnitude")
        return 1.0, False

    @staticmethod
    def _reference_sub_exposure(
        candidate: ImagingRecommendationCandidate,
        warnings: list[str],
    ) -> float:
        camera = candidate.camera
        if camera.is_dedicated_astronomy_camera:
            if not camera.cooled:
                warnings.append("uncooled_camera_thermal_noise")
                return 60.0
            return 120.0
        if not camera.bulb_mode:
            warnings.append("bulb_mode_unavailable")
            return 15.0
        warnings.append("uncooled_camera_thermal_noise")
        return 60.0

    @staticmethod
    def _target_sub_exposure_factor(
        candidate: ImagingRecommendationCandidate,
    ) -> float:
        return _TARGET_SUB_EXPOSURE_FACTORS.get(
            candidate.target.target_class,
            1.0,
        )

    @classmethod
    def _tracking_limit(
        cls,
        candidate: ImagingRecommendationCandidate,
        mount_type: str,
        warnings: list[str],
    ) -> float:
        base_limit = _MOUNT_BASE_LIMIT_SECONDS.get(mount_type, 1.0)
        sampling_factor = cls._clamp(
            candidate.configuration.pixel_scale_arcsec_per_pixel / 1.5,
            0.40,
            1.50,
        )
        limit = base_limit * sampling_factor
        if mount_type in _FIELD_ROTATION_MOUNTS:
            warnings.append("field_rotation_limits_sub_exposure")
        elif mount_type in _MANUAL_MOUNTS:
            warnings.append("manual_tracking_limits_sub_exposure")
        elif mount_type == "OTA":
            warnings.append("mount_type_unverified")
        if candidate.target.target_class is ImagingTargetClass.COMET:
            limit = min(limit, 60.0)
            warnings.append("comet_motion_limits_sub_exposure")
        if (
            candidate.camera.kind is ImagingCameraKind.CAMERA_BODY
            and not candidate.camera.bulb_mode
        ):
            limit = min(limit, 30.0)
        return cls._clamp(
            limit,
            _MIN_SUB_EXPOSURE_SECONDS,
            _MAX_SUB_EXPOSURE_SECONDS,
        )

    @classmethod
    def _sub_exposure_range(
        cls,
        desired_seconds: float,
        tracking_limit_seconds: float,
    ) -> tuple[float, float]:
        desired = cls._clamp(
            desired_seconds,
            _MIN_SUB_EXPOSURE_SECONDS,
            _MAX_SUB_EXPOSURE_SECONDS,
        )
        upper_raw = min(desired * 1.35, tracking_limit_seconds)
        lower_raw = min(desired * 0.65, upper_raw * 0.50)
        upper = cls._round_sub_exposure(
            upper_raw,
            round_down=True,
        )
        lower = cls._round_sub_exposure(
            min(lower_raw, upper),
            round_down=False,
        )
        lower = min(lower, upper)
        return lower, upper

    @staticmethod
    def _round_sub_exposure(
        seconds: float,
        *,
        round_down: bool,
    ) -> float:
        value = max(_MIN_SUB_EXPOSURE_SECONDS, seconds)
        if value < 1.0:
            step = 0.25
        elif value < 10.0:
            step = 1.0
        elif value < 60.0:
            step = 5.0
        elif value < 180.0:
            step = 15.0
        else:
            step = 30.0
        scaled = value / step
        rounded = (
            math.floor(scaled) * step
            if round_down
            else round(scaled) * step
        )
        return max(_MIN_SUB_EXPOSURE_SECONDS, float(rounded))

    @staticmethod
    def _round_integration_minutes(value: float) -> int:
        bounded = ImagingExposureAdvisor._clamp(
            value,
            float(_MIN_TOTAL_INTEGRATION_MINUTES),
            float(_MAX_TOTAL_INTEGRATION_MINUTES),
        )
        return int(round(bounded / 5.0) * 5)

    @staticmethod
    def _long_exposure_capability_is_known(
        candidate: ImagingRecommendationCandidate,
    ) -> bool:
        return (
            candidate.camera.is_dedicated_astronomy_camera
            or candidate.camera.bulb_mode
        )

    @staticmethod
    def _bounded_float(
        value: object,
        minimum: float,
        maximum: float,
    ) -> float | None:
        if value is None:
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
        try:
            normalized = float(value)
        except (TypeError, ValueError):
            return False
        return math.isfinite(normalized) and normalized > 0

    @staticmethod
    def _unique(values: list[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(values))

    @staticmethod
    def _clamp(
        value: float,
        minimum: float = 0.0,
        maximum: float = 1.0,
    ) -> float:
        return max(minimum, min(maximum, float(value)))
