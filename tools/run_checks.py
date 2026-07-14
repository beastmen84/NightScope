from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from tempfile import TemporaryDirectory
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Check:
    name: str
    args: tuple[str, ...]
    isolated_runtime: bool = False


def _checks(*, include_coverage: bool, include_security: bool) -> list[Check]:
    checks = [
        Check("pip-check", ("-m", "pip", "check")),
        Check("ruff", ("-m", "ruff", "check", "astro_viewer", "tools")),
        Check("compileall", ("-m", "compileall", "-q", "astro_viewer", "tools")),
    ]
    if include_security:
        checks.append(
            Check("pip-audit", ("-m", "pip_audit", "--progress-spinner", "off"))
        )
    pytest_args = [
        "-m",
        "pytest",
        "-q",
        "-n",
        "4",
        "astro_viewer/tests",
    ]
    if include_coverage:
        pytest_args.extend(
            (
                "--cov=astro_viewer.app",
                "--cov=astro_viewer.main",
                "--cov-report=term-missing",
            )
        )
    checks.append(
        Check("pytest-cov" if include_coverage else "pytest", tuple(pytest_args))
    )
    checks.extend(
        [
            Check(
                "smoke-test",
                ("-m", "astro_viewer.main", "--smoke-test"),
                isolated_runtime=True,
            ),
            Check(
                "qml-smoke-test",
                ("-m", "astro_viewer.main", "--qml-smoke-test"),
                isolated_runtime=True,
            ),
        ]
    )
    return checks


def _run_check(check: Check) -> int:
    command = (sys.executable, *check.args)
    print(f"\n=== {check.name} ===", flush=True)
    print(" ".join(command), flush=True)
    start = time.perf_counter()
    if check.isolated_runtime:
        with TemporaryDirectory(prefix=f"nightscope-{check.name}-") as temp_dir:
            environment = os.environ.copy()
            environment["NIGHTSCOPE_RUNTIME_DIR"] = temp_dir
            completed = subprocess.run(
                command,
                cwd=REPO_ROOT,
                env=environment,
                check=False,
            )
    else:
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
        help="Run the standard checks with four pytest workers; skip pytest-cov.",
    )
    mode.add_argument(
        "--coverage",
        action="store_true",
        help="Run full validation including pytest-cov. This is the default.",
    )
    parser.add_argument(
        "--security",
        action="store_true",
        help="Also audit the installed environment with pip-audit (requires network access).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    include_coverage = not args.fast
    for check in _checks(
        include_coverage=include_coverage,
        include_security=args.security,
    ):
        return_code = _run_check(check)
        if return_code != 0:
            print(f"\nValidation stopped at failed check: {check.name}", flush=True)
            return return_code
    print("\nAll NightScope validation checks passed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
