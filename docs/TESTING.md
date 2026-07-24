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

The equivalent commands on Linux are:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r astro_viewer/requirements.txt
.venv/bin/python -m pip install -r requirements-dev.txt
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
4. Third-party license archive validation.
5. Offline MPC observatory snapshot validation.
6. Optional `pip-audit`.
7. Exactly one complete pytest pass, with or without runtime-code coverage.
8. Backend smoke test.
9. Normal-mode QML smoke test.
10. Red Night Vision QML smoke test.

The committed third-party archive records the exact Windows release
environment. On Windows the gate compares it byte-for-byte with the installed
dependency closure. On Linux and other development hosts the same generator
must resolve every installed runtime license, but it does not compare that
platform-specific closure with the Windows archive.

Backend and QML smoke tests receive a fresh `NIGHTSCOPE_RUNTIME_DIR` and delete
it after the subprocess exits. This developer/test-only override keeps the
database, preferences, caches, and logs separate from the checkout and from
personal application data. A fresh runtime has automatic location detection
disabled, so these smoke tests do not make location-provider requests.

Run the Red Night Vision scene directly in an isolated runtime:

```powershell
$env:NIGHTSCOPE_RUNTIME_DIR = Join-Path $env:TEMP "nightscope-red-smoke"
.\.venv\Scripts\python.exe -m astro_viewer.main --qml-smoke-test --red-night-vision
Remove-Item Env:NIGHTSCOPE_RUNTIME_DIR
```

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

Validate the packaged MPC observatory snapshot without accessing the network:

```powershell
.\.venv\Scripts\python.exe astro_viewer\tools\update_mpc_observatories.py --check
.\.venv\Scripts\python.exe -m pytest -q astro_viewer\tests\test_mpc_observatories.py
```

Run `pyside6-qmllint` over every file below `astro_viewer/app/ui`. QML lint
currently reports non-fatal `unqualified access` diagnostics for context
properties and nested component access. Treat a non-zero exit as a failure;
track the existing warnings as technical debt rather than silently declaring a
zero-warning baseline.

## Measured 1.41.0 Ubuntu Source And Portable Bundle Gate

Measured on Ubuntu 26.04 LTS with Python 3.14.4, PySide/Qt 6.11.1 and
Ruff 0.16.0 and PyInstaller 6.21.0 on 2026-07-24 after completing the first
native Linux source and frozen-bundle runs:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --fast` | Passed |
| `pip check`, Ruff, `compileall`, installed license closure | Passed |
| Offline MPC snapshot check | 2,683 fixed terrestrial observatories passed |
| `pytest -q -n 4 astro_viewer/tests` | 919 passed, 1 skipped, 642 warnings, 10 subtests passed in 109.09 s |
| Backend, normal QML, and red QML smoke tests | Passed without teardown binding errors |
| Native Qt platform probes | Wayland selected by default; explicit XCB fallback loaded |
| Controlled real GUI run | Wayland startup and clean automatic shutdown passed |
| Linux desktop services | User D-Bus active; GeoClue 2 source visible; Secret Service backend priority 5 |
| `./packaging/build_linux.sh` | Passed; platform-aware Qt, legal-file, data and runtime-state audit passed |
| Frozen application smoke | Backend, Wayland normal/red QML and XCB normal QML passed |
| Frozen bundle inventory | Version 1.41.0; 5,306 files; 548 MiB |
| Frozen credential modules | Secret Service, SecretStorage and jeepney present; Windows keyring backend absent |
| Linux Python license archive | 63 installed distributions covered, including SecretStorage and jeepney |
| Deterministic release-candidate archive | `NightScope-v1.41.0-ubuntu-26.04-x64.tar.gz`; 263,574,875 bytes (252 MiB) |
| Archive SHA-256 | `134c79f6b4dfd5101bce231477102e56beadf6b88cd5afcf88b568d81d478d60` |
| Clean archive extraction | Checksum, bundle audit, backend smoke, Wayland normal/red QML and XCB normal QML passed |

This was a fast source/bundle gate without coverage or `pip-audit`; the frozen
directory is a local packaging candidate, not a published Linux release. Its
generated archive covers the installed Python dependency closure. A public
artifact still requires an inventory and notices for copied system ELF
libraries plus validation on the oldest supported glibc baseline. The committed
third-party archive remains the exact Windows release artifact and is still
compared byte-for-byte on Windows.

## Measured 1.40.1 Recommendation Boundary Gate

Measured on Windows with Python 3.14.5 on 2026-07-23 after correcting Skyfield
altitude parsing and removing display-score eligibility from the pre-NSOM
deep-sky pool:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed |
| `pip check`, Ruff, `compileall`, third-party archive | Passed |
| Offline MPC snapshot check | 2,683 fixed terrestrial observatories passed |
| Final `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 917 passed, 642 warnings, 10 subtests passed in 119.05 s |
| Runtime coverage | 84% across 16,032 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Backend, normal QML, and red QML smoke tests | Passed |
| Equipment quality matrix | 375 checks across 15 profiles and 25 targets; 0 invariant violations |
| Real Skyfield candidate checks | Nairobi 195/195, Rome 148/148, Sydney 165/165 under active urban display context |

