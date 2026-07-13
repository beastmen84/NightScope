from __future__ import annotations

from dataclasses import replace

from astro_viewer.app.models.equipment import FocalReducer
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.reducer_recommendation_service import (
    ReducerRecommendationService,
)


def test_recommendation_uses_only_owned_reducers_compatible_with_selected_telescope() -> None:
    target = replace(_target(), imaging_reducer_recommended=True)
    owned = _reducer("owned", "Owned 0.8x", 0.8, ("scope-a",))
    other = _reducer("other", "Other 0.7x", 0.7, ("scope-a",))

    recommendation = ReducerRecommendationService().recommend(
        target,
        "scope-a",
        [owned],
        [owned, other],
    )

    assert recommendation.applicable is True
    assert recommendation.available is True
    assert recommendation.label == "Riduttore fotografico consigliato"
    assert [item.reducer_id for item in recommendation.items] == ["owned"]


def test_missing_profile_reducer_suggests_exact_catalog_match() -> None:
    target = replace(_target(), imaging_reducer_recommended=True)
    candidate = _reducer("catalog", "Dedicated 0.7x", 0.7, ("scope-a",))

    recommendation = ReducerRecommendationService().recommend(
        target,
        "scope-a",
        [],
        [candidate],
    )

    assert recommendation.applicable is True
    assert recommendation.available is False
    assert recommendation.label == (
        "Riduttore fotografico suggerito (non disponibile)"
    )
    assert recommendation.value == "Dedicated 0.7x (0.7x)"


def test_non_photographic_and_incompatible_reducers_are_ignored() -> None:
    target = replace(_target(), imaging_reducer_recommended=True)
    visual_only = _reducer(
        "visual",
        "Visual only",
        0.6,
        ("scope-a",),
        imaging_compatible=False,
    )
    wrong_scope = _reducer("wrong", "Wrong scope", 0.8, ("scope-b",))

    recommendation = ReducerRecommendationService().recommend(
        target,
        "scope-a",
        [visual_only, wrong_scope],
        [visual_only, wrong_scope],
    )

    assert recommendation.applicable is False


def test_target_flag_and_telescope_setup_are_required() -> None:
    candidate = _reducer("catalog", "Dedicated", 0.7, ("scope-a",))
    service = ReducerRecommendationService()

    assert service.recommend(_target(), "scope-a", [], [candidate]).applicable is False
    assert (
        service.recommend(
            replace(_target(), imaging_reducer_recommended=True),
            "",
            [],
            [candidate],
        ).applicable
        is False
    )


def test_multiple_compatible_reducers_are_reported_without_fake_ranking() -> None:
    target = replace(_target(), imaging_reducer_recommended=True)
    reducers = [
        _reducer("zeta", "Zeta 0.6x", 0.6, ("scope-a",)),
        _reducer("alpha", "Alpha 0.8x", 0.8, ("scope-a",)),
    ]

    recommendation = ReducerRecommendationService().recommend(
        target,
        "scope-a",
        reducers,
        reducers,
    )

    assert [item.reducer_id for item in recommendation.items] == ["alpha", "zeta"]
    assert recommendation.value == "Alpha 0.8x (0.8x) / Zeta 0.6x (0.6x)"


def _reducer(
    reducer_id: str,
    name: str,
    factor: float,
    telescope_ids: tuple[str, ...],
    *,
    imaging_compatible: bool = True,
) -> FocalReducer:
    return FocalReducer(
        id=reducer_id,
        name=name,
        reduction_factor=factor,
        optical_system="REFRACTOR",
        imaging_compatible=imaging_compatible,
        compatible_telescope_ids=telescope_ids,
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
