from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path


_STARTUP_SERVICES_MESSAGE = "Preparing application services..."
_STARTUP_INTERFACE_MESSAGE = "Opening the interface..."
_STARTUP_READY_MESSAGE = "NightScope is ready."


@dataclass(frozen=True)
class _InitializationProgressState:
    stage: int
    percent: int
    detail: str


@dataclass
class _InitializationSplash:
    dialog: object
    status: object
    progress: object
    step_labels: tuple[object, ...]
    step_counter: object


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


def _detect_platform_capabilities():
    from astro_viewer.app.platform_capabilities import detect_platform_capabilities

    return detect_platform_capabilities()


PLATFORM_CAPABILITIES = _detect_platform_capabilities()


def _resolve_runtime_paths():
    from astro_viewer.app.runtime_paths import resolve_runtime_paths

    return resolve_runtime_paths(
        platform_family=PLATFORM_CAPABILITIES.family,
        project_root=PROJECT_ROOT,
        executable_dir=Path(sys.executable).resolve().parent,
        frozen=bool(getattr(sys, "frozen", False)),
        override=os.environ.get("NIGHTSCOPE_RUNTIME_DIR", ""),
    )


def _resolve_runtime_dir() -> Path:
    """Return the data directory retained by the legacy single-path API."""
    return _resolve_runtime_paths().data_dir


RUNTIME_PATHS = _resolve_runtime_paths()
RUNTIME_DIR = RUNTIME_PATHS.data_dir


def _configure_application_metadata(app) -> None:
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    if PLATFORM_CAPABILITIES.is_linux:
        from astro_viewer.app.platform_capabilities import NIGHTSCOPE_DESKTOP_ID

        app.setDesktopFileName(NIGHTSCOPE_DESKTOP_ID)


def _database_paths() -> tuple[Path, Path]:
    database_path = RUNTIME_PATHS.database_path
    schema_path = _data_dir() / "schema.sql"
    _copy_legacy_runtime_files()
    return database_path, schema_path


def _data_dir() -> Path:
    return BASE_DIR / "data"


def _legacy_runtime_paths() -> list[Path]:
    portable_runtime_dir = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else PROJECT_ROOT
    )
    candidates = [
        BASE_DIR / "data" / "nightscope.db",
        portable_runtime_dir / "nightscope.db",
        portable_runtime_dir / "data" / "nightscope.db",
        RUNTIME_PATHS.data_dir / "data" / "nightscope.db",
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


def _copy_legacy_runtime_files() -> None:
    database_path = RUNTIME_PATHS.database_path
    for legacy_database_path in _legacy_runtime_paths():
        if legacy_database_path == database_path or not legacy_database_path.exists():
            continue
        if not database_path.exists():
            database_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_database_path, database_path)
            logging.getLogger(__name__).info(
                "Runtime database copied from legacy location: %s",
                legacy_database_path,
            )
        _copy_legacy_sidecar(
            legacy_database_path.parent / "user_preferences.json",
            RUNTIME_PATHS.preferences_path,
        )
        _copy_legacy_sidecar(
            legacy_database_path.parent / "location_cache.json",
            RUNTIME_PATHS.location_cache_path,
        )
        _copy_legacy_sidecar(
            legacy_database_path.parent / "nasa_aod_cache.json",
            RUNTIME_PATHS.nasa_aod_cache_path,
        )
        _copy_legacy_sidecar(
            legacy_database_path.with_suffix(".db.backup"),
            RUNTIME_PATHS.database_backup_path,
        )
        return


def _copy_legacy_sidecar(source: Path, target: Path) -> None:
    if source.exists() and not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _build_controller(progress_callback=None):
    from astro_viewer.app.astronomy.comet_windows import CometWindowEventSource
    from astro_viewer.app.astronomy.iss_passes import IssPassEventSource
    from astro_viewer.app.database.bootstrap import initialize_database
    from astro_viewer.app.database.orbital_element_cache_repository import (
        OrbitalElementCacheRepository,
    )
    from astro_viewer.app.viewmodels.app_controller import AppController

    database_path, schema_path = _database_paths()
    initialize_database(
        database_path,
        schema_path,
        progress_callback=progress_callback,
        geonames_data_dir=_data_dir(),
    )
    if progress_callback:
        progress_callback(_STARTUP_SERVICES_MESSAGE)
    orbital_cache = OrbitalElementCacheRepository(database_path)
    iss_pass_source = IssPassEventSource(orbital_cache)
    comet_window_source = CometWindowEventSource(orbital_cache)
    return AppController(
        base_dir=BASE_DIR,
        database_path=database_path,
        preferences_path=RUNTIME_PATHS.preferences_path,
        location_cache_path=RUNTIME_PATHS.location_cache_path,
        nasa_aod_cache_path=RUNTIME_PATHS.nasa_aod_cache_path,
        transient_event_sources=(iss_pass_source, comet_window_source),
    )


