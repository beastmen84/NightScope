# Detail/Object NSOM Runtime Path

## Status

NightScope 1.10.3 adds the first Detail/Object NSOM runtime path as an internal
default-off backend path.

- Feature flag: `NSOM_DETAIL_OBJECT_ENABLED = False`.
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

## Next Step

Review 1.10.3, then run a Detail/Object default-on readiness audit before
changing the default flag.
