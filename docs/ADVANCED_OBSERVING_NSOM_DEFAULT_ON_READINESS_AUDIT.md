# Advanced Observing NSOM Default-On Readiness Audit

## Executive Summary

This developer-only audit checks whether Advanced Observing NSOM can be enabled by default as a backend/internal projection. It does not enable the flag, does not replace `advancedScores`, does not render visible QML UI, does not tune scores, does not change Planner, NotificationService, Home Best Object or Sky Compass, and does not log automatically, call the network or write runtime files.

## Readiness Verdict

- Verdict: `ready_for_advanced_observing_nsom_backend_default_on`.
- Ready for backend default-on: `True`.
- Ready for visible UI: `False`.
- Ready to replace `advancedScores`: `False`.
- Current default flag: `NSOM_ADVANCED_OBSERVING_ENABLED = False`.
- Default flag currently enabled: `False`.
- Requires separate flag change: `True`.
- Explicit rollback: `AppController(use_nsom_advanced_observing=False)`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next change: set `NSOM_ADVANCED_OBSERVING_ENABLED = True` in a separate backend-only switch commit, keeping `advancedScores` and visible QML unchanged.

## Default-On Blockers

- None for backend/internal projection default-on.

## Remaining Non-Blocking Items

- `advanced-observing-visible-ui-design-not-approved`
- `advanced-observing-visible-copy-localization-not-designed`
- `advanced-observing-advanced-scores-replacement-not-scoped`

## Decisions

| Decision | Status | Blocks backend default-on | Blocks visible UI | Summary |
| --- | --- | --- | --- | --- |
| `backend_projection_default_on` | `ready` | `False` | `False` | Default-on is scoped to the internal Advanced Observing NSOM projection. |
| `visible_ui` | `deferred_non_blocking` | `False` | `True` | Do not render Advanced Observing NSOM in visible QML UI yet. |
| `advanced_scores_replacement` | `out_of_scope` | `False` | `False` | Do not replace `advancedScores` in this switch. |
| `read_only_property_safety` | `accepted` | `False` | `False` | The `advancedObservingNsom` property is read-only and defensive-copy hardened. |
| `qml_visibility` | `accepted_no_visible_usage` | `False` | `False` | No visible QML reads `controller.advancedObservingNsom`. |
| `consumer_split` | `accepted` | `False` | `False` | Planner and notifications keep legacy-compatible `advancedScores` inputs. |
| `confidence_metadata` | `accepted` | `False` | `False` | RecommendationConfidence remains metadata-only. |
| `report_tooling` | `developer_only` | `False` | `False` | Comparison/readiness reports remain explicit developer tooling. |
| `source_reports` | `accepted` | `False` | `False` | Readiness builds on the presentation contract, QML exposure and QML policy reports. |

## Checks

| Check | Result |
| --- | --- |
| `default_flag_still_off_for_audit` | `True` |
| `source_reports_strict_json_compatible` | `True` |
| `read_only_property_available` | `True` |
| `property_defensive_copy_hardened` | `True` |
| `visible_qml_usage_absent` | `True` |
| `advanced_scores_remains_current_qml_contract` | `True` |
| `advanced_scores_not_replaced` | `True` |
| `planner_notifications_keep_legacy_inputs` | `True` |
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
| `planner_notification_legacy_consumer_split` | `True` |

## Source Summary

- Presentation contract verdict: `advanced_observing_nsom_presentation_read_only_qml_property_wired`.
- QML exposure verdict: `advanced_observing_nsom_read_only_qml_property_available`.
- QML presentation policy verdict: `advanced_observing_nsom_qml_policy_applied_read_only_property`.
- Historical contract blockers: `['advanced-observing-visible-ui-review-required']`.
- QML policy remaining items: `['advanced-observing-visible-ui-design-not-approved', 'advanced-observing-default-flag-still-off']`.

## Recommended Next Step

Implement the default-on switch as a narrow backend-only commit: set `NSOM_ADVANCED_OBSERVING_ENABLED = True`, preserve `AppController(use_nsom_advanced_observing=False)` as rollback, keep `advancedScores` and visible QML unchanged, and rerun focused Advanced Observing NSOM runtime tests.
