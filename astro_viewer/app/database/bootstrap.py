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

TELESCOPE_BRANDS = [
    "Celestron",
    "Sky-Watcher",
    "Bresser",
    "Omegon",
    "Orion",
    "Explore Scientific",
    "William Optics",
    "Meade",
]

TELESCOPE_MODELS = [
    ("Celestron", "NexStar 130SLT", "Newton", 130, 650, "GoTo altazimutale"),
    ("Celestron", "NexStar 8SE", "Schmidt-Cassegrain", 203, 2032, "GoTo altazimutale"),
    ("Celestron", "AstroMaster 130EQ", "Newton", 130, 650, "equatoriale"),
    ("Sky-Watcher", "Heritage 130P", "Newton", 130, 650, "Dobson tabletop"),
    ("Sky-Watcher", "Classic 200P Dobson", "Newton", 200, 1200, "Dobson"),
    ("Sky-Watcher", "Evostar 80ED", "rifrattore", 80, 600, "OTA"),
    ("Sky-Watcher", "Explorer 150PDS", "Newton", 150, 750, "OTA"),
    ("Bresser", "Messier AR-102/1000", "rifrattore", 102, 1000, "equatoriale"),
    ("Bresser", "Messier NT-150S", "Newton", 150, 750, "equatoriale"),
    ("Omegon", "Advanced 150/750 EQ-320", "Newton", 150, 750, "equatoriale"),
    ("Omegon", "ProDob N 203/1200", "Newton", 203, 1200, "Dobson"),
    ("Orion", "SkyQuest XT8", "Newton", 203, 1200, "Dobson"),
    ("Orion", "StarBlast 4.5", "Newton", 114, 450, "Dobson tabletop"),
    ("Explore Scientific", "ED80 Essential", "rifrattore", 80, 480, "OTA"),
    ("Explore Scientific", "AR102", "rifrattore", 102, 663, "OTA"),
    ("William Optics", "Zenithstar 61", "rifrattore", 61, 360, "OTA"),
    ("William Optics", "Gran Turismo 81", "rifrattore", 81, 478, "OTA"),
    ("Meade", "LX90 8 ACF", "Schmidt-Cassegrain", 203, 2000, "GoTo forcella"),
    ("Meade", "ETX125 Observer", "Maksutov", 127, 1900, "GoTo altazimutale"),
]

EYEPIECE_CATALOG = [
    ("Celestron", "X-Cel LX", 25.0, 60.0),
    ("Celestron", "X-Cel LX", 9.0, 60.0),
    ("Sky-Watcher", "Super Plossl", 25.0, 52.0),
    ("Sky-Watcher", "Super Plossl", 10.0, 52.0),
    ("Bresser", "SPL", 26.0, 52.0),
    ("Omegon", "Redline", 15.0, 70.0),
    ("Orion", "Expanse", 6.0, 66.0),
    ("Explore Scientific", "82 Series", 11.0, 82.0),
    ("William Optics", "Swan", 20.0, 72.0),
    ("Meade", "Series 4000 Super Plossl", 32.0, 52.0),
]

BARLOW_CATALOG = [
    ("Celestron", "Omni 2x", 2.0),
    ("Celestron", "X-Cel LX 3x", 3.0),
    ("Sky-Watcher", "Deluxe 2x", 2.0),
    ("Omegon", "Achromatic 2x", 2.0),
    ("Orion", "Shorty 2x", 2.0),
    ("Explore Scientific", "Focal Extender 3x", 3.0),
]

