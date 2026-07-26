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

For coordinate-based locations, NightScope resolves the IANA timezone directly
from offline geographic polygons. A nearby city name is presentation metadata;
it is not an input to local-night boundaries or event times. A valid timezone
returned by the approximate IP provider is retained, while the computer
timezone is only a fallback if geographic resolution cannot run.

### NSOM Input Availability Boundary

As of `1.18.2`, NightScope keeps backend recommendation inputs separated by
availability and ownership:

- Location is the minimum required input. It can come from manual coordinates,
  system location (Windows or GeoClue 2 on Linux), or approximate online
  lookup. Once location exists, local astronomy calculations can produce target
  positions, visibility and Moon phase/illumination without provider data.
- Equipment profile data is local and optional. If no profile is active, the
  backend falls back to naked-eye/default observer assumptions before applying
  ObserverCapability or PracticalTargetValue where those concepts are used.
- Weather is an optional external provider input. Seeing and atmospheric
  transparency belong to the Sky layer; Session applies only the binary
  usable/blocked policy. This prevents the same clouds, humidity and wind from
  scaling a target once in `ObservationEnvironment` and again through a
  continuous Session score.
- VIIRS sky quality is optional/hybrid. Real `viirs_radiance` or a real local
  preprocessed dataset can feed sky-background calculations. Missing data stays
  unavailable; no Bortle class or sky-background penalty is synthesized.
- NASA AOD and OpenAQ particulate data are optional external provider inputs.
  They affect only the canonical atmospheric-transparency factor when already
  available and provider-quality gates pass. They never mutate
  `CelestialObject.score`: AOD is the primary aerosol-column source and OpenAQ
  PM is its non-additive fallback/context. Confidence remains metadata and does
  not scale score.

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
Astronomy refresh is its invalidation boundary. Accepted AOD/OpenAQ completions
reuse that geometry and recompute Home, Planner, Best Object and Sky Compass
locally; they do not repeat ephemeris work or mutate QML payload contracts. If a
weather refresh is already running, its completion performs the pending
recalculation once with the newest provider values.

When Planner needs several targets, Skyfield evaluates them on one shared
30-minute timeline. Observer state, observing-night bounds and Moon apparent
position are computed once; target altitude and Moon separation remain
target-specific. The single-target method uses the same batch implementation,
so diagnostics and Planner preserve identical geometry semantics.

Moon geometry is part of every NSOM consumer through the shared
`ObservationEnvironment`. AOD/OpenAQ atmospheric influence is also canonical
when provider-quality gates pass. Neither path has a selectable runtime flag.

The read-only `homeObservingOverview` contract is a presentation projection of
existing Session, weather, NSOM category, sky-quality and Moon
outputs. It does not recompute those values and does not feed Planner, Home
target ranking, Best Object or Sky Compass ranking. The upper Home QML consumes
the projection without displaying the numeric category diagnostics; only the
weather index remains numeric and is labelled as weather-specific.

Sky Compass direction ranking remains independent from this presentation
projection. The Home QML uses the projected Session state only to label the
direction as either an observing suggestion or geometric orientation; it does
not rerank directions or targets. Missing weather also forces orientation-only
copy.

The lower-Home candidate pool contains every planet and deep-sky object with a
useful window during the observing night. `visible` means useful at some point
in that night; `observable_now` is a separate live geometry result. The Home
alternatives projection removes the plan IDs, combines planet and deep-sky
rows and orders them first by the start of their observing window. Best time,
category and a natural numeric name key are deterministic tie-breaks. The name
key orders catalogue identifiers by their numeric component (`M3`, `M40`,
`M100`, and equivalently `C2`, `C14`) instead of raw lexicographic text. Active
Bortle/VIIRS presentation context can penalize and reorder deep-sky display
scores, but it preserves astronomical `visible` state and candidate
cardinality. Home, Planner, Best Object and Sky Compass receive the raw target
through the conditioned read model and apply target-class sky-background
sensitivity once in the canonical NSOM environment.

All runtime target pools use the normalized non-empty object ID as identity.
Whitespace and case differences do not create a second target; the first
occurrence is retained so ordering remains stable. Objects without an ID are
not discarded by this guard. Planner, Best Object, Home ranking, Sky Compass
and the lower-Home presentation apply the same invariant before scoring or
counting.

