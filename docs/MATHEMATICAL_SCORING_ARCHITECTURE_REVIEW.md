# NightScope Mathematical Scoring Architecture Review

Status: design review, no production scoring changes.

Scope:

- describe the current scoring pipeline as one mathematical system;
- identify double-counting risks;
- define a coherent physical model for target observability;
- separate intrinsic target properties from the observation environment;
- separate the observer from both the target and the sky;
- separate target desirability from session viability;
- introduce recommendation confidence as a quality indicator, not as another
  score modifier;
- keep NASA AOD and OpenAQ score-neutral until explicit feature flags are
  enabled;
- keep equipment recommendation logic separate from target desirability.

This document is intentionally prescriptive for future milestones. It does not
describe an already enabled production model.

## Core Architectural Rules

NightScope's long-term scoring model should be based on physical phenomena, not
on an accumulating list of penalties.

Core rules:

1. One physical phenomenon has one owner.
2. One physical phenomenon has one mathematical meaning.
3. One physical phenomenon contributes once to a given target desirability
   score.
4. Different consumers may reuse the same computed result, but they must not
   recompute or independently reapply the same phenomenon.
5. The Universe, the Sky and the Observer are separate worlds.
6. Intrinsic target properties, observation environment and observer capability
   are separate inputs.
7. Target desirability and session viability are separate concepts.
8. Recommendation confidence is separate from recommendation score and runs in
   parallel with the whole model.

The preferred mental model is:

```text
The Universe
    -> Intrinsic Target

The Sky
    -> Observation Environment
    -> Effective Observability
    -> Observable Target Value

The Observer
    -> Observer Capability
    -> Practical Target Value

Session Viability
    -> Planner
    -> Presentation

Recommendation Confidence runs in parallel.
```

Implementation may still use internal deltas, caps or component factors, but
the architecture should describe what happens physically: how observable the
target is, not how many unrelated penalties are subtracted.

Recommended terminology:

- `Effective Observability`: the physical fraction of the target's intrinsic
  astronomical quality that is actually observable under the current sky.
- `Observable Target Value`: the resulting value available to Planner, Home and
  guidance surfaces after intrinsic target quality meets the observation
  environment. It is objective for the same target under the same sky.
- `Observer Capability`: how much of the observable target this specific
  observer can exploit.
- `Practical Target Value`: the value a specific observer can realistically use
  after objective observability meets observer capability.

This is intentionally stronger than "conditioned score". The goal is to model
the physical observation, not to modify an arbitrary score.

## The Three Worlds

NightScope's long-term mathematical model should keep three realities separate.

### A. The Universe

The Universe is everything that exists independently of the observer and the
local sky.

Examples:

- right ascension and declination;
- altitude and observing window from the active location;
- magnitude;
- angular size;
- object class;
- astronomical visibility.

This produces the intrinsic astronomical value of the target.

### B. The Sky

The Sky is everything between the observer and the target that changes how much
of the intrinsic target can be observed.

Examples:

- Moon sky background;
- static sky brightness;
- atmospheric transparency;
- aerosols;
- extinction;
- local horizon and future obstruction models.

This produces `EffectiveObservability` and objective `ObservableTargetValue`.
The target itself has not changed. The sky through which it is observed has
changed.

### C. The Observer

The Observer is everything that determines what this specific observer can
exploit.

Examples:

- telescope;
- binoculars;
- smart telescope or EAA system;
- filters;
- eyepieces and Barlows;
- seeing-limited magnification;
- future experience level;
- future personal preferences.

This produces `ObserverCapability` and `PracticalTargetValue`. Two observers
under the same sky can legitimately receive the same `ObservableTargetValue`
and different `PracticalTargetValue`.

## 1. Current Scoring Pipeline

NightScope currently has several partially overlapping scoring layers.

```text
SkyfieldAstronomyEngine raw objects
    -> AppController Home filtering and condition presentation
    -> ObservationConditionsService moon/light-pollution presentation context
    -> EquipmentService optical setup recommendation
    -> ObservingScoreService global observing score and best object
    -> SeeingTransparencyService seeing/transparency estimates
    -> AdvancedObservingService planetary/deep-sky category scores
    -> PlannerScoringService observing-plan ranking
    -> SkyCompassService broad direction ranking
    -> QML presentation
```

The architecture is workable, but it is not yet a single mathematical model.
The same physical phenomena can influence multiple downstream scores:

- Moon illumination affects global observing score, advanced scores, Home/Detail
  deep-sky conditioning and Planner penalties.
- VIIRS/Bortle affects transparency, advanced deep-sky score, Home/Detail
  deep-sky conditioning, Planner pollution penalty and equipment difficulty.
- Weather affects global observing score, advanced scores, Planner direct
  contribution, Planner weather factor and weather blocking.
- Seeing affects advanced planetary score and equipment magnification limits.
- Difficulty affects best-object selection, Planner ranking and UI labels.

Some overlap is intentional because one measurement can be used for separate
decisions. For example, seeing can constrain usable magnification even when it
does not meaningfully change the broad observability of a large galaxy. The
problem is not reuse of a measurement; the problem is independent recomputation
of the same physical effect inside the same mathematical decision.

