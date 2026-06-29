# NightScope Mathematical Scoring Architecture Review

Status: design review, no production scoring changes.

Scope:

- describe the current scoring pipeline as one mathematical system;
- identify double-counting risks;
- define a coherent target model for future scoring;
- keep NASA AOD and OpenAQ score-neutral until explicit feature flags are
  enabled;
- keep equipment recommendation logic separate from target desirability.

This document is intentionally prescriptive for future milestones. It does not
describe an already enabled production model.

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
decisions. For example, seeing may affect both target desirability and maximum
usable magnification. The key rule for future work is:

> The same physical phenomenon may feed separate decision dimensions, but it
> must not be added more than once to the same final desirability score.

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
| Home/Detail pollution context | `ObservationConditionsService` | presentation/context penalty for bright skies | Home, Detail, Sky Compass candidates | Medium |
| Planner score | `PlannerScoringService` | plan-specific aggregation | Night Planner | High: includes object, category, weather, Moon, pollution, difficulty |
| Equipment score | `EquipmentService` | optical suitability | Home, Detail, Planner setup | Acceptable if not reused as target desirability |
| Recommendation presentation | `RecommendationPresenter` | serialization and labels | QML | Low |
| Sky Compass score | `SkyCompassService` | direction grouping from prepared targets | Home | Low if it only consumes prepared targets |
| NASA AOD diagnostics | `ObservationConditionsService` | column aerosol proxy | diagnostics only | Low today, future risk |
| OpenAQ PM diagnostics | `ObservationConditionsService` | ground particulate proxy | diagnostics only | Low today, future risk |

## 3. Proposed Global Mathematical Flow

The recommended model is a layered pipeline with explicit ownership.

```text
1. Raw astronomical target quality
2. Hard observability gates
3. Global session quality
4. Target-specific observing conditions
5. Equipment suitability
6. Planner sequencing and practical ranking
7. Presentation
```

### 3.1 Raw Astronomical Target Quality

Owner: `SkyfieldAstronomyEngine`.

Purpose: describe the target independent of weather, Moon, equipment and
provider quality.

Inputs:

- altitude or maximum altitude;
- visibility threshold;
- magnitude;
- object type;
- optional angular size or surface-brightness metadata when available.

Output:

```text
RawTargetScore A in [0, 100]
```

This score should stay purely astronomical. It should not include weather,
Moon, VIIRS, AOD, PM, equipment or planner difficulty.

### 3.2 Hard Observability Gates

Owner: astronomy layer plus Planner orchestration.

Examples:

- target never reaches the minimum useful altitude;
- target has no useful window;
- weather is globally blocking;
- solar-system monthly visibility excludes the object from Home eligibility.

Output:

```text
Gate G in {0, 1}
```

Hard gates decide whether an object can be considered. They should not be
implemented as large numeric penalties that can be accidentally offset by other
bonuses.

### 3.3 Global Session Quality

Owner: `ObservingScoreService`, with future cleanup.

Purpose: answer "is tonight generally usable?".

Inputs:

- cloud cover;
- precipitation;
- wind;
- humidity;
- optionally forecast confidence.

Recommended future correction:

- remove target-specific Moon meaning from this score;
- keep Moon as a separate target-specific condition.

Output:

```text
SessionQuality W in [0, 1]
SessionState in {recommended, monitor, discouraged}
```

`W` may cap or scale plan usefulness, but it should not be mixed repeatedly as
direct contribution, category score input and final factor.

### 3.4 Target-Specific Observing Conditions

Owner: `ObservationConditionsService`.

Purpose: transform raw target score into a condition-adjusted target score.

Inputs:

- raw target score;
- target type and sensitivity profile;
- Moon illumination and geometry;
- light-pollution context;
- aerosol/particulate diagnostics when enabled later;
- seeing only if used as a target desirability condition, not as equipment
  selection.

Recommended future formula:

```text
P_conditions = min(
    target_total_condition_cap,
    P_moon_geometry
    + P_sky_background
    + P_aerosol_residual
    + P_seeing_target
)

ConditionedTargetScore C = clamp(A - P_conditions, 0, 100)
```

Important:

- AOD and PM must enter only through one atmospheric residual term.
- VIIRS/Bortle must enter only through one light-pollution term.
- Moon must enter only through one Moon term.

### 3.5 Equipment Suitability

Owner: `EquipmentService`.

Purpose: answer "how should I observe this target with my profile?".

Inputs:

- target traits;
- active telescopes/binoculars/eyepieces/Barlows;
- seeing as a magnification constraint;
- sky quality as a setup suitability constraint.

Output:

```text
EquipmentRecommendation
EquipmentSuitabilityDiagnostic
```

Recommendation:

- keep equipment scoring out of target desirability;
- allow equipment constraints to explain setup choice;
- avoid using equipment score as another target score unless a future feature
  explicitly asks for "best target for my profile".

