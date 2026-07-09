# NSOM 1.0 - NightScope Observation Model

Status: FROZEN reference model - NSOM 1.0

This document defines the long-term NightScope observation model.

Future implementation should adapt to this model rather than changing the model
to fit short-term implementation constraints.

Changes to this document should be rare and should require explicit
architectural review.

Current production code does not fully implement NSOM 1.0 yet, but Planner,
Home `recommendedDeepSky`, Best Object, Sky Compass and the Advanced Observing
backend now have default-on NSOM consumers or projections with explicit
internal rollback paths. `AdvancedObservingService` still keeps
`advancedScores` as the legacy-compatible visible/consumer contract, while the
default-on NSOM projection is exposed separately through the read-only
`advancedObservingNsom` property and is not consumed by visible QML. Sky
Compass remains a direction/presentation service, but its default direction
candidate base is now NSOM `ObservableTargetValue` with no QML payload change.

## Core Diagram

```text
NightScope Observation Model (NSOM 1.0)

The Universe
    |
    v
Intrinsic Target
    |
    v
The Sky / Observation Environment
    |
    v
Effective Observability
    |
    v
Observable Target Value
    |
    v
The Observer
    |
    v
Observer Capability
    |
    v
Practical Target Value
    |
    v
Observation Opportunity
    |
    v
Planner
    |
    v
Presentation


Recommendation Confidence
    +- Weather confidence
    +- AOD confidence
    +- OpenAQ confidence
    +- VIIRS confidence
    +- Moon geometry confidence
    +- Provider / fallback confidence

Confidence runs in parallel.
It must not silently modify score.
```

## Implementation Principle

The model is the source of truth.

Code should move toward NSOM 1.0.

NSOM 1.0 should not be rewritten to justify accidental implementation details.

## Decision Rule

Any future scoring or planning change should answer:

1. Which NSOM layer does this belong to?
2. Which physical phenomenon or observer capability does it model?
3. Who owns it?
4. Could it double-count an existing phenomenon?
5. Does it affect score, confidence, or presentation?
6. Does it preserve the separation between Universe, Sky, Observer,
   Opportunity and Planner?

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

Observation Opportunity
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
  observer can exploit, represented as a structured capability profile rather
  than a single scalar.
- `Practical Target Value`: the value a specific observer can realistically use
  after objective observability meets observer capability.
- `Observation Opportunity`: a concrete candidate for planning that combines
  practical target value, observing window, chronology, session viability,
  practical constraints and confidence annotations.

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

This produces a structured `ObserverCapability` profile and
`PracticalTargetValue`. Two observers under the same sky can legitimately
receive the same `ObservableTargetValue` and different `PracticalTargetValue`.

## 1. Current Scoring Pipeline

NightScope currently has several partially overlapping scoring layers.

```text
SkyfieldAstronomyEngine raw objects
    -> AppController Home filtering and condition presentation
    -> ObservationConditionsService moon/light-pollution presentation context
    -> EquipmentService optical setup recommendation
    -> ObservingScoreService global observing score and legacy fallback
    -> BestObjectNsomSelectionService default Best Object
    -> SeeingTransparencyService seeing/transparency estimates
    -> AdvancedObservingService planetary/deep-sky category scores
    -> PlannerNsomScoringService default observing-plan ranking
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
| Global observing score | `ObservingScoreService` | weather plus Moon illumination | Home, best object fallback/display compatibility, Planner rollback, advanced scores | High: includes Moon and weather |
| Best object | `BestObjectNsomSelectionService` default; `ObservingScoreService` rollback/fallback | Home-specific `ObservationOpportunity` from practical value and session viability | Home | Managed: legacy displayed score remains compatibility data |
| Seeing score | `SeeingTransparencyService` | atmospheric steadiness | Advanced scores, equipment | Medium but acceptable if separated by dimension |
| Transparency score | `SeeingTransparencyService` | cloud layers, humidity, visibility, VIIRS/Bortle | Advanced deep-sky score | High if AOD/PM are added elsewhere |
| Advanced planetary score | `AdvancedObservingService` | weather, seeing, wind, Moon | Planner category score, UI | High: weather and Moon already exist |
| Advanced deep-sky score | `AdvancedObservingService` | weather, transparency, VIIRS/Bortle, Moon | Planner category score, UI | High |
| Home/Detail Moon adjustment | `ObservationConditionsService` | object-specific Moon sensitivity | Home, Detail, Sky Compass candidates | Medium |
| Home/Detail pollution context | `ObservationConditionsService` | presentation/context adjustment for bright skies | Home, Detail, Sky Compass candidates | Medium |
| Planner score | `PlannerNsomScoringService` default; `PlannerScoringService` rollback | NSOM `ObservationOpportunity` by default, legacy plan-specific aggregation as rollback | Night Planner | Managed: legacy path retained only as rollback |
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
7. Observation opportunity
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

Practical Target Value + window + session + constraints
    -> Observation Opportunity

Observation Opportunity
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
ObserverCapabilityProfile
    light_grasp
    resolution
    field_of_view
    magnification_range
    tracking_or_goto
    automation_or_eaa
    filters
    experience_level
    observing_style
    practical_comfort

ObserverCapabilityBreakdown
EquipmentRecommendation
```

Equipment is only the first implemented part of observer capability. This layer
is fundamentally different from the sky. Two observers under the same sky can
obtain very different results from the same `ObservableTargetValue`.

`ObserverCapability` is conceptually multidimensional. It may eventually expose
a scalar summary for Planner, but that scalar is a projection of the capability
profile, not the capability itself.

Implementation note for 1.5.0: the current experimental Planner path still uses
a flat mean for `ObserverCapability.summary_for_planning()`. The developer-only
ObserverCapability review fixtures show that isolated aperture, focal length,
tracking, field-of-view and practical-comfort changes produce uniform observer
summary deltas across target classes. That is useful evidence for reviewing
`Q_target` before calibration; it is not a weight tuning change.

Implementation note for 1.5.1: the experimental Planner path now uses an
internal Observer-layer projection named `Q_target`:

```text
Q_target = project_observer_capability_for_target(
    ObserverCapabilityProfile,
    target_class,
)
```

The profile remains multidimensional. `Q_target` is only the scalar projection
used when `PracticalTargetValue` needs a multiplier. Explicit internal weighting
profiles cover planet, Moon, galaxy, diffuse nebula, open cluster and globular
cluster. Planets emphasize resolution, magnification and tracking; Moon
emphasizes resolution and practical comfort; galaxies emphasize light grasp and
field of view; diffuse nebulae emphasize light grasp, field of view and setup
suitability represented by practical comfort; open clusters emphasize field of
view and comfort; globular clusters emphasize light grasp and resolution. These
profiles are experimental evidence for the next review step, not final
calibration.

Implementation note for 1.5.2: calibration review thresholds are now reported
by developer-only tooling before any weight tuning. They classify deterministic
NSOM Planner evidence as `expected`, `review` or `warning` for large rank
deltas, protected planet/Moon degradation, bright-sky deep-sky sensitivity,
observer dominance, all-zero groups and missing/invisible-window handling.
Blocked sessions are reviewed under two policies: the current hard block where
`ObservationOpportunity` becomes `0.0`, and a preserved target-ordering view
based on `PracticalTargetValue` that remains explicitly non-actionable. These
thresholds are not part of the NSOM formula and must not affect score.