## 2. Current Score Ownership

| Score or factor | Current owner | Physical meaning | Current consumers | Overlap risk |
| --- | --- | --- | --- | --- |
| Raw object score | `SkyfieldAstronomyEngine` | altitude, magnitude, object type, visibility | Home, Planner, Sky Compass, best object | Low |
| Global observing score | `ObservingScoreService` | weather plus Moon illumination | Home, best object, Planner, advanced scores | High: includes Moon and weather |
| Best object | `ObservingScoreService` | visible object score times weather/difficulty | Home | Medium: difficulty overlaps Planner |
| Seeing score | `SeeingTransparencyService` | atmospheric steadiness | Advanced scores, equipment | Medium but acceptable if separated by dimension |
| Transparency score | `SeeingTransparencyService` | cloud layers, humidity, visibility, VIIRS/Bortle | Advanced deep-sky score | High if AOD/PM are added elsewhere |
| Advanced planetary score | `AdvancedObservingService` | weather, seeing, wind, Moon | Planner category score, UI | High: weather and Moon already exist |
| Advanced deep-sky score | `AdvancedObservingService` | weather, transparency, VIIRS/Bortle, Moon | Planner category score, UI | High |
| Home/Detail Moon adjustment | `ObservationConditionsService` | object-specific Moon sensitivity | Home, Detail, Sky Compass candidates | Medium |
| Home/Detail pollution context | `ObservationConditionsService` | presentation/context adjustment for bright skies | Home, Detail, Sky Compass candidates | Medium |
| Planner score | `PlannerScoringService` | plan-specific aggregation | Night Planner | High: includes object, category, weather, Moon, pollution, difficulty |
| Equipment score | `EquipmentService` | current observer capability / optical suitability | Home, Detail, Planner setup | Acceptable if it feeds observer capability instead of target physics |
| Recommendation presentation | `RecommendationPresenter` | serialization and labels | QML | Low |
| Sky Compass score | `SkyCompassService` | direction grouping from prepared targets | Home | Low if it only consumes prepared targets |
| NASA AOD diagnostics | `ObservationConditionsService` | column aerosol proxy | diagnostics only | Low today, future risk |
| OpenAQ PM diagnostics | `ObservationConditionsService` | ground particulate proxy | diagnostics only | Low today, future risk |

## 3. Proposed Global Mathematical Flow

The recommended model is a layered physical model with explicit ownership.

```text
1. Intrinsic target model
2. Observation environment model
3. Effective observability
4. Observable target value
5. Observer capability
6. Practical target value
7. Session viability
8. Planner sequencing and practical ranking
9. Presentation

Recommendation confidence runs in parallel across these layers.
```

Final conceptual diagram:

```text
The Universe / Intrinsic Target
    altitude
    right ascension / declination
    magnitude
    angular size
    object type
    astronomical visibility

The Sky / Observation Environment
    Moon sky background
    static sky brightness
    atmospheric transparency
    future extinction
    future horizon effects

The Observer / Observer Capability
    telescope
    binoculars
    smart telescope
    eyepieces / Barlows / filters
    seeing-limited magnification
    future experience level
    future preferences

Intrinsic Target + Observation Environment
    -> Effective Observability
    -> Observable Target Value

Observable Target Value + Observer Capability
    -> Practical Target Value

Practical Target Value
    -> Session Viability
    -> Planner
    -> Presentation

Recommendation Confidence
    <- weather confidence
    <- AOD confidence
    <- OpenAQ confidence
    <- VIIRS confidence
    <- Moon-geometry confidence
    <- provider/fallback confidence
```

This order is intentional. Session viability should not modify the physics of the
target. Heavy rain does not make M31 intrinsically worse; it makes the observing
session poor or impossible. The Planner may later say:

```text
M31 is still the best target in the prepared set,
but tonight's session is not recommended.
```

This is cleaner than hiding session failure inside the target score.

The same separation applies to the observer. A small binocular profile does not
change M31's objective observable target value under a given sky. It changes
how much of that observable value this observer can exploit.

### 3.1 Intrinsic Target Model

Owner: `SkyfieldAstronomyEngine`.

Purpose: describe the target and its astronomical availability before the
observation environment is applied.

Inputs:

- altitude or maximum altitude;
- visibility threshold;
- magnitude;
- object type;
- optional angular size or surface-brightness metadata when available.

Output:

```text
IntrinsicTargetQuality A in [0, 100]
IntrinsicTargetBreakdown
```

This model should stay purely astronomical. It should not include weather,
Moon, VIIRS, AOD, PM, equipment, planner difficulty or provider confidence.

### 3.2 Observation Environment Model

Owner: `ObservationConditionsService`, fed by astronomy and data-provider
contexts.

Purpose: describe the physical environment through which the intrinsic target
is observed.

This explicitly separates two worlds:

```text
Intrinsic Target
    altitude
    magnitude
    angular size
    object type
    astronomical visibility

Observation Environment
    Moon sky background
    static sky brightness
    atmospheric transparency
    local/future extinction
    future horizon effects
```

