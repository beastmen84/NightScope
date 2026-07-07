# Advanced Observing NSOM Comparison Report

## Executive Summary

This developer-only report compares the current legacy advanced planetary/deep-sky scores with NSOM reference concepts. It does not change `AdvancedObservingService`, Home, Best Object, Planner, Sky Compass, QML, logging, network behaviour or runtime file writes.
The matrix covers 8 deterministic scenarios and 16 category rows. It exposes the legacy formula components and shows NSOM reference projections for session, sky/environment, effective observability and confidence.
Result: Advanced Observing should be migrated as a presentation/diagnostic consumer of NSOM components, not as another independent scoring owner.

## Methodology

- Uses `AdvancedObservingNsomComparisonService` with fixed in-memory fixtures only.
- Legacy formulas are shown exactly from `AdvancedObservingService`.
- NSOM projections are reference-only; score parity is not expected.
- Weather/session is shown as `SessionViability` metadata in NSOM.
- Moon and light pollution are shown as target-class sky/environment effects.
- `RecommendationConfidence` remains metadata-only with zero score effect.
- No runtime wiring, QML exposure, automatic logging, network call or runtime file write.

## Scenario Matrix

| Scenario | Sky | Session | Seeing/Transparency | Confidence | Expected behaviour |
| --- | --- | --- | --- | --- | --- |
| A01_good_session | dark_sky | good | good | high | Baseline advanced observing conditions. |
| A02_poor_weather | dark_sky | poor | good | high | Legacy scores fall through weather factors while NSOM keeps target references stable. |
| A03_blocked_session | dark_sky | blocked | good | high | Weather cap and SessionViability both expose non-actionable session pressure. |
| A04_bright_moon | bright_moon | good | good | high | Moon should affect deep-sky references more than planetary sky background. |
| A05_high_light_pollution | high_light_pollution | good | good | high | Light pollution should affect deep-sky references more than planetary references. |
| A06_poor_seeing | dark_sky | good | poor_seeing | high | Seeing should mostly pressure planetary legacy score and planetary atmospheric reference. |
| A07_poor_transparency | dark_sky | good | poor_transparency | high | Transparency should mostly pressure deep-sky legacy score and deep-sky atmospheric reference. |
| A08_low_confidence | dark_sky | good | good | low | Confidence should change metadata only. |

## Score Comparison

| Scenario | Legacy Planetary | Legacy Deep-Sky | Planet Reference OTV | Deep-Sky Avg OTV | Session | Confidence |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| A01_good_session | 90 | 88 | 86.00 | 82.00 | usable | 1.00 |
| A02_poor_weather | 43 | 43 | 86.00 | 82.00 | usable | 1.00 |
| A03_blocked_session | 20 | 20 | 86.00 | 82.00 | blocked | 1.00 |
| A04_bright_moon | 88 | 76 | 86.00 | 61.46 | usable | 1.00 |
| A05_high_light_pollution | 89 | 70 | 86.00 | 70.15 | usable | 1.00 |
| A06_poor_seeing | 66 | 88 | 30.00 | 82.00 | usable | 1.00 |
| A07_poor_transparency | 90 | 72 | 86.00 | 29.29 | usable | 1.00 |
| A08_low_confidence | 90 | 88 | 86.00 | 82.00 | usable | 0.38 |

## Legacy Formula Details

