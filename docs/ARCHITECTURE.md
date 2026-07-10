# NightScope Architecture

This document describes the current NightScope architecture as reviewed for the
v1.0 release candidate. It is descriptive, not a redesign proposal.

## Project Structure

NightScope is organized around a small desktop application package:

- `astro_viewer/main.py`: application entry point, CLI smoke-test entry points,
  QApplication setup and QML loading.
- `astro_viewer/app/ui`: QML pages, components, theme and presentation logic.
- `astro_viewer/app/viewmodels`: Qt-facing controller/ViewModel layer. The main
  object is `AppController`.
- `astro_viewer/app/services`: business services for astronomy, weather,
  observing quality, planning, equipment recommendations, light pollution,
  NASA/OpenAQ data providers, seeing/transparency and logging.
- `astro_viewer/app/astronomy`: astronomy engine protocol, mock fallback,
  Skyfield-based engine and coordinate parsing helpers.
- `astro_viewer/app/database`: SQLite bootstrap, migrations, repositories and
  import helpers.
- `astro_viewer/app/models`: dataclasses used as service and controller DTOs.
- `astro_viewer/data`: schema, catalog CSV files, seed data and Skyfield
  ephemeris files. The runtime SQLite database is created as `nightscope.db`
  next to the application/repository root and is not distributed as seed data.
- `astro_viewer/resources`: icons, images and themes consumed by QML and build
  packaging.
- `astro_viewer/tests`: unittest/pytest-compatible regression tests.
- `astro_viewer/tools`: one-off import, validation and packaging-support tools.
- `packaging`: PyInstaller spec, hooks and Windows build script.

## Architectural Style

The application follows a pragmatic MVVM-style structure:

- QML owns layout, visual state and user interaction.
- `AppController` exposes Qt properties, slots and signals to QML.
- Services contain most domain decisions and calculations.
- Repositories own persistence and SQLite access.
- Models are simple dataclasses used to move structured data between layers.

The current implementation is coherent, but the ViewModel/controller layer has
grown beyond a narrow presentation adapter. `AppController` also orchestrates
refresh flows, profile mutation, object formatting, weather digests, calendar
presentation and recommendation enrichment.

## NightScope Observation Model

NightScope's long-term scoring and planning direction is defined by
[NSOM 1.0 - NightScope Observation Model](NIGHTSCOPE_OBSERVATION_MODEL_1_0.md).

NSOM separates:

- Universe / Intrinsic Target
- Sky / Observation Environment
- Effective Observability
- Observable Target Value
- Observer Capability
- Practical Target Value
- Observation Opportunity
- Planner
- Recommendation Confidence

Future scoring changes should be checked against this model before
implementation.

