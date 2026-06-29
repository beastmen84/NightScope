# NightScope Calculation Logic

This document describes the calculations currently implemented in NightScope for
the v1.0 release candidate.

## Astronomical Calculations

### Source

The primary astronomy engine is `SkyfieldAstronomyEngine`.

It uses:

- Skyfield time scales,
- JPL `de421.bsp` ephemeris,
- Skyfield almanac helpers for solar-system rise, transit and set,
- Astropy/Skyfield coordinate helpers for catalog object altitude/azimuth.

If the ephemeris is unavailable or corrupt, the application falls back to
`MockAstronomyEngine` so the UI remains usable.

### Observer Inputs

Inputs:

- latitude,
- longitude,
- elevation in meters,
- timezone,
- current date/time.

All object visibility is observer-dependent.

### Solar-System Objects

For Sun, Moon and planets, the engine computes:

- current altitude,
- current azimuth,
- distance label when available,
- rise time,
- transit/culmination time,
- set time,
- maximum sampled altitude during the observing window,
- observing window above threshold,
- score label and visibility flag.

The current observing window used for sampling is evening to morning, roughly
18:00 to 07:00 local time. Solar-system objects use an altitude threshold of
about 8 degrees for useful night visibility. An object can be considered
available if it is currently above the horizon or reaches the threshold during
the sampled window.

### Deep-Sky Objects

Deep-sky objects come from the Messier catalog. The engine performs a cheap
maximum-altitude prefilter using declination and observer latitude, then
computes detailed visibility for the best candidates.

Deep-sky visibility uses:

- right ascension,
- declination,
- magnitude,
- object type,
- sampled altitude through the night,
- a useful altitude threshold of about 15 degrees.

The engine returns the top visible deep-sky objects by score.

### Catalogue Observability

The `Oggetti celesti` catalogue keeps two location-dependent concepts separate
for fixed-coordinate catalogue objects:

- geometric observability: the object rises above the horizon from the active
  location at least once (`maximum altitude > 0°`);
- useful deep-sky observability: the object reaches the useful deep-sky altitude
  threshold (`maximum altitude >= 15°`).

The catalogue UI currently displays only useful deep-sky observability in the
`Utile (≥15°)` column. Geometric observability is kept internally so that
low southern Messier objects can still be distinguished from objects that never
rise at all. Solar-System objects do not use this location-only fixed-coordinate
column because their coordinates are time-dependent; the catalogue shows `—`
for them in `Utile (≥15°)` and uses the monthly visibility calculation
instead.

For Solar-System Home eligibility, the catalogue monthly visibility criterion is
the source of truth. A planet can be above the horizon at a specific instant and
still be excluded from Home recommendations if, in the active catalogue month
and location, it does not reach at least 15 degrees during astronomical
darkness. This keeps "above horizon now" separate from "usefully visible this
month".

### Object Score

The raw object score is based on:

- maximum altitude,
- visual magnitude when known,
- object-type bonus,
- visibility threshold.

Altitude contributes up to about 55 points. Magnitude contributes up to about
35 points. Object type contributes a small bonus. Scores are clamped to 0-100.

### Limitations

Implemented:

- rise,
- set,
- transit/culmination,
- current altitude,
- current azimuth,
- sampled night maximum altitude,
- sampled observing window,
- basic visibility thresholds.

Not implemented:

- atmospheric extinction modeling,
- horizon masks or local obstructions,
- object surface-brightness visibility modeling in the astronomy engine,
- Moon/object angular separation,
- Moon altitude in deep-sky visibility,
- continuous minute-level optimization of observing windows.

## Moon

The Moon implementation includes:

- phase name,
- illumination percentage,
- phase angle,
- rise/set/transit from the same solar-system machinery,
- global observing score penalty,
- advanced-score contribution,
- object-dependent deep-sky penalty in planning and presentation.

