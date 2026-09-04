"""Load, index, filter, and project physical catalogue records without Qt."""

from __future__ import annotations

import re
from collections.abc import Mapping

from astro_viewer.app.astronomy.coordinates import parse_dec_degrees
from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.astronomy.skyfield_engine import DEEP_SKY_USEFUL_ALTITUDE_DEG
from astro_viewer.app.database.catalogue_repository import CatalogueRepository
from astro_viewer.app.services.catalogue_presentation import (
    catalogue_constellation_label,
    catalogue_object_type_label,
    catalogue_observation_type_label,
)
from astro_viewer.app.services.catalogue_records import (
    SOLAR_SYSTEM_CATALOGUE,
    catalogue_item_from_record,
    catalogue_sort_key,
    is_editorial_placeholder,
    solar_system_catalogue_objects,
)
from astro_viewer.app.services.localization import (
    content_text,
    format_month_year,
    presentation_text,
    render_text,
    tr,
)


CATALOGUE_ALL_FILTER = "__all__"
CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG = DEEP_SKY_USEFUL_ALTITUDE_DEG


class CatalogueQueryService:
    """Loads, indexes, projects and filters catalogue records without Qt state."""

    def __init__(
        self,
        catalogue_repository: CatalogueRepository | None,
    ) -> None:
        self._catalogue_repository = catalogue_repository

    def load_objects(
        self,
        object_descriptions: Mapping[str, dict],
    ) -> list[dict]:
        if self._catalogue_repository is None:
            raise RuntimeError("Catalogue repository is not configured.")
        objects = []
        for row in self._catalogue_repository.list_objects():
            item = catalogue_item_from_record(row)
            editorial = object_descriptions.get(str(item["object_id"])) or {}
            short_description = presentation_text(
                editorial.get("short_description", ""),
                strip=True,
            )
            if short_description and is_editorial_placeholder(item["description"]):
                item["description"] = short_description
            objects.append(item)
        objects.extend(solar_system_catalogue_objects(object_descriptions))
        return sorted(objects, key=catalogue_sort_key)

    def filtered_objects(
        self,
        objects: list[dict],
        *,
        search_query: str,
        filters: Mapping[str, str],
        visible_this_month_only: bool,
        visibility: Mapping[str, bool],
        observability: Mapping[str, Mapping[str, bool | None]],
        has_location: bool,
        selected_month: int,
        year: int,
    ) -> list[dict]:
        query = search_query.casefold()
        filtered = objects
        if query:
            filtered = [
                item
                for item in filtered
                if catalogue_query_matches_designation(item, query)
                or query == str(item.get("object_id", "")).casefold()
                or query in render_text(item["name"]).casefold()
                or query
                in render_text(
                    content_text(
                        "catalogue_objects",
                        str(item.get("object_id", "")),
                        "name",
                        item.get("name", ""),
                    )
                ).casefold()
                or query in str(item.get("search_terms", "")).casefold()
            ]

        catalogue_filter = filters.get("catalogue", CATALOGUE_ALL_FILTER)
        if catalogue_filter != CATALOGUE_ALL_FILTER:
            filtered = [
                projected
                for item in filtered
                for projected in catalogue_items_for_catalogue(
                    item,
                    catalogue_filter,
                )
            ]

        for filter_name, field_name in (
            ("type", "type"),
            ("constellation", "constellation"),
            ("observation_type", "recommended_observation_type"),
        ):
            value = filters.get(filter_name, CATALOGUE_ALL_FILTER)
            if value != CATALOGUE_ALL_FILTER:
                filtered = [
                    item for item in filtered if item[field_name] == value
                ]

        projected_objects = [
            catalogue_item_with_visibility(
                item,
                visibility=visibility,
                observability=observability,
                visible_this_month_only=visible_this_month_only,
                has_location=has_location,
                selected_month=selected_month,
                year=year,
            )
            for item in filtered
        ]
        if visible_this_month_only:
            projected_objects = [
                item for item in projected_objects if item["visible_this_month"]
            ]
        if query:
            return sorted(
                projected_objects,
                key=lambda item: catalogue_search_sort_key(item, query),
            )
        return sorted(projected_objects, key=catalogue_sort_key)


