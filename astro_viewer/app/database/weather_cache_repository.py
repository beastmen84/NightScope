from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


class WeatherCacheRepository:
    """Small SQLite cache for Open-Meteo payloads."""

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get(self, cache_key: str) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT cache_key, fetched_at, payload
                FROM WeatherCache
                WHERE cache_key = ?
                """,
                (cache_key,),
            ).fetchone()
        if not row:
            return None
        return {
            "cache_key": row["cache_key"],
            "fetched_at": row["fetched_at"],
            "payload": row["payload"],
        }

    def set(self, cache_key: str, fetched_at: str, payload: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO WeatherCache (cache_key, fetched_at, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    fetched_at = excluded.fetched_at,
                    payload = excluded.payload
                """,
                (cache_key, fetched_at, payload),
            )
            connection.commit()
