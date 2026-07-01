# NightScope Architecture

This document describes the current NightScope architecture as reviewed for the
v1.0 release candidate. It is descriptive, not a redesign proposal.

## Project Structure

NightScope is organized around a small desktop application package:

- `astro_viewer/main.py`: application entry point, CLI smoke-test entry points,
  QApplication setup and QML loading.
- `astro_viewer/app/ui`: QML pages, components, theme and presentation logic.
- `astro_viewer/app/viewmodels`: Qt-facing controller/ViewModel layer. The main
  object is `AppController`.
- `astro_viewer/app/services`: business services for astronomy, weather,
  observing quality, planning, equipment recommendations, light pollution,
  NASA/OpenAQ data providers, seeing/transparency, notifications and logging.
- `astro_viewer/app/astronomy`: astronomy engine protocol, mock fallback,
  Skyfield-based engine and coordinate parsing helpers.
- `astro_viewer/app/database`: SQLite bootstrap, migrations, repositories and
  import helpers.
- `astro_viewer/app/models`: dataclasses used as service and controller DTOs.
- `astro_viewer/data`: schema, catalog CSV files, seed data and Skyfield
  ephemeris files. The runtime SQLite database is created as `nightscope.db`
  next to the application/repository root and is not distributed as seed data.
- `astro_viewer/resources`: icons, images and themes consumed by QML and build
  packaging.
- `astro_viewer/tests`: unittest/pytest-compatible regression tests.
- `astro_viewer/tools`: one-off import, validation and packaging-support tools.
- `packaging`: PyInstaller spec, hooks and Windows build script.

## Architectural Style

The application follows a pragmatic MVVM-style structure:

- QML owns layout, visual state and user interaction.
- `AppController` exposes Qt properties, slots and signals to QML.
- Services contain most domain decisions and calculations.
- Repositories own persistence and SQLite access.
- Models are simple dataclasses used to move structured data between layers.

The current implementation is coherent, but the ViewModel/controller layer has
grown beyond a narrow presentation adapter. `AppController` also orchestrates
refresh flows, profile mutation, object formatting, weather digests, calendar
presentation and recommendation enrichment.

## NightScope Observation Model

NightScope's long-term scoring and planning direction is defined by
[NSOM 1.0 - NightScope Observation Model](NIGHTSCOPE_OBSERVATION_MODEL_1_0.md).

NSOM separates:

- Universe / Intrinsic Target
- Sky / Observation Environment
- Effective Observability
- Observable Target Value
- Observer Capability
- Practical Target Value
- Observation Opportunity
- Planner
- Recommendation Confidence

Future scoring changes should be checked against this model before
implementation.

