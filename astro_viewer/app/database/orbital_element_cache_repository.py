from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OrbitalElementCacheRecord:
    provider: str
    object_id: str
    element_format: str
    fetched_at: str
    source_epoch: str
    expires_at: str
    payload: str


class OrbitalElementCacheRepository:
    """SQLite cache shared by short-horizon orbital event providers."""

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get(self, provider: str, object_id: str) -> OrbitalElementCacheRecord | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT provider, object_id, element_format, fetched_at,
                       source_epoch, expires_at, payload
                FROM OrbitalElementCache
                WHERE provider = ? AND object_id = ?
                """,
                (provider, object_id),
            ).fetchone()
        if row is None:
            return None
        return OrbitalElementCacheRecord(**dict(row))

    def set(self, record: OrbitalElementCacheRecord) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO OrbitalElementCache (
                    provider, object_id, element_format, fetched_at,
                    source_epoch, expires_at, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, object_id) DO UPDATE SET
                    element_format = excluded.element_format,
                    fetched_at = excluded.fetched_at,
                    source_epoch = excluded.source_epoch,
                    expires_at = excluded.expires_at,
                    payload = excluded.payload
                """,
                (
                    record.provider,
                    record.object_id,
                    record.element_format,
                    record.fetched_at,
                    record.source_epoch,
                    record.expires_at,
                    record.payload,
                ),
            )
            connection.commit()
