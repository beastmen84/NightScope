"""Carry immutable atmosphere, Moon, seeing, and sky-condition inputs."""

from __future__ import annotations

from dataclasses import dataclass

from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality


@dataclass(frozen=True)
class AodConditionInput:
    available: bool = False
    freshness_category: str = "unavailable"
    aod_550: float | None = None
    source: str = ""
    product: str = ""
    status: str = "unavailable"
    age_days: float | None = None
    uncertainty: float | None = None
    qa_raw: int | None = None
    method: str = ""
    local_valid_pixel_count: int | None = None
    neighborhood_radius_pixels: int | None = None
    nearest_valid_pixel_distance_km: float | None = None


@dataclass(frozen=True)
class ParticulateConditionInput:
    available: bool = False
    freshness_category: str = "unavailable"
    pm25: float | None = None
    pm10: float | None = None
    source: str = ""
    status: str = "unavailable"
    age_days: float | None = None
    distance_km: float | None = None


@dataclass(frozen=True)
class MoonGeometryConditionInput:
    """Target-specific Moon geometry used by the canonical NSOM environment."""

    moon_altitude_deg: float | None = None
    moon_target_separation_deg: float | None = None
    moon_above_horizon: bool | None = None
    moon_visible_during_target_window: bool | None = None
    moon_set_before_target_window: bool | None = None


@dataclass(frozen=True)
class ObservationConditionInputs:
    """Immutable input boundary for canonical observing-condition services."""

    moon: MoonSummary | None = None
    sky_quality: SkyQuality | None = None
    seeing: SeeingTransparency | None = None
    aod: AodConditionInput | None = None
    particulate: ParticulateConditionInput | None = None
    moon_geometry: MoonGeometryConditionInput | None = None
