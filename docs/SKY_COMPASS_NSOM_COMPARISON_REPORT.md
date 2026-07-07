# Sky Compass NSOM Comparison Report

## Executive Summary

This developer-only report compares the current Sky Compass direction ranking with NSOM target and direction reference values. It does not change Sky Compass runtime output, Home, Best Object, Planner, QML, logging, network behaviour or runtime file writes.
The matrix covers 8 deterministic scenarios and 48 candidate rows. Legacy direction ranking is compared with NSOM `ObservableTargetValue` and `PracticalTargetValue` direction references.
Result: Sky Compass is not a pure target-value ranker. It is a direction/presentation policy that combines prepared candidate score, Night Plan membership, Best Object status and target concentration.

## Methodology

- Uses `SkyCompassNsomComparisonService` with fixed in-memory fixtures only.
- Repeats the current legacy direction formula without changing runtime output.
- Shows NSOM Observable and Practical direction references separately.
- Marks unavailable legacy components instead of reconstructing upstream score details.
- Keeps SessionViability and RecommendationConfidence as metadata only.
- No controller/QML import, automatic logging, network call or runtime file write.

## Scenario Matrix

| Scenario | Sky | Session | Equipment | Context | Expected behaviour |
| --- | --- | --- | --- | --- | --- |
| S01_dark_sky | dark_sky | good | medium_telescope | none | Baseline should show current direction policy and NSOM direction references. |
| S02_bright_moon | bright_moon | good | medium_telescope | none | Moon-sensitive deep-sky targets should degrade through NSOM sky ownership only. |
| S03_high_light_pollution | high_light_pollution | good | medium_telescope | none | Static sky background should affect NSOM references, not legacy direction formula. |
| S04_poor_weather | dark_sky | poor | medium_telescope | none | Poor weather should remain session/caution metadata for Sky Compass. |
| S05_blocked_session | dark_sky | blocked | medium_telescope | none | Blocked weather should not mutate target or direction physics. |
| S06_small_equipment | dark_sky | good | small_telescope | none | Equipment should change PracticalTargetValue references only. |
| S07_large_equipment | dark_sky | good | large_telescope | none | Large equipment should change PracticalTargetValue references only. |
| S08_plan_best_boost | dark_sky | good | medium_telescope | plan_best | Plan membership and Best Object identity should be visible as presentation boosts. |

## Direction Ranking Comparison

| Scenario | Legacy Direction Order | NSOM Observable Direction Reference | NSOM Practical Direction Reference | Legacy Top | Observable Top |
| --- | --- | --- | --- | --- | --- |
| S01_dark_sky | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Est > Ovest | Sud | Sud |
| S02_bright_moon | Sud > Nord-Est > Est > Ovest | Nord-Est > Sud > Est > Ovest | Nord-Est > Sud > Est > Ovest | Sud | Nord-Est |
| S03_high_light_pollution | Sud > Nord-Est > Est > Ovest | Nord-Est > Sud > Est > Ovest | Nord-Est > Sud > Est > Ovest | Sud | Nord-Est |
| S04_poor_weather | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Est > Ovest | Sud | Sud |
| S05_blocked_session | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Est > Ovest | Sud | Sud |
| S06_small_equipment | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Ovest > Est | Sud | Sud |
| S07_large_equipment | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Est > Ovest | Sud | Sud |
| S08_plan_best_boost | Nord-Est > Sud > Est > Ovest | Sud > Nord-Est > Est > Ovest | Sud > Nord-Est > Est > Ovest | Nord-Est | Sud |

## Candidate Details

