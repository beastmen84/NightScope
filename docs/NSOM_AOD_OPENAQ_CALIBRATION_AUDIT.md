# NSOM AOD/OpenAQ Calibration Audit

## Executive Summary

This developer-only audit reviews the 1.14.9 default-off AOD/OpenAQ scoring experiment across deterministic target classes, provider states and freshness cases. It does not tune weights, does not enable the feature flag and does not change runtime behaviour.

## Verdict

- Verdict: `aod_openaq_calibration_review_required`.
- Default flag: `ObservationConditionFeatureFlags.experimental_aerosol_scoring = False`.
- Default runtime score effect: `0.0`.
- Formula changed by audit: `False`.
- Weights tuned by audit: `False`.
- Ready for default-on: `False`.
- Recommended next step: Review this calibration audit, then decide whether to tune the aerosol score scale or keep the default-off formula unchanged.

## Formula Under Review

- Score modifier: `-min(penalty_cap, penalty_cap * sensitivity * severity * freshness_weight * source_weight)`.
- AOD source weight: `1.0`.
- OpenAQ PM fallback source weight: `0.6`.
- Confidence role: Provider confidence and RecommendationConfidence remain metadata. They gate eligibility but do not scale target-specific score.
- Not in formula: `provider_product_weight`, `provider_confidence_weight`, `recommendation_confidence`, `weather_factor`, `moon_geometry`, `viirs_sky_background`.

## Calibration Matrix

