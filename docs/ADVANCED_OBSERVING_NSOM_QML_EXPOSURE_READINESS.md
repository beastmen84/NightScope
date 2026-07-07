# Advanced Observing NSOM QML Exposure Readiness

## Executive Summary

This developer-only audit checks whether the internal Advanced Observing NSOM presentation payload is safely exposed to QML. As of 1.8.14, `advancedObservingNsom` is a read-only property backed by the private `_advanced_observing_nsom_presentation` snapshot and the existing `weatherChanged` lifecycle. As of 1.8.15, the property returns a defensive deep copy so consumers cannot mutate the private snapshot. This report does not change `advancedScores`, enable `NSOM_ADVANCED_OBSERVING_ENABLED`, tune scores, render visible UI, log automatically, call the network or write runtime files.

## Readiness Verdict

- Verdict: `advanced_observing_nsom_read_only_qml_property_available`.
- Ready for QML exposure: `True`.
- Ready for user-visible UI: `False`.
- Current default flag: `NSOM_ADVANCED_OBSERVING_ENABLED = True`.
- Default flag currently enabled: `True`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next change: decide separately whether visible UI should consume `advancedObservingNsom` or whether Advanced Observing NSOM should remain developer-facing.
- Reason: The internal projection is now available through a read-only QML property using the existing weather lifecycle. No QML UI consumes it yet, and visible UI still needs explicit design approval.

## Remaining Items

- None for read-only QML exposure; visible UI remains a separate decision.

## QML Exposure Decisions

| Decision | Status | Blocks QML exposure | Summary |
| --- | --- | --- | --- |
| `internal_projection_safe_to_keep` | `accepted` | `False` | Keep the 1.8.10 internal projection as developer-only data. |
| `public_qml_property` | `implemented_read_only` | `False` | Expose `advancedObservingNsom` as a read-only QML property. |
| `visible_ui_copy` | `blocks_visible_ui_only` | `False` | Do not render the payload in the Home UI yet. |
| `score_label_semantics` | `blocks_visible_ui_only` | `False` | Do not show NSOM category values as legacy `/100` actionability scores. |
| `legacy_advanced_scores_contract` | `accepted` | `False` | Keep `advancedScores` as the only current public QML contract. |
| `confidence_metadata` | `accepted` | `False` | Keep RecommendationConfidence outside score and display reduction semantics. |
| `read_only_qml_property_wired` | `verified` | `False` | The controller exposes the payload through a read-only property, but QML UI does not read it. |

## Presentation Contract Summary

- Contract verdict: `advanced_observing_nsom_presentation_read_only_qml_property_wired`.
- Payload schema: `advanced_observing_nsom_presentation_v1`.
- Current QML property: `advancedScores`.
- Future QML property: `advancedObservingNsom`.
- Contract blockers: `['advanced-observing-visible-ui-review-required']`.

## Static Wiring Checks

| Check | Result |
| --- | --- |
| `qml_nsom_matches` | `[]` |
| `runtime_report_import_matches` | `[]` |
| `controller_private_projection_present` | `True` |
| `controller_public_property_present` | `True` |
| `controller_public_signal_present` | `False` |
| `qml_reads_existing_advanced_scores` | `True` |

## Checks

| Check | Result |
| --- | --- |
| `default_flag_still_off` | `False` |
| `contract_runtime_projection_available` | `True` |
| `contract_visible_ui_review_still_blocking` | `True` |
| `required_qml_exposure_decisions_recorded` | `True` |
| `advanced_scores_remains_current_qml_contract` | `True` |
| `future_property_exposed_read_only` | `True` |
| `visible_qml_usage_absent` | `True` |
| `notify_signal_not_introduced` | `True` |
| `runtime_report_imports_absent` | `True` |
| `confidence_score_neutral` | `True` |
| `no_runtime_behaviour_change` | `True` |

## Recommended Next Step

The read-only `advancedObservingNsom` property is wired and defensive-copy hardened. Keep visible UI and any default-on Advanced Observing NSOM switch as separate decisions.
