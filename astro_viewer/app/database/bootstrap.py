from __future__ import annotations

import csv
import logging
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


logger = logging.getLogger(__name__)

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

    if database_path.exists() and not _database_is_healthy(database_path):
        _quarantine_database(database_path)
    elif database_path.exists():
        _backup_database(database_path)

    try:
        _build_database(database_path, schema_sql, seed_path)
    except sqlite3.DatabaseError as exc:
        if not _is_recoverable_database_error(exc):
            logger.exception("Database bootstrap failed during schema migration.")
            raise
        logger.warning("Database appears damaged; rebuilding from local schema.", exc_info=True)
        _quarantine_database(database_path)
        _build_database(database_path, schema_sql, seed_path)


def _build_database(database_path: Path, schema_sql: str, seed_path: Path) -> None:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.executescript(schema_sql)
        _migrate_database(connection)
        data_dir = seed_path.parent
        city_count = connection.execute("SELECT COUNT(*) FROM City").fetchone()[0]
        if city_count < 50:
            _seed_cities(connection, data_dir / "cities_seed.csv")
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
        _seed_telescope_catalog(connection, data_dir / "telescope_catalog_seed.csv")
        _seed_optics_catalog(
            connection,
            data_dir / "eyepiece_catalog_seed.csv",
            data_dir / "barlow_catalog_seed.csv",
        )
        _seed_object_images(connection, data_dir / "object_images_seed.csv")
        _seed_object_descriptions(connection, data_dir / "object_descriptions_seed.csv")
        _seed_default_profiles(connection)
        connection.commit()
    logger.info("Database ready.")


