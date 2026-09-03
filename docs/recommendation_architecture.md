# NightScope Recommendation Architecture

This document describes the current recommendation architecture in NightScope
`1.45.20`. The typed profile, binocular and recommendation boundaries originated
in the NightScope 1.1 refactors and remain the active design.

The recommendation system has one main rule:

> Python owns recommendation decisions. QML renders the recommendation data
> already produced by the backend.

## High-Level Flow

```text
TargetObservationTraits
+
ObservationConfigurationBuilder
    |
    v
ObservationConfiguration
    |
    v
RecommendationCandidate
    |
    v
EquipmentService scoring and selection
    |
    v
RecommendationPresenter
    |
    v
CatalogueRecommendationWorkflow
    |
    v
AppController (Qt scheduling and state application)
    |
    v
Home / Object Detail / Calendar / Planner
```

Two inputs meet inside the recommendation pipeline:

- `TargetObservationTraits` describes what the target needs.
- `ObservationConfigurationBuilder` describes what the active profile can do.

`EquipmentService` compares those two sides with weighted scoring and selects
the best `RecommendationCandidate`. `RecommendationPresenter` serializes the
selected candidate and chooses display-only role representatives from the
already-scored candidates for the UI-facing DTO used by `AppController` and
QML.

Since `1.45.1`, `CatalogueRecommendationWorkflow` owns the synchronous,
framework-independent preparation of the complete catalogue recommendation
snapshot: equipment setup enrichment, condition read models, NSOM ranking,
best-object selection, night planning and the Sky Compass payload. The Qt
controller owns request generations, debounce/timers, worker lifecycle, stale
result rejection and application of the prepared immutable snapshot. Snapshot
contracts live in `astro_viewer.app.application.snapshots`, so the application
workflow does not depend on the view-model module.

Since `1.45.2`, observing status/explanation text and weather/session read
models are produced by dedicated presentation services. Shared parsing and
night-clock functions live in `observing_time`; weather window selection lives
in `weather_presentation`. `AppController` supplies current runtime state and
retains compatibility wrappers, but no longer owns those presentation
algorithms.

Since `1.45.3`, catalogue record normalization, designation-aware search,
filters, localization projections and static observability checks live in
dedicated catalogue services. A separate detail service builds catalogue
objects and metadata. The controller retains UI model notifications, runtime
visibility caches and serialized access to the astronomy engine.

Since `1.45.4`, loading and mapping equipment catalogues, parsing equipment
form values, profile inventory queries and equipment presentation read models
live in framework-independent services. `AppController` retains repository
mutations, localized validation feedback and Qt signals, while compatibility
wrappers keep the established integration surface stable.

Since `1.45.5`, condition-input DTOs live in the model layer and optical
configuration builders depend on a narrow protocol rather than the complete
recommendation service. Production imports are acyclic and checked from the
Python AST; compatibility exports preserve the established condition-input
imports for external callers.

## Responsibilities

### TargetObservationTraits

`TargetObservationTraits` is the normalized target-observation model.

It reads a `CelestialObject` and exposes:

- object type and lower-case object type
- parsed magnitude
- parsed apparent size in arcminutes
- angular size in degrees
- Messier `max_angular_size_deg`, when available
- max altitude in degrees
- `recommended_observation_type`
- surface-brightness proxy
- booleans for wide-field, high-magnification, general, planetary/lunar and
  deep-sky targets

It prefers machine-readable Messier metadata and falls back to text parsing and
legacy object-type interpretation when metadata is missing.

### ObservationConfigurationBuilder

`ObservationConfigurationBuilder` is target-agnostic.

It enumerates every physically available observing configuration from the
active profile. It does not know about targets, object types, Messier metadata,
scores, rankings or explanations.

It currently builds:

- telescope configurations from assigned telescopes, eyepieces and Barlows
- binocular configurations from assigned binoculars

### ObservationConfiguration

`ObservationConfiguration` is the normalized optical setup model.

It represents one complete setup and stores:

- `configuration_id`
- `equipment_type`
- magnification
- exit pupil
- true field of view, when known
- limiting magnitude estimate, when known
- resolution estimate, when known
- image-stabilization flag
- references to telescope, eyepiece, Barlow or binocular as applicable
- sampled zoom focal position when applicable

