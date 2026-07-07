from __future__ import annotations

from statistics import mean

from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    IntrinsicTargetQuality,
    NsomTargetClass,
    ObservableTargetValue,
    ObservationEnvironment,
    RecommendationConfidence,
    SessionViability,
    nsom_to_json_compatible,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.app.services.home_nsom_observable import build_home_observation_environment
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_recommendation_confidence,
    build_session_viability,
)


class AdvancedObservingNsomComparisonService:
    """Developer-only comparison between legacy advanced scores and NSOM layers.

    The service evaluates only caller-supplied runtime inputs and returns a
    JSON-compatible diagnostic dictionary. It does not change advanced scores,
    Home, Best Object, Planner or Sky Compass, and it does not write files, log,
    fetch data or expose anything to QML.
    """

    def __init__(
        self,
        *,
        advanced_service: AdvancedObservingService | None = None,
    ) -> None:
        self._advanced_service = advanced_service or AdvancedObservingService()

    def compare(
        self,
        *,
        weather: WeatherSummary,
        seeing: SeeingTransparency,
        sky_quality: SkyQuality,
        moon: MoonSummary | None = None,
        confidence: RecommendationConfidence | None = None,
    ) -> dict[str, object]:
        advanced_scores = self._advanced_service.scores(weather, seeing, sky_quality, moon)
        blocking_status = NightPlannerService.weather_blocking_status(weather)
        session = build_session_viability(
            weather_summary=weather,
            blocking_status=blocking_status,
        )
        recommendation_confidence = confidence or build_recommendation_confidence(
            weather_summary=weather,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon is not None,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:advanced_observing_comparison",),
        )
        planetary_reference = _category_reference(
            NsomTargetClass.PLANET,
            weather=weather,
            seeing=seeing,
            sky_quality=sky_quality,
            moon=moon,
            category="planetary",
        )
        deep_sky_references = tuple(
            _category_reference(
                target_class,
                weather=weather,
                seeing=seeing,
                sky_quality=sky_quality,
                moon=moon,
                category="deep_sky",
            )
            for target_class in (
                NsomTargetClass.GALAXY,
                NsomTargetClass.DIFFUSE_NEBULA,
                NsomTargetClass.OPEN_CLUSTER,
                NsomTargetClass.GLOBULAR_CLUSTER,
            )
        )

        return nsom_to_json_compatible(
            {
                "legacy": {
                    "advanced_scores": advanced_scores,
                    "planetary": self._legacy_planetary_projection(
                        weather=weather,
                        seeing=seeing,
                        moon=moon,
                        final_score=advanced_scores.planetary_score,
                        label=advanced_scores.planetary_label,
                    ),
                    "deep_sky": self._legacy_deep_sky_projection(
                        weather=weather,
                        seeing=seeing,
                        sky_quality=sky_quality,
                        moon=moon,
                        final_score=advanced_scores.deep_sky_score,
                        label=advanced_scores.deep_sky_label,
                    ),
                },
                "nsom": {
                    "planetary_reference": planetary_reference,
                    "deep_sky_references": deep_sky_references,
                    "deep_sky_reference_summary": _deep_sky_reference_summary(deep_sky_references),
                    "session_viability": _session_projection(
                        session,
                        weather=weather,
                        blocking_status=blocking_status,
                    ),
                    "recommendation_confidence": _confidence_projection(recommendation_confidence),
                    "ownership": _ownership_projection(),
                },
                "metadata": {
                    "developer_only": True,
                    "runtime_wiring": False,
                    "score_parity_expected": False,
                    "reference_only": True,
                    "side_effects": {
                        "file_writes": False,
                        "automatic_logging": False,
                        "network": False,
                        "qml_exposure": False,
                        "advanced_scores_changed": False,
                        "home_changed": False,
                        "best_object_changed": False,
                        "planner_changed": False,
                        "sky_compass_changed": False,
                    },
                },
            }
        )

    def _legacy_planetary_projection(
        self,
        *,
        weather: WeatherSummary,
        seeing: SeeingTransparency,
        moon: MoonSummary | None,
        final_score: int,
        label: str,
    ) -> dict[str, object]:
        moon_illumination = self._advanced_service._moon_illumination(moon)
        weather_component = weather.score_value * 0.36
        seeing_component = seeing.seeing_score * 0.42
        wind_quality = 100 - min(55, weather.wind_kmh * 1.4)
        wind_component = wind_quality * 0.12
        moon_quality = 100 - min(25, moon_illumination * 0.15)
        moon_component = moon_quality * 0.10
        raw_score = round(weather_component + seeing_component + wind_component + moon_component)
        weather_cap = self._advanced_service._weather_cap(weather)
        return {
            "score": final_score,
            "label": label,
            "raw_score_before_cap": raw_score,
            "weather_cap": weather_cap,
            "formula": (
                "round(weather.score_value*0.36 + seeing.seeing_score*0.42 + "
                "(100-min(55, wind_kmh*1.4))*0.12 + "
                "(100-min(25, moon_illumination*0.15))*0.10), capped by weather"
            ),
            "components": {
                "weather": {
                    "input": weather.score_value,
                    "weight": 0.36,
                    "contribution": weather_component,
                    "nsom_layer": "session",
                },
                "seeing": {
                    "input": seeing.seeing_score,
                    "weight": 0.42,
                    "contribution": seeing_component,
                    "nsom_layer": "sky_atmospheric_stability_or_future_observer_limit",
                },
                "wind": {
                    "input": weather.wind_kmh,
                    "quality": wind_quality,
                    "weight": 0.12,
                    "contribution": wind_component,
                    "nsom_layer": "session",
                },
                "moon": {
                    "input": moon_illumination,
                    "quality": moon_quality,
                    "weight": 0.10,
                    "contribution": moon_component,
                    "nsom_layer": "sky",
                },
            },
            "ownership_mixing": (
                "weather_session_mixed_into_category_score",
                "seeing_mixed_into_category_score",
                "moon_mixed_into_planetary_category_score",
            ),
            "unavailable_components": (
                "intrinsic_target_quality:not_target_specific",
                "observer_capability:not_part_of_advanced_scores",
                "recommendation_confidence:not_part_of_advanced_scores",
            ),
        }

    def _legacy_deep_sky_projection(
        self,
        *,
        weather: WeatherSummary,
        seeing: SeeingTransparency,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
        final_score: int,
        label: str,
    ) -> dict[str, object]:
        moon_illumination = self._advanced_service._moon_illumination(moon)
        light_pollution_quality = self._advanced_service._light_pollution_quality(sky_quality)
        weather_component = weather.score_value * 0.34
        transparency_component = seeing.transparency_score * 0.30
        light_pollution_component = light_pollution_quality * 0.24
        moon_component = (100 - moon_illumination) * 0.12
        raw_score = round(
            weather_component
            + transparency_component
            + light_pollution_component
            + moon_component
        )
        weather_cap = self._advanced_service._weather_cap(weather)
        return {
            "score": final_score,
            "label": label,
            "raw_score_before_cap": raw_score,
            "weather_cap": weather_cap,
            "formula": (
                "round(weather.score_value*0.34 + transparency_score*0.30 + "
                "light_pollution_quality*0.24 + (100-moon_illumination)*0.12), "
                "capped by weather"
            ),
            "components": {
                "weather": {
                    "input": weather.score_value,
                    "weight": 0.34,
                    "contribution": weather_component,
                    "nsom_layer": "session",
                },
                "transparency": {
                    "input": seeing.transparency_score,
                    "weight": 0.30,
                    "contribution": transparency_component,
                    "nsom_layer": "sky",
                },
                "light_pollution": {
                    "input": {
                        "bortle_class": sky_quality.bortle_class,
                        "viirs_radiance": sky_quality.viirs_radiance,
                    },
                    "quality": light_pollution_quality,
                    "weight": 0.24,
                    "contribution": light_pollution_component,
                    "nsom_layer": "sky",
                },
                "moon": {
                    "input": moon_illumination,
                    "weight": 0.12,
                    "contribution": moon_component,
                    "nsom_layer": "sky",
                },
            },
            "ownership_mixing": (
                "weather_session_mixed_into_category_score",
                "transparency_mixed_into_category_score",
                "light_pollution_mixed_into_category_score",
                "moon_mixed_into_category_score",
            ),
            "unavailable_components": (
                "intrinsic_target_quality:not_target_specific",
                "target_class_specific_sky_sensitivity:not_exposed",
                "observer_capability:not_part_of_advanced_scores",
                "recommendation_confidence:not_part_of_advanced_scores",
            ),
        }


