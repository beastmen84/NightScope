"""Protect Red Night Vision persistence, Qt notifications, and pre-QML rendering."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from astro_viewer import main as main_module
from astro_viewer.app.services.appearance_manager import AppearanceManager


UI_DIR = Path(__file__).resolve().parents[1] / "app" / "ui"


def test_startup_red_stylesheet_covers_every_color() -> None:
    normal = main_module._startup_stylesheet(red_night_vision=False)
    red = main_module._startup_stylesheet(red_night_vision=True)
    normal_colors = re.findall(r"#[0-9a-f]{6}", normal)
    red_colors = re.findall(r"#[0-9a-f]{6}", red)
    assert len(normal_colors) == len(red_colors) > 15
    for color in red_colors:
        r, g, b = (int(color[offset:offset + 2], 16) for offset in (1, 3, 5))
        assert r > 2 * max(g, b)
    assert "#6fd6e7" in normal
    assert set(normal_colors).isdisjoint(red_colors)


def _assert_startup_widgets(directory: str) -> None:
    """Exercise real QWidget painting in a fresh process, independent of QCoreApplication tests."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtWidgets import QApplication, QLabel

    from astro_viewer.app.runtime_paths import RuntimePaths

    app = QApplication([])
    if sys.platform == "win32":
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
        app.setFont(QFont("Segoe UI"))
    paths = RuntimePaths.colocated(Path(directory))
    paths.database_path.touch()

    def check_red(widget, name: str) -> None:
        app.processEvents()
        frame = widget.grab().toImage()
        assert frame.save(str(Path(directory) / f"{name}.png"))
        visible = 0
        for y in range(frame.height()):
            for x in range(frame.width()):
                color = frame.pixelColor(x, y)
                if color.alpha() > 0 and max(color.red(), color.green(), color.blue()) > 10:
                    visible += 1
                    assert color.red() > 1.5 * max(color.green(), color.blue()), (
                        name, x, y, color.name(),
                    )
        assert visible > 1000

    with patch.object(main_module, "RUNTIME_PATHS", paths), patch.object(
        main_module, "_legacy_runtime_paths", return_value=[],
    ):
        for language in ("it", "en", "es"):
            paths.preferences_path.write_text(json.dumps({
                "red_night_vision_enabled": True, "language": language,
            }), encoding="utf-8")
            translator = main_module._build_translation_manager()
            translator.install()
            appearance = main_module._build_appearance_manager()
            assert appearance.redNightVisionEnabled is True
            context = main_module._startup_context()
            assert context.existing_database and not context.first_use
            splash = main_module._create_startup_splash(
                app, context, red_night_vision=appearance.redNightVisionEnabled,
            )
            try:
                assert splash.dialog.findChild(QLabel, "startupIcon").isHidden()
                check_red(splash.dialog, f"{language}-startup")
                for index, message in enumerate((
                    "Importazione cataloghi...", main_module._STARTUP_SERVICES_MESSAGE,
                    main_module._STARTUP_INTERFACE_MESSAGE, main_module._STARTUP_READY_MESSAGE,
                    "Impossibile inizializzare il database locale.",
                )):
                    main_module._update_startup_splash(app, splash, message)
                    check_red(splash.dialog, f"{language}-progress-{index}")
            finally:
                splash.dialog.close()
            error = main_module._create_startup_error_dialog(
                "NightScope: startup error", red_night_vision=True,
            )
            try:
                assert error.windowFlags() & Qt.FramelessWindowHint
                error.show()
                check_red(error, f"{language}-error")
            finally:
                error.close()
            app.removeTranslator(translator._translator)

        normal = main_module._create_startup_splash(
            app, main_module._StartupContext(first_use=True, existing_database=False),
        )
        try:
            assert normal.status.text() == "Creating the local database..."
            icon = normal.dialog.findChild(QLabel, "startupIcon")
            assert not icon.isHidden() and not icon.pixmap().isNull()
        finally:
            normal.dialog.close()


def test_persisted_red_mode_covers_startup_progress_and_failure(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-c", (
            "import sys; from astro_viewer.tests.test_appearance_manager "
            "import _assert_startup_widgets; _assert_startup_widgets(sys.argv[1])"
        ), str(tmp_path)],
        cwd=UI_DIR.parents[2],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_appearance_defaults_to_normal_mode(tmp_path: Path) -> None:
    manager = AppearanceManager(tmp_path / "user_preferences.json")

    assert manager.redNightVisionEnabled is False


def test_appearance_reads_persisted_red_mode(tmp_path: Path) -> None:
    preferences_path = tmp_path / "user_preferences.json"
    preferences_path.write_text(
        json.dumps({"red_night_vision_enabled": True}),
        encoding="utf-8",
    )

    manager = AppearanceManager(preferences_path)

    assert manager.redNightVisionEnabled is True


