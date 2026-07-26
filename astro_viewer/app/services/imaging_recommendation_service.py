from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from types import MappingProxyType

from astro_viewer.app.models.imaging import (
    ImagingCameraKind,
    ImagingModifierKind,
    ImagingTrainConfiguration,
)
from astro_viewer.app.models.imaging_recommendation import (
    ImagingCaptureMode,
    ImagingRecommendationCandidate,
    ImagingScoreComponent,
    ImagingTargetClass,
    ImagingTargetTraits,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_taxonomy import (
    MOUNT_TYPE_LABELS,
    canonical_mount_type,
)
from astro_viewer.app.services.imaging_target_traits import (
    ImagingTargetTraitsAdapter,
)


STILL_COMPONENT_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {
        "framing": 25.0,
        "sampling": 20.0,
        "camera": 20.0,
        "mount": 20.0,
        "capture_efficiency": 15.0,
    }
)
DISC_VIDEO_COMPONENT_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {
        "sampling": 30.0,
        "camera": 25.0,
        "frame_acquisition": 25.0,
        "framing": 10.0,
        "mount": 10.0,
    }
)
PLANETARY_VIDEO_COMPONENT_WEIGHTS: Mapping[str, float] = MappingProxyType(
    {
        "sampling": 25.0,
        "aperture": 15.0,
        "camera": 20.0,
        "frame_acquisition": 20.0,
        "framing": 10.0,
        "mount": 10.0,
    }
)
_FRAME_EDGE_MARGIN = 0.95
_STILL_IDEAL_FRAME_FILL = 0.58
_LUNAR_IDEAL_FRAME_FILL = 0.68
_PLANETARY_CRITICAL_FOCAL_RATIO_PER_PIXEL = 5.0
_LUNAR_WHOLE_DISC_FOCAL_RATIO_PER_PIXEL = 2.5


