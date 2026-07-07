# Advanced Observing NSOM Presentation Readiness

## Executive Summary

This developer-only audit checks whether Advanced Observing NSOM can be enabled by default after the 1.8.7 consumer split. It does not change the flag, tune scores, expose QML, log automatically, call the network or write runtime files. Planner and NotificationService are protected by legacy-compatible consumer inputs, but the NSOM category values are still private diagnostics with no presentation contract.

## Readiness Verdict

- Verdict: `not_ready_for_advanced_observing_nsom_default_on`.
- Ready for default-on switch: `False`.
- Current default flag: `NSOM_ADVANCED_OBSERVING_ENABLED = False`.
- Default flag currently enabled: `False`.
- Requires separate flag change: `True`.
- Runtime behaviour changed by this audit: `False`.
- Consumer split resolved: `True`.
- Recommended switch change: do not set NSOM_ADVANCED_OBSERVING_ENABLED = True yet; implement a presentation contract for NSOM Advanced Observing first
- Reason: Planner and NotificationService are protected by the consumer split, but the forced-on NSOM Advanced Observing values are still a private snapshot with no QML/presentation contract. Enabling the flag now would not complete the Advanced Observing migration.

## Default-On Blockers

- `advanced-observing-nsom-snapshot-visibility`
- `advanced-observing-nsom-presentation-contract`
- `advanced-observing-score-label-semantics`

## Presentation Decisions

| Decision | Status | Blocks default-on | Summary |
| --- | --- | --- | --- |
| `legacy_advanced_scores_cards` | `accepted_current_runtime_contract` | `False` | Keep existing Home advanced score cards legacy-compatible for now. |
| `nsom_snapshot_visibility` | `hidden_internal_only` | `True` | Do not expose `_advanced_observing_nsom_scores` to QML in this step. |
| `nsom_presentation_contract` | `needs_design_before_default_on` | `True` | Define whether Advanced Observing NSOM is hidden diagnostics or user-facing category guidance. |
| `score_label_semantics` | `needs_copy_policy_before_default_on` | `True` | Resolve `/100` score and label wording before showing NSOM category values. |
| `downstream_consumer_split` | `resolved` | `False` | Planner and NotificationService receive legacy-compatible consumer scores. |
| `confidence_policy` | `accepted` | `False` | RecommendationConfidence remains metadata-only. |

## Presentation Evidence

- QML reads existing `advancedScores`: `True`.
- QML reads NSOM Advanced Observing snapshot: `False`.
- Public advancedScores payload keys: `['planetary_score', 'deep_sky_score', 'planetary_label', 'deep_sky_label', 'explanation', 'planetaryScore', 'deepSkyScore', 'planetaryLabel', 'deepSkyLabel']`.
- Forced-on NSOM snapshot differs from legacy scores: `True`.
- Forced-on NSOM snapshot has presentation effect: `False`.
- Hidden snapshot blocks meaningful default-on switch: `True`.
- Confidence score-neutral: `True`.

## Checks

| Check | Result |
| --- | --- |
| `default_flag_still_off` | `True` |
| `downstream_consumer_split_resolved` | `True` |
| `required_presentation_decisions_recorded` | `True` |
| `existing_qml_payload_remains_legacy_compatible` | `True` |
| `existing_qml_advanced_scores_still_used` | `True` |
| `nsom_snapshot_not_qml_exposed` | `True` |
| `hidden_snapshot_blocks_default_on` | `True` |
| `presentation_contract_blocks_default_on` | `True` |
| `score_label_semantics_blocks_default_on` | `True` |
| `confidence_score_neutral` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_nsom_exposure_absent` | `True` |
| `runtime_behaviour_unchanged` | `True` |

## Runtime And QML Wiring

- QML NSOM exposure matches: `[]`.
- Runtime report imports: `[]`.
- Controller internal snapshot present: `True`.
- Controller public NSOM Advanced Observing property present: `False`.

## Recommended Next Step

Implement `1.8.9` as an Advanced Observing NSOM presentation contract design step: either keep NSOM hidden as developer diagnostics, or add a separate QML-safe NSOM explanation/payload with explicit labels before any default-on switch.