Implementation note for 1.5.3: the calibration decision log records review
outcomes without changing the model. Decision statuses are `accepted`,
`deferred`, `needs_calibration` and `needs_policy_decision`. Accepted entries
are documented as intentional NSOM behaviour and do not become tuning
requirements. `needs_calibration` entries identify future targeted formula
work, while `needs_policy_decision` entries hold blocked-session, invisible
target and missing-window policy questions outside the score path. The log is
developer-only metadata and must not affect recommendation score.

Implementation note for 1.5.4: non-actionable opportunity policy is now
explicit developer metadata. Blocked sessions keep the hard-block equation
`ObservationOpportunity = 0.0`, but any preserved `PracticalTargetValue` order is
reported as `non_actionable_preserved_order` and is never recommendation order.
Invisible targets with zero geometric visibility are non-actionable ties. Visible
targets with missing observing windows keep the conservative 0.5 fallback and are
marked `actionable_with_uncertain_timing`. These policy labels resolve the
policy blockers without changing score formulas or legacy Planner behaviour.

Implementation note for 1.5.5: the targeted small-equipment planet calibration
is implemented as an Observer-layer `Q_target` projection rule, not as a sky,
session, confidence or legacy-score change. For planets only, a profile that
meets minimum observable dimensions for light grasp, resolution, magnification
and tracking may use a small floor in `Q_target`; this represents "planet
observable" rather than "planet optimal detail". The rule changes
`PracticalTargetValue` only through `Q_target` and leaves
`ObservableTargetValue`, `EffectiveObservability`, `SessionViability` and
`RecommendationConfidence` unchanged.

Implementation note for 1.5.6: the targeted open-cluster recurring-demotion
calibration is also implemented as an Observer-layer `Q_target` projection rule.
For open clusters only, when the ObserverCapability profile already has usable
field of view and adequate practical comfort, the projection applies a modest
field-of-view usability floor before computing the target-class weighted mean.
This represents the fact that open clusters are often easy, wide-field,
beginner-friendly targets even when the field is not optimal. Genuinely narrow
fields remain limited. The rule changes `PracticalTargetValue` only through
`Q_target` and leaves `IntrinsicTargetQuality`, `ObservableTargetValue`,
`EffectiveObservability`, `SessionViability` and `RecommendationConfidence`
unchanged.

Implementation note for 1.5.7: the default-on readiness audit is developer-only
evidence, not a model or scoring change. It verifies that `default_on_blockers`
is empty, accepted/deferred calibration decisions are documented, deferred items
are non-blocking, the Planner NSOM flag remained default-off in that step,
legacy Planner remained the default runtime path and report tooling is not exposed to QML,
automatic logging, network calls or runtime file writes. The audit verdict can
recommend a separate default-on switch PR, but this step does not enable NSOM
Planner.

Implementation note for 1.5.8: Planner NSOM is enabled by default by setting
`NSOM_PLANNER_SCORING_ENABLED = True`. This is a switch of the existing
Planner consumer path, not a mathematical model change: NSOM formulas,
`Q_target`, `RecommendationConfidence`, report tooling, QML exposure, network
behaviour, logging and runtime file writes are unchanged. The legacy Planner
scoring path remains callable as an explicit rollback with
`NightPlannerService(use_nsom_planner_scoring=False)`.

Implementation note for 1.5.9: the NSOM Planner migration is closed. NSOM
Planner is now the default Planner path, and legacy Planner is retained only as
an explicit rollback through `NightPlannerService(use_nsom_planner_scoring=False)`.
This step does not change scoring, NSOM formulas, `Q_target`,
`RecommendationConfidence`, QML exposure, report runtime wiring, logging,
network behaviour or runtime file writes beyond the already-enabled `1.5.8`
state. The remaining deferred non-blocking review items are
`medium-equipment-q-target-review-band` and
`moon-planet-favouring-category-factor`; they are future calibration review
topics and do not block the completed Planner migration. Comparison,
mathematical trace, calibration decision-log and readiness-audit tooling remain
developer-only and are not runtime Planner inputs.

Implementation note for 1.6.5: the Home `recommendedDeepSky` migration is
closed. The default Home deep-sky order is now NSOM `ObservableTargetValue`
order, owned by the Universe/Sky side of the model:
`IntrinsicTargetQuality`, `ObservationEnvironment`, `EffectiveObservability`
and `ObservableTargetValue`. Home intentionally does not use
`PracticalTargetValue`, `ObserverCapability`, `SessionViability`,
`RecommendationConfidence` or `ObservationOpportunity` for this list. The
legacy Home order remains available only as an explicit internal rollback with
`AppController(use_nsom_home_recommended_deep_sky=False)`. If sky quality is
missing, Home still falls back to the legacy moon-adjusted path because
`ObservationEnvironment` cannot be built from current sky inputs. The QML
payload remains unchanged and no NSOM fields are exposed. Displayed Home scores
remain legacy/base scores for compatibility, so they may not be monotonic with
the NSOM order until a future UI rationale pass decides how to present NSOM
explanations.

Implementation note for 1.7.0: Best Object now has a developer-only NSOM
comparison layer. The runtime Best Object selector is still legacy and still
uses `item.score * weather_factor * difficulty_factor`; the comparison helper
does not alter selection. For the same candidate set it projects
`IntrinsicTargetQuality`, `ObservationEnvironment`, `EffectiveObservability`,
`ObservableTargetValue`, `PracticalTargetValue`, `SessionViability` metadata
and `RecommendationConfidence` metadata. This exposes the ownership mismatch:
legacy Best Object combines target score, weather/session and difficulty in a
single scalar, while NSOM keeps sky, observer, session and confidence
separate. Components not exposed by the legacy implementation are marked
unavailable rather than inferred. The helper is not runtime ranking, QML/UI,
logging, network work or runtime file output.

Implementation note for 1.7.1: `docs/BEST_OBJECT_NSOM_COMPARISON_REPORT.md`
captures the Best Object comparison layer as a deterministic developer-only
report. It compares legacy Best Object score/order with NSOM
`ObservableTargetValue` order, NSOM `PracticalTargetValue` order,
`SessionViability` metadata and `RecommendationConfidence` metadata across
good, poor and blocked sessions, bright Moon, high light pollution, small and
large equipment, and a mixed planet/deep-sky candidate set. The report's
semantic recommendation is that Best Object is currently a Home-specific
hybrid: `ObservableTargetValue` is too object/sky-only, `PracticalTargetValue`
omits session actionability, and a future NSOM runtime path should evaluate
`ObservationOpportunity` with a Home-specific presentation policy. The report
tool remains explicit developer tooling and is not a runtime input.

