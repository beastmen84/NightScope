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
  NASA/OpenAQ data providers, seeing/transparency and logging.
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

NightScope's scoring and planning direction is defined by
[NSOM 1.0 - NightScope Observation Model](NIGHTSCOPE_OBSERVATION_MODEL_1_0.md).

NSOM separates Universe, Sky, Observer, Session, Opportunity and Confidence:

- Universe owns intrinsic target data.
- Sky owns the observation environment and effective observability.
- Observer owns capability and practical target value.
- Session owns viability/blocking state.
- Opportunity combines target, observer, timing and session for ranking.
- Recommendation Confidence is metadata and does not scale score.

Current runtime status for `1.20.0`:

- Planner, Home `recommendedDeepSky`, Best Object, Sky Compass and Detail/Object
  internal payload are NSOM-backed by default.
- Advanced Observing computes a backend/internal NSOM projection while preserving
  its existing visible contract.
- ObservationConditions applies the calibrated AOD/OpenAQ modifier by default
  only when provider-quality gates pass.
- Equipment remains setup-local; its current score is not replaced by an NSOM
  scalar, but ObserverCapability boundaries are explicit.
- Planner now consumes the telescope selected by `EquipmentService` for each
  target in a multi-instrument profile and emits four selected opportunities
  before chronological presentation.
- Home and Sky Compass share the complete useful-night target pool. Sky Compass
  filters live `observable_now` geometry and no longer lets plan/Best Object
  bonuses choose the direction.
- If the NSOM Sky Compass selector raises unexpectedly, the controller logs the
  failure and preserves the legacy payload fallback. Missing sky-quality input
  remains a normal, non-error fallback.
- `ObservingNightWindow` is the shared temporal boundary for astronomy,
  forecast selection, global score, seeing/transparency, Home, Planner and Sky
  Compass. Skyfield owns sunset/sunrise calculation and caches one result per
  location/night.
- Sampled target windows include the exact astronomical end as a boundary,
  interpolate altitude-threshold crossings and never use the sunrise boundary
  itself as a best-observation instant.
- The initial Open-Meteo lookup is a worker continuation of the asynchronous
  astronomy snapshot. The controller keeps the full-refresh loading state until
  the still-current weather result has been applied on the Qt thread.
- Weather presentation has a separate rolling boundary: `weatherNext24Hours`
  exposes the current local hour plus the following 23 hourly slots and marks
  active-night samples for QML. Observing score, seeing/transparency and NSOM
  consumers remain on the night-only `observingWeatherHourly` boundary. The
  cloud-chart night legend is presentation-only header content.
- The navigation sidebar consumes `homeObservingOverview.session` for its
  compact evening status. It does not expose the legacy weather score or feed
  any recommendation calculation.
- `HomeNightPlanOverviewService` owns the lower-Home presentation contract. It
  projects Session state, a count-based multi-equipment summary, four compact
  plan rows and score-free alternative rows without changing Planner ranking.
- Lower-Home alternatives are presented by observing-window start; shared best
  times and target category are tie-breaks, followed by a natural numeric name
  key suitable for Messier, Caldwell and future catalogue identifiers.
- `ObservingObjectDetailService` owns the score-free read model used by the
  observing detail opened from Home or Calendar. It combines live target
  geometry, Session metadata and target-specific Equipment selection while
  keeping the raw Catalogue branch on the existing `selectedObject` contract.
  Its Session badge is qualified locally (`Sessione ...`), so the compact Home
  payload and layout remain unchanged.
  `ObjectDetailPage.qml` switches between those contracts by source; the Moon
  cycle remains an observing-only extension. Observation persistence stays in
  the backend for a future dedicated log surface and is no longer embedded in
  object detail. Database bootstrap also corrects the exact legacy Moon
  `best_seen` typo without overwriting other seeded or user-held values.