def test_appearance_update_preserves_other_preferences(tmp_path: Path) -> None:
    preferences_path = tmp_path / "user_preferences.json"
    preferences_path.write_text(
        json.dumps({"language": "es", "auto_detect_location_on_startup": True}),
        encoding="utf-8",
    )
    manager = AppearanceManager(preferences_path)
    changes = []
    manager.redNightVisionEnabledChanged.connect(lambda: changes.append(True))

    assert manager.setRedNightVisionEnabled(True) is True

    payload = json.loads(preferences_path.read_text(encoding="utf-8"))
    assert payload == {
        "language": "es",
        "auto_detect_location_on_startup": True,
        "red_night_vision_enabled": True,
    }
    assert changes == [True]


def test_appearance_does_not_emit_when_mode_is_unchanged(tmp_path: Path) -> None:
    manager = AppearanceManager(tmp_path / "user_preferences.json")
    changes = []
    manager.redNightVisionEnabledChanged.connect(lambda: changes.append(True))

    assert manager.setRedNightVisionEnabled(False) is True

    assert changes == []
    assert not (tmp_path / "user_preferences.json").exists()


def test_invalid_preferences_fall_back_to_normal_mode(tmp_path: Path) -> None:
    preferences_path = tmp_path / "user_preferences.json"
    preferences_path.write_text("not json", encoding="utf-8")

    manager = AppearanceManager(preferences_path)

    assert manager.redNightVisionEnabled is False


def test_non_boolean_red_mode_preference_is_rejected(tmp_path: Path) -> None:
    preferences_path = tmp_path / "user_preferences.json"
    preferences_path.write_text(
        json.dumps({"red_night_vision_enabled": "false"}),
        encoding="utf-8",
    )

    manager = AppearanceManager(preferences_path)

    assert manager.redNightVisionEnabled is False


def test_qml_colors_outside_the_theme_are_semantic() -> None:
    literal_color = re.compile(r"#[0-9a-fA-F]{6,8}|rgba\(")
    offenders = []
    for path in sorted(UI_DIR.rglob("*.qml")):
        if path.name == "AppTheme.qml":
            continue
        if literal_color.search(path.read_text(encoding="utf-8")):
            offenders.append(path.relative_to(UI_DIR).as_posix())

    assert offenders == []


def test_metric_tile_uses_teal_unless_accent_is_meaningful() -> None:
    component = (UI_DIR / "components" / "MetricTile.qml").read_text(
        encoding="utf-8"
    )
    assert "property bool accentMeaningful: false" in component
    assert (
        "color: root.accentMeaningful ? root.accentColor : theme.teal"
        in component
    )
    assert "opacity: root.accentMeaningful ? 0.75 : 0.6" in component

    metric_tile = re.compile(r"\bMetricTile\s*\{([^{}]*)\}", re.DOTALL)
    for page_name in ("EquipmentProfilesPage.qml", "WeatherPage.qml"):
        page = (UI_DIR / "pages" / page_name).read_text(encoding="utf-8")
        assert all("accentColor:" not in block for block in metric_tile.findall(page))

    calendar = (UI_DIR / "pages" / "CalendarPage.qml").read_text(
        encoding="utf-8"
    )
    calendar_tiles = metric_tile.findall(calendar)
    colored_calendar_tiles = [
        block for block in calendar_tiles if "accentColor:" in block
    ]
    assert len(calendar_tiles) == 9
    assert len(colored_calendar_tiles) == 8
    assert all("accentMeaningful: true" in block for block in colored_calendar_tiles)

    detail = (UI_DIR / "pages" / "ObjectDetailPage.qml").read_text(
        encoding="utf-8"
    )
    colored_detail_tiles = [
        block for block in metric_tile.findall(detail) if "accentColor:" in block
    ]
    assert len(colored_detail_tiles) == 1
    assert "accentMeaningful:" in colored_detail_tiles[0]
    assert detail.count('"accentMeaningful": true') == 2
    assert "photographicMetricAccent" not in detail


