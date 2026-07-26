from __future__ import annotations

from dataclasses import asdict, dataclass

from astro_viewer.app.services.localization import format_compact_number, tr


@dataclass(frozen=True)
class Telescope:
    id: str
    name: str
    aperture_mm: int
    focal_length_mm: int
    optical_type: str
    mount: str

    def to_qml(self) -> dict:
        data = asdict(self)
        data["apertureMm"] = self.aperture_mm
        data["focalLengthMm"] = self.focal_length_mm
        data["type"] = self.optical_type
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
