from __future__ import annotations

import math
import re

from astro_viewer.app.models.imaging_recommendation import (
    ImagingCaptureMode,
    ImagingTargetClass,
    ImagingTargetTraits,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.target_observation_traits import (
    TargetObservationTraits,
)


_SUN_IDS = frozenset({"sun", "sole", "sol"})
_MOON_IDS = frozenset({"moon", "luna"})
_PLANET_IDS = frozenset(
    {
        "mercury",
        "mercurio",
        "venus",
        "venere",
        "mars",
        "marte",
        "jupiter",
        "giove",
        "saturn",
        "saturno",
        "uranus",
        "urano",
        "neptune",
        "nettuno",
        "neptuno",
    }
)
_ANGULAR_NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")
_DEFAULT_MOON_DIAMETER_DEG = 0.52
_SOLAR_FILTER_REASON = "certified_solar_filter_not_modeled"


class ImagingTargetTraitsAdapter:
    """Builds the photographic target contract from a runtime target."""

    @classmethod
    def from_object(
        cls,
        target: CelestialObject,
    ) -> ImagingTargetTraits:
        observation_traits = TargetObservationTraits.from_object(target)
        target_class = cls._target_class(target)
        major_deg, minor_deg = cls._angular_dimensions(
            target.apparent_size,
            target.max_angular_size_deg,
        )
        if target_class is ImagingTargetClass.MOON and major_deg is None:
            major_deg = _DEFAULT_MOON_DIAMETER_DEG
            minor_deg = _DEFAULT_MOON_DIAMETER_DEG

        supported = target_class is not ImagingTargetClass.SUN
        capture_mode = (
            None
            if not supported
            else ImagingCaptureMode.VIDEO
            if target_class
            in {ImagingTargetClass.MOON, ImagingTargetClass.PLANET}
            else ImagingCaptureMode.STILL
        )
        return ImagingTargetTraits(
            target_id=target.id.strip(),
            name=target.name.strip(),
            target_class=target_class,
            recommended_capture_mode=capture_mode,
            magnitude=observation_traits.magnitude,
            angular_size_major_deg=major_deg,
            angular_size_minor_deg=minor_deg,
            surface_brightness_proxy=(
                observation_traits.surface_brightness_proxy
            ),
            reducer_preferred=bool(target.imaging_reducer_recommended),
            recommendation_supported=supported,
            unsupported_reason_code=(
                "" if supported else _SOLAR_FILTER_REASON
            ),
        )

    @staticmethod
    def _target_class(target: CelestialObject) -> ImagingTargetClass:
        target_id = target.id.strip().casefold()
        if target_id in _SUN_IDS:
            return ImagingTargetClass.SUN
        if target_id in _MOON_IDS:
            return ImagingTargetClass.MOON
        if target_id in _PLANET_IDS:
            return ImagingTargetClass.PLANET

        text = (
            f"{target.object_type} {target.name}"
            .strip()
            .casefold()
        )
        if any(value in text for value in ("comet", "cometa")):
            return ImagingTargetClass.COMET
        if any(
            value in text
            for value in (
                "planetary nebula",
                "nebulosa planetaria",
            )
        ):
            return ImagingTargetClass.PLANETARY_NEBULA
        if any(value in text for value in ("globular", "globulare")):
            return ImagingTargetClass.GLOBULAR_CLUSTER
        if any(
            value in text
            for value in (
                "open cluster",
                "ammasso aperto",
                "cumulo abierto",
                "cúmulo abierto",
                "star cloud",
                "asterism",
                "asterismo",
            )
        ):
            return ImagingTargetClass.OPEN_CLUSTER
        if any(
            value in text
            for value in ("galaxy", "galassia", "galaxia")
        ):
            return ImagingTargetClass.GALAXY
        if any(
            value in text
            for value in (
                "nebula",
                "nebulosa",
                "supernova remnant",
                "resto di supernova",
                "remanente de supernova",
            )
        ):
            return ImagingTargetClass.DIFFUSE_NEBULA
        if any(
            value in text
            for value in (
                "double",
                "doppia",
                "doble",
                "star",
                "stella",
                "estrella",
                "unclassified object",
            )
        ):
            return ImagingTargetClass.STELLAR
        if any(value in text for value in ("planet", "pianeta")):
            return ImagingTargetClass.PLANET
        return ImagingTargetClass.UNKNOWN

    @staticmethod
    def _angular_dimensions(
        value: str,
        canonical_major_deg: float | None,
    ) -> tuple[float | None, float | None]:
        cleaned = value.strip().casefold()
        numbers = [
            float(match.group(0).replace(",", "."))
            for match in _ANGULAR_NUMBER_PATTERN.finditer(cleaned)
        ]
        positive_numbers = sorted(
            (
                number
                for number in numbers
                if math.isfinite(number) and number > 0
            ),
            reverse=True,
        )
        parsed_major: float | None = None
        parsed_minor: float | None = None
        if positive_numbers:
            multiplier = ImagingTargetTraitsAdapter._angular_unit_deg(
                cleaned
            )
            parsed_major = positive_numbers[0] * multiplier
            parsed_minor = (
                positive_numbers[1] * multiplier
                if len(positive_numbers) > 1
                else parsed_major
            )

        canonical_major = (
            float(canonical_major_deg)
            if canonical_major_deg is not None
            and math.isfinite(float(canonical_major_deg))
            and float(canonical_major_deg) > 0
            else None
        )
        if canonical_major is None:
            return parsed_major, parsed_minor
        if parsed_major is None or parsed_minor is None:
            return canonical_major, canonical_major
        aspect_ratio = max(0.01, min(1.0, parsed_minor / parsed_major))
        return canonical_major, canonical_major * aspect_ratio

    @staticmethod
    def _angular_unit_deg(value: str) -> float:
        if any(token in value for token in ("arcsec", "″", '"')):
            return 1.0 / 3600.0
        if any(
            token in value
            for token in ("degree", "degrees", "gradi", "°")
        ):
            return 1.0
        return 1.0 / 60.0
