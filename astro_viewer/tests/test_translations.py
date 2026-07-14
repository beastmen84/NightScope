from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from xml.etree import ElementTree

from PySide6.QtCore import QCoreApplication, QLocale, QObject

from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.localization import (
    active_language_code,
    content_text,
    format_datetime,
    format_number,
    render_payload,
    render_text,
)
from astro_viewer.app.services.translation_manager import (
    TranslationManager,
    discover_language_packs,
)
from astro_viewer.app.viewmodels.app_controller import AppController
from tools.update_content_translations import (
    SECTION_SOURCE_LANGUAGES,
    source_content,
)


PROJECT_DIR = Path(__file__).resolve().parents[2]
TRANSLATIONS_DIR = PROJECT_DIR / "astro_viewer" / "translations"
QML_DIR = PROJECT_DIR / "astro_viewer" / "app" / "ui"
PLACEHOLDER_PATTERN = re.compile(
    r"%L?\d+|%n|\{[A-Za-z_][A-Za-z0-9_]*(?:![rsa])?(?::[^{}]+)?\}"
)
STATIC_QML_TEXT_PATTERN = re.compile(
    r"^\s*(?:\{\s*)?(?:property\s+string\s+)?[\"']?"
    r"(?:label|text|title|subtitle|placeholderText|toolTip|accessibleName|emptyText|"
    r"message|description)[\"']?\s*:\s*([\"'])(.*?)\1",
    re.MULTILINE,
)


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
            assert translation_node.get("type") not in {
                "unfinished",
                "obsolete",
                "vanished",
            }
            translation = translation_node.text or ""
            assert translation.strip()
            assert sorted(PLACEHOLDER_PATTERN.findall(source)) == sorted(
                PLACEHOLDER_PATTERN.findall(translation)
            )
            entries[(context_name, source)] = translation
    return root, entries


def test_discovered_language_catalogs_are_complete_and_symmetric() -> None:
    packs = discover_language_packs(TRANSLATIONS_DIR)
    assert {"it", "en"} <= packs.keys()

    source_pack = next(pack for pack in packs.values() if pack.source)
    reference_keys: set[tuple[str, str]] | None = None
    catalogs: dict[str, dict[tuple[str, str], str]] = {}
    for code, pack in packs.items():
        ts_path = TRANSLATIONS_DIR / f"{code}.ts"
        assert ts_path.is_file()
        assert pack.qm_path.is_file()
        assert pack.qm_path.stat().st_size > 1_000

        root, entries = _catalog_entries(ts_path)
        assert root.get("language") == pack.locale
        assert root.get("sourcelanguage") == source_pack.locale
        assert len(entries) >= 1_400
        if reference_keys is None:
            reference_keys = set(entries)
        else:
            assert set(entries) == reference_keys
        catalogs[code] = entries

    assert all(
        translation == source
        for (_, source), translation in catalogs[source_pack.code].items()
    )
    assert catalogs["en"][("main", "Calendario")] == "Calendar"
    assert catalogs["en"][("main", "Log Osservazioni")] == "Observation Log"
    assert catalogs["en"][("main", "Lingua")] == "Language"
    assert catalogs["en"][("WeatherPage", "Meteo osservativo")] == (
        "Observing weather"
    )


def test_structured_content_covers_every_translatable_seed_field() -> None:
    sources = source_content()
    packs = discover_language_packs(TRANSLATIONS_DIR)

    assert set(sources) == set(SECTION_SOURCE_LANGUAGES)
    for pack in packs.values():
        translation_code = str(
            pack.payload["language"].get("translation_code") or pack.code
        )
        expected_sections = {
            section
            for section, source_code in SECTION_SOURCE_LANGUAGES.items()
            if source_code != translation_code
        }
        content = pack.payload["content"]
        assert set(content) == expected_sections
        for section in expected_sections:
            assert content[section].keys() == sources[section].keys()
            for item_key, fields in sources[section].items():
                translated_fields = content[section][item_key]
                assert translated_fields.keys() == fields.keys()
                assert all(str(value).strip() for value in translated_fields.values())


