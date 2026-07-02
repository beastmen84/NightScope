# Home NSOM Comparison Report

## Executive Summary

This developer-only report compares the current Home `recommendedDeepSky` ordering with NSOM `ObservableTargetValue` ordering. It does not change Home ranking, Best Object selection, Sky Compass, QML, logging, network behaviour or runtime file writes.
The matrix covers 7 deterministic scenarios and 28 deep-sky candidate rows. `PracticalTargetValue` is shown for inspection only and is not used as the proposed Home ranking decision.
Result: `recommendedDeepSky` looks safe to migrate behind a default-off flag only after the ordering differences below are reviewed. The first runtime migration should use `ObservableTargetValue`, not `PracticalTargetValue` or `ObservationOpportunity`.

## Methodology

- Uses `HomeNsomComparisonService` with fixed in-memory fixtures only.
- Compares current Home deep-sky Moon-adjusted legacy order with NSOM `ObservableTargetValue` order.
- Shows `PracticalTargetValue` separately to inspect equipment sensitivity before Home uses it.
- Marks legacy components unavailable instead of reconstructing non-existent breakdowns.
- Keeps `RecommendationConfidence` as metadata only with zero score effect.
- No runtime wiring, QML exposure, automatic logging, network call or runtime file write.

## Scenario Matrix

| Scenario | Sky | Session | Equipment | Confidence | Expected behaviour |
| --- | --- | --- | --- | --- | --- |
| H01_bright_moon | bright_moon | good | medium_telescope | high | Moon-sensitive deep-sky classes should move through sky-owned NSOM factors. |
| H02_dark_sky | dark_sky | good | medium_telescope | high | Baseline should show limited sky degradation. |
| H03_high_light_pollution | high_light_pollution | good | medium_telescope | high | NSOM should expose static sky background where legacy Home Moon adjustment does not. |
| H04_poor_weather | dark_sky | poor | medium_telescope | high | Weather should stay outside Home ObservableTargetValue in this comparison. |
| H05_blocked_session | dark_sky | blocked | medium_telescope | high | Blocked session should not mutate Home ObservableTargetValue. |
| H06_small_equipment | dark_sky | good | small_telescope | high | Equipment should change PracticalTargetValue only. |
| H07_large_equipment | dark_sky | good | large_telescope | high | Large equipment should change PracticalTargetValue only. |

## Ordering Comparison

| Scenario | Legacy Home Order | NSOM Observable Order | Order Changed | Practical Top |
| --- | --- | --- | --- | --- |
| H01_bright_moon | open_cluster > globular_cluster > diffuse_nebula > galaxy | open_cluster > globular_cluster > diffuse_nebula > galaxy | no | open_cluster |
| H02_dark_sky | galaxy > diffuse_nebula > globular_cluster > open_cluster | galaxy > diffuse_nebula > globular_cluster > open_cluster | no | globular_cluster |
| H03_high_light_pollution | galaxy > diffuse_nebula > globular_cluster > open_cluster | globular_cluster > open_cluster > diffuse_nebula > galaxy | yes | globular_cluster |
| H04_poor_weather | galaxy > diffuse_nebula > globular_cluster > open_cluster | galaxy > diffuse_nebula > globular_cluster > open_cluster | no | globular_cluster |
| H05_blocked_session | galaxy > diffuse_nebula > globular_cluster > open_cluster | galaxy > diffuse_nebula > globular_cluster > open_cluster | no | globular_cluster |
| H06_small_equipment | galaxy > diffuse_nebula > globular_cluster > open_cluster | galaxy > diffuse_nebula > globular_cluster > open_cluster | no | diffuse_nebula |
| H07_large_equipment | galaxy > diffuse_nebula > globular_cluster > open_cluster | galaxy > diffuse_nebula > globular_cluster > open_cluster | no | globular_cluster |

## Candidate Details

