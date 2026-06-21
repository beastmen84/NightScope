from __future__ import annotations

from dataclasses import asdict, dataclass


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
    barrel_size: str = ""

    def to_qml(self) -> dict:
        data = asdict(self)
        data["focalLengthMm"] = self.focal_length_mm
        data["apparentFieldDeg"] = self.apparent_field_deg
        data["barrelSize"] = self.barrel_size
        return data


@dataclass(frozen=True)
class Barlow:
    id: str
    name: str
    multiplier: float
    barrel_size: str = ""

    def to_qml(self) -> dict:
        data = asdict(self)
        data["barrelSize"] = self.barrel_size
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
