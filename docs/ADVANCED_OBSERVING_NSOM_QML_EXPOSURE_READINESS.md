# Advanced Observing NSOM QML Exposure Readiness

## Executive Summary

This developer-only audit checks whether the internal Advanced Observing NSOM presentation payload should be exposed to QML. It does not add a QML property, change `advancedScores`, enable `NSOM_ADVANCED_OBSERVING_ENABLED`, tune scores, log automatically, call the network or write runtime files. The 1.8.10 projection exists and 1.8.11 fixed session metadata fidelity, but a public QML surface is not ready until copy, label semantics and property lifecycle are designed.

## Readiness Verdict

- Verdict: `advanced_observing_nsom_qml_exposure_not_ready`.
- Ready for QML exposure: `False`.
- Ready for user-visible UI: `False`.
- Current default flag: `NSOM_ADVANCED_OBSERVING_ENABLED = False`.
- Default flag currently enabled: `False`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next change: define UI copy, score-label semantics and notify-signal lifecycle before adding any public `advancedObservingNsom` property.
- Reason: The internal projection is JSON-compatible and default-off, but a QML surface still needs explicit presentation copy, localization, score-display semantics and property lifecycle policy.

## Remaining Blockers

- `advanced-observing-public-qml-property`
- `advanced-observing-visible-ui-copy`
- `advanced-observing-score-label-semantics`

## QML Exposure Decisions

| Decision | Status | Blocks QML exposure | Summary |
| --- | --- | --- | --- |
| `internal_projection_safe_to_keep` | `accepted` | `False` | Keep the 1.8.10 internal projection as developer-only data. |
| `public_qml_property` | `blocked_until_lifecycle_policy` | `True` | Do not add `advancedObservingNsom` as a public QML property yet. |
| `visible_ui_copy` | `blocked_until_copy_policy` | `True` | Do not render the payload in the Home UI yet. |
| `score_label_semantics` | `blocked_until_score_display_policy` | `True` | Do not show NSOM category values as legacy `/100` actionability scores. |
| `legacy_advanced_scores_contract` | `accepted` | `False` | Keep `advancedScores` as the only current public QML contract. |
| `confidence_metadata` | `accepted` | `False` | Keep RecommendationConfidence outside score and display reduction semantics. |
| `no_current_qml_wiring` | `verified` | `False` | No current QML or public controller property exposes the payload. |

## Presentation Contract Summary

- Contract verdict: `advanced_observing_nsom_presentation_runtime_projected_not_qml_exposed`.
- Payload schema: `advanced_observing_nsom_presentation_v1`.
- Current QML property: `advancedScores`.
- Future QML property: `advancedObservingNsom`.
- Contract blockers: `['advanced-observing-qml-exposure-review-required']`.

## Static Wiring Checks

| Check | Result |
| --- | --- |
| `qml_nsom_matches` | `[]` |
| `runtime_report_import_matches` | `[]` |
| `controller_private_projection_present` | `True` |
| `controller_public_property_present` | `False` |
| `controller_public_signal_present` | `False` |
| `qml_reads_existing_advanced_scores` | `True` |

## Checks

| Check | Result |
| --- | --- |
| `default_flag_still_off` | `True` |
| `contract_runtime_projection_available` | `True` |
| `contract_qml_review_still_blocking` | `True` |
| `required_qml_exposure_decisions_recorded` | `True` |
| `advanced_scores_remains_current_qml_contract` | `True` |
| `future_property_not_exposed` | `True` |
| `notify_signal_not_introduced` | `True` |
| `runtime_report_imports_absent` | `True` |
| `confidence_score_neutral` | `True` |
| `no_runtime_behaviour_change` | `True` |

## Recommended Next Step

Implement the next step as UI-copy and lifecycle policy only, or keep `advancedObservingNsom` internal. Do not expose a public QML property until the notify-signal policy, localization, score-label copy and visual placement are approved.
