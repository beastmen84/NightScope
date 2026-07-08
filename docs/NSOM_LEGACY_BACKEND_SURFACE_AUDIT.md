# NSOM Legacy Backend Surface Audit

## Executive Summary

This developer-only audit classifies the remaining legacy backend surfaces after the default-on NSOM recommendation migrations. It does not change runtime behaviour, QML, scoring, logging, network access or runtime file writes.

## Verdict

- Verdict: `legacy_backend_surface_cleanup_complete`.
- Sky Map migration recommendation: `removed_dead_legacy_surface`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next step: Review 1.12.0, then decide Equipment NSOM policy readiness.
- Reason: The QML Home page consumes Sky Compass and no longer consumes `controller.skyMap`. The 1.11.1 cleanup removes the controller property, `_sky_map` storage, recomputation and `SkyMapService`, so Sky Map is no longer a backend migration target. Equipment now has a developer-only ObserverCapability/Q_target comparison report.

## Classification Policy

- `removed_dead_legacy`: Formerly computed legacy code whose current QML/runtime consumer is absent and whose controller/service path has been removed.
- `dead_legacy`: Code still present or computed, but no longer consumed by current QML/runtime presentation.
- `temporary_rollback`: Explicit old path retained only as internal rollback after a default-on NSOM migration.
- `payload_compatibility`: Legacy/base fields still needed to keep existing QML payloads stable until a separate UI/presentation step.
- `active_legacy_or_hybrid`: Code still actively used and requiring a separate NSOM policy or read-model migration before removal.

## Removed Dead Legacy Surfaces

| Surface | Classification | Evidence | Recommended handling |
| --- | --- | --- | --- |
| Sky Map | `removed_dead_legacy` | HomePage.qml consumes `controller.skyCompass`, not `controller.skyMap`.<br>`AppController.skyMap`, `_sky_map` storage and recomputation are absent.<br>`SkyMapService` has been removed. | Keep removed; do not rebuild a Sky Map NSOM migration unless a real consumer is reintroduced through a separate product decision. |

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
| Equipment recommendations | `active_legacy_or_hybrid` | `EquipmentService` still computes practical setup recommendations; `docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md` now compares them with ObserverCapability/Q_target. | Review ObserverCapability/Q_target evidence, then run an Equipment policy/readiness step before any runtime replacement. |
| ObservationConditions prepared-object cache | `active_legacy_or_hybrid` | Conditioned object copies still feed fallback and compatibility presentation paths. | Defer cleanup until an ObservationSnapshot/read-model boundary exists. |
| Notifications | `active_legacy_or_hybrid` | Notifications consume legacy-compatible best object, plan and advanced-score payloads. | Define notification-specific NSOM semantics before replacement. |
| Catalogue / raw object score | `active_legacy_or_hybrid` | Catalogue/base scores remain Universe input and display compatibility data. | Treat as Universe/read-model work, not as a ranking hotfix. |

## Safety Checks

| Check | Result |
| --- | --- |
| `sky_map_qml_consumers_absent` | `True` |
| `sky_map_controller_computation_absent` | `True` |
| `sky_map_service_file_absent` | `True` |
| `sky_map_removed_not_nsom_target` | `True` |
| `temporary_rollbacks_are_internal` | `True` |
| `payload_compatibility_not_rank_source` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Recommended Sequence

- `Review 1.11.1`: Confirm the Sky Map controller/property/service path is removed cleanly.
- `Rollback cleanup series`: After dead code is removed, decide whether internal legacy rollback constructor flags are still useful in an undistributed app.
- `Review 1.12.0`: Confirm the Equipment/ObserverCapability comparison report is accurate and runtime Equipment behaviour is unchanged.
- `1.12.1 Equipment NSOM policy readiness`: Decide whether Equipment gets a default-off NSOM path or stays a practical setup helper.

## Conclusion

Sky Map has been removed from the backend runtime surface instead of being migrated to NSOM. Equipment now has a developer-only ObserverCapability/Q_target comparison report; the next useful backend step is policy readiness, while temporary rollback cleanup remains a separate policy decision.
