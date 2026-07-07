# Advanced Observing NSOM QML Presentation Policy

## Executive Summary

This developer-only policy closes the 1.8.12 presentation-design gap for a future Advanced Observing NSOM QML surface. It defines the future property name, notify/lifecycle policy, visible-copy boundaries, score label semantics and rollback expectation. It does not add a QML property, does not render visible UI, does not change `advancedScores`, does not enable `NSOM_ADVANCED_OBSERVING_ENABLED`, and does not write files at runtime, log automatically or call the network.

## Readiness Verdict

- Verdict: `advanced_observing_nsom_qml_policy_defined_not_wired`.
- Policy status: `defined_developer_only`.
- Policy covers 1.8.12 blockers: `True`.
- Ready for runtime QML exposure now: `False`.
- Ready for user-visible UI now: `False`.
- Ready for separate read-only property step: `True`.
- Current default flag: `NSOM_ADVANCED_OBSERVING_ENABLED = False`.
- Default flag currently enabled: `False`.
- Runtime behaviour changed by this policy: `False`.
- Recommended next change: review this policy, then implement a separate default-off read-only `advancedObservingNsom` property only if QML exposure is approved.
- Reason: The missing lifecycle, copy and score-label decisions from 1.8.12 are now documented, but no public QML property or visible UI is implemented in this step.

## Remaining Items Before Runtime QML Exposure

- `advanced-observing-read-only-qml-property-not-implemented`
- `advanced-observing-visible-ui-design-not-approved`
- `advanced-observing-default-flag-still-off`

## Policy Decisions

| Decision | Status | Covers 1.8.12 blocker | Runtime change | Summary |
| --- | --- | --- | --- | --- |
| `future_qml_property_name` | `accepted_policy` | `advanced-observing-public-qml-property` | `False` | Reserve `advancedObservingNsom` as the future read-only QML property name. |
| `notify_signal_lifecycle` | `accepted_policy` | `advanced-observing-public-qml-property` | `False` | Use the existing `weatherChanged` lifecycle for any future property. |
| `visible_ui_copy_policy` | `accepted_policy` | `advanced-observing-visible-ui-copy` | `False` | Keep visible UI blocked; future copy must be localization-key based. |
| `score_label_semantics` | `accepted_policy` | `advanced-observing-score-label-semantics` | `False` | Label category values as NSOM diagnostics, not legacy actionability scores. |
| `confidence_metadata_policy` | `accepted` | `advanced-observing-score-label-semantics` | `False` | Display confidence only as data-trust metadata if a future UI uses it. |
| `visual_placement_policy` | `accepted_policy` | `advanced-observing-visible-ui-copy` | `False` | Any future visible UI belongs in a separate diagnostic area, not inside legacy score cards. |
| `rollback_policy` | `accepted` | `None` | `False` | Keep the future rollback path as the existing internal flag/constructor override. |
| `source_blockers_addressed_at_policy_level` | `verified` | `None` | `False` | The 1.8.12 blocker categories now have explicit policy decisions. |

## Future Property Lifecycle

- Future property: `advancedObservingNsom`.
- Notify signal: `weatherChanged`.
- New signal required: `False`.
- Runtime source: `_advanced_observing_nsom_presentation`.
- Recompute on property read: `False`.

## Copy And Score Semantics

- Copy delivery: `localization_keys_or_existing_translation_layer`.
- Visible UI approved now: `False`.
- Title key: `advanced_observing_nsom.title`.
- Category label key: `advanced_observing_nsom.category_value`.
- Score display label: `NSOM category diagnostic value`.
- Must not display as legacy `/100` actionability: `True`.
- Confidence score effect: `0.0`.

## Source Readiness Summary

- Source verdict: `advanced_observing_nsom_qml_exposure_not_ready`.
- Source blockers: `['advanced-observing-public-qml-property', 'advanced-observing-visible-ui-copy', 'advanced-observing-score-label-semantics']`.
- Future property: `advancedObservingNsom`.
- Current property: `advancedScores`.

## Static Wiring Checks

| Check | Result |
| --- | --- |
| `qml_nsom_matches` | `[]` |
| `runtime_report_import_matches` | `[]` |
| `controller_private_projection_present` | `True` |
| `controller_public_property_present` | `False` |
| `controller_public_signal_present` | `False` |
| `weather_changed_signal_present` | `True` |
| `advanced_scores_property_uses_weather_changed` | `True` |
| `qml_reads_existing_advanced_scores` | `True` |

## Checks

| Check | Result |
| --- | --- |
| `default_flag_still_off` | `True` |
| `source_readiness_was_not_ready` | `True` |
| `policy_covers_source_blockers` | `True` |
| `future_property_name_defined` | `True` |
| `future_read_only_property_policy_defined` | `True` |
| `visible_ui_copy_policy_defined` | `True` |
| `visible_ui_still_not_approved` | `True` |
| `score_label_policy_avoids_legacy_actionability` | `True` |
| `confidence_score_neutral` | `True` |
| `rollback_policy_defined` | `True` |
| `advanced_scores_remains_current_qml_contract` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_exposure_absent` | `True` |
| `future_property_not_wired` | `True` |
| `new_signal_not_wired` | `True` |
| `existing_weather_changed_available` | `True` |
| `private_projection_available` | `True` |
| `qml_reads_existing_advanced_scores` | `True` |
| `no_runtime_behaviour_change` | `True` |

## Recommended Next Step

Review this policy. If accepted, implement a separate read-only `advancedObservingNsom` property in a later step using the existing `weatherChanged` lifecycle and the private `_advanced_observing_nsom_presentation` snapshot. Keep visible UI and default-on Advanced Observing NSOM as separate decisions.