Object-dependent Moon sensitivity is implemented in
`ObservationConditionsService`. Planets, the Moon and the Sun have no Moon
penalty. Diffuse objects and galaxies are penalized more strongly. Globular
clusters are penalized less. Open clusters are penalized lightly.

`PlannerScoringService` reuses the same Moon-condition primitive, but owns how
that penalty is combined with Planner-specific weather, difficulty, aperture
and light-pollution factors.

Known limitations:

- Moon altitude is not used in the score.
- Moon/object angular separation is not used.
- Moon rise/set timing is not integrated into per-object deep-sky penalties.
- No sky-surface-brightness model is used.
- No object angular-size-specific lunar scattering model is used.

## Observing Quality

`ObservingScoreService.weather_score` produces the global observing score.

Inputs:

- hourly weather forecast,
- Moon summary.

Night hours are selected from forecast hours with hour >= 19 or hour <= 5. If no
night hours are found, the service falls back to the first available hours.

The score starts at 100 and applies:

- cloud penalty: `min(55, round(avg_cloud * 0.55))`,
- precipitation penalty: `min(30, round(max_rain * 0.45))`,
- wind penalty: `max(0, avg_wind - 10)`,
- humidity penalty: `max(0, round((avg_humidity - 70) * 0.25))`,
- Moon penalty: `round(max(0, illumination - 35) * 0.28)`.

The result is clamped to 0-100.

Labels:

- 0-25: `Pessima`,
- 26-50: `Scarsa`,
- 51-70: `Discreta`,
- 71-85: `Buona`,
- 86-100: `Ottima`.

If no forecast is available, the output is `Pessima`, score 0.

## Blocking Weather And Session State

The observing plan is blocked by `NightPlannerService.weather_blocking_status`
when any of these are true:

- observing score <= 25,
- precipitation probability >= 65,
- cloud cover >= 85.

The blocking decision is centralized in Python and exposed through
`AppController`. QML renders the computed state and does not duplicate the
blocking thresholds.

NightScope presents three session states:

- `recommended`: no global blocking warning; the normal observing plan is
  displayed.
- `monitor`: current summary is blocked, but the forecast still contains a
  realistic later observing window. The warning shows "Sessione da monitorare",
  the best predicted window and potential targets.
- `discouraged`: current summary is blocked and no useful observing window is
  found. The warning shows "Sessione sconsigliata" and hides target/window
  suggestions.

The `monitor` state is selected when `AppController` finds at least two
consecutive usable night forecast hours. A usable hour currently requires:

- precipitation probability <= 35,
- cloud cover <= 65,
- wind <= 28 km/h,
- per-hour observing score >= 45.

Hours are considered consecutive if they are no more than about 90 minutes
apart, allowing normal hourly forecast spacing across midnight.

When a session warning is active, object-specific astronomical reasoning is
still kept, but the global warning explains whether targets are only potential
or whether the session is not advisable.

Presentation:

- QML renders `observingSessionState`, `observingSessionTitle`,
  `observingSessionIcon`, `observingSessionDetail`,
  `observingSessionDescription`, `showObservingSessionOpportunity`,
  `blockingReason`, `blockingDetail` and `suggestedObservingWindow`.

## Seeing And Transparency

`SeeingTransparencyService` currently uses `BasicForecastSeeingProvider`.

Seeing score inputs:

- average wind,
- average gust,
- low cloud cover,
- dew-point gap.

Seeing starts at 100 and is reduced for wind, gusts, low cloud and small
dew-point gap.

Transparency score inputs:

- total cloud cover,
- low/mid/high cloud cover,
- humidity,
- visibility,
- light pollution.

Transparency starts at 100 and is reduced by cloud layers, humidity, reduced
visibility and sky-quality penalty.

Labels:

- >= 82: Excellent,
- >= 65: Good,
- >= 42: Average,
- below 42: Poor.