Current implementation status for `1.8.6`: `astro_viewer/app/models/nsom.py`
contains the first internal immutable NSOM core DTOs for Universe, Sky,
Observer, Session, Opportunity and Confidence ownership boundaries.
`astro_viewer/app/services/nsom_diagnostic_adapters.py` adapts existing runtime
objects and diagnostic snapshots into that core model without network calls or
heavy recomputation. `ObservationOpportunity` stores `SessionViability` as its
single session source of truth; the diagnostic `session_viability` value is a
read-only compatibility projection and cannot diverge from the session object.
`astro_viewer/app/services/planner_nsom_service.py` is the first real NSOM
consumer: `NightPlannerService` can use it behind the internal
`NSOM_PLANNER_SCORING_ENABLED` flag, which is `True` by default as of `1.5.8`.
Planner candidates are converted to
`ObservationOpportunity` instances and ranked by opportunity value. In `1.4.2`
the experimental NSOM path no longer asks `PlannerScoringService` for
Moon/light-pollution condition ownership; `planner_nsom_service.py` builds the
NSOM `ObservationEnvironment` from Planner runtime inputs already in hand and
builds telescope-aware `ObserverCapability` before deriving
`PracticalTargetValue`. The diagnostic export is not exposed to QML, does not
write files, does not log automatically, does not emit signals and does not
recompute Planner, Home, Equipment or Sky Compass output. Confidence remains
parallel metadata and does not change recommendation score. As of `1.13.8`, the
runtime constructor rollback `NightPlannerService(use_nsom_planner_scoring=False)`
has been removed; legacy Planner formula access remains developer-only through
`PlannerScoringService` and comparison/report tooling.
`astro_viewer/app/services/planner_nsom_comparison.py` adds an internal,
developer-only comparison helper for `1.4.3`. It computes legacy Planner scores
and experimental NSOM Planner opportunities from the same supplied runtime
inputs, then returns JSON-compatible dictionaries with score/rank deltas and
NSOM component projections. It is not connected to QML, performs no writes or
automatic logging, and did not change the then-default-off Planner NSOM flag.
`1.4.4` adds behavioural comparison fixtures that intentionally validate NSOM
rules rather than legacy equivalence: planets and the Moon stay protected from
sky-background penalties, galaxies and diffuse nebulae degrade more under bright
sky, session viability changes opportunity value without mutating target value,
equipment changes practical value without changing observable value, and
confidence remains score-neutral.
`1.4.5` adds developer-facing explanation projections to the experimental
Planner NSOM path. `PlannerNsomScoringService.explain_opportunity()` describes
target identity, final opportunity score, score components, main limiting
factors and main positive factors from the already-built
`ObservationOpportunity`. Sky-owned factors explain `EffectiveObservability`,
observer/equipment factors explain `PracticalTargetValue`, session factors
explain `SessionViability`, and `RecommendationConfidence` is projected only as
trust metadata with no score effect. The explanations are returned through the
internal comparison helper as JSON-compatible dictionaries and are not exposed
to QML, written to disk or logged automatically.
`1.4.6` adds `PlannerNsomCalibrationInspectionService`, another developer-only
helper layered on top of the comparison and explanation services. It produces
named scenario groups for bright sky, poor/good session conditions, small/large
telescopes, planet-favouring conditions, deep-sky-favouring conditions and a
Moon target case. Each group reports ranked NSOM opportunities, explanation
breakdowns, limiting/positive factors, legacy rank/score references and the
intended NSOM behavioural expectation. The helper is passive: it uses fixed
in-memory fixtures, returns JSON-compatible dictionaries, does not write files,
does not log automatically, performs no network work and is not connected to
QML.
`1.4.7` adds developer/test tooling in
`astro_viewer/tools/nsom_planner_comparison_report.py` plus the static report
`docs/NSOM_PLANNER_COMPARISON_REPORT.md`. The tool builds 120 deterministic
scenario rows across target type, sky, session, equipment, target geometry and
confidence axes, compares exposed legacy Planner score breakdowns with
experimental NSOM `ObservationOpportunity` explanations, and marks unavailable
legacy concepts explicitly. This is not imported by runtime services or QML and
does not tune weights or enable NSOM Planner by default.
`1.4.8` adds developer/test tooling in
`astro_viewer/tools/nsom_mathematical_trace_report.py` plus the static report
`docs/NSOM_MATHEMATICAL_TRACE_REPORT.md`. The tool reuses the existing
deterministic comparison matrix and traces the complete NSOM mathematical
pipeline for every scenario: `IntrinsicTargetQuality`,
`ObservationEnvironment`, `EffectiveObservability`, `ObservableTargetValue`,
`ObserverCapability`, `PracticalTargetValue`, observation window, chronology,
`SessionViability`, `ObservationOpportunity` and final Planner ranking.
`RecommendationConfidence` is reported outside that pipeline as trust metadata
with zero score effect. The report also aggregates common limiting/positive
factors and calibration concerns. It is generated only by explicit developer
tooling and is not connected to runtime services, QML, automatic logging,
network work or Planner scoring changes.
`1.4.8b` hardens that trace report for calibration review. All-zero
opportunity groups, including blocked sessions, are marked as tied and
non-actionable so deterministic stable order is not presented as a meaningful
recommendation. The trace expands lower-level formula diagnostics for Moon
background, sky background, atmospheric transparency, horizon/geometric
visibility and observer-capability derivation, marking values as
adapter-derived or unavailable where inputs are not retained. The deterministic
report fixtures now expose `observing_window_quality` values of `1.0`, `0.5`
and `0.0`, and component dominance language is explicitly frequency-based
rather than a statement about weight or calibrated sensitivity. The hardening
remains developer/report tooling only.
`1.4.9` adds formula parity and sensitivity evidence before calibration. The
trace report now carries expected/reported comparisons for reconstructable
sub-formulas, while adapter-derived or unavailable formulas remain explicitly
marked. Focused tests compare those report formulas with the actual NSOM
Planner service for Moon background, sky background, atmospheric transparency,
geometric/horizon visibility, observing-window quality, observer-capability
summary and SessionViability. Separate sensitivity fixtures isolate one
component at a time and assert direction plus ownership without tuning weights,
changing Planner scoring or enabling the NSOM Planner flag.
`1.5.0` adds a developer-only ObserverCapability target-specific review before
calibration. `astro_viewer/tools/nsom_observer_capability_review.py` builds
JSON-compatible fixtures that isolate aperture-only, focal-length-only,
mount/tracking-only, field-of-view-only and practical-comfort/setup-only
changes across planet, Moon, galaxy, diffuse nebula, open cluster and globular
cluster targets. The review is also summarized in the mathematical trace
report. It keeps sky/session inputs stable, verifies that observer changes do
not mutate `ObservableTargetValue`, and records that the current flat
`ObserverCapability.summary_for_planning()` produces uniform observer-summary
deltas across target classes. This is evidence for a future target-specific
weighting decision, not a calibration or scoring change.
`1.5.1` adds the internal experimental `Q_target` projection:
`project_observer_capability_for_target(observer_capability, target_class)`.
`ObserverCapability` remains multidimensional; `Q_target` is only the
Observer-layer scalar projection consumed by the NSOM Planner path, which was
still default-off at that step,
when building `PracticalTargetValue`. Target-class weighting profiles are
explicit for planet, Moon, galaxy, diffuse nebula, open cluster and globular
cluster. Reports now show the full ObserverCapability profile, the flat summary,
`Q_target`, the weighting profile and the practical-value delta versus flat.
This is not final calibration, does not alter legacy Planner scoring and does
not expose anything to QML.
`1.5.2` adds developer-only calibration review thresholds around the existing
experimental NSOM Planner evidence. `PlannerNsomCalibrationInspectionService`
and `nsom_planner_comparison_report.py` now classify rows and groups as
`expected`, `review` or `warning` for large rank deltas, unexpected protected
target degradation, unexpected bright-sky deep-sky protection, observer
dominance, all-zero groups and missing/invisible-window handling. The
comparison report also documents blocked-session policy alternatives: the
current hard block where `ObservationOpportunity` is `0.0`, and a preserved
`PracticalTargetValue` ordering that remains explicitly non-actionable. These
thresholds are review metadata only; they do not tune NSOM weights, change
legacy Planner scoring, enable NSOM Planner by default, write runtime files,
log automatically or expose QML.
`1.5.3` adds developer/test tooling in
`astro_viewer/tools/nsom_calibration_decision_log.py` plus the static report
`docs/NSOM_CALIBRATION_DECISION_LOG.md`. The decision log consumes the existing
deterministic comparison report data and links every warning/review row to a
decision entry with status `accepted`, `deferred`, `needs_calibration` or
`needs_policy_decision`. It records the affected NSOM layer and target class,
whether the difference is intentional NSOM behaviour or a possible calibration
issue, whether it blocks default-on work, and notes for blocked-session and
rank-delta review. This is documentation and developer tooling only; it does
not tune weights, change runtime Planner behaviour, write files except through
the explicit report command, log automatically or expose QML.
`1.5.4` resolves the non-actionable Planner policy blockers in developer-only
metadata. `opportunity_policy_review` now classifies groups as
`actionable_ranked_recommendation`, `actionable_with_uncertain_timing`,
`non_actionable_hard_block` or `non_actionable_invisible_target`. Blocked
sessions keep the current hard-block score behaviour, invisible targets remain
non-actionable ties, and visible missing-window targets keep the conservative
0.5 observing-window fallback with timing uncertainty. The preserved
`PracticalTargetValue` order is exposed only as `non_actionable_preserved_order`
for diagnostics; it is not runtime ranking, logging, QML or UI.
`1.5.5` resolves the targeted `small-equipment-planet-q-target` calibration
blocker inside the Observer layer. `project_observer_capability_for_target()`
keeps the target-class weighting profiles, then applies a planet-only
observable floor when small equipment still meets minimum light grasp,
resolution, magnification and tracking dimensions. The floor affects only
`Q_target`, so `PracticalTargetValue` can change while `ObservableTargetValue`,
`EffectiveObservability`, `SessionViability` and `RecommendationConfidence`
remain unchanged. The comparison report, mathematical trace and decision log
show the conditional floor; the NSOM Planner flag remains default-off and
legacy Planner scoring is unchanged in that calibration step.
`1.5.6` resolves the targeted `open-cluster-recurring-demotion` calibration
blocker inside the Observer layer. `project_observer_capability_for_target()`
now applies an open-cluster-only field-of-view usability floor before computing
the target-class weighted `Q_target`, but only when the reported field of view
is usable and practical comfort is adequate. Genuinely narrow fields remain
limited. The rule affects `PracticalTargetValue` only through `Q_target`; it
does not change `IntrinsicTargetQuality`, `ObservableTargetValue`,
`EffectiveObservability`, `SessionViability`, confidence metadata, legacy
Planner scoring, QML exposure or the then-default-off NSOM Planner flag. The
comparison report, mathematical trace and decision log show the conditional
open-cluster projection, and no default-on calibration blockers remain.
`1.5.7` adds developer/test tooling in
`astro_viewer/tools/nsom_default_on_readiness_audit.py` plus the static report
`docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md`. The audit consumes the
comparison report, mathematical trace and calibration decision log, then checks
that no calibration or policy blockers remain, accepted/deferred decisions are
documented, deferred items are non-blocking, `NSOM_PLANNER_SCORING_ENABLED`
remains `False`, report tooling is developer-only, and no QML/runtime import
wiring exists for the reports. It is an explicit developer command only; it
does not enable NSOM Planner, tune weights, change legacy Planner scoring, log
automatically, perform network work or write runtime files.
`1.5.8` changes the Planner NSOM flag default to `True`. The runtime switch is
limited to `NSOM_PLANNER_SCORING_ENABLED = True`; no NSOM formula, QML exposure,
report wiring, logging, network path or runtime file write is added. That step
kept a legacy Planner rollback; `1.13.8` later removes the runtime constructor
rollback.
`1.5.9` closes the NSOM Planner migration. NSOM Planner is now the default
Planner implementation. The explicit internal rollback path retained at that
time was removed in `1.13.8`; legacy formula comparison remains developer-only.
This is a documentation/status step only: it does not change scoring, Planner
runtime behaviour beyond the existing `1.5.8` default-on state, QML/UI,
runtime logging, network behaviour or runtime file writes. The developer-only
comparison, trace, decision-log and readiness-audit tooling remains passive and
unwired from runtime services and QML. The remaining deferred non-blocking
review items are `medium-equipment-q-target-review-band` and
`moon-planet-favouring-category-factor`; they remain future calibration review
topics, not default-on blockers.
`1.6.5` closes the Home `recommendedDeepSky` NSOM migration. The default Home
deep-sky list now orders candidates with NSOM `ObservableTargetValue`, using
`IntrinsicTargetQuality`, Home `ObservationEnvironment` and
`EffectiveObservability` only. It deliberately does not consume
`PracticalTargetValue`, `ObserverCapability`, `SessionViability`,
`RecommendationConfidence` or `ObservationOpportunity` for Home ranking. The
legacy Home order was temporarily available through an explicit controller
rollback, which `1.13.8` removes. If runtime sky quality is unavailable, the
controller still keeps the legacy moon-adjusted data fallback.
The QML payload remains the same and no NSOM fields are exposed; displayed Home
scores remain the legacy/base score for compatibility, so visible score values
may not be monotonic with the NSOM order. Best Object, Sky Compass, report
tooling, logging, network behaviour and runtime file writes are unchanged.
`1.7.0` adds `astro_viewer/app/services/best_object_nsom_comparison.py`, a
developer-only comparison helper for the current Best Object candidate set. It
computes `IntrinsicTargetQuality`, `ObservationEnvironment`,
`EffectiveObservability`, `ObservableTargetValue`, `PracticalTargetValue`,
`SessionViability` metadata and `RecommendationConfidence` metadata next to
the legacy Best Object formula `item.score * weather_factor *
difficulty_factor`. The helper explicitly records that the legacy scalar mixes
target value, weather/session and difficulty, and marks sky, observer,
session-policy and confidence breakdowns as unavailable when the legacy path
does not expose them. It is not imported by `AppController`, QML or report
runtime wiring, and it does not change Best Object selection,
`recommendedDeepSky`, Planner, Sky Compass, logging, network behaviour or
runtime file writes.
`1.7.1` adds `astro_viewer/tools/best_object_nsom_comparison_report.py` and the
static report `docs/BEST_OBJECT_NSOM_COMPARISON_REPORT.md`. The report uses the
Best Object comparison service across deterministic scenarios for good/poor/
blocked sessions, bright Moon, high light pollution, small/large equipment and
an expanded mixed planet/deep-sky candidate set. It compares legacy Best Object
order, NSOM ObservableTargetValue order, NSOM PracticalTargetValue order,
SessionViability metadata and RecommendationConfidence metadata. Its semantic
recommendation is that current Best Object is a Home-specific hybrid; a future
NSOM migration should evaluate ObservationOpportunity with Home presentation
policy. The tool is explicit developer tooling and is not imported by runtime
services or QML.
`1.7.2` adds `astro_viewer/app/services/best_object_nsom_ranking.py`, an
internal default-off runtime path for Best Object. The default flag is
`NSOM_BEST_OBJECT_ENABLED = False`, so `AppController` still preserved legacy
Best Object selection unless constructed with `use_nsom_best_object=True`; that
temporary constructor control was removed in `1.13.8`. The NSOM path
builds Home `ObservableTargetValue`, projects telescope-aware
`ObserverCapability` through target-specific `Q_target`, derives
`PracticalTargetValue`, and ranks `ObservationOpportunity` with Home-specific
actionability. Blocked sessions and invisible candidates are non-actionable;
blocked-session practical ordering remains diagnostic-only inside the service,
not a runtime recommendation. `RecommendationConfidence` is metadata only. The
path does not expose NSOM fields to QML, does not wire report tooling into
runtime, does not log automatically, does not perform network work and does not
write runtime files. If sky quality is unavailable, `AppController` falls back
to legacy Best Object selection.
`1.7.3` resolves Best Object actionability policy for default-on readiness.
Blocked sessions and invisible targets remain non-actionable; visible targets
with missing or uncertain windows stay actionable with timing uncertainty. Any
preserved practical ordering for non-actionable candidates is diagnostic-only
inside the NSOM service and is never runtime recommendation order.
`1.7.4` adds the developer-only default-on readiness audit in
`docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md`, verifying rollback,
non-actionable policy, QML/runtime safety and confidence neutrality before the
switch.
`1.7.5` changes the Best Object NSOM flag default to `True`. The default
controller path now selects Best Object through
`BestObjectNsomSelectionService` when weather and sky quality are available.
The temporary explicit internal rollback retained at switch time was removed in
`1.13.8`; the missing-sky-quality fallback remains. No QML fields, report
runtime wiring, logging,
network work or runtime file writes are added.
`1.7.6` closes the Best Object NSOM migration as documentation/status. Best
Object is now default-on NSOM with Home-specific `ObservationOpportunity`
policy; the legacy Best Object runtime rollback retained at that time was
removed in `1.13.8`, while missing-sky fallback remains. The
QML payload remains compatible and displayed Best Object score remains the
legacy/base compatibility score, so it may not be monotonic with NSOM
selection.
`1.8.0` starts the Advanced Observing NSOM migration with
`astro_viewer/app/services/advanced_observing_nsom_comparison.py`, a
developer-only comparison helper. It projects the current
`AdvancedObservingService` planetary and deep-sky formulas into explicit legacy
components, then shows NSOM reference layers for session viability,
target-class sky sensitivity, effective observability and confidence metadata.
The helper is reference-only and is not runtime score parity: it does not
change `AdvancedObservingService`, Home, Best Object, Planner, Sky Compass,
QML, logging, network behaviour or runtime file writes.
`1.8.1` adds explicit developer/test tooling in
`astro_viewer/tools/advanced_observing_nsom_comparison_report.py` plus the
static report `docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md`. The report
covers deterministic good/poor/blocked sessions, bright Moon, high light
pollution, poor seeing, poor transparency and low-confidence scenarios. It is
not imported by runtime services or QML and does not change advanced scores or
other recommendation paths.
`1.8.2` is a review-only checkpoint for that report. It makes no code or
runtime changes, but records that Advanced Observing needs explicit policy
decisions before a default-off NSOM runtime path.
`1.8.3` adds
`astro_viewer/tools/advanced_observing_nsom_policy_readiness.py` and the static
report `docs/ADVANCED_OBSERVING_NSOM_POLICY_READINESS.md`. The report records
developer-only policy decisions for Advanced Observing: category diagnostics
remain presentation-owned, `SessionViability` stays separate from sky values,
planetary/Moon diagnostics are protected from Moon/light-pollution background
penalties, deep-sky keeps target-class-aware components, legacy weather caps
stay rollback/default-only for now, `ObserverCapability` is deferred, and
`RecommendationConfidence` remains metadata-only. It is not runtime wiring and
does not change advanced scores, Home, Best Object, Planner, Sky Compass, QML,
logging, network behaviour or runtime file writes.
`1.8.4` adds the internal/default-off Advanced Observing NSOM runtime path in
`astro_viewer/app/services/advanced_observing_nsom_service.py`. The controller
constructor now accepts `use_nsom_advanced_observing`, defaulting to
`NSOM_ADVANCED_OBSERVING_ENABLED = False`, so existing runtime behaviour remains
legacy unless explicitly forced in tests/development. The forced-on path keeps
the existing `AdvancedObservingScores` payload shape and computes planetary and
deep-sky category diagnostics from NSOM `ObservableTargetValue`; session
viability and recommendation confidence remain metadata and do not affect the
score. No QML toggle, report runtime wiring, logging, network work or runtime
file writes are added.
`1.8.5` adds
`astro_viewer/tools/advanced_observing_nsom_runtime_review.py` and the static
report `docs/ADVANCED_OBSERVING_NSOM_RUNTIME_REVIEW.md`. The report reviews the
forced-on path without changing the default flag. It confirms payload
compatibility, confidence neutrality, session viability outside category scores,
planetary protection from Moon/light-pollution background, and deep-sky
sensitivity. It also records a default-on blocker: `advancedScores` is consumed
by QML, Planner and NotificationService, so a future switch must decide whether
those consumers receive NSOM category values, ignore them or keep a
legacy-compatible copy.
`1.8.6` adds
`astro_viewer/tools/advanced_observing_nsom_downstream_policy.py` and the static
report `docs/ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY.md`. The report records
the downstream policy decision: `advancedScores` must stay legacy-compatible
until Planner and NotificationService are split from that shared presentation
contract. Planner currently consumes the value as an atmospheric-transparency
factor inside NSOM `EffectiveObservability`; NotificationService thresholds it
directly for favourable observing-condition notifications. Therefore
`NSOM_ADVANCED_OBSERVING_ENABLED` remains `False` and default-on is blocked
until those consumers receive explicit consumer-specific inputs or policy gates.
`1.8.7` implements that consumer split in `AppController`: the public/shared
`advancedScores` payload remains legacy-compatible, while forced-on Advanced
Observing NSOM scores are stored only in the internal parallel
`_advanced_observing_nsom_scores` snapshot. Planner and NotificationService now
receive explicit legacy-compatible consumer score inputs, so NSOM category
diagnostics are not reused as Planner atmospheric transparency or notification
thresholds. The Advanced Observing NSOM flag remains default-off; the remaining
default-on blocker is the presentation/QML policy for whether and how NSOM
Advanced Observing diagnostics should ever be shown.
`1.8.8` adds
`astro_viewer/tools/advanced_observing_nsom_presentation_readiness.py` and the
static report `docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_READINESS.md`. The
audit confirms that the downstream consumer split is resolved, but the Advanced
Observing NSOM path is not ready for default-on because forced-on NSOM category
values are still only the private `_advanced_observing_nsom_scores` snapshot.
QML continues to render legacy-compatible `advancedScores`, no public NSOM
property exists, and `/100` score/label semantics for NSOM category diagnostics
are intentionally unresolved. The flag remains `False` until a presentation
contract is designed.
`1.8.9` defines that presentation contract in
`astro_viewer/tools/advanced_observing_nsom_presentation_contract.py` and
`docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md`. The future contract is
a separate, versioned `advancedObservingNsom` payload; it does not replace
`advancedScores`, does not feed Planner or NotificationService, and does not
affect Home Best Object or Sky Compass. Category values are documented as
NSOM `ObservableTargetValue` diagnostics only. `ObserverCapability`,
`PracticalTargetValue`, `SessionViability`, `RecommendationConfidence` and
`ObservationOpportunity` remain outside the category value. Runtime projection
and any QML exposure remain separate future steps.
`1.8.10` adds that runtime projection in
`astro_viewer/app/services/advanced_observing_nsom_presentation.py` and stores
it in AppController only as the private `_advanced_observing_nsom_presentation`
snapshot when `use_nsom_advanced_observing=True` is forced internally. The
projection follows the 1.8.9 contract, remains default-off, is not a QML
property, does not replace `advancedScores`, and is not passed to Planner,
NotificationService, Home Best Object or Sky Compass. The remaining default-on
blocker is a separate QML/UI exposure review for any future public
`advancedObservingNsom` surface.
`1.8.11` hardens that private projection by aligning the session metadata with
the controller's existing observing-session policy. A weather-blocked session
with a later usable observing window is now projected as `monitor`, not
`discouraged`. This remains metadata outside category values; no QML property or
new Planner, NotificationService, Best Object or Sky Compass input is added.
`1.8.12` adds
`astro_viewer/tools/advanced_observing_nsom_qml_exposure_readiness.py` and the
static report `docs/ADVANCED_OBSERVING_NSOM_QML_EXPOSURE_READINESS.md`. The
audit confirms that the internal projection is safe to keep, but a public QML
property or visible UI remains blocked until property notify/lifecycle policy,
localized copy, visual placement and NSOM score-label semantics are explicitly
designed. `advancedScores` remains the only current public QML contract.
`1.8.13` defines that policy in
`astro_viewer/tools/advanced_observing_nsom_qml_presentation_policy.py` and
`docs/ADVANCED_OBSERVING_NSOM_QML_PRESENTATION_POLICY.md`. The future
`advancedObservingNsom` property is still not implemented, but if a later step
adds it, the policy says it must be read-only, use the private
`_advanced_observing_nsom_presentation` snapshot, reuse the existing
`weatherChanged` lifecycle, avoid recomputation on property read and avoid new
signals. Visible UI remains unapproved; future copy must be localization-key
based and values must be labelled as NSOM diagnostics rather than legacy `/100`
actionability scores. Runtime behaviour, QML exposure, Planner,
NotificationService, Home, Best Object and Sky Compass remain unchanged.
`1.8.14` implements that read-only property in `AppController`.
`advancedObservingNsom` returns the existing private
`_advanced_observing_nsom_presentation` snapshot or `{}` when the path is
disabled/unavailable. It reuses `weatherChanged`, adds no new signal and does
not recompute on property read. No visible QML file reads the property yet, so
the Home Advanced Observing cards continue to use `advancedScores`. Planner,
NotificationService, Home Best Object and Sky Compass continue to receive their
existing inputs, and `NSOM_ADVANCED_OBSERVING_ENABLED` remains `False`.
`1.8.15` hardens that read-only surface by returning a defensive deep copy of
the private snapshot, including reads through the Qt property system. This keeps
the QML property immutable from consumers in practice, preserves strict
JSON-compatible payload semantics and does not change visible UI, scoring,
consumer wiring or the default-off Advanced Observing NSOM flag.
`1.8.16` adds
`astro_viewer/tools/advanced_observing_nsom_default_on_readiness.py` and
`docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md`. The audit
concludes that Advanced Observing NSOM is ready for a backend/internal default-on
switch only: the flag can be enabled in a later narrow commit to compute the
parallel NSOM projection by default, while `advancedScores`, visible QML,
Planner, NotificationService, Home Best Object and Sky Compass remain unchanged.
Visible UI, localized copy and any replacement of legacy score semantics remain
separate non-blocking work.
`1.8.17` enables that backend/internal Advanced Observing NSOM projection by
default with `NSOM_ADVANCED_OBSERVING_ENABLED = True`. `AppController` now
computes `_advanced_observing_nsom_scores` and the read-only
`advancedObservingNsom` presentation snapshot by default, while `advancedScores`
continues to be produced by the legacy `AdvancedObservingService` and remains
the visible Home-card, Planner and NotificationService contract. The explicit
rollback retained at that time was removed in `1.13.8`. No visible QML
consumer, report runtime wiring, logging, network path or runtime file write is
added by the switch.
`1.8.18` closes the Advanced Observing NSOM backend migration as documented
status. The default backend projection remains NSOM, the visible and consumer
contract remains legacy-compatible `advancedScores`, and
`advancedObservingNsom` remains a separate read-only property with no visible
QML consumer. Legacy Advanced Observing semantics for Planner/notifications are
retained through the consumer split; the explicit rollback retained at that time
was removed in `1.13.8`. Visible UI, localized copy
and any replacement of legacy score display semantics remain separate future
presentation work, not blockers for the completed backend migration.
`1.9.0` starts the Sky Compass NSOM migration with
`SkyCompassNsomComparisonService`, a developer-only helper that compares the
current direction formula against NSOM target, sky, observer, session and
confidence concepts. The runtime Sky Compass payload and direction ranking
remain owned by `SkyCompassService`; no controller/QML wiring, logging, network
path, runtime file write or report runtime hook is added. The helper marks
legacy components unavailable where Sky Compass only receives an already
prepared candidate score.
`1.9.1` adds the developer-only
`docs/SKY_COMPASS_NSOM_COMPARISON_REPORT.md`, generated only by the explicit
`astro_viewer/tools/sky_compass_nsom_comparison_report.py` command. The report
uses deterministic scenarios to show that Sky Compass is a direction and
presentation policy, not a pure target-value ranking. NSOM observable and
practical direction references are useful for review, but plan membership,
Best Object identity and direction concentration remain separate presentation
policy inputs. No runtime import, QML exposure, logging, network path or
runtime file write is added.
`1.9.2` adds the developer-only
`docs/SKY_COMPASS_NSOM_POLICY_READINESS.md`, generated only by
`astro_viewer/tools/sky_compass_nsom_policy_readiness.py`. It records that a
future default-off Sky Compass NSOM path may use `ObservableTargetValue.value`
as the candidate base, while Night Plan membership, Best Object identity and
direction concentration stay presentation policy. `PracticalTargetValue`
remains reference-only for this migration slice, session/caution and confidence
remain metadata, legacy fallback is required, and the `skyCompass` QML payload
shape must stay unchanged. No runtime flag or scoring path is added by this
readiness step.
`1.9.3` adds that internal/default-off runtime path with
`NSOM_SKY_COMPASS_ENABLED = False` and `SkyCompassNsomDirectionService`.
`AppController(use_nsom_sky_compass=True)` opts into the experimental direction
policy: candidates are based on `ObservableTargetValue.value`, while Night Plan
membership, Best Object identity and target presence remain presentation-policy
boosts. The public `skyCompass` payload shape is preserved, no NSOM fields are
exposed to QML, and missing sky quality or service failure falls back to the
legacy `SkyCompassService`. The default runtime path remains unchanged.
`1.9.4` adds the developer-only default-on readiness audit in
`docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md`, generated only by
`astro_viewer/tools/sky_compass_nsom_default_on_readiness_audit.py`. The audit
verdict is `ready_for_sky_compass_nsom_default_on_switch`; it records no
blockers, explicit rollback `AppController(use_nsom_sky_compass=False)`,
legacy fallback for missing sky quality or service failure, unchanged
`skyCompass` payload shape and no QML/report runtime wiring. The audit does
not enable the flag; `NSOM_SKY_COMPASS_ENABLED` remains `False` until a
separate switch-only commit.
`1.9.5` enables Sky Compass NSOM by default with
`NSOM_SKY_COMPASS_ENABLED = True`. The default controller path now uses
`SkyCompassNsomDirectionService` when sky quality is available, while
the explicit legacy rollback retained at that time was removed in `1.13.8`, and
missing sky quality or NSOM service failure still falls back to
`SkyCompassService`. The public `skyCompass` payload shape remains unchanged
and no QML/UI field, logging path, network call, runtime file write or report
runtime wiring is added.
`1.9.6` closes the Sky Compass NSOM migration as documentation/status. Sky
Compass now defaults to NSOM `ObservableTargetValue` as the candidate base
inside `SkyCompassNsomDirectionService`; legacy `SkyCompassService` remains
available only as a data/error fallback after `1.13.8`; the explicit runtime
rollback was removed. The `skyCompass` payload remains
legacy-compatible, displayed target `score` remains base display data rather
than NSOM rationale, and visible explanation UI remains a separate future
design step.
`1.9.7` adds the developer-only overall backend migration audit in
`docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md`, generated only by
`astro_viewer/tools/nsom_backend_migration_status_audit.py`. The audit records
that Planner, Home `recommendedDeepSky`, Best Object, the Advanced Observing
backend projection and Sky Compass are closed default-on NSOM surfaces with
explicit rollback paths. Remaining Detail/selected-object, Sky Map, Equipment,
conditioned-object cache, Notification and catalogue-score work is classified
as non-blocking follow-up. The audit recommends starting the next backend area
with a Detail/Object NSOM comparison layer and does not change runtime
behaviour, QML, scoring, logging, network access or runtime file writes.
`1.10.0` starts that Detail/Object migration with
`DetailObjectNsomComparisonService` and the developer-only static report
`docs/DETAIL_OBJECT_NSOM_COMPARISON_REPORT.md`. The helper compares the current
selected-object Detail display policy with NSOM projections without changing
`AppController.selectedObject`. Observing-source Detail is represented as the
current `_moon_adjusted_object()` replacement policy; catalogue Detail is
represented as raw selected-object presentation. NSOM `ObservableTargetValue`
and `PracticalTargetValue` are computed separately, while `SessionViability`
and `RecommendationConfidence` remain metadata. The helper is not imported by
runtime controller/QML and does not alter Home, Best Object, Planner, Sky
Compass, logging, network access or runtime file writes.
`1.10.1` adds the developer-only readiness audit in
`docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md`, generated only by
`astro_viewer/tools/detail_nsom_readiness_audit.py`. The verdict is
`not_ready_for_default_off_detail_nsom_path`: the comparison evidence is useful,
but a runtime Detail NSOM path should wait until source-specific Detail policy,
displayed score semantics and a payload/display contract are explicitly
decided. The audit keeps `RecommendationConfidence` metadata-only and verifies
that no controller/QML/report runtime wiring, logging, network access or
runtime file write is added.
`1.10.2` adds that source/display policy contract in
`docs/DETAIL_OBJECT_NSOM_POLICY_CONTRACT.md`, generated only by
`astro_viewer/tools/detail_nsom_policy_contract.py`. The contract accepts the
existing source split: observing Detail keeps the legacy moon-adjusted
compatibility display score, while catalogue Detail keeps the raw catalogue
compatibility score. It also defines `selectedObject.score` as legacy/base
compatibility data, not NSOM rationale, and reserves a separate future internal
payload named `detailObjectNsom`. The readiness audit now reports
`ready_for_default_off_detail_nsom_path`, but no runtime path, QML field,
visible UI, logging, network access or runtime file write is added.
`1.10.3` implements that runtime path as an internal default-off service:
`astro_viewer/app/services/detail_nsom_runtime.py`. The feature flag is
`NSOM_DETAIL_OBJECT_ENABLED = False`, with controller rollback through
`AppController(use_nsom_detail_object=False)`. When forced on, the controller
can build a separate internal payload through `_selected_object_nsom_payload()`;
it does not add a QML `@Property`, does not add NSOM fields to `selectedObject`,
and does not change Home, Best Object, Planner, Sky Compass, logging, network
access or runtime file writes. The Detail payload includes Observable and
Practical target values, while SessionViability and RecommendationConfidence
remain metadata-only.
`1.10.4` adds
`docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md`, generated only by
`astro_viewer/tools/detail_nsom_default_on_readiness_audit.py`. The audit
concludes that the internal Detail/Object path is ready for a separate
default-on switch, while keeping `NSOM_DETAIL_OBJECT_ENABLED = False` for this
commit. It verifies explicit rollback, separate internal payload semantics,
unchanged `selectedObject`, no QML exposure, no report runtime wiring and
metadata-only SessionViability/RecommendationConfidence. Visible Detail page
NSOM explanations remain a later UI/design step.
`1.10.5` performs that switch by setting
`NSOM_DETAIL_OBJECT_ENABLED = True`. The default Detail/Object backend path can
now build the separate internal NSOM payload, but the public QML contract is
unchanged: `selectedObject` still carries legacy/base compatibility display
data, no Detail NSOM property is exposed, and the temporary runtime rollback
was removed in `1.13.8`.
`1.10.6` closes the backend Detail/Object NSOM migration in
`docs/DETAIL_OBJECT_NSOM_MIGRATION_CLOSEOUT.md`. Detail/Object is now a
default-on backend NSOM surface with unchanged visible Detail page payload. The
explicit rollback retained at closeout was removed in `1.13.8`. Future visible
NSOM rationale/copy for the Detail page is
separate UI/design work.
`1.11.0` adds the developer-only legacy backend surface audit in
`docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md`. The audit reclassifies Sky Map as
dead legacy rather than a backend NSOM migration target: Home QML consumes
Sky Compass and no longer consumes `controller.skyMap`, while `AppController`
still computes `_sky_map`. The next backend step is therefore focused removal
of the dead Sky Map controller/property/service path after review, not an NSOM
comparison layer. The audit also distinguishes temporary internal rollback
flags, payload/UI compatibility fields and active legacy/hybrid surfaces that
still need separate policy work.
`1.11.1` removes that dead Sky Map path: `SkyMapService`,
`AppController.skyMap`, `_sky_map` storage and Sky Map recomputation are gone.
Sky Compass remains the supported directional Home surface, with unchanged QML
payload semantics and no ranking/scoring changes. The next active backend NSOM
area is Equipment/ObserverCapability.
`1.12.0` adds the developer-only Equipment/ObserverCapability comparison layer
and `docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md`. The report compares the current
`EquipmentService` component score with NSOM `ObserverCapability`, target-class
`Q_target` and `PracticalTargetValue`, while keeping runtime Equipment
recommendations unchanged and adding no QML exposure. The next step is review
and policy/readiness before any default-off Equipment NSOM path is considered.
`1.12.1` records that policy in
`docs/EQUIPMENT_NSOM_POLICY_READINESS.md`: `EquipmentService` remains the runtime
setup helper for eyepieces, Barlow, binoculars, fallbacks and `setupOptions`.
No default-off Equipment replacement path is added. The next backend step is to
extract a shared `ObserverCapability`/`Q_target` adapter or read model while
leaving Equipment recommendations and QML payloads unchanged.
`1.12.2` extracts that shared adapter in
`astro_viewer/app/services/observer_capability_adapter.py`. Equipment comparison
now consumes the shared `ObserverCapability`/`Q_target` projection instead of
owning report-private capability math. `EquipmentService.suggest_for_profile(...)`
and all QML payloads remain unchanged.
`1.12.2b` hardens the extracted projection so target-class weighting metadata is
immutable while still projecting to strict JSON. This does not change Equipment
runtime ranking, Planner, Home, Best Object, Advanced Observing, Sky Compass,
Detail/Object, QML, logging, network behaviour or runtime file writes.
`1.12.3` adds the developer-only
`docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md`. The audit confirms that the current
QML/Home UI no longer consumes `controller.notifications`, while the old
`NotificationService`, controller property and DTO still exist. Notifications
are therefore classified as `dead_legacy_pending_removal`, not as an NSOM
migration surface. No runtime behaviour changes in this audit step.
`1.12.4` removes that dead backend path: `NotificationService`,
`AppController.notifications`, runtime notification storage/recomputation and
the `Notification` DTO are gone. Notifications are now classified as
`removed_dead_legacy`; future work should not rebuild them unless a visible
product requirement reintroduces notifications.
`1.12.5` adds `docs/OBSERVATION_CONDITIONS_READ_MODEL_AUDIT.md`. The audit
confirms that `ObservationConditionsService` is still active hybrid runtime
code: it creates condition-adjusted `CelestialObject` copies for display and
fallback compatibility, and those copies can become inputs to default-on NSOM
observable calculations. No runtime behavior changes in this audit step; the
next implementation step should introduce an explicit raw/display/NSOM
read-model boundary.
`1.12.6` introduces that internal boundary. `ObservationConditionedTargetReadModel`
keeps raw target input, conditioned display target, condition breakdown, raw
score and display score as separate fields. `AppController` stores this only in
private caches; no QML property, report runtime wiring or visible payload field
is added. Runtime ranking and selection remain unchanged in this commit. The
remaining review item is whether Home, Best Object and Sky Compass NSOM
consumers should be rerouted to the raw read-model target in a separate,
behaviour-reviewed step.
`1.12.7` adds `docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md`. The
audit defines the consumer policy: NSOM math should read raw read-model targets,
while QML-compatible Home/Best/Sky Compass payloads should keep conditioned
display targets. No runtime consumer is rerouted in this step; the first
recommended runtime implementation after review is Home `recommendedDeepSky`.
`1.12.8` applies that policy to Home `recommendedDeepSky` only. The default
Home NSOM path ranks from `ObservationConditionedTargetReadModel.nsom_target_input`
and still returns `ObservationConditionedTargetReadModel.qml_display_target` to
the existing QML payload. The rollback constructor parameter and missing-sky
quality fallback continue to use the legacy moon-adjusted path. Best Object and
Sky Compass remain separate consumer reroute work.
`1.12.9` applies the same raw-score/display-payload split to Best Object. The
default Best Object NSOM path scores candidates from
`ObservationConditionedTargetReadModel.nsom_target_input`, then returns the
selected `ObservationConditionedTargetReadModel.qml_display_target` so the QML
payload shape and displayed score semantics remain compatible. The explicit
rollback and missing-sky-quality fallback remain unchanged. Sky Compass remains
the only ObservationConditions consumer still pending a raw-target reroute
decision at that point in the migration sequence.
`1.12.10` adds `docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md`. The policy
states that Sky Compass must not be rerouted by passing only raw targets to the
current service. `ObservableTargetValue` should read target physics from
`ObservationConditionedTargetReadModel.nsom_target_input`, while direction
grouping, visibility, horizon/current position and payload fields remain owned
by the display/live target. Night Plan and Best Object boosts remain
presentation/context policy outside target physics. No runtime Sky Compass path
is changed in this policy step.
`1.12.11` implements that split adapter in the default Sky Compass NSOM path.
`AppController` now builds per-target observable objects from raw read-model
target physics plus current display/live geometry, and passes them to
`SkyCompassNsomDirectionService` through an internal `observable_objects_by_id`
map. Sky Compass payload fields still come from display/live candidates, and
the missing-sky-quality and service-error fallbacks still use the legacy Sky
Compass service.
`1.12.12` closes the ObservationConditions consumer reroute series. Home
`recommendedDeepSky`, Best Object and Sky Compass are now documented as routed
through the raw/display read-model boundary. No ranking logic, payload shape or
QML exposure changes in the closeout step; the next backend NSOM area is the
Equipment presenter contract.
`1.13.0` adds the developer-only Equipment presenter contract audit in
`docs/EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT.md`. The audit records the
runtime setup payload contract (`setupOptions`, fallback states,
`selectionScore` and QML-facing fields), keeps `Q_target` reference-only for
ObserverCapability/PracticalTargetValue, and confirms
`RecommendationConfidence` remains metadata-only. `EquipmentService.suggest_for_profile(...)`
continues to own the runtime setup recommendation; no Equipment ranking,
payload, QML, logging, network or runtime file-write behaviour changes. The
next safe backend step is a runtime-neutral Equipment setup read-model/presenter
DTO before any scoring replacement.
`1.13.1` introduces that runtime-neutral boundary in
`astro_viewer/app/services/equipment_setup_read_model.py`. `EquipmentService`
still computes the active setup recommendation and payload, but
`AppController._apply_equipment(...)` now converts the suggestion through an
immutable `EquipmentSetupReadModel` before projecting the existing
`CelestialObject` fields. The boundary preserves `setupOptions`, fallback
payloads, `selectionScore`, setup type and explanation semantics without adding
QML fields or NSOM UI exposure. Equipment scoring replacement remains deferred
until a setup-score ownership audit separates target traits, seeing, sky
quality, fallback states and presentation-local selection score.
`1.13.2` adds that developer-only setup-score ownership audit in
`docs/EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT.md`. The audit maps the real
`EquipmentService._configuration_score` components (`angular_scale`,
`magnification`, `exit_pupil`, `light_gathering`, `seeing_compatibility` and
`handling`) to NSOM ownership boundaries and confirms that the scalar setup
score mixes target traits, observer setup, sky quality, seeing and
presentation-local practicality. It is not a direct `ObservableTargetValue`,
`PracticalTargetValue`, `Q_target` or `RecommendationConfidence` replacement.
No Equipment recommendation, ranking, QML, logging, network or runtime
file-write behaviour changes; the next safe step is a component read-model with
strict parity tests.
`1.13.3` introduces that component boundary in
`astro_viewer/app/services/equipment_setup_score_read_model.py`.
`EquipmentService._configuration_score(...)` now builds an
`EquipmentSetupScoreReadModel` from the real component values and returns the
same clamped 0-100 score. `EquipmentNsomComparisonService` reads the legacy
breakdown from that read-model instead of duplicating the formula. No Equipment
ranking, selection score, payload shape, QML, logging, network or runtime
file-write behaviour changes. The next safe step is to review the boundary and
then decide, via policy audit, whether Equipment needs a default-off NSOM setup
path at all.
`1.13.4` adds `docs/EQUIPMENT_NSOM_DEFAULT_OFF_PATH_POLICY_AUDIT.md` and closes
that decision: Equipment should not gain a default-off NSOM replacement path
now. `EquipmentService` remains a setup-local service that chooses eyepiece,
zoom position, Barlow, binocular and fallback payloads. `ObserverCapability`,
`Q_target` and the setup-score component read-model remain NSOM boundaries and
metadata, not a runtime replacement. No ranking, selection score, payload, QML,
logging, network or runtime file-write behaviour changes; the next step is the
Equipment migration closeout.
`1.13.5` adds `docs/EQUIPMENT_NSOM_MIGRATION_CLOSEOUT.md` and records Equipment
as closed for the current backend NSOM scope. The architectural decision is that
Equipment remains a setup-local service, not a target-ranking surface:
`EquipmentService.suggest_for_profile(...)` continues to own concrete setup-row
selection, while ObserverCapability/Q_target, presenter, score ownership and
score-component read-models remain explicit NSOM boundaries. No default-off
Equipment runtime path is added and no runtime recommendation, payload, QML,
logging, network or runtime file-write behaviour changes.
`1.13.6` adds `docs/NSOM_OVERALL_BACKEND_READINESS_AUDIT.md`, a developer-only
roll-up after the Equipment closeout. It records Planner, Home
`recommendedDeepSky`, Best Object, Advanced Observing backend, Sky Compass and
Detail/Object as closed NSOM backend surfaces, Equipment as a closed setup-local
NSOM-bounded service, ObservationConditions as a closed raw/display compatibility
boundary, and Sky Map/Notifications as removed dead legacy. Remaining work is
non-blocking policy or presentation cleanup: internal rollback flags,
legacy/base payload score fields and future Catalogue/Universe score semantics.
No scoring, runtime path, QML, logging, network or runtime file-write behaviour
changes.
`1.13.7` adds `docs/NSOM_ROLLBACK_CLEANUP_POLICY_AUDIT.md` and sets the policy
for the remaining internal rollback paths. Because the app is not distributed,
and the backend NSOM surfaces are already closed, the rollback constructor flags
and legacy branches for Planner, Home `recommendedDeepSky`, Best Object,
Advanced Observing backend, Sky Compass and Detail/Object internal payload should
be removed in the next focused implementation step. The 1.13.7 audit does not
remove those flags or change runtime behaviour; it records the decision and
required validation.
`1.13.8` implements that policy. Runtime constructor rollback parameters are
removed from `AppController` and `NightPlannerService`, so the closed NSOM
backend surfaces no longer expose selectable legacy ranking paths. Missing-input
and service-failure fallbacks remain where they are data-safety policies, such as
missing sky quality, but they are not internal rollback switches. The backend,
legacy-surface, overall-readiness and rollback-cleanup reports are updated to
record the removal.
`1.13.9` adds
`docs/NSOM_UNIVERSE_CATALOGUE_SCORE_BOUNDARY_AUDIT.md`, a developer-only audit of
the remaining raw catalogue/prepared-object score boundary. It classifies
`CelestialObject.score` as an interim Universe/IntrinsicTargetQuality seed and
payload compatibility field, not as a final NSOM score to tune directly. The
ObservationConditions raw/display read-model boundary remains the protection
against display-conditioned scores becoming intrinsic target input. Future
UniverseTargetProfile/provenance work is non-blocking and separate from visible
score explanation design.
`1.14.0` adds
`docs/NSOM_UNIVERSE_TARGET_PROFILE_POLICY.md` and decides not to introduce a
runtime `UniverseTargetProfile` yet. `IntrinsicTargetQuality` remains the
current internal Universe DTO, with diagnostic source fields carrying the
available prepared-object context. The future profile contract is documented for
object identity, target class, score seed, provenance, geometry, magnitude/size
and presentation-only score projection, but implementation waits for concrete
provenance, catalogue-import, intrinsic-calibration or visible-explanation
requirements.
`1.14.1` adds
`docs/NSOM_LOCAL_INPUT_MOON_GEOMETRY_READINESS.md`, a developer-only audit that
separates local always-available astronomy inputs from local optional equipment
and external optional providers. The architecture decision is that Moon geometry
is the next backend physical-model step because Moon altitude, Moon-target
separation and Moon/window overlap can be computed from active location, time
and local ephemeris data without weather, VIIRS, NASA AOD or OpenAQ. Current
runtime scoring still uses Moon illumination/background only; the geometry
fields remain score-neutral readiness inputs until a later explicit scoring
step.
`1.14.2` implements the local Moon-geometry diagnostic boundary. `MoonGeometrySummary`
is produced by `SkyfieldAstronomyEngine.moon_geometry(...)` from the active
location, local time and ephemeris data, then adapted by `AppController` into
`MoonGeometryConditionInput` for NSOM diagnostic snapshots and neutral condition
breakdowns. This remains score-neutral: Planner, Home, Best Object, Advanced
Observing, Sky Compass, Detail/Object, Equipment and QML keep their existing
runtime behaviour, and no report tooling is wired into runtime.
`1.14.3` adds the first default-off Planner use of that input. When
`PlannerNsomScoringService` is constructed with
`ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=True)`,
`MoonGeometryConditionInput` modifies only the Sky-owned
`ObservationEnvironment.lunar_sky_background` component. `AppController`
builds the per-target Moon-geometry map only when the Planner service advertises
that flag, so the default runtime path remains unchanged and no QML/UI exposure
is added.
`1.14.4` adds the developer-only
`docs/NSOM_MOON_GEOMETRY_PLANNER_CALIBRATION.md` report. It compares the
illumination-only Planner rollback model with the Moon-geometry model across
fixed target classes and Moon geometry cases, and verifies that the experimental
effect remains confined to the Sky-owned `lunar_sky_background` component.
Planner `moon_geometry_confidence` now tracks actual `MoonGeometryConditionInput`
availability instead of generic `MoonSummary` availability, but confidence
remains outside the scoring formula.
`1.14.5` adds
`docs/NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS.md`, a developer-only
readiness audit for a future default-on switch. It accepts the 1.14.4
calibration guardrails, confirms that `NightPlannerService` remains default-off
for Moon geometry today, and recommends a separate narrow switch if the audit is
accepted.
`1.14.6` enables that switch through
`NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED = True`. The generic
`ObservationConditionFeatureFlags.experimental_moon_geometry_scoring` default
remains `False`, so the change is Planner-specific and does not enable
ObservationConditions modifiers, AOD/OpenAQ or other consumers.
`1.14.7` adds `docs/NSOM_AOD_OPENAQ_SCORING_READINESS.md`, a developer-only
readiness audit for provider-backed aerosol inputs. The architecture decision is
that NASA AOD and OpenAQ remain Sky/Confidence diagnostics only until formal AOD
QA/uncertainty, OpenAQ locality/representativeness and double-counting policies
with VIIRS sky background, weather transparency and Moon geometry are accepted.
At that step, `ObservationConditionFeatureFlags.experimental_aerosol_scoring`
remained default-off and the current aerosol modifier remained `0.0`.
`1.14.8` adds `docs/NSOM_AOD_OPENAQ_PROVIDER_QUALITY_POLICY.md` and accepts
those provider-quality policies as explicit internal gates for a future
default-off experiment. AOD requires finite value, useful freshness,
uncertainty within threshold, QA raw traceability and sufficient local-pixel
support. OpenAQ PM requires local representativeness and is fallback/context
only. AOD and PM are not additive, and VIIRS sky background, weather
transparency and Moon geometry retain separate ownership. Scoring remains
disabled.
`1.14.9` implements that default-off experiment. When
`ObservationConditionFeatureFlags.experimental_aerosol_scoring=True`,
`ObservationConditionsService` computes a target-specific aerosol modifier from
the policy-selected source: AOD is primary, local OpenAQ PM is a weaker fallback,
freshness is an explicit formula input, and provider confidence remains outside
the score formula. The flag remains `False` by default, so runtime Planner, Home,
Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment, QML,
logging, network access and runtime file writes remain unchanged.
`1.14.11` adds `docs/NSOM_AOD_OPENAQ_CALIBRATION_AUDIT.md` as a developer-only
calibration review of that default-off formula. It does not tune weights or
enable the flag; it records score-scale and penalty-cap/transparency-shape as
default-on review items.
`1.14.12` applies the targeted formula-shape calibration: class caps are mapped
to maximum transparency loss and the score modifier is derived from
`target.score * transparency_loss`. The flag still remains default-off; only
absolute score-scale validation remains before any default-on decision.
`1.14.13` adds `docs/NSOM_AOD_OPENAQ_DEFAULT_ON_READINESS.md`. That audit keeps
the flag off, accepts provider quality, source ownership, formula shape and
confidence neutrality, and leaves absolute aerosol score scale as the only
default-on blocker.
`1.14.14` adds `docs/NSOM_AOD_OPENAQ_FIELD_CALIBRATION.md`. The deterministic
field-like fixtures pass the configured bands for clear air, moderate haze,
high AOD, PM fallback, stale AOD, rejected providers and protected
solar-system targets. The flag remains off until the synthetic scale is accepted
for a narrow switch or real observing outcomes are collected.
`1.14.15` adds `docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_PROBE.md`. The explicit
developer-only probe uses real NASA Earthdata AOD and OpenAQ responses for
Bologna, San Pedro de Atacama, New Delhi, Mauna Kea and Addis Ababa. It records
policy branches `none`, `aod` and `particulate`, keeps default flag-off scoring
neutral, and does not add runtime wiring, QML exposure, automatic logging or
credential disclosure. AOD/OpenAQ remains default-off pending human review of
the real-provider result.
`1.14.16` expands the same probe to 15 mixed locations and adds per-location
policy reasons to the report. The expanded run still observes `aod`,
`particulate` and `none`, confirms flag-off neutrality, and keeps deep-sky
penalties larger than planet/Moon penalties when the internal experimental
flag is enabled manually.
`1.14.17` adds `docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_READINESS_AUDIT.md`. The
offline audit reads that checked-in provider report, accepts the real-provider
score scale as directionally coherent, and keeps AOD/OpenAQ default-off because
all usable AOD inputs in the run are stale and the evidence is one temporal
snapshot.
`1.14.18` adds `docs/NSOM_AOD_OPENAQ_STALE_CURRENT_REPLAY_AUDIT.md`. The
offline replay treats the same real stale AOD values as current to test the
freshness policy. The current replay remains bounded and protected for
planet/Moon targets, so `stale=0.5` is accepted as a conservative policy while
the runtime flag remains off.
`1.14.19` adds `docs/NSOM_AOD_OPENAQ_DEFAULT_ON_SWITCH.md` and enables the
calibrated AOD/OpenAQ path by default:
`ObservationConditionFeatureFlags.experimental_aerosol_scoring=True`. The
rollback remains explicit through
`ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)`. No
formula, provider fetch, QML payload, report runtime wiring, logging or runtime
file write is added by the switch.
`1.15.0` adds `docs/NSOM_BACKEND_MIGRATION_CLOSEOUT.md` and closes the current
backend NSOM recommendation-surface migration scope. Planner, Home
`recommendedDeepSky`, Best Object, Advanced Observing backend, Sky Compass,
Detail/Object internal payload and AOD/OpenAQ condition scoring are all in their
intended default-on backend state. Remaining work is non-blocking and split into
future real-observing AOD/OpenAQ monitoring, Catalogue/Universe raw-score policy
and visible UI explanation design.

