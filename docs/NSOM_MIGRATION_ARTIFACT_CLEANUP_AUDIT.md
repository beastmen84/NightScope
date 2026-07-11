# NSOM Migration Artifact Cleanup Audit

Audit date: 2026-07-11
Result: complete in source `1.21.0`.

## Scope

The audit checked production Python, QML, active tests and current documents for
parallel ranking paths, migration flags, automatic diagnostics, shadow payloads
and unused UI components.

## Removed

- Advanced Observing legacy/shadow services and tests.
- Detail/Object NSOM shadow runtime and tests.
- Planner legacy scorer and comparison/characterization tests.
- Separate Sky Compass NSOM ranking service.
- `NsomDiagnosticSnapshot`, target snapshot models and automatic controller
  refresh/export wiring.
- AOD/OpenAQ and Moon-geometry feature flags.
- Redundant Best Object fallback scorer.
- Obsolete controller Qt properties/state for shadow data.
- Unused `ObjectRow.qml`.

## Retained Intentionally

- Display `score` fields required by the current QML contract. NSOM ranking uses
  raw intrinsic inputs and does not treat these fields as a full explanation.
- Display-only Moon/light-pollution conditioning used by existing cards and
  detail copy. Internal condition flags prevent double application and are not
  exported to QML.
- Explicit JSON conversion and diagnostic notes used by active read models and
  developer-invoked explanation helpers. There is no automatic file output.
- Provider and astronomy fallbacks required when external data or ephemerides
  are unavailable.

## Static Checks

No production references remain to:

- `PlannerScoringService`;
- `SkyCompassNsomDirectionService`;
- `advancedObservingNsom`;
- Detail NSOM shadow payload services;
- `ObservationConditionFeatureFlags`;
- `NsomDiagnosticSnapshot` or `NsomTargetDiagnostic`;
- configurable `use_nsom_*` constructor parameters.

## Behavioral Checks

- Planner chooses the four highest NSOM opportunities and then presents them
  chronologically.
- Active target windows schedule at the current time, never at the interval end.
- Home, Best Object and Sky Compass keep canonical ranking active when optional
  sky/provider data is missing.
- Target-specific telescope selection and Moon geometry reach all relevant
  NSOM consumers.
- AOD/OpenAQ affects atmospheric transparency once and never mutates the base
  object score.
- QML payload shapes remain unchanged and do not expose internal NSOM models.

## Verification

The full parallel suite passes with `610 passed` and `7 subtests passed`.
`ruff`, `compileall` and `pip check` are part of the release validation ladder.
