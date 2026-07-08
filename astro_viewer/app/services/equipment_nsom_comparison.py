from __future__ import annotations

import math
from collections.abc import Iterable

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    IntrinsicTargetQuality,
    ObservableTargetValue,
    ObserverCapability,
    ObservationEnvironment,
    PracticalTargetValue,
    RecommendationConfidence,
    nsom_to_json_compatible,
    observer_capability_weight_profile_for_target,
    project_observer_capability_for_target,
)
from astro_viewer.app.models.observation_configuration import ObservationConfiguration
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.recommendation_candidate import RecommendationCandidate
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.target_observation_traits import TargetObservationTraits
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.home_nsom_observable import build_home_observation_environment
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_intrinsic_target_quality,
    build_recommendation_confidence,
)


class EquipmentNsomComparisonService:
    """Developer-only comparison between EquipmentService scoring and NSOM ObserverCapability.

    The helper evaluates only caller-supplied objects/equipment and returns a
    JSON-compatible diagnostic dictionary. It does not change equipment
    recommendations, mutate runtime objects, write files, log, fetch data or
    expose QML fields.
    """

    def __init__(self, *, equipment_service: EquipmentService | None = None) -> None:
        self._equipment_service = equipment_service or EquipmentService()

    def compare(
        self,
        target: CelestialObject,
        *,
        sky_quality: SkyQuality,
        telescopes: Iterable[Telescope] = (),
        eyepieces: Iterable[Eyepiece] = (),
        barlows: Iterable[Barlow] = (),
        binoculars: Iterable[Binocular] = (),
        seeing: SeeingTransparency | None = None,
        moon: MoonSummary | None = None,
        confidence: RecommendationConfidence | None = None,
    ) -> dict[str, object]:
        telescope_items = tuple(telescopes)
        eyepiece_items = tuple(eyepieces)
        barlow_items = tuple(barlows)
        binocular_items = tuple(binoculars)
        candidates = tuple(
            self._equipment_service._ranked_profile_candidates(
                target,
                list(telescope_items),
                list(eyepiece_items),
                list(barlow_items),
                list(binocular_items),
                seeing,
                sky_quality,
            )
        )
        recommended = self._equipment_service._recommended_candidate(list(candidates)) if candidates else None
        intrinsic = build_intrinsic_target_quality(target)
        environment = build_home_observation_environment(target, intrinsic, sky_quality=sky_quality, moon=moon)
        effective = EffectiveObservability.from_environment(environment)
        observable = ObservableTargetValue.from_intrinsic(
            intrinsic_target_quality=intrinsic,
            effective_observability=effective,
            target_class=intrinsic.target_class,
        )
        recommendation_confidence = confidence or build_recommendation_confidence(
            weather_summary=None,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon is not None,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:equipment_comparison",),
        )
        rows = tuple(
            self._candidate_row(
                candidate,
                target=target,
                intrinsic=intrinsic,
                environment=environment,
                effective=effective,
                observable=observable,
                sky_quality=sky_quality,
                seeing=seeing,
                confidence=recommendation_confidence,
            )
            for candidate in candidates
        )

        return nsom_to_json_compatible(
            {
                "target": _target_projection(target, intrinsic),
                "legacy_formula": {
                    "name": "EquipmentService",
                    "formula": (
                        "angular_scale + magnification + exit_pupil + "
                        "light_gathering + seeing_compatibility + handling"
                    ),
                    "component_weights": {
                        "angular_scale": 24.0,
                        "magnification": 24.0,
                        "exit_pupil": 16.0,
                        "light_gathering": 16.0,
                        "seeing_compatibility": 10.0,
                        "handling": 10.0,
                    },
                    "recommended_candidate_id": (
                        recommended.configuration.configuration_id if recommended else None
                    ),
                    "recommended_label": recommended.detail_label if recommended else None,
                    "ownership_note": (
                        "Legacy EquipmentService scores target scale, sky-quality "
                        "context, seeing and practical setup handling inside one "
                        "configuration score."
                    ),
                },
                "rankings": {
                    "legacy_equipment_score": _ranking_projection(
                        rows,
                        _rank_by_score(
                            (row["candidate_id"], row["legacy"]["score"])
                            for row in rows
                        ),
                        "legacy",
                        "score",
                    ),
                    "nsom_q_target": _ranking_projection(
                        rows,
                        _rank_by_score(
                            (row["candidate_id"], row["nsom"]["observer_capability"]["q_target"])
                            for row in rows
                        ),
                        "nsom",
                        "observer_capability.q_target",
                    ),
                    "nsom_practical_target_value": _ranking_projection(
                        rows,
                        _rank_by_score(
                            (row["candidate_id"], _practical_target_value(row))
                            for row in rows
                        ),
                        "nsom",
                        "practical_target_value.value",
                    ),
                },
                "candidates": rows,
                "metadata": {
                    "developer_only": True,
                    "runtime_wiring": False,
                    "side_effects": {
                        "file_writes": False,
                        "automatic_logging": False,
                        "network": False,
                        "qml_exposure": False,
                        "equipment_recommendations_changed": False,
                        "planner_changed": False,
                        "home_changed": False,
                        "best_object_changed": False,
                        "sky_compass_changed": False,
                    },
                    "candidate_count": len(rows),
                    "equipment_profile": {
                        "telescope_count": len(telescope_items),
                        "eyepiece_count": len(eyepiece_items),
                        "barlow_count": len(barlow_items),
                        "binocular_count": len(binocular_items),
                    },
                },
            }
        )

    def _candidate_row(
        self,
        candidate: RecommendationCandidate,
        *,
        target: CelestialObject,
        intrinsic: IntrinsicTargetQuality,
        environment: ObservationEnvironment,
        effective: EffectiveObservability,
        observable: ObservableTargetValue,
        sky_quality: SkyQuality,
        seeing: SeeingTransparency | None,
        confidence: RecommendationConfidence,
    ) -> dict[str, object]:
        observer = _observer_capability_from_candidate(candidate)
        q_target = project_observer_capability_for_target(observer, observable.target_class)
        practical = PracticalTargetValue.from_observable(
            observable_target_value=observable,
            observer_capability=observer,
            capability_summary=q_target,
        )
        legacy = self._legacy_candidate_projection(candidate, target, sky_quality=sky_quality, seeing=seeing)
        return {
            "candidate_id": candidate.configuration.configuration_id,
            "label": candidate.detail_label,
            "equipment_type": candidate.equipment_type,
            "setup_type": candidate.setup_type,
            "telescope_name": candidate.telescope_name,
            "configuration": _configuration_projection(candidate.configuration),
            "legacy": legacy,
            "nsom": _nsom_projection(
                intrinsic,
                environment,
                effective,
                observable,
                practical,
                confidence,
                seeing=seeing,
                sky_quality=sky_quality,
            ),
            "deltas": {
                "q_target_minus_legacy_unit_score": q_target - candidate.score / 100.0,
                "practical_minus_legacy_score": practical.value - candidate.score,
            },
        }

    def _legacy_candidate_projection(
        self,
        candidate: RecommendationCandidate,
        target: CelestialObject,
        *,
        sky_quality: SkyQuality,
        seeing: SeeingTransparency | None,
    ) -> dict[str, object]:
        traits = TargetObservationTraits.from_object(target)
        profile = self._legacy_profile(candidate, target, traits, seeing=seeing, sky_quality=sky_quality)
        components = self._legacy_component_breakdown(candidate, traits, profile, sky_quality)
        return {
            "score": candidate.score,
            "formula": (
                "angular_scale + magnification + exit_pupil + light_gathering + "
                "seeing_compatibility + handling"
            ),
            "components": components,
            "component_sum": sum(float(value) for value in components.values()),
            "target_profile": profile,
            "available_components": tuple(components),
            "unavailable_components": (
                "observer_capability_profile:not_exposed_as_structured_profile",
                "q_target:not_part_of_equipment_service_formula",
                "observable_target_value:not_separated_from_equipment_score",
                "recommendation_confidence:not_part_of_equipment_score",
            ),
            "ownership_mixing": {
                "target_traits": {
                    "used": True,
                    "mixed_into_equipment_score": True,
                    "examples": ("angular_size", "magnitude", "recommended_observation_type"),
                },
                "sky_quality": {
                    "used": True,
                    "mixed_into_equipment_score": True,
                    "source": sky_quality.source,
                },
                "seeing": {
                    "used": seeing is not None,
                    "mixed_into_equipment_score": True,
                    "source": seeing.source if seeing else "not_supplied",
                },
                "observer_configuration": {
                    "used": True,
                    "mixed_into_equipment_score": True,
                    "examples": ("magnification", "exit_pupil", "field_of_view", "barlow"),
                },
            },
        }

    def _legacy_profile(
        self,
        candidate: RecommendationCandidate,
        target: CelestialObject,
        traits: TargetObservationTraits,
        *,
        seeing: SeeingTransparency | None,
        sky_quality: SkyQuality,
    ) -> dict[str, object]:
        if candidate.binocular:
            return self._equipment_service._binocular_target_profile(traits, sky_quality)
        telescope = candidate.telescope
        if telescope:
            return self._equipment_service._target_profile(target, telescope, seeing, sky_quality)
        return {}

    def _legacy_component_breakdown(
        self,
        candidate: RecommendationCandidate,
        traits: TargetObservationTraits,
        profile: dict[str, object],
        sky_quality: SkyQuality,
    ) -> dict[str, float]:
        configuration = candidate.configuration
        multiplier = candidate.multiplier
        return {
            "angular_scale": self._equipment_service._angular_scale_score(
                traits,
                configuration,
                profile,
                24.0,
            ),
            "magnification": self._equipment_service._magnification_score(
                configuration.magnification,
                profile,
                24.0,
            ),
            "exit_pupil": self._equipment_service._exit_pupil_score(
                configuration.exit_pupil_mm,
                profile,
                16.0,
            ),
            "light_gathering": self._equipment_service._light_gathering_score(
                traits,
                configuration,
                sky_quality,
                16.0,
            ),
            "seeing_compatibility": self._equipment_service._seeing_compatibility_score(
                configuration.magnification,
                profile,
                10.0,
            ),
            "handling": self._equipment_service._handling_score(
                configuration,
                profile,
                multiplier,
                10.0,
            ),
        }


