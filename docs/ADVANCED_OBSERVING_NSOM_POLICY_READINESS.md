# Advanced Observing NSOM Policy Readiness

## Executive Summary

This developer-only audit records the Advanced Observing NSOM policy decisions needed before a default-off runtime path can be added. It uses the existing comparison report as evidence and does not change `AdvancedObservingService`, Home, Best Object, Planner, Sky Compass, QML, logging, network behaviour or runtime file writes.

## Readiness Verdict

- Verdict: `ready_for_default_off_advanced_observing_nsom_path`.
- Ready for default-off path: `True`.
- Runtime behaviour changed by this review: `False`.
- Explicit legacy default: AdvancedObservingService.scores(...) remains unchanged.
- Recommended next change: Add NSOM_ADVANCED_OBSERVING_ENABLED = False and keep AdvancedObservingService legacy by default.
- Reason: Advanced Observing policy decisions are documented, remaining items are non-blocking, confidence remains metadata-only, and no runtime/QML wiring exists. A separate default-off NSOM path can now be implemented.

## Default-Off Blockers

- none

## Policy Decisions

| Policy | Status | NSOM layer | Blocks default-off | Decision |
| --- | --- | --- | --- | --- |
| `advanced_observing_role` | `accepted` | `presentation` | `False` | Advanced Observing is a presentation/category diagnostic surface, not an owner of independent target ranking. |
| `session_viability_policy` | `accepted` | `session` | `False` | SessionViability must stay separate from category sky values. Blocked sessions should be displayed as non-actionable session context, not hidden inside target or sky quality. |
| `planetary_seeing_policy` | `accepted_for_experimental_path` | `sky` | `False` | Seeing may feed a planetary atmospheric stability diagnostic, but it must remain separate from Moon and light-pollution background. |
| `planetary_moon_policy` | `accepted` | `sky` | `False` | Planetary and Moon diagnostics should be protected from Moon and light-pollution sky-background penalties. |
| `deep_sky_target_class_policy` | `accepted` | `sky` | `False` | Deep-sky diagnostics should preserve target-class sensitivity for galaxies, diffuse nebulae, open clusters and globular clusters even if the current UI keeps one broad deep-sky badge. |
| `weather_cap_policy` | `accepted_for_rollback_only` | `session` | `False` | Legacy weather caps remain only in the legacy rollback/default path until a default-off NSOM path is added. |
| `observer_capability_policy` | `deferred_non_blocking` | `observer` | `False` | Advanced Observing 1.8.x will not consume ObserverCapability until a later equipment-specific category advice pass. |
| `confidence_policy` | `accepted` | `confidence` | `False` | RecommendationConfidence remains metadata-only and never modifies advanced category scores or future NSOM category values. |

## Evidence From Comparison Report

- Source report: `docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md`.
- Scenario count: `8`.
- Category rows: `16`.
- Semantic recommendation: `presentation diagnostic / category quality surface`.
- Runtime score replacement ready in comparison report: `False`.
- Confidence score effect: `0.0`.

## Main Mismatches

- Legacy advanced scores mix weather/session directly into both category scores.
- Legacy deep-sky score has one broad scalar for galaxy, nebula and cluster classes.
- Legacy planetary score includes a Moon component even though NSOM protects planets from sky-background damage.
- Weather caps duplicate session viability and can hide whether the limiting factor is sky or actionability.
- Legacy advanced scores do not expose observer capability or confidence as separate concepts.

## Readiness Checks

| Check | Result |
| --- | --- |
| `comparison_report_developer_only` | `True` |
| `comparison_report_has_no_runtime_writes` | `True` |
| `legacy_formula_components_available` | `True` |
| `required_policy_decisions_recorded` | `True` |
| `policy_decisions_do_not_block_default_off` | `True` |
| `confidence_score_neutral` | `True` |
| `deep_sky_target_classes_preserved` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_scores_unchanged_by_review` | `True` |

## Runtime And QML Wiring

| Check | Result |
| --- | --- |
| QML matches | `[]` |
| Runtime report imports | `[]` |

## Non-Blocking Risks

- The current UI expects scalar planetary and deep-sky score labels.
- A future default-off path must preserve the legacy output shape until UI semantics are designed.
- Seeing ownership may need a later calibration review before any default-on switch.
- One broad deep-sky badge can hide target-class differences unless diagnostic data stays class-aware.
- ObserverCapability is intentionally deferred for Advanced Observing 1.8.x.

## Recommended Next Step

Implement `1.8.4` as a default-off Advanced Observing NSOM runtime path behind `NSOM_ADVANCED_OBSERVING_ENABLED = False`, preserving the existing legacy advanced score output by default.