Implementation note for 1.7.2: Best Object now has an internal default-off NSOM
runtime path in `BestObjectNsomSelectionService`, guarded by
`NSOM_BEST_OBJECT_ENABLED = False`. The controller default still preserves the
legacy formula; rollback remains explicit with
`AppController(use_nsom_best_object=False)`, and the experimental path can be
forced with `AppController(use_nsom_best_object=True)`. The path builds
Home-owned `ObservableTargetValue`, projects telescope-aware
`ObserverCapability` through target-specific `Q_target`, derives
`PracticalTargetValue`, and ranks by `ObservationOpportunity` with a compact
Home actionability policy. Blocked sessions are non-actionable and return no
runtime Best Object while preserving diagnostic practical ordering inside the
service; invisible candidates are also non-actionable. `RecommendationConfidence`
is carried only as metadata and does not affect opportunity value. No NSOM
fields are added to QML, no report tooling is wired into runtime, and missing
sky quality keeps the legacy Best Object fallback.

Implementation note for 1.7.3: Best Object actionability policy is resolved
for default-on readiness. Blocked sessions and invisible candidates remain
non-actionable and are not treated as meaningful recommendation order; visible
candidates with missing or uncertain windows are marked with timing
uncertainty. Preserved practical ordering for non-actionable cases is
diagnostic-only inside the service.

Implementation note for 1.7.4: the developer-only readiness audit
`docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md` verifies that the Best
Object NSOM path has no blocking policy issues, keeps confidence score-neutral,
preserves rollback and does not expose QML, logging, network work, runtime file
writes or report runtime wiring.

Implementation note for 1.7.5: Best Object NSOM is enabled by default via
`NSOM_BEST_OBJECT_ENABLED = True`. Runtime selection uses
`BestObjectNsomSelectionService` when weather and sky quality inputs are
available. Legacy Best Object remains available only as explicit rollback with
`AppController(use_nsom_best_object=False)` and as fallback when sky quality is
missing.

Implementation note for 1.7.6: the Best Object NSOM migration is closed as a
documented default-on path. Best Object now uses Home-specific
`ObservationOpportunity` policy by default; the QML payload remains unchanged,
no NSOM fields are exposed, and the displayed score remains legacy/base
compatibility data. That score may not be monotonic with NSOM selection until a
future presentation rationale pass changes score display semantics.

Implementation note for 1.8.0: `AdvancedObservingService` now has a
developer-only NSOM comparison layer. The runtime advanced planetary and
deep-sky scores remain legacy and unchanged. The comparison helper exposes the
exact legacy formula components, including weather, seeing/transparency, wind,
Moon, light pollution and weather caps, then contrasts them with reference-only
NSOM projections for `SessionViability`, target-class `ObservationEnvironment`,
`EffectiveObservability`, `ObservableTargetValue` and parallel
`RecommendationConfidence`. The NSOM projection is explicitly not score parity,
not a replacement advanced score and not wired to QML, logging, network work or
runtime file output.

Implementation note for 1.8.1: the developer-only report
`docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md` renders the Advanced
Observing comparison layer across deterministic scenarios for good, poor and
blocked sessions, bright Moon, high light pollution, poor seeing, poor
transparency and low confidence. It documents that Advanced Observing is best
treated as a presentation/category diagnostic consumer of NSOM components,
rather than an independent owner of Moon, weather, light-pollution and
transparency scoring. The report is explicit tooling only and is not runtime
wiring.

Implementation note for 1.8.2: the Advanced Observing comparison report was
reviewed without implementation changes. The review confirmed that the report
is useful for policy work, but that session/actionability handling,
planetary/Moon protection from sky-background penalties, deep-sky target-class
visibility, displayed score semantics and deferred observer capability need
explicit decisions before adding a runtime path.

Implementation note for 1.8.3: the developer-only report
`docs/ADVANCED_OBSERVING_NSOM_POLICY_READINESS.md` records those policy
decisions. Advanced Observing remains a presentation/category diagnostic
surface, `SessionViability` is separate from sky and target values, planetary
and Moon diagnostics are protected from Moon/light-pollution background
penalties, deep-sky diagnostics preserve target-class components, legacy weather
caps remain only in the legacy/default path until a future default-off path is
implemented, `ObserverCapability` is deferred for Advanced Observing, and
`RecommendationConfidence` remains parallel metadata with zero score effect.
This step changes no runtime advanced score, Home, Best Object, Planner, Sky
Compass, QML, logging, network behaviour or runtime file writes.

Implementation note for 1.8.4: `AdvancedObservingNsomService` introduces the
first runtime Advanced Observing NSOM path, but it is default-off via
`NSOM_ADVANCED_OBSERVING_ENABLED = False`. `AppController` keeps the legacy
`AdvancedObservingService` path by default and exposes only the internal
constructor override `use_nsom_advanced_observing=True` for tests/development.
The forced-on path keeps the existing `AdvancedObservingScores`/QML payload
shape and derives category values from NSOM `ObservableTargetValue` references:
planetary uses the planet target class and seeing transparency, while deep-sky
uses a target-class-aware aggregate across galaxy, diffuse nebula, open cluster
and globular cluster references. `SessionViability` and
`RecommendationConfidence` are metadata only and do not multiply or cap category
scores; `ObserverCapability` is still deferred for Advanced Observing. This step
does not add QML fields, report runtime wiring, logging, network work or
runtime file writes.

Implementation note for 1.8.5: the developer-only report
`docs/ADVANCED_OBSERVING_NSOM_RUNTIME_REVIEW.md` reviews the forced-on
Advanced Observing NSOM path against the legacy path. It confirms the path is
safe to keep while default-off: payload shape remains compatible, confidence is
score-neutral, session viability does not cap/multiply category values,
planetary category values are protected from Moon/light-pollution background,
and deep-sky remains sensitive to sky background. The report also records that
default-on is not ready: `advancedScores` is a shared runtime input consumed by
QML, Planner and NotificationService, so those downstream consumers need an
explicit policy before `NSOM_ADVANCED_OBSERVING_ENABLED` can change.

Implementation note for 1.8.6: the developer-only report
`docs/ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY.md` records that
`advancedScores` must remain legacy-compatible until downstream consumers are
split. Planner currently treats `advancedScores` as an atmospheric-transparency
factor inside NSOM `EffectiveObservability`, while NotificationService treats it
as a direct threshold for favourable condition notifications. Forced-on
Advanced Observing NSOM values intentionally keep session viability outside
category scores, so using them as shared legacy-style scores would change
Planner ranking semantics and could trigger favourable notifications in blocked
sessions. The Advanced Observing NSOM flag remains default-off and this step
changes no runtime behaviour.

Implementation note for 1.8.7: `AppController` now applies the downstream
consumer split. The shared `advancedScores` payload remains the
legacy-compatible presentation/consumer contract for QML, Planner and
NotificationService. When the internal Advanced Observing NSOM flag is forced on,
NSOM category values are computed only as the private
`_advanced_observing_nsom_scores` snapshot. Planner and NotificationService
receive explicit legacy-compatible score inputs, so `ObservableTargetValue`
category diagnostics are not reused as Planner atmospheric transparency or
notification thresholds. `RecommendationConfidence` remains score-neutral, no
QML fields are exposed and `NSOM_ADVANCED_OBSERVING_ENABLED` remains `False`.
The remaining blocker before any Advanced Observing NSOM default-on switch is
the presentation/QML policy.

