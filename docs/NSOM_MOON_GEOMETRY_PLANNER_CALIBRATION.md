# NSOM Moon Geometry Planner Calibration

## Executive Summary

This developer-only report evaluates 30 deterministic Planner rows for the default-off experimental Moon geometry path.
The experiment changes only the Sky-owned `ObservationEnvironment.lunar_sky_background` component. It does not change ObserverCapability, SessionViability, RecommendationConfidence score effect, QML payloads, runtime logging, network calls or automatic file writes.
The intended direction is visible: close high Moon geometry lowers deep-sky opportunities more than far high Moon geometry, Moon set before the target window removes the lunar background penalty, and planets/Moon remain protected from lunar sky-background penalties.

## Methodology

- Used fixed in-memory Planner candidates only.
- Compared the default Planner NSOM Moon model with the feature-flagged Moon geometry model.
- Experimental flag under review: `experimental_moon_geometry_scoring`.
- Held sky quality, weather, equipment, target score and session context stable inside each comparison.
- Treated RecommendationConfidence as metadata only; it is not part of the score formula.
- Marked this tooling as developer-only and kept it outside runtime imports/QML.

## Scenario Matrix

| Geometry Case | Target | Flag Off Score | Flag On Score | Score Delta | Lunar Background Delta | Geometry Factor | Expectation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| missing | Pianeta | 46.7127 | 46.7127 | +0.0000 | +0.0000 | 1.000 | flag-on matches the illumination-only baseline |
| missing | Luna | 47.8215 | 47.8215 | +0.0000 | +0.0000 | 1.000 | flag-on matches the illumination-only baseline |
| missing | Galaxy | 28.1248 | 28.1248 | +0.0000 | +0.0000 | 1.000 | flag-on matches the illumination-only baseline |
| missing | Nebula | 28.2137 | 28.2137 | +0.0000 | +0.0000 | 1.000 | flag-on matches the illumination-only baseline |
| missing | Open Cluster | 37.1273 | 37.1273 | +0.0000 | +0.0000 | 1.000 | flag-on matches the illumination-only baseline |
| missing | Globular Cluster | 33.7743 | 33.7743 | +0.0000 | +0.0000 | 1.000 | flag-on matches the illumination-only baseline |
| set_before_window | Pianeta | 46.7127 | 46.7127 | +0.0000 | +0.0000 | 0.000 | lunar sky-background penalty is removed |
| set_before_window | Luna | 47.8215 | 47.8215 | +0.0000 | +0.0000 | 0.000 | lunar sky-background penalty is removed |
| set_before_window | Galaxy | 28.1248 | 37.4997 | +9.3749 | +0.2500 | 0.000 | lunar sky-background penalty is removed |
| set_before_window | Nebula | 28.2137 | 36.1136 | +7.8998 | +0.2188 | 0.000 | lunar sky-background penalty is removed |
| set_before_window | Open Cluster | 37.1273 | 39.6025 | +2.4752 | +0.0625 | 0.000 | lunar sky-background penalty is removed |
| set_before_window | Globular Cluster | 33.7743 | 38.0556 | +4.2812 | +0.1125 | 0.000 | lunar sky-background penalty is removed |
| low_altitude_close | Pianeta | 46.7127 | 46.7127 | +0.0000 | +0.0000 | 0.338 | low altitude softens the close-separation penalty |
| low_altitude_close | Luna | 47.8215 | 47.8215 | +0.0000 | +0.0000 | 0.338 | low altitude softens the close-separation penalty |
| low_altitude_close | Galaxy | 28.1248 | 34.3357 | +6.2109 | +0.1656 | 0.338 | low altitude softens the close-separation penalty |
| low_altitude_close | Nebula | 28.2137 | 33.4474 | +5.2336 | +0.1449 | 0.338 | low altitude softens the close-separation penalty |
| low_altitude_close | Open Cluster | 37.1273 | 38.7671 | +1.6398 | +0.0414 | 0.338 | low altitude softens the close-separation penalty |
| low_altitude_close | Globular Cluster | 33.7743 | 36.6106 | +2.8363 | +0.0745 | 0.338 | low altitude softens the close-separation penalty |
| high_altitude_close | Pianeta | 46.7127 | 46.7127 | +0.0000 | +0.0000 | 1.350 | close high Moon applies the strongest lunar background penalty |
| high_altitude_close | Luna | 47.8215 | 47.8215 | +0.0000 | +0.0000 | 1.350 | close high Moon applies the strongest lunar background penalty |
| high_altitude_close | Galaxy | 28.1248 | 24.8435 | -3.2812 | -0.0875 | 1.350 | close high Moon applies the strongest lunar background penalty |
| high_altitude_close | Nebula | 28.2137 | 25.4488 | -2.7649 | -0.0766 | 1.350 | close high Moon applies the strongest lunar background penalty |
| high_altitude_close | Open Cluster | 37.1273 | 36.2610 | -0.8663 | -0.0219 | 1.350 | close high Moon applies the strongest lunar background penalty |
| high_altitude_close | Globular Cluster | 33.7743 | 32.2759 | -1.4984 | -0.0394 | 1.350 | close high Moon applies the strongest lunar background penalty |
| high_altitude_far | Pianeta | 46.7127 | 46.7127 | +0.0000 | +0.0000 | 0.350 | large separation reduces the lunar background penalty |
| high_altitude_far | Luna | 47.8215 | 47.8215 | +0.0000 | +0.0000 | 0.350 | large separation reduces the lunar background penalty |
| high_altitude_far | Galaxy | 28.1248 | 34.2185 | +6.0937 | +0.1625 | 0.350 | large separation reduces the lunar background penalty |
| high_altitude_far | Nebula | 28.2137 | 33.3486 | +5.1349 | +0.1422 | 0.350 | large separation reduces the lunar background penalty |
| high_altitude_far | Open Cluster | 37.1273 | 38.7362 | +1.6089 | +0.0406 | 0.350 | large separation reduces the lunar background penalty |
| high_altitude_far | Globular Cluster | 33.7743 | 36.5571 | +2.7828 | +0.0731 | 0.350 | large separation reduces the lunar background penalty |

## Ownership Checks

| Check | Value |
| --- | --- |
| `strict_json_compatible` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `only_lunar_environment_component_changes` | `True` |
| `confidence_has_zero_score_effect` | `True` |
| `flag_default_off_documented` | `True` |

## Calibration Observations

- Deep-sky rows reduced by close Moon geometry: `4`.
- Deep-sky rows improved when the Moon is set before the target window: `4`.
- Planet/Moon rows protected from lunar background deltas: `10`.
- Rows where only the lunar sky-background component changed: `30`.
- Rows with non-zero confidence score effect: `0`.

## Review Notes

- This report is not a weight-tuning step.
- It is evidence for whether Moon geometry should eventually be enabled by default.
- If calibration is needed, it should stay inside the Sky/ObservationEnvironment Moon-background layer.
- AOD and OpenAQ remain separate provider-backed inputs and are not evaluated by this report.

## Recommended Next Step

Review this calibration output before enabling Moon geometry by default or moving to AOD/OpenAQ scoring.
