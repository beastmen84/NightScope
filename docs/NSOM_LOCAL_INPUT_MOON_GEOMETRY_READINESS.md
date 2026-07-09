# NSOM Local Input and Moon Geometry Readiness

## Executive Summary

This developer-only audit separates NightScope input sources into local always-available astronomy, local optional equipment and external optional providers. It confirms that Moon geometry is available as a runtime diagnostic and as a default-off Planner NSOM scoring input computed from the active location and local astronomy engine without network, weather, VIIRS, AOD or OpenAQ. No default runtime scoring, ranking, QML, logging, network or runtime file-write behaviour changes.

## Verdict

- Verdict: `local_input_moon_geometry_runtime_diagnostics_available`.
- Moon geometry scoring enabled now: `False`.
- Moon geometry ready for local implementation: `True`.
- Moon geometry runtime diagnostics available: `True`.
- Moon geometry Planner scoring path available: `True`.
- First scoring candidate: `moon_geometry_behind_experimental_flag`.
- Requires provider before next step: `False`.
- Blocks current default-on surfaces: `False`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next step: Review docs/NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS.md, then implement a narrow Planner Moon geometry default-on switch if accepted.
- Reason: Location plus local ephemeris data now computes Moon altitude, Moon-target separation and window overlap without weather, VIIRS, AOD or OpenAQ. Current default runtime scoring still uses Moon illumination only; the experimental Planner path can apply geometry to ObservationEnvironment.lunar_sky_background when experimental_moon_geometry_scoring is enabled.

## Data Source Taxonomy

| Source | Availability | External provider | NSOM owner | Current scoring role | Missing-input policy |
| --- | --- | --- | --- | --- | --- |
| `location` | minimum_required_input | `False` | Sky / geometry context | required before Home recommendations can be computed | recommendations cannot be meaningful until location exists |
| `local_astronomy_ephemeris` | available_after_location | `False` | Universe and Sky | target positions, visibility, Moon phase and illumination | fallback engine keeps UI usable but lowers astronomical fidelity |
| `equipment_profile` | optional_local | `False` | Observer | ObserverCapability and PracticalTargetValue where applicable | use naked-eye/default observer assumptions |
| `weather_open_meteo` | optional_external | `True` | Session | SessionViability and weather blocking when available | weather-dependent conclusions remain unknown or fallback-safe |
| `sky_quality_viirs_or_fallback` | optional_hybrid | `hybrid` | Sky | static_sky_background when VIIRS radiance or fallback exists | distinguish real VIIRS radiance from fallback sky quality |
| `nasa_aod` | optional_external | `True` | Sky / Confidence future aerosol component | display and diagnostic only; score-neutral in current runtime | omit from scoring and confidence notes when unavailable |
| `openaq_particulate` | optional_external | `True` | Sky / Confidence future particulate component | display and diagnostic only; score-neutral in current runtime | omit or mark unavailable/historical according to freshness |

## Moon Geometry Field Inventory

| Field | Status | Source today | Required implementation | Score role now |
| --- | --- | --- | --- | --- |
| `moon_phase` | `active_current` | MoonSummary.phase | already available | display and Moon context |
| `moon_illumination` | `active_current` | MoonSummary.illumination | already available | active lunar_sky_background / existing Moon adjustment input |
| `moon_phase_angle` | `active_current` | MoonSummary.phase_angle | already available | display/context only |
| `moon_altitude_deg` | `runtime_score_neutral_geometry_input` | MoonGeometrySummary -> MoonGeometryConditionInput; absent from MoonSummary | implemented from sampled Moon altitude and local ephemeris | default score-neutral; Planner flag can use it through lunar_sky_background |
| `moon_target_separation_deg` | `runtime_score_neutral_geometry_input` | MoonGeometrySummary -> MoonGeometryConditionInput; absent from MoonSummary | implemented as angular Moon-target separation at bounded window samples | default score-neutral; Planner flag can use it through lunar_sky_background |
| `moon_above_horizon` | `runtime_score_neutral_geometry_input` | MoonGeometrySummary -> MoonGeometryConditionInput; derived from sampled altitude | implemented from Moon altitude samples, not from display strings | default score-neutral; Planner flag can use it through lunar_sky_background |
| `moon_visible_during_target_window` | `runtime_score_neutral_geometry_input` | MoonGeometrySummary -> MoonGeometryConditionInput | implemented by comparing Moon samples with target window samples | default score-neutral; Planner flag can use it through lunar_sky_background |
| `moon_set_before_target_window` | `runtime_score_neutral_geometry_input` | MoonGeometrySummary -> MoonGeometryConditionInput | implemented from sampled Moon geometry relative to target window | default score-neutral; Planner flag can use it through lunar_sky_background |

## Current Moon Consumers

| Consumer | Current Moon input | Geometry input | Score status | Notes |
| --- | --- | --- | --- | --- |
| Planner NSOM | MoonSummary.illumination | default-off experimental scoring input | default active illumination-only lunar_sky_background; flag can apply geometry | Moon altitude and separation affect only ObservationEnvironment.lunar_sky_background when experimental_moon_geometry_scoring is enabled. |
| Home recommendedDeepSky NSOM | MoonSummary.illumination | diagnostic export only | active illumination-based ObservableTargetValue background | Home intentionally excludes session/weather/equipment from ObservableTargetValue. |
| Best Object NSOM | MoonSummary.illumination through Home observable adapter | diagnostic export only | active through ObservableTargetValue and Opportunity | SessionViability remains separate from target and sky physics. |
| Sky Compass NSOM | MoonSummary.illumination through Home observable adapter | diagnostic export only | active as candidate base only | Direction policy remains presentation/context outside target physics. |
| ObservationConditions legacy compatibility | MoonSummary.illumination | diagnostic notes only when supplied | geometry modifier is neutral | Existing presentation compatibility score remains bounded by raw/display policy. |
| AOD/OpenAQ | none | none | external provider data remains score-neutral | Do not combine aerosol and Moon work in the same implementation step. |