- `CalendarOverviewService` projects the complete 365-day event set into a
  score-free read model. Event instant, observing window and local visibility
  are separate fields; future setups use profile capability without reusing
  tonight's seeing. Calendar QML and the Home event strip consume this read
  model; the legacy `events` property remains available only for compatibility
  and no event is removed by a usefulness cap.
- The checked-in source of truth is now the runtime code, active regression
  tests, `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md` and this architecture/model
  documentation. Historical migration reports and report generators were removed
  in `1.15.2` per `docs/NSOM_MIGRATION_ARTIFACT_CLEANUP_AUDIT.md`.
- The first visible follow-up is limited to Weather page condition-data
  semantics: AOD is labelled as aerosol data, OpenAQ as local particulate data,
  freshness is visible, and no NSOM ranking explanation panel is exposed.
- VIIRS cache hardening is active: cached Black Marble values are revalidated
  every 7 days while stale data remains available if NASA cannot be reached.
- AOD and OpenAQ worker completions carry a location key. A stale-location
  result is discarded and the current location is scheduled immediately; old
  provider presentation data is cleared as soon as the active location changes.
- AOD and VIIRS provider-cache lookups reuse a valid observation within 500
  metres to absorb normal Windows geolocation jitter. Exact location keys remain
  unchanged for asynchronous refresh identity and stale-result rejection. AOD
  performs this cache-only preflight before a background worker is started.
- Open-Meteo retains cached forecasts on provider failure and classifies
  retryable transport/server failures separately from permanent client/rate
  errors. Retryable failures schedule a forced lookup after five minutes;
  status-code logging excludes request coordinates and parameters.
- The upper Home overview has a dedicated read-only presentation boundary,
  `homeObservingOverview`. It separates Session state, weather index, NSOM
  category diagnostics and Moon impact. The upper QML cards consume this
  boundary: only the weather card exposes a numeric condition score, while
  planetary/deep-sky cards expose descriptive category diagnostics. Sky Compass
  consumes the same Session state only for copy/actionability: its direction,
  target selection and NSOM ranking remain unchanged.
- Upper-Home sky quality and lower-Home observing guidance share the same
  Bortle presentation mapping; class 7 is the suburban-to-urban transition.
- The overview boundary distinguishes startup location detection (`pending`)
  from a genuinely missing location (`unavailable`). Pending and no-data
  payloads are presentation-only states and cannot produce favourable category
  hints. Upper-card subtitles opt into two-line wrapping through `GlassCard`
  without changing the component default for other pages.

Runtime safety rules remain unchanged: no report tooling is wired into QML, no
automatic report logging is performed, and scoring must not trigger provider
network calls or runtime file writes.

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
  plan, visible-night alternatives and weather warning presentation. The lower
  surface renders `homeNightPlanOverview` through a state-aware plan card and a
  unified filterable table for non-plan visible targets.
- `ObjectCataloguePage.qml`: informational catalogue browser with search,
  filters and object-detail click-through. It renders catalogue data and does
  not present recommendation ranking.
- `ObjectDetailPage.qml`: selected object detail and setup alternatives.
- `EquipmentProfilesPage.qml`, `EquipmentTelescopesPage.qml`,
  `EquipmentOpticsPage.qml`: profile and equipment management.
- `LocationPage.qml`, `WeatherPage.qml`, `CalendarPage.qml`,
  `EventDetailPage.qml`: location, weather, calendar list and calendar event
  detail workflows. `WeatherPage.qml` presents AOD/OpenAQ as condition data
  sources with freshness, not as an NSOM ranking explanation surface.

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
- night plan and Sky Compass,
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
- recomputation of best object, plan, Sky Compass and
  selected detail.

### Services

Services hold business logic:

- `ObservingScoreService`: global observing score and best-object selection.
- `AdvancedObservingService`: separate planetary and deep-sky quality scores.
- `SeeingTransparencyService`: seeing/transparency estimation from forecast
  fields and sky quality.