## Dependency Flow

The intended dependency flow is:

`QML -> AppController -> services/repositories -> models/data`

The services do not depend on QML. Repositories do not depend on services. The
controller composes repositories and services and converts dataclasses into
QML-friendly dictionaries.

The astronomy layer depends on Skyfield/Astropy when available and provides a
mock fallback through `MockAstronomyEngine`. Weather, VIIRS and NASA AOD network
clients are isolated behind service classes.

No circular Python package dependency was found in the reviewed structure.

## Responsibilities

### QML

QML pages are responsible for:

- visual layout and responsive presentation,
- binding to controller properties,
- invoking controller slots,
- local display formatting when the formatting is purely visual.

Important pages:

- `HomePage.qml`: home dashboard, observing quality, best target, observing
  plan, planets, deep-sky objects and weather warning presentation.
- `ObjectCataloguePage.qml`: informational catalogue browser with search,
  filters and object-detail click-through. It renders catalogue data and does
  not present recommendation ranking.
- `ObjectDetailPage.qml`: selected object detail and setup alternatives.
- `EquipmentProfilesPage.qml`, `EquipmentTelescopesPage.qml`,
  `EquipmentOpticsPage.qml`: profile and equipment management.
- `LocationPage.qml`, `WeatherPage.qml`, `CalendarPage.qml`,
  `EventDetailPage.qml`: location, weather, calendar list and calendar event
  detail workflows.