def _category_reference(
    target_class: NsomTargetClass,
    *,
    weather: WeatherSummary,
    seeing: SeeingTransparency,
    sky_quality: SkyQuality,
    moon: MoonSummary | None,
    category: str,
) -> dict[str, object]:
    intrinsic = IntrinsicTargetQuality.from_score(
        100,
        object_id=f"advanced-reference-{target_class.value}",
        name=f"Advanced {target_class.value} reference",
        target_class=target_class,
        astronomical_visibility=True,
        source_fields=(
            ("reference_only", True),
            ("category", category),
        ),
    )
    base_environment = build_home_observation_environment(
        _reference_target(target_class),
        intrinsic,
        sky_quality=sky_quality,
        moon=moon,
    )
    transparency = (
        seeing.seeing_score / 100.0
        if category == "planetary"
        else seeing.transparency_score / 100.0
    )
    environment = ObservationEnvironment.from_components(
        geometric_visibility=base_environment.geometric_visibility,
        lunar_sky_background=base_environment.lunar_sky_background,
        static_sky_background=base_environment.static_sky_background,
        atmospheric_transparency=transparency,
        horizon_context=base_environment.horizon_context,
        sky_quality_source=base_environment.sky_quality_source,
        weather_source="advanced_observing_reference",
        notes=(
            "nsom:advanced_observing_comparison",
            "reference_only:true",
            f"category={category}",
            f"weather_score_excluded_from_observable={weather.score_value}",
            f"atmospheric_reference={transparency:.3f}",
            *base_environment.notes,
        ),
    )
    effective = EffectiveObservability.from_environment(environment)
    observable = ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=intrinsic,
        effective_observability=effective,
        target_class=target_class,
    )
    return {
        "target_class": target_class,
        "reference_only": True,
        "category": category,
        "intrinsic_target_quality": intrinsic,
        "observation_environment": environment,
        "effective_observability": effective,
        "observable_target_value": observable,
        "score_role": (
            "NSOM reference projection only; not used by AdvancedObservingService "
            "and not a runtime replacement score."
        ),
    }