- `NightPlannerService`: four-item observing plan, weather blocking and
  chronological plan presentation. It delegates default ranking to
  `PlannerNsomScoringService` and accepts selected telescopes by target.
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
  compact processed AOD results for the Weather page `Aerosol atmosferico`
  section and for gated `ObservationConditionsService` condition inputs. It
  remains disconnected from forecast transparency, seeing and provider refresh
  decisions.
- `ObservationConditionsService`: shared equivalence layer for observing
  condition adjustments. It owns Home/Detail Moon-adjusted scores, the existing
  deep-sky light-pollution context formerly implemented inside `AppController`,
  batch conditioning for Home/Sky Compass candidates and diagnostic placeholders
  for future weather/seeing/transparency/equipment inputs.
  It accepts provider-gated NASA AOD and particulate inputs with freshness
  notes. Since 1.14.19, the calibrated aerosol modifier is enabled by default
  through `ObservationConditionFeatureFlags.experimental_aerosol_scoring=True`;
  rollback is explicit by passing
  `ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)`.
  Runtime diagnostic freshness is explicit: NASA AOD older than seven days is
  omitted from condition inputs; fresh/recent NASA AOD is included when
  provider-quality gates accept it. OpenAQ data is included as fallback/context
  when the `LocalAtmosphere` result has usable data, including
  stale-but-present readings, and omitted when historical, failed, unavailable
  or unconfigured. The 1.14.7
  readiness audit documents fresh AOD as the future primary aerosol-column source
  and OpenAQ PM as fallback/context. The 1.14.8 policy hardens provider-quality
  and double-counting gates; 1.14.9 implements the target-specific default-off
  formula; 1.14.11 audits its calibration without tuning weights or enabling it;
  1.14.12 maps the class cap to transparency loss before deriving the score
  modifier; 1.14.13 records default-on readiness as blocked only by score-scale
  acceptance; 1.14.14 records field-like calibration fixtures for that scale,
  1.14.15 records a real-provider probe across five mixed locations,
  1.14.16 expands it to 15 mixed locations with policy reasons, and 1.14.17
  accepts the observed score scale while deferring default-on for temporal AOD
  freshness/repeatability evidence. 1.14.18 replays those same real AOD values
  as current and accepts the stale/current freshness policy without enabling the
  flag.
  These inputs are not exposed as NSOM fields in QML. WeatherPage may display
  their provider values and freshness, while condition-adjusted scores use them
  only through the explicit aerosol feature flag and provider-quality policy.
  Deep-sky light-pollution conditioning marks targets with an internal condition
  flag so repeated passes do not reapply the same presentation penalty; the flag
  is intentionally removed from the QML payload.
  It does not own Planner score aggregation, equipment recommendations,
  best-object selection, OpenAQ or NASA AOD behavior.
- `OpenMeteoWeatherService`: forecast retrieval and weather cache integration.
- `SkyCompassService`: guidance DTO generation for the Sky Compass assistant
  from already prepared Home targets; it does not call weather, VIIRS, Planner
  or recommendation services. Direction ranking combines current altitude,
  target value and density; plan/Best flags are annotations only.
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
4. `BestObjectNsomSelectionService` selects Best Object by default when weather
   and sky quality are available; `ObservingScoreService` remains only the
   missing-sky fallback after internal rollback cleanup.
5. `NightPlannerService` produces the observing plan unless weather is
   blocking, using the NSOM Planner path by default. `PlannerScoringService`
   remains available for developer-only legacy formula comparison. The four
   highest `ObservationOpportunity` values are selected before chronological
   ordering, using the setup telescope selected for each target.
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

Home refresh timing and section dependencies are now covered by the controller
refresh flow, runtime tests and the ObservationConditions read-model boundary.

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
OpenAQ/AOD Weather updates do not dirty Planner, equipment or Sky Compass state
by accident. Condition scoring consumes already available provider DTOs through
ObservationConditions rather than triggering provider refreshes from scoring.

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

