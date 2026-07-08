# Detail/Object NSOM Migration Closeout

## Status

NightScope 1.10.6 closes the backend Detail/Object NSOM migration.

The internal Detail/Object NSOM path is default-on:

- flag: `NSOM_DETAIL_OBJECT_ENABLED = True`;
- rollback: `AppController(use_nsom_detail_object=False)`;
- runtime service: `astro_viewer/app/services/detail_nsom_runtime.py`;
- internal controller entry point: `_selected_object_nsom_payload()`.

## Runtime Contract

The migration is backend-only. It does not change the visible Detail page QML
contract.

`selectedObject` remains the compatibility payload consumed by QML:

- observing-source Detail keeps the moon-adjusted legacy/base display score;
- catalogue Detail keeps the raw catalogue display score;
- no NSOM fields are added to `selectedObject`;
- no `detailObjectNsom` QML property is exposed.

The separate internal Detail/Object NSOM payload can be built by the backend and
contains:

- `IntrinsicTargetQuality`;
- `ObservationEnvironment`;
- `EffectiveObservability`;
- `ObservableTargetValue`;
- `PracticalTargetValue`;
- `SessionViability`;
- `RecommendationConfidence`.

`SessionViability` and `RecommendationConfidence` remain metadata-only for the
Detail/Object path. `ObservationOpportunity` is intentionally not used for
Detail/Object.

## Safety

The closeout does not introduce:

- QML/UI changes;
- report runtime wiring;
- automatic logging;
- network calls;
- runtime file writes;
- Home changes;
- Best Object changes;
- Planner changes;
- Sky Compass changes.

## Remaining Non-Blocking Items

The visible Detail page still shows legacy/base compatibility score semantics.
That is intentional for this backend migration. Any visible NSOM explanation,
score rationale or UI copy should be handled in a separate UI/design step.

After the 1.11.0 legacy backend surface audit, Sky Map is no longer treated as
the next backend NSOM area. It is classified as dead legacy controller work:
Home QML consumes Sky Compass, not `controller.skyMap`, while the controller
still computes `_sky_map`. The next step is a focused removal commit after
review, not a Sky Map NSOM comparison layer.
