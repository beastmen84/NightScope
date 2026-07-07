# Sky Compass NSOM Default-On Readiness Audit

## Executive Summary

This developer-only audit checks whether the existing default-off Sky Compass NSOM direction path is ready for or already past a separate default-on switch. It reports the current flag state but does not change QML, wire report tooling into runtime, log automatically, call the network or write runtime files.

## Readiness Verdict

- Verdict: `sky_compass_nsom_default_on_enabled`.
- Ready for default-on switch: `True`.
- Current default flag: `NSOM_SKY_COMPASS_ENABLED = True`.
- Default flag currently enabled: `True`.
- Requires separate flag change: `False`.
- Runtime behaviour changed by this audit: `False`.
- Explicit legacy rollback: `AppController(use_nsom_sky_compass=False)`.
- Explicit NSOM path: `AppController(use_nsom_sky_compass=True)`.
- Recommended switch change: `already enabled`.
- Reason: The Sky Compass NSOM default-on switch is active with explicit rollback, legacy fallback, unchanged payload shape, documented non-blocking risks and no QML/report runtime wiring.

## Default-On Blockers

- none

## Runtime Policy Evidence

| Policy | Evidence |
| --- | --- |
| Flag off | Direction `Sud`, equals legacy `True`. |
| Flag on | Legacy top `Sud`, NSOM top `Nord-Est`. |
| Rollback | `AppController(use_nsom_sky_compass=False)` preserves legacy `True`. |
| Fallback | Missing sky quality fallback `True`, service failure fallback `True`. |
| Payload | Payload keys unchanged `True`, target keys unchanged `True`, NSOM fields exposed `False`. |
| Ownership | Observable base `True`, PracticalTargetValue used `False`, confidence parameter `False`. |
| Mutation | Runtime objects mutated `False`. |

## Displayed Score Semantics

- Status: `accepted_non_blocking_for_default_on`.
- Keep legacy/base displayed score: `True`.
- Score monotonic with NSOM direction decision: `False`.
- Blocks default-on switch: `False`.
- Decision: The `score` field remains the existing target display/base score so the QML contract stays compatible. It is not a Sky Compass NSOM rationale.
- Future UI work: If the UI later needs score rationale, add separate explanation fields in a dedicated design step rather than changing this default-on switch.

## Fallback And Rollback

- Missing sky quality fallback: `True`.
- Service failure fallback: `True`.
- Fallback target: legacy SkyCompassService.compass(...)
- Blocks default-on switch: `False`.
- Constructor rollback: `AppController(use_nsom_sky_compass=False)`.
- Legacy path preserved: `True`.

## Runtime Safety

| Check | Result |
| --- | --- |
| `current_flag_default_on` | `True` |
| `default_off_policy_ready` | `True` |
| `comparison_tooling_developer_only` | `True` |
| `comparison_tooling_has_no_runtime_writes` | `True` |
| `comparison_tooling_has_no_automatic_logging` | `True` |
| `comparison_tooling_has_no_network` | `True` |
| `comparison_tooling_has_no_qml_exposure` | `True` |
| `sky_compass_runtime_unchanged_by_this_audit` | `True` |
| `home_runtime_unchanged` | `True` |
| `best_object_runtime_unchanged` | `True` |
| `planner_runtime_unchanged` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_report_imports_absent` | `True` |
| `runtime_objects_not_mutated` | `True` |

## Non-Blocking Risks

- Default-on will intentionally change direction choice in some bright-sky/high-light-pollution scenarios.
- The displayed target `score` remains legacy/base compatibility data and is not an NSOM direction rationale.
- Sky Compass still has no visible NSOM explanation UI; adding one should be a separate UX/design step.
- Missing sky quality keeps the legacy fallback, so default-on coverage is partial until sky quality is available.
- Equipment-aware compass semantics remain deferred because `PracticalTargetValue` is intentionally not used.

## Recommended Next Step

Review the default-on switch, then close the Sky Compass NSOM migration in documentation while keeping `AppController(use_nsom_sky_compass=False)` as rollback and the `skyCompass` QML payload shape unchanged.
