# NSOM Rollback Cleanup Policy Audit

## Executive Summary

This developer-only audit records the policy and closeout state for internal legacy rollback paths after the backend NSOM migration closeouts. It is not wired into runtime, QML, logging, network access or runtime file writes.

## Verdict

- Verdict: `rollback_cleanup_implemented_internal_rollbacks_removed`.
- Rollback cleanup recommended: `False`.
- Rollback cleanup implemented: `True`.
- Safe to implement cleanup next: `False`.
- Runtime behaviour changed by this audit: `False`.
- Public compatibility required: `False`.
- Recommended next step: Review 1.13.8, then proceed to visible explanation planning or Universe/catalogue policy work.
- Reason: All remaining rollback paths are internal constructor/service flags, the app is not distributed, and the default-on NSOM backend surfaces are closed. 1.13.8 removed those runtime rollback paths; Git history is the rollback mechanism for a reviewed revert.

## Rollback Surfaces

| Surface | Default flag | Rollback | Recommendation | Reason |
| --- | --- | --- | --- | --- |
| Planner | `NSOM_PLANNER_SCORING_ENABLED = True` | `removed: NightPlannerService(use_nsom_planner_scoring=False)` | `removed_internal_rollback` | The NSOM default path is closed and this internal rollback constructor path was removed by 1.13.8. |
| Home recommendedDeepSky | `NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED = True` | `removed: AppController(use_nsom_home_recommended_deep_sky=False)` | `removed_internal_rollback` | The NSOM default path is closed and this internal rollback constructor path was removed by 1.13.8. |
| Best Object | `NSOM_BEST_OBJECT_ENABLED = True` | `removed: AppController(use_nsom_best_object=False)` | `removed_internal_rollback` | The NSOM default path is closed and this internal rollback constructor path was removed by 1.13.8. |
| Advanced Observing backend | `NSOM_ADVANCED_OBSERVING_ENABLED = True` | `removed: AppController(use_nsom_advanced_observing=False)` | `removed_internal_rollback` | The NSOM default path is closed and this internal rollback constructor path was removed by 1.13.8. |
| Sky Compass | `NSOM_SKY_COMPASS_ENABLED = True` | `removed: AppController(use_nsom_sky_compass=False)` | `removed_internal_rollback` | The NSOM default path is closed and this internal rollback constructor path was removed by 1.13.8. |
| Detail/Object internal payload | `NSOM_DETAIL_OBJECT_ENABLED = True` | `removed: AppController(use_nsom_detail_object=False)` | `removed_internal_rollback` | The NSOM default path is closed and this internal rollback constructor path was removed by 1.13.8. |

## Policy Decisions

| Decision | Status | Blocks cleanup | Reason |
| --- | --- | --- | --- |
| `remove_internal_rollback_flags` | `implemented_in_1_13_8` | `False` | 6 internal rollback surfaces are recorded as removed. The runtime constructors no longer expose those rollback parameters. |
| `public_compatibility_exception` | `not_required` | `False` | The legacy audit marks every rollback as internal and the app is not distributed, so no public compatibility exception is required. |
| `visible_ui_explanation_dependency` | `cleanup_completed_before_ui_explanation` | `False` | Rollback cleanup is complete before visible UI/explanation work. |
| `runtime_change_policy` | `implemented_by_followup` | `False` | The original audit recorded policy only; 1.13.8 performed the runtime constructor and branch cleanup. |

## Implementation Plan

| Phase | Scope | Runtime change allowed by this audit | Validation |
| --- | --- | --- | --- |
| `1.13.8` | Completed removal of rollback constructor parameters and runtime legacy branches for: Planner, Home recommendedDeepSky, Best Object, Advanced Observing backend, Sky Compass, Detail/Object internal payload. | `False` | Focused runtime tests must prove default paths, payload shapes and QML-visible data remain stable. |
| `post-cleanup-review` | Review removed branches and remaining payload compatibility fields. | `False` | Run compileall, focused NSOM/default path tests and full pytest if shared runtime changes are broad. |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `source_reports_present` | `True` |
| `overall_backend_ready` | `True` |
| `legacy_cleanup_complete` | `True` |
| `rollback_surfaces_recorded` | `True` |
| `all_rollback_surfaces_internal` | `True` |
| `all_rollback_parameters_removed_after_cleanup` | `True` |
| `all_rollback_surfaces_recommended_for_removal` | `True` |
| `policy_blocks_no_cleanup` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.13.7`: Confirm rollback cleanup policy before deleting any runtime branches.
- `1.13.8 Remove internal legacy rollback paths`: Remove constructor rollback flags and dead legacy branches in a focused runtime cleanup commit with rollback via Git.
- `Review 1.13.8`: Confirm default runtime behaviour and QML payloads remain stable.

## Conclusion

The policy decision has been implemented by 1.13.8. Internal runtime rollback constructor parameters are removed; explicit developer reports can still compare legacy formulas where those formulas are available.