Implementation note for 1.8.8: the developer-only report
`docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_READINESS.md` audits that remaining
presentation blocker. The consumer split from 1.8.7 is accepted as resolved:
Planner and NotificationService continue to receive legacy-compatible
`advancedScores`. However, the forced-on Advanced Observing NSOM values remain
private `_advanced_observing_nsom_scores`; QML still renders the existing
legacy-compatible `advancedScores` cards and no public NSOM Advanced Observing
property exists. Therefore `NSOM_ADVANCED_OBSERVING_ENABLED` remains `False`
until a QML-safe presentation contract and score/label semantics are defined.
`RecommendationConfidence` remains metadata-only.

Implementation note for 1.8.9: the developer-only report
`docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md` defines the future
QML-safe contract without wiring it into runtime or QML. The contract introduces
a separate versioned `advancedObservingNsom` payload, keeps `advancedScores` as
the legacy-compatible contract, and explicitly excludes Planner,
NotificationService, Best Object and Sky Compass consumption. Advanced Observing
category values are defined as `ObservableTargetValue` diagnostics only:
`ObserverCapability`, `PracticalTargetValue`, `SessionViability`,
`RecommendationConfidence` and `ObservationOpportunity` stay outside the category
value. As of 1.8.10, runtime projection is implemented internally/default-off;
the remaining blocker is a separate QML exposure review.

Implementation note for 1.8.10: `AppController` now has an internal/default-off
runtime projection for the 1.8.9 Advanced Observing NSOM presentation contract.
When `use_nsom_advanced_observing=True` is forced in development, the controller
stores `_advanced_observing_nsom_presentation`, built by
`astro_viewer/app/services/advanced_observing_nsom_presentation.py`. The payload
keeps category values as `ObservableTargetValue` diagnostics, keeps
`SessionViability` and `RecommendationConfidence` as score-neutral metadata,
does not replace `advancedScores`, and is not consumed by Planner,
NotificationService, Best Object or Sky Compass. No QML property is exposed and
`NSOM_ADVANCED_OBSERVING_ENABLED` remains `False`; the only remaining blocker is
a separate UI/QML exposure review.

Implementation note for 1.8.11: the private Advanced Observing NSOM
presentation projection now mirrors the controller's existing session state for
the `monitor` case. If weather is currently blocking but a later usable
observing window exists, `_advanced_observing_nsom_presentation["session"]`
reports `monitor` instead of collapsing every warning into `discouraged`.
Session state remains score-neutral metadata outside `ObservableTargetValue`;
category values, `advancedScores`, Planner, NotificationService, Best Object,
Sky Compass and QML exposure are unchanged.

Implementation note for 1.8.12: the developer-only report
`docs/ADVANCED_OBSERVING_NSOM_QML_EXPOSURE_READINESS.md` audits whether the
private `advancedObservingNsom` projection should become a public QML surface.
The verdict is not ready for QML exposure. The projection is safe to keep
internally, but a public property needs explicit notify-signal/lifecycle policy,
localized UI copy, visual placement and score-label semantics. This prevents
`ObservableTargetValue` category diagnostics from being mistaken for legacy
`/100` actionability scores. `advancedScores` remains the only current public
QML contract and `NSOM_ADVANCED_OBSERVING_ENABLED` remains `False`.

Implementation note for 1.8.13: the developer-only report
`docs/ADVANCED_OBSERVING_NSOM_QML_PRESENTATION_POLICY.md` defines the missing
QML presentation policy without adding runtime exposure. A future
`advancedObservingNsom` property, if implemented in a later step, must be
read-only, use `_advanced_observing_nsom_presentation` as its source, reuse the
existing `weatherChanged` lifecycle, avoid recomputation on property read and
avoid a new notify signal. Visible UI remains blocked pending a separate design
decision; future copy must be localization-key based and label values as NSOM
diagnostics, not legacy `/100` actionability scores, Planner inputs or
NotificationService thresholds. `RecommendationConfidence` remains metadata
only, `advancedScores` remains the only current public QML contract and
`NSOM_ADVANCED_OBSERVING_ENABLED` remains `False`.

Implementation note for 1.8.14: `AppController` now exposes
`advancedObservingNsom` as a read-only QML property. The property returns the
existing private `_advanced_observing_nsom_presentation` snapshot, or `{}` when
Advanced Observing NSOM is disabled or no snapshot exists. It uses the existing
`weatherChanged` lifecycle, introduces no new signal and does not recompute on
property read. No visible QML UI consumes the property yet; `advancedScores`
remains the visible Home card contract, Planner/NotificationService/Home Best
Object/Sky Compass inputs are unchanged, `RecommendationConfidence` remains
metadata-only and `NSOM_ADVANCED_OBSERVING_ENABLED` remains `False`.

Implementation note for 1.8.15: the `advancedObservingNsom` getter now returns a
defensive deep copy of the private presentation snapshot. The Qt property remains
read-only, uses `weatherChanged` as its notify signal, returns `{}` when the
NSOM path is disabled/unavailable and can be serialized with strict JSON. Reads
through the Python helper or Qt property system cannot mutate
`_advanced_observing_nsom_presentation`. This is a property-safety hardening
only: no visible QML, scoring path, Planner, NotificationService, Best Object,
Sky Compass, network, logging or runtime file-write behaviour changes.

Implementation note for 1.8.16:
`docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md` audits the final
backend default-on decision for Advanced Observing NSOM. The verdict is ready
for a backend/internal projection switch: enabling
`NSOM_ADVANCED_OBSERVING_ENABLED` in a later commit would compute
`_advanced_observing_nsom_scores` and `_advanced_observing_nsom_presentation`
by default, but would not replace `advancedScores`, would not render visible
QML, and would not change Planner, NotificationService, Home Best Object or Sky
Compass inputs. The remaining visible UI design, copy/localization and future
legacy-score replacement questions are explicitly non-blocking for that backend
switch and remain separate NSOM presentation work.

Implementation note for 1.8.17:
Advanced Observing NSOM is enabled by default for the backend/internal
projection only: `NSOM_ADVANCED_OBSERVING_ENABLED = True`. The default
controller path computes the parallel NSOM category snapshot and read-only
presentation data, but keeps `advancedScores` legacy-compatible for visible Home
cards, Planner transparency input and NotificationService thresholds. The
rollback remains `AppController(use_nsom_advanced_observing=False)`.
SessionViability and RecommendationConfidence remain metadata outside category
values; no visible QML consumer, scoring replacement, report runtime wiring,
logging, network call or runtime file write is introduced by the switch.

Implementation note for 1.8.18:
the Advanced Observing NSOM backend migration is closed. Advanced Observing now
has a default-on NSOM internal projection for category diagnostics and a
read-only `advancedObservingNsom` surface, while the visible/consumer contract
`advancedScores` intentionally remains legacy-compatible. This preserves Planner
and NotificationService semantics and keeps visible Home cards unchanged. The
legacy-compatible path remains available through
`AppController(use_nsom_advanced_observing=False)`. Visible UI design,
copy/localization and any future replacement of legacy score display semantics
are deferred non-blocking presentation work, not open backend migration
blockers.

