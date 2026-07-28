from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from astro_viewer.app.models.equipment import Barlow, FocalReducer, Telescope


class ImagingCameraKind(StrEnum):
    ASTRONOMY_CAMERA = "astronomy_camera"
    CAMERA_BODY = "camera_body"
    SMART_INTEGRATED = "smart_integrated"


class ImagingModifierKind(StrEnum):
    NONE = "none"
    FOCAL_REDUCER = "focal_reducer"
    BARLOW = "barlow"


@dataclass(frozen=True)
class ImagingCamera:
    """Normalized camera specification used by the photographic domain."""

    id: str
    name: str
    kind: ImagingCameraKind
    sensor_width_mm: float
    sensor_height_mm: float
    resolution_width_px: int
    resolution_height_px: int
    pixel_size_um: float
    bit_depth: int
    camera_class: str = ""
    sensor_technology: str = ""
    color_mode: str = ""
    full_resolution_fps: float | None = None
    cooled: bool = False
    cooling_delta_c: float | None = None
    shutter_type: str = ""
    backfocus_mm: float | None = None
    body_type: str = ""
    sensor_format: str = ""
    lens_mount: str = ""
    video_width_px: int | None = None
    video_height_px: int | None = None
    video_fps: float | None = None
    live_view: bool = False
    bulb_mode: bool = False
    supports_live_stacking: bool = False
    supports_video: bool = False
    supports_mosaic: bool = False
    exposure_control_mode: str = "USER_CONFIGURABLE"
    integrated_filter_codes: tuple[str, ...] = ()

    @property
    def sensor_diagonal_mm(self) -> float:
        return math.hypot(self.sensor_width_mm, self.sensor_height_mm)

    @property
    def is_dedicated_astronomy_camera(self) -> bool:
        return self.kind in {
            ImagingCameraKind.ASTRONOMY_CAMERA,
            ImagingCameraKind.SMART_INTEGRATED,
        }

    @property
    def is_device_managed(self) -> bool:
        return self.exposure_control_mode == "DEVICE_MANAGED"


@dataclass(frozen=True)
class ImagingTrainConfiguration:
    """One target-agnostic telescope/camera photographic configuration."""

    configuration_id: str
    telescope: Telescope
    camera: ImagingCamera
    modifier_kind: ImagingModifierKind
    focal_length_factor: float
    effective_focal_length_mm: float
    effective_focal_ratio: float
    pixel_scale_arcsec_per_pixel: float
    field_width_deg: float
    field_height_deg: float
    field_diagonal_deg: float
    reducer: FocalReducer | None = None
    barlow: Barlow | None = None

    @property
    def mount_type(self) -> str:
        return self.telescope.mount

    @property
    def required_backfocus_mm(self) -> float | None:
        if self.reducer is None:
            return None
        value = self.reducer.backfocus_mm
        if value is None or not math.isfinite(value) or value <= 0:
            return None
        return value

    @property
    def additional_backfocus_spacing_mm(self) -> float | None:
        required = self.required_backfocus_mm
        camera_backfocus = self.camera.backfocus_mm
        if (
            required is None
            or camera_backfocus is None
            or not math.isfinite(camera_backfocus)
            or camera_backfocus <= 0
        ):
            return None
        return required - camera_backfocus
