# Detail/Object NSOM Runtime Path

## Status

NightScope 1.10.3 added the first Detail/Object NSOM runtime path as an
internal default-off backend path. NightScope 1.10.5 enables that internal path
by default.

- Feature flag: `NSOM_DETAIL_OBJECT_ENABLED = True`.
- Rollback path: `AppController(use_nsom_detail_object=False)`.
- Runtime service: `astro_viewer/app/services/detail_nsom_runtime.py`.
- Controller entry point: `_selected_object_nsom_payload()`.

## Payload Policy

The path builds a separate internal `detailObjectNsom` payload. It does not add
fields to `selectedObject`, does not add a QML property and does not change the
existing Detail page payload shape.

`selectedObject.score` remains legacy/base compatibility data:

- observing-source Detail keeps the current moon-adjusted compatibility display
  score;
- catalogue Detail keeps the raw catalogue compatibility display score.

## NSOM Ownership

The internal payload contains:

- `IntrinsicTargetQuality`;
- `ObservationEnvironment`;
- `EffectiveObservability`;
- `ObservableTargetValue`;
- `PracticalTargetValue`;
- `SessionViability`;
- `RecommendationConfidence`.

`SessionViability` is Detail metadata only. `RecommendationConfidence` is
metadata only. Neither modifies `ObservableTargetValue`,
`PracticalTargetValue` or `selectedObject`.

`ObservationOpportunity` is intentionally not used for Detail/Object.

## Runtime Safety

The path is internal only and default-off. It does not change:

- QML/UI;
- `selectedObject`;
- Home;
- Best Object;
- Planner;
- Sky Compass;
- logging;
- network access;
- runtime file writes.

## Closeout

NightScope 1.10.4 adds
`docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md` and classifies this
path as ready for a separate default-on switch. NightScope 1.10.5 performs that
switch. NightScope 1.10.6 closes the backend migration in
`docs/DETAIL_OBJECT_NSOM_MIGRATION_CLOSEOUT.md`.

NightScope 1.11.0 supersedes the earlier Sky Map follow-up recommendation with
`docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md`: Sky Map is classified as dead
legacy controller work, not as an NSOM migration target. NightScope 1.11.1
removes that path from the backend controller and service layer. Visible Detail
page NSOM explanations remain separate UI/design work.
