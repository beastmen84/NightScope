"""Persist user-owned image associations separately from reseeded catalogue images."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


class PersonalImageRepository:
    """Store canonical object IDs and portable content-addressed filenames, never source paths."""

    def __init__(self, database_path: Path):
        self.database_path = database_path

    def all(self) -> dict[str, dict]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("SELECT * FROM PersonalObjectImages ORDER BY object_id").fetchall()
        return {row["object_id"]: dict(row) for row in rows}

    def save(self, object_id: str, digest: str) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute(
                "INSERT INTO PersonalObjectImages (object_id, image_hash, updated_at) "
                "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now')) "
                "ON CONFLICT(object_id) DO UPDATE SET "
                "image_hash=excluded.image_hash, updated_at=excluded.updated_at",
                (object_id, digest),
            )

    def reset(self, object_id: str) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection, connection:
            connection.execute("DELETE FROM PersonalObjectImages WHERE object_id = ?", (object_id,))
