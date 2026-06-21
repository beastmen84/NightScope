from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


class CityRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def list_cities(self, limit: int = 50) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, city_name, country, latitude, longitude, timezone
                FROM City
                ORDER BY country, city_name
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_city(row) for row in rows]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        normalized = f"%{query.strip()}%"
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, city_name, country, latitude, longitude, timezone
                FROM City
                WHERE city_name LIKE ? OR country LIKE ?
                ORDER BY city_name
                LIMIT ?
                """,
                (normalized, normalized, limit),
            ).fetchall()
        return [self._row_to_city(row) for row in rows]

    def get_by_id(self, city_id: int) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT id, city_name, country, latitude, longitude, timezone
                FROM City
                WHERE id = ?
                """,
                (city_id,),
            ).fetchone()
        return self._row_to_city(row) if row else None

    def get_default(self) -> dict:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT id, city_name, country, latitude, longitude, timezone
                FROM City
                WHERE city_name = 'Milano'
                LIMIT 1
                """
            ).fetchone()
        if row:
            return self._row_to_city(row)
        cities = self.list_cities(limit=1)
        return cities[0]

    @staticmethod
    def _row_to_city(row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "city": row["city_name"],
            "country": row["country"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "timezone": row["timezone"],
        }
