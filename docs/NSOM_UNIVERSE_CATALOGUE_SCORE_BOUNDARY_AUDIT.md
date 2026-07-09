# NSOM Universe/Catalogue Score Boundary Audit

## Executive Summary

This developer-only audit reviews the remaining raw catalogue/prepared-object score boundary after the backend NSOM recommendation surfaces were closed and internal rollback paths were removed. It does not change scoring, runtime ranking, QML, logging, network access or runtime file writes.

## Verdict

- Verdict: `universe_catalogue_score_boundary_audited`.
- Runtime migration recommended now: `False`.
- Score change recommended now: `False`.
- Safe to keep `score` as interim intrinsic seed: `True`.
- Blocks current default-on surfaces: `False`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next step: Review 1.13.9, then decide whether to introduce an explicit UniverseTargetProfile/catalogue intrinsic read model before visible UI explanation work.
- Reason: The current default-on backend surfaces already consume NSOM values, but the first Universe input is still the prepared `CelestialObject.score`. That score is acceptable as an interim IntrinsicTargetQuality seed because the ObservationConditions read model keeps raw target input separate from display conditioning. It should not be treated as final presentation semantics or as a future calibration target.

## Score Semantics

| Score concept | Owner | Runtime role | NSOM policy |
| --- | --- | --- | --- |
| CelestialObject.score | prepared target DTO / Universe seed compatibility | Input to IntrinsicTargetQuality and existing QML-compatible display score fields. | Accepted interim intrinsic seed; future work should expose provenance rather than tune the raw field directly. |
| NightPlanItem.score | Planner output | Final Planner payload score after NSOM opportunity ranking. | Planner result, not Universe input; keep separate from IntrinsicTargetQuality provenance. |
| Equipment setup score | Equipment setup-local service | Ranks practical setup/eyepiece/Barlow suggestions. | Setup-local score remains outside ObservableTargetValue; it can inform ObserverCapability boundaries but is not a target score. |
| Payload/display score | QML compatibility presentation | Existing visible payload field shape and labels. | Presentation compatibility only; visible score semantics require a separate UI/design step. |

## Boundary Inventory

| Surface | Classification | Score role | Ranking authority | Risk | Decision |
| --- | --- | --- | --- | --- | --- |
| Skyfield/catalogue prepared objects | `catalogue_engine_intrinsic_seed` | Computes raw object score from altitude, magnitude, type and visibility. | NSOM consumers adapt it into IntrinsicTargetQuality. | Not a pure immutable catalogue fact because location geometry and visibility are already present. | accept_as_interim_universe_seed |
| NSOM intrinsic adapter | `universe_adapter` | Maps target.score through IntrinsicTargetQuality.from_score(). | Universe-owned input to ObservableTargetValue, PracticalTargetValue and ObservationOpportunity. | Adapter cannot yet distinguish catalogue, engine and fixture score provenance. | keep_stable_until_explicit_universe_profile |
| ObservationConditions read model | `closed_raw_display_boundary` | Separates raw_score/nsom_target_input from display_score/qml_display_target. | Raw target input for NSOM consumers after the 1.12 reroute. | Display-conditioned score remains visible for payload compatibility. | accepted_boundary_prevents_conditioning_from_becoming_intrinsic |
| Home recommendedDeepSky | `default_on_nsom_consumer` | Keeps score field in payload while ranking by ObservableTargetValue. | ObservableTargetValue from raw target plus sky environment. | Displayed score may be non-monotonic with NSOM order until UI semantics change. | presentation_followup_not_backend_blocker |
| Best Object | `default_on_nsom_consumer` | Returns existing display target while scoring a raw-target NSOM opportunity. | Home-specific ObservationOpportunity. | Visible payload still carries compatibility score. | presentation_followup_not_backend_blocker |
| Sky Compass | `default_on_nsom_consumer` | Keeps target.score in direction payload while direction policy uses observable value. | ObservableTargetValue plus direction/presentation context. | Direction score is intentionally a presentation policy, not pure target value. | accepted_direction_policy_boundary |
| Planner | `default_on_nsom_consumer` | Uses target.score as intrinsic seed and emits NightPlanItem.score as result. | ObservationOpportunity.value. | Input and output score names remain easy to confuse in diagnostics. | document_input_output_score_boundary |
| Equipment recommendations | `setup_local_non_universe_score` | Setup score ranks equipment choices, not target desirability. | EquipmentService setup-local compatibility logic. | Should not be folded into ObservableTargetValue. | keep_outside_universe_score_boundary |