The deterministic tests connect the Skyfield degree-label producer to
`TargetObservationTraits`, preserve low display-score targets in conditioned
read models and verify that raw targets remain the NSOM inputs. The three
fixed-time location probes parsed every returned maximum altitude.

One intermediate parallel rerun lost an `xdist` worker to a native Qt access
violation while starting an Update Manager background check. The affected file
then passed `22/22` in serial execution and the following complete four-worker
run passed `917/917`; no assertion failure was reproduced.

## Measured 1.40.0 Linux Secret Service Gate

Measured on Windows with Python 3.14.5 on 2026-07-23 after introducing the
explicit Linux credential backend:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed |
| `pip check`, Ruff, `compileall`, third-party archive | Passed |
| Offline MPC snapshot check | 2,683 fixed terrestrial observatories passed |
| Final `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 912 passed, 642 warnings, 10 subtests passed in 171.70 s |
| Runtime coverage | 84% across 16,036 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Backend, normal QML, and red QML smoke tests | Passed |
| Credential backend, Earthdata, and OpenAQ focused tests | 25 passed |
| Runtime/tooling/release extended focused tests | 84 passed, 493 known warnings |
| Windows environment | `keyring 25.7.0`, `WinVaultKeyring` selected |
| Linux conditional dependencies | `SecretStorage>=3.2` and `jeepney>=0.4.2` declared by installed `keyring` metadata |

Deterministic tests prove that Windows retains the existing keyring dispatcher,
Linux selects Secret Service directly, and Linux reports secure storage as
unavailable when Secret Service cannot initialize or is not a recommended
backend. The interactive save/read/delete test still requires a Linux desktop
session with D-Bus and an unlocked Secret Service collection.

## Measured 1.39.0 Linux XDG Runtime Gate

Measured on Windows with Python 3.14.5 on 2026-07-23 after separating Linux
data, configuration, cache and state directories:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed |
| `pip check`, Ruff, `compileall`, third-party archive | Passed |
| Offline MPC snapshot check | 2,683 fixed terrestrial observatories passed |
| Final `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 907 passed, 642 warnings, 10 subtests passed in 114.00 s |
| Runtime coverage | 84% across 16,024 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Backend, normal QML, and red QML smoke tests | Passed with co-located disposable runtime override |
| Focused runtime/platform/database/location/release suite | 150 passed |

Deterministic resolver tests cover Linux XDG defaults, absolute environment
overrides, invalid relative values, portable source/frozen layouts on other
platforms and the all-path test override. The Windows-host integration asserts
that source execution still resolves every category to the repository root.
Migration tests verify database, backup, preference and cache placement and
prove that existing XDG preferences are not overwritten. A real installed
Linux package remains a later packaging gate.

## Measured 1.38.0 Startup Update Check Gate

