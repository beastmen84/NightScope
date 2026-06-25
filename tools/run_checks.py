from __future__ import annotations

import argparse
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Check:
    name: str
    args: tuple[str, ...]


def _checks(*, include_coverage: bool) -> list[Check]:
    checks = [
        Check("ruff", ("-m", "ruff", "check", "astro_viewer")),
        Check("pytest", ("-m", "pytest", "astro_viewer/tests", "-q")),
    ]
    if include_coverage:
        checks.append(
            Check(
                "pytest-cov",
                (
                    "-m",
                    "pytest",
                    "astro_viewer/tests",
                    "-q",
                    "--cov=astro_viewer",
                    "--cov-report=term-missing",
                ),
            )
        )
    checks.extend(
        [
            Check("smoke-test", ("-m", "astro_viewer.main", "--smoke-test")),
            Check("qml-smoke-test", ("-m", "astro_viewer.main", "--qml-smoke-test")),
            Check("compileall", ("-m", "compileall", "astro_viewer")),
        ]
    )
    return checks


def _run_check(check: Check) -> int:
    command = (sys.executable, *check.args)
    print(f"\n=== {check.name} ===", flush=True)
    print(" ".join(command), flush=True)
    start = time.perf_counter()
    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    elapsed = time.perf_counter() - start
    print(f"--- {check.name} finished in {elapsed:.1f}s with exit code {completed.returncode} ---", flush=True)
    return completed.returncode


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run NightScope standard validation checks. Default mode is full validation "
            "including pytest coverage. Use --fast to skip coverage."
        )
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--fast",
        action="store_true",
        help="Run ruff, pytest, smoke-test, qml-smoke-test and compileall; skip pytest-cov.",
    )
    mode.add_argument(
        "--coverage",
        action="store_true",
        help="Run full validation including pytest-cov. This is the default.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    include_coverage = not args.fast
    for check in _checks(include_coverage=include_coverage):
        return_code = _run_check(check)
        if return_code != 0:
            print(f"\nValidation stopped at failed check: {check.name}", flush=True)
            return return_code
    print("\nAll NightScope validation checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
