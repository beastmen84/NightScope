# NSOM Planner Comparison Report

## Executive Summary

This developer-facing report compares legacy Planner scoring with the default-off experimental NSOM Planner path across 108 deterministic scenario rows in 18 ranked groups.
NSOM generally follows the intended model direction: planets and the Moon remain protected from sky-background damage, galaxies and diffuse nebulae show sky-owned degradation under bright sky, equipment changes practical target value, session viability changes opportunity value, and confidence remains metadata only.
The inspection also highlights review areas before enabling NSOM by default: legacy and NSOM use different score scales, blocked sessions expose a sharper NSOM session cap than legacy score reduction, and some rank differences are expected rather than regressions.

## Methodology

- Generated fixed in-memory fixtures only; no network calls.
- Compared six target types in each matrix group: planet, Moon, galaxy, diffuse nebula, open cluster and globular cluster.
- Used legacy `PlannerScoringService.score_breakdown()` only for legacy values that are actually exposed.
- Marked unavailable legacy concepts explicitly instead of fabricating values.
- Built NSOM opportunities with `PlannerNsomScoringService` and exported the existing explanation breakdown.
- Left `NSOM_PLANNER_SCORING_ENABLED` set to `False`; this report is not wired into runtime, QML or automatic logging.

## Scenario Matrix Overview

| Group | Sky | Session | Equipment | Geometry | Confidence | Expected NSOM behaviour |
| --- | --- | --- | --- | --- | --- | --- |
| G01 | dark_sky | good | medium_telescope | standard | high | baseline NSOM component separation |
| G02 | bright_sky | good | medium_telescope | standard | high | planet/Moon protection and deep-sky sky-background sensitivity |
| G03 | strong_moon | good | medium_telescope | standard | high | planet/Moon protection and deep-sky sky-background sensitivity |
| G04 | low_moon | good | medium_telescope | standard | high | baseline NSOM component separation |
| G05 | high_moon | mediocre | medium_telescope | standard | high | planet/Moon protection and deep-sky sky-background sensitivity; session quality should reduce opportunity only |
| G06 | high_light_pollution | good | medium_telescope | standard | high | planet/Moon protection and deep-sky sky-background sensitivity |
| G07 | dark_sky | mediocre | medium_telescope | standard | high | session quality should reduce opportunity only |
| G08 | dark_sky | poor | medium_telescope | standard | high | session quality should reduce opportunity only |
| G09 | bright_sky | blocked | medium_telescope | standard | high | planet/Moon protection and deep-sky sky-background sensitivity; SessionViability should cap NSOM opportunity |
| G10 | dark_sky | good | binocular | standard | high | equipment should move PracticalTargetValue but not ObservableTargetValue |
| G11 | dark_sky | good | small_telescope | standard | high | equipment should move PracticalTargetValue but not ObservableTargetValue |
| G12 | dark_sky | good | large_telescope | standard | high | equipment should move PracticalTargetValue but not ObservableTargetValue |
| G13 | bright_sky | good | large_telescope | standard | high | planet/Moon protection and deep-sky sky-background sensitivity; equipment should move PracticalTargetValue but not ObservableTargetValue |
| G14 | planet_favouring | good | medium_telescope | standard | high | planet/Moon protection and deep-sky sky-background sensitivity |
| G15 | deep_sky_favouring | good | large_telescope | standard | high | deep-sky targets should retain high effective observability; equipment should move PracticalTargetValue but not ObservableTargetValue |
| G16 | dark_sky | good | medium_telescope | low_altitude | high | horizon context should limit EffectiveObservability |
| G17 | dark_sky | good | medium_telescope | late_window | high | chronology fit should affect opportunity |
| G18 | dark_sky | good | medium_telescope | standard | low | low confidence should remain metadata |

## Score And Rank Comparison

