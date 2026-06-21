from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


class MessierRepository:
    """SQLite repository for the embedded Messier catalog."""

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def list_objects(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, messier_id, nome, tipo, costellazione, magnitudine,
                       ascensione_retta, declinazione, dimensione_apparente, descrizione
                FROM MessierObject
                ORDER BY CAST(SUBSTR(messier_id, 2) AS INTEGER)
                """
            ).fetchall()
        return [self._row_to_object(row) for row in rows]

    def search(self, query: str, limit: int = 30) -> list[dict]:
        normalized = f"%{query.strip()}%"
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, messier_id, nome, tipo, costellazione, magnitudine,
                       ascensione_retta, declinazione, dimensione_apparente, descrizione
                FROM MessierObject
                WHERE messier_id LIKE ?
                   OR nome LIKE ?
                   OR tipo LIKE ?
                   OR costellazione LIKE ?
                ORDER BY CAST(SUBSTR(messier_id, 2) AS INTEGER)
                LIMIT ?
                """,
                (normalized, normalized, normalized, normalized, limit),
            ).fetchall()
        return [self._row_to_object(row) for row in rows]

    def filter_by_type(self, object_type: str, limit: int = 50) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, messier_id, nome, tipo, costellazione, magnitudine,
                       ascensione_retta, declinazione, dimensione_apparente, descrizione
                FROM MessierObject
                WHERE tipo LIKE ?
                ORDER BY magnitudine IS NULL, magnitudine ASC
                LIMIT ?
                """,
                (f"%{object_type.strip()}%", limit),
            ).fetchall()
        return [self._row_to_object(row) for row in rows]

    @staticmethod
    def _row_to_object(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "messier_id": row["messier_id"],
            "name": row["nome"],
            "object_type": row["tipo"],
            "constellation": row["costellazione"],
            "magnitude": row["magnitudine"],
            "ra": row["ascensione_retta"],
            "dec": row["declinazione"],
            "apparent_size": row["dimensione_apparente"],
            "description": row["descrizione"],
        }