| Case | Target | Source | Severity | Freshness | Modifier | Score delta | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `moon_no_providers` | `moon` | `none` | `0.0` | `0.0` | `0.0` | `0` | missing_provider_inputs, neutral |
| `moon_clean_aod_current` | `moon` | `aod` | `0.0` | `1.0` | `0.0` | `0` | aod_primary, clean_aod |
| `moon_moderate_aod_current` | `moon` | `aod` | `0.5` | `1.0` | `-0.025` | `0` | aod_primary, current |
| `moon_moderate_aod_stale` | `moon` | `aod` | `0.5` | `0.5` | `-0.013` | `0` | aod_primary, stale_half_weight |
| `moon_high_aod_current` | `moon` | `aod` | `1.0` | `1.0` | `-0.05` | `0` | aod_primary, high_aod |
| `moon_high_aod_modis_confidence` | `moon` | `aod` | `1.0` | `1.0` | `-0.05` | `0` | aod_primary, product_confidence_metadata |
| `moon_local_pm_fallback` | `moon` | `particulate` | `1.0` | `1.0` | `-0.03` | `0` | aod_rejected_high_uncertainty, pm_local_fallback |
| `moon_pm_only_local` | `moon` | `particulate` | `1.0` | `1.0` | `-0.03` | `0` | pm_local_fallback |
| `moon_context_pm_rejected` | `moon` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_missing_qa, pm_context_only_rejected |
| `moon_historical_aod_no_pm` | `moon` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_historical, neutral |
| `mars_no_providers` | `planet` | `none` | `0.0` | `0.0` | `0.0` | `0` | missing_provider_inputs, neutral |
| `mars_clean_aod_current` | `planet` | `aod` | `0.0` | `1.0` | `0.0` | `0` | aod_primary, clean_aod |
| `mars_moderate_aod_current` | `planet` | `aod` | `0.5` | `1.0` | `-0.225` | `0` | aod_primary, current |
| `mars_moderate_aod_stale` | `planet` | `aod` | `0.5` | `0.5` | `-0.112` | `0` | aod_primary, stale_half_weight |
| `mars_high_aod_current` | `planet` | `aod` | `1.0` | `1.0` | `-0.45` | `0` | aod_primary, high_aod |
| `mars_high_aod_modis_confidence` | `planet` | `aod` | `1.0` | `1.0` | `-0.45` | `0` | aod_primary, product_confidence_metadata |
| `mars_local_pm_fallback` | `planet` | `particulate` | `1.0` | `1.0` | `-0.27` | `0` | aod_rejected_high_uncertainty, pm_local_fallback |
| `mars_pm_only_local` | `planet` | `particulate` | `1.0` | `1.0` | `-0.27` | `0` | pm_local_fallback |
| `mars_context_pm_rejected` | `planet` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_missing_qa, pm_context_only_rejected |
| `mars_historical_aod_no_pm` | `planet` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_historical, neutral |
| `m31_no_providers` | `galaxy` | `none` | `0.0` | `0.0` | `0.0` | `0` | missing_provider_inputs, neutral |
| `m31_clean_aod_current` | `galaxy` | `aod` | `0.0` | `1.0` | `0.0` | `0` | aod_primary, clean_aod |
| `m31_moderate_aod_current` | `galaxy` | `aod` | `0.5` | `1.0` | `-6.0` | `-6` | aod_primary, current |
| `m31_moderate_aod_stale` | `galaxy` | `aod` | `0.5` | `0.5` | `-3.0` | `-3` | aod_primary, stale_half_weight |
| `m31_high_aod_current` | `galaxy` | `aod` | `1.0` | `1.0` | `-12.0` | `-12` | aod_primary, high_aod |
| `m31_high_aod_modis_confidence` | `galaxy` | `aod` | `1.0` | `1.0` | `-12.0` | `-12` | aod_primary, product_confidence_metadata |
| `m31_local_pm_fallback` | `galaxy` | `particulate` | `1.0` | `1.0` | `-7.2` | `-7` | aod_rejected_high_uncertainty, pm_local_fallback |
| `m31_pm_only_local` | `galaxy` | `particulate` | `1.0` | `1.0` | `-7.2` | `-7` | pm_local_fallback |
| `m31_context_pm_rejected` | `galaxy` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_missing_qa, pm_context_only_rejected |
| `m31_historical_aod_no_pm` | `galaxy` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_historical, neutral |
| `m42_no_providers` | `diffuse_nebula` | `none` | `0.0` | `0.0` | `0.0` | `0` | missing_provider_inputs, neutral |
| `m42_clean_aod_current` | `diffuse_nebula` | `aod` | `0.0` | `1.0` | `0.0` | `0` | aod_primary, clean_aod |
| `m42_moderate_aod_current` | `diffuse_nebula` | `aod` | `0.5` | `1.0` | `-3.4` | `-3` | aod_primary, current |
| `m42_moderate_aod_stale` | `diffuse_nebula` | `aod` | `0.5` | `0.5` | `-1.7` | `-2` | aod_primary, stale_half_weight |
| `m42_high_aod_current` | `diffuse_nebula` | `aod` | `1.0` | `1.0` | `-6.8` | `-7` | aod_primary, high_aod |
| `m42_high_aod_modis_confidence` | `diffuse_nebula` | `aod` | `1.0` | `1.0` | `-6.8` | `-7` | aod_primary, product_confidence_metadata |
| `m42_local_pm_fallback` | `diffuse_nebula` | `particulate` | `1.0` | `1.0` | `-4.08` | `-4` | aod_rejected_high_uncertainty, pm_local_fallback |
| `m42_pm_only_local` | `diffuse_nebula` | `particulate` | `1.0` | `1.0` | `-4.08` | `-4` | pm_local_fallback |
| `m42_context_pm_rejected` | `diffuse_nebula` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_missing_qa, pm_context_only_rejected |
| `m42_historical_aod_no_pm` | `diffuse_nebula` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_historical, neutral |
| `m57_no_providers` | `planetary_nebula` | `none` | `0.0` | `0.0` | `0.0` | `0` | missing_provider_inputs, neutral |
| `m57_clean_aod_current` | `planetary_nebula` | `aod` | `0.0` | `1.0` | `0.0` | `0` | aod_primary, clean_aod |
| `m57_moderate_aod_current` | `planetary_nebula` | `aod` | `0.5` | `1.0` | `-1.375` | `-1` | aod_primary, current |
| `m57_moderate_aod_stale` | `planetary_nebula` | `aod` | `0.5` | `0.5` | `-0.688` | `-1` | aod_primary, stale_half_weight |
| `m57_high_aod_current` | `planetary_nebula` | `aod` | `1.0` | `1.0` | `-2.75` | `-3` | aod_primary, high_aod |
| `m57_high_aod_modis_confidence` | `planetary_nebula` | `aod` | `1.0` | `1.0` | `-2.75` | `-3` | aod_primary, product_confidence_metadata |
| `m57_local_pm_fallback` | `planetary_nebula` | `particulate` | `1.0` | `1.0` | `-1.65` | `-2` | aod_rejected_high_uncertainty, pm_local_fallback |
| `m57_pm_only_local` | `planetary_nebula` | `particulate` | `1.0` | `1.0` | `-1.65` | `-2` | pm_local_fallback |
| `m57_context_pm_rejected` | `planetary_nebula` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_missing_qa, pm_context_only_rejected |
| `m57_historical_aod_no_pm` | `planetary_nebula` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_historical, neutral |
| `m13_no_providers` | `globular_cluster` | `none` | `0.0` | `0.0` | `0.0` | `0` | missing_provider_inputs, neutral |
| `m13_clean_aod_current` | `globular_cluster` | `aod` | `0.0` | `1.0` | `0.0` | `0` | aod_primary, clean_aod |
| `m13_moderate_aod_current` | `globular_cluster` | `aod` | `0.5` | `1.0` | `-0.9` | `-1` | aod_primary, current |
| `m13_moderate_aod_stale` | `globular_cluster` | `aod` | `0.5` | `0.5` | `-0.45` | `0` | aod_primary, stale_half_weight |
| `m13_high_aod_current` | `globular_cluster` | `aod` | `1.0` | `1.0` | `-1.8` | `-2` | aod_primary, high_aod |
| `m13_high_aod_modis_confidence` | `globular_cluster` | `aod` | `1.0` | `1.0` | `-1.8` | `-2` | aod_primary, product_confidence_metadata |
| `m13_local_pm_fallback` | `globular_cluster` | `particulate` | `1.0` | `1.0` | `-1.08` | `-1` | aod_rejected_high_uncertainty, pm_local_fallback |
| `m13_pm_only_local` | `globular_cluster` | `particulate` | `1.0` | `1.0` | `-1.08` | `-1` | pm_local_fallback |
| `m13_context_pm_rejected` | `globular_cluster` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_missing_qa, pm_context_only_rejected |
| `m13_historical_aod_no_pm` | `globular_cluster` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_historical, neutral |
| `m45_no_providers` | `open_cluster` | `none` | `0.0` | `0.0` | `0.0` | `0` | missing_provider_inputs, neutral |
| `m45_clean_aod_current` | `open_cluster` | `aod` | `0.0` | `1.0` | `0.0` | `0` | aod_primary, clean_aod |
| `m45_moderate_aod_current` | `open_cluster` | `aod` | `0.5` | `1.0` | `-0.75` | `-1` | aod_primary, current |
| `m45_moderate_aod_stale` | `open_cluster` | `aod` | `0.5` | `0.5` | `-0.375` | `0` | aod_primary, stale_half_weight |
| `m45_high_aod_current` | `open_cluster` | `aod` | `1.0` | `1.0` | `-1.5` | `-2` | aod_primary, high_aod |
| `m45_high_aod_modis_confidence` | `open_cluster` | `aod` | `1.0` | `1.0` | `-1.5` | `-2` | aod_primary, product_confidence_metadata |
| `m45_local_pm_fallback` | `open_cluster` | `particulate` | `1.0` | `1.0` | `-0.9` | `-1` | aod_rejected_high_uncertainty, pm_local_fallback |
| `m45_pm_only_local` | `open_cluster` | `particulate` | `1.0` | `1.0` | `-0.9` | `-1` | pm_local_fallback |
| `m45_context_pm_rejected` | `open_cluster` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_missing_qa, pm_context_only_rejected |
| `m45_historical_aod_no_pm` | `open_cluster` | `none` | `0.0` | `0.0` | `0.0` | `0` | aod_historical, neutral |

