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
  NASA/OpenAQ data providers, seeing/transparency, update notification and
  logging.
- `astro_viewer/app/astronomy`: astronomy engine protocol, mock fallback,
  Skyfield-based engine and coordinate parsing helpers.
- `astro_viewer/app/database`: SQLite bootstrap, migrations, repositories and
  import helpers.
- `astro_viewer/app/models`: dataclasses used as service and controller DTOs.
- `astro_viewer/data`: schema, catalog CSV files, seed data and Skyfield
  ephemeris files. Runtime data is not distributed as seed data.
- `astro_viewer/resources`: icons, images and themes consumed by QML and build
  packaging.
- `astro_viewer/translations`: Qt Linguist source (`.ts`) and compiled (`.qm`)
  catalogues for the Italian source UI and the English and Spanish
  translations.
- `astro_viewer/tests`: unittest/pytest-compatible regression tests.
- `astro_viewer/tools`: one-off import, validation and packaging-support tools.
- `packaging`: PyInstaller spec, hooks, platform build scripts and the
  deterministic Linux release-archive script.
- `tools/audit_qt_bundle.py`: cross-platform Qt, data, runtime-state and legal
  bundle gate.
- `tools/generate_linux_native_notices.py`: maps system binaries from the
  PyInstaller COLLECT manifest to installed Debian/Ubuntu packages or the
  python.org runtime, exact source versions and bundled copyright/license
  texts.
- `tools/update_translations.ps1`: deterministic QML extraction, catalogue
  completeness validation and `.qm` compilation.

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

## Runtime Data Ownership

`astro_viewer.app.runtime_paths` resolves an immutable `RuntimePaths` value
before constructing the translation manager, database, controller or logger.
It owns separate data, configuration, cache and state directories plus the
canonical paths for the SQLite database, preferences and file caches.

Windows retains the portable contract unchanged: a source checkout uses the
project root and a frozen build uses the directory containing the executable
for all four categories. macOS and unrecognized platforms retain that same
fallback until they receive dedicated packaging support.

Linux follows the XDG base-directory contract:

- data: `$XDG_DATA_HOME/NightScope`, defaulting to
  `~/.local/share/NightScope`;
- configuration: `$XDG_CONFIG_HOME/NightScope`, defaulting to
  `~/.config/NightScope`;
- cache: `$XDG_CACHE_HOME/NightScope`, defaulting to
  `~/.cache/NightScope`;
- state: `$XDG_STATE_HOME/NightScope`, defaulting to
  `~/.local/state/NightScope`.

Only absolute XDG overrides are accepted. The developer/test-only
`NIGHTSCOPE_RUNTIME_DIR` override takes priority and co-locates all four
categories, so standard smoke checks remain isolated and remove their complete
runtime after each subprocess.

On the first XDG run, the entry point copies an existing portable database,
database backup, preferences, location cache and NASA AOD cache into their new
owners. Existing XDG files are never replaced. `AppController` accepts explicit
configuration/cache paths but retains database-adjacent defaults for existing
constructors and tests.

If the rotating file logger cannot create its directory, the entry point falls
back to console logging and continues into the normal startup error boundary.
The portable Windows contract still requires a writable extracted application
directory. Linux installations require writable user XDG directories, not a
writable installation directory.

## System Credential Storage

`astro_viewer.app.services.credential_backend` is the common secure-storage
boundary used by both Earthdata and OpenAQ. On Windows it preserves the
existing `keyring` platform dispatch, which resolves to Windows Credential
Manager in the supported environment.

On Linux the boundary instantiates `keyring.backends.SecretService.Keyring`
directly and evaluates its runtime priority. Secure storage is available only
when the `SecretStorage` integration can reach or activate a compliant
freedesktop.org Secret Service through the desktop D-Bus session. A missing
dependency, missing daemon or failed D-Bus initialization returns no backend;
the existing credential state then disables save/test workflows with the
localized system-store-unavailable message.

Direct Secret Service selection is deliberate: Linux does not honor a
`PYTHON_KEYRING_BACKEND` or keyring configuration that redirects NightScope to
a plaintext, null, fail or unrelated third-party backend. Usernames and
non-secret verification markers remain in the XDG configuration JSON; Earthdata
passwords and OpenAQ API keys remain exclusively in the system credential
store. A native Linux package and an interactive Secret Service integration
test remain separate release gates.

## Platform Capability Boundary

`astro_viewer.app.platform_capabilities` is the single source of truth for the
host operating-system family and the platform features currently implemented
by NightScope. It converts `sys.platform` into an immutable
`PlatformCapabilities` value once during entry-point initialization. Both the
normal application and QML smoke-test paths expose the same capability map as
the `platformCapabilities` QML context property.

Source version `1.35.0` introduced detection only. Version `1.35.1` extends the
same boundary with system-location providers: Windows retains its existing
precise/coarse WinRT sequence, while Linux uses Qt Positioning's `geoclue2`
plugin with the stable desktop ID `io.github.beastmen84.NightScope`. The Linux
adapter requests one position through a thread-local Qt event loop, applies a
bounded timeout, maps Qt provider errors to the existing location failure
reasons, and then reuses the same offline city/timezone normalization as the
Windows provider.