### AppController

`AppController` is the central Qt-facing object. It owns:

- current location state,
- current weather hours and weather summary,
- base and enriched solar-system objects,
- base and enriched deep-sky objects,
- Moon summary,
- visible planet/deep-sky lists,
- active profile equipment snapshot,
- sky quality, seeing/transparency and advanced scores,
- night plan and Sky Compass,
- generic catalogue object dictionaries and catalogue filter state,
- selected object and detail dictionaries,
- calendar event setup text and object-detail target mapping,
- QML signals for every major dependent property.

It also coordinates:

- startup loading,
- location refresh,
- weather refresh,
- VIIRS refresh,
- profile/equipment refresh,
- recomputation of best object, plan, Sky Compass and
  selected detail.

### Services

Services hold business logic:

- `ObservingScoreService`: global observing score and best-object selection.
- `AdvancedObservingService`: separate planetary and deep-sky quality scores.
- `SeeingTransparencyService`: seeing/transparency estimation from forecast
  fields and sky quality.
- `NightPlannerService`: ordered observing plan, weather blocking and
  chronological plan presentation. It delegates Planner ranking math to
  `PlannerScoringService`.
- `PlannerScoringService`: Planner-specific score aggregation, diagnostic
  breakdown, weather factor, difficulty factor and Planner-specific
  light-pollution penalty. It reuses shared Moon-condition primitives from
  `ObservationConditionsService`.