Seeing can be excellent while global observing quality is poor. This is not a
mathematical contradiction: seeing estimates atmospheric steadiness, while the
global score also considers cloud cover and precipitation. The UI should keep
the global blocked-session warning prominent when weather is unusable.

## Advanced Observing Scores

`AdvancedObservingService` computes separate planetary and deep-sky scores.

Planetary score:

`weather * 0.36 + seeing * 0.42 + wind_component * 0.12 + moon_component * 0.10`

where:

- `wind_component = 100 - min(55, wind_kmh * 1.4)`,
- `moon_component = 100 - min(25, moon_illumination * 0.15)`.

Deep-sky score:

`weather * 0.34 + transparency * 0.30 + light_pollution_quality * 0.24 + (100 - moon_illumination) * 0.12`

Both scores are capped by blocking weather:

- precipitation >= 70 caps at 25,
- precipitation >= 45 caps at 40,
- cloud >= 85 caps at 30,
- cloud >= 70 caps at 45,
- observing score <= 25 caps near the current observing score,
- observing score <= 50 caps near the current observing score.

This prevents high planetary/deep-sky scores under unusable weather, although
the independent seeing label may still be high.

## Planetary Recommendations

Planetary recommendations depend on:

- solar-system visibility,
- altitude and observing window,
- global and planetary weather scores,
- seeing-limited magnification,
- active profile equipment,
- practical telescope magnification limits.

Equipment recommendations for planets prefer higher magnification, but the
target magnification is reduced under low altitude or poor seeing. Barlows are
allowed for planetary targets when they improve the setup enough.
When seeing is unavailable, NightScope treats it as unknown rather than
excellent and uses a conservative magnification cap. With a Mak 127 and Baader
Hyperion Zoom, unknown seeing should prefer a safer medium-high click position
such as 16 mm instead of defaulting to 8 mm.

## Deep-Sky Recommendations

Deep-sky recommendations depend on:

- altitude and observing window,
- raw object score,
- object type,
- magnitude,
- light pollution,
- Moon illumination,
- object-dependent Moon sensitivity,
- active profile equipment,
- field-of-view and exit-pupil suitability.

Galaxies are penalized more than globular clusters under strong moonlight.
Current Moon sensitivity is shared through `ObservationConditionsService`.
Light-pollution presentation filtering also uses a stronger galaxy multiplier
than globular clusters, while Planner-specific light-pollution ranking remains
owned by `PlannerScoringService`.

`ObservationConditionsService` can also carry provider-neutral diagnostics for
NASA AOD and OpenAQ particulate data, including freshness categories. These
fields currently stay neutral: AOD and PM modifiers remain zero and do not feed
Planner ranking, Home scores, Recommendation Engine, Sky Compass, seeing or
transparency scores.

Medium globular clusters such as M5, M92 and M15 keep the `General` observation
mode but receive a target-profile bias toward medium magnification. This avoids
treating them like genuinely wide-field objects while leaving wide-field targets
such as M24, M31, M44 and M45 low-power friendly.

## Night Planner Ranking

`NightPlannerService.plan` first blocks the plan if weather is unusable. If not
blocked, it selects visible objects with useful observing windows, falling back
to visible scored objects when no useful-window candidates exist.

Planner ranking math is owned by `PlannerScoringService`; `NightPlannerService`
orchestrates selection and chronological display of the final plan.

Planner score:

`(object_score * 0.48 + category_score * 0.34 + weather_score * 0.18 + aperture_bonus - pollution_penalty - moon_penalty) * difficulty_factor * weather_factor`

Factors:

- object score comes from astronomy plus later adjustments,
- category score is planetary or deep-sky advanced score,
- weather score is global observing quality,
- aperture bonus is limited by telescope aperture,
- pollution penalty is object-type dependent,
- Moon penalty is object-type dependent,
- difficulty factor favors easier objects,
- weather factor reduces ranking under weaker weather.

