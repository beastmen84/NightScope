# ObservationConditions NSOM Read-Model Audit

## Executive Summary

This developer-only audit reviews the active ObservationConditions runtime boundary after Sky Map and Notifications were removed as dead legacy. It does not change runtime behaviour, QML, scoring, logging, network access or runtime file writes.

## Verdict

- Verdict: `read_model_boundary_introduced_consumer_reroute_pending`.
- Runtime migration recommended now: `False`.
- Safe to remove service: `False`.
- Safe to keep current runtime temporarily: `True`.
- Recommended next step: Review the 1.12.6 boundary, then decide whether NSOM Home, Best Object and Sky Compass consumers can read raw read-model targets without changing presentation payloads unexpectedly.
- Reason: ObservationConditionsService is active runtime code. It returns replacement CelestialObject instances for Moon and light-pollution presentation compatibility, and those conditioned objects can become inputs to default-on NSOM Home/Best Object/Sky Compass observable calculations. The 1.12.6 boundary now preserves raw and display targets separately, but runtime consumer rerouting remains a separate behaviour-changing review.

## Blockers

- `observation-conditions-conditioned-score-as-nsom-intrinsic`
- `observation-conditions-deep-sky-cache-is-condition-adjusted`

## Ownership

- Current owner: `ObservationConditionsService`.
- Owns today: `['Moon-adjusted display score copies', 'light-pollution display/context copies', 'AOD/PM/Moon-geometry score-neutral diagnostics', 'double-counting condition flags']`.
- Should not own: `['ObserverCapability', 'PracticalTargetValue', 'SessionViability', 'RecommendationConfidence aggregation', 'Planner chronology', 'visible QML field design']`.
- Target state: A read model with raw_target, condition_breakdown, display_score, display_notes, condition_flags and NSOM-safe raw ObservableTargetValue input.

## Runtime Consumers

| Consumer | Uses conditioned object | Uses NSOM observable | Current risk |
| --- | --- | --- | --- |
| Home recommendedDeepSky | `True` | `True` | Default-on Home NSOM ranks ObservableTargetValue from the current deep-sky candidate objects; those objects may already carry condition-adjusted display scores. |
| Best Object | `True` | `True` | Best Object receives planning objects from the controller deep-sky cache, so condition-adjusted score can become intrinsic target input. |
| Sky Compass | `True` | `True` | Sky Compass intentionally uses the conditioned cache for display compatibility, but NSOM direction policy also computes observable values from those targets. |
| Detail/Object selectedObject | `True` | `False` | Visible Detail keeps a moon-adjusted compatibility display score; future visible NSOM detail fields need a separate raw/read-model input. |
| Planner | `False` | `False` | Planner has its own NSOM path and should not consume conditioned Home display objects as target physics. |

## Phenomenon Fixture

- Raw score: `88`.
- Pollution-conditioned score: `44`.
- Moon-conditioned score: `54`.
- Combined-conditioned score: `10`.
- Raw ObservableTargetValue: `42.634712`.
- Pollution-conditioned ObservableTargetValue: `21.317356`.
- Combined-conditioned ObservableTargetValue: `0.0`.
- NSOM conditioned-score input risk: `True`.
- Original target mutated: `False`.
- Pollution reapply guarded: `True`.

## Read-Model Boundary

- Object id: `m31`.
- Raw score: `88`.
- Display score: `10`.
- Applied components: `['moon', 'light_pollution']`.
- Condition flags: `['light_pollution']`.
- Raw target preserved for NSOM input: `True`.
- QML display target preserved: `True`.
- NSOM input uses raw target: `True`.
- Strict JSON compatible: `True`.

## Checks

| Check | Result |
| --- | --- |
| `service_is_active_runtime_code` | `True` |
| `conditioned_caches_present` | `True` |
| `pollution_context_writes_deep_sky_cache` | `True` |
| `home_nsom_can_consume_conditioned_candidates` | `False` |
| `best_object_can_consume_pollution_conditioned_deep_sky` | `True` |
| `sky_compass_uses_conditioned_cache` | `True` |
| `service_uses_replacement_not_mutation` | `True` |
| `service_preserves_original_target_reference` | `True` |
| `double_count_guard_present_for_pollution` | `True` |
| `nsom_conditioned_score_input_risk_visible` | `True` |
| `read_model_boundary_present` | `True` |
| `read_model_strict_json_compatible` | `True` |
| `read_model_display_score_separate_from_raw_score` | `True` |
| `aod_pm_score_neutral_today` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.12.5`: Confirm the ObservationConditions audit correctly identifies active consumers and read-model risks.
- `1.12.6 ObservationConditions read-model boundary`: Introduce explicit raw/display/conditioned fields without changing visible ranking or QML payload shape.
- `Review 1.12.6`: Verify NSOM consumers read raw target inputs while legacy display compatibility reads display fields.

## Conclusion

ObservationConditions is not dead legacy. The 1.12.6 read-model boundary now preserves raw and display targets separately, while runtime consumer rerouting remains a separate behaviour-reviewed step before condition-adjusted CelestialObject scores can be fully removed from NSOM intrinsic input paths.
