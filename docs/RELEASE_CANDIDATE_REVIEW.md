# NightScope v1.0 Release Candidate Review

Review date: 2026-06-25

Scope: architecture, calculations, code quality, documentation, tests, coverage
and maintainability. No new features were implemented. PyInstaller was not run
and `dist/` was not modified.

Post-review note: this file preserves the original release-candidate findings.
Several release-gate items were later addressed during v1.0 stabilization:
`ruff` is clean, weather blocking is centralized in Python, the runtime
database initialization/update path is portable, and standard validation can be
run with `python tools/run_checks.py`.

## Executive Result

NightScope is functionally coherent and the core calculation services are better
tested than the surrounding UI/controller layer. The project is close to a
stable 1.0, but it should not be considered ready for a high-quality v1.0 until
the remaining release-gate and maintainability issues are addressed.

Release readiness: No, not yet.

Material blockers:

- `ruff` fails on one lint error in `skyfield_engine.py`.
- Profile/equipment and refresh correctness have tests, but the most important
  orchestration class is still under-covered and oversized.
- Weather blocking criteria are duplicated between planner logic and QML
  presentation, creating a realistic future inconsistency risk.
- Equipment profile persistence has a legacy single-telescope field alongside
  current many-to-many assignment tables, which is easy to misunderstand.

## Architecture

### Strengths

- The project has a clear folder structure: UI, ViewModel/controller, services,
  repositories, models, astronomy, data and tests are separated.
- Most domain calculations live in services rather than QML.
- Repositories mostly stay focused on SQLite persistence.
- Models are simple dataclasses and are easy to inspect.
- Fallback paths exist for astronomy, weather, light pollution and location.
- The refresh chain now explicitly recomputes profile-dependent recommendations
  after active-profile and equipment changes.

### Weaknesses

- `AppController` is about 2290 lines and mixes orchestration, presentation
  formatting, refresh invalidation, equipment mutation, weather digest,
  calendar setup and object-detail reasoning.
- `HomePage.qml` is about 1100 lines and contains non-trivial weather-blocking
  presentation logic.
- Cache ownership is split between repositories, services and controller fields
  without a single documented invalidation policy.
- Some thresholds are duplicated across Python and QML.
- The equipment profile schema still carries legacy compatibility behavior.

### Suggested Future Improvements

- Split `AppController` gradually into focused presenters or coordinator
  objects after 1.0 stabilization.
- Centralize weather-blocking thresholds in Python and expose the result to QML.
- Centralize Moon-illumination parsing and night-hour selection.
- Document or migrate the legacy `EquipmentProfile.telescope_id` field.
- Keep all future ranking and scoring changes in services, with QML only
  displaying controller-provided state.

## Calculation Logic

### Confirmed Calculations

Astronomy:

- Solar-system rise, set, transit, altitude, azimuth and night-window visibility
  are computed through Skyfield.
- Deep-sky visibility uses Messier catalog coordinates and sampled altitude
  windows.
- Deep-sky useful altitude threshold is higher than solar-system threshold.

Observing quality:

- Global score combines cloud, precipitation, wind, humidity and Moon
  illumination.
- Blocking weather suspends the observing plan when score, cloud or
  precipitation crosses minimum usability thresholds.

Planetary score:

- Combines global weather, seeing, wind and Moon contribution.
- Weather cap prevents excellent category scores under blocked weather.

Deep-sky score:

- Combines weather, transparency, light pollution and Moon illumination.
- Moon and light-pollution penalties are object-type dependent.
- Galaxies are penalized more than globular clusters under strong moonlight.

Equipment:

- Recommendations use active-profile equipment only.
- Zoom eyepieces remain single records and are sampled internally.
- Barlows are suggested only when assigned and only when they improve the setup.
- Magnification, exit pupil and true field are calculated from telescope,
  eyepiece and Barlow parameters.

VIIRS/light pollution:

- Uses cache, CSV providers, NASA Black Marble VIIRS when authorized and offline
  fallback.
- Radiance-to-Bortle conversion is threshold-based.

### Potential Inconsistencies

- Seeing can display as excellent while global observing quality is poor. This
  is mathematically valid because seeing is atmospheric steadiness, not cloud or
  rain usability. It remains a UX risk unless the blocked-session warning is
  visually dominant.
- Best-object selection uses a weather-factor floor, so a target can remain
  selected in poor weather. The current global warning mitigates this by making
  it a potential target, not a recommendation to observe now.
- Planner weather blocking and QML warning logic are duplicated. They currently
  match conceptually but can drift.

### Hidden Assumptions

- Night weather windows are hard-coded around evening/morning hours and vary
  slightly by service.
- VIIRS cache freshness uses a 7-day revalidation interval; the interval is a
  product-cadence policy rather than a guarantee that NASA has published a new
  monthly composite.
- Moon penalties use illumination only, not Moon altitude or angular distance.
- Equipment recommendations assume catalog focal length, aperture and apparent
  field values are trustworthy.

### Possible Improvements

- Expose a single computed `isObservingSessionBlocked` state from Python.
- Add a service-level result that explains why a plan is suspended.
- Add tests for Moon-heavy and high-light-pollution ranking in the controller
  layer, not only service-level tests.
- Add tests for profile delete/rename and active-profile equipment deletion
  refresh paths.

## Code Quality

### Duplicated Logic

- Weather blocking thresholds in planner and QML.
- Score labels in observing score and astronomy engine.
- Night-hour filtering in observing score, seeing and home digest.
- Moon illumination string parsing in multiple services.
- Deep-sky Moon/light-pollution adjustments in planner and controller.

