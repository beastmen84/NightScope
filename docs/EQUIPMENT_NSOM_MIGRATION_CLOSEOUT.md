# Equipment NSOM Migration Closeout

## Executive Summary

This developer-only closeout records Equipment as an NSOM-bounded setup-local service. It does not add an Equipment NSOM runtime path, change setup recommendation ranking, expose QML fields, log, access the network or write files at runtime.

## Verdict

- Verdict: `equipment_nsom_migration_closed_setup_local`.
- Migration closed: `True`.
- Setup-local service: `True`.
- Default-off Equipment path added: `False`.
- Default-off Equipment path recommended now: `False`.
- Runtime replacement ready: `False`.
- Ready to return to backend planning: `True`.
- Runtime behaviour changed by closeout: `False`.
- Recommended next step: Review 1.13.5, then choose the next backend NSOM area or run an overall backend readiness audit.
- Reason: Equipment is not a target-ranking surface. It remains a setup-local service that selects concrete eyepiece, zoom-position, Barlow, binocular and fallback payload rows for a selected target. The NSOM migration is closed by keeping explicit ObserverCapability/Q_target, presenter, score ownership and component boundaries without adding a runtime replacement path.

## Closed Decisions

| Decision | Status | Blocks next backend planning | Reason |
| --- | --- | --- | --- |
| `observer_capability_adapter` | `closed_shared_adapter_available` | `False` | The policy readiness data confirms the shared ObserverCapability/Q_target adapter is extracted. |
| `presenter_contract_boundary` | `closed_runtime_neutral_read_model` | `False` | The presenter contract audit confirms payload and setup-option keys are preserved through an immutable read-model boundary. |
| `setup_score_ownership` | `closed_owned_by_equipment_service` | `False` | The ownership audit classifies the current setup score as a local EquipmentService formula, not a drop-in NSOM scalar. |
| `setup_score_component_boundary` | `closed_with_parity_read_model` | `False` | The component boundary exposes real score components without changing the clamped setup score. |
| `default_off_replacement_policy` | `closed_no_default_off_path_now` | `False` | The policy audit rejects a default-off Equipment replacement path now and keeps Equipment setup-local with explicit NSOM boundaries. |
| `confidence_policy` | `closed_metadata_only` | `False` | RecommendationConfidence remains parallel metadata with zero score effect. |

## Evidence

- Scenario count: `5`.
- Candidate row count: `34`.
- Observer adapter extracted: `True`.
- Presenter contract audited: `True`.
- Runtime setup read-model boundary present: `True`.
- Score ownership audited: `True`.
- Score component boundary introduced: `True`.
- Score component boundary parity checked: `True`.
- Default-off policy set: `True`.
- Default-off path recommended now: `False`.
- Confidence score-neutral: `True`.

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `all_required_equipment_reports_present` | `True` |
| `observer_adapter_extracted` | `True` |
| `presenter_contract_preserved` | `True` |
| `setup_score_ownership_audited` | `True` |
| `component_boundary_parity_checked` | `True` |
| `default_off_path_absent` | `True` |
| `setup_local_policy_closed` | `True` |
| `confidence_score_neutral` | `True` |
| `no_closeout_blockers` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
| `runtime_behaviour_unchanged_by_closeout` | `True` |

## Static Wiring

- Runtime report imports: `[]`.
- QML report exposure: `[]`.

## Recommended Sequence

- `Review 1.13.5`: Confirm Equipment is closed as an NSOM-bounded setup-local service and no runtime behaviour changed.
- `Next backend NSOM area selection audit`: Choose the next backend area, or run an overall backend readiness audit before visible UI/explanation work.

## Conclusion

The Equipment NSOM migration is closed for the current backend scope. `EquipmentService` remains the runtime setup recommender, while NSOM ownership is explicit through shared observer capability, presenter, score ownership and score-component boundaries. A future Equipment UI/explanation step may present these boundaries, but that is separate from backend migration.
