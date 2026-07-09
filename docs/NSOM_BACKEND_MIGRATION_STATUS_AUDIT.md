# NSOM Backend Migration Status Audit

## Executive Summary

This developer-only audit reviews the current NSOM backend migration state after the Planner, Home `recommendedDeepSky`, Best Object, Advanced Observing backend, Sky Compass and Detail/Object default-on steps. It does not change runtime behaviour, QML, scoring, logging, network access or runtime file writes.

## Readiness Verdict

- Verdict: `backend_nsom_default_on_surfaces_closed`.
- Current default-on surfaces closed: `True`.
- Ready to start next backend area: `True`.
- Ready for visible UI redesign: `False`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next step: Review the 1.12.6 ObservationConditions read-model boundary, then decide whether NSOM consumers should use the raw read-model target in a separate behaviour-reviewed step.
- Reason: Planner, Home recommendedDeepSky, Best Object, Advanced Observing backend, Sky Compass and Detail/Object have default-on NSOM paths with explicit rollback. Remaining items are non-blocking legacy or hybrid surfaces; Sky Map and Notifications have been removed as dead legacy. ObservationConditions is active hybrid runtime code and now has a read-model boundary that separates raw and display targets, while consumer rerouting remains a separate review. Equipment now has a shared ObserverCapability/Q_target adapter while runtime setup recommendations remain unchanged.

## Audit Blockers

- none

## Default-On NSOM Surfaces

| Surface | Status | Default flag | Rollback | NSOM role |
| --- | --- | --- | --- | --- |
| Planner | `default_on_closed` | `NSOM_PLANNER_SCORING_ENABLED = True` | `NightPlannerService(use_nsom_planner_scoring=False)` | ObservationOpportunity ranking |
| Home recommendedDeepSky | `default_on_closed` | `NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED = True` | `AppController(use_nsom_home_recommended_deep_sky=False)` | ObservableTargetValue ordering |
| Best Object | `default_on_closed` | `NSOM_BEST_OBJECT_ENABLED = True` | `AppController(use_nsom_best_object=False)` | Home-specific ObservationOpportunity selection |
| Advanced Observing backend | `default_on_closed_backend_only` | `NSOM_ADVANCED_OBSERVING_ENABLED = True` | `AppController(use_nsom_advanced_observing=False)` | category ObservableTargetValue projection |
| Sky Compass | `default_on_closed` | `NSOM_SKY_COMPASS_ENABLED = True` | `AppController(use_nsom_sky_compass=False)` | ObservableTargetValue based direction policy |
| Detail/Object internal payload | `default_on_closed_backend_only` | `NSOM_DETAIL_OBJECT_ENABLED = True` | `AppController(use_nsom_detail_object=False)` | separate internal Detail/Object payload |

## Remaining Legacy Or Hybrid Surfaces

| Area | Status | Why it remains | Recommended handling |
| --- | --- | --- | --- |
| Equipment recommendations | `observer_adapter_extracted` | `EquipmentService` still ranks eyepiece/Barlow/binocular candidates with its own practical configuration score. `observer_capability_adapter.py` now provides shared ObserverCapability/Q_target projection while `docs/EQUIPMENT_NSOM_POLICY_READINESS.md` keeps runtime setup recommendations unchanged. | Keep deferred while the 1.12.6 ObservationConditions boundary is reviewed; revisit Equipment presenter contract work after the consumer-reroute decision is stable. |
| ObservationConditions prepared-object cache | `read_model_boundary_introduced_consumer_reroute_pending` | `ObservationConditionsService` still creates conditioned object copies for moon and light-pollution presentation/fallback paths; the 1.12.6 boundary now preserves raw and display target fields separately before any consumer reroute. | Review `docs/OBSERVATION_CONDITIONS_READ_MODEL_AUDIT.md`, then decide whether Home, Best Object and Sky Compass NSOM consumers should read raw read-model targets. |
| Catalogue / raw object score | `upstream_legacy_input` | Catalogue and engine prepared scores remain the raw target input for several compatibility payloads. | Treat as Universe/read-model work, not as a ranking hotfix. |