def test_reviewed_structured_content_uses_consistent_astronomy_terms() -> None:
    english = json.loads((TRANSLATIONS_DIR / "en.json").read_text(encoding="utf-8"))
    italian = json.loads((TRANSLATIONS_DIR / "it.json").read_text(encoding="utf-8"))
    descriptions = english["content"]["objects"]

    expected_constellations = {
        "messier-M5": "Serpens",
        "messier-M6": "Scorpius",
        "messier-M16": "Serpens",
        "messier-M26": "Scutum",
        "messier-M30": "Capricornus",
        "messier-M46": "Puppis",
        "messier-M50": "Monoceros",
        "messier-M53": "Coma Berenices",
        "messier-M63": "Canes Venatici",
        "messier-M71": "Sagitta",
        "messier-M77": "Cetus",
        "messier-M79": "Lepus",
        "messier-M80": "Scorpius",
        "messier-M102": "Draco",
        "caldwell-C5": "Camelopardalis",
        "caldwell-C16": "Lacerta",
        "caldwell-C21": "Canes Venatici",
        "caldwell-C37": "Vulpecula",
        "caldwell-C51": "Cetus",
        "caldwell-C71": "Puppis",
        "caldwell-C79": "Vela",
        "caldwell-C81": "Ara",
        "caldwell-C87": "Horologium",
        "caldwell-C88": "Circinus",
        "caldwell-C89": "Norma",
        "caldwell-C93": "Pavo",
        "caldwell-C95": "Triangulum Australe",
        "caldwell-C104": "Tucana",
        "caldwell-C105": "Musca",
        "caldwell-C107": "Apus",
        "caldwell-C109": "Chamaeleon",
    }
    for object_id, constellation in expected_constellations.items():
        assert constellation in descriptions[object_id]["short_description"]

    assert "Beehive Cluster" in descriptions["messier-M44"]["short_description"]
    assert "Whirlpool Galaxy" in descriptions["messier-M51"]["short_description"]
    assert "Owl Cluster" in descriptions["caldwell-C13"]["short_description"]
    assert "Jewel Box Cluster" in descriptions["caldwell-C94"]["observing_notes"]
    assert all(
        "\u200b" not in path.read_text(encoding="utf-8")
        for path in TRANSLATIONS_DIR.glob("*.json")
    )

    italian_catalogue = italian["content"]["catalogue_objects"]
    assert italian_catalogue["messier-M3"]["description"].endswith("Cani da Caccia.")
    assert italian_catalogue["messier-M11"]["description"].endswith("Scudo.")
    assert italian_catalogue["messier-M41"]["description"].endswith("Cane Maggiore.")
    italian_filters = italian["content"]["equipment_filters"]
    assert italian_filters["astronomik::h-beta visual"]["notes"] == (
        "Per nebulose dominate dalla riga H-beta."
    )
    assert italian_filters["baader::oiii super-g 9 nm"]["notes"] == (
        "Filtro OIII stretto per aperture medio-grandi."
    )


def test_translation_manager_switches_live_and_preserves_preferences(
    tmp_path: Path,
) -> None:
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
    assert render_payload(
        SkyQuality(
            7,
            4.6,
            18.8,
            "Fonte: NightScope local urban baseline",
            "urban",
        ).to_qml()
    )["source"] == "Source: NightScope local urban baseline"
    assert render_text(AppController._format_catalogue_angle(0.233)) == "0.233°"

    stored_preferences = json.loads(preferences_path.read_text(encoding="utf-8"))
    assert stored_preferences["saved_location"] == {"name": "Roma"}
    assert stored_preferences["language"] == "en"

    assert not manager.setLanguage("de")
    assert manager.languageCode == "en"
    assert engine.retranslate_calls == 1
    assert manager.setLanguage("it")
    assert QCoreApplication.translate("main", "Calendario") == "Calendario"
    assert engine.retranslate_calls == 2


