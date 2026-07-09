# Advanced Observing NSOM Downstream Policy

## Executive Summary

This developer-only policy report resolves the consumer question raised by the `1.8.5` runtime review: `advancedScores` is a shared runtime contract read by QML and Planner. NotificationService has since been removed as dead legacy. The current Advanced Observing NSOM backend projection remains separate from the visible `advancedScores` payload. This report does not change the flag, tune scores, alter Planner, expose QML, log automatically, call the network or write runtime files. In `1.8.7`, AppController keeps the shared `advancedScores` payload legacy-compatible and stores forced-on NSOM Advanced Observing scores only as an internal parallel snapshot.

## Readiness Verdict

- Verdict: `consumer_split_resolved_but_qml_policy_blocks_default_on`.
- Default flag: `NSOM_ADVANCED_OBSERVING_ENABLED = True`.
- Ready for default-on switch: `False`.
- Runtime behaviour changed by this policy: `False`.
- Forced-on path safe to keep: `True`.
- Consumer split implemented: `True`.
- Recommended next change: Define the Advanced Observing presentation/QML policy before enabling NSOM Advanced Observing by default.

## Default-On Blockers

- `advanced-observing-qml-display-policy`

## Policy Decisions

| Policy | Status | Blocks default-on | Decision |
| --- | --- | --- | --- |
| `shared_advanced_scores_contract` | `implemented_legacy_contract_preserved` | `False` | `advancedScores` remains the legacy-compatible shared runtime payload. Forced-on NSOM Advanced Observing scores are kept as an internal parallel snapshot. |
| `planner_consumer_policy` | `resolved_by_legacy_consumer_input` | `False` | Planner receives the legacy-compatible AdvancedObservingScores consumer input, so forced-on Advanced Observing NSOM category diagnostics do not become Planner atmospheric transparency. |
| `notification_consumer_policy` | `removed_dead_legacy_consumer` | `False` | Notifications are no longer a runtime consumer. The dead backend path, controller property and DTO were removed instead of migrated to NSOM. |
| `qml_display_policy` | `deferred_blocking_for_default_on` | `True` | QML may keep the existing payload shape, but a default-on switch needs copy/label policy so NSOM category diagnostics are not read as legacy actionability scores. |
| `confidence_policy` | `accepted` | `False` | RecommendationConfidence remains metadata-only and must not alter downstream scores. |
| `home_best_object_sky_compass_policy` | `accepted` | `False` | Home recommendedDeepSky, Best Object and Sky Compass are not changed by this policy step. |

## Notification Evidence

- Legacy blocked-session titles: `[]`.
- NSOM forced-on blocked-session titles: `[]`.
- Notification backend present: `False`.
- Notification score path absent: `True`.
- Removed backend prevents favourable blocked-session notifications: `True`.

## Planner Evidence

- Planner uses `advancedScores` as atmospheric transparency: `True`.
- Poor-weather legacy category factor: `0.43`.
- Poor-weather NSOM category factor: `0.82`.
- Planner score changes with forced-on NSOM scores: `True`.
- Consumer split preserves legacy Planner score: `True`.
- Duplicate ownership risk: `True`.

## Checks

| Check | Result |
| --- | --- |
| `default_flag_still_off` | `False` |
| `runtime_review_identified_downstream_blocker` | `True` |
| `required_decisions_recorded` | `True` |
| `shared_contract_split_resolved` | `True` |
| `planner_consumer_split_resolved` | `True` |
| `notification_consumer_split_resolved` | `True` |
| `qml_policy_blocks_default_on` | `True` |
| `confidence_score_neutral` | `True` |
| `notification_backend_removed` | `True` |
| `notification_score_path_absent` | `True` |
| `planner_score_risk_visible` | `True` |
| `removed_backend_prevents_notification_risk` | `True` |
| `consumer_split_preserves_planner_score` | `True` |
| `controller_consumer_split_methods_present` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_behaviour_unchanged` | `True` |

## Runtime And QML Wiring

- QML matches: `[]`.
- Runtime report imports: `[]`.

## Recommended Next Step

Implement `1.8.8` as the Advanced Observing presentation/default-on readiness audit: decide whether QML should keep legacy cards, gain separate NSOM explanation fields, or continue hiding the internal NSOM snapshot.
