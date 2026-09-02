"""Provide SQLite CRUD operations for the completed-observation log."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


class ObservationRepository:
    """Persistence boundary for the observation log."""

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
    ) -> int:
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                """
                INSERT INTO ObservationHistory (
                    date, object_name, location, telescope, eyepiece, rating, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (date, object_name, location, telescope, eyepiece, rating, notes),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def list_all(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, date, object_name, location, telescope, eyepiece, rating, notes
                FROM ObservationHistory
                ORDER BY date DESC, id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def update(
        self,
        observation_id: int,
        date: str,
        object_name: str,
        location: str,
        telescope: str,
        eyepiece: str,
        rating: int,
        notes: str,
    ) -> bool:
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                """
                UPDATE ObservationHistory
                SET date = ?, object_name = ?, location = ?, telescope = ?,
                    eyepiece = ?, rating = ?, notes = ?
                WHERE id = ?
                """,
                (
                    date,
                    object_name,
                    location,
                    telescope,
                    eyepiece,
                    rating,
                    notes,
                    observation_id,
                ),
            )
            connection.commit()
            return cursor.rowcount == 1

    def delete(self, observation_id: int) -> bool:
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                "DELETE FROM ObservationHistory WHERE id = ?",
                (observation_id,),
            )
            connection.commit()
            return cursor.rowcount == 1
