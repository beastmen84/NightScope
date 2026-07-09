# NSOM AOD/OpenAQ Scoring Readiness

## Executive Summary

This developer-only audit reviews whether provider-dependent NASA AOD and OpenAQ particulate inputs are ready to affect NSOM scores. They are not enabled for scoring in this step. The current runtime keeps AOD and PM score-neutral, does not change Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment or QML, and does not add network calls, logging or runtime file writes.

## Verdict

- Verdict: `aod_openaq_scoring_blocked_pending_provider_quality_policy`.
- Experimental aerosol scoring default: `False`.
- Current runtime score effect: `0.0`.
- Ready for default-on: `False`.
- Ready for default-off experiment: `False`.
- Score formula implemented: `False`.
- Recommended next step: Implement AOD/OpenAQ provider-quality policy hardening before any default-off scoring path.
- Reason: NASA AOD and OpenAQ PM inputs are already adapted as diagnostic Sky/Confidence data with freshness and source precedence, but formal AOD QA/uncertainty policy and double-counting policy must be hardened before they can influence ObservationEnvironment.

## Provider Contracts

| Provider | Source | Runtime role | Freshness policy | Scoring status | Blocker |
| --- | --- | --- | --- | --- | --- |
| `nasa_aod` | NASA Earthdata MAIAC AOD; VIIRS primary, MODIS fallback | Weather page display plus diagnostic AodConditionInput | include current/stale inputs up to seven days; omit historical | score-neutral; modifier remains 0.0 | formal AOD_QA bit decoding and uncertainty policy before scoring |
| `openaq_particulate` | OpenAQ PM2.5/PM10 nearest local stations | Weather page display plus diagnostic ParticulateConditionInput | current <=1 day, recent <=3 days, stale <=7 days, historical omitted | score-neutral; modifier remains 0.0 | station locality/representativeness and fallback policy before scoring |

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
| `aod_qa_policy` | `needs_policy_before_scoring` | `True` | Sky / ObservationEnvironment | Formal AOD_QA bit decoding and uncertainty thresholds are required before score use. |
| `aod_pm_source_precedence` | `accepted_for_readiness` | `False` | Sky / Confidence | Fresh AOD is primary; PM is fallback/context when AOD is unavailable or historical. |
| `openaq_locality_policy` | `needs_policy_before_scoring` | `True` | Sky / Confidence | PM station distance/representativeness must be explicit before score use. |
| `double_counting_policy` | `needs_policy_before_scoring` | `True` | Sky / Session | Aerosol, VIIRS sky background, weather transparency and Moon geometry need non-overlap rules. |
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
| `provider_quality_blockers_explicit` | `True` |
| `double_counting_blocker_explicit` | `True` |
| `confidence_metadata_policy_accepted` | `True` |

## Blockers

- `aod_qa_policy`
- `openaq_locality_policy`
- `double_counting_policy`

## Conclusion

AOD/OpenAQ should remain score-neutral for now. The next useful backend step is not formula tuning; it is provider-quality policy hardening: formal AOD QA/uncertainty handling, OpenAQ locality and freshness policy, and explicit double-counting rules with VIIRS sky background, weather transparency and Moon geometry.
