from __future__ import annotations

import sqlite3
import unicodedata
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
                SELECT id, city_name, ascii_name, country, country_code, admin_region,
                       latitude, longitude, timezone, population, aliases, search_name
                FROM City
                ORDER BY population DESC NULLS LAST, country, city_name
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_city(row) for row in rows]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        normalized_query = _normalize_search(query)
        if not normalized_query:
            return self.list_cities(limit=limit)
        normalized = f"%{normalized_query}%"
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, city_name, ascii_name, country, country_code, admin_region,
                       latitude, longitude, timezone, population, aliases, search_name
                FROM City
                WHERE search_name LIKE ?
                   OR LOWER(city_name) LIKE ?
                   OR LOWER(COALESCE(ascii_name, '')) LIKE ?
                   OR LOWER(COALESCE(aliases, '')) LIKE ?
                   OR LOWER(country) LIKE ?
                   OR LOWER(COALESCE(country_code, '')) LIKE ?
                   OR EXISTS (
                        SELECT 1
                        FROM CityAlias ca
                        WHERE ca.city_id = City.id
                          AND ca.normalized_alias LIKE ?
                   )
                ORDER BY
                    CASE
                        WHEN search_name = ? THEN 0
                        WHEN EXISTS (
                            SELECT 1 FROM CityAlias ca
                            WHERE ca.city_id = City.id
                              AND ca.normalized_alias = ?
                        ) THEN 0
                        WHEN search_name LIKE ? THEN 1
                        ELSE 2
                    END,
                    population DESC NULLS LAST,
                    city_name
                LIMIT ?
                """,
                (
                    normalized,
                    normalized,
                    normalized,
                    normalized,
                    normalized,
                    normalized,
                    normalized,
                    normalized_query,
                    normalized_query,
                    f"{normalized_query}%",
                    limit,
                ),
            ).fetchall()
        return [self._row_to_city(row) for row in rows]

    def get_by_id(self, city_id: int) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT id, city_name, ascii_name, country, country_code, admin_region,
                       latitude, longitude, timezone, population, aliases, search_name
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
                SELECT id, city_name, ascii_name, country, country_code, admin_region,
                       latitude, longitude, timezone, population, aliases, search_name
                FROM City
                WHERE city_name IN ('Milano', 'Roma')
                ORDER BY CASE city_name WHEN 'Milano' THEN 0 ELSE 1 END
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
            "ascii_name": row["ascii_name"] if "ascii_name" in row.keys() else row["city_name"],
            "country": row["country"],
            "country_code": row["country_code"] if "country_code" in row.keys() else "",
            "admin_region": row["admin_region"] if "admin_region" in row.keys() else "",
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "timezone": row["timezone"],
            "population": row["population"] if "population" in row.keys() else None,
            "aliases": row["aliases"] if "aliases" in row.keys() else "",
            "search_name": row["search_name"] if "search_name" in row.keys() else "",
        }


def _normalize_search(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    ascii_value = "".join(character for character in normalized if not unicodedata.combining(character))
    return " ".join(ascii_value.replace("-", " ").replace("_", " ").split())
