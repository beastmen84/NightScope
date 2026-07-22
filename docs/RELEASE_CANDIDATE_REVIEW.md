# NightScope Pre-Release Audit

Review date: 2026-07-21

Scope: Python and QML application code, SQLite/bootstrap paths, astronomy and
recommendation boundaries, external-provider handling, localization, packaged
data and images, developer tooling, dependency security, user documentation,
privacy-sensitive logging, and Windows packaging configuration.

The initial audit did not rebuild `dist`. The user later rebuilt the persistent
`1.33.2` bundle; its legal/Qt audit and packaged backend/QML smoke tests pass.
The public release is available at
`https://github.com/beastmen84/NightScope/releases/tag/v1.33.2`.

## Verdict

No high-severity functional application defect was found. The deterministic
suite, static checks, catalogue asset checks, and runtime dependency audit are
clean after the fixes listed below.

NightScope 1.33.2 has been published, but it is **not yet fully approved by its
own release checklist**. The remaining work concerns release hardening and
product verification rather than a known broken core:

1. The Windows distribution has been rebuilt and passes automated artifact
   checks, but it must still pass the packaged-build visual matrix. Validation
   creates runtime data beside the executable, so tests must use a copy and the
   final archive must come from a pristine bundle. The published ZIP has passed
   this audit and the release notes identify its exact MPL source commit.
2. The final live-provider matrix has not been executed for Open-Meteo,
   CelesTrak, JPL SBDB, Earthdata VIIRS/AOD, OpenAQ, Windows location, and the
   explicit IP fallback.
3. Release dependencies are range-based rather than frozen into a tested lock
   or SBOM, and the artifact is not signed. Its SHA-256 digest is published.

Use `docs/RELEASE_CHECKLIST.md` as the release gate.

## Defects Corrected In This Audit

### Project and dependency licensing

NightScope is now licensed under MPL-2.0, Copyright 2026 Davide Marchi. A
  consolidated third-party notice covers Python packages, Qt/PySide, GeoNames,
  MPC observatory data, timezone-boundary data, astronomical data, and image
  provenance. A generated archive preserves the exact installed license and copyright texts and is
validated by the standard repository gate.

The previous PyInstaller bundle collected every QML module installed with
PySide6, including unused Qt Addons and GPL-only modules. Runtime requirements
now select PySide6 Essentials, custom hooks retain only NightScope's required
LGPL-compatible QML modules, and the build script rejects missing legal files,
missing required Qt DLLs, or unexpected GPL-only Qt modules. The isolated
PyInstaller bundle, persistent Windows build, and extracted public ZIP passed
the Qt/legal audit. The packaged backend and QML smoke tests pass, and the ZIP
contains no NightScope runtime database, backup, cache, or log.

### Developer dependency advisory

`deep-translator 1.11.4` was present only for translation maintenance, but the
installed-environment audit reported `PYSEC-2022-252`. The package was removed
from `requirements-dev.txt` and replaced by a small, timeout-bounded developer
adapter using the already required `requests` dependency. The translation tools
remain best-effort utilities and generated text still requires human review.

Advisory: `https://osv.dev/vulnerability/PYSEC-2022-252`.

### Privacy-sensitive logging

Several information logs could include exact coordinates, a location cache
key, the complete Windows diagnostic payload, timezone/city normalization
details, or an Earthdata username. The messages now retain operational status
without those identifiers. Regression tests explicitly reject coordinate,
payload, cache-key, and username disclosure.

An unused Windows diagnostic property and slot were also removed from the QML
controller surface. The developer service diagnostic remains available to its
focused tests but no longer logs the raw report.

### Validation runner and developer environment

The default validation runner executed the full test suite once without and
once with coverage. It now performs exactly one suite run: coverage by default,
or no coverage with `--fast`. `requirements-dev.txt` now lists every tool used
by the documented workflow. Optional `--security` runs `pip-audit`. Parallel
pytest execution is capped at four workers; using every logical CPU caused
unnecessary memory pressure in the Windows/PyCharm development environment.
Coverage now targets application and entry-point modules only; tests and
developer utilities no longer inflate the reported percentage.

### Runtime and log ownership

The frozen entry point configured logs from the bundled code directory while
the database and preferences were rooted beside the executable. In a PyInstaller
onedir build this could place logs under `_internal/logs`, contradicting the
portable-data contract and the user documentation. Logging now consumes the
same resolved runtime directory as the database, preferences, and caches.

The runtime resolver also accepts a developer/test-only override. Standard
backend and QML smoke checks create a fresh temporary runtime, where automatic
location detection is disabled by default, and delete it after the subprocess.
They therefore do not depend on or modify the developer's database, preferences,
caches, or logs.

### Provider concurrency and input hardening follow-up

The 2026-07-21 deep review reproduced edge cases that the original release
audit did not cover. OpenAQ distances below 500 metres were interpreted as
kilometres, an exact zero-distance station lost ordering priority, and failed
`latest` requests could be cached as genuine no-data. The service now follows
the API v3 metre contract, preserves zero and only caches measurements,
historical results or successful no-data responses.

