"""Search and project embedded cities and MPC observatories as locations."""

from __future__ import annotations

import sqlite3
import unicodedata
from contextlib import closing
from pathlib import Path

from astro_viewer.app.database.city_repository import CityRepository


class LocationRepository:
    def __init__(self, database_path: Path):
        self._database_path = database_path
        self._cities = CityRepository(database_path)

    def search(self, query: str, limit: int = 20) -> list[dict]:
        normalized_query = _normalize_search(query)
        if not normalized_query:
            return []
        observatories = self._search_observatories(normalized_query)
        cities = self._cities.search(query, limit=limit)
        results = [self._observatory_result(row, normalized_query) for row in observatories]
        results.extend(self._city_result(city, normalized_query) for city in cities)
        results.sort(key=lambda item: item["search_rank"])
        selected = results[:limit]
        for item in selected:
            item.pop("search_rank", None)
        return selected

    def get_city(self, city_id: int) -> dict | None:
        return self._cities.get_by_id(city_id)

    def get_observatory(self, mpc_code: str) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT mpc_code, name, short_name, latitude, longitude,
                       elevation_m, observations_type, first_date, last_date,
                       web_link, old_names, source_updated_at, search_name
                FROM MpcObservatory
                WHERE mpc_code = ?
                """,
                (mpc_code.strip().upper(),),
            ).fetchone()
        return self._row_to_observatory(row) if row else None

    def _search_observatories(self, query: str) -> list[sqlite3.Row]:
        pattern = f"%{query}%"
        with closing(self._connect()) as connection:
            return connection.execute(
                """
                SELECT mpc_code, name, short_name, latitude, longitude,
                       elevation_m, observations_type, first_date, last_date,
                       web_link, old_names, source_updated_at, search_name
                FROM MpcObservatory
                WHERE LOWER(mpc_code) LIKE ? OR search_name LIKE ?
                ORDER BY mpc_code
                """,
                (pattern, pattern),
            ).fetchall()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _city_result(city: dict, query: str) -> dict:
        normalized_name = _normalize_search(city["city"])
        if normalized_name == query:
            match_rank = 1
        elif normalized_name.startswith(query):
            match_rank = 2
        elif query in normalized_name:
            match_rank = 3
        else:
            match_rank = 4
        return {
            "kind": "city",
            "selection_id": str(city["id"]),
            "name": city["city"],
            "context": city["country"],
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "search_rank": (match_rank, -(city.get("population") or 0), city["city"]),
        }

    @classmethod
    def _observatory_result(cls, row: sqlite3.Row, query: str) -> dict:
        observatory = cls._row_to_observatory(row)
        normalized_name = _normalize_search(observatory["name"])
        normalized_short_name = _normalize_search(observatory["short_name"])
        if observatory["mpc_code"].casefold() == query:
            match_rank = 0
        elif query in {normalized_name, normalized_short_name}:
            match_rank = 1
        elif normalized_name.startswith(query) or normalized_short_name.startswith(query):
            match_rank = 2
        else:
            match_rank = 3
        return {
            "kind": "mpc_observatory",
            "selection_id": observatory["mpc_code"],
            "name": observatory["name"],
            "context": f"MPC {observatory['mpc_code']}",
            "latitude": observatory["latitude"],
            "longitude": observatory["longitude"],
            "search_rank": (match_rank, 0, observatory["mpc_code"]),
        }

    @staticmethod
    def _row_to_observatory(row: sqlite3.Row) -> dict:
        return {
            "mpc_code": row["mpc_code"],
            "name": row["name"],
            "short_name": row["short_name"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "elevation_m": row["elevation_m"],
            "observations_type": row["observations_type"],
            "first_date": row["first_date"],
            "last_date": row["last_date"],
            "web_link": row["web_link"],
            "old_names": row["old_names"],
            "source_updated_at": row["source_updated_at"],
            "search_name": row["search_name"],
        }


def _normalize_search(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.strip().casefold())
    ascii_value = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(ascii_value.replace("-", " ").replace("_", " ").split())