The persisted startup preference is now
`use_system_location_on_startup`. Reads accept the legacy
`use_windows_location_on_startup` field and the next location-preference update
writes only the platform-neutral key. The old controller properties, slots,
and Windows service method remain compatibility aliases; visible QML uses only
the system-location contract. Runtime storage and credential behavior remain
unchanged in this step. Further platform adapters must extend this capability
boundary instead of adding independent `sys.platform` checks throughout
services or QML.

## UI Localization

`TranslationManager` is created before the controller and QML engine. It reads
the `language` key from `user_preferences.json`, installs the selected Qt
catalogue and is exposed to QML as `translationManager`. The sidebar selector
persists changes and calls `QQmlApplicationEngine.retranslate()`, so QML
bindings using `qsTr()` update without rebuilding controller state or
recomputing NSOM.

Italian is the source and fallback language; complete Italian, English, and
Spanish packs are currently bundled. Runtime packs are auto-discovered from
`<code>.json` metadata and use matching Qt `<code>.qm` catalogues, so the
sidebar and PyInstaller spec contain no hard-coded language list. Static QML
copy uses `qsTr()`. Python services retain lazy `tr()` messages and structured
`content_text()` references until the controller renders a QML property.
Dates, numbers, seeded descriptions, curiosities, catalogue names and equipment
notes therefore follow the selected locale without changing domain codes or
user-entered text.

The sidebar help button opens the packaged self-contained `manuale.html` through
the constant `AppController.manualUrl`. The current runtime language is passed
as `?lang=<code>`; the manual owns its Italian/English/Spanish selection without
adding another runtime translation surface. In source the file is resolved from
the project root; in PyInstaller it is resolved from the bundle data root.

Internal read models consume canonical, unrendered payloads. A language switch
emits presentation signals only and does not recompute astronomy, weather,
equipment, scoring or NSOM. The complete file contract and the code-free process
for adding another language are documented in [LOCALIZATION.md](LOCALIZATION.md).

## UI Appearance

`AppearanceManager` owns the presentation-only
`red_night_vision_enabled` preference and exposes it to QML independently from
`AppController`. Its default is normal mode. Updating it merges the value into
`user_preferences.json`, preserving language, location and other settings, and
emits only an appearance signal: astronomy, providers, NSOM and controller read
models are not recomputed.

Every QML component derives its colors from `AppTheme`. Normal values preserve
the existing interface, while Red Night Vision maps backgrounds, text, borders,
semantic accents, Canvas drawings and interaction states to a controlled
black/red palette. `NightVisionIcon` colorizes functional SVG icons through
`QtQuick.Effects`. Full-color object photographs and Home plan thumbnails use
an empty source and leave the layout while red mode is active; functional
diagrams remain visible and repaint when the mode changes.

Pages use themed controls such as `DarkTextField`, `DarkComboBox`,
`DarkSpinBox` and `DarkCheckBox` instead of relying on platform-native
indicators. This keeps modal and disabled states inside the same palette, not
only the controls visible in the initial page state.

The standard validation runner loads both normal and red QML scenes in isolated
runtimes. Bundle validation requires Qt Quick Effects in addition to the
existing Qt Quick modules. External windows and websites remain outside the
application appearance boundary.

## Startup Update Check

`UpdateManager` is a QML-facing service independent from `AppController`. The
normal application path constructs it from the bundled root `VERSION` and the
runtime `user_preferences.json`; QML smoke tests receive the same context
property but do not start a network request.

After a successful QML load, `main.py` schedules one check 750 ms later.
`UpdateManager` performs the request on a daemon thread with a four-second
timeout and emits only the result back to the Qt thread. Network, HTTP, JSON and
version errors are logged below warning level and do not change startup state
or produce user-facing errors.

The service consumes GitHub's public `releases/latest` endpoint, accepts only a
stable `major.minor.patch` version newer than the bundled version, and validates
that `html_url` is an HTTPS release path for
`beastmen84/NightScope`. It never downloads or installs an artifact. QML opens
the validated release page through the operating-system browser only after an
explicit user action.

The localized `DarkDialog` can be deferred on every startup or suppressed for
one specific release. Suppression stores `ignored_update_version` while
preserving the other shared JSON preferences; a later release remains eligible
for notification. The dialog uses the same normal and Red Night Vision theme
tokens as the rest of the application.

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

Current runtime status for `1.27.0`:

- Planner, Home `recommendedDeepSky`, Best Object, Sky Compass and upper-Home
  category summaries consume the canonical NSOM observation environment.
- There are no selectable NSOM feature flags, parallel shadow payloads or
  legacy ranking services. Detail pages consume their dedicated presentation
  read models and do not maintain a second internal NSOM payload.
- ObservationConditions applies the calibrated AOD/OpenAQ modifier by default
  only when provider-quality gates pass.
- Equipment remains setup-local; its current score is not replaced by an NSOM
  scalar, but ObserverCapability boundaries are explicit.
- Astronomy cameras and camera bodies are persistent profile inventory in
  schema 21. Schema 22 additionally stores a user-declared
  full-aperture-solar-filter capability on each profile-to-telescope
  assignment. These photographic inventory fields do not enter
  `EquipmentService`, ObserverCapability, Planner, Home, Sky Compass or NSOM.
  Catalogue edits and profile links notify `profileInventoryChanged`; they do
  not rebuild the visual active-profile setup or emit its downstream Home and
  observing-detail signals. A separate backend-only imaging train builder,
  target adapter and still/video scorer now consume typed data only when
  called directly; none is registered with `AppController` or QML.
