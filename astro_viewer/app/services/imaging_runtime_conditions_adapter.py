from __future__ import annotations

import math
import re

from astro_viewer.app.models.condition_inputs import MoonGeometryConditionInput
from astro_viewer.app.models.imaging_exposure import (
    ImagingSessionConditions,
)
from astro_viewer.app.models.imaging_runtime import ImagingRuntimeConditions
from astro_viewer.app.models.imaging_video_capture import (
    ImagingVideoSessionConditions,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality


_NUMBER_PATTERN = re.compile(r"-?\d+(?:[.,]\d+)?")


class ImagingRuntimeConditionsAdapter:
    """Maps current observing facts without reusing conditioned visual scores."""

    @classmethod
    def from_runtime(
        cls,
        target: CelestialObject,
        *,
        sky_quality: SkyQuality | None = None,
        seeing_transparency: SeeingTransparency | None = None,
        moon: MoonSummary | None = None,
        moon_geometry: MoonGeometryConditionInput | None = None,
    ) -> ImagingRuntimeConditions:
        transparency_score = None
        seeing_score = None
        if seeing_transparency is not None:
            transparency_score = (
                seeing_transparency.atmospheric_transparency_score
                if seeing_transparency.atmospheric_transparency_score
                is not None
                else seeing_transparency.transparency_score
            )
            seeing_score = seeing_transparency.seeing_score

        return ImagingRuntimeConditions(
            still=ImagingSessionConditions(
                sky_brightness_mag_arcsec2=(
                    sky_quality.sky_brightness
                    if sky_quality is not None
                    else None
                ),
                bortle_class=(
                    sky_quality.bortle_class
                    if sky_quality is not None
                    else None
                ),
                transparency_score=transparency_score,
                target_current_altitude_deg=(
                    target.current_altitude_degrees
                ),
                target_maximum_altitude_deg=(
                    cls._degrees_value(target.max_altitude)
                ),
                moon_illumination_fraction=(
                    cls._moon_illumination_fraction(moon)
                ),
                moon_altitude_deg=(
                    moon_geometry.moon_altitude_deg
                    if moon_geometry is not None
                    else None
                ),
                moon_target_separation_deg=(
                    moon_geometry.moon_target_separation_deg
                    if moon_geometry is not None
                    else None
                ),
                moon_visible_during_target_window=(
                    moon_geometry.moon_visible_during_target_window
                    if moon_geometry is not None
                    else None
                ),
            ),
            video=ImagingVideoSessionConditions(
                achievable_fps=None,
                seeing_score=seeing_score,
                target_altitude_deg=target.current_altitude_degrees,
            ),
        )

    @staticmethod
    def _moon_illumination_fraction(
        moon: MoonSummary | None,
    ) -> float | None:
        if moon is None:
            return None
        text = str(moon.illumination or "").strip()
        match = _NUMBER_PATTERN.search(text)
        if match is None:
            return None
        try:
            value = float(match.group(0).replace(",", "."))
        except ValueError:
            return None
        if not math.isfinite(value):
            return None
        if "%" in text or value > 1.0:
            value /= 100.0
        if not 0.0 <= value <= 1.0:
            return None
        return value

    @staticmethod
    def _degrees_value(text: object) -> float | None:
        match = _NUMBER_PATTERN.search(str(text or ""))
        if match is None:
            return None
        try:
            value = float(match.group(0).replace(",", "."))
        except ValueError:
            return None
        if not math.isfinite(value) or not -90.0 <= value <= 90.0:
            return None
        return value
