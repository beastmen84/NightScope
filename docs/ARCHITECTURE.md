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
  seeing/transparency, notifications and logging.
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

## Dependency Flow

The intended dependency flow is:

`QML -> AppController -> services/repositories -> models/data`

The services do not depend on QML. Repositories do not depend on services. The
controller composes repositories and services and converts dataclasses into
QML-friendly dictionaries.

The astronomy layer depends on Skyfield/Astropy when available and provides a
mock fallback through `MockAstronomyEngine`. Weather and VIIRS network clients
are isolated behind service classes.

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
- `NightPlannerService`: ordered observing plan, weather blocking, Moon and
  light-pollution penalties.
- `EquipmentService`: magnification, true field, exit pupil, profile
  capabilities and setup recommendation.
- `LightPollutionService`: sky-quality lookup from cache, local CSV providers,
  NASA VIIRS and offline fallback.
- `OpenMeteoWeatherService`: forecast retrieval and weather cache integration.
- `SkyMapService`: compact sky-map DTO generation.
- `SkyCompassService`: broad direction ranking from already prepared Home
  targets; it does not call weather, VIIRS, Planner or recommendation services.
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
3. Deep-sky objects may be adjusted by light-pollution and Moon context.
4. `ObservingScoreService` selects the best object.
5. `NightPlannerService` produces the observing plan unless weather is blocking.
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
- Light-pollution/Moon penalties for deep-sky ranking appear in both
  `NightPlannerService` and `AppController` presentation filtering.
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
- When changing Moon or light-pollution logic, verify galaxy, nebula, globular
  cluster and open-cluster ranking separately.
- When changing calendar event copy or event-to-object linking, keep practical
  text in `EventDetailPage.qml` and target/setup enrichment in `AppController`.
