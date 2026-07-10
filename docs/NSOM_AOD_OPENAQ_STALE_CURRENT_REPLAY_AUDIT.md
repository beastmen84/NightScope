# NSOM AOD/OpenAQ Stale-vs-Current Replay Audit

## Executive Summary

This developer-only audit replays the checked-in expanded real-provider AOD/OpenAQ evidence with only one change: policy-eligible stale AOD rows are treated as current to measure the score effect of `freshness_weight=1.0` versus `0.5`. It does not call NASA/OpenAQ, does not enable aerosol scoring, and does not change Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment or QML.

## Verdict

- Verdict: `aod_openaq_stale_policy_ready_for_default_on_review`.
- Ready for default-on review: `True`.
- Default-on enabled by this audit: `False`.
- Default flag: `ObservationConditionFeatureFlags.experimental_aerosol_scoring = False`.
- Default runtime score effect: `0.0`.
- Stale AOD weight policy: `keep_stale_aod_weight_0_5`.
- Recommended next step: Review this replay audit. If accepted, the next implementation step can be a narrow AOD/OpenAQ default-on switch.
- Reason: Replaying the checked-in real AOD values as current keeps the score effect bounded and target-specific. The stale 0.5 weight is therefore a reasonable conservative runtime policy.

## Formula

- Replay change: Only AOD freshness is changed from stale weight 0.5 to current weight 1.0.
- Score modifier: `-target_score * min(max_transparency_loss, max_transparency_loss * sensitivity * severity * freshness_weight * source_weight)`.
- Source scope: AOD-source rows only; particulate and none rows are unchanged.
- Confidence role: RecommendationConfidence and provider confidence remain metadata only.

## Summary

- AOD source location count: `8`.
- AOD replay row count: `48`.
- Stale deep-sky max penalty: `-3.69`.
- Current replay deep-sky max penalty: `-7.38`.
- Stale solar-system max penalty: `-0.139`.
- Current replay solar-system max penalty: `-0.277`.
- Max additional deep-sky penalty: `-3.69`.
- Max additional solar-system penalty: `-0.138`.
- Max current/stale non-zero ratio: `2.003`.
- Zero-effect AOD locations preserved: `['Cairo, Egypt', 'Cape Town, South Africa', 'Los Angeles, USA', 'Mauna Kea, USA', 'San Pedro de Atacama, Chile']`.
- Particulate rows unchanged: `True`.
- None-source rows unchanged: `True`.

## Readiness Gates

| Gate | Status | Blocks default-on | Reason | Evidence |
| --- | --- | --- | --- | --- |
| `offline_replay_only` | `accepted` | `False` | The replay uses checked-in provider evidence and performs no network work. | docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_PROBE.md |
| `stale_weight_policy` | `accepted` | `False` | Stale AOD at weight 0.5 should be a conservative half-strength version of current AOD. | max_ratio=2.003 |
| `current_replay_score_scale` | `accepted` | `False` | Treating the same real AOD as current should keep deep-sky impact bounded. | aod_current_deep_sky=-7.38 |
| `protected_target_current_replay` | `accepted` | `False` | Planets and Moon should remain protected even when real AOD is replayed as current. | aod_current_solar_system=-0.277 |
| `zero_effect_aod_preserved` | `accepted` | `False` | Low/clean AOD-source locations should stay neutral after current replay. | locations=('Cairo, Egypt', 'Cape Town, South Africa', 'Los Angeles, USA', 'Mauna Kea, USA', 'San Pedro de Atacama, Chile') |
| `fallback_sources_unchanged` | `accepted` | `False` | Changing AOD freshness must not alter PM fallback or no-source rows. | particulate=True, none=True |
| `confidence_neutrality` | `accepted` | `False` | Confidence remains metadata and is not a replay score factor. | confidence_score_neutral=True |

## Representative Replay Rows

| Location | Target | Source | Stale modifier | Current replay modifier | Additional penalty |
| --- | --- | --- | --- | --- | --- |
| San Pedro de Atacama, Chile | `galaxy` | `aod` | `0.0` | `0.0` | `0.0` |
| San Pedro de Atacama, Chile | `planet` | `aod` | `0.0` | `0.0` | `0.0` |
| San Pedro de Atacama, Chile | `moon` | `aod` | `0.0` | `0.0` | `0.0` |
| Mauna Kea, USA | `galaxy` | `aod` | `0.0` | `0.0` | `0.0` |
| Mauna Kea, USA | `planet` | `aod` | `0.0` | `0.0` | `0.0` |
| Mauna Kea, USA | `moon` | `aod` | `0.0` | `0.0` | `0.0` |
| Addis Ababa, Ethiopia | `galaxy` | `aod` | `-3.69` | `-7.38` | `-3.69` |
| Addis Ababa, Ethiopia | `planet` | `aod` | `-0.139` | `-0.277` | `-0.138` |
| Addis Ababa, Ethiopia | `moon` | `aod` | `-0.016` | `-0.031` | `-0.015` |
| Cairo, Egypt | `galaxy` | `aod` | `0.0` | `0.0` | `0.0` |
| Cairo, Egypt | `planet` | `aod` | `0.0` | `0.0` | `0.0` |
| Cairo, Egypt | `moon` | `aod` | `0.0` | `0.0` | `0.0` |
| Marrakech, Morocco | `galaxy` | `aod` | `-2.46` | `-4.92` | `-2.46` |
| Marrakech, Morocco | `planet` | `aod` | `-0.092` | `-0.184` | `-0.092` |
| Marrakech, Morocco | `moon` | `aod` | `-0.011` | `-0.021` | `-0.01` |
| Los Angeles, USA | `galaxy` | `aod` | `0.0` | `0.0` | `0.0` |
| Los Angeles, USA | `planet` | `aod` | `0.0` | `0.0` | `0.0` |
| Los Angeles, USA | `moon` | `aod` | `0.0` | `0.0` | `0.0` |
| Singapore, Singapore | `galaxy` | `aod` | `-3.69` | `-7.38` | `-3.69` |
| Singapore, Singapore | `planet` | `aod` | `-0.139` | `-0.277` | `-0.138` |
| Singapore, Singapore | `moon` | `aod` | `-0.016` | `-0.031` | `-0.015` |
| Cape Town, South Africa | `galaxy` | `aod` | `0.0` | `0.0` | `0.0` |
| Cape Town, South Africa | `planet` | `aod` | `0.0` | `0.0` | `0.0` |
| Cape Town, South Africa | `moon` | `aod` | `0.0` | `0.0` | `0.0` |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `feature_flag_default_off` | `True` |
| `default_runtime_neutral` | `True` |
| `aod_replay_rows_present` | `True` |
| `stale_weight_doubles_nonzero_effect_at_most` | `True` |
| `current_replay_score_scale_accepted` | `True` |
| `protected_targets_remain_protected` | `True` |
| `pm_and_none_rows_unchanged` | `True` |
| `confidence_neutral` | `True` |
| `ready_for_default_on_review` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |

## Conclusion

The replay supports keeping stale AOD at half weight. If those same AOD values were current, the strongest deep-sky penalty would remain bounded, low-AOD AOD-source locations would still be neutral, and protected solar-system targets would remain only minimally affected. The audit therefore removes stale/current freshness as a technical blocker, while keeping the actual default flag off for a separate reviewed switch.
