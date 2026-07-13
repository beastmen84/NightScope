from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable

from astro_viewer.app.models.equipment import OpticalFilter
from astro_viewer.app.models.filtering import FILTER_CLASS_LABELS
from astro_viewer.app.models.observing import CelestialObject


@dataclass(frozen=True)
class FilterRecommendation:
    applicable: bool = False
    available: bool = False
    label: str = ""
    value: str = ""
    filter_class: str = ""
    filter_class_label: str = ""
    filter_id: str = ""

    def to_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["filterClass"] = self.filter_class
        payload["filterClassLabel"] = self.filter_class_label
        payload["filterId"] = self.filter_id
        return payload


@dataclass(frozen=True)
class TargetFilterRecommendations:
    primary: FilterRecommendation = field(default_factory=FilterRecommendation)
    optional_color: FilterRecommendation = field(default_factory=FilterRecommendation)

    def to_payload(self) -> dict[str, object]:
        return {
            "primary": self.primary.to_payload(),
            "optionalColor": self.optional_color.to_payload(),
        }


class FilterRecommendationService:
    """Selects owned filters without modifying equipment or NSOM scores."""

    def recommend(
        self,
        target: CelestialObject,
        available_filters: Iterable[OpticalFilter],
    ) -> TargetFilterRecommendations:
        filters = tuple(available_filters)
        primary_classes = _valid_classes(
            target.best_filter_class,
            target.fallback_filter_class,
        )
        color_classes = _valid_classes(target.optional_color_filter_class)
        return TargetFilterRecommendations(
            primary=self._select(
                primary_classes,
                filters,
                available_label="Filtro raccomandato",
                unavailable_label="Filtro suggerito (non disponibile)",
            ),
            optional_color=self._select(
                color_classes,
                filters,
                available_label="Filtro colorato opzionale",
                unavailable_label="Filtro colorato opzionale (non disponibile)",
            ),
        )

    @staticmethod
    def _select(
        filter_classes: tuple[str, ...],
        available_filters: tuple[OpticalFilter, ...],
        *,
        available_label: str,
        unavailable_label: str,
    ) -> FilterRecommendation:
        if not filter_classes:
            return FilterRecommendation()
        for filter_class in filter_classes:
            matches = sorted(
                (
                    item
                    for item in available_filters
                    if item.filter_class.strip().upper() == filter_class
                ),
                key=lambda item: (item.name.casefold(), item.id.casefold()),
            )
            if not matches:
                continue
            selected = matches[0]
            return FilterRecommendation(
                applicable=True,
                available=True,
                label=available_label,
                value=selected.name,
                filter_class=filter_class,
                filter_class_label=FILTER_CLASS_LABELS[filter_class],
                filter_id=selected.id,
            )

        labels = tuple(FILTER_CLASS_LABELS[item] for item in filter_classes)
        return FilterRecommendation(
            applicable=True,
            label=unavailable_label,
            value=" / ".join(labels),
            filter_class=filter_classes[0],
            filter_class_label=labels[0],
        )


def _valid_classes(*values: str) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        filter_class = value.strip().upper()
        if (
            filter_class
            and filter_class != "COLOR_UNSPECIFIED"
            and filter_class in FILTER_CLASS_LABELS
            and filter_class not in result
        ):
            result.append(filter_class)
    return tuple(result)