The recommendation system should not need to infer whether a setup came from a
telescope, a telescope plus Barlow, a zoom eyepiece position or a binocular.
That information is normalized here.

### RecommendationCandidate

`RecommendationCandidate` wraps an `ObservationConfiguration` with
recommendation-scoring metadata:

- score
- display label
- detail label
- Barlow multiplier and label
- telescope name

It exposes convenience properties for equipment type, setup type, telescope,
eyepiece, Barlow, binocular, focal position, magnification, true field and exit
pupil.

This is the primary internal representation passed from configuration
enumeration into scoring and presentation.

### EquipmentService

`EquipmentService` owns recommendation scoring and selection.

Its responsibilities are:

- build ranked candidates for one telescope or the whole active profile
- derive target profiles from `TargetObservationTraits`
- score telescope configurations against target profiles
- score binocular configurations conservatively
- apply seeing-limited magnification
- apply Barlow preference rules
- select the recommended candidate
- build profile telescope capability DTOs from `ObservationConfiguration`
  objects
- choose fallback DTOs through `RecommendationPresenter` when no useful optical
  setup exists

It does not own QML layout. It still contains the central scoring logic and is
the main domain service for equipment recommendations.

### RecommendationPresenter

`RecommendationPresenter` owns UI-facing serialization.

It converts selected `RecommendationCandidate` objects into the existing DTO
shape consumed by QML:

- `setupText`
- `setupOptions`
- `bestEyepiece`
- `barlow`
- `difficulty`
- `alternative`
- `highMagnification`
- `wideField`
- `explanation`
- `equipmentType`
- `setupType`
- `selectionScore`

It formats telescope, binocular, naked-eye and fallback recommendations without
changing the selected recommendation or any candidate score. Its
`high_magnification` role is a secondary presentation choice, not another
ranking pass: it first excludes telescope configurations above two times the
aperture in millimetres or below a 0.45 mm exit pupil. For faint extended
galaxies, nebulae and supernova remnants with a surface-brightness proxy of at
least 13.5, it also prefers no Barlow, an exit pupil of at least 1 mm and,
when target size is known, a field at least 105% of that size. The highest
magnification that survives is shown; if none survives, the existing fallback
keeps the role populated. These rules never replace the candidate selected by
`EquipmentService`.

Each item in `setupOptions` keeps the physical setup identity (`detailLabel`,
`telescopeName`, `barlow`, metrics) and also exposes `displayLabel` for UI
rendering. `displayLabel` matches `detailLabel` in normal cases, but includes
the telescope name when two visible options would otherwise share the same
eyepiece/focal label, for example two different telescopes both using `32 mm`.
This disambiguation is presentation-only and does not affect scoring,
candidate selection or duplicate suppression.

### AppController

`AppController` is the application-facing coordinator.

It:

- reads the active profile equipment
- calls `EquipmentService.suggest_for_profile()`
- stores the presenter DTO fields into `CelestialObject`
- exposes objects and recommendations to QML
- keeps Calendar recommendations aligned with Home and Object Detail by using
  the same profile-aware recommendation path

It also contains some object-detail explanatory text helpers. Those helpers are
presentation-oriented and should not become a second recommendation decision
engine.

### QML / UI

QML should render backend recommendation data.

Home now uses the backend-provided `Consigliato` setup option and
`equipmentExplanation`. It no longer decides that a target should display
`Campo largo` or `Alternativa` by inspecting object type strings.

Object Detail, Calendar and Planner consume the same backend fields. UI code may
format a binocular setup differently from a telescope setup, but it should not
choose the recommendation.

## Telescope Path

### Configuration Generation

For telescope profiles, the builder generates combinations of:

```text
assigned telescope
x assigned eyepiece
x assigned Barlow option
```

The Barlow options include the explicit no-Barlow setup plus one alternative
for each distinct assigned multiplier greater than 1.0. Multiple owned Barlows
with the same multiplier are labeled as equivalent options and are not scored
as duplicate optical configurations.

For each combination, `EquipmentService.telescope_configuration_values()`
provides:

- magnification
- true field of view
- exit pupil
- limiting magnitude estimate
- resolution estimate

These become `ObservationConfiguration` instances.

### Zoom Eyepiece Sampling

Zoom eyepieces remain a single catalogue/profile equipment record.

