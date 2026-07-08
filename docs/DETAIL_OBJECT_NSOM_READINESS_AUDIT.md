# Detail/Object NSOM Readiness Audit

## Executive Summary

This developer-only audit checks whether the Detail/Object comparison evidence is ready for a default-off runtime path. It does not change `selectedObject`, QML, Home, Best Object, Planner, Sky Compass, logging, network behaviour or runtime file writes.

## Readiness Verdict

- Verdict: `not_ready_for_default_off_detail_nsom_path`.
- Ready for default-off path: `False`.
- Runtime path exists: `False`.
- Ready for visible UI: `False`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next step: 1.10.2 Detail/Object source and display policy contract.
- Reason: Detail has source-specific legacy display semantics and no defined NSOM payload/display contract yet. A default-off runtime path should wait until those policies are explicit.

## Default-Off Blockers

- `detail-source-policy-unresolved`
- `detail-displayed-score-semantics-unresolved`
- `detail-payload-contract-not-defined`

## Source Policy Review

- Status: `needs_policy_decision`.
- Blocks default-off path: `True`.
- Observing policy: `observing_detail_moon_adjusted_copy`.
- Catalogue policy: `catalogue_detail_raw_object`.
- Observing display score: `53`.
- Catalogue display score: `88`.
- Comparable observable values: `True`.
- Decision needed: Decide whether a future Detail NSOM path preserves source-specific legacy display score semantics, or introduces a separate NSOM explanation/rationale payload while leaving `selectedObject.score` as compatibility data.

## Displayed Score Semantics

- Status: `needs_contract`.
- Blocks default-off path: `True`.
- Keep legacy displayed score for compatibility: `True`.
- Score monotonic with NSOM values: `False`.
- Decision needed: Document that visible `score` remains legacy/base compatibility data, then define any future NSOM rationale fields separately.

## Payload Contract Review

- Status: `not_defined`.
- Blocks default-off path: `True`.
- Existing payload should remain unchanged: `True`.
- Add NSOM fields now: `False`.
- Decision needed: Define a future internal payload contract before runtime code starts building Detail NSOM data. The first runtime path should preserve `selectedObject` keys and keep NSOM fields private or separately named.

## Confidence Review

- Status: `accepted`.
- Blocks default-off path: `False`.
- Score factor: `False`.
- Score effect: `0.0`.

## Runtime Safety

| Check | Result |
| --- | --- |
| `comparison_tooling_developer_only` | `True` |
| `comparison_tooling_has_no_runtime_writes` | `True` |
| `comparison_tooling_has_no_automatic_logging` | `True` |
| `comparison_tooling_has_no_network` | `True` |
| `comparison_tooling_has_no_qml_exposure` | `True` |
| `selected_object_runtime_unchanged` | `True` |
| `home_runtime_unchanged` | `True` |
| `best_object_runtime_unchanged` | `True` |
| `planner_runtime_unchanged` | `True` |
| `sky_compass_runtime_unchanged` | `True` |
| `controller_runtime_wiring_absent` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_report_imports_absent` | `True` |

## Recommended Next Steps

1. Review and decide the Detail source policy explicitly.
2. Define a payload/display contract before adding any default-off runtime path.
3. Keep visible NSOM explanation UI as a later design step.
