# NightScope Testing Workflow

This document contains the current validation contract. Historical measurements
through source `1.45.6` are preserved in
`docs/archive/TESTING_HISTORY_THROUGH_1.45.6.md`; release approval remains in
`docs/RELEASE_CHECKLIST.md`.

## Environment

Create a virtual environment and install runtime and developer dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r astro_viewer\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

On Linux, replace the executable with `.venv/bin/python`. The standard runner
always uses four pytest workers. Do not substitute `-n auto`: PySide and
Skyfield make each worker comparatively expensive, especially on high-core
Windows hosts.

## Standard Source Gates

Fast complete gate without coverage:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --fast
```

Fast gate plus installed-environment vulnerability audit:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --fast --security
```

Full source/release gate with coverage and dependency audit:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --security
```

The runner performs these checks in order:

1. `pip check`.
2. Ruff over application, tests, and developer tools.
3. Production import-cycle and protected-layer validation.
4. Bandit comparison with the reviewed source-context baseline.
5. Quiet bytecode compilation.
6. Third-party license archive validation.
7. Offline MPC observatory snapshot validation.
8. Offline OpenNGC snapshot and derived-seed validation.
9. Optional `pip-audit`.
10. One complete pytest pass, with or without runtime-code coverage.
11. Backend smoke test in a disposable runtime.
12. Normal-mode QML smoke test in a disposable runtime.
13. Red Night Vision QML smoke test in a disposable runtime.

The source gate does not build, update, or approve `dist`.

## Architecture And Security Policies

`tools/check_import_cycles.py` rejects strongly connected components and
self-imports in production Python modules. It also prevents models, database,
astronomy, and service modules from importing either the Qt view-model layer or
the application composition layer. These rules protect the outer dependency
boundaries without pretending that the current codebase is a pure clean-
architecture implementation.

`tools/check_bandit.py` scans the application, entry point, and developer tools.
The baseline records rule, severity, confidence, portable path, triggering
source line, and a hash of Bandit's code context after line numbers are removed.
A new finding, removed finding, changed context, or reclassification fails.
High-severity findings are never accepted.

Inspect a proposed baseline without writing it:

```powershell
.\.venv\Scripts\python.exe tools\check_bandit.py --render-baseline
```

Use `--write-baseline` only after reviewing every difference and its rationale.

Pytest promotes unexpected warnings to errors. `pytest.ini` contains only two
repository-wide exceptions: the exact Skyfield `dtype` and `shape` deprecation
signatures caused by NumPy 2.5, constrained by message, category, and module.
Remove those filters when the upstream behavior is fixed and rerun the complete
astronomy suite.

## Continuous Integration

`.github/workflows/source-validation.yml` reuses the local fast gate on:

- Windows with Python 3.14;
- Linux with Python 3.12.

A separate Linux/Python 3.14 job runs `pip check` and `pip-audit` over the
installed dependency closure. The workflow has read-only repository permission,
uses the official checkout and Python setup actions, caches pip downloads, and
does not run packaging commands.

Local validation proves the workflow contract and commands; it does not prove a
remote GitHub run. Record remote results separately when CI has actually run.

## Focused Development Checks

Run the smallest relevant test file while changing one service:

```powershell
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_location_service.py
```

Run the complete deterministic suite directly:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -n 4 astro_viewer\tests
```

Use a serial run only to investigate ordering, process, or worker behavior:

```powershell
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests
```

## Specialized Data And UI Checks

Validate and compile every language pack:

```powershell
.\tools\update_translations.ps1 -CompileOnly
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_translations.py
```

Validate repository images:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\sync_catalogue_images.py --check
.\.venv\Scripts\python.exe astro_viewer\tools\sync_solar_system_images.py --check
```

Validate fixed MPC and OpenNGC inputs without network access:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\update_mpc_observatories.py --check
.\.venv\Scripts\python.exe astro_viewer\tools\update_ngc_catalogue.py --check
```

Run `pyside6-qmllint` over every QML file below `astro_viewer/app/ui`. Existing
`unqualified access` diagnostics for context properties and nested components
are non-fatal technical debt, but any non-zero tool exit remains a failure.

## Latest Measured Gate

The `1.45.7` fast source gate passed on Windows/Python 3.14.5 with 1,168 tests
and 10 subtests in 273.47 seconds, no unexpected warning summary, an acyclic
production graph, zero protected-layer violations, an unchanged Bandit
baseline (0 high, 37 medium, 14 low), clean dependency/license/MPC/OpenNGC
checks, and successful backend, normal QML, and Red Night Vision QML smoke
tests. A direct installed-environment `pip-audit` immediately afterward found
no known vulnerabilities.

No remote CI result, distribution build, source tag, checksum, or release is
implied by that local source measurement.

## Change Policy

For a narrow service change, run Ruff, the architecture/security tools, and the
relevant focused tests first. For shared controller, persistence, astronomy,
provider, QML, localization, or packaging changes, run the complete source gate
before commit. A release artifact additionally requires every manual, provider,
upgrade, legal, visual, and artifact check in `docs/RELEASE_CHECKLIST.md`.
