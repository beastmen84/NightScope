from __future__ import annotations

import csv
import json
import logging
import math
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
        connection.row_factory = sqlite3.Row
        connection.executescript(schema_sql)
        _migrate_database(connection)
        data_dir = seed_path.parent
        city_count = connection.execute("SELECT COUNT(*) FROM City").fetchone()[0]
        if city_count < 50:
            _seed_cities(connection, data_dir / "cities_seed.csv")
        _deduplicate_small_city_catalog(connection)
        _import_geonames_cities_if_available(connection, database_path.parent)
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
            "aliases": "TEXT",
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
    connection.execute("CREATE INDEX IF NOT EXISTS idx_city_coordinates ON City(latitude, longitude)")
    connection.execute("DROP INDEX IF EXISTS idx_city_unique_name_country")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS CityAlias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id INTEGER NOT NULL,
            alias TEXT NOT NULL,
            normalized_alias TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'geonames',
            FOREIGN KEY (city_id) REFERENCES City(id) ON DELETE CASCADE,
            UNIQUE (city_id, normalized_alias)
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_city_alias_normalized ON CityAlias(normalized_alias)")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS DataImportLog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_name TEXT NOT NULL UNIQUE,
            source_path TEXT NOT NULL,
            source_size INTEGER NOT NULL,
            source_mtime TEXT NOT NULL,
            imported_at TEXT NOT NULL,
            report_json TEXT NOT NULL
        )
        """
    )


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
                    row.get("aliases", ""),
                    row.get("search_name") or _search_name(row["city_name"], row.get("ascii_name", ""), row.get("aliases", "")),
                )
                for row in csv.DictReader(file)
                if row.get("city_name") and row.get("timezone")
            ]
    else:
        rows = [
            (city, city, country, "", "", latitude, longitude, timezone, None, "", _search_name(city, "", ""))
            for city, country, latitude, longitude, timezone in SEED_CITIES
        ]
    for row in rows:
        _upsert_seed_city(connection, row)
    _refresh_city_aliases(connection)


def _import_geonames_cities_if_available(connection: sqlite3.Connection, data_dir: Path) -> None:
    candidates = (
        data_dir / "cities15000.txt",
        data_dir / "geonames" / "cities15000.txt",
    )
    source_path = next((candidate for candidate in candidates if candidate.exists()), None)
    if source_path is None:
        logger.info("GeoNames cities15000.txt not found; using existing local city catalog.")
        return
    source_stat = source_path.stat()
    source_mtime = datetime.fromtimestamp(source_stat.st_mtime).isoformat(timespec="seconds")
    existing_import = connection.execute(
        """
        SELECT source_size, source_mtime, report_json
        FROM DataImportLog
        WHERE source_name = ?
        """,
        ("cities15000.txt",),
    ).fetchone()
    if (
        existing_import
        and int(existing_import["source_size"]) == source_stat.st_size
        and str(existing_import["source_mtime"]) == source_mtime
    ):
        logger.info("GeoNames cities15000 import already current: %s", existing_import["report_json"])
        return
    from astro_viewer.app.database.geonames_importer import import_geonames_cities

    country_info_path = _first_existing_path(
        data_dir / "countryInfo.txt",
        data_dir / "geonames" / "countryInfo.txt",
    )
    admin1_codes_path = _first_existing_path(
        data_dir / "admin1CodesASCII.txt",
        data_dir / "geonames" / "admin1CodesASCII.txt",
    )
    report = import_geonames_cities(
        connection,
        source_path,
        country_info_path=country_info_path,
        admin1_codes_path=admin1_codes_path,
    )
    payload = report.to_dict()
    payload["aliases_generated"] = report.aliases_added
    payload["db_size_bytes"] = _database_size_bytes(connection)
    connection.execute(
        """
        INSERT INTO DataImportLog (source_name, source_path, source_size, source_mtime, imported_at, report_json)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_name) DO UPDATE SET
            source_path = excluded.source_path,
            source_size = excluded.source_size,
            source_mtime = excluded.source_mtime,
            imported_at = excluded.imported_at,
            report_json = excluded.report_json
        """,
        (
            "cities15000.txt",
            str(source_path),
            source_stat.st_size,
            source_mtime,
            datetime.now().isoformat(timespec="seconds"),
            json.dumps(payload, ensure_ascii=True),
        ),
    )
    logger.info("GeoNames cities15000 import report: %s", json.dumps(payload, ensure_ascii=True))


def _first_existing_path(*paths: Path) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def _database_size_bytes(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA database_list").fetchone()
    if not row:
        return 0
    database_path = Path(row[2])
    try:
        return database_path.stat().st_size
    except OSError:
        return 0


def _upsert_seed_city(connection: sqlite3.Connection, row: tuple) -> None:
    (
        city_name,
        ascii_name,
        country,
        country_code,
        admin_region,
        latitude,
        longitude,
        timezone,
        population,
        aliases,
        search_name,
    ) = row
    existing = connection.execute(
        """
        SELECT id, latitude, longitude, timezone
        FROM City
        WHERE city_name = ?
          AND country = ?
        ORDER BY population DESC NULLS LAST, id
        LIMIT 1
        """,
        (city_name, country),
    ).fetchone()
    if existing and existing["timezone"] == timezone and _distance_km(latitude, longitude, existing["latitude"], existing["longitude"]) <= 5.0:
        connection.execute(
            """
            UPDATE City
            SET ascii_name = ?,
                country_code = ?,
                admin_region = ?,
                latitude = ?,
                longitude = ?,
                timezone = ?,
                population = ?,
                aliases = ?,
                search_name = ?
            WHERE id = ?
            """,
            (
                ascii_name,
                country_code,
                admin_region,
                latitude,
                longitude,
                timezone,
                population,
                aliases,
                search_name,
                existing["id"],
            ),
        )
        return
    connection.execute(
        """
        INSERT INTO City (
            city_name, ascii_name, country, country_code, admin_region,
            latitude, longitude, timezone, population, aliases, search_name
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row,
    )


