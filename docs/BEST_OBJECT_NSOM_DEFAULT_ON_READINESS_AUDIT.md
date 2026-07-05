# Best Object NSOM Default-On Readiness Audit

## Executive Summary

This developer-only audit checks whether the existing default-off Best Object NSOM path is ready for a separate default-on switch. It does not enable `NSOM_BEST_OBJECT_ENABLED`, change Best Object ranking, expose QML fields, write runtime files, log automatically, call the network, change recommendedDeepSky, Planner or Sky Compass.

## Readiness Verdict

- Verdict: `ready_for_default_on_switch_pr`.
- Ready for default-on switch: `True`.
- Current default flag: `NSOM_BEST_OBJECT_ENABLED = False`.
- Default flag currently enabled: `False`.
- Requires separate flag change: `True`.
- Runtime behaviour changed by this audit: `False`.
- Explicit legacy rollback: `AppController(use_nsom_best_object=False)`.
- Explicit NSOM path: `AppController(use_nsom_best_object=True)`.
- Recommended switch change: `set NSOM_BEST_OBJECT_ENABLED = True`.
- Reason: The default-off runtime path, non-actionable policies, confidence neutrality, rollback path, missing-sky fallback and developer-only safety checks are ready for a separate flag switch.

## Default-On Blockers

- none

## Runtime Policy Evidence

| Policy | Evidence |
| --- | --- |
| Good session | Selected `jupiter` as `actionable_ranked_recommendation`. |
| Blocked session | Selected `None`; actionabilities `non_actionable_hard_block > non_actionable_hard_block > non_actionable_hard_block > non_actionable_hard_block`; stable order is recommendation order `False`. |
| Invisible target | `hidden_galaxy` is `non_actionable_invisible_target` and selected `False`. |
| Confidence | Low/high score parity `True`; score effect `0.0`. |
| Mutation | Runtime objects mutated `False`. |

## Blocked Session Policy

- Selected object: `None`.
- All scores zero: `True`.
- Actionability: `non_actionable_hard_block > non_actionable_hard_block > non_actionable_hard_block > non_actionable_hard_block`.
- Stable order is recommendation order: `False`.
- Diagnostic-only preserved PracticalTargetValue order: `jupiter > galaxy > diffuse_nebula > open_cluster`.
- Preserved order is recommendation order: `False`.

## Displayed Score Semantics

- Status: `accepted_non_blocking_for_default_on_switch`.
- Keep legacy/base displayed score: `True`.
- Score monotonic with NSOM order: `False`.
- Blocks default-on switch: `False`.
- Decision: Keep the existing QML payload and base/legacy score field for the switch. The displayed score is compatibility data and is not the NSOM rationale.
- Future UI work: Add explicit NSOM explanation/display fields only in a later UI design step.

## Missing Sky Quality Policy

- Status: `accepted_non_blocking_fallback`.
- Runtime fallback: legacy Best Object when `_sky_quality` is missing
- Blocks default-on switch: `False`.
- Reason: NSOM Best Object requires ObservationEnvironment inputs. Missing sky quality therefore remains a compatibility fallback to the legacy Best Object path.

## Rollback Policy

- Constructor rollback: `AppController(use_nsom_best_object=False)`.
- Legacy path preserved: `True`.
- Blocks default-on switch: `False`.

## Runtime Safety

| Check | Result |
| --- | --- |
| `current_flag_remains_default_off` | `True` |
| `default_off_audit_ready` | `True` |
| `comparison_tooling_developer_only` | `True` |
| `comparison_tooling_has_no_runtime_writes` | `True` |
| `comparison_tooling_has_no_automatic_logging` | `True` |
| `comparison_tooling_has_no_network` | `True` |
| `comparison_tooling_has_no_qml_exposure` | `True` |
| `best_object_runtime_unchanged_by_this_audit` | `True` |
| `recommended_deep_sky_runtime_unchanged` | `True` |
| `planner_runtime_unchanged` | `True` |
| `sky_compass_runtime_unchanged` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_report_imports_absent` | `True` |
| `runtime_objects_not_mutated` | `True` |

## Non-Blocking Risks

- Displayed `score` remains the existing base/legacy-compatible score and may not be monotonic with NSOM order.
- Missing sky quality falls back to the legacy Best Object path because NSOM environment inputs are incomplete.
- Best Object uses Home presentation policy with flat timing factors, not Planner chronology.
- Blocked sessions return no actionable Best Object under NSOM; that is intentional but user-facing copy is unchanged.

## Recommended Next Step

Create a separate default-on switch commit that only sets `NSOM_BEST_OBJECT_ENABLED = True`, keeps `AppController(use_nsom_best_object=False)` as rollback, and reruns focused Best Object runtime tests.
