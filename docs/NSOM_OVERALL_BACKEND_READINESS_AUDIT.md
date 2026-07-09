# NSOM Overall Backend Readiness Audit

## Executive Summary

This developer-only audit rolls up the backend NSOM migration state after the Equipment closeout. It does not change runtime behaviour, scoring, QML, logging, network access or runtime file writes.

## Readiness Verdict

- Verdict: `overall_backend_nsom_ready_for_next_phase`.
- Backend recommendation surfaces closed: `True`.
- Equipment closed setup-local: `True`.
- Dead legacy removed: `True`.
- Runtime behaviour changed by this audit: `False`.
- Safe to start rollback cleanup policy: `True`.
- Safe to start visible UI/explanation design: `True`.
- Visible UI/explanation recommended now: `False`.
- Recommended next step: Review 1.13.7, then remove internal legacy rollback paths in a focused implementation step.
- Reason: Planner, Home recommendedDeepSky, Best Object, Advanced Observing backend, Sky Compass and Detail/Object are closed on NSOM default-on paths; Equipment is closed as a setup-local NSOM-bounded service; Sky Map and Notifications are removed dead legacy. Remaining items are internal rollback flags, payload compatibility fields and Universe/catalogue input semantics, none of which block the closed backend recommendation surfaces. The 1.13.7 rollback policy audit recommends removing the internal rollback paths next.

## Closed Backend Surfaces

| Surface | Status | NSOM role | Evidence |
| --- | --- | --- | --- |
| Planner | `default_on_closed` | ObservationOpportunity ranking | docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md |
| Home recommendedDeepSky | `default_on_closed` | ObservableTargetValue ordering | docs/HOME_NSOM_RECOMMENDED_DEEP_SKY_READINESS_AUDIT.md |
| Best Object | `default_on_closed` | Home-specific ObservationOpportunity selection | docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md |
| Advanced Observing backend | `default_on_closed_backend_only` | category ObservableTargetValue projection | docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md |
| Sky Compass | `default_on_closed` | ObservableTargetValue based direction policy | docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md |
| Detail/Object internal payload | `default_on_closed_backend_only` | separate internal Detail/Object payload | docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md |
| Equipment recommendations | `equipment_nsom_migration_closed_setup_local` | setup-local service with explicit NSOM boundaries | docs/EQUIPMENT_NSOM_MIGRATION_CLOSEOUT.md |
| ObservationConditions consumers | `observation_conditions_consumer_reroute_closed` | raw/display read-model compatibility boundary | docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md |
| Sky Map | `removed_dead_legacy` | removed dead legacy, not an NSOM migration surface | HomePage.qml consumes `controller.skyCompass`, not `controller.skyMap`.; `AppController.skyMap`, `_sky_map` storage and recomputation are absent.; `SkyMapService` has been removed. |
| Notifications | `removed_dead_legacy` | removed dead legacy, not an NSOM migration surface | No QML files consume `controller.notifications` or equivalent notification models.; AppController no longer exposes or computes a notifications property.; `NotificationService` and the `Notification` DTO are absent. |

## Remaining Non-Blocking Items

| Item | Classification | Why it remains | Recommended handling |
| --- | --- | --- | --- |
| Internal legacy rollback flags | `cleanup_policy_pending` | Planner, Home, Best Object, Advanced Observing, Sky Compass and Detail/Object still expose explicit internal rollback constructor flags. | Review the 1.13.7 policy, then remove these internal rollback paths before visible UI/explanation work. |
| Legacy/base payload compatibility fields | `presentation_compatibility` | Existing QML payloads still contain score-shaped compatibility fields even when NSOM owns ranking. | Keep until a separate UI/presentation design decides what to show. |
| ObservationConditions prepared-object cache | `observation_conditions_consumer_reroute_closed` | `ObservationConditionsService` still creates conditioned object copies for moon and light-pollution presentation/fallback paths; the 1.12.6 boundary preserves raw and display target fields separately, the 1.12.7 audit defines how consumers should reroute to raw inputs, and the 1.12.8 runtime step applies that policy to Home recommendedDeepSky. The 1.12.9 runtime step applies the same raw-score/display-payload split to Best Object. The 1.12.10 policy defines the remaining Sky Compass split, and the 1.12.11 runtime step implements it. The 1.12.12 closeout records the consumer reroute series as complete. | Keep the read-model boundary as active compatibility code; no ObservationConditions consumer reroute work remains open. |
| Catalogue / raw object score | `upstream_legacy_input` | Catalogue and engine prepared scores remain the raw target input for several compatibility payloads. | Treat as Universe/read-model work, not as a ranking hotfix. |

## Next Phase Decisions

| Decision | Priority | Status | Reason |
| --- | --- | --- | --- |
| `rollback_cleanup_policy` | `1` | `policy_set_remove_internal_rollbacks` | 6 internal rollback surfaces remain. The 1.13.7 policy audit recommends removing them before adding visible UI rationale. |
| `visible_ui_explanation_policy` | `2` | `deferred_until_backend_cleanup_policy` | Backend NSOM is ready for planning visible explanations, but score display semantics should be designed separately from this audit. |
| `payload_score_semantics` | `3` | `presentation_followup` | 5 payload compatibility surfaces still carry legacy/base score fields for QML compatibility. |
| `catalogue_universe_score_boundary` | `4` | `future_backend_audit` | Treat as Universe/read-model work, not as a ranking hotfix. |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `source_reports_present` | `True` |
| `all_default_on_backend_surfaces_closed` | `True` |
| `all_default_flags_enabled` | `True` |
| `all_rollback_paths_present` | `True` |
| `equipment_closed_setup_local` | `True` |
| `equipment_runtime_unchanged` | `True` |
| `legacy_surface_cleanup_complete` | `True` |
| `dead_legacy_removed` | `True` |
| `remaining_items_non_blocking` | `True` |
| `confidence_score_neutral` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.13.6`: Confirm the overall backend readiness audit is accurate.
- `Review 1.13.7`: Confirm rollback cleanup policy before deleting runtime branches.
- `1.13.8 Remove internal legacy rollback paths`: Remove internal rollback flags and legacy branches in a focused commit.
- `Visible UI/explanation planning`: Start only after rollback cleanup is implemented, because the backend NSOM recommendation surfaces are already closed.

## Conclusion

The backend NSOM recommendation migration is ready for the next phase. The rollback cleanup policy is now set: internal legacy rollback flags should be removed in a focused implementation step, because the application is not distributed and those branches now create more maintenance surface than product value. Visible UI/explanation work remains a separate design step.
