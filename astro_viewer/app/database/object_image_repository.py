"""Read local object imagery, editorial descriptions, and curiosity metadata."""

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
                SELECT object_id, image_path, thumbnail_path, attribution,
                       source_url, license, verified
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
                SELECT object_id, image_path, thumbnail_path, attribution,
                       source_url, license, verified
                FROM ObjectImages
                ORDER BY object_id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def descriptions(self) -> dict[str, dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT object_id, short_description, observing_notes, best_seen,
                       difficulty_naked_eye, difficulty_binocular, difficulty_small_scope,
                       difficulty_medium_scope, difficulty_large_scope, is_builtin
                FROM ObjectDescription
                ORDER BY object_id
                """
            ).fetchall()
        return {row["object_id"]: dict(row) for row in rows}

    def curiosities(self) -> dict[str, dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT object_id, curiosity_text, source_label, source_url, verified,
                       is_builtin
                FROM ObjectCuriosity
                ORDER BY object_id
                """
            ).fetchall()
        return {row["object_id"]: dict(row) for row in rows}
