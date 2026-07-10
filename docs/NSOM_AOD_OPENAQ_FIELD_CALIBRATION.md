# NSOM AOD/OpenAQ Field Calibration

## Executive Summary

This developer-only report characterizes the calibrated default-off AOD/OpenAQ scale against deterministic field-like scenarios. It does not enable AOD/OpenAQ scoring, does not change runtime behaviour and does not add network calls, logging or runtime file writes.

## Verdict

- Verdict: `aod_openaq_field_calibration_scale_acceptance_ready`.
- Ready for default-on: `False`.
- Default flag: `ObservationConditionFeatureFlags.experimental_aerosol_scoring = False`.
- Field calibration complete: `True`.
- Score scale status: `accepted_for_narrow_default_on_review`.
- Recommended next step: Review these field-calibration fixtures. If synthetic fixture bands are accepted as sufficient, proceed to a narrow default-on switch; otherwise collect real observing outcomes before enabling AOD/OpenAQ.

## Scenario Matrix

| Scenario | Target | Source | Modifier | Band | Status | Reason |
| --- | --- | --- | --- | --- | --- | --- |
| `clear_air_baseline` | `galaxy` | `clean_aod_current` | `0.0` | `0.0..0.0` | `accepted` | Clean AOD should be neutral for every target class. |
| `clear_air_baseline` | `diffuse_nebula` | `clean_aod_current` | `0.0` | `0.0..0.0` | `accepted` | Clean AOD should be neutral for every target class. |
| `clear_air_baseline` | `planet` | `clean_aod_current` | `0.0` | `0.0..0.0` | `accepted` | Clean AOD should be neutral for every target class. |
| `clear_air_baseline` | `moon` | `clean_aod_current` | `0.0` | `0.0..0.0` | `accepted` | Clean AOD should be neutral for every target class. |
| `moderate_haze_deep_sky` | `galaxy` | `moderate_aod_current` | `-4.92` | `-5.0..-0.5` | `accepted` | Moderate aerosol should affect deep-sky targets but not dominate the recommendation. |
| `moderate_haze_deep_sky` | `diffuse_nebula` | `moderate_aod_current` | `-2.788` | `-5.0..-0.5` | `accepted` | Moderate aerosol should affect deep-sky targets but not dominate the recommendation. |
| `moderate_haze_deep_sky` | `globular_cluster` | `moderate_aod_current` | `-0.738` | `-5.0..-0.5` | `accepted` | Moderate aerosol should affect deep-sky targets but not dominate the recommendation. |
| `moderate_haze_deep_sky` | `open_cluster` | `moderate_aod_current` | `-0.615` | `-5.0..-0.5` | `accepted` | Moderate aerosol should affect deep-sky targets but not dominate the recommendation. |
| `high_aod_deep_sky` | `galaxy` | `high_aod_current` | `-9.84` | `-12.0..-4.0` | `accepted` | High AOD should be a visible penalty for broad/faint deep-sky targets. |
| `high_aod_deep_sky` | `diffuse_nebula` | `high_aod_current` | `-5.576` | `-12.0..-4.0` | `accepted` | High AOD should be a visible penalty for broad/faint deep-sky targets. |
| `protected_solar_system` | `planet` | `high_aod_current` | `-0.369` | `-1.0..0.0` | `accepted` | Planets and Moon should remain protected from broad aerosol penalties. |
| `protected_solar_system` | `moon` | `high_aod_current` | `-0.041` | `-1.0..0.0` | `accepted` | Planets and Moon should remain protected from broad aerosol penalties. |
| `pm_fallback_deep_sky` | `galaxy` | `pm_only_local` | `-5.904` | `-8.0..-2.0` | `accepted` | Local OpenAQ PM fallback should be weaker than high AOD but still visible. |
| `pm_fallback_deep_sky` | `diffuse_nebula` | `pm_only_local` | `-3.346` | `-8.0..-2.0` | `accepted` | Local OpenAQ PM fallback should be weaker than high AOD but still visible. |
| `stale_aod_reduced` | `galaxy` | `moderate_aod_stale` | `-2.46` | `-3.5..-0.5` | `accepted` | Stale AOD should have reduced impact, not act like current AOD. |
| `stale_aod_reduced` | `diffuse_nebula` | `moderate_aod_stale` | `-1.394` | `-3.5..-0.5` | `accepted` | Stale AOD should have reduced impact, not act like current AOD. |
| `provider_rejected_neutral` | `galaxy` | `context_pm_rejected` | `0.0` | `0.0..0.0` | `accepted` | Context-only or rejected providers must be neutral. |
| `provider_rejected_neutral` | `diffuse_nebula` | `context_pm_rejected` | `0.0` | `0.0..0.0` | `accepted` | Context-only or rejected providers must be neutral. |
| `provider_rejected_neutral` | `planet` | `context_pm_rejected` | `0.0` | `0.0..0.0` | `accepted` | Context-only or rejected providers must be neutral. |
| `provider_rejected_neutral` | `moon` | `context_pm_rejected` | `0.0` | `0.0..0.0` | `accepted` | Context-only or rejected providers must be neutral. |

## Assessment

- Accepted rows: `20`.
- Review rows: `0`.
- Warning rows: `0`.
- Remaining blocker: `human_acceptance_or_real_field_observations`.

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `default_runtime_neutral` | `True` |
| `readiness_blocker_was_score_scale` | `True` |
| `all_rows_within_or_near_expected_band` | `True` |
| `clean_air_neutral` | `True` |
| `rejected_providers_neutral` | `True` |
| `deep_sky_more_affected_than_solar_system` | `True` |
| `pm_fallback_weaker_than_high_aod` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |

## Conclusion

The current scale passes the deterministic field-like bands used in this report. Because these are still synthetic fixtures rather than measured observing outcomes, the report does not enable AOD/OpenAQ by default. The remaining decision is whether the user accepts this scale for a narrow default-on switch or wants real field observations before enabling it.