- `EquipmentService`: magnification, true field, exit pupil, profile
  capabilities and setup recommendation.
- `LightPollutionService`: sky-quality lookup from cache, local CSV providers,
  NASA VIIRS and offline fallback.
- `NasaAodProvider`: NASA MAIAC aerosol lookup using VIIRS primary and MODIS
  fallback. `AppController` starts it in the background when a valid location
  exists and Earthdata credentials have a successful connection test. It returns
  compact processed AOD results for the Weather page `Trasparenza atmosferica`
  section, but remains disconnected from seeing/transparency, Planner,
  Recommendation Engine, Sky Compass and observing scores.
- `ObservationConditionsService`: shared equivalence layer for observing
  condition adjustments. It owns Home/Detail Moon-adjusted scores, the existing
  deep-sky light-pollution context formerly implemented inside `AppController`,
  batch conditioning for Home/Sky Compass candidates and diagnostic placeholders
  for future weather/seeing/transparency/equipment inputs.
  It accepts provider-gated NASA AOD and particulate inputs with freshness
  notes. Since 1.14.19, the calibrated aerosol modifier is enabled by default
  through `ObservationConditionFeatureFlags.experimental_aerosol_scoring=True`;
  rollback is explicit by passing
  `ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)`.
  Runtime diagnostic freshness is explicit: NASA AOD older than seven days is
  omitted from diagnostic inputs; fresh/recent NASA AOD is included
  diagnostically only. OpenAQ data is included diagnostically when the
  `LocalAtmosphere` result has usable data, including stale-but-present readings,
  and omitted when historical, failed, unavailable or unconfigured. The 1.14.7
  readiness audit documents fresh AOD as the future primary aerosol-column source
  and OpenAQ PM as fallback/context. The 1.14.8 policy hardens provider-quality
  and double-counting gates; 1.14.9 implements the target-specific default-off
  formula; 1.14.11 audits its calibration without tuning weights or enabling it;
  1.14.12 maps the class cap to transparency loss before deriving the score
  modifier; 1.14.13 records default-on readiness as blocked only by score-scale
  acceptance; 1.14.14 records field-like calibration fixtures for that scale,
  1.14.15 records a real-provider probe across five mixed locations,
  1.14.16 expands it to 15 mixed locations with policy reasons, and 1.14.17
  accepts the observed score scale while deferring default-on for temporal AOD
  freshness/repeatability evidence. 1.14.18 replays those same real AOD values
  as current and accepts the stale/current freshness policy without enabling the
  flag.
  These inputs are not exposed to QML and do not affect Planner, Home, equipment,
  weather, seeing/transparency, advanced scores or Sky Compass unless the
  internal experimental flag is explicitly enabled.
  Deep-sky light-pollution conditioning marks targets with an internal condition
  flag so repeated passes do not reapply the same presentation penalty; the flag
  is intentionally removed from the QML payload.
  It does not own Planner score aggregation, equipment recommendations,
  best-object selection, OpenAQ or NASA AOD behavior.
