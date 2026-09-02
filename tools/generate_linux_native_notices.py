"""Inventory bundled Linux binaries and write exact package and license provenance."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import platform
import re
import shutil
import subprocess
import sys
import sysconfig
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote


MANIFEST_NAME = "LINUX_NATIVE_COMPONENTS.tsv"
NOTICE_ROOT = Path("legal") / "linux-native"
COMMON_LICENSE_PATTERN = re.compile(
    r"/usr/share/common-licenses/([A-Za-z0-9][A-Za-z0-9.+_-]*)"
)
COMMON_LICENSE_ALIASES = {
    "GPL-1.0": "GPL-1",
    "GPL-2.0": "GPL-2",
    "GPL-3.0": "GPL-3",
    "LGPL-2.0": "LGPL-2",
    "LGPL-3.0": "LGPL-3",
}
MANIFEST_FIELDS = (
    "bundle_path",
    "sha256",
    "binary_package",
    "binary_version",
    "source_package",
    "source_version",
    "notice_path",
    "source_url",
)
SYSTEM_SOURCE_ROOTS = (Path("/usr"), Path("/lib"))
LOCAL_INSTALL_ROOT = Path("/usr/local")
SUPPORTED_PACKAGE_ORIGINS = {"debian", "ubuntu"}
PYTHON_RUNTIME_PACKAGE = "python.org-cpython"
PYTHON_SOURCE_PACKAGE = "Python"


@dataclass(frozen=True)
class CollectedBinary:
    bundle_path: PurePosixPath
    source_path: Path


@dataclass(frozen=True)
class PackageMetadata:
    binary_package: str
    binary_version: str
    source_package: str
    source_version: str
    copyright_path: Path
    source_url: str


@dataclass(frozen=True)
class ManifestRecord:
    binary: CollectedBinary
    package: PackageMetadata
    sha256: str
    notice_path: PurePosixPath

    def as_row(self) -> dict[str, str]:
        return {
            "bundle_path": self.binary.bundle_path.as_posix(),
            "sha256": self.sha256,
            "binary_package": self.package.binary_package,
            "binary_version": self.package.binary_version,
            "source_package": self.package.source_package,
            "source_version": self.package.source_version,
            "notice_path": self.notice_path.as_posix(),
            "source_url": self.package.source_url,
        }


def _is_system_source(path: Path) -> bool:
    posix_path = PurePosixPath(path.as_posix())
    if not posix_path.is_absolute():
        return False
    local_install_root = PurePosixPath(LOCAL_INSTALL_ROOT.as_posix())
    if (
        posix_path == local_install_root
        or posix_path.is_relative_to(local_install_root)
    ):
        return sys.platform.startswith("linux") and _is_unmanaged_python_runtime(path)
    return any(
        posix_path == PurePosixPath(root.as_posix())
        or posix_path.is_relative_to(PurePosixPath(root.as_posix()))
        for root in SYSTEM_SOURCE_ROOTS
    )


def linux_package_origin(
    os_release: dict[str, str] | None = None,
) -> str:
    release = os_release or platform.freedesktop_os_release()
    identifiers = [
        release.get("ID", ""),
        *release.get("ID_LIKE", "").split(),
    ]
    for candidate in identifiers:
        normalized = candidate.strip().lower()
        if normalized in SUPPORTED_PACKAGE_ORIGINS:
            return normalized
    raise RuntimeError(
        "Linux native-component notices support Debian- or Ubuntu-derived "
        "build environments; /etc/os-release identifies "
        f"{release.get('ID', 'unknown')!r}."
    )


def source_package_url(
    package_origin: str,
    source_package: str,
    source_version: str,
) -> str:
    package = quote(source_package, safe="")
    version = quote(source_version, safe="")
    if package_origin == "ubuntu":
        return f"https://launchpad.net/ubuntu/+source/{package}/{version}"
    if package_origin == "debian":
        return f"https://sources.debian.org/src/{package}/{version}/"
    if package_origin == "python":
        return (
            "https://github.com/python/cpython/archive/refs/tags/"
            f"v{version}.tar.gz"
        )
    raise RuntimeError(f"Unsupported Linux package origin: {package_origin}")


def read_collected_system_binaries(collect_toc: Path) -> list[CollectedBinary]:
    try:
        toc = ast.literal_eval(collect_toc.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError) as exc:
        raise RuntimeError(f"Cannot read PyInstaller COLLECT TOC: {collect_toc}") from exc

    if (
        not isinstance(toc, tuple)
        or len(toc) != 1
        or not isinstance(toc[0], list)
    ):
        raise RuntimeError(f"Unexpected PyInstaller COLLECT TOC format: {collect_toc}")

    binaries: list[CollectedBinary] = []
    seen_paths: set[PurePosixPath] = set()
    for entry in toc[0]:
        if not isinstance(entry, tuple) or len(entry) != 3:
            continue
        destination, raw_source, entry_type = entry
        if entry_type not in {"BINARY", "EXTENSION"}:
            continue
        source_path = Path(raw_source)
        if not _is_system_source(source_path):
            continue

        relative_destination = PurePosixPath(str(destination).replace("\\", "/"))
        if relative_destination.is_absolute() or ".." in relative_destination.parts:
            raise RuntimeError(
                f"Unsafe PyInstaller bundle destination: {relative_destination}"
            )
        bundle_path = PurePosixPath("_internal") / relative_destination
        if bundle_path in seen_paths:
            raise RuntimeError(f"Duplicate system binary destination: {bundle_path}")
        seen_paths.add(bundle_path)
        binaries.append(
            CollectedBinary(
                bundle_path=bundle_path,
                source_path=source_path,
            )
        )

    if not binaries:
        raise RuntimeError(f"No Linux native binaries found in {collect_toc}")
    return sorted(binaries, key=lambda item: item.bundle_path.as_posix())


def _run_dpkg(*args: str) -> str:
    try:
        result = subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required command is not installed: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or "no diagnostic output"
        raise RuntimeError(f"{' '.join(args)} failed: {detail}") from exc
    return result.stdout


def _owning_package(source_path: Path) -> str:
    candidates = (source_path, source_path.resolve())
    for candidate in dict.fromkeys(candidates):
        try:
            output = _run_dpkg("dpkg-query", "--search", str(candidate))
        except RuntimeError:
            continue
        for line in output.splitlines():
            package, separator, owned_path = line.partition(": ")
            if separator and Path(owned_path) == candidate:
                return package
    raise RuntimeError(
        f"No installed Debian/Ubuntu package owns {source_path}"
    )


def _package_metadata(
    package: str,
    *,
    package_origin: str,
) -> PackageMetadata:
    output = _run_dpkg(
        "dpkg-query",
        "--show",
        "--showformat=${binary:Package}\\t${Version}\\t"
        "${source:Package}\\t${source:Version}\\n",
        package,
    ).strip()
    fields = output.split("\t")
    if len(fields) != 4 or not all(fields):
        raise RuntimeError(f"Incomplete dpkg metadata for {package}: {output!r}")

    binary_package, binary_version, source_package, source_version = fields
    documentation_package = binary_package.split(":", 1)[0]
    copyright_path = Path("/usr/share/doc") / documentation_package / "copyright"
    if not copyright_path.is_file():
        raise RuntimeError(
            f"Package copyright notice is missing for {binary_package}: "
            f"{copyright_path}"
        )
    return PackageMetadata(
        binary_package=binary_package,
        binary_version=binary_version,
        source_package=source_package,
        source_version=source_version,
        copyright_path=copyright_path,
        source_url=source_package_url(
            package_origin,
            source_package,
            source_version,
        ),
    )


def _python_license_path() -> Path:
    candidates = tuple(
        dict.fromkeys(
            (
                Path(sys.base_prefix) / "LICENSE.txt",
                Path(sys.exec_prefix) / "LICENSE.txt",
                Path(sysconfig.get_path("stdlib")) / "LICENSE.txt",
            )
        )
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    checked_paths = ", ".join(str(path) for path in candidates)
    raise RuntimeError(
        f"Python runtime license file not found; checked: {checked_paths}"
    )


def _is_unmanaged_python_runtime(source_path: Path) -> bool:
    base_prefix = Path(sys.base_prefix).resolve()
    if base_prefix in SYSTEM_SOURCE_ROOTS:
        return False
    resolved_source = source_path.resolve()
    runtime_library_dir = Path(
        sysconfig.get_config_var("LIBDIR") or base_prefix / "lib"
    ).resolve()
    runtime_library_names = {
        str(name)
        for name in (
            sysconfig.get_config_var("LDLIBRARY"),
            sysconfig.get_config_var("INSTSONAME"),
        )
        if name
    }
    if (
        runtime_library_names
        and resolved_source.parent == runtime_library_dir
        and resolved_source.name in runtime_library_names
    ):
        return True

    lib_dynload = Path(sysconfig.get_path("stdlib")).resolve() / "lib-dynload"
    return (
        resolved_source == lib_dynload
        or resolved_source.is_relative_to(lib_dynload)
    )


def _python_runtime_metadata() -> PackageMetadata:
    version = sys.version.split()[0]
    return PackageMetadata(
        binary_package=PYTHON_RUNTIME_PACKAGE,
        binary_version=version,
        source_package=PYTHON_SOURCE_PACKAGE,
        source_version=version,
        copyright_path=_python_license_path(),
        source_url=source_package_url("python", PYTHON_SOURCE_PACKAGE, version),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _notice_text(
    source_package: str,
    package_notices: dict[str, str],
) -> str:
    unique_texts: dict[str, tuple[list[str], str]] = {}
    for binary_package, text in sorted(package_notices.items()):
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in unique_texts:
            unique_texts[digest][0].append(binary_package)
        else:
            unique_texts[digest] = ([binary_package], text)

    if len(unique_texts) == 1:
        return next(iter(unique_texts.values()))[1].rstrip() + "\n"

    sections = [
        f"Copyright notices for source package {source_package}",
        "=" * 72,
        "",
        "The following sections reproduce the installed component copyright",
        "files verbatim. Section labels identify the binary packages that supplied",
        "each distinct notice.",
    ]
    for packages, text in sorted(unique_texts.values(), key=lambda item: item[0]):
        sections.extend(
            [
                "",
                f"Binary packages: {', '.join(packages)}",
                "-" * 72,
                text.rstrip(),
            ]
        )
    return "\n".join(sections).rstrip() + "\n"


def _referenced_common_licenses(text: str) -> set[str]:
    return {
        match.rstrip(".,;:")
        for match in COMMON_LICENSE_PATTERN.findall(text)
    }


def _common_license_source(
    name: str,
    *,
    common_license_root: Path = Path("/usr/share/common-licenses"),
) -> Path:
    source = common_license_root / name
    if source.is_file():
        return source
    alias = COMMON_LICENSE_ALIASES.get(name)
    if alias:
        aliased_source = common_license_root / alias
        if aliased_source.is_file():
            return aliased_source
    raise RuntimeError(f"Referenced Linux common license is missing: {source}")


def generate_native_notices(
    bundle_dir: Path,
    collect_toc: Path,
) -> tuple[int, int, int]:
    if not bundle_dir.is_dir():
        raise RuntimeError(f"Bundle directory does not exist: {bundle_dir}")

    binaries = read_collected_system_binaries(collect_toc)
    package_origin = linux_package_origin()
    metadata_cache: dict[str, PackageMetadata] = {}
    package_notices: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    pending_records: list[tuple[CollectedBinary, PackageMetadata, str]] = []

    for binary in binaries:
        bundled_file = bundle_dir / Path(binary.bundle_path.as_posix())
        if not bundled_file.is_file():
            raise RuntimeError(
                f"System binary recorded by PyInstaller is missing: "
                f"{binary.bundle_path}"
            )
        try:
            owner = _owning_package(binary.source_path)
        except RuntimeError:
            if not _is_unmanaged_python_runtime(binary.source_path):
                raise
            owner = PYTHON_RUNTIME_PACKAGE
            if owner not in metadata_cache:
                metadata_cache[owner] = _python_runtime_metadata()
        else:
            if owner not in metadata_cache:
                metadata_cache[owner] = _package_metadata(
                    owner,
                    package_origin=package_origin,
                )
        package = metadata_cache[owner]
        copyright_text = package.copyright_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).lstrip("\ufeff")
        package_notices[(package.source_package, package.source_version)][
            package.binary_package
        ] = copyright_text
        pending_records.append((binary, package, _sha256(bundled_file)))

    notice_root = bundle_dir / NOTICE_ROOT
    if notice_root.exists():
        shutil.rmtree(notice_root)
    notice_root.mkdir(parents=True)

    notice_paths: dict[tuple[str, str], PurePosixPath] = {}
    common_license_names: set[str] = set()
    for (source_package, source_version), notices in sorted(package_notices.items()):
        relative_path = (
            PurePosixPath(NOTICE_ROOT.as_posix())
            / source_package
            / "copyright"
        )
        destination = bundle_dir / Path(relative_path.as_posix())
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = _notice_text(source_package, notices)
        destination.write_text(text, encoding="utf-8", newline="\n")
        notice_paths[(source_package, source_version)] = relative_path
        common_license_names.update(_referenced_common_licenses(text))

    common_license_dir = notice_root / "common-licenses"
    common_license_dir.mkdir()
    for name in sorted(common_license_names):
        source = _common_license_source(name)
        shutil.copyfile(source, common_license_dir / name)

    records = [
        ManifestRecord(
            binary=binary,
            package=package,
            sha256=digest,
            notice_path=notice_paths[
                (package.source_package, package.source_version)
            ],
        )
        for binary, package, digest in pending_records
    ]
    manifest_path = bundle_dir / MANIFEST_NAME
    with manifest_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=MANIFEST_FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(
            record.as_row()
            for record in sorted(
                records,
                key=lambda item: item.binary.bundle_path.as_posix(),
            )
        )

    return len(records), len(metadata_cache), len(package_notices)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate the manifest and bundled native-component notices for "
            "Linux ELF files collected by PyInstaller."
        )
    )
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument(
        "--collect-toc",
        type=Path,
        required=True,
        help="PyInstaller COLLECT-00.toc produced by the same build",
    )
    args = parser.parse_args()

    try:
        file_count, binary_package_count, source_package_count = (
            generate_native_notices(
                args.bundle_dir.resolve(),
                args.collect_toc.resolve(),
            )
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "Wrote Linux native-component notices for "
        f"{file_count} files, {binary_package_count} binary packages, and "
        f"{source_package_count} source packages."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