| Scenario | Target | Direction | Legacy Contribution | Observable | Practical | Session | Confidence |
| --- | --- | --- | ---: | ---: | ---: | --- | ---: |
| S01_dark_sky | jupiter | Est | 96.00 | 86.00 | 47.30 | usable | 1.00 |
| S01_dark_sky | moon | Ovest | 92.00 | 82.00 | 46.13 | usable | 1.00 |
| S01_dark_sky | galaxy | Sud | 100.00 | 86.84 | 53.20 | usable | 1.00 |
| S01_dark_sky | diffuse_nebula | Sud | 98.00 | 85.35 | 51.29 | usable | 1.00 |
| S01_dark_sky | open_cluster | Nord-Est | 88.00 | 77.06 | 50.63 | usable | 1.00 |
| S01_dark_sky | globular_cluster | Nord-Est | 94.00 | 82.48 | 52.39 | usable | 1.00 |
| S02_bright_moon | jupiter | Est | 96.00 | 86.00 | 47.30 | usable | 1.00 |
| S02_bright_moon | moon | Ovest | 92.00 | 82.00 | 46.13 | usable | 1.00 |
| S02_bright_moon | galaxy | Sud | 100.00 | 53.12 | 32.54 | usable | 1.00 |
| S02_bright_moon | diffuse_nebula | Sud | 98.00 | 56.30 | 33.84 | usable | 1.00 |
| S02_bright_moon | open_cluster | Nord-Est | 88.00 | 69.34 | 45.56 | usable | 1.00 |
| S02_bright_moon | globular_cluster | Nord-Est | 94.00 | 67.83 | 43.08 | usable | 1.00 |
| S03_high_light_pollution | jupiter | Est | 96.00 | 86.00 | 47.30 | usable | 1.00 |
| S03_high_light_pollution | moon | Ovest | 92.00 | 82.00 | 46.13 | usable | 1.00 |
| S03_high_light_pollution | galaxy | Sud | 100.00 | 68.13 | 41.74 | usable | 1.00 |
| S03_high_light_pollution | diffuse_nebula | Sud | 98.00 | 69.67 | 41.87 | usable | 1.00 |
| S03_high_light_pollution | open_cluster | Nord-Est | 88.00 | 71.50 | 46.98 | usable | 1.00 |
| S03_high_light_pollution | globular_cluster | Nord-Est | 94.00 | 73.50 | 46.69 | usable | 1.00 |
| S04_poor_weather | jupiter | Est | 96.00 | 86.00 | 47.30 | usable | 1.00 |
| S04_poor_weather | moon | Ovest | 92.00 | 82.00 | 46.13 | usable | 1.00 |
| S04_poor_weather | galaxy | Sud | 100.00 | 86.84 | 53.20 | usable | 1.00 |
| S04_poor_weather | diffuse_nebula | Sud | 98.00 | 85.35 | 51.29 | usable | 1.00 |
| S04_poor_weather | open_cluster | Nord-Est | 88.00 | 77.06 | 50.63 | usable | 1.00 |
| S04_poor_weather | globular_cluster | Nord-Est | 94.00 | 82.48 | 52.39 | usable | 1.00 |
| S05_blocked_session | jupiter | Est | 96.00 | 86.00 | 47.30 | blocked | 1.00 |
| S05_blocked_session | moon | Ovest | 92.00 | 82.00 | 46.13 | blocked | 1.00 |
| S05_blocked_session | galaxy | Sud | 100.00 | 86.84 | 53.20 | blocked | 1.00 |
| S05_blocked_session | diffuse_nebula | Sud | 98.00 | 85.35 | 51.29 | blocked | 1.00 |
| S05_blocked_session | open_cluster | Nord-Est | 88.00 | 77.06 | 50.63 | blocked | 1.00 |
| S05_blocked_session | globular_cluster | Nord-Est | 94.00 | 82.48 | 52.39 | blocked | 1.00 |
| S06_small_equipment | jupiter | Est | 96.00 | 86.00 | 32.88 | usable | 1.00 |
| S06_small_equipment | moon | Ovest | 92.00 | 82.00 | 39.55 | usable | 1.00 |
| S06_small_equipment | galaxy | Sud | 100.00 | 86.84 | 49.26 | usable | 1.00 |
| S06_small_equipment | diffuse_nebula | Sud | 98.00 | 85.35 | 51.70 | usable | 1.00 |
| S06_small_equipment | open_cluster | Nord-Est | 88.00 | 77.06 | 53.06 | usable | 1.00 |
| S06_small_equipment | globular_cluster | Nord-Est | 94.00 | 82.48 | 42.45 | usable | 1.00 |
| S07_large_equipment | jupiter | Est | 96.00 | 86.00 | 61.26 | usable | 1.00 |
| S07_large_equipment | moon | Ovest | 92.00 | 82.00 | 56.37 | usable | 1.00 |
| S07_large_equipment | galaxy | Sud | 100.00 | 86.84 | 64.19 | usable | 1.00 |
| S07_large_equipment | diffuse_nebula | Sud | 98.00 | 85.35 | 59.34 | usable | 1.00 |
| S07_large_equipment | open_cluster | Nord-Est | 88.00 | 77.06 | 55.62 | usable | 1.00 |
| S07_large_equipment | globular_cluster | Nord-Est | 94.00 | 82.48 | 66.37 | usable | 1.00 |
| S08_plan_best_boost | jupiter | Est | 96.00 | 86.00 | 47.30 | usable | 1.00 |
| S08_plan_best_boost | moon | Ovest | 92.00 | 82.00 | 46.13 | usable | 1.00 |
| S08_plan_best_boost | galaxy | Sud | 100.00 | 86.84 | 53.20 | usable | 1.00 |
| S08_plan_best_boost | diffuse_nebula | Sud | 98.00 | 85.35 | 51.29 | usable | 1.00 |
| S08_plan_best_boost | open_cluster | Nord-Est | 88.00 | 77.06 | 50.63 | usable | 1.00 |
| S08_plan_best_boost | globular_cluster | Nord-Est | 194.00 | 82.48 | 52.39 | usable | 1.00 |