def _observer_capability_from_candidate(candidate: RecommendationCandidate) -> ObserverCapability:
    configuration = candidate.configuration
    objective = _configuration_objective_mm(configuration)
    true_field = configuration.true_field_of_view_deg
    if configuration.binocular:
        binocular = configuration.binocular
        tracking = 0.35 if binocular.image_stabilized else 0.15
        practical_comfort = _binocular_comfort(configuration.magnification, binocular.image_stabilized)
        field_of_view = 0.78 if configuration.magnification <= 12.0 else 0.55
        notes = (
            "nsom:equipment_observer_capability",
            "adapter:configuration_derived",
            f"binocular={binocular.name}",
            f"magnification={configuration.magnification:.1f}",
        )
    else:
        telescope = configuration.telescope
        tracking = _tracking_capability(telescope.mount if telescope else "")
        practical_comfort = _telescope_comfort(configuration)
        field_of_view = _clamp_unit((true_field or 0.0) / 3.0)
        notes = (
            "nsom:equipment_observer_capability",
            "adapter:configuration_derived",
            f"telescope={telescope.name if telescope else ''}",
            f"magnification={configuration.magnification:.1f}",
            f"true_field={true_field:.3f}" if true_field is not None else "true_field=unavailable",
        )

    return ObserverCapability(
        light_grasp=_unit_from_range(objective, lower=35.0, upper=250.0),
        resolution=_unit_from_range(objective, lower=50.0, upper=250.0),
        field_of_view=field_of_view,
        magnification_range=_clamp_unit(configuration.magnification / 180.0),
        tracking_or_goto=tracking,
        automation_or_eaa=0.0,
        filters=(),
        experience_level=0.75,
        observing_style="visual",
        practical_comfort=practical_comfort,
        notes=notes,
    )


