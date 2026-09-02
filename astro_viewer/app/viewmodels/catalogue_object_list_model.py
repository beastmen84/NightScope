"""Expose virtualized catalogue rows and targeted updates through Qt's model API."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, Qt

from astro_viewer.app.services.localization import render_payload


_MAX_TARGETED_DATA_CHANGE_ROWS = 64


class CatalogueObjectListModel(QAbstractListModel):
    """Virtualized catalogue rows with targeted recommendation-state updates."""

    ItemDataRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[dict] = []
        self._rendered_items: list[dict | None] = []
        self._rows_by_object_id: dict[str, tuple[int, ...]] = {}
        self._editable_object_ids: dict[str, str] = {}
        self._editable_enabled_ids: dict[str, str] = {}
        self._editable_disabled_ids: dict[str, str] = {}

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
        self._rebuild_recommendation_states()
        self.endResetModel()

    def update_recommendation_enabled(self, object_id: str, enabled: bool) -> bool:
        return bool(
            self.update_recommendations_enabled(
                (object_id,),
                enabled,
            )
        )

    def update_recommendations_enabled(
        self,
        object_ids: Iterable[str],
        enabled: bool,
    ) -> tuple[str, ...]:
        normalized_ids: dict[str, str] = {}
        for object_id in object_ids:
            canonical_id = object_id.strip()
            if canonical_id:
                normalized_ids.setdefault(
                    canonical_id.casefold(),
                    canonical_id,
                )
        if not normalized_ids:
            return ()

        changed_rows = []
        changed_ids: dict[str, str] = {}
        for normalized_id, requested_id in normalized_ids.items():
            for row in self._rows_by_object_id.get(normalized_id, ()):
                item = self._items[row]
                if bool(item.get("recommendation_enabled", True)) == bool(
                    enabled
                ):
                    continue
                updated = dict(item)
                updated["recommendation_enabled"] = bool(enabled)
                self._items[row] = updated
                self._rendered_items[row] = None
                changed_rows.append(row)
                changed_ids.setdefault(
                    normalized_id,
                    str(item.get("object_id") or "").strip()
                    or requested_id,
                )

        if not changed_rows:
            return ()
        changed_rows.sort()

        target_states = (
            self._editable_enabled_ids
            if enabled
            else self._editable_disabled_ids
        )
        opposite_states = (
            self._editable_disabled_ids
            if enabled
            else self._editable_enabled_ids
        )
        for normalized_id, canonical_id in changed_ids.items():
            if normalized_id not in self._editable_object_ids:
                continue
            opposite_states.pop(normalized_id, None)
            target_states[normalized_id] = canonical_id

        changed_ranges = self._contiguous_ranges(changed_rows)
        if len(changed_rows) > _MAX_TARGETED_DATA_CHANGE_ROWS:
            changed_ranges = ((changed_rows[0], changed_rows[-1]),)
        for first_row, last_row in changed_ranges:
            self.dataChanged.emit(
                self.index(first_row, 0),
                self.index(last_row, 0),
                [int(self.ItemDataRole)],
            )
        return tuple(changed_ids.values())

    def recommendation_object_ids_requiring(
        self,
        enabled: bool,
    ) -> tuple[str, ...]:
        source = (
            self._editable_disabled_ids
            if enabled
            else self._editable_enabled_ids
        )
        return tuple(source.values())

    def recommendation_change_count(self, enabled: bool) -> int:
        source = (
            self._editable_disabled_ids
            if enabled
            else self._editable_enabled_ids
        )
        return len(source)

    def item(self, row: int) -> dict:
        if row < 0 or row >= len(self._items):
            return {}
        return dict(self._items[row])

    def _rebuild_recommendation_states(self) -> None:
        editable_object_ids: dict[str, str] = {}
        enabled_ids: dict[str, str] = {}
        disabled_ids: dict[str, str] = {}
        for item in self._items:
            if not bool(item.get("recommendation_editable", False)):
                continue
            canonical_id = str(item.get("object_id") or "").strip()
            normalized_id = canonical_id.casefold()
            if not normalized_id or normalized_id in editable_object_ids:
                continue
            editable_object_ids[normalized_id] = canonical_id
            target = (
                enabled_ids
                if bool(item.get("recommendation_enabled", True))
                else disabled_ids
            )
            target[normalized_id] = canonical_id
        self._editable_object_ids = editable_object_ids
        self._editable_enabled_ids = enabled_ids
        self._editable_disabled_ids = disabled_ids

    @staticmethod
    def _contiguous_ranges(rows: list[int]) -> tuple[tuple[int, int], ...]:
        if not rows:
            return ()
        ranges = []
        first_row = rows[0]
        last_row = first_row
        for row in rows[1:]:
            if row == last_row + 1:
                last_row = row
                continue
            ranges.append((first_row, last_row))
            first_row = row
            last_row = row
        ranges.append((first_row, last_row))
        return tuple(ranges)
