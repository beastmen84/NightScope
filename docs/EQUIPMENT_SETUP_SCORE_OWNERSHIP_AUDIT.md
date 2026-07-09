# Equipment Setup Score Ownership Audit

## Executive Summary

This developer-only audit classifies the current EquipmentService setup-score components from EquipmentService._configuration_score before any scoring replacement. It does not change EquipmentService, Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, QML, logging, network behaviour or runtime file writes.

## Verdict

- Verdict: `equipment_setup_score_ownership_audited`.
- Runtime replacement ready: `False`.
- Score component boundary recommended: `True`.
- Default-off Equipment path recommended now: `False`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next step: Review 1.13.4, then close the Equipment backend NSOM migration as setup-local with NSOM boundaries.
- Reason: EquipmentService setup score is useful and deterministic, but its single scalar mixes target traits, observer configuration, seeing, sky quality and presentation practicality. The 1.13.3 component read-model makes that boundary explicit; replacement still needs a separate policy audit.

## Current Formula

- Formula: `angular_scale + magnification + exit_pupil + light_gathering + seeing_compatibility + handling`.
- Total weight: `100.0`.
- Source: `astro_viewer/app/services/equipment_service.py`.

| Component | Weight | Current inputs | NSOM ownership | Replacement policy |
| --- | ---: | --- | --- | --- |
| `angular_scale` | 24 | target apparent size, true field, target profile mode | universe, observer, presentation/setup | Keep as setup compatibility; do not fold into ObservableTargetValue. |
| `magnification` | 24 | configuration magnification, target profile idealMag | observer, presentation/setup | Keep as setup compatibility; Q_target may reference capability but must not replace focal-position selection. |
| `exit_pupil` | 16 | configuration exit pupil, target profile idealExit, sky-adjusted profile | observer, sky, presentation/setup | Requires explicit setup context because sky quality can alter ideal exit pupil. |
| `light_gathering` | 16 | aperture/objective, target magnitude, surface brightness proxy, sky quality | universe, observer, sky | Split before replacement; target faintness and sky quality cannot be hidden inside observer capability. |
| `seeing_compatibility` | 10 | configuration magnification, seeing-limited maxUsefulMag | sky, session, observer, presentation/setup | Keep separate from ObserverCapability until seeing/session ownership is explicit. |
| `handling` | 10 | Barlow multiplier, binocular stabilization, target profile barlowFriendly | observer, presentation/setup | Presentation/practical setup factor; not target physics and not RecommendationConfidence. |

## Component Statistics

| Component | Average | Max | Appears in rows |
| --- | ---: | ---: | ---: |
| `angular_scale` | 22.17 | 24.00 | 34 |
| `magnification` | 10.21 | 24.00 | 34 |
| `exit_pupil` | 8.25 | 16.00 | 34 |
| `light_gathering` | 14.78 | 16.00 | 34 |
| `seeing_compatibility` | 8.33 | 10.00 | 34 |
| `handling` | 9.58 | 10.00 | 34 |

## Scenario Evidence

| Scenario | Rows | Score sums match | Main mixed components |
| --- | ---: | --- | --- |
| E01_planet_mixed_equipment | 16 | `True` | angular_scale, magnification, light_gathering |
| E02_open_cluster_wide_field | 5 | `True` | angular_scale, magnification, exit_pupil |
| E03_galaxy_high_light_pollution | 4 | `True` | angular_scale, magnification, light_gathering |
| E04_planet_poor_seeing | 5 | `True` | angular_scale, magnification, light_gathering |
| E05_confidence_metadata | 4 | `True` | angular_scale, magnification, light_gathering |

## Decision Log

| Decision | Status | Blocks replacement | Reason |
| --- | --- | --- | --- |
| `equipment_score_scalar_policy` | `needs_component_boundary` | `True` | The current scalar is a setup-local score, not NSOM target value, PracticalTargetValue or RecommendationConfidence. |
| `sky_and_seeing_ownership` | `needs_explicit_setup_context` | `True` | Sky quality and seeing affect the legacy score and must be visible as setup context before replacement. |
| `q_target_replacement_policy` | `rejected_as_direct_replacement` | `True` | Q_target lacks eyepiece, focal-position, Barlow and fallback semantics. |
| `component_coverage` | `covered` | `False` | 6 score components are classified. |
| `confidence_policy` | `accepted_metadata_only` | `False` | RecommendationConfidence remains parallel metadata with zero score effect. |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `formula_components_match_equipment_service` | `True` |
| `component_weights_sum_to_100` | `True` |
| `all_component_sums_match_scores` | `True` |
| `all_components_block_replacement_until_boundary` | `True` |
| `sky_and_seeing_not_hidden_in_observer_capability` | `True` |
| `q_target_not_direct_replacement` | `True` |
| `confidence_score_neutral` | `True` |
| `setup_read_model_boundary_present` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.13.2`: Confirm setup-score ownership is classified correctly and does not imply score tuning.
- `1.13.3 Equipment setup-score component boundary`: Extract a runtime-neutral setup-score component read-model with parity tests before any replacement path.
- `Review 1.13.4`: Confirm Equipment should remain setup-local with NSOM boundaries.
- `1.13.5 Equipment NSOM migration closeout`: Close Equipment as an NSOM-bounded setup service.

## Conclusion

EquipmentService should not be replaced by Q_target or by a raw NSOM target-value score. The setup-score component boundary is now explicit, and the default-off path policy keeps Equipment setup-local.