## Boundary Decisions

| Decision | Status | Affected layer | Blocks default-on work | Reason |
| --- | --- | --- | --- | --- |
| `catalogue_score_as_intrinsic_seed` | `accepted_interim` | Universe / IntrinsicTargetQuality | `False` | Current NSOM consumers need a stable intrinsic seed. The prepared score is already sanitized and clamped by IntrinsicTargetQuality, and read-model rerouting prevents display conditioning from being used as intrinsic input. |
| `prepared_score_provenance` | `deferred_targeted_backend_policy` | Universe / catalogue read model | `False` | The source field does not yet encode whether the number came from catalogue fixtures, Skyfield geometry, comparison fixtures or a display payload. That should be made explicit before future calibration, but it does not invalidate the current backend paths. |
| `payload_score_semantics` | `presentation_followup` | Presentation | `False` | Existing payload shapes still expose score fields. They are kept for UI compatibility and should be redesigned only in a visible presentation step. |
| `equipment_score_boundary` | `accepted_setup_local` | Observer / Equipment setup service | `False` | Equipment setup scoring is not an intrinsic target score and is kept outside ObservableTargetValue. |

## Remaining Policy Items

| Item | Status | Blocking | Recommended handling |
| --- | --- | --- | --- |
| Explicit UniverseTargetProfile / catalogue intrinsic read model | `deferred_non_blocking` | `False` | Introduce only when there is a concrete need to expose provenance or replace the current prepared-score seed. |
| Visible score semantics | `presentation_followup` | `False` | Design after backend score ownership is stable; do not reuse payload score as an NSOM explanation. |
| Catalogue score calibration | `not_recommended_now` | `False` | Do not tune raw score directly; first separate provenance and physical components if calibration evidence requires it. |

## Source Marker Checks

| Surface | Path | All markers found | Missing markers |
| --- | --- | --- | --- |
| CelestialObject score DTO field | `astro_viewer/app/models/observing.py` | `True` | `[]` |
| Skyfield raw object score | `astro_viewer/app/astronomy/skyfield_engine.py` | `True` | `[]` |
| NSOM intrinsic adapter | `astro_viewer/app/services/nsom_diagnostic_adapters.py` | `True` | `[]` |
| Home observable adapter | `astro_viewer/app/services/home_nsom_observable.py` | `True` | `[]` |
| ObservationConditions raw/display read model | `astro_viewer/app/services/observation_conditions_read_model.py` | `True` | `[]` |
| Best Object NSOM selection | `astro_viewer/app/services/best_object_nsom_ranking.py` | `True` | `[]` |
| Sky Compass NSOM direction policy | `astro_viewer/app/services/sky_compass_nsom_ranking.py` | `True` | `[]` |
| Planner NSOM opportunity scoring | `astro_viewer/app/services/planner_nsom_service.py` | `True` | `[]` |
| Equipment setup score boundary | `astro_viewer/app/services/equipment_setup_score_read_model.py` | `True` | `[]` |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `source_markers_all_found` | `True` |
| `intrinsic_adapter_boundary_present` | `True` |
| `read_model_raw_display_boundary_present` | `True` |
| `payload_scores_classified_as_compatibility` | `True` |
| `equipment_score_kept_outside_universe` | `True` |
| `no_decision_blocks_default_on_work` | `True` |
| `remaining_policy_items_non_blocking` | `True` |
| `confidence_not_in_score_boundary` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.13.9`: Confirm raw score ownership is described accurately and no runtime ranking changed.
- `Universe intrinsic profile policy`: If needed, design a first-class UniverseTargetProfile that makes catalogue/prepared score provenance explicit.
- `Visible explanation design`: Only after backend score semantics are clear, decide what the UI should show instead of legacy/base score compatibility.

## Conclusion

The raw `CelestialObject.score` boundary is now explicitly classified. It remains an interim Universe/IntrinsicTargetQuality seed and a compatibility display field, not an NSOM score to tune or a runtime rollback target. Future work should make catalogue score provenance explicit before visible score/explanation design.
