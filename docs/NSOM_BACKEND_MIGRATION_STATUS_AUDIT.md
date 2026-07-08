# NSOM Backend Migration Status Audit

## Executive Summary

This developer-only audit reviews the current NSOM backend migration state after the Planner, Home `recommendedDeepSky`, Best Object, Advanced Observing backend and Sky Compass default-on steps. It does not change runtime behaviour, QML, scoring, logging, network access or runtime file writes.

## Readiness Verdict

- Verdict: `backend_nsom_default_on_surfaces_closed`.
- Current default-on surfaces closed: `True`.
- Ready to start next backend area: `True`.
- Ready for visible UI redesign: `False`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next step: 1.10.0 Detail/Object NSOM comparison layer.
- Reason: Planner, Home recommendedDeepSky, Best Object, Advanced Observing backend and Sky Compass have default-on NSOM paths with explicit rollback. Remaining items are legacy or hybrid surfaces that need comparison/readiness work before any UI-facing explanation changes.

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

## Remaining Legacy Or Hybrid Surfaces

| Area | Status | Why it remains | Recommended handling |
| --- | --- | --- | --- |
| Detail / selected object | `legacy_conditioned_presentation` | `selectedObject` still projects prepared `CelestialObject` fields and applies the legacy Moon adjustment for observing-source detail. | Start with a developer-only Detail/Object NSOM comparison layer. |
| Sky Map | `legacy_display_order` | `SkyMapService` groups visible targets and sorts each direction by prepared `CelestialObject.score`. | Review after Detail because it shares the same display-score contract. |
| Equipment recommendations | `legacy_practical_setup_scoring` | `EquipmentService` still ranks eyepiece/Barlow candidates with its own practical configuration score. | Compare against ObserverCapability/Q_target before any runtime replacement. |
| ObservationConditions prepared-object cache | `hybrid_conditioned_objects` | `ObservationConditionsService` still creates conditioned object copies for moon and light-pollution presentation/fallback paths. | Defer broad cleanup until an ObservationSnapshot/read-model boundary exists. |
| Notifications | `legacy_compatible_consumer_contract` | `NotificationService` consumes legacy-compatible best object, plan and advanced-score payloads rather than NSOM explanations. | Leave stable until notification-specific NSOM semantics are defined. |
| Catalogue / raw object score | `upstream_legacy_input` | Catalogue and engine prepared scores remain the raw target input for several compatibility payloads. | Treat as Universe/read-model work, not as a ranking hotfix. |

## Documentation State

| Check | Result |
| --- | --- |
| `version` | `1.9.7` |
| `source_reports_present` | `[True, True, True, True, True]` |
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
- `1.10.0 Detail/Object NSOM comparison layer`: Compare selected-object/detail legacy conditioned score and NSOM ObservableTargetValue/PracticalTargetValue without UI changes.
- `1.10.x Detail/Object readiness and default-off path`: Only after comparison evidence, add a rollbackable default-off detail path if useful.
- `Later UI explanation work`: Expose NSOM rationale only in a dedicated UX step after backend semantics are stable.

## Conclusion

The backend NSOM migration is closed for the already migrated recommendation surfaces. The next useful backend step is a Detail/Object comparison layer, because selected-object detail still projects legacy conditioned `CelestialObject` score fields and explanation semantics into the UI contract.
