# NSOM Calibration Decision Log

## Executive Summary

This developer-only decision log records how current NSOM Planner calibration review rows are accepted, deferred, escalated to targeted calibration, or held for policy decisions. It does not tune weights, enable NSOM Planner, or change runtime Planner behaviour.

## Decision Status Counts

| Status | Count |
| --- | ---: |
| `accepted` | 1 |
| `deferred` | 2 |
| `needs_calibration` | 2 |
| `needs_policy_decision` | 3 |

## Default-On Blockers

- `blocked-session-hard-block-policy`
- `invisible-target-non-actionable-policy`
- `small-equipment-planet-q-target`
- `open-cluster-recurring-demotion`
- `missing-window-policy`

## Decision Entries

| Decision | Status | Layer | Target | Blocks Default-On | Reason |
| --- | --- | --- | --- | --- | --- |
| `blocked-session-hard-block-policy` | `needs_policy_decision` | SessionViability/ObservationOpportunity | all | yes | G09 all-zero scores are correct for the current hard block, but stable ordering is not a meaningful recommendation order. |
| `invisible-target-non-actionable-policy` | `needs_policy_decision` | ObservationEnvironment/ObservationOpportunity | all | yes | G20 invisible targets correctly reach zero opportunity, but the diagnostic stable order needs the same non-actionable policy as blocked sessions. |
| `small-equipment-planet-q-target` | `needs_calibration` | ObserverCapability/PracticalTargetValue | planet | yes | G10/G11 planets fall five ranks with binocular/small telescope inputs. Planet observer projection needs a targeted floor or resolution/magnification review before default-on. |
| `globular-large-telescope-promotion` | `accepted` | ObserverCapability/PracticalTargetValue | globular_cluster | no | Large-telescope deep-sky conditions intentionally favour globular clusters through light grasp and resolution in Q_target. |
| `open-cluster-recurring-demotion` | `needs_calibration` | Universe/ObserverCapability/PracticalTargetValue | open_cluster | yes | Open clusters recur as large positive rank deltas across baseline, session, geometry and large-telescope groups. Review intrinsic cluster value and Q_target field-of-view/comfort weighting together. |
| `medium-equipment-q-target-review-band` | `deferred` | ObserverCapability/PracticalTargetValue | all | no | Many review rows are driven by Q_target being below the current review threshold rather than by a directional rule failure. Keep them linked but do not turn them into broad tuning work. |
| `missing-window-policy` | `needs_policy_decision` | ObservationOpportunity | all | yes | G19 visible targets with missing observing time use the current 0.5 timing fallback. Decide whether this fallback is acceptable before default-on ranking. |
| `moon-planet-favouring-category-factor` | `deferred` | Sky/ObservableTargetValue | moon | no | G14 Moon warning is caused by the generic protected-target threshold interacting with category/session factors, not by sky-background damage. Keep it visible for the Moon-specific pass. |

## Warning And Review Row Links