def _nsom_projection(
    intrinsic: IntrinsicTargetQuality,
    environment: ObservationEnvironment,
    effective: EffectiveObservability,
    observable: ObservableTargetValue,
    practical: PracticalTargetValue,
    confidence: RecommendationConfidence,
    *,
    seeing: SeeingTransparency | None,
    sky_quality: SkyQuality,
) -> dict[str, object]:
    observer = practical.observer_capability
    return {
        "intrinsic_target_quality": intrinsic,
        "observation_environment": environment,
        "effective_observability": effective,
        "observable_target_value": observable,
        "observer_capability": {
            **nsom_to_json_compatible(observer),
            "summary_for_planning": observer.summary_for_planning(),
            "q_target": practical.observer_capability_summary,
            "target_class_weighting_profile": observer_capability_weight_profile_for_target(observable.target_class),
            "derivation": "configuration_derived_adapter",
        },
        "practical_target_value": practical,
        "recommendation_confidence": _confidence_projection(confidence),
        "ownership": {
            "observer_equipment_effects": {
                "used_in_observer_capability": True,
                "used_in_practical_target_value": True,
                "used_in_observable_target_value": False,
                "q_target": practical.observer_capability_summary,
            },
            "sky_quality_effects": {
                "sky_quality_source": sky_quality.source,
                "used_in_observer_capability": False,
                "used_in_practical_target_value_through_observable": True,
                "legacy_equipment_score_uses_sky_quality": True,
            },
            "seeing_effects": {
                "seeing_source": seeing.source if seeing else "not_supplied",
                "used_in_observer_capability": False,
                "used_in_practical_target_value": False,
                "legacy_equipment_score_uses_seeing": seeing is not None,
            },
            "confidence_effects": {
                "role": "metadata_only",
                "score_factor": False,
                "score_effect": 0.0,
            },
        },
    }


def _confidence_projection(confidence: RecommendationConfidence) -> dict[str, object]:
    return {
        **nsom_to_json_compatible(confidence),
        "value": confidence.value,
        "role": "metadata_only",
        "score_factor": False,
        "score_effect": 0.0,
    }