## Findings

- `deep_sky_directional_penalty`: High AOD penalizes galaxies more than protected solar-system targets: galaxy modifier -12.0, planet -0.45, Moon -0.05.
- `freshness_reduces_aod_effect`: Stale AOD keeps the same source ownership but halves the current freshness effect in the representative galaxy case (-6.0 to -3.0).
- `pm_fallback_weaker_than_aod`: Local OpenAQ PM remains a weaker fallback than AOD for the same target class (-7.2 vs -12.0).
- `protected_target_rounding_visibility`: Planet and Moon aerosol modifiers are intentionally small and can round away in the integer score path, while remaining visible in developer breakdowns.

## Review Items

| Item | Severity | Blocks default-on | Reason |
| --- | --- | --- | --- |
| `aerosol-score-scale-human-calibration` | `review` | `True` | The formula is directionally tested, but absolute point scale has not been validated against observational expectations. |
| `penalty-cap-vs-transparency-shape` | `review` | `True` | The implementation uses target-class point caps and derives a transparency factor from points; calibration should confirm this shape before default-on. |
| `protected-target-small-modifier-rounding` | `note` | `False` | Some protected-target modifiers do not move the rounded integer score. This is acceptable for default-off review but should be known during calibration. Cases: moon_moderate_aod_current, moon_moderate_aod_stale, moon_high_aod_current, moon_high_aod_modis_confidence, moon_local_pm_fallback, moon_pm_only_local, mars_moderate_aod_current, mars_moderate_aod_stale, mars_high_aod_current, mars_high_aod_modis_confidence, mars_local_pm_fallback, mars_pm_only_local, m13_moderate_aod_stale, m45_moderate_aod_stale. |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `default_runtime_neutral` | `True` |
| `feature_flag_default_off` | `True` |
| `aod_primary_when_eligible` | `True` |
| `pm_fallback_when_aod_rejected` | `True` |
| `pm_context_only_rejected` | `True` |
| `historical_aod_without_pm_neutral` | `True` |
| `high_aod_target_class_order_directional` | `True` |
| `stale_aod_reduces_current_effect` | `True` |
| `pm_fallback_weaker_than_aod` | `True` |
| `provider_product_confidence_not_in_score` | `True` |
| `confidence_not_in_formula` | `True` |
| `protected_target_rounding_cases_identified` | `True` |
| `default_on_blockers_explicit` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |

## Conclusion

The 1.14.9 formula is directionally coherent and remains safely default-off. AOD and OpenAQ are not additive, local OpenAQ PM is a weaker fallback, stale data is reduced, rejected provider inputs are neutral and confidence remains metadata. The remaining work is calibration review of the score scale and protected-target rounding before any default-on decision.
