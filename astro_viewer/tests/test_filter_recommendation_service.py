"""Protect owned-filter compatibility and target-class recommendation rules."""

from __future__ import annotations

from dataclasses import replace

from astro_viewer.app.models.equipment import OpticalFilter
from astro_viewer.app.models.filtering import SOLAR_SYSTEM_FILTER_PREFERENCES
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.filter_recommendation_service import (
    FilterRecommendationService,
)


def test_recommendation_prefers_aperture_compatible_primary_filter() -> None:
    target = replace(_target(), best_filter_class="OIII", fallback_filter_class="UHC")
    filters = [
        _filter("catalog-filter-3", "Alpha OIII", "OIII", minimum_aperture_mm=150),
        _filter("catalog-filter-2", "Zeta OIII", "OIII", minimum_aperture_mm=100),
        _filter("catalog-filter-1", "UHC", "UHC"),
    ]

    recommendation = FilterRecommendationService().recommend(
        target,
        filters,
        filters,
        telescope_aperture_mm=120,
    )

    assert recommendation.primary.available is True
    assert recommendation.primary.filter_class == "OIII"
    assert recommendation.primary.value == "Zeta OIII"
    assert recommendation.primary.filter_id == "catalog-filter-2"
    assert recommendation.optional_color.applicable is False


def test_recommendation_prefers_highest_supported_minimum_aperture() -> None:
    target = replace(_target(), best_filter_class="OIII")
    filters = [
        _filter("catalog-filter-1", "Wide OIII", "OIII", minimum_aperture_mm=100),
        _filter("catalog-filter-2", "Selective OIII", "OIII", minimum_aperture_mm=150),
    ]

    recommendation = FilterRecommendationService().recommend(
        target,
        filters,
        filters,
        telescope_aperture_mm=200,
    )

    assert recommendation.primary.filter_id == "catalog-filter-2"


def test_recommendation_uses_owned_fallback_without_stacking_filters() -> None:
    target = replace(
        _target(),
        best_filter_class="POLARIZING",
        fallback_filter_class="ND",
    )

    owned = [_filter("catalog-filter-4", "Celestron Moon", "ND")]
    catalogue = [
        _filter("catalog-filter-3", "Variable Polarizer", "POLARIZING"),
        *owned,
    ]

    recommendation = FilterRecommendationService().recommend(
        target,
        owned,
        catalogue,
        telescope_aperture_mm=100,
    )

    assert recommendation.primary.available is True
    assert recommendation.primary.filter_class == "ND"
    assert recommendation.primary.value == "Celestron Moon"


def test_missing_primary_reports_only_preferred_class_without_inventing_product() -> None:
    target = replace(
        _target(),
        best_filter_class="POLARIZING",
        fallback_filter_class="ND",
    )

    catalogue = [
        _filter("catalog-filter-3", "Variable Polarizer", "POLARIZING"),
        _filter("catalog-filter-4", "Moon ND", "ND"),
    ]

    recommendation = FilterRecommendationService().recommend(
        target,
        [],
        catalogue,
        telescope_aperture_mm=100,
    )

    assert recommendation.primary.applicable is True
    assert recommendation.primary.available is False
    assert recommendation.primary.label == "Filtro suggerito (non disponibile)"
    assert recommendation.primary.value == "Polarizzatore"
    assert recommendation.primary.filter_id == ""


def test_optional_color_recommendation_is_independent_from_primary() -> None:
    target = replace(
        _target(),
        best_filter_class="CONTRAST",
        optional_color_filter_class="COLOR_RED",
    )

    filters = [
        _filter(
            "catalog-filter-8",
            "Celestron #25 Red",
            "COLOR_RED",
            minimum_aperture_mm=150,
        )
    ]

    recommendation = FilterRecommendationService().recommend(
        target,
        filters,
        filters,
        telescope_aperture_mm=200,
    )

    assert recommendation.primary.available is False
    assert recommendation.optional_color.available is True
    assert recommendation.optional_color.label == "Filtro colorato opzionale"
    assert recommendation.optional_color.value == "Celestron #25 Red"


def test_class_is_hidden_when_catalogue_has_no_aperture_compatible_product() -> None:
    target = replace(_target(), best_filter_class="H_BETA")
    catalogue = [
        _filter(
            "catalog-filter-9",
            "H-beta",
            "H_BETA",
            minimum_aperture_mm=150,
        )
    ]

    recommendation = FilterRecommendationService().recommend(
        target,
        [],
        catalogue,
        telescope_aperture_mm=100,
    )

    assert recommendation.primary.applicable is False


def test_target_specific_color_requires_sufficient_aperture() -> None:
    target = replace(
        _target(),
        id="uranus",
        optional_color_filter_class="COLOR_YELLOW",
    )
    filters = [_filter("catalog-filter-10", "Yellow", "COLOR_YELLOW")]

    below_threshold = FilterRecommendationService().recommend(
        target,
        filters,
        filters,
        telescope_aperture_mm=200,
    )
    at_threshold = FilterRecommendationService().recommend(
        target,
        filters,
        filters,
        telescope_aperture_mm=280,
    )

    assert below_threshold.optional_color.applicable is False
    assert at_threshold.optional_color.available is True
    assert at_threshold.optional_color.filter_id == "catalog-filter-10"


def test_solar_system_policy_keeps_color_as_a_secondary_recommendation() -> None:
    assert SOLAR_SYSTEM_FILTER_PREFERENCES["moon"] == (
        "POLARIZING",
        "ND",
        "COLOR_YELLOW",
    )
    assert SOLAR_SYSTEM_FILTER_PREFERENCES["mars"] == (
        "CONTRAST",
        "MOON_SKYGLOW",
        "COLOR_RED",
    )
    assert SOLAR_SYSTEM_FILTER_PREFERENCES["uranus"] == (
        "",
        "",
        "COLOR_YELLOW",
    )
    assert SOLAR_SYSTEM_FILTER_PREFERENCES["neptune"] == (
        "",
        "",
        "COLOR_YELLOW",
    )


def _filter(
    filter_id: str,
    name: str,
    filter_class: str,
    *,
    minimum_aperture_mm: int | None = None,
) -> OpticalFilter:
    return OpticalFilter(
        id=filter_id,
        name=name,
        filter_class=filter_class,
        minimum_aperture_mm=minimum_aperture_mm,
    )


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