`homeNightPlanOverview` is a presentation-only projection over those existing
results. In `recommended` state it emits at most the four Planner items and
removes ranking scores and long Equipment explanations. In `monitor`,
`discouraged`, `pending` and `unavailable` states it emits no numbered sequence.
Its compact setup includes the selected telescope name only when more than one
is assigned to the active profile. None of these fields feed Planner, Equipment
selection, Home target ordering or Session policy.

When the active profile contains neither telescopes nor binoculars, this
presentation projection removes alternatives whose existing
`EquipmentSetupReadModel.requires_optical_instrument` flag is true. It does not
re-score or reorder targets and it does not duplicate the naked-eye suitability
rule owned by `RecommendationPresenter`; a missing setup read model is not
presented as a confirmed naked-eye target.

The lower Home QML consumes this projection directly. It renders the plan state
card from the projected labels and shows non-plan planets/deep-sky rows in one
filterable table. The table intentionally omits legacy target scores and
Equipment explanations; selecting a row still opens the detail page, where the
longer observing guidance belongs. While that table overflows its bounded
height, its wheel handler owns mouse-wheel and touchpad events over the list,
including at either boundary; the outer Home page scroll remains active outside
the list and when the table has no internal overflow.

The observing detail opened from Home or Calendar consumes the score-free
`observingObjectDetail` projection. Its display target prefers the geometry
snapshot refreshed every minute for Sky Compass, while NSOM keeps using the raw
target from the condition read model. Deep-sky observability uses the same
15-degree useful-altitude threshold as Skyfield; planets and Moon use 8 degrees.
The full useful window, its duration and the best instant remain separate
fields. Deep-sky rows expose useful-window start/end instead of placeholder
horizon events, while Solar-System targets retain real rise/set data. Session
state is metadata and never changes target geometry or score. Equipment labels
come from the setup selected for that target, including multi-telescope
profiles. A separate filter projection may show one primary recommendation and
one optional color recommendation from the active profile; neither changes the
selected setup or any score. Catalogue detail remains on the raw
`selectedObject` contract.

Observation persistence is intentionally not part of object detail. The
dedicated `Log Osservazioni` surface owns complete CRUD operations on
`ObservationHistory`, with no result cut. Its service validates local date/time,
object name and the 1-5 rating, rejects future entries and builds only
score-free presentation fields and aggregate counts. It does not feed NSOM,
Planner, Home, Sky Compass, Equipment or target recommendations.

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
deep-sky potential from zero/default placeholders. When weather supports a
deep-sky category diagnostic but sky quality is absent, the presentation state
is `partial`: the backend score remains unchanged for existing consumers, while
Home uses an amber `Parziale` badge and explicitly leaves faint-object
visibility unverified.

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

Deep-sky objects come from the generic physical-object catalogue: 7,585 unique
targets comprising 110 Messier, 109 Caldwell and 7,366 NGC-only objects.
OpenNGC contributes 7,839 usable designations that resolve to 7,571 physical
targets; overlaps and aliases therefore do not duplicate calculations.

Before parsing coordinates, `CatalogueRepository` returns only targets whose
effective recommendation preference is enabled. The engine then evaluates each
admitted `object_id` once, performs a cheap maximum-altitude prefilter using
declination and observer latitude, and computes detailed visibility in a
NumPy-backed Skyfield batch. A scalar fallback preserves behavior if the batch
path fails.

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

The list's `Visibili nel mese` control calculates the complete catalogue for
the selected month and location, filters out negative results and deliberately
does not repeat that result in a table column. Catalogue detail has a separate
boundary: it evaluates only the opened object for the current local year and
month, regardless of list filter state or selected list month. The result is
cached by location, month and object. `No` is reserved for a calculated
negative result; missing location, unsupported engines and calculation errors
remain unknown (`—`). Italian object-type and observation-mode labels are a
presentation mapping only; canonical catalogue values remain unchanged for
filters and calculations.

For Solar-System Home eligibility, the catalogue monthly visibility criterion is
the source of truth. A planet can be above the horizon at a specific instant and
still be excluded from Home recommendations if, in the active catalogue month
and location, it does not reach at least 15 degrees during astronomical
darkness. This keeps "above horizon now" separate from "usefully visible this
month".

### Catalogue Recommendation Eligibility

