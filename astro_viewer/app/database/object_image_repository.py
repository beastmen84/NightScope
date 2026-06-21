from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


class ObjectImageRepository:
    """Returns local image paths and attribution for astronomical objects."""

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get(self, object_id: str) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT object_id, image_path, attribution
                FROM ObjectImages
                WHERE object_id = ?
                """,
                (object_id,),
            ).fetchone()
        return dict(row) if row else None

    def all(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT object_id, image_path, attribution
                FROM ObjectImages
                ORDER BY object_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