### 3.6 Planner Ranking

Owner: `PlannerScoringService`.

Purpose: answer "what should I observe, and in what order?".

Planner should combine:

- condition-adjusted target score;
- useful observing window quality;
- chronology;
- session state/cap;
- practical difficulty;
- optional active-profile capability.

Planner should not reapply Moon, light pollution, AOD or PM if those have
already been applied by `ObservationConditionsService`.

Recommended future shape:

```text
PlannerScore =
    G
    * SessionCap(W)
    * (
        C * target_weight
        + WindowQuality * window_weight
        + Practicality * practicality_weight
        + Capability * capability_weight
    )
```

Chronological display should remain a presentation step after target selection.

### 3.7 Presentation

Owners: `RecommendationPresenter`, QML.

Presentation should render already computed values. It should not decide target
rank, apply penalties or infer equipment recommendations from object strings.

## 4. Factor Classification

| Factor | Correct class | Recommended owner | Future mathematical role |
| --- | --- | --- | --- |
| Altitude / window | astronomical | astronomy engine / Planner | gate and raw score |
| Magnitude / size | astronomical | astronomy engine / target traits | raw score and equipment traits |
| Cloud cover | atmospheric global | observing/session service | session factor/cap |
| Precipitation | atmospheric global | observing/session service | hard block or session cap |
| Wind | atmospheric global / seeing proxy | session and seeing services | session factor; seeing input |
| Humidity / dew gap | atmospheric global / transparency proxy | session and transparency services | session or transparency context, not both in final score |
| Forecast visibility | transparency proxy | transparency context | transparency residual |
| Seeing | atmospheric target/equipment | conditions and equipment | target penalty for planets; equipment magnification cap |
| VIIRS/Bortle | sky background | conditions service | light-pollution penalty |
| NASA AOD | atmospheric column aerosol | conditions service | aerosol residual, feature-flagged |
| OpenAQ PM2.5/PM10 | ground particulate proxy | conditions service | fallback/correction, feature-flagged |
| Moon illumination | sky background | conditions service | Moon penalty primitive |
| Moon altitude/separation | sky background geometry | conditions service | Moon geometry multiplier |
| Equipment capability | equipment-related | equipment service | setup selection; optional Planner capability only |
| Difficulty | observational/planner | planner scoring / presenter | practicality, not raw object score |
| Planner chronology | planner-related | planner service | display order after selection |
| Sky Compass direction | presentation/guidance | sky compass service | direction grouping, not new target scoring |

## 5. Double-Counting Audit

### 5.1 Moon

Current duplication:

- global observing score subtracts Moon illumination;
- advanced planetary/deep-sky scores include Moon;
- Home/Detail applies object-specific Moon adjustment;
- Planner subtracts Moon penalty.

Recommended target state:

- Moon belongs to `ObservationConditionsService`;
- global weather/session score should not apply target-specific Moon damage;
- Planner should consume a condition-adjusted score or a Moon breakdown, not
  both;
- advanced scores should either become diagnostic labels or consume the same
  Moon component without adding a second penalty.

### 5.2 Light Pollution / VIIRS / Bortle

Current duplication:

- transparency score includes sky-quality penalty;
- advanced deep-sky score includes light-pollution quality;
- Home/Detail applies deep-sky pollution context;
- Planner applies a Planner-specific pollution penalty;
- equipment and difficulty use Bortle context.

Recommended target state:

- target desirability gets one light-pollution penalty from
  `ObservationConditionsService`;
- equipment may still use Bortle to choose a setup, because this is a different
  decision dimension;
- Planner should not subtract a second pollution penalty if it consumes
  condition-adjusted targets.

### 5.3 Weather / Cloud / Humidity / Visibility

Current duplication:

- weather score includes cloud, rain, wind, humidity;
- seeing/transparency includes wind, clouds, humidity and visibility;
- advanced scores include weather and transparency;
- Planner includes category score, direct weather contribution and weather
  factor.

Recommended target state:

- severe cloud/rain is a session gate/cap;
- clouds and humidity should not be counted both as weather score and as
  target transparency penalty unless one is explicitly a diagnostic;
- Planner should use one session factor and one target transparency context.

### 5.4 Seeing

Current use:

- advanced planetary score;
- equipment magnification cap.

This overlap is acceptable if kept dimensionally separate:

- one seeing component may affect target desirability for seeing-sensitive
  targets;
- the same seeing measurement may constrain magnification recommendation;
- it should not be added again inside Planner after target conditions.

### 5.5 Equipment and Difficulty

Current duplication:

- difficulty affects best-object selection and Planner ranking;
- equipment uses target difficulty context for setup suitability.

Recommended target state:

- equipment selection remains independent;
- difficulty belongs to Planner/practicality and presentation;
- if active-profile capability is used in Planner, it should be a named Planner
  term, not hidden inside weather or condition score.

## 6. Atmospheric Transparency Model

The cleanest model is a single provider-independent atmospheric context consumed
by `ObservationConditionsService`.

```text
AtmosphericContext
    cloud_transmission       from forecast cloud layers
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
- cloud cover remains primarily a session gate/cap.
- humidity/visibility can be part of transparency, but must not be counted
  again as a full weather penalty inside the same target score.

### 6.1 AOD vs PM

Recommended policy:

- AOD is primary when fresh enough because it measures the column more relevant
  to astronomical transparency.
- PM is fallback when AOD is missing, stale or invalid.
- If both exist, PM may add at most a small correction, not a second full
  penalty.
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

### 6.2 Aerosol Penalty Shape

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

P_aerosol = min(type_aerosol_cap, type_sensitivity * aerosol_cap * freshness_weight)
```

This keeps PM weaker than AOD and prevents AOD+PM double-counting.

## 7. Moon Model

The current Moon model is useful but incomplete. It mainly uses illumination and
target type. The future model should add cheap geometry.

Recommended future formula:

```text
P_moon =
    MoonSensitivity(target)
    * IlluminationFactor
    * MoonAltitudeFactor
    * MoonSeparationFactor
    * MoonWindowFactor
```

Where:

```text
IlluminationFactor = clamp((illumination - 25) / 75, 0, 1)

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

Sampling strategy:

- do not sample minute-by-minute;
- sample target window start, midpoint, best-time sample and end;
- use the worst meaningful Moon geometry sample or a weighted midpoint;
- cache Moon alt/az samples per location/date/time bucket.

This model should first be diagnostic-only, then enabled behind a feature flag
for Planner only.

## 8. Recommended Caps and Sensitivity Matrix

Caps protect recommendations from one bad parameter destroying every target.

| Target class | AOD sensitivity | PM role | AOD/PM cap | Moon cap | Light-pollution cap | Total condition cap |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| Moon | very low | none | 1 | 0 | 0 | 5 |
| Planets | low | none/minor | 3 | 0 | 0 | 18 |
| Globular clusters | medium-low | low fallback | 4 | 18 | 18 | 35 |
| Open clusters | medium-low | low/medium fallback | 3 | 10 | 12 | 25 |
| Planetary nebulae | medium | medium fallback | 5 | 18 | 22 | 38 |
| Diffuse nebulae | high | medium-high fallback | 8 | 35 | 30 | 55 |
| Galaxies | very high | high fallback | 12 | 40 | 35 | 60 |

Global caps:

- weather/session cap: handled separately as a gate or multiplier;
- combined aerosol/PM cap: 12 points;
- combined sky-background cap from Moon plus light pollution: 45 points;
- total target-condition cap: target-class dependent, never above 60;
- planets should be protected from transparency over-penalization and instead
  be primarily affected by seeing and altitude.

## 9. Worked Examples

These examples use the proposed future model, not current production scoring.
They are illustrative and should become tests before enablement.

Assumed session:

- weather/session factor `W = 0.85`;
- Bortle/VIIRS produces moderate light-pollution penalties;
- AOD is fresh and moderate;
- PM exists but is treated only as minor correction because AOD exists;
- Moon illumination is 70%.

### 9.1 M31, galaxy

```text
Raw astronomical score A = 82
Light-pollution penalty = 14
Moon penalty = 18
AOD/PM residual = 4
Combined condition penalty = 36, below galaxy cap 60
Conditioned score C = 82 - 36 = 46
Session-adjusted planning value = 46 * 0.85 = 39.1
```

Interpretation: M31 remains possible, but bright Moon, moderate aerosols and
sky brightness make it much less attractive than the raw astronomical score
suggests.

### 9.2 Saturn, planet

```text
Raw astronomical score A = 88
Light-pollution penalty = 0
Moon penalty = 0
AOD/PM residual = 1
Seeing target penalty = 8
Combined condition penalty = 9, below planet cap 18
Conditioned score C = 88 - 9 = 79
Session-adjusted planning value = 79 * 0.85 = 67.2
```

Interpretation: Moon and light pollution do not matter much. Seeing matters for
target desirability, while EquipmentService separately uses seeing to choose a
realistic magnification.

### 9.3 M13, globular cluster

```text
Raw astronomical score A = 78
Light-pollution penalty = 7
Moon penalty = 8
AOD/PM residual = 2
Combined condition penalty = 17, below globular cap 35
Conditioned score C = 61
Session-adjusted planning value = 61 * 0.85 = 51.9
```

Interpretation: globular clusters degrade under poor sky, but less severely
than galaxies and diffuse nebulae.

### 9.4 M42, diffuse nebula

```text
Raw astronomical score A = 84
Light-pollution penalty = 16
Moon penalty = 20
AOD/PM residual = 6
Combined condition penalty = 42, below diffuse-nebula cap 55
Conditioned score C = 42
Session-adjusted planning value = 42 * 0.85 = 35.7
```

Interpretation: diffuse nebulae should be strongly penalized by Moon, sky
brightness and aerosol scattering.

### 9.5 Moon

```text
Raw astronomical score A = 95
Light-pollution penalty = 0
Moon penalty = 0
AOD/PM residual = 0
Cloud/session factor W = 0.85
Conditioned score C = 95
Session-adjusted planning value = 95 * 0.85 = 80.8
```

Interpretation: the Moon is mainly limited by cloud/session state and seeing,
not by sky brightness or aerosol transparency penalties.

## 10. ObservationConditionsService Boundaries

`ObservationConditionsService` should own:

- Moon illumination and Moon geometry target penalties;
- light-pollution target penalties from VIIRS/Bortle;
- future AOD/PM residual transparency penalties;
- target sensitivity profiles;
- freshness-weighted diagnostic breakdowns;
- double-counting flags for applied condition components.

It should not own:

- raw astronomical score generation;
- weather data download;
- global weather blocking;
- equipment candidate scoring;
- optical setup selection;
- Planner chronology;
- Sky Compass direction ranking;
- UI presentation strings beyond diagnostic identifiers.

`PlannerScoringService` should own:

- how conditioned target score is combined with observing-window quality;
- chronology-aware plan selection;
- difficulty/practicality factor;
- optional active-profile capability term;
- weather/session cap application;
- final Planner diagnostics.

`EquipmentService` should own:

- magnification, exit pupil, field of view and limiting magnitude suitability;
- seeing-limited magnification;
- active-profile setup choice.

## 11. Recommended Migration Roadmap

### Step 1: Mathematical constants and test fixtures

- Define target classes, sensitivity profiles and caps in tests first.
- Keep production scoring unchanged.
- Add explicit "phenomenon ownership" tests where possible.

### Step 2: Diagnostic completeness

- Ensure every condition breakdown can report Moon, light pollution, AOD, PM,
  weather placeholder, seeing placeholder, transparency placeholder and feature
  flags.
- Keep modifiers neutral.

### Step 3: Planner-only experimental flag

- Add feature-flagged Planner path:
  - default off;
  - consumes condition-adjusted score;
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

### Step 8: Home and Best Object integration

- Only after Planner equivalence is proven, move Home/Best Object to the same
  conditioned target score.
- Keep Sky Compass consuming prepared targets only.

## 12. Tests Required Before Enablement

### Characterization tests

- Current Planner output unchanged with flags off.
- Current Home/Detail output unchanged with flags off.
- Current Best Object unchanged with flags off.
- Current equipment recommendations unchanged with flags off.
- Sky Compass live refresh still does not call scoring or heavy refresh paths.

### Atmospheric tests

- AOD freshness weights: 0-3 days, 4-7 days, >7 days.
- OpenAQ freshness weights: 0-24 h, 24-72 h, 3-7 days, >7 days.
- AOD dominates PM when both are fresh.
- PM acts only as fallback or small correction.
- PM is ignored when AOD exists and correction cap is reached.
- AOD/PM penalty caps per target type.
- AOD/PM modifiers remain zero with feature flag off.
- AOD/PM do not feed transparency, weather, Planner and target score
  simultaneously.

### Moon tests

- Moon below horizon reduces or eliminates Moon penalty.
- Moon high above horizon applies the normal illumination penalty.
- Moon close to target increases penalty.
- Moon far from target reduces penalty.
- Moon set before target window is neutral.
- Galaxies and diffuse nebulae remain more sensitive than clusters.
- Planets, Moon and Sun remain neutral for Moon sky-brightness penalty.

### Double-counting tests

- A target cannot have `moon` applied twice in the same final score.
- A target cannot have `light_pollution` applied twice in the same final score.
- AOD and PM cannot both contribute full independent penalties.
- Weather cannot be applied as direct contribution, category contribution and
  final factor in a new scoring path.
- Equipment score cannot silently become target desirability.

### Performance tests

- Moon geometry sampling uses bounded samples, not minute-by-minute loops.
- AOD/PM diagnostics do not trigger network refreshes from scoring.
- Sky Compass live refresh stays position-only.

## 13. Recommendation

Do not enable AOD/OpenAQ scoring in production yet.

The safe next step is:

1. keep feature flags default off;
2. add formal mathematical constants and regression fixtures;
3. implement Planner-only experimental scoring behind a flag;
4. compare output against current Planner for many scenarios;
5. only then decide whether the new model should replace the current layered
   scores.

This preserves NightScope's current stable behavior while moving toward a
single explainable mathematical system where each physical phenomenon has one
owner and one role in the final target desirability score.
