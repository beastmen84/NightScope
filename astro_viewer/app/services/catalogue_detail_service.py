"""Construct catalogue detail targets without mutating controller state."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace

from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.catalogue_presentation import (
    catalogue_constellation_label,
    catalogue_display_name,
)
from astro_viewer.app.services.catalogue_query_service import (
    CATALOGUE_ALL_FILTER,
    catalogue_item_for_catalogue,
    catalogue_label,
)
from astro_viewer.app.services.catalogue_records import (
    format_catalogue_number,
    is_solar_system_catalogue_item,
)
from astro_viewer.app.services.localization import content_text, presentation_text, tr


CATALOGUE_SOURCE = "catalogue"


class CatalogueDetailService:
    """Builds catalogue detail objects and metadata without controller state."""

    def detail_object(
        self,
        item: dict,
        *,
        solar_system_source: CelestialObject | None,
        apply_content: Callable[[CelestialObject], CelestialObject],
    ) -> CelestialObject:
        if is_solar_system_catalogue_item(item):
            return self._solar_system_detail_object(
                item,
                solar_system_source=solar_system_source,
                apply_content=apply_content,
            )
        name = content_text(
            "catalogue_objects",
            str(item["object_id"]),
            "name",
            item["name"],
        )
        display_name = catalogue_display_name(str(item["catalogue_id"]), name)
        visibility_class = tr(
            "Catalogo {catalogue}",
            catalogue=catalogue_label(str(item["catalogue"])),
        )
        return apply_content(
            CelestialObject(
                id=item["object_id"],
                name=display_name,
                object_type=item["type"],
                image=SkyfieldAstronomyEngine._catalogue_image(
                    str(item["object_id"]),
                    str(item["catalogue_id"]),
                    str(item["type"]),
                ),
                magnitude=format_catalogue_number(item["magnitude"]),
                distance=tr("n/d"),
                max_altitude=tr("n/d"),
                direction=tr("n/d"),
                best_time=tr("n/d"),
                observing_window=tr("n/d"),
                notes=content_text(
                    "catalogue_objects",
                    str(item["object_id"]),
                    "description",
                    item["description"],
                ),
                recommended_setup="",
                visibility_class=visibility_class,
                azimuth=tr("n/d"),
                time_above_horizon=tr("n/d"),
                visible=True,
                score=0,
                score_label=tr("n/d"),
                difficulty=tr("n/d"),
                apparent_size=item["apparent_size"],
                max_angular_size_deg=item["max_angular_size_deg"],
                recommended_observation_type=(
                    item["recommended_observation_type"]
                ),
                best_filter_class=item.get("best_filter_class", ""),
                fallback_filter_class=item.get("fallback_filter_class", ""),
                optional_color_filter_class=item.get(
                    "optional_color_filter_class",
                    "",
                ),
                imaging_reducer_recommended=bool(
                    item.get("imaging_reducer_recommended")
                ),
                detail_source=CATALOGUE_SOURCE,
            )
        )

    def metadata(self, catalogue_item: Mapping[str, object] | None) -> dict:
        if not catalogue_item:
            return {}
        constellation = str(catalogue_item.get("constellation") or "")
        if is_solar_system_catalogue_item(catalogue_item) and not constellation:
            constellation = "—"
        return {
            "catalogue": str(catalogue_item.get("catalogue") or ""),
            "catalogueLabel": catalogue_label(
                str(catalogue_item.get("catalogue") or "")
            ),
            "catalogueId": str(catalogue_item.get("catalogue_id") or ""),
            "constellation": constellation,
            "constellationLabel": (
                constellation
                if constellation == "—"
                else catalogue_constellation_label(constellation)
            ),
            "rightAscension": str(
                catalogue_item.get("right_ascension") or ""
            ),
            "declination": str(catalogue_item.get("declination") or ""),
            "maxAngularSizeLabel": presentation_text(
                catalogue_item.get("max_angular_size_label", "")
            ),
            "catalogueDesignations": list(
                catalogue_item.get("designations", [])
            ),
            "catalogueDesignationLabels": list(
                catalogue_item.get("designation_labels", [])
            ),
        }

    def name_for_detail(
        self,
        catalogue_item: dict | None,
        *,
        active_catalogue_filter: str = CATALOGUE_ALL_FILTER,
    ) -> str:
        if catalogue_item is None:
            return tr("locale")
        if active_catalogue_filter != CATALOGUE_ALL_FILTER:
            catalogue_item = (
                catalogue_item_for_catalogue(
                    catalogue_item,
                    active_catalogue_filter,
                )
                or catalogue_item
            )
        return catalogue_label(
            str(catalogue_item.get("catalogue") or "")
        ) or tr("locale")

    def _solar_system_detail_object(
        self,
        item: dict,
        *,
        solar_system_source: CelestialObject | None,
        apply_content: Callable[[CelestialObject], CelestialObject],
    ) -> CelestialObject:
        visibility_class = tr(
            "Catalogo {catalogue}",
            catalogue=catalogue_label(str(item["catalogue"])),
        )
        if solar_system_source:
            return replace(
                solar_system_source,
                visibility_class=visibility_class,
                recommended_setup="",
                score=0,
                score_label=tr("n/d"),
                difficulty=tr("n/d"),
                setup_options=[],
                equipment_explanation="",
                best_filter_class=item.get("best_filter_class", ""),
                fallback_filter_class=item.get("fallback_filter_class", ""),
                optional_color_filter_class=item.get(
                    "optional_color_filter_class",
                    "",
                ),
                imaging_reducer_recommended=False,
                detail_source=CATALOGUE_SOURCE,
            )
        return apply_content(
            CelestialObject(
                id=item["object_id"],
                name=presentation_text(item["name"], strip=True),
                object_type=item["type"],
                image=str(item.get("image") or "resources/images/m13.svg"),
                magnitude="",
                distance=tr("n/d"),
                max_altitude=tr("n/d"),
                direction=tr("n/d"),
                best_time=tr("n/d"),
                observing_window=tr("n/d"),
                notes=item["description"],
                recommended_setup="",
                visibility_class=visibility_class,
                azimuth=tr("n/d"),
                time_above_horizon=tr("n/d"),
                visible=True,
                score=0,
                score_label=tr("n/d"),
                difficulty=tr("n/d"),
                apparent_size="",
                max_angular_size_deg=None,
                recommended_observation_type=(
                    item["recommended_observation_type"]
                ),
                best_filter_class=item.get("best_filter_class", ""),
                fallback_filter_class=item.get("fallback_filter_class", ""),
                optional_color_filter_class=item.get(
                    "optional_color_filter_class",
                    "",
                ),
                imaging_reducer_recommended=False,
                detail_source=CATALOGUE_SOURCE,
            )
        )


def is_catalogue_detail_object(item: CelestialObject) -> bool:
    return item.detail_source == CATALOGUE_SOURCE