| Scenario | Category | Formula | Raw Before Cap | Weather Cap | Ownership Mixing | Unavailable Components |
| --- | --- | --- | ---: | ---: | --- | --- |
| A01_good_session | planetary | round(weather.score_value*0.36 + seeing.seeing_score*0.42 + (100-min(55, wind_kmh*1.4))*0.12 + (100-min(25, moon_illumination*0.15))*0.10), capped by weather | 90 | 100 | weather_session_mixed_into_category_score, seeing_mixed_into_category_score, moon_mixed_into_planetary_category_score | intrinsic_target_quality:not_target_specific, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A01_good_session | deep_sky | round(weather.score_value*0.34 + transparency_score*0.30 + light_pollution_quality*0.24 + (100-moon_illumination)*0.12), capped by weather | 88 | 100 | weather_session_mixed_into_category_score, transparency_mixed_into_category_score, light_pollution_mixed_into_category_score, moon_mixed_into_category_score | intrinsic_target_quality:not_target_specific, target_class_specific_sky_sensitivity:not_exposed, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A02_poor_weather | planetary | round(weather.score_value*0.36 + seeing.seeing_score*0.42 + (100-min(55, wind_kmh*1.4))*0.12 + (100-min(25, moon_illumination*0.15))*0.10), capped by weather | 68 | 43 | weather_session_mixed_into_category_score, seeing_mixed_into_category_score, moon_mixed_into_planetary_category_score | intrinsic_target_quality:not_target_specific, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A02_poor_weather | deep_sky | round(weather.score_value*0.34 + transparency_score*0.30 + light_pollution_quality*0.24 + (100-moon_illumination)*0.12), capped by weather | 69 | 43 | weather_session_mixed_into_category_score, transparency_mixed_into_category_score, light_pollution_mixed_into_category_score, moon_mixed_into_category_score | intrinsic_target_quality:not_target_specific, target_class_specific_sky_sensitivity:not_exposed, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A03_blocked_session | planetary | round(weather.score_value*0.36 + seeing.seeing_score*0.42 + (100-min(55, wind_kmh*1.4))*0.12 + (100-min(25, moon_illumination*0.15))*0.10), capped by weather | 59 | 20 | weather_session_mixed_into_category_score, seeing_mixed_into_category_score, moon_mixed_into_planetary_category_score | intrinsic_target_quality:not_target_specific, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A03_blocked_session | deep_sky | round(weather.score_value*0.34 + transparency_score*0.30 + light_pollution_quality*0.24 + (100-moon_illumination)*0.12), capped by weather | 61 | 20 | weather_session_mixed_into_category_score, transparency_mixed_into_category_score, light_pollution_mixed_into_category_score, moon_mixed_into_category_score | intrinsic_target_quality:not_target_specific, target_class_specific_sky_sensitivity:not_exposed, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A04_bright_moon | planetary | round(weather.score_value*0.36 + seeing.seeing_score*0.42 + (100-min(55, wind_kmh*1.4))*0.12 + (100-min(25, moon_illumination*0.15))*0.10), capped by weather | 88 | 100 | weather_session_mixed_into_category_score, seeing_mixed_into_category_score, moon_mixed_into_planetary_category_score | intrinsic_target_quality:not_target_specific, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A04_bright_moon | deep_sky | round(weather.score_value*0.34 + transparency_score*0.30 + light_pollution_quality*0.24 + (100-moon_illumination)*0.12), capped by weather | 76 | 100 | weather_session_mixed_into_category_score, transparency_mixed_into_category_score, light_pollution_mixed_into_category_score, moon_mixed_into_category_score | intrinsic_target_quality:not_target_specific, target_class_specific_sky_sensitivity:not_exposed, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A05_high_light_pollution | planetary | round(weather.score_value*0.36 + seeing.seeing_score*0.42 + (100-min(55, wind_kmh*1.4))*0.12 + (100-min(25, moon_illumination*0.15))*0.10), capped by weather | 89 | 100 | weather_session_mixed_into_category_score, seeing_mixed_into_category_score, moon_mixed_into_planetary_category_score | intrinsic_target_quality:not_target_specific, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A05_high_light_pollution | deep_sky | round(weather.score_value*0.34 + transparency_score*0.30 + light_pollution_quality*0.24 + (100-moon_illumination)*0.12), capped by weather | 70 | 100 | weather_session_mixed_into_category_score, transparency_mixed_into_category_score, light_pollution_mixed_into_category_score, moon_mixed_into_category_score | intrinsic_target_quality:not_target_specific, target_class_specific_sky_sensitivity:not_exposed, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A06_poor_seeing | planetary | round(weather.score_value*0.36 + seeing.seeing_score*0.42 + (100-min(55, wind_kmh*1.4))*0.12 + (100-min(25, moon_illumination*0.15))*0.10), capped by weather | 66 | 100 | weather_session_mixed_into_category_score, seeing_mixed_into_category_score, moon_mixed_into_planetary_category_score | intrinsic_target_quality:not_target_specific, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A06_poor_seeing | deep_sky | round(weather.score_value*0.34 + transparency_score*0.30 + light_pollution_quality*0.24 + (100-moon_illumination)*0.12), capped by weather | 88 | 100 | weather_session_mixed_into_category_score, transparency_mixed_into_category_score, light_pollution_mixed_into_category_score, moon_mixed_into_category_score | intrinsic_target_quality:not_target_specific, target_class_specific_sky_sensitivity:not_exposed, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A07_poor_transparency | planetary | round(weather.score_value*0.36 + seeing.seeing_score*0.42 + (100-min(55, wind_kmh*1.4))*0.12 + (100-min(25, moon_illumination*0.15))*0.10), capped by weather | 90 | 100 | weather_session_mixed_into_category_score, seeing_mixed_into_category_score, moon_mixed_into_planetary_category_score | intrinsic_target_quality:not_target_specific, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A07_poor_transparency | deep_sky | round(weather.score_value*0.34 + transparency_score*0.30 + light_pollution_quality*0.24 + (100-moon_illumination)*0.12), capped by weather | 72 | 100 | weather_session_mixed_into_category_score, transparency_mixed_into_category_score, light_pollution_mixed_into_category_score, moon_mixed_into_category_score | intrinsic_target_quality:not_target_specific, target_class_specific_sky_sensitivity:not_exposed, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A08_low_confidence | planetary | round(weather.score_value*0.36 + seeing.seeing_score*0.42 + (100-min(55, wind_kmh*1.4))*0.12 + (100-min(25, moon_illumination*0.15))*0.10), capped by weather | 90 | 100 | weather_session_mixed_into_category_score, seeing_mixed_into_category_score, moon_mixed_into_planetary_category_score | intrinsic_target_quality:not_target_specific, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |
| A08_low_confidence | deep_sky | round(weather.score_value*0.34 + transparency_score*0.30 + light_pollution_quality*0.24 + (100-moon_illumination)*0.12), capped by weather | 88 | 100 | weather_session_mixed_into_category_score, transparency_mixed_into_category_score, light_pollution_mixed_into_category_score, moon_mixed_into_category_score | intrinsic_target_quality:not_target_specific, target_class_specific_sky_sensitivity:not_exposed, observer_capability:not_part_of_advanced_scores, recommendation_confidence:not_part_of_advanced_scores |