Every persistent catalogue object has an effective recommendation-eligibility
value. The seed supplies `recommendation_enabled_by_default`; the local
`CatalogueRecommendationPreference` table stores the user's persistent choice.
The 219 Messier and Caldwell objects start enabled and can be changed. The
7,366 NGC-only physical targets start disabled; the 205 NGC identities already
represented by Messier or Caldwell retain the curated object's default. The
nine synthetic Solar System S1-S9 entries are always enabled and cannot store
an override.

This value is a hard admission gate and never multiplies, caps or otherwise
changes a target score. The repository resolves it in SQL before coordinate,
nightly visibility and Moon-geometry calculations. The controller repeats the
filter when reusing cached base deep-sky targets, before Equipment enrichment,
condition projections and NSOM consumers.
Consequently a disabled object cannot appear in Home, Best Object, Planner or
Sky Compass and cannot receive a suggested setup. It remains available to
catalogue search, filters, observability calculations and descriptive detail.
Re-enabling a target starts a deep-sky-only astronomy refresh so it can enter
the current suggestion pool immediately; disabling removes it from downstream
pools immediately.

The catalogue bulk controls apply the same gate to the complete current filter
result. They deduplicate aliases by normalized physical `object_id`, skip the
locked Solar System rows, validate the complete request before a single SQLite
transaction, update the virtualized model without a reset, and enqueue one
latest-state recommendation refresh. They do not introduce another score,
ranking path, worker type or platform-specific multiprocessing behavior.

Fixed-target nightly visibility, monthly catalogue visibility and Moon
separation use vectorized Skyfield/NumPy batches with scalar fallbacks. The
preference join uses the indexed `NOCASE` primary key; applying `LOWER()` to
both sides would disable that lookup and make an all-enabled query quadratic.
This design is the same in Windows and Linux and does not share Qt or SQLite
state across processes.

On the 2026-07-25 Windows development benchmark, the indexed eligibility query
for all 7,585 targets took about 0.15 seconds instead of 18.9 seconds. A
controlled end-to-end refresh at Bologna took about 7.55 seconds with the 219
default targets and 12.45 seconds with all 7,585 targets enabled. The latter
includes nightly and monthly astronomy, annual events, Moon geometry,
Equipment enrichment, NSOM, Planner and Sky Compass; 5,384 deep-sky targets
were useful in that test. The extreme case therefore adds about 4.9 seconds
inside the existing background worker. Multiprocessing is not part of the
current design.

### Object Scores

`CelestialObject.score` is the compatibility/display score based on:

- maximum altitude,
- visual magnitude when known,
- object-type bonus,
- visibility threshold.

Altitude contributes up to about 55 points. Magnitude contributes up to about
35 points. Object type contributes a small bonus. Scores are clamped to 0-100.

From `1.21.0`, Skyfield also prepares an internal `intrinsic_score`. It uses
only magnitude and the object-type component, normalized to 0-100, and is
therefore independent from observer location, current altitude, observing
window and visibility threshold. `IntrinsicTargetQuality` consumes this value;
runtime/test objects that do not carry it temporarily fall back to the
compatibility score. `intrinsic_score` is deliberately omitted from the QML
payload.

The compatibility score is not exposed as an `Oggetti celesti` catalogue UI
score and is not a final NSOM recommendation score. Geometry belongs to
`ObservationEnvironment`; observer equipment, Session and Opportunity are
applied only in their respective downstream NSOM layers.

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
- Moon/object angular separation in the astronomy visibility window itself,
- Moon altitude in the astronomy visibility threshold itself,
- continuous minute-level optimization of observing windows.

## Moon

The Moon implementation includes:

- phase name,
- illumination percentage,
- phase angle,
- rise/set/transit from the same solar-system machinery,
- global observing score penalty,
- object-dependent deep-sky presentation adjustment,
- target-specific NSOM Moon background from illumination, altitude, separation
  and target-window overlap.

Object-dependent presentation sensitivity remains in
`ObservationConditionsService`. Ranking sensitivity is owned by target-class
profiles and composed once by `NsomObservationEnvironmentService`; Planner then
adds observer capability, timing and binary Session viability.

Known limitations:

- The presentation compatibility score still uses illumination-only Moon
  adjustment; altitude/separation belong to NSOM ranking.
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