Cold astronomy work is isolated from the Qt thread. Location/startup and night
rollover refreshes build an immutable snapshot containing the observing-night
window, Solar System objects, deep-sky objects, Moon summary, events, batched
Moon geometry and monthly catalogue visibility when required. The controller
accepts the snapshot only when its request id and location key are current,
then applies Equipment, weather and Planner continuations on the Qt thread.
VIIRS completion uses the same worker boundary for its deep-sky-only reload.

Sky Compass live refresh is controller-owned and runs on a 60-second `QTimer`
when a valid location and a stored nightly candidate snapshot exist. It keeps
running when the current compass DTO has no observable target, allowing later
rise/window transitions to become available automatically. Normal Home/Planner refreshes compute `_sky_compass_candidates()`
and store the result in `AppController._sky_compass_candidate_snapshot`. The
live tick never calls `_sky_compass_candidates()`: it uses
`SkyfieldAstronomyEngine.refresh_current_positions()` to update current
altitude, azimuth, direction and `observable_now` for the stored snapshot, emits only
`skyCompassChanged` and clears `COMPASS_LIVE` after the update.

The position calculation runs on a daemon worker. A Qt completion signal applies
the result on the controller thread only when request id and location key are
still current. Shared Skyfield access is serialized, so a live tick cannot
overlap a night-window, catalogue, Moon-geometry or full astronomy calculation.

Recent tests cover profile assignment, Barlow assignment, empty-profile
assignment and active-profile switching without restart.

## Cache Ownership

Weather cache:

- Owner: `OpenMeteoWeatherService` plus `WeatherCacheRepository`.
- Key: latitude, longitude, timezone and 48-hour forecast shape. The previous
  `24h` key is read only as a transitional stale-cache fallback.
- Lifetime: 45 minutes.
- Force refresh bypasses fresh cache.
- On network failure, stale cached data may be reused when available.

Sky-quality cache:

- Owner: `LightPollutionService` plus `SkyQualityRepository`.
- Key: rounded latitude, longitude and city.
- Local/non-VIIRS cache is reused unless its source matches a legacy marker.
- NASA Black Marble VIIRS entries have explicit `missing`, `fresh` and `stale`
  states based on `SkyQualityEstimate.updated_at`.
- VIIRS is revalidated after 7 days. A stale value is served immediately and
  remains the fallback if the background NASA lookup fails.
- Non-VIIRS local sky-quality estimates still have no general age-based TTL.

NASA AOD cache:

- Owner: `NasaAodProvider`.
- Key: rounded latitude/longitude, with result metadata preserving product and
  granule id.
- Lifetime: 18 hours.
- Only compact processed AOD results are cached. The provider keeps an in-memory
  copy for the current process and a small JSON cache so app restarts can reuse
  recent processed results.
- Downloaded VIIRS/MODIS granules are temporary and deleted after extraction.

The Weather page `Aggiorna` command forces the weather forecast request and
also schedules normal cache-aware VIIRS/AOD checks. It does not bypass a fresh
VIIRS entry or the AOD 18-hour TTL.

In-memory controller caches:

- base solar-system objects,
- base deep-sky objects,
- equipment-enriched object lists,
- weather hours,
- sky quality,
- seeing/transparency,
- advanced scores,
- night plan,
- Sky Compass,
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
- `HomePage.qml` is also large. Upper-Home and lower-Home decisions are moving
  into explicit presentation contracts, while visual formatting remains QML.
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
- Before changing AOD/OpenAQ or transparency scoring, use
  `docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md`,
  `docs/CALCULATION_LOGIC.md` and `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md` as
  the mathematical ownership, provider-quality and double-counting references.
- When changing calendar event copy or event-to-object linking, keep practical
  text in `EventDetailPage.qml` and target/setup enrichment in `AppController`.
