# NightScope Testing Workflow

This document defines the current local validation workflow. Release history
belongs in `astro_viewer/CHANGELOG.md`; release approval belongs in
`docs/RELEASE_CHECKLIST.md`.

## Environment Setup

Create the virtual environment and install both dependency sets:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r astro_viewer\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

`pytest-xdist` is deliberately capped at four workers by the standard runner.
Using `-n auto` can create one heavy PySide/Skyfield worker per logical CPU and
cause excessive memory pressure on Windows development machines.

## Standard Gates

Fast complete gate, without coverage:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --fast
```

Fast gate plus an audit of the installed environment:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --fast --security
```

Release gate, with coverage and dependency audit:

```powershell
.\.venv\Scripts\python.exe tools\run_checks.py --security
```

The runner executes, in order:

1. `pip check`.
2. Ruff over application, tests, and developer tools.
3. Quiet bytecode compilation.
4. Optional `pip-audit`.
5. Exactly one complete pytest pass, with or without runtime-code coverage.
6. Backend smoke test.
7. QML smoke test.

Backend and QML smoke tests receive a fresh `NIGHTSCOPE_RUNTIME_DIR` and delete
it after the subprocess exits. This developer/test-only override keeps the
database, preferences, caches, and logs separate from the checkout and from
personal application data. A fresh runtime has automatic location detection
disabled, so these smoke tests do not make location-provider requests.

## Focused Checks

Run a focused test while developing:

```powershell
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_location_service.py
```

Run the complete deterministic suite directly:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -n 4 astro_viewer\tests
```

Use the serial suite only to investigate an order-dependent or worker-specific
failure:

```powershell
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests
```

Validate and compile every discovered language pack:

```powershell
.\tools\update_translations.ps1 -CompileOnly
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_translations.py
```

Run the repository image checks:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\sync_catalogue_images.py --check
.\.venv\Scripts\python.exe astro_viewer\tools\sync_solar_system_images.py --check
```

Run `pyside6-qmllint` over every file below `astro_viewer/app/ui`. QML lint
currently reports non-fatal `unqualified access` diagnostics for context
properties and nested component access. Treat a non-zero exit as a failure;
track the existing warnings as technical debt rather than silently declaring a
zero-warning baseline.

## Measured 1.33.0 Baseline

Measured on Windows with Python 3.14.5 on 2026-07-14 after the pre-release
audit:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --coverage --security` | Passed in 205.5 s |
| `pip check` | No broken requirements |
| Ruff application/tool scan | Passed |
| `compileall` application/tool scan | Passed |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Runtime coverage | 84% across 15,212 statements; tests and developer tools excluded |
| `pytest -q -n 4 astro_viewer/tests` | 785 passed, 613 warnings, 7 subtests passed in 112.92 s |
| Backend smoke, disposable runtime | Passed |
| Italian QML smoke, disposable runtime | Passed |
| English QML smoke, disposable runtime | Passed |
| Translation catalogues | IT and EN: 1,595 finished, 0 unfinished each |
| Translation regression tests | 15 passed |
| QML lint | 30 files, no non-zero exit |
| Deep-sky image check | 219 JPEG assets passed |
| Solar System image check | 9 JPEG assets passed |
| Bilingual manual | Desktop and 390 px mobile rendering checked; language switching passed |

The 613 pytest warnings come from Skyfield assigning deprecated NumPy `dtype`
or `shape` attributes. They are dependency-compatibility warnings, not failed
NightScope assertions. Keep them visible: a future dependency update must rerun
the astronomy, ISS, comet, Calendar, and release-scenario tests before the
warnings can be considered resolved.

Coverage is lowest at the process/UI entry point because backend and QML smoke
checks run in separate subprocesses after pytest. Core repositories, astronomy,
recommendation services, and provider policies are measured by the pytest
phase; the smoke checks independently verify application construction and QML
loading.

## Change Policy

For a narrow service change, run Ruff, compileall, and the relevant focused
tests first. For shared controller, persistence, astronomy, provider, QML,
localization, or packaging changes, run the complete gate before commit. For a
release artifact, also complete every manual, provider, upgrade, legal, and
artifact step in `docs/RELEASE_CHECKLIST.md`; automated tests alone do not
approve a release.
