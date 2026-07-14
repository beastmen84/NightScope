from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path


class SkyQualityRepository:
    """Caches provider-derived sky quality estimates."""

    def __init__(self, database_path: Path):
        self._database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def get(self, location_key: str) -> dict | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT location_key, bortle_class, limiting_magnitude,
                       sky_brightness, source, confidence, updated_at
                FROM SkyQualityEstimate
                WHERE location_key = ?
                """,
                (location_key,),
            ).fetchone()
        return dict(row) if row else None

    def list_estimates(self) -> list[dict]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT location_key, bortle_class, limiting_magnitude,
                       sky_brightness, source, confidence, updated_at
                FROM SkyQualityEstimate
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def set(
        self,
        location_key: str,
        bortle_class: int,
        limiting_magnitude: float,
        sky_brightness: float,
        source: str,
        confidence: str,
        updated_at: str,
    ) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO SkyQualityEstimate (
                    location_key, bortle_class, limiting_magnitude,
                    sky_brightness, source, confidence, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(location_key) DO UPDATE SET
                    bortle_class = excluded.bortle_class,
                    limiting_magnitude = excluded.limiting_magnitude,
                    sky_brightness = excluded.sky_brightness,
                    source = excluded.source,
                    confidence = excluded.confidence,
                    updated_at = excluded.updated_at
                """,
                (location_key, bortle_class, limiting_magnitude, sky_brightness, source, confidence, updated_at),
            )
            connection.commit()

    def delete_non_viirs_estimates(self) -> int:
        """Remove legacy local or synthetic estimates from the provider cache."""
        with closing(self._connect()) as connection:
            cursor = connection.execute(
                """
                DELETE FROM SkyQualityEstimate
                WHERE source NOT LIKE ?
                """,
                ("%NASA Black Marble VNP46A3%",),
            )
            connection.commit()
        return max(0, cursor.rowcount)
