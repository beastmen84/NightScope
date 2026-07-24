from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote


MANIFEST_NAME = "LINUX_NATIVE_COMPONENTS.tsv"
NOTICE_ROOT = Path("legal") / "linux-native"
COMMON_LICENSE_PATTERN = re.compile(
    r"/usr/share/common-licenses/([A-Za-z0-9][A-Za-z0-9.+_-]*)"
)
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

    @property
    def source_url(self) -> str:
        package = quote(self.source_package, safe="")
        version = quote(self.source_version, safe="")
        return f"https://launchpad.net/ubuntu/+source/{package}/{version}"


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
    return path.is_absolute() and any(
        path == root or path.is_relative_to(root) for root in SYSTEM_SOURCE_ROOTS
    )


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
        raise RuntimeError(f"No Ubuntu system binaries found in {collect_toc}")
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
    raise RuntimeError(f"No installed Ubuntu package owns {source_path}")


def _package_metadata(package: str) -> PackageMetadata:
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
            f"Ubuntu copyright notice is missing for {binary_package}: "
            f"{copyright_path}"
        )
    return PackageMetadata(
        binary_package=binary_package,
        binary_version=binary_version,
        source_package=source_package,
        source_version=source_version,
        copyright_path=copyright_path,
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
        f"Ubuntu copyright notices for source package {source_package}",
        "=" * 72,
        "",
        "The following sections reproduce the installed Debian/Ubuntu copyright",
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


def generate_native_notices(
    bundle_dir: Path,
    collect_toc: Path,
) -> tuple[int, int, int]:
    if not bundle_dir.is_dir():
        raise RuntimeError(f"Bundle directory does not exist: {bundle_dir}")

    binaries = read_collected_system_binaries(collect_toc)
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
        owner = _owning_package(binary.source_path)
        if owner not in metadata_cache:
            metadata_cache[owner] = _package_metadata(owner)
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
        source = Path("/usr/share/common-licenses") / name
        if not source.is_file():
            raise RuntimeError(f"Referenced Ubuntu common license is missing: {source}")
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
            "Generate the manifest and bundled Ubuntu notices for system ELF "
            "files collected by PyInstaller."
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