Target-aware zoom sampling is preserved by passing a focal-position provider
from `EquipmentService` into `ObservationConfigurationBuilder`. The provider
derives an ideal focal length from the target profile, but zoom eyepieces with
configured click positions generate only those physically selectable positions.
For example, the Baader Hyperion Zoom 8-24 mm is evaluated at:

- 24 mm
- 20 mm
- 16 mm
- 12 mm
- 8 mm

Zoom eyepieces without explicit click-position data fall back to a conservative
range sample using high, midpoint and low positions. Duplicate sampled positions
and duplicate presentation options are removed.

This keeps the builder target-agnostic while preserving the existing
target-aware zoom recommendation behavior and avoids recommendations such as
23.8 mm or 15.7 mm for click-stop zooms.

### Telescope Target Profiles

`EquipmentService._target_profile()` derives the observing profile from
`TargetObservationTraits`.

When Messier metadata exists:

- `WideField` favors lower magnification, larger true field and no Barlow.
- `HighMagnification` favors higher magnification and allows Barlow when seeing
  supports it.
- `General` favors medium magnification and balanced exit pupil/field.

Planetary and lunar targets remain special physical cases because seeing,
altitude and useful magnification matter strongly.

When metadata is absent, legacy object-type fallbacks still apply for globular
clusters, planetary nebulae, open clusters, galaxies and nebulae.

### Weighted Scoring v2

Recommendation Engine v2 scores each `RecommendationCandidate` by comparing:

```text
TargetObservationTraits
against
ObservationConfiguration / RecommendationCandidate
```

Object type is now a fallback or modifier when better metadata is missing. The
primary scoring dimensions are optical and observational:

| Dimension | Weight |
| --- | ---: |
| Angular scale compatibility | 24 |
| Magnification suitability | 24 |
| Exit pupil suitability | 16 |
| Light gathering / limiting magnitude | 16 |
| Seeing compatibility | 10 |
| Stability / Barlow / handheld practicality | 10 |

The score is intentionally explainable. Each component maps to an observing
concern a visual observer would recognize:

- angular scale compares target size against true field when available
- magnification compares the setup against the observing mode
- exit pupil rewards useful brightness/contrast balance
- light gathering considers aperture, binocular objective diameter and limiting
  magnitude
- seeing compatibility preserves the seeing-limited magnification cap
- stability/Barlow/handling preserves conservative Barlow behavior and
  binocular handheld practicality

Representative behavior:

- M31 may prefer a `32 mm` eyepiece or binoculars because its large angular
  scale needs a wide field.
- M45 and M44 favor wide-field telescope configurations or binoculars.
- M57 and M76 remain high-magnification telescope targets.
- M27, M97 and M107 behave as `General` targets and usually prefer
  medium-magnification telescope configurations when available.
- Medium globular clusters such as M5, M92 and M15 remain `General` targets but
  bias toward medium magnification instead of low-power wide-field behavior.
- Planets and the Moon remain special physical cases because seeing, altitude
  and useful magnification dominate their visual observing setup.
- `object_type` remains a fallback/modifier when metadata is missing.
- Binocular true field of view is not stored yet, so binocular field suitability
  remains conservative and class-based by magnification range.

### Seeing-Limited Magnification

`EquipmentService._seeing_limited_magnification()` caps useful magnification by
seeing score and telescope aperture.

The target profile stores `maxUsefulMag`; weighted scoring penalizes any
candidate exceeding that limit. This keeps planetary and high-magnification
recommendations from selecting unrealistic setups under poor seeing.
Missing seeing is treated as unknown, not excellent: the engine applies a
conservative cap so planetary recommendations do not default to very high power
unless seeing data genuinely supports it.

### Barlow Selection Rule

All telescope candidates are scored, including no-Barlow and Barlow variants.

Barlow use is:

- penalized when the target profile is not Barlow-friendly
- lightly penalized even when allowed
- additionally penalized for wide-field mode

After scoring, `_recommended_candidate()` keeps the best candidate unless it is
a Barlow telescope candidate only marginally better than the best no-Barlow
candidate. If the Barlow advantage is not meaningful, the no-Barlow candidate is
selected.

## Binocular Path

### Catalogue and Profile Support

