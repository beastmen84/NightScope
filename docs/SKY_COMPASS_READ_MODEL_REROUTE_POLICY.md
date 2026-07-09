# Sky Compass Read-Model Reroute Policy

## Executive Summary

This developer-only policy defines how Sky Compass should consume the ObservationConditions read model in a later runtime step. It does not change Sky Compass runtime behaviour, QML, logging, network access or runtime file writes.

## Verdict

- Verdict: `sky_compass_read_model_policy_defined_runtime_pending`.
- Runtime reroute ready for next step: `True`.
- Runtime changed by this step: `False`.
- Recommended next step: Review this policy, then implement a Sky Compass read-model adapter that uses raw target physics for ObservableTargetValue and display/live targets for geometry and payload compatibility.
- Reason: Sky Compass is a direction/presentation surface. Replacing the candidate with the raw target would avoid display-score reuse, but it could also drop display/live direction, visibility and current-position data. The safe policy is a split adapter.

## Policy Decisions

| Boundary | Source | Runtime role | Reason |
| --- | --- | --- | --- |
| ObservableTargetValue target physics | read_model.nsom_target_input | NSOM score contribution | Avoid reusing condition-adjusted display score as intrinsic target value. |
| Direction grouping | current display/live target | Sky Compass direction and zone grouping | Direction can change during live refresh and belongs to current geometry, not raw catalogue value. |
| Visibility and horizon geometry | current display/live target | Candidate eligibility and horizon context | Live position refresh can update visible state and altitude without recomputing raw target data. |
| QML payload | read_model.qml_display_target or current live display target | Existing target card fields | Payload keys, display score and labels must remain compatible. |
| Night Plan and Best Object boosts | target id context | Presentation/context boost | Plan and Best Object membership are not target physics and should stay outside ObservableTargetValue. |
| Missing read-model fallback | current display/live target | Compatibility fallback | Plan-only or live-refreshed candidates may lack a read-model row and must remain renderable. |

## Fixture Evidence

- Raw observable value: `46.631716`.
- Display observable value: `16.956988`.
- Raw minus display observable: `29.674728`.
- Raw direction: `Sud`.
- Display direction: `Sud`.
- Live direction: `Sud-Ovest`.
- Policy observable source: `read_model.nsom_target_input`.
- Policy geometry source: `current_display_or_live_target`.
- Policy payload source: `read_model.qml_display_target_or_live_display_target`.

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `raw_observable_differs_from_display` | `True` |
| `observable_target_physics_uses_raw` | `True` |
| `direction_grouping_uses_live_display_geometry` | `True` |
| `visibility_horizon_uses_live_display_geometry` | `True` |
| `payload_uses_display_target` | `True` |
| `context_boosts_remain_presentation` | `True` |
| `missing_read_model_fallback_defined` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_policy` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.
- Current runtime uses conditioned/display candidates: `True`.
- Live refresh updates current candidate geometry: `True`.
- Current NSOM service computes observable from candidate object: `True`.

## Recommended Sequence

- `Review 1.12.9`: Confirm Best Object raw-target scoring and display target return.
- `1.12.10 Sky Compass read-model reroute policy`: Define raw target physics vs display/live geometry ownership before runtime changes.
- `1.12.11 Sky Compass read-model reroute`: Implement the policy if review accepts the split adapter.

## Conclusion

Sky Compass should not be rerouted by passing only raw targets to the existing service. The next runtime step should introduce a small adapter that joins raw NSOM target input with display/live geometry and payload data by target id.
