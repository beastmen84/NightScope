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

### NSOM Input Availability Boundary

As of `1.18.2`, NightScope keeps backend recommendation inputs separated by
availability and ownership:

- Location is the minimum required input. It can come from manual coordinates,
  Windows location or approximate online lookup. Once location exists, local
  astronomy calculations can produce target positions, visibility and Moon
  phase/illumination without provider data.
- Equipment profile data is local and optional. If no profile is active, the
  backend falls back to naked-eye/default observer assumptions before applying
  ObserverCapability or PracticalTargetValue where those concepts are used.
- Weather is an optional external provider input. When present, it belongs to
  session viability and blocking policy. When absent, weather-dependent
  conclusions remain unknown or fallback-safe rather than changing target
  physics.
- VIIRS sky quality is optional/hybrid. Real `viirs_radiance` can feed
  sky-background calculations; local preprocessed/fallback sky-quality data must
  remain distinguishable in confidence and source notes.
- NASA AOD and OpenAQ particulate data are optional external provider inputs.
  They can affect condition-adjusted scores by default only when the data is
  already available and provider-quality gates pass. AOD is the primary aerosol
  column source; OpenAQ PM is fallback/context. Confidence/provider confidence
  remains metadata and does not scale score.

Provider cache identity is deliberately distinct from refresh identity. AOD and
VIIRS keep their existing exact rounded location keys for asynchronous refresh
tokens, but a fresh provider result can be reused within 500 metres. This
absorbs normal Windows geolocation jitter without merging observations across a
broad area. AOD checks this processed cache before starting provider
authentication or a background worker; entries dated in the future are not
treated as fresh.

Open-Meteo failures do not clear an existing forecast. Timeout, network,
HTTP `408`/`425`/`5xx`, malformed JSON and empty responses are retryable and
schedule a forced provider lookup after five minutes. HTTP `400` and `429` do
not receive the short retry; the same applies to other permanent `4xx` errors.
This changes refresh lifecycle only: cached values continue to drive the same
weather summary, Session thresholds and scoring until a fresh response
succeeds.

Moon geometry is local deterministic input. The runtime computes Moon altitude,
Moon-target separation and Moon/window overlap from location, time and ephemeris
data, not from weather, VIIRS, NASA AOD, OpenAQ or equipment.

The controller keeps this geometry for the active location and observing night.
Astronomy refresh is the invalidation boundary; provider-only AOD/OpenAQ updates
reuse the existing values when rebuilding the private NSOM diagnostic snapshot.
This avoids repeating the same ephemeris work without changing Planner scoring
or any QML payload.

When Planner needs several targets, Skyfield evaluates them on one shared
30-minute timeline. Observer state, observing-night bounds and Moon apparent
position are computed once; target altitude and Moon separation remain
target-specific. The single-target method uses the same batch implementation,
so diagnostics and Planner preserve identical geometry semantics.

Planner NSOM uses Moon geometry by default through
`NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED = True`. The generic
`ObservationConditionFeatureFlags.experimental_moon_geometry_scoring` default
remains `False`, so non-Planner consumers are not implicitly rerouted.

`ObservationConditionFeatureFlags.experimental_aerosol_scoring` defaults to
`True`. Passing `ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)`
preserves the AOD/OpenAQ rollback path.

The read-only `homeObservingOverview` contract is a presentation projection of
existing Session, weather, Advanced Observing category, sky-quality and Moon
outputs. It does not recompute those values and does not feed Planner, Home
target ranking, Best Object or Sky Compass ranking. The upper Home QML consumes
the projection without displaying the numeric category diagnostics; only the
legacy weather index remains numeric and is labelled as weather-specific.

Sky Compass direction ranking remains independent from this presentation
projection. The Home QML uses the projected Session state only to label the
direction as either an observing suggestion or geometric orientation; it does
not rerank directions or targets. Missing weather also forces orientation-only
copy.

The lower-Home candidate pool contains every planet and deep-sky object with a
useful window during the observing night. `visible` means useful at some point
in that night; `observable_now` is a separate live geometry result. The Home
alternatives projection removes the four plan IDs, combines planet and deep-sky
rows and orders them first by the start of their observing window. Best time,
category and name are deterministic tie-breaks. Active Bortle/VIIRS context can
penalize, reorder or remove a deep-sky target that is no longer useful after
conditioning, but it does not truncate the surviving pool to a fixed count.