Binoculars have a global catalogue and can be assigned to profiles. The
recommendation engine only considers binoculars assigned to the active profile.
Global catalogue binoculars are ignored unless assigned.

The current binocular model stores:

- brand/model name
- magnification
- objective diameter in millimeters
- image-stabilized flag

### Configuration Generation

One assigned binocular creates one `ObservationConfiguration`.

The builder sets:

- `equipment_type = "Binocular"`
- magnification from the binocular model
- exit pupil as `objective_diameter_mm / magnification`
- image-stabilized flag

Binocular true field of view is currently not stored, so
`true_field_of_view_deg` remains `None`.

### Binocular Scoring Principles

Binocular scoring is conservative and target-aware inside `EquipmentService`.

Wide-field targets receive meaningful bonuses, especially when angular size is
large. Examples include M31, M45, M44 and other large bright targets.

High-magnification targets are strongly penalized. Small planetary nebulae,
planets and compact targets should prefer telescopes when available.

General targets may be acceptable in binoculars, but binoculars should not
automatically beat a suitable telescope. Magnitude, angular size, objective
diameter, exit pupil, magnification class, image stabilization and sky quality
all influence the binocular score.

Current binocular assumptions:

- 7x to 10x: wide-field capable
- 11x to 15x: medium/wide capable
- 16x and higher: narrower binocular use, with handheld penalty unless image
  stabilized
- exit pupil around 4-6 mm is favorable
- image stabilization gives a small bonus, especially around 12x-18x

### Binocular-Only Profiles

If a profile has binoculars and no telescopes:

- wide-field targets can receive useful binocular recommendations
- high-magnification targets can still return a cautious binocular
  recommendation rather than a telescope placeholder
- if no optical equipment exists, the existing naked-eye fallback remains

### Mixed Profiles

In mixed profiles, telescope and binocular configurations become candidates in
the same ranked list.

This allows:

- binoculars to win for large wide-field targets
- telescopes to win for high-magnification and detail-oriented targets
- general objects to remain conservative

## Catalogue Observation Metadata

Physical catalogue objects include two machine-readable recommendation fields,
independently from their Messier, Caldwell or future designations.

### max_angular_size_deg

`max_angular_size_deg` is the largest apparent angular dimension of the target,
stored in degrees.

It is preferred over parsing textual apparent-size strings. It allows the
recommendation system to reason about observing scale directly.

Examples:

- very large objects push toward wide-field telescope configurations or
  binoculars
- very small objects push away from binoculars and toward higher-magnification
  telescope setups

### recommended_observation_type

Allowed values:

- `WideField`
- `General`
- `HighMagnification`

This field describes the recommended observing scale. It influences both
telescope target profiles and binocular scoring.

Current behavior:

- `WideField`: lower magnification, wider field, Barlow-unfriendly, binoculars
  competitive
- `General`: medium magnification, balanced exit pupil and field, binoculars
  considered cautiously
- `HighMagnification`: higher magnification, binocular penalty, Barlow may be
  acceptable if seeing supports it

### Fallback Behavior

When metadata is missing or invalid, `TargetObservationTraits` falls back to:

- planet/lunar IDs and object type
- parsed apparent-size text
- legacy object-type interpretation

Legacy fallbacks keep older catalogue objects functional while allowing seeded
catalogue targets to use a data-driven observing model.

## UI Presentation

### Backend Decision Ownership

The backend owns:

- recommended setup selection
- setup option roles
- explanation text
- setup type
- equipment type
- binocular/telescope distinction

QML should render those fields.

### Home

Home renders:

- backend `Consigliato` option from `setupOptions`
- backend `equipmentExplanation`
- binocular setup formatting based on `equipmentType`

Home no longer chooses `Alternativa` or `Campo largo` by reading object type
strings.

### Object Detail

Object Detail uses `recommendedSetupType`, `setupOptions` and `equipmentType` to
display telescope and binocular setups without empty eyepiece/Barlow
placeholders.

`AppController._setup_reason()` still builds detail-page explanatory text from
the selected setup and object type. This is presentation logic, but it should
not become a separate recommendation decision path.

### Calendar

Calendar now uses `_calendar_profile_setup()`, which calls the same
profile-aware `EquipmentService.suggest_for_profile()` path used by Home and
Object Detail. This prevents Calendar from bypassing binoculars or mixed-profile
recommendations.