def test_catalogue_choices_are_sorted_after_localization(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    manager = TranslationManager(TRANSLATIONS_DIR, tmp_path / "preferences.json")
    assert app is not None
    assert manager.install()
    assert manager.setLanguage("en")

    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._catalogue_objects = [
        {
            "catalogues": ["Sistema Solare"],
            "type": "planetary nebula",
            "constellation": "",
            "recommended_observation_type": "General",
        },
        {
            "catalogues": ["Messier"],
            "type": "galaxy",
            "constellation": "",
            "recommended_observation_type": "HighMagnification",
        },
        {
            "catalogues": ["Caldwell"],
            "type": "open cluster",
            "constellation": "",
            "recommended_observation_type": "WideField",
        },
    ]

    try:
        options = controller.catalogueFilterOptions
        for key in ("catalogueChoices", "typeChoices", "observationTypeChoices"):
            labels = [item["label"] for item in options[key]]
            assert labels == sorted(labels, key=str.casefold)
        assert [item["label"] for item in options["observationTypeChoices"]] == [
            "General",
            "High magnification",
            "Wide field",
        ]
    finally:
        assert manager.setLanguage("it")


def test_third_language_pack_requires_no_runtime_code_change(tmp_path: Path) -> None:
    translations_dir = tmp_path / "translations"
    translations_dir.mkdir()
    for code in ("it", "en"):
        for suffix in ("json", "ts", "qm"):
            shutil.copy2(
                TRANSLATIONS_DIR / f"{code}.{suffix}",
                translations_dir / f"{code}.{suffix}",
            )

    french = json.loads((TRANSLATIONS_DIR / "en.json").read_text(encoding="utf-8"))
    french["language"] = {
        "code": "fr",
        "label": "Francais",
        "locale": "fr_FR",
        "source": False,
    }
    french["formats"] = {
        "date": "yyyy-MM-dd",
        "date_time": "yyyy-MM-dd HH:mm",
    }
    french["content"] = {
        "objects": {
            "sun": {
                "short_description": "Description francaise de test.",
            }
        }
    }
    (translations_dir / "fr.json").write_text(
        json.dumps(french, ensure_ascii=False),
        encoding="utf-8",
    )
    shutil.copy2(translations_dir / "en.ts", translations_dir / "fr.ts")
    shutil.copy2(translations_dir / "en.qm", translations_dir / "fr.qm")

    preferences_path = tmp_path / "preferences.json"
    preferences_path.write_text(
        json.dumps({"language": "it", "unrelated": {"kept": True}}),
        encoding="utf-8",
    )
    app = QCoreApplication.instance() or QCoreApplication([])
    manager = TranslationManager(translations_dir, preferences_path)
    assert [item["code"] for item in manager.languageOptions] == ["it", "en", "fr"]
    assert manager.install()
    assert manager.setLanguage("fr")
    assert app is not None
    assert manager.languageCode == "fr"
    assert active_language_code() == "fr"
    assert QLocale().name() == "fr_FR"
    assert render_text(
        content_text("objects", "sun", "short_description", "Fonte italiana")
    ) == "Description francaise de test."
    assert render_text(format_datetime(datetime(2026, 7, 13, 22, 5))) == (
        "2026-07-13 22:05"
    )
    assert render_text(format_number(12.5, decimals=1)).endswith(",5")
    assert render_payload({"userNotes": "Testo libero dell'utente"}) == {
        "userNotes": "Testo libero dell'utente"
    }
    assert json.loads(preferences_path.read_text(encoding="utf-8"))["unrelated"] == {
        "kept": True
    }
    assert manager.setLanguage("it")


def test_language_change_refreshes_presentation_without_recomputing_nsom() -> None:
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._observation_rows = []
    controller._observation_log_service = Mock()
    controller._observation_log_service.build_entries.return_value = []
    controller._observation_log_service.build_summary.return_value = {}
    controller._equipment_status_message = Mock(return_value="ok")
    controller._refresh_all = Mock()
    controller._request_astronomy_refresh = Mock()
    controller._refresh_sky_compass_live = Mock()

    emitted: list[str] = []
    signal_names = (
        "locationChanged",
        "statusChanged",
        "earthdataCredentialsChanged",
        "openaqCredentialsChanged",
        "catalogueChanged",
        "equipmentChanged",
        "observationChanged",
        "dataChanged",
        "weatherChanged",
        "skyCompassChanged",
        "selectedObjectChanged",
    )
    for signal_name in signal_names:
        getattr(controller, signal_name).connect(
            lambda signal_name=signal_name: emitted.append(signal_name)
        )

    controller.retranslatePresentation()

    assert emitted == list(signal_names)
    controller._observation_log_service.build_entries.assert_called_once_with([])
    controller._observation_log_service.build_summary.assert_called_once_with([])
    controller._refresh_all.assert_not_called()
    controller._request_astronomy_refresh.assert_not_called()
    controller._refresh_sky_compass_live.assert_not_called()


def test_qml_has_no_untranslated_static_user_facing_properties() -> None:
    violations = []
    for path in sorted(QML_DIR.rglob("*.qml")):
        source = path.read_text(encoding="utf-8")
        for match in STATIC_QML_TEXT_PATTERN.finditer(source):
            value = match.group(2).strip()
            if value:
                line = source.count("\n", 0, match.start()) + 1
                violations.append(f"{path.relative_to(PROJECT_DIR)}:{line}: {value}")
    assert violations == []


def test_qml_translates_complete_messages_instead_of_sentence_fragments() -> None:
    violations = []
    concatenated_translation = re.compile(r"qsTr\([^\n]*\)\s*\+")
    for path in sorted(QML_DIR.rglob("*.qml")):
        source = path.read_text(encoding="utf-8")
        for match in concatenated_translation.finditer(source):
            line = source.count("\n", 0, match.start()) + 1
            violations.append(f"{path.relative_to(PROJECT_DIR)}:{line}")
    assert violations == []


def test_italian_qml_source_has_no_known_english_commands() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(QML_DIR.rglob("*.qml"))
    )
    assert 'qsTr("Create account")' not in source
    assert 'qsTr("Account already configured")' not in source


