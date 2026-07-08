# Detail/Object NSOM Comparison Report

## Executive Summary

This developer-only report compares current selected-object Detail semantics with NSOM target projections. It does not change `selectedObject`, QML, Home, Best Object, Planner, Sky Compass, logging, network behaviour or runtime file writes.
The matrix covers 6 deterministic Detail scenarios. Observing-source Detail currently displays a moon-adjusted replacement object; catalogue Detail displays the raw catalogue object. NSOM values are parallel comparison data only.

## Methodology

- Uses `DetailObjectNsomComparisonService` with fixed in-memory fixtures only.
- Replicates the current selected-object score policy without calling `AppController`.
- Computes NSOM `ObservableTargetValue` and `PracticalTargetValue` separately.
- Keeps `SessionViability` and `RecommendationConfidence` as metadata.
- Marks unavailable legacy components instead of fabricating breakdowns.
- No runtime wiring, QML exposure, automatic logging, network call or runtime file write.

## Scenario Matrix

| Scenario | Source | Target | Sky | Session | Equipment | Confidence | Expectation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D01_observing_bright_moon | observing | galaxy | bright_moon | good | medium | high | Observing-source Detail should show a legacy moon-adjusted score copy. |
| D02_catalogue_bright_moon | catalogue | catalogue-galaxy | bright_moon | good | medium | high | Catalogue Detail should keep raw legacy score while NSOM still reports sky context. |
| D03_high_light_pollution | observing | diffuse_nebula | high_light_pollution | good | medium | high | NSOM should expose static sky background separately from legacy Detail score. |
| D04_blocked_session | observing | galaxy | dark | blocked | medium | high | Session viability should be metadata and not mutate target values. |
| D05_small_equipment | observing | galaxy | dark | good | small | high | Equipment should affect PracticalTargetValue only. |
| D06_large_equipment | observing | galaxy | dark | good | large | high | Large equipment should increase PracticalTargetValue without changing ObservableTargetValue. |

## Detail Comparison

| Scenario | Policy | Legacy Display | Score Delta | Lunar Sky | Static Sky | Observable | Practical | Session | Confidence |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| D01_observing_bright_moon | observing_detail_moon_adjusted_copy | 53.00 | -35.00 | 0.625 | 1.000 | 55.00 | 36.48 | usable | 1.00 |
| D02_catalogue_bright_moon | catalogue_detail_raw_object | 88.00 | 0.00 | 0.625 | 1.000 | 55.00 | 36.48 | usable | 1.00 |
| D03_high_light_pollution | observing_detail_moon_adjusted_copy | 86.00 | 0.00 | 1.000 | 0.785 | 67.52 | 45.18 | usable | 1.00 |
| D04_blocked_session | observing_detail_moon_adjusted_copy | 88.00 | 0.00 | 1.000 | 1.000 | 88.00 | 58.37 | blocked | 1.00 |
| D05_small_equipment | observing_detail_moon_adjusted_copy | 88.00 | 0.00 | 1.000 | 1.000 | 88.00 | 49.91 | usable | 1.00 |
| D06_large_equipment | observing_detail_moon_adjusted_copy | 88.00 | 0.00 | 1.000 | 1.000 | 88.00 | 65.05 | usable | 1.00 |

## Findings

- Observing-source Detail still uses a moon-adjusted replacement object for displayed score.
- Catalogue Detail keeps raw selected-object score and does not expose a moon-adjustment breakdown.
- Static sky background is visible in NSOM ObservableTargetValue but not in legacy selectedObject score.
- Session viability is useful Detail metadata but does not modify target values.
- Equipment changes PracticalTargetValue only; ObservableTargetValue remains objective.
- RecommendationConfidence remains metadata-only with zero score effect.

## Controls

- Equipment control: observable delta `0.0000`, practical delta `15.1307`.
- Confidence control: observable delta `0.0000`, practical delta `0.0000`, score factor `False`.

## Migration Recommendation

Do not change Detail UI yet. First review whether selected-object Detail should present NSOM explanation fields separately from the legacy/base `score`, because the current payload uses compatibility score semantics and source-specific conditioning.

## Recommended Next Steps

1. Review this report for source-specific Detail semantics.
2. Add a readiness audit before any default-off Detail NSOM runtime path.
3. Keep any visible NSOM explanation UI as a separate design step.
