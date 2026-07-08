# Detail/Object NSOM Default-On Readiness Audit

## Executive Summary

This developer-only audit checks whether the existing default-off Detail/Object NSOM runtime path is ready for a later default-on switch. It does not change `NSOM_DETAIL_OBJECT_ENABLED`, `selectedObject`, QML, Home, Best Object, Planner, Sky Compass, logging, network access or runtime file writes.

## Readiness Verdict

- Verdict: `ready_for_detail_object_nsom_default_on_switch`.
- Ready for default-on switch: `True`.
- Current default flag: `NSOM_DETAIL_OBJECT_ENABLED = False`.
- Default flag currently enabled: `False`.
- Default flag remains off for this commit: `True`.
- Requires separate flag change: `True`.
- Runtime behaviour changed by this audit: `False`.
- Explicit legacy rollback: `AppController(use_nsom_detail_object=False)`.
- Explicit NSOM path: `AppController(use_nsom_detail_object=True)`.
- Recommended switch change: `set NSOM_DETAIL_OBJECT_ENABLED = True`.
- Reason: The default-off Detail/Object runtime path has rollback, preserves `selectedObject`, keeps session/confidence metadata-only and has no QML or report runtime wiring.

## Default-On Blockers

- none

## Runtime Policy Evidence

| Policy | Evidence |
| --- | --- |
| Flag off | Payload empty `True`, `selectedObject` unchanged `True`. |
| Observing source | Policy `observing_detail_moon_adjusted_copy`, internal payload exists `True`, selected payload unchanged `True`. |
| Catalogue source | Policy `catalogue_detail_raw_object`, internal payload exists `True`, selected payload unchanged `True`. |
| Session | Blocked session value `0.0`, observable unchanged `True`, practical unchanged `True`. |
| Confidence | Low/high values `0.05` / `1.0`, score effect `0.0`. |
| Mutation | Runtime object mutated `False`. |

## Display Score Semantics

- Status: `accepted`.
- Keep legacy/base displayed score: `True`.
- Score monotonic with NSOM payload: `False`.
- Blocks default-on switch: `False`.
- Decision: `selectedObject.score` remains legacy/base compatibility data even if the internal Detail/Object NSOM path is enabled by default.
- Future UI work: Visible NSOM rationale or score labels require a separate Detail page UX step.

## Missing Input Policy

- Status: `accepted`.
- Missing sky quality returns empty payload: `True`.
- Missing weather returns empty payload: `True`.
- Blocks default-on switch: `False`.
- Reason: The internal payload is absent until required runtime inputs exist; `selectedObject` continues to provide the legacy-compatible view.

## Rollback Policy

- Constructor rollback: `AppController(use_nsom_detail_object=False)`.
- Legacy path preserved: `True`.
- NSOM path explicit: `AppController(use_nsom_detail_object=True)`.
- Blocks default-on switch: `False`.

## Runtime Safety

| Check | Result |
| --- | --- |
| `developer_only_audit` | `True` |
| `runtime_writes` | `False` |
| `automatic_logging` | `False` |
| `network` | `False` |
| `qml_exposure_absent` | `True` |
| `runtime_report_imports_absent` | `True` |
| `selected_object_payload_preserved` | `True` |
| `nsom_fields_absent_from_selected_object` | `True` |
| `home_changed` | `False` |
| `best_object_changed` | `False` |
| `planner_changed` | `False` |
| `sky_compass_changed` | `False` |
| `default_off_readiness_has_no_blockers` | `True` |

## Non-Blocking Risks

- `selectedObject.score` remains legacy/base compatibility data and may not be monotonic with NSOM values.
- Visible Detail page NSOM explanations still require a separate UX/design step.
- Missing sky quality or weather leaves the internal NSOM payload empty while legacy Detail remains available.

## Recommended Next Step

Review this audit, then use a separate switch commit to set `NSOM_DETAIL_OBJECT_ENABLED = True` if the default-on decision is accepted.
