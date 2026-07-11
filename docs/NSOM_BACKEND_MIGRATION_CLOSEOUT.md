# NSOM Backend Closeout

Status: complete for NightScope `1.21.0`.

This document is the current backend status, not a migration plan. NSOM has one
production path. There are no runtime migration flags, shadow QML payloads or
legacy ranking implementations.

## Canonical Model

The runtime composition is:

1. Universe: `IntrinsicTargetQuality` from catalogue/astronomy data. The
   internal `CelestialObject.intrinsic_score` is independent from current
   altitude, visibility and provider conditions.
2. Sky: `NsomObservationEnvironmentService` composes geometric visibility,
   target-specific Moon background, VIIRS/Bortle sky background,
   seeing/transparency, AOD/OpenAQ and horizon context.
3. Observer: target-specific equipment becomes `ObserverCapability` and
   `PracticalTargetValue`.
4. Session: weather policy is binary usable/blocked. Weather already contributes
   to the Sky layer and is not multiplied again as a continuous Session score.
5. Opportunity: Planner and Best Object add timing and practical constraints.
6. Confidence: provider availability and freshness remain metadata; confidence
   does not scale recommendation scores.

Target classification is shared by all consumers through `nsom_target.py`,
including planets, Moon, galaxies, diffuse/planetary nebulae, open/globular
clusters and double stars.

## Runtime Consumers

| Consumer | Ranking/input owner | Visible contract |
| --- | --- | --- |
| Upper Home categories | `NsomCategoryScoreService` | descriptive planetary/deep-sky summaries |
| Home recommended deep sky | `HomeRecommendedDeepSkyNsomRankingService` | existing object cards and display fields |
| Best Object | `BestObjectNsomSelectionService` | existing `bestObjectOfNight` object payload |
| Planner | `NightPlannerService` plus `PlannerNsomScoringService` | four best opportunities, then chronological order |
| Sky Compass | `SkyCompassService` | existing direction/target payload |
| Observing detail | `ObservingObjectDetailService` | score-free detail read model |
| Catalogue detail | catalogue/astronomy presentation path | current-month local visibility, no NSOM ranking panel |

Home, Planner, Best Object and Sky Compass use the same primitive condition
inputs. Provider completion recomputes these consumers without repeating local
astronomy or Moon-geometry calculations.

## Condition Ownership

- VIIRS/Bortle affects static sky background.
- Forecast seeing and atmospheric transparency affect the weather-derived
  atmospheric component.
- AOD is the primary aerosol-column input when its quality policy accepts it.
- OpenAQ particulate is a non-additive fallback/context input.
- Moon illumination is combined with target-window altitude and angular
  separation.
- Target-specific equipment is applied only in the Observer layer.
- AOD/OpenAQ never mutates `CelestialObject.score`.

Missing optional providers produce neutral factors and lower confidence. They
do not select another ranking implementation.

## Retired Migration Surfaces

The `1.21.0` cleanup removed:

- `PlannerScoringService` and Planner formula rollback APIs;
- the separate `SkyCompassNsomDirectionService`;
- Advanced Observing shadow services and `advancedObservingNsom`;
- Detail/Object shadow payload generation;
- automatic `NsomDiagnosticSnapshot` refresh/export wiring;
- aerosol and Moon-geometry feature flags;
- `ObservingScoreService.best_object()`;
- obsolete comparison/characterization tests tied to retired paths;
- unused `ObjectRow.qml`.

The remaining `nsom_to_json_compatible()` and diagnostic notes support explicit
read-model/explanation data. They do not write files, emit signals or expose a
second runtime recommendation path.

## Fallback Policy

Fallbacks are data/runtime safety boundaries only:

- missing ephemeris can use `MockAstronomyEngine` to keep the application open;
- missing provider data is neutral in the canonical environment;
- Sky Compass catches an unexpected canonical-ranking exception and returns a
  geometry-only payload with the same QML shape;
- cached provider data follows each provider's freshness policy.

There is no configurable NSOM rollback.

## UI Boundary

QML does not receive raw `ObservableTargetValue`, `PracticalTargetValue`,
`ObservationOpportunity` or `RecommendationConfidence` objects. Existing
display `score` fields remain presentation compatibility data and are not a
complete explanation of ranking order.

Any future visible explanation work must define a stable presentation contract
for factors, confidence and limiting conditions before adding QML panels.

## Validation

Closeout validation on Windows/Python 3.14 uses:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ruff check astro_viewer
.\.venv\Scripts\python.exe -m compileall -q astro_viewer
.\.venv\Scripts\python.exe -m pytest -n auto -q
```

The `1.21.0` implementation suite completed with `610 passed` and `7 subtests
passed`. Skyfield currently emits upstream NumPy dtype deprecation warnings;
they are not test failures.
