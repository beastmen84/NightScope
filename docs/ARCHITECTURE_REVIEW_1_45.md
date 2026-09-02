# NightScope 1.45 Architecture Review

Date: 2026-09-02
Scope: source `1.44.0` through `1.45.18`

## Verdict

NightScope is a robust and heavily tested desktop application whose architecture
is now coherent enough to support the next catalogue-content phase safely. It
is not a uniformly small or classically layered codebase. Its strongest areas
are domain isolation, regression coverage, explicit persistence behavior, and
runtime validation. Its main weakness is concentration: the Qt controller, two
persistence modules, the Skyfield implementation, and several QML pages remain
large.

The `1.45.x` work materially improves organization without changing QML
contracts, database schema, scoring, or recommendation outcomes. Concrete
dependencies have one composition boundary; large pure workflows have moved out
of Qt; the production import graph is acyclic; lower layers cannot import the
controller/composition root; and the standard source gate now detects security,
warning, architectural, and missing-documentation regressions before pytest.

The architecture is substantially healthier, but the work is not exhausted.
The remaining risks are concentrated and have identifiable seams. They justify
further focused versions around persistence aggregates, astronomy/provider
components, and selected controller commands; they do not justify a wholesale
rewrite or arbitrary splitting by line count.

## Evidence Snapshot

Measurements are physical source lines from the working tree unless otherwise
stated.

| Area | Evidence | Assessment |
| --- | --- | --- |
| Production Python | 123 modules, 47,332 lines | Broad domain surface; every module now states its responsibility and package boundaries are discoverable. |
| Tests | 87 test files plus 2 support/package modules, 35,805 lines; 1,201 tests and 10 subtests at the 1.45.18 gate | Very strong regression protection relative to production size. |
| `AppController` | 9,836 lines at 1.44.0; 7,814 at 1.45.18, including its module header; 2,022 net lines removed (20.6%) | Still the largest risk, but now more clearly a Qt orchestration boundary. |
| Controller surface | 561 methods, including 114 slots and 141 properties | Large compatibility/API surface makes wholesale rewriting risky. |
| Largest persistence modules | `equipment_catalog_repository.py` 3,027 lines; `bootstrap.py` 2,492 | Transactionally cohesive but too concentrated for easy local reasoning. |
| Astronomy implementation | `skyfield_engine.py` 2,434 lines | Complex by domain necessity; provider/event subcomponents can still be separated. |
| Largest QML pages | Home 1,708 lines; Object Detail 1,245 | Backend decisions are mostly extracted, but layout/component complexity remains. |
| Import structure | 0 cycles; 0 protected-layer violations | Good and now mechanically enforced. |
| Documentation inventory | 243 Python, 34 QML, and 15 operational files | Complete governed coverage, enforced before the long test suite. |
| Static/security gate | Ruff 0.16.5, compileall, documentation inventory, exact Bandit baseline and pip-audit; 0 high findings and no known dependency vulnerabilities | Good incremental protection; whole-project type checking remains absent. |
| Validated build toolchain | pip 26.2.1, coverage 7.16.0, PyInstaller 6.22.2 and `pyinstaller-hooks-contrib` 2026.7 on Windows/Python 3.14.5 | Current source floors and local environment are aligned; portable bundles still require a separate final build and audit. |
| Validated UI/astronomy runtime | PySide6/Qt/shiboken6 6.11.2, Skyfield 1.55, Astropy 8.0.1, current IERS data and NumPy 2.5.2 | Focused astronomy/timezone tests, QML smoke modes and all-file `qmllint` pass without changing application or QML source. |
| Validated Earthdata runtime | earthaccess 0.18.0, s3fs/fsspec 2026.7.0, aiobotocore 3.9.0 and botocore 1.43.56 | The provider transport closure resolves together, imports on Python 3.14.5, passes the NASA AOD suite, and is protected against partial requirement updates. |
| Runtime gate | Backend plus normal and red QML smoke tests in disposable runtimes | Strong protection of construction and UI loading paths. |

## What Changed In 1.45.x

### Composition and application workflows

`astro_viewer.app.application.dependencies` now constructs repositories,
providers, services, the astronomy engine, and the fallback policy. The entry
point injects one `AppControllerDependencies` object. Direct controller
construction remains available through a compatibility factory, which limits
migration risk without duplicating normal startup composition.

