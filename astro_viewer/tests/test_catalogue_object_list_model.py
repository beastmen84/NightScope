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
    changed_rows: list[int] = []
    model.dataChanged.connect(
        lambda first, _last, _roles: changed_rows.append(first.row())
    )

    assert model.update_recommendation_enabled("NGC-ngc6", True) is True

    assert model.rowCount() == 3
    assert changed_rows == [0, 1]
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