These two worlds meet inside `ObservationConditionsService`. Other services may
provide inputs, but they should not independently reconstruct the same physical
observability calculation.

Environment components:

- Moon illumination and Moon-target geometry;
- sky background from VIIRS/Bortle and Moonlight;
- atmospheric transparency from aerosols, haze and future extinction models;
- future local horizon or obstruction effects;
- local conditions that physically change target observability.

Output:

```text
ObservationEnvironment
ObservationEnvironmentBreakdown
```

### 3.3 Effective Observability

Owner: `ObservationConditionsService`.

Purpose: model how much of the intrinsic target can actually be observed
through the current environment.

```text
EffectiveObservability E = combine(
    geometric_visibility,
    lunar_sky_background,
    static_sky_background,
    atmospheric_transparency,
    future_horizon_context
)
```

`E` is a physical observability factor in `[0, 1]`. It is not a list of
penalties. It answers:

```text
Given this target and this sky, how much of the target is observationally
available?
```

Hard impossibilities, such as "never reaches useful altitude", can still become
gates. But most effects should express reduced observability rather than a
standalone penalty list.

### 3.4 Observable Target Value

Owner: `ObservationConditionsService`.

Purpose: combine intrinsic target quality and effective observability.

Recommended future shape:

```text
ObservableTargetValue O = A * E
```

Where:

- `A` is intrinsic target quality;
- `E` is effective observability;
- `O` is the physical observational value available to downstream consumers;
- `O` does not include session viability or confidence.

Caps are still useful, but they should be described as maximum influence of a
physical component, not as the primary mental model. For example, the model may
limit how much aerosol opacity can affect planets, while still treating aerosol
as a transparency phenomenon.

### 3.5 Observer Capability

Owner: current implementation is mainly `EquipmentService`; long-term ownership
may become an `ObserverCapabilityService` that aggregates equipment, experience
and preferences.

Purpose: answer "given this observer, how much of the observable target can
actually be exploited?".

Inputs:

- target traits;
- active telescopes/binoculars/eyepieces/Barlows;
- filters;
- smart telescope or EAA capabilities;
- seeing as a magnification constraint;
- sky brightness and target surface brightness as setup-suitability context;
- future user experience level;
- future preferred observing style and personal constraints.

Output:

```text
ObserverCapability Q in [0, 1]
ObserverCapabilityBreakdown
EquipmentRecommendation
```

Equipment is only the first implemented part of observer capability. This layer
is fundamentally different from the sky. Two observers under the same sky can
obtain very different results from the same `ObservableTargetValue`.

Examples:

- binocular-only profile;
- Mak 127 with high-magnification eyepieces;
- smart telescope / EAA workflow;
- future manual vs GoTo distinction;
- future observer experience level;
- future object-type preferences;
- future fatigue, time budget or minimum acceptable quality.

None of these modify the Universe. None of these modify the Sky. They describe
the Observer.

### 3.6 Practical Target Value

Owner: long-term `PlannerScoringService` should consume it; the capability
component should come from `EquipmentService` or a future
`ObserverCapabilityService`.

Purpose: combine objective observable value with this observer's capability.

Recommended future shape:

```text
PracticalTargetValue P = O * Q
```

Where:

- `O` is objective observable target value under the current sky;
- `Q` is observer capability for this target;
- `P` is the practical value for this observer;
- `P` does not include session viability or confidence.

Planner should consume `PracticalTargetValue` because Planner answers:

```text
What should this observer observe first?
```

It does not answer:

```text
How observable is this target under the sky?
```

### 3.7 Seeing Position in the Model

Seeing should not be treated as a general effective-observability modifier.

Poor seeing does not make M31 or M44 intrinsically less observable in the same
way that moonlight or bright sky background does. Seeing primarily affects:

- usable magnification;
- sharp planetary detail;
- close double stars;
- small high-surface-brightness targets;
- small planetary nebulae when high magnification is needed.

Recommended ownership:

- `EquipmentService` owns seeing-limited magnification and setup choice.
- `ObservationConditionsService` may own a small effective-observability component
  only for seeing-sensitive classes.
- broad deep-sky targets should usually receive no direct seeing modifier.

This keeps seeing physically meaningful and avoids reducing large targets for a
phenomenon that mainly affects resolution.

### 3.8 Session Viability

Owner: `ObservingScoreService`, with future cleanup.

Purpose: answer "is the observing session viable?".

Inputs:

- cloud cover;
- precipitation;
- wind;
- humidity;
- optionally forecast confidence.

Recommended future correction:

- remove target-specific Moon meaning from session quality;
- keep Moon in effective observability;
- keep cloud/rain as session viability or hard session state;
- avoid feeding the same weather score into Planner multiple times.

Output:

```text
SessionViability S in [0, 1]
SessionState in {recommended, monitor, discouraged}
```

`S` should be carried alongside target scores. It may block or annotate a plan,
but it should not rewrite effective observability. This lets NightScope explain:

```text
Target recommendation: M31
Session viability: poor due to rain
Confidence: high/low depending on data freshness
```

### 3.9 Recommendation Confidence

