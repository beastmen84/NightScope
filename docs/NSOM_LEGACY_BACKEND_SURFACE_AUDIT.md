# NSOM Legacy Backend Surface Audit

## Executive Summary

This developer-only audit classifies the remaining legacy backend surfaces after the default-on NSOM recommendation migrations. It does not change runtime behaviour, QML, scoring, logging, network access or runtime file writes.

## Verdict

- Verdict: `legacy_backend_surface_cleanup_complete`.
- Sky Map migration recommendation: `removed_dead_legacy_surface`.
- Notifications migration recommendation: `removed_dead_legacy`.
- ObservationConditions recommendation: `observation_conditions_consumer_reroute_closed`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next step: Start Equipment presenter contract review now that the ObservationConditions consumer reroute series is closed.
- Reason: The QML Home page consumes Sky Compass and no longer consumes `controller.skyMap`. The 1.11.1 cleanup removes the controller property, `_sky_map` storage, recomputation and `SkyMapService`, so Sky Map is no longer a backend migration target. Equipment now has a shared ObserverCapability/Q_target adapter while the runtime setup helper remains unchanged. The QML Home page no longer consumes notifications, and the 1.12.4 cleanup removes the controller property, runtime recomputation, `NotificationService` and DTO. ObservationConditions remains active runtime code and now has an explicit read-model boundary plus consumer reroute policy. Home recommendedDeepSky now uses the raw read-model target for NSOM ranking, and Best Object now scores raw read-model targets while returning display targets. Sky Compass now uses a raw-target/display-live-geometry split adapter. The ObservationConditions consumer reroute series is closed.

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
| Notifications | `removed_dead_legacy` | No QML files consume `controller.notifications` or equivalent notification models.<br>AppController no longer exposes or computes a notifications property.<br>`NotificationService` and the `Notification` DTO are absent. | Keep removed; do not rebuild unless a visible product requirement reintroduces notifications. |

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
| Advanced Observing | `advancedScores` | Home cards and Planner still consume the legacy-compatible scores; the old notification consumer has been removed as dead legacy. | NSOM or separate active service |
| Detail/Object | `selectedObject.score` | Visible Detail QML still consumes selectedObject without NSOM fields. | NSOM or separate active service |

## Active Legacy Or Hybrid Surfaces

| Surface | Classification | Why active | Recommended handling |
| --- | --- | --- | --- |
| Equipment recommendations | `active_legacy_or_hybrid` | `EquipmentService` still computes practical setup recommendations; `observer_capability_adapter.py` now provides shared ObserverCapability/Q_target projection while `docs/EQUIPMENT_NSOM_POLICY_READINESS.md` keeps the runtime setup helper unchanged. | Revisit Equipment presenter contract work now that the raw-target consumer migration is closed. |
| ObservationConditions prepared-object cache | `active_legacy_or_hybrid` | Conditioned object copies still feed fallback and compatibility presentation paths; the 1.12.6 boundary reports `read_model_boundary_introduced_consumer_reroute_pending` and the 1.12.7 consumer audit now reports `observation_conditions_consumer_reroute_closed`. | Keep the read-model boundary as active compatibility code; no ObservationConditions consumer reroute work remains open. |
| Catalogue / raw object score | `active_legacy_or_hybrid` | Catalogue/base scores remain Universe input and display compatibility data. | Treat as Universe/read-model work, not as a ranking hotfix. |

## Safety Checks

| Check | Result |
| --- | --- |
| `sky_map_qml_consumers_absent` | `True` |
| `sky_map_controller_computation_absent` | `True` |
| `sky_map_service_file_absent` | `True` |
| `sky_map_removed_not_nsom_target` | `True` |
| `notifications_qml_consumers_absent` | `True` |
| `notifications_not_nsom_target` | `True` |
| `notifications_removed_dead_legacy` | `True` |
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
- `Review 1.12.1`: Confirm the policy defers runtime replacement and preserves EquipmentService behaviour.
- `1.12.2 ObserverCapability adapter extraction`: Extract reusable ObserverCapability/Q_target projection without changing Equipment recommendations.
- `Review 1.12.2`: Confirm the adapter extraction preserved Equipment comparison values and runtime behaviour.
- `1.12.3 Notifications dead legacy audit`: Classify Notifications as dead legacy because no QML/Home consumer remains.
- `1.12.4 Remove dead Notifications backend path`: Confirm AppController notifications, NotificationService and leftover DTO/tests are removed.
- `1.12.5 ObservationConditions read-model audit`: Audit conditioned-object cache ownership and NSOM input risks.
- `Review 1.12.5`: Confirm the ObservationConditions audit before adding a read-model boundary.
- `1.12.6 ObservationConditions read-model boundary`: Separate raw target input from condition-adjusted display compatibility fields.
- `Review 1.12.6`: Confirm read-model fidelity before rerouting runtime consumers.
- `1.12.7 ObservationConditions consumer reroute audit`: Define raw-target consumer policy for Home, Best Object and Sky Compass.
- `1.12.8 Home recommendedDeepSky raw-target reroute`: Use raw read-model targets for Home recommendedDeepSky NSOM ranking while preserving display payload targets.
- `1.12.9 Best Object raw-target reroute`: Use raw read-model targets for Best Object NSOM scoring while returning the selected display payload target.
- `1.12.10 Sky Compass read-model reroute policy`: Define Sky Compass raw target physics vs display/live geometry ownership before runtime changes.
- `1.12.11 Sky Compass read-model reroute`: Use raw target physics for Sky Compass ObservableTargetValue while preserving display/live geometry and payload fields.

## Conclusion

Sky Map has been removed from the backend runtime surface instead of being migrated to NSOM. Notifications are removed dead legacy rather than a backend NSOM migration surface. ObservationConditions is active hybrid runtime code with a read-model boundary and a consumer reroute policy; runtime rerouting remains a separate implementation step. Equipment now has a shared ObserverCapability/Q_target adapter while runtime setup recommendations remain unchanged. Temporary rollback cleanup remains a separate policy decision.
