from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


class ObservationRepository:
    """Persistence boundary for future observing session notes."""

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def add(
        self,
        date: str,
        object_name: str,
        location: str,
        telescope: str,
        eyepiece: str,
        rating: int,
        notes: str,
    ) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO ObservationHistory (
                    date, object_name, location, telescope, eyepiece, rating, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (date, object_name, location, telescope, eyepiece, rating, notes),
            )
            connection.commit()

    def recent(self, limit: int = 20) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, date, object_name, location, telescope, eyepiece, rating, notes
                FROM ObservationHistory
                ORDER BY date DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
