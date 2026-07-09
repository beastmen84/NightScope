# Equipment NSOM Comparison Report

## Executive Summary

This developer-only report compares current EquipmentService setup ranking with NSOM ObserverCapability/Q_target projections. It does not change equipment recommendations, Planner, Home, Best Object, Sky Compass, Detail/Object, QML, logging, network behaviour or runtime file writes.
Roadmap label: Equipment/ObserverCapability NSOM comparison.
The matrix covers 5 deterministic scenarios and 34 candidate rows.

## Methodology

- Uses `EquipmentNsomComparisonService` with fixed in-memory fixtures only.
- Legacy formula is the real EquipmentService component sum.
- NSOM ObserverCapability is projected by the shared `observer_capability_adapter`.
- Q_target is target-class specific and affects PracticalTargetValue only.
- Sky quality and seeing are identified as ownership-mixing in legacy Equipment scoring.
- RecommendationConfidence remains metadata and never modifies score.

## Scenario Matrix

| Scenario | Target | Equipment | Sky | Seeing | Expected behaviour |
| --- | --- | --- | --- | --- | --- |
| E01_planet_mixed_equipment | planet | small_and_large_telescopes | dark_sky | good_seeing | Planet Q_target should reward resolution, magnification and tracking. |
| E02_open_cluster_wide_field | open_cluster | binocular_and_small_scope | dark_sky | average_seeing | Open clusters should value field of view and practical comfort. |
| E03_galaxy_high_light_pollution | galaxy | medium_telescope | high_light_pollution | good_seeing | Legacy Equipment scoring still reacts to sky quality inside setup score. |
| E04_planet_poor_seeing | planet | mak_zoom | dark_sky | poor_seeing | Seeing should be visible as legacy Equipment context, not confidence. |
| E05_confidence_metadata | galaxy | medium_telescope | dark_sky | good_seeing | Confidence changes report trust only and never changes Equipment or Q_target scores. |

## Candidate Ranking Comparison

| Scenario | Legacy Equipment Top | NSOM Q_target Top | NSOM Practical Top | Candidate Count |
| --- | --- | --- | --- | ---: |
| E01_planet_mixed_equipment | Planetary 10 mm | Planetary 10 mm | Planetary 10 mm | 16 |
| E02_open_cluster_wide_field | Nikon 10×50 | Wide 32 mm | Wide 32 mm | 5 |
| E03_galaxy_high_light_pollution | Planetary 10 mm | Wide 32 mm | Wide 32 mm | 4 |
| E04_planet_poor_seeing | Zoom 8-24 mm @ 24 mm | Zoom 8-24 mm @ 8 mm | Zoom 8-24 mm @ 8 mm | 5 |
| E05_confidence_metadata | Planetary 10 mm | Wide 32 mm | Wide 32 mm | 4 |

## Candidate Details

| Scenario | Candidate | Legacy Score | Q_target | Practical | Legacy Main Component | Legacy Ownership Mixing |
| --- | --- | ---: | ---: | ---: | --- | --- |
| E01_planet_mixed_equipment | Planetary 10 mm | 98.03 | 0.841 | 77.34 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E01_planet_mixed_equipment | Planetary 10 mm + 2x Barlow | 91.48 | 0.327 | 30.11 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E01_planet_mixed_equipment | Planetary 6 mm | 88.91 | 0.313 | 28.83 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E01_planet_mixed_equipment | Plossl 25 mm + 2x Barlow | 84.85 | 0.774 | 71.23 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E01_planet_mixed_equipment | Planetary 6 mm | 79.30 | 0.832 | 76.51 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E01_planet_mixed_equipment | Planetary 10 mm | 76.57 | 0.268 | 24.68 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E01_planet_mixed_equipment | Wide 32 mm + 2x Barlow | 73.93 | 0.735 | 67.57 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E01_planet_mixed_equipment | Plossl 25 mm + 2x Barlow | 69.84 | 0.243 | 22.38 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E02_open_cluster_wide_field | Nikon 10×50 | 94.75 | 0.582 | 51.19 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E02_open_cluster_wide_field | Plossl 25 mm | 84.96 | 0.613 | 53.91 | angular_scale=22.69 | target_traits, sky_quality, seeing, observer_configuration |
| E02_open_cluster_wide_field | Wide 32 mm | 75.82 | 0.657 | 57.78 | angular_scale=16.27 | target_traits, sky_quality, seeing, observer_configuration |
| E02_open_cluster_wide_field | Planetary 10 mm | 51.11 | 0.510 | 44.84 | magnification=12.19 | target_traits, sky_quality, seeing, observer_configuration |
| E02_open_cluster_wide_field | Planetary 6 mm | 34.19 | 0.418 | 36.78 | light_gathering=11.45 | target_traits, sky_quality, seeing, observer_configuration |
| E03_galaxy_high_light_pollution | Planetary 10 mm | 88.25 | 0.444 | 28.18 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E03_galaxy_high_light_pollution | Plossl 25 mm | 69.74 | 0.506 | 32.09 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E03_galaxy_high_light_pollution | Planetary 6 mm | 67.99 | 0.435 | 27.60 | angular_scale=23.97 | target_traits, sky_quality, seeing, observer_configuration |
| E03_galaxy_high_light_pollution | Wide 32 mm | 63.07 | 0.576 | 36.59 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E04_planet_poor_seeing | Zoom 8-24 mm @ 24 mm | 90.98 | 0.499 | 44.89 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E04_planet_poor_seeing | Zoom 8-24 mm @ 20 mm | 88.86 | 0.550 | 49.50 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E04_planet_poor_seeing | Zoom 8-24 mm @ 16 mm | 79.12 | 0.550 | 49.50 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E04_planet_poor_seeing | Zoom 8-24 mm @ 12 mm | 71.56 | 0.584 | 52.53 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E04_planet_poor_seeing | Zoom 8-24 mm @ 8 mm | 64.09 | 0.660 | 59.39 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E05_confidence_metadata | Planetary 10 mm | 92.73 | 0.444 | 37.29 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E05_confidence_metadata | Plossl 25 mm | 74.22 | 0.506 | 42.47 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |
| E05_confidence_metadata | Planetary 6 mm | 72.48 | 0.435 | 36.52 | angular_scale=23.97 | target_traits, sky_quality, seeing, observer_configuration |
| E05_confidence_metadata | Wide 32 mm | 67.55 | 0.576 | 48.42 | angular_scale=24.00 | target_traits, sky_quality, seeing, observer_configuration |

## Main Findings

- Legacy EquipmentService exposes a useful component sum, but mixes target traits, sky quality, seeing and setup handling in one score.
- NSOM Q_target is configuration-derived and target-class-specific; it stays outside ObservableTargetValue.
- ObserverCapability/Q_target projection is now shared adapter logic, not private report-only code.
- RecommendationConfidence is present only as metadata and has zero score effect.
- Equipment remains an active backend area; the shared adapter supports diagnostics/read models, not a runtime setup switch.

## Recommended Next Steps

1. Review the shared ObserverCapability/Q_target adapter extraction.
2. Review the 1.13.1 setup read-model boundary for output parity.
3. Audit EquipmentService setup-score ownership before any scoring replacement.