def _refresh_city_aliases(connection: sqlite3.Connection) -> None:
    for row in connection.execute(
        "SELECT id, city_name, ascii_name, country, country_code, admin_region, aliases FROM City"
    ).fetchall():
        aliases = {
            row["city_name"],
            row["ascii_name"] or "",
            row["country"] or "",
            row["country_code"] or "",
            row["admin_region"] or "",
            *(row["aliases"] or "").split("|"),
        }
        connection.executemany(
            """
            INSERT OR IGNORE INTO CityAlias (city_id, alias, normalized_alias, source)
            VALUES (?, ?, ?, ?)
            """,
            [
                (row["id"], alias.strip(), _normalize_search(alias), "seed")
                for alias in aliases
                if alias and _normalize_search(alias)
            ],
        )


def _deduplicate_existing_cities(connection: sqlite3.Connection, proximity_km: float = 5.0) -> None:
    rows = connection.execute(
        """
        SELECT id, city_name, ascii_name, country, country_code, admin_region,
               latitude, longitude, timezone, population, aliases, search_name
        FROM City
        ORDER BY population DESC NULLS LAST, id
        """
    ).fetchall()
    canonical_rows: list[sqlite3.Row] = []
    deleted_ids: set[int] = set()
    for row in rows:
        if row["id"] in deleted_ids:
            continue
        duplicate = _matching_canonical_city(row, canonical_rows, proximity_km)
        if duplicate is None:
            canonical_rows.append(row)
            continue
        _merge_existing_city(connection, duplicate, row)
        connection.execute("DELETE FROM CityAlias WHERE city_id = ?", (row["id"],))
        connection.execute("DELETE FROM City WHERE id = ?", (row["id"],))
        deleted_ids.add(row["id"])
    if deleted_ids:
        logger.info("Deduplicated %d city rows into canonical records.", len(deleted_ids))


