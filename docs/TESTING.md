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

The `1.46.1` Windows/Python 3.14.5 baseline was validated with pip 26.2.1,
Ruff 0.16.5, coverage 7.16.0, PyInstaller 6.22.2,
`pyinstaller-hooks-contrib` 2026.7, PySide6/Qt/shiboken6 6.11.2, Skyfield 1.55,
Astropy 8.0.1, astropy-IERS-data `0.2026.8.31.0.57.9`, NumPy 2.5.2,
earthaccess 0.18.0, s3fs/fsspec 2026.7.0, aiobotocore 3.9.0, and botocore
1.43.56. The five Earthdata requirements are intentionally constrained and
must be upgraded as one resolver unit.

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
2. Ruff over application, tests, developer tools, and packaging Python modules.
3. Complete Python, QML, and operational-file documentation inventory.
4. Production import-cycle and protected-layer validation.
5. Bandit comparison with the reviewed source-context baseline.
6. Quiet bytecode compilation, including packaging Python modules.
7. Third-party license archive validation.
8. Offline MPC observatory snapshot validation.
9. Offline OpenNGC snapshot and derived-seed validation.
10. Network-free catalogue editorial baseline, translation, provenance, and
    accepted-batch validation.
11. Optional `pip-audit`.
12. One complete pytest pass, with or without runtime-code coverage.
13. Backend smoke test in a disposable runtime.
14. Normal-mode QML smoke test in a disposable runtime.
15. Red Night Vision QML smoke test in a disposable runtime.

The source gate does not build, update, or approve `dist`.

## Architecture And Security Policies

`tools/check_code_documentation.py` discovers governed Python and QML sources
recursively and validates the operational source families defined in
`docs/CODE_DOCUMENTATION_POLICY.md`. It enforces responsibility docstrings and
purpose/contract headers; review still owns their semantic accuracy.

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
The `dtype` exception remains reproducible with Skyfield 1.55 and NumPy 2.5.2.
Remove both filters only when the corresponding upstream behavior is fixed and
rerun the complete astronomy suite.

## Continuous Integration

`.github/workflows/source-validation.yml` reuses the local fast gate on:

- Windows with Python 3.14.5 and
  `packaging/windows-release-constraints.txt`;
- Linux with Python 3.12.

A separate Linux/Python 3.14 job runs `pip check` and `pip-audit` over the
latest resolvable dependency closure. Runtime requirements continue to express
supported ranges, while the Windows constraints file pins the 62 runtime/build
components recorded in `THIRD_PARTY_LICENSES.txt`. A tooling test enforces exact
name/version equality and requires the workflow's Windows Python patch to match
the archive. License collection excludes Python source, bytecode and cache
directories; arbitrary notice filenames are accepted only below the standard
`.dist-info/licenses` directory. The workflow has read-only repository
permission, uses the official checkout and Python setup actions, caches pip
downloads, and does not run packaging commands.

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
.\.venv\Scripts\python.exe astro_viewer\tools\audit_catalogue_editorial.py
```

The editorial audit reports the immutable 228-object pre-programme identity,
the 50 accepted NGC-only additions, complete IT/EN/ES coverage, accepted
manifests and the remaining 7,316-object NGC-only backlog. Pass `--batch` to
screen one candidate batch for near-duplicate prose; run
`audit_curiosity_sources.py --batch ...` separately because live URL state is
review evidence rather than a deterministic source gate.

Run `pyside6-qmllint` over every QML file below `astro_viewer/app/ui`. Existing
`unqualified access` diagnostics for context properties and nested components
are non-fatal technical debt, but any non-zero tool exit remains a failure.

## Latest Measured Gate

The `1.46.1` coverage/security source gate passed on Windows/Python 3.14.5 with
1,224 tests and 10 subtests in 315.84 seconds, 86% aggregate application
coverage, no unexpected warning summary, complete documentation coverage for
247 Python, 34 QML, and 17 operational files, an acyclic production graph, zero
protected-layer violations, a reviewed Bandit baseline (0 high, 34 medium, 14
low), clean dependency/license/MPC/OpenNGC/editorial checks, and successful
backend, normal QML, and Red Night Vision QML smoke tests. The in-gate installed-
environment `pip-audit` found no known vulnerabilities. The most recent separate
PySide6 6.11.2 `qmllint` pass over all 34 QML files remains the `1.45.22` pass;
its existing non-fatal diagnostics remain tracked technical debt.

The separate `1.46.1` batch evidence includes a successful live audit of 99
distinct manifest URLs and 36 reviewed Object Detail renders: six objects in
IT/EN/ES, each in normal and Red Night Vision mode. The sample includes the
multi-designation NGC 5906/5907 identity.

No remote CI result, distribution build, source tag, checksum, or release is
implied by that local source measurement.

## Change Policy

For a narrow service change, run Ruff, the architecture/security tools, and the
relevant focused tests first. For shared controller, persistence, astronomy,
provider, QML, localization, or packaging changes, run the complete source gate
before commit. A release artifact additionally requires every manual, provider,
upgrade, legal, visual, and artifact check in `docs/RELEASE_CHECKLIST.md`.
