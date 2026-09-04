"""Render editorial-batch detail samples in every supported display language and theme."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, required=True, help="editorial batch manifest")
    parser.add_argument("--output-dir", type=Path, required=True, help="screenshot destination")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument(
        "--scroll-y",
        type=int,
        default=570,
        help="vertical detail-page offset used to expose description and curiosity cards",
    )
    return parser.parse_args(argv)


def _sample_ids(batch_path: Path) -> list[str]:
    payload = json.loads(batch_path.read_text(encoding="utf-8"))
    samples = payload.get("visual_review", {}).get("samples", [])
    object_ids = [
        str(sample.get("object_id") or "").strip()
        for sample in samples
        if isinstance(sample, dict)
    ]
    object_ids = [object_id for object_id in object_ids if object_id]
    if not object_ids:
        raise ValueError("the manifest has no visual-review samples")
    if len(object_ids) != len(set(object_ids)):
        raise ValueError("visual-review sample IDs must be unique")
    return object_ids


def _settle(app, milliseconds: int = 180) -> None:
    deadline = time.monotonic() + milliseconds / 1000
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()


def _set_detail_scroll(root, offset: int) -> None:
    from PySide6.QtCore import QObject

    scroll = root.findChild(QObject, "objectDetailScroll")
    if scroll is None:
        raise RuntimeError("objectDetailScroll was not created")
    flickables = [
        child
        for child in scroll.findChildren(QObject)
        if child.metaObject().indexOfProperty("contentY") >= 0
        and child.metaObject().indexOfProperty("contentHeight") >= 0
    ]
    if not flickables:
        raise RuntimeError("objectDetailScroll has no internal flickable")
    content_item = max(
        flickables,
        key=lambda child: float(child.property("contentHeight") or 0),
    )
    content_height = float(content_item.property("contentHeight") or 0)
    viewport_height = float(content_item.property("height") or 0)
    maximum = max(0, int(content_height - viewport_height))
    content_item.setProperty("contentY", min(max(0, offset), maximum))


def _render_contact_sheet(image_paths: list[Path], destination: Path) -> None:
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QColor, QFont, QImage, QPainter

    columns = 2
    cell_width = 720
    cell_height = 520
    label_height = 34
    rows = (len(image_paths) + columns - 1) // columns
    canvas = QImage(
        columns * cell_width,
        rows * cell_height,
        QImage.Format.Format_RGB32,
    )
    canvas.fill(QColor("#070b12"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setPen(QColor("#e6edf3"))
    painter.setFont(QFont("Segoe UI", 12))
    for index, image_path in enumerate(image_paths):
        source = QImage(str(image_path))
        column = index % columns
        row = index // columns
        cell_x = column * cell_width
        cell_y = row * cell_height
        target = QRect(cell_x + 8, cell_y + label_height, cell_width - 16, cell_height - label_height - 8)
        scaled = source.scaled(
            target.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        image_x = target.x() + (target.width() - scaled.width()) // 2
        painter.drawImage(image_x, target.y(), scaled)
        painter.drawText(
            QRect(cell_x + 12, cell_y, cell_width - 24, label_height),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            image_path.stem,
        )
    painter.end()
    if not canvas.save(str(destination)):
        raise RuntimeError(f"could not save contact sheet: {destination}")


def _install_review_font(app) -> str:
    """Register a deterministic UI font for headless Windows rendering."""
    from PySide6.QtGui import QFont, QFontDatabase

    candidates: list[Path] = []
    windows_dir = os.environ.get("WINDIR")
    if windows_dir:
        candidates.append(Path(windows_dir) / "Fonts" / "segoeui.ttf")
    candidates.extend(
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        )
    )
    for font_path in candidates:
        if not font_path.is_file():
            continue
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id < 0:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            app.setFont(QFont(families[0]))
            return families[0]
    return app.font().family()


def render_samples(args: argparse.Namespace) -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QSG_RHI_BACKEND", "software")

    isolated_runtime = None
    if not os.environ.get("NIGHTSCOPE_RUNTIME_DIR"):
        isolated_runtime = tempfile.TemporaryDirectory(prefix="nightscope-editorial-render-")
        os.environ["NIGHTSCOPE_RUNTIME_DIR"] = isolated_runtime.name

    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow
    from shiboken6 import getCppPointer, wrapInstance

    from astro_viewer import main as app_main

    batch_path = args.batch if args.batch.is_absolute() else ROOT / args.batch
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_ids = _sample_ids(batch_path)

    app = QGuiApplication(sys.argv[:1])
    review_font = _install_review_font(app)
    app_main._configure_application_metadata(app)
    translation_manager = app_main._build_translation_manager()
    if not translation_manager.install():
        raise RuntimeError("the initial language pack could not be installed")
    appearance_manager = app_main._build_appearance_manager()
    update_manager = app_main._build_update_manager()
    controller = app_main._build_controller()
    translation_manager.languageChanged.connect(controller.retranslatePresentation)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(app_main.BASE_DIR / "app" / "ui"))
    engine.rootContext().setContextProperty("appController", controller)
    engine.rootContext().setContextProperty("translationManager", translation_manager)
    engine.rootContext().setContextProperty("appearanceManager", appearance_manager)
    engine.rootContext().setContextProperty("updateManager", update_manager)
    engine.rootContext().setContextProperty(
        "platformCapabilities",
        app_main.PLATFORM_CAPABILITIES.as_qml_context(),
    )
    engine.load(QUrl.fromLocalFile(str(app_main.BASE_DIR / "app" / "ui" / "main.qml")))
    translation_manager.attach_engine(engine)
    if not engine.rootObjects():
        raise RuntimeError("the QML scene could not be loaded")

    root = engine.rootObjects()[0]
    quick_root = wrapInstance(getCppPointer(root)[0], QQuickWindow)
    root.showNormal()
    root.setWidth(args.width)
    root.setHeight(args.height)
    root.setProperty("detailBackTarget", "objectCatalogue")
    root.setProperty("currentPage", "detail")
    _settle(app, 350)

    for language in ("it", "en", "es"):
        if not translation_manager.setLanguage(language):
            raise RuntimeError(f"language pack could not be selected: {language}")
        _settle(app)
        for mode_name, red_night_vision in (("normal", False), ("red", True)):
            appearance_manager.setRedNightVisionEnabled(red_night_vision)
            _settle(app)
            rendered: list[Path] = []
            for object_id in sample_ids:
                controller.selectCatalogueObject(object_id)
                root.setProperty("currentPage", "detail")
                _settle(app, 250)
                _set_detail_scroll(root, args.scroll_y)
                _settle(app, 120)
                image = quick_root.grabWindow()
                if image.isNull():
                    raise RuntimeError(f"empty render for {object_id} ({language}, {mode_name})")
                destination = output_dir / f"{language}_{mode_name}_{object_id}.png"
                if not image.save(str(destination)):
                    raise RuntimeError(f"could not save render: {destination}")
                rendered.append(destination)
            _render_contact_sheet(
                rendered,
                output_dir / f"contact_{language}_{mode_name}.png",
            )

    translation_manager.detach_engine()
    root.close()
    _settle(app, 50)
    del engine
    del controller
    if isolated_runtime is not None:
        try:
            isolated_runtime.cleanup()
        except OSError:
            pass
    print(
        f"Editorial visual samples rendered: {len(sample_ids)} objects, "
        f"3 languages, 2 themes, font {review_font!r} -> {output_dir}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.width < 1040 or args.height < 700:
        raise SystemExit("width must be at least 1040 and height at least 700")
    if args.scroll_y < 0:
        raise SystemExit("scroll-y must be non-negative")
    return render_samples(args)


if __name__ == "__main__":
    raise SystemExit(main())