- Filters and focal reducers are persistent profile inventory. Separate
  presentation services can feed the score-free observing-detail read model,
  but neither accessory enters `EquipmentService`, ObserverCapability, setup
  selection, scoring, Planner or NSOM. Reducer recommendations additionally
  require a target flag, the telescope already selected for that target and an
  exact normalized `ReducerTelescopeCompatibility` link.
- Planner now consumes the telescope selected by `EquipmentService` for each
  target in a multi-instrument profile and emits up to four selected
  opportunities before chronological presentation.
- Home and Sky Compass share the complete useful-night target pool. Sky Compass
  filters live `observable_now` geometry and no longer lets plan/Best Object
  bonuses choose the direction.
- Lower Home can apply the complete `skyCompass.targets` ID set as a local QML
  presentation filter over plan and alternatives. This does not rebuild the
  Home overview, change list ordering or add another ranking path.
- Runtime target identity is the normalized non-empty object ID. Home, Best
  Object, Planner and Sky Compass keep the first occurrence before scoring;
  lower-Home plan/alternative counts use the same invariant.
- Catalogue identity is physical-object based: `CatalogueObject.object_id` is
  stable and `CatalogueDesignation` owns one or more catalogue codes,
  including multiple historical aliases from the same catalogue. A secondary
  designation never creates another runtime target.
- Catalogue recommendation eligibility is a candidate-admission policy, not a
  score. `CatalogueObject.recommendation_enabled_by_default` owns the seeded
  first-run value, while `CatalogueRecommendationPreference` owns persistent
  user overrides. Synthetic Solar System S1-S9 entries are always enabled and
  expose a locked control. `CatalogueRepository.list_recommendation_objects`
  resolves the effective value in SQL before Skyfield parses coordinates or
  calculates visibility. The controller repeats the admission check when
  reusing a cached snapshot so disabling is immediate. Disabled targets
  therefore cannot reach Equipment, Home, Best Object, Planner or Sky Compass,
  while the complete catalogue and its descriptive detail remain available.
- The packaged deep-sky catalogue contains 7,585 physical targets: the 110
  Messier and 109 Caldwell targets plus 7,366 NGC-only targets. OpenNGC adds
  7,839 usable NGC designations representing 7,571 physical targets; 205 map
  to existing Messier/Caldwell identities and duplicate or compound codes
  share an `object_id`. NGC-only targets start disabled, while an overlapping
  curated target retains its Messier/Caldwell default.
- Every current catalogue type maps to an existing NSOM class. Planetary
  nebulae are classified before the generic planet token; supernova remnants
  map explicitly to `DIFFUSE_NEBULA` across environment and legacy condition
  boundaries. Point-like or unclassified OpenNGC types use the conservative
  existing point-source class; explicit galaxy types take precedence over a
  common name containing words such as “Nebula”. Equipment continues to
  consume each target's explicit observing metadata, without introducing
  catalogue-specific equipment categories.
- `ObjectDescription`, `ObjectCuriosity` and `ObjectImages` retain the complete
  curated presentation for 228 targets: 219 Messier/Caldwell objects and nine
  Solar System bodies. Each has a dedicated local `512 x 512` JPEG, with
  survey cutouts for deep sky and normalized NASA/JPL PIA observations for
  Solar System bodies. NGC-only objects deliberately use a type-specific
  fallback image and the localized `Work in progress` description/curiosity
  until they are enriched individually. Source URL, attribution and usage
  metadata do not enter ranking.
- `ObjectCuriosity` remains a separate presentation table and has no NSOM,
  Equipment or observability role. Seeded descriptions and curiosities are
  managed through `is_builtin`; bootstrap refreshes them, while content
  imported by the user is marked custom and preserved.
- The 228 curated Solar System and deep-sky descriptions keep identity, season
  and difficulty metadata separate from `short_description` and
  `observing_notes`. NGC-only placeholder text remains in the physical
  catalogue seed and is excluded from the structured-content translation
  generator. The seeds remain UTF-8 without BOM because bootstrap reads
  canonical CSV headers with the standard `utf-8` codec.
- If Sky Compass ranking raises unexpectedly, the controller logs the failure
  and uses a geometry-only payload. Missing sky-quality input is neutral inside
  the canonical environment and does not switch ranking implementation.
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
  projects Session state, a count-based multi-equipment summary, up to four
  compact plan rows and score-free alternative rows without changing Planner
  ranking.
  Repeated equipment rows are counted once per normalized `(kind, id)` pair.
- Lower-Home alternatives are presented by observing-window start; shared best
  times and target category are tie-breaks, followed by a natural numeric name
  key suitable for Messier, Caldwell and future catalogue identifiers.
- `ObservingObjectDetailService` owns the score-free read model used by the
  observing detail opened from Home or Calendar. It combines live target
  geometry, Session metadata, target-specific Equipment selection and the
  sanitized filter recommendation projection while keeping the raw Catalogue
  branch on the existing `selectedObject` contract.
  Its Session badge is qualified locally (`Sessione ...`), so the compact Home
  payload and layout remain unchanged.
  `ObjectDetailPage.qml` switches between those contracts by source; the Moon
  cycle remains an observing-only extension. Observation persistence stays in
  the backend for a future dedicated log surface and is no longer embedded in
  object detail. Database bootstrap also corrects the exact legacy Moon
  `best_seen` typo without overwriting other seeded or user-held values.