`homeNightPlanOverview` is a presentation-only projection over those existing
results. In `recommended` state it emits at most the four Planner items and
removes ranking scores and long Equipment explanations. In `monitor`,
`discouraged`, `pending` and `unavailable` states it emits no numbered sequence.
Its compact setup includes the selected telescope name only when more than one
is assigned to the active profile. None of these fields feed Planner, Equipment
selection, Home target ordering or Session policy.

The lower Home QML consumes this projection directly. It renders the plan state
card from the projected labels and shows non-plan planets/deep-sky rows in one
filterable table. The table intentionally omits legacy target scores and
Equipment explanations; selecting a row still opens the detail page, where the
longer observing guidance belongs. While that table overflows its bounded
height, its wheel handler owns mouse-wheel and touchpad events over the list,
including at either boundary; the outer Home page scroll remains active outside
the list and when the table has no internal overflow.

Sky Compass runs from the same prepared pool but filters `observable_now=False`.
Its direction contribution is the NSOM `ObservableTargetValue` scaled by a
bounded current-altitude factor, plus a fixed per-target presence term. The
direction therefore balances target quality and current density. Plan and Best
Object flags remain payload annotations and target-order tie-breaks; they do not
add direction-score bonuses. The 60-second tick updates geometry only and keeps
running with a non-empty nightly snapshot even when no target is observable at
the current minute.

During automatic startup location detection, `homeObservingOverview` emits a
presentation state of `pending` for Session, Weather and category cards. A
completed detection with no valid location emits `unavailable`. Neither state
is a score and neither feeds recommendation calculations. Missing seeing and
sky-quality inputs produce neutral no-data hints instead of inferring favourable
deep-sky potential from zero/default placeholders.

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

`SkyfieldAstronomyEngine` builds one location-aware `ObservingNightWindow` for
the current or next night. In the normal case its boundaries are local sunset
and the following local sunrise. Solar-system objects use an altitude threshold
of about 8 degrees for useful night visibility, and their sampled observing
window is always contained inside those solar boundaries.

Skyfield boundaries retain second precision while user-facing object times use
`HH:MM`. A clock label therefore represents its complete minute: when that
minute overlaps sunset, `ObservingNightWindow` resolves it to the exact sunset
instant instead of rejecting it as earlier than the boundary. This same rule is
used by Home ordering and Planner chronology.

Altitude sampling always includes the exact end of the observing night, even
when the 15/30-minute cadence does not land on sunrise. That final point is a
boundary sample only: it can extend a valid window to sunrise but cannot become
the target's best time by itself. Window start/end values are estimated by
linear interpolation where adjacent samples cross the useful-altitude
threshold. A target that reaches the threshold only at sunrise is not exposed
as a useful zero-duration opportunity.

The same `ObservingNightWindow` gates current observability for Sky Compass.
When Skyfield reports continuous daylight, no observing night is exposed. When
it reports continuous darkness, NightScope uses an explicit rolling 24-hour
planning horizon instead of pretending that sunset and sunrise occurred at
fixed clock times. An ephemeris failure produces an unavailable window rather
than a silent `18:00-07:00` fallback.

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

As of `1.13.9`, this raw prepared-object score is explicitly treated as an
interim NSOM Universe/`IntrinsicTargetQuality` seed and as a backend
compatibility field for existing services. It is not exposed as an `Oggetti
celesti` catalogue UI score, and it is not the Home visible score, which is
produced downstream after sky, observer, session and condition inputs are
applied. It is not a final NSOM recommendation score and should not be tuned
directly without a future catalogue/provenance read-model step. The
ObservationConditions read model keeps raw target input separate from
conditioned recommendation/display score so Moon/light-pollution presentation
adjustments do not become intrinsic target physics.

As of `1.14.0`, a runtime `UniverseTargetProfile` is intentionally deferred.
The future contract is documented, but the current calculation path keeps
`IntrinsicTargetQuality` as the Universe DTO until provenance, multi-catalogue
imports, intrinsic calibration or visible score explanation require a separate
profile.

As of `1.15.2`, the Catalogue/Universe raw-score policy has been reviewed for
the current backend scope. The existing separation is sufficient:

- intrinsic quality is represented by `IntrinsicTargetQuality`, seeded from the
  raw prepared-object score;
- catalogue/provenance metadata remains on catalogue rows and diagnostic
  `source_fields`, not in a new runtime profile;
- geometric and useful observability stay separate from raw score through
  catalogue observability fields and `EffectiveObservability`;
- the `Oggetti celesti` UI does not display the raw score;
- Home visible score/payload semantics remain the existing downstream
  `CelestialObject.score` display contract, while Home ordering uses NSOM
  `ObservableTargetValue` where available.

No new runtime `UniverseTargetProfile` is needed for the current backend
migration. Revisit that profile only if a future feature requires
multi-catalogue provenance, intrinsic calibration across catalogues, or visible
score explanations that expose the distinction to users.

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

Open-Meteo supplies a rolling 48-hour forecast. `AppController` parses the full
local timestamp of each `WeatherHour` and keeps only samples contained in the
current or upcoming `ObservingNightWindow`. The resulting ordered set is shared
by `ObservingScoreService`, seeing/transparency, the Home weather digest and the
session-state calculation. Daytime samples are not used as a fallback when the
astronomical window is unavailable.

The initial lookup after an astronomy snapshot uses the same background worker
boundary as manual and timer refreshes. Network retries and timeouts never run
on the Qt thread; the full-refresh loading state ends only after the current
location's result has been applied.

The visible Weather chart and hourly selector consume the separate
`weatherNext24Hours` projection. It starts at the current local hourly bucket,
ends 24 hours later and adds `isObservingNight` to samples contained in the
active `ObservingNightWindow`; QML uses that flag only for color treatment.
Selection is keyed by the forecast timestamp, so the selected hour remains
stable when the existing top-of-hour refresh removes the elapsed bucket. The
selected card uses cyan while `isObservingNight` uses teal, and the horizontal
selector remains scrollable without a visible overlapping scrollbar. The
complete 48-hour `weatherHourly` payload remains available as a compatibility
contract, while `observingWeatherHourly` remains the only input for score,
seeing/transparency, Home digest, Session and NSOM ranking.

The Home `Migliore finestra` remains the lowest-penalty relative block of up to
three consecutive forecast hours. Candidate blocks are split whenever adjacent
timestamps are more than 90 minutes apart, so samples from two different nights
cannot form a label such as `05:00-22:00`. The displayed end is clamped to the
exact `ObservingNightWindow.end`, so the final hourly sample never extends the
label beyond local sunrise.

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

`ObservationConditionsService` also accepts provider-gated NASA AOD and OpenAQ
particulate inputs, including freshness categories. In the current default
runtime, AOD and PM modifiers can affect condition-adjusted target scores only
when `experimental_aerosol_scoring` is enabled and provider-quality gates pass.
AOD owns column aerosol when policy eligible, OpenAQ PM remains fallback/context
only, and VIIRS sky background, weather transparency and Moon geometry remain
separate owners. The 1.14.11 calibration audit kept the formula disabled while
score-scale plus penalty-cap/transparency shape were reviewed; 1.14.12 resolved
the shape item by using transparency loss as the mathematical owner and
preserving a derived score modifier only for compatibility. The path was later
accepted for default-on use with explicit rollback.

The Home/Detail deep-sky pollution context keeps a user-facing note for
backward compatibility and also sets an internal target condition flag. The flag
is not exported to QML and is used only to prevent applying the same context
penalty twice during repeated refresh passes.

Medium globular clusters such as M5, M92 and M15 keep the `General` observation
mode but receive a target-profile bias toward medium magnification. This avoids
treating them like genuinely wide-field objects while leaving wide-field targets
such as M24, M31, M44 and M45 low-power friendly.

## Night Planner Ranking

`NightPlannerService.plan` first blocks the plan if weather is unusable. If not
blocked, it selects visible objects with useful observing windows, falling back
to visible scored objects when no useful-window candidates exist.

The default runtime ranking is owned by `PlannerNsomScoringService`, which
builds one `ObservationOpportunity` per candidate. `NightPlannerService`
selects the four highest-valued unique targets and only then orders those four
chronologically for display. `PlannerScoringService` remains a legacy formula
and diagnostic comparison helper, not the default ranking owner.

