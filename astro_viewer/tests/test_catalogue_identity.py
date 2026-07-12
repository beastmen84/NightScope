from __future__ import annotations

from astro_viewer.app.viewmodels.app_controller import (
    CATALOGUE_ALL_FILTER,
    AppController,
)


def test_catalogue_filter_projects_designation_without_duplicating_object() -> None:
    controller = AppController.__new__(AppController)
    item = controller._catalogue_item_from_record(_multi_catalogue_record())
    controller._catalogue_objects = [item]
    controller._catalogue_identifier_index = controller._build_catalogue_identifier_index(
        controller._catalogue_objects
    )
    controller._catalogue_search_query = ""
    controller._catalogue_filters = _filters()
    controller._catalogue_visible_this_month_only = False
    controller._catalogue_year = 2026
    controller._catalogue_selected_month = 7
    controller._catalogue_observability_map = lambda: {}
    controller._catalogue_visibility_map = lambda: {}
    controller._has_valid_location = lambda: False

    all_items = controller._filtered_catalogue_objects()
    assert len(all_items) == 1
    assert all_items[0]["object_id"] == "messier-M31"
    assert all_items[0]["catalogue"] == "Messier"
    assert all_items[0]["catalogue_id"] == "M31"
    assert controller._catalogue_option_values("catalogue") == ["Caldwell", "Messier"]

    controller._catalogue_filters["catalogue"] = "Caldwell"
    caldwell_items = controller._filtered_catalogue_objects()
    assert len(caldwell_items) == 1
    assert caldwell_items[0]["object_id"] == "messier-M31"
    assert caldwell_items[0]["catalogue"] == "Caldwell"
    assert caldwell_items[0]["catalogue_id"] == "C23"


def test_catalogue_identifier_index_resolves_all_designations_to_same_object() -> None:
    controller = AppController.__new__(AppController)
    item = controller._catalogue_item_from_record(_multi_catalogue_record())
    controller._catalogue_objects = [item]
    controller._catalogue_identifier_index = controller._build_catalogue_identifier_index(
        controller._catalogue_objects
    )

    resolved = {
        controller._catalogue_item_for_object_id(identifier)["object_id"]
        for identifier in ("messier-M31", "M31", "Messier-M31", "C23", "Caldwell-C23")
    }
    assert resolved == {"messier-M31"}


def test_catalogue_search_matches_secondary_designation_once() -> None:
    controller = AppController.__new__(AppController)
    item = controller._catalogue_item_from_record(_multi_catalogue_record())
    controller._catalogue_objects = [item]
    controller._catalogue_identifier_index = controller._build_catalogue_identifier_index(
        controller._catalogue_objects
    )
    controller._catalogue_search_query = "c23"
    controller._catalogue_filters = _filters()
    controller._catalogue_visible_this_month_only = False
    controller._catalogue_year = 2026
    controller._catalogue_selected_month = 7
    controller._catalogue_observability_map = lambda: {}
    controller._catalogue_visibility_map = lambda: {}
    controller._has_valid_location = lambda: False

    result = controller._filtered_catalogue_objects()
    assert len(result) == 1
    assert result[0]["object_id"] == "messier-M31"


def _filters() -> dict[str, str]:
    return {
        "catalogue": CATALOGUE_ALL_FILTER,
        "type": CATALOGUE_ALL_FILTER,
        "constellation": CATALOGUE_ALL_FILTER,
        "observation_type": CATALOGUE_ALL_FILTER,
    }


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
        "catalogues": ["Messier", "Caldwell"],
        "designations": [
            {
                "catalogue": "Messier",
                "designation": "M31",
                "sort_index": 31,
                "is_primary": True,
            },
            {
                "catalogue": "Caldwell",
                "designation": "C23",
                "sort_index": 23,
                "is_primary": False,
            },
        ],
    }