Measured on Windows with Python 3.14.5 on 2026-07-23 after adding the
non-blocking stable-release notification:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed |
| `pip check`, Ruff, `compileall`, third-party archive | Passed |
| Offline MPC snapshot check | 2,683 fixed terrestrial observatories passed |
| Final `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 889 passed, 642 warnings, 10 subtests passed in 136.16 s |
| Runtime coverage | 84% across 15,965 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Translation catalogues | IT, EN, and ES: 1,697 finished, 0 unfinished each |
| Backend, normal QML, and red QML smoke tests | Passed in disposable runtimes |
| Live GitHub release probe | `1.36.0` found `v1.37.0`; `1.38.0` found no newer release |
| Minimum viewport popup | Spanish Red Night Vision dialog opened centered at 560 x 204 within 1040 x 700 |

The update request is not run by backend or QML smoke tests. Unit coverage uses
mocked GitHub responses for version ordering, stable-release filtering, URL
validation, ignored-version persistence and the one-check-per-session guard.
The separate live probe confirms the public API contract without making the
deterministic suite depend on network availability.

## Measured 1.37.0 Red Night Vision Gate

Measured on Windows with Python 3.14.5 on 2026-07-22 after adding the
persistent Red Night Vision appearance mode:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed again after the distribution follow-up |
| `pip check`, Ruff, `compileall`, third-party archive | Passed |
| Offline MPC snapshot check | 2,683 fixed terrestrial observatories passed |
| Final `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 867 passed, 642 warnings, 10 subtests passed in 133.26 s |
| Runtime coverage | 84% across 15,823 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Translation catalogues | IT, EN, and ES: 1,692 finished, 0 unfinished each |
| Backend, normal QML, and red QML smoke tests | Passed in disposable runtimes |
| `qmllint` across `astro_viewer/app/ui` | Exit code 0; known static warnings only |
| Red visual matrix | 13 views at 1240 x 820: max G=74, max B=61, 0 pixels above G>90 or B>80 |
| Native Windows icon render | SVG icons remained visible through `MultiEffect`; max G=74 and max B=61 |
| Raster photo suppression | No JPG, PNG, WebP, or JPEG source loaded; selected-object detail included |
| Minimum viewport | Normal and red Spanish UI passed at 1040 x 700; selector labels fit |

The normal render retained the previous full-color range (`G=247`, `B=255`).
The visual matrix covered every component selected by `main.qml`, while static
regressions cover modal-only equipment controls and prevent pages from using
native `CheckBox` or `TextField` rendering. The manual was intentionally not
changed for this source release. Icon visibility is checked with the native
Windows graphics backend because Qt's `offscreen` backend does not render
`MultiEffect`; the offscreen matrix remains the deterministic color and layout
gate for non-shader content.

The first packaged-distribution trial exposed two additional UI cases. A QML
runtime check with the long Orion observatory label returned
`truncated=False`; the Moon source link emitted the red inline style
`color:#d94a3d`. Coordinates now remain in the secondary location context, and
the rich-text anchor includes the reactive theme token instead of relying only
on Qt's cached `linkColor` rendering.

## Measured 1.36.0 Unified Location Search Gate

Measured on Windows with Python 3.14.5 on 2026-07-22 after combining the
offline GeoNames city search with the fixed terrestrial MPC observatory
snapshot:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed in 262.9 s |
| `pip check`, Ruff, `compileall`, third-party archive | Passed |
| Offline MPC snapshot check | 2,683 fixed terrestrial observatories passed |
| Final `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 853 passed, 642 warnings, 10 subtests passed in 135.81 s |
| Runtime coverage | 84% across 15,764 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Translation catalogues | IT, EN, and ES: 1,691 finished, 0 unfinished each |
| Backend and QML smoke tests | Passed in disposable runtimes |

The SQLite schema is now version 17. Existing databases are migrated in place;
only the derived `MpcObservatory` catalogue is imported or refreshed. No
distribution or repository runtime database was regenerated, and the public
Windows release remains `1.34.2`. The standard gate completed before the final
ranking-limit regression was added; the complete coverage suite was rerun after
that addition and produced the final count above.

## Measured 1.35.1 Linux System Location Gate

Measured on Windows with Python 3.14.5 on 2026-07-22 after adding the Linux
GeoClue 2 provider while preserving the existing Windows provider order:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed in 206.6 s |
| `pip check`, Ruff, `compileall`, third-party archive | Passed |
| `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 841 passed, 613 warnings, 10 subtests passed in 110.37 s |
| Runtime coverage | 84% across 15,615 statements; platform module 100% |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Focused platform, location, translation, and tooling regressions | 87 passed |
| Translation catalogues | IT, EN, and ES: 1,684 finished, 0 unfinished each |
| Backend and QML smoke tests | Passed in disposable runtimes |

No distribution or repository database was regenerated. The Windows system
location path keeps the precise/coarse provider order used before `1.35.1`.
GeoClue behavior is covered with deterministic Qt sources; a real D-Bus test
still requires a Linux desktop with GeoClue installed and authorized.

## Measured 1.35.0 Platform Capability Gate