- Catalogue list filtering keeps canonical English type/observation values but
  exposes separate Italian presentation labels. Monthly filtering still uses
  the selected list month; Catalogue detail instead calculates only the opened
  object's visibility for the current local year/month and caches it by object
  and location. The detail result is independent from list filter state and
  uses unknown rather than `No` when location or calculation is unavailable.
- `CalendarOverviewService` v4 projects annual and short-horizon events into a
  score-free read model. Event instant, observing window, local visibility,
  participants, angular separation, source and interval facts are separate
  fields; future setups use
  profile capability without reusing tonight's seeing. Highlight selection
  combines intrinsic event priority with a bounded local-visibility penalty.
  Event and participant IDs are normalized before presentation counts so an
  identified event cannot appear twice; id-less events remain untouched.
  Calendar QML and the Home event strip consume this read model; the Home
  projection excludes solar conjunctions while the complete Calendar keeps
  them. The legacy `events` property remains available only for compatibility
  and no event is removed by a usefulness cap.
- `TransientCalendarEventSource` is the extension boundary for location-aware
  operational events that do not belong to `CatalogueObject`. Production
  injects `IssPassEventSource` and `CometWindowEventSource`; tests opt in
  explicitly so they never perform unplanned network calls. Each source has a
  preparation phase for provider/cache access and a calculation phase that
  consumes prepared data.
  The annual Skyfield snapshot never calls a transient provider, so a slow or
  failed source cannot delay or remove the annual event set.
- ISS prediction uses public CelesTrak OMM elements, Skyfield/SGP4 propagation,
  a 10-day moving horizon, a 10-degree minimum altitude, satellite sunlight and
  local solar altitude at or below -6 degrees. `OrbitalElementCacheRepository`
  refreshes after 6 hours and permits a recent cached element set for at most 3
  days if refresh fails. The controller rebuilds the moving pass set hourly;
  fresh cache reuse prevents that cadence from becoming an hourly network
  request. ISS IDs use the continuous orbital revolution rather than predicted
  peak seconds. This path has no Catalogue, score, Equipment, Planner, Home
  ranking or NSOM dependency.
- Comet prediction queries the public NASA/JPL SBDB Query API for active
  periodic and non-periodic comet elements with total-magnitude parameters.
  `OrbitalElementCacheRepository` refreshes the global candidate set after 24
  hours and permits a fallback for at most 7 days. Skyfield's MPC orbit helper
  uses pandas to propagate each candidate across a 90-day moving horizon; the
  total-magnitude estimate follows the supplied `M1`/`K1` parameters and is
  presented as an approximate range rather than a precise measurement.
  Detailed 30-minute samples require magnitude at most 14.5, altitude at least
  20 degrees, local solar altitude at or below -12 degrees, solar elongation at
  least 30 degrees and acceptable Moon geometry. Each useful segment lasts at
  least 60 minutes. Consecutive observing nights are aggregated and only the
  best continuous group becomes one stable event per comet, capped to the 12
  brightest candidates. This path is independent from Catalogue, weather,
  profile equipment, score, Planner, Home ranking and NSOM.
  Calendar rows reserve at most two lines for the compact date label, so a
  comet start/end range remains visible without allowing the tile to grow
  without bound.
- Planetary conjunction candidates are observational close approaches found by
  `Skyfield.searchlib.find_minima()` across all 21 pairs of the seven planets.
  The annual contract retains minima up to 6 degrees, then samples adjacent
  local nights to require both planets above the 8-degree useful threshold.
  Windows shorter than 20 minutes are retained with `check` confidence instead
  of being cut. Solar conjunctions remain a separate, non-observing category
  with no optical setup recommendation.
- Lunar-eclipse visibility describes the computed maximum only. A maximum in
  daylight or below the local horizon has no observing window; the UI asks the
  observer to verify individual phase contacts instead of implying that the
  whole eclipse is either visible or invisible.
- The checked-in source of truth is the runtime code, active regression tests,
  `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md` and this architecture/model
  documentation. `docs/NSOM_MIGRATION_ARTIFACT_CLEANUP_AUDIT.md` records the
  final removal of migration-only runtime surfaces.
- The first visible follow-up is limited to Weather page condition-data
  semantics: AOD is labelled as aerosol data, OpenAQ as local particulate data,
  freshness is visible, and no NSOM ranking explanation panel is exposed.
- VIIRS cache hardening is active: cached Black Marble values are revalidated
  every 7 days while stale data remains available if NASA cannot be reached.
- AOD, OpenAQ and VIIRS worker completions carry both a request generation and
  a location key. Results started for old credentials or an old location are
  discarded without changing the running state of a newer request; old
  provider presentation data is cleared as soon as the active location changes.
- AOD and VIIRS provider-cache lookups reuse a valid observation within 500
  metres to absorb normal Windows geolocation jitter. Exact location keys remain
  unchanged for asynchronous refresh identity and stale-result rejection. AOD
  performs this cache-only preflight before a background worker is started.
- Open-Meteo retains cached forecasts on provider failure and classifies
  retryable transport/server failures separately from permanent client/rate
  errors. Error, HTTP and retry state is thread-local so overlapping stale and
  current workers cannot mix their result metadata. Retryable failures schedule
  a forced lookup after five minutes; status-code logging excludes request
  coordinates and parameters.
- OpenAQ v3 location distances are meters and are converted unconditionally to
  kilometres at the service boundary. HTTP, transport and invalid-payload
  failures from per-location `latest` requests remain retryable and are not
  cached as genuine no-data results.
