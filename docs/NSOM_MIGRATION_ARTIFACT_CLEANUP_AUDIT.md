# NSOM Migration Artifact Cleanup Audit

Version: `1.15.1`

Cleanup applied: `1.15.2`

## Verdict

The backend NSOM migration is closed for the current recommendation surfaces, so
the historical migration evidence can be reduced. The repository should keep the
runtime NSOM code, behavioural regression tests and base architecture/model
documentation, while removing one-off migration reports, report generators and
tests that only validate those historical reports.

This audit does not change runtime behaviour, scoring, QML, logging, provider
access or file-writing behaviour.

## Keep

Keep these as current project state:

- Runtime NSOM model and adapters:
  - `astro_viewer/app/models/nsom.py`
  - `astro_viewer/app/services/nsom_diagnostic_adapters.py`
  - runtime NSOM services used by `AppController`, Planner, Home, Best Object,
    Advanced Observing, Sky Compass, Detail/Object and ObservationConditions.
- Runtime read-model and ownership boundaries:
  - `observation_conditions_read_model.py`
  - `equipment_setup_read_model.py`
  - `equipment_setup_score_read_model.py`
  - `observer_capability_adapter.py`
- Behavioural tests for active runtime paths:
  - NSOM DTO immutability and JSON compatibility;
  - Planner/Home/Best Object/Sky Compass/Detail runtime ranking;
  - Advanced Observing internal runtime payload;
  - ObservationConditions AOD/OpenAQ behaviour;
  - Equipment setup/read-model boundaries.
- Base documentation:
  - `README.md`
  - `astro_viewer/CHANGELOG.md`
  - `VERSION`
  - `docs/ARCHITECTURE.md`
  - `docs/CALCULATION_LOGIC.md`
  - `docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md`
  - `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md`
  - `docs/NEXT_CHAT_HANDOFF.md` while the chat handoff is useful.

## Remove In 1.15.2

Remove closed migration artifacts that are no longer the source of truth:

- Historical report Markdown files under `docs/` with prefixes such as
  `NSOM_*_AUDIT`, `NSOM_*_REPORT`, `HOME_NSOM_*`, `BEST_OBJECT_NSOM_*`,
  `ADVANCED_OBSERVING_NSOM_*`, `SKY_COMPASS_NSOM_*`, `DETAIL_OBJECT_NSOM_*`,
  `EQUIPMENT_NSOM_*`, `OBSERVATION_CONDITIONS_*`, `NOTIFICATIONS_*`,
  `SKY_COMPASS_READ_MODEL_*` and `HOME_REFRESH_*`.
- Developer-only report/audit generators under `astro_viewer/tools/` matching
  the same migration families.
- Tests whose only purpose is validating those report generators or historical
  report files.
- Developer-only comparison/calibration services that are not imported by
  runtime code and only exist to feed deleted reports.

## Do Not Remove

- Provider implementations, cache code, repositories or runtime services.
- QML/UI files.
- Runtime NSOM flags and service integrations.
- Active behavioural tests that prove current default-on NSOM behaviour.
- The real-provider probe should not be executed during cleanup. It may be
  removed as historical tooling, but cleanup must not make network calls.

## Base Documentation Policy

After 1.15.2, base documentation should stop acting like a full migration
journal. It should describe the current architecture and link only to live
reference documents. The detailed step-by-step migration remains available in
Git history instead of being duplicated across dozens of checked-in reports.

## Cleanup Safety Checks

Before committing 1.15.2:

- `python -m compileall astro_viewer`
- focused runtime NSOM tests
- full pytest with `-n auto` if collection changes are broad
- `rg` check for references to deleted report paths

## 1.15.2 Result

The cleanup removes the historical migration reports, report generators,
report-only tests and unused developer-only comparison/calibration services.
The active source of truth is now the runtime NSOM code, behavioural regression
tests and base documentation. No runtime scoring, QML/UI, provider calls,
logging or runtime file writes are changed by the cleanup.
