"""Audit a PyInstaller bundle against NightScope's Qt, data, and legal allowlists."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from pathlib import Path, PurePosixPath
from urllib.parse import quote


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
    "OPENNGC_LICENSE.txt",
    "SOURCE_CODE.md",
    "THIRD_PARTY_LICENSES.txt",
    "THIRD_PARTY_NOTICES.md",
}
LINUX_NATIVE_MANIFEST = "LINUX_NATIVE_COMPONENTS.tsv"
LINUX_NATIVE_NOTICE_ROOT = PurePosixPath("legal/linux-native")
LINUX_NATIVE_MANIFEST_FIELDS = (
    "bundle_path",
    "sha256",
    "binary_package",
    "binary_version",
    "source_package",
    "source_version",
    "notice_path",
    "source_url",
)
COMMON_LICENSE_PATTERN = re.compile(
    r"/usr/share/common-licenses/([A-Za-z0-9][A-Za-z0-9.+_-]*)"
)
PYTHON_RUNTIME_DIRECTORY_PATTERN = re.compile(r"python\d+\.\d+")
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_bundle_path(raw_path: str) -> PurePosixPath | None:
    path = PurePosixPath(raw_path)
    if not raw_path or path.is_absolute() or ".." in path.parts:
        return None
    return path


def _linux_native_candidates(bundle_dir: Path) -> set[str]:
    candidates: set[str] = set()
    internal_dir = bundle_dir / "_internal"
    if not internal_dir.is_dir():
        return candidates

    for path in internal_dir.rglob("*"):
        if path.is_symlink() or not path.is_file() or ".so" not in path.name:
            continue
        relative = path.relative_to(bundle_dir)
        parts = relative.parts
        is_top_level_library = (
            len(parts) == 2
            and parts[0] == "_internal"
            and path.name.startswith("lib")
        )
        is_python_runtime_extension = (
            len(parts) >= 4
            and parts[0] == "_internal"
            and PYTHON_RUNTIME_DIRECTORY_PATTERN.fullmatch(parts[1]) is not None
            and parts[2] == "lib-dynload"
        )
        if is_top_level_library or is_python_runtime_extension:
            candidates.add(relative.as_posix())
    return candidates


def _referenced_common_licenses(text: str) -> set[str]:
    return {
        match.rstrip(".,;:")
        for match in COMMON_LICENSE_PATTERN.findall(text)
    }


def _valid_linux_source_urls(
    source_package: str,
    source_version: str,
) -> set[str]:
    package = quote(source_package, safe="")
    version = quote(source_version, safe="")
    urls = {
        (
            "https://launchpad.net/ubuntu/+source/"
            f"{package}/{version}"
        ),
        f"https://sources.debian.org/src/{package}/{version}/",
    }
    if source_package == "Python":
        urls.update(
            {
                (
                    "https://github.com/python/cpython/archive/refs/tags/"
                    f"v{version}.tar.gz"
                ),
                (
                    "https://www.python.org/ftp/python/"
                    f"{version}/Python-{version}.tgz"
                ),
            }
        )
    return urls


def _audit_linux_native_notices(bundle_dir: Path) -> list[str]:
    manifest_path = bundle_dir / LINUX_NATIVE_MANIFEST
    if not manifest_path.is_file():
        return [f"missing Linux native-component manifest: {LINUX_NATIVE_MANIFEST}"]

    try:
        with manifest_path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, delimiter="\t")
            if tuple(reader.fieldnames or ()) != LINUX_NATIVE_MANIFEST_FIELDS:
                return [
                    "invalid Linux native-component manifest columns: "
                    f"{LINUX_NATIVE_MANIFEST}"
                ]
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error) as exc:
        return [f"cannot read Linux native-component manifest: {exc}"]

    errors: list[str] = []
    manifest_bundle_paths: set[str] = set()
    referenced_notices: set[PurePosixPath] = set()
    for row_number, row in enumerate(rows, start=2):
        if None in row or any(not row[field] for field in LINUX_NATIVE_MANIFEST_FIELDS):
            errors.append(
                f"incomplete Linux native-component manifest row {row_number}"
            )
            continue

        bundle_path = _safe_bundle_path(row["bundle_path"])
        notice_path = _safe_bundle_path(row["notice_path"])
        if bundle_path is None:
            errors.append(
                f"unsafe Linux native bundle path on row {row_number}: "
                f"{row['bundle_path']}"
            )
            continue
        if (
            notice_path is None
            or notice_path.parts[: len(LINUX_NATIVE_NOTICE_ROOT.parts)]
            != LINUX_NATIVE_NOTICE_ROOT.parts
        ):
            errors.append(
                f"unsafe Linux native notice path on row {row_number}: "
                f"{row['notice_path']}"
            )
            continue

        normalized_bundle_path = bundle_path.as_posix()
        if normalized_bundle_path in manifest_bundle_paths:
            errors.append(
                f"duplicate Linux native manifest entry: {normalized_bundle_path}"
            )
            continue
        manifest_bundle_paths.add(normalized_bundle_path)
        referenced_notices.add(notice_path)

        bundled_file = bundle_dir / Path(normalized_bundle_path)
        if not bundled_file.is_file():
            errors.append(
                f"Linux native manifest file is missing: {normalized_bundle_path}"
            )
        elif not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            errors.append(
                f"invalid Linux native SHA-256: {normalized_bundle_path}"
            )
        elif _sha256(bundled_file) != row["sha256"]:
            errors.append(
                f"Linux native SHA-256 mismatch: {normalized_bundle_path}"
            )

        valid_source_urls = _valid_linux_source_urls(
            row["source_package"],
            row["source_version"],
        )
        if row["source_url"] not in valid_source_urls:
            errors.append(
                f"invalid Linux native source URL on row {row_number}: "
                f"{row['source_url']}"
            )

    candidates = _linux_native_candidates(bundle_dir)
    unmanifested = sorted(candidates - manifest_bundle_paths)
    if unmanifested:
        errors.append(
            "unmanifested Linux native files: " + ", ".join(unmanifested)
        )
    stale_entries = sorted(manifest_bundle_paths - candidates)
    if stale_entries:
        errors.append(
            "stale Linux native manifest entries: " + ", ".join(stale_entries)
        )

    common_license_names: set[str] = set()
    for notice_path in sorted(referenced_notices):
        notice_file = bundle_dir / Path(notice_path.as_posix())
        if not notice_file.is_file():
            errors.append(f"Linux native notice is missing: {notice_path}")
            continue
        text = notice_file.read_text(encoding="utf-8", errors="replace")
        common_license_names.update(_referenced_common_licenses(text))

    missing_common_licenses = sorted(
        name
        for name in common_license_names
        if not (
            bundle_dir
            / Path(LINUX_NATIVE_NOTICE_ROOT.as_posix())
            / "common-licenses"
            / name
        ).is_file()
    )
    if missing_common_licenses:
        errors.append(
            "missing Linux native common-license texts: "
            + ", ".join(missing_common_licenses)
        )
    return errors


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
        errors.extend(_audit_linux_native_notices(bundle_dir))
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
