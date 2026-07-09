# NSOM Moon Geometry Planner Default-On Readiness

## Executive Summary

This developer-only audit decides whether the default-off Planner Moon geometry path has enough evidence for a separate default-on switch. It does not enable the switch, tune weights, alter Planner ranking, expose QML, log automatically, call the network or write runtime files.

## Readiness Verdict

- Verdict: `moon_geometry_planner_ready_for_default_on_switch`.
- Ready for default-on switch: `True`.
- Default-on switch completed: `False`.
- Requires separate switch: `True`.
- Current default flag: `ObservationConditionFeatureFlags.experimental_moon_geometry_scoring = False`.
- NightPlannerService default uses Moon geometry: `False`.
- Opt-in path available: `True`.
- Ready for AOD/OpenAQ scoring: `False`.
- Recommended next step: Review 1.14.5, then implement a narrow default-on switch for Planner Moon geometry if accepted.
- Reason: The 1.14.4 calibration evidence is directionally coherent, score ownership stays in Sky/ObservationEnvironment, missing geometry falls back to the illumination-only baseline, and confidence remains score-neutral. The current runtime default is still off, so a separate switch is required.

## Default-On Blockers

- None for a narrow Planner Moon geometry default-on switch.

## Decisions

| Decision | Status | Blocks default-on | Summary | Evidence |
| --- | --- | --- | --- | --- |
| `calibration_direction` | `accepted_for_default_on_review` | `False` | Moon geometry changes follow expected NSOM direction without legacy score matching. | close_reduced=4; set_before_window_improved=4 |
| `missing_geometry_fallback` | `accepted` | `False` | Missing geometry keeps the illumination-only baseline and leaves Moon-geometry confidence unknown. | missing_identity=True |
| `protected_targets` | `accepted` | `False` | Planets and Moon remain protected from lunar sky-background damage. | protected_rows_without_delta=10 |
| `ownership_boundary` | `accepted` | `False` | The experimental effect is confined to the Sky-owned lunar_sky_background component. | only_lunar_rows=30 |
| `confidence_metadata` | `accepted` | `False` | RecommendationConfidence remains metadata and has zero score effect. | rows_with_confidence_score_effect=0 |
| `runtime_cost` | `monitor_after_switch` | `False` | Default-on would add bounded local ephemeris sampling for Planner targets only when location is available. | no_network; app_controller_builds_geometry_only_when_service_flag_is_true |
| `aod_openaq_scope` | `deferred` | `False` | AOD/OpenAQ provider scoring remains out of scope until Moon geometry is closed. | provider_inputs_not_evaluated_by_moon_geometry_audit |

## Representative Cases

| Case | Target | Score Delta | Lunar Background Delta | Confidence Effect | Interpretation |
| --- | --- | ---: | ---: | ---: | --- |
| missing | galaxy | +0.0000 | +0.0000 | +0.0000 | Missing geometry preserves the baseline. |
| set_before_window | galaxy | +9.3749 | +0.2500 | +0.0000 | Moon outside the window removes deep-sky penalty. |
| high_altitude_close | galaxy | -3.2812 | -0.0875 | +0.0000 | Close high Moon reduces deep-sky opportunity. |
| high_altitude_far | galaxy | +6.0937 | +0.1625 | +0.0000 | Large separation softens deep-sky penalty. |
| high_altitude_close | planet | +0.0000 | +0.0000 | +0.0000 | Planet remains protected from lunar background damage. |

## Remaining Non-Blocking Items

- `visible_moon_geometry_explanation`: Defer until a separate UI/explanation design step.
- `runtime_ephemeris_cost_monitoring`: Monitor after switch; calculations are local and bounded.
- `aod_openaq_provider_scoring`: Handle after Moon geometry default-on review is closed.

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `calibration_report_developer_only` | `True` |
| `calibration_runtime_writes_absent` | `True` |
| `calibration_network_absent` | `True` |
| `calibration_qml_exposure_absent` | `True` |
| `calibration_scenario_count_ok` | `True` |
| `deep_sky_close_moon_reduces_value` | `True` |
| `moon_set_before_window_improves_deep_sky` | `True` |
| `planet_and_moon_protected` | `True` |
| `only_lunar_environment_component_changes` | `True` |
| `confidence_zero_score_effect` | `True` |
| `missing_geometry_keeps_baseline` | `True` |
| `feature_flag_default_off_now` | `True` |
| `night_planner_default_off_now` | `True` |
| `opt_in_path_available` | `True` |
| `all_decisions_non_blocking` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Static Wiring Checks

| Check | Result |
| --- | --- |
| `runtime_report_import_matches` | `[]` |
| `qml_report_exposure_matches` | `[]` |

## Recommended Next Step

If review accepts this audit, implement the smallest possible default-on switch for Planner Moon geometry. Keep AOD/OpenAQ out of scope until after that switch is reviewed.