OBJECT_IMAGES = [
    ("sun", "resources/images/sun.svg", "NightScope generated local SVG"),
    ("moon", "resources/images/moon.svg", "NightScope generated local SVG"),
    ("mercury", "resources/images/mercury.svg", "NightScope generated local SVG"),
    ("venus", "resources/images/venus.svg", "NightScope generated local SVG"),
    ("mars", "resources/images/mars.svg", "NightScope generated local SVG"),
    ("jupiter", "resources/images/jupiter.svg", "NightScope generated local SVG"),
    ("saturn", "resources/images/saturn.svg", "NightScope generated local SVG"),
    ("uranus", "resources/images/uranus.svg", "NightScope generated local SVG"),
    ("neptune", "resources/images/neptune.svg", "NightScope generated local SVG"),
    ("messier-default-cluster", "resources/images/m13.svg", "NightScope generated local SVG"),
    ("messier-default-nebula", "resources/images/m57.svg", "NightScope generated local SVG"),
    ("messier-default-galaxy", "resources/images/m31.svg", "NightScope generated local SVG"),
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
        _seed_telescope_catalog(connection)
        _seed_optics_catalog(connection)
        _seed_object_images(connection)
        _seed_default_profiles(connection)
        connection.commit()


def _optional_float(value: str) -> float | None:
    clean_value = value.strip()
    if not clean_value:
        return None
    try:
        return float(clean_value)
    except ValueError:
        return None


def _seed_telescope_catalog(connection: sqlite3.Connection) -> None:
    brand_count = connection.execute("SELECT COUNT(*) FROM TelescopeBrand").fetchone()[0]
    if brand_count == 0:
        connection.executemany("INSERT INTO TelescopeBrand (name) VALUES (?)", [(name,) for name in TELESCOPE_BRANDS])

    model_count = connection.execute("SELECT COUNT(*) FROM TelescopeModel").fetchone()[0]
    if model_count != 0:
        return
    brand_ids = {
        row[1]: row[0]
        for row in connection.execute("SELECT id, name FROM TelescopeBrand").fetchall()
    }
    connection.executemany(
        """
        INSERT INTO TelescopeModel (
            brand_id, name, optical_type, aperture_mm, focal_length_mm, mount_type
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (brand_ids[brand], name, optical_type, aperture, focal, mount)
            for brand, name, optical_type, aperture, focal, mount in TELESCOPE_MODELS
        ],
    )


def _seed_optics_catalog(connection: sqlite3.Connection) -> None:
    eyepiece_count = connection.execute("SELECT COUNT(*) FROM EyepieceCatalog").fetchone()[0]
    if eyepiece_count == 0:
        connection.executemany(
            """
            INSERT INTO EyepieceCatalog (brand, model, focal_length_mm, apparent_field_deg)
            VALUES (?, ?, ?, ?)
            """,
            EYEPIECE_CATALOG,
        )

    barlow_count = connection.execute("SELECT COUNT(*) FROM BarlowCatalog").fetchone()[0]
    if barlow_count == 0:
        connection.executemany(
            """
            INSERT INTO BarlowCatalog (brand, model, multiplier)
            VALUES (?, ?, ?)
            """,
            BARLOW_CATALOG,
        )


def _seed_object_images(connection: sqlite3.Connection) -> None:
    image_count = connection.execute("SELECT COUNT(*) FROM ObjectImages").fetchone()[0]
    if image_count == 0:
        connection.executemany(
            """
            INSERT INTO ObjectImages (object_id, image_path, attribution)
            VALUES (?, ?, ?)
            """,
            OBJECT_IMAGES,
        )


def _seed_default_profiles(connection: sqlite3.Connection) -> None:
    profile_count = connection.execute("SELECT COUNT(*) FROM EquipmentProfile").fetchone()[0]
    if profile_count == 0:
        connection.executemany(
            """
            INSERT INTO EquipmentProfile (profile_name, active, telescope_id)
            VALUES (?, ?, ?)
            """,
            [
                ("NexStar 130SLT", 1, "catalog:Celestron:NexStar 130SLT"),
                ("Dobson 200P", 0, "catalog:Sky-Watcher:Classic 200P Dobson"),
                ("Binocolo 10x50", 0, "preset:binoculars"),
            ],
        )


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[2]
    initialize_database(base_dir / "data" / "nightscope.db", base_dir / "data" / "schema.sql")
    print("Database inizializzato:", base_dir / "data" / "nightscope.db")
