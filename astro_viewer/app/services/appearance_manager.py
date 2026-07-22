from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot


logger = logging.getLogger(__name__)


class AppearanceManager(QObject):
    redNightVisionEnabledChanged = Signal()

    def __init__(self, preferences_path: Path):
        super().__init__()
        self._preferences_path = preferences_path
        stored_value = self._read_preferences().get("red_night_vision_enabled", False)
        self._red_night_vision_enabled = (
            stored_value if isinstance(stored_value, bool) else False
        )

    @Property(bool, notify=redNightVisionEnabledChanged)
    def redNightVisionEnabled(self) -> bool:
        return self._red_night_vision_enabled

    @Slot(bool, result=bool)
    def setRedNightVisionEnabled(self, enabled: bool) -> bool:
        normalized = bool(enabled)
        if normalized == self._red_night_vision_enabled:
            return True
        self._red_night_vision_enabled = normalized
        self._write_preference(normalized)
        self.redNightVisionEnabledChanged.emit()
        return True

    def _write_preference(self, enabled: bool) -> None:
        payload = self._read_preferences()
        payload["red_night_vision_enabled"] = enabled
        temporary_path = self._preferences_path.with_suffix(
            self._preferences_path.suffix + ".tmp"
        )
        try:
            self._preferences_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary_path.replace(self._preferences_path)
        except OSError:
            logger.warning(
                "Appearance preference could not be written: %s",
                self._preferences_path,
                exc_info=True,
            )
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _read_preferences(self) -> dict:
        if not self._preferences_path.exists():
            return {}
        try:
            payload = json.loads(self._preferences_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning(
                "Preference file could not be read: %s",
                self._preferences_path,
                exc_info=True,
            )
            return {}
        return payload if isinstance(payload, dict) else {}
