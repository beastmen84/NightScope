# Home Refresh Lifecycle Review

This review documents the current Home refresh model before introducing Sky
Compass. It is descriptive first, then proposes a future shared Observation
Snapshot architecture. No application code has been changed for this review.

## Current Architecture

Home is rendered by `HomePage.qml`, but Home data is owned by `AppController`.
The QML page has no data-refresh timer of its own. It binds directly to
controller properties and reacts to Qt notify signals:

- `dataChanged` for astronomy objects, Moon, events, best object, plan, sky map
  and notifications;
- `weatherChanged` for weather, observing quality, seeing, sky quality,
  advanced scores and blocking-session state;
- `locationChanged` for active location labels and location workflows;
- `statusChanged` for loading/service status;
- `equipmentChanged` for profile/equipment widgets.

There is a central controller refresh path, but it is not a single immutable
Home model. Instead, `AppController` maintains several mutable fields and emits
coarse signals after each refresh branch.

The main refresh entry point is `_refresh_all()`:

1. If startup location detection is still running, Home enters a pending
   no-location context.
2. If a valid location exists, `_refresh_astronomy()` runs first.
3. `_refresh_weather_and_conditions()` then computes weather, sky quality,
   seeing, equipment-aware objects, scores, plan, sky map and notifications.
4. If no valid location exists, `_refresh_no_location_context()` clears
   location-dependent objects and exposes placeholder summaries.

Additional refresh branches update subsets of the same state:

- `_finish_weather_refresh()` updates weather-derived state after manual or
  timed weather refreshes.
- `_finish_viirs_sky_quality_refresh()` updates sky quality and recomputes
  deep-sky context when remote VIIRS data arrives.
- `_refresh_active_profile_dependencies()` recomputes equipment-dependent
  recommendations after profile/equipment changes.
- `selectCity()`, `selectRecentLocation()`, `setManualLocation()`,
  `useWindowsLocation()` and `useApproximateOnlineLocation()` all apply a
  location and then call `_refresh_all()`.

## Timers, Triggers And Caches

### Timers

The only refresh timer found in the Home data path is
`AppController._weather_refresh_timer`, a single-shot `QTimer`.

- It is scheduled by `_schedule_next_weather_refresh()`.
- It fires at the next local hour boundary, with a minimum delay of 60 seconds.
- It calls `_refresh_weather_from_timer()`, which starts a cache-friendly
  weather refresh with `force_refresh=False`.

No `Timer` exists in `HomePage.qml`. The manual "Aggiorna" action is on
`WeatherPage.qml` and calls `refreshWeatherNow()`, which uses
`force_refresh=True`.

### Update Triggers

- Startup: controller construction calls `_initialize_startup_location()` and
  `_refresh_all()`.
- Location changes: apply the new location, invalidate catalogue visibility,
  call `_refresh_all()`, then emit `locationChanged`.
- Weather timer: refreshes weather asynchronously and recomputes weather,
  seeing, equipment recommendations, scores, plan, sky map and selected detail.
- Manual weather refresh: same as timer refresh, but bypasses fresh weather
  cache.
- VIIRS completion: updates sky quality, reloads/re-contextualizes deep-sky
  objects and recomputes observing outputs.
- Profile/equipment changes: reload profile equipment when needed, recompute
  equipment recommendations and observing outputs, then emit profile-dependent
  signals.
- Selected object changes: resolve the selected object from the current
  enriched object lists and refresh Object Detail.

### Caches

- Weather cache: `OpenMeteoWeatherService` with `WeatherCacheRepository`, keyed
  by latitude, longitude, timezone and 24-hour forecast shape. TTL is 45
  minutes. Manual refresh bypasses the fresh-cache check.
- Sky quality cache: `LightPollutionService` with `SkyQualityRepository`, keyed
  by rounded latitude, longitude and city. NASA VIIRS cache entries are treated
  as fresh when present; there is no broad age-based TTL.
- Controller memory state: base solar-system objects, base deep-sky objects,
  enriched objects, weather hours, Moon, events, sky quality,
  seeing/transparency, advanced scores, night plan, sky map, notifications and
  selected object.
- Catalogue visibility caches are separate from Home. They should not be used
  as a Home/Sky Compass cache.

## Home Section Dependency Matrix

| Home section | Current time | Location | Weather | Seeing | Recommendation engine | Astronomy calculations |
| --- | --- | --- | --- | --- | --- | --- |
| Header/location/status | No | Yes | Indirect status only | No | No | No |
| Service/loading banner | No | Indirect | Indirect | No | No | Indirect error state |
| Observing quality | Forecast window | Yes | Yes | No | Observing score service | Moon summary penalty |
| Moon card | Yes | Yes | No | No | No | Moon phase, rise/set, body detail |
| Planetary score | Via forecast/Moon | Yes | Yes | Yes | Advanced score service | Moon summary |
| Deep-sky score | Via forecast/Moon | Yes | Yes | Transparency | Advanced score service | Moon summary |
| Weather panel | Forecast hours | Yes | Yes | No | Weather digest helpers | No |
| Session warning/blocking | Forecast window | Yes | Yes | No | Night planner blocking rules | No |
| Night Planner preview | Object windows | Yes | Yes | Indirect through category scores/equipment | Planner service and best-object scoring | Planet/deep-sky object calculations |
| Other visible planets | Yes | Yes | No direct dependency | Equipment setup can use seeing | Equipment recommendation service | Solar-system altitude/rise/set/window |
| Other deep-sky objects | Yes | Yes | No direct dependency | Equipment setup can use seeing/transparency | Equipment recommendation and Moon-adjusted presentation | Messier altitude/window calculation |
| Sky map | Yes | Yes | No | No | No | Current altitude/direction from visible objects |
| Calendar/highlights | Current date | Yes | No | Profile setup may use seeing | Event setup enrichment only | Skyfield event generation |
| Notifications | Indirect | Yes | Yes | Through advanced scores | Notification service | Events/Moon/current targets |