Meteor showers and some lunar/eclipse event text remain event-specific because
they are not ordinary equipment recommendations.

### Planner

Planner items receive the `recommended_setup` already attached to
`CelestialObject` after `AppController._apply_equipment()` has run. Planner
also receives the telescope selected for each target from the equipment setup
read model.

Planner ranking is owned by `PlannerNsomScoringService`. It combines canonical
observable target value with target-specific observer capability, timing and
binary Session viability. `NightPlannerService` remains responsible for weather
blocking, candidate selection, duplicate-name suppression and chronological
plan presentation.

## Profile Capabilities

The profile telescope capability section now derives its available telescope
configurations from
`ObservationConfigurationBuilder.build_telescope_configurations()`.

The UI-facing capability DTO still has the same shape as before:

- available magnification range
- exit pupil range
- true field range
- `availableConfigurations`
- `availableConfigurationsText`

This section intentionally includes only telescope, eyepiece and Barlow
configurations. Assigned binoculars remain excluded from the legacy telescope
capability summary because profiles already expose a dedicated `Binocoli del
profilo` section with binocular-specific derived values such as exit pupil.

This keeps the old telescope capability display visually unchanged while
removing the duplicate manual telescope configuration enumeration path.

## Known Technical Debt

### EquipmentService Still Centralizes Scoring

Severity: Medium.

`EquipmentService` still owns target-profile derivation, telescope scoring,
binocular scoring, seeing handling, Barlow preference and candidate selection.
The responsibilities are clearer than before, but the class remains the central
recommendation decision point.

Possible future cleanup: extract a dedicated `ConfigurationScorer` or separate
telescope/binocular scorer classes while preserving the same
`RecommendationCandidate` inputs.

### Planner Capability Is Telescope-Centric

Severity: Medium.

Planner uses the target-specific selected telescope in observer capability.
Binocular and naked-eye recommendations preserve their setup presentation, but
the scalar observer projection remains less detailed than the full
`ObservationConfiguration` candidate model. A future extension can project
those configuration types without changing Universe or Sky factors.

### QML Must Remain Presentation-Only

Severity: Low to Medium.

Home has been cleaned up, but UI code should continue to be reviewed when new
equipment types are introduced. QML may branch on `setupType` or
`equipmentType` for display, but should not decide which setup is better.

### AppController Contains Some Presentation Reason Text

Severity: Low.

`AppController._setup_reason()` still formats object-detail explanations using
object type and selected setup metrics. This is acceptable as presentation
logic, but it overlaps conceptually with `RecommendationPresenter` explanation
formatting.

Possible future cleanup: move all recommendation explanation formatting into
`RecommendationPresenter`.

### Profile Capability DTOs Still Return Dictionaries

Severity: Low.

Profile capability display now derives configurations from
`ObservationConfigurationBuilder`, but still serializes them into the existing
dictionary-shaped QML DTO. This is acceptable for compatibility, but a future
typed presenter could make the boundary cleaner.

### Binocular True Field Is Not Stored

Severity: Low to Medium.

Binocular scoring uses conservative magnification-class assumptions because the
binocular catalogue does not store true field of view. This remains sufficient
for the current runtime, but precise binocular FOV would improve future
wide-field matching.

## Deferred Recommendation Work

Recommended follow-up work:

- extract scoring from `EquipmentService` into a dedicated
  `ConfigurationScorer`
- keep `EquipmentService` focused on orchestration and candidate selection
- add binocular true field of view if the catalogue model is expanded
- make Planner ranking more configuration-aware
- consolidate all recommendation explanation text in `RecommendationPresenter`
- keep QML presentation-only as new setup types are introduced

## Smart Telescope Path

Schema 24 represents a smart telescope as a category of `TelescopeModel`, not
as an optical design and not as a separate equipment catalogue. Category
`SMART_INTEGRATED` can therefore coexist with an optical type such as
`APOCHROMATIC_REFRACTOR`. Schema 25 adds the one-to-one
`SmartTelescopeCapability` contract. It stores explicit visual/external-accessory
admission flags plus the primary astronomical sensor geometry, live-stacking,
video, mosaic, exposure-control and integrated-filter capabilities.

The runtime paths are deliberately separate:

- `ObservationConfigurationBuilder` admits a telescope to the visual
  eyepiece/Barlow path only when both optical visual observation and
  interchangeable eyepieces are declared.
- A smart-only profile receives score-neutral routing to the photographic EAA
  card. It does not create magnification, exit-pupil or true-field values and
  does not inject photographic suitability into visual or NSOM ranking.
- `ImagingTrainBuilder` creates the integrated camera from the telescope
  capability record. External profile cameras and optical modifiers are
  ignored unless the smart model explicitly declares those capabilities.
- A profile containing traditional and smart telescopes keeps separate
  candidates: normal telescope/camera trains for the former and integrated
  trains for the latter. No camera or eyepiece is crossed between modalities.
- Incomplete smart sensor geometry is valid catalogue state but produces no
  photographic configuration. The presenter reports insufficient integrated
  specifications instead of falling back to an unrelated external camera.

Seestar S30 and S50 seed one primary astronomical channel. The S30 wide-angle
camera is treated as a pointing/scenery channel and is not used as a second
astronomical train. Both seeded models disallow optical visual use,
interchangeable eyepieces, external cameras and external optical modifiers.
Their photographic presentation uses native field and pixel scale, describes
sub-exposure control as device-managed, emphasizes total stacking time, gates
oversized-target mosaic guidance on the persisted capability and warns when a
planet is poorly sampled at native scale. Solar admission still requires the
exact profile-to-telescope full-aperture safety declaration.

## Future Extension Points

### Spotting Scopes

Spotting scopes can likely reuse much of the telescope path if they have focal
length/aperture and compatible eyepieces. If they are fixed-zoom instruments,
they may be better represented as one or more direct configurations.

The builder should normalize them into `ObservationConfiguration` objects before
scoring.

### Focal Reducers

The current `ReducerRecommendationService` is presentation-only. For targets
explicitly marked as photographic reducer opportunities, it matches the
telescope already selected by `EquipmentService` against exact normalized
compatibility links. It reports owned products first or catalogue products as
unavailable, without changing the selected configuration.

A future camera/sensor-aware optical-train model could make focal reducers
configuration modifiers similar to Barlows but with inverse optical effects:

- lower magnification
- larger true field
- larger exit pupil

That future calculation should be included by the builder as part of
configuration enumeration, not handled in QML. It requires camera sensor,
image-circle and backfocus data that the current visual setup model does not
own.

### Photographic Optical-Train Foundation

The first backend-only photographic foundation is separate from
`ObservationConfiguration`, `RecommendationCandidate` and `EquipmentService`.
It currently follows this target-neutral flow:

```text
AstronomyCameraCatalog / CameraBodyCatalog
    |
    v
ImagingCameraAdapter
    |
    v
ImagingCamera
    |
    + Telescope + optional imaging reducer or Barlow
    |
    v
ImagingTrainBuilder
    |
    v
ImagingTrainConfiguration
```

`ImagingCamera` preserves the technical distinction between full-resolution
astronomy-camera FPS and camera-body FPS at a declared video resolution.
`ImagingTrainConfiguration` stores the selected physical equipment plus
effective focal length, focal ratio, horizontal/vertical/diagonal field of
view, pixel scale and the remaining reducer-to-sensor backfocus spacing when
known.

The builder always emits the prime-focus train. It additionally emits only
reducers explicitly marked for imaging and exactly linked to the telescope,
plus the supplied optically distinct Barlow multipliers as separate
alternatives. Reducers and Barlows are never stacked. Equal-multiplier Barlows
collapse to one labeled choice because the current model has no further
optical discriminator. Reducer links are fail-closed: generic compatibility
text is not stored or interpreted, and an unconfigured reducer generates no
train. The caller owns inventory scope, so the runtime assembler passes
active-profile equipment without the builder ever reading catalogues or
profile state itself.

The builder deliberately does not classify targets, score candidates, choose
between still imaging and video, estimate exposure, serialize a UI DTO or
register with `AppController`.

### Photographic Target And Configuration Scoring

The second backend-only layer consumes the optical trains without changing
their enumeration:

```text
CelestialObject
    |
    v
ImagingTargetTraitsAdapter ---> ImagingTargetTraits
                                      |
ImagingTrainConfiguration ------------+
                                      |
                                      v
                        ImagingRecommendationService
                                      |
                                      v
                        ImagingRecommendationCandidate
```

