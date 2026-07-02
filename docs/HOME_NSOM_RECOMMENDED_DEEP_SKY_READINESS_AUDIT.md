# Home NSOM RecommendedDeepSky Readiness Audit

## Executive Summary

Readiness verdict: ready for a separate default-on switch PR.

`NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED` remains `False` in this audit. The default runtime path still uses the legacy Home `recommendedDeepSky` order. The experimental path ranks Home deep-sky candidates by NSOM `ObservableTargetValue` only.

This audit does not change Home ranking logic, Best Object, Sky Compass, QML, logging, network behaviour, runtime file writes or report runtime wiring.

## Scope

- Audit the default-off NSOM Home `recommendedDeepSky` path.
- Strengthen deterministic high-light-pollution ordering coverage.
- Verify full controller `recommendedDeepSky` payload compatibility.
- Document displayed score semantics before any default-on switch.

Out of scope:

- Enabling `NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED`.
- Adding UI-visible NSOM explanation fields.
- Using `PracticalTargetValue`, `ObserverCapability`, `SessionViability`, `RecommendationConfidence` or `ObservationOpportunity` for Home ranking.
- Changing Best Object or Sky Compass.

## Current Flag State

- Flag: `NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED`
- Current value: `False`
- Rollback path: keep the flag false, or force the controller constructor parameter `use_nsom_home_recommended_deep_sky=False`.
- Default-on switch condition: change only the flag after the tests in this audit remain green.

## Ordering Evidence

The high-light-pollution scenario now has an exact regression expectation:

`globular_cluster > open_cluster > diffuse_nebula > galaxy`

This matches `docs/HOME_NSOM_COMPARISON_REPORT.md`, where the high-light-pollution comparison showed legacy Home keeping galaxy first while NSOM ObservableTargetValue promotes cluster targets under strong static sky background.

## Displayed Score Semantics Decision

Decision: keep the legacy/base displayed score for compatibility during the first default-on switch.

Reason:

- QML payload shape must remain unchanged.
- No NSOM fields should be exposed in this step.
- Home cards already expect the current `score` and `scoreLabel` fields.
- `ObservableTargetValue` should drive ordering only while the UI design for NSOM rationale remains undecided.

Known non-blocking risk:

- With flag-on, card order can be NSOM Observable order while displayed `score` remains the legacy/base score. In high light pollution, this means `globular_cluster` and `open_cluster` can appear above `galaxy` even though the visible score field may not be monotonic.

Accepted handling for default-on switch:

- Do not expose score rationale yet.
- Do not add provisional UI text.
- Document the risk and keep rollback explicit.
- Add NSOM explanation fields only in a later UI/design step.

## Payload Compatibility

Integration-style tests now call the controller `recommendedDeepSky` property directly.

Verified:

- Payload keys are unchanged.
- No `nsom`, `observableTargetValue` or `practicalTargetValue` fields are present.
- Displayed `score` and `scoreLabel` remain compatible.
- Original `CelestialObject` instances are not mutated.
- Flag-off payload/order matches the legacy path.
- Flag-on changes ordering only.

## Ownership Boundaries

The Home NSOM ranking path uses:

- `IntrinsicTargetQuality`
- `ObservationEnvironment`
- `EffectiveObservability`
- `ObservableTargetValue`

It does not use:

- `PracticalTargetValue`
- `ObserverCapability`
- `SessionViability`
- `RecommendationConfidence`
- `ObservationOpportunity`

Confidence remains metadata-only and is not part of Home ranking.

## Runtime Safety

- No QML/UI changes.
- No Best Object changes.
- No Sky Compass changes.
- No runtime logging.
- No network calls.
- No runtime file writes.
- No report runtime wiring.

## Blockers

No blockers for a separate default-on switch PR.

## Non-Blocking Risks

1. Displayed score is legacy/base while order is NSOM Observable.
2. No user-facing rationale is available for the new order.
3. High-light-pollution ordering intentionally differs from legacy Home order and should be called out in release notes or internal migration notes.

## Recommended Default-On Switch Conditions

1. Change only `NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED` to `True`.
2. Keep the constructor rollback parameter available.
3. Run focused Home NSOM tests and relevant Home/Sky Compass tests.
4. Do not add QML-visible NSOM fields in the same switch.
5. Defer score/rationale display design to a separate Home UI step.
