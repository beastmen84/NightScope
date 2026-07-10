# NSOM Backend Migration Closeout

## Executive Summary

This developer-only closeout records that the backend NSOM migration for recommendation surfaces is complete for the current scope. It does not change scoring, Planner, Home, Best Object, Advanced Observing, Sky Compass, Detail/Object, Equipment, QML, logging, network access or runtime file writes.

## Verdict

- Verdict: `backend_nsom_recommendation_surfaces_closed`.
- Migration status: `closed_for_backend_recommendation_surfaces`.
- Runtime behaviour changed by closeout: `False`.
- Ready for visible UI redesign: `False`.
- Backend default-on blockers: `[]`.
- Recommended next step: Review this closeout, then perform the separate visible UI verification/design step. Monitor AOD/OpenAQ real observing feedback after real program use before tuning.
- Reason: Planner, Home recommendedDeepSky, Best Object, Advanced Observing backend, Sky Compass and Detail/Object are default-on NSOM surfaces. AOD/OpenAQ condition scoring is also default-on after the 1.14.19 switch. Equipment remains intentionally setup-local, ObservationConditions remains an active raw/display compatibility boundary, and Catalogue raw scores have been reviewed as upstream backend Universe input policy rather than a ranking hotfix or visible UI score.

## Visible UI Readiness Meaning

`Ready for visible UI redesign: False` does not mean the UI is broken and does
not block the backend NSOM closeout. It means the current visible UI remains a
compatibility presentation surface rather than a designed NSOM-aware
explanation surface.

Current UI contract:

- QML keeps the same pages, blocks and payload keys for Home, Planner, Best
  Object, Sky Compass and Detail/Object.
- No NSOM panels, labels or diagnostic fields are displayed.
- Existing display fields such as object `score` remain compatibility/base
  presentation fields where the current UI needs them.
- Those display fields are not guaranteed to explain the NSOM order. For
  example, Home may order candidates by `ObservableTargetValue` while the card
  still shows the legacy-compatible `CelestialObject.score` field.

A visible NSOM-aware UI needs a separate design/data-contract step before QML
changes. That step should decide which explanations to show, whether to replace
or hide legacy display scores, how to present confidence and provider sources,
and how to describe limiting factors such as Moon, AOD/OpenAQ freshness, seeing
or transparency without exposing internal model jargon.

## 1.16.0 Weather UI Semantics Follow-Up

`1.16.0` starts with a limited Weather page copy/semantics pass. It labels NASA
AOD as aerosol data, OpenAQ as local particulate data and exposes provider
freshness more clearly. This does not add NSOM ranking explanations, does not
change the Home/Planner/Best Object/Sky Compass payload contracts and does not
change scoring formulas or provider refresh behavior.

## 1.16.1 VIIRS Cache Follow-Up

`1.16.1` is a provider-cache hardening step outside NSOM ranking policy. NASA
Black Marble VIIRS cache entries are revalidated every 7 days while stale data
remains available on lookup failure. The Weather `Aggiorna` command schedules
cache-aware VIIRS and AOD checks; AOD keeps its 18-hour TTL. This changes
provider refresh timing only and does not change scoring formulas, ranking,
confidence weighting or QML payload contracts.

## 1.17.0 Upper Home Presentation Follow-Up

The first `1.17.0` step adds the read-only `homeObservingOverview` presentation
contract. It separates Session actionability, legacy weather index, NSOM
planetary/deep-sky category diagnostics and scoped Moon impact copy. This step
does not yet change QML and does not alter scoring, ranking or provider inputs.

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
| `Catalogue / raw object score` | `evaluated_backend_input` | Keep as backend Universe/read-model input for the current scope; do not treat it as a ranking hotfix or visible catalogue/Home score. |

## Follow-Up Policy

| Area | Status | Blocks backend closeout | Policy |
| --- | --- | --- | --- |
| `AOD/OpenAQ real observing feedback` | `monitor_before_tuning` | `False` | Do not tune weights until enough real observing outcomes are reviewed. |
| `Catalogue / Universe raw score semantics` | `current_policy_evaluated` | `False` | Existing separation is sufficient for current backend scope; defer a new `UniverseTargetProfile` until multi-catalogue provenance, intrinsic calibration or visible score explanations require it. |
| `Visible UI explanations` | `future_design_step` | `False` | `1.16.0` only clarifies Weather condition-data semantics. Keep full NSOM explanations, score semantics, confidence/source copy and QML payload contracts separate until designed explicitly. |

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `backend_status_has_no_blockers` | `True` |
| `all_current_default_on_surfaces_closed` | `True` |
| `aod_openaq_default_on` | `True` |
| `aod_openaq_rollback_documented` | `True` |
| `aod_openaq_confidence_score_neutral` | `True` |
| `catalogue_universe_raw_score_policy_evaluated` | `True` |
| `remaining_items_are_non_blocking` | `True` |
| `visible_ui_redesign_not_started` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
