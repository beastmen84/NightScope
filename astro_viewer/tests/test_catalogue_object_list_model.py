from __future__ import annotations

from unittest.mock import patch

from PySide6.QtCore import Qt

from astro_viewer.app.viewmodels.catalogue_object_list_model import (
    CatalogueObjectListModel,
)


def test_catalogue_model_updates_only_rows_for_the_same_physical_target() -> None:
    model = CatalogueObjectListModel()
    model.replace_items(
        [
            {
                "object_id": "ngc-NGC6",
                "catalogue_id": "NGC 6",
                "recommendation_enabled": False,
            },
            {
                "object_id": "ngc-NGC6",
                "catalogue_id": "NGC 20",
                "recommendation_enabled": False,
            },
            {
                "object_id": "ngc-NGC7",
                "catalogue_id": "NGC 7",
                "recommendation_enabled": False,
            },
        ]
    )
    changed_ranges: list[tuple[int, int]] = []
    model.dataChanged.connect(
        lambda first, last, _roles: changed_ranges.append(
            (first.row(), last.row())
        )
    )

    assert model.update_recommendation_enabled("NGC-ngc6", True) is True

    assert model.rowCount() == 3
    assert changed_ranges == [(0, 1)]
    assert model.data(
        model.index(0, 0),
        int(CatalogueObjectListModel.ItemDataRole),
    )["recommendation_enabled"] is True
    assert model.data(
        model.index(1, 0),
        int(CatalogueObjectListModel.ItemDataRole),
    )["recommendation_enabled"] is True
    assert model.data(
        model.index(2, 0),
        int(CatalogueObjectListModel.ItemDataRole),
    )["recommendation_enabled"] is False
    assert model.data(
        model.index(0, 0),
        int(Qt.ItemDataRole.DisplayRole),
    )["catalogue_id"] == "NGC 6"


def test_catalogue_model_does_not_emit_for_an_unchanged_value() -> None:
    model = CatalogueObjectListModel()
    model.replace_items(
        [
            {
                "object_id": "messier-M31",
                "recommendation_enabled": True,
            }
        ]
    )
    emissions: list[object] = []
    model.dataChanged.connect(lambda *_args: emissions.append(object()))

    assert model.update_recommendation_enabled("messier-M31", True) is False
    assert emissions == []


def test_catalogue_model_renders_only_rows_requested_by_the_view() -> None:
    model = CatalogueObjectListModel()
    rows = [
        {
            "object_id": f"ngc-NGC{number}",
            "recommendation_enabled": False,
        }
        for number in range(100)
    ]

    with patch(
        "astro_viewer.app.viewmodels.catalogue_object_list_model.render_payload",
        side_effect=lambda payload: dict(payload),
    ) as render:
        model.replace_items(rows)
        render.assert_not_called()

        first_index = model.index(0, 0)
        assert model.data(first_index)["object_id"] == "ngc-NGC0"
        assert model.data(first_index)["object_id"] == "ngc-NGC0"

    assert render.call_count == 1


def test_bulk_actions_deduplicate_aliases_and_skip_locked_rows() -> None:
    model = CatalogueObjectListModel()
    model.replace_items(
        [
            {
                "object_id": "sun",
                "catalogue_id": "S1",
                "recommendation_editable": False,
                "recommendation_enabled": True,
            },
            {
                "object_id": "messier-M31",
                "catalogue_id": "M31",
                "recommendation_editable": True,
                "recommendation_enabled": True,
            },
            {
                "object_id": "ngc-NGC6",
                "catalogue_id": "NGC 6",
                "recommendation_editable": True,
                "recommendation_enabled": False,
            },
            {
                "object_id": "ngc-NGC6",
                "catalogue_id": "NGC 20",
                "recommendation_editable": True,
                "recommendation_enabled": False,
            },
            {
                "object_id": "ngc-NGC7",
                "catalogue_id": "NGC 7",
                "recommendation_editable": True,
                "recommendation_enabled": False,
            },
        ]
    )

    assert model.recommendation_change_count(True) == 2
    assert model.recommendation_change_count(False) == 1
    assert model.recommendation_object_ids_requiring(True) == (
        "ngc-NGC6",
        "ngc-NGC7",
    )
    assert model.recommendation_object_ids_requiring(False) == (
        "messier-M31",
    )


def test_bulk_update_emits_compact_ranges_without_resetting_the_model() -> None:
    model = CatalogueObjectListModel()
    model.replace_items(
        [
            {
                "object_id": f"messier-M{number}",
                "recommendation_editable": True,
                "recommendation_enabled": True,
            }
            for number in range(1, 7)
        ]
    )
    changed_ranges: list[tuple[int, int]] = []
    resets = []
    model.dataChanged.connect(
        lambda first, last, _roles: changed_ranges.append(
            (first.row(), last.row())
        )
    )
    model.modelReset.connect(lambda: resets.append(True))

    changed_ids = model.update_recommendations_enabled(
        ("messier-M2", "messier-M3", "messier-M5"),
        False,
    )

    assert changed_ids == ("messier-M2", "messier-M3", "messier-M5")
    assert changed_ranges == [(1, 2), (4, 4)]
    assert resets == []
    assert model.recommendation_change_count(True) == 3
    assert model.recommendation_change_count(False) == 3


def test_large_bulk_update_coalesces_model_notification() -> None:
    model = CatalogueObjectListModel()
    model.replace_items(
        [
            {
                "object_id": f"ngc-NGC{number}",
                "recommendation_editable": True,
                "recommendation_enabled": number % 2 == 0,
            }
            for number in range(150)
        ]
    )
    changed_ranges: list[tuple[int, int]] = []
    model.dataChanged.connect(
        lambda first, last, _roles: changed_ranges.append(
            (first.row(), last.row())
        )
    )

    changed_ids = model.update_recommendations_enabled(
        model.recommendation_object_ids_requiring(True),
        True,
    )

    assert len(changed_ids) == 75
    assert changed_ranges == [(1, 149)]
    assert model.recommendation_change_count(True) == 0
    assert model.recommendation_change_count(False) == 150
