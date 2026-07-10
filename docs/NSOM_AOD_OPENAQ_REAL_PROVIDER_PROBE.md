# NSOM AOD/OpenAQ Real Provider Probe

## Executive Summary

This developer-only probe uses real NASA Earthdata AOD and OpenAQ responses for a mixed-location set. It compares the default aerosol flag-off behaviour with the explicit experimental flag-on score effect. It is not wired into runtime, QML or automatic tests.

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
- Location set: `expanded`.
- Location count: `15`.

## Provider Results By Location

| Location | NASA AOD | AOD input | OpenAQ | PM input | Policy source |
| --- | --- | --- | --- | --- | --- |
| Bologna, Italy | `ok` AOD 0.124 | `True` `stale` | `historical`  | `False` `none` | `none` |
| San Pedro de Atacama, Chile | `ok` AOD 0.062 | `True` `stale` | `unavailable`  | `False` `none` | `aod` |
| New Delhi, India | `no_valid_pixel`  | `False` `none` | `ok` PM2.5 35 µg/m³, PM10 92 µg/m³ | `True` `current` | `particulate` |
| Mauna Kea, USA | `ok` AOD 0.061 | `True` `stale` | `unavailable`  | `False` `none` | `aod` |
| Addis Ababa, Ethiopia | `ok` AOD 0.422 | `True` `stale` | `historical`  | `False` `none` | `aod` |
| Cairo, Egypt | `ok` AOD 0.083 | `True` `stale` | `historical`  | `False` `none` | `aod` |
| Marrakech, Morocco | `ok` AOD 0.118 | `True` `stale` | `ok` PM2.5 24.6 µg/m³ | `True` `current` | `aod` |
| Mexico City, Mexico | `no_valid_pixel`  | `False` `none` | `historical`  | `False` `none` | `none` |
| Los Angeles, USA | `ok` AOD 0.064 | `True` `stale` | `ok` PM2.5 17.9 µg/m³, PM10 36 µg/m³ | `True` `current` | `aod` |
| Beijing, China | `ok` AOD 0.758 | `True` `stale` | `ok` PM2.5 13.5 µg/m³ | `True` `current` | `particulate` |
| Tokyo, Japan | `download_error`  | `False` `none` | `ok` PM2.5 6 µg/m³ | `True` `current` | `particulate` |
| Singapore, Singapore | `ok` AOD 0.365 | `True` `stale` | `unavailable`  | `False` `none` | `aod` |
| Sydney, Australia | `ok` AOD 0.530 | `True` `stale` | `ok` PM2.5 6 µg/m³ | `True` `current` | `particulate` |
| Cape Town, South Africa | `ok` AOD 0.072 | `True` `stale` | `historical`  | `False` `none` | `aod` |
| Reykjavik, Iceland | `ok` AOD 0.381 | `True` `stale` | `ok` PM2.5 2.1 µg/m³, PM10 5.3 µg/m³ | `True` `current` | `particulate` |

## Policy Reasons By Location

