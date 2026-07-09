# Best Object NSOM Readiness Audit

## Executive Summary

This developer-only audit checked whether Best Object was ready for a default-off NSOM runtime path after the comparison report. The path exists and is now default-on; the temporary constructor rollback was removed in 1.13.8. The current default flag is reported below. The path does not change recommendedDeepSky, Planner, Sky Compass, QML, logging, network behaviour or runtime file writes.

## Readiness Verdict

- Verdict: `ready_for_default_off_path`.
- Ready for default-off path: `True`.
- Runtime path exists: `True`.
- Default flag: `NSOM_BEST_OBJECT_ENABLED = True`.
- Runtime behaviour changed by default: `True`.
- Explicit NSOM opt-in: `default AppController()`.
- Explicit legacy rollback: `removed: AppController(use_nsom_best_object=False)`.
- Recommendation: `default_on_path_validated_and_runtime_rollback_removed`.
- Reason: Best Object non-actionable policy, displayed score semantics and runtime safety were validated behind an internal Best Object NSOM path. The temporary constructor rollback was removed in 1.13.8.

## Default-Off Blockers

- none

## Policy Review

| Policy | Status | Blocks Default-Off Path | Decision |
| --- | --- | --- | --- |
| `best-object-blocked-session-non-actionable-policy` | `accepted` | `False` | Blocked sessions are non-actionable in a future NSOM Best Object path. Do not surface legacy, ObservableTargetValue or PracticalTargetValue order as an actionable recommendation. |
| `best-object-observation-opportunity-home-policy` | `accepted_direction` | `False` | Best Object should migrate toward ObservationOpportunity-style actionability with a Home-specific presentation policy. |
| `best-object-confidence-metadata-policy` | `accepted` | `False` | RecommendationConfidence remains metadata and must not modify score. |

## Blocked Session Evidence

- Scenario: `B03_blocked_session`.
- Blocking reason: rischio precipitazioni.
- Legacy Best Object order: `jupiter > open_cluster > galaxy > diffuse_nebula`.
- Diagnostic ObservableTargetValue order: `galaxy > jupiter > diffuse_nebula > open_cluster`.
- Diagnostic PracticalTargetValue order: `galaxy > diffuse_nebula > open_cluster > jupiter`.
- Actionability: `non_actionable`.
- Diagnostic orders are recommendation orders: `False`.

## Displayed Score Semantics

- Decision status: `accepted_for_default_off_experiment`.
- Keep legacy displayed score for compatibility: `True`.
- Score monotonic with proposed NSOM order: `False`.
- Blocks default-off path: `False`.
- Decision: For the first default-off experiment, preserve the existing Best Object payload and displayed legacy/base score. Do not expose provisional NSOM score rationale to QML.
- Future runtime policy: Displayed score is compatibility data, not the NSOM ordering rationale. A later UI/rationale step can add explicit NSOM explanation fields.

## Semantic Migration Target

- Recommended concept: `ObservationOpportunity with Home-specific presentation policy`.
- Use pure ObservableTargetValue: `False`.
- Use pure PracticalTargetValue: `False`.
- Use ObservationOpportunity with Home policy: `True`.
- Reason: Best Object is action-oriented. ObservableTargetValue omits equipment and session actionability; PracticalTargetValue omits session actionability; ObservationOpportunity can carry session policy, but Home needs compact presentation rules distinct from Planner chronology.

## Runtime Safety

| Check | Result |
| --- | --- |
| `best_object_nsom_runtime_path_available` | `True` |
| `current_default_flag_enabled` | `True` |
| `legacy_rollback_removed` | `True` |
| `comparison_tooling_developer_only` | `True` |
| `comparison_tooling_has_no_runtime_writes` | `True` |
| `comparison_tooling_has_no_automatic_logging` | `True` |
| `comparison_tooling_has_no_network` | `True` |
| `comparison_tooling_has_no_qml_exposure` | `True` |
| `best_object_runtime_unchanged_when_flag_off` | `True` |
| `recommended_deep_sky_runtime_unchanged` | `True` |
| `planner_runtime_unchanged` | `True` |
| `sky_compass_runtime_unchanged` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_report_imports_absent` | `True` |

## Recommended Next Steps

1. Keep the Best Object NSOM backend path default-on.
2. Keep blocked-session, invisible-target and missing-sky-quality policy documented.
3. Treat visible Best Object explanation UI as a separate design step.
