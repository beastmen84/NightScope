# Advanced Observing NSOM Downstream Policy

## Executive Summary

This developer-only policy report resolves the consumer question raised by the `1.8.5` runtime review: `advancedScores` is a shared runtime contract read by QML, Planner and NotificationService. The current Advanced Observing NSOM path remains default-off. This report does not change the flag, tune scores, alter Planner or NotificationService, expose QML, log automatically, call the network or write runtime files.

## Readiness Verdict

- Verdict: `not_ready_for_advanced_observing_nsom_default_on`.
- Default flag: `NSOM_ADVANCED_OBSERVING_ENABLED = False`.
- Ready for default-on switch: `False`.
- Runtime behaviour changed by this policy: `False`.
- Forced-on path safe to keep: `True`.
- Recommended next change: Implement a consumer split so Planner and NotificationService do not receive NSOM category diagnostics as legacy advancedScores.

## Default-On Blockers

- `advanced-observing-shared-advanced-scores-contract`
- `advanced-observing-planner-consumer-policy`
- `advanced-observing-notification-consumer-policy`
- `advanced-observing-qml-display-policy`

## Policy Decisions

| Policy | Status | Blocks default-on | Decision |
| --- | --- | --- | --- |
| `shared_advanced_scores_contract` | `needs_consumer_split_before_default_on` | `True` | `advancedScores` must remain legacy-compatible for shared runtime consumers until Planner and NotificationService receive explicit consumer-specific inputs. |
| `planner_consumer_policy` | `needs_implementation_before_default_on` | `True` | Planner must not consume forced-on NSOM Advanced Observing category values as `advanced_score_factor`. It should receive either a legacy-compatible condition score or explicit NSOM environment components without duplicated sky/session ownership. |
| `notification_consumer_policy` | `needs_implementation_before_default_on` | `True` | NotificationService must not trigger favourable observing-condition notifications from NSOM category values during blocked sessions. It needs either legacy-compatible scores or an explicit SessionViability gate. |
| `qml_display_policy` | `deferred_blocking_for_default_on` | `True` | QML may keep the existing payload shape, but a default-on switch needs copy/label policy so NSOM category diagnostics are not read as legacy actionability scores. |
| `confidence_policy` | `accepted` | `False` | RecommendationConfidence remains metadata-only and must not alter downstream scores. |
| `home_best_object_sky_compass_policy` | `accepted` | `False` | Home recommendedDeepSky, Best Object and Sky Compass are not changed by this policy step. |

## Notification Evidence

- Legacy blocked-session titles: `[]`.
- NSOM forced-on blocked-session titles: `['Condizioni planetarie favorevoli', 'Finestra cielo profondo utile']`.
- NSOM would trigger favourable blocked-session notifications: `True`.

## Planner Evidence

- Planner uses `advancedScores` as atmospheric transparency: `True`.
- Poor-weather legacy category factor: `0.43`.
- Poor-weather NSOM category factor: `0.82`.
- Planner score changes with forced-on NSOM scores: `True`.
- Duplicate ownership risk: `True`.

## Checks

| Check | Result |
| --- | --- |
| `default_flag_still_off` | `True` |
| `runtime_review_identified_downstream_blocker` | `True` |
| `required_decisions_recorded` | `True` |
| `planner_policy_blocks_default_on` | `True` |
| `notification_policy_blocks_default_on` | `True` |
| `confidence_score_neutral` | `True` |
| `notification_blocked_session_risk_visible` | `True` |
| `planner_score_risk_visible` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_behaviour_unchanged` | `True` |

## Runtime And QML Wiring

- QML matches: `[]`.
- Runtime report imports: `[]`.

## Recommended Next Step

Implement `1.8.7` as the consumer-split design/implementation: keep `advancedScores` legacy-compatible for Planner and notifications, or introduce explicit runtime inputs so those consumers no longer depend on the shared Advanced Observing presentation score.