Measured on Windows with Python 3.14.5 on 2026-07-22 after introducing the
platform-capability boundary without changing current Windows behavior:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed in 245.7 s |
| `pip check`, Ruff, `compileall`, third-party archive | Passed |
| `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 832 passed, 613 warnings, 10 subtests passed in 141.89 s |
| Runtime coverage | 84% across 15,465 statements; platform module 100% |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Focused platform, tooling, and location regressions | 58 passed |
| Direct `astro_viewer/main.py --help` startup | Passed |
| Backend and QML smoke tests | Passed in disposable runtimes |

No distribution or repository database was regenerated. Windows remains the
only platform that declares a supported system-location provider in this
step; location execution, preferences, runtime storage, credentials, scoring,
recommendations, and visible QML behavior are unchanged.

## Measured 1.34.3 Italian And English Editorial Gate

Measured on Windows with Python 3.14.5 on 2026-07-22 after the full Italian and
English structured-content, Qt catalogue, and manual review:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed in 163.5 s |
| `pip check`, Ruff, `compileall`, third-party archive | Passed |
| `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 822 passed, 613 warnings, 10 subtests passed in 107.86 s |
| Runtime coverage | 84% across 15,413 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Focused localization and developer-tooling regressions | 35 passed |
| Translation catalogues | IT, EN, and ES: 1,679 finished, 0 unfinished each |
| LanguageTool changed-content audit | No unresolved actionable findings |
| LanguageTool full English audit | 2,534 entries; remaining findings manually classified as punctuation style, fragments, or proper-name false positives |
| Backend and QML smoke tests | Passed in disposable runtimes |

No distribution or repository database was regenerated. The C53 seed
classification changed from elliptical to lenticular; an exact-match bootstrap
correction updates the obsolete built-in row in existing databases while
preserving customized text. SQLite schema, scoring, recommendation policy, and
UI behavior are unchanged.

## Measured 1.34.2 Responsive Layout Follow-up

Measured on Windows with Python 3.14.5 on 2026-07-22 after correcting the
Earthdata credential-grid threshold and the wide ISS event-details layout:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed in 335.3 s |
| `pip check`, Ruff, `compileall`, and third-party archive | Passed |
| `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 821 passed, 613 warnings, 10 subtests passed in 217.12 s |
| Runtime coverage | 84% across 15,410 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Focused responsive-layout regressions | 3 passed |
| Backend and QML smoke tests | Passed in disposable runtimes |
| `qmllint` on the two changed QML files | Passed; known static warnings only |
| ISS event detail offscreen render | Passed at 1600 x 1100 |

## Measured 1.34.2 Earthdata Authorization Gate

Measured on Windows with Python 3.14.5 on 2026-07-22 after distinguishing
invalid Earthdata credentials from missing LAADS OPeNDAP authorization:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed in 250.6 s |
| `pip check`, Ruff, `compileall`, and third-party archive | Passed |
| `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 821 passed, 613 warnings, 10 subtests passed in 170.93 s |
| Runtime coverage | 84% across 15,410 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Focused Earthdata and Data Providers regressions | 13 passed |
| Backend and QML smoke tests | Passed in disposable runtimes |

The live diagnostic used exactly one invalid-password attempt and one valid
credential attempt without LAADS application authorization. No account
credentials, cookies, tokens, or response query parameters were retained.

## Measured 1.34.1 Deep Review And Provider Guidance Gate

Measured on Windows with Python 3.14.5 on 2026-07-21 after the provider,
location-cache, numeric-input and startup hardening follow-up and the localized
provider-account guidance:

| Check | Result |
| --- | --- |
| `python tools/run_checks.py --security` | Passed in 218.6 s |
| `pip check`, Ruff, `compileall`, and third-party archive | Passed |
| `pytest -q -n 4 astro_viewer/tests` with runtime coverage | 817 passed, 613 warnings, 10 subtests passed in 120.46 s |
| Runtime coverage | 84% across 15,403 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Focused provider-guidance verification | 23 passed |
| Translation catalogues | IT, EN, and ES: 1,679 finished, 0 unfinished each |
| Separate Italian, English, and Spanish QML smoke runs | Passed in disposable runtimes |
| Data Providers visual rendering | IT, EN, and ES passed at 1,400 and 774 px page widths |
| `qmllint` | 31 files, 0 failures, 760 known static warnings |
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
