# NightScope - Next Chat Handoff

Updated: 2026-09-03

## Current State

- Source version: `1.45.21`.
- Current public release: `v1.43.0`.
- Public-release source commit: `26dfaf49df8f9b8e73e84f406396f406170400b2`.
- The `1.45.x` architectural series is source-only. No `1.45.x` tag, checksum,
  Windows/Linux bundle, or GitHub release has been created.
- `dist` was deliberately not regenerated or modified during the series.
- Historical handoff detail through `1.45.6` is preserved in
  `docs/archive/NEXT_CHAT_HANDOFF_1.45.6.md`.

## Architectural Series

| Version | Commit | Outcome |
| --- | --- | --- |
| 1.45.0 | `6e4e2e9` | Introduced the application composition root and injected resolved dependencies into the controller. |
| 1.45.1 | `771ebcd` | Extracted synchronous catalogue recommendation orchestration and immutable worker snapshots. |
| 1.45.2 | `f5285fd` | Extracted observing, weather, session, and night-time presentation logic. |
| 1.45.3 | `2328be9` | Extracted catalogue records, search/filter projections, observability, and detail construction. |
| 1.45.4 | `6000599` | Extracted equipment input, catalogue, profile-inventory, and presentation workflows. |
| 1.45.5 | `18ec214` | Removed all detected production import cycles and introduced lower-level DTO/protocol boundaries. |
| 1.45.6 | `60a964f` | Added CI, strict warning policy, incremental Bandit review, and standard architecture gates. |
| 1.45.7 | `1fec5df` | Consolidates architecture/testing documentation and closes the final structural audit. |
| 1.45.8 | `cef54b3` | Defines the code-documentation contract and documents application/model boundaries. |
| 1.45.9 | `06b514e` | Documents every domain, provider, presentation, equipment, catalogue, and localization service. |
| 1.45.10 | `35972b7` | Documents persistence, astronomy, Qt view models, and runtime composition boundaries. |
| 1.45.11 | `6719979` | Documents the responsibility and boundary contract of every QML file. |
| 1.45.12 | `8f4a9f2` | Documents maintenance, packaging, CI, configuration, schema, and manual files. |
| 1.45.13 | `0caf68f` | Documents every test/support module and enforces the complete source-documentation inventory. |
| 1.45.14 | `de25eab` | Updates the validated development and portable-packaging toolchain without changing runtime behavior. |
| 1.45.15 | `8c11175` | Updates the validated Qt and astronomy runtime baseline while preserving application contracts. |
| 1.45.16 | `a8584a8` | Updates and constrains the Earthdata transport family as one tested resolver unit. |
| 1.45.17 | `98b7b67` | Extracts concrete location adapters behind an explicit composition-root bundle while retaining compatibility imports. |
| 1.45.18 | `d18e7d9` | Extracts controller-facing location commands into a framework-independent workflow with explicit inputs and outcomes. |
| 1.45.19 | `62f6383` | Separates installed profile inventory from global equipment catalogues without changing the SQLite schema or identifiers. |
| 1.45.20 | `4cf60a1` | Pins the Windows Python/dependency closure; its remote run exposed path-dependent bytecode in the legal archive. |
| 1.45.21 | current source | Excludes code and bytecode from license notices so clean Windows environments generate an identical archive. |

## Resulting Architecture

`astro_viewer.main` resolves runtime paths and builds
`AppControllerDependencies`. `AppController` remains the Qt boundary and owns
signals, slots, asynchronous scheduling, stale-result rejection, and publication
of runtime state. Framework-independent application workflows and presentation
services now prepare recommendation, catalogue, observing/weather, and equipment
read models. The composition root also builds the concrete location-adapter
bundle; `LocationService` owns provider selection, fallback and result
normalization. `LocationCommandWorkflow` owns search, selection, validation,
startup fallback and recent-location policy while the controller retains Qt
lifecycle and publication. `EquipmentProfileRepository` owns profile lifecycle
and assignments independently from global catalogue CRUD; the legacy repository
surface remains compatible and forced removals still share one SQLite
transaction. Repositories own SQLite transactions and models carry typed data.

The Windows source job uses Python 3.14.5 plus an exact 62-component constraints
file that is mechanically matched to `THIRD_PARTY_LICENSES.txt`. Linux testing
and the separate Python 3.14 dependency audit remain floating compatibility
signals rather than release-record environments.

License collection accepts arbitrary notice filenames only below the standard
`.dist-info/licenses` directory and excludes Python source, bytecode and cache
directories. The regenerated archive is identical between the project venv and
a clean Windows environment despite their different absolute paths.