The Weather page labels its top summary as night-scoped: cloud cover, wind,
humidity and temperature are averages over `observingWeatherHourly`, while the
precipitation value is the maximum probability in that set. Seeing and
transparency use the same hours; Bortle is explicitly labeled as a local,
non-hourly property.

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

Atmospheric transparency inputs:

- total cloud cover,
- low/mid/high cloud cover,
- humidity,
- visibility.

Atmospheric transparency starts at 100 and is reduced by cloud layers, humidity
and reduced visibility. The legacy composite `transparency_score` additionally
includes the sky-quality penalty for compatibility with existing backend
consumers.

From `1.21.0`, `SeeingTransparency` also carries an internal
`atmospheric_transparency_score`: the same cloud/humidity/visibility estimate
before the VIIRS/Bortle sky-background penalty. The numeric internal field is
omitted from QML, while `atmosphericTransparency` exposes only its localized
quality label. From `1.32.9`, Weather and the Home deep-sky summary use that
label and present Bortle separately; the legacy composite label and score remain
available for compatibility. NSOM applies atmospheric transparency and static
sky background once in separate environment components.

Labels:

- >= 82: Excellent,
- >= 65: Good,
- >= 42: Average,
- below 42: Poor.

Seeing can be excellent while global observing quality is poor. This is not a
mathematical contradiction: seeing estimates atmospheric steadiness, while the
global score also considers cloud cover and precipitation. The UI should keep
the global blocked-session warning prominent when weather is unusable.

## Home Category Scores

`NsomCategoryScoreService` projects broad planetary and deep-sky conditions
through `NsomObservationEnvironmentService`.

- Planetary conditions use a representative intrinsic-quality 100 planet.
- Deep-sky conditions are the rounded mean of representative galaxy, diffuse
  nebula, open-cluster and globular-cluster observable values.
- Geometry, Moon, static sky background and atmospheric transparency use the
  same target-class profiles as runtime ranking.
- Session blocking and equipment do not enter these category summaries.

The numeric values remain internal to the Home overview contract; QML presents
descriptive labels so they are not confused with a target score or Planner
opportunity.

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
The light-pollution presentation projection also uses a stronger galaxy
multiplier than globular clusters. It cannot remove a candidate or change
astronomical visibility. NSOM ranking applies target-class sensitivity once
through the canonical static-sky-background factor.

`ObservationConditionsService` also accepts provider-gated NASA AOD and OpenAQ
particulate inputs, including freshness categories. AOD and PM influence the
canonical atmospheric-transparency factor only when provider-quality gates pass;
they do not mutate display `CelestialObject.score` values.
AOD owns column aerosol when policy eligible, OpenAQ PM remains fallback/context
only, and VIIRS sky background, weather transparency and Moon geometry remain
separate owners. The 1.14.11 calibration audit kept the formula disabled while
score-scale plus penalty-cap/transparency shape were reviewed; 1.14.12 resolved
the shape item by using transparency loss as the mathematical owner and
preserving a derived score modifier only for diagnostics. The accepted formula
is now part of the canonical environment without a runtime switch.

The Home/Detail deep-sky pollution context keeps a user-facing note for
backward compatibility and also sets an internal target condition flag. The flag
is not exported to QML and is used only to prevent applying the same context
penalty twice during repeated refresh passes. Its score and note are display
compatibility data; the associated raw target remains the NSOM input.

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
selects up to four highest-valued unique targets and only then orders that
selection chronologically for display. No parallel legacy Planner formula
remains.

An observing window is an interval, not two candidate instants. If its best
time has passed but the current local time is still inside the interval, the
Planner schedules the target at the current minute. If the interval has not
started it uses its start; once it has ended it is no longer useful. The end of
a window is never presented as the next observing time.

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

Planner composition:

`E = geometric_visibility * lunar_sky_background * static_sky_background * atmospheric_transparency * horizon_context`

`O = intrinsic_target_quality * E`

`P = O * target_specific_observer_capability`

`Opportunity = P * observing_window_quality * chronology_fit * session_viability * practical_constraints`

Each component appears once. `SessionViability` is binary and does not multiply
the continuous weather contribution a second time. `RecommendationConfidence`
is attached as metadata and is not part of `Opportunity`.

The final plan contains up to four unique selected opportunities and schedules
items in roughly 45-minute increments from their useful time when no explicit
target time is available. Candidate identity is the canonical object ID; a
normalized-name guard also prevents aliases of the same display target from
occupying multiple plan rows.

