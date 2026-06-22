from __future__ import annotations

import argparse
import logging
import os
import sys
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


def _build_controller():
    from astro_viewer.app.database.bootstrap import initialize_database
    from astro_viewer.app.services.logging_service import configure_logging
    from astro_viewer.app.viewmodels.app_controller import AppController

    configure_logging(BASE_DIR)
    database_path = BASE_DIR / "data" / "nightscope.db"
    schema_path = BASE_DIR / "data" / "schema.sql"
    initialize_database(database_path, schema_path)
    return AppController(base_dir=BASE_DIR, database_path=database_path)


def run_smoke_test() -> int:
    controller = _build_controller()
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


def run_app() -> int:
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ModuleNotFoundError as exc:
        missing = exc.name or "PySide6"
        print(
            f"Dipendenza mancante: {missing}. Installa le dipendenze con "
            "`python -m pip install -r astro_viewer/requirements.txt`."
        )
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