`CatalogueRecommendationWorkflow` owns the synchronous preparation of
equipment enrichment, condition read models, NSOM ranking, Best Object, night
plan, and Sky Compass candidates. Immutable snapshots cross the worker/Qt
boundary. The controller retains scheduling, request generations, cancellation
semantics, stale-result rejection, state swaps, and signals.

`LocationCommandWorkflow` now owns location search, city/MPC/manual selection,
system and online provider commands, startup fallback, recent-location
deduplication, validation and result messages. Explicit immutable outcomes cross
the boundary. The controller retains Qt slots, request cancellation and stale
result rejection, persistence timing, dependent refreshes, state application
and signal publication.

### Presentation and catalogue boundaries

Observing/session explanations, weather windows, night-time parsing, catalogue
record normalization, designation search, filtering, detail construction,
equipment form parsing, profile inventory queries, and equipment read models
now live in framework-independent modules. These services receive explicit
data or repositories and are testable without constructing QObject state.

### Dependency structure

Condition DTOs moved to `models`; equipment configuration depends on a narrow
protocol and shared target-neutral optical calculations. The former aerosol,
equipment-builder, and bootstrap/entry-point cycles were removed. The AST gate
now checks both cycles and these protected outer boundaries:

```text
main.py
   |
   v
application composition root
   |
   +------> repositories/providers
   +------> domain and presentation services
   +------> astronomy engine
   |
   v
AppController <------ QML
   |
   v
application workflows and services publish immutable/read-model results
```

Models, database, astronomy, and services may not import `viewmodels` or
`application`. The code deliberately does not claim stricter clean-architecture
rules that it does not yet meet: localization helpers remain cross-cutting, and
some services depend directly on concrete repositories.

### Quality gates

The standard runner checks code-documentation coverage, architecture, and Bandit
before the long test suite. The documentation inventory recursively covers all
Python and QML sources plus governed automation/configuration families; it
checks structure mechanically while review remains responsible for truthfulness.
Bandit's 51 existing findings are not globally skipped: each exact code context
is recorded with a review rationale, any change reopens review, and high
severity cannot be baselined. Unexpected pytest warnings fail. This policy
immediately exposed one SQLite test connection that the older warning summary
did not reveal; it was closed explicitly.

CI reuses the local runner on Windows/Python 3.14 and Linux/Python 3.12, with a
separate Python 3.14 dependency audit. This reduces divergence between local and
remote validation. A checked workflow definition is not itself evidence of a
remote CI pass.

## Organization By Area

| Concern | Current owner | Review |
| --- | --- | --- |
| Object identities and persistence | `CatalogueRepository`, designation seed data | Strong: physical identity is separate from catalogue aliases. |
| Recommendation decisions | NSOM/equipment/planner services plus application workflow | Strong: decisions remain in Python and are covered by matrix tests. |
| Qt state and concurrency | `AppController` | Correct boundary, excessive surface area. |
| Runtime composition | `application.dependencies` | Strong: one normal construction path with explicit compatibility fallback. |
| Equipment persistence | `EquipmentCatalogRepository` | Functionally strong, structurally concentrated. |
| Database migration/seeding | `database.bootstrap` | Deterministic and tested, but large and multi-purpose. |
| Astronomy/provider implementation | astronomy and provider services | Good isolation at package level; several individual modules remain large. |
| UI decisions | Python read models; QML visual rendering | Direction is good; largest pages still contain substantial local presentation structure. |
| Localization | Qt catalogues plus structured JSON overlays | Mature multilingual mechanism, but the helper module cuts across nominal layers. |
| Documentation | governed source headers, living documents, immutable archive | Every hand-written source family is covered and the inventory is mechanically enforced. |

## Residual Risks And Priorities

### Completed focus: controller and location/provider orchestration

At 7,814 physical lines and 561 methods, `AppController` is still expensive to
understand and easy to touch accidentally. Its remaining responsibilities are
not all misplaced: Qt properties, slots, signals, timers, thread handoff, and
compatibility adapters belong at this boundary. Future extraction should target
other coherent commands still mixing mutation and presentation, such as
calendar-event projection and observation-log operations.