def test_curated_english_astronomy_terms_remain_technically_correct() -> None:
    _, entries = _catalog_entries(TRANSLATIONS_DIR / "en.ts")
    by_source: dict[str, set[str]] = {}
    for (_, source), translation in entries.items():
        by_source.setdefault(source, set()).add(translation)

    expected = {
        "Discreto": "Fair",
        "Dati riduttore non validi.": "Invalid focal reducer data.",
        "%1 di %2 riduttori": "%1 of %2 focal reducers",
        "Pupilla %1": "Exit pupil %1",
        "Altezza massima {altitude} e magnitudine {magnitude}.": (
            "Maximum altitude {altitude} and magnitude {magnitude}."
        ),
    }
    for source, translation in expected.items():
        assert by_source[source] == {translation}

    expected_by_context = {
        ("", "Crescente"): "Waxing crescent",
        ("", "Calante"): "Waning crescent",
        ("", "Gibbosa crescente"): "Waxing gibbous",
        ("", "Cielo profondo favorito"): "Favorable for deep-sky observing",
        ("", "Altro"): "Other",
        ("", "Durata utile non disponibile"): "Useful duration unavailable",
        ("", "Recupero dati VIIRS NASA..."): "Retrieving NASA VIIRS data...",
        ("", "quota utile"): "a useful altitude",
        (
            "",
            "senza Barlow per mantenere contrasto e campo",
        ): "without a Barlow to preserve contrast and field of view",
        (
            "",
            "È un evento da pianificare usando protezioni certificate specifiche "
            "per l'osservazione solare.",
        ): "Plan this event using certified protection designed specifically for solar viewing.",
        ("EquipmentOpticsPage", "%1 di %2 Barlow"): "%1 of %2 Barlow lenses",
        ("ObjectCataloguePage", "Tutti"): "All",
        ("ObjectDetailPage", "A.R."): "R.A.",
    }
    for key, translation in expected_by_context.items():
        assert entries[key] == translation

    rendered = "\n".join(entries.values()).casefold()
    for forbidden in (
        "gearbox",
        "sunscreen",
        "discreet",
        "maximum height",
        "profit share",
        "maintain tackle",
        "data recovery",
        "crescent gibbous",
        "out of plane",
        "service life not available",
        "colorful (",
        "100mm opening",
        "certified sun protection",
    ):
        assert forbidden not in rendered


def test_catalogue_content_keeps_language_pack_metadata_through_astronomy() -> None:
    skyfield_source = (
        PROJECT_DIR / "astro_viewer" / "app" / "astronomy" / "skyfield_engine.py"
    ).read_text(encoding="utf-8")
    home_source = (QML_DIR / "pages" / "HomePage.qml").read_text(encoding="utf-8")

    assert 'content_text(\n            "catalogue_objects"' in skyfield_source
    assert '"name"' in skyfield_source
    assert '"description"' in skyfield_source
    assert "catalogue_display_name(designation, name)" in skyfield_source
    assert "skyCompassTypeLabel" not in home_source


def test_language_packs_do_not_store_derived_catalogue_display_names() -> None:
    sources = source_content()["catalogue_objects"]
    assert all("display_name" not in item for item in sources.values())
    for path in sorted(TRANSLATIONS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        catalogue_objects = payload.get("content", {}).get("catalogue_objects", {})
        assert all("display_name" not in item for item in catalogue_objects.values())


def test_internal_read_models_receive_canonical_unrendered_payloads() -> None:
    source = (
        PROJECT_DIR / "astro_viewer" / "app" / "viewmodels" / "app_controller.py"
    ).read_text(encoding="utf-8")
    assert "events=self.events" not in source
    assert "self.homeObservingOverview" not in source
    assert "self.activeEquipmentProfile" not in source
    assert "events=[self._event_to_qml(event) for event in self._events]" in source


def test_translation_assets_are_packaged_and_sidebar_exposes_selector() -> None:
    spec = (PROJECT_DIR / "packaging" / "NightScope.spec").read_text(encoding="utf-8")
    main_qml = (QML_DIR / "main.qml").read_text(encoding="utf-8")

    assert '(str(APP_DIR / "translations"), "astro_viewer/translations")' in spec
    assert 'text: qsTr("Lingua")' in main_qml
    assert "model: translationManager.languageOptions" in main_qml
    assert "translationManager.setLanguage" in main_qml