- `OpenMeteoWeatherService`: forecast retrieval and weather cache integration.
- `SkyCompassService`: guidance DTO generation for the Sky Compass assistant
  from already prepared Home targets; it does not call weather, VIIRS, Planner
  or recommendation services.
- `LocationService`: Windows, IP and manual location providers.

### Repositories

Repositories own SQLite persistence:

- `CityRepository`: city search and reverse lookup.
- `MessierRepository`: Messier catalog rows.
- `EquipmentCatalogRepository`: telescope, eyepiece, Barlow and equipment
  profile CRUD and profile assignments.
- `WeatherCacheRepository`: weather response cache.
- `SkyQualityRepository`: light-pollution estimate cache.
- `ObjectImageRepository`: image and description lookup.
- `ObservationRepository`: observation history.

Repositories should not contain scoring or recommendation logic. The reviewed
repositories mostly respect this boundary.

## Data Flow

Startup flow:

1. `main.py` creates the application and `AppController`.
2. `AppController` initializes database-backed catalogs and profiles.
3. The astronomy engine builds base solar-system, Moon, calendar and deep-sky
   data for the current location if one is available.
4. Weather, sky quality, seeing, advanced scores, equipment recommendations and
   planning are layered on top.
5. QML receives property change signals and renders dictionaries exposed by the
   controller.

