"""Prepare immutable Home clock labels and ordering, without images or Qt state."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services import observing_time


@dataclass(frozen=True)
class HomeTargetTimingSnapshot:
    """One input-specific preparation; target identity avoids deep DTO comparisons.

    Frozen targets are borrowed read-only, including their nested setup options.
    No rendered language strings, profile state or personal-image paths are
    retained. Clock labels use the same absolute/DST and legacy fallback helpers
    as the full detail projection. A different night or target requires a rebuild.
    """

    targets: tuple[CelestialObject, ...]
    night_window: ObservingNightWindow | None
    labels_by_id: Mapping[str, tuple[str, str]]
    ordered_targets: tuple[CelestialObject, ...]

    @classmethod
    def build(
        cls,
        targets: Sequence[CelestialObject],
        night_window: ObservingNightWindow | None,
        *,
        check_cancelled: Callable[[], None] = lambda: None,
    ) -> HomeTargetTimingSnapshot:
        labels = {}
        sort_keys = {}
        for item in targets:
            check_cancelled()
            window_label = observing_time.home_window_label(item, night_window)
            labels[item.id] = (
                window_label,
                "" if window_label else observing_time.home_time_label(item, night_window),
            )
            sort_keys[item.id] = alternative_sort_key(item, night_window)
        ordered = tuple(sorted(targets, key=lambda item: sort_keys[item.id]))
        check_cancelled()
        return cls(tuple(targets), night_window, MappingProxyType(labels), ordered)

    def matches(
        self, targets: Sequence[CelestialObject], night_window: ObservingNightWindow | None,
    ) -> bool:
        # Identity also distinguishes equal-looking fold=0/fold=1 boundaries.
        return (
            self.night_window is night_window
            and len(self.targets) == len(targets)
            and all(left is right for left, right in zip(self.targets, targets, strict=True))
        )


def alternative_sort_key(
    item: CelestialObject, night_window: ObservingNightWindow | None,
) -> tuple[int, int, int, tuple[tuple[int, int | str], ...]]:
    window_start = observing_time.first_observing_datetime(item.observing_window, night_window)
    best_time = observing_time.first_observing_datetime(item.best_time, night_window)
    return (
        alternative_time_order(window_start or best_time, night_window),
        alternative_time_order(best_time, night_window),
        0 if item.object_type == "Pianeta" else 1,
        natural_name_sort_key(item.name),
    )


def alternative_time_order(target_time: datetime | None, night_window: ObservingNightWindow | None) -> int:
    if target_time is None:
        return 10_000
    if night_window is not None and night_window.start is not None:
        return round((target_time - night_window.start).total_seconds() / 60)
    hour = (target_time.hour + 24) if target_time.hour < 12 else target_time.hour
    return hour * 60 + target_time.minute


def natural_name_sort_key(value: str) -> tuple[tuple[int, int | str], ...]:
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part.casefold())
        for part in re.split(r"(\d+)", value)
        if part
    )
