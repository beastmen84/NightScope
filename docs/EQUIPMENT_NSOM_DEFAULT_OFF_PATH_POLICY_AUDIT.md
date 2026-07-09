# Equipment NSOM Default-Off Path Policy Audit

## Executive Summary

This developer-only audit decides whether Equipment should gain a default-off NSOM replacement path. The decision is no: Equipment remains a setup-local recommendation service with NSOM boundaries and metadata. No runtime scoring, payload, QML, logging, network or file write behaviour changes.

## Verdict

- Verdict: `equipment_default_off_path_policy_set_setup_local`.
- Default-off Equipment path recommended now: `False`.
- Setup-local service recommended: `True`.
- Runtime replacement ready: `False`.
- Component boundary ready: `True`.
- Component boundary parity checked: `True`.
- Blocks backend migration closeout: `False`.
- Runtime behaviour changed by policy: `False`.
- Recommended next step: Review 1.13.4, then close the Equipment backend NSOM migration as setup-local with NSOM boundaries.
- Reason: EquipmentService recommends configurations for a selected target. Its setup score includes eyepiece, Barlow, binocular, seeing, sky quality and fallback semantics that Q_target and PracticalTargetValue do not replace. The NSOM boundary is now explicit, so a default-off replacement path would add complexity without a model requirement.

## Policy Options

| Option | Status | Runtime path | Reason |
| --- | --- | --- | --- |
| `add_default_off_nsom_equipment_path` | `rejected_now` | `False` | A replacement path would need to reproduce eyepiece, focal-position, Barlow, binocular and fallback semantics. Q_target and PracticalTargetValue do not own those setup choices. |
| `keep_equipment_setup_local_with_nsom_boundaries` | `accepted` | `True` | The presenter contract and component boundary preserve current runtime behaviour while making NSOM ownership explicit. |
| `future_equipment_explanation_metadata` | `deferred_non_blocking` | `False` | Future UI/explanation work may expose why a setup was chosen, but that is presentation work and not required for backend NSOM closure. |

## Policy Decisions

| Decision | Status | Blocks closeout | Reason |
| --- | --- | --- | --- |
| `equipment_runtime_policy` | `setup_local_service_accepted` | `False` | The presenter contract and component boundary preserve current runtime behaviour while making NSOM ownership explicit. |
| `default_off_replacement_policy` | `not_recommended_now` | `False` | A replacement path would need to reproduce eyepiece, focal-position, Barlow, binocular and fallback semantics. Q_target and PracticalTargetValue do not own those setup choices. |
| `q_target_replacement_policy` | `rejected_as_direct_replacement` | `False` | Q_target can describe observer capability metadata, but it does not rank concrete eyepiece, Barlow, focal-position or binocular setup rows. |
| `confidence_policy` | `accepted_metadata_only` | `False` | RecommendationConfidence remains parallel metadata with zero score effect. |

## Evidence

- Scenario count: `5`.
- Candidate row count: `34`.
- Component boundary parity checked: `True`.
- Fallback payload preserved: `True`.
- Q_target direct replacement rejected: `True`.
- Confidence score-neutral: `True`.
- Legacy formula unavailable components are marked unavailable: `True`.

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `default_off_path_rejected_now` | `True` |
| `setup_local_service_accepted` | `True` |
| `component_boundary_parity_checked` | `True` |
| `presenter_contract_preserved` | `True` |
| `q_target_direct_replacement_rejected` | `True` |
| `confidence_score_neutral` | `True` |
| `legacy_unavailable_components_marked` | `True` |
| `no_decision_blocks_closeout` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_policy` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.13.4`: Confirm Equipment should remain setup-local and that no default-off replacement path is needed now.
- `1.13.5 Equipment NSOM migration closeout`: Close Equipment as an NSOM-bounded setup service and return to overall backend migration planning.

## Conclusion

Equipment should not get a default-off NSOM replacement path now. The correct backend state is an Equipment-owned setup service with explicit NSOM ownership, component and presenter boundaries.
