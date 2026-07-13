from __future__ import annotations

import json
import logging
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, Property, QTranslator, Signal, Slot


logger = logging.getLogger(__name__)

DEFAULT_LANGUAGE = "it"
SUPPORTED_LANGUAGES = (
    {"code": "it", "label": "Italiano"},
    {"code": "en", "label": "English"},
)
SUPPORTED_LANGUAGE_CODES = frozenset(item["code"] for item in SUPPORTED_LANGUAGES)


class TranslationManager(QObject):
    languageChanged = Signal()

    def __init__(self, translations_dir: Path, preferences_path: Path):
        super().__init__()
        self._translations_dir = translations_dir
        self._preferences_path = preferences_path
        self._translator = QTranslator(self)
        self._engine = None
        self._language_code = self._read_language()

    @Property(str, notify=languageChanged)
    def languageCode(self) -> str:
        return self._language_code

    @Property("QVariant", constant=True)
    def languageOptions(self) -> list[dict]:
        return [dict(item) for item in SUPPORTED_LANGUAGES]

    def install(self) -> bool:
        return self._apply_language(self._language_code)

    def attach_engine(self, engine) -> None:
        self._engine = engine

    @Slot(str, result=bool)
    def setLanguage(self, language_code: str) -> bool:
        normalized = language_code.strip().lower()
        if normalized not in SUPPORTED_LANGUAGE_CODES:
            return False
        if normalized == self._language_code:
            return True
        previous = self._language_code
        if not self._apply_language(normalized):
            self._apply_language(previous)
            return False
        self._language_code = normalized
        self._write_language(normalized)
        if self._engine is not None:
            self._engine.retranslate()
        self.languageChanged.emit()
        return True

    def _apply_language(self, language_code: str) -> bool:
        app = QCoreApplication.instance()
        if app is None:
            return language_code == DEFAULT_LANGUAGE
        app.removeTranslator(self._translator)
        if language_code == DEFAULT_LANGUAGE:
            return True
        translation_path = self._translations_dir / f"{language_code}.qm"
        if not self._translator.load(str(translation_path)):
            logger.error("Translation catalog could not be loaded: %s", translation_path)
            return False
        app.installTranslator(self._translator)
        return True

    def _read_language(self) -> str:
        payload = self._read_preferences()
        language_code = str(payload.get("language") or DEFAULT_LANGUAGE).strip().lower()
        return language_code if language_code in SUPPORTED_LANGUAGE_CODES else DEFAULT_LANGUAGE

    def _write_language(self, language_code: str) -> None:
        payload = self._read_preferences()
        payload["language"] = language_code
        temporary_path = self._preferences_path.with_suffix(self._preferences_path.suffix + ".tmp")
        try:
            self._preferences_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary_path.replace(self._preferences_path)
        except OSError:
            logger.warning("Language preference could not be written: %s", self._preferences_path, exc_info=True)
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
            logger.warning("Preference file could not be read: %s", self._preferences_path, exc_info=True)
            return {}
        return payload if isinstance(payload, dict) else {}