Implementation note for 1.9.0:
Sky Compass migration starts with a developer-only comparison layer. The helper
compares the current direction formula, based on prepared candidate score, plan
membership, Best Object identity and direction concentration, against NSOM
`IntrinsicTargetQuality`, `ObservationEnvironment`, `EffectiveObservability`,
`ObservableTargetValue`, `PracticalTargetValue`, `SessionViability` and
`RecommendationConfidence`. The comparison is reference-only: it does not
replace `SkyCompassService`, does not alter the `skyCompass` QML payload, does
not emit signals, and does not write files, log, fetch network data or wire
reports into runtime. Legacy score subcomponents that are not available from a
Sky Compass candidate are explicitly marked unavailable rather than
reconstructed.

Implementation note for 1.9.1:
`docs/SKY_COMPASS_NSOM_COMPARISON_REPORT.md` captures deterministic Sky Compass
comparison scenarios generated by
`astro_viewer/tools/sky_compass_nsom_comparison_report.py`. The report confirms
that Sky Compass should not be treated as a pure NSOM target-value ranker:
`ObservableTargetValue` and `PracticalTargetValue` can provide direction
references, but Night Plan membership, Best Object identity, target
concentration and caution/actionability remain presentation policy outside
target physics. The tool is explicit developer tooling only; it is not imported
by the controller, does not alter `skyCompass`, and does not add QML exposure,
logging, network calls or runtime file writes.

Implementation note for 1.9.2:
`docs/SKY_COMPASS_NSOM_POLICY_READINESS.md` records the policy decisions for a
future default-off Sky Compass NSOM path. The first experimental path should
not be a pure target-value ranking: `ObservableTargetValue.value` may provide
the candidate base, while plan membership, Best Object identity and target
concentration remain presentation policy outside target physics.
`PracticalTargetValue` stays reference-only until equipment-aware compass
semantics are reviewed. Session state and `RecommendationConfidence` remain
metadata, missing location/direction cases keep legacy unavailable handling,
and the existing `skyCompass` QML payload shape must be preserved. This step is
developer-only readiness tooling; it does not add a runtime flag, QML exposure,
logging, network calls or runtime file writes.

Implementation note for 1.9.3:
`SkyCompassNsomDirectionService` implements the first internal/default-off Sky
Compass NSOM direction path. The flag is `NSOM_SKY_COMPASS_ENABLED = False`,
with opt-in through `AppController(use_nsom_sky_compass=True)` and forced
rollback through `False`. The experimental path uses `ObservableTargetValue`
only as the candidate base, preserves Night Plan membership, Best Object status
and target presence as presentation-policy boosts, keeps
`PracticalTargetValue`, `SessionViability` and `RecommendationConfidence` out
of runtime direction scoring, and returns the existing `skyCompass` payload
shape without NSOM fields. Missing sky quality or service failure falls back to
legacy `SkyCompassService`; no report tooling, QML exposure, network, logging
or runtime file write is introduced.

Implementation note for 1.9.4:
`docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md` records the developer-only
readiness audit for making the Sky Compass NSOM path default-on in a later
switch-only commit. The verdict is
`ready_for_sky_compass_nsom_default_on_switch`, with no blockers. The audit
confirms default-off legacy parity, forced-on NSOM behaviour, explicit rollback
`AppController(use_nsom_sky_compass=False)`, missing-sky-quality and service
failure fallback to legacy `SkyCompassService`, unchanged `skyCompass` payload
keys and no QML/report runtime wiring. It also documents that displayed
`score` remains legacy/base compatibility data and that `PracticalTargetValue`,
`ObserverCapability`, `SessionViability`, weather/equipment inputs and
`RecommendationConfidence` remain outside runtime Sky Compass direction
scoring. `NSOM_SKY_COMPASS_ENABLED` remains `False`.

Implementation note for 1.9.5:
Sky Compass NSOM is now enabled by default with
`NSOM_SKY_COMPASS_ENABLED = True`. The default controller path uses
`SkyCompassNsomDirectionService` when sky quality exists, with
`ObservableTargetValue.value` as candidate base and Night Plan membership, Best
Object identity and target presence retained as presentation-policy boosts.
Explicit rollback remains `AppController(use_nsom_sky_compass=False)`, and
missing sky quality or NSOM service failure falls back to legacy
`SkyCompassService`. `PracticalTargetValue`, `ObserverCapability`,
`SessionViability`, weather/equipment inputs and `RecommendationConfidence`
remain outside runtime Sky Compass direction scoring. The `skyCompass` payload
shape remains legacy-compatible and no QML/UI exposure, logging, network call,
runtime file write or report runtime wiring is added.

Implementation note for 1.9.6:
the Sky Compass NSOM migration is closed as a documented default-on backend
path. Sky Compass now uses `ObservableTargetValue.value` as its default
candidate base while preserving presentation-policy boosts for Night Plan
membership, Best Object identity and target presence. Legacy
`SkyCompassService` remains explicit rollback/fallback only. The visible
`skyCompass` payload remains legacy-compatible, displayed target `score`
remains base display data rather than NSOM rationale, and no QML/UI explanation
fields are introduced in this migration.

Implementation note for 1.9.7:
`docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md` records the overall backend NSOM
migration status after the Sky Compass close. Planner, Home
`recommendedDeepSky`, Best Object, Advanced Observing backend and Sky Compass
are default-on NSOM consumers/projections with explicit rollback paths.
Remaining Detail/selected-object, Sky Map, Equipment, conditioned-object cache,
Notification and catalogue-score surfaces are non-blocking follow-up areas, not
default-on blockers for the already migrated paths. The recommended next backend
step is a Detail/Object NSOM comparison layer. This audit is developer-only and
does not change score formulas, QML, runtime logging, network access or runtime
file writes.

Implementation note for 1.10.0:
`DetailObjectNsomComparisonService` starts the Detail/Object NSOM migration as
a comparison layer only. It compares current selected-object Detail semantics
against NSOM `IntrinsicTargetQuality`, `ObservationEnvironment`,
`EffectiveObservability`, `ObservableTargetValue`, `ObserverCapability`,
`PracticalTargetValue`, `SessionViability` metadata and
`RecommendationConfidence` metadata. The comparison records that observing
Detail still displays a moon-adjusted legacy replacement object, while
catalogue Detail displays the raw selected object. No runtime Detail payload,
QML field, score formula, Planner/Home/Best Object/Sky Compass path, logging,
network access or runtime file write is changed.

Implementation note for 1.10.1:
`docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md` records that Detail/Object is not
ready for a default-off NSOM runtime path yet. The blockers are policy and
contractual, not mathematical: observing Detail and catalogue Detail currently
have different legacy display-score semantics; visible `score` is compatibility
data and is not monotonic with NSOM values; and no separate Detail NSOM
payload/display contract exists. `RecommendationConfidence` is accepted as
metadata-only. Runtime Detail, QML, Home, Best Object, Planner, Sky Compass,
logging, network access and runtime file writes remain unchanged.

