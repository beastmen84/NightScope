from __future__ import annotations

import math
from typing import Protocol, TypedDict

from astro_viewer.app.models.equipment import Barlow, Eyepiece, Telescope
from astro_viewer.app.services.barlow_equivalence import (
    optically_distinct_barlows,
)
from astro_viewer.app.services.localization import (
    format_compact_number,
    tr,
)


NAKED_EYE_ID = "preset:naked-eye"


class FocalPosition(TypedDict):
    focal: float
    position: str


class TelescopeConfigurationValues(TypedDict):
    magnification: float
    true_field_of_view_deg: float
    exit_pupil_mm: float
    limiting_magnitude_estimate: float
    resolution_estimate: float


class EquipmentConfigurationPort(Protocol):
    """Minimal optical-calculation contract used by configuration builders."""

    def can_use_eyepieces(self, telescope: Telescope) -> bool: ...

    def barlow_options(self, barlows: list[Barlow]) -> list[Barlow | None]: ...

    def eyepiece_focal_positions(
        self,
        eyepiece: Eyepiece,
        ideal_focal_mm: float | None = None,
    ) -> list[FocalPosition]: ...

    def telescope_configuration_values(
        self,
        telescope: Telescope,
        eyepiece: Eyepiece,
        focal_mm: float,
        barlow: Barlow | None = None,
        barlow_multiplier: float | None = None,
    ) -> TelescopeConfigurationValues: ...


class EquipmentConfigurationService:
    """Owns target-neutral optical configuration calculations."""

    NAKED_EYE_ID = NAKED_EYE_ID

    def barlow_options(
        self,
        barlows: list[Barlow],
    ) -> list[Barlow | None]:
        owned = [barlow for barlow in barlows if barlow.multiplier > 1.0]
        return [None, *optically_distinct_barlows(owned)]

    def eyepiece_focal_positions(
        self,
        eyepiece: Eyepiece,
        ideal_focal_mm: float | None = None,
    ) -> list[FocalPosition]:
        del ideal_focal_mm
        if eyepiece.eyepiece_type != "Zoom":
            return [
                {
                    "focal": eyepiece.focal_length_mm,
                    "position": tr(
                        "{value} mm",
                        value=format_compact_number(
                            eyepiece.focal_length_mm
                        ),
                    ),
                }
            ]
        minimum = eyepiece.min_focal_length_mm or min(
            eyepiece.focal_length_mm,
            eyepiece.max_focal_length_mm or eyepiece.focal_length_mm,
        )
        maximum = eyepiece.max_focal_length_mm or max(
            eyepiece.focal_length_mm,
            minimum,
        )
        low = min(minimum, maximum)
        high = max(minimum, maximum)
        click_positions = [
            position
            for position in eyepiece.zoom_click_positions_mm
            if low <= position <= high
        ]
        candidates = click_positions or [high, (low + high) / 2, low]
        positions: list[FocalPosition] = []
        seen = set()
        for value in candidates:
            rounded = round(value, 1)
            key = round(rounded, 1)
            if key in seen:
                continue
            seen.add(key)
            positions.append(
                {
                    "focal": rounded,
                    "position": tr(
                        "{value} mm",
                        value=format_compact_number(rounded),
                    ),
                }
            )
        return positions

    def telescope_configuration_values(
        self,
        telescope: Telescope,
        eyepiece: Eyepiece,
        focal_mm: float,
        barlow: Barlow | None = None,
        barlow_multiplier: float | None = None,
    ) -> TelescopeConfigurationValues:
        multiplier = (
            barlow_multiplier
            if barlow_multiplier is not None
            else barlow.multiplier
            if barlow
            else 1.0
        )
        magnification = (telescope.focal_length_mm / focal_mm) * multiplier
        return {
            "magnification": magnification,
            "true_field_of_view_deg": (
                eyepiece.apparent_field_deg / magnification
            ),
            "exit_pupil_mm": telescope.aperture_mm / magnification,
            "limiting_magnitude_estimate": (
                2 + 5 * self._log10(max(1.0, telescope.aperture_mm))
            ),
            "resolution_estimate": 116 / telescope.aperture_mm,
        }

    def has_optical_telescope(self, telescope: Telescope) -> bool:
        return (
            telescope.id != self.NAKED_EYE_ID
            and telescope.aperture_mm > 0
            and telescope.focal_length_mm > 0
        )

    def can_use_eyepieces(self, telescope: Telescope) -> bool:
        return bool(
            self.has_optical_telescope(telescope)
            and telescope.supports_optical_visual
            and telescope.supports_interchangeable_eyepieces
        )

    @staticmethod
    def _log10(value: float) -> float:
        return math.log10(value)