- Earthdata connection tests and VIIRS requests share one serialized temporary
  `NETRC` context because `NETRC` is a process-wide environment variable.
  VIIRS distinguishes missing monthly granules from authentication, rate-limit,
  network and HTTP failures and stops the month scan on provider-wide failures.
- The upper Home overview has a dedicated read-only presentation boundary,
  `homeObservingOverview`. It separates Session state, weather index, NSOM
  category diagnostics and Moon impact. The upper QML cards consume this
  boundary: only the weather card exposes a numeric condition score, while
  planetary/deep-sky cards expose descriptive category diagnostics. Sky Compass
  consumes the same Session state only for copy/actionability: its direction,
  target selection and NSOM ranking remain unchanged.
- Upper-Home sky quality and lower-Home observing guidance share the same
  Bortle presentation mapping; class 7 is the suburban-to-urban transition.
- Missing sky quality is a first-class `None` state. Home marks local
  visibility as unverified and Weather shows `n/d`; NSOM, Equipment and seeing
  receive no synthetic Bortle input and continue with their remaining inputs.
- If those remaining inputs still produce a deep-sky category diagnostic, the
  Home read model marks it `partial` and presents an amber `Parziale` badge;
  this presentation state does not modify the underlying NSOM score.
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
  unified filterable table for non-plan visible targets. With no telescope or
  binocular in the active profile, the presentation service keeps only rows
  whose existing Equipment read model does not require an optical instrument.
- `ObjectCataloguePage.qml`: informational catalogue browser with search,
  filters and object-detail click-through. It renders catalogue data and does
  not present recommendation ranking.
- `ObjectDetailPage.qml`: selected object detail and setup alternatives.
- `EquipmentProfilesPage.qml`, `EquipmentTelescopesPage.qml`,
  `EquipmentOpticsPage.qml`, `EquipmentBinocularsPage.qml` and
  `EquipmentFiltersReducersPage.qml`: profile and visual-equipment management.
  Seeded rows expose edit but not delete actions; repository protection
  enforces the delete boundary outside QML, while persisted user overrides
  prevent later seed refreshes from replacing corrected values.
  Each assigned telescope also exposes its schema-22 full-aperture solar-filter
  flag. The control updates `profileInventoryChanged` only and carries explicit
  front-of-objective and no-eyepiece-filter safety copy.
- `EquipmentCamerasPage.qml`: two-column catalogue for astronomy cameras and
  interchangeable-lens camera bodies. The rows can be assigned from
  `EquipmentProfilesPage.qml`, while remaining outside the visual
  recommendation consumer.
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
- astronomy-camera and camera-body catalogue snapshots,
- filter/reducer catalogue and assignment snapshots,
- sky quality, seeing/transparency and NSOM category scores,
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

- `ObservingScoreService`: forecast/Moon observing-weather summary and labels.
- `NsomCategoryScoreService`: upper-Home planetary and deep-sky category
  summaries from the canonical observation environment.
- `SeeingTransparencyService`: seeing/transparency estimation from forecast
  fields and sky quality.
- `NightPlannerService`: observing plan capped at four unique targets, weather
  blocking and chronological plan presentation. It delegates default ranking to
  `PlannerNsomScoringService` and accepts selected telescopes by target.
- `PlannerNsomScoringService`: practical target value, binary session viability,
  timing factors and final `ObservationOpportunity` ranking.
- `NsomObservationEnvironmentService`: the single target-specific composition
  of geometry, Moon background, VIIRS/Bortle background,
  seeing/transparency and provider-gated AOD/OpenAQ conditions.
- `EquipmentService`: magnification, true field, exit pupil, profile
  capabilities and setup recommendation.
- `ImagingTrainBuilder`: target-neutral telescope/camera enumeration at prime
  focus, with one exact imaging reducer or one Barlow, plus focal ratio, field,
  sampling and known backfocus geometry.
- `ImagingRecommendationService`: additive static still/video suitability over
  photographic target traits and imaging trains. Its data-completeness
  metadata has zero score effect; the service has no runtime, visual-engine or
  QML registration. Solar configurations require an explicit exact set of
  telescope IDs from the caller.
- `ImagingExposureAdvisor`: score-neutral broadband planning ranges for one
  still candidate. It consumes only a typed `ImagingSessionConditions`
  snapshot, emits inspectable multipliers, sub-exposure/total-integration
  intervals and confidence metadata, and remains outside runtime and QML.
- `ImagingVideoCaptureAdvisor`: score-neutral single-clip guidance for a
  solar, lunar or planetary video candidate. It keeps achievable FPS distinct
  from catalogue maxima and target goals, emits duration/FPS/frame ranges and
  explicit missing-data metadata, and remains outside runtime and QML.
- `FilterRecommendationService`: presentation-only matching between target
  filter preferences, the aperture of the target-specific telescope, the
  complete filter catalogue and products assigned to the active profile. It
  returns at most one aperture-compatible primary recommendation and one
  optional color recommendation and never changes setup or NSOM values.
- `ReducerRecommendationService`: presentation-only matching between a target
  photographic-reducer flag, the target-specific telescope selected by
  `EquipmentService` and exact normalized reducer compatibility. It prefers
  compatible reducers in the active profile, otherwise reports compatible
  catalogue products as unavailable, and never recalculates optical values or
  changes setup and NSOM values.