def _target_projection(target: CelestialObject, intrinsic: IntrinsicTargetQuality) -> dict[str, object]:
    return {
        "object_id": target.id,
        "name": target.name,
        "object_type": target.object_type,
        "target_class": intrinsic.target_class,
        "visible": target.visible,
        "score": target.score,
        "recommended_observation_type": target.recommended_observation_type,
        "max_altitude": target.max_altitude,
        "magnitude": target.magnitude,
        "apparent_size": target.apparent_size,
    }


def _configuration_projection(configuration: ObservationConfiguration) -> dict[str, object]:
    return {
        "configuration_id": configuration.configuration_id,
        "equipment_type": configuration.equipment_type,
        "magnification": configuration.magnification,
        "exit_pupil_mm": configuration.exit_pupil_mm,
        "true_field_of_view_deg": configuration.true_field_of_view_deg,
        "limiting_magnitude_estimate": configuration.limiting_magnitude_estimate,
        "resolution_estimate": configuration.resolution_estimate,
        "image_stabilized": configuration.image_stabilized,
        "telescope_id": configuration.telescope.id if configuration.telescope else None,
        "telescope_name": configuration.telescope.name if configuration.telescope else None,
        "eyepiece_id": configuration.eyepiece.id if configuration.eyepiece else None,
        "eyepiece_name": configuration.eyepiece.name if configuration.eyepiece else None,
        "barlow_id": configuration.barlow.id if configuration.barlow else None,
        "barlow_name": configuration.barlow.name if configuration.barlow else None,
        "binocular_id": configuration.binocular.id if configuration.binocular else None,
        "binocular_name": configuration.binocular.name if configuration.binocular else None,
        "focal_position_mm": configuration.focal_position_mm,
        "focal_position_label": configuration.focal_position_label,
    }


def _rank_by_score(scores: Iterable[tuple[object, object]]) -> dict[str, int]:
    ordered = sorted(
        (
            (str(candidate_id), float(score), index)
            for index, (candidate_id, score) in enumerate(scores)
        ),
        key=lambda item: (-item[1], item[2]),
    )
    return {candidate_id: rank for rank, (candidate_id, _, _) in enumerate(ordered, start=1)}


def _ranking_projection(
    rows: tuple[dict[str, object], ...],
    ranks: dict[str, int],
    section: str,
    score_path: str,
) -> tuple[dict[str, object], ...]:
    by_id = {str(row["candidate_id"]): row for row in rows}
    return tuple(
        {
            "candidate_id": candidate_id,
            "rank": rank,
            "label": by_id[candidate_id]["label"],
            "score": _score_from_path(by_id[candidate_id], section, score_path),
        }
        for candidate_id, rank in sorted(ranks.items(), key=lambda item: item[1])
    )


def _score_from_path(row: dict[str, object], section: str, score_path: str) -> object:
    value: object = row[section]
    for part in score_path.split("."):
        if isinstance(value, dict):
            value = value[part]
        else:
            value = getattr(value, part)
    return value


def _practical_target_value(row: dict[str, object]) -> float:
    practical = row["nsom"]["practical_target_value"]  # type: ignore[index]
    return float(getattr(practical, "value"))


def _configuration_objective_mm(configuration: ObservationConfiguration) -> float:
    if configuration.telescope:
        return float(configuration.telescope.aperture_mm)
    if configuration.binocular:
        return float(configuration.binocular.objective_diameter_mm)
    return 7.0


def _telescope_comfort(configuration: ObservationConfiguration) -> float:
    comfort = 0.82
    if configuration.barlow:
        comfort -= 0.18
    if configuration.magnification > 180.0:
        comfort -= 0.22
    elif configuration.magnification > 120.0:
        comfort -= 0.10
    if configuration.exit_pupil_mm < 0.5:
        comfort -= 0.20
    return _clamp_unit(comfort)


def _binocular_comfort(magnification: float, image_stabilized: bool) -> float:
    if magnification <= 10.0:
        comfort = 0.92
    elif magnification <= 12.0:
        comfort = 0.80
    elif magnification <= 15.0:
        comfort = 0.62
    else:
        comfort = 0.42
    if image_stabilized:
        comfort += 0.18
    return _clamp_unit(comfort)


def _tracking_capability(value: object) -> float:
    text = str(value).lower()
    if any(token in text for token in ("goto", "go-to", "computer", "eq", "tracking", "motoriz")):
        return 0.8
    if any(token in text for token in ("dob", "altaz", "manual")):
        return 0.2
    return 0.4


def _unit_from_range(value: object, *, lower: float, upper: float) -> float:
    number = _finite_float(value, default=lower)
    if upper <= lower:
        return 0.0
    return _clamp_unit((number - lower) / (upper - lower))


def _finite_float(value: object, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _clamp_unit(value: object) -> float:
    return max(0.0, min(1.0, _finite_float(value)))
