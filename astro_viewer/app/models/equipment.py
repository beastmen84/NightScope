from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from astro_viewer.app.services.localization import format_compact_number, tr


@dataclass(frozen=True)
class IntegratedImagingSystem:
    """Primary astronomical imaging channel built into a smart telescope."""

    sensor_model: str = ""
    sensor_width_mm: float | None = None
    sensor_height_mm: float | None = None
    resolution_width_px: int | None = None
    resolution_height_px: int | None = None
    pixel_size_um: float | None = None
    bit_depth: int | None = None
    color_mode: str = ""
    full_resolution_fps: float | None = None
    supports_live_stacking: bool = False
    supports_video: bool = False
    supports_mosaic: bool = False
    exposure_control_mode: str = "DEVICE_MANAGED"
    filter_codes: tuple[str, ...] = ()
    specification_source_url: str = ""

    @property
    def has_complete_sensor_geometry(self) -> bool:
        positive_values = (
            self.sensor_width_mm,
            self.sensor_height_mm,
            self.resolution_width_px,
            self.resolution_height_px,
            self.pixel_size_um,
            self.bit_depth,
        )
        try:
            positive_values_are_valid = all(
                value is not None
                and not isinstance(value, bool)
                and math.isfinite(float(value))
                and float(value) > 0
                for value in positive_values
            )
            integer_values_are_valid = all(
                value is not None
                and not isinstance(value, bool)
                and float(value).is_integer()
                for value in (
                    self.resolution_width_px,
                    self.resolution_height_px,
                    self.bit_depth,
                )
            )
            optional_fps_is_valid = (
                self.full_resolution_fps is None
                or (
                    not isinstance(self.full_resolution_fps, bool)
                    and math.isfinite(float(self.full_resolution_fps))
                    and float(self.full_resolution_fps) > 0
                )
            )
        except (TypeError, ValueError):
            positive_values_are_valid = False
            integer_values_are_valid = False
            optional_fps_is_valid = False
        return (
            bool(self.sensor_model.strip())
            and self.color_mode in {"COLOR", "MONO"}
            and self.exposure_control_mode
            in {"DEVICE_MANAGED", "USER_CONFIGURABLE"}
            and positive_values_are_valid
            and integer_values_are_valid
            and optional_fps_is_valid
        )


@dataclass(frozen=True)
class Telescope:
    id: str
    name: str
    aperture_mm: int
    focal_length_mm: int
    optical_type: str
    mount: str
    instrument_category: str = "TRADITIONAL"
    supports_optical_visual: bool | None = None
    supports_interchangeable_eyepieces: bool | None = None
    supports_external_cameras: bool | None = None
    supports_external_optical_modifiers: bool | None = None
    integrated_imaging: IntegratedImagingSystem | None = None

    def __post_init__(self) -> None:
        default_capability = not self.is_smart_integrated
        for field_name in (
            "supports_optical_visual",
            "supports_interchangeable_eyepieces",
            "supports_external_cameras",
            "supports_external_optical_modifiers",
        ):
            if getattr(self, field_name) is None:
                object.__setattr__(
                    self,
                    field_name,
                    default_capability,
                )

    @property
    def is_smart_integrated(self) -> bool:
        return self.instrument_category == "SMART_INTEGRATED"

    @property
    def has_complete_integrated_imaging(self) -> bool:
        return (
            self.is_smart_integrated
            and self.integrated_imaging is not None
            and self.integrated_imaging.has_complete_sensor_geometry
        )

    def to_qml(self) -> dict:
        data = asdict(self)
        data["apertureMm"] = self.aperture_mm
        data["focalLengthMm"] = self.focal_length_mm
        data["type"] = self.optical_type
        data["instrumentCategory"] = self.instrument_category
        data["isSmartIntegrated"] = self.is_smart_integrated
        data["supportsOpticalVisual"] = self.supports_optical_visual
        data["supportsInterchangeableEyepieces"] = (
            self.supports_interchangeable_eyepieces
        )
        data["supportsExternalCameras"] = self.supports_external_cameras
        data["supportsExternalOpticalModifiers"] = (
            self.supports_external_optical_modifiers
        )
        data["hasCompleteIntegratedImaging"] = (
            self.has_complete_integrated_imaging
        )
        return data


