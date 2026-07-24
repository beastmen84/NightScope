from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import sys
import sysconfig
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_REQUIREMENTS = PROJECT_ROOT / "astro_viewer" / "requirements.txt"
OUTPUT_PATH = PROJECT_ROOT / "THIRD_PARTY_LICENSES.txt"
COMMON_LICENSE_DIR = PROJECT_ROOT / "legal" / "licenses"

BUILD_COMPONENTS = ("PyInstaller",)
EXCLUDED_RUNTIME_ROOTS = {canonicalize_name("PyInstaller")}
QT_COMPONENTS = {
    canonicalize_name(name)
    for name in (
        "PySide6",
        "PySide6_Addons",
        "PySide6_Essentials",
        "shiboken6",
    )
}

LICENSE_OVERRIDES = {
    canonicalize_name("colorama"): "BSD-3-Clause",
    canonicalize_name("flatbuffers"): "Apache-2.0",
    canonicalize_name("h3"): "Apache-2.0",
    canonicalize_name("jaraco.classes"): "MIT",
    canonicalize_name("pandas"): "BSD-3-Clause",
    canonicalize_name("pqdm"): "MIT",
    canonicalize_name("pyerfa"): "BSD-3-Clause",
    canonicalize_name("python-dateutil"): "Apache-2.0 OR BSD-3-Clause",
    canonicalize_name("s3fs"): "BSD-3-Clause",
    canonicalize_name("timezonefinder"): "MIT; bundled timezone data: ODbL-1.0",
}

COMMON_LICENSE_COVERAGE = {
    canonicalize_name("flatbuffers"): ("Apache-2.0.txt",),
    **{
        name: ("LGPL-3.0.txt", "GPL-3.0.txt")
        for name in QT_COMPONENTS
    },
}


@dataclass(frozen=True)
class Component:
    name: str
    version: str
    declared_license: str
    distribution: importlib.metadata.Distribution

    @property
    def canonical_name(self) -> str:
        return canonicalize_name(self.name)


def _runtime_roots() -> list[str]:
    roots: list[str] = []
    for raw_line in RUNTIME_REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        requirement = Requirement(line)
        if canonicalize_name(requirement.name) not in EXCLUDED_RUNTIME_ROOTS:
            roots.append(requirement.name)
    return roots


def _declared_license(distribution: importlib.metadata.Distribution) -> str:
    canonical_name = canonicalize_name(distribution.metadata["Name"])
    if canonical_name in LICENSE_OVERRIDES:
        return LICENSE_OVERRIDES[canonical_name]

    expression = distribution.metadata.get("License-Expression")
    if expression:
        return " ".join(expression.split())

    legacy = distribution.metadata.get("License", "")
    normalized = " ".join(legacy.split())
    if normalized and len(normalized) <= 160:
        return normalized
    return "See included component notice"


