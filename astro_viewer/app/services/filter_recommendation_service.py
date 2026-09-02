"""Choose aperture-compatible owned filters for a target's declared classes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable

from astro_viewer.app.models.equipment import OpticalFilter
from astro_viewer.app.models.filtering import (
    FILTER_CLASS_LABELS,
    TARGET_FILTER_CLASS_MINIMUM_APERTURE_MM,
)
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.localization import tr


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
        catalogue_filters: Iterable[OpticalFilter],
        *,
        telescope_aperture_mm: int,
    ) -> TargetFilterRecommendations:
        if telescope_aperture_mm <= 0:
            return TargetFilterRecommendations()
        filters = tuple(available_filters)
        catalogue = tuple(catalogue_filters)
        primary_classes = _usable_classes(
            target.id,
            _valid_classes(
                target.best_filter_class,
                target.fallback_filter_class,
            ),
            catalogue,
            telescope_aperture_mm,
        )
        color_classes = _usable_classes(
            target.id,
            _valid_classes(target.optional_color_filter_class),
            catalogue,
            telescope_aperture_mm,
        )
        return TargetFilterRecommendations(
            primary=self._select(
                primary_classes,
                filters,
                telescope_aperture_mm,
                available_label=tr("Filtro raccomandato"),
                unavailable_label=tr("Filtro suggerito (non disponibile)"),
            ),
            optional_color=self._select(
                color_classes,
                filters,
                telescope_aperture_mm,
                available_label=tr("Filtro colorato opzionale"),
                unavailable_label=tr("Filtro colorato opzionale (non disponibile)"),
            ),
        )

    @staticmethod
    def _select(
        filter_classes: tuple[str, ...],
        available_filters: tuple[OpticalFilter, ...],
        telescope_aperture_mm: int,
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
                    and _supports_aperture(item, telescope_aperture_mm)
                ),
                key=lambda item: (
                    -_minimum_aperture(item),
                    item.name.casefold(),
                    item.id.casefold(),
                ),
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

        filter_class = filter_classes[0]
        filter_class_label = FILTER_CLASS_LABELS[filter_class]
        return FilterRecommendation(
            applicable=True,
            label=unavailable_label,
            value=filter_class_label,
            filter_class=filter_class,
            filter_class_label=filter_class_label,
        )


def _valid_classes(*values: str) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        filter_class = value.strip().upper()
        if (
            filter_class
            and filter_class in FILTER_CLASS_LABELS
            and filter_class not in result
        ):
            result.append(filter_class)
    return tuple(result)


def _usable_classes(
    target_id: str,
    filter_classes: tuple[str, ...],
    catalogue_filters: tuple[OpticalFilter, ...],
    telescope_aperture_mm: int,
) -> tuple[str, ...]:
    normalized_target_id = target_id.strip().casefold()
    result: list[str] = []
    for filter_class in filter_classes:
        target_minimum = TARGET_FILTER_CLASS_MINIMUM_APERTURE_MM.get(
            (normalized_target_id, filter_class),
            0,
        )
        if telescope_aperture_mm < target_minimum:
            continue
        if any(
            item.filter_class.strip().upper() == filter_class
            and _supports_aperture(item, telescope_aperture_mm)
            for item in catalogue_filters
        ):
            result.append(filter_class)
    return tuple(result)


def _supports_aperture(
    optical_filter: OpticalFilter,
    telescope_aperture_mm: int,
) -> bool:
    return telescope_aperture_mm >= _minimum_aperture(optical_filter)


def _minimum_aperture(optical_filter: OpticalFilter) -> int:
    return optical_filter.minimum_aperture_mm or 0
