"""Represent a scored visual-equipment recommendation candidate."""

from __future__ import annotations

from dataclasses import dataclass

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.observation_configuration import ObservationConfiguration
from astro_viewer.app.services.localization import tr


@dataclass(frozen=True)
class RecommendationCandidate:
    configuration: ObservationConfiguration
    score: float
    label: str
    detail_label: str
    multiplier: float = 1.0
    barlow_label: str = tr("No")
    telescope_name: str = ""

    @property
    def equipment_type(self) -> str:
        return self.configuration.equipment_type

    @property
    def setup_type(self) -> str:
        if self.equipment_type == "Binocular":
            return "binocular"
        if self.equipment_type == "Telescope":
            return "telescope"
        return self.equipment_type.lower()

    @property
    def telescope(self) -> Telescope | None:
        return self.configuration.telescope

    @property
    def eyepiece(self) -> Eyepiece | None:
        return self.configuration.eyepiece

    @property
    def barlow(self) -> Barlow | None:
        return self.configuration.barlow

    @property
    def binocular(self) -> Binocular | None:
        return self.configuration.binocular

    @property
    def focal_position(self) -> str:
        return self.configuration.focal_position_label

    @property
    def focal_mm(self) -> float | None:
        return self.configuration.focal_position_mm

    @property
    def magnification(self) -> float:
        return self.configuration.magnification

    @property
    def true_field(self) -> float | None:
        return self.configuration.true_field_of_view_deg

    @property
    def exit_pupil(self) -> float:
        return self.configuration.exit_pupil_mm
