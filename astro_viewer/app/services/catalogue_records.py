from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Protocol

from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.models.filtering import SOLAR_SYSTEM_FILTER_PREFERENCES
from astro_viewer.app.services.localization import (
    format_number,
    presentation_text,
    tr,
)


SOLAR_SYSTEM_CATALOGUE = "Sistema Solare"
RECOMMENDATION_EDITABLE_CATALOGUES = frozenset({"Messier", "Caldwell", "NGC"})


class SolarSystemBodyConfig(Protocol):
    object_id: str
    name: object
    object_type: str
    image: str


def catalogue_item_from_record(row: dict) -> dict:
    object_id = str(row["object_id"])
    recommendation_enabled_by_default = bool(
        row.get("recommendation_enabled_by_default", True)
    )
    primary_catalogue = str(row.get("primary_catalogue") or "")
    primary_designation = str(row.get("primary_designation") or object_id)
    designations = [dict(item) for item in row.get("designations", [])]
    catalogues = [str(item) for item in row.get("catalogues", [])]
    recommendation_editable = bool(
        RECOMMENDATION_EDITABLE_CATALOGUES.intersection(catalogues)
    )
    designation_labels = [
        f"{item['catalogue']} {item['designation']}".strip()
        for item in designations
    ]
    search_terms = " ".join(
        (
            str(row.get("name") or ""),
            *designation_labels,
            *(str(item.get("designation") or "") for item in designations),
        )
    ).strip()
    return {
        "catalogue": primary_catalogue,
        "object_id": object_id,
        "id": object_id,
        "catalogue_id": primary_designation,
        "catalogues": catalogues,
        "designations": designations,
        "designation_labels": designation_labels,
        "name": row["name"] or "",
        "type": row["object_type"] or "",
        "constellation": row["constellation"] or "",
        "magnitude": row["magnitude"],
        "magnitude_label": format_catalogue_number(row["magnitude"]),
        "right_ascension": row["ra"] or "",
        "declination": row["dec"] or "",
        "apparent_size": row["apparent_size"] or "",
        "max_angular_size_deg": row["max_angular_size_deg"],
        "max_angular_size_label": format_catalogue_angle(
            row["max_angular_size_deg"]
        ),
        "recommended_observation_type": (
            row["recommended_observation_type"] or ""
        ),
        "best_filter_class": row.get("best_filter_class") or "",
        "fallback_filter_class": row.get("fallback_filter_class") or "",
        "optional_color_filter_class": (
            row.get("optional_color_filter_class") or ""
        ),
        "imaging_reducer_recommended": bool(
            row.get("imaging_reducer_recommended")
        ),
        "recommendation_enabled_by_default": recommendation_enabled_by_default,
        "recommendation_enabled": bool(
            row.get(
                "recommendation_enabled",
                recommendation_enabled_by_default,
            )
        ),
        "recommendation_editable": recommendation_editable,
        "description": row["description"] or "",
        "search_terms": search_terms,
        "catalogue_sort_index": row.get("primary_sort_index"),
    }


def solar_system_catalogue_objects(
    object_descriptions: Mapping[str, dict],
) -> list[dict]:
    return [
        catalogue_item_from_solar_system(
            config,
            sort_index,
            object_descriptions,
        )
        for sort_index, config in enumerate(
            SkyfieldAstronomyEngine.BODY_CONFIGS,
            start=1,
        )
    ]


def catalogue_item_from_solar_system(
    config: SolarSystemBodyConfig,
    sort_index: int,
    object_descriptions: Mapping[str, dict],
) -> dict:
    observation_type = ""
    if config.object_id == "moon":
        observation_type = "General"
    elif config.object_type == "Pianeta":
        observation_type = "HighMagnification"
    description = object_descriptions.get(config.object_id, {})
    best_filter_class, fallback_filter_class, optional_color_filter_class = (
        SOLAR_SYSTEM_FILTER_PREFERENCES.get(config.object_id, ("", "", ""))
    )
    display_id = f"S{sort_index}"
    return {
        "catalogue": SOLAR_SYSTEM_CATALOGUE,
        "object_id": config.object_id,
        "id": config.object_id,
        "catalogue_id": display_id,
        "catalogues": [SOLAR_SYSTEM_CATALOGUE],
        "designations": [
            {
                "catalogue": SOLAR_SYSTEM_CATALOGUE,
                "designation": display_id,
                "sort_index": sort_index,
                "is_primary": True,
            }
        ],
        "designation_labels": [f"{SOLAR_SYSTEM_CATALOGUE} {display_id}"],
        "name": config.name,
        "type": config.object_type,
        "constellation": "",
        "magnitude": None,
        "magnitude_label": "",
        "right_ascension": "",
        "declination": "",
        "apparent_size": "",
        "max_angular_size_deg": None,
        "max_angular_size_label": "",
        "recommended_observation_type": observation_type,
        "best_filter_class": best_filter_class,
        "fallback_filter_class": fallback_filter_class,
        "optional_color_filter_class": optional_color_filter_class,
        "imaging_reducer_recommended": False,
        "recommendation_enabled_by_default": True,
        "recommendation_enabled": True,
        "recommendation_editable": False,
        "description": presentation_text(
            description.get("short_description", ""),
            strip=True,
        ),
        "image": config.image,
        "solar_system_body_id": config.object_id,
        "search_terms": solar_system_search_terms(
            config.object_id,
            str(config.name),
            display_id,
        ),
        "catalogue_sort_index": sort_index,
    }


def solar_system_search_terms(
    object_id: str,
    name: str,
    display_id: str,
) -> str:
    english_names = {
        "sun": "Sun",
        "moon": "Moon",
        "mercury": "Mercury",
        "venus": "Venus",
        "mars": "Mars",
        "jupiter": "Jupiter",
        "saturn": "Saturn",
        "uranus": "Uranus",
        "neptune": "Neptune",
    }
    return " ".join(
        (
            display_id,
            f"solar-{object_id}",
            object_id,
            name,
            english_names.get(object_id, ""),
        )
    ).strip()


def catalogue_sort_key(item: dict) -> tuple[str, int, str]:
    catalogue_id = str(item.get("catalogue_id", ""))
    match = re.search(r"\d+", catalogue_id)
    explicit_sort_index = item.get("catalogue_sort_index")
    if explicit_sort_index is not None:
        numeric_id = int(explicit_sort_index)
    elif match:
        numeric_id = int(match.group(0))
    else:
        numeric_id = 999_999
    return (
        str(item.get("catalogue", "")).casefold(),
        numeric_id,
        catalogue_id.casefold(),
    )


def format_catalogue_number(value: object) -> str:
    if value is None:
        return tr("n/d")
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    normalized = f"{number:g}"
    decimals = (
        len(normalized.partition(".")[2])
        if "e" not in normalized.lower()
        else 2
    )
    return format_number(number, decimals=decimals)


def format_catalogue_angle(value: object) -> str:
    if value is None:
        return tr("n/d")
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    normalized = f"{number:g}"
    decimals = (
        len(normalized.partition(".")[2])
        if "e" not in normalized.lower()
        else 2
    )
    return tr(
        "{value}°",
        value=format_number(number, decimals=decimals),
    )


def is_solar_system_catalogue_item(item: Mapping[str, object]) -> bool:
    return str(item.get("catalogue", "")) == SOLAR_SYSTEM_CATALOGUE
