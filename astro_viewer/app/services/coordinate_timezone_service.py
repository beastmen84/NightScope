from __future__ import annotations

import logging
import math
from collections.abc import Callable
from threading import Lock
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


logger = logging.getLogger(__name__)


class CoordinateTimezoneResolver(Protocol):
    def timezone_at(self, latitude: float, longitude: float) -> str | None:
        ...


class _TimezoneFinder(Protocol):
    def timezone_at(self, *, lat: float, lng: float) -> str | None:
        ...


class CoordinateTimezoneService:
    """Resolves IANA timezones from WGS84 coordinates without network access."""

    def __init__(self, finder_factory: Callable[[], _TimezoneFinder] | None = None):
        self._finder_factory = finder_factory
        self._finder: _TimezoneFinder | None = None
        self._lock = Lock()

    def timezone_at(self, latitude: float, longitude: float) -> str | None:
        if not _valid_coordinates(latitude, longitude):
            return None

        try:
            timezone_name = self._get_finder().timezone_at(
                lat=float(latitude),
                lng=float(longitude),
            )
        except Exception:
            logger.warning(
                "Offline coordinate timezone lookup failed.",
                exc_info=True,
            )
            return None

        normalized = str(timezone_name or "").strip()
        return normalized if is_iana_timezone(normalized) else None

    def _get_finder(self) -> _TimezoneFinder:
        if self._finder is not None:
            return self._finder

        with self._lock:
            if self._finder is None:
                if self._finder_factory is not None:
                    self._finder = self._finder_factory()
                else:
                    from timezonefinder import TimezoneFinder

                    self._finder = TimezoneFinder()
        return self._finder


def is_iana_timezone(timezone_name: str) -> bool:
    normalized = str(timezone_name or "").strip()
    if not normalized:
        return False
    try:
        ZoneInfo(normalized)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def _valid_coordinates(latitude: float, longitude: float) -> bool:
    try:
        parsed_latitude = float(latitude)
        parsed_longitude = float(longitude)
    except (TypeError, ValueError):
        return False
    return (
        math.isfinite(parsed_latitude)
        and math.isfinite(parsed_longitude)
        and -90.0 <= parsed_latitude <= 90.0
        and -180.0 <= parsed_longitude <= 180.0
    )


DEFAULT_COORDINATE_TIMEZONE_RESOLVER = CoordinateTimezoneService()
