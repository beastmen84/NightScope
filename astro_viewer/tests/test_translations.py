from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from xml.etree import ElementTree

import pytest
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
    source_content,
    source_language,
)
from tools.update_ts_translations import (
    _apply_translation_review,
    _reviewed_translations,
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
    assert {"it", "en", "es"} <= packs.keys()

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
    assert catalogs["es"][("main", "Meteo")] == "Meteorología"
    assert catalogs["es"][("main", "Lingua")] == "Idioma"
    assert catalogs["es"][("EquipmentProfilesPage", "Pupilla d’uscita")] == (
        "Pupila de salida"
    )
    assert catalogs["es"][("EquipmentTelescopesPage", "Montatura *")] == (
        "Montura *"
    )
    assert catalogs["es"][("EquipmentBinocularsPage", "Catalogo binocoli")] == (
        "Catálogo de prismáticos"
    )
    assert catalogs["es"][("WeatherPage", "Seeing notturno")] == (
        "Seeing nocturno"
    )
    assert catalogs["es"][
        ("", "Scegliere un orizzonte aperto a Nord-Est e un cielo buio.")
    ] == "Elija un horizonte abierto hacia el noreste y un cielo oscuro."
    assert catalogs["es"][("", "Aggiungi oculari per suggerimenti completi")] == (
        "Añada oculares para obtener sugerencias completas"
    )
    assert catalogs["es"][("", "Regolo")] == "Escuadra"
    assert catalogs["es"][("CalendarPage", "Eclissi")] == "Eclipses"
    assert catalogs["es"][("", "Non puntare binocoli, telescopi o cercatori vicino al Sole.")] == (
        "No apunte prismáticos, telescopios ni buscadores cerca del Sol."
    )
    assert catalogs["es"][
        (
            "",
            "Il terminatore evidenzia crateri e rilievi; usa ingrandimenti progressivi.",
        )
    ] == (
        "El terminador resalta cráteres y relieves; aumente la magnificación "
        "progresivamente."
    )
    assert catalogs["es"][
        (
            "",
            "È un evento da pianificare usando protezioni certificate specifiche "
            "per l'osservazione solare.",
        )
    ] == (
        "Este evento debe planificarse utilizando protección certificada específica "
        "para la observación solar."
    )
    spanish_messages = "\n".join(catalogs["es"].values())
    assert re.search(r"\b(?:tu|tus)\b", spanish_messages, re.IGNORECASE) is None
    for informal_instruction in (
        "Aumenta el aumento",
        "Aumenta los aumentos",
        "aumenta progresivamente",
        "Escribe una ciudad",
        "Elige un horizonte",
        "Llega a un lugar",
        "No apuntes",
        "No consideres",
        "Planifica este evento",
        "Prepara el instrumento",
        "Prepara la configuración",
        "Prepara los prismáticos",
        "Prueba primero",
        "resérvala",
        "Usa prismáticos",
        "Configura una ubicación",
    ):
        assert informal_instruction not in spanish_messages


def test_structured_content_covers_every_translatable_seed_field() -> None:
    sources = source_content()
    packs = discover_language_packs(TRANSLATIONS_DIR)

    for pack in packs.values():
        translation_code = str(
            pack.payload["language"].get("translation_code") or pack.code
        )
        expected: dict[str, dict[str, set[str]]] = {}
        for section, items in sources.items():
            for item_key, fields in items.items():
                translated_fields = {
                    field
                    for field in fields
                    if source_language(section, item_key, field) != translation_code
                }
                if translated_fields:
                    expected.setdefault(section, {})[item_key] = translated_fields

        content = pack.payload["content"]
        assert set(content) == set(expected)
        for section, items in expected.items():
            assert content[section].keys() == items.keys()
            for item_key, fields in items.items():
                translated_fields = content[section][item_key]
                assert translated_fields.keys() == fields
                assert all(str(value).strip() for value in translated_fields.values())

    assert source_language("catalogue_objects", "messier-M1", "name") == "en"
    assert source_language("catalogue_objects", "caldwell-C1", "name") == "it"
    assert source_language("equipment_telescopes", "any", "notes") == "en"
    assert source_language("equipment_telescopes", "any", "optical_type") == "it"
    assert source_language("equipment_reducers", "any", "compatible_models") == "it"


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
    assert "equipment_filters" not in italian["content"]
    english_filters = english["content"]["equipment_filters"]
    assert english_filters["astronomik::h-beta visual"]["notes"] == (
        "For nebulae dominated by the H-beta line."
    )
    assert english_filters["baader::oiii super-g 9 nm"]["notes"] == (
        "Narrow OIII filter for medium to large apertures."
    )

    english_catalogue = english["content"]["catalogue_objects"]
    assert len(english_catalogue) == 109
    assert english_catalogue["caldwell-C13"]["name"] == "NGC 457 - Owl Cluster"
    assert english_catalogue["caldwell-C38"]["name"] == "NGC 4565 - Needle Galaxy"
    assert english_catalogue["caldwell-C53"]["name"] == "NGC 3115 - Spindle Galaxy"
    for item in english_catalogue.values():
        assert re.search(r"\b(NGC|IC)\d", item["name"]) is None
        assert not any(
            bad in item["description"]
            for bad in ("Moscow", "Regulus", "Volpetta", "Cani da Caccia")
        )

    assert descriptions["caldwell-C1"]["observing_notes"] == (
        "Use a medium field under dark skies; increase magnification moderately "
        "to separate the many faint stars from the background."
    )
    english_reducers = english["content"]["equipment_reducers"]
    assert english_reducers["baader::alan gee mark ii telecompressor::0.59"][
        "compatible_models"
    ]
    structured_english = json.dumps(english["content"], ensure_ascii=False).casefold()
    for forbidden in (
        "medium shot",
        "narrowing the shot",
        "dedicated gearbox",
        "fuso galaxy",
        "ago galaxy",
        "planetary mixer",
        "multi-billion-dollar",
        "discreet and not immediate",
        "dark sky counts more",
        "magnitude figure concerns",
        "magnitude figure applies",
        "move up",
        "of integrated magnitude",
        "initially retains",
        "initially preserves",
    ):
        assert forbidden not in structured_english


def test_curated_spanish_content_uses_reviewed_astronomy_terms() -> None:
    spanish = json.loads((TRANSLATIONS_DIR / "es.json").read_text(encoding="utf-8"))
    assert spanish["language"] == {
        "code": "es",
        "label": "Español",
        "locale": "es_ES",
        "source": False,
    }
    assert spanish["formats"] == {
        "date": "dd/MM/yyyy",
        "date_time": "dd/MM/yyyy HH:mm",
    }

    objects = spanish["content"]["objects"]
    catalogue = spanish["content"]["catalogue_objects"]
    assert "pupila de salida" in objects["messier-M16"]["observing_notes"]
    assert "0,3′/21′" in objects["caldwell-C59"]["short_description"]
    assert catalogue["messier-M13"]["name"] == "Gran cúmulo de Hércules"
    assert catalogue["messier-M11"]["name"] == "Cúmulo del Pato Salvaje"
    assert catalogue["caldwell-C13"]["name"] == "NGC 457 - Cúmulo del Búho"
    assert catalogue["caldwell-C1"]["name"] == "NGC 188"
    assert catalogue["caldwell-C5"]["name"] == "IC 342"
    assert "constelación de Escuadra" in objects["caldwell-C89"]["short_description"]
    assert catalogue["caldwell-C89"]["description"] == (
        "C89 (NGC 6087): cúmulo abierto en Escuadra."
    )
    assert catalogue["caldwell-C99"]["description"] == (
        "C99 - Nebulosa oscura en la Cruz del Sur."
    )

    telescope_content = spanish["content"]["equipment_telescopes"]
    assert {item["optical_type"] for item in telescope_content.values()} == {
        "Cassegrain clásico",
        "Catadióptrico",
        "Maksutov",
        "Maksutov-Newton",
        "Newtoniano",
        "Refractor",
        "Refractor Petzval",
        "Ritchey-Chrétien",
        "Schmidt-Cassegrain",
        "Telescopio inteligente",
    }
    assert {item["mount_type"] for item in telescope_content.values()} == {
        "Altazimutal",
        "Altazimutal GoTo",
        "Altazimutal PushTo",
        "Dobson",
        "Dobson de sobremesa",
        "Dobson plegable",
        "Dobson PushTo",
        "Ecuatorial",
        "Ecuatorial CG-4",
        "Horquilla GoTo",
        "OTA",
    }

    rendered = json.dumps(spanish["content"], ensure_ascii=False).casefold()
    for forbidden in (
        "binoculares",
        "capítulo 99",
        "caja de cambios",
        "clúster",
        "cúmulo cúmulo",
        "estrellas solubles",
        "la aumento",
        "mayores poderes",
        "nebula cocoon",
        "nebulosa dumbbell",
        "ng 188",
        "racimo",
        "una globular",
        "visión evitada",
        "\u200b",
    ):
        assert forbidden not in rendered


def test_spanish_ts_review_is_complete_and_idempotent() -> None:
    translations, contexts = _reviewed_translations("es")
    assert len(translations) >= 600
    assert sum(len(entries) for entries in contexts.values()) >= 4

    root = ElementTree.parse(TRANSLATIONS_DIR / "es.ts").getroot()
    assert _apply_translation_review(root, "es") == 0


def test_ts_review_rejects_invalid_or_stale_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review_dir = tmp_path / "translation_reviews"
    review_dir.mkdir()
    review_path = review_dir / "es.json"
    monkeypatch.setattr(
        "tools.update_ts_translations.TRANSLATION_REVIEWS_DIR",
        review_dir,
    )
    root = ElementTree.fromstring(
        "<TS><context><name>Test</name><message>"
        "<source>Valore %1</source><translation>Valor %1</translation>"
        "</message></context></TS>"
    )

    review_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "translations": {"Valore %1": "Valor"},
                "contexts": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Placeholder mismatch"):
        _apply_translation_review(root, "es")

    review_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "translations": {"Messaggio rimosso": "Mensaje eliminado"},
                "contexts": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing from es.ts"):
        _apply_translation_review(root, "es")

    review_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "translations": {"Valore %1": "  "},
                "contexts": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid translation review entries"):
        _reviewed_translations("es")


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
            "Fonte: World Atlas sample",
            "urban",
        ).to_qml()
    )["source"] == "Source: World Atlas sample"
    assert render_text(AppController._format_catalogue_angle(0.233)) == "0.233°"

    assert manager.setLanguage("es")
    assert manager.languageCode == "es"
    assert engine.retranslate_calls == 2
    assert QCoreApplication.translate("main", "Lingua") == "Idioma"
    assert QLocale().name() == "es_ES"
    assert render_text(format_datetime(datetime(2026, 7, 13, 22, 5))) == (
        "13/07/2026 22:05"
    )
    assert render_text(format_number(12.5, decimals=1)).endswith(",5")

    stored_preferences = json.loads(preferences_path.read_text(encoding="utf-8"))
    assert stored_preferences["saved_location"] == {"name": "Roma"}
    assert stored_preferences["language"] == "es"

    assert not manager.setLanguage("de")
    assert manager.languageCode == "es"
    assert engine.retranslate_calls == 2
    assert manager.setLanguage("it")
    assert QCoreApplication.translate("main", "Calendario") == "Calendario"
    assert engine.retranslate_calls == 3


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