### Dead Code And Obsolete Code

- No `TODO`, `FIXME`, `XXX`, `HACK`, `deprecated` or `obsolete` markers were
  found by static text scan.
- Several import/tool scripts have 0 percent test coverage because they are
  operational tools, not because they are proven dead.

### Technical Debt

- `AppController`: 2290 lines.
- `HomePage.qml`: 1109 lines.
- `location_service.py`: 946 lines.
- `equipment_catalog_repository.py`: 593 lines.
- `skyfield_engine.py`: 557 lines.
- `light_pollution_service.py`: 544 lines.
- `equipment_service.py`: 514 lines.

Large files are not automatically wrong, but the controller and home page are
where future regressions are most likely.

## Documentation

Created:

- `docs/ARCHITECTURE.md`
- `docs/CALCULATION_LOGIC.md`
- `docs/RELEASE_CANDIDATE_REVIEW.md`

Completeness:

- Architecture boundaries and data flow are documented.
- Refresh and cache ownership are documented.
- Astronomical, weather, Moon, VIIRS, recommendation and equipment calculations
  are documented.
- Known limitations are explicitly listed.

Missing areas:

- There is still no developer-facing API/reference document for every
  `AppController` property and signal.
- There is no schema migration guide for the profile-equipment legacy field.

## Testing

### Commands Run

`ruff`:

- Command: `.venv\Scripts\python.exe -m ruff check astro_viewer`
- Result: failed.
- Error: `F841 Local variable exc is assigned to but never used` in
  `astro_viewer/app/astronomy/skyfield_engine.py:63`.

`pytest`:

- Command: `.venv\Scripts\python.exe -m pytest astro_viewer\tests -q`
- Result: passed.
- Summary: 107 passed in 70.93s.

`pytest-cov`:

- Command: `.venv\Scripts\python.exe -m pytest astro_viewer\tests -q --cov=astro_viewer --cov-report=term-missing`
- Result: passed.
- Summary: 107 passed in 60.47s.
- Total coverage including tests/tools: 71%.
- Application-only coverage: 75%.

`smoke-test`:

- Command: `.venv\Scripts\python.exe -m astro_viewer.main --smoke-test`
- Result: passed.
- Output showed app startup in no-location state with zero objects/weather, which
  is expected without an active location.

`qml-smoke-test`:

- Command: `.venv\Scripts\python.exe -m astro_viewer.main --qml-smoke-test`
- Result: passed.

`compileall`:

- Command: `.venv\Scripts\python.exe -m compileall astro_viewer`
- Result: passed.

Notes:

- `pytest-cov` generated the full terminal report.
- `coverage.py` was used only to print the application-only filtered view from
  the `.coverage` data file.
- The runtime database was restored after the initial test run.
- The intermediate `.coverage` file was removed after extracting the report.

### Coverage Of Critical Modules

Strong coverage:

- `observing_score_service.py`: 95%.
- `night_planner_service.py`: 91%.
- `advanced_observing_service.py`: 91%.
- `seeing_service.py`: 90%.
- `weather_service.py`: 83%.
- `skyfield_engine.py`: 86%.
- `sky_quality_repository.py`: 100%.
- `weather_cache_repository.py`: 100%.

Moderate or weak coverage:

- `app_controller.py`: 65%.
- `equipment_catalog_repository.py`: 51%.
- `equipment_service.py`: 80%.
- `light_pollution_service.py`: 78%.
- `location_service.py`: 78%.
- `database/bootstrap.py`: 77%.
- `models/sky.py`: 74%.

Untested or intentionally tool-like:

- `main.py`: 0% under coverage because smoke tests were run separately.
- `logging_service.py`: 0%.
- Several `tools/*` scripts: 0%.

### Untested Critical Paths

- Some active-profile CRUD/delete/rename edge cases remain under-covered.
- Some profile repository mutation paths are under-covered.
- Controller-level integration of Moon/light-pollution presentation filtering is
  weaker than service-level coverage.
- QML warning behavior is covered only by smoke-level validation, not granular
  UI assertions.

### Recommended Additional Tests

- Active profile delete and fallback profile refresh.
- Profile rename when identity changes internally.
- Deleting assigned telescope/eyepiece/Barlow from active profile.
- Controller-level high-Moon ranking: galaxy vs globular vs open cluster.
- Controller-level blocking-weather warning state matching planner blocking.

## Long-Term Maintainability

An experienced developer could maintain NightScope, especially with the new
architecture and calculation documents. The main difficulty is that too much
implicit behavior is concentrated in `AppController` and `HomePage.qml`.

Most worrying areas:

- `AppController`, because many refresh and presentation decisions intersect
  there.
- Profile/equipment persistence, because it mixes legacy and current schema
  concepts.
- Weather-blocked presentation, because criteria exist in both Python and QML.
- Light-pollution/VIIRS, because provider fallback and cache freshness rules are
  implicit and operationally complex.
- Moon/deep-sky ranking, because the current model is intentionally simplified
  and can be mistaken for a physical visibility model.

## Release Readiness

NightScope is not yet ready for a high-quality stable v1.0.

Only material issues:

- The lint gate fails and should be clean for v1.0.
- The largest controller has insufficient coverage relative to its release
  impact and historical refresh bugs.
- The profile/equipment repository layer is under-covered for a critical user
  workflow.
- Weather blocking should have one source of truth to avoid plan/warning drift.
- The legacy profile telescope field should be explicitly handled in code
  comments or migration documentation before future maintenance.

These are stabilization issues, not feature requests.