## Moon Readiness Contract

| Requirement | Value |
| --- | --- |
| `requires_location` | `True` |
| `requires_current_time_or_session_window` | `True` |
| `requires_weather_provider` | `False` |
| `requires_viirs_provider` | `False` |
| `requires_nasa_aod` | `False` |
| `requires_openaq` | `False` |
| `requires_equipment_profile` | `False` |
| `calculation_layer` | `SkyfieldAstronomyEngine.moon_geometry` |
| `nsom_owner` | `Sky / ObservationEnvironment` |
| `first_consumer` | `Planner before Home` |
| `sampling_policy` | `bounded start/mid/best/end samples` |
| `confidence_policy` | `RecommendationConfidence metadata only` |
| `planner_scoring_flag` | `experimental_moon_geometry_scoring` |
| `planner_scoring_default` | `False` |
| `moon_geometry_planner_scoring_path_available` | `True` |
| `planner_scoring_owner` | `Sky / ObservationEnvironment.lunar_sky_background` |
| `current_geometry_factor_example` | `0.65` |
| `current_modifier_with_flag_off` | `0.0` |
| `current_modifier_with_flag_on` | `0.0` |

## Source Marker Checks

| Surface | Path | All markers found | Missing markers |
| --- | --- | --- | --- |
| Manual and automatic location inputs | `astro_viewer/app/viewmodels/app_controller.py` | `True` | `[]` |
| Skyfield Moon summary | `astro_viewer/app/astronomy/skyfield_engine.py` | `True` | `[]` |
| MoonSummary runtime DTO | `astro_viewer/app/models/observing.py` | `True` | `[]` |
| MoonGeometrySummary runtime DTO | `astro_viewer/app/models/observing.py` | `True` | `[]` |
| Skyfield Moon geometry diagnostics | `astro_viewer/app/astronomy/skyfield_engine.py` | `True` | `[]` |
| Moon geometry future condition input | `astro_viewer/app/services/observation_conditions_service.py` | `True` | `[]` |
| NSOM runtime Moon geometry diagnostics | `astro_viewer/app/viewmodels/app_controller.py` | `True` | `[]` |
| AOD and OpenAQ neutral condition inputs | `astro_viewer/app/services/observation_conditions_service.py` | `True` | `[]` |
| Planner NSOM moon background | `astro_viewer/app/services/planner_nsom_service.py` | `True` | `[]` |
| Home NSOM moon background | `astro_viewer/app/services/home_nsom_observable.py` | `True` | `[]` |
| VIIRS sky-quality distinction | `astro_viewer/app/models/sky.py` | `True` | `[]` |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `minimum_location_source_documented` | `True` |
| `local_astronomy_is_not_external_provider` | `True` |
| `equipment_default_is_local_optional` | `True` |
| `weather_marked_external_optional` | `True` |
| `viirs_source_distinguishes_fallback` | `True` |
| `aod_openaq_external_score_neutral` | `True` |
| `moon_summary_has_phase_illumination` | `True` |
| `moon_geometry_fields_are_runtime_diagnostics` | `True` |
| `moon_geometry_absent_from_moon_summary` | `True` |
| `moon_geometry_requires_no_provider` | `True` |
| `moon_geometry_modifier_still_neutral` | `True` |
| `moon_geometry_planner_scoring_path_available` | `True` |
| `source_markers_all_found` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `no_scoring_change` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.14.1`: Confirm the source taxonomy and Moon geometry readiness before adding runtime calculations.
- `1.14.2 Moon geometry diagnostics runtime`: Computed Moon altitude, Moon-target separation and Moon/window overlap from local astronomy samples; still score-neutral.
- `Review 1.14.2`: Confirm runtime Moon geometry diagnostics are physically sane, score-neutral and not wired into QML/runtime reports.
- `1.14.3 Moon geometry scoring behind flag`: Use the diagnostics in Planner ObservationEnvironment behind experimental_moon_geometry_scoring; keep the flag default-off.
- `Review 1.14.3`: Confirm default-off runtime behaviour, ownership boundaries and calibration risk before any Moon geometry default-on work.
- `1.14.4 Moon geometry Planner calibration`: Add deterministic developer-only fixtures comparing the illumination-only Planner path with the experimental Moon geometry path before any default-on decision.
- `Review 1.14.4`: Confirm calibration evidence, confidence metadata semantics and whether Moon geometry needs tuning before default-on.
- `1.14.5 Moon geometry Planner default-on readiness`: Classify the calibration evidence and decide whether a narrow Planner Moon geometry default-on switch is ready.
- `Review 1.14.5`: Confirm default-on readiness, default-off runtime state and non-blocking risks before changing the switch.
- `AOD/OpenAQ scoring readiness`: Only after Moon geometry, audit freshness, QA and double-counting before enabling provider-dependent aerosol scoring.

## Conclusion

The backend NSOM consumer migration is closed for current recommendation surfaces, and the physical model now has local Moon geometry diagnostics plus a default-off Planner NSOM scoring path. Moon altitude and Moon-target separation are deterministic once location and time are known, so the next step is review and calibration before any default-on Moon geometry, NASA AOD or OpenAQ scoring. AOD and OpenAQ remain optional provider inputs with freshness and confidence semantics.