- `LightPollutionService`: sky-quality lookup from NASA VIIRS cache, optional
  real preprocessed local datasets and asynchronous NASA refresh. It returns
  unavailable when none of those sources covers the active location.
- `NasaAodProvider`: NASA MAIAC aerosol lookup using VIIRS primary and MODIS
  fallback. `AppController` starts it in the background when a valid location
  exists and Earthdata credentials have a successful connection test. It returns
  compact processed AOD results for the Weather page `Aerosol atmosferico`
  section and for gated `ObservationConditionsService` condition inputs. It
  decodes the packed MAIAC QA field and accepts only clear, non-adjacent,
  best-quality AOD samples. Exact-pixel extraction falls back to quality-filtered
  5x5 and 11x11 neighborhoods with at least three samples, preserving radius and
  nearest-valid-pixel distance. It remains disconnected from forecast
  transparency, seeing and provider refresh decisions.
- `ObservationConditionsService`: shared equivalence layer for observing
  condition adjustments. It owns Home/Detail Moon-adjusted scores, the existing
  deep-sky light-pollution context formerly implemented inside `AppController`,
  batch conditioning for visible Home/detail display payloads and structured
  condition inputs for NSOM consumers. It accepts provider-gated NASA AOD and
  particulate inputs with freshness notes. The calibrated aerosol factor and
  target-specific Moon geometry are canonical and have no runtime feature
  flags.
  Runtime diagnostic freshness is explicit: NASA AOD older than seven days is
  omitted from condition inputs; fresh/recent NASA AOD is included when
  provider-quality gates accept it. OpenAQ data is included as fallback/context
  when the `LocalAtmosphere` result has usable data, including
  stale-but-present readings, and omitted when historical, failed, unavailable
  or unconfigured. AOD is primary when quality-eligible; local OpenAQ PM is a
  non-additive fallback/context source. Target-class caps are expressed as
  atmospheric-transparency loss before deriving diagnostic penalty points.
  These inputs are not exposed as NSOM fields in QML. WeatherPage may display
  provider values and freshness; ranking uses them only through the canonical
  environment and provider-quality policy.
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
- `LocationService`: Windows, GeoClue, IP, manual and MPC-observatory location
  providers. Geographic
  timezone resolution is separate from city metadata: `CoordinateTimezoneService`
  lazily reuses the offline `timezonefinder` polygon index to map exact WGS84
  coordinates to an IANA timezone. Manual coordinates, manual city or MPC
    observatory selection, and system-location modes use that result; a valid
    timezone supplied by the IP provider remains authoritative. The computer timezone is only a defensive
  fallback when the polygon lookup is unavailable, and its PowerShell probe is
  evaluated lazily. Precise Windows positions may use a GeoNames city within
  50 km to enrich city, country and region, but that lookup neither changes the
  coordinates nor chooses the timezone.
  Normalization belongs to acquisition only. Persisted and recent locations
  produced by the current build are trusted as stored and are not migrated or
  recomputed by the controller.

### Repositories

Repositories own SQLite persistence:

- `CityRepository`: offline city search and presentation-only reverse lookup;
  its GeoNames timezone field is not an operational timezone source.
- `LocationRepository`: unified read-only search over GeoNames cities and the
  separate `MpcObservatory` table. Exact MPC codes rank first; names and
  accent-insensitive aliases share the same result contract without treating an
  observatory as a city.
- `CatalogueRepository`: physical catalogue targets, their designations and
  persistent per-object recommendation-eligibility overrides. Batch preference
  changes validate every requested identity before one SQLite transaction.
- `EquipmentCatalogRepository`: telescope, eyepiece, Barlow, binocular, filter,
  focal-reducer, astronomy-camera and camera-body CRUD. Visual equipment keeps
  its profile assignments; schema 21 stores camera assignments and schema 22
  stores the full-aperture-solar-filter declaration for each
  profile-to-telescope link as inventory for the separate backend imaging
  engine, without invoking that engine at runtime.
  Every catalogue row exposes `is_builtin`, `seed_key` and `is_user_modified`;
  seeded rows can be updated but not deleted, while user rows can be managed
  after any applicable profile links are handled. Updating a seeded row marks
  it as user-modified so bootstrap keeps the override. Each equipment CSV owns
  an explicit immutable `seed_key`, independent from mutable brand, model and
  technical fields. Bootstrap and reducer-telescope compatibility resolve rows
  by that identifier, so a seed correction updates the original row and its
  links instead of creating a duplicate. If the corrected natural identity is
  already owned by a custom row, the custom row is preserved and that
  conflicting seed update is skipped. For direct upgrades from schemas without
  these identifiers, bootstrap uses the historical built-in identity once to
  attach the matching explicit key; normal reseeding never derives ownership
  from mutable display fields. Telescope mount input is a controlled code
  taxonomy; its visual tracking projection preserves legacy coefficients while
  retaining finer capability distinctions for future imaging logic.
  Connections enable SQLite foreign keys, usage counts operate on distinct
  valid profiles and reducer rows expose normalized exact telescope
  compatibility where available.
- `WeatherCacheRepository`: weather response cache.
- `OrbitalElementCacheRepository`: provider-neutral OMM/TLE cache for
  short-horizon orbital event sources.
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
4. Weather, sky quality, seeing, NSOM category summaries, equipment recommendations and
   planning are layered on top.
5. QML receives property change signals and renders dictionaries exposed by the
   controller.

Home recommendation flow:

1. `CatalogueRepository` returns only physical deep-sky targets whose seeded
   default or persistent user override admits them to recommendations.
2. The astronomy engine parses and prefilters only those rows, then uses
   NumPy-backed Skyfield batches for fixed-target nightly geometry. It retains
   scalar fallbacks without multiprocessing or platform-specific process
   sharing.
3. `AppController` applies the same admission map defensively to cached data
   and then adds active-profile equipment recommendations. Disabling is
   immediate; enabling starts a deep-sky-only background astronomy refresh.
4. Deep-sky objects may be adjusted by light-pollution context and Home/Detail
   Moon context through `ObservationConditionsService`.
5. `BestObjectNsomSelectionService` always selects Best Object from canonical
   observation opportunities. Missing provider inputs are neutral factors.
6. `NightPlannerService` produces the observing plan unless weather is
   blocking, using `PlannerNsomScoringService`. Up to four
   highest `ObservationOpportunity` values are selected before chronological
   ordering, using the setup telescope selected for each target.
7. `AppController` exposes the centralized blocking state to QML.
8. QML presents the plan, a global "Sessione da monitorare" warning with a
   potential observing window, or a full "Sessione sconsigliata" warning when
   no useful window is expected.

Catalogue browsing flow:

1. `AppController` loads one row per physical target from repository-backed
   local data. The unfiltered view therefore shows 7,585 deep-sky rows plus
   nine Solar System rows.
2. `CatalogueRepository` attaches every designation to that target. The
   presentation keeps compatibility fields `catalogue` and `catalogue_id`, plus
   `catalogues` and `designations`; selecting a catalogue projects its code
   without changing `object_id`. The NGC filter expands same-target aliases and
   therefore exposes all 7,839 usable NGC designations.
3. `ObjectCataloguePage.qml` applies controller-backed search and filters for
    catalogue, object type, constellation and observation type through a
    virtualized `ListView` backed by `CatalogueObjectListModel`, a
    `QAbstractListModel` with one map role. Filter changes reset the projected
    model, while a `Home` change emits `dataChanged` only for rows sharing the
    physical `object_id`; aliases therefore stay synchronized without
    rebuilding or serializing the other catalogue rows. Its compact `Home`
    checkbox changes the persistent recommendation preference without removing
    the row for Messier, Caldwell or NGC targets. Solar System S1-S9 rows show
    the same checkbox checked and locked.
    `Attiva risultati` and `Disattiva risultati` operate on the complete
    filtered model, not only instantiated delegates. The confirmation reports
    the exact number of editable physical targets; multiple catalogue aliases
    count once and locked Solar System rows are excluded.
    Exact search matches are ordered before prefix and substring matches, so a
    growing catalogue does not hide a direct body/name match among aliases;
    compact codes such as `NGC1` are normalized without making `C23` match
    `NGC 23`.
4. Preference persistence and the row update complete synchronously. A bulk
   action case-insensitively deduplicates physical IDs, validates the complete
   set, writes it with one `executemany` transaction, updates canonical and
   projected model state in one pass, and queues one recommendation refresh.
   Large `dataChanged` sets are coalesced into one range without resetting the
   list or its scroll position. With a valid location, a 200 ms single-shot
   timer coalesces successive changes into the newest generation. At most one
   recommendation worker runs; a change made during that run requests one
   replacement calculation rather than queuing every intermediate state.
   Request generation, location key and a signature of equipment/condition
   inputs prevent stale results from being published. QML exposes the pending
   or running state without waiting on the calculation.
5. The worker calculates fixed-target geometry and Moon geometry, then prepares
   Equipment projections, pollution context, conditioned read models, NSOM
   ranking, Best Object, Planner and Sky Compass from captured immutable
   inputs. The Qt thread only swaps the prepared collections and emits their
   presentation signals. Disabling a target removes it immediately from the
   current recommendation collections and temporarily clears Sky Compass until
   the prepared snapshot arrives. This uses the existing Python thread and Qt
   queued-signal boundary on Windows and Linux; no process-specific or
   fork-dependent behavior is required.
6. `selectCatalogueDesignation` preserves the exact opened alias and creates a
    detail-compatible object without invoking weather, equipment suggestions,
    best-object scoring, planner ranking or `recommended_deep_sky()`.
7. Object Detail is reused for click-through, with back navigation returning
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
3. `AppController._event_to_qml` enriches events with active-profile setup text,
   `targetObjectIds` and display names when the event maps to known objects.
4. A planetary conjunction maps to both planets and exposes one detail button
   for each. Oppositions and solar conjunctions map to their single planet;
   Moon phases and lunar eclipses map to `moon`, allowing the existing object
   detail navigation to be reused.
5. Transient events can instead expose explicit start/end/peak timestamps,
   source freshness and fact rows without mapping to any catalogue target. ISS
   passes and comet windows use this path and therefore show generic observing
   guidance rather than active-profile equipment recommendations.
6. The Calendar projection removes completed intervals and instant events from
   earlier dates before event-ID deduplication. Ongoing intervals remain at
   `daysUntil = 0`; provider-backed details format the exact update timestamp in
   the active locale.

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
neutral. Operational refresh dispatch uses domain-specific reasons. Accepted
OpenAQ/AOD completions recompute condition-dependent NSOM consumers only when
their DTO changed; they do not repeat astronomy, Equipment selection or seeing
estimation. Condition scoring consumes already available provider DTOs rather
than triggering provider refreshes itself.

