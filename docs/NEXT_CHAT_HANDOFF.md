# NightScope - Next Chat Handoff

Updated: 2026-09-02

## Current State

- Source version: `1.45.9`.
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
| 1.45.9 | current source | Documents every domain, provider, presentation, equipment, catalogue, and localization service. |

## Resulting Architecture

`astro_viewer.main` resolves runtime paths and builds
`AppControllerDependencies`. `AppController` remains the Qt boundary and owns
signals, slots, asynchronous scheduling, stale-result rejection, and publication
of runtime state. Framework-independent application workflows and presentation
services now prepare recommendation, catalogue, observing/weather, and equipment
read models. Repositories own SQLite transactions and models carry typed data.

The production graph is acyclic. The architecture gate also prevents models,
database, astronomy, and service modules from importing the controller or the
application composition layer. Compatibility wrappers remain where existing
tests or integrations construct the controller directly.

The detailed assessment is in `docs/ARCHITECTURE_REVIEW_1_45.md`. The concise
verdict is that the codebase is robust, well tested, and materially better
organized than `1.44.0`, but not uniformly modular: `AppController`, the
equipment repository/bootstrap, the Skyfield engine, and the largest QML pages
remain concentrated maintenance areas.

## Validation

The final local `1.45.7` fast source gate passed on Windows/Python 3.14.5:

- 1,168 tests and 10 subtests in 273.47 seconds, with no unexpected warning
  summary;
- Ruff, compilation, license archive, MPC/OpenNGC snapshot checks;
- 0 import cycles and 0 protected-layer violations;
- Bandit baseline unchanged: 0 high, 37 medium, 14 low reviewed findings;
- `pip check`; a direct `pip-audit` afterward found no known vulnerabilities;
- backend, normal QML, and Red Night Vision smoke tests.

The GitHub workflow definition and its commands were checked locally. Do not
claim a remote CI pass until GitHub has run it.

## Next Product Work: Catalogue Editorial Content

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