Home recommendation flow:

1. Astronomy engine produces base objects.
2. `AppController` applies active-profile equipment recommendations.
3. Deep-sky objects may be adjusted by light-pollution context and Home/Detail
   Moon context through `ObservationConditionsService`.
4. `BestObjectNsomSelectionService` selects Best Object by default when weather
   and sky quality are available; `ObservingScoreService` remains only the
   missing-sky fallback after internal rollback cleanup.
5. `NightPlannerService` produces the observing plan unless weather is
   blocking, using the NSOM Planner path by default. `PlannerScoringService`
   remains available for developer-only legacy formula comparison.
6. `AppController` exposes the centralized blocking state to QML.
7. QML presents the plan, a global "Sessione da monitorare" warning with a
   potential observing window, or a full "Sessione sconsigliata" warning when
   no useful window is expected.

Catalogue browsing flow:

1. `AppController` loads catalogue rows from repository-backed local data.
2. The current implementation maps Messier rows into a generic catalogue item
   shape with `catalogue`, `object_id`, `catalogue_id`, type, constellation,
   magnitude, size, observation-type metadata and description.
3. `ObjectCataloguePage.qml` applies controller-backed search and filters for
   catalogue, object type, constellation and observation type.
4. `selectCatalogueObject` resolves the catalogue object and creates a
   detail-compatible object without invoking weather, equipment suggestions,
   best-object scoring, planner ranking or `recommended_deep_sky()`.