| Scenario | Target | Legacy Adjusted | Mutation Delta | Observable | Practical | Legacy Unavailable Components |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| H01_bright_moon | galaxy | 53.00 | -35.00 | 51.94 | 31.82 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H01_bright_moon | diffuse_nebula | 62.00 | -24.00 | 55.02 | 33.07 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H01_bright_moon | open_cluster | 69.00 | -9.00 | 69.34 | 44.37 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H01_bright_moon | globular_cluster | 67.00 | -17.00 | 67.83 | 43.08 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H02_dark_sky | galaxy | 88.00 | 0.00 | 84.91 | 52.01 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H02_dark_sky | diffuse_nebula | 86.00 | 0.00 | 83.41 | 50.13 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H02_dark_sky | open_cluster | 78.00 | 0.00 | 77.06 | 49.32 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H02_dark_sky | globular_cluster | 84.00 | 0.00 | 82.48 | 52.39 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H03_high_light_pollution | galaxy | 88.00 | 0.00 | 66.62 | 40.81 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H03_high_light_pollution | diffuse_nebula | 86.00 | 0.00 | 68.09 | 40.92 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H03_high_light_pollution | open_cluster | 78.00 | 0.00 | 71.50 | 45.76 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H03_high_light_pollution | globular_cluster | 84.00 | 0.00 | 73.50 | 46.69 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H04_poor_weather | galaxy | 88.00 | 0.00 | 84.91 | 52.01 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H04_poor_weather | diffuse_nebula | 86.00 | 0.00 | 83.41 | 50.13 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H04_poor_weather | open_cluster | 78.00 | 0.00 | 77.06 | 49.32 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H04_poor_weather | globular_cluster | 84.00 | 0.00 | 82.48 | 52.39 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H05_blocked_session | galaxy | 88.00 | 0.00 | 84.91 | 52.01 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H05_blocked_session | diffuse_nebula | 86.00 | 0.00 | 83.41 | 50.13 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H05_blocked_session | open_cluster | 78.00 | 0.00 | 77.06 | 49.32 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H05_blocked_session | globular_cluster | 84.00 | 0.00 | 82.48 | 52.39 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H06_small_equipment | galaxy | 88.00 | 0.00 | 84.91 | 48.16 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H06_small_equipment | diffuse_nebula | 86.00 | 0.00 | 83.41 | 50.52 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H06_small_equipment | open_cluster | 78.00 | 0.00 | 77.06 | 49.90 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H06_small_equipment | globular_cluster | 84.00 | 0.00 | 82.48 | 42.45 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H07_large_equipment | galaxy | 88.00 | 0.00 | 84.91 | 62.76 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H07_large_equipment | diffuse_nebula | 86.00 | 0.00 | 83.41 | 57.99 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H07_large_equipment | open_cluster | 78.00 | 0.00 | 77.06 | 55.17 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |
| H07_large_equipment | globular_cluster | 84.00 | 0.00 | 82.48 | 66.37 | weather_session_component:not_part_of_home_deep_sky_adjustment, observer_capability_component:not_part_of_home_deep_sky_adjustment |

## Main Ordering Differences

- `H03_high_light_pollution` changes top candidate from `galaxy` to `globular_cluster`; `PracticalTargetValue` remains inspection-only.

## Legacy Score Mutation Notes

Current Home deep-sky conditioning returns replacement `CelestialObject` instances with adjusted `score` and `score_label`. The original runtime objects are not mutated by this report, but the Home presentation path does rank by the adjusted replacement score.
- `H01_bright_moon:galaxy` legacy Home adjusted score 88 -> 53 (delta -35).
- `H01_bright_moon:diffuse_nebula` legacy Home adjusted score 86 -> 62 (delta -24).
- `H01_bright_moon:open_cluster` legacy Home adjusted score 78 -> 69 (delta -9).
- `H01_bright_moon:globular_cluster` legacy Home adjusted score 84 -> 67 (delta -17).

## Confidence Control

Changing only confidence keeps `ObservableTargetValue` delta `0.0000` and `PracticalTargetValue` delta `0.0000`. Confidence remains metadata-only and is not a ranking factor.

## Migration Readiness

- RecommendedDeepSky safe behind flag: `True`.
- Use `ObservableTargetValue` as the first candidate ranking value.
- Keep `PracticalTargetValue` comparison-only until equipment-driven Home semantics are reviewed.
- Do not use session/weather or `ObservationOpportunity` for base Home ranking in the first migration.

## Recommended Next Steps

1. Add a default-off Home NSOM flag around `recommendedDeepSky` ordering only.
2. Preserve current legacy Home order as rollback and comparison baseline.
3. Add runtime characterization tests before exposing any QML-visible ordering change.
