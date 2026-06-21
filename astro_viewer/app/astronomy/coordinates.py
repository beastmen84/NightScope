from __future__ import annotations

import re

import astropy.units as u
from astropy.coordinates import SkyCoord


def parse_ra_hours(value: str) -> float:
    """Parse right ascension strings like '05h 34m 31.9s' into decimal hours."""

    try:
        return float(SkyCoord(_normalize_angle(value), "0d", unit=(u.hourangle, u.deg), frame="icrs").ra.hour)
    except Exception:
        pass

    numbers = [float(part) for part in re.findall(r"[-+]?\d+(?:\.\d+)?", value)]
    if not numbers:
        raise ValueError(f"Invalid right ascension: {value}")
    hours = numbers[0]
    minutes = numbers[1] if len(numbers) > 1 else 0.0
    seconds = numbers[2] if len(numbers) > 2 else 0.0
    return hours + minutes / 60.0 + seconds / 3600.0


def parse_dec_degrees(value: str) -> float:
    """Parse declination strings like '+22° 00′ 52.2″' into decimal degrees."""

    try:
        return float(SkyCoord("0h", _normalize_angle(value), unit=(u.hourangle, u.deg), frame="icrs").dec.deg)
    except Exception:
        pass

    clean_value = value.replace("−", "-")
    sign = -1.0 if clean_value.strip().startswith("-") else 1.0
    numbers = [float(part) for part in re.findall(r"\d+(?:\.\d+)?", clean_value)]
    if not numbers:
        raise ValueError(f"Invalid declination: {value}")
    degrees = numbers[0]
    minutes = numbers[1] if len(numbers) > 1 else 0.0
    seconds = numbers[2] if len(numbers) > 2 else 0.0
    return sign * (degrees + minutes / 60.0 + seconds / 3600.0)


def _normalize_angle(value: str) -> str:
    return (
        value.replace("°", "d")
        .replace("º", "d")
        .replace("′", "m")
        .replace("'", "m")
        .replace("″", "s")
        .replace('"', "s")
        .replace("−", "-")
    )
