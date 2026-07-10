# NSOM AOD/OpenAQ Real-Provider Readiness Audit

## Executive Summary

This developer-only audit reviews the expanded real NASA Earthdata AOD and OpenAQ probe before any AOD/OpenAQ default-on decision. It reads the checked-in provider report as evidence, does not call the network, does not enable aerosol scoring, and does not change Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment or QML.

## Verdict

- Verdict: `aod_openaq_default_on_deferred_for_temporal_provider_evidence`.
- Ready for default-on: `False`.
- Default flag: `ObservationConditionFeatureFlags.experimental_aerosol_scoring = False`.
- Default runtime score effect: `0.0`.
- Feature flag change in this audit: `False`.
- Recommended next step: Repeat the real-provider probe on another date/time or explicitly accept stale-AOD runtime policy. Only then consider a narrow default-on switch.
- Reason: The expanded real-provider probe resolves the score-scale review with modest target-specific effects, but all usable AOD inputs in the checked-in provider run are stale and the evidence is still a single temporal snapshot.

## Evidence Summary

- Source report: `docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_PROBE.md`.
- Location set: `expanded`.
- Location count: `15`.
- Policy source counts: `{'aod': 8, 'none': 2, 'particulate': 5}`.
- NASA AOD status counts: `{'download_error': 1, 'no_valid_pixel': 2, 'ok': 12}`.
- OpenAQ status counts: `{'historical': 5, 'ok': 7, 'unavailable': 3}`.
- AOD freshness counts: `{'none': 3, 'stale': 12}`.
- PM input freshness counts: `{'current': 7, 'none': 8}`.
- Locations with provider data and zero score effect: `['San Pedro de Atacama, Chile', 'Mauna Kea, USA', 'Cairo, Egypt', 'Los Angeles, USA', 'Cape Town, South Africa', 'Reykjavik, Iceland']`.
- Locations with non-zero aerosol effect: `['New Delhi, India', 'Addis Ababa, Ethiopia', 'Marrakech, Morocco', 'Beijing, China', 'Tokyo, Japan', 'Singapore, Singapore', 'Sydney, Australia']`.
- Deep-sky max penalty: `-3.69`.
- Solar-system max penalty: `-0.139`.

## Readiness Gates

| Gate | Status | Blocks default-on | Reason | Evidence |
| --- | --- | --- | --- | --- |
| `expanded_real_provider_coverage` | `accepted` | `False` | The checked-in probe should cover the expanded 15-location set. | location_count=15 |
| `policy_branch_coverage` | `accepted` | `False` | Real data should exercise AOD, OpenAQ PM fallback and no-source neutrality. | policy_source_counts={'aod': 8, 'none': 2, 'particulate': 5} |
| `real_provider_score_scale` | `accepted` | `False` | Expanded real-provider effects should remain modest, target-specific and stronger for deep-sky targets than for protected solar-system targets. | deep_sky=-3.69, solar_system=-0.139 |
| `provider_rejection_and_fallback_policy` | `accepted` | `False` | Rejected/missing AOD should either remain neutral or fall back to local OpenAQ PM without additive double-counting. | policy_source_counts={'aod': 8, 'none': 2, 'particulate': 5} |
| `zero_effect_provider_success` | `accepted` | `False` | Clean/low provider data must be allowed to produce no score change. | locations=('San Pedro de Atacama, Chile', 'Mauna Kea, USA', 'Cairo, Egypt', 'Los Angeles, USA', 'Cape Town, South Africa', 'Reykjavik, Iceland') |
| `credential_and_runtime_safety` | `accepted` | `False` | The report must remain developer-only with no credential values or runtime wiring. | safety={'runtime_behaviour_changed': False, 'qml_exposure': False, 'network': True, 'automatic_logging': False, 'persistent_writes': False, 'credential_values_stored_in_report': False} |
| `aod_current_coverage_absent` | `review` | `True` | The expanded real-provider run contains usable stale AOD but no current AOD input, so runtime behaviour under fresh AOD is not confirmed by real provider evidence. | aod_freshness_counts={'none': 3, 'stale': 12} |
| `single_snapshot_repeatability` | `review` | `True` | The checked-in evidence is one provider snapshot. Provider availability, AOD freshness and OpenAQ coverage should be repeated or explicitly accepted before default-on. | real_provider_probe_runs=1 |

## Blockers

- `aod_current_coverage_absent`
- `single_snapshot_repeatability`

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `feature_flag_default_off` | `True` |
| `default_runtime_neutral` | `True` |
| `source_report_exists` | `True` |
| `expanded_location_count_is_15` | `True` |
| `all_policy_sources_observed` | `True` |
| `score_scale_resolved_by_real_provider_probe` | `True` |
| `zero_effect_provider_success_observed` | `True` |
| `rejection_and_fallback_observed` | `True` |
| `has_no_current_aod_input` | `True` |
| `all_aod_inputs_are_stale_or_missing` | `True` |
| `temporal_evidence_still_blocks_default_on` | `True` |
| `ready_for_default_on_is_false` | `True` |
| `confidence_neutral_notes_present` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |

## Conclusion

The real-provider evidence is directionally coherent and the absolute score scale no longer looks like the blocker: low/clean provider successes stay neutral, deep-sky targets receive the largest effect, and protected solar-system targets remain nearly neutral. The default-on decision is still deferred because this checked-in evidence contains no current AOD input and represents one provider snapshot only.
