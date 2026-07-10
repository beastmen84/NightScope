# NSOM AOD/OpenAQ Default-On Switch

## Executive Summary

This developer-only report records the 1.14.19 AOD/OpenAQ default-on switch. It changes only the default value of `ObservationConditionFeatureFlags.experimental_aerosol_scoring`, keeps the explicit rollback path, and does not add QML exposure, report runtime wiring, logging, network calls or runtime file writes.

## Review

- Reviewed step: `1.14.18`.
- Review verdict: `safe_to_switch_default_on`.
- Accepted policy: `keep_stale_aod_weight_0_5`.
- Reason: The stale/current replay accepted the score scale and protected target behaviour. The switch changes only the default feature flag; provider fetches, formulas, QML payloads and report wiring are unchanged.

## Switch

- Default flag: `ObservationConditionFeatureFlags.experimental_aerosol_scoring = True`.
- Rollback: `ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)`.
- Formula changed: `False`.
- Weights changed: `False`.
- Provider calls changed: `False`.
- Runtime effect: Only condition targets with policy-eligible AOD/OpenAQ inputs can receive a target-specific aerosol modifier.

## Example

- Target: `m31` / `galaxy`.
- Base score: `82`.
- Default adjusted score: `75`.
- Forced-off adjusted score: `82`.
- Default primary source: `aod`.
- Default score modifier: `-7.38`.
- Forced-off components: `[]`.

## Checks

| Check | Result |
| --- | --- |
| `strict_json_compatible` | `True` |
| `default_flag_enabled` | `True` |
| `default_path_uses_aod_openaq_when_policy_eligible` | `True` |
| `forced_off_rollback_is_neutral` | `True` |
| `confidence_metadata_does_not_scale_score` | `True` |
| `runtime_report_imports_absent` | `True` |
| `qml_report_exposure_absent` | `True` |
