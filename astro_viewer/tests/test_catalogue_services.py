from __future__ import annotations

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.catalogue_detail_service import (
    CATALOGUE_SOURCE,
    CatalogueDetailService,
)
from astro_viewer.app.services.catalogue_query_service import (
    CATALOGUE_ALL_FILTER,
    CatalogueQueryService,
    build_catalogue_identifier_index,
    catalogue_item_observability,
)
from astro_viewer.app.services.catalogue_records import catalogue_item_from_record


def test_query_service_filters_secondary_designation_without_qt_state() -> None:
    item = catalogue_item_from_record(_multi_catalogue_record())
    filters = {
        "catalogue": "Secondary",
        "type": CATALOGUE_ALL_FILTER,
        "constellation": CATALOGUE_ALL_FILTER,
        "observation_type": CATALOGUE_ALL_FILTER,
    }

    result = CatalogueQueryService(None).filtered_objects(
        [item],
        search_query="s31",
        filters=filters,
        visible_this_month_only=False,
        visibility={},
        observability={},
        has_location=False,
        selected_month=9,
        year=2026,
    )

    assert len(result) == 1
    assert result[0]["object_id"] == "messier-M31"
    assert result[0]["catalogue"] == "Secondary"
    assert result[0]["catalogue_id"] == "S31"


def test_identifier_and_observability_queries_are_framework_independent() -> None:
    item = catalogue_item_from_record(_multi_catalogue_record())
    index = build_catalogue_identifier_index([item])

    assert index["secondary-s31"] is item
    assert index["m31"] is item
    assert catalogue_item_observability(
        item,
        ObserverLocation(
            "Rome",
            "Italy",
            41.9,
            12.5,
            "Europe/Rome",
        ),
    ) == {
        "is_geometrically_observable": True,
        "is_usefully_observable": True,
    }


def test_detail_service_builds_catalogue_object_without_controller_state() -> None:
    item = catalogue_item_from_record(_multi_catalogue_record())

    detail = CatalogueDetailService().detail_object(
        item,
        solar_system_source=None,
        apply_content=lambda value: value,
    )

    assert detail.id == "messier-M31"
    assert detail.name.startswith("M31")
    assert detail.detail_source == CATALOGUE_SOURCE
    assert detail.max_angular_size_deg == 3.17


def _multi_catalogue_record() -> dict:
    return {
        "object_id": "messier-M31",
        "name": "Andromeda Galaxy",
        "object_type": "Spiral galaxy",
        "constellation": "Andromeda",
        "magnitude": 3.4,
        "ra": "00h 42m 44.3s",
        "dec": "+41 deg 16 min 09 sec",
        "apparent_size": "3.17 deg x 1 deg",
        "max_angular_size_deg": 3.17,
        "recommended_observation_type": "WideField",
        "description": "Fixture",
        "primary_catalogue": "Messier",
        "primary_designation": "M31",
        "primary_sort_index": 31,
        "catalogues": ["Messier", "Secondary"],
        "designations": [
            {
                "catalogue": "Messier",
                "designation": "M31",
                "sort_index": 31,
                "is_primary": True,
            },
            {
                "catalogue": "Secondary",
                "designation": "S31",
                "sort_index": 31,
                "is_primary": False,
            },
        ],
    }