Current implementation status for `1.5.0`: `astro_viewer/app/models/nsom.py`
contains the first internal immutable NSOM core DTOs for Universe, Sky,
Observer, Session, Opportunity and Confidence ownership boundaries.
`astro_viewer/app/services/nsom_diagnostic_adapters.py` adapts existing runtime
objects and diagnostic snapshots into that core model without network calls or
heavy recomputation. `ObservationOpportunity` stores `SessionViability` as its
single session source of truth; the diagnostic `session_viability` value is a
read-only compatibility projection and cannot diverge from the session object.
`astro_viewer/app/services/planner_nsom_service.py` is the first real NSOM
consumer: `NightPlannerService` can use it behind the internal
`NSOM_PLANNER_SCORING_ENABLED` flag, which is `False` by default. With the flag
disabled, Planner continues to use the legacy `PlannerScoringService` ranking.
With the flag enabled, Planner candidates are converted to
`ObservationOpportunity` instances and ranked by opportunity value. In `1.4.2`
the experimental NSOM path no longer asks `PlannerScoringService` for
Moon/light-pollution condition ownership; `planner_nsom_service.py` builds the
NSOM `ObservationEnvironment` from Planner runtime inputs already in hand and
builds telescope-aware `ObserverCapability` before deriving
`PracticalTargetValue`. The diagnostic export is not exposed to QML, does not
write files, does not log automatically, does not emit signals and does not
recompute Planner, Home, Equipment or Sky Compass output. Confidence remains
parallel metadata and does not change recommendation score.
`astro_viewer/app/services/planner_nsom_comparison.py` adds an internal,
developer-only comparison helper for `1.4.3`. It computes legacy Planner scores
and experimental NSOM Planner opportunities from the same supplied runtime
inputs, then returns JSON-compatible dictionaries with score/rank deltas and
NSOM component projections. It is not connected to QML, performs no writes or
automatic logging, and does not change the default-off Planner NSOM flag.
`1.4.4` adds behavioural comparison fixtures that intentionally validate NSOM
rules rather than legacy equivalence: planets and the Moon stay protected from
sky-background penalties, galaxies and diffuse nebulae degrade more under bright
sky, session viability changes opportunity value without mutating target value,
equipment changes practical value without changing observable value, and
confidence remains score-neutral.
`1.4.5` adds developer-facing explanation projections to the experimental
Planner NSOM path. `PlannerNsomScoringService.explain_opportunity()` describes
target identity, final opportunity score, score components, main limiting
factors and main positive factors from the already-built
`ObservationOpportunity`. Sky-owned factors explain `EffectiveObservability`,
observer/equipment factors explain `PracticalTargetValue`, session factors
explain `SessionViability`, and `RecommendationConfidence` is projected only as
trust metadata with no score effect. The explanations are returned through the
internal comparison helper as JSON-compatible dictionaries and are not exposed
to QML, written to disk or logged automatically.
`1.4.6` adds `PlannerNsomCalibrationInspectionService`, another developer-only
helper layered on top of the comparison and explanation services. It produces
named scenario groups for bright sky, poor/good session conditions, small/large
telescopes, planet-favouring conditions, deep-sky-favouring conditions and a
Moon target case. Each group reports ranked NSOM opportunities, explanation
breakdowns, limiting/positive factors, legacy rank/score references and the
intended NSOM behavioural expectation. The helper is passive: it uses fixed
in-memory fixtures, returns JSON-compatible dictionaries, does not write files,
does not log automatically, performs no network work and is not connected to
QML.
`1.4.7` adds developer/test tooling in
`astro_viewer/tools/nsom_planner_comparison_report.py` plus the static report
`docs/NSOM_PLANNER_COMPARISON_REPORT.md`. The tool builds 108 deterministic
scenario rows across target type, sky, session, equipment, target geometry and
confidence axes, compares exposed legacy Planner score breakdowns with
experimental NSOM `ObservationOpportunity` explanations, and marks unavailable
legacy concepts explicitly. This is not imported by runtime services or QML and
does not tune weights or enable NSOM Planner by default.
`1.4.8` adds developer/test tooling in
`astro_viewer/tools/nsom_mathematical_trace_report.py` plus the static report
`docs/NSOM_MATHEMATICAL_TRACE_REPORT.md`. The tool reuses the existing
deterministic comparison matrix and traces the complete NSOM mathematical
pipeline for every scenario: `IntrinsicTargetQuality`,
`ObservationEnvironment`, `EffectiveObservability`, `ObservableTargetValue`,
`ObserverCapability`, `PracticalTargetValue`, observation window, chronology,
`SessionViability`, `ObservationOpportunity` and final Planner ranking.
`RecommendationConfidence` is reported outside that pipeline as trust metadata
with zero score effect. The report also aggregates common limiting/positive
factors and calibration concerns. It is generated only by explicit developer
tooling and is not connected to runtime services, QML, automatic logging,
network work or Planner scoring changes.
`1.4.8b` hardens that trace report for calibration review. All-zero
opportunity groups, including blocked sessions, are marked as tied and
non-actionable so deterministic stable order is not presented as a meaningful
recommendation. The trace expands lower-level formula diagnostics for Moon
background, sky background, atmospheric transparency, horizon/geometric
visibility and observer-capability derivation, marking values as
adapter-derived or unavailable where inputs are not retained. The deterministic
report fixtures now expose `observing_window_quality` values of `1.0`, `0.5`
and `0.0`, and component dominance language is explicitly frequency-based
rather than a statement about weight or calibrated sensitivity. The hardening
remains developer/report tooling only.
`1.4.9` adds formula parity and sensitivity evidence before calibration. The
trace report now carries expected/reported comparisons for reconstructable
sub-formulas, while adapter-derived or unavailable formulas remain explicitly
marked. Focused tests compare those report formulas with the actual NSOM
Planner service for Moon background, sky background, atmospheric transparency,
geometric/horizon visibility, observing-window quality, observer-capability
summary and SessionViability. Separate sensitivity fixtures isolate one
component at a time and assert direction plus ownership without tuning weights,
changing Planner scoring or enabling the NSOM Planner flag.
`1.5.0` adds a developer-only ObserverCapability target-specific review before
calibration. `astro_viewer/tools/nsom_observer_capability_review.py` builds
JSON-compatible fixtures that isolate aperture-only, focal-length-only,
mount/tracking-only, field-of-view-only and practical-comfort/setup-only
changes across planet, Moon, galaxy, diffuse nebula, open cluster and globular
cluster targets. The review is also summarized in the mathematical trace
report. It keeps sky/session inputs stable, verifies that observer changes do
not mutate `ObservableTargetValue`, and records that the current flat
`ObserverCapability.summary_for_planning()` produces uniform observer-summary
deltas across target classes. This is evidence for a future target-specific
weighting decision, not a calibration or scoring change.

