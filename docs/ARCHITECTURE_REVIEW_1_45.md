# NightScope 1.45 Architecture Review

Date: 2026-09-02
Scope: source `1.44.0` through `1.45.7`

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
warning, and architectural regressions before pytest.

This is a good stopping point for the architectural series. Further extraction
should be driven by a concrete change area, not by line count alone.

## Evidence Snapshot

Measurements are physical source lines from the working tree unless otherwise
stated.

| Area | Evidence | Assessment |
| --- | --- | --- |
| Production Python | 121 modules, 46,585 lines | Broad domain surface, but responsibilities are discoverable by package and service names. |
| Tests | 86 test files, 34,963 lines; 1,168 tests at the 1.45.7 gate | Very strong regression protection relative to production size. |
| `AppController` | 9,836 lines at 1.44.0; 7,908 at 1.45.6/1.45.7; 1,928 lines removed (19.6%) | Still the largest risk, but now more clearly a Qt orchestration boundary. |
| Controller surface | 562 methods, including 114 slots and 141 properties | Large compatibility/API surface makes wholesale rewriting risky. |
| Largest persistence modules | `equipment_catalog_repository.py` 3,025 lines; `bootstrap.py` 2,490 | Transactionally cohesive but too concentrated for easy local reasoning. |
| Astronomy implementation | `skyfield_engine.py` 2,432 lines | Complex by domain necessity; provider/event subcomponents can still be separated. |
| Largest QML pages | Home 1,705 lines; Object Detail 1,242 | Backend decisions are mostly extracted, but layout/component complexity remains. |
| Import structure | 0 cycles; 0 protected-layer violations | Good and now mechanically enforced. |
| Static/security gate | Ruff, compileall, exact Bandit baseline; 0 high findings | Good incremental protection; whole-project type checking remains absent. |
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

The standard runner checks architecture and Bandit before the long test suite.
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
| Documentation | living documents plus immutable archive | Consolidated in 1.45.7; historical evidence no longer dominates operational guidance. |

## Residual Risks And Priorities

### Priority 1: controller concentration

At 7,908 physical lines and 562 methods, `AppController` is still expensive to
understand and easy to touch accidentally. Its remaining responsibilities are
not all misplaced: Qt properties, slots, signals, timers, thread handoff, and
compatibility adapters belong at this boundary. Future extraction should target
coherent use cases still mixing mutation and presentation, such as location/
provider orchestration, calendar-event projection, or observation-log commands.

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

### Priority 2: large provider and QML modules

The Skyfield engine, location service, NASA provider, Home page, and Object
Detail page remain large. Event-source adapters and platform location providers
are natural Python seams. Reusable QML sections should become components when
they have a stable input contract; visual fragments with tightly shared state
should remain local until that contract exists.

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

Recommended status: proceed to catalogue editorial work in small reviewed
versions. Continue architectural extraction only when that work reveals a
specific bottleneck; do not reopen broad refactoring before content work.