Owner: each subsystem owns its own confidence contribution; a later aggregator
combines them into overall recommendation confidence.

Confidence is not another penalty and should not be mixed into target score.
It measures how reliable the recommendation is, given the data quality.

Examples:

```text
Recommendation score: 81
Confidence: 98%

Recommendation score: 81
Confidence: 43%
```

Possible confidence inputs:

- weather forecast freshness;
- forecast provider quality;
- NASA AOD freshness;
- OpenAQ freshness;
- VIIRS age or fallback status;
- missing Moon geometry;
- missing visibility data;
- fallback astronomy/provider paths.

Recommended output:

```text
RecommendationConfidence K in [0, 1]
ConfidenceBreakdown
```

`K` is a parallel quality dimension. Each physical subsystem can contribute:

```text
Weather -> confidence
NASA AOD -> confidence
OpenAQ -> confidence
VIIRS -> confidence
Moon geometry -> confidence
Fallback astronomy/provider paths -> confidence
```

The final recommendation can therefore be:

```text
Recommendation: 81
Confidence: 98%

Recommendation: 81
Confidence: 41%
```

The score is independent. Confidence should primarily affect presentation,
caution text and user trust, not the physical target value.

### 3.10 Planner Ranking

Owner: `PlannerScoringService`.

Purpose: answer "what should I observe, and in what order?".

Planner should combine:

- practical target value;
- useful observing window quality;
- chronology;
- session viability as block/cap/context, not as target physics;
- confidence as presentation/caution, not as a hidden score penalty;
- practical difficulty;
- observing-window practicality.

Planner should not reapply Moon, light pollution, AOD or PM if those have
already been applied by `ObservationConditionsService`.

Recommended future shape:

```text
TargetPlanValue =
    P * target_weight
    + WindowQuality * window_weight
    + Practicality * practicality_weight

PlannerOutput =
    select/order targets by TargetPlanValue
    annotate with SessionViability S
    annotate with RecommendationConfidence K
```

If session viability is very poor, Planner may block or downgrade the session
state, but the target's observable value remains interpretable.

Chronological display should remain a presentation step after target selection.

Planner should consume `PracticalTargetValue`; it should not reconstruct Moon,
sky brightness, AOD, PM, transparency or observer capability itself. Planner
answers:

```text
What should I observe first?
```

It should not answer:

```text
How observable is this object under the current sky?
```

That belongs to `ObservationConditionsService`.

Observer capability belongs to `EquipmentService` today and to a future
observer-capability layer if NightScope adds experience level, smart telescope
automation, preferences or other personalization.

### 3.11 Presentation

Owners: `RecommendationPresenter`, QML.

Presentation should render already computed values. It should not decide target
rank, apply score modifiers or infer equipment recommendations from object
strings.

## 4. Factor Classification

| Factor | Correct class | Recommended owner | Future mathematical role |
| --- | --- | --- | --- |
| Altitude / window | astronomical | astronomy engine / Planner | gate and raw score |
| Magnitude / size | astronomical | astronomy engine / target traits | raw score and equipment traits |
| Cloud cover | session viability / sky access | observing/session service | session state, block or viability factor |
| Precipitation | session viability | observing/session service | hard block or session viability |
| Wind | session viability / seeing proxy | session and seeing services | session practicality; seeing input |
| Humidity / dew gap | transparency proxy | effective-observability context or session context, but not both | haze/dew confidence and transparency context |
| Forecast visibility | transparency proxy | effective-observability context | atmospheric transparency component |
| Seeing | resolution stability | observer capability; target conditions only for seeing-sensitive classes | magnification constraint; limited effective-observability component |
| VIIRS/Bortle | static sky background | conditions service | effective-observability component |
| NASA AOD | atmospheric column aerosol | conditions service | target transparency component, feature-flagged |
| OpenAQ PM2.5/PM10 | ground particulate proxy | conditions service | fallback/correction to transparency, feature-flagged |
| Moon illumination | dynamic sky background | conditions service | effective-observability component |
| Moon altitude/separation | dynamic sky background geometry | conditions service | effective-observability component |
| Equipment capability | observer-related | equipment service / future observer capability service | current observer capability component |
| Experience level | observer-related | future observer capability service | future observer capability component |
| Observing style/preferences | observer-related | future observer capability service | future personalization component |
| Difficulty | observer/planner-related | planner scoring / presenter | practicality, not raw object score |
| Planner chronology | planner-related | planner service | display order after selection |
| Sky Compass direction | presentation/guidance | sky compass service | direction grouping, not new target scoring |
| Provider freshness | confidence | source owner plus conditions/session DTOs | confidence, not score |

## 5. Double-Counting Audit

### 5.1 Moon

Current duplication:

- global observing score subtracts Moon illumination;
- advanced planetary/deep-sky scores include Moon;
- Home/Detail applies object-specific Moon adjustment;
- Planner subtracts Moon penalty.

Recommended target state:

- Moon belongs to `ObservationConditionsService`;
- Moon contributes once to effective observability through sky-background geometry;
- global weather/session viability should not include target-specific Moon
  damage;
- Planner should consume effective observability or the Moon breakdown, not
  independently recalculate Moon impact;
