# Advanced Observing NSOM Runtime Review

## Executive Summary

This developer-only report reviews the default-off Advanced Observing NSOM runtime path added in `1.8.4`. It compares forced-on NSOM output with legacy `AdvancedObservingService` output and checks whether the path is safe to keep before any default-on switch. It does not change the flag, tune scores, expose QML fields, log automatically, call the network or write runtime files.

## Readiness Verdict

- Verdict: `not_ready_for_default_on_switch`.
- Default flag: `NSOM_ADVANCED_OBSERVING_ENABLED = True`.
- Ready for default-on switch: `False`.
- Forced-on path safe to keep: `True`.
- Runtime behaviour changed by this review: `False`.
- Explicit opt-in: `AppController() / NSOM_ADVANCED_OBSERVING_ENABLED`.
- Legacy default: `AppController(use_nsom_advanced_observing=False)`.
- Recommended next change: Add an Advanced Observing default-on readiness audit only after Planner/notification use of advancedScores has an explicit policy.

## Default-On Blockers

- `advanced-observing-downstream-consumer-policy`
- `advanced-observing-score-label-policy`
- `advanced-observing-blocked-session-display-policy`

## Scenario Score Deltas

| Scenario | Legacy P | NSOM P | Delta P | Legacy DSO | NSOM DSO | Delta DSO | Session | Confidence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| A01_good_session | 90 | 86 | -4 | 88 | 82 | -6 | usable | 1.00 |
| A02_poor_weather | 43 | 86 | 43 | 43 | 82 | 39 | usable | 1.00 |
| A03_blocked_session | 20 | 86 | 66 | 20 | 82 | 62 | blocked | 1.00 |
| A04_bright_moon | 88 | 86 | -2 | 76 | 61 | -15 | usable | 1.00 |
| A05_high_light_pollution | 89 | 86 | -3 | 70 | 70 | 0 | usable | 1.00 |
| A06_poor_seeing | 66 | 30 | -36 | 88 | 82 | -6 | usable | 1.00 |
| A07_poor_transparency | 90 | 86 | -4 | 72 | 29 | -43 | usable | 1.00 |
| A08_low_confidence | 90 | 86 | -4 | 88 | 82 | -6 | usable | 0.38 |

## Policy Checks

- Default flag remains off: review
- Forced-on path changes scores and therefore needs review: passed
- QML payload shape remains compatible: passed
- Confidence remains score-neutral: passed
- Blocked-session viability stays outside category values: passed
- Planets are protected from Moon/light-pollution background: passed
- Deep-sky score remains sensitive to Moon/light pollution: passed
- ObserverCapability is not used by Advanced Observing 1.8.x: passed

## Downstream Consumer Evidence

| Consumer | Evidence |
| --- | --- |
| QML Home advanced scores | `True` |
| AppController passes advanced scores to Planner | `True` |
| Planner consumes advanced scores | `True` |
| AppController passes advanced scores to notifications | `True` |
| NotificationService consumes advanced scores | `True` |

## Default-On Risks

- Forced-on `advancedScores` are shared with Planner and NotificationService, so default-on would affect more than the Home advanced-score cards.
- Blocked sessions keep NSOM category values high/physical while legacy caps scores; UI copy needs an explicit session/actionability treatment before default-on.
- Displayed score labels still use the legacy scalar field shape; users could read NSOM category values as direct legacy-quality equivalents.

## Runtime And QML Wiring

| Check | Result |
| --- | --- |
| QML matches | `[]` |
| Runtime report imports | `[]` |

## Source Reports

- Comparison report: `docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md`.
- Policy readiness report: `docs/ADVANCED_OBSERVING_NSOM_POLICY_READINESS.md`.

## Recommended Next Step

Implement `1.8.6` as an Advanced Observing default-on readiness audit only after deciding how Planner and notifications should consume, ignore or receive a legacy-compatible copy of `advancedScores`.
