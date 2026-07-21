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

## Measured 1.34.1 Deep Review Hardening Gate

Measured on Windows with Python 3.14.5 on 2026-07-21 after the provider,
location-cache, numeric-input and startup hardening follow-up:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed in 246.5 s |
| `pip check`, Ruff, `compileall`, and third-party archive | Passed |
| `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 816 passed, 613 warnings, 10 subtests passed in 143.85 s |
| Runtime coverage | 84% across 15,403 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Focused post-fix verification | 62 passed |
| Translation catalogues | IT, EN, and ES: 1,670 finished, 0 unfinished each |
| Focused localization and developer-tooling tests | 34 passed |
| Separate Italian, English, and Spanish QML smoke runs | Passed in disposable runtimes |
| `qmllint` | 30 files, 0 failures, 760 known static warnings |
| Repository image checks | 219 deep-sky and 9 Solar System JPEG assets passed |
| Bandit application/tool scan | 0 high, 26 medium, 12 low; unchanged reviewed baseline |

No schema migration, seed-data change, distribution rebuild or scoring and
recommendation-policy change belongs to this hardening pass.

## Measured 1.34.0 Spanish Localization Gate

Measured on Windows with Python 3.14.5 on 2026-07-21 after the second complete
editorial review of the Spanish language pack and multilingual manual:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --fast` | Passed in 193.8 s |
| `pip check`, Ruff, `compileall`, and third-party archive | Passed |
| `pytest -q -n 4 astro_viewer/tests` | 795 passed, 613 warnings, 7 subtests passed in 119.31 s |
| Translation catalogues | IT, EN, and ES: 1,665 finished, 0 unfinished each |
| Focused localization and developer-tooling tests | 31 passed |
| Separate Italian, English, and Spanish QML smoke runs | Passed in disposable runtimes |
| Spanish structured content | 7 sections, 821 items, 2,038 translated fields |
| Spanish narrative review | 228 unique descriptions, notes, and curiosities; terminology and LanguageTool checks passed |
| Spanish manual | Chromium desktop and 390 px mobile rendering passed; no horizontal overflow; ES/EN/ES switching and anchors passed |

This source gate does not replace the page-by-page Spanish visual matrix or a
clean Windows `1.34.1` bundle audit. The published package remains `1.33.2`.

## Measured 1.33.2 Licensing And Bundle Gate

Measured on Windows with Python 3.14.5 on 2026-07-15 after adding the project
license, generated third-party archive, and restricted Qt packaging hooks:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed in 271.7 s |
| `pip check`, Ruff and `compileall` | Passed |
| Third-party license archive check | Current; 61 distributions covered |
| `pytest -q -n 4 astro_viewer/tests` | 791 passed, 613 warnings, 7 subtests passed in 153.85 s |
| Runtime coverage | 84% across 15,242 statements; tests and developer tools excluded |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Bandit application/tool scan | 0 high, 26 medium, 12 low; no change from the reviewed baseline |
| Backend and source QML smoke | Passed in disposable runtimes |
| Isolated PyInstaller bundle | 5,223 files, 469.8 MiB; Qt/legal audit and packaged QML smoke passed |

The isolated package was deleted after validation. The persistent Windows
distribution was subsequently rebuilt as `1.33.2`; its packaged `VERSION`,
manual revision, legal files, Qt module audit, backend smoke, and QML smoke are
correct. Running the executable in place created `nightscope.db`, its backup,
and logs as designed, so that directory is a validation copy rather than the
final release artifact. The bundle audit now rejects such runtime state. The
public archive must use a pristine copy and still complete the visual, provider,
and artifact-security gates.

The published `NightScope-v1.33.2-windows-x64.zip` was verified against its
local source archive and extracted to a disposable directory. It contains
`5,221` files (`434,071,829` uncompressed bytes), passes the
Qt/legal/runtime-state bundle audit, and contains no NightScope runtime database
or root log directory. GitHub and the local file report the same SHA-256 digest:
`33424e4e8317dee951230d795e2f0de936946910ede232ba478e893c73e02967`.
The release tag `v1.33.2` resolves to audited source commit
`9c17204f718223e83183367e9ccea078805b5a00`.

## Measured 1.33.1 Visual-Fix Gate

Measured on Windows with Python 3.14.5 on 2026-07-15 after resolving the
bilingual visual checklist:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed in 204.1 s |
| `pip check`, Ruff and `compileall` | Passed |
| `pytest -q -n 4 astro_viewer/tests` | 788 passed, 613 warnings, 7 subtests passed in 112.44 s |
| Runtime coverage | 84% across 15,242 statements; tests and developer tools excluded |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Bandit application/tool scan | 0 high, 26 medium, 12 low; no change from the reviewed baseline |
| Backend smoke, disposable runtime | Passed |
| QML smoke from the standard gate | Passed |
| Separate Italian and English QML smoke runs | Passed |
| Translation catalogues | IT and EN: 1,665 finished, 0 unfinished each |
| Translation regression tests | 15 passed |
| Focused localization, Equipment, Home and Calendar tests | 113 passed |
| QML lint | 30 files, exit 0; 760 known static warnings |
| Deep-sky image check | 219 JPEG assets passed |
| Solar System image check | 9 JPEG assets passed |

The public artifact gate must repeat these checks after rebuilding the Windows
distribution.

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