- advanced scores should either become diagnostic labels or consume the same
  Moon component without adding a second target modification.

### 5.2 Light Pollution / VIIRS / Bortle

Current duplication:

- transparency score includes sky-quality penalty;
- advanced deep-sky score includes light-pollution quality;
- Home/Detail applies deep-sky pollution context;
- Planner applies a Planner-specific pollution penalty;
- equipment and difficulty use Bortle context.

Recommended target state:

- effective observability gets one static sky-background component from
  `ObservationConditionsService`;
- equipment may still use Bortle to choose a setup, because this is a different
  decision dimension;
- Planner should not apply a second sky-background modification if it consumes
  condition-adjusted targets.

### 5.3 Weather / Cloud / Humidity / Visibility

Current duplication:

- weather score includes cloud, rain, wind, humidity;
- seeing/transparency includes wind, clouds, humidity and visibility;
- advanced scores include weather and transparency;
- Planner includes category score, direct weather contribution and weather
  factor.

Recommended target state:

- severe cloud/rain is session viability, not target identity;
- clouds may block sky access at the session level;
- humidity and forecast visibility may contribute to atmospheric transparency,
  but should not also be applied as independent session-score damage inside the
  same Planner target value;
- Planner should consume one session viability result and one effective-observability
  result.

### 5.4 Seeing

Current use:

- advanced planetary score;
- equipment magnification cap.

This overlap is acceptable if kept dimensionally separate:

- seeing may affect effective observability only for seeing-sensitive targets;
- the same seeing measurement may constrain magnification recommendation;
- it should not be added again inside Planner after target conditions.

### 5.5 Observer Capability, Equipment and Difficulty

Current duplication:

- difficulty affects best-object selection and Planner ranking;
- equipment uses target difficulty context for setup suitability.

Recommended target state:

- observer capability remains independent from the Universe and the Sky;
- equipment is the currently implemented part of observer capability;
- future observer experience, preferred observing style, smart telescope
  automation and personal constraints belong here, not in
  `ObservationConditionsService`;
- difficulty belongs to observer practicality and Planner presentation;
- Planner should consume `PracticalTargetValue`, not mix observer capability
  back into Moon, sky background or atmospheric transparency.

## 6. Atmospheric Transparency Model

The cleanest model is a single provider-independent atmospheric context consumed
by `ObservationConditionsService` as part of `EffectiveObservability`.

```text
AtmosphericContext
    sky_access               from forecast cloud/rain session state
    humidity_haze            from humidity/dew/visibility
    aerosol_column           from NASA AOD
    particulate_ground       from OpenAQ PM2.5/PM10
    light_pollution          from VIIRS/Bortle
    freshness/confidence     per source
```

Recommended separation:

- `light_pollution` is sky-background brightness, not transparency.
- `aerosol_column` is extinction/scattering through the atmospheric column.
- `particulate_ground` is a weaker ground-level proxy.
- cloud cover and precipitation primarily describe session sky access.
- humidity/visibility can be part of transparency, but must not be counted
  again as full session-score damage inside the same Planner target value.

Long-term output:

```text
AtmosphericTransparency T in [0, 1]
AtmosphericConfidence K_atmosphere in [0, 1]
```

`T` describes how transparent the air is for target observability. `K` describes
how reliable that estimate is. A historical AOD value should reduce confidence
or be ignored; it should not pretend to describe tonight's atmosphere.

### 6.1 AOD vs PM

Recommended policy:

- AOD is primary when fresh enough because it measures the column more relevant
  to astronomical transparency.
- PM is fallback when AOD is missing, stale or invalid.
- If both exist, PM may add at most a small confidence-qualified correction, not
  a second full atmospheric contribution.
- PM should never dominate AOD.
- Both must be freshness-weighted.

Freshness weights:

| Source | Age | Weight |
| --- | ---: | ---: |
| NASA AOD | 0-3 days | 1.0 |
| NASA AOD | 4-7 days | 0.5 |
| NASA AOD | > 7 days | 0.0 |
| OpenAQ PM | 0-24 h | 1.0 |
| OpenAQ PM | 24-72 h | 0.7 |
| OpenAQ PM | 3-7 days | 0.3 |
| OpenAQ PM | > 7 days | 0.0 |

### 6.2 Aerosol Visibility Shape

Recommended future scoring shape:

```text
AOD_severity =
    0.0 if AOD <= 0.10
    0.25 if AOD <= 0.20
    0.50 if AOD <= 0.35
    0.75 if AOD <= 0.60
    1.00 if AOD > 0.60

PM_severity = worst(PM2.5_severity, PM10_severity)

if fresh_AOD:
    aerosol_severity = AOD_severity
    pm_correction = min(0.20, PM_severity * 0.20) if fresh_PM else 0
else:
    aerosol_severity = PM_severity * 0.60

AtmosphericTransparency =
    1 - min(type_aerosol_max_influence,
            type_sensitivity * aerosol_severity * freshness_weight)
```

This keeps PM weaker than AOD and prevents AOD+PM double-counting. Internally,
the implementation may store a delta for compatibility, but the mathematical
meaning is a transparency factor inside `EffectiveObservability`.