## Dependency Flow

The intended dependency flow is:

`QML -> AppController -> services/repositories -> models/data`

The services do not depend on QML. Repositories do not depend on services. The
controller composes repositories and services and converts dataclasses into
QML-friendly dictionaries.

The astronomy layer depends on Skyfield/Astropy when available and provides a
mock fallback through `MockAstronomyEngine`. Weather, VIIRS and NASA AOD network
clients are isolated behind service classes.

No circular Python package dependency was found in the reviewed structure.

## Responsibilities

### QML

QML pages are responsible for:

- visual layout and responsive presentation,
- binding to controller properties,
- invoking controller slots,
- local display formatting when the formatting is purely visual.

Important pages:

- `HomePage.qml`: home dashboard, observing quality, best target, observing
  plan, planets, deep-sky objects and weather warning presentation.
- `ObjectCataloguePage.qml`: informational catalogue browser with search,
  filters and object-detail click-through. It renders catalogue data and does
  not present recommendation ranking.
- `ObjectDetailPage.qml`: selected object detail and setup alternatives.
- `EquipmentProfilesPage.qml`, `EquipmentTelescopesPage.qml`,
  `EquipmentOpticsPage.qml`: profile and equipment management.
- `LocationPage.qml`, `WeatherPage.qml`, `CalendarPage.qml`,
  `EventDetailPage.qml`: location, weather, calendar list and calendar event
  detail workflows.

### AppController

`AppController` is the central Qt-facing object. It owns:

- current location state,
- current weather hours and weather summary,
- base and enriched solar-system objects,
- base and enriched deep-sky objects,
- Moon summary,
- visible planet/deep-sky lists,
- active profile equipment snapshot,
- sky quality, seeing/transparency and advanced scores,
- night plan, sky map, Sky Compass and notifications,
- generic catalogue object dictionaries and catalogue filter state,
- selected object and detail dictionaries,
- calendar event setup text and object-detail target mapping,
- QML signals for every major dependent property.

It also coordinates:

- startup loading,
- location refresh,
- weather refresh,
- VIIRS refresh,
- profile/equipment refresh,
- recomputation of best object, plan, sky map, Sky Compass, notifications and
  selected detail.

### Services

Services hold business logic:

- `ObservingScoreService`: global observing score and best-object selection.
- `AdvancedObservingService`: separate planetary and deep-sky quality scores.
- `SeeingTransparencyService`: seeing/transparency estimation from forecast
  fields and sky quality.
- `NightPlannerService`: ordered observing plan, weather blocking and
  chronological plan presentation. It delegates Planner ranking math to
  `PlannerScoringService`.
- `PlannerScoringService`: Planner-specific score aggregation, diagnostic
  breakdown, weather factor, difficulty factor and Planner-specific
  light-pollution penalty. It reuses shared Moon-condition primitives from
  `ObservationConditionsService`.
- `EquipmentService`: magnification, true field, exit pupil, profile
  capabilities and setup recommendation.
- `LightPollutionService`: sky-quality lookup from cache, local CSV providers,
  NASA VIIRS and offline fallback.
- `NasaAodProvider`: NASA MAIAC aerosol lookup using VIIRS primary and MODIS
  fallback. `AppController` starts it in the background when a valid location
  exists and Earthdata credentials have a successful connection test. It returns
  compact processed AOD results for the Weather page `Trasparenza atmosferica`
  section, but remains disconnected from seeing/transparency, Planner,
  Recommendation Engine, Sky Compass and observing scores.
