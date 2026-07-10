# NSOM Backend Migration Closeout

## Executive Summary

This developer-only closeout records that the backend NSOM migration for recommendation surfaces is complete for the current scope. It does not change scoring, Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment, QML, logging, network access or runtime file writes.

## Verdict

- Verdict: `backend_nsom_recommendation_surfaces_closed`.
- Migration status: `closed_for_backend_recommendation_surfaces`.
- Runtime behaviour changed by closeout: `False`.
- Ready for visible UI redesign: `False`.
- Backend default-on blockers: `[]`.
- Recommended next step: Review this closeout, then monitor AOD/OpenAQ real observing feedback. Future work should treat Catalogue/Universe raw-score semantics and visible UI explanations as separate design steps.
- Reason: Planner, Home recommendedDeepSky, Best Object, Advanced Observing backend, Sky Compass and Detail/Object are default-on NSOM surfaces. AOD/OpenAQ condition scoring is also default-on after the 1.14.19 switch. Equipment remains intentionally setup-local, ObservationConditions remains an active raw/display compatibility boundary, and Catalogue raw scores remain upstream Universe input policy rather than a ranking hotfix.

## Closed Backend Surfaces

| Surface | Status | Default flag | NSOM role |
| --- | --- | --- | --- |
| `Planner` | `default_on_closed` | `NSOM_PLANNER_SCORING_ENABLED = True` | ObservationOpportunity ranking |
| `Home recommendedDeepSky` | `default_on_closed` | `NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED = True` | ObservableTargetValue ordering |
| `Best Object` | `default_on_closed` | `NSOM_BEST_OBJECT_ENABLED = True` | Home-specific ObservationOpportunity selection |
| `Advanced Observing backend` | `default_on_closed_backend_only` | `NSOM_ADVANCED_OBSERVING_ENABLED = True` | category ObservableTargetValue projection |
| `Sky Compass` | `default_on_closed` | `NSOM_SKY_COMPASS_ENABLED = True` | ObservableTargetValue based direction policy |
| `Detail/Object internal payload` | `default_on_closed_backend_only` | `NSOM_DETAIL_OBJECT_ENABLED = True` | separate internal Detail/Object payload |

## AOD/OpenAQ Switch State

- Default flag: `ObservationConditionFeatureFlags.experimental_aerosol_scoring = True`.
- Rollback: `ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)`.
- Formula changed: `False`.
- Weights changed: `False`.
- Provider calls changed: `False`.
- Confidence metadata does not scale score: `True`.

## Remaining Non-Blocking Items

| Area | Status | Recommended handling |
| --- | --- | --- |
| `Equipment recommendations` | `equipment_nsom_migration_closed_setup_local` | Keep Equipment as a setup-local service; rollback cleanup is complete, so visible UI/explanation or Universe/catalogue policy can be considered separately. |
| `ObservationConditions prepared-object cache` | `observation_conditions_consumer_reroute_closed` | Keep the read-model boundary as active compatibility code; no ObservationConditions consumer reroute work remains open. |
| `Catalogue / raw object score` | `upstream_legacy_input` | Treat as Universe/read-model work, not as a ranking hotfix. |

## Future Work Policy

| Area | Status | Blocks backend closeout | Policy |
| --- | --- | --- | --- |
| `AOD/OpenAQ real observing feedback` | `monitor_before_tuning` | `False` | Do not tune weights until enough real observing outcomes are reviewed. |
| `Catalogue / Universe raw score semantics` | `future_universe_policy` | `False` | Clarify intrinsic catalogue scores as Universe inputs, not as a ranking hotfix. |
| `Visible UI explanations` | `future_design_step` | `False` | Keep UI unchanged until backend explanations and display semantics are designed explicitly. |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `backend_status_has_no_blockers` | `True` |
| `all_current_default_on_surfaces_closed` | `True` |
| `aod_openaq_default_on` | `True` |
| `aod_openaq_rollback_documented` | `True` |
| `aod_openaq_confidence_score_neutral` | `True` |
| `remaining_items_are_non_blocking` | `True` |
| `visible_ui_redesign_not_started` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