@dataclass(frozen=True)
class Eyepiece:
    id: str
    name: str
    focal_length_mm: float
    apparent_field_deg: float
    eyepiece_type: str = "Fixed"
    min_focal_length_mm: float | None = None
    max_focal_length_mm: float | None = None
    zoom_click_positions_mm: tuple[float, ...] = ()

    def to_qml(self) -> dict:
        data = asdict(self)
        data["focalLengthMm"] = self.focal_length_mm
        data["apparentFieldDeg"] = self.apparent_field_deg
        data["type"] = self.eyepiece_type
        data["minFocalLengthMm"] = self.min_focal_length_mm or self.focal_length_mm
        data["maxFocalLengthMm"] = self.max_focal_length_mm or self.focal_length_mm
        data["zoomClickPositionsMm"] = list(self.zoom_click_positions_mm)
        if self.eyepiece_type == "Zoom":
            data["focalRangeLabel"] = tr(
                "{minimum}-{maximum} mm",
                minimum=format_compact_number(data["minFocalLengthMm"]),
                maximum=format_compact_number(data["maxFocalLengthMm"]),
            )
        else:
            data["focalRangeLabel"] = tr(
                "{value} mm",
                value=format_compact_number(self.focal_length_mm),
            )
        return data


@dataclass(frozen=True)
class Barlow:
    id: str
    name: str
    multiplier: float

    def to_qml(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Binocular:
    id: str
    name: str
    magnification: int
    objective_diameter_mm: int
    image_stabilized: bool = False

    def to_qml(self) -> dict:
        data = asdict(self)
        data["objectiveDiameterMm"] = self.objective_diameter_mm
        data["imageStabilized"] = self.image_stabilized
        data["specLabel"] = f"{self.magnification}×{self.objective_diameter_mm}"
        return data


@dataclass(frozen=True)
class OpticalFilter:
    id: str
    name: str
    filter_class: str
    central_wavelength_nm: float | None = None
    bandwidth_nm: float | None = None
    transmission_pct: float | None = None
    minimum_aperture_mm: int | None = None

    def to_qml(self) -> dict:
        data = asdict(self)
        data["filterClass"] = self.filter_class
        data["centralWavelengthNm"] = self.central_wavelength_nm
        data["bandwidthNm"] = self.bandwidth_nm
        data["transmissionPct"] = self.transmission_pct
        data["minimumApertureMm"] = self.minimum_aperture_mm
        return data


@dataclass(frozen=True)
class FocalReducer:
    id: str
    name: str
    reduction_factor: float
    optical_system: str
    connection: str = ""
    backfocus_mm: float | None = None
    visual_compatible: bool = False
    imaging_compatible: bool = True
    corrected_field: bool = False
    compatible_telescope_ids: tuple[str, ...] = ()
    compatible_telescope_names: tuple[str, ...] = ()

    def to_qml(self) -> dict:
        data = asdict(self)
        data["reductionFactor"] = self.reduction_factor
        data["opticalSystem"] = self.optical_system
        data["backfocusMm"] = self.backfocus_mm
        data["visualCompatible"] = self.visual_compatible
        data["imagingCompatible"] = self.imaging_compatible
        data["correctedField"] = self.corrected_field
        data["compatibleTelescopeIds"] = list(self.compatible_telescope_ids)
        data["compatibleTelescopeNames"] = list(self.compatible_telescope_names)
        return data


@dataclass(frozen=True)
class BeginnerPreset:
    id: str
    name: str
    target: str
    description: str
    suggested_objects: str

    def to_qml(self) -> dict:
        data = asdict(self)
        data["suggestedObjects"] = self.suggested_objects
        return data