- `ObservationConditionsService`: shared equivalence layer for observing
  condition adjustments. It owns Home/Detail Moon-adjusted scores, the existing
  deep-sky light-pollution context formerly implemented inside `AppController`,
  batch conditioning for Home/Sky Compass candidates and neutral diagnostic
  placeholders for future weather/seeing/transparency/equipment inputs.
  It accepts provider-neutral NASA AOD and particulate inputs as diagnostic-only
  data with freshness notes, while keeping their score modifiers neutral.
  Runtime diagnostic freshness is explicit: NASA AOD older than seven days is
  omitted from diagnostic inputs; fresh/recent NASA AOD is included
  diagnostically only. OpenAQ data is included diagnostically when the
  `LocalAtmosphere` result has usable data, including stale-but-present readings,
  and omitted when historical, failed, unavailable or unconfigured. These inputs
  are not exposed to QML and do not affect Planner, Home, equipment, weather,
  seeing/transparency, advanced scores or Sky Compass.
  Deep-sky light-pollution conditioning marks targets with an internal condition
  flag so repeated passes do not reapply the same presentation penalty; the flag
  is intentionally removed from the QML payload.
  It does not own Planner score aggregation, equipment recommendations,
  best-object selection, OpenAQ or NASA AOD behavior.
- `OpenMeteoWeatherService`: forecast retrieval and weather cache integration.
- `SkyMapService`: compact sky-map DTO generation.
- `SkyCompassService`: guidance DTO generation for the Sky Compass assistant
  from already prepared Home targets; it does not call weather, VIIRS, Planner
  or recommendation services.
- `NotificationService`: dashboard notifications from current conditions.
- `LocationService`: Windows, IP and manual location providers.

### Repositories

Repositories own SQLite persistence:

- `CityRepository`: city search and reverse lookup.
- `MessierRepository`: Messier catalog rows.
- `EquipmentCatalogRepository`: telescope, eyepiece, Barlow and equipment
  profile CRUD and profile assignments.
- `WeatherCacheRepository`: weather response cache.
- `SkyQualityRepository`: light-pollution estimate cache.
- `ObjectImageRepository`: image and description lookup.
- `ObservationRepository`: observation history.

Repositories should not contain scoring or recommendation logic. The reviewed
repositories mostly respect this boundary.

## Data Flow

Startup flow:

1. `main.py` creates the application and `AppController`.
2. `AppController` initializes database-backed catalogs and profiles.
3. The astronomy engine builds base solar-system, Moon, calendar and deep-sky
   data for the current location if one is available.
4. Weather, sky quality, seeing, advanced scores, equipment recommendations and
   planning are layered on top.
5. QML receives property change signals and renders dictionaries exposed by the
   controller.

Home recommendation flow:

1. Astronomy engine produces base objects.
2. `AppController` applies active-profile equipment recommendations.
3. Deep-sky objects may be adjusted by light-pollution context and Home/Detail
   Moon context through `ObservationConditionsService`.
4. `ObservingScoreService` selects the best object.
5. `NightPlannerService` produces the observing plan unless weather is
   blocking, using `PlannerScoringService` for Planner-specific ranking.
6. `AppController` exposes the centralized blocking state to QML.
7. QML presents the plan, a global "Sessione da monitorare" warning with a
   potential observing window, or a full "Sessione sconsigliata" warning when
   no useful window is expected.

Catalogue browsing flow:

1. `AppController` loads catalogue rows from repository-backed local data.
2. The current implementation maps Messier rows into a generic catalogue item
   shape with `catalogue`, `object_id`, `catalogue_id`, type, constellation,
   magnitude, size, observation-type metadata and description.
3. `ObjectCataloguePage.qml` applies controller-backed search and filters for
   catalogue, object type, constellation and observation type.
4. `selectCatalogueObject` resolves the catalogue object and creates a
   detail-compatible object without invoking weather, equipment suggestions,
   best-object scoring, planner ranking or `recommended_deep_sky()`.
5. Object Detail is reused for click-through, with back navigation returning
   to the catalogue page when that was the source.

Object detail flow:

1. QML selects an object.
2. `AppController` resolves the selected object from current enriched lists.
3. Detail fields, setup options and reasoning are generated from the selected
   object, active equipment, weather, Moon, seeing and sky quality.