Implementation note for 1.10.2:
`docs/DETAIL_OBJECT_NSOM_POLICY_CONTRACT.md` resolves those Detail/Object policy
blockers without adding runtime code. The contract keeps source-specific legacy
display semantics in `selectedObject`: observing Detail keeps the moon-adjusted
compatibility display score, catalogue Detail keeps the raw catalogue display
score, and `selectedObject.score` is explicitly legacy/base compatibility data
rather than NSOM rationale. A future default-off runtime path may build a
separate internal `detailObjectNsom` payload, but must not add NSOM fields to
`selectedObject` in the first runtime path. The updated readiness audit is
`ready_for_default_off_detail_nsom_path`; visible UI remains a later design
step.

Implementation note for 1.10.3:
`astro_viewer/app/services/detail_nsom_runtime.py` adds the first Detail/Object
runtime path as an internal default-off NSOM consumer. The flag is
`NSOM_DETAIL_OBJECT_ENABLED = False`; the controller rollback path is
`AppController(use_nsom_detail_object=False)`. When enabled explicitly, the
controller builds a separate internal payload through
`_selected_object_nsom_payload()` and keeps `selectedObject` unchanged. The
payload projects `IntrinsicTargetQuality`, `ObservationEnvironment`,
`EffectiveObservability`, `ObservableTargetValue` and `PracticalTargetValue`.
`SessionViability` and `RecommendationConfidence` remain parallel metadata;
`ObservationOpportunity` is intentionally not used for Detail/Object. No QML
property, visible UI, Home, Best Object, Planner, Sky Compass, logging, network
access or runtime file write is introduced.

Implementation note for 1.10.4:
`docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md` records the default-on
readiness decision for the Detail/Object internal runtime path. The audit keeps
`NSOM_DETAIL_OBJECT_ENABLED = False` and recommends a later switch commit if
accepted. It verifies that enabling the path would still preserve
`selectedObject`, keep the NSOM payload separate, avoid QML exposure, preserve
constructor rollback through `AppController(use_nsom_detail_object=False)`, and
keep `SessionViability` plus `RecommendationConfidence` outside the Detail score
path. Visible Detail explanations remain future UX work.

Implementation note for 1.10.5:
The Detail/Object internal runtime path is now default-on with
`NSOM_DETAIL_OBJECT_ENABLED = True`. This does not expose NSOM fields in QML and
does not change `selectedObject`; it only makes the separate backend
`detailObjectNsom` payload path the default internal state. Rollback remains
`AppController(use_nsom_detail_object=False)`. `SessionViability` and
`RecommendationConfidence` continue to be metadata-only for Detail/Object.

Implementation note for 1.10.6:
the backend Detail/Object NSOM migration is closed. Detail/Object now has a
default-on internal NSOM payload path, explicit rollback, unchanged
`selectedObject` semantics and no QML exposure. The visible Detail page still
uses the legacy/base compatibility display score, and any future visible NSOM
rationale belongs to a separate UI/design step.

Implementation note for 1.11.0:
the legacy backend surface audit in
`docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md` clarifies that not every remaining
legacy path should become an NSOM migration. Sky Map is classified as
`dead_legacy`: Home QML consumes Sky Compass and no longer consumes
`controller.skyMap`, while `AppController` still computes `_sky_map`. The NSOM
direction is therefore to remove that dead controller/property/service path
after review, not to build a Sky Map NSOM comparison layer. Temporary rollback
flags remain internal safety nets, while payload compatibility fields such as
visible `score` values are presentation contracts until a separate UI/design
step replaces them.

Implementation note for 1.11.1:
the dead Sky Map path is removed rather than migrated. `SkyMapService`,
`AppController.skyMap`, `_sky_map` storage and Sky Map recomputation are gone.
Sky Compass remains the supported directional Home surface. No NSOM scoring,
Planner, Home recommendation, Best Object, Advanced Observing, Detail/Object or
QML payload behaviour changes in this cleanup. The next active backend NSOM area
is Equipment/ObserverCapability.

Implementation note for 1.12.0:
`docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md` adds a developer-only comparison
between the current `EquipmentService` setup score and NSOM
`ObserverCapability`, target-specific `Q_target` and `PracticalTargetValue`.
The report shows where the legacy formula mixes target traits, sky quality,
seeing and setup handling in one equipment score. NSOM keeps
`ObservableTargetValue` separate from observer capability; confidence remains
metadata-only. Runtime Equipment recommendations, QML payloads and other
recommendation surfaces are unchanged. The next step is review and
policy/readiness before any default-off Equipment NSOM path.

Implementation note for 1.12.1:
`docs/EQUIPMENT_NSOM_POLICY_READINESS.md` records that Equipment is not ready
for a default-off NSOM runtime replacement and should not be treated as another
target-ranking surface. `EquipmentService.suggest_for_profile(...)` remains the
runtime setup helper for eyepieces, Barlow, binoculars, naked-eye/no-eyepiece
fallbacks and `setupOptions`. The NSOM-owned next step is to extract a shared
`ObserverCapability`/`Q_target` adapter or read model. Sky quality and seeing
must stay behind explicit environment/setup-stability boundaries; confidence
remains metadata-only.

Implementation note for 1.12.2:
`observer_capability_adapter.py` now owns the shared
`ObserverCapability`/`Q_target` projection from concrete equipment
configurations and `RecommendationCandidate` objects. The Equipment comparison
report consumes this adapter instead of carrying report-private capability math.
This is still backend/internal infrastructure: `EquipmentService` remains the
runtime setup recommender, no default-off Equipment replacement path is added,
and QML receives no NSOM equipment fields.

Implementation note for 1.12.2b:
the extracted `ObserverCapabilityProjection` keeps target-class weighting
metadata immutable while preserving strict JSON projection. The hardening is
limited to DTO integrity; it does not change observer formulas, Q_target,
PracticalTargetValue, runtime Equipment ranking, QML or report runtime wiring.

Implementation note for 1.12.3:
`docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md` classifies the old Notifications path
as dead legacy pending removal. Current QML/Home no longer consumes
`controller.notifications`, so Notifications should be removed like Sky Map
rather than migrated to NSOM. This audit does not change runtime behaviour; the
removal belongs to a separate cleanup commit.

Implementation note for 1.12.4:
the Notifications cleanup removes `NotificationService`,
`AppController.notifications`, runtime notification storage/recomputation and
the `Notification` DTO. This is not an NSOM migration and does not change any
score or visible QML payload; it removes a dead Home-era backend path so future
NSOM work can focus on active backend surfaces.

Implementation note for 1.12.5:
`docs/OBSERVATION_CONDITIONS_READ_MODEL_AUDIT.md` audits the active
`ObservationConditionsService` boundary. The current service is not dead legacy:
it creates condition-adjusted `CelestialObject` copies for display/fallback
compatibility, while NSOM Home/Best Object/Sky Compass can compute observable
values from those same objects. The next implementation step should introduce a
read model that separates raw target score, condition-adjusted display score,
condition diagnostics and NSOM-safe `ObservableTargetValue` input.

Implementation note for 1.12.6:
`ObservationConditionedTargetReadModel` introduces the explicit internal
read-model boundary for ObservationConditions. It preserves raw target input for
future NSOM `IntrinsicTargetQuality`/`ObservableTargetValue` construction while
keeping the condition-adjusted `CelestialObject` as a display compatibility
object. This commit does not reroute Home, Best Object or Sky Compass ranking;
that remains a separate reviewed behaviour step.

