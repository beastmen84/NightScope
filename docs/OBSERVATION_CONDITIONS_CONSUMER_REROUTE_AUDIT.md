# ObservationConditions Consumer Reroute Audit

## Executive Summary

This developer-only audit reviews whether NSOM consumers should use the raw target side of the ObservationConditions read model. Home recommendedDeepSky and Best Object have now been rerouted; Sky Compass has a read-model policy and remains runtime-pending. The audit itself does not change runtime behaviour, QML, scoring, logging, network access or runtime file writes.

## Verdict

- Verdict: `sky_compass_read_model_policy_defined_runtime_pending`.
- Runtime reroute recommended now: `True`.
- Safe to change runtime in this step: `False`.
- Safe to keep current runtime temporarily: `True`.
- Recommended next step: Review the 1.12.10 Sky Compass read-model reroute policy, then implement the split adapter if accepted.
- Reason: The read-model boundary exposes raw target inputs and conditioned display targets separately. Home recommendedDeepSky now ranks the NSOM path from read_model.nsom_target_input while returning read_model.qml_display_target for payload compatibility. Best Object now scores raw read-model candidates and returns the selected display target. Sky Compass now has a policy defining raw ObservableTargetValue input plus display/live geometry and payload ownership, but runtime rerouting is still pending.

## Consumer Policies

| Consumer | Current input | Candidate input | Payload target | Status |
| --- | --- | --- | --- | --- |
| Home recommendedDeepSky | read_model.nsom_target_input | read_model.nsom_target_input | read_model.qml_display_target | `runtime_rerouted_to_raw_read_model_target` |
| Best Object | read_model.nsom_target_input for scoring | read_model.nsom_target_input for scoring | read_model.qml_display_target when selected | `runtime_rerouted_to_raw_read_model_target` |
| Sky Compass | conditioned display target for direction scoring | read_model.nsom_target_input for observable contribution plus display/live geometry | read_model.qml_display_target or current live display target | `read_model_reroute_policy_defined_runtime_pending` |

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
| `home_runtime_reroute_uses_raw_read_model_targets` | `True` |
| `home_runtime_payload_uses_display_target` | `True` |
| `best_object_policy_preserves_display_return` | `True` |
| `best_object_runtime_reroute_uses_raw_read_model_targets` | `True` |
| `best_object_runtime_returns_display_target` | `True` |
| `sky_compass_policy_keeps_display_payload` | `True` |
| `sky_compass_policy_defined_runtime_pending` | `True` |
| `sky_compass_policy_report_present` | `True` |
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
- `1.12.8 Home recommendedDeepSky raw-target reroute`: Rank Home recommendedDeepSky NSOM candidates from the raw read-model target while preserving display payload targets.
- `1.12.9 Best Object raw-target reroute`: Score Best Object NSOM candidates from raw read-model targets while returning the selected display target.
- `1.12.10 Sky Compass read-model reroute policy`: Define raw target physics vs display/live geometry ownership before changing Sky Compass runtime.

## Conclusion

The NSOM-correct direction is to score Home, Best Object and Sky Compass from raw read-model targets while preserving conditioned display targets for compatibility payloads. Home recommendedDeepSky and Best Object now follow this policy. Sky Compass now has a split policy that keeps display/live geometry separate from raw ObservableTargetValue input; runtime implementation should be a separate reviewed commit.