`ImagingTargetTraits` owns photographic class, still/video choice, physical
angular dimensions and the curated reducer preference. It does not consume the
visual target score, observability, Home rank or NSOM values. Solar
recommendations default to unsupported. The scorer accepts a caller-supplied
set of full-aperture-solar-filter telescope IDs and retains only the exact
matching configurations; it does not infer safety capability from telescope
models or camera classes.

The scorer is additive rather than multiplicative. Its explicit components
cover framing, sampling, camera role, mount capability and capture behavior;
still and video use separate component weights and separate FPS semantics.
Planetary video also assigns 15% to a saturating telescope-aperture component,
while whole-disc Sun/Moon video retains its original five-component policy.
The result is a static equipment-suitability score, not a probability and not
an exposure recommendation.

A camera body's declared video resolution does not prove active sensor crop,
binning or readout. Its video field and image-scale components therefore stay
neutral and are recorded as missing rather than borrowing full still-sensor
geometry. If such trains otherwise tie, prime focus is the conservative first
choice.

`data_completeness` and stable missing-input codes remain parallel metadata:
they never scale the score. This makes current limits such as seeing, sky
background, tracking accuracy, mechanical adapters and image circle visible
without inventing values. A known negative reducer spacing is the only modeled
accessory-compatibility condition that removes a candidate at this layer;
non-positive or non-finite optical geometry is also rejected.

`AppController` does not own or invoke the service directly. The private
runtime assembler owns it and can call it only on demand; it remains absent
from `EquipmentService`, QML, Home, Planner, Sky Compass and NSOM.

### Photographic Exposure Planning

The third backend-only layer starts from one already-scored still candidate:

```text
ImagingRecommendationCandidate + ImagingSessionConditions
                             |
                             v
                 ImagingExposureAdvisor
                             |
                             v
                  ImagingExposureAdvice
```

The advisor returns ranges for one sub-exposure and total stacked integration,
an indicative frame-count range, the conservative mount limit and every
multiplier used by policy version `imaging_exposure_v2`. It never changes the
candidate score and returns no still-exposure advice for video targets. A
900-minute planning ceiling is censored metadata, not a fabricated exact
endpoint: the presentation uses a lower-bound value and explains that usable
light frames can be accumulated over multiple nights.

The policy consumes effective focal ratio, target brightness, explicit SQM or
a Bortle fallback, transparency and complete Moon geometry. Mount taxonomy
caps the sub-exposure, with stricter limits for field rotation and manual
tracking. Missing inputs use named neutral assumptions and reduce confidence.
Gain/ISO, read noise, autoguiding, measured tracking accuracy and filter
passband remain explicit unmodeled limitations, so the result is a conservative
broadband planning interval rather than camera calibration.

Current and nightly maximum target altitude add score-neutral operational
warnings. In particular, a still target that never reaches 30 degrees is
identified as low for deep-sky imaging; the existing visual observing window
is not presented as a photographic-quality window.

This layer is not registered directly with `AppController` and remains absent
from `EquipmentService`, QML, Home, Planner, Sky Compass and NSOM. The private
runtime assembler can invoke it for a selected still candidate.

### Photographic Video Capture Planning

The sibling backend-only video layer consumes an already-scored solar, lunar
or planetary candidate:

```text
ImagingRecommendationCandidate + ImagingVideoSessionConditions
                             |
                             v
              ImagingVideoCaptureAdvisor
                             |
                             v
               ImagingVideoCaptureAdvice
```

Policy `imaging_video_capture_v2` returns a conservative duration range for
one independently stackable clip without image derotation, a planned FPS
range and the corresponding captured-frame range. Solar, lunar and all seven
planet profiles are explicit. The candidate score is never changed, and still
candidates receive no video advice.

An optional achievable FPS is authoritative. Without it, the camera's
full-resolution FPS or body video FPS is only an upper bound; when even that is
missing, the output remains a named target goal with low confidence. Seeing
and target altitude contribute warnings and completeness but never fabricate
an exact frame exposure or clip duration.

Camera bodies additionally report unknown video active area and pixel scale.
These inputs reduce completeness, and their still-sensor field of view is not
presented as verified video geometry.