## 7. Moon Model

The current Moon model is useful but incomplete. It mainly uses illumination and
target type. The future model should add cheap geometry.

Recommended future formula:

```text
MoonSkyBackgroundEffect =
    MoonSensitivity(target)
    * MoonIlluminationFactor
    * MoonAltitudeFactor
    * MoonSeparationFactor
    * MoonWindowFactor

MoonVisibility =
    1 - min(target_moon_max_influence, MoonSkyBackgroundEffect)
```

Where:

```text
MoonIlluminationFactor = clamp((illumination - 25) / 75, 0, 1)

MoonAltitudeFactor:
    Moon below horizon or not visible in target window -> 0.0
    0-10 deg -> 0.25
    10-30 deg -> 0.60
    > 30 deg -> 1.00

MoonSeparationFactor:
    < 20 deg -> 1.35
    20-45 deg -> 1.00
    45-90 deg -> 0.65
    > 90 deg -> 0.35

MoonWindowFactor:
    Moon set before target window -> 0.0
    Moon rises after target window -> 0.0
    Moon partly overlaps -> 0.5
    Moon overlaps main observing time -> 1.0
```

`MoonVisibility` is one component of `EffectiveObservability`. It should not
also appear inside global session viability or Planner as a second independent
operation.

Sampling strategy:

- do not sample minute-by-minute;
- sample target window start, midpoint, best-time sample and end;
- use the worst meaningful Moon geometry sample or a weighted midpoint;
- cache Moon alt/az samples per location/date/time bucket.

This model should first be diagnostic-only, then enabled behind a feature flag
for Planner only.

## 8. Recommended Caps and Sensitivity Matrix

Caps protect recommendations from one measured phenomenon dominating the whole
model. They are not the core concept; they are guardrails around physical
components.

The table below expresses maximum influence on effective observability. If the
implementation stores these as score deltas for compatibility, the diagnostic
language should still describe them as visibility components.

| Target class | AOD sensitivity | PM role | Max AOD/PM influence | Max Moon influence | Max sky-background influence | Max total visibility influence |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Moon | very low | none | 1 | 0 | 0 | 5 |
| Planets | low | none/minor | 3 | 0 | 0 | 18 |
| Globular clusters | medium-low | low fallback | 4 | 18 | 18 | 35 |
| Open clusters | medium-low | low/medium fallback | 3 | 10 | 12 | 25 |
| Planetary nebulae | medium | medium fallback | 5 | 18 | 22 | 38 |
| Diffuse nebulae | high | medium-high fallback | 8 | 35 | 30 | 55 |
| Galaxies | very high | high fallback | 12 | 40 | 35 | 60 |

Global caps:

- session viability is handled separately and does not change target physics;
- combined aerosol/PM influence should not exceed the target-class cap;
- combined sky-background influence from Moon plus VIIRS/Bortle should be
  bounded;
- total effective-observability influence is target-class dependent, never above 60%;
- planets should be protected from excessive transparency influence and instead
  be primarily affected by seeing and altitude.

## 9. Worked Examples

These examples use the proposed future model, not current production scoring.
They are illustrative and should become tests before enablement.

Assumed session:

- session viability `S = 0.85`;
- Bortle/VIIRS produces moderate sky-background degradation;
- AOD is fresh and moderate;
- PM exists but is treated only as minor correction because AOD exists;
- Moon illumination is 70%.

### 9.1 M31, galaxy

```text
Raw astronomical score A = 82

Geometric/useful visibility = 1.00
Moon visibility component = 0.78
Static sky-background component = 0.86
Atmospheric transparency component = 0.95

EffectiveObservability E = 1.00 * 0.78 * 0.86 * 0.95 = 0.64
ObservableTargetValue O = 82 * 0.64 = 52.5

ObserverCapability Q = 0.82 for the active profile
PracticalTargetValue P = 52.5 * 0.82 = 43.1

Session viability S = 0.85
Recommendation confidence K = 0.92
```

Interpretation: M31 remains intrinsically attractive, but the target is less
observable under bright sky background and moderate aerosol transparency.
`O` is objective for the same sky. `P` depends on this observer's profile.
Session viability is separate and should be shown as session context, not mixed
into the target physics or observer capability.

### 9.2 Saturn, planet

```text
Raw astronomical score A = 88

Geometric/useful visibility = 1.00
Moon visibility component = 1.00
Static sky-background component = 1.00
Atmospheric transparency component = 0.99
Seeing-sensitive detail component = 0.90

EffectiveObservability E = 1.00 * 1.00 * 1.00 * 0.99 * 0.90 = 0.89
ObservableTargetValue O = 88 * 0.89 = 78.3

ObserverCapability Q = 0.90 for a telescope profile with useful magnification
PracticalTargetValue P = 78.3 * 0.90 = 70.5

Session viability S = 0.85
Recommendation confidence K = 0.92
```

Interpretation: Moon and light pollution do not materially affect Saturn.
Seeing matters because Saturn is detail-sensitive; the same seeing measurement
also constrains the eyepiece choice inside `EquipmentService`.

