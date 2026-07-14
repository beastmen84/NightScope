from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import time
from pathlib import Path


def _resolve_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "astro_viewer"
    return Path(__file__).resolve().parent


BASE_DIR = _resolve_base_dir()
PROJECT_ROOT = BASE_DIR.parent
RUNTIME_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else PROJECT_ROOT
APP_NAME = "NightScope"
ORG_NAME = "NightScope"
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _database_paths() -> tuple[Path, Path]:
    database_path = RUNTIME_DIR / "nightscope.db"
    schema_path = _data_dir() / "schema.sql"
    _copy_legacy_runtime_files(database_path)
    return database_path, schema_path


def _data_dir() -> Path:
    return BASE_DIR / "data"


def _legacy_runtime_paths() -> list[Path]:
    candidates = [
        BASE_DIR / "data" / "nightscope.db",
        RUNTIME_DIR / "data" / "nightscope.db",
    ]
    unique = []
    seen = set()
    for path in candidates:
        key = path.resolve() if path.exists() else path.absolute()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _copy_legacy_runtime_files(database_path: Path) -> None:
    if database_path.exists():
        return
    for legacy_database_path in _legacy_runtime_paths():
        if legacy_database_path == database_path or not legacy_database_path.exists():
            continue
        database_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_database_path, database_path)
        _copy_legacy_sidecar(
            legacy_database_path.parent / "user_preferences.json",
            database_path.parent / "user_preferences.json",
        )
        _copy_legacy_sidecar(
            legacy_database_path.parent / "location_cache.json",
            database_path.parent / "location_cache.json",
        )
        logging.getLogger(__name__).info("Runtime database copied from legacy location: %s", legacy_database_path)
        return


def _copy_legacy_sidecar(source: Path, target: Path) -> None:
    if source.exists() and not target.exists():
        shutil.copy2(source, target)


def _build_controller(progress_callback=None):
    from astro_viewer.app.astronomy.comet_windows import CometWindowEventSource
    from astro_viewer.app.astronomy.iss_passes import IssPassEventSource
    from astro_viewer.app.database.bootstrap import initialize_database
    from astro_viewer.app.database.orbital_element_cache_repository import (
        OrbitalElementCacheRepository,
    )
    from astro_viewer.app.services.logging_service import configure_logging
    from astro_viewer.app.viewmodels.app_controller import AppController

    configure_logging(BASE_DIR)
    database_path, schema_path = _database_paths()
    initialize_database(
        database_path,
        schema_path,
        progress_callback=progress_callback,
        geonames_data_dir=_data_dir(),
    )
    orbital_cache = OrbitalElementCacheRepository(database_path)
    iss_pass_source = IssPassEventSource(orbital_cache)
    comet_window_source = CometWindowEventSource(orbital_cache)
    return AppController(
        base_dir=BASE_DIR,
        database_path=database_path,
        transient_event_sources=(iss_pass_source, comet_window_source),
    )


def _build_translation_manager():
    from astro_viewer.app.services.translation_manager import TranslationManager

    return TranslationManager(
        translations_dir=BASE_DIR / "translations",
        preferences_path=RUNTIME_DIR / "user_preferences.json",
    )


def _database_initialization_required() -> bool:
    from astro_viewer.app.database.bootstrap import database_initialization_required

    database_path, schema_path = _database_paths()
    return database_initialization_required(database_path, schema_path, geonames_data_dir=_data_dir())