Equipment capability is target-specific. `EquipmentService` evaluates every
assigned telescope/binocular and optical combination, while the controller
preserves the selected setup read-model for each target. Planner scoring uses
the selected telescope for that target instead of the first telescope in the
profile. Binocular and naked-eye recommendations retain their own capability
projection and are not mixed with an unrelated telescope.

Planet difficulty is target-specific as well. Moon, Venus and Jupiter remain
the accessible reference targets, while Mercury, Mars, Uranus and Neptune use
separate telescope-aperture classes consistent with their practical observing
requirements. A maximum altitude below 25 degrees degrades the resulting class.
Binocular and naked-eye projections use their own planet matrix. This value is
presentation data and also feeds Planner's practical-constraint factor.

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

The final plan contains exactly four selected opportunities and schedules items
in roughly 45-minute increments from their useful time when no explicit target
time is available.

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
- All assigned telescopes and binoculars are evaluated per target; there is no
  single active telescope for recommendation ranking.
- The selected per-target telescope is retained for Planner
  `ObserverCapability` projection.
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
Home presentation uses one shared label map for both the deep-sky card and the
alternative-target guidance. In particular, Bortle 7 is described as
`transizione suburbana-urbana`; this copy does not alter the numeric class or
any light-pollution scoring.

Cache policy:

- VIIRS cache state is `missing`, `fresh` or `stale` for the active rounded
  location key.
- `SkyQualityEstimate.updated_at` records the last successful VIIRS retrieval.
- A VIIRS value is fresh for 7 days. After that interval it remains available
  to the UI and backend while a background lookup searches for a newer monthly
  product.
- A failed lookup preserves the stale VIIRS value; only a successful lookup
  replaces it and resets `updated_at`.
- The Weather page `Aggiorna` command schedules this cache-aware check and does
  not force a network request while the VIIRS entry is fresh.

Known limitations:

- Non-VIIRS local sky-quality estimates have no general age-based TTL.
- Offline estimates are coarse and should not be treated as measured data.
- VIIRS radiance is converted through fixed thresholds, not calibrated against
  local horizon, terrain or transient lighting.

## NASA AOD Provider Backend

`NasaAodProvider` is a satellite aerosol data provider for the Weather page
`Aerosol atmosferico` section. The same compact result can also become an
`ObservationConditionsService` input when it is already available and
provider-quality gates pass. It remains separate from forecast transparency,
seeing and provider refresh logic.

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
- The Weather page `Aggiorna` command also schedules an AOD lookup, but the
  provider reuses a processed cache entry while its 18-hour TTL is valid.
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
- Provider results are displayed in the Weather page and may influence
  condition-adjusted recommendation scoring when `experimental_aerosol_scoring`
  is enabled and provider-quality gates pass. Successful and failed lookups are
  logged with status, product, acquisition date, AOD value, method and cache-hit
  information.
- MODIS fallback depends on `netCDF4` native binaries. A PyInstaller probe passed
  on the current Windows development environment, but distribution size and
  native dependency behavior should remain monitored.
- AOD is a column aerosol proxy, not the same concept as forecast transparency
  and not the same concept as OpenAQ ground-level PM2.5/PM10 measurements.
- The `1.16.0` Weather page labels AOD as aerosol data and shows freshness
  explicitly so stale-but-usable data is not presented as a fresh condition.
- Historical AOD/OpenAQ migration reports were removed in `1.15.2`. The live source of truth is this calculation document, the runtime `ObservationConditionsService` implementation and `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md`.

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
- selected object detail refresh.

Location changes trigger:

- a background astronomy snapshot containing night bounds, object geometry,
  Moon data, events and monthly catalogue visibility,
- weather refresh,
- sky-quality refresh,
- diagnostic NASA AOD backend refresh when Earthdata credentials are verified,
- profile-dependent recommendation refresh.

VIIRS completion triggers:

- sky-quality update,
- background deep-sky reload,
- equipment recommendation refresh,
- deep-sky pollution context,
- observing outputs and selected detail refresh.

Astronomy and VIIRS worker results carry both a monotonically increasing
request id and the active location key. Results produced for an older request
or location are discarded. The Qt thread keeps ownership of controller state,
signals, Equipment projections and Planner outputs.

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
