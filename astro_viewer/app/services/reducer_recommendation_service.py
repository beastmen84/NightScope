"""Recommend compatible owned or catalogue focal reducers for imaging."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from astro_viewer.app.models.equipment import FocalReducer
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.localization import format_compact_number, join_text, tr


@dataclass(frozen=True)
class ReducerRecommendationItem:
    reducer_id: str
    name: str
    reduction_factor: float

    @property
    def display_label(self) -> str:
        return tr(
            "{name} ({factor}x)",
            name=self.name,
            factor=format_compact_number(self.reduction_factor),
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "reducerId": self.reducer_id,
            "name": self.name,
            "reductionFactor": self.reduction_factor,
            "displayLabel": self.display_label,
        }


@dataclass(frozen=True)
class ReducerRecommendation:
    applicable: bool = False
    available: bool = False
    label: str = ""
    value: str = ""
    items: tuple[ReducerRecommendationItem, ...] = field(default_factory=tuple)

    def to_payload(self) -> dict[str, object]:
        return {
            "applicable": self.applicable,
            "available": self.available,
            "label": self.label,
            "value": self.value,
            "items": [item.to_payload() for item in self.items],
        }


class ReducerRecommendationService:
    """Matches photographic reducers without changing Equipment or NSOM."""

    def recommend(
        self,
        target: CelestialObject,
        telescope_id: str,
        profile_reducers: Iterable[FocalReducer],
        catalog_reducers: Iterable[FocalReducer],
    ) -> ReducerRecommendation:
        normalized_telescope_id = telescope_id.strip()
        if (
            not target.imaging_reducer_recommended
            or not normalized_telescope_id
        ):
            return ReducerRecommendation()

        owned = _compatible_reducers(
            profile_reducers,
            normalized_telescope_id,
        )
        candidates = owned or _compatible_reducers(
            catalog_reducers,
            normalized_telescope_id,
        )
        if not candidates:
            return ReducerRecommendation()

        items = tuple(
            ReducerRecommendationItem(
                reducer_id=reducer.id,
                name=reducer.name,
                reduction_factor=reducer.reduction_factor,
            )
            for reducer in candidates
        )
        available = bool(owned)
        return ReducerRecommendation(
            applicable=True,
            available=available,
            label=(
                tr("Riduttore fotografico consigliato")
                if available
                else tr("Riduttore fotografico suggerito (non disponibile)")
            ),
            value=join_text([item.display_label for item in items], " / "),
            items=items,
        )


def _compatible_reducers(
    reducers: Iterable[FocalReducer],
    telescope_id: str,
) -> tuple[FocalReducer, ...]:
    matches = {
        reducer.id: reducer
        for reducer in reducers
        if reducer.imaging_compatible
        and telescope_id in reducer.compatible_telescope_ids
    }
    return tuple(
        sorted(
            matches.values(),
            key=lambda reducer: (
                reducer.name.casefold(),
                reducer.reduction_factor,
                reducer.id.casefold(),
            ),
        )
    )