class ImagingRecommendationService:
    """Ranks photographic trains without observing or visual-engine scores."""

    def rank(
        self,
        target: CelestialObject,
        configurations: Iterable[ImagingTrainConfiguration],
        *,
        full_aperture_solar_filter_telescope_ids: Iterable[str] = (),
    ) -> list[ImagingRecommendationCandidate]:
        unique_configurations = self._unique_configurations(
            configurations
        )
        solar_filter_telescope_ids = frozenset(
            telescope_id
            for value in full_aperture_solar_filter_telescope_ids
            if (telescope_id := str(value).strip())
        )
        solar_filter_available = any(
            configuration.telescope.id
            in solar_filter_telescope_ids
            for configuration in unique_configurations
        )
        traits = ImagingTargetTraitsAdapter.from_object(
            target,
            full_aperture_solar_filter_available=(
                solar_filter_available
            ),
        )
        capture_mode = traits.recommended_capture_mode
        if not traits.recommendation_supported or capture_mode is None:
            return []

        candidates = [
            self._candidate(traits, configuration, capture_mode)
            for configuration in unique_configurations
            if self._configuration_is_usable(configuration)
            and (
                traits.target_class is not ImagingTargetClass.SUN
                or configuration.telescope.id
                in solar_filter_telescope_ids
            )
        ]
        candidates.sort(
            key=self._ranking_key
        )
        return candidates

    def best(
        self,
        target: CelestialObject,
        configurations: Iterable[ImagingTrainConfiguration],
        *,
        full_aperture_solar_filter_telescope_ids: Iterable[str] = (),
    ) -> ImagingRecommendationCandidate | None:
        candidates = self.rank(
            target,
            configurations,
            full_aperture_solar_filter_telescope_ids=(
                full_aperture_solar_filter_telescope_ids
            ),
        )
        return candidates[0] if candidates else None

    def _candidate(
        self,
        traits: ImagingTargetTraits,
        configuration: ImagingTrainConfiguration,
        capture_mode: ImagingCaptureMode,
    ) -> ImagingRecommendationCandidate:
        if capture_mode is ImagingCaptureMode.VIDEO:
            component_values = {
                "sampling": self._video_sampling(
                    traits,
                    configuration,
                ),
                "camera": self._video_camera(configuration),
                "frame_acquisition": self._frame_acquisition(
                    configuration
                ),
                "framing": self._video_framing(
                    traits,
                    configuration,
                ),
                "mount": self._mount_score(configuration, capture_mode),
            }
            if traits.target_class is ImagingTargetClass.PLANET:
                component_values["aperture"] = (
                    self._planetary_aperture(configuration)
                )
                weights = PLANETARY_VIDEO_COMPONENT_WEIGHTS
            else:
                weights = DISC_VIDEO_COMPONENT_WEIGHTS
        else:
            component_values = {
                "framing": self._still_framing(
                    traits,
                    configuration,
                ),
                "sampling": self._still_sampling(
                    traits,
                    configuration,
                ),
                "camera": self._still_camera(configuration),
                "mount": self._mount_score(configuration, capture_mode),
                "capture_efficiency": self._still_capture_efficiency(
                    traits,
                    configuration,
                ),
            }
            weights = STILL_COMPONENT_WEIGHTS

        components = tuple(
            ImagingScoreComponent(
                name=name,
                value=self._clamp(component_values[name]),
                weight=weight,
            )
            for name, weight in weights.items()
        )
        score = round(
            self._clamp(
                sum(
                    component.weighted_points
                    for component in components
                )
                / 100.0
            )
            * 100.0,
            6,
        )
        missing_inputs, data_completeness = self._data_completeness(
            traits,
            configuration,
            capture_mode,
        )
        return ImagingRecommendationCandidate(
            target=traits,
            configuration=configuration,
            capture_mode=capture_mode,
            components=components,
            score=score,
            data_completeness=data_completeness,
            missing_inputs=missing_inputs,
        )

    @classmethod
    def _still_framing(
        cls,
        traits: ImagingTargetTraits,
        configuration: ImagingTrainConfiguration,
    ) -> float:
        return cls._known_target_framing(
            traits,
            configuration,
            ideal_fill=_STILL_IDEAL_FRAME_FILL,
        )

    @classmethod
    def _video_framing(
        cls,
        traits: ImagingTargetTraits,
        configuration: ImagingTrainConfiguration,
    ) -> float:
        if configuration.camera.kind is ImagingCameraKind.CAMERA_BODY:
            return 0.5
        if traits.target_class in {
            ImagingTargetClass.MOON,
            ImagingTargetClass.SUN,
        }:
            return cls._known_target_framing(
                traits,
                configuration,
                ideal_fill=_LUNAR_IDEAL_FRAME_FILL,
            )
        minimum_field = min(
            configuration.field_width_deg,
            configuration.field_height_deg,
        )
        if minimum_field >= 0.08:
            return 1.0
        if minimum_field >= 0.04:
            return 0.8
        if minimum_field >= 0.02:
            return 0.55
        return 0.25

    @classmethod
    def _known_target_framing(
        cls,
        traits: ImagingTargetTraits,
        configuration: ImagingTrainConfiguration,
        *,
        ideal_fill: float,
    ) -> float:
        target_major = traits.angular_size_major_deg
        target_minor = traits.angular_size_minor_deg
        if target_major is None or target_minor is None:
            return 0.5

        field_major = max(
            configuration.field_width_deg,
            configuration.field_height_deg,
        )
        field_minor = min(
            configuration.field_width_deg,
            configuration.field_height_deg,
        )
        safe_major = field_major * _FRAME_EDGE_MARGIN
        safe_minor = field_minor * _FRAME_EDGE_MARGIN
        overflow = max(
            target_major / safe_major,
            target_minor / safe_minor,
        )
        if overflow > 1.0:
            return cls._clamp(1.0 - (overflow - 1.0) * 1.5)

        fill = max(
            target_major / field_major,
            target_minor / field_minor,
        )
        return cls._log_closeness(
            fill,
            ideal_fill,
            penalty_per_stop=0.25,
        )

    @classmethod
    def _still_sampling(
        cls,
        traits: ImagingTargetTraits,
        configuration: ImagingTrainConfiguration,
    ) -> float:
        target_scale = 1.4
        if (
            traits.is_extended
            or traits.angular_size_major_deg is not None
            and traits.angular_size_major_deg >= 1.0
        ):
            target_scale = 2.0
        elif traits.target_class in {
            ImagingTargetClass.PLANETARY_NEBULA,
            ImagingTargetClass.STELLAR,
        }:
            target_scale = 0.75
        elif traits.target_class is ImagingTargetClass.GLOBULAR_CLUSTER:
            target_scale = 1.0
        elif traits.is_compact:
            target_scale = 0.9
        return cls._log_closeness(
            configuration.pixel_scale_arcsec_per_pixel,
            target_scale,
            penalty_per_stop=0.30,
        )

    @classmethod
    def _video_sampling(
        cls,
        traits: ImagingTargetTraits,
        configuration: ImagingTrainConfiguration,
    ) -> float:
        if configuration.camera.kind is ImagingCameraKind.CAMERA_BODY:
            return 0.5
        critical_factor = (
            _LUNAR_WHOLE_DISC_FOCAL_RATIO_PER_PIXEL
            if traits.target_class
            in {ImagingTargetClass.MOON, ImagingTargetClass.SUN}
            else _PLANETARY_CRITICAL_FOCAL_RATIO_PER_PIXEL
        )
        target_focal_ratio = (
            critical_factor * configuration.camera.pixel_size_um
        )
        return cls._log_closeness(
            configuration.effective_focal_ratio,
            target_focal_ratio,
            penalty_per_stop=0.32,
        )

    @classmethod
    def _planetary_aperture(
        cls,
        configuration: ImagingTrainConfiguration,
    ) -> float:
        return cls._piecewise_score(
            float(configuration.telescope.aperture_mm),
            (
                (40.0, 0.20),
                (60.0, 0.32),
                (80.0, 0.45),
                (100.0, 0.56),
                (130.0, 0.68),
                (160.0, 0.78),
                (200.0, 0.88),
                (250.0, 0.96),
                (300.0, 1.00),
            ),
        )

    @classmethod
    def _still_camera(
        cls,
        configuration: ImagingTrainConfiguration,
    ) -> float:
        camera = configuration.camera
        bit_depth = cls._clamp((camera.bit_depth - 8.0) / 8.0)
        if camera.kind is ImagingCameraKind.ASTRONOMY_CAMERA:
            role = {
                "DEEP_SKY": 1.0,
                "ALL_ROUND": 0.85,
                "PLANETARY": 0.45,
            }.get(camera.camera_class, 0.65)
            cooling = 1.0 if camera.cooled else 0.55
            return 0.45 * role + 0.35 * cooling + 0.20 * bit_depth

        body_role = 0.82
        bulb = 1.0 if camera.bulb_mode else 0.45
        live_view = 0.8 if camera.live_view else 0.5
        return (
            0.40 * body_role
            + 0.35 * bulb
            + 0.20 * bit_depth
            + 0.05 * live_view
        )

    @classmethod
    def _video_camera(
        cls,
        configuration: ImagingTrainConfiguration,
    ) -> float:
        camera = configuration.camera
        bit_depth = 0.5 + 0.5 * cls._clamp(
            (camera.bit_depth - 8.0) / 8.0
        )
        if camera.kind is ImagingCameraKind.ASTRONOMY_CAMERA:
            role = {
                "PLANETARY": 1.0,
                "ALL_ROUND": 0.90,
                "DEEP_SKY": 0.55,
            }.get(camera.camera_class, 0.70)
            shutter = {
                "GLOBAL": 1.0,
                "ROLLING": 0.85,
            }.get(camera.shutter_type, 0.75)
            return 0.70 * role + 0.15 * shutter + 0.15 * bit_depth

        video_known = (
            camera.video_width_px is not None
            and camera.video_height_px is not None
            and camera.video_fps is not None
        )
        live_view = 0.9 if camera.live_view else 0.5
        return (
            0.60 * 0.58
            + 0.20 * live_view
            + 0.20 * (1.0 if video_known else 0.6)
        )

    @classmethod
    def _frame_acquisition(
        cls,
        configuration: ImagingTrainConfiguration,
    ) -> float:
        camera = configuration.camera
        if camera.kind is ImagingCameraKind.ASTRONOMY_CAMERA:
            if camera.full_resolution_fps is None:
                return 0.5
            return cls._piecewise_score(
                camera.full_resolution_fps,
                (
                    (0.0, 0.10),
                    (10.0, 0.35),
                    (30.0, 0.65),
                    (60.0, 0.82),
                    (120.0, 1.0),
                ),
            )

        if camera.video_fps is None:
            fps_score = 0.5
        else:
            fps_score = cls._piecewise_score(
                camera.video_fps,
                (
                    (0.0, 0.10),
                    (24.0, 0.45),
                    (30.0, 0.55),
                    (60.0, 0.78),
                    (120.0, 1.0),
                ),
            )
        video_height = camera.video_height_px
        if video_height is None:
            resolution_score = 0.5
        elif video_height >= 2160:
            resolution_score = 1.0
        elif video_height >= 1080:
            resolution_score = 0.75
        else:
            resolution_score = 0.5
        return 0.75 * fps_score + 0.25 * resolution_score

    @classmethod
    def _still_capture_efficiency(
        cls,
        traits: ImagingTargetTraits,
        configuration: ImagingTrainConfiguration,
    ) -> float:
        reference_focal_ratio = (
            5.0
            if traits.is_extended
            or (
                traits.surface_brightness_proxy is not None
                and traits.surface_brightness_proxy >= 13.5
            )
            else 7.0
        )
        ratio = (
            configuration.effective_focal_ratio
            / reference_focal_ratio
        )
        speed = (
            1.0
            if ratio <= 1.0
            else cls._clamp(1.0 - math.log2(ratio) * 0.45)
        )

        modifier = configuration.modifier_kind
        if traits.reducer_preferred:
            modifier_score = {
                ImagingModifierKind.FOCAL_REDUCER: 1.0,
                ImagingModifierKind.NONE: 0.65,
                ImagingModifierKind.BARLOW: 0.15,
            }[modifier]
        elif traits.is_compact:
            modifier_score = {
                ImagingModifierKind.FOCAL_REDUCER: 0.75,
                ImagingModifierKind.NONE: 1.0,
                ImagingModifierKind.BARLOW: 0.70,
            }[modifier]
        else:
            modifier_score = {
                ImagingModifierKind.FOCAL_REDUCER: 0.85,
                ImagingModifierKind.NONE: 1.0,
                ImagingModifierKind.BARLOW: 0.35,
            }[modifier]
        return 0.75 * speed + 0.25 * modifier_score

    @staticmethod
    def _mount_score(
        configuration: ImagingTrainConfiguration,
        capture_mode: ImagingCaptureMode,
    ) -> float:
        mount_type = canonical_mount_type(configuration.mount_type)
        if capture_mode is ImagingCaptureMode.STILL:
            return {
                "EQUATORIAL_TRACKING": 1.0,
                "FORK_GOTO": 0.65,
                "ALTAZ_GOTO": 0.55,
                "DOBSONIAN_GOTO": 0.55,
                "EQUATORIAL_MANUAL": 0.35,
                "ALTAZ_PUSHTO": 0.20,
                "DOBSONIAN_PUSHTO": 0.20,
                "MANUAL_UNSPECIFIED": 0.15,
                "ALTAZ_MANUAL": 0.15,
                "DOBSONIAN_MANUAL": 0.15,
                "OTA": 0.10,
                "OTHER": 0.40,
            }.get(mount_type, 0.50)
        return {
            "EQUATORIAL_TRACKING": 1.0,
            "FORK_GOTO": 1.0,
            "ALTAZ_GOTO": 0.95,
            "DOBSONIAN_GOTO": 0.95,
            "EQUATORIAL_MANUAL": 0.80,
            "ALTAZ_PUSHTO": 0.70,
            "DOBSONIAN_PUSHTO": 0.70,
            "MANUAL_UNSPECIFIED": 0.65,
            "ALTAZ_MANUAL": 0.65,
            "DOBSONIAN_MANUAL": 0.65,
            "OTA": 0.40,
            "OTHER": 0.55,
        }.get(mount_type, 0.60)

    @staticmethod
    def _configuration_is_usable(
        configuration: ImagingTrainConfiguration,
    ) -> bool:
        physical_values = (
            configuration.effective_focal_length_mm,
            configuration.effective_focal_ratio,
            configuration.pixel_scale_arcsec_per_pixel,
            configuration.field_width_deg,
            configuration.field_height_deg,
        )
        if any(
            not math.isfinite(value) or value <= 0
            for value in physical_values
        ):
            return False
        remaining_backfocus = configuration.additional_backfocus_spacing_mm
        return (
            remaining_backfocus is None
            or remaining_backfocus >= -1e-6
        )

    @staticmethod
    def _ranking_key(
        candidate: ImagingRecommendationCandidate,
    ) -> tuple[float, int, str]:
        conservative_body_video_modifier_rank = 0
        if (
            candidate.capture_mode is ImagingCaptureMode.VIDEO
            and candidate.camera.kind is ImagingCameraKind.CAMERA_BODY
            and candidate.configuration.modifier_kind
            is not ImagingModifierKind.NONE
        ):
            conservative_body_video_modifier_rank = 1
        return (
            -candidate.score,
            conservative_body_video_modifier_rank,
            candidate.configuration.configuration_id,
        )

    @staticmethod
    def _unique_configurations(
        configurations: Iterable[ImagingTrainConfiguration],
    ) -> tuple[ImagingTrainConfiguration, ...]:
        unique: list[ImagingTrainConfiguration] = []
        seen: set[str] = set()
        for configuration in configurations:
            configuration_id = configuration.configuration_id.strip()
            if not configuration_id or configuration_id in seen:
                continue
            seen.add(configuration_id)
            unique.append(configuration)
        return tuple(unique)

    @staticmethod
    def _data_completeness(
        traits: ImagingTargetTraits,
        configuration: ImagingTrainConfiguration,
        capture_mode: ImagingCaptureMode,
    ) -> tuple[tuple[str, ...], float]:
        camera = configuration.camera
        checks: list[tuple[str, bool]] = [
            (
                "target_class",
                traits.target_class is not ImagingTargetClass.UNKNOWN,
            ),
            (
                "mount_type",
                canonical_mount_type(configuration.mount_type)
                in MOUNT_TYPE_LABELS,
            ),
            ("mechanical_connection", False),
            ("image_circle", False),
            ("seeing", False),
        ]
        if capture_mode is ImagingCaptureMode.STILL:
            checks.extend(
                (
                    (
                        "target_angular_size",
                        traits.has_known_angular_size,
                    ),
                    ("target_magnitude", traits.magnitude is not None),
                    ("sky_background", False),
                    ("tracking_accuracy", False),
                )
            )
            if camera.kind is ImagingCameraKind.ASTRONOMY_CAMERA:
                checks.append(("camera_class", bool(camera.camera_class)))
        else:
            if camera.kind is ImagingCameraKind.ASTRONOMY_CAMERA:
                checks.append(
                    (
                        "full_resolution_fps",
                        camera.full_resolution_fps is not None,
                    )
                )
            else:
                checks.extend(
                    (
                        ("video_fps", camera.video_fps is not None),
                        (
                            "video_resolution",
                            camera.video_width_px is not None
                            and camera.video_height_px is not None,
                        ),
                        ("video_active_sensor_area", False),
                        ("video_pixel_scale", False),
                    )
                )

        if configuration.reducer is not None:
            checks.extend(
                (
                    (
                        "reducer_backfocus",
                        configuration.required_backfocus_mm is not None,
                    ),
                    (
                        "camera_backfocus",
                        camera.backfocus_mm is not None,
                    ),
                )
            )
        missing = tuple(name for name, available in checks if not available)
        completeness = (
            sum(1 for _, available in checks if available) / len(checks)
            if checks
            else 1.0
        )
        return missing, completeness

    @staticmethod
    def _log_closeness(
        value: float,
        ideal: float,
        *,
        penalty_per_stop: float,
    ) -> float:
        if (
            not math.isfinite(value)
            or not math.isfinite(ideal)
            or value <= 0
            or ideal <= 0
        ):
            return 0.5
        return ImagingRecommendationService._clamp(
            1.0
            - abs(math.log2(value / ideal)) * penalty_per_stop
        )

    @staticmethod
    def _piecewise_score(
        value: float,
        points: tuple[tuple[float, float], ...],
    ) -> float:
        if not math.isfinite(value):
            return 0.5
        if value <= points[0][0]:
            return points[0][1]
        for (left_x, left_y), (right_x, right_y) in zip(
            points,
            points[1:],
        ):
            if value <= right_x:
                position = (value - left_x) / (right_x - left_x)
                return left_y + position * (right_y - left_y)
        return points[-1][1]

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))
