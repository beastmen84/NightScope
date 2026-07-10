# NSOM AOD/OpenAQ Default-Off Scoring Experiment

## Executive Summary

This developer-only report documents the 1.14.9 default-off AOD/OpenAQ scoring experiment. The implementation adds a target-specific aerosol modifier only when `ObservationConditionFeatureFlags.experimental_aerosol_scoring` is explicitly enabled. The default runtime keeps the flag off, so Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment and QML behaviour remain unchanged.

## Verdict

- Verdict: `aod_openaq_default_off_scoring_experiment_implemented`.
- Default flag: `ObservationConditionFeatureFlags.experimental_aerosol_scoring = False`.
- Default runtime score effect: `0.0`.
- Ready for default-on: `False`.
- Recommended next step: Review 1.14.9, then audit calibration and default-on readiness for provider-backed aerosol scoring.

## Formula

- AOD severity: 0.0 if AOD <= 0.10; 0.25 if <= 0.20; 0.50 if <= 0.35; 0.75 if <= 0.60; 1.00 otherwise.
- PM severity: max(PM2.5 severity, PM10 severity).
- Source policy: policy-eligible AOD primary; local policy-eligible OpenAQ PM fallback only.
- Score modifier: `-target_score * min(max_transparency_loss, max_transparency_loss * sensitivity * severity * freshness_weight * source_weight)`.
- Max transparency loss: `penalty_cap / 100`.
- Source weights: AOD `1.0`, PM `0.6`.
- Confidence role: RecommendationConfidence and provider confidence remain outside the score formula.

## Cases

| Case | Target class | Default delta | Experimental source | Experimental modifier | Notes |
| --- | --- | --- | --- | --- | --- |
| `fresh_aod_galaxy` | `galaxy` | `0` | `aod` | `-7.38` | aod_primary, deep_sky_sensitive |
| `fresh_aod_diffuse_nebula` | `diffuse_nebula` | `0` | `aod` | `-4.182` | aod_primary, nebula_sensitive |
| `fresh_aod_planet` | `planet` | `0` | `aod` | `-0.276` | aod_primary, planet_protected |
| `fresh_aod_moon` | `moon` | `0` | `aod` | `-0.031` | aod_primary, moon_protected |
| `pm_fallback_galaxy` | `galaxy` | `0` | `particulate` | `-4.428` | aod_rejected, pm_local_fallback |
| `rejected_sources_neutral` | `galaxy` | `0` | `none` | `0.0` | aod_missing_qa, pm_context_only |
| `confidence_product_neutral` | `galaxy` | `0` | `aod` | `-7.38` | modis_product_confidence_not_score_modifier |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `default_runtime_neutral` | `True` |
| `aod_is_primary_when_eligible` | `True` |
| `pm_is_fallback_when_aod_rejected` | `True` |
| `rejected_sources_remain_neutral` | `True` |
| `deep_sky_more_sensitive_than_planet_moon` | `True` |
| `confidence_not_in_formula` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |

## Conclusion

The experiment is implemented but intentionally default-off. AOD owns the aerosol-column contribution when provider-quality gates pass; OpenAQ PM is a weaker local fallback only. VIIRS sky brightness, Moon geometry, weather/session state and RecommendationConfidence remain separate NSOM owners.