## Best Object Selection

`BestObjectNsomSelectionService` ranks visible candidates by the same canonical
`ObservableTargetValue`, target-specific `ObserverCapability` and binary
Session viability used by the runtime NSOM path. A hard-blocked Session returns
no actionable Best Object.

For profiles with multiple instruments, Best Object receives the telescope
selected by `EquipmentService` for each target. It does not evaluate every
candidate with the first/current telescope; binocular and naked-eye targets
retain their non-telescope capability projection. Missing sky-quality data is
neutral in the canonical environment and does not switch selection service.

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

Filter recommendation boundary:

- `CatalogueObject` can define a primary filter class, one equivalent fallback
  class and one optional specific color class. Solar-System targets use the
  same three-field contract through local configuration.
- `FilterRecommendationService` runs only when the target-specific Equipment
  setup selects a real telescope. Binocular and naked-eye recommendations do
  not expose eyepiece filters.
- The selected telescope aperture is checked against both product
  `minimum_aperture_mm` and any target-specific class threshold. The complete
  catalogue determines whether a class is usable; only products assigned to
  the active profile can be reported as available.
- Class priority remains primary then fallback. Within one class, the product
  with the highest supported minimum-aperture threshold is preferred; name and
  ID are deterministic tie-breaks only after suitability checks.
- If no assigned product matches, the detail reports only the preferred usable
  class as `non disponibile`; it never invents an owned product or joins the
  primary and fallback labels.
- Primary and fallback are alternatives, not a request to stack filters. The
  optional color is presented separately because color-filter observing is a
  specialized choice.
- Yellow-filter detail on Uranus and Neptune is suppressed below `280 mm`, in
  line with the source guidance for 11-inch-class apertures.
- Filter format is intentionally not modeled. A product exists once in the
  catalogue even when sold in multiple barrel sizes.
- This logic is presentation-only. It does not alter Equipment setup selection,
  ObserverCapability, target score, Planner, Home ranking, Sky Compass or NSOM.

Photographic reducer recommendation boundary:

- `CatalogueObject.imaging_reducer_recommended` explicitly marks targets for
  which a reducer can be useful in astrophotography. It is independent of the
  target category and is not a score input.
- `ReducerRecommendationService` runs only when the flag is true and the
  target-specific Equipment recommendation identifies a telescope.
- A candidate must be `imaging_compatible` and have an exact normalized link to
  that telescope. Descriptive compatibility text is never parsed.
- Compatible reducers assigned to the active profile are reported as
  available. If none is owned, exact matches from the global catalogue are
  reported as `non disponibile`. Without an exact match, no reducer row is
  shown.
- Multiple exact matches are listed deterministically. NightScope does not
  invent a single best reducer without camera, sensor, image circle and
  backfocus context.
- This logic is presentation-only. Reduction factor, effective focal length,
  field of view and exposure are not recalculated. Reducers remain outside
  Equipment setup selection, ObserverCapability, target score, Planner, Home
  ranking, Sky Compass and NSOM.

Photographic optical-train foundation:

- `ImagingCameraAdapter` converts astronomy-camera and camera-body catalogue
  rows into one immutable `ImagingCamera` contract. Astronomy-camera
  full-resolution FPS and camera-body video FPS remain separate fields so the
  future scorer cannot compare unlike capture modes as if they were identical.
- `ImagingTrainBuilder` is target-agnostic. From only the telescopes, cameras,
  reducers and Barlows supplied by its caller it emits prime-focus trains,
  trains with one exact telescope-linked imaging reducer, and trains with one
  Barlow. It never stacks a reducer and Barlow in the same configuration.
- Reducer descriptive compatibility text is not parsed. A reducer participates
  only when `imaging_compatible` is true and the normalized telescope ID is in
  `compatible_telescope_ids`.
- For focal-length factor `k`, telescope focal length `F`, aperture `D`, pixel
  pitch `p` in micrometres and sensor dimension `s` in millimetres:

  - effective focal length: `F_eff = F * k`;
  - effective focal ratio: `f_ratio = F_eff / D`;
  - pixel scale: `206.264806247 * p / F_eff` arcsec/pixel;
  - field of view: `2 * atan(s / (2 * F_eff))`, converted to degrees.

