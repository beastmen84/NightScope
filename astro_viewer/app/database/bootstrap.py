from __future__ import annotations

import csv
import sqlite3
from contextlib import closing
from pathlib import Path


SEED_CITIES = [
    ("Milano", "Italia", 45.4642, 9.1900, "Europe/Rome"),
    ("Roma", "Italia", 41.9028, 12.4964, "Europe/Rome"),
    ("Torino", "Italia", 45.0703, 7.6869, "Europe/Rome"),
    ("Napoli", "Italia", 40.8518, 14.2681, "Europe/Rome"),
    ("Palermo", "Italia", 38.1157, 13.3615, "Europe/Rome"),
    ("Londra", "Regno Unito", 51.5072, -0.1276, "Europe/London"),
    ("Parigi", "Francia", 48.8566, 2.3522, "Europe/Paris"),
    ("Berlino", "Germania", 52.5200, 13.4050, "Europe/Berlin"),
    ("New York", "Stati Uniti", 40.7128, -74.0060, "America/New_York"),
    ("Los Angeles", "Stati Uniti", 34.0522, -118.2437, "America/Los_Angeles"),
    ("Tokyo", "Giappone", 35.6762, 139.6503, "Asia/Tokyo"),
    ("Sydney", "Australia", -33.8688, 151.2093, "Australia/Sydney"),
    ("Nairobi", "Kenya", -1.2921, 36.8219, "Africa/Nairobi"),
    ("Madrid", "Spagna", 40.4168, -3.7038, "Europe/Madrid"),
    ("Buenos Aires", "Argentina", -34.6037, -58.3816, "America/Argentina/Buenos_Aires"),
]


def initialize_database(database_path: Path, schema_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = schema_path.read_text(encoding="utf-8")
    seed_path = schema_path.with_name("messier_seed.csv")

    with closing(sqlite3.connect(database_path)) as connection:
        connection.executescript(schema_sql)
        city_count = connection.execute("SELECT COUNT(*) FROM City").fetchone()[0]
        if city_count == 0:
            connection.executemany(
                """
                INSERT INTO City (city_name, country, latitude, longitude, timezone)
                VALUES (?, ?, ?, ?, ?)
                """,
                SEED_CITIES,
            )
        messier_count = connection.execute("SELECT COUNT(*) FROM MessierObject").fetchone()[0]
        if messier_count == 0 and seed_path.exists():
            with seed_path.open("r", encoding="utf-8", newline="") as file:
                rows = [
                    (
                        row["messier_id"],
                        row["nome"],
                        row["tipo"],
                        row["costellazione"],
                        _optional_float(row["magnitudine"]),
                        row["ascensione_retta"],
                        row["declinazione"],
                        row["dimensione_apparente"],
                        row["descrizione"],
                    )
                    for row in csv.DictReader(file)
                ]
            connection.executemany(
                """
                INSERT INTO MessierObject (
                    messier_id,
                    nome,
                    tipo,
                    costellazione,
                    magnitudine,
                    ascensione_retta,
                    declinazione,
                    dimensione_apparente,
                    descrizione
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        connection.commit()


def _optional_float(value: str) -> float | None:
    clean_value = value.strip()
    if not clean_value:
        return None
    try:
        return float(clean_value)
    except ValueError:
        return None


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[2]
    initialize_database(base_dir / "data" / "nightscope.db", base_dir / "data" / "schema.sql")
    print("Database inizializzato:", base_dir / "data" / "nightscope.db")