## Legacy Ownership Mixing

Sky Compass legacy direction score is intentionally presentation oriented. It mixes a prepared target score with plan membership, Best Object status and one fixed target-presence bonus.
- 1 rows include plan or Best Object boosts that are presentation context, not target physics.
- Legacy Sky Compass receives an already prepared candidate score and cannot expose upstream score components.
- Moon and sky background are visible in NSOM sky ownership but unavailable in the legacy direction formula.
- SessionViability and RecommendationConfidence are metadata and have zero target-value effect.
- Observer equipment changes PracticalTargetValue references, not legacy Sky Compass direction contribution.

## Main Direction Differences

- `S02_bright_moon` legacy top `Sud` differs from Observable `Nord-Est` or Practical `Nord-Est`.
- `S03_high_light_pollution` legacy top `Sud` differs from Observable `Nord-Est` or Practical `Nord-Est`.
- `S08_plan_best_boost` legacy top `Nord-Est` differs from Observable `Sud` or Practical `Sud`.

## Confidence Control

Changing only confidence keeps legacy direction top `Sud` -> `Sud`, Observable top `Sud` -> `Sud`, and target value deltas `0.0000` / `0.0000`.
Confidence remains metadata-only and is not a score factor.

## Migration Readiness

- Sky Compass should not be migrated as a pure target ranking.
- A future default-off path should preserve direction/presentation policy explicitly.
- `ObservableTargetValue` can inform direction references but should not replace plan/best/context boosts blindly.
- `PracticalTargetValue` should remain inspection-only until equipment-aware compass semantics are designed.
- Session blocked/poor-weather state should stay caution/actionability metadata, not target physics.

## Recommended Next Steps

1. Review whether Sky Compass should remain a presentation policy over NSOM-prepared candidates.
2. Add a default-off experimental Sky Compass NSOM direction policy only after that review.
3. Keep the current `skyCompass` QML payload shape unchanged until a UI/rationale design step.
