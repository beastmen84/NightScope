# NSOM Planner Default-On Readiness Audit

## Executive Summary

This developer-only audit checks whether the default-off experimental NSOM Planner path is ready for a separate default-on switch PR. It does not enable NSOM Planner, tune weights, change legacy Planner scoring, write runtime files, log automatically, perform network work or expose QML.

## Readiness Verdict

- Verdict: `ready_for_default_on_switch_pr`.
- Ready for default-on switch PR: `True`.
- Ready to enable in this commit: `False`.
- Recommendation: `ready_for_default_on_switch_pr`.
- Reason: No calibration or policy blockers remain; accepted/deferred decisions are documented; deferred items are non-blocking; the runtime flag is still default-off; developer-only report tooling remains unwired.

## Blocking Checks

| Check | Result |
| --- | --- |
| Default-on blockers | `none` |
| Needs calibration decisions | `none` |
| Needs policy decisions | `none` |
| Unlinked review or policy rows | `none` |

## Decision Coverage

| Item | Result |
| --- | --- |
| Accepted decisions documented | `True` |
| Deferred decisions documented | `True` |
| Deferred decisions non-blocking | `True` |
| Accepted decisions | `blocked-session-hard-block-policy`, `invisible-target-non-actionable-policy`, `small-equipment-planet-q-target`, `globular-large-telescope-promotion`, `deep-sky-favouring-planet-review-row`, `open-cluster-recurring-demotion`, `missing-window-policy` |
| Deferred decisions | `medium-equipment-q-target-review-band`, `moon-planet-favouring-category-factor` |

## Remaining Non-Blocking Review Items

- `medium-equipment-q-target-review-band` (ObserverCapability/PracticalTargetValue, all): Many review rows are driven by Q_target being below the current review threshold rather than by a directional rule failure. Keep them linked but do not turn them into broad tuning work.
- `moon-planet-favouring-category-factor` (Sky/ObservableTargetValue, moon): G14 Moon warning is caused by the generic protected-target threshold interacting with category/session factors, not by sky-background damage. Keep it visible for the Moon-specific pass.

## Runtime Safety

| Check | Result |
| --- | --- |
| `flag_default_off` | `True` |
| `legacy_planner_preserved_by_default_flag` | `True` |
| `qml_exposure_absent` | `True` |
| `runtime_report_imports_absent` | `True` |
| `tooling_developer_only` | `True` |
| `tooling_has_no_runtime_writes` | `True` |
| `tooling_has_no_automatic_logging` | `True` |
| `tooling_has_no_network` | `True` |
| `tooling_has_no_qml_exposure` | `True` |

## Developer-Only Tooling

| Tool | Developer Only | Runtime Writes | Automatic Logging | Network | QML Exposure |
| --- | --- | --- | --- | --- | --- |
| `comparison_report` | `True` | `False` | `False` | `False` | `False` |
| `mathematical_trace_report` | `True` | `False` | `False` | `False` | `False` |
| `calibration_decision_log` | `True` | `False` | `False` | `False` | `False` |

## Risks Before Actual Default-On Switch

- The actual default-on PR will intentionally change Planner ranking and needs its own acceptance review.
- Deferred review items should remain visible after enabling so they do not become hidden calibration debt.
- A rollback path should be kept for the first default-on change even though this audit does not add one.

## Source Reports

- `docs/NSOM_PLANNER_COMPARISON_REPORT.md`
- `docs/NSOM_MATHEMATICAL_TRACE_REPORT.md`
- `docs/NSOM_CALIBRATION_DECISION_LOG.md`

## Final Recommendation

Open a separate default-on switch PR only after this audit remains green and the switch PR includes its own runtime acceptance check. Do not enable the flag in this audit commit.