def _build_translation_manager():
    from astro_viewer.app.services.translation_manager import TranslationManager

    return TranslationManager(
        translations_dir=BASE_DIR / "translations",
        preferences_path=RUNTIME_PATHS.preferences_path,
    )


def _build_appearance_manager():
    from astro_viewer.app.services.appearance_manager import AppearanceManager

    return AppearanceManager(preferences_path=RUNTIME_PATHS.preferences_path)


def _build_update_manager():
    from astro_viewer.app.services.update_manager import UpdateManager

    return UpdateManager(
        version_path=PROJECT_ROOT / "VERSION",
        preferences_path=RUNTIME_PATHS.preferences_path,
    )


def _database_initialization_required() -> bool:
    from astro_viewer.app.database.bootstrap import database_initialization_required

    database_path, schema_path = _database_paths()
    return database_initialization_required(database_path, schema_path, geonames_data_dir=_data_dir())


def _create_initialization_splash(app):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QVBoxLayout,
        QWidget,
    )

    dialog = QDialog()
    dialog.setWindowTitle(APP_NAME)
    dialog.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dialog.setAttribute(Qt.WA_TranslucentBackground, True)
    dialog.setModal(False)
    dialog.setFixedWidth(520)
    dialog.setStyleSheet(
        """
        QDialog {
            background-color: transparent;
        }
        QWidget#splashSurface {
            background-color: #14181f;
            border: 1px solid #343c49;
            border-radius: 8px;
        }
        QLabel#appName {
            color: #f4f7fb;
            font-size: 26px;
            font-weight: 600;
        }
        QLabel#message {
            color: #cbd4df;
            font-size: 15px;
        }
        QLabel#secondary {
            color: #8f9baa;
            font-size: 12px;
        }
        QWidget#steps {
            background-color: #1a2029;
            border: 1px solid #2c3440;
            border-radius: 6px;
        }
        QLabel[stepState="pending"] {
            color: #7f8a98;
        }
        QLabel[stepState="active"] {
            color: #f4f7fb;
            font-weight: 600;
        }
        QLabel[stepState="complete"] {
            color: #aeb9c6;
        }
        QLabel#stepBadge {
            min-width: 24px;
            max-width: 24px;
            min-height: 24px;
            max-height: 24px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }
        QLabel#stepBadge[stepState="pending"] {
            color: #7f8a98;
            background-color: #222934;
            border: 1px solid #394351;
        }
        QLabel#stepBadge[stepState="active"] {
            color: #10171d;
            background-color: #6fd6e7;
            border: 1px solid #8be0ed;
        }
        QLabel#stepBadge[stepState="complete"] {
            color: #b9eaf1;
            background-color: #253b43;
            border: 1px solid #40727b;
        }
        QLabel#status {
            color: #d7dee8;
            font-size: 13px;
        }
        QLabel#stepCounter {
            color: #8f9baa;
            font-size: 12px;
        }
        QProgressBar {
            min-height: 10px;
            max-height: 10px;
            border: none;
            border-radius: 5px;
            background-color: #252c36;
        }
        QProgressBar::chunk {
            border-radius: 5px;
            background-color: #6fd6e7;
        }
        """
    )

    window_layout = QVBoxLayout(dialog)
    window_layout.setContentsMargins(0, 0, 0, 0)
    surface = QWidget(dialog)
    surface.setObjectName("splashSurface")
    surface.setAttribute(Qt.WA_StyledBackground, True)
    window_layout.addWidget(surface)

    layout = QVBoxLayout(surface)
    layout.setContentsMargins(32, 28, 32, 30)
    layout.setSpacing(12)

    header = QHBoxLayout()
    header.setSpacing(18)
    icon_label = QLabel()
    icon_label.setFixedSize(72, 72)
    icon_label.setAlignment(Qt.AlignCenter)
    app_icon = QIcon(str(BASE_DIR / "resources" / "icons" / "nightscope.ico"))
    icon = app_icon.pixmap(64, 64) if not app_icon.isNull() else QPixmap()
    if icon.isNull():
        icon = QPixmap(str(BASE_DIR / "resources" / "icons" / "telescope.svg")).scaled(
            64,
            64,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
    if not icon.isNull():
        icon_label.setPixmap(icon)
    header.addWidget(icon_label)

    title_layout = QVBoxLayout()
    title_layout.setSpacing(3)
    title_layout.addStretch()
    app_name = QLabel(APP_NAME)
    app_name.setObjectName("appName")
    title_layout.addWidget(app_name)
    message = QLabel("Preparing NightScope for first use")
    message.setObjectName("message")
    title_layout.addWidget(message)
    secondary = QLabel("This one-time setup may take a minute.")
    secondary.setObjectName("secondary")
    title_layout.addWidget(secondary)
    title_layout.addStretch()
    header.addLayout(title_layout, 1)
    layout.addLayout(header)

    steps_widget = QWidget()
    steps_widget.setObjectName("steps")
    steps_layout = QVBoxLayout(steps_widget)
    steps_layout.setContentsMargins(16, 12, 16, 12)
    steps_layout.setSpacing(9)
    step_labels = []
    for index, label_text in enumerate(
        ("Database", "Local catalogues", "Application services", "Interface")
    ):
        step_row = QHBoxLayout()
        step_row.setSpacing(10)
        badge = QLabel(str(index + 1))
        badge.setObjectName("stepBadge")
        badge.setAlignment(Qt.AlignCenter)
        label = QLabel(label_text)
        step_state = "active" if index == 0 else "pending"
        badge.setProperty("stepState", step_state)
        label.setProperty("stepState", step_state)
        step_row.addWidget(badge)
        step_row.addWidget(label, 1)
        steps_layout.addLayout(step_row)
        step_labels.append((badge, label))
    layout.addWidget(steps_widget)

    status_row = QHBoxLayout()
    status = QLabel("Creating the local database...")
    status.setObjectName("status")
    status_row.addWidget(status, 1)
    step_counter = QLabel("Step 1 of 4")
    step_counter.setObjectName("stepCounter")
    step_counter.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    status_row.addWidget(step_counter)
    layout.addLayout(status_row)

    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(8)
    progress.setTextVisible(False)
    layout.addWidget(progress)

    dialog.show()
    app.processEvents()
    return _InitializationSplash(
        dialog=dialog,
        status=status,
        progress=progress,
        step_labels=tuple(step_labels),
        step_counter=step_counter,
    )


def _initialization_progress_state(message: object) -> _InitializationProgressState:
    source = str(getattr(message, "source", message))
    values = getattr(message, "values", {})

    if source == "Creazione database...":
        return _InitializationProgressState(0, 12, "Creating the local database...")
    if source == "Ricostruzione database locale...":
        return _InitializationProgressState(0, 14, "Rebuilding the local database...")
    if source == "Importazione cataloghi...":
        return _InitializationProgressState(1, 28, "Preparing the local catalogues...")
    if source == "Importazione catalogo città... {rows} righe":
        try:
            rows = max(0, int(values.get("rows", 0)))
        except (TypeError, ValueError):
            rows = 0
        percent = min(68, 34 + rows // 1_000)
        return _InitializationProgressState(
            1,
            percent,
            f"Importing the city catalogue - {rows:,} rows processed",
        )
    if source == "Finalizzazione...":
        return _InitializationProgressState(1, 74, "Finalizing the local catalogues...")
    if source == _STARTUP_SERVICES_MESSAGE:
        return _InitializationProgressState(2, 82, source)
    if source == _STARTUP_INTERFACE_MESSAGE:
        return _InitializationProgressState(3, 94, source)
    if source == _STARTUP_READY_MESSAGE:
        return _InitializationProgressState(3, 100, source)
    return _InitializationProgressState(0, 8, "Preparing local data...")


def _set_initialization_step_state(splash: _InitializationSplash, active_stage: int) -> None:
    for index, (badge, label) in enumerate(splash.step_labels):
        step_state = (
            "complete"
            if index < active_stage
            else "active"
            if index == active_stage
            else "pending"
        )
        for widget in (badge, label):
            widget.setProperty("stepState", step_state)
            widget.style().unpolish(widget)
            widget.style().polish(widget)


def _update_initialization_splash(
    app, splash: _InitializationSplash | None, message: object
) -> None:
    if not splash:
        return

    state = _initialization_progress_state(message)
    splash.status.setText(state.detail)
    splash.progress.setValue(max(splash.progress.value(), state.percent))
    splash.step_counter.setText(f"Step {state.stage + 1} of {len(splash.step_labels)}")
    _set_initialization_step_state(splash, state.stage)
    app.processEvents()


def _close_initialization_splash_after_first_frame(
    app,
    splash: _InitializationSplash,
    root_object,
    *,
    fallback_ms: int = 2_000,
) -> None:
    from PySide6.QtCore import QTimer

    frame_swapped = getattr(root_object, "frameSwapped", None)
    completed = False
    close_scheduled = False

    def close_splash() -> None:
        nonlocal completed
        if completed:
            return
        completed = True
        if frame_swapped is not None:
            try:
                frame_swapped.disconnect(schedule_close)
            except (RuntimeError, TypeError):
                pass
        _update_initialization_splash(app, splash, _STARTUP_READY_MESSAGE)
        splash.dialog.close()

    def schedule_close() -> None:
        nonlocal close_scheduled
        if completed or close_scheduled:
            return
        close_scheduled = True
        QTimer.singleShot(0, splash.dialog, close_splash)

    if frame_swapped is None:
        schedule_close()
    else:
        frame_swapped.connect(schedule_close)
    QTimer.singleShot(fallback_ms, splash.dialog, close_splash)


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
        from PySide6.QtCore import QTimer, QUrl
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
    _configure_application_metadata(app)
    translation_manager = _build_translation_manager()
    translation_manager.install()
    appearance_manager = _build_appearance_manager()
    update_manager = _build_update_manager()

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
            splash.dialog.close()
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
        _update_initialization_splash(app, splash, _STARTUP_INTERFACE_MESSAGE)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(BASE_DIR / "app" / "ui"))
    engine.rootContext().setContextProperty("appController", controller)
    engine.rootContext().setContextProperty("translationManager", translation_manager)
    engine.rootContext().setContextProperty("appearanceManager", appearance_manager)
    engine.rootContext().setContextProperty("updateManager", update_manager)
    engine.rootContext().setContextProperty(
        "platformCapabilities",
        PLATFORM_CAPABILITIES.as_qml_context(),
    )
    engine.load(QUrl.fromLocalFile(str(BASE_DIR / "app" / "ui" / "main.qml")))
    translation_manager.attach_engine(engine)

    if not engine.rootObjects():
        if splash:
            splash.dialog.close()
        translation_manager.detach_engine()
        del engine
        return 1
    if splash:
        _close_initialization_splash_after_first_frame(
            app,
            splash,
            engine.rootObjects()[0],
        )
    QTimer.singleShot(750, update_manager.checkForUpdates)
    exit_code = app.exec()
    translation_manager.detach_engine()
    del engine
    return exit_code


def run_qml_smoke_test(*, red_night_vision: bool = False) -> int:
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
    _configure_application_metadata(app)
    translation_manager = _build_translation_manager()
    translation_manager.install()
    appearance_manager = _build_appearance_manager()
    update_manager = _build_update_manager()
    if red_night_vision:
        appearance_manager.setRedNightVisionEnabled(True)
    controller = _build_controller()
    translation_manager.languageChanged.connect(controller.retranslatePresentation)
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(BASE_DIR / "app" / "ui"))
    engine.rootContext().setContextProperty("appController", controller)
    engine.rootContext().setContextProperty("translationManager", translation_manager)
    engine.rootContext().setContextProperty("appearanceManager", appearance_manager)
    engine.rootContext().setContextProperty("updateManager", update_manager)
    engine.rootContext().setContextProperty(
        "platformCapabilities",
        PLATFORM_CAPABILITIES.as_qml_context(),
    )
    engine.load(QUrl.fromLocalFile(str(BASE_DIR / "app" / "ui" / "main.qml")))
    translation_manager.attach_engine(engine)
    if not engine.rootObjects():
        translation_manager.detach_engine()
        del engine
        return 1
    QTimer.singleShot(0, app.quit)
    app.exec()
    translation_manager.detach_engine()
    del engine
    mode = "red night vision" if red_night_vision else "normal"
    print(f"QML smoke test ok ({mode})")
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
    parser.add_argument(
        "--red-night-vision",
        action="store_true",
        help="Enable red night vision for the QML smoke test.",
    )
    return parser.parse_args()


def main() -> int:
    from astro_viewer.app.services.logging_service import configure_logging

    try:
        configure_logging(RUNTIME_PATHS.state_dir)
    except OSError:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
        logging.getLogger(__name__).warning(
            "Runtime log directory is not writable; continuing with console logging.",
            exc_info=True,
        )
    try:
        args = parse_args()
        if args.qml_smoke_test:
            return run_qml_smoke_test(red_night_vision=args.red_night_vision)
        if args.smoke_test:
            return run_smoke_test()
        return run_app()
    except Exception:
        logging.getLogger(__name__).exception("Unhandled NightScope error.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