5. Object Detail is reused for click-through, with back navigation returning
   to the catalogue page when that was the source.

Object detail flow:

1. QML selects an object.
2. `AppController` resolves the selected object from current enriched lists.
3. Detail fields, setup options and reasoning are generated from the selected
   object, active equipment, weather, Moon, seeing and sky quality.

Calendar event detail flow:

1. `CalendarPage.qml` selects an event from the inline calendar list.
2. `EventDetailPage.qml` renders practical observing text, profile guidance and
   field tips without changing event calculations.
3. `AppController._event_to_qml` enriches events with active-profile setup text
   and `targetObjectId` when the event maps to a known object.
4. Planetary opposition/conjunction events map to their planet object. Moon
   phases and lunar eclipses map to `moon`, allowing the existing object detail
   navigation to be reused.

## Refresh Flow

The controller refresh chain is the main consistency mechanism.

For a focused review of Home refresh timing, section dependencies and the
proposed future `ObservationSnapshot` read model for Home, Sky Compass and
Planner consumers, see `docs/HOME_REFRESH_LIFECYCLE_REVIEW.md`.

NightScope 1.2.x introduces `RefreshManager` as a lightweight lifecycle helper.
It does not own refresh work and does not decide whether QML is updated.
`AppController` remains the QML-facing orchestrator, while `RefreshManager`
classifies refresh reasons and domains, tracks dirty domains and documents
which dependencies are affected by each refresh family.

Current refresh domains are:

- `LOCATION`
- `ASTRONOMY`
- `WEATHER`
- `SKY_QUALITY`
- `AIR_QUALITY`
- `AOD`
- `EQUIPMENT`
- `PLANNER`
- `COMPASS`
- `COMPASS_LIVE`
- `CATALOG`

Current refresh reasons are:

- `STARTUP`
- `MANUAL`
- `LOCATION_CHANGED`
- `PROVIDER_CHANGED`
- `API_KEY_CHANGED`
- `EQUIPMENT_CHANGED`
- `BORTLE_CHANGED`
- `TTL_EXPIRED`
- `WEATHER_TTL_EXPIRED`
- `AIR_QUALITY_TTL_EXPIRED`
- `AOD_TTL_EXPIRED`
- `SKY_QUALITY_TTL_EXPIRED`
- `ASYNC_COMPLETED`
- `WEATHER_COMPLETED`
- `AIR_QUALITY_COMPLETED`
- `AOD_COMPLETED`
- `SKY_QUALITY_COMPLETED`
- `LIVE_TICK`

The generic `TTL_EXPIRED` and `ASYNC_COMPLETED` reasons are intentionally
neutral. Operational refresh dispatch should use the domain-specific reasons so
display-only OpenAQ/AOD updates cannot dirty Planner, equipment or Sky Compass
state by accident.

`LIVE_TICK` is the Sky Compass live refresh lane. It maps only to
`COMPASS_LIVE`, which is separate from the broader `COMPASS` domain used by
normal Home/Planner/weather-driven recomputation. The live lane updates only
current positional fields for already prepared Sky Compass targets and must not
call weather, OpenAQ, NASA AOD, VIIRS, Planner, equipment or Recommendation
Engine refresh paths.

The following changes are expected to trigger dependent recomputation:

- active profile switch,
- profile equipment assignment/removal,
- profile equipment deletion,
- catalog equipment addition when assigned to the active profile,
- location change,
- valid weather refresh,
- sky-quality refresh,
- VIIRS refresh completion,
- astronomy catalog reload caused by location or sky-quality context,
- selected object change.

Important methods:

- `_refresh_weather_and_conditions`
- `_finish_weather_refresh`
- `_finish_viirs_sky_quality_refresh`
- `_finish_nasa_aod_refresh`
- `_refresh_active_profile_dependencies`
- `_refresh_equipment_recommendations_for_current_objects`
- `_recalculate_observing_outputs`
- `_emit_profile_dependent_changes`

The refresh chain currently recomputes:

- best object,
- observing plan,
- visible planets,
- visible deep-sky objects,
- sky map,
- observing scores,
- recommended setups,
- selected-object setup/detail data.

NASA AOD refresh completion updates only the display DTO consumed by the Weather
page and logs product/date/value/status. It does not recompute Home, Planner,
Sky Compass, seeing/transparency, weather score, observing scores or
recommendation outputs.

Sky Compass live refresh is controller-owned and runs on a 60-second `QTimer`
only when a valid location, an available compass DTO and a stored candidate
snapshot exist. Normal Home/Planner refreshes compute `_sky_compass_candidates()`
and store the result in `AppController._sky_compass_candidate_snapshot`. The
live tick never calls `_sky_compass_candidates()`: it uses
`SkyfieldAstronomyEngine.refresh_current_positions()` to update current
altitude, azimuth and direction for the stored snapshot, emits only
`skyCompassChanged` and clears `COMPASS_LIVE` after the update.

Recent tests cover profile assignment, Barlow assignment, empty-profile
assignment and active-profile switching without restart.

## Cache Ownership

Weather cache:

- Owner: `OpenMeteoWeatherService` plus `WeatherCacheRepository`.
- Key: latitude, longitude, timezone and 24-hour forecast shape.
- Lifetime: 45 minutes.
- Force refresh bypasses fresh cache.
- On network failure, stale cached data may be reused when available.

Sky-quality cache:

- Owner: `LightPollutionService` plus `SkyQualityRepository`.
- Key: rounded latitude, longitude and city.
- Local cache is reused unless it is recognized as a legacy/stale source.
- NASA Black Marble VIIRS cache entries are treated as fresh if present.
- There is no general age-based TTL for sky-quality estimates.

NASA AOD cache:

- Owner: `NasaAodProvider`.
- Key: rounded latitude/longitude, with result metadata preserving product and
  granule id.
- Lifetime: 18 hours.
- Only compact processed AOD results are cached. The provider keeps an in-memory
  copy for the current process and a small JSON cache so app restarts can reuse
  recent processed results.
- Downloaded VIIRS/MODIS granules are temporary and deleted after extraction.

In-memory controller caches:

- base solar-system objects,
- base deep-sky objects,
- equipment-enriched object lists,
- weather hours,
- sky quality,
- seeing/transparency,
- advanced scores,
- night plan,
- Sky Compass,
- selected-object dictionary.

These are invalidated by controller refresh methods, not by a standalone cache
manager.

## Duplicated Logic And Technical Debt

The following duplication or concentration of responsibility should be tracked:

- Weather blocking is centralized in `NightPlannerService.weather_blocking_status`.
  `AppController` exposes `isObservingSessionBlocked`, `blockingReason`,
  `blockingDetail` and `suggestedObservingWindow`; QML renders those values
  without duplicating the thresholds.
- Score labels are implemented in `ObservingScoreService` and also separately
  in the astronomy engine for raw object scores.
- Night-hour selection is repeated in observing score, seeing estimation and
  home weather digest logic with slightly different ranges.
- Moon parsing from string percentages is repeated in multiple services.
- Light-pollution handling intentionally has two current contexts:
  Home/Detail deep-sky presentation context in `ObservationConditionsService`
  and Planner-specific ranking penalty in `PlannerScoringService`. These
  formulas are behavior-preserving and should not be merged without dedicated
  equivalence tests.
- Moon sensitivity is centralized in `ObservationConditionsService`, while
  `PlannerScoringService` owns how that penalty is combined with Planner
  weather, difficulty and aperture factors.
- `AppController` is oversized and mixes controller, presenter and orchestration
  responsibilities.
- `HomePage.qml` is also large and contains non-trivial presentation decisions.
- `EquipmentProfile.telescope_id` remains as a legacy single-telescope field
  while many-to-many profile assignment tables hold the current multi-equipment
  model.

These are not immediate functional failures, but they are the main
maintainability risks for a 1.0 codebase.

## Maintenance Guidance

For future changes:

- Put new calculation rules in services, not QML.
- Keep repositories focused on persistence.
- Treat `AppController` as an orchestration boundary; avoid adding new
  algorithms there unless they are purely presentation-specific.
- When changing profile/equipment behavior, add tests that assert immediate
  refresh of home, detail and calendar/profile-dependent outputs.
- When changing weather blocking thresholds, update
  `NightPlannerService.weather_blocking_status` and keep QML as a renderer of
  controller state.
- When changing Moon or light-pollution logic, verify Home/Detail conditioned
  objects and Planner ranking separately for galaxies, nebulae, globular
  clusters and open clusters.
- Before enabling new AOD/OpenAQ or transparency scoring, use
  `docs/NIGHTSCOPE_OBSERVATION_MODEL_1_0.md` and
  `docs/NSOM_AOD_OPENAQ_SCORING_READINESS.md` plus
  `docs/NSOM_AOD_OPENAQ_PROVIDER_QUALITY_POLICY.md` and
  `docs/NSOM_AOD_OPENAQ_DEFAULT_OFF_SCORING_EXPERIMENT.md` as the mathematical
  ownership, provider-quality, double-counting and default-off formula
  references.
- When changing calendar event copy or event-to-object linking, keep practical
  text in `EventDetailPage.qml` and target/setup enrichment in `AppController`.