`LIVE_TICK` is the Sky Compass live refresh lane. It maps only to
`COMPASS_LIVE`, which is separate from the broader `COMPASS` domain used by
normal Home/Planner/weather-driven recomputation. The live lane updates only
current positional fields for already prepared Sky Compass targets and must not
call weather, OpenAQ, NASA AOD, VIIRS, Planner, equipment or Recommendation
Engine refresh paths.

Short-horizon calendar events use a separate controller timer rather than a
`RefreshManager` scoring domain. The worker prepares provider/cache data before
acquiring the shared astronomy lock, performs only the Skyfield calculation
inside that lock, rejects results whose location key is no longer current and
then replaces the transient subset while preserving the annual subset. A full
astronomy refresh for the same location retains the last valid transient rows
until their replacement is ready.
The timer wakes at the shortest configured source interval, currently one hour
for ISS. The astronomy engine caches results independently per source and
rebuilds only sources whose own interval has elapsed, currently six hours for
comets. A location change invalidates reuse and forces every source to rebuild.

The following changes are expected to trigger dependent recomputation:

- active profile switch,
- profile equipment assignment/removal,
- profile equipment deletion,
- catalog equipment addition when assigned to the active profile,
- location change,
- valid weather refresh,
- sky-quality refresh,
- VIIRS refresh completion,
- accepted AOD/OpenAQ refresh completion when provider data changed,
- astronomy catalog reload caused by location or sky-quality context,
- selected object change.

Important methods:

- `_refresh_weather_and_conditions`
- `_finish_weather_refresh`
- `_complete_weather_refresh`
- `_finish_local_atmosphere_refresh`
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
- Sky Compass,
- NSOM category scores,
- recommended setups,
- selected-object setup/detail data.

NASA AOD and OpenAQ completion update their Weather-page DTO and, when the
accepted value changed, recompute Home ranking, Best Object, Planner, category
scores and Sky Compass from the existing astronomy/seeing state. The provider
completion does not repeat ephemerides, Moon geometry, weather score or seeing.

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

The optional Home filter remains active while the live payload has targets and
replaces its membership only when the normalized ID set changes. An unavailable
or `no_targets` payload clears the toggle. This behavior is UI-local and does
not trigger Planner, Equipment, weather or NSOM recomputation.

The position calculation runs on a daemon worker. A Qt completion signal applies
the result on the controller thread only when request id and location key are
still current. Shared Skyfield access is serialized, so a live tick cannot
overlap a night-window, catalogue, Moon-geometry or full astronomy calculation.

Recent tests cover profile assignment, Barlow assignment, empty-profile
assignment and active-profile switching without restart. They also verify
filter/reducer CRUD, schema-v16 migration, stable equipment seed ownership,
immutable CSV identifiers, in-place seed identity correction, collision-safe
preservation of built-in user overrides, legacy key attachment without
duplication, filter duplicate remapping,
profile-aware filter and reducer detail recommendations, managed-content
provenance, exact built-in and custom reducer compatibility, orphan cleanup,
forced unlinking and assignment without NSOM or capability refresh. The schema
16 migration also renames the historical seeded profile to `Default` without
confusing that profile name with the derived naked-eye observing mode.

## Cache Ownership

Approximate IP-location cache:

- Owner: `IpGeolocationProvider`; persisted in `location_cache.json`.
- Lifetime: 24 hours. Missing, invalid, future-dated or older entries are not
  accepted as the result of a new online-location request.
- A valid fallback is labelled as a previously loaded location rather than a
  fresh internet detection. Manually selected and Windows-provider cache rows
  are never consumed as IP-provider cache entries.

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
- NASA Black Marble VIIRS entries have explicit `missing`, `fresh` and `stale`
  states based on `SkyQualityEstimate.updated_at`.
- VIIRS is revalidated after 7 days. A stale value is served immediately and
  remains the fallback if the background NASA lookup fails.
- The controller classifies the cache before checking Earthdata credentials.
  With an unverified account, a stale real value remains available and Weather
  shows that it must be updated; freshness does not overwrite provider
  confidence.
- Non-VIIRS rows from retired baseline/offline providers are removed at service
  startup. Real optional local datasets are read directly and not cached in
  `SkyQualityEstimate`.

NASA AOD cache:

- Owner: `NasaAodProvider`.
- Key: rounded latitude/longitude, with result metadata preserving product and
  granule id.
- Lifetime: 18 hours for positive measurements; 6 hours for genuine
  `no_granules` or `no_valid_pixel` results.
- Only compact processed AOD results and structured genuine no-data summaries
  are cached. Authentication, search, download and parsing failures remain
  retryable and are never written to cache. The provider keeps an in-memory copy
  for the current process and a small JSON cache so app restarts can reuse
  recent results.
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
- NSOM category scores,
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
- Observing score, seeing estimation and Home weather digest consume the same
  centralized night-hour selection; their downstream summaries remain
  intentionally different.
- Moon parsing from string percentages is repeated in multiple services.
- Light-pollution handling has two explicit outputs: display compatibility in
  `ObservationConditionsService` and physical sky background in
  `NsomObservationEnvironmentService`. The display projection preserves
  astronomical visibility and candidate cardinality; raw target inputs prevent
  double application in ranking.
- Moon illumination and target geometry are composed once by
  `NsomObservationEnvironmentService`; Planner adds only observer, timing and
  session layers.
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