def catalogue_search_sort_key(
    item: dict,
    query: str,
) -> tuple[int, str, int, str]:
    candidates = [
        str(item.get("catalogue_id") or ""),
        str(item.get("name") or ""),
        str(item.get("object_id") or ""),
        *(
            str(designation.get("designation") or "")
            for designation in item.get("designations", [])
        ),
    ]
    normalized = [candidate.casefold() for candidate in candidates if candidate]
    compact_query = compact_catalogue_designation(query)
    compact_candidates = [
        compact_catalogue_designation(candidate) for candidate in normalized
    ]
    if query in normalized or compact_query in compact_candidates:
        match_rank = 0
    elif any(candidate.startswith(query) for candidate in normalized) or any(
        candidate.startswith(compact_query) for candidate in compact_candidates
    ):
        match_rank = 1
    else:
        match_rank = 2
    catalogue, numeric_id, catalogue_id = catalogue_sort_key(item)
    return match_rank, catalogue, numeric_id, catalogue_id


def catalogue_query_matches_designation(item: dict, query: str) -> bool:
    designations = [
        str(item.get("catalogue_id") or ""),
        *(
            str(designation.get("designation") or "")
            for designation in item.get("designations", [])
        ),
    ]
    if any(query in designation.casefold() for designation in designations):
        return True
    compact_query = compact_catalogue_designation(query)
    return bool(compact_query) and any(
        compact_catalogue_designation(designation).startswith(compact_query)
        for designation in designations
        if designation
    )


def compact_catalogue_designation(value: str) -> str:
    return re.sub(r"[\s_-]+", "", value.casefold())


def catalogue_item_for_catalogue(item: dict, catalogue: str) -> dict | None:
    projected = catalogue_items_for_catalogue(item, catalogue)
    return projected[0] if projected else None


def catalogue_items_for_catalogue(item: dict, catalogue: str) -> list[dict]:
    normalized = catalogue.strip().casefold()
    result = []
    for designation in item.get("designations", []):
        if (
            str(designation.get("catalogue", "")).strip().casefold()
            != normalized
        ):
            continue
        projected = dict(item)
        projected["catalogue"] = str(designation.get("catalogue") or "")
        projected["catalogue_id"] = str(designation.get("designation") or "")
        projected["catalogue_sort_index"] = designation.get("sort_index")
        result.append(projected)
    return result


def catalogue_item_for_designation(
    item: dict,
    catalogue: str,
    designation: str,
) -> dict | None:
    normalized_catalogue = catalogue.strip().casefold()
    normalized_designation = designation.strip().casefold()
    for projected in catalogue_items_for_catalogue(item, catalogue):
        if (
            str(projected.get("catalogue", "")).strip().casefold()
            == normalized_catalogue
            and str(projected.get("catalogue_id", "")).strip().casefold()
            == normalized_designation
        ):
            return projected
    return None


def catalogue_item_with_visibility(
    item: dict,
    *,
    visibility: Mapping[str, bool],
    observability: Mapping[str, Mapping[str, bool | None]],
    visible_this_month_only: bool,
    has_location: bool,
    selected_month: int,
    year: int,
) -> dict:
    object_id = str(item.get("object_id", ""))
    visible_value: bool | None = (
        bool(visibility[object_id])
        if visible_this_month_only and has_location and object_id in visibility
        else None
    )
    observability_values = observability.get(object_id, {}) if has_location else {}
    geometric_value = observability_values.get("is_geometrically_observable")
    useful_value = observability_values.get("is_usefully_observable")
    data = dict(item)
    data["catalogue_label"] = catalogue_label(str(item.get("catalogue", "")))
    if item.get("solar_system_body_id"):
        data["name"] = presentation_text(item.get("name", ""), strip=True)
        data["description"] = presentation_text(
            item.get("description", ""),
            strip=True,
        )
    else:
        data["name"] = content_text(
            "catalogue_objects",
            object_id,
            "name",
            item.get("name", ""),
        )
        data["description"] = content_text(
            "catalogue_objects",
            object_id,
            "description",
            item.get("description", ""),
        )
    data["constellation_label"] = catalogue_constellation_label(
        str(item.get("constellation", ""))
    )
    data["is_geometrically_observable"] = geometric_value is True
    data["is_geometrically_observable_known"] = geometric_value is not None
    data["is_geometrically_observable_label"] = catalogue_boolean_label(
        geometric_value
    )
    data["is_usefully_observable"] = useful_value is True
    data["is_usefully_observable_known"] = useful_value is not None
    data["is_usefully_observable_label"] = catalogue_boolean_label(useful_value)
    data["observable"] = data["is_usefully_observable"]
    data["observable_known"] = data["is_usefully_observable_known"]
    data["observable_label"] = data["is_usefully_observable_label"]
    data["visible_this_month"] = visible_value is True
    data["visible_this_month_label"] = catalogue_boolean_label(visible_value)
    data["visibility_month_label"] = format_month_year(selected_month, year)
    data["type_label"] = catalogue_object_type_label(str(item.get("type", "")))
    data["recommended_observation_type_label"] = (
        catalogue_observation_type_label(
            str(item.get("recommended_observation_type", ""))
        )
    )
    return data