`1.45.17` separates the former 1,461-line location module into a 1,147-line
infrastructure adapter module and a 472-line selection/normalization service.
The composition root now constructs an explicit immutable adapter bundle;
legacy provider imports remain available through `location_service.py`.
`1.45.18` moves controller-facing search, selection, validation, provider
commands, startup fallback, result copy and recent-location policy into a
445-line framework-independent workflow with explicit inputs and immutable
results. The controller no longer reaches directly into the location repository
or service. Its Qt signal timing, asynchronous request generations, provider
errors, persistence and cache precedence remain covered by focused tests.

Do not split the file mechanically. Every extraction should reduce controller
state access, accept explicit inputs, preserve signal timing, and land with
focused plus full-gate evidence.

### Priority 1: persistence concentration

`EquipmentCatalogRepository` spans multiple aggregates and
`database.bootstrap` spans schema creation, migration, seed reconciliation, and
data import. The current transaction behavior is well tested, so a rewrite
would carry more risk than benefit. Split by aggregate or migration family only
when a feature requires sustained edits there, while keeping cross-equipment
transactions explicit.

### Priority 2: provider, astronomy, and presentation concentration

The 1,330-line NASA AOD provider combines network discovery, cache selection,
granule readers, quality masks, and result projection. `equipment_service.py`
(1,061), `imaging_recommendation_presentation.py` (1,064), OpenAQ (753), light
pollution (712), and calendar presentation (691) are secondary hotspots. Split
them only along stable policy/provider/read-model boundaries, with the existing
tests preserving fallback and payload behavior.

The 2,434-line Skyfield engine can separate event sources and calculation
families behind the existing astronomy protocol. Home (1,708 QML lines) and
Object Detail (1,245) should gain reusable sections only where inputs and emitted
actions can be stated independently; fragments with tightly shared visual state
should remain local.

### Priority 2: cross-cutting localization

Models, astronomy, and database code still import
`services.localization`. This is practical and currently acyclic, but it makes
the nominal service layer partly infrastructural. A future focused change can
move translation/formatting primitives to a lower neutral package and keep the
old module as a compatibility facade.

### Priority 3: static typing and lint depth

The extracted boundaries use dataclasses, `Protocol`, and `TypedDict`, but the
repository has no whole-project type-checking gate and Ruff intentionally
enforces a small rule set. Introduce stricter rules or typing one package at a
time; enabling a broad rule set in one commit would create a large mechanical
diff with weak architectural value.

## Catalogue Content Readiness

The next editorial phase has a sound technical base:

- stable physical `object_id` values and alias-aware catalogue designations;
- separate `ObjectDescription` and `ObjectCuriosity` tables;
- built-in upserts that preserve user-managed rows;
- structured Italian source content with English/Spanish overlays;
- source label, HTTPS URL, verification state, and UI link fields for facts;
- tests for uniqueness, completeness, source presence, language consistency,
  identity preservation, and separation from ranking.

The current gap is scale, not storage: 228 curated Solar System, Messier, and
Caldwell objects have complete editorial content, while 7,366 NGC-only physical
targets intentionally use `Work in progress`. Filling that gap must not turn
OpenNGC measurements into generic prose or invent historical facts. The
batching, provenance, translation, and review contract is defined in
`docs/CATALOGUE_EDITORIAL_WORKFLOW.md`.

No editorial field should enter visibility, NSOM, equipment scoring, or planner
ranking. That separation is the main architectural safeguard for the next
phase.

## Final Assessment

NightScope is well organized where correctness matters most: domain decisions,
identity, persistence rules, provider quality, and regression testing. It is
less well organized where years of UI-facing functionality accumulated in a
single controller and a few large infrastructure files. The `1.45.x` series
does not erase that history, but it creates clear seams and automated rules that
make incremental improvement safe.

Recommended status: the codebase is safe for editorial work, but architecture
still has worthwhile focused work. Continue in small reviewed versions in this
order: persistence aggregates, Skyfield event/calculation seams, remaining
controller command workflows, large QML sections, and finally a neutral home
for localization primitives. Each extraction must reduce coupling or state
reach and preserve observable contracts; line-count reduction alone is not a
success criterion.