Calendar event detail flow:

1. `CalendarPage.qml` selects an event from the inline calendar list.
2. `EventDetailPage.qml` renders practical observing text, profile guidance and
   field tips without changing event calculations.
3. `AppController._event_to_qml` enriches events with active-profile setup text
   and `targetObjectId` when the event maps to a known object.
4. Planetary opposition/conjunction events map to their planet object. Moon
   phases and lunar eclipses map to `moon`, allowing the existing object detail
   navigation to be reused.

## Refresh Flow

The controller refresh chain is the main consistency mechanism.

For a focused review of Home refresh timing, section dependencies and the
proposed future `ObservationSnapshot` read model for Home, Sky Compass and
Planner consumers, see `docs/HOME_REFRESH_LIFECYCLE_REVIEW.md`.

NightScope 1.2.x introduces `RefreshManager` as a lightweight lifecycle helper.
It does not own refresh work and does not decide whether QML is updated.
`AppController` remains the QML-facing orchestrator, while `RefreshManager`
classifies refresh reasons and domains, tracks dirty domains and documents
which dependencies are affected by each refresh family.

Current refresh domains are:

- `LOCATION`
- `ASTRONOMY`
- `WEATHER`
- `SKY_QUALITY`
- `AIR_QUALITY`
- `AOD`
- `EQUIPMENT`
- `PLANNER`
- `COMPASS`
- `COMPASS_LIVE`
- `CATALOG`

Current refresh reasons are:

- `STARTUP`
- `MANUAL`
- `LOCATION_CHANGED`
- `PROVIDER_CHANGED`
- `API_KEY_CHANGED`
- `EQUIPMENT_CHANGED`
- `BORTLE_CHANGED`
- `TTL_EXPIRED`
- `WEATHER_TTL_EXPIRED`
- `AIR_QUALITY_TTL_EXPIRED`
- `AOD_TTL_EXPIRED`
- `SKY_QUALITY_TTL_EXPIRED`
- `ASYNC_COMPLETED`
- `WEATHER_COMPLETED`
- `AIR_QUALITY_COMPLETED`
- `AOD_COMPLETED`
- `SKY_QUALITY_COMPLETED`
- `LIVE_TICK`

The generic `TTL_EXPIRED` and `ASYNC_COMPLETED` reasons are intentionally
neutral. Operational refresh dispatch should use the domain-specific reasons so
display-only OpenAQ/AOD updates cannot dirty Planner, equipment or Sky Compass
state by accident.

`LIVE_TICK` is the Sky Compass live refresh lane. It maps only to
`COMPASS_LIVE`, which is separate from the broader `COMPASS` domain used by
normal Home/Planner/weather-driven recomputation. The live lane updates only
current positional fields for already prepared Sky Compass targets and must not
call weather, OpenAQ, NASA AOD, VIIRS, Planner, equipment or Recommendation
Engine refresh paths.

The following changes are expected to trigger dependent recomputation:

- active profile switch,
- profile equipment assignment/removal,
- profile equipment deletion,
- catalog equipment addition when assigned to the active profile,
- location change,
- valid weather refresh,
- sky-quality refresh,
- VIIRS refresh completion,
- astronomy catalog reload caused by location or sky-quality context,
- selected object change.

Important methods:

- `_refresh_weather_and_conditions`
- `_finish_weather_refresh`
- `_finish_viirs_sky_quality_refresh`
- `_finish_nasa_aod_refresh`
- `_refresh_active_profile_dependencies`
- `_refresh_equipment_recommendations_for_current_objects`
- `_recalculate_observing_outputs`
- `_emit_profile_dependent_changes`

The refresh chain currently recomputes:

- best object,
- observing plan,
- visible planets,
- visible deep-sky objects,
- sky map,
- observing scores,
- recommended setups,
- selected-object setup/detail data.

NASA AOD refresh completion updates only the display DTO consumed by the Weather
page and logs product/date/value/status. It does not recompute Home, Planner,
Sky Compass, seeing/transparency, weather score, observing scores or
recommendation outputs.

