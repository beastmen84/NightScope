# NSOM Planner Comparison Report

## Executive Summary

This developer-facing report compares legacy Planner scoring with the default-off experimental NSOM Planner path across 120 deterministic scenario rows in 20 ranked groups.
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
| G19 | dark_sky | good | medium_telescope | missing_window | high | missing observing time should expose observing_window_quality 0.5 |
| G20 | dark_sky | good | medium_telescope | invisible_missing_window | high | invisible target without observing time should expose observing_window_quality 0.0 |

## Score And Rank Comparison

| Scenario | Target | Legacy Rank | Legacy Score | NSOM Rank | NSOM Score | Rank Delta | Review | Policy | Main NSOM Limit |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| G01:planet | planet | 1 | 100.24 | 1 | 40.95 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.63 |
| G01:moon | moon | 3 | 95.67 | 2 | 40.41 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G01:galaxy | galaxy | 4 | 87.04 | 3 | 40.02 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.61 |
| G01:globular_cluster | globular_cluster | 6 | 85.85 | 4 | 39.36 | -2 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G01:diffuse_nebula | diffuse_nebula | 5 | 86.90 | 5 | 38.57 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.60 |
| G01:open_cluster | open_cluster | 2 | 96.55 | 6 | 38.45 | 4 | review | actionable_ranked_recommendation | observer:q_target=0.62 |
| G02:planet | planet | 1 | 100.24 | 1 | 40.95 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.63 |
| G02:moon | moon | 2 | 80.53 | 2 | 36.82 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G02:open_cluster | open_cluster | 3 | 79.31 | 3 | 31.38 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.62 |
| G02:globular_cluster | globular_cluster | 4 | 62.88 | 4 | 29.75 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G02:diffuse_nebula | diffuse_nebula | 5 | 56.66 | 5 | 24.57 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.60 |
| G02:galaxy | galaxy | 6 | 47.50 | 6 | 23.97 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.61 |
| G03:planet | planet | 1 | 100.98 | 1 | 41.90 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.63 |
| G03:moon | moon | 2 | 91.76 | 2 | 37.71 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G03:open_cluster | open_cluster | 3 | 83.07 | 3 | 32.29 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.62 |
| G03:globular_cluster | globular_cluster | 4 | 66.37 | 4 | 30.20 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G03:diffuse_nebula | diffuse_nebula | 5 | 59.88 | 5 | 23.75 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.60 |
| G03:galaxy | galaxy | 6 | 48.93 | 6 | 22.85 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.61 |
| G04:planet | planet | 1 | 100.24 | 1 | 40.95 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.63 |
| G04:moon | moon | 3 | 93.96 | 2 | 40.41 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G04:galaxy | galaxy | 5 | 84.56 | 3 | 39.17 | -2 | review | actionable_ranked_recommendation | observer:q_target=0.61 |
| G04:globular_cluster | globular_cluster | 6 | 84.27 | 4 | 38.93 | -2 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G04:open_cluster | open_cluster | 2 | 95.35 | 5 | 38.18 | 3 | review | actionable_ranked_recommendation | observer:q_target=0.62 |
| G04:diffuse_nebula | diffuse_nebula | 4 | 84.87 | 6 | 37.87 | 2 | review | actionable_ranked_recommendation | observer:q_target=0.60 |
| G05:planet | planet | 1 | 78.80 | 1 | 24.44 | 0 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G05:moon | moon | 2 | 70.38 | 2 | 23.05 | 0 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G05:open_cluster | open_cluster | 3 | 65.38 | 3 | 19.96 | 0 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G05:globular_cluster | globular_cluster | 4 | 52.54 | 4 | 18.94 | 0 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G05:diffuse_nebula | diffuse_nebula | 5 | 47.83 | 5 | 15.56 | 0 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G05:galaxy | galaxy | 6 | 39.98 | 6 | 15.21 | 0 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G06:planet | planet | 1 | 100.24 | 1 | 40.95 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.63 |
| G06:moon | moon | 3 | 74.68 | 2 | 35.92 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G06:open_cluster | open_cluster | 2 | 80.76 | 3 | 31.71 | 1 | review | actionable_ranked_recommendation | observer:q_target=0.62 |
| G06:globular_cluster | globular_cluster | 4 | 66.63 | 4 | 31.17 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G06:diffuse_nebula | diffuse_nebula | 5 | 63.11 | 5 | 27.99 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.60 |
| G06:galaxy | galaxy | 6 | 58.68 | 6 | 27.91 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.61 |
| G07:planet | planet | 1 | 79.42 | 1 | 25.02 | 0 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G07:moon | moon | 3 | 75.54 | 2 | 24.69 | -1 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G07:galaxy | galaxy | 4 | 68.90 | 3 | 24.46 | -1 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G07:globular_cluster | globular_cluster | 6 | 67.89 | 4 | 24.05 | -2 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G07:diffuse_nebula | diffuse_nebula | 5 | 68.78 | 5 | 23.57 | 0 | expected | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G07:open_cluster | open_cluster | 2 | 76.28 | 6 | 23.50 | 4 | review | actionable_ranked_recommendation | session:weather_suitability=0.55 |
| G08:planet | planet | 1 | 57.57 | 1 | 13.65 | 0 | expected | actionable_ranked_recommendation | session:weather_suitability=0.30 |
| G08:moon | moon | 3 | 54.61 | 2 | 13.47 | -1 | expected | actionable_ranked_recommendation | session:weather_suitability=0.30 |
| G08:galaxy | galaxy | 4 | 49.91 | 3 | 13.34 | -1 | expected | actionable_ranked_recommendation | session:weather_suitability=0.30 |
| G08:globular_cluster | globular_cluster | 6 | 49.13 | 4 | 13.12 | -2 | expected | actionable_ranked_recommendation | session:weather_suitability=0.30 |
| G08:diffuse_nebula | diffuse_nebula | 5 | 49.82 | 5 | 12.86 | 0 | expected | actionable_ranked_recommendation | session:weather_suitability=0.30 |
| G08:open_cluster | open_cluster | 2 | 55.18 | 6 | 12.82 | 4 | review | actionable_ranked_recommendation | session:weather_suitability=0.30 |
| G09:planet | planet | 1 | 29.64 | 1 | 0.00 | 0 | warning | non_actionable_hard_block | session:blocking_factor=0.00 |
| G09:moon | moon | 2 | 22.74 | 2 | 0.00 | 0 | warning | non_actionable_hard_block | session:blocking_factor=0.00 |
| G09:galaxy | galaxy | 6 | 11.84 | 3 | 0.00 | -3 | warning | non_actionable_hard_block | session:blocking_factor=0.00 |
| G09:diffuse_nebula | diffuse_nebula | 5 | 15.04 | 4 | 0.00 | -1 | warning | non_actionable_hard_block | session:blocking_factor=0.00 |
| G09:open_cluster | open_cluster | 3 | 22.32 | 5 | 0.00 | 2 | warning | non_actionable_hard_block | session:blocking_factor=0.00 |
| G09:globular_cluster | globular_cluster | 4 | 17.22 | 6 | 0.00 | 2 | warning | non_actionable_hard_block | session:blocking_factor=0.00 |
| G10:open_cluster | open_cluster | 2 | 91.93 | 1 | 40.29 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.65 |
| G10:diffuse_nebula | diffuse_nebula | 5 | 82.84 | 2 | 38.51 | -3 | review | actionable_ranked_recommendation | observer:q_target=0.60 |
| G10:galaxy | galaxy | 4 | 82.98 | 3 | 36.43 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.56 |
| G10:planet | planet | 1 | 95.62 | 4 | 35.76 | 3 | review | actionable_ranked_recommendation | observer:q_target=0.55 |
| G10:moon | moon | 3 | 91.05 | 5 | 34.69 | 2 | review | actionable_ranked_recommendation | observer:q_target=0.55 |
| G10:globular_cluster | globular_cluster | 6 | 81.79 | 6 | 30.95 | 0 | warning | actionable_ranked_recommendation | observer:q_target=0.50 |
| G11:open_cluster | open_cluster | 2 | 92.53 | 1 | 40.42 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.65 |
| G11:diffuse_nebula | diffuse_nebula | 5 | 83.37 | 2 | 38.88 | -3 | review | actionable_ranked_recommendation | observer:q_target=0.61 |
| G11:galaxy | galaxy | 4 | 83.51 | 3 | 37.06 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.57 |
| G11:planet | planet | 1 | 96.22 | 4 | 35.76 | 3 | review | actionable_ranked_recommendation | observer:q_target=0.55 |
| G11:moon | moon | 3 | 91.65 | 5 | 35.33 | 2 | review | actionable_ranked_recommendation | observer:q_target=0.56 |
| G11:globular_cluster | globular_cluster | 6 | 82.32 | 6 | 31.89 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.51 |
| G12:planet | planet | 1 | 105.82 | 1 | 52.85 | 0 | expected | actionable_ranked_recommendation | observer:q_target=0.81 |
| G12:globular_cluster | globular_cluster | 6 | 90.76 | 2 | 49.86 | -4 | review | actionable_ranked_recommendation | observer:q_target=0.80 |
| G12:moon | moon | 3 | 101.25 | 3 | 48.30 | 0 | expected | actionable_ranked_recommendation | observer:q_target=0.76 |
| G12:galaxy | galaxy | 4 | 91.95 | 4 | 48.29 | 0 | expected | actionable_ranked_recommendation | observer:q_target=0.74 |
| G12:diffuse_nebula | diffuse_nebula | 5 | 91.81 | 5 | 44.62 | 0 | expected | actionable_ranked_recommendation | observer:q_target=0.70 |
| G12:open_cluster | open_cluster | 2 | 102.13 | 6 | 41.75 | 4 | review | actionable_ranked_recommendation | observer:q_target=0.67 |
| G13:planet | planet | 1 | 105.82 | 1 | 52.85 | 0 | expected | actionable_ranked_recommendation | observer:q_target=0.81 |
| G13:moon | moon | 2 | 86.11 | 2 | 44.01 | 0 | expected | actionable_ranked_recommendation | observer:q_target=0.76 |
| G13:globular_cluster | globular_cluster | 4 | 67.79 | 3 | 37.69 | -1 | expected | actionable_ranked_recommendation | observer:q_target=0.80 |
| G13:open_cluster | open_cluster | 3 | 84.89 | 4 | 34.07 | 1 | expected | actionable_ranked_recommendation | observer:q_target=0.67 |
| G13:galaxy | galaxy | 6 | 52.41 | 5 | 28.93 | -1 | expected | actionable_ranked_recommendation | observer:q_target=0.74 |
| G13:diffuse_nebula | diffuse_nebula | 5 | 61.57 | 6 | 28.43 | 1 | expected | actionable_ranked_recommendation | observer:q_target=0.70 |
| G14:planet | planet | 1 | 103.91 | 1 | 45.71 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.63 |
| G14:moon | moon | 2 | 69.63 | 2 | 30.53 | 0 | warning | actionable_ranked_recommendation | observer:q_target=0.64 |
| G14:open_cluster | open_cluster | 3 | 65.39 | 3 | 24.26 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.62 |
| G14:globular_cluster | globular_cluster | 4 | 45.51 | 4 | 21.75 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G14:diffuse_nebula | diffuse_nebula | 5 | 34.42 | 5 | 15.54 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.60 |
| G14:galaxy | galaxy | 6 | 18.73 | 6 | 14.32 | 0 | expected | actionable_ranked_recommendation | sky:moon_background=0.61 |
| G15:globular_cluster | globular_cluster | 6 | 92.70 | 1 | 53.18 | -5 | warning | actionable_ranked_recommendation | observer:q_target=0.80 |
| G15:moon | moon | 2 | 103.46 | 2 | 51.52 | 0 | expected | actionable_ranked_recommendation | observer:q_target=0.76 |
| G15:galaxy | galaxy | 4 | 93.89 | 3 | 51.51 | -1 | expected | actionable_ranked_recommendation | observer:q_target=0.74 |
| G15:diffuse_nebula | diffuse_nebula | 5 | 93.75 | 4 | 47.60 | -1 | expected | actionable_ranked_recommendation | observer:q_target=0.70 |
| G15:planet | planet | 3 | 102.15 | 5 | 46.70 | 2 | expected | actionable_ranked_recommendation | sky:atmospheric_transparency=0.76 |
| G15:open_cluster | open_cluster | 1 | 104.33 | 6 | 44.53 | 5 | warning | actionable_ranked_recommendation | observer:q_target=0.67 |
| G16:planet | planet | 1 | 100.24 | 1 | 11.70 | 0 | expected | actionable_ranked_recommendation | sky:horizon_context=0.29 |
| G16:moon | moon | 3 | 95.67 | 2 | 11.55 | -1 | expected | actionable_ranked_recommendation | sky:horizon_context=0.29 |
| G16:galaxy | galaxy | 4 | 87.04 | 3 | 11.44 | -1 | expected | actionable_ranked_recommendation | sky:horizon_context=0.29 |
| G16:globular_cluster | globular_cluster | 6 | 85.85 | 4 | 11.24 | -2 | expected | actionable_ranked_recommendation | sky:horizon_context=0.29 |
| G16:diffuse_nebula | diffuse_nebula | 5 | 86.90 | 5 | 11.02 | 0 | expected | actionable_ranked_recommendation | sky:horizon_context=0.29 |
| G16:open_cluster | open_cluster | 2 | 96.55 | 6 | 10.99 | 4 | review | actionable_ranked_recommendation | sky:horizon_context=0.29 |
| G17:planet | planet | 1 | 100.24 | 1 | 34.80 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.63 |
| G17:moon | moon | 3 | 95.67 | 2 | 34.35 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G17:galaxy | galaxy | 4 | 87.04 | 3 | 34.02 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.61 |
| G17:globular_cluster | globular_cluster | 6 | 85.85 | 4 | 33.45 | -2 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G17:diffuse_nebula | diffuse_nebula | 5 | 86.90 | 5 | 32.79 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.60 |
| G17:open_cluster | open_cluster | 2 | 96.55 | 6 | 32.69 | 4 | review | actionable_ranked_recommendation | observer:q_target=0.62 |
| G18:planet | planet | 1 | 100.24 | 1 | 40.95 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.63 |
| G18:moon | moon | 3 | 95.67 | 2 | 40.41 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G18:galaxy | galaxy | 4 | 87.04 | 3 | 40.02 | -1 | review | actionable_ranked_recommendation | observer:q_target=0.61 |
| G18:globular_cluster | globular_cluster | 6 | 85.85 | 4 | 39.36 | -2 | review | actionable_ranked_recommendation | observer:q_target=0.64 |
| G18:diffuse_nebula | diffuse_nebula | 5 | 86.90 | 5 | 38.57 | 0 | review | actionable_ranked_recommendation | observer:q_target=0.60 |
| G18:open_cluster | open_cluster | 2 | 96.55 | 6 | 38.45 | 4 | review | actionable_ranked_recommendation | observer:q_target=0.62 |
| G19:planet | planet | 1 | 100.24 | 1 | 16.38 | 0 | expected | actionable_with_uncertain_timing | opportunity:observing_window_quality=0.50 |
| G19:moon | moon | 3 | 95.67 | 2 | 16.16 | -1 | expected | actionable_with_uncertain_timing | opportunity:observing_window_quality=0.50 |
| G19:galaxy | galaxy | 4 | 87.04 | 3 | 16.01 | -1 | expected | actionable_with_uncertain_timing | opportunity:observing_window_quality=0.50 |
| G19:globular_cluster | globular_cluster | 6 | 85.85 | 4 | 15.74 | -2 | expected | actionable_with_uncertain_timing | opportunity:observing_window_quality=0.50 |
| G19:diffuse_nebula | diffuse_nebula | 5 | 86.90 | 5 | 15.43 | 0 | expected | actionable_with_uncertain_timing | opportunity:observing_window_quality=0.50 |
| G19:open_cluster | open_cluster | 2 | 96.55 | 6 | 15.38 | 4 | review | actionable_with_uncertain_timing | opportunity:observing_window_quality=0.50 |
| G20:planet | planet | 1 | 100.24 | 1 | 0.00 | 0 | warning | non_actionable_invisible_target | sky:geometric_visibility=0.00 |
| G20:moon | moon | 3 | 95.67 | 2 | 0.00 | -1 | warning | non_actionable_invisible_target | sky:geometric_visibility=0.00 |
| G20:galaxy | galaxy | 4 | 87.04 | 3 | 0.00 | -1 | warning | non_actionable_invisible_target | sky:geometric_visibility=0.00 |
| G20:diffuse_nebula | diffuse_nebula | 5 | 86.90 | 4 | 0.00 | -1 | warning | non_actionable_invisible_target | sky:geometric_visibility=0.00 |
| G20:open_cluster | open_cluster | 2 | 96.55 | 5 | 0.00 | 3 | warning | non_actionable_invisible_target | sky:geometric_visibility=0.00 |
| G20:globular_cluster | globular_cluster | 6 | 85.85 | 6 | 0.00 | 0 | warning | non_actionable_invisible_target | sky:geometric_visibility=0.00 |