Implementation note for 1.12.7:
`docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md` defines the consumer
reroute policy for the ObservationConditions read model. NSOM-owned calculations
should consume `ObservationConditionedTargetReadModel.nsom_target_input`, while
existing Home/Best/Sky Compass payload compatibility should continue to display
`ObservationConditionedTargetReadModel.qml_display_target`. Runtime rerouting is
intentionally deferred to a separate behaviour-reviewed commit.

Implementation note for 1.12.8:
Home `recommendedDeepSky` now follows the read-model ownership boundary in the
default NSOM path. Its `ObservableTargetValue` ranking is computed from
`ObservationConditionedTargetReadModel.nsom_target_input`, avoiding reuse of
condition-adjusted display score as NSOM target physics. The Home QML payload is
still built from `ObservationConditionedTargetReadModel.qml_display_target`, so
visible fields and display/base score compatibility are preserved. Best Object
and Sky Compass are not rerouted in this step.

Implementation note for 1.12.9:
Best Object now follows the same ObservationConditions read-model boundary in
the default NSOM path. `BestObjectNsomSelectionService` receives raw
`nsom_target_input` candidates, so `ObservationOpportunity` is built from the
Universe-owned target value rather than a condition-adjusted display score. The
controller maps the selected raw target back to `qml_display_target` for the
existing QML payload. At that point Sky Compass remains the only
ObservationConditions consumer pending a raw-target reroute decision.

Implementation note for 1.12.10:
`docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md` defines the remaining Sky
Compass ObservationConditions policy. Sky Compass is a direction/presentation
surface, so future runtime reroute work must split sources: raw
`nsom_target_input` for `ObservableTargetValue` target physics, display/live
target for direction grouping, visibility, horizon/current position and QML
payload, and target-id context for Night Plan / Best Object boosts. This step
does not change Sky Compass runtime behaviour.

Implementation note for 1.12.11:
Sky Compass now implements the split source policy. The runtime builds internal
observable targets by combining raw read-model target physics with current
display/live geometry before constructing `ObservableTargetValue`; direction
grouping and QML payload still use the display/live candidates. This completes
the Home, Best Object and Sky Compass consumer reroute over the
ObservationConditions raw/display boundary.

Implementation note for 1.12.12:
The ObservationConditions consumer reroute series is closed. Home
`recommendedDeepSky`, Best Object and Sky Compass now consume the raw side of
the read-model for NSOM target physics while preserving display/live targets for
compatibility payloads. The closeout changes only developer-facing status/docs;
the next backend NSOM area is Equipment presenter contract work.

Implementation note for 1.13.0:
`docs/EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT.md` defines the current Equipment
presenter contract before any runtime scoring replacement. The audit keeps
`EquipmentService.suggest_for_profile(...)` as the runtime owner of setup
payloads, fallback states, `setupOptions` and `selectionScore`; it treats
`ObserverCapability`/`Q_target` as reference-only NSOM observer metadata for now
and keeps `RecommendationConfidence` parallel and score-neutral. No QML field,
runtime Equipment ranking, Planner/Home/Best Object/Sky Compass path, logging,
network call or runtime write is introduced. The next NSOM-safe backend step is
a runtime-neutral Equipment setup read-model/presenter DTO.

Implementation note for 1.13.1:
`EquipmentSetupReadModel` and `EquipmentSetupReadModelBuilder` introduce the
runtime-neutral Equipment setup boundary. The runtime still asks
`EquipmentService.suggest_for_profile(...)` for the concrete setup
recommendation; the new read-model preserves that payload and projects only the
existing `CelestialObject` fields consumed by Home/Object Detail. This makes
presentation ownership explicit without moving setup scoring into
`ObserverCapability` or `Q_target`. No `ObservableTargetValue`,
`PracticalTargetValue`, `SessionViability`, `RecommendationConfidence`, QML
payload field, Planner/Home/Best Object/Sky Compass ranking or runtime write is
changed. Future Equipment work should audit setup-score ownership before any
replacement path.

Implementation note for 1.13.2:
`docs/EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT.md` records the ownership audit for
the real `EquipmentService._configuration_score` formula. The audit treats
`angular_scale`, `magnification`, `exit_pupil`, `light_gathering`,
`seeing_compatibility` and `handling` as setup-score components, not as a
drop-in NSOM scalar. It confirms that the current Equipment score mixes target
traits, observer configuration, sky quality, seeing and presentation-local
practicality, so it cannot be replaced directly by `ObservableTargetValue`,
`PracticalTargetValue`, `Q_target` or `RecommendationConfidence`. No runtime
ranking, payload, QML, logging, network call or runtime write is changed; the
next safe Equipment step is a component read-model with strict parity tests.

Implementation note for 1.13.3:
`EquipmentSetupScoreReadModel` and `EquipmentSetupScoreReadModelBuilder` expose
the real `EquipmentService._configuration_score` components as an immutable
internal boundary. The service still owns the setup score and still returns the
same clamped scalar; the read-model makes `angular_scale`, `magnification`,
`exit_pupil`, `light_gathering`, `seeing_compatibility` and `handling` explicit
for audits and comparison tooling. `EquipmentNsomComparisonService` now consumes
this boundary instead of recomputing component breakdowns privately. This is not
a default-off Equipment replacement path and does not move setup scoring into
`ObservableTargetValue`, `PracticalTargetValue`, `Q_target` or
`RecommendationConfidence`. No runtime ranking, QML payload, logging, network
call or runtime write is changed.

Implementation note for 1.13.4:
`docs/EQUIPMENT_NSOM_DEFAULT_OFF_PATH_POLICY_AUDIT.md` records the policy
decision for Equipment. Equipment does not get a default-off NSOM replacement
path now because setup recommendation is not a target ranking surface:
`EquipmentService` owns concrete eyepiece, zoom-position, Barlow, binocular and
fallback-payload choices for a selected target. `ObserverCapability`, `Q_target`
and `PracticalTargetValue` can describe observer capability and practical value
metadata, but they do not replace setup-row selection. Equipment therefore
remains setup-local with explicit NSOM ownership, presenter and component
boundaries. No runtime scoring, payload, QML, logging, network call or runtime
write is changed.

Implementation note for 1.13.5:
`docs/EQUIPMENT_NSOM_MIGRATION_CLOSEOUT.md` closes the Equipment backend NSOM
migration for the current setup-local scope. The final policy is that Equipment
does not need a default-off NSOM replacement path now: `EquipmentService` keeps
owning concrete setup recommendation, while shared ObserverCapability/Q_target,
presenter, setup-score ownership and component read-models make NSOM boundaries
explicit for future explanation or UI work. This closeout changes no runtime
score, setup recommendation, Planner/Home/Best Object/Advanced Observing/Sky
Compass/Detail path, QML payload, logging, network call or runtime file write.

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
ObserverCapabilitySummary Q_target =
    project(ObserverCapabilityProfile, target_requirements)

