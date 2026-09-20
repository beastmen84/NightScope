"""Compute bounded, weather-independent meteor opportunities from local geometry.

Five-minute samples conservatively bound intervals (no added trailing sample).
These are planning thresholds, not a flux/ZHR or exact-peak prediction. Only
the UT maximum date and its two neighbouring dates are analysed, inside the
annual activity bounds. No network access or mutable engine caches are used.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, time, timedelta

import numpy as np
from skyfield import almanac
from skyfield.api import wgs84
from skyfield.functions import mxv


STEP = timedelta(minutes=5)
MIN_WINDOW = timedelta(minutes=30)


@dataclass(frozen=True)
class MeteorWindow:
    start: datetime
    end: datetime
    favorable: bool
    radiant_min: float
    radiant_max: float
    moon_altitude_max: float
    moon_illumination_max: float
    drift_used: bool
    samples: tuple[tuple[float, float, float, bool], ...] = field(default=(), repr=False)


@dataclass(frozen=True)
class MeteorGeometry:
    windows: tuple[MeteorWindow, ...] = ()
    reason: str = "unavailable"


def remaining_window(window, lower):
    """Clip an ongoing interval and recompute its facts from cached samples."""
    if lower <= window.start:
        return window
    offset = int((lower - window.start) / STEP)
    rows = window.samples[offset:]
    if not rows:
        return replace(window, start=lower)
    return replace(window, start=lower, samples=rows,
                   radiant_min=min(row[0] for row in rows), radiant_max=max(row[0] for row in rows),
                   moon_altitude_max=max(row[1] for row in rows), moon_illumination_max=max(row[2] for row in rows),
                   drift_used=all(row[3] for row in rows))


def radiant_at(shower, instant):
    """Interpolate RA across zero without extrapolating missing drift rows."""
    rows = shower.radiant_drift
    for first, second in zip(rows, rows[1:]):
        start = datetime.combine(first[0], time(), UTC)
        end = datetime.combine(second[0], time(), UTC)
        if start <= instant <= end:
            fraction = (instant - start) / (end - start)
            delta = (second[1] - first[1] + 180) % 360 - 180
            return ((first[1] + fraction * delta) % 360,
                    first[2] + fraction * (second[2] - first[2]), True)
    return float(shower.radiant_ra_deg), float(shower.radiant_dec_deg), False


def calculate_meteor_geometry(ephemeris, timescale, location, shower):
    """Vectorise one shower's 72-hour local geometry using installed ephemerides."""
    first = max(shower.active_start, shower.peak - timedelta(days=1))
    last = min(shower.active_end, shower.peak + timedelta(days=1)) + timedelta(days=1)
    start, end = (datetime.combine(day, time(), UTC) for day in (first, last))
    instants = tuple(start + index * STEP for index in range(int((end - start) / STEP) + 1))
    coordinates = [radiant_at(shower, instant) for instant in instants]
    times = timescale.from_datetimes(instants)
    site = wgs84.latlon(location.latitude, location.longitude)
    observer = ephemeris["earth"] + site
    positions = observer.at(times)
    sun = positions.observe(ephemeris["sun"]).apparent().altaz()[0].degrees
    moon = positions.observe(ephemeris["moon"]).apparent().altaz()[0].degrees
    illumination = almanac.fraction_illuminated(ephemeris, "moon", times) * 100
    # Radiants are J2000 celestial directions, not nearby Solar System bodies.
    ra, dec = np.radians(np.array([(row[0], row[1]) for row in coordinates]).T)
    directions = np.array([np.cos(dec) * np.cos(ra), np.cos(dec) * np.sin(ra), np.sin(dec)])
    # Skyfield's ICRF -> local horizon rotation includes precession/nutation.
    # Radiants are directions: no stellar parallax, proper motion or refraction.
    local = mxv(site.rotation_at(times), directions)
    radiant = np.degrees(np.arcsin(np.clip(local[2], -1, 1)))
    return windows_from_samples(instants, sun, radiant, moon, illumination,
                                [row[2] for row in coordinates])


def windows_from_samples(instants, sun, radiant, moon, illumination, drift):
    """Keep continuous dark/useful and dark/high/low-Moon intervals separately."""
    if not instants:
        return MeteorGeometry()
    arrays = [np.asarray(value, dtype=float) for value in (sun, radiant, moon, illumination)]
    if any(len(value) != len(instants) or not np.isfinite(value).all() for value in arrays):
        return MeteorGeometry()
    sun, radiant, moon, illumination = arrays
    dark = sun <= -18
    useful = dark & (radiant >= 15)
    # -0.83 is a conservative no-visible-Moon bound including limb/refraction.
    favorable = useful & (radiant >= 30) & ((moon <= -0.83) | (illumination <= 25))
    windows = []
    for flag, mask in ((True, favorable), (False, useful)):
        first = None
        for index in range(len(instants) + 1):
            valid = index < len(instants) and bool(mask[index])
            gap = index > 0 and index < len(instants) and instants[index] - instants[index - 1] != STEP
            if first is not None and (not valid or gap):
                last = index - 1
                if instants[last] - instants[first] >= MIN_WINDOW:
                    cut = slice(first, last + 1)
                    windows.append(MeteorWindow(instants[first], instants[last], flag,
                        float(min(radiant[cut])), float(max(radiant[cut])), float(max(moon[cut])),
                        float(max(illumination[cut])), all(drift[cut]),
                        tuple((float(radiant[i]), float(moon[i]), float(illumination[i]), bool(drift[i]))
                              for i in range(first, last + 1))))
                first = None
            if valid and first is None:
                first = index
    reason = "ok" if windows else "no_darkness" if not dark.any() else "low_radiant" if not useful.any() else "too_short"
    return MeteorGeometry(tuple(windows), reason)
