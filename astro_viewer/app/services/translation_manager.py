from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from PySide6.QtCore import QCoreApplication, QLocale, QObject, Property, QTranslator, Signal, Slot

from astro_viewer.app.services.localization import (
    DEFAULT_LANGUAGE_CODE,
    activate_language_pack,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LanguagePack:
    code: str
    label: str
    locale: str
    source: bool
    payload: Mapping[str, Any]
    qm_path: Path


def discover_language_packs(translations_dir: Path) -> dict[str, LanguagePack]:
    packs: dict[str, LanguagePack] = {}
    for metadata_path in sorted(translations_dir.glob("*.json")):
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"Invalid language pack: {metadata_path}") from error
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            raise ValueError(f"Unsupported language-pack schema: {metadata_path}")
        language = payload.get("language")
        if not isinstance(language, dict):
            raise ValueError(f"Missing language metadata: {metadata_path}")
        code = str(language.get("code") or "").strip().lower()
        label = str(language.get("label") or "").strip()
        locale = str(language.get("locale") or "").strip()
        if not code or code != metadata_path.stem or not label or not locale:
            raise ValueError(f"Invalid language metadata: {metadata_path}")
        if code in packs:
            raise ValueError(f"Duplicate language code: {code}")
        packs[code] = LanguagePack(
            code=code,
            label=label,
            locale=locale,
            source=bool(language.get("source")),
            payload=payload,
            qm_path=translations_dir / f"{code}.qm",
        )
    source_packs = [pack for pack in packs.values() if pack.source]
    if len(source_packs) != 1:
        raise ValueError("Exactly one source language pack is required.")
    if source_packs[0].code != DEFAULT_LANGUAGE_CODE:
        raise ValueError(f"The source language must be {DEFAULT_LANGUAGE_CODE}.")
    return packs


class TranslationManager(QObject):
    languageChanged = Signal()

    def __init__(self, translations_dir: Path, preferences_path: Path):
        super().__init__()
        self._translations_dir = translations_dir
        self._preferences_path = preferences_path
        self._translator = QTranslator(self)
        self._engine = None
        self._packs = discover_language_packs(translations_dir)
        self._language_code = self._read_language()

    @Property(str, notify=languageChanged)
    def languageCode(self) -> str:
        return self._language_code

    @Property("QVariant", constant=True)
    def languageOptions(self) -> list[dict]:
        ordered = sorted(
            self._packs.values(),
            key=lambda pack: (not pack.source, pack.label.casefold()),
        )
        return [{"code": pack.code, "label": pack.label} for pack in ordered]

    def install(self) -> bool:
        return self._apply_language(self._language_code)

    def attach_engine(self, engine) -> None:
        self._engine = engine

    @Slot(str, result=bool)
    def setLanguage(self, language_code: str) -> bool:
        normalized = language_code.strip().lower()
        if normalized not in self._packs:
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
        pack = self._packs.get(language_code)
        if pack is None:
            return False
        app = QCoreApplication.instance()
        if app is None:
            activate_language_pack(pack.payload)
            QLocale.setDefault(QLocale(pack.locale))
            return language_code == DEFAULT_LANGUAGE_CODE
        app.removeTranslator(self._translator)
        if not self._translator.load(str(pack.qm_path)):
            logger.error("Translation catalog could not be loaded: %s", pack.qm_path)
            return False
        app.installTranslator(self._translator)
        activate_language_pack(pack.payload)
        QLocale.setDefault(QLocale(pack.locale))
        return True

    def _read_language(self) -> str:
        payload = self._read_preferences()
        language_code = str(payload.get("language") or DEFAULT_LANGUAGE_CODE).strip().lower()
        return language_code if language_code in self._packs else DEFAULT_LANGUAGE_CODE

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
