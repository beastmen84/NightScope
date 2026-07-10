# NSOM AOD/OpenAQ Default-On Readiness

## Executive Summary

This developer-only audit reviews whether the calibrated AOD/OpenAQ formula is ready for a default-on switch. It does not enable the flag, does not change Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment or QML, and does not add network calls, logging or runtime file writes.

## Verdict

- Verdict: `aod_openaq_default_on_blocked_by_score_scale_review`.
- Ready for default-on: `False`.
- Default flag: `ObservationConditionFeatureFlags.experimental_aerosol_scoring = False`.
- Default runtime score effect: `0.0`.
- Feature flag change in this audit: `False`.
- Formula shape calibrated: `True`.
- Remaining blocker count: `1`.
- Recommended next step: Review this readiness audit. If the aerosol score-scale risk is accepted, the next implementation step can be a narrow default-on switch; otherwise collect field-calibration fixtures first.

## Readiness Gates

| Gate | Status | Blocks default-on | Reason |
| --- | --- | --- | --- |
| `provider_quality_policy` | `accepted` | `False` | AOD QA/uncertainty/local-pixel gates and OpenAQ locality gates are explicit. |
| `source_ownership` | `accepted` | `False` | AOD is primary when eligible; OpenAQ PM is fallback/context only. |
| `formula_shape` | `accepted` | `False` | 1.14.12 maps target-class caps to transparency loss before deriving score modifier. |
| `confidence_neutrality` | `accepted` | `False` | Provider confidence gates eligibility but does not scale target-specific score. |
| `default_runtime_safety` | `accepted` | `False` | The feature flag remains false by default and default runtime score effect is 0.0. |
| `aerosol_score_scale` | `review` | `True` | The calibrated formula is directionally coherent, but the absolute score-scale impact has not been accepted against observation expectations. |

## Impact Rows

| Case | Target | Source | Transparency loss | Score modifier | Notes |
| --- | --- | --- | --- | --- | --- |
| `moon_high_aod_current` | `moon` | `aod` | `0.0005` | `-0.041` | aod_primary, high_aod |
| `mars_high_aod_current` | `planet` | `aod` | `0.0045` | `-0.369` | aod_primary, high_aod |
| `m31_high_aod_current` | `galaxy` | `aod` | `0.12` | `-9.84` | aod_primary, high_aod |
| `m31_pm_only_local` | `galaxy` | `particulate` | `0.072` | `-5.904` | pm_local_fallback |
| `m31_context_pm_rejected` | `galaxy` | `none` | `0.0` | `0.0` | aod_missing_qa, pm_context_only_rejected |
| `m42_high_aod_current` | `diffuse_nebula` | `aod` | `0.068` | `-5.576` | aod_primary, high_aod |

## Blockers

- `aerosol_score_scale`

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `feature_flag_default_off` | `True` |
| `default_runtime_neutral` | `True` |
| `provider_quality_policy_accepted` | `True` |
| `source_ownership_accepted` | `True` |
| `formula_shape_calibrated` | `True` |
| `confidence_neutral` | `True` |
| `score_scale_remains_blocking` | `True` |
| `ready_for_default_on_is_false` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |

## Conclusion

AOD/OpenAQ is not enabled by this audit. Provider-quality gates, source ownership, confidence neutrality and formula shape are now documented and tested. The only default-on blocker left by this audit is human acceptance or field validation of the absolute aerosol score scale.