def test_catalogue_visibility_colors_preserve_unknown_state() -> None:
    theme = (UI_DIR / "components" / "AppTheme.qml").read_text(encoding="utf-8")
    assert "function booleanStateColor(value, known)" in theme
    assert "if (known !== true) return textMuted" in theme
    assert "return value === true ? green : coral" in theme

    detail = (UI_DIR / "pages" / "ObjectDetailPage.qml").read_text(
        encoding="utf-8"
    )
    assert detail.count("theme.booleanStateColor(") == 2
    assert "objectData.catalogueUsefullyObservableKnown" in detail
    assert "objectData.catalogueVisibleCurrentMonthKnown" in detail

    catalogue = (UI_DIR / "pages" / "ObjectCataloguePage.qml").read_text(
        encoding="utf-8"
    )
    assert "function usefulObservableColor(item)" in catalogue
    assert "item.is_usefully_observable_known === true" in catalogue
    assert "item.observable_known === true" in catalogue
    assert "return theme.booleanStateColor(value, known)" in catalogue
    assert "color: root.usefulObservableColor(itemData)" in catalogue


def test_glass_card_uses_teal_unless_accent_is_meaningful() -> None:
    component = (UI_DIR / "components" / "GlassCard.qml").read_text(
        encoding="utf-8"
    )
    assert "property bool accentMeaningful: false" in component
    assert (
        "color: root.accentMeaningful ? root.accentColor : theme.teal"
        in component
    )
    assert "opacity: root.accentMeaningful ? 1.0 : 0.7" in component

    expected_meaningful_counts = {
        "DataProvidersPage.qml": 2,
        "EquipmentProfilesPage.qml": 1,
        "EventDetailPage.qml": 2,
        "HomePage.qml": 6,
        "LocationPage.qml": 1,
        "WeatherPage.qml": 0,
    }
    for page_name, expected_count in expected_meaningful_counts.items():
        page = (UI_DIR / "pages" / page_name).read_text(encoding="utf-8")
        assert page.count("accentMeaningful: true") == expected_count

    home = (UI_DIR / "pages" / "HomePage.qml").read_text(encoding="utf-8")
    assert "accentColor: root.moonImpactAccent(" in home
    assert home.count("accentColor: root.observingCategoryAccent(") == 2
    assert re.search(
        r'if \(state === "recommended"\)\s+return theme\.green',
        home,
    )
    assert re.search(
        r'if \(state === "discouraged"\)\s+return theme\.coral',
        home,
    )

    providers = (UI_DIR / "pages" / "DataProvidersPage.qml").read_text(
        encoding="utf-8"
    )
    assert "accentColor: earthdataCard.accentColor" in providers
    assert "accentColor: openaqCard.accentColor" in providers

    location = (UI_DIR / "pages" / "LocationPage.qml").read_text(
        encoding="utf-8"
    )
    assert (
        "accentColor: controller.hasValidLocation ? theme.green : theme.amber"
        in location
    )

    detail = (UI_DIR / "pages" / "ObjectDetailPage.qml").read_text(
        encoding="utf-8"
    )
    assert detail.count("accentMeaningful: true") == 3
    assert "accentColor: root.photographicStateAccent()" in detail
    assert "accentColor: root.photographicModeAccent()" in detail
    assert 'if (root.photographicData.ready === true)\n            return theme.green' in detail
    assert detail.count("return theme.green") >= 3

    main_qml = (UI_DIR / "main.qml").read_text(encoding="utf-8")
    assert re.search(
        r'if \(state === "recommended"\)\s+return theme\.green',
        main_qml,
    )
    for page_name in ("CalendarPage.qml", "EventDetailPage.qml"):
        page = (UI_DIR / "pages" / page_name).read_text(encoding="utf-8")
        assert re.search(
            r'if \(state === "visible" \|\| state === "favorable" '
            r'\|\| state === "nearby_night"\)\s+return theme\.green',
            page,
        )

    informational_marker = re.compile(
        r"Layout\.preferredWidth:\s*4\s+"
        r"Layout\.preferredHeight:\s*28\s+"
        r"radius:\s*2\s+"
        r"color:\s*theme\.teal\s+"
        r"opacity:\s*0\.7"
    )
    for page_name, expected_count in {
        "EquipmentCamerasPage.qml": 1,
        "EquipmentFiltersReducersPage.qml": 2,
        "EquipmentOpticsPage.qml": 2,
    }.items():
        page = (UI_DIR / "pages" / page_name).read_text(encoding="utf-8")
        assert len(informational_marker.findall(page)) == expected_count

    visible_target = (UI_DIR / "components" / "HomeVisibleTargetRow.qml").read_text(
        encoding="utf-8"
    )
    assert visible_target.count("root.accent()") == 2