| Scenario | Target | Legacy Rank | Legacy Score | NSOM Rank | NSOM Score | Rank Delta | Main NSOM Limit |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| G01:galaxy | galaxy | 4 | 87.04 | 1 | 42.21 | -3 | observer:observer_capability_summary=0.65 |
| G01:planet | planet | 1 | 100.24 | 2 | 42.00 | 1 | observer:observer_capability_summary=0.65 |
| G01:diffuse_nebula | diffuse_nebula | 5 | 86.90 | 3 | 41.46 | -2 | observer:observer_capability_summary=0.65 |
| G01:moon | moon | 3 | 95.67 | 4 | 40.82 | 1 | observer:observer_capability_summary=0.65 |
| G01:open_cluster | open_cluster | 2 | 96.55 | 5 | 40.32 | 3 | observer:observer_capability_summary=0.65 |
| G01:globular_cluster | globular_cluster | 6 | 85.85 | 6 | 40.03 | 0 | observer:observer_capability_summary=0.65 |
| G02:planet | planet | 1 | 100.24 | 1 | 42.00 | 0 | observer:observer_capability_summary=0.65 |
| G02:moon | moon | 2 | 80.53 | 2 | 37.19 | 0 | observer:observer_capability_summary=0.65 |
| G02:open_cluster | open_cluster | 3 | 79.31 | 3 | 32.91 | 0 | observer:observer_capability_summary=0.65 |
| G02:globular_cluster | globular_cluster | 4 | 62.88 | 4 | 30.26 | 0 | observer:observer_capability_summary=0.65 |
| G02:diffuse_nebula | diffuse_nebula | 5 | 56.66 | 5 | 26.41 | 0 | observer:observer_capability_summary=0.65 |
| G02:galaxy | galaxy | 6 | 47.50 | 6 | 25.28 | 0 | observer:observer_capability_summary=0.65 |
| G03:planet | planet | 1 | 100.98 | 1 | 42.98 | 0 | observer:observer_capability_summary=0.65 |
| G03:moon | moon | 2 | 91.76 | 2 | 38.09 | 0 | observer:observer_capability_summary=0.65 |
| G03:open_cluster | open_cluster | 3 | 83.07 | 3 | 33.86 | 0 | observer:observer_capability_summary=0.65 |
| G03:globular_cluster | globular_cluster | 4 | 66.37 | 4 | 30.72 | 0 | observer:observer_capability_summary=0.65 |
| G03:diffuse_nebula | diffuse_nebula | 5 | 59.88 | 5 | 25.53 | 0 | observer:observer_capability_summary=0.65 |
| G03:galaxy | galaxy | 6 | 48.93 | 6 | 24.10 | 0 | sky:moon_background=0.62 |
| G04:planet | planet | 1 | 100.24 | 1 | 42.00 | 0 | observer:observer_capability_summary=0.65 |
| G04:galaxy | galaxy | 5 | 84.56 | 2 | 41.31 | -3 | observer:observer_capability_summary=0.65 |
| G04:moon | moon | 3 | 93.96 | 3 | 40.82 | 0 | observer:observer_capability_summary=0.65 |
| G04:diffuse_nebula | diffuse_nebula | 4 | 84.87 | 4 | 40.71 | 0 | observer:observer_capability_summary=0.65 |
| G04:open_cluster | open_cluster | 2 | 95.35 | 5 | 40.04 | 3 | observer:observer_capability_summary=0.65 |
| G04:globular_cluster | globular_cluster | 6 | 84.27 | 6 | 39.60 | 0 | observer:observer_capability_summary=0.65 |
| G05:planet | planet | 1 | 78.80 | 1 | 25.07 | 0 | session:weather_suitability=0.55 |
| G05:moon | moon | 2 | 70.38 | 2 | 23.28 | 0 | session:weather_suitability=0.55 |
| G05:open_cluster | open_cluster | 3 | 65.38 | 3 | 20.93 | 0 | session:weather_suitability=0.55 |
| G05:globular_cluster | globular_cluster | 4 | 52.54 | 4 | 19.27 | 0 | session:weather_suitability=0.55 |
| G05:diffuse_nebula | diffuse_nebula | 5 | 47.83 | 5 | 16.73 | 0 | session:weather_suitability=0.55 |
| G05:galaxy | galaxy | 6 | 39.98 | 6 | 16.04 | 0 | session:weather_suitability=0.55 |
| G06:planet | planet | 1 | 100.24 | 1 | 42.00 | 0 | observer:observer_capability_summary=0.65 |
| G06:moon | moon | 3 | 74.68 | 2 | 36.28 | -1 | observer:observer_capability_summary=0.65 |
| G06:open_cluster | open_cluster | 2 | 80.76 | 3 | 33.26 | 1 | observer:observer_capability_summary=0.65 |
| G06:globular_cluster | globular_cluster | 4 | 66.63 | 4 | 31.71 | 0 | observer:observer_capability_summary=0.65 |
| G06:diffuse_nebula | diffuse_nebula | 5 | 63.11 | 5 | 30.09 | 0 | observer:observer_capability_summary=0.65 |
| G06:galaxy | galaxy | 6 | 58.68 | 6 | 29.44 | 0 | observer:observer_capability_summary=0.65 |
| G07:galaxy | galaxy | 4 | 68.90 | 1 | 25.79 | -3 | session:weather_suitability=0.55 |
| G07:planet | planet | 1 | 79.42 | 2 | 25.67 | 1 | session:weather_suitability=0.55 |
| G07:diffuse_nebula | diffuse_nebula | 5 | 68.78 | 3 | 25.34 | -2 | session:weather_suitability=0.55 |
| G07:moon | moon | 3 | 75.54 | 4 | 24.94 | 1 | session:weather_suitability=0.55 |
| G07:open_cluster | open_cluster | 2 | 76.28 | 5 | 24.64 | 3 | session:weather_suitability=0.55 |
| G07:globular_cluster | globular_cluster | 6 | 67.89 | 6 | 24.46 | 0 | session:weather_suitability=0.55 |
| G08:galaxy | galaxy | 4 | 49.91 | 1 | 14.07 | -3 | session:weather_suitability=0.30 |
| G08:planet | planet | 1 | 57.57 | 2 | 14.00 | 1 | session:weather_suitability=0.30 |
| G08:diffuse_nebula | diffuse_nebula | 5 | 49.82 | 3 | 13.82 | -2 | session:weather_suitability=0.30 |
| G08:moon | moon | 3 | 54.61 | 4 | 13.61 | 1 | session:weather_suitability=0.30 |
| G08:open_cluster | open_cluster | 2 | 55.18 | 5 | 13.44 | 3 | session:weather_suitability=0.30 |
| G08:globular_cluster | globular_cluster | 6 | 49.13 | 6 | 13.34 | 0 | session:weather_suitability=0.30 |
| G09:planet | planet | 1 | 29.64 | 1 | 0.00 | 0 | session:blocking_factor=0.00 |
| G09:moon | moon | 2 | 22.74 | 2 | 0.00 | 0 | session:blocking_factor=0.00 |
| G09:galaxy | galaxy | 6 | 11.84 | 3 | 0.00 | -3 | session:blocking_factor=0.00 |
| G09:diffuse_nebula | diffuse_nebula | 5 | 15.04 | 4 | 0.00 | -1 | session:blocking_factor=0.00 |
| G09:open_cluster | open_cluster | 3 | 22.32 | 5 | 0.00 | 2 | session:blocking_factor=0.00 |
| G09:globular_cluster | globular_cluster | 4 | 17.22 | 6 | 0.00 | 2 | session:blocking_factor=0.00 |
| G10:galaxy | galaxy | 4 | 82.98 | 1 | 37.80 | -3 | observer:observer_capability_summary=0.58 |
| G10:planet | planet | 1 | 95.62 | 2 | 37.62 | 1 | observer:observer_capability_summary=0.58 |
| G10:diffuse_nebula | diffuse_nebula | 5 | 82.84 | 3 | 37.14 | -2 | observer:observer_capability_summary=0.58 |
| G10:moon | moon | 3 | 91.05 | 4 | 36.55 | 1 | observer:observer_capability_summary=0.58 |
| G10:open_cluster | open_cluster | 2 | 91.93 | 5 | 36.11 | 3 | observer:observer_capability_summary=0.58 |
| G10:globular_cluster | globular_cluster | 6 | 81.79 | 6 | 35.85 | 0 | observer:observer_capability_summary=0.58 |
| G11:galaxy | galaxy | 4 | 83.51 | 1 | 38.30 | -3 | observer:observer_capability_summary=0.59 |
| G11:planet | planet | 1 | 96.22 | 2 | 38.12 | 1 | observer:observer_capability_summary=0.59 |
| G11:diffuse_nebula | diffuse_nebula | 5 | 83.37 | 3 | 37.63 | -2 | observer:observer_capability_summary=0.59 |
| G11:moon | moon | 3 | 91.65 | 4 | 37.04 | 1 | observer:observer_capability_summary=0.59 |
| G11:open_cluster | open_cluster | 2 | 92.53 | 5 | 36.59 | 3 | observer:observer_capability_summary=0.59 |
| G11:globular_cluster | globular_cluster | 6 | 82.32 | 6 | 36.32 | 0 | observer:observer_capability_summary=0.59 |
| G12:galaxy | galaxy | 4 | 91.95 | 1 | 50.50 | -3 | observer:observer_capability_summary=0.77 |
| G12:planet | planet | 1 | 105.82 | 2 | 50.25 | 1 | observer:observer_capability_summary=0.77 |
| G12:diffuse_nebula | diffuse_nebula | 5 | 91.81 | 3 | 49.60 | -2 | observer:observer_capability_summary=0.77 |
| G12:moon | moon | 3 | 101.25 | 4 | 48.83 | 1 | observer:observer_capability_summary=0.77 |
| G12:open_cluster | open_cluster | 2 | 102.13 | 5 | 48.24 | 3 | observer:observer_capability_summary=0.77 |
| G12:globular_cluster | globular_cluster | 6 | 90.76 | 6 | 47.88 | 0 | observer:observer_capability_summary=0.77 |
| G13:planet | planet | 1 | 105.82 | 1 | 50.25 | 0 | observer:observer_capability_summary=0.77 |
| G13:moon | moon | 2 | 86.11 | 2 | 44.49 | 0 | observer:observer_capability_summary=0.77 |
| G13:open_cluster | open_cluster | 3 | 84.89 | 3 | 39.37 | 0 | observer:observer_capability_summary=0.77 |
| G13:globular_cluster | globular_cluster | 4 | 67.79 | 4 | 36.20 | 0 | observer:observer_capability_summary=0.77 |
| G13:diffuse_nebula | diffuse_nebula | 5 | 61.57 | 5 | 31.60 | 0 | observer:observer_capability_summary=0.77 |
| G13:galaxy | galaxy | 6 | 52.41 | 6 | 30.24 | 0 | observer:observer_capability_summary=0.77 |
| G14:planet | planet | 1 | 103.91 | 1 | 46.89 | 0 | observer:observer_capability_summary=0.65 |
| G14:moon | moon | 2 | 69.63 | 2 | 30.84 | 0 | observer:observer_capability_summary=0.65 |
| G14:open_cluster | open_cluster | 3 | 65.39 | 3 | 25.44 | 0 | observer:observer_capability_summary=0.65 |
| G14:globular_cluster | globular_cluster | 4 | 45.51 | 4 | 22.12 | 0 | observer:observer_capability_summary=0.65 |
| G14:diffuse_nebula | diffuse_nebula | 5 | 34.42 | 5 | 16.71 | 0 | observer:observer_capability_summary=0.65 |
| G14:galaxy | galaxy | 6 | 18.73 | 6 | 15.11 | 0 | sky:moon_background=0.61 |
| G15:galaxy | galaxy | 4 | 93.89 | 1 | 53.86 | -3 | observer:observer_capability_summary=0.77 |
| G15:diffuse_nebula | diffuse_nebula | 5 | 93.75 | 2 | 52.91 | -3 | observer:observer_capability_summary=0.77 |
| G15:moon | moon | 2 | 103.46 | 3 | 52.08 | 1 | observer:observer_capability_summary=0.77 |
| G15:open_cluster | open_cluster | 1 | 104.33 | 4 | 51.46 | 3 | observer:observer_capability_summary=0.77 |
| G15:globular_cluster | globular_cluster | 6 | 92.70 | 5 | 51.08 | -1 | observer:observer_capability_summary=0.77 |
| G15:planet | planet | 3 | 102.15 | 6 | 44.40 | 3 | sky:atmospheric_transparency=0.76 |
| G16:galaxy | galaxy | 4 | 87.04 | 1 | 12.06 | -3 | sky:horizon_context=0.29 |
| G16:planet | planet | 1 | 100.24 | 2 | 12.00 | 1 | sky:horizon_context=0.29 |
| G16:diffuse_nebula | diffuse_nebula | 5 | 86.90 | 3 | 11.85 | -2 | sky:horizon_context=0.29 |
| G16:moon | moon | 3 | 95.67 | 4 | 11.66 | 1 | sky:horizon_context=0.29 |
| G16:open_cluster | open_cluster | 2 | 96.55 | 5 | 11.52 | 3 | sky:horizon_context=0.29 |
| G16:globular_cluster | globular_cluster | 6 | 85.85 | 6 | 11.44 | 0 | sky:horizon_context=0.29 |
| G17:galaxy | galaxy | 4 | 87.04 | 1 | 35.88 | -3 | observer:observer_capability_summary=0.65 |
| G17:planet | planet | 1 | 100.24 | 2 | 35.70 | 1 | observer:observer_capability_summary=0.65 |
| G17:diffuse_nebula | diffuse_nebula | 5 | 86.90 | 3 | 35.24 | -2 | observer:observer_capability_summary=0.65 |
| G17:moon | moon | 3 | 95.67 | 4 | 34.69 | 1 | observer:observer_capability_summary=0.65 |
| G17:open_cluster | open_cluster | 2 | 96.55 | 5 | 34.28 | 3 | observer:observer_capability_summary=0.65 |
| G17:globular_cluster | globular_cluster | 6 | 85.85 | 6 | 34.02 | 0 | observer:observer_capability_summary=0.65 |
| G18:galaxy | galaxy | 4 | 87.04 | 1 | 42.21 | -3 | observer:observer_capability_summary=0.65 |
| G18:planet | planet | 1 | 100.24 | 2 | 42.00 | 1 | observer:observer_capability_summary=0.65 |
| G18:diffuse_nebula | diffuse_nebula | 5 | 86.90 | 3 | 41.46 | -2 | observer:observer_capability_summary=0.65 |
| G18:moon | moon | 3 | 95.67 | 4 | 40.82 | 1 | observer:observer_capability_summary=0.65 |
| G18:open_cluster | open_cluster | 2 | 96.55 | 5 | 40.32 | 3 | observer:observer_capability_summary=0.65 |
| G18:globular_cluster | globular_cluster | 6 | 85.85 | 6 | 40.03 | 0 | observer:observer_capability_summary=0.65 |