| Scenario | Decisions |
| --- | --- |
| `G01:planet` | `medium-equipment-q-target-review-band` |
| `G01:moon` | `medium-equipment-q-target-review-band` |
| `G01:galaxy` | `medium-equipment-q-target-review-band` |
| `G01:globular_cluster` | `medium-equipment-q-target-review-band` |
| `G01:diffuse_nebula` | `medium-equipment-q-target-review-band` |
| `G01:open_cluster` | `open-cluster-recurring-demotion`, `medium-equipment-q-target-review-band` |
| `G02:planet` | `medium-equipment-q-target-review-band` |
| `G02:moon` | `medium-equipment-q-target-review-band` |
| `G02:open_cluster` | `medium-equipment-q-target-review-band` |
| `G02:globular_cluster` | `medium-equipment-q-target-review-band` |
| `G02:diffuse_nebula` | `medium-equipment-q-target-review-band` |
| `G02:galaxy` | `medium-equipment-q-target-review-band` |
| `G03:planet` | `medium-equipment-q-target-review-band` |
| `G03:moon` | `medium-equipment-q-target-review-band` |
| `G03:open_cluster` | `medium-equipment-q-target-review-band` |
| `G03:globular_cluster` | `medium-equipment-q-target-review-band` |
| `G03:diffuse_nebula` | `medium-equipment-q-target-review-band` |
| `G03:galaxy` | `medium-equipment-q-target-review-band` |
| `G04:planet` | `medium-equipment-q-target-review-band` |
| `G04:moon` | `medium-equipment-q-target-review-band` |
| `G04:galaxy` | `medium-equipment-q-target-review-band` |
| `G04:globular_cluster` | `medium-equipment-q-target-review-band` |
| `G04:open_cluster` | `open-cluster-recurring-demotion`, `medium-equipment-q-target-review-band` |
| `G04:diffuse_nebula` | `medium-equipment-q-target-review-band` |
| `G06:planet` | `medium-equipment-q-target-review-band` |
| `G06:moon` | `medium-equipment-q-target-review-band` |
| `G06:open_cluster` | `medium-equipment-q-target-review-band` |
| `G06:globular_cluster` | `medium-equipment-q-target-review-band` |
| `G06:diffuse_nebula` | `medium-equipment-q-target-review-band` |
| `G06:galaxy` | `medium-equipment-q-target-review-band` |
| `G07:open_cluster` | `open-cluster-recurring-demotion` |
| `G08:open_cluster` | `open-cluster-recurring-demotion` |
| `G09:planet` | `blocked-session-hard-block-policy` |
| `G09:moon` | `blocked-session-hard-block-policy` |
| `G09:galaxy` | `blocked-session-hard-block-policy` |
| `G09:diffuse_nebula` | `blocked-session-hard-block-policy` |
| `G09:open_cluster` | `blocked-session-hard-block-policy` |
| `G09:globular_cluster` | `blocked-session-hard-block-policy` |
| `G10:open_cluster` | `medium-equipment-q-target-review-band` |
| `G10:diffuse_nebula` | `medium-equipment-q-target-review-band` |
| `G10:galaxy` | `medium-equipment-q-target-review-band` |
| `G10:moon` | `medium-equipment-q-target-review-band` |
| `G10:globular_cluster` | `medium-equipment-q-target-review-band` |
| `G10:planet` | `small-equipment-planet-q-target`, `medium-equipment-q-target-review-band` |
| `G11:open_cluster` | `medium-equipment-q-target-review-band` |
| `G11:diffuse_nebula` | `medium-equipment-q-target-review-band` |
| `G11:galaxy` | `medium-equipment-q-target-review-band` |
| `G11:moon` | `medium-equipment-q-target-review-band` |
| `G11:globular_cluster` | `medium-equipment-q-target-review-band` |
| `G11:planet` | `small-equipment-planet-q-target`, `medium-equipment-q-target-review-band` |
| `G12:globular_cluster` | `globular-large-telescope-promotion` |
| `G12:open_cluster` | `open-cluster-recurring-demotion` |
| `G14:planet` | `medium-equipment-q-target-review-band` |
| `G14:moon` | `medium-equipment-q-target-review-band`, `moon-planet-favouring-category-factor` |
| `G14:open_cluster` | `medium-equipment-q-target-review-band` |
| `G14:globular_cluster` | `medium-equipment-q-target-review-band` |
| `G14:diffuse_nebula` | `medium-equipment-q-target-review-band` |
| `G15:globular_cluster` | `globular-large-telescope-promotion` |
| `G15:open_cluster` | `open-cluster-recurring-demotion` |
| `G16:open_cluster` | `open-cluster-recurring-demotion` |
| `G17:planet` | `medium-equipment-q-target-review-band` |
| `G17:moon` | `medium-equipment-q-target-review-band` |
| `G17:galaxy` | `medium-equipment-q-target-review-band` |
| `G17:globular_cluster` | `medium-equipment-q-target-review-band` |
| `G17:diffuse_nebula` | `medium-equipment-q-target-review-band` |
| `G17:open_cluster` | `open-cluster-recurring-demotion`, `medium-equipment-q-target-review-band` |
| `G18:planet` | `medium-equipment-q-target-review-band` |
| `G18:moon` | `medium-equipment-q-target-review-band` |
| `G18:galaxy` | `medium-equipment-q-target-review-band` |
| `G18:globular_cluster` | `medium-equipment-q-target-review-band` |
| `G18:diffuse_nebula` | `medium-equipment-q-target-review-band` |
| `G18:open_cluster` | `open-cluster-recurring-demotion`, `medium-equipment-q-target-review-band` |
| `G19:planet` | `missing-window-policy` |
| `G19:moon` | `missing-window-policy` |
| `G19:galaxy` | `missing-window-policy` |
| `G19:globular_cluster` | `missing-window-policy` |
| `G19:diffuse_nebula` | `missing-window-policy` |
| `G19:open_cluster` | `open-cluster-recurring-demotion`, `missing-window-policy` |
| `G20:planet` | `invisible-target-non-actionable-policy` |
| `G20:moon` | `invisible-target-non-actionable-policy` |
| `G20:galaxy` | `invisible-target-non-actionable-policy` |
| `G20:diffuse_nebula` | `invisible-target-non-actionable-policy` |
| `G20:open_cluster` | `invisible-target-non-actionable-policy` |
| `G20:globular_cluster` | `invisible-target-non-actionable-policy` |

## Blocked-Session Policy Placeholder

`blocked-session-hard-block-policy` keeps the current hard-block runtime interpretation for now. Before NSOM Planner can be made default-on, a human decision must choose whether all-zero blocked groups stay hard ties or whether a non-actionable `PracticalTargetValue` ordering should be shown in diagnostics only.

## Confidence Control

Low confidence score `40.0246` and high confidence score `40.0246` produce score delta `0.0000`.

## Recommended Next Step

Resolve policy decisions before default-on work, then target only the entries marked `needs_calibration` with isolated formula changes.
