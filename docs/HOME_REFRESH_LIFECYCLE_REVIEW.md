# Home Refresh Lifecycle Review

This review documents the current Home refresh model and the Sky Compass
prototype. It is descriptive first, then proposes a future shared Observation
Snapshot architecture. Sky Compass v2 intentionally stays inside the existing
Home refresh lifecycle instead of introducing the future snapshot model.

## Current Architecture

Home is rendered by `HomePage.qml`, but Home data is owned by `AppController`.
The QML page has no data-refresh timer of its own. It binds directly to
controller properties and reacts to Qt notify signals:

- `dataChanged` for astronomy objects, Moon, events, best object and plan;
- `skyCompassChanged` for the Sky Compass DTO, including its 60-second live
  positional refresh;
- `weatherChanged` for weather, observing quality, seeing, sky quality,
  advanced scores and blocking-session state;
- `locationChanged` for active location labels and location workflows;
- `statusChanged` for loading/service status;
- `equipmentChanged` for profile/equipment widgets.

There is a central controller refresh path, but it is not a single immutable
Home model. Instead, `AppController` maintains several mutable fields and emits
coarse signals after each refresh branch.

As of the 1.2.x Refresh & Data Lifecycle foundation, `AppController` also owns
a lightweight `RefreshManager`. The manager classifies refresh reasons, maps
them to affected domains and tracks dirty domains while preserving the existing
controller-owned refresh methods. It is a lifecycle aid, not a replacement for
the current refresh pipeline.

The main refresh entry point is `_refresh_all()`:

1. If startup location detection is still running, Home enters a pending
   no-location context.
2. If a valid location exists, `_refresh_astronomy()` runs first.
3. `_refresh_weather_and_conditions()` then computes weather, sky quality,
   seeing, equipment-aware objects, scores, plan and Sky Compass.
4. If no valid location exists, `_refresh_no_location_context()` clears
   location-dependent objects and exposes placeholder summaries.

Additional refresh branches update subsets of the same state:

- `_finish_weather_refresh()` updates weather-derived state after manual or
  timed weather refreshes.
- `_finish_viirs_sky_quality_refresh()` updates sky quality and recomputes
  deep-sky context when remote VIIRS data arrives.
- `_finish_nasa_aod_refresh()` stores the display-only aerosol result for the
  Weather page and logs status/details without recomputing Home presentation
  state.
- `_refresh_active_profile_dependencies()` recomputes equipment-dependent
  recommendations after profile/equipment changes.
- `selectCity()`, `selectRecentLocation()`, `setManualLocation()`,
  `useWindowsLocation()` and `useApproximateOnlineLocation()` all apply a
  location and then call `_refresh_all()`.

## Timers, Triggers And Caches

### Timers

The Home data path currently has two backend-owned timers. The external-data
timer is `AppController._weather_refresh_timer`, a single-shot `QTimer`.

- It is scheduled by `_schedule_next_weather_refresh()`.
- It fires at the next local hour boundary, with a minimum delay of 60 seconds.
- It calls `_refresh_weather_from_timer()`, which starts a cache-friendly
  weather refresh with `force_refresh=False`.

Sky Compass also has a backend-owned `AppController._sky_compass_live_timer`.

- It runs every 60 seconds only when there is a valid location, an available
  compass DTO and a stored Sky Compass candidate snapshot.
- It calls `_refresh_sky_compass_live()`, which marks `LIVE_TICK`, updates only
  current target altitude/azimuth/direction from the stored snapshot through the
  astronomy engine and clears `COMPASS_LIVE` after completion.
- It does not call the full refresh, weather, VIIRS, NASA AOD, OpenAQ, Planner,
  equipment, `_sky_compass_candidates()` or Recommendation Engine paths.

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
- NASA AOD completion: updates only the Weather-page display DTO and logs
  status; it does not recompute Home sections.
- Sky Compass live tick: updates only the Sky Compass DTO from the stored
  candidate snapshot and emits `skyCompassChanged`.
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
- NASA AOD cache: `NasaAodProvider`, keyed by rounded latitude/longitude with
  product and granule id retained in the stored result. TTL is 18 hours; only
  compact processed results are retained in memory and JSON cache, while
  downloaded granules are temporary.
- Controller memory state: base solar-system objects, base deep-sky objects,
  enriched objects, weather hours, Moon, events, sky quality,
  seeing/transparency, advanced scores, night plan, Sky Compass and selected
  object.
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
| Sky Compass v2 | 60-second positional update for current Home target directions | Yes | No new weather call; may display existing caution text | No new seeing call | Consumes existing best object/plan scores; no new engine call | Current alt/az/direction for already prepared Home targets |
| Calendar/highlights | Current date | Yes | No | Profile setup may use seeing | Event setup enrichment only | Skyfield event generation |
| Notifications | Indirect | Yes | Yes | Through advanced scores | Notification service | Events/Moon/current targets |

