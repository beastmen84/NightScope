# NSOM Rollback Cleanup Policy Audit

## Executive Summary

This developer-only audit decides the policy for remaining internal legacy rollback paths after the backend NSOM migration closeouts. It does not remove flags, change runtime behaviour, expose QML, log, access the network or write files at runtime.

## Verdict

- Verdict: `rollback_cleanup_policy_set_remove_internal_rollbacks`.
- Rollback cleanup recommended: `True`.
- Remove rollbacks in this audit: `False`.
- Safe to implement cleanup next: `True`.
- Runtime behaviour changed by this audit: `False`.
- Public compatibility required: `False`.
- Recommended next step: Review 1.13.7, then remove internal legacy rollback paths in a focused implementation step.
- Reason: All remaining rollback paths are internal constructor/service flags, the app is not distributed, and the default-on NSOM backend surfaces are closed. Keeping rollback branches now adds maintenance surface without a public compatibility requirement.

## Rollback Surfaces

| Surface | Default flag | Rollback | Recommendation | Reason |
| --- | --- | --- | --- | --- |
| Planner | `NSOM_PLANNER_SCORING_ENABLED = True` | `NightPlannerService(use_nsom_planner_scoring=False)` | `remove_internal_rollback_next` | The NSOM default path is closed and this rollback is internal, not a public compatibility contract. |
| Home recommendedDeepSky | `NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED = True` | `AppController(use_nsom_home_recommended_deep_sky=False)` | `remove_internal_rollback_next` | The NSOM default path is closed and this rollback is internal, not a public compatibility contract. |
| Best Object | `NSOM_BEST_OBJECT_ENABLED = True` | `AppController(use_nsom_best_object=False)` | `remove_internal_rollback_next` | The NSOM default path is closed and this rollback is internal, not a public compatibility contract. |
| Advanced Observing backend | `NSOM_ADVANCED_OBSERVING_ENABLED = True` | `AppController(use_nsom_advanced_observing=False)` | `remove_internal_rollback_next` | The NSOM default path is closed and this rollback is internal, not a public compatibility contract. |
| Sky Compass | `NSOM_SKY_COMPASS_ENABLED = True` | `AppController(use_nsom_sky_compass=False)` | `remove_internal_rollback_next` | The NSOM default path is closed and this rollback is internal, not a public compatibility contract. |
| Detail/Object internal payload | `NSOM_DETAIL_OBJECT_ENABLED = True` | `AppController(use_nsom_detail_object=False)` | `remove_internal_rollback_next` | The NSOM default path is closed and this rollback is internal, not a public compatibility contract. |

## Policy Decisions

| Decision | Status | Blocks cleanup | Reason |
| --- | --- | --- | --- |
| `remove_internal_rollback_flags` | `accepted_for_next_implementation` | `False` | 6 internal rollback surfaces remain and all are recommended for removal in a focused follow-up. |
| `public_compatibility_exception` | `not_required` | `False` | The legacy audit marks every rollback as internal and the app is not distributed, so no public compatibility exception is required. |
| `visible_ui_explanation_dependency` | `cleanup_before_ui_explanation` | `False` | The overall backend audit recommends settling rollback cleanup before visible UI/explanation work. |
| `runtime_change_policy` | `not_in_this_audit` | `False` | This audit records policy only. Runtime constructor and service branch removal belongs to the next implementation step. |

## Implementation Plan

| Phase | Scope | Runtime change allowed by this audit | Validation |
| --- | --- | --- | --- |
| `1.13.8` | Remove rollback constructor parameters, default flag constants and legacy branches for: Planner, Home recommendedDeepSky, Best Object, Advanced Observing backend, Sky Compass, Detail/Object internal payload. | `False` | Focused runtime tests must prove default paths, payload shapes and QML-visible data remain stable. |
| `post-cleanup-review` | Review removed branches and remaining payload compatibility fields. | `False` | Run compileall, focused NSOM/default path tests and full pytest if shared runtime changes are broad. |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `source_reports_present` | `True` |
| `overall_backend_ready` | `True` |
| `legacy_cleanup_complete` | `True` |
| `rollback_surfaces_present` | `True` |
| `all_rollback_surfaces_internal` | `True` |
| `all_rollback_parameters_present_before_cleanup` | `True` |
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

The policy decision is to remove internal legacy rollback paths in the next focused implementation step. This audit only records that decision; it deliberately leaves runtime constructors, flags and branches unchanged.
