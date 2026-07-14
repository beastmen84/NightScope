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

Measured on the current Windows development environment for `1.32.8`:

| Command | Result | Time |
| --- | --- | ---: |
| `python -m pytest -q -n 4 astro_viewer/tests` | `764 passed, 7 subtests passed` | `0:01:43.34` |

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
The `1.31.0` additions cover generic orbital-element persistence, deterministic
offline ISS pass prediction, fresh-cache reuse, bounded stale fallback,
interval-aware Calendar/Home filtering and source/fact presentation without
Catalogue, scoring, Equipment, Planner or NSOM coupling.
The `1.31.1` corrections cover past-instant rejection before deduplication,
stable revolution-based ISS IDs, provider preparation outside the astronomy
lock, location-safe transient replacement and the dedicated hourly timer while
preserving the six-hour OMM cache TTL.
The `1.32.0` additions cover deterministic offline comet propagation, nightly
window aggregation, fresh/stale SBDB cache behavior, bounded retry, magnitude
cutoff, Calendar/Home comet presentation and independent per-source refresh
intervals. The fixture uses real JPL elements but never performs network calls.
The `1.32.1` additions cover the schema-v16 profile-name migration, collision
handling for an existing `Default` profile, stable ownership of all six seeded
equipment catalogues, built-in edit persistence, delete protection and form
validation. Presentation checks cover the compact sidebar, optional-value
visibility, binocular versus naked-eye wording and location-dependent empty
states in Home, Weather, Calendar and Catalogue.
The `1.32.2` corrections require explicit unique identifiers in all six
equipment CSV files and stable-key references in reducer compatibility data.
Regression tests simulate a schema-v16/`1.32.1` row whose product name is
corrected, verify that its database ID and reducer links remain unchanged, keep
user overrides intact and preserve a custom row when the corrected natural
identity would collide. A schema-v15 simulation removes all six classes of
equipment key and confirms that bootstrap restores them without changing row
counts.
The `1.32.3` corrections cover the no-location sky-quality guard, direct
Home/Weather/Calendar navigation to location setup, localized barrel-size
labels, degree-symbol catalogue dimensions and the revised required/optional
Equipment form copy. Italian and English QML smoke tests use disposable
runtime directories.
The `1.32.4` corrections cover the backend catalogue-angle label actually used
by QML, naked-eye alternative filtering through the existing Equipment read
model, the neutral Home Moon icon, readable alternative columns, explicit
night-aggregate Weather labels, localized urban-baseline provenance and manual
coordinate required-state copy. A live CelesTrak probe for Addis Ababa is kept
outside the deterministic suite; the product code was unchanged after it
confirmed that the current ten-day `0` ISS count is physically consistent.
The `1.32.5` corrections cover removal of the synthetic light-pollution seed,
cleanup of legacy non-VIIRS cache rows, explicit unavailable sky-quality state,
weather-only seeing when Bortle is absent, continued reuse of real VIIRS cache
and optional real local CSV data. QML checks cover `n/d` sky-quality metrics,
balanced Home target columns and event titles capped at two lines.
The `1.32.6` corrections cover the partial Home deep-sky state when weather is
available without Bortle, non-optimistic faint-object copy, the amber partial
badge and stale-VIIRS disclosure when Earthdata is not verified. The lifecycle
test also confirms that this offline stale-cache path starts no network worker.
The `1.32.7` additions cover real offline timezone polygons for land and ocean,
lazy resolver reuse, exact-coordinate preservation, Windows city metadata
separation, manual-coordinate and coarse-Windows normalization, valid IP
timezone precedence and provider/system fallback.
The `1.32.8` corrections verify acquisition-only normalization, coordinate-based
timezones for manual city selection, complete exclusion of the GeoNames
timezone field, lazy system-timezone fallback and direct reuse of current
saved-location records.
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