## Calibration Review Thresholds

Thresholds classify deterministic fixture rows as `expected`, `review` or `warning`. They are review gates only; they do not tune NSOM weights and do not alter Planner scoring.

| Threshold | Value |
| --- | ---: |
| `large_rank_delta_review` | 3 |
| `large_rank_delta_warning` | 5 |
| `protected_target_min_effective_observability` | 0.75 |
| `deep_sky_bright_sky_max_effective_observability` | 0.75 |
| `observer_q_target_review` | 0.65 |
| `observer_q_target_warning` | 0.5 |
| `observer_dominance_review_share` | 0.75 |
| `observer_dominance_warning_share` | 0.9 |
| `missing_window_expected_quality` | 0.5 |
| `invisible_target_expected_quality` | 0.0 |

## Opportunity Policy Review

| Group | Policy Type | Actionable | Recommendation Order | Tie Order | Timing Uncertain | Policy Notes |
| --- | --- | --- | --- | --- | --- | --- |
| G09 | non_actionable_hard_block | no | no | yes | no | Current hard-block policy is accepted for now: all-zero NSOM opportunity scores are non-actionable, and stable order is not a recommendation order. |
| G19 | actionable_with_uncertain_timing | yes | yes | no | yes | Visible targets with missing observing time keep the conservative 0.5 observing-window fallback and are marked actionable with uncertain timing. |
| G20 | non_actionable_invisible_target | no | no | yes | no | Invisible targets are non-actionable; all-zero stable order is not a recommendation order. |