### 9.3 M13, globular cluster

```text
Raw astronomical score A = 78

Geometric/useful visibility = 1.00
Moon visibility component = 0.91
Static sky-background component = 0.93
Atmospheric transparency component = 0.98

EffectiveObservability E = 1.00 * 0.91 * 0.93 * 0.98 = 0.83
ObservableTargetValue O = 78 * 0.83 = 64.7

ObserverCapability Q = 0.88
PracticalTargetValue P = 64.7 * 0.88 = 56.9

Session viability S = 0.85
Recommendation confidence K = 0.92
```

Interpretation: globular clusters degrade under poor sky, but less severely
than galaxies and diffuse nebulae.

### 9.4 M42, diffuse nebula

```text
Raw astronomical score A = 84

Geometric/useful visibility = 1.00
Moon visibility component = 0.76
Static sky-background component = 0.82
Atmospheric transparency component = 0.93

EffectiveObservability E = 1.00 * 0.76 * 0.82 * 0.93 = 0.58
ObservableTargetValue O = 84 * 0.58 = 48.7

ObserverCapability Q = 0.75 without a suitable filter / EAA aid
PracticalTargetValue P = 48.7 * 0.75 = 36.5

Session viability S = 0.85
Recommendation confidence K = 0.92
```

Interpretation: diffuse nebulae should be strongly affected by Moon, sky
brightness and aerosol scattering.

### 9.5 Moon

```text
Raw astronomical score A = 95

Geometric/useful visibility = 1.00
Moon visibility component = 1.00
Static sky-background component = 1.00
Atmospheric transparency component = 1.00

EffectiveObservability E = 1.00
ObservableTargetValue O = 95

ObserverCapability Q = 0.95
PracticalTargetValue P = 90.3

Session viability S = 0.85
Recommendation confidence K = 0.92
```

Interpretation: the Moon is mainly limited by cloud/session state and seeing,
not by sky brightness or aerosol transparency components.

### 9.6 Same M31, heavy rain

```text
Raw astronomical score A = 82
EffectiveObservability E = 0.64
ObservableTargetValue O = 52.5

ObserverCapability Q = 0.82
PracticalTargetValue P = 43.1

Session viability S = 0.05
Session state = discouraged
Recommendation confidence K = 0.95
```

Interpretation: M31 did not become physically worse, and this observer's
capability did not change. The session became unusable. Planner should be able
to explain: "M31 remains the strongest practical target, but tonight is not a
good observing session."

## 10. ObservationConditionsService Boundaries

`ObservationConditionsService` should model physical observing phenomena, not
conceptual "penalties". It owns the place where intrinsic target properties meet
the observation environment and become `EffectiveObservability` and
`ObservableTargetValue`.

For backward compatibility, an implementation may temporarily store deltas,
score adjustments or caps. Those are implementation details. The architectural
meaning remains physical:

```text
Moon sky background
Static sky brightness
Atmospheric transparency
Future extinction
Future horizon effects
```

`ObservationConditionsService` should own:

- Moon illumination and Moon geometry visibility components;
- light-pollution visibility components from VIIRS/Bortle;
- future AOD/PM residual transparency components;
- target sensitivity profiles;
- freshness-weighted diagnostic breakdowns;
- target-condition confidence for the phenomena it owns;
- double-counting flags for applied condition components.

It should not own:

- raw astronomical score generation;
- observer capability;
- practical target value;
- weather data download;
- global weather blocking;
- full session viability;
- full recommendation confidence aggregation across unrelated providers;
- equipment candidate scoring;
- optical setup selection;
- Planner chronology;
- Sky Compass direction ranking;
- UI presentation strings beyond diagnostic identifiers.

`PlannerScoringService` should own:

- how practical target value is combined with observing-window quality;
- chronology-aware plan selection;
- difficulty/practicality factor;
- session viability application as block/context, not target mutation;
- confidence pass-through or Planner-level confidence aggregation;
- final Planner diagnostics.

`EquipmentService` should own:

- magnification, exit pupil, field of view and limiting magnitude suitability;
- seeing-limited magnification;
- active-profile setup choice;
- the current equipment-based part of observer capability.

A future `ObserverCapabilityService` should own:

- aggregation of equipment capability;
- experience level;
- observing style;
- manual vs GoTo / smart telescope automation;
- personal preferences and constraints;
- practical target value before Planner ranking.

## 11. Recommended Migration Roadmap

### Step 1: Mathematical constants and test fixtures

- Define target classes, sensitivity profiles, visibility components and caps in
  tests first.
- Define `ObserverCapability` and `PracticalTargetValue` fixtures as separate
  from `ObservableTargetValue`.
- Define `RecommendationConfidence` fixtures as score-neutral metadata.
- Keep production scoring unchanged.
- Add explicit "phenomenon ownership" tests where possible.

### Step 2: Diagnostic completeness

- Ensure every condition breakdown can report Moon, light pollution, AOD, PM,
  weather placeholder, seeing placeholder, transparency placeholder and feature
  flags.
- Keep modifiers neutral.
- Ensure confidence inputs are present as diagnostics and never change score.

### Step 3: Planner-only experimental flag

