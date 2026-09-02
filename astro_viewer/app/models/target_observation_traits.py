"""Normalize catalogue targets into optical observation traits."""

from __future__ import annotations

from dataclasses import dataclass

from astro_viewer.app.models.observing import CelestialObject


ALLOWED_OBSERVATION_TYPES = {"WideField", "General", "HighMagnification"}
PLANETARY_OR_LUNAR_IDS = {"moon", "mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"}
SUPERNOVA_REMNANT_TYPE_FRAGMENTS = (
    "supernova remnant",
    "resto di supernova",
    "remanente di supernova",
)


def is_supernova_remnant_type(object_type: str) -> bool:
    normalized = object_type.casefold()
    return any(fragment in normalized for fragment in SUPERNOVA_REMNANT_TYPE_FRAGMENTS)


@dataclass(frozen=True)
class TargetObservationTraits:
    object_type: str
    object_type_lower: str
    magnitude: float | None
    apparent_size_arcmin: float | None
    profile_size_arcmin: float | None
    angular_size_deg: float | None
    max_angular_size_deg: float | None
    max_altitude_deg: float
    recommended_observation_type: str
    surface_brightness_proxy: float | None
    is_wide_field: bool
    is_high_magnification: bool
    is_general: bool
    is_planetary_or_lunar: bool
    is_deep_sky: bool

    @classmethod
    def from_object(cls, celestial_object: CelestialObject) -> TargetObservationTraits:
        object_type = celestial_object.object_type
        object_type_lower = object_type.lower()
        magnitude = _parse_magnitude(celestial_object.magnitude)
        apparent_size_arcmin = _parse_apparent_size_arcmin(celestial_object.apparent_size)
        profile_size_arcmin = _parse_profile_size_arcmin(celestial_object.apparent_size)
        max_angular_size_deg = _positive_or_none(celestial_object.max_angular_size_deg)
        angular_size_deg = max_angular_size_deg or _parse_angular_size_deg(celestial_object.apparent_size)
        max_altitude_deg = _parse_altitude(celestial_object.max_altitude)
        is_planetary_or_lunar = (
            celestial_object.id in PLANETARY_OR_LUNAR_IDS
            or "pianeta" in object_type_lower
            or "luna" in object_type_lower
        )
        recommended_observation_type = _recommended_observation_type(
            celestial_object,
            object_type_lower,
            angular_size_deg,
        )
        surface_brightness_proxy = _surface_brightness_proxy(magnitude, apparent_size_arcmin)
        is_deep_sky = not is_planetary_or_lunar and (
            is_supernova_remnant_type(object_type_lower)
            or any(
                fragment in object_type_lower
                for fragment in (
                    "galaxy",
                    "galassia",
                    "nebula",
                    "nebul",
                    "cluster",
                    "ammasso",
                    "globular",
                    "asterism",
                    "star",
                    "double",
                    "unclassified object",
                )
            )
        )
        return cls(
            object_type=object_type,
            object_type_lower=object_type_lower,
            magnitude=magnitude,
            apparent_size_arcmin=apparent_size_arcmin,
            profile_size_arcmin=profile_size_arcmin,
            angular_size_deg=angular_size_deg,
            max_angular_size_deg=max_angular_size_deg,
            max_altitude_deg=max_altitude_deg,
            recommended_observation_type=recommended_observation_type,
            surface_brightness_proxy=surface_brightness_proxy,
            is_wide_field=recommended_observation_type == "WideField",
            is_high_magnification=recommended_observation_type == "HighMagnification",
            is_general=recommended_observation_type == "General",
            is_planetary_or_lunar=is_planetary_or_lunar,
            is_deep_sky=is_deep_sky,
        )


def _recommended_observation_type(
    celestial_object: CelestialObject,
    object_type_lower: str,
    angular_size_deg: float | None,
) -> str:
    configured = celestial_object.recommended_observation_type.strip()
    if configured in ALLOWED_OBSERVATION_TYPES:
        return configured
    if celestial_object.id in PLANETARY_OR_LUNAR_IDS:
        return "HighMagnification"
    if "planetary nebula" in object_type_lower or "nebulosa planetaria" in object_type_lower:
        return "HighMagnification"
    if angular_size_deg and angular_size_deg >= 1.0:
        return "WideField"
    if "open" in object_type_lower or "ammasso aperto" in object_type_lower:
        return "WideField"
    return "General"


def _parse_angular_size_deg(value: str) -> float | None:
    value = value.strip().lower()
    if not value:
        return None
    numbers = _numbers_from_angular_text(value)
    if not numbers:
        return None
    maximum = max(numbers)
    if "arcsec" in value or "″" in value or '"' in value:
        return maximum / 3600.0
    if "deg" in value or "degree" in value or "gradi" in value or "°" in value:
        return maximum
    return maximum / 60.0


def _parse_apparent_size_arcmin(value: str) -> float | None:
    cleaned = value.strip().lower().replace(",", ".")
    if not cleaned:
        return None
    numbers = _numbers_from_angular_text(cleaned)
    if not numbers:
        return None
    size = max(numbers)
    if "arcsec" in cleaned or "″" in cleaned or '"' in cleaned:
        return size / 60.0
    if "deg" in cleaned or "degree" in cleaned or "gradi" in cleaned or "°" in cleaned:
        return size * 60.0
    return size


def _parse_profile_size_arcmin(value: str) -> float | None:
    if not value:
        return None
    cleaned = value.lower().replace("arcmin", "'").replace("′", "'").replace("x", " ")
    numbers = []
    for token in cleaned.replace(",", ".").replace("'", " ").replace('"', " ").split():
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    if not numbers:
        return None
    return max(numbers)


def _numbers_from_angular_text(value: str) -> list[float]:
    cleaned = (
        value.replace(",", ".")
        .replace("×", " ")
        .replace("x", " ")
        .replace("arcsec", " ")
        .replace("arcmin", " ")
        .replace("gradi", " ")
        .replace("degrees", " ")
        .replace("degree", " ")
        .replace("deg", " ")
        .replace("°", " ")
        .replace("′", " ")
        .replace("'", " ")
        .replace("″", " ")
        .replace('"', " ")
    )
    numbers = []
    for token in cleaned.split():
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    return numbers


def _surface_brightness_proxy(magnitude: float | None, apparent_size_arcmin: float | None) -> float | None:
    if magnitude is None or not apparent_size_arcmin or apparent_size_arcmin <= 0:
        return None
    return magnitude + 2.5 * _log10(max(apparent_size_arcmin * apparent_size_arcmin, 1.0))


def _positive_or_none(value: float | None) -> float | None:
    if value and value > 0:
        return value
    return None


def _parse_magnitude(value: str) -> float | None:
    try:
        return float(value.split("/")[0].strip().replace(",", "."))
    except (ValueError, IndexError):
        return None


def _parse_altitude(value: str) -> float:
    numbers = _numbers_from_angular_text(value.strip().lower())
    return numbers[0] if numbers else 0.0


def _log10(value: float) -> float:
    import math

    return math.log10(value)