The production graph is acyclic. The architecture gate also prevents models,
database, astronomy, and service modules from importing the controller or the
application composition layer. Compatibility wrappers remain where existing
tests or integrations construct the controller directly.

The detailed assessment is in `docs/ARCHITECTURE_REVIEW_1_45.md`. The concise
verdict is that the codebase is robust, well tested, and materially better
organized than `1.44.0`, but not uniformly modular: `AppController`, the NASA
provider, equipment repository/bootstrap, the Skyfield engine, and the largest
QML pages remain concentrated maintenance areas.

## Validation

The final local `1.45.21` coverage/security source gate passed on
Windows/Python 3.14.5:

- 1,209 tests and 10 subtests in 371.21 seconds, with 86% aggregate application
  coverage and no unexpected warning summary;
- validated toolchain: pip 26.2.1, Ruff 0.16.5, coverage 7.16.0, PyInstaller
  6.22.2, and `pyinstaller-hooks-contrib` 2026.7;
- validated UI/astronomy runtime: PySide6/Qt/shiboken6 6.11.2, Skyfield 1.55,
  Astropy 8.0.1, astropy-IERS-data `0.2026.8.31.0.57.9`, and NumPy 2.5.2;
- validated Earthdata runtime: earthaccess 0.18.0, s3fs/fsspec 2026.7.0,
  aiobotocore 3.9.0, and maximum compatible botocore 1.43.56;
- complete documentation inventory: 245 Python, 34 QML, and 16 operational
  files;
- Ruff, compilation, license archive, MPC/OpenNGC snapshot checks;
- 0 import cycles and 0 protected-layer violations;
- Bandit baseline unchanged: 0 high, 34 medium, 14 low reviewed findings;
- `pip check`; the in-gate `pip-audit` found no known vulnerabilities;
- backend, normal QML, and Red Night Vision smoke tests;
- PySide6 6.11.2 `qmllint` over all 34 QML files exited successfully.

The GitHub workflow definition and its commands were checked locally. Do not
claim a remote CI pass until GitHub has run it.

## Next Architectural Step

`1.45.19` completed the first persistence split. Profile CRUD and every
equipment-assignment family now live in `EquipmentProfileRepository`, while
`EquipmentCatalogRepository` owns global catalogue CRUD and inherits the old
profile surface only for compatibility. Both repositories use the existing
tables and stable IDs. A populated-database test verifies profile inventory
survives bootstrap unchanged, and a forced-failure test proves catalogue delete
plus assignment cleanup still roll back atomically.

The next persistence change should not be automatic. Choose either one coherent
catalogue family from the remaining repository or one migration/seed family
from `database.bootstrap`, only after mapping its transaction boundary. The
Skyfield event/calculation seams remain the next non-persistence priority.

## Deferred Product Work: Catalogue Editorial Content

The next planned stream is source-backed descriptions and curiosities for the
NGC-only physical targets, in Italian, English, and Spanish. The existing 228
curated Solar System/Messier/Caldwell entries are complete; 7,366 NGC-only
physical targets currently retain the localized `Work in progress` fallback.

Use `docs/CATALOGUE_EDITORIAL_WORKFLOW.md` as the acceptance contract. Important
boundaries:

- work in reviewed batches with one source version and commit per batch;
- never fabricate a fun fact from catalogue type alone;
- retain per-object source label, HTTPS URL, verification state, and stable
  `object_id`;
- review all three languages editorially rather than accepting raw automatic
  translation;
- keep editorial fields out of NSOM, equipment selection, visibility, and
  recommendation scores;
- do not regenerate `dist` until explicitly requested.

## Release Boundary

The stable public bundles remain `v1.43.0`. Source readiness is not publication.
Before a future release, update the target version, run the coverage/security
gate, compile translations, complete QML and visual review, build fresh Windows
and Debian 12 artifacts, audit their legal/runtime contents, calculate and
verify checksums, create the source tag, and only then publish the GitHub
release. Follow `docs/RELEASE_CHECKLIST.md`.

## Living References

- `docs/ARCHITECTURE.md`: detailed current runtime architecture.
- `docs/ARCHITECTURE_REVIEW_1_45.md`: evidence-backed structural assessment.
- `docs/TESTING.md`: current local and CI gate contract.
- `docs/CATALOGUE_EDITORIAL_WORKFLOW.md`: next multilingual content workflow.
- `docs/RELEASE_CHECKLIST.md`: artifact and publication approval.
- `astro_viewer/CHANGELOG.md`: source-version history.