Alt-azimuth GoTo retains the ordinary Jupiter window because short-frame
planetary capture does not require an equatorial mount. Field rotation caps
only longer clips; manual and unknown mounts use shorter conservative windows.
Exposure/gain and histogram, ROI/readout, actual transfer throughput, codec or
RAW format, atmospheric-dispersion correction, apparent diameter/phase, lucky
frame-selection fraction and image derotation remain explicit limitations.

This layer is not registered directly with `AppController` and remains absent
from QML, Home, Planner, Sky Compass and NSOM. The private runtime assembler
can invoke it for a selected video candidate.

### Photographic Runtime Assembly And Presentation

The runtime and selected-detail presentation boundaries are now implemented:

```text
active profile + current observing facts + CelestialObject
                         |
                         v
             ImagingRuntimeConditionsAdapter
                         +
             ImagingRuntimeInventory
                         |
                         v
              ImagingRuntimeAssembler
                         |
       ImagingTrainBuilder -> static rank -> best candidate
                         |
                  still OR video advisor
                         |
                         v
          ImagingRuntimeRecommendation
                         |
                         v
          ImagingRecommendationPresenter
                         |
                         v
      Object Detail photographic plan (selected target only)
```

The inventory snapshot includes only assigned telescopes, astronomy cameras,
camera bodies, imaging reducers and Barlows. A full-aperture solar-filter ID is
forwarded only if the same telescope is assigned to the active profile. This
keeps solar admission fail-closed and exact.

The condition adapter supplies SQM/Bortle, raw atmospheric transparency, Moon
illumination and target geometry to still planning, and seeing/current target
altitude to video planning. It deliberately does not reuse a conditioned visual
target score. NightScope has no camera-control telemetry, so achievable FPS
remains absent and the video advisor keeps its existing catalogue/goal
provenance.

Policy `imaging_runtime_v2` returns the best static candidate with exactly one
mode-specific advice object, or a stable unavailable status for missing
profile/inventory, invalid trains, solar safety gating or an unavailable
advisor. Conditions remain score-neutral.

`AppController` keeps the assembler behind a private Python method and exposes
only a localized `photographicRecommendation` DTO for the selected detail
target. The dedicated notify gate compares a semantic input signature:
target selection, photographic inventory and relevant current-condition
changes invalidate the card, while visual-only equipment changes do not. It
does not enqueue or recompute the catalogue, Home or Planner. There is no
photographic cache or worker.

The presenter exports no suitability score. It formats the winning optical
train, sensor field of view, image scale, effective focal geometry, reducer
back-focus spacing and exactly one capture plan. Still mode shows sub-exposure,
total integration, estimated sub-exposures and a conservative tracking limit;
video mode shows single-clip duration, planned FPS, estimated frames and FPS
provenance. A maximum of four prioritized operational notices includes
visibility/seeing/mount limits and explicit crop-or-mosaic guidance when a
known target is larger than the selected sensor field. Camera-body video
instead labels field and image scale as unverified and explains that video crop
or resampling may differ from the still sensor.

### Filters

The current `FilterRecommendationService` compares explicit target preferences
with the telescope already selected for the target, its aperture, the complete
filter catalogue and filters assigned to the active profile. Product minimum
aperture and target-specific thresholds remove unsuitable choices before the
service returns one primary choice and one optional color choice. Filters are
presentation metadata, not optical configurations, and do not alter score or
setup.

A future optical model could attach measured filter transmission and
camera/sensor response to `RecommendationCandidate` or a successor model, but
that is separate from the current visual recommendation.

### Additional Catalogues

Additional object catalogues should expose the same kind of machine-readable
observing metadata used by Messier:

- angular scale
- recommended observation type
- magnitude
- object class

The recommendation engine should continue moving from category shortcuts toward
matching target observing needs against available configuration capabilities.

## Current Architectural Direction

The current architecture is intentionally transitional:

- configuration enumeration is normalized
- recommendation candidates are typed
- binoculars participate in scoring
- Messier metadata influences telescope and binocular scoring
- Home renders backend recommendation decisions

The next long-term architectural improvement would be to extract scoring from
`EquipmentService` into a dedicated scorer while keeping the same flow:

```text
TargetObservationTraits
+
ObservationConfiguration
    |
    v
RecommendationCandidate
    |
    v
ConfigurationScorer
    |
    v
RecommendationPresenter
```
