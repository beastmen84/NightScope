# Equipment Setup Score Component Boundary

## Executive Summary

This developer-only report verifies that EquipmentService setup scoring now exposes an immutable component read-model while preserving current score values. It does not add an Equipment replacement path, QML fields, logging, network calls or runtime file writes.

## Verdict

- Verdict: `equipment_setup_score_component_boundary_introduced`.
- Runtime replacement ready: `False`.
- Component read-model present: `True`.
- Default-off Equipment path recommended now: `False`.
- Runtime behaviour changed by boundary: `False`.
- Recommended next step: Review 1.13.5, then choose the next backend NSOM area or run an overall backend readiness audit.
- Reason: Equipment setup scoring now has an immutable component read-model with parity against the current EquipmentService score. This makes ownership visible but does not yet define a replacement policy.

## Read-Model Boundary

- Class: `EquipmentSetupScoreReadModel`.
- Builder: `EquipmentSetupScoreReadModelBuilder`.
- Runtime owner: `EquipmentService._configuration_score`.
- Formula: `angular_scale + magnification + exit_pupil + light_gathering + seeing_compatibility + handling`.
- Score policy: `sum_components_clamped_0_100`.
- NSOM policy: `setup_score_component_boundary_not_nsom_target_value`.
- Confidence policy: `parallel_metadata_zero_score_effect`.

| Component | Weight |
| --- | ---: |
| `angular_scale` | 24 |
| `magnification` | 24 |
| `exit_pupil` | 16 |
| `light_gathering` | 16 |
| `seeing_compatibility` | 10 |
| `handling` | 10 |

## Parity

- Scenario count: `5`.
- Candidate row count: `34`.
- All rows expose read-model: `True`.
- All read-model scores match candidate scores: `True`.
- All read-model component values match legacy component projection: `True`.
- Max score delta: `0.000000000000`.

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `component_weights_sum_to_100` | `True` |
| `component_order_complete` | `True` |
| `score_read_model_present_in_comparison` | `True` |
| `score_read_model_matches_candidate_scores` | `True` |
| `component_values_match_legacy_projection` | `True` |
| `confidence_score_neutral` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_boundary` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.13.5`: Confirm Equipment is closed setup-local and no runtime path changed.
- `Next backend NSOM area selection audit`: Choose the next backend NSOM area or run an overall backend readiness audit before visible UI/explanation work.

## Conclusion

The setup-score component boundary is now explicit and parity-checked. The score remains Equipment-owned setup logic, not an NSOM target value or confidence modifier.