def _create_initialization_splash(app):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout
    from astro_viewer.app.services.localization import render_text, tr

    dialog = QDialog()
    dialog.setWindowTitle(APP_NAME)
    dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dialog.setModal(False)
    dialog.setFixedWidth(420)
    dialog.setStyleSheet(
        """
        QDialog {
            background-color: #171a20;
            border: 1px solid #303641;
            border-radius: 8px;
        }
        QLabel#appName {
            color: #f4f7fb;
            font-size: 24px;
            font-weight: 600;
        }
        QLabel#message {
            color: #d7dee8;
            font-size: 14px;
        }
        QLabel#secondary, QLabel#status {
            color: #aeb7c4;
            font-size: 12px;
        }
        QProgressBar {
            min-height: 8px;
            border: 1px solid #303641;
            border-radius: 4px;
            background-color: #252b34;
        }
        QProgressBar::chunk {
            border-radius: 4px;
            background-color: #65d6e8;
        }
        """
    )

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(34, 28, 34, 28)
    layout.setSpacing(10)

    icon_label = QLabel()
    icon_label.setAlignment(Qt.AlignHCenter)
    app_icon = QIcon(str(BASE_DIR / "resources" / "icons" / "nightscope.ico"))
    icon = app_icon.pixmap(80, 80) if not app_icon.isNull() else QPixmap()
    if icon.isNull():
        icon = QPixmap(str(BASE_DIR / "resources" / "icons" / "telescope.svg")).scaled(
            80,
            80,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
    if not icon.isNull():
        icon_label.setPixmap(icon)
    layout.addWidget(icon_label)

    app_name = QLabel(APP_NAME)
    app_name.setObjectName("appName")
    app_name.setAlignment(Qt.AlignHCenter)
    layout.addWidget(app_name)

    message = QLabel(render_text(tr("Inizializzazione database al primo avvio...")))
    message.setObjectName("message")
    message.setAlignment(Qt.AlignHCenter)
    layout.addWidget(message)

    secondary = QLabel(render_text(tr("Preparazione cataloghi e dati locali.")))
    secondary.setObjectName("secondary")
    secondary.setAlignment(Qt.AlignHCenter)
    layout.addWidget(secondary)

    status = QLabel(render_text(tr("Creazione database...")))
    status.setObjectName("status")
    status.setAlignment(Qt.AlignHCenter)
    layout.addWidget(status)

    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(12)
    progress.setTextVisible(False)
    layout.addWidget(progress)

    dialog.show()
    app.processEvents()
    return dialog, status, progress


def _update_initialization_splash(app, splash, message: object) -> None:
    if not splash:
        return
    _, status, progress = splash
    from astro_viewer.app.services.localization import render_text

    status.setText(render_text(message))
    next_value = progress.value() + 9
    progress.setValue(18 if next_value > 92 else next_value)
    app.processEvents()


def run_smoke_test() -> int:
    controller = _build_controller()
    _wait_for_startup_location(controller)
    print(f"{APP_NAME} smoke test")
    print(f"location={controller.location['city']}, {controller.location['country']}")
    print(f"planets={len(controller.visiblePlanets)}")
    print(f"deep_sky={len(controller.recommendedDeepSky)}")
    print(f"events={len(controller.events)}")
    print(f"weather_hours={len(controller.weatherHourly)}")
    print(f"observing_quality={controller.observingQuality.get('scoreValue', 0)}/100")
    overview = controller.homeObservingOverview
    print(f"planetary_conditions={overview.get('planetary', {}).get('label', 'n/d')}")
    print(f"deep_sky_conditions={overview.get('deepSky', {}).get('label', 'n/d')}")
    print(f"bortle={controller.skyQuality.get('bortleClass', 'n/d')}")
    print(f"night_plan={len(controller.nightPlan)}")
    print(f"best_object={controller.bestObjectOfNight.get('name', 'n/d')}")
    return 0


def _wait_for_startup_location(controller, timeout_seconds: float = 8.0) -> bool:
    try:
        from PySide6.QtCore import QCoreApplication
    except ModuleNotFoundError:
        return False

    app = QCoreApplication.instance() or QCoreApplication([])
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if not getattr(controller, "startupLocationDetectionRunning", False):
            app.processEvents()
            return True
        time.sleep(0.02)
    app.processEvents()
    return not getattr(controller, "startupLocationDetectionRunning", False)


def run_app() -> int:
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtWidgets import QApplication, QMessageBox
    except ModuleNotFoundError as exc:
        missing = exc.name or "PySide6"
        print(
            f"Dipendenza mancante: {missing}. Installa le dipendenze con "
            "`python -m pip install -r astro_viewer/requirements.txt`."
        )
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    translation_manager = _build_translation_manager()
    translation_manager.install()

    try:
        initialization_required = _database_initialization_required()
    except Exception:
        logging.getLogger(__name__).warning("Database initialization preflight failed.", exc_info=True)
        initialization_required = True
    splash = _create_initialization_splash(app) if initialization_required else None
    progress_callback = (lambda message: _update_initialization_splash(app, splash, message)) if splash else None
    try:
        controller = _build_controller(progress_callback=progress_callback)
    except Exception:
        from astro_viewer.app.services.localization import render_text, tr

        logging.getLogger(__name__).exception("NightScope database initialization failed.")
        error_title = tr("Impossibile inizializzare il database locale.")
        if splash:
            _update_initialization_splash(app, splash, error_title)
            splash[0].close()
        QMessageBox.critical(
            None,
            APP_NAME,
            render_text(
                tr(
                    "Impossibile inizializzare il database locale.\n\n"
                    "Verifica i permessi della cartella dell'applicazione e riavvia NightScope."
                )
            ),
        )
        return 1
    translation_manager.languageChanged.connect(controller.retranslatePresentation)
    if splash:
        splash[0].close()

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(BASE_DIR / "app" / "ui"))
    engine.rootContext().setContextProperty("appController", controller)
    engine.rootContext().setContextProperty("translationManager", translation_manager)
    engine.load(QUrl.fromLocalFile(str(BASE_DIR / "app" / "ui" / "main.qml")))
    translation_manager.attach_engine(engine)

    if not engine.rootObjects():
        return 1
    return app.exec()


def run_qml_smoke_test() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6.QtCore import QTimer, QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ModuleNotFoundError as exc:
        missing = exc.name or "PySide6"
        print(f"Dipendenza mancante per QML smoke test: {missing}.")
        return 1

    app = QGuiApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    translation_manager = _build_translation_manager()
    translation_manager.install()
    controller = _build_controller()
    translation_manager.languageChanged.connect(controller.retranslatePresentation)
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(BASE_DIR / "app" / "ui"))
    engine.rootContext().setContextProperty("appController", controller)
    engine.rootContext().setContextProperty("translationManager", translation_manager)
    engine.load(QUrl.fromLocalFile(str(BASE_DIR / "app" / "ui" / "main.qml")))
    translation_manager.attach_engine(engine)
    if not engine.rootObjects():
        return 1
    QTimer.singleShot(0, app.quit)
    app.exec()
    print("QML smoke test ok")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} desktop astronomy app")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Initialize services and print a compact readiness report.",
    )
    parser.add_argument(
        "--qml-smoke-test",
        action="store_true",
        help="Load the QML scene offscreen and exit.",
    )
    return parser.parse_args()


def main() -> int:
    from astro_viewer.app.services.logging_service import configure_logging

    configure_logging(BASE_DIR)
    try:
        args = parse_args()
        if args.qml_smoke_test:
            return run_qml_smoke_test()
        if args.smoke_test:
            return run_smoke_test()
        return run_app()
    except Exception:
        logging.getLogger(__name__).exception("Unhandled NightScope error.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
