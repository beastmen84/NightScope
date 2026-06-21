from __future__ import annotations

import math
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
                        WHEN (' ' || search_name || ' ') LIKE ? THEN 1
                        WHEN search_name LIKE ? THEN 2
                        ELSE 3
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
                    f"% {normalized_query} %",
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

    def nearest_by_coordinates(self, latitude: float, longitude: float, max_radius_km: float = 50.0) -> dict | None:
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            return None
        latitude_delta = max(max_radius_km / 111.0, 0.01)
        cosine = max(abs(math.cos(math.radians(latitude))), 0.01)
        longitude_delta = max(max_radius_km / (111.0 * cosine), 0.01)
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, city_name, ascii_name, country, country_code, admin_region,
                       latitude, longitude, timezone, population, aliases, search_name
                FROM City
                WHERE ABS(latitude - ?) <= ?
                  AND ABS(longitude - ?) <= ?
                """,
                (latitude, latitude_delta, longitude, longitude_delta),
            ).fetchall()
        nearest_row = None
        nearest_distance = None
        for row in rows:
            distance = _distance_km(latitude, longitude, row["latitude"], row["longitude"])
            if distance > max_radius_km:
                continue
            if nearest_distance is None or distance < nearest_distance:
                nearest_row = row
                nearest_distance = distance
        if nearest_row is None or nearest_distance is None:
            return None
        city = self._row_to_city(nearest_row)
        city["distance_km"] = nearest_distance
        return city

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


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(value), math.sqrt(1 - value))
