# ObservationConditions Consumer Reroute Audit

## Executive Summary

This developer-only audit reviews whether NSOM consumers should use the raw target side of the ObservationConditions read model. It does not change runtime behaviour, QML, scoring, logging, network access or runtime file writes.

## Verdict

- Verdict: `consumer_reroute_policy_defined_runtime_change_pending`.
- Runtime reroute recommended now: `False`.
- Safe to change runtime in this step: `False`.
- Safe to keep current runtime temporarily: `True`.
- Recommended next step: Review this audit, then implement read-model-aware raw target consumption one consumer at a time, starting with Home recommendedDeepSky.
- Reason: The read-model boundary exposes raw target inputs and conditioned display targets separately. Rerouting Home, Best Object or Sky Compass to raw inputs is NSOM-correct, but it can change ranking or selected objects, so it must be a separate behaviour-reviewed runtime step.

## Consumer Policies

| Consumer | Current input | Candidate input | Payload target | Status |
| --- | --- | --- | --- | --- |
| Home recommendedDeepSky | conditioned display target | read_model.nsom_target_input | read_model.qml_display_target | `ready_for_targeted_reroute_after_review` |
| Best Object | planning object from conditioned deep-sky cache | read_model.nsom_target_input for scoring | read_model.qml_display_target when selected | `requires_selection_adapter_before_reroute` |
| Sky Compass | conditioned display target for direction scoring | read_model.nsom_target_input for observable contribution | read_model.qml_display_target | `requires_direction_delta_review_before_reroute` |

## Raw Vs Display Observable Fixture

- Display observable order: `['open_cluster', 'globular_cluster', 'diffuse_nebula', 'galaxy']`.
- Raw observable order: `['open_cluster', 'globular_cluster', 'diffuse_nebula', 'galaxy']`.

| Target | Raw score | Display score | Raw observable | Display observable | Delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| jupiter | 90 | 90 | 90.000000 | 90.000000 | 0.000000 |
| moon | 82 | 82 | 82.000000 | 82.000000 | 0.000000 |
| open_cluster | 78 | 65 | 65.066556 | 54.222130 | 10.844426 |
| globular_cluster | 82 | 54 | 60.128759 | 39.596988 | 20.531771 |
| diffuse_nebula | 86 | 48 | 46.640311 | 26.031802 | 20.608510 |
| galaxy | 88 | 28 | 42.634712 | 13.565590 | 29.069122 |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `raw_observable_differs_from_display_for_conditioned_targets` | `True` |
| `solar_system_targets_are_not_conditioned` | `True` |
| `home_policy_preserves_qml_display_target` | `True` |
| `best_object_policy_requires_display_return_adapter` | `True` |
| `sky_compass_policy_keeps_display_payload` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.12.6`: Confirm the read-model boundary preserves raw and display target fields without runtime behaviour changes.
- `1.12.7 ObservationConditions consumer reroute audit`: Define the consumer policy before changing Home, Best Object or Sky Compass runtime inputs.
- `Review 1.12.7`: Confirm raw-target reroute policy and choose the first runtime consumer migration.

## Conclusion

The NSOM-correct direction is to score Home, Best Object and Sky Compass from raw read-model targets while preserving conditioned display targets for compatibility payloads. Because this can change ranking and selected objects, the runtime reroute should be implemented in a separate reviewed commit, starting with Home recommendedDeepSky.
