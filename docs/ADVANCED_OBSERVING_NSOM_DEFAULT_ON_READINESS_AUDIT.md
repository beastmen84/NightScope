# Advanced Observing NSOM Default-On Readiness Audit

## Executive Summary

This developer-only audit checks whether Advanced Observing NSOM can be kept enabled by default as a backend/internal projection. It records the backend switch state, does not replace `advancedScores`, does not render visible QML UI, does not tune scores, does not change Planner, Home Best Object or Sky Compass, and does not log automatically, call the network or write runtime files.

## Readiness Verdict

- Verdict: `advanced_observing_nsom_backend_default_on_enabled`.
- Ready for backend default-on: `True`.
- Ready for visible UI: `False`.
- Ready to replace `advancedScores`: `False`.
- Current default flag: `NSOM_ADVANCED_OBSERVING_ENABLED = True`.
- Default flag currently enabled: `True`.
- Requires separate flag change: `False`.
- Default-on switch completed: `True`.
- Explicit rollback: `AppController(use_nsom_advanced_observing=False)`.
- Runtime default changed by switch: `True`.
- Visible runtime behaviour changed: `False`.
- Recommended next change: keep the backend default-on switch, use explicit rollback for legacy diagnostics when needed, and review visible UI separately.

## Default-On Blockers

- None for backend/internal projection default-on.

## Remaining Non-Blocking Items

- `advanced-observing-visible-ui-design-not-approved`
- `advanced-observing-visible-copy-localization-not-designed`
- `advanced-observing-advanced-scores-replacement-not-scoped`

## Decisions

| Decision | Status | Blocks backend default-on | Blocks visible UI | Summary |
| --- | --- | --- | --- | --- |
| `backend_projection_default_on` | `enabled` | `False` | `False` | Default-on is active for the internal Advanced Observing NSOM projection. |
| `visible_ui` | `deferred_non_blocking` | `False` | `True` | Do not render Advanced Observing NSOM in visible QML UI yet. |
| `advanced_scores_replacement` | `out_of_scope` | `False` | `False` | Do not replace `advancedScores` in this switch. |
| `read_only_property_safety` | `accepted` | `False` | `False` | The `advancedObservingNsom` property is read-only and defensive-copy hardened. |
| `qml_visibility` | `accepted_no_visible_usage` | `False` | `False` | No visible QML reads `controller.advancedObservingNsom`. |
| `consumer_split` | `accepted` | `False` | `False` | Planner keeps legacy-compatible `advancedScores` input; Notifications are absent. |
| `confidence_metadata` | `accepted` | `False` | `False` | RecommendationConfidence remains metadata-only. |
| `report_tooling` | `developer_only` | `False` | `False` | Comparison/readiness reports remain explicit developer tooling. |
| `source_reports` | `accepted` | `False` | `False` | Readiness builds on the presentation contract, QML exposure and QML policy reports. |

## Checks

| Check | Result |
| --- | --- |
| `default_flag_enabled_for_switch` | `True` |
| `source_reports_strict_json_compatible` | `True` |
| `read_only_property_available` | `True` |
| `property_defensive_copy_hardened` | `True` |
| `visible_qml_usage_absent` | `True` |
| `advanced_scores_remains_current_qml_contract` | `True` |
| `advanced_scores_not_replaced` | `True` |
| `planner_keeps_legacy_input_and_notifications_absent` | `True` |
| `confidence_metadata_only` | `True` |
| `report_tooling_developer_only` | `True` |
| `no_runtime_file_logging_network` | `True` |
| `required_decisions_recorded` | `True` |
| `backend_default_on_blockers_absent` | `True` |
| `visible_ui_still_deferred` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Static Wiring Checks

| Check | Result |
| --- | --- |
| `visible_qml_nsom_matches` | `[]` |
| `runtime_report_import_matches` | `[]` |
| `controller_public_property_present` | `True` |
| `property_defensive_copy_present` | `True` |
| `new_nsom_signal_absent` | `True` |
| `planner_legacy_consumer_input_and_notifications_absent` | `True` |

## Source Summary

- Presentation contract verdict: `advanced_observing_nsom_presentation_read_only_qml_property_wired`.
- QML exposure verdict: `advanced_observing_nsom_read_only_qml_property_available`.
- QML presentation policy verdict: `advanced_observing_nsom_qml_policy_applied_read_only_property`.
- Historical contract blockers: `['advanced-observing-visible-ui-review-required']`.
- QML policy remaining items: `['advanced-observing-visible-ui-design-not-approved']`.

## Recommended Next Step

Keep the backend default-on switch narrow: preserve `AppController(use_nsom_advanced_observing=False)` as rollback, keep `advancedScores` and visible QML unchanged, and review any visible Advanced Observing NSOM UI separately.