## Intentional NSOM Differences From Legacy

- `G01:galaxy`: legacy rank 4 vs NSOM rank 1; main NSOM limit observer:observer_capability_summary=0.65.
- `G01:planet`: legacy rank 1 vs NSOM rank 2; main NSOM limit observer:observer_capability_summary=0.65.
- `G01:diffuse_nebula`: legacy rank 5 vs NSOM rank 3; main NSOM limit observer:observer_capability_summary=0.65.
- `G01:moon`: legacy rank 3 vs NSOM rank 4; main NSOM limit observer:observer_capability_summary=0.65.
- `G01:open_cluster`: legacy rank 2 vs NSOM rank 5; main NSOM limit observer:observer_capability_summary=0.65.
- `G04:galaxy`: legacy rank 5 vs NSOM rank 2; main NSOM limit observer:observer_capability_summary=0.65.
- `G04:open_cluster`: legacy rank 2 vs NSOM rank 5; main NSOM limit observer:observer_capability_summary=0.65.
- `G06:moon`: legacy rank 3 vs NSOM rank 2; main NSOM limit observer:observer_capability_summary=0.65.

## Cases Where NSOM Better Follows The Model

- 14 bright-sky planet/Moon rows avoid sky-background limiting factors.
- 14 bright-sky galaxy/nebula rows show sky-owned background limits.
- Small vs large equipment changes PracticalTargetValue while ObservableTargetValue stays sky-owned.
- Blocked sessions reduce NSOM opportunity through SessionViability instead of mutating target value.
- Confidence controls produce zero score delta.

## Cases Requiring Further Review

- 6 blocked-session rows need policy review before default-on Planner NSOM.
- 59 rows have rank deltas; review large deltas against observing priorities.
- Legacy exposes aperture bonus but not full observer capability, so equipment parity cannot be exact.
- Legacy and NSOM scores use different semantics and should not be calibrated by raw numeric equality.

## Confidence Control

The confidence-only control keeps the same physical inputs and changes only `RecommendationConfidence`: low confidence score `42.2094`, high confidence score `42.2094`. The score delta is `0.0000`.

## Recommended Next Steps

1. Review rank-delta examples manually against expected observing priorities.
2. Decide whether blocked-session handling should become an explicit Planner NSOM policy before default-on work.
3. Tune only named NSOM components with failing behavioural evidence, not broad legacy parity targets.
4. Keep comparison/report tooling developer-only until the Planner path is ready to replace legacy ranking.
