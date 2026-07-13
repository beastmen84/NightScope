from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

from PySide6.QtCore import QCoreApplication

from astro_viewer.app.services.translation_manager import TranslationManager


PROJECT_DIR = Path(__file__).resolve().parents[2]
TRANSLATIONS_DIR = PROJECT_DIR / "astro_viewer" / "translations"


def _catalog_entries(path: Path) -> tuple[ElementTree.Element, dict[tuple[str, str], str]]:
    root = ElementTree.parse(path).getroot()
    entries: dict[tuple[str, str], str] = {}
    for context in root.findall("context"):
        context_name = context.findtext("name", default="")
        for message in context.findall("message"):
            source = message.findtext("source", default="")
            translation_node = message.find("translation")
            assert source
            assert translation_node is not None
            assert translation_node.get("type") != "unfinished"
            translation = translation_node.text or ""
            assert translation.strip()
            entries[(context_name, source)] = translation
    return root, entries


def test_italian_and_english_catalogs_are_complete_and_symmetric() -> None:
    en_root, en_entries = _catalog_entries(TRANSLATIONS_DIR / "en.ts")
    it_root, it_entries = _catalog_entries(TRANSLATIONS_DIR / "it.ts")

    assert en_root.get("language") == "en_US"
    assert it_root.get("language") == "it_IT"
    assert en_root.get("sourcelanguage") == "it_IT"
    assert it_root.get("sourcelanguage") == "it_IT"
    assert en_entries.keys() == it_entries.keys()
    assert len(en_entries) >= 500
    assert all(it_entries[key] == key[1] for key in it_entries)

    assert en_entries[("main", "Calendario")] == "Calendar"
    assert en_entries[("main", "Log Osservazioni")] == "Observation Log"
    assert en_entries[("main", "Lingua")] == "Language"
    assert en_entries[("WeatherPage", "Meteo osservativo")] == "Observing weather"


def test_compiled_catalogs_are_present() -> None:
    for language_code in ("it", "en"):
        catalog = TRANSLATIONS_DIR / f"{language_code}.qm"
        assert catalog.is_file()
        assert catalog.stat().st_size > 1_000


def test_translation_manager_switches_live_and_preserves_preferences(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    preferences_path = tmp_path / "user_preferences.json"
    preferences_path.write_text(
        json.dumps({"saved_location": {"name": "Roma"}, "language": "it"}),
        encoding="utf-8",
    )
    manager = TranslationManager(TRANSLATIONS_DIR, preferences_path)

    class EngineProbe:
        def __init__(self) -> None:
            self.retranslate_calls = 0

        def retranslate(self) -> None:
            self.retranslate_calls += 1

    engine = EngineProbe()
    manager.attach_engine(engine)

    assert app is not None
    assert manager.languageCode == "it"
    assert manager.install()
    assert QCoreApplication.translate("main", "Calendario") == "Calendario"
    assert manager.setLanguage("en")
    assert manager.languageCode == "en"
    assert engine.retranslate_calls == 1
    assert QCoreApplication.translate("main", "Calendario") == "Calendar"

    stored_preferences = json.loads(preferences_path.read_text(encoding="utf-8"))
    assert stored_preferences["saved_location"] == {"name": "Roma"}
    assert stored_preferences["language"] == "en"

    assert not manager.setLanguage("de")
    assert manager.languageCode == "en"
    assert engine.retranslate_calls == 1
    assert manager.setLanguage("it")
    assert QCoreApplication.translate("main", "Calendario") == "Calendario"
    assert engine.retranslate_calls == 2


def test_translation_assets_are_packaged_and_sidebar_exposes_selector() -> None:
    spec = (PROJECT_DIR / "packaging" / "NightScope.spec").read_text(encoding="utf-8")
    main_qml = (PROJECT_DIR / "astro_viewer" / "app" / "ui" / "main.qml").read_text(
        encoding="utf-8"
    )

    assert '(str(APP_DIR / "translations"), "astro_viewer/translations")' in spec
    assert 'text: qsTr("Lingua")' in main_qml
    assert "model: translationManager.languageOptions" in main_qml
    assert "translationManager.setLanguage" in main_qml
