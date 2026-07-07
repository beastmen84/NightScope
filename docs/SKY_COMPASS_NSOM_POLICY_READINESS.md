# Sky Compass NSOM Policy Readiness

## Executive Summary

This developer-only audit records the policy decisions needed before an experimental default-off Sky Compass NSOM path can be added. It uses the comparison report as evidence and does not change `SkyCompassService`, Home, Best Object, Planner, QML, logging, network behaviour or runtime file writes.

## Readiness Verdict

- Verdict: `ready_for_default_off_sky_compass_nsom_path`.
- Ready for default-off path: `True`.
- Ready for default-on: `False`.
- Runtime behaviour changed by this review: `False`.
- Explicit legacy default: SkyCompassService.compass(...) remains unchanged.
- Recommended next change: Add a default-off experimental Sky Compass NSOM direction policy that preserves payload shape and explicit legacy rollback.
- Reason: Sky Compass policy decisions are documented, remaining risks are non-blocking, confidence remains metadata-only, and no runtime/QML wiring exists. A separate default-off NSOM path can now be implemented.

## Default-Off Blockers

- none

## Policy Decisions

| Policy | Status | NSOM layer | Blocks default-off | Decision |
| --- | --- | --- | --- | --- |
| `sky_compass_role` | `accepted` | `presentation` | `False` | Sky Compass remains a direction and presentation policy, not a pure target-value ranking. |
| `candidate_base_policy` | `accepted_for_default_off` | `sky` | `False` | The first default-off path may use ObservableTargetValue as the candidate base for direction aggregation. |
| `context_boost_policy` | `accepted` | `presentation` | `False` | Night Plan membership and Best Object identity remain explicit presentation/context boosts outside NSOM target physics. |
| `direction_concentration_policy` | `accepted` | `presentation` | `False` | Target concentration remains a direction aggregation policy and must not be hidden inside target DTOs. |
| `practical_target_value_policy` | `deferred_non_blocking` | `observer` | `False` | PracticalTargetValue remains diagnostic/reference-only for the first default-off Sky Compass path. |
| `session_caution_policy` | `accepted` | `session` | `False` | Poor or blocked sessions remain caution/actionability metadata and do not mutate ObservableTargetValue or direction target physics. |
| `missing_location_direction_policy` | `accepted` | `presentation` | `False` | No-location and missing-direction cases continue to use the legacy empty/unavailable Sky Compass policy. |
| `qml_payload_policy` | `accepted` | `presentation` | `False` | The first default-off path must preserve the existing `skyCompass` payload keys and expose no NSOM fields to QML. |
| `fallback_policy` | `accepted` | `presentation` | `False` | Any missing runtime input or NSOM adapter failure must fall back to the current legacy SkyCompassService path. |
| `confidence_policy` | `accepted` | `confidence` | `False` | RecommendationConfidence remains metadata-only and never modifies Sky Compass direction scores. |

## Recommended Default-Off Policy

- Candidate base: `ObservableTargetValue.value`.
- Direction formula: `sum(observable_candidate_value + in_plan_bonus + best_object_bonus + target_presence_bonus) per normalized direction`.
- PracticalTargetValue use: `reference_only_for_1.9.x`.
- Session use: `caution_or_non_actionable_metadata_only`.
- Confidence use: `metadata_only_zero_score_effect`.
- QML payload policy: `preserve_existing_skyCompass_keys_no_nsom_fields`.
- Fallback policy: `legacy_sky_compass_on_missing_inputs_or_adapter_failure`.

## Evidence From Comparison Report

- Source report: `docs/SKY_COMPASS_NSOM_COMPARISON_REPORT.md`.
- Scenario count: `8`.
- Candidate row count: `48`.
- Direction differences: `3`.
- Scenarios with direction differences: `['S02_bright_moon', 'S03_high_light_pollution', 'S08_plan_best_boost']`.
- Confidence score effect: `0.0`.

## Readiness Checks

| Check | Result |
| --- | --- |
| `comparison_report_developer_only` | `True` |
| `comparison_report_has_no_runtime_writes` | `True` |
| `comparison_report_has_direction_differences` | `True` |
| `required_policy_decisions_recorded` | `True` |
| `policy_decisions_do_not_block_default_off` | `True` |
| `default_off_policy_is_not_pure_target_ranking` | `True` |
| `candidate_base_is_observable_not_practical` | `True` |
| `session_and_confidence_are_metadata` | `True` |
| `fallback_policy_recorded` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_review` | `True` |

## Runtime And QML Wiring

| Check | Result |
| --- | --- |
| QML matches | `[]` |
| Runtime report imports | `[]` |

## Non-Blocking Risks

- The current Home card copy explains direction, not NSOM score rationale.
- A future default-off path must keep the same `skyCompass` payload keys until UI design is scoped.
- Equipment-aware direction ranking is deferred because it may change the meaning of the compass.
- Plan and Best Object boosts are presentation policy and may need calibration before default-on.
- Bright sky scenarios intentionally diverge from legacy direction ranking and need human review before default-on.

## Recommended Next Step

Implement `1.9.3` as a default-off experimental Sky Compass NSOM direction policy behind an internal flag. Preserve legacy Sky Compass as the default and keep the existing `skyCompass` QML payload shape unchanged.
