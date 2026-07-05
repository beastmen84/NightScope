# Best Object NSOM Readiness Audit

## Executive Summary

This developer-only audit checked whether Best Object was ready for a default-off NSOM runtime path after the comparison report. The default-off path now exists, but the default runtime still preserves legacy Best Object selection. The path does not change recommendedDeepSky, Planner, Sky Compass, QML, logging, network behaviour or runtime file writes.

## Readiness Verdict

- Verdict: `ready_for_default_off_path`.
- Ready for default-off path: `True`.
- Runtime path exists: `True`.
- Default flag: `NSOM_BEST_OBJECT_ENABLED = False`.
- Runtime behaviour changed by default: `False`.
- Explicit NSOM opt-in: `AppController(use_nsom_best_object=True)`.
- Explicit legacy rollback: `AppController(use_nsom_best_object=False)`.
- Recommendation: `review_default_off_best_object_nsom_path_before_default_on_readiness`.
- Reason: Best Object non-actionable policy, displayed score semantics and runtime safety are implemented behind an internal default-off path. The next change should review behaviour before any default-on audit.

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
| `best_object_nsom_runtime_path_default_off` | `True` |
| `legacy_rollback_available` | `True` |
| `comparison_tooling_developer_only` | `True` |
| `comparison_tooling_has_no_runtime_writes` | `True` |
| `comparison_tooling_has_no_automatic_logging` | `True` |
| `comparison_tooling_has_no_network` | `True` |
| `comparison_tooling_has_no_qml_exposure` | `True` |
| `best_object_runtime_unchanged_by_default` | `True` |
| `recommended_deep_sky_runtime_unchanged` | `True` |
| `planner_runtime_unchanged` | `True` |
| `sky_compass_runtime_unchanged` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_report_imports_absent` | `True` |

## Recommended Next Steps

1. Review the default-off Best Object NSOM path before any default-on readiness audit.
2. Verify blocked-session, invisible-target and missing-sky-quality policy in the runtime selector.
3. Preserve legacy Best Object as explicit rollback until a separate default-on switch is reviewed.