PracticalTargetValue P = O * Q_target
```

Where:

- `O` is objective observable target value under the current sky;
- `ObserverCapabilityProfile` is multidimensional;
- `Q_target` is a target-specific summary of that profile when a scalar is
  needed;
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

### 3.7 Observation Opportunity

Owner: `PlannerScoringService` should build and rank this concept; upstream
services provide its ingredients.

Purpose: represent one concrete thing the Planner can choose.

Planner should not rank abstract targets directly. It should rank observing
opportunities:

```text
ObservationOpportunity
    target
    PracticalTargetValue
    observing_window_quality
    chronology
    SessionViability
    practical_constraints
    RecommendationConfidence annotations
```

This is the first layer that can legitimately combine target, observer, time
and session. It answers:

```text
Is this a good opportunity for this observer during this session?
```

It does not recompute the Universe, the Sky or the Observer.

### 3.8 Seeing Position in the Model

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

### 3.9 Session Viability

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

### 3.10 Recommendation Confidence

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

### 3.11 Planner Ranking

Owner: `PlannerScoringService`.

Purpose: select and order observation opportunities.

Planner consumes `ObservationOpportunity` items that already combine:

- practical target value;
- useful observing window quality;
- chronology;
- session viability as block/cap/context, not as target physics;
- confidence as presentation/caution, not as a hidden score penalty;
- practical difficulty;
- observing-window practicality.

Planner should not rank raw targets directly, and it should not reapply Moon,
light pollution, AOD or PM if those have already been represented upstream.

Recommended future shape:

```text
ObservationOpportunityValue =
    PracticalTargetValue * target_weight
    + observing_window_quality * window_weight
    + chronology_fit * chronology_weight
    + practical_constraints * practicality_weight

PlannerOutput =
    select/order ObservationOpportunity items
    annotate with SessionViability S
    annotate with RecommendationConfidence K
```

If session viability is very poor, Planner may block or downgrade the session
state, but the target's observable value remains interpretable.

Chronological display should remain a presentation step after opportunity
selection.

Planner should consume `ObservationOpportunity`; it should not reconstruct Moon,
sky brightness, AOD, PM, transparency, observer capability or practical target
value itself. Planner answers:

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

### 3.12 Presentation

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
| Observing window | opportunity-related | planner service | `ObservationOpportunity` component |
| Planner chronology | opportunity/planner-related | planner service | opportunity selection and display order |
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

ObserverCapability profile summary Q_target = 0.82 for the active profile
PracticalTargetValue P = 52.5 * 0.82 = 43.1
ObservationOpportunity value = P plus window/session/practical context

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

ObserverCapability profile summary Q_target = 0.90 for a telescope profile with useful magnification
PracticalTargetValue P = 78.3 * 0.90 = 70.5
ObservationOpportunity value = P plus window/session/practical context

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

ObserverCapability profile summary Q_target = 0.88
PracticalTargetValue P = 64.7 * 0.88 = 56.9
ObservationOpportunity value = P plus window/session/practical context

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

ObserverCapability profile summary Q_target = 0.75 without a suitable filter / EAA aid
PracticalTargetValue P = 48.7 * 0.75 = 36.5
ObservationOpportunity value = P plus window/session/practical context

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

ObserverCapability profile summary Q_target = 0.95
PracticalTargetValue P = 90.3
ObservationOpportunity value = P plus window/session/practical context

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

ObserverCapability profile summary Q_target = 0.82
PracticalTargetValue P = 43.1
ObservationOpportunity value = P plus poor session context

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

- construction and ranking of `ObservationOpportunity` items;
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
- practical target value before `ObservationOpportunity` construction.

## 11. Recommended Migration Roadmap

### Step 1: Mathematical constants and test fixtures

- Define target classes, sensitivity profiles, visibility components and caps in
  tests first.
- Define `ObserverCapability` and `PracticalTargetValue` fixtures as separate
  from `ObservableTargetValue`.
- Define `ObservationOpportunity` fixtures as separate from raw target fixtures.
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
  - consumes `ObservationOpportunity` items;
  - keeps practical target value, session viability and confidence explicit
    inside the opportunity;
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

- Status: Planner, Home `recommendedDeepSky` and Best Object have now moved to
  staged default-on NSOM consumers with explicit rollback paths.
- Future work should review score presentation, AdvancedObserving and Sky
  Compass consumers before removing remaining legacy score surfaces.
- Status update for 1.8.0: AdvancedObserving review has started as a
  developer-only comparison layer; runtime advanced scores are still legacy.
- Status update for 1.8.1: AdvancedObserving comparison now has a static
  developer-only report; no default-off runtime path exists yet.
- Status update for 1.8.2: AdvancedObserving report review was completed
  without implementation changes.
- Status update for 1.8.3: AdvancedObserving policy/readiness is documented and
  has no blocker for a separate default-off NSOM runtime path.
- Status update for 1.8.4: AdvancedObserving now has an internal default-off
  NSOM runtime path with legacy default and no QML exposure.
- Status update for 1.8.5: AdvancedObserving forced-on runtime review is
  documented; the path is safe to keep but blocked for default-on by shared
  `advancedScores` downstream consumers.
- Status update for 1.8.6: downstream policy is documented; `advancedScores`
  stays legacy-compatible until Planner and NotificationService are split from
  the shared presentation score.
- Keep Sky Compass consuming prepared targets only.
- Expose recommendation confidence only after scores and labels remain stable.

### Step 9: Observer capability expansion

- Keep equipment as the first observer-capability implementation.
- Add experience level, observing style, smart telescope/EAA support and
  preferences only after the physics model is stable.
- Verify no observer-specific factor enters `ObservationConditionsService`.

## 12. Tests Required Before Enablement

### Characterization tests

- Legacy Planner output unchanged through explicit rollback.
- Legacy Home/Detail output unchanged through explicit rollback/fallback.
- Legacy Best Object unchanged through explicit rollback/fallback.
- Current equipment recommendations unchanged with flags off.
- Observable target value remains identical for two observers under the same sky.
- Practical target value can differ for two observers under the same sky.
- `ObserverCapability` can expose multiple dimensions without requiring a
  single scalar in diagnostics.
- `ObservationOpportunity` combines practical target value, observing window,
  chronology, session viability, constraints and confidence annotations.
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
- Planner ranks `ObservationOpportunity` items, not raw targets.
- Observation opportunity construction cannot mutate intrinsic target quality,
  effective observability or observer capability.

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
   multidimensional `ObserverCapability`, `PracticalTargetValue`,
   `ObservationOpportunity`, `SessionViability` and `RecommendationConfidence`
   as separate mathematical concepts;
3. add formal mathematical constants and regression fixtures;
4. implement Planner-only experimental scoring behind a flag;
5. compare output against current Planner for many scenarios;
6. only then decide whether the new model should replace the current layered
   scores.

This preserves NightScope's current stable behavior while moving toward a
single explainable mathematical system where each physical phenomenon has one
owner and one role. The Universe defines the intrinsic target. The Sky defines
effective observability and objective observable target value. The Observer
defines multidimensional capability and practical target value. Observation
opportunity combines the target, observer, time and session into what Planner
can rank. Session viability describes whether tonight is usable, and confidence
describes how much trust NightScope has in the data behind the recommendation.