def _deduplicate_small_city_catalog(connection: sqlite3.Connection) -> None:
    city_count = connection.execute("SELECT COUNT(*) FROM City").fetchone()[0]
    if city_count > 5000:
        logger.info("Skipping legacy city deduplication for large catalog: %d rows.", city_count)
        return
    _deduplicate_existing_cities(connection)


def _matching_canonical_city(row: sqlite3.Row, canonical_rows: list[sqlite3.Row], proximity_km: float) -> sqlite3.Row | None:
    row_aliases = _city_alias_set(row)
    for candidate in canonical_rows:
        if (row["country_code"] or "") != (candidate["country_code"] or ""):
            continue
        if (row["timezone"] or "") != (candidate["timezone"] or ""):
            continue
        if _distance_km(row["latitude"], row["longitude"], candidate["latitude"], candidate["longitude"]) > proximity_km:
            continue
        if row_aliases & _city_alias_set(candidate):
            return candidate
    return None


def _merge_existing_city(connection: sqlite3.Connection, canonical: sqlite3.Row, duplicate: sqlite3.Row) -> None:
    aliases = _raw_alias_set(canonical) | _raw_alias_set(duplicate)
    search_name = _search_name(
        canonical["city_name"],
        canonical["ascii_name"] or duplicate["ascii_name"] or canonical["city_name"],
        aliases_to_text(aliases),
    )
    population = max(canonical["population"] or 0, duplicate["population"] or 0) or None
    connection.execute(
        """
        UPDATE City
        SET aliases = ?, search_name = ?, population = ?
        WHERE id = ?
        """,
        (aliases_to_text(aliases), search_name, population, canonical["id"]),
    )
    _refresh_city_aliases_for_row(connection, canonical["id"], aliases)


def _refresh_city_aliases_for_row(connection: sqlite3.Connection, city_id: int, aliases: set[str]) -> None:
    connection.executemany(
        """
        INSERT OR IGNORE INTO CityAlias (city_id, alias, normalized_alias, source)
        VALUES (?, ?, ?, ?)
        """,
        [
            (city_id, alias.strip(), _normalize_search(alias), "dedupe")
            for alias in aliases
            if alias and _normalize_search(alias)
        ],
    )


def _city_alias_set(row: sqlite3.Row) -> set[str]:
    return {_normalize_search(alias) for alias in _raw_alias_set(row) if _normalize_search(alias)}


def _raw_alias_set(row: sqlite3.Row) -> set[str]:
    return {
        row["city_name"] or "",
        row["ascii_name"] or "",
        row["country"] or "",
        row["country_code"] or "",
        row["admin_region"] or "",
        *(row["aliases"] or "").split("|"),
        *(row["search_name"] or "").split(),
    }


def aliases_to_text(aliases: set[str]) -> str:
    return "|".join(sorted(alias.strip() for alias in aliases if alias and alias.strip()))


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


def _search_name(city_name: str, ascii_name: str, aliases: str) -> str:
    values = {city_name.lower(), ascii_name.lower()}
    values.update(alias.strip().lower() for alias in aliases.split("|") if alias.strip())
    return " ".join(sorted(value for value in values if value)).strip()


def _normalize_search(value: str) -> str:
    import unicodedata

    normalized = unicodedata.normalize("NFKD", value.strip().lower())
    ascii_value = "".join(character for character in normalized if not unicodedata.combining(character))
    return " ".join(ascii_value.replace("-", " ").replace("_", " ").replace(",", " ").split())


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(value), math.sqrt(1 - value))


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[2]
    initialize_database(base_dir / "data" / "nightscope.db", base_dir / "data" / "schema.sql")
    print("Database inizializzato:", base_dir / "data" / "nightscope.db")
