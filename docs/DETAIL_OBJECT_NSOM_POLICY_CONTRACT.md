# Detail/Object NSOM Policy Contract

## Executive Summary

This developer-only contract resolves the policy questions raised by the Detail/Object comparison and readiness audit. It does not change `selectedObject`, QML, Home, Best Object, Planner, Sky Compass, logging, network behaviour or runtime file writes.

## Readiness Verdict

- Verdict: `detail_object_nsom_policy_contract_defined`.
- Ready for default-off path after contract: `True`.
- Ready for visible UI: `False`.
- Runtime behaviour changed by this contract: `False`.
- Recommended next change: review the contract, then implement a default-off Detail/Object NSOM path behind explicit rollback.
- Reason: Source-specific Detail display semantics, displayed score compatibility and separate NSOM payload policy are now explicit.

## Default-Off Blockers

- none

## Contract Decisions

| Decision | Status | Blocks default-off | Summary |
| --- | --- | --- | --- |
| `source_specific_detail_policy` | `accepted` | `False` | Preserve source-specific legacy Detail display semantics in `selectedObject` during the first default-off NSOM runtime path. |
| `displayed_score_compatibility` | `accepted` | `False` | `selectedObject.score` remains legacy/base compatibility data and is not an NSOM rationale. |
| `separate_nsom_payload` | `accepted` | `False` | Future Detail NSOM runtime data must be private or separately named; it must not add fields to `selectedObject` in the first runtime path. |
| `observable_target_value_role` | `accepted` | `False` | ObservableTargetValue explains objective target plus sky value only. |
| `practical_target_value_role` | `accepted` | `False` | PracticalTargetValue may explain equipment suitability separately from displayed score. |
| `session_viability_metadata` | `accepted` | `False` | SessionViability is Detail metadata and does not mutate target values. |
| `confidence_metadata` | `accepted` | `False` | RecommendationConfidence remains metadata-only with zero score effect. |

## Payload Contract

- Schema version: `detail-object-nsom-policy-v1`.
- Current QML property: `selectedObject`.
- Future internal payload: `detailObjectNsom`.
- Visible QML exposure approved: `False`.
- Preserve selectedObject keys: `True`.
- `selectedObject.score` meaning: legacy/base compatibility data; not NSOM rationale
- NSOM fields added to selectedObject: `False`.

## Source Policies

| Source | Legacy display policy | NSOM policy | Score policy |
| --- | --- | --- | --- |
| `observing` | observing_detail_moon_adjusted_copy | build parallel NSOM payload only; preserve selectedObject display semantics | moon-adjusted compatibility display score remains in selectedObject |
| `catalogue` | catalogue_detail_raw_object | build parallel NSOM payload only; preserve selectedObject display semantics | raw catalogue compatibility display score remains in selectedObject |

## NSOM Separation

- ObservableTargetValue role: objective target plus sky explanation
- PracticalTargetValue role: observer/equipment explanation only
- SessionViability role: metadata/actionability context only
- RecommendationConfidence role: metadata/trust only, zero score effect

## Checks

| Check | Result |
| --- | --- |
| `source_policy_decision_recorded` | `True` |
| `displayed_score_decision_recorded` | `True` |
| `separate_payload_decision_recorded` | `True` |
| `observable_role_recorded` | `True` |
| `practical_role_recorded` | `True` |
| `session_metadata_recorded` | `True` |
| `confidence_metadata_recorded` | `True` |
| `selected_object_payload_preserved` | `True` |
| `future_payload_separate` | `True` |
| `visible_qml_exposure_not_approved` | `True` |
| `runtime_constraints_safe` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_report_imports_absent` | `True` |

## Runtime And QML Wiring

- QML matches: `[]`.
- Runtime report imports: `[]`.

## Recommended Next Steps

1. Review this contract.
2. Implement a default-off Detail/Object NSOM runtime path with explicit rollback.
3. Keep visible NSOM explanation UI as a later design step.
