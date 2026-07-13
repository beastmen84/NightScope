# NightScope Testing Workflow

NightScope has several hundred tests. The full serial suite remains a diagnostic
fallback, but it is too slow for every small NSOM commit.

## Recommended Commands

Fast syntax validation:

```powershell
.\.venv\Scripts\python.exe -m compileall astro_viewer
```

Runtime dependency consistency:

```powershell
.\.venv\Scripts\python.exe -m pip check
```

Focused area validation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q astro_viewer/tests/test_observation_conditions_service.py
```

Focused NSOM validation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q astro_viewer/tests/test_nsom*.py
```

Parallel full suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -n auto
```

Serial full suite fallback:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Developer Dependency

Parallel execution uses `pytest-xdist`. Translation updaters can use
`deep-translator`; it is a developer-only dependency and is not required by the
application runtime. Install developer dependencies with:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## Measured Baseline

Measured on the current Windows development environment for `1.30.0`:

| Command | Result | Time |
| --- | --- | ---: |
| `python -m pytest -q -n 4 astro_viewer/tests` | `725 passed, 7 subtests passed` | `0:01:51.24` |

The current count includes the generic catalogue schema, all 109 Caldwell
targets, complete description/curiosity/image seed coverage, licensed survey
and NASA/JPL Solar System asset migration, multi-designation identity
projections and the target-taxonomy contract for every raw type in all 219
Messier/Caldwell records. It also covers the NSOM invariants for single-pass
factor construction and defensive Home/Planner/Sky Compass counts. The count
also includes the lower-Home Sky Compass filter contract and live target
membership replacement without a general Home refresh. The `1.27.1` baseline
includes schema v14, explicit color classes, profile-aware filter matching,
target photographic flags, exact reducer matching against the target-specific
telescope, structured custom compatibility and the complete Home-detail payload
path. The current filter coverage also checks telescope-only presentation,
product and target aperture thresholds, single-class fallback copy and
exclusion from scoring and ObserverCapability. The `1.28.0` additions cover
the complete observation-log repository and controller CRUD cycle, validation,
unlimited result projection, navigation and preservation through database
bootstrap and runtime-folder copies.
The `1.30.0` additions validate auto-discovered language packs, symmetric and
complete Qt catalogues, compiled translation assets, structured seed coverage,
locale-aware dates and numbers, live runtime switching, preference preservation
and PyInstaller packaging. A synthetic third language verifies that runtime,
sidebar and packaging need no code changes. Boundary tests also ensure internal
services consume canonical payloads and a presentation-only language refresh
does not recompute astronomy, weather, equipment, scoring or NSOM. QML smoke
tests are run in Italian and English from disposable runtime directories.
The earlier reduction in `1.21.0` was intentional:
migration-only
comparison, rollback, shadow-payload and automatic-diagnostic tests were
removed with the retired production paths they exercised.

The latest serial diagnostic baseline before `1.18.2` was `658 passed, 7
subtests passed` in `0:02:33`; it was used to isolate a repeated Skyfield
calculation, not as the normal validation path.

Use the parallel full suite for normal pre-commit validation when the change
touches shared runtime services. Use the serial suite only to isolate a
parallel/order-dependent failure or to diagnose timing in one deterministic
process.

The `1.20.0` Calendar probe for Addis Ababa produces 82 annual events in about
2.8 seconds inside the astronomy worker. Planetary conjunction discovery scans
all 21 planet pairs in less than one second; the remaining time includes local
night-window and common-altitude sampling. The repeated warnings in Calendar
tests come from the known Skyfield/NumPy dtype deprecation, not application
failures.

## Validation Policy

For small developer-only documentation or report updates:

1. Run `compileall astro_viewer`.
2. Run focused tests for the files or reports touched.

For shared runtime changes:

1. Run `pip check` and `compileall astro_viewer`.
2. Run focused tests for the touched area.
3. Run `pytest -q -n auto`.

For release candidates or broad refactors:

1. Run `compileall astro_viewer`.
2. Run focused tests for the touched area.
3. Run `pytest -q -n auto`.
4. Run serial `pytest -q` only if parallel execution reports a failure that may
   be order- or worker-dependent.