| Location | Policy source | AOD eligible | AOD reasons | PM eligible | PM reasons |
| --- | --- | --- | --- | --- | --- |
| Bologna, Italy | `none` | `False` | `aod_local_neighborhood_too_sparse` | `False` | `particulate_missing` |
| San Pedro de Atacama, Chile | `aod` | `True` | `none` | `False` | `particulate_missing` |
| New Delhi, India | `particulate` | `False` | `aod_missing` | `True` | `none` |
| Mauna Kea, USA | `aod` | `True` | `none` | `False` | `particulate_missing` |
| Addis Ababa, Ethiopia | `aod` | `True` | `none` | `False` | `particulate_missing` |
| Cairo, Egypt | `aod` | `True` | `none` | `False` | `particulate_missing` |
| Marrakech, Morocco | `aod` | `True` | `none` | `True` | `none` |
| Mexico City, Mexico | `none` | `False` | `aod_missing` | `False` | `particulate_missing` |
| Los Angeles, USA | `aod` | `True` | `none` | `True` | `none` |
| Beijing, China | `particulate` | `False` | `aod_local_neighborhood_too_sparse` | `True` | `none` |
| Tokyo, Japan | `particulate` | `False` | `aod_missing` | `True` | `none` |
| Singapore, Singapore | `aod` | `True` | `none` | `False` | `particulate_missing` |
| Sydney, Australia | `particulate` | `False` | `aod_uncertainty_missing_or_high`, `aod_local_neighborhood_too_sparse` | `True` | `none` |
| Cape Town, South Africa | `aod` | `True` | `none` | `False` | `particulate_missing` |
| Reykjavik, Iceland | `particulate` | `False` | `aod_uncertainty_missing_or_high`, `aod_local_neighborhood_too_sparse` | `True` | `none` |

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
| Cairo, Egypt | `galaxy` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Cairo, Egypt | `diffuse_nebula` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Cairo, Egypt | `open_cluster` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Cairo, Egypt | `globular_cluster` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Cairo, Egypt | `planet` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Cairo, Egypt | `moon` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Marrakech, Morocco | `galaxy` | `aod` | `0.0` | `-2.46` | `80` | `0.03` |
| Marrakech, Morocco | `diffuse_nebula` | `aod` | `0.0` | `-1.394` | `81` | `0.017` |
| Marrakech, Morocco | `open_cluster` | `aod` | `0.0` | `-0.307` | `82` | `0.00375` |
| Marrakech, Morocco | `globular_cluster` | `aod` | `0.0` | `-0.369` | `82` | `0.0045` |
| Marrakech, Morocco | `planet` | `aod` | `0.0` | `-0.092` | `82` | `0.00112` |
| Marrakech, Morocco | `moon` | `aod` | `0.0` | `-0.011` | `82` | `0.00013` |
| Mexico City, Mexico | `galaxy` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Mexico City, Mexico | `diffuse_nebula` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Mexico City, Mexico | `open_cluster` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Mexico City, Mexico | `globular_cluster` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Mexico City, Mexico | `planet` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Mexico City, Mexico | `moon` | `none` | `0.0` | `0.0` | `82` | `0.0` |
| Los Angeles, USA | `galaxy` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Los Angeles, USA | `diffuse_nebula` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Los Angeles, USA | `open_cluster` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Los Angeles, USA | `globular_cluster` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Los Angeles, USA | `planet` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Los Angeles, USA | `moon` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Beijing, China | `galaxy` | `particulate` | `0.0` | `-1.476` | `81` | `0.018` |
| Beijing, China | `diffuse_nebula` | `particulate` | `0.0` | `-0.836` | `81` | `0.0102` |
| Beijing, China | `open_cluster` | `particulate` | `0.0` | `-0.184` | `82` | `0.00225` |
| Beijing, China | `globular_cluster` | `particulate` | `0.0` | `-0.221` | `82` | `0.0027` |
| Beijing, China | `planet` | `particulate` | `0.0` | `-0.055` | `82` | `0.00067` |
| Beijing, China | `moon` | `particulate` | `0.0` | `-0.006` | `82` | `7e-05` |
| Tokyo, Japan | `galaxy` | `particulate` | `0.0` | `-1.476` | `81` | `0.018` |
| Tokyo, Japan | `diffuse_nebula` | `particulate` | `0.0` | `-0.836` | `81` | `0.0102` |
| Tokyo, Japan | `open_cluster` | `particulate` | `0.0` | `-0.184` | `82` | `0.00225` |
| Tokyo, Japan | `globular_cluster` | `particulate` | `0.0` | `-0.221` | `82` | `0.0027` |
| Tokyo, Japan | `planet` | `particulate` | `0.0` | `-0.055` | `82` | `0.00067` |
| Tokyo, Japan | `moon` | `particulate` | `0.0` | `-0.006` | `82` | `7e-05` |
| Singapore, Singapore | `galaxy` | `aod` | `0.0` | `-3.69` | `78` | `0.045` |
| Singapore, Singapore | `diffuse_nebula` | `aod` | `0.0` | `-2.091` | `80` | `0.0255` |
| Singapore, Singapore | `open_cluster` | `aod` | `0.0` | `-0.461` | `82` | `0.00562` |
| Singapore, Singapore | `globular_cluster` | `aod` | `0.0` | `-0.553` | `81` | `0.00675` |
| Singapore, Singapore | `planet` | `aod` | `0.0` | `-0.139` | `82` | `0.00169` |
| Singapore, Singapore | `moon` | `aod` | `0.0` | `-0.016` | `82` | `0.00019` |
| Sydney, Australia | `galaxy` | `particulate` | `0.0` | `-1.476` | `81` | `0.018` |
| Sydney, Australia | `diffuse_nebula` | `particulate` | `0.0` | `-0.836` | `81` | `0.0102` |
| Sydney, Australia | `open_cluster` | `particulate` | `0.0` | `-0.184` | `82` | `0.00225` |
| Sydney, Australia | `globular_cluster` | `particulate` | `0.0` | `-0.221` | `82` | `0.0027` |
| Sydney, Australia | `planet` | `particulate` | `0.0` | `-0.055` | `82` | `0.00067` |
| Sydney, Australia | `moon` | `particulate` | `0.0` | `-0.006` | `82` | `7e-05` |
| Cape Town, South Africa | `galaxy` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Cape Town, South Africa | `diffuse_nebula` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Cape Town, South Africa | `open_cluster` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Cape Town, South Africa | `globular_cluster` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Cape Town, South Africa | `planet` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Cape Town, South Africa | `moon` | `aod` | `0.0` | `0.0` | `82` | `0.0` |
| Reykjavik, Iceland | `galaxy` | `particulate` | `0.0` | `0.0` | `82` | `0.0` |
| Reykjavik, Iceland | `diffuse_nebula` | `particulate` | `0.0` | `0.0` | `82` | `0.0` |
| Reykjavik, Iceland | `open_cluster` | `particulate` | `0.0` | `0.0` | `82` | `0.0` |
| Reykjavik, Iceland | `globular_cluster` | `particulate` | `0.0` | `0.0` | `82` | `0.0` |
| Reykjavik, Iceland | `planet` | `particulate` | `0.0` | `0.0` | `82` | `0.0` |
| Reykjavik, Iceland | `moon` | `particulate` | `0.0` | `0.0` | `82` | `0.0` |

## Aggregate Checks

| Check | Result |
| --- | --- |
| `location_count_is_5_to_15` | `True` |
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