The final plan is capped to a small ordered list and schedules items in roughly
45-minute increments from their useful time.

## Best Object Selection

`ObservingScoreService.best_object` selects from visible objects.

Ranking uses:

- object score,
- weather factor: `max(0.25, weather_score / 100)`,
- difficulty factor.

Because the weather factor has a floor, a visible object can still be selected
under poor weather. The blocked-session presentation is therefore important: it
explains that targets are only potential if a clear window appears.

## Equipment Calculations

`EquipmentService` uses active-profile equipment only.

Inputs:

- active profile telescopes,
- active profile eyepieces,
- active profile Barlows,
- target object type,
- target magnitude,
- target angular size,
- target altitude,
- seeing score,
- Bortle/sky-quality context.

Calculated values:

- magnification: `(telescope_focal_length / eyepiece_focal_length) * barlow`,
- true field of view: `apparent_field / magnification`,
- exit pupil: `aperture / magnification`,
- practical useful magnification range,
- limiting magnitude estimate,
- resolution estimate,
- available configuration count.

Assigned equipment only:

- `AppController` passes active-profile telescopes, eyepieces and Barlows.
- `EquipmentService.suggest_for_profile` never considers unassigned equipment.
- If no optical telescope is assigned, a naked-eye fallback is used or the
  recommendation asks the user to add appropriate equipment.

Zoom eyepieces:

- A zoom eyepiece remains one equipment record.
- Zoom eyepieces can define actual selectable click positions in the catalogue.
  The recommendation engine evaluates those physical positions instead of
  synthetic ideal focal lengths.
- The Baader Hyperion Zoom 8-24 mm is evaluated at 24, 20, 16, 12 and 8 mm.
- Display text may show the selected focal position, but the catalog record is
  not duplicated.

Barlow logic:

- Only assigned Barlows are candidates.
- Barlows are not invented.
- A Barlow is selected only if it improves the score sufficiently over the
  no-Barlow option.
- Wide-field and non-Barlow-friendly targets penalize Barlow usage.

Recommended setup score:

- target magnification deviation,
- exit pupil deviation,
- true-field suitability,
- seeing-limited maximum magnification,
- Barlow appropriateness,
- target type.

## VIIRS And Light Pollution

`LightPollutionService` resolves sky quality using:

1. cache,
2. World Atlas CSV provider,
3. local sky-quality CSV provider,
4. NASA VIIRS Black Marble provider when Earthdata credentials are verified,
5. offline estimate fallback.

Cache key:

- rounded latitude,
- rounded longitude,
- city name.

NASA VIIRS provider:

- product: NASA Black Marble VNP46A3,
- version: 002,
- collection: 5200,
- lookup window: searches recent monthly products up to 36 months back,
- tile mapping uses a 10-degree grid,
- reads a small OPeNDAP subset around the observer,
- uses radiance, observation count and quality fields,
- prefers quality code 0 and falls back to quality <= 2.

Radiance-to-Bortle conversion:

- radiance < 0.2: Bortle 2,
- < 1: Bortle 3,
- < 5: Bortle 4,
- < 15: Bortle 5,
- < 40: Bortle 6,
- < 100: Bortle 7,
- < 300: Bortle 8,
- otherwise Bortle 9.

Sky-brightness-to-Bortle conversion is also implemented for CSV/local sources.

Known limitations:

- No general age-based TTL for sky-quality cache entries.
- A cached NASA VIIRS source is treated as fresh if present.
- Offline estimates are coarse and should not be treated as measured data.
- VIIRS radiance is converted through fixed thresholds, not calibrated against
  local horizon, terrain or transient lighting.

## NASA AOD Provider Backend

`NasaAodProvider` is a satellite aerosol data provider for the Weather page
`Trasparenza atmosferica` section. It is display-only and is not used by
Recommendation Engine, Planner, Sky Compass, seeing, transparency, weather score
or observing scores.

Product order:

1. VIIRS MAIAC AOD `VNP19A2.002`, using `Optical_Depth_055`,
   `AOD_Uncertainty` and `AOD_QA`.
2. MODIS MAIAC AOD `MCD19A2.061`, using the same fields as fallback only.

Access flow:

- CMR/LP DAAC Cloud discovery and download are handled through `earthaccess`.
- Earthdata username/password are read from the existing verified Earthdata
  credential store.
- `AppController` schedules the provider in the background when both a valid
  active observing location and a successful Earthdata connection test are
  available.
- `earthaccess.login(..., persist=False)` is retried with backoff because URS
  token creation can time out.
- Long-lived manually generated Earthdata tokens are not required by the default
  provider path.

Extraction policy:

- Candidate granules are searched newest first over the recent lookup window.
- Each granule is downloaded to a temporary directory, parsed, then deleted even
  if extraction fails.
- VIIRS HDF5 is read with `h5py`.
- MODIS HDF4 fallback is read with `netCDF4`.
- The provider maps the observer coordinate into the MAIAC sinusoidal grid,
  tries the exact pixel first, then uses a 5x5 local median when the exact pixel
  is invalid or no-data.
- The result stores AOD 550 nm, uncertainty when available, raw QA value,
  acquisition date, granule id, extraction method and local valid-pixel count.

Cache policy:

- Only compact processed results are cached. A memory copy avoids repeated work
  inside the running process, while a small JSON cache allows app restarts to
  reuse recent processed AOD results within the TTL.
- HDF/HDF5 granules are never cached.
- Cache keys use rounded latitude/longitude; the stored result preserves product,
  acquisition date and granule id.
- Default TTL is 18 hours.

Current limitations:

- QA filtering is basic; formal `AOD_QA` bit decoding should be improved before
  these values are used operationally for scoring.
- The provider result is exposed only in the Weather page. Successful and failed
  lookups are logged with status, product, acquisition date, AOD value, method
  and cache-hit information, but Planner, Sky Compass and recommendation outputs
  do not consume the value.
- MODIS fallback depends on `netCDF4` native binaries. A PyInstaller probe passed
  on the current Windows development environment, but distribution size and
  native dependency behavior should remain monitored.
- AOD is a column aerosol/transparency proxy, not the same concept as OpenAQ
  ground-level PM2.5/PM10 measurements.

## Refresh Chain

Profile/equipment changes trigger:

- profile equipment reload when needed,
- equipment recommendation recomputation from base objects,
- deep-sky pollution context reapplied,
- observing outputs recomputed,
- selected object preserved by id where possible,
- QML profile-dependent signals emitted.

Weather changes trigger:

- weather score,
- sky quality lookup,
- seeing/transparency,
- equipment recommendations,
- advanced scores,
- best object,
- plan,
- sky map,
- notifications,
- selected object detail refresh.

Location changes trigger:

- astronomy data reload,
- weather refresh,
- sky-quality refresh,
- diagnostic NASA AOD backend refresh when Earthdata credentials are verified,
- profile-dependent recommendation refresh.

VIIRS completion triggers:

- sky-quality update,
- deep-sky reload,
- equipment recommendation refresh,
- deep-sky pollution context,
- observing outputs and selected detail refresh.

## Known Limitations

- Moon altitude is not used in scoring.
- Moon/object separation is not used.
- Moon rise/set timing is not used to vary deep-sky penalties by hour.
- No local horizon mask is implemented.
- No atmospheric extinction model is implemented.
- No surface-brightness model for extended objects is implemented.
- Weather blocking thresholds are intentionally owned by
  `NightPlannerService.weather_blocking_status`.
- Seeing can remain high while observing quality is poor, because seeing and
  transparency/global weather are separate concepts.
- Sky-quality cache has no broad TTL policy.
- Best-object selection applies a weather-factor floor, so global blocked
  session messaging is needed to avoid over-promising.
