"""Conservative short-term total-brightness calibration, not an orbit or outburst fit.

Thresholds are explicit NightScope safety policies, not COBS accuracy guarantees.
Visual estimates and CCD visual-equivalent (Z) observations are fitted separately.
Ordinary instrumental V, R, unfiltered and nuclear photometry never calibrate
visual detectability. The JPL distance law/slope remains the baseline.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

import numpy as np

from astro_viewer.app.services.cobs_observations import CometObservation, utc


FIT_LOOKBACK = timedelta(days=7)
MAX_PROJECTION = timedelta(hours=72)
MIN_MARGIN = 0.35
MAX_RESIDUAL_RANGE = 1.0
MAX_DAY_DRIFT = 0.6
MAX_OFFSET = 3.0


@dataclass(frozen=True)
class BrightnessCalibration:
    offset: float
    margin: float
    latest_at: datetime
    valid_until: datetime
    family: str
    count: int
    observers: int

    def applies(self, when: datetime) -> bool:
        return self.latest_at <= utc(when) <= self.valid_until

    def adjust(self, magnitudes: np.ndarray, dates: list[datetime]) -> np.ndarray:
        mask = np.asarray([self.applies(value) for value in dates])
        return magnitudes + np.where(mask, self.offset, 0.0)

    def faint_limit(self, magnitudes: np.ndarray, dates: list[datetime]) -> np.ndarray:
        mask = np.asarray([self.applies(value) for value in dates])
        return magnitudes + np.where(mask, self.margin, 0.0)


@dataclass(frozen=True)
class BrightnessAssessment:
    observations: tuple[CometObservation, ...] = ()
    calibration: BrightnessCalibration | None = None
    reason: str = "missing"


def assess_brightness(
    observations: tuple[CometObservation, ...],
    model_magnitudes: np.ndarray,
    now: datetime,
) -> BrightnessAssessment:
    """Fit a robust offset at each measurement epoch; never average raw magnitudes."""
    now = utc(now)
    if not observations:
        return BrightnessAssessment()
    if len(observations) != len(model_magnitudes):
        raise ValueError("COBS observations/model epochs do not match")
    groups: dict[str, list] = {"visual": [], "ccd_visual": []}
    for observation, model in zip(observations, model_magnitudes, strict=True):
        if (not observation.observer or not now - FIT_LOOKBACK <= observation.observed_at <= now
                or not np.isfinite(model) or (observation.error is not None and observation.error > 0.5)):
            continue
        family = ("visual" if observation.kind == "V" and observation.method in {"S", "B", "M"}
                  else "ccd_visual" if observation.kind == "C" and observation.method == "Z" else "")
        if family:
            groups[family].append((observation, observation.magnitude - float(model)))
    fits = {family: _fit(rows, family, now) for family, rows in groups.items()}
    visual, ccd = fits["visual"], fits["ccd_visual"]
    if visual[0] and ccd[0] and abs(visual[0].offset - ccd[0].offset) > 0.75:
        return BrightnessAssessment(observations, reason="conflicting")
    # Do not choose the apparently stable photographic series over conflicting
    # or rapidly changing well-supported visual observations.
    if visual[1] == "unstable":
        return BrightnessAssessment(observations, reason="unstable")
    calibration = visual[0] or ccd[0]
    reason = ("calibrated" if calibration else "unstable" if ccd[1] == "unstable"
              else "stale" if "stale" in (visual[1], ccd[1]) else "insufficient")
    return BrightnessAssessment(observations, calibration, reason)


def _fit(rows: list, family: str, now: datetime) -> tuple[BrightnessCalibration | None, str]:
    # Collapse repeated measurements, then balance observers rather than giving
    # a prolific observer/camera disproportionate statistical weight.
    by_observer_day = defaultdict(list)
    for observation, residual in rows:
        by_observer_day[(observation.observer, observation.observed_at.date())].append(residual)
    required_bins, required_observers = (3, 2) if family == "visual" else (6, 3)
    observers = {key[0] for key in by_observer_day}
    dates = {key[1] for key in by_observer_day}
    if len(by_observer_day) < required_bins or len(observers) < required_observers or len(dates) < 2:
        return None, "insufficient"
    latest = max(row.observed_at for row, _residual in rows)
    if now >= latest + MAX_PROJECTION:
        return None, "stale"
    bins = {key: median(values) for key, values in by_observer_day.items()}
    by_observer, by_day = defaultdict(list), defaultdict(list)
    for (observer, day), value in bins.items():
        by_observer[observer].append(value)
        by_day[day].append(value)
    offset = median(median(values) for values in by_observer.values())
    daily = [median(values) for values in by_day.values()]
    values = list(bins.values())
    if (max(values) - min(values) > MAX_RESIDUAL_RANGE
            or max(daily) - min(daily) > MAX_DAY_DRIFT or abs(offset) > MAX_OFFSET):
        return None, "unstable"
    # A practical safety margin, NOT a formal confidence interval. Never shrink
    # it as 1/sqrt(N): independent observations can still share systematic bias.
    margin = max(MIN_MARGIN, max(abs(value - offset) for value in values),
                 max((row.error or 0.0) for row, _residual in rows))
    return BrightnessCalibration(offset, margin, latest, latest + MAX_PROJECTION,
                                 family, len(bins), len(observers)), "calibrated"