- When both reducer and camera backfocus are known, the configuration exposes
  the remaining mechanical spacing as `reducer_backfocus - camera_backfocus`.
  This is a geometric value, not a claim that adapters, image circle or the
  rest of the mechanical train are compatible.
- The telescope mount code is carried unchanged into the configuration. The
  foundation assumes that the mount selected for the telescope reflects the
  user's real setup; it does not infer a different mount from model names.
- The optical-train builder itself has no target classification, score,
  capture-mode decision, exposure advice or presentation payload. It is not
  called by `AppController`, `EquipmentService`, Home, Object Detail, Planner,
  Sky Compass or NSOM.

Photographic target and static configuration scoring:

- `ImagingTargetTraitsAdapter` consumes only astronomical identity, type,
  magnitude, angular size and the curated reducer preference. It does not read
  visual compatibility score, altitude, current observability, Home ranking or
  NSOM values.
- Moon and planets select `video`; catalogue targets, comets and unknown
  non-solar targets select `still`. The Moon uses a `0.52°` whole-disc planning
  diameter when no runtime diameter is available. The Sun returns no
  candidates until a certified solar-filter capability can be represented.
- Catalogue major/minor axes are normalized to degrees. A canonical major axis
  remains authoritative while the textual dimensions preserve its aspect
  ratio. Framing accepts sensor rotation by 90°, keeps a 5% edge margin and
  prefers a target fill near 58% for still imaging or 68% for full-disc lunar
  video. Unknown dimensions use the neutral component value `0.5`.
- Every component is clamped to `[0, 1]`; weights sum to 100 and the score is
  additive:

  `score = sum(component_value * component_weight)`

  | Still component | Weight |
  | --- | ---: |
  | framing | 25 |
  | nominal sampling | 20 |
  | camera suitability | 20 |
  | photographic mount capability | 20 |
  | capture efficiency | 15 |

  | Video component | Weight |
  | --- | ---: |
  | critical sampling | 30 |
  | camera suitability | 25 |
  | frame acquisition | 25 |
  | framing/context field | 10 |
  | mount capability | 10 |

- Nominal still sampling targets 2.0 arcsec/pixel for known extended targets,
  1.4 for general targets, 1.0 for globular clusters, 0.9 for other compact
  targets and 0.75 for planetary nebulae or stellar targets. These are static
  equipment-comparison policies, not claims about current seeing.
- Planetary video starts from critical sampling
  `f_ratio = N * pixel_pitch_um / (1.22 * wavelength_um)`. With three samples
  across the diffraction feature and a nominal `0.5 µm` wavelength this is
  approximately `5 * pixel_pitch_um`. Whole-disc lunar video uses the more
  conservative `2.5 * pixel_pitch_um` planning policy, while its independent
  framing component strongly penalizes a cropped disc.
- Astronomy-camera full-resolution FPS and camera-body FPS at the declared
  video resolution use separate scoring curves. Cooling affects long-exposure
  still suitability, not short-frame video suitability. Body Bulb capability
  affects still suitability.
- The photographic mount map is independent from the compatibility-preserving
  visual tracking coefficient. Equatorial tracking is strongest for still
  imaging; alt-azimuth GoTo remains usable but is reduced because mount type
  alone cannot prove polar alignment or remove field rotation. Short video
  gives much less weight to mount type.
- A reducer with known negative remaining backfocus spacing is not rankable.
  Unknown spacing remains rankable but is reported as incomplete.
- `data_completeness` and `missing_inputs` are parallel metadata and have zero
  score effect. They explicitly report missing seeing, sky background,
  tracking accuracy, mechanical connection, image circle and any unavailable
  target, FPS or backfocus values.
- Scores are rounded to six decimals before deterministic ID tie-breaking.
  The service remains unregistered with runtime controllers and QML. It does
  not estimate sub-exposure or total integration time.

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

`LightPollutionService` resolves immediate sky quality using:

1. an exact or nearby cached NASA VIIRS Black Marble result,
2. an optional real preprocessed World Atlas/VIIRS local dataset,
3. unavailable (`None`) when neither source exists.

When Earthdata credentials are verified, the controller performs the NASA
VIIRS lookup asynchronously. A successful result replaces the immediate local
state and is persisted; a failed lookup leaves a real local dataset in place or
keeps sky quality unavailable.

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
- Cache freshness is evaluated before the Earthdata credential gate. If a
  stale real value exists but the account is not verified, Weather keeps the
  value and exposes an update warning instead of presenting it as current.
  Provider confidence remains the confidence of the stored measurement and is
  not reused as a freshness indicator.
