from __future__ import annotations

from dataclasses import replace

from astro_viewer.app.models.equipment import OpticalFilter
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.filter_recommendation_service import (
    FilterRecommendationService,
)


def test_recommendation_prefers_owned_primary_class_and_is_deterministic() -> None:
    target = replace(_target(), best_filter_class="OIII", fallback_filter_class="UHC")
    filters = [
        _filter("catalog-filter-3", "Zeta OIII", "OIII"),
        _filter("catalog-filter-2", "Alpha OIII", "OIII"),
        _filter("catalog-filter-1", "UHC", "UHC"),
    ]

    recommendation = FilterRecommendationService().recommend(target, filters)

    assert recommendation.primary.available is True
    assert recommendation.primary.filter_class == "OIII"
    assert recommendation.primary.value == "Alpha OIII"
    assert recommendation.primary.filter_id == "catalog-filter-2"
    assert recommendation.optional_color.applicable is False


def test_recommendation_uses_owned_fallback_without_stacking_filters() -> None:
    target = replace(
        _target(),
        best_filter_class="POLARIZING",
        fallback_filter_class="ND",
    )

    recommendation = FilterRecommendationService().recommend(
        target,
        [_filter("catalog-filter-4", "Celestron Moon", "ND")],
    )

    assert recommendation.primary.available is True
    assert recommendation.primary.filter_class == "ND"
    assert recommendation.primary.value == "Celestron Moon"


def test_missing_primary_reports_classes_without_inventing_a_product() -> None:
    target = replace(
        _target(),
        best_filter_class="POLARIZING",
        fallback_filter_class="ND",
    )

    recommendation = FilterRecommendationService().recommend(target, [])

    assert recommendation.primary.applicable is True
    assert recommendation.primary.available is False
    assert recommendation.primary.label == "Filtro suggerito (non disponibile)"
    assert recommendation.primary.value == "Polarizzatore / Densità neutra"
    assert recommendation.primary.filter_id == ""


def test_optional_color_recommendation_is_independent_from_primary() -> None:
    target = replace(
        _target(),
        best_filter_class="CONTRAST",
        optional_color_filter_class="COLOR_RED",
    )

    recommendation = FilterRecommendationService().recommend(
        target,
        [_filter("catalog-filter-8", "Celestron #25 Red", "COLOR_RED")],
    )

    assert recommendation.primary.available is False
    assert recommendation.optional_color.available is True
    assert recommendation.optional_color.label == "Filtro colorato opzionale"
    assert recommendation.optional_color.value == "Celestron #25 Red"


def test_legacy_unspecified_color_is_never_recommended() -> None:
    target = replace(_target(), optional_color_filter_class="COLOR_UNSPECIFIED")

    recommendation = FilterRecommendationService().recommend(
        target,
        [_filter("catalog-filter-9", "Filtro legacy", "COLOR_UNSPECIFIED")],
    )

    assert recommendation.optional_color.applicable is False


def _filter(filter_id: str, name: str, filter_class: str) -> OpticalFilter:
    return OpticalFilter(id=filter_id, name=name, filter_class=filter_class)


def _target() -> CelestialObject:
    return CelestialObject(
        id="target",
        name="Target",
        object_type="Nebulosa",
        image="",
        magnitude="8",
        distance="Catalogo",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="23:00",
        observing_window="21:00 - 02:00",
        notes="",
        recommended_setup="",
        visibility_class="Telescopio",
        azimuth="180 gradi",
        time_above_horizon="5 h",
    )
