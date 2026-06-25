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

Object-dependent Moon sensitivity is implemented in `NightPlannerService`.
Planets, the Moon and the Sun have no Moon penalty. Diffuse objects and
galaxies are penalized more strongly. Globular clusters are penalized less.
Open clusters are penalized lightly.

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

## Blocking Weather And "Sessione Sconsigliata"

The observing plan is blocked by `NightPlannerService` when any of these are
true:

- observing score <= 25,
- precipitation probability >= 65,
- cloud cover >= 85.

The home page displays a global warning when the plan is empty and blocking
weather is detected. The current QML warning logic mirrors the same conceptual
conditions.

When blocking weather is active, object-specific astronomical reasoning is still
kept, but the global warning explains that the session is not reliable.

Known consistency risk:

- The blocking thresholds are duplicated between Python planner logic and QML
  presentation logic. If one changes without the other, the UI can disagree with
  the planner.

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
Current Moon sensitivity in planning is higher for galaxies than for globular
clusters. Light-pollution presentation filtering also uses a stronger galaxy
multiplier than globular clusters.

## Night Planner Ranking

`NightPlannerService.plan` first blocks the plan if weather is unusable. If not
blocked, it selects visible objects with useful observing windows, falling back
to visible scored objects when no useful-window candidates exist.

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
- The recommendation engine internally samples focal positions such as high,
  low, midpoint and ideal clamped positions.
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
- Weather blocking thresholds are duplicated between planner and QML warning
  presentation.
- Seeing can remain high while observing quality is poor, because seeing and
  transparency/global weather are separate concepts.
- Sky-quality cache has no broad TTL policy.
- Best-object selection applies a weather-factor floor, so global blocked
  session messaging is needed to avoid over-promising.