- The Weather page `Aggiorna` command schedules this cache-aware check and does
  not force a network request while the VIIRS entry is fresh.
- `SkyQualityEstimate` is a VIIRS provider cache. Legacy seed, local-baseline
  and offline-estimate rows are deleted at service startup. Optional local CSV
  datasets are read directly and are not copied into this cache.
- Without sky-quality data, seeing uses atmospheric weather inputs only and
  light-pollution conditioning is omitted rather than assigned a neutral-looking
  Bortle number. Weather exposes Bortle, SQM and visual limit as `n/d`.

Known limitations:

- Optional local preprocessed datasets carry their own source and confidence;
  NightScope does not refresh those files automatically.
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
  decodes the packed `AOD_QA` bit field and accepts only cloud-mask `clear`,
  adjacency-mask `normal/clear` and best-quality AOD samples.
- It tries the exact pixel first, then a 5x5 neighborhood and finally an 11x11
  neighborhood. A neighborhood requires at least three quality-eligible pixels.
- The AOD value is the local median. The stored QA is an actual eligible pixel
  nearest to that median, never a numeric median of bit fields.
- The result stores AOD 550 nm, uncertainty when available, decoded-source raw
  QA, acquisition date, granule id, extraction method, valid-pixel count,
  neighborhood radius and nearest-valid-pixel distance.

Cache policy:

- Compact processed measurements and structured genuine no-data results are
  cached. A memory copy avoids repeated work inside the running process, while a
  small JSON cache allows app restarts to reuse recent results within their TTL.
- HDF/HDF5 granules are never cached.
- Cache keys use rounded latitude/longitude; the stored result preserves product,
  acquisition date and granule id.
- Positive measurements use an 18-hour TTL. `no_granules` and `no_valid_pixel`
  use a 6-hour negative TTL; authentication, search, download and parsing errors
  are not cached.
- Genuine no-data presentation summarizes the searched date range, products and
  granule count rather than exposing the final granule as if it represented the
  whole search.

Current limitations:

- Provider results are displayed in the Weather page and may influence
  canonical atmospheric-transparency scoring when provider-quality gates pass.
  Successful and failed lookups are
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
- seeing/transparency,
- equipment recommendations,
- NSOM category scores,
- best object,
- plan,
- Sky Compass,
- selected object detail refresh.

Seeing/transparency is computed once when weather or VIIRS sky quality changes.
Generic observing-output recomputation reuses that value, so profile, month and
AOD/OpenAQ refreshes do not repeat the same estimate.

Location changes trigger:

- a background astronomy snapshot containing night bounds, object geometry,
  Moon data, events and monthly catalogue visibility,
- weather refresh,
- sky-quality refresh,
- NASA AOD refresh when Earthdata credentials are verified,
- profile-dependent recommendation refresh.

VIIRS completion triggers:

- sky-quality update,
- background deep-sky reload,
- equipment recommendation refresh,
- deep-sky pollution context,
- observing outputs and selected detail refresh.

AOD/OpenAQ completion triggers:

- acceptance only for the still-current location and credentials;
- replacement of the provider input when its value changed;
- local recomputation of Home, Planner, Best Object and Sky Compass using the
  cached astronomy/Moon geometry;
- no repeated ephemeris calculation and no cumulative score subtraction.

Editable catalogue recommendation changes trigger:

- a persistent per-object preference update;
- local filtering of cached base deep-sky targets;
- Equipment, Home, Best Object, Planner and Sky Compass recomputation;
- no astronomy, weather or provider refresh.

Astronomy and VIIRS worker results carry both a monotonically increasing
request id and the active location key. Results produced for an older request
or location are discarded. The Qt thread keeps ownership of controller state,
signals, Equipment projections and Planner outputs.

## Known Limitations

- No local horizon mask is implemented.
- No atmospheric extinction model is implemented.
- No surface-brightness model for extended objects is implemented.
- Weather blocking thresholds are intentionally owned by
  `NightPlannerService.weather_blocking_status`.
- Seeing can remain high while observing quality is poor, because seeing and
  transparency/global weather are separate concepts.
- Sky-quality cache has no broad TTL policy.
