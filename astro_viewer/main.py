from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path


def _resolve_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "astro_viewer"
    return Path(__file__).resolve().parent


BASE_DIR = _resolve_base_dir()
PROJECT_ROOT = BASE_DIR.parent
APP_NAME = "NightScope"
ORG_NAME = "NightScope"
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _database_paths() -> tuple[Path, Path]:
    return BASE_DIR / "data" / "nightscope.db", BASE_DIR / "data" / "schema.sql"


def _build_controller(progress_callback=None):
    from astro_viewer.app.database.bootstrap import initialize_database
    from astro_viewer.app.services.logging_service import configure_logging
    from astro_viewer.app.viewmodels.app_controller import AppController

    configure_logging(BASE_DIR)
    database_path, schema_path = _database_paths()
    initialize_database(database_path, schema_path, progress_callback=progress_callback)
    return AppController(base_dir=BASE_DIR, database_path=database_path)


def _database_initialization_required() -> bool:
    from astro_viewer.app.database.bootstrap import database_initialization_required

    database_path, schema_path = _database_paths()
    return database_initialization_required(database_path, schema_path)


def _create_initialization_splash(app):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

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
    icon = QPixmap(str(BASE_DIR / "resources" / "icons" / "nightscope.ico"))
    if icon.isNull():
        icon = QPixmap(str(BASE_DIR / "resources" / "icons" / "telescope.svg"))
    if not icon.isNull():
        icon_label.setPixmap(icon.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    layout.addWidget(icon_label)

    app_name = QLabel(APP_NAME)
    app_name.setObjectName("appName")
    app_name.setAlignment(Qt.AlignHCenter)
    layout.addWidget(app_name)

    message = QLabel("Inizializzazione database al primo avvio...")
    message.setObjectName("message")
    message.setAlignment(Qt.AlignHCenter)
    layout.addWidget(message)

    secondary = QLabel("Preparazione cataloghi e dati locali.")
    secondary.setObjectName("secondary")
    secondary.setAlignment(Qt.AlignHCenter)
    layout.addWidget(secondary)

    status = QLabel("Creazione database...")
    status.setObjectName("status")
    status.setAlignment(Qt.AlignHCenter)
    layout.addWidget(status)

    progress = QProgressBar()
    progress.setRange(0, 0)
    progress.setTextVisible(False)
    layout.addWidget(progress)

    dialog.show()
    app.processEvents()
    return dialog, status


def _update_initialization_splash(app, splash, message: str) -> None:
    if not splash:
        return
    _, status = splash
    status.setText(message)
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
    print(f"planetary_score={controller.advancedScores.get('planetaryScore', 0)}/100")
    print(f"deep_sky_score={controller.advancedScores.get('deepSkyScore', 0)}/100")
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
        logging.getLogger(__name__).exception("NightScope database initialization failed.")
        if splash:
            _update_initialization_splash(app, splash, "Impossibile inizializzare il database locale.")
            splash[0].close()
        QMessageBox.critical(
            None,
            APP_NAME,
            "Impossibile inizializzare il database locale.\n\n"
            "Verifica i permessi della cartella dell'applicazione e riavvia NightScope.",
        )
        return 1
    if splash:
        splash[0].close()

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(BASE_DIR / "app" / "ui"))
    engine.rootContext().setContextProperty("appController", controller)
    engine.load(QUrl.fromLocalFile(str(BASE_DIR / "app" / "ui" / "main.qml")))

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
    controller = _build_controller()
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(BASE_DIR / "app" / "ui"))
    engine.rootContext().setContextProperty("appController", controller)
    engine.load(QUrl.fromLocalFile(str(BASE_DIR / "app" / "ui" / "main.qml")))
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