## Main Mismatches

- Legacy advanced scores mix weather/session directly into both category scores.
- Legacy deep-sky score has one broad scalar for galaxy, nebula and cluster classes.
- Legacy planetary score includes a Moon component even though NSOM protects planets from sky-background damage.
- Weather caps duplicate session viability and can hide whether the limiting factor is sky or actionability.
- Legacy advanced scores do not expose observer capability or confidence as separate concepts.

## NSOM Behaviour Checks

- Bright Moon lowers deep-sky reference OTV: passed
- Bright Moon leaves planet sky background protected: passed
- High light pollution lowers deep-sky reference OTV: passed
- Blocked weather changes session viability but not reference observable values: passed
- Changing confidence alone does not change reference observable values: passed

## Semantic Recommendation

- Classification: `presentation diagnostic / category quality surface`.
- Recommended migration target: `NSOM-derived category diagnostics with separate session policy`.
- Reason: Advanced Observing produces user-facing category badges rather than a target ranking. It should consume NSOM sky/session components instead of owning independent Moon, weather and transparency penalties.
- Runtime score replacement ready: `False`.
- Confidence score effect: `0.0`.

## Recommended Next Steps

1. Review whether advanced scores should become NSOM-derived presentation diagnostics.
2. Decide whether planetary and deep-sky category badges should consume session viability or show it separately.
3. Add a default-off Advanced Observing NSOM path only after score-display semantics are decided.
