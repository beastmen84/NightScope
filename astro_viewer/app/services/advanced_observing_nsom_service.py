from __future__ import annotations

from statistics import mean

from astro_viewer.app.models.nsom import (
    EffectiveObservability,
    IntrinsicTargetQuality,
    NsomTargetClass,
    ObservableTargetValue,
    ObservationEnvironment,
    RecommendationConfidence,
)
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.home_nsom_observable import build_home_observation_environment
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.nsom_diagnostic_adapters import (
    build_recommendation_confidence,
    build_session_viability,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService

NSOM_ADVANCED_OBSERVING_ENABLED = True


class AdvancedObservingNsomService:
    """Experimental Advanced Observing scores from NSOM category diagnostics.

    The service is an internal/default-on runtime path. It preserves the
    existing `AdvancedObservingScores` payload shape, does not expose NSOM fields
    to QML, and keeps SessionViability and RecommendationConfidence out of the
    score path.
    """

    def scores(
        self,
        weather: WeatherSummary,
        seeing: SeeingTransparency,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
        *,
        confidence: RecommendationConfidence | None = None,
    ) -> AdvancedObservingScores:
        session = build_session_viability(
            weather_summary=weather,
            blocking_status=NightPlannerService.weather_blocking_status(weather),
        )
        recommendation_confidence = confidence or build_recommendation_confidence(
            weather_summary=weather,
            viirs_available=getattr(sky_quality, "viirs_radiance", None) is not None,
            moon_geometry_available=moon is not None,
            provider_fallback_used=getattr(sky_quality, "viirs_radiance", None) is None,
            notes=("nsom:advanced_observing_runtime",),
        )

        planetary = _category_observable_value(
            NsomTargetClass.PLANET,
            sky_quality=sky_quality,
            moon=moon,
            atmospheric_transparency=seeing.seeing_score / 100.0,
            category="planetary",
        )
        deep_sky_values = tuple(
            _category_observable_value(
                target_class,
                sky_quality=sky_quality,
                moon=moon,
                atmospheric_transparency=seeing.transparency_score / 100.0,
                category="deep_sky",
            )
            for target_class in (
                NsomTargetClass.GALAXY,
                NsomTargetClass.DIFFUSE_NEBULA,
                NsomTargetClass.OPEN_CLUSTER,
                NsomTargetClass.GLOBULAR_CLUSTER,
            )
        )

        planetary_score = _score_from_observable(planetary)
        deep_sky_score = _score_from_observable(mean(value.value for value in deep_sky_values))
        scorer = ObservingScoreService()
        explanation = (
            "NSOM sperimentale: planetario e cielo profondo usano ObservableTargetValue "
            "di categoria; meteo/sessione e confidence restano metadati paralleli "
            f"({session.state}, confidence {_confidence_label(recommendation_confidence)})."
        )
        return AdvancedObservingScores(
            planetary_score=planetary_score,
            deep_sky_score=deep_sky_score,
            planetary_label=scorer.score_label(planetary_score),
            deep_sky_label=scorer.score_label(deep_sky_score),
            explanation=explanation,
        )


def _category_observable_value(
    target_class: NsomTargetClass,
    *,
    sky_quality: SkyQuality,
    moon: MoonSummary | None,
    atmospheric_transparency: float,
    category: str,
) -> ObservableTargetValue:
    intrinsic = IntrinsicTargetQuality.from_score(
        100,
        object_id=f"advanced-runtime-{target_class.value}",
        name=f"Advanced {target_class.value} runtime reference",
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
    environment = ObservationEnvironment.from_components(
        geometric_visibility=base_environment.geometric_visibility,
        lunar_sky_background=base_environment.lunar_sky_background,
        static_sky_background=base_environment.static_sky_background,
        atmospheric_transparency=atmospheric_transparency,
        horizon_context=base_environment.horizon_context,
        sky_quality_source=base_environment.sky_quality_source,
        weather_source="advanced_observing_nsom_runtime",
        notes=(
            "nsom:advanced_observing_runtime",
            "advanced_observing:session_viability_excluded_from_score",
            "advanced_observing:confidence_metadata_only",
            f"category={category}",
            f"target_class={target_class.value}",
            *base_environment.notes,
        ),
    )
    effective = EffectiveObservability.from_environment(environment)
    return ObservableTargetValue.from_intrinsic(
        intrinsic_target_quality=intrinsic,
        effective_observability=effective,
        target_class=target_class,
    )


def _reference_target(target_class: NsomTargetClass) -> CelestialObject:
    return CelestialObject(
        id=f"advanced-runtime-{target_class.value}",
        name=f"Advanced {target_class.value} runtime reference",
        object_type=_object_type_for_target_class(target_class),
        image="",
        magnitude="n/d",
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="21:00",
        observing_window="21:00 - 02:00",
        notes="NSOM AdvancedObserving runtime reference target.",
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


def _score_from_observable(value: ObservableTargetValue | float) -> int:
    numeric = value.value if isinstance(value, ObservableTargetValue) else float(value)
    return max(0, min(100, round(numeric)))


def _confidence_label(confidence: RecommendationConfidence) -> str:
    value = confidence.value
    return "n/d" if value is None else f"{value:.2f}"