Sky Compass live refresh is controller-owned and runs on a 60-second `QTimer`
only when a valid location, an available compass DTO and a stored candidate
snapshot exist. Normal Home/Planner refreshes compute `_sky_compass_candidates()`
and store the result in `AppController._sky_compass_candidate_snapshot`. The
live tick never calls `_sky_compass_candidates()`: it uses
`SkyfieldAstronomyEngine.refresh_current_positions()` to update current
altitude, azimuth and direction for the stored snapshot, emits only
`skyCompassChanged` and clears `COMPASS_LIVE` after the update.

Recent tests cover profile assignment, Barlow assignment, empty-profile
assignment and active-profile switching without restart.

## Cache Ownership

Weather cache:

- Owner: `OpenMeteoWeatherService` plus `WeatherCacheRepository`.
- Key: latitude, longitude, timezone and 24-hour forecast shape.
- Lifetime: 45 minutes.
- Force refresh bypasses fresh cache.
- On network failure, stale cached data may be reused when available.

Sky-quality cache:

- Owner: `LightPollutionService` plus `SkyQualityRepository`.
- Key: rounded latitude, longitude and city.
- Local cache is reused unless it is recognized as a legacy/stale source.
- NASA Black Marble VIIRS cache entries are treated as fresh if present.
- There is no general age-based TTL for sky-quality estimates.

NASA AOD cache:

- Owner: `NasaAodProvider`.
- Key: rounded latitude/longitude, with result metadata preserving product and
  granule id.
- Lifetime: 18 hours.
- Only compact processed AOD results are cached. The provider keeps an in-memory
  copy for the current process and a small JSON cache so app restarts can reuse
  recent processed results.
- Downloaded VIIRS/MODIS granules are temporary and deleted after extraction.

In-memory controller caches:

- base solar-system objects,
- base deep-sky objects,
- equipment-enriched object lists,
- weather hours,
- sky quality,
- seeing/transparency,
- advanced scores,
- night plan,
- sky map,
- notifications,
- selected-object dictionary.

These are invalidated by controller refresh methods, not by a standalone cache
manager.

## Duplicated Logic And Technical Debt

The following duplication or concentration of responsibility should be tracked:

- Weather blocking is centralized in `NightPlannerService.weather_blocking_status`.
  `AppController` exposes `isObservingSessionBlocked`, `blockingReason`,
  `blockingDetail` and `suggestedObservingWindow`; QML renders those values
  without duplicating the thresholds.
- Score labels are implemented in `ObservingScoreService` and also separately
  in the astronomy engine for raw object scores.
- Night-hour selection is repeated in observing score, seeing estimation and
  home weather digest logic with slightly different ranges.
- Moon parsing from string percentages is repeated in multiple services.
- Light-pollution handling intentionally has two current contexts:
  Home/Detail deep-sky presentation context in `ObservationConditionsService`
  and Planner-specific ranking penalty in `PlannerScoringService`. These
  formulas are behavior-preserving and should not be merged without dedicated
  equivalence tests.
- Moon sensitivity is centralized in `ObservationConditionsService`, while
  `PlannerScoringService` owns how that penalty is combined with Planner
  weather, difficulty and aperture factors.
- `AppController` is oversized and mixes controller, presenter and orchestration
  responsibilities.
- `HomePage.qml` is also large and contains non-trivial presentation decisions.
- `EquipmentProfile.telescope_id` remains as a legacy single-telescope field
  while many-to-many profile assignment tables hold the current multi-equipment
  model.

These are not immediate functional failures, but they are the main
maintainability risks for a 1.0 codebase.

## Maintenance Guidance

For future changes:

- Put new calculation rules in services, not QML.
- Keep repositories focused on persistence.
- Treat `AppController` as an orchestration boundary; avoid adding new
  algorithms there unless they are purely presentation-specific.
- When changing profile/equipment behavior, add tests that assert immediate
  refresh of home, detail and calendar/profile-dependent outputs.
- When changing weather blocking thresholds, update
  `NightPlannerService.weather_blocking_status` and keep QML as a renderer of
  controller state.
- When changing Moon or light-pollution logic, verify Home/Detail conditioned
  objects and Planner ranking separately for galaxies, nebulae, globular
  clusters and open clusters.
- Before enabling new AOD/OpenAQ, Moon-geometry or transparency scoring, use
  `docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md` as the mathematical ownership and
  double-counting reference.
- When changing calendar event copy or event-to-object linking, keep practical
  text in `EventDetailPage.qml` and target/setup enrichment in `AppController`.