Open-Meteo request status is now thread-local. OpenAQ, VIIRS and NASA AOD
completions carry request generations as well as location identity, so stale
credential/location workers cannot complete a newer refresh. Temporary
Earthdata `NETRC` use is serialized across connection tests and VIIRS. VIIRS
reports authentication, rate-limit, HTTP and transport failures separately
from missing granules and stops retrying older months on provider-wide errors.

The same pass added a 24-hour freshness limit and explicit cached wording for
the approximate IP-location fallback, finite-number validation at controller
and repository boundaries, timezone-aware initialization of the Catalogue
month, and console-log fallback when the portable runtime cannot create its log
directory. The database/schema and all recommendation/scoring policies remain
unchanged.

### User documentation and access

The GitHub README was an Italian release diary mixed with project instructions.
It is now an English product and contributor overview that links to the
changelog for history and states the pre-release limitations explicitly.

The former Italian-only manual contained a contradiction about OpenAQ's role in
canonical transparency. It has been replaced by a self-contained Italian and
English manual with a language selector, responsive navigation, print styling,
privacy/provider guidance, troubleshooting, equipment formulas, and an
astronomer-facing explanation of recommendation boundaries. A help button in
the sidebar opens the manual in the current application language.

## Reviewed Areas With No Confirmed Defect

### Database and SQL

Dynamic SQL identified by static analysis was inspected. Dynamic identifiers
and placeholder counts come from fixed internal tables/columns or constructed
integer counts; user values are bound parameters. No exploitable SQL injection
path was found.

Bootstrap remains schema version 16. Built-in equipment rows keep stable seed
keys and user overrides; user-created rows remain separate. The legacy
`EquipmentProfile.telescope_id` field is still technical debt, not the owner of
the current many-to-many profile model.

### Recommendation and astronomy boundaries

The audit did not change NSOM, Planner, Home target ranking, Equipment scoring,
Sky Compass scoring, or transient-event semantics. Moon geometry, atmosphere,
sky background, observer capability, target timing, and session state retain
their documented ownership. ISS and comet events remain outside Catalogue,
Equipment, weather scoring, Planner, and NSOM.

### Providers and asynchronous state

External requests use HTTPS and bounded timeouts. Credentials are held through
the system credential backend. Location/provider completion paths compare the
active identity and reject stale asynchronous results. Provider no-data states
remain distinct from authentication, network, parsing, and stale-cache states.

### Data and assets

The packaged deep-sky image set and Solar System image set passed their
repository checks. GeoNames remains necessary for offline city search and
labels; timezone calculation itself uses offline coordinate polygons. Synthetic
light-pollution fallback data remains removed, so unavailable Bortle/SQM values
stay unavailable.

### Secrets

No secret was found in tracked source files. Local credential/test files covered
by `.gitignore` were not read, modified, or staged.

## Residual Engineering Risk

These items are not current release blockers by themselves, but they increase
future regression cost:

- `AppController` is approximately 7,100 lines and still mixes orchestration,
  presentation projection, refresh ownership, and mutation commands.
- `HomePage.qml` is approximately 1,700 lines.
- `location_service.py`, `equipment_catalog_repository.py`, and
  `skyfield_engine.py` are also large ownership surfaces.
- There is no repository CI workflow; validation currently depends on local
  execution.
- QML lint exits successfully for all 30 files but reports a large existing set
  of `unqualified access` warnings around Python context properties and nested
  component ownership. Italian/English runtime smoke tests pass; removing the
  warnings requires a separate, visually verified QML qualification pass.
- The portable runtime requires a writable extracted folder and has no
  installer/update/rollback workflow.
- Skyfield/NumPy emit known deprecation warnings in the current environment.
- Dependency ranges permit drift between development and a later rebuild.

Refactoring the controller or schema immediately before release would create
more risk than it removes. Track these as post-release work unless the remaining
visual/provider checks expose a concrete defect.

## Audit Evidence

Baseline and final commands completed during this audit:

| Check | Result |
| --- | --- |
| `python -m pip check` | No broken requirements |
| `python -m ruff check astro_viewer tools` | Passed |
| `python -m compileall -q astro_viewer tools` | Passed |
| Third-party license archive | Current; 61 distributions covered |
| `python -m pytest -q -n 4 astro_viewer/tests` | 816 passed, 613 warnings, 10 subtests passed |
| Runtime-only coverage | 84% across 15,403 statements |
| Installed-environment `pip-audit` | No known vulnerabilities |
| Bandit application/tool scan | 0 high, 26 medium, 12 low; dynamic-SQL and subprocess findings manually reviewed |
| Translation catalogues | IT/EN/ES: 1,670 finished, 0 unfinished each |
| Translation and developer-tooling regression tests | 34 passed |
| QML lint and smoke | 30 files linted with no failure; 760 known static warnings; Italian, English and Spanish smoke passed |
| Deep-sky image repository check | 219 JPEG assets passed |
| Solar System image repository check | 9 JPEG assets passed |
| Windows bundles | Isolated, persistent, and published-ZIP Qt/legal audits passed; packaged smoke passed and the ZIP contains no runtime state |

Detailed commands, timings, known dependency warnings, and the disposable
runtime contract are recorded in `docs/TESTING.md`.