## Removed Dead Legacy

- Notifications classification: `removed_dead_legacy`.
- Notifications controller runtime present: `False`.
- Notifications service file present: `False`.
- Notifications model DTO present: `False`.

## ObservationConditions Audit

- Verdict: `read_model_boundary_introduced_consumer_reroute_pending`.
- Runtime migration recommended now: `False`.
- Safe to remove service: `False`.
- Recommended next step: Review the 1.12.6 boundary, then decide whether NSOM Home, Best Object and Sky Compass consumers can read raw read-model targets without changing presentation payloads unexpectedly.

## Documentation State

| Check | Result |
| --- | --- |
| `version` | `1.12.6` |
| `source_reports_present` | `[True, True, True, True, True, True, True, True, True, True, True, True]` |
| `base_docs_expected_to_be_updated_with_this_audit` | `True` |
| `report_path` | `docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md` |

## Safety Checks

| Check | Result |
| --- | --- |
| `developer_only` | `True` |
| `runtime_writes` | `False` |
| `automatic_logging` | `False` |
| `network` | `False` |
| `qml_exposure` | `False` |
| `runtime_report_imports_absent` | `True` |
| `qml_audit_exposure_absent` | `True` |
| `runtime_behaviour_changed_by_this_audit` | `False` |

## Recommended Sequence

- `Review 1.9.7`: Verify this backend status audit before opening a new migration area.
- `Review 1.10.6`: Verify Detail/Object NSOM migration closeout documentation.
- `1.11.0 Legacy backend surface audit`: Classify remaining legacy paths as dead code, temporary rollback or payload compatibility.
- `Review 1.11.1`: Confirm the Sky Map controller/property/service path is removed cleanly.
- `1.12.0 Equipment/ObserverCapability NSOM comparison`: Start the next active backend NSOM area with Equipment recommendation comparison.
- `Review 1.12.0`: Confirm the comparison report is accurate and no runtime Equipment behaviour changed.
- `1.12.1 Equipment NSOM policy readiness`: Decide whether Equipment should get a default-off NSOM path or stay a practical setup helper.
- `Review 1.12.1`: Confirm the Equipment policy decision defers runtime replacement and preserves behaviour.
- `1.12.2 ObserverCapability adapter extraction`: Extract a shared ObserverCapability/Q_target adapter while leaving EquipmentService runtime output unchanged.
- `Review 1.12.2`: Confirm adapter extraction preserved Equipment comparison values and runtime output.
- `1.12.3 Notifications dead legacy audit`: Classify Notifications as dead legacy because no QML/Home consumer remains.
- `1.12.4 Remove dead Notifications backend path`: Confirm AppController notifications, NotificationService and leftover DTO/tests are removed.
- `1.12.5 ObservationConditions read-model audit`: Audit conditioned-object cache ownership and NSOM input risks.
- `Review 1.12.5`: Confirm the audit before adding a read-model boundary.
- `1.12.6 ObservationConditions read-model boundary`: Separate raw target input from condition-adjusted display compatibility fields.
- `Later UI explanation work`: Expose NSOM rationale only in a dedicated UX step after backend semantics are stable.

## Conclusion

The backend NSOM migration is closed for the already migrated recommendation surfaces and Detail/Object. Sky Map has been removed as dead legacy rather than migrated to NSOM. Notifications are now removed dead legacy, not an NSOM migration surface. ObservationConditions is active hybrid runtime code and now has an internal read-model boundary separating raw and display target data; consumer rerouting remains a separate reviewed behaviour step. Equipment now has a shared ObserverCapability/Q_target adapter while runtime setup recommendations remain unchanged. Visible UI explanation work remains separate.