Important distinction: the current Home sections are refreshed from shared
controller state, but individual QML helpers still derive presentation subsets
such as "other visible planets", "other visible deep sky", limiting-factor copy
and chronological event filtering. Home therefore has central orchestration, not
a central Home snapshot.

## Current Risks For Sky Compass

- Time freshness is tied mostly to weather-hour refreshes and full location
  refreshes. Current altitude, azimuth and cardinal direction can become stale
  between hourly weather refreshes.
- Recomputing all astronomy objects just to keep a compass current would be too
  heavy and would also move recommendation cards unexpectedly.
- Night-hour filtering exists in several places with slightly different ranges:
  observing score, seeing estimation and Home weather digest.
- `AppController` owns orchestration and a large amount of presentation logic,
  so adding Sky Compass directly as another set of controller fields would
  increase coupling.
- QML currently reads many independent properties; partial signal emissions can
  briefly render a mixed state during asynchronous weather or VIIRS updates.

## Proposed Observation Snapshot Architecture

Introduce a backend-owned `ObservationSnapshot` model as a coherent read model
for "what is true for the active observation context right now". It should be a
service/controller-level DTO, not a QML-only construct.

Recommended shape:

- `generated_at`: timezone-aware timestamp for the active location.
- `location`: active observer location and stable location key.
- `time_bucket`: rounded minute bucket used for lightweight time refresh.
- `weather`: forecast hours, summary, digest, status and refresh metadata.
- `sky_conditions`: sky quality, seeing/transparency and advanced scores.
- `astronomy`: Moon summary, solar-system object states, deep-sky object states,
  events and current alt/az fields.
- `recommendations`: best object, recommended cards, night plan,
  recommendation reasons and setup suggestions.
- `compass`: compact directional target list for Sky Compass with current
  altitude, azimuth, visibility state and stable object ids.
- `notifications`: Home notification DTOs.
- `validity`: per-domain timestamps or dirty flags such as `weather_at`,
  `astronomy_at`, `equipment_at`, `sky_quality_at`.

The snapshot builder should compose existing services rather than replace them:

1. `ObservationContextService` normalizes location, current time and active
   equipment profile.
2. `AstronomyStateService` computes or incrementally updates alt/az, Moon and
   object windows.
3. `ConditionStateService` owns weather, seeing, sky quality and advanced
   scores.
4. `RecommendationStateService` consumes astronomy plus conditions to produce
   recommendation cards and planner items.
5. `ObservationSnapshotService` assembles immutable dictionaries/dataclasses for
   QML.

`AppController` should eventually expose one `observationSnapshot` property and
thin compatibility properties can read from it while Home is migrated.

## Recommended Refresh Intervals

Use separate refresh lanes instead of one global timer:

- Fast astronomical tick: every 60 seconds for Sky Compass current alt/az,
  current direction, "above horizon now" and clock-sensitive labels. This
  should not recompute recommendation ranking by default.
- Recommendation refresh: every 10 to 15 minutes, plus immediate refresh on
  location, profile/equipment, sky-quality or weather-summary changes. This is
  enough for Home cards and avoids ranking churn.
- Weather refresh: keep the existing next-hour scheduling and 45-minute service
  cache TTL. Manual refresh should continue to force the weather cache.
- VIIRS refresh: keep event-driven asynchronous refresh after location or
  credential changes. It should update sky quality and mark recommendation
  state dirty.
- Calendar/events refresh: daily, on location change, and on app startup. Events
  are date-scale data and should not participate in the fast tick.
- Catalogue monthly visibility: keep independent from Home/Sky Compass and
  refresh only on catalogue filter/month/location changes.

For the first Sky Compass implementation, the fast tick can update only a small
compass target subset derived from the latest snapshot: Moon, visible planets,
best object, planned objects and a few high-score alternatives.

## Expected Performance Impact

Current full refreshes are acceptable for startup/location/weather changes but
too expensive for a frequent compass tick because they can call Skyfield for
planets, Messier samples, Moon, events, equipment scoring, planner ranking,
weather scoring and optional VIIRS handling.

With a snapshot architecture:

- A 60-second compass tick should compute alt/az only for a small target set.
  That keeps UI motion fresh without touching weather, planner or equipment
  recommendation logic.
- Existing heavy operations remain on slower/event-driven lanes.
- Weather network calls remain protected by the existing cache and timer.
- Recommendation churn is reduced because cards do not rerank every minute.
- Snapshot immutability makes it easier to avoid mixed QML states during async
  updates.

## Expected User Experience Impact

- Sky Compass can feel live because current directions and altitudes update
  frequently.
- Home recommendation cards remain stable enough to read and act on.
- Manual weather refresh still has visible impact when the user explicitly asks
  for it.
- Location changes continue to feel comprehensive because they rebuild the full
  observation context.
- The separation between "where is it now?" and "what should I observe?" stays
  clear: Sky Compass can be live and informational while recommendations remain
  slower, scored decisions.

## Implementation Guidance For Sky Compass

- Do not add a QML timer that directly calls many controller properties. The
  timer should be owned by the controller or a snapshot service so all consumers
  receive the same time bucket.
- Do not call recommendation services from the fast compass tick.
- Do not call weather or VIIRS services from the fast compass tick.
- Reuse existing Skyfield observer/body helpers for alt/az rather than
  duplicating coordinate math in QML.
- Keep planner and recommendation refreshes event-driven or slow-timer-driven.
- Add tests that assert the fast tick updates compass fields without calling
  weather, planner or recommendation scoring.
