"""Represent one concrete visual-observation equipment configuration."""

from __future__ import annotations

from dataclasses import dataclass

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope


@dataclass(frozen=True)
class ObservationConfiguration:
    configuration_id: str
    equipment_type: str
    magnification: float
    exit_pupil_mm: float
    true_field_of_view_deg: float | None = None
    limiting_magnitude_estimate: float | None = None
    resolution_estimate: float | None = None
    image_stabilized: bool = False
    telescope: Telescope | None = None
    eyepiece: Eyepiece | None = None
    barlow: Barlow | None = None
    binocular: Binocular | None = None
    focal_position_mm: float | None = None
    focal_position_label: str = ""
