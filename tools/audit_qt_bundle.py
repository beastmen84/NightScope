from __future__ import annotations

import argparse
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


def audit_bundle(bundle_dir: Path) -> list[str]:
    errors: list[str] = []
    if not bundle_dir.is_dir():
        return [f"bundle directory does not exist: {bundle_dir}"]

    files = [path for path in bundle_dir.rglob("*") if path.is_file()]
    filenames = {path.name.lower() for path in files}
    missing_dlls = sorted(REQUIRED_DLLS - filenames)
    if missing_dlls:
        errors.append("missing required Qt DLLs: " + ", ".join(missing_dlls))

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
        normalized_path = f"/{relative.as_posix().lower()}/"
        if (
            lowered_parts & FORBIDDEN_PATH_PARTS
            or any(
                fragment in normalized_path
                for fragment in FORBIDDEN_PATH_FRAGMENTS
            )
            or any(
                lowered_name.startswith(prefix)
                for prefix in FORBIDDEN_DLL_PREFIXES
            )
        ):
            forbidden.append(relative.as_posix())
    if forbidden:
        errors.append(
            "unexpected GPL-only Qt modules: " + ", ".join(sorted(forbidden))
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit a NightScope PyInstaller bundle for its Qt/legal contract."
    )
    parser.add_argument("bundle_dir", type=Path)
    args = parser.parse_args()

    errors = audit_bundle(args.bundle_dir.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Qt, legal-file, and runtime-state bundle audit passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