def _reference_target(target_class: NsomTargetClass) -> CelestialObject:
    return CelestialObject(
        id=f"advanced-reference-{target_class.value}",
        name=f"Advanced {target_class.value} reference",
        object_type=_object_type_for_target_class(target_class),
        image="",
        magnitude="n/d",
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="21:00",
        observing_window="21:00 - 02:00",
        notes="NSOM AdvancedObserving reference target.",
        recommended_setup="n/d",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=100,
        score_label="Reference",
        difficulty="Media",
    )


def _object_type_for_target_class(target_class: NsomTargetClass) -> str:
    return {
        NsomTargetClass.PLANET: "Pianeta",
        NsomTargetClass.MOON: "Luna",
        NsomTargetClass.GALAXY: "Galaxy",
        NsomTargetClass.DIFFUSE_NEBULA: "Diffuse nebula",
        NsomTargetClass.OPEN_CLUSTER: "Open cluster",
        NsomTargetClass.GLOBULAR_CLUSTER: "Globular cluster",
        NsomTargetClass.PLANETARY_NEBULA: "Planetary nebula",
    }[target_class]


def _deep_sky_reference_summary(references: tuple[dict[str, object], ...]) -> dict[str, object]:
    observable_values = tuple(
        float(reference["observable_target_value"].value)
        for reference in references
    )
    effective_values = tuple(
        float(reference["effective_observability"].value)
        for reference in references
    )
    return {
        "reference_only": True,
        "target_classes": tuple(str(reference["target_class"].value) for reference in references),
        "average_observable_target_value": mean(observable_values) if observable_values else None,
        "average_effective_observability": mean(effective_values) if effective_values else None,
        "score_role": "diagnostic summary only; not an AdvancedObserving runtime score",
    }


def _session_projection(
    session: SessionViability,
    *,
    weather: WeatherSummary,
    blocking_status: WeatherBlockingStatus,
) -> dict[str, object]:
    return {
        **nsom_to_json_compatible(session),
        "role": "session_metadata",
        "weather_score": weather.score_value,
        "blocking_status": blocking_status,
        "score_effect_on_reference_observable_values": 0.0,
    }


def _confidence_projection(confidence: RecommendationConfidence) -> dict[str, object]:
    return {
        **nsom_to_json_compatible(confidence),
        "value": confidence.value,
        "role": "metadata_only",
        "score_factor": False,
        "score_effect": 0.0,
    }


def _ownership_projection() -> dict[str, object]:
    return {
        "legacy_advanced_scores": {
            "mixes_session_weather": True,
            "mixes_sky_transparency": True,
            "mixes_moon_background": True,
            "mixes_light_pollution": True,
            "mixes_observer_capability": False,
            "mixes_confidence": False,
        },
        "nsom_reference": {
            "weather": "SessionViability metadata; excluded from reference ObservableTargetValue",
            "seeing_transparency": "Sky/environment reference component",
            "moon": "Sky/environment reference component with target-class sensitivity",
            "light_pollution": "Sky/environment reference component with target-class sensitivity",
            "observer_capability": "Not part of AdvancedObservingService comparison in 1.8.0",
            "recommendation_confidence": "Parallel metadata only",
        },
    }
