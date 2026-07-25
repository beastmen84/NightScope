from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, Qt

from astro_viewer.app.services.localization import render_payload


class CatalogueObjectListModel(QAbstractListModel):
    """Virtualized catalogue rows with targeted recommendation-state updates."""

    ItemDataRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[dict] = []
        self._rendered_items: list[dict | None] = []
        self._rows_by_object_id: dict[str, tuple[int, ...]] = {}

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            int(self.ItemDataRole): QByteArray(b"itemData"),
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._items)

    def data(
        self,
        index: QModelIndex,
        role: int = int(Qt.ItemDataRole.DisplayRole),
    ) -> object:
        if (
            not index.isValid()
            or index.row() < 0
            or index.row() >= len(self._items)
            or role not in {int(Qt.ItemDataRole.DisplayRole), int(self.ItemDataRole)}
        ):
            return None
        row = index.row()
        rendered = self._rendered_items[row]
        if rendered is None:
            rendered = render_payload(self._items[row])
            self._rendered_items[row] = rendered
        return rendered

    def replace_items(self, items: Iterable[dict]) -> None:
        rows = [dict(item) for item in items]
        rows_by_object_id: defaultdict[str, list[int]] = defaultdict(list)
        for row, item in enumerate(rows):
            object_id = str(item.get("object_id") or "").strip().casefold()
            if object_id:
                rows_by_object_id[object_id].append(row)

        self.beginResetModel()
        self._items = rows
        self._rendered_items = [None] * len(rows)
        self._rows_by_object_id = {
            object_id: tuple(indices)
            for object_id, indices in rows_by_object_id.items()
        }
        self.endResetModel()

    def update_recommendation_enabled(self, object_id: str, enabled: bool) -> bool:
        normalized_id = object_id.strip().casefold()
        rows = self._rows_by_object_id.get(normalized_id, ())
        changed = False
        for row in rows:
            item = self._items[row]
            if bool(item.get("recommendation_enabled", True)) == bool(enabled):
                continue
            updated = dict(item)
            updated["recommendation_enabled"] = bool(enabled)
            self._items[row] = updated
            self._rendered_items[row] = None
            model_index = self.index(row, 0)
            self.dataChanged.emit(
                model_index,
                model_index,
                [int(self.ItemDataRole)],
            )
            changed = True
        return changed

    def item(self, row: int) -> dict:
        if row < 0 or row >= len(self._items):
            return {}
        return dict(self._items[row])