def test_unavailable_state_accents_use_muted_color() -> None:
    home = (UI_DIR / "pages" / "HomePage.qml").read_text(encoding="utf-8")
    assert (
        home.count(
            'if (state === "unavailable")\n'
            "            return theme.textMuted"
        )
        == 3
    )
    assert (
        'if (impact === "unavailable")\n'
        "            return theme.textMuted"
    ) in home
    assert (
        "root.weatherOverview.available\n"
        "                                    ? theme.scoreColor("
        "root.weatherOverview.scoreValue)\n"
        "                                    : theme.textMuted)"
    ) in home

    main_qml = (UI_DIR / "main.qml").read_text(encoding="utf-8")
    assert (
        'if (state === "unavailable")\n'
        "            return theme.textMuted"
    ) in main_qml

    detail = (UI_DIR / "pages" / "ObjectDetailPage.qml").read_text(
        encoding="utf-8"
    )
    assert (
        detail.count(
            'if (state === "unavailable")\n'
            "            return theme.textMuted"
        )
        == 2
    )


def test_red_palette_contains_no_bright_green_blue_or_white_tokens() -> None:
    theme = (UI_DIR / "components" / "AppTheme.qml").read_text(encoding="utf-8")
    red_colors = re.findall(r'redNightVision \? "#([0-9a-fA-F]{6})"', theme)

    assert len(red_colors) >= 30
    for value in red_colors:
        red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
        assert red >= green
        assert red >= blue
        assert green <= 90
        assert blue <= 80


def test_red_mode_control_and_photo_suppression_contract() -> None:
    main_qml = (UI_DIR / "main.qml").read_text(encoding="utf-8")
    plan_row = (UI_DIR / "components" / "HomePlanStepRow.qml").read_text(
        encoding="utf-8"
    )
    detail = (UI_DIR / "pages" / "ObjectDetailPage.qml").read_text(
        encoding="utf-8"
    )
    icon = (UI_DIR / "components" / "NightVisionIcon.qml").read_text(
        encoding="utf-8"
    )

    assert main_qml.index('text: qsTr("Stasera")') < main_qml.index(
        'text: qsTr("Visione rossa")'
    )
    assert "appearanceManager.setRedNightVisionEnabled(false)" in main_qml
    assert "appearanceManager.setRedNightVisionEnabled(true)" in main_qml
    assert 'source: theme.redNightVision ? "" : root.imageSource()' in plan_row
    for branch in ("!root.isCatalogueDetail", "root.isCatalogueDetail"):
        assert f"source: root.hasObject && {branch} && !theme.redNightVision" in detail
    assert detail.count("visible: !theme.redNightVision") >= 4
    assert "MultiEffect" in icon
    assert "layer.enabled: theme.redNightVision" in icon
    assert "layer.effect: MultiEffect" in icon
    assert "colorization: 1.0" in icon


def test_only_suppressible_photographs_use_plain_qml_images() -> None:
    plain_images = []
    for path in sorted(UI_DIR.rglob("*.qml")):
        count = len(re.findall(r"^\s*Image\s*\{", path.read_text(encoding="utf-8"), re.MULTILINE))
        plain_images.extend([path.relative_to(UI_DIR).as_posix()] * count)

    assert plain_images == [
        "components/HomePlanStepRow.qml",
        "components/NightVisionIcon.qml",
        "components/ObjectImageEditor.qml",
        "pages/ObjectDetailPage.qml",
        "pages/ObjectDetailPage.qml",
    ]
    editor = (UI_DIR / "components/ObjectImageEditor.qml").read_text(encoding="utf-8")
    assert 'source: root.visible && !theme.redNightVision ? (root.imageState.previewUrl || "") : ""' in editor
    assert "enabled: !root.imageState.busy && !theme.redNightVision" in editor
    assert "if (redNightVision) picker.close()" in editor


def test_pages_do_not_use_native_checkbox_or_text_field_rendering() -> None:
    native_controls = re.compile(r"^\s*(?:CheckBox|TextField)\s*\{", re.MULTILINE)
    offenders = []
    for path in sorted((UI_DIR / "pages").glob("*.qml")):
        if native_controls.search(path.read_text(encoding="utf-8")):
            offenders.append(path.relative_to(UI_DIR).as_posix())

    assert offenders == []


def test_red_source_link_embeds_the_reactive_theme_color() -> None:
    detail = (UI_DIR / "pages" / "ObjectDetailPage.qml").read_text(
        encoding="utf-8"
    )

    assert '"<a style=\\"color:" + theme.cyan.toString() + "\\" href="' in detail


def test_current_location_keeps_name_and_coordinates_separate() -> None:
    location = (UI_DIR / "pages" / "LocationPage.qml").read_text(encoding="utf-8")

    assert "return controller.location.city || controller.location.coordinatesLabel" in location
    assert "parts.push(coordinates)" in location
    title_start = location.index("text: root.currentLocationTitle()")
    title_end = location.index("}", title_start)
    title_block = location[title_start:title_end]
    assert "wrapMode: Text.WordWrap" in title_block
    assert "maximumLineCount" not in title_block
    assert "elide:" not in title_block