Important distinction: the current Home sections are refreshed from shared
controller state, but individual QML helpers still derive presentation subsets
such as "other visible planets", "other visible deep sky", limiting-factor copy
and chronological event filtering. Home therefore has central orchestration, not
a central Home snapshot.

## Current Risks For Sky Compass

- Recomputing all astronomy objects just to keep a compass current would be too
  heavy and would also move recommendation cards unexpectedly.
- Night-hour filtering exists in several places with slightly different ranges:
  observing score, seeing estimation and Home weather digest.
- `AppController` owns orchestration and a large amount of presentation logic.
  Sky Compass v2 uses a small controller DTO for prototype speed; it should be
  migrated into the future snapshot model instead of growing further in place.
- QML currently reads many independent properties; partial signal emissions can
  briefly render a mixed state during asynchronous weather or VIIRS updates.

## Sky Compass V2 Prototype

Sky Compass v2 is not a planetarium and does not replace `Mappa cielo`. It
answers a narrower practical question: "where should I look first?" The backend
builds a guidance-oriented DTO from already available Home data:

- Home-filtered visible planets, which already respect catalogue monthly
  visibility for Solar-System eligibility;
- Home-filtered and Moon-adjusted deep-sky objects;
- current best object;
- current observing plan membership.

`SkyCompassService` groups targets into eight broad directions: Nord, Nord-Est,
Est, Sud-Est, Sud, Sud-Ovest, Ovest and Nord-Ovest. It skips targets without a
current direction, boosts objects already in the current plan and boosts the
best object. The DTO exposes the winning direction, a user-facing zone label,
practical decision reasons, up to three primary targets, a secondary count for
additional targets and up to two alternative directions. It does not expose
internal scores.

Sky Compass does not call weather, VIIRS, NASA AOD, OpenAQ, Planner, catalogue
visibility or Recommendation Engine services; it only consumes the controller
state already computed for Home. Normal Home/Planner refreshes store the
candidate set in `AppController._sky_compass_candidate_snapshot`. Its live lane
is backend-owned: every 60 seconds, `_refresh_sky_compass_live()` updates only
current positional fields for that stored snapshot, rebuilds the Sky Compass DTO
and emits `skyCompassChanged`.

The QML card renders `controller.skyCompass`. There is no QML timer in v2.

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
- `compass`: guidance DTO for Sky Compass with winning direction, practical
  reasons, prioritized targets, alternatives and stable object ids.
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

- Fast astronomical tick: every 60 seconds for Sky Compass current alt/az and
  current direction. This does not recompute recommendation ranking.
- Recommendation refresh: every 10 to 15 minutes, plus immediate refresh on
  location, profile/equipment, sky-quality or weather-summary changes. This is
  enough for Home cards and avoids ranking churn.
- Weather refresh: keep the existing next-hour scheduling and 45-minute service
  cache TTL. Manual refresh should continue to force the weather cache.
- VIIRS refresh: keep event-driven asynchronous refresh after location or
  credential changes. It should update sky quality and mark recommendation
  state dirty.
- NASA AOD refresh: keep event-driven asynchronous refresh after location or
  verified Earthdata credential changes. The visible Weather card should remain
  display-only; score integration would require a separate design pass.
- Calendar/events refresh: daily, on location change, and on app startup. Events
  are date-scale data and should not participate in the fast tick.
- Catalogue monthly visibility: keep the calculation independent from scoring,
  weather and Planner logic. Home may read the cached catalogue monthly
  visibility as the Solar-System eligibility gate, while catalogue filter/month
  and location changes still invalidate the monthly cache.

The current Sky Compass live lane applies the fast tick to the small candidate
snapshot produced by the last normal Sky Compass refresh. That normal refresh is
where `_sky_compass_candidates()` is called to combine Home-filtered visible
planets, Home-filtered and Moon-adjusted deep-sky objects, the best object and
current plan objects. The live tick itself does not call
`_sky_compass_candidates()` and does not rebuild the full catalogue.

## Expected Performance Impact

Current full refreshes are acceptable for startup/location/weather changes but
too expensive for a frequent compass tick because they can call Skyfield for
planets, Messier samples, Moon, events, equipment scoring, planner ranking,
weather scoring and optional VIIRS/AOD handling.

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

- Sky Compass feels live because current directions and altitudes can update
  every minute while Home recommendation cards remain stable.
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
  current live timer is owned by `AppController` and limited to Sky Compass.
- Do not call recommendation services from the fast compass tick.
- Do not call weather, VIIRS or AOD services from the fast compass tick.
- Reuse existing Skyfield observer/body helpers for alt/az rather than
  duplicating coordinate math in QML.
- Keep planner and recommendation refreshes event-driven or slow-timer-driven.
- Add tests that assert the fast tick updates compass fields without calling
  weather, planner or recommendation scoring.