- Add feature-flagged Planner path:
  - default off;
  - consumes practical target value, session viability and confidence
    separately;
  - does not change Home, Detail, Best Object or Sky Compass.

### Step 4: AOD/PM experimental modifiers

- Enable aerosol residual only behind `experimental_aerosol_scoring`.
- AOD primary, PM fallback/correction.
- Verify no AOD/PM contribution enters transparency score or advanced score at
  the same time.

### Step 5: Moon geometry diagnostics

- Compute Moon altitude/separation at start/mid/best/end samples.
- Keep diagnostic-only until stable.

### Step 6: Moon-aware Planner scoring

- Enable Moon geometry behind `experimental_moon_geometry_scoring`.
- Planner first, Home later.

### Step 7: Advanced score cleanup

- Decide whether `AdvancedObservingService` remains a user-facing diagnostic
  score or becomes a consumer of the same condition components.
- Remove or neutralize duplicated Moon/light-pollution/weather terms before
  production enablement.
- Ensure session viability and effective observability remain separate outputs.

### Step 8: Home and Best Object integration

- Only after Planner equivalence is proven, move Home/Best Object to the same
  observable/practical target value split.
- Keep Sky Compass consuming prepared targets only.
- Expose recommendation confidence only after scores and labels remain stable.

### Step 9: Observer capability expansion

- Keep equipment as the first observer-capability implementation.
- Add experience level, observing style, smart telescope/EAA support and
  preferences only after the physics model is stable.
- Verify no observer-specific factor enters `ObservationConditionsService`.

## 12. Tests Required Before Enablement

### Characterization tests

- Current Planner output unchanged with flags off.
- Current Home/Detail output unchanged with flags off.
- Current Best Object unchanged with flags off.
- Current equipment recommendations unchanged with flags off.
- Observable target value remains identical for two observers under the same sky.
- Practical target value can differ for two observers under the same sky.
- Sky Compass live refresh still does not call scoring or heavy refresh paths.

### Atmospheric tests

- AOD freshness weights: 0-3 days, 4-7 days, >7 days.
- OpenAQ freshness weights: 0-24 h, 24-72 h, 3-7 days, >7 days.
- AOD dominates PM when both are fresh.
- PM acts only as fallback or small correction.
- PM is ignored when AOD exists and correction cap is reached.
- AOD/PM influence caps per target type.
- AOD/PM modifiers remain zero with feature flag off.
- AOD/PM do not feed transparency, weather, Planner and target score
  simultaneously.
- AOD/PM freshness can lower confidence without lowering score when scoring is
  disabled.

### Moon tests

- Moon below horizon reduces or eliminates the Moon visibility effect.
- Moon high above horizon applies the normal illumination effect.
- Moon close to target increases the Moon sky-background effect.
- Moon far from target reduces the Moon sky-background effect.
- Moon set before target window is neutral.
- Galaxies and diffuse nebulae remain more sensitive than clusters.
- Planets, Moon and Sun remain neutral for Moon sky-brightness influence.

### Double-counting tests

- A target cannot have `moon` applied twice in the same final score.
- A target cannot have `light_pollution` applied twice in the same final score.
- AOD and PM cannot both contribute full independent atmospheric influences.
- Weather cannot be applied as direct contribution, category contribution and
  final factor in a new scoring path.
- Equipment score cannot silently become target desirability.
- Session viability cannot mutate observable target value.
- Low confidence cannot silently reduce target score.
- Observer capability cannot mutate intrinsic target quality or effective
  observability.
- Planner cannot reconstruct observer capability after consuming practical
  target value.

### Confidence tests

- Fresh weather, AOD, OpenAQ and VIIRS produce high confidence.
- Missing optional providers reduce confidence but do not change score.
- Historical AOD is ignored or lowers confidence, never presented as current.
- Historical OpenAQ is omitted or lowers confidence, never presented as current.
- Fallback sky-quality or astronomy paths are visible in confidence diagnostics.
- Same recommendation score with different confidence remains possible and
  explainable.

### Performance tests

- Moon geometry sampling uses bounded samples, not minute-by-minute loops.
- AOD/PM diagnostics do not trigger network refreshes from scoring.
- Sky Compass live refresh stays position-only.

## 13. Recommendation

Do not enable AOD/OpenAQ scoring in production yet.

The safe next step is:

1. keep feature flags default off;
2. formalize `EffectiveObservability`, `ObservableTargetValue`,
   `ObserverCapability`, `PracticalTargetValue`, `SessionViability` and
   `RecommendationConfidence` as separate mathematical concepts;
3. add formal mathematical constants and regression fixtures;
4. implement Planner-only experimental scoring behind a flag;
5. compare output against current Planner for many scenarios;
6. only then decide whether the new model should replace the current layered
   scores.

This preserves NightScope's current stable behavior while moving toward a
single explainable mathematical system where each physical phenomenon has one
owner and one role. The Universe defines the intrinsic target. The Sky defines
effective observability and objective observable target value. The Observer
defines practical target value. Session viability describes whether tonight is
usable, and confidence describes how much trust NightScope has in the data
behind the recommendation.