## Intentional NSOM Differences From Legacy

- `G01:moon`: legacy rank 3 vs NSOM rank 2; main NSOM limit observer:q_target=0.64.
- `G01:galaxy`: legacy rank 4 vs NSOM rank 3; main NSOM limit observer:q_target=0.61.
- `G01:globular_cluster`: legacy rank 6 vs NSOM rank 4; main NSOM limit observer:q_target=0.64.
- `G01:open_cluster`: legacy rank 2 vs NSOM rank 6; main NSOM limit observer:q_target=0.62.
- `G04:moon`: legacy rank 3 vs NSOM rank 2; main NSOM limit observer:q_target=0.64.
- `G04:galaxy`: legacy rank 5 vs NSOM rank 3; main NSOM limit observer:q_target=0.61.
- `G04:globular_cluster`: legacy rank 6 vs NSOM rank 4; main NSOM limit observer:q_target=0.64.
- `G04:open_cluster`: legacy rank 2 vs NSOM rank 5; main NSOM limit observer:q_target=0.62.

## Cases Where NSOM Better Follows The Model

- 14 bright-sky planet/Moon rows avoid sky-background limiting factors.
- 14 bright-sky galaxy/nebula rows show sky-owned background limits.
- Small vs large equipment changes PracticalTargetValue while ObservableTargetValue stays sky-owned.
- Blocked sessions reduce NSOM opportunity through SessionViability instead of mutating target value.
- Confidence controls produce zero score delta.

## Cases Requiring Further Review

- 6 blocked-session rows use the resolved non-actionable hard-block policy.
- 6 invisible-target rows use the resolved non-actionable invisible-target policy.
- 6 missing-window rows remain actionable with uncertain timing.
- 16 rows are classified as calibration warnings by developer-only thresholds.
- 63 rows are classified as calibration review cases by developer-only thresholds.
- 64 rows have rank deltas; review large deltas against observing priorities.
- Legacy exposes aperture bonus but not full observer capability, so equipment parity cannot be exact.
- Legacy and NSOM scores use different semantics and should not be calibrated by raw numeric equality.

## Confidence Control

The confidence-only control keeps the same physical inputs and changes only `RecommendationConfidence`: low confidence score `40.0246`, high confidence score `40.0246`. The score delta is `0.0000`.

## Recommended Next Steps

1. Review rank-delta examples manually against expected observing priorities.
2. Keep non-actionable opportunity policy metadata explicit while resolving targeted calibration blockers.
3. Tune only named NSOM components with failing behavioural evidence, not broad legacy parity targets.
4. Keep comparison/report tooling developer-only until the Planner path is ready to replace legacy ranking.
