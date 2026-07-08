# NSOM Legacy Backend Surface Audit

## Executive Summary

This developer-only audit classifies the remaining legacy backend surfaces after the default-on NSOM recommendation migrations. It does not change runtime behaviour, QML, scoring, logging, network access or runtime file writes.

## Verdict

- Verdict: `legacy_backend_surface_audit_complete`.
- Sky Map migration recommendation: `do_not_migrate_dead_legacy_surface`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next step: Review 1.11.0, then remove the dead Sky Map controller/property path in 1.11.1 if the audit is accepted.
- Reason: The QML Home page consumes Sky Compass and no longer consumes `controller.skyMap`, while the controller still computes `_sky_map`. This makes Sky Map a dead legacy runtime computation rather than a backend NSOM migration target.

## Classification Policy

- `dead_legacy`: Code still present or computed, but no longer consumed by current QML/runtime presentation.
- `temporary_rollback`: Explicit old path retained only as internal rollback after a default-on NSOM migration.
- `payload_compatibility`: Legacy/base fields still needed to keep existing QML payloads stable until a separate UI/presentation step.
- `active_legacy_or_hybrid`: Code still actively used and requiring a separate NSOM policy or read-model migration before removal.

## Dead Legacy Surfaces

| Surface | Classification | Evidence | Recommended handling |
| --- | --- | --- | --- |
| Sky Map | `dead_legacy` | HomePage.qml consumes `controller.skyCompass`, not `controller.skyMap`.<br>`AppController` still exposes `skyMap` and recomputes `_sky_map`.<br>`SkyMapService` sorts visible targets by legacy `CelestialObject.score`. | Remove the controller/property/service path after review; do not build a Sky Map NSOM migration for dead legacy code. |

## Temporary Rollback Surfaces

| Surface | Default flag | Rollback | Public compatibility contract | Recommended handling |
| --- | --- | --- | --- | --- |
| Planner | `NSOM_PLANNER_SCORING_ENABLED = True` | `NightPlannerService(use_nsom_planner_scoring=False)` | `False` | Keep only until the rollback cleanup series is explicitly accepted. |
| Home recommendedDeepSky | `NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED = True` | `AppController(use_nsom_home_recommended_deep_sky=False)` | `False` | Keep only until the rollback cleanup series is explicitly accepted. |
| Best Object | `NSOM_BEST_OBJECT_ENABLED = True` | `AppController(use_nsom_best_object=False)` | `False` | Keep only until the rollback cleanup series is explicitly accepted. |
| Advanced Observing backend | `NSOM_ADVANCED_OBSERVING_ENABLED = True` | `AppController(use_nsom_advanced_observing=False)` | `False` | Keep until Advanced Observing visible presentation policy is settled. |
| Sky Compass | `NSOM_SKY_COMPASS_ENABLED = True` | `AppController(use_nsom_sky_compass=False)` | `False` | Keep only until the rollback cleanup series is explicitly accepted. |
| Detail/Object internal payload | `NSOM_DETAIL_OBJECT_ENABLED = True` | `AppController(use_nsom_detail_object=False)` | `False` | Keep until visible Detail presentation policy is settled. |

## Payload Compatibility Surfaces

| Surface | Compatibility field | Why it remains | Ranking authority |
| --- | --- | --- | --- |
| Home recommendedDeepSky | `score` | Existing QML cards expect the field as display/base compatibility data. | NSOM or separate active service |
| Best Object | `score` | The visible Best Object payload still shows legacy/base score semantics. | NSOM or separate active service |
| Sky Compass | `target.score` | The compass payload shape is intentionally unchanged for QML. | NSOM or separate active service |
| Advanced Observing | `advancedScores` | Home cards, Planner and notifications still consume the legacy-compatible scores. | NSOM or separate active service |
| Detail/Object | `selectedObject.score` | Visible Detail QML still consumes selectedObject without NSOM fields. | NSOM or separate active service |

## Active Legacy Or Hybrid Surfaces

| Surface | Classification | Why active | Recommended handling |
| --- | --- | --- | --- |
| Equipment recommendations | `active_legacy_or_hybrid` | `EquipmentService` still computes practical setup recommendations. | Migrate through ObserverCapability/Q_target in a dedicated Equipment step. |
| ObservationConditions prepared-object cache | `active_legacy_or_hybrid` | Conditioned object copies still feed fallback and compatibility presentation paths. | Defer cleanup until an ObservationSnapshot/read-model boundary exists. |
| Notifications | `active_legacy_or_hybrid` | Notifications consume legacy-compatible best object, plan and advanced-score payloads. | Define notification-specific NSOM semantics before replacement. |
| Catalogue / raw object score | `active_legacy_or_hybrid` | Catalogue/base scores remain Universe input and display compatibility data. | Treat as Universe/read-model work, not as a ranking hotfix. |

## Safety Checks

| Check | Result |
| --- | --- |
| `sky_map_qml_consumers_absent` | `True` |
| `sky_map_controller_computation_present` | `True` |
| `sky_map_is_dead_legacy_not_nsom_target` | `True` |
| `temporary_rollbacks_are_internal` | `True` |
| `payload_compatibility_not_rank_source` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Recommended Sequence

- `Review 1.11.0`: Confirm Sky Map is dead legacy rather than a surface to migrate to NSOM.
- `1.11.1 Remove dead Sky Map legacy path`: Remove `SkyMapService`, `AppController.skyMap`, `_sky_map` storage and controller recomputation if no hidden consumer is found.
- `Rollback cleanup series`: After dead code is removed, decide whether internal legacy rollback constructor flags are still useful in an undistributed app.
- `Equipment/ObserverCapability migration`: Treat active Equipment recommendations as the next real backend NSOM area, not Sky Map.

## Conclusion

Sky Map should not receive an NSOM comparison layer unless a hidden consumer is found. The current evidence shows it is dead legacy controller work left behind after Sky Compass replaced the old Home map. The next useful step is a focused removal commit, followed by a separate decision on temporary rollback cleanup.
