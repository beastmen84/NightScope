# Equipment NSOM Policy Readiness

## Executive Summary

This developer-only audit records the Equipment/ObserverCapability policy decision after the comparison report. It does not change `EquipmentService`, Planner, Home, Best Object, Sky Compass, Detail/Object, QML, logging, network behaviour or runtime file writes.

## Readiness Verdict

- Verdict: `equipment_nsom_policy_set_runtime_replacement_deferred`.
- Ready for default-off path: `False`.
- Ready for ObserverCapability adapter step: `True`.
- Runtime behaviour changed by this review: `False`.
- Explicit legacy default: EquipmentService.suggest_for_profile(...) remains unchanged.
- Recommended next change: Extract a shared ObserverCapability/Q_target adapter or read model from the comparison layer while keeping EquipmentService runtime setup recommendations unchanged.
- Reason: EquipmentService is still the concrete setup presenter and fallback owner. The comparison is sufficient to extract ObserverCapability/Q_target, but a default-off runtime replacement should wait for payload and environment boundaries.

## Default-Off Runtime Replacement Blockers

- `equipment-equipment-runtime-role`
- `equipment-q-target-runtime-policy`
- `equipment-seeing-policy`
- `equipment-sky-quality-policy`
- `equipment-payload-policy`
- `equipment-fallback-policy`

## Policy Decisions

| Policy | Status | NSOM layer | Blocks default-off runtime path | Decision |
| --- | --- | --- | --- | --- |
| `equipment_runtime_role` | `accepted` | `observer` | `True` | Equipment remains a practical setup helper for eyepieces, Barlow, binoculars, focal position, difficulty and setup-option payloads. |
| `observer_capability_adapter_policy` | `accepted_for_next_step` | `observer` | `False` | The next NSOM backend step should extract a shared ObserverCapability/Q_target adapter or read model from the comparison implementation. |
| `q_target_runtime_policy` | `accepted_reference_only` | `observer` | `True` | Q_target may feed PracticalTargetValue and diagnostics, but it is not sufficient by itself to rank concrete eyepiece/Barlow choices. |
| `seeing_policy` | `deferred_non_blocking` | `sky` | `True` | Seeing may remain legacy setup feasibility context for now; a future NSOM adapter must keep atmospheric conditions separate from ObserverCapability unless a narrow setup-stability field is defined. |
| `sky_quality_policy` | `accepted_for_legacy_helper_only` | `sky` | `True` | Sky quality must not change ObserverCapability; any Equipment runtime replacement would need an explicit environment input boundary rather than mixing Bortle/VIIRS into capability. |
| `payload_policy` | `accepted` | `presentation` | `True` | Any future path must preserve the existing recommendation payload shape and setupOptions roles, and expose no NSOM fields to QML in a backend migration step. |
| `fallback_policy` | `accepted` | `presentation` | `True` | Missing eyepieces, no useful configuration, naked-eye and binocular fallbacks remain owned by EquipmentService until an equivalent presenter contract exists. |
| `confidence_policy` | `accepted` | `confidence` | `False` | RecommendationConfidence remains metadata-only and never modifies Equipment setup scores, Q_target or PracticalTargetValue. |

## Recommended Policy

- Equipment runtime role: `practical_setup_helper_preserved`.
- NSOM-owned output: `ObserverCapability_profile_and_Q_target_projection`.
- First runtime-safe step: `shared_observer_capability_adapter_extraction`.
- Default-off replacement policy: `defer_until_payload_and_environment_boundaries_exist`.
- Seeing policy: `environment_or_setup_stability_context_not_capability_scalar`.
- Sky-quality policy: `ObservationEnvironment_input_not_ObserverCapability_modifier`.
- Confidence policy: `metadata_only_zero_score_effect`.
- QML payload policy: `preserve_existing_equipment_payload_no_nsom_fields`.

## Evidence From Comparison Report

- Source report: `docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md`.
- Scenario count: `5`.
- Candidate rows: `34`.
- Ranking disagreement scenarios: `['E02_open_cluster_wide_field', 'E03_galaxy_high_light_pollution', 'E04_planet_poor_seeing', 'E05_confidence_metadata']`.
- Legacy ownership mixing observed: `True`.
- Observer isolated from ObservableTargetValue: `True`.
- Confidence score effect: `0.0`.

## Readiness Checks

| Check | Result |
| --- | --- |
| `comparison_report_developer_only` | `True` |
| `comparison_report_has_no_runtime_writes` | `True` |
| `comparison_report_has_candidate_evidence` | `True` |
| `required_policy_decisions_recorded` | `True` |
| `default_off_runtime_replacement_deferred` | `True` |
| `observer_capability_adapter_ready_next` | `True` |
| `q_target_does_not_replace_setup_score` | `True` |
| `observer_isolated_from_observable` | `True` |
| `legacy_ownership_mixing_documented` | `True` |
| `confidence_score_neutral` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_review` | `True` |

## Runtime And QML Wiring

| Check | Result |
| --- | --- |
| QML matches | `[]` |
| Runtime report imports | `[]` |

## Non-Blocking Risks

- The existing setup recommendation copy and setupOptions roles are UI-facing compatibility data.
- Seeing and sky quality still affect legacy EquipmentService setup scoring and need explicit boundaries before replacement.
- A shared ObserverCapability adapter should avoid depending on private EquipmentService helper methods long term.
- Q_target can rank capability differently from legacy setup score; this is expected evidence, not a calibration target.
- A future visible UI explanation step can expose rationale only after backend semantics are stable.

## Recommended Next Step

Implement `1.12.2` as an internal ObserverCapability/Q_target adapter extraction. Keep `EquipmentService.suggest_for_profile(...)` as the runtime setup recommender and do not add a default-off Equipment replacement path yet.