def _migrate_database(connection: sqlite3.Connection) -> None:
    _add_columns(
        connection,
        "City",
        {
            "ascii_name": "TEXT",
            "country_code": "TEXT",
            "admin_region": "TEXT",
            "population": "INTEGER",
            "search_name": "TEXT",
        },
    )
    _add_columns(connection, "TelescopeModel", {"focal_ratio": "REAL", "notes": "TEXT"})
    _add_columns(connection, "EyepieceCatalog", {"barrel_size": "TEXT", "notes": "TEXT"})
    _add_columns(connection, "BarlowCatalog", {"barrel_size": "TEXT", "notes": "TEXT"})
    _add_columns(connection, "SkyQualityEstimate", {"confidence": "TEXT"})
    _add_columns(
        connection,
        "ObjectImages",
        {
            "thumbnail_path": "TEXT",
            "source_url": "TEXT",
            "license": "TEXT",
            "verified": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_city_search_name ON City(search_name)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_city_country_code ON City(country_code)")
    connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_city_unique_name_country ON City(city_name, country)")


def _add_columns(connection: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    existing = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, definition in columns.items():
        if column_name not in existing:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _database_is_healthy(database_path: Path) -> bool:
    try:
        with closing(sqlite3.connect(database_path)) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError:
        logger.warning("Database integrity check failed.", exc_info=True)
        return False
    return bool(result and result[0] == "ok")


def _backup_database(database_path: Path) -> None:
    backup_path = database_path.with_suffix(database_path.suffix + ".backup")
    try:
        shutil.copy2(database_path, backup_path)
    except OSError:
        logger.warning("Database backup could not be created.", exc_info=True)
        return
    logger.info("Database backup refreshed.")


def _quarantine_database(database_path: Path) -> None:
    if not database_path.exists():
        return
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    quarantine_path = database_path.with_suffix(database_path.suffix + f".corrupt-{timestamp}.bak")
    try:
        database_path.replace(quarantine_path)
    except OSError:
        logger.error("Corrupt database could not be quarantined.", exc_info=True)
        raise
    logger.warning("Corrupt database quarantined; a fresh database will be created.")


def _is_recoverable_database_error(error: sqlite3.DatabaseError) -> bool:
    message = str(error).lower()
    return any(
        fragment in message
        for fragment in (
            "malformed",
            "not a database",
            "file is not a database",
            "database disk image",
        )
    )


def _optional_float(value: str) -> float | None:
    clean_value = value.strip()
    if not clean_value:
        return None
    try:
        return float(clean_value)
    except ValueError:
        return None


def _optional_int(value: str) -> int | None:
    clean_value = value.strip()
    if not clean_value:
        return None
    try:
        return int(float(clean_value))
    except ValueError:
        return None


def _seed_cities(connection: sqlite3.Connection, city_seed_path: Path) -> None:
    if city_seed_path.exists():
        with city_seed_path.open("r", encoding="utf-8", newline="") as file:
            rows = [
                (
                    row["city_name"],
                    row.get("ascii_name") or row["city_name"],
                    row["country"],
                    row.get("country_code", ""),
                    row.get("admin_region", ""),
                    float(row["latitude"]),
                    float(row["longitude"]),
                    row["timezone"],
                    _optional_int(row.get("population", "")),
                    row.get("search_name") or _search_name(row["city_name"], row.get("ascii_name", "")),
                )
                for row in csv.DictReader(file)
            ]
    else:
        rows = [
            (city, city, country, "", "", latitude, longitude, timezone, None, _search_name(city, ""))
            for city, country, latitude, longitude, timezone in SEED_CITIES
        ]
    connection.executemany(
        """
        INSERT INTO City (
            city_name, ascii_name, country, country_code, admin_region,
            latitude, longitude, timezone, population, search_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(city_name, country) DO UPDATE SET
            ascii_name = excluded.ascii_name,
            country_code = excluded.country_code,
            admin_region = excluded.admin_region,
            latitude = excluded.latitude,
            longitude = excluded.longitude,
            timezone = excluded.timezone,
            population = excluded.population,
            search_name = excluded.search_name
        """,
        rows,
    )


def _seed_telescope_catalog(connection: sqlite3.Connection, catalog_path: Path | None = None) -> None:
    catalog_rows = _telescope_catalog_rows(catalog_path)
    brand_names = sorted({row[0] for row in catalog_rows} | set(TELESCOPE_BRANDS))
    brand_count = connection.execute("SELECT COUNT(*) FROM TelescopeBrand").fetchone()[0]
    if brand_count < len(brand_names):
        connection.executemany(
            "INSERT OR IGNORE INTO TelescopeBrand (name) VALUES (?)",
            [(name,) for name in brand_names],
        )

    brand_ids = {
        row[1]: row[0]
        for row in connection.execute("SELECT id, name FROM TelescopeBrand").fetchall()
    }
    connection.executemany(
        """
        INSERT INTO TelescopeModel (
            brand_id, name, optical_type, aperture_mm, focal_length_mm,
            focal_ratio, mount_type, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(brand_id, name) DO UPDATE SET
            optical_type = excluded.optical_type,
            aperture_mm = excluded.aperture_mm,
            focal_length_mm = excluded.focal_length_mm,
            focal_ratio = excluded.focal_ratio,
            mount_type = excluded.mount_type,
            notes = excluded.notes
        """,
        [
            (brand_ids[brand], name, optical_type, aperture, focal, ratio, mount, notes)
            for brand, name, optical_type, aperture, focal, ratio, mount, notes in catalog_rows
        ],
    )


def _telescope_catalog_rows(catalog_path: Path | None) -> list[tuple]:
    if catalog_path and catalog_path.exists():
        with catalog_path.open("r", encoding="utf-8", newline="") as file:
            return [
                (
                    row["brand"],
                    row["model"],
                    row["optical_type"],
                    int(float(row["aperture_mm"])),
                    int(float(row["focal_length_mm"])),
                    _optional_float(row.get("focal_ratio", "")),
                    row["mount_type"],
                    row.get("notes", ""),
                )
                for row in csv.DictReader(file)
            ]
    return [
        (brand, name, optical_type, aperture, focal, round(focal / aperture, 1), mount, "Legacy NightScope seed.")
        for brand, name, optical_type, aperture, focal, mount in TELESCOPE_MODELS
    ]


def _seed_optics_catalog(connection: sqlite3.Connection, eyepiece_path: Path | None = None, barlow_path: Path | None = None) -> None:
    connection.executemany(
        """
        INSERT INTO EyepieceCatalog (brand, model, focal_length_mm, apparent_field_deg, barrel_size, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(brand, model, focal_length_mm) DO UPDATE SET
            apparent_field_deg = excluded.apparent_field_deg,
            barrel_size = excluded.barrel_size,
            notes = excluded.notes
        """,
        _eyepiece_catalog_rows(eyepiece_path),
    )

    connection.executemany(
        """
        INSERT INTO BarlowCatalog (brand, model, multiplier, barrel_size, notes)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(brand, model, multiplier) DO UPDATE SET
            barrel_size = excluded.barrel_size,
            notes = excluded.notes
        """,
        _barlow_catalog_rows(barlow_path),
    )


def _eyepiece_catalog_rows(eyepiece_path: Path | None) -> list[tuple]:
    if eyepiece_path and eyepiece_path.exists():
        with eyepiece_path.open("r", encoding="utf-8", newline="") as file:
            return [
                (
                    row["brand"],
                    row["model"],
                    float(row["focal_length_mm"]),
                    float(row["apparent_field_deg"]),
                    row.get("barrel_size", ""),
                    row.get("notes", ""),
                )
                for row in csv.DictReader(file)
            ]
    return [(brand, model, focal, field, "", "Legacy NightScope seed.") for brand, model, focal, field in EYEPIECE_CATALOG]


def _barlow_catalog_rows(barlow_path: Path | None) -> list[tuple]:
    if barlow_path and barlow_path.exists():
        with barlow_path.open("r", encoding="utf-8", newline="") as file:
            return [
                (
                    row["brand"],
                    row["model"],
                    float(row["multiplier"]),
                    row.get("barrel_size", ""),
                    row.get("notes", ""),
                )
                for row in csv.DictReader(file)
            ]
    return [(brand, model, multiplier, "", "Legacy NightScope seed.") for brand, model, multiplier in BARLOW_CATALOG]


def _seed_object_images(connection: sqlite3.Connection, images_path: Path | None = None) -> None:
    connection.executemany(
        """
        INSERT INTO ObjectImages (
            object_id, image_path, thumbnail_path, attribution, source_url, license, verified
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(object_id) DO UPDATE SET
            image_path = excluded.image_path,
            thumbnail_path = excluded.thumbnail_path,
            attribution = excluded.attribution,
            source_url = excluded.source_url,
            license = excluded.license,
            verified = excluded.verified
        """,
        _object_image_rows(images_path),
    )


def _object_image_rows(images_path: Path | None) -> list[tuple]:
    if images_path and images_path.exists():
        with images_path.open("r", encoding="utf-8", newline="") as file:
            return [
                (
                    row["object_id"],
                    row["image_path"],
                    row.get("thumbnail_path", ""),
                    row["attribution"],
                    row.get("source_url", ""),
                    row.get("license", ""),
                    1 if str(row.get("verified", "")).strip().lower() in {"1", "true", "yes"} else 0,
                )
                for row in csv.DictReader(file)
            ]
    return [(object_id, image_path, image_path, attribution, "", "NightScope local generated asset", 1) for object_id, image_path, attribution in OBJECT_IMAGES]


def _seed_object_descriptions(connection: sqlite3.Connection, descriptions_path: Path | None = None) -> None:
    if not descriptions_path or not descriptions_path.exists():
        return
    with descriptions_path.open("r", encoding="utf-8", newline="") as file:
        rows = [
            (
                row["object_id"],
                row["short_description"],
                row["observing_notes"],
                row.get("best_seen", ""),
                row.get("difficulty_naked_eye", ""),
                row.get("difficulty_binocular", ""),
                row.get("difficulty_small_scope", ""),
                row.get("difficulty_medium_scope", ""),
                row.get("difficulty_large_scope", ""),
            )
            for row in csv.DictReader(file)
        ]
    connection.executemany(
        """
        INSERT INTO ObjectDescription (
            object_id, short_description, observing_notes, best_seen,
            difficulty_naked_eye, difficulty_binocular, difficulty_small_scope,
            difficulty_medium_scope, difficulty_large_scope
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(object_id) DO UPDATE SET
            short_description = excluded.short_description,
            observing_notes = excluded.observing_notes,
            best_seen = excluded.best_seen,
            difficulty_naked_eye = excluded.difficulty_naked_eye,
            difficulty_binocular = excluded.difficulty_binocular,
            difficulty_small_scope = excluded.difficulty_small_scope,
            difficulty_medium_scope = excluded.difficulty_medium_scope,
            difficulty_large_scope = excluded.difficulty_large_scope
        """,
        rows,
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
                ("Occhio nudo", 1, "preset:naked-eye"),
            ],
        )


def _search_name(city_name: str, ascii_name: str) -> str:
    return " ".join({city_name.lower(), ascii_name.lower()}).strip()


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[2]
    initialize_database(base_dir / "data" / "nightscope.db", base_dir / "data" / "schema.sql")
    print("Database inizializzato:", base_dir / "data" / "nightscope.db")