def catalogue_option_values(objects: list[dict], field_name: str) -> list[str]:
    if field_name == "catalogue":
        values = {
            str(catalogue).strip()
            for item in objects
            for catalogue in item.get("catalogues", [])
        }
    else:
        values = {str(item.get(field_name, "")).strip() for item in objects}
    return sorted((value for value in values if value), key=str.casefold)


def catalogue_label(value: str) -> str:
    return tr("Sistema Solare") if value == SOLAR_SYSTEM_CATALOGUE else value


def normalize_catalogue_filter_name(filter_name: str) -> str:
    normalized = filter_name.strip().casefold()
    aliases = {
        "catalogue": "catalogue",
        "catalog": "catalogue",
        "type": "type",
        "object_type": "type",
        "constellation": "constellation",
        "observation_type": "observation_type",
        "recommended_observation_type": "observation_type",
    }
    return aliases.get(normalized, "")


def build_catalogue_identifier_index(objects: list[dict]) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for item in objects:
        identifiers = {
            str(item.get("object_id") or "").strip(),
            str(item.get("id") or "").strip(),
            str(item.get("catalogue_id") or "").strip(),
        }
        for designation in item.get("designations", []):
            catalogue = str(designation.get("catalogue") or "").strip()
            value = str(designation.get("designation") or "").strip()
            identifiers.add(value)
            if catalogue and value:
                identifiers.add(f"{catalogue}-{value}")
        for identifier in identifiers:
            if identifier:
                index.setdefault(identifier.casefold(), item)
    return index


def catalogue_item_observability(
    item: dict,
    location: ObserverLocation | None,
) -> dict[str, bool | None]:
    if not isinstance(location, ObserverLocation) or item.get(
        "solar_system_body_id"
    ):
        return {
            "is_geometrically_observable": None,
            "is_usefully_observable": None,
        }
    try:
        dec_degrees = parse_dec_degrees(
            str(item.get("dec") or item.get("declination") or "")
        )
    except ValueError:
        return {
            "is_geometrically_observable": None,
            "is_usefully_observable": None,
        }
    theoretical_max_altitude = 90.0 - abs(location.latitude - dec_degrees)
    return {
        "is_geometrically_observable": theoretical_max_altitude > 0.0,
        "is_usefully_observable": (
            theoretical_max_altitude
            >= CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG
        ),
    }


def catalogue_observability_map(
    objects: list[dict],
    location: ObserverLocation | None,
) -> dict[str, dict[str, bool | None]]:
    observability = {}
    for item in objects:
        object_id = str(item.get("object_id", ""))
        if object_id:
            observability[object_id] = catalogue_item_observability(
                item,
                location,
            )
    return observability


def catalogue_boolean_label(value: bool | None) -> str:
    if value is True:
        return tr("Sì")
    if value is False:
        return tr("No")
    return "—"


def catalogue_visibility_cache_key(
    location: ObserverLocation | None,
    year: int,
    month: int,
) -> tuple[float, float, str, int, int, float]:
    if not isinstance(location, ObserverLocation):
        return (
            0.0,
            0.0,
            "",
            year,
            month,
            CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
        )
    return (
        round(location.latitude, 5),
        round(location.longitude, 5),
        location.timezone,
        year,
        month,
        CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
    )


def catalogue_observability_cache_key(
    location: ObserverLocation | None,
) -> tuple[float, float, str, float]:
    if not isinstance(location, ObserverLocation):
        return (0.0, 0.0, "", CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG)
    return (
        round(location.latitude, 5),
        round(location.longitude, 5),
        location.timezone,
        CATALOGUE_VISIBILITY_ALTITUDE_THRESHOLD_DEG,
    )
