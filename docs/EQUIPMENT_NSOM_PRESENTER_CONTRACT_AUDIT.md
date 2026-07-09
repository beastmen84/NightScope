# Equipment NSOM Presenter Contract Audit

## Executive Summary

This developer-only audit defines the presenter contract that must exist before any Equipment runtime scoring replacement. It does not change EquipmentService, Planner, Home, Best Object, Sky Compass, Detail/Object, QML, logging, network behaviour or runtime file writes.

## Verdict

- Verdict: `equipment_setup_read_model_boundary_introduced`.
- Presenter contract audited: `True`.
- Runtime replacement ready: `False`.
- Runtime read-model boundary recommended: `False`.
- Runtime read-model boundary present: `True`.
- Default-off Equipment path recommended now: `False`.
- Runtime behaviour changed by this audit: `False`.
- Recommended next step: Review 1.13.1, then audit EquipmentService setup-score ownership before any scoring replacement.
- Reason: Equipment is an active setup-presentation helper. The existing runtime payload owns eyepiece, Barlow, binocular, fallback and setupOptions fields that Q_target does not replace. A runtime-neutral setup read-model boundary now preserves that payload before AppController projects it to CelestialObject fields. NSOM can own ObserverCapability/Q_target and future PracticalTargetValue metadata, but EquipmentService scoring is not ready for replacement.

## Presenter Contract

- Runtime role: `active_practical_setup_presenter`.
- NSOM-owned input: `ObserverCapability_profile_Q_target_reference`.
- Presentation-owned output: `equipment_setup_payload_and_setupOptions`.
- Replacement policy: `defer_scoring_replacement_until_setup_read_model_exists`.
- QML policy: `preserve_existing_payload_no_nsom_fields`.
- Confidence policy: `metadata_only_zero_score_effect`.

## Payload Shape

- Suggestion payload keys: `['bestEyepiece', 'suggestedPosition', 'barlow', 'difficulty', 'alternative', 'highMagnification', 'wideField', 'setupText', 'setupOptions', 'explanation', 'telescopeId', 'telescopeName', 'equipmentType', 'setupType', 'selectionScore']`.
- Setup option keys: `['role', 'label', 'detailLabel', 'displayLabel', 'suggestedPosition', 'magnification', 'trueField', 'exitPupil', 'barlow', 'score', 'telescopeName', 'equipmentType']`.
- Setup option roles: `['Consigliato', 'Alternativa', 'Alto ingrandimento', 'Campo largo']`.
- Fallback payloads are compatible subsets: `True`.
- Read-model payload roundtrip matches service output: `True`.
- Read-model celestial projection keys: `['recommended_setup', 'best_eyepiece', 'barlow', 'difficulty', 'recommended_setup_type', 'setup_options', 'equipment_explanation']`.

## Contract Decisions

| Decision | Status | Layer | Blocks runtime replacement | Summary |
| --- | --- | --- | --- | --- |
| `equipment_runtime_role` | `accepted` | `presentation` | `True` | Equipment remains the runtime setup presenter, not a target recommendation score. |
| `payload_shape_contract` | `accepted` | `presentation` | `True` | Future work must preserve suggestion payload keys and setupOptions roles. |
| `q_target_policy` | `accepted_reference_only` | `observer` | `True` | Q_target is a reference projection for PracticalTargetValue, not a setup-option score. |
| `seeing_and_sky_boundary` | `needs_score_ownership_audit` | `sky` | `True` | Seeing and sky quality need explicit setup-score ownership review before Equipment scoring can be separated from legacy mixing. |
| `fallback_policy` | `accepted` | `presentation` | `True` | Naked-eye, missing-eyepiece and no-useful-configuration fallbacks stay presenter-owned. |
| `selection_score_policy` | `accepted_compatibility` | `presentation` | `True` | selectionScore remains a setup-local compatibility score until replaced by a named setup metric. |
| `confidence_policy` | `accepted` | `confidence` | `False` | RecommendationConfidence remains metadata only and does not affect Equipment score or Q_target. |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `required_contract_decisions_recorded` | `True` |
| `payload_keys_preserved` | `True` |
| `setup_option_keys_preserved` | `True` |
| `recommended_setup_option_present` | `True` |
| `fallback_payloads_are_known_subsets` | `True` |
| `read_model_payload_roundtrip_preserves_service_output` | `True` |
| `read_model_celestial_projection_preserves_contract` | `True` |
| `q_target_reference_only` | `True` |
| `policy_runtime_replacement_deferred` | `True` |
| `observer_capability_adapter_extracted` | `True` |
| `comparison_evidence_available` | `True` |
| `confidence_score_neutral` | `True` |
| `controller_projection_fields_present` | `True` |
| `setup_read_model_boundary_present` | `True` |
| `qml_payload_consumers_present` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_audit` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.
- AppController Equipment projection fields present: `True`.
- AppController uses Equipment setup read-model boundary: `True`.
- QML uses current Equipment payload fields: `True`.

## Recommended Sequence

- `Review 1.13.1`: Confirm the Equipment setup read-model boundary preserves runtime output and QML payload shape.
- `1.13.2 Equipment setup score ownership audit`: Separate setup score components, sky/seeing inputs and presentation-owned fallback semantics before any scoring replacement.

## Conclusion

Equipment should not be migrated by replacing its setup score with Q_target. The setup read-model boundary now preserves the current payload while making ObserverCapability/Q_target ownership explicit; the next work is score-ownership review.