def _resolve_components() -> list[Component]:
    queue = _runtime_roots()
    seen: set[str] = set()
    components: list[Component] = []

    while queue:
        requested_name = queue.pop(0)
        requested_key = canonicalize_name(requested_name)
        if requested_key in seen:
            continue

        try:
            distribution = importlib.metadata.distribution(requested_name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise RuntimeError(
                f"Required distribution is not installed: {requested_name}"
            ) from exc

        name = distribution.metadata["Name"]
        canonical_name = canonicalize_name(name)
        if canonical_name in seen:
            continue
        seen.add(canonical_name)
        components.append(
            Component(
                name=name,
                version=distribution.version,
                declared_license=_declared_license(distribution),
                distribution=distribution,
            )
        )

        for requirement_text in distribution.requires or ():
            requirement = Requirement(requirement_text)
            if requirement.marker and not requirement.marker.evaluate({"extra": ""}):
                continue
            queue.append(requirement.name)

    for requested_name in BUILD_COMPONENTS:
        distribution = importlib.metadata.distribution(requested_name)
        canonical_name = canonicalize_name(distribution.metadata["Name"])
        if canonical_name in seen:
            continue
        seen.add(canonical_name)
        components.append(
            Component(
                name=distribution.metadata["Name"],
                version=distribution.version,
                declared_license=_declared_license(distribution),
                distribution=distribution,
            )
        )

    return sorted(components, key=lambda component: component.canonical_name)


def _is_notice_path(path: importlib.metadata.PackagePath) -> bool:
    pure_path = PurePosixPath(str(path).replace("\\", "/"))
    filename = pure_path.name.lower()
    if filename == "licenseref-qt-commercial.txt":
        return False
    if filename in {"data_license", "notice"}:
        return True
    if filename.startswith(("license", "licence", "copying", "notice")):
        return True
    return "licenses" in {part.lower() for part in pure_path.parts}


def _component_notices(component: Component) -> list[tuple[list[str], str]]:
    notices_by_hash: dict[str, tuple[list[str], str]] = {}
    for package_path in component.distribution.files or ():
        if not _is_notice_path(package_path):
            continue
        source_path = Path(component.distribution.locate_file(package_path)).resolve()
        if not source_path.is_file():
            continue
        text = source_path.read_text(encoding="utf-8", errors="replace")
        text = text.lstrip("\ufeff").rstrip()
        if not text:
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        relative_label = str(package_path).replace("\\", "/")
        if digest in notices_by_hash:
            notices_by_hash[digest][0].append(relative_label)
        else:
            notices_by_hash[digest] = ([relative_label], text)
    return sorted(notices_by_hash.values(), key=lambda item: item[0][0].lower())


def _common_license_text(filename: str) -> str:
    path = COMMON_LICENSE_DIR / filename
    if not path.is_file():
        raise RuntimeError(f"Missing canonical license text: {path}")
    return path.read_text(encoding="utf-8").lstrip("\ufeff").rstrip()


def _python_license_candidates() -> tuple[Path, ...]:
    candidates = (
        Path(sys.base_prefix) / "LICENSE.txt",
        Path(sys.exec_prefix) / "LICENSE.txt",
        Path(sysconfig.get_path("stdlib")) / "LICENSE.txt",
    )
    return tuple(dict.fromkeys(candidates))


def _python_license() -> str:
    candidates = _python_license_candidates()
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace").rstrip()
    checked_paths = ", ".join(str(path) for path in candidates)
    raise RuntimeError(f"Python license file not found; checked: {checked_paths}")


def render_archive() -> str:
    components = _resolve_components()
    lines = [
        "NightScope Third-Party License Archive",
        "======================================",
        "",
        "This file is generated by tools/generate_third_party_licenses.py.",
        "Do not edit it manually. It records the installed dependency closure",
        "used for the current Windows release candidate. Regenerate it in the",
        "clean release environment before publishing a new artifact.",
        "",
        f"Python runtime: {sys.version.split()[0]} (PSF-2.0)",
        f"Distributions covered: {len(components)}",
        "",
        "Component inventory",
        "-------------------",
    ]
    for component in components:
        lines.append(
            f"- {component.name} {component.version}: {component.declared_license}"
        )

    lines.extend(
        [
            "",
            "NightScope selects the LGPL-3.0-only option for PySide6, its Qt",
            "libraries, and shiboken6. GPL alternatives shown in package metadata",
            "are not the selected license for NightScope's own source code.",
            "",
            "Python runtime license",
            "----------------------",
            _python_license(),
        ]
    )

    uncovered: list[str] = []
    for component in components:
        lines.extend(
            [
                "",
                "=" * 79,
                f"Component: {component.name} {component.version}",
                f"Declared license: {component.declared_license}",
            ]
        )
        notices = _component_notices(component)
        if not notices and component.canonical_name not in COMMON_LICENSE_COVERAGE:
            uncovered.append(component.name)
            lines.append("No component-specific notice file was installed.")
        for source_labels, notice_text in notices:
            lines.extend(
                [
                    f"Notice source: {', '.join(source_labels)}",
                    "-" * 79,
                    notice_text,
                ]
            )

    if uncovered:
        raise RuntimeError(
            "No installed or canonical license text covers: " + ", ".join(uncovered)
        )

    common_files = sorted(
        {
            filename
            for component in components
            for filename in COMMON_LICENSE_COVERAGE.get(
                component.canonical_name, ()
            )
        }
    )
    for filename in common_files:
        lines.extend(
            [
                "",
                "=" * 79,
                f"Canonical license text: {filename}",
                "-" * 79,
                _common_license_text(filename),
            ]
        )

    archive = "\n".join(lines)
    return "\n".join(line.rstrip() for line in archive.split("\n")).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate or verify NightScope's third-party license archive."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when THIRD_PARTY_LICENSES.txt is missing or stale",
    )
    args = parser.parse_args()

    rendered = render_archive()
    if args.check:
        if not OUTPUT_PATH.is_file():
            print(f"Missing generated file: {OUTPUT_PATH}", file=sys.stderr)
            return 1
        current = OUTPUT_PATH.read_text(encoding="utf-8")
        if current != rendered:
            if sys.platform != "win32":
                print(
                    "Installed dependency licenses are complete. Exact archive "
                    "comparison is skipped outside Windows because the committed "
                    "archive records the Windows release environment."
                )
                return 0
            print(
                "THIRD_PARTY_LICENSES.txt is stale; regenerate it with "
                "tools/generate_third_party_licenses.py",
                file=sys.stderr,
            )
            return 1
        print("Third-party license archive is current.")
        return 0

    OUTPUT_PATH.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT_PATH}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
