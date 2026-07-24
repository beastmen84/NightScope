from __future__ import annotations

import argparse
import sys
from pathlib import Path


REQUIRED_DLLS = {
    "effectsplugin.dll",
    "qt6core.dll",
    "qt6gui.dll",
    "qt6qml.dll",
    "qt6positioning.dll",
    "qt6quick.dll",
    "qt6quickeffects.dll",
    "qt6widgets.dll",
}
REQUIRED_LINUX_LIBRARIES = {
    "libeffectsplugin.so",
    "libqt6core.so.6",
    "libqt6gui.so.6",
    "libqt6qml.so.6",
    "libqt6positioning.so.6",
    "libqt6quick.so.6",
    "libqt6quickeffects.so.6",
    "libqt6widgets.so.6",
}
REQUIRED_LEGAL_FILES = {
    "LICENSE",
    "THIRD_PARTY_LICENSES.txt",
    "THIRD_PARTY_NOTICES.md",
}
REQUIRED_DATA_FILES = {
    "mpc_observatories_seed.csv",
}
FORBIDDEN_RUNTIME_ENTRIES = {
    "location_cache.json",
    "logs",
    "nasa_aod_cache.json",
    "nightscope.db",
    "user_preferences.json",
}
FORBIDDEN_PATH_PARTS = {
    "qtcanvaspainter",
    "qtcoap",
    "qtgraphs",
    "qtgrpc",
    "qthttpserver",
    "qtlottieanimation",
    "qtmqtt",
    "qtnetworkauth",
    "qtqmlcompiler",
    "qtquick3d",
    "qtquicktimeline",
    "qtvirtualkeyboard",
    "qtwaylandcompositor",
}
FORBIDDEN_PATH_FRAGMENTS = {
    "/qtquick/timeline/",
    "/qtquick/virtualkeyboard/",
}
FORBIDDEN_DLL_PREFIXES = {
    "qt6canvaspainter",
    "qt6coap",
    "qt6graphs",
    "qt6grpc",
    "qt6httpserver",
    "qt6lottieanimation",
    "qt6mqtt",
    "qt6networkauth",
    "qt6qmlcompiler",
    "qt6quick3d",
    "qt6quicktimeline",
    "qt6virtualkeyboard",
    "qt6waylandcompositor",
    "qmldbg_quick3d",
    "qtvirtualkeyboardplugin",
}
UNSUPPORTED_LINUX_QT_PLUGINS = {
    "libqtiff.so",
}


def _bundle_platform(filenames: set[str], platform_name: str | None) -> str:
    if platform_name:
        if platform_name not in {"linux", "windows"}:
            raise ValueError(f"Unsupported bundle platform: {platform_name}")
        return platform_name
    if "qt6core.dll" in filenames:
        return "windows"
    if "libqt6core.so.6" in filenames:
        return "linux"
    return "windows" if sys.platform == "win32" else "linux"


def audit_bundle(
    bundle_dir: Path,
    *,
    platform_name: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not bundle_dir.is_dir():
        return [f"bundle directory does not exist: {bundle_dir}"]

    files = [path for path in bundle_dir.rglob("*") if path.is_file()]
    filenames = {path.name.lower() for path in files}
    bundle_platform = _bundle_platform(filenames, platform_name)
    required_qt_files = (
        REQUIRED_DLLS
        if bundle_platform == "windows"
        else REQUIRED_LINUX_LIBRARIES
    )
    missing_qt_files = sorted(required_qt_files - filenames)
    if missing_qt_files:
        label = "Qt DLLs" if bundle_platform == "windows" else "Qt shared libraries"
        errors.append(f"missing required {label}: " + ", ".join(missing_qt_files))

    missing_legal = sorted(
        filename
        for filename in REQUIRED_LEGAL_FILES
        if not (bundle_dir / filename).is_file()
    )
    if missing_legal:
        errors.append("missing legal files: " + ", ".join(missing_legal))

    missing_data = sorted(REQUIRED_DATA_FILES - filenames)
    if missing_data:
        errors.append("missing required data files: " + ", ".join(missing_data))

    runtime_entries = sorted(
        path.name
        for path in bundle_dir.iterdir()
        if path.name.lower() in FORBIDDEN_RUNTIME_ENTRIES
        or path.name.lower().startswith(("nightscope.db.", "nightscope.db-"))
    )
    if runtime_entries:
        errors.append(
            "runtime state present in release bundle: "
            + ", ".join(runtime_entries)
        )

    forbidden: list[str] = []
    for path in files:
        relative = path.relative_to(bundle_dir)
        lowered_parts = {part.lower() for part in relative.parts}
        lowered_name = path.name.lower()
        normalized_library_name = lowered_name.removeprefix("lib")
        normalized_path = f"/{relative.as_posix().lower()}/"
        if (
            lowered_parts & FORBIDDEN_PATH_PARTS
            or any(
                fragment in normalized_path
                for fragment in FORBIDDEN_PATH_FRAGMENTS
            )
            or any(
                normalized_library_name.startswith(prefix)
                for prefix in FORBIDDEN_DLL_PREFIXES
            )
        ):
            forbidden.append(relative.as_posix())
    if forbidden:
        errors.append(
            "unexpected GPL-only Qt modules: " + ", ".join(sorted(forbidden))
        )
    if bundle_platform == "linux":
        unsupported_plugins = sorted(
            path.relative_to(bundle_dir).as_posix()
            for path in files
            if path.name.lower() in UNSUPPORTED_LINUX_QT_PLUGINS
        )
        if unsupported_plugins:
            errors.append(
                "unsupported Linux Qt plugins: "
                + ", ".join(unsupported_plugins)
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit a NightScope PyInstaller bundle for its Qt/legal contract."
    )
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument(
        "--platform",
        choices=("linux", "windows"),
        help="Override automatic bundle-platform detection.",
    )
    args = parser.parse_args()

    errors = audit_bundle(
        args.bundle_dir.resolve(),
        platform_name=args.platform,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Qt, legal-file, and runtime-state bundle audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
