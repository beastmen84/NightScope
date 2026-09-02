"""Replace the embedded MPC observatory catalogue from a normalized CSV snapshot."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path


def import_mpc_observatories(
    connection: sqlite3.Connection,
    source_path: Path,
) -> int:
    with source_path.open("r", encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    connection.execute("DELETE FROM MpcObservatory")
    connection.executemany(
        """
        INSERT INTO MpcObservatory (
            mpc_code, name, short_name, latitude, longitude, elevation_m,
            rho_cos_phi, rho_sin_phi, observations_type, first_date, last_date,
            web_link, old_names, source_updated_at, search_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["mpc_code"],
                row["name"],
                row.get("short_name") or "",
                float(row["latitude"]),
                float(row["longitude"]),
                _optional_float(row.get("elevation_m")),
                float(row["rho_cos_phi"]),
                float(row["rho_sin_phi"]),
                row.get("observations_type") or "",
                row.get("first_date") or "",
                row.get("last_date") or "",
                row.get("web_link") or "",
                row.get("old_names") or "",
                row.get("source_updated_at") or "",
                row["search_name"],
            )
            for row in rows
        ],
    )
    return len(rows)


def _optional_float(value: object) -> float | None:
    text = str(value or "").strip()
    return float(text) if text else None
