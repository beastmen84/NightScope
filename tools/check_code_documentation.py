"""Enforce repository-wide responsibility headers for hand-written source files."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterable
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOTS = ("astro_viewer", "tools", "packaging")
QML_ROOT = "astro_viewer/app/ui"
OPERATIONAL_EXACT_PATHS = (
    "astro_viewer/data/schema.sql",
    "astro_viewer/requirements.txt",
    "manuale.html",
    "requirements-dev.txt",
)
OPERATIONAL_PATTERNS = (
    ".github/**/*.yml",
    ".github/**/*.yaml",
    "*.ini",
    "*.toml",
    "packaging/**/*.ps1",
    "packaging/**/*.sh",
    "packaging/**/*.spec",
    "packaging/**/Dockerfile*",
    "tools/**/*.ps1",
    "tools/**/*.sh",
)
HEADER_SCAN_LINES = 8
_HEADER_PATTERN = re.compile(r"\b(?P<label>Purpose|Contract):\s*\S")


def python_sources(repo_root: Path) -> tuple[Path, ...]:
    """Return every hand-written Python module owned by the source repository."""

    paths = {
        path
        for relative_root in PYTHON_ROOTS
        for path in (repo_root / relative_root).rglob("*.py")
        if path.is_file()
    }
    return tuple(sorted(paths))


def qml_sources(repo_root: Path) -> tuple[Path, ...]:
    """Return every QML page and reusable component."""

    return tuple(sorted(path for path in (repo_root / QML_ROOT).rglob("*.qml") if path.is_file()))


def operational_sources(repo_root: Path) -> tuple[Path, ...]:
    """Return hand-written automation, packaging, configuration, schema, and manual files."""

    paths = {
        repo_root / relative_path
        for relative_path in OPERATIONAL_EXACT_PATHS
        if (repo_root / relative_path).is_file()
    }
    for pattern in OPERATIONAL_PATTERNS:
        paths.update(path for path in repo_root.glob(pattern) if path.is_file())
    return tuple(sorted(paths))


def python_documentation_error(path: Path) -> str | None:
    """Return an error when a Python module is invalid or lacks its responsibility docstring."""

    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as error:
        return f"cannot parse Python source: {error}"
    if not (ast.get_docstring(tree, clean=False) or "").strip():
        return "missing module responsibility docstring"
    return None


def qml_documentation_error(path: Path) -> str | None:
    """Return an error unless the first two QML lines declare purpose and contract."""

    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as error:
        return f"cannot read QML source: {error}"
    expected = ("// Purpose:", "// Contract:")
    for index, prefix in enumerate(expected):
        if len(lines) <= index or not lines[index].startswith(prefix) or not lines[index][len(prefix) :].strip():
            return f"line {index + 1} must start with a non-empty {prefix} header"
    return None


def operational_documentation_error(path: Path) -> str | None:
    """Return an error unless an operational source declares purpose and contract near its start."""

    try:
        header = path.read_text(encoding="utf-8-sig").splitlines()[:HEADER_SCAN_LINES]
    except (OSError, UnicodeError) as error:
        return f"cannot read operational source: {error}"
    labels = {match.group("label") for line in header for match in _HEADER_PATTERN.finditer(line)}
    missing = [label for label in ("Purpose", "Contract") if label not in labels]
    if missing:
        return f"missing non-empty {' and '.join(missing)} header in first {HEADER_SCAN_LINES} lines"
    return None


def _family_errors(
    repo_root: Path,
    paths: Iterable[Path],
    validator,
) -> list[str]:
    errors = []
    for path in paths:
        error = validator(path)
        if error:
            errors.append(f"{path.relative_to(repo_root).as_posix()}: {error}")
    return errors


def documentation_errors(repo_root: Path) -> list[str]:
    """Return deterministic documentation failures for all governed source families."""

    return [
        *_family_errors(repo_root, python_sources(repo_root), python_documentation_error),
        *_family_errors(repo_root, qml_sources(repo_root), qml_documentation_error),
        *_family_errors(repo_root, operational_sources(repo_root), operational_documentation_error),
    ]


def documentation_counts(repo_root: Path) -> dict[str, int]:
    """Return the current audited inventory by documentation family."""

    return {
        "Python": len(python_sources(repo_root)),
        "QML": len(qml_sources(repo_root)),
        "operational": len(operational_sources(repo_root)),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the optional repository root used by tests and local diagnostics."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Validate the inventory and print an actionable, path-stable report."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    repo_root = args.root.resolve()
    errors = documentation_errors(repo_root)
    if errors:
        print("Code documentation gate failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    counts = documentation_counts(repo_root)
    summary = ", ".join(f"{count} {family}" for family, count in counts.items())
    print(f"Code documentation gate passed: {summary} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
