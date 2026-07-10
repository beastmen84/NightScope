# NSOM AOD/OpenAQ Real Provider Probe

## Executive Summary

This developer-only probe uses real NASA Earthdata AOD and OpenAQ responses for a small mixed-location set. It compares the default aerosol flag-off behaviour with the explicit experimental flag-on score effect. It is not wired into runtime, QML or automatic tests.

## Safety

- Runtime behaviour changed: `False`.
- QML exposure: `False`.
- Network: `True`.
- Automatic logging: `False`.
- Persistent writes: `False`.
- Credential values stored in report: `False`.

## Verdict

- Verdict: `real_provider_probe_ready_for_human_review`.
- Ready for default-on: `False`.
- Recommended next step: Review real-provider results, then decide whether AOD/OpenAQ can move to a narrow default-on switch or needs more field observations.

## Provider Results By Location

| Location | NASA AOD | AOD input | OpenAQ | PM input | Policy source |
| --- | --- | --- | --- | --- | --- |
| Bologna, Italy | `ok` AOD 0.124 | `True` `stale` | `historical`  | `False` `none` | `none` |
| San Pedro de Atacama, Chile | `ok` AOD 0.062 | `True` `stale` | `unavailable`  | `False` `none` | `aod` |
| New Delhi, India | `no_valid_pixel`  | `False` `none` | `ok` PM2.5 35 µg/m³, PM10 92 µg/m³ | `True` `current` | `particulate` |
| Mauna Kea, USA | `ok` AOD 0.061 | `True` `stale` | `unavailable`  | `False` `none` | `aod` |
| Addis Ababa, Ethiopia | `ok` AOD 0.422 | `True` `stale` | `historical`  | `False` `none` | `aod` |

## Flag Off/On Aerosol Effects

| Location | Target | Source | Flag off | Flag on modifier | Flag on score | Transparency loss |
| --- | --- | --- | --- | --- | --- | --- |
| Bologna, Italy | `galaxy` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Bologna, Italy | `diffuse_nebula` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Bologna, Italy | `open_cluster` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Bologna, Italy | `globular_cluster` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Bologna, Italy | `planet` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Bologna, Italy | `moon` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| San Pedro de Atacama, Chile | `galaxy` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| San Pedro de Atacama, Chile | `diffuse_nebula` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| San Pedro de Atacama, Chile | `open_cluster` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| San Pedro de Atacama, Chile | `globular_cluster` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| San Pedro de Atacama, Chile | `planet` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| San Pedro de Atacama, Chile | `moon` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| New Delhi, India | `galaxy` | `particulate` | `0.0` | `-2.952` | `79` | `0.036` |
| New Delhi, India | `diffuse_nebula` | `particulate` | `0.0` | `-1.673` | `80` | `0.0204` |
| New Delhi, India | `open_cluster` | `particulate` | `0.0` | `-0.369` | `82` | `0.0045` |
| New Delhi, India | `globular_cluster` | `particulate` | `0.0` | `-0.443` | `82` | `0.0054` |
| New Delhi, India | `planet` | `particulate` | `0.0` | `-0.111` | `82` | `0.00135` |
| New Delhi, India | `moon` | `particulate` | `0.0` | `-0.012` | `82` | `0.00015` |
| Mauna Kea, USA | `galaxy` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Mauna Kea, USA | `diffuse_nebula` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Mauna Kea, USA | `open_cluster` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Mauna Kea, USA | `globular_cluster` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Mauna Kea, USA | `planet` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Mauna Kea, USA | `moon` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Addis Ababa, Ethiopia | `galaxy` | `aod` | `0.0` | `-3.69` | `78` | `0.045` |
| Addis Ababa, Ethiopia | `diffuse_nebula` | `aod` | `0.0` | `-2.091` | `80` | `0.0255` |
| Addis Ababa, Ethiopia | `open_cluster` | `aod` | `0.0` | `-0.461` | `82` | `0.00562` |
| Addis Ababa, Ethiopia | `globular_cluster` | `aod` | `0.0` | `-0.553` | `81` | `0.00675` |
| Addis Ababa, Ethiopia | `planet` | `aod` | `0.0` | `-0.139` | `82` | `0.00169` |
| Addis Ababa, Ethiopia | `moon` | `aod` | `0.0` | `-0.016` | `82` | `0.00019` |

## Aggregate Checks

| Check | Result |
| --- | --- |
| `location_count_is_4_or_5` | `True` |
| `strict_json_compatible` | `True` |
| `flag_off_always_neutral` | `True` |
| `has_real_provider_success` | `True` |
| `has_policy_eligible_source` | `True` |
| `policy_sources_observed` | `['aod', 'none', 'particulate']` |
| `deep_sky_max_penalty` | `-3.69` |
| `solar_system_max_penalty` | `-0.139` |
| `deep_sky_penalty_at_least_solar_system` | `True` |
| `confidence_score_neutral_notes_present` | `True` |

## Notes For Review

- A location can have provider data but still no score effect if freshness or provider-quality policy rejects the input.
- NASA AOD remains primary when policy-eligible. OpenAQ PM remains fallback/context only and is not additive with AOD.
- The default runtime stays score-neutral because `ObservationConditionFeatureFlags.experimental_aerosol_scoring` is still `False`.
