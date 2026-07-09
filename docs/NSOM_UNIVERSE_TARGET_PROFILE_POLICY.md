# NSOM UniverseTargetProfile Policy

## Executive Summary

This developer-only policy report decides whether to introduce a first-class UniverseTargetProfile after the 1.13.9 raw score boundary audit. The decision is no for now: keep the current IntrinsicTargetQuality adapter and defer the profile until a concrete provenance, catalogue-import, calibration or visible explanation need exists. No runtime scoring, ranking, QML, logging, network or runtime file-write behaviour changes.

## Verdict

- Verdict: `universe_target_profile_deferred_non_blocking`.
- Introduce runtime profile now: `False`.
- Keep current intrinsic adapter: `True`.
- Score change recommended now: `False`.
- Visible UI change recommended now: `False`.
- Blocks current default-on surfaces: `False`.
- Runtime behaviour changed by this policy: `False`.
- Recommended next step: Review 1.14.0, then start visible score/explanation policy only if the UI needs to present NSOM rationale; otherwise keep the backend stable.
- Reason: A first-class UniverseTargetProfile would currently duplicate IntrinsicTargetQuality plus diagnostic source fields without changing any backend recommendation. The score boundary audit already prevents display-conditioned scores from becoming intrinsic target input, so the runtime profile should wait until there is a concrete provenance, catalogue-import, intrinsic-calibration or visible explanation requirement.

## Policy Options

| Option | Status | Runtime impact | Reason |
| --- | --- | --- | --- |
| `introduce_runtime_universe_target_profile_now` | `rejected_now` | `would add runtime DTO/adaptation churn` | Current default-on NSOM consumers already receive IntrinsicTargetQuality. A new runtime profile would mostly wrap the same prepared score and source fields without new semantics. |
| `keep_intrinsic_target_quality_adapter` | `accepted` | `none` | The adapter is already immutable/JSON-compatible through NSOM DTOs, and the read-model boundary keeps display-conditioned score out of intrinsic input. |
| `define_future_profile_contract_only` | `accepted_developer_policy` | `none` | Documenting the future fields prevents ad hoc provenance work without introducing unused runtime code. |
| `start_visible_score_explanation_now` | `deferred` | `would require UI/presentation policy` | Visible explanation should be a separate design step after backend score ownership is stable. |

## Policy Decisions

| Decision | Status | Affected layer | Blocks runtime | Reason |
| --- | --- | --- | --- | --- |
| `runtime_universe_target_profile` | `deferred_non_blocking` | Universe | `False` | No current consumer requires a distinct profile beyond IntrinsicTargetQuality and diagnostic source fields. |
| `intrinsic_adapter_policy` | `keep_current_adapter` | Universe / IntrinsicTargetQuality | `False` | The current adapter is the stable input boundary for default-on Planner, Home, Best Object, Sky Compass, Advanced Observing and Detail/Object projections. |
| `score_provenance_policy` | `future_entry_criterion` | Universe / catalogue read model | `False` | Provenance becomes necessary before intrinsic calibration or visible score explanation, but is not required for the current closed backend recommendations. |
| `visible_score_policy` | `separate_presentation_step` | Presentation | `False` | QML payload score compatibility remains unchanged; visible NSOM rationale needs product/UI policy before code exposure. |

## Future Profile Contract

| Field | Owner | Source today | Required before implementation |
| --- | --- | --- | --- |
| `object_id` | Universe | CelestialObject.id | already available |
| `target_class` | Universe | target_class_from_runtime_target() | already available |
| `intrinsic_score_seed` | Universe | CelestialObject.score | explicit provenance label |
| `score_provenance` | Universe / catalogue read model | not explicit | catalogue, engine, fixture and display-source distinction |
| `geometry_summary` | Universe/location geometry | max_altitude, visible, observing_window | define which geometry is intrinsic seed vs session opportunity |
| `magnitude_and_size` | Universe | magnitude, apparent_size | already available but surface-brightness model remains future work |
| `display_score_projection` | Presentation | existing payload score fields | keep out of UniverseTargetProfile unless explicitly labelled presentation-only |

## Future Entry Criteria

| Criterion | Status | Why it matters |
| --- | --- | --- |
| `intrinsic_calibration_requested` | `not_active` | Calibrating target intrinsic value requires provenance and physical component separation. |
| `multiple_catalogue_sources_active` | `not_active` | Different catalogue/import sources would need explicit source and score provenance. |
| `visible_score_explanation_required` | `not_active` | UI explanation should not expose raw payload score as if it were the final NSOM rationale. |
| `remove_celestial_object_score_payload` | `not_active` | Removing compatibility score fields requires a replacement presentation contract. |
| `surface_brightness_model_added` | `not_active` | A richer intrinsic model would justify a dedicated Universe DTO instead of a score-seed adapter. |

## Source Marker Checks

| Surface | Path | All markers found | Missing markers |
| --- | --- | --- | --- |
| IntrinsicTargetQuality core DTO | `astro_viewer/app/models/nsom.py` | `True` | `[]` |
| Runtime intrinsic adapter | `astro_viewer/app/services/nsom_diagnostic_adapters.py` | `True` | `[]` |
| ObservationConditions raw target input | `astro_viewer/app/services/observation_conditions_read_model.py` | `True` | `[]` |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `score_boundary_audit_clean` | `True` |
| `runtime_profile_not_recommended_now` | `True` |
| `current_intrinsic_adapter_kept` | `True` |
| `future_contract_documented` | `True` |
| `entry_criteria_all_non_active` | `True` |
| `policy_decisions_non_blocking` | `True` |
| `source_markers_all_found` | `True` |
| `intrinsic_dto_boundary_present` | `True` |
| `read_model_boundary_present` | `True` |
| `no_scoring_change` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_policy` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.14.0`: Confirm the UniverseTargetProfile deferral is accurate and does not hide a runtime scoring bug.
- `Visible score/explanation policy`: Decide what, if anything, the UI should show for NSOM score rationale without changing the established QML layout first.
- `Future UniverseTargetProfile implementation`: Implement only when entry criteria such as score provenance, new catalogue imports or intrinsic calibration are active.

## Conclusion

UniverseTargetProfile is a valid future boundary, but introducing it now would add a pass-through abstraction without improving runtime recommendations. Keep IntrinsicTargetQuality as the current internal Universe DTO, keep CelestialObject.score as an interim intrinsic seed, and revisit the profile only when provenance or visible explanation requirements become concrete.
