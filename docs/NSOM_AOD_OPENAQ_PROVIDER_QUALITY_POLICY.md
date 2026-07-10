# NSOM AOD/OpenAQ Provider Quality Policy

## Executive Summary

This developer-only policy hardening step resolves the AOD/OpenAQ provider-quality decisions that blocked a future default-off aerosol scoring experiment. It does not enable scoring by default, does not change Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment or QML, and does not add network calls, automatic logging or runtime file writes.

## Verdict

- Verdict: `aod_openaq_provider_quality_policy_hardened`.
- Ready for default-off experiment: `True`.
- Ready for default-on: `False`.
- Scoring formula implemented: `True`.
- Scoring formula enabled: `False`.
- Current runtime score effect: `0.0`.
- Experimental aerosol scoring default: `False`.
- Recommended next step: Review 1.14.9, then audit/calibrate the default-off aerosol scoring experiment before any default-on switch.
- Reason: AOD QA/uncertainty, OpenAQ locality and source double-counting have explicit policy gates. Target-specific AOD/OpenAQ scoring now exists only behind the default-off experimental flag, while the provider-quality policy itself remains target-neutral.

## Policy Thresholds

| Threshold | Value |
| --- | --- |
| `aod_max_value` | `3.0` |
| `aod_max_uncertainty` | `0.15` |
| `aod_local_neighborhood_min_pixels` | `3` |
| `openaq_local_representative_km` | `25.0` |
| `openaq_context_only_km` | `50.0` |

## Scenario Decisions

| Case | Primary source | AOD role | AOD eligible | PM role | PM eligible | Score modifier | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `fresh_viirs_aod_local_pm` | `aod` | `primary_aerosol_column` | `True` | `fallback_ground_particulate` | `True` | `0.0` | aod_primary_pm_context_only |
| `aod_high_uncertainty_pm_local_fallback` | `particulate` | `metadata_only` | `False` | `fallback_ground_particulate` | `True` | `0.0` | aod_uncertainty_missing_or_high, aod_rejected_pm_fallback |
| `aod_missing_qa_pm_local_fallback` | `particulate` | `metadata_only` | `False` | `fallback_ground_particulate` | `True` | `0.0` | aod_qa_raw_missing, aod_rejected_missing_qa |
| `aod_sparse_neighborhood_pm_local_fallback` | `particulate` | `metadata_only` | `False` | `fallback_ground_particulate` | `True` | `0.0` | aod_local_neighborhood_too_sparse, aod_rejected_sparse_local_pixels |
| `historical_aod_local_pm` | `particulate` | `metadata_only` | `False` | `fallback_ground_particulate` | `True` | `0.0` | aod_not_fresh_enough, historical_aod_not_primary |
| `missing_aod_local_pm` | `particulate` | `missing` | `False` | `fallback_ground_particulate` | `True` | `0.0` | aod_missing, pm_fallback_when_aod_missing |
| `missing_aod_context_distance_pm` | `none` | `missing` | `False` | `metadata_only` | `False` | `0.0` | aod_missing, openaq_context_distance_not_scoring_representative, pm_context_only_not_scoring_representative |
| `missing_aod_distant_pm` | `none` | `missing` | `False` | `metadata_only` | `False` | `0.0` | aod_missing, openaq_too_distant, pm_rejected_too_distant |
| `missing_aod_unknown_distance_pm` | `none` | `missing` | `False` | `metadata_only` | `False` | `0.0` | aod_missing, openaq_distance_unknown, pm_rejected_unknown_distance |
| `no_provider_data` | `none` | `missing` | `False` | `missing` | `False` | `0.0` | aod_missing, particulate_missing, no_aerosol_provider_for_scoring |

## Double-Counting Policy

- `aod_and_particulate_are_not_additive`
- `fresh_aod_owns_column_aerosol_when_policy_eligible`
- `openaq_pm_is_fallback_or_context_only`
- `viirs_sky_background_remains_separate`
- `weather_transparency_remains_separate`
- `moon_geometry_remains_separate`

## Confidence Policy

- `provider_quality_changes_confidence_metadata_only`
- `provider_quality_does_not_change_target_specific_score`
- `recommendation_confidence_remains_score_neutral`

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `fresh_aod_is_primary` | `True` |
| `pm_is_fallback_when_aod_rejected` | `True` |
| `pm_context_distance_not_fallback` | `True` |
| `distant_pm_rejected` | `True` |
| `unknown_distance_pm_rejected` | `True` |
| `targetless_policy_score_modifier_neutral` | `True` |
| `forced_flag_marks_formula_enabled` | `True` |
| `double_counting_policy_present` | `True` |

## Conclusion

The provider-quality blockers are now explicit policy gates. Fresh, QA-traceable, low-uncertainty AOD is the only primary aerosol-column source for a future experiment; OpenAQ PM can only be local fallback/context when AOD is not policy-eligible. VIIRS sky background, weather transparency and Moon geometry remain separate owners. The target-specific formula is available only through the explicit default-off experiment flag.
