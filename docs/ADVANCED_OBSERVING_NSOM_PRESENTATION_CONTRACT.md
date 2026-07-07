# Advanced Observing NSOM Presentation Contract

## Executive Summary

This developer-only contract defines the future QML-safe Advanced Observing NSOM presentation payload. It does not expose QML, change `advancedScores`, enable `NSOM_ADVANCED_OBSERVING_ENABLED`, tune scores, log automatically, call the network or write runtime files. The contract keeps NSOM category diagnostics separate from legacy scores, Planner inputs and notification thresholds.

## Readiness Verdict

- Verdict: `advanced_observing_nsom_presentation_contract_defined_not_wired`.
- Ready for default-on switch: `False`.
- Current default flag: `NSOM_ADVANCED_OBSERVING_ENABLED = False`.
- Runtime behaviour changed by this contract: `False`.
- Contract status: `defined_developer_only`.
- Future QML property: `advancedObservingNsom`.
- Current QML property: `advancedScores`.
- Recommended next change: Implement a default-off `advancedObservingNsom` runtime property using this contract, while leaving `advancedScores` legacy-compatible.

## Remaining Default-On Blockers

- `advanced-observing-runtime-projection-not-implemented`
- `advanced-observing-qml-exposure-review-required`

## Contract Decisions

| Decision | Status | Blocks default-on | Summary |
| --- | --- | --- | --- |
| `separate_nsom_presentation_payload` | `accepted_design` | `False` | Add a future separate `advancedObservingNsom` payload instead of replacing `advancedScores`. |
| `advanced_scores_legacy_compatibility` | `accepted` | `False` | Keep `advancedScores` legacy-compatible and unchanged. |
| `observable_value_only` | `accepted` | `False` | Use ObservableTargetValue category diagnostics for Advanced Observing NSOM presentation. |
| `session_and_confidence_metadata` | `accepted` | `False` | Keep SessionViability and RecommendationConfidence outside category values. |
| `runtime_projection_not_implemented` | `blocks_default_on` | `True` | The future payload is designed but not yet projected by AppController. |
| `qml_exposure_review_required` | `blocks_default_on` | `True` | QML exposure requires a later UI/review step. |
| `previous_readiness_blocker_addressed` | `accepted` | `False` | The 1.8.8 presentation-contract blocker is addressed at design level. |

## Payload Shape

- Schema version: `advanced_observing_nsom_presentation_v1`.
- Runtime state: `contract_only_not_wired`.
- Replaces `advancedScores`: `False`.
- Planner input: `False`.
- Notification input: `False`.
- Session score effect: `0.0`.
- Confidence score effect: `0.0`.

## Categories

| Category | NSOM value | Legacy value | Score meaning |
| --- | ---: | ---: | --- |
| `planetary` | 86 | 88 | NSOM ObservableTargetValue category diagnostic |
| `deepSky` | 54 | 61 | NSOM ObservableTargetValue category diagnostic |

## Checks

| Check | Result |
| --- | --- |
| `default_flag_still_off` | `True` |
| `presentation_readiness_was_blocked` | `True` |
| `contract_schema_versioned` | `True` |
| `contract_defines_separate_future_property` | `True` |
| `contract_does_not_replace_advanced_scores` | `True` |
| `contract_excludes_planner_and_notifications` | `True` |
| `categories_use_observable_value_only` | `True` |
| `session_and_confidence_are_metadata` | `True` |
| `observer_and_opportunity_excluded` | `True` |
| `required_contract_decisions_recorded` | `True` |
| `runtime_projection_still_blocks_default_on` | `True` |
| `qml_exposure_review_still_blocks_default_on` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_exposure_absent` | `True` |
| `future_property_not_wired` | `True` |
| `runtime_behaviour_unchanged` | `True` |

## Runtime And QML Wiring

- QML matches: `[]`.
- Runtime report imports: `[]`.
- Future property already wired: `False`.

## Recommended Next Step

Implement `1.8.10` as a default-off runtime projection for the `advancedObservingNsom` contract. Keep `advancedScores` unchanged and do not expose the new property to QML until a separate UI review.
