from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.location_service import LocationDetectionResult


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StartupLocationPreferences:
    auto_detect_location_on_startup: bool = False
    allow_approximate_online_location: bool = False
    use_windows_location_on_startup: bool = False


class LocationPreferenceStore:
    def __init__(self, preferences_path: Path, cache_path: Path):
        self._preferences_path = preferences_path
        self._cache_path = cache_path

    def preferences(self) -> StartupLocationPreferences:
        payload = self._read_json(self._preferences_path)
        return self._startup_preferences_from_payload(payload)

    def update_preferences(
        self,
        *,
        auto_detect_location_on_startup: bool | None = None,
        allow_approximate_online_location: bool | None = None,
        use_windows_location_on_startup: bool | None = None,
    ) -> StartupLocationPreferences:
        payload = self._read_json(self._preferences_path)
        if auto_detect_location_on_startup is not None:
            payload["auto_detect_location_on_startup"] = bool(auto_detect_location_on_startup)
        if allow_approximate_online_location is not None:
            payload["allow_approximate_online_location"] = bool(allow_approximate_online_location)
        if use_windows_location_on_startup is not None:
            payload["use_windows_location_on_startup"] = bool(use_windows_location_on_startup)
        self._normalize_startup_preferences(payload)
        self._write_json(self._preferences_path, payload)
        return self.preferences()

    def saved_location(self) -> LocationDetectionResult | None:
        return self._result_from_payload(self._read_json(self._preferences_path).get("saved_location"))

    def cached_location(self) -> LocationDetectionResult | None:
        return self._result_from_payload(self._read_json(self._cache_path))

    def save_location(self, result: LocationDetectionResult, *, saved: bool = True, cached: bool = True) -> None:
        payload = result.to_qml()
        payload["savedAt"] = datetime.now().isoformat(timespec="seconds")
        if saved:
            preferences = self._read_json(self._preferences_path)
            preferences["saved_location"] = payload
            self._write_json(self._preferences_path, preferences)
        if cached:
            cache_payload = dict(payload)
            cache_payload["cachedAt"] = payload["savedAt"]
            self._write_json(self._cache_path, cache_payload)

    def _result_from_payload(self, payload) -> LocationDetectionResult | None:
        if not isinstance(payload, dict):
            return None
        location_payload = payload.get("location")
        if not isinstance(location_payload, dict):
            return None
        try:
            latitude = float(location_payload["latitude"])
            longitude = float(location_payload["longitude"])
            timezone = str(location_payload["timezone"]).strip()
        except (KeyError, TypeError, ValueError):
            logger.warning("Stored location payload is invalid.", exc_info=True)
            return None
        if not timezone or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            logger.warning("Stored location payload has invalid coordinates or timezone.")
            return None
        location = ObserverLocation(
            city=str(location_payload.get("city") or "").strip(),
            country=str(location_payload.get("country") or "").strip(),
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
        )
        return LocationDetectionResult(
            location=location,
            provider=str(payload.get("provider") or "cached"),
            source=str(payload.get("source") or "Posizione salvata"),
            accuracy=str(payload.get("accuracy") or "cached"),
            approximate=bool(payload.get("approximate", False)),
            region=str(payload.get("region") or ""),
            country_code=str(payload.get("country_code") or location_payload.get("country_code") or ""),
            raw_provider_timezone=str(payload.get("raw_provider_timezone") or ""),
            message=str(payload.get("message") or "Posizione caricata."),
        )

    @staticmethod
    def _read_json(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Preference file could not be read: %s", path, exc_info=True)
            return {}
        return payload if isinstance(payload, dict) else {}

    @classmethod
    def _startup_preferences_from_payload(cls, payload: dict) -> StartupLocationPreferences:
        normalized = dict(payload)
        cls._normalize_startup_preferences(normalized)
        return StartupLocationPreferences(
            auto_detect_location_on_startup=bool(normalized.get("auto_detect_location_on_startup", False)),
            allow_approximate_online_location=bool(normalized.get("allow_approximate_online_location", False)),
            use_windows_location_on_startup=bool(normalized.get("use_windows_location_on_startup", False)),
        )

    @staticmethod
    def _normalize_startup_preferences(payload: dict) -> None:
        auto_detect = bool(payload.get("auto_detect_location_on_startup", False))
        use_windows = bool(payload.get("use_windows_location_on_startup", False))
        allow_online = bool(payload.get("allow_approximate_online_location", False))

        if not auto_detect:
            payload["use_windows_location_on_startup"] = False
            payload["allow_approximate_online_location"] = False
            return

        if not use_windows and not allow_online:
            payload["use_windows_location_on_startup"] = True

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            logger.warning("Preference file could not be written: %s", path, exc_info=True)
