# NSOM AOD/OpenAQ Scoring Readiness

## Executive Summary

This developer-only audit reviews whether provider-dependent NASA AOD and OpenAQ particulate inputs are ready to affect NSOM scores. They are not enabled for scoring in this step. The current runtime keeps AOD and PM score-neutral, does not change Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment or QML, and does not add network calls, logging or runtime file writes.

## Verdict

- Verdict: `aod_openaq_policy_hardened_ready_for_default_off_experiment`.
- Experimental aerosol scoring default: `False`.
- Current runtime score effect: `0.0`.
- Ready for default-on: `False`.
- Ready for default-off experiment: `True`.
- Score formula implemented: `False`.
- Recommended next step: Review 1.14.8, then implement a default-off aerosol scoring experiment if the provider-quality policy is accepted.
- Reason: NASA AOD and OpenAQ PM inputs are already adapted as diagnostic Sky/Confidence data. AOD QA/uncertainty, OpenAQ locality and double-counting now have explicit policy gates, but the scoring formula remains intentionally unimplemented and disabled.

## Provider Contracts

| Provider | Source | Runtime role | Freshness policy | Scoring status | Blocker |
| --- | --- | --- | --- | --- | --- |
| `nasa_aod` | NASA Earthdata MAIAC AOD; VIIRS primary, MODIS fallback | Weather page display plus diagnostic AodConditionInput | include current/stale inputs up to seven days; omit historical | policy-hardened and score-neutral; modifier remains 0.0 | none for default-off experiment; formula still not implemented |
| `openaq_particulate` | OpenAQ PM2.5/PM10 nearest local stations | Weather page display plus diagnostic ParticulateConditionInput | current <=1 day, recent <=3 days, stale <=7 days, historical omitted | policy-hardened fallback/context and score-neutral; modifier remains 0.0 | none for default-off experiment; formula still not implemented |

## Freshness Policy

| Input | Age/category | Weight | Current scoring role |
| --- | --- | --- | --- |
| `nasa_aod` | `0 days` | `1.0` | diagnostic confidence only |
| `nasa_aod` | `3 days` | `1.0` | diagnostic confidence only |
| `nasa_aod` | `4 days` | `0.5` | diagnostic confidence only |
| `nasa_aod` | `7 days` | `0.5` | diagnostic confidence only |
| `nasa_aod` | `7.01 days` | `0.0` | diagnostic confidence only |
| `nasa_aod` | `historical` | `0.0` | diagnostic confidence only |
| `openaq_particulate` | `0 days` | `1.0` | diagnostic confidence only |
| `openaq_particulate` | `1 day` | `1.0` | diagnostic confidence only |
| `openaq_particulate` | `2 days` | `0.7` | diagnostic confidence only |
| `openaq_particulate` | `4 days` | `0.3` | diagnostic confidence only |
| `openaq_particulate` | `7 days` | `0.3` | diagnostic confidence only |
| `openaq_particulate` | `7.01 days` | `0.0` | diagnostic confidence only |
| `openaq_particulate` | `historical` | `0.0` | diagnostic confidence only |

## Target Sensitivity Characterization

| Target class | Sensitivity | Penalty cap | AOD role | PM role | Scoring status |
| --- | --- | --- | --- | --- | --- |
| `moon` | `0.05` | `1.0` | minor/protected candidate | metadata/context only | characterized only; no score effect |
| `planet` | `0.15` | `3.0` | minor/protected candidate | metadata/context only | characterized only; no score effect |
| `globular_cluster` | `0.45` | `4.0` | secondary aerosol/transparency candidate | low/medium fallback when fresh AOD is unavailable | characterized only; no score effect |
| `open_cluster` | `0.5` | `3.0` | secondary aerosol/transparency candidate | low/medium fallback when fresh AOD is unavailable | characterized only; no score effect |
| `planetary_nebula` | `0.55` | `5.0` | secondary aerosol/transparency candidate | low/medium fallback when fresh AOD is unavailable | characterized only; no score effect |
| `diffuse_nebula` | `0.85` | `8.0` | primary aerosol/transparency candidate | fallback/context when fresh AOD is unavailable | characterized only; no score effect |
| `galaxy` | `1.0` | `12.0` | primary aerosol/transparency candidate | fallback/context when fresh AOD is unavailable | characterized only; no score effect |

## Source Precedence

| Case | AOD freshness | PM freshness | Primary source | Reason |
| --- | --- | --- | --- | --- |
| `fresh_aod_and_pm` | `current` | `current` | `aod` | fresh AOD is the column aerosol source; PM remains fallback/context |
| `historical_aod_fresh_pm` | `historical` | `current` | `particulate` | historical AOD is not eligible; PM can be the fallback source |
| `fresh_aod_missing_pm` | `current` | `missing` | `aod` | AOD can stand alone when fresh enough |
| `no_eligible_provider` | `historical` | `historical` | `none` | historical provider data remains metadata only |

## Score Neutrality

| Case | Target | AOD | PM | Flag off modifier | Flag on modifier | Adjusted score delta |
| --- | --- | --- | --- | --- | --- | --- |
| `galaxy_high_aerosol` | `galaxy` | `available` | `available` | `0.0` | `0.0` | `0` |
| `diffuse_nebula_high_aerosol` | `diffuse_nebula` | `available` | `available` | `0.0` | `0.0` | `0` |
| `planet_protected` | `planet` | `available` | `available` | `0.0` | `0.0` | `0` |
| `moon_protected` | `moon` | `available` | `available` | `0.0` | `0.0` | `0` |
| `missing_providers` | `globular_cluster` | `missing` | `missing` | `0.0` | `0.0` | `0` |

## Policy Decisions

| Decision | Status | Blocks scoring | Affected layer | Reason |
| --- | --- | --- | --- | --- |
| `aod_qa_policy` | `accepted_for_default_off_experiment` | `False` | Sky / ObservationEnvironment | AOD requires finite value, freshness, QA raw traceability, uncertainty threshold and pixel support. |
| `aod_pm_source_precedence` | `accepted_for_readiness` | `False` | Sky / Confidence | Fresh AOD is primary; PM is fallback/context when AOD is unavailable or historical. |
| `openaq_locality_policy` | `accepted_for_default_off_experiment` | `False` | Sky / Confidence | OpenAQ PM is eligible only as local fallback within 25 km; 25-50 km remains context only. |
| `double_counting_policy` | `accepted_for_default_off_experiment` | `False` | Sky / Session | AOD and PM are not additive; VIIRS, weather transparency and Moon geometry keep separate ownership. |
| `confidence_metadata_policy` | `accepted` | `False` | Confidence | Provider freshness and availability remain metadata and do not change score. |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `source_markers_all_found` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `aod_and_openaq_are_external` | `True` |
| `freshness_policy_has_historical_zero` | `True` |
| `target_sensitivity_order_characterized` | `True` |
| `aod_primary_pm_fallback` | `True` |
| `aerosol_modifier_score_neutral` | `True` |
| `provider_quality_policy_accepted` | `True` |
| `double_counting_policy_accepted` | `True` |
| `confidence_metadata_policy_accepted` | `True` |

## Blockers

- None.

## Conclusion

AOD/OpenAQ should remain score-neutral until a separate default-off experiment introduces a formula. The provider-quality blockers from 1.14.7 now have explicit policy gates: AOD QA/uncertainty, OpenAQ locality and freshness, and non-overlap with VIIRS sky background, weather transparency and Moon geometry.
