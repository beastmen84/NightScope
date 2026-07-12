from __future__ import annotations

import csv
import json
import logging
import shutil
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Callable


logger = logging.getLogger(__name__)
ProgressCallback = Callable[[str], None]
SCHEMA_VERSION = 10
CATALOGUE_OBSERVATION_TYPES = {"WideField", "General", "HighMagnification"}
REQUIRED_TABLES = {
    "City",
    "CityAlias",
    "DataImportLog",
    "CatalogueObject",
    "CatalogueDesignation",
    "WeatherCache",
    "ObservationHistory",
    "TelescopeBrand",
    "TelescopeModel",
    "EyepieceCatalog",
    "BarlowCatalog",
    "BinocularCatalog",
    "FilterCatalog",
    "ReducerCatalog",
    "SkyQualityEstimate",
    "ObjectImages",
    "ObjectDescription",
    "ObjectCuriosity",
    "EquipmentProfile",
    "EquipmentProfileTelescope",
    "EquipmentProfileEyepiece",
    "EquipmentProfileBarlow",
    "EquipmentProfileBinocular",
    "EquipmentProfileFilter",
    "EquipmentProfileReducer",
}
SEEDED_TABLES = {
    "CatalogueObject": "catalogue_objects_seed.csv",
    "CatalogueDesignation": "catalogue_designations_seed.csv",
    "TelescopeBrand": "telescope_catalog_seed.csv",
    "TelescopeModel": "telescope_catalog_seed.csv",
    "EyepieceCatalog": "eyepiece_catalog_seed.csv",
    "BarlowCatalog": "barlow_catalog_seed.csv",
    "BinocularCatalog": "binocular_catalog_seed.csv",
    "FilterCatalog": "filter_catalog_seed.csv",
    "ReducerCatalog": "reducer_catalog_seed.csv",
    "ObjectImages": "object_images_seed.csv",
    "ObjectDescription": "object_descriptions_seed.csv",
    "ObjectCuriosity": "object_curiosities_seed.csv",
    "EquipmentProfile": "",
}

OBJECT_IMAGES = [
    (
        "sun",
        "resources/images/solar_system/sun.jpg",
        "NASA/GSFC/Solar Dynamics Observatory",
        "https://science.nasa.gov/photojournal/image-of-sun-from-nasas-solar-dynamics-observatory/",
    ),
    (
        "moon",
        "resources/images/solar_system/moon.jpg",
        "NASA/JPL/USGS",
        "https://science.nasa.gov/photojournal/earths-moon/",
    ),
    (
        "mercury",
        "resources/images/solar_system/mercury.jpg",
        "NASA/Johns Hopkins University Applied Physics Laboratory/Carnegie Institution of Washington",
        "https://science.nasa.gov/photojournal/mercury-in-color/",
    ),
    (
        "venus",
        "resources/images/solar_system/venus.jpg",
        "NASA/JPL-Caltech",
        "https://science.nasa.gov/photojournal/venus-from-mariner-10/",
    ),
    (
        "mars",
        "resources/images/solar_system/mars.jpg",
        "NASA/JPL/USGS",
        "https://science.nasa.gov/photojournal/global-color-views-of-mars/",
    ),
    (
        "jupiter",
        "resources/images/solar_system/jupiter.jpg",
        "NASA/JPL/Space Science Institute",
        "https://science.nasa.gov/resource/cassini-jupiter-portrait/",
    ),
    (
        "saturn",
        "resources/images/solar_system/saturn.jpg",
        "NASA/JPL/Space Science Institute",
        "https://science.nasa.gov/image-detail/amf-pia11141/",
    ),
    (
        "uranus",
        "resources/images/solar_system/uranus.jpg",
        "NASA/JPL-Caltech",
        "https://science.nasa.gov/photojournal/uranus-as-seen-by-nasas-voyager-2/",
    ),
    (
        "neptune",
        "resources/images/solar_system/neptune.jpg",
        "NASA/JPL",
        "https://science.nasa.gov/photojournal/neptune-full-disk-view/",
    ),
    (
        "messier-default-cluster",
        "resources/images/m13.svg",
        "NightScope generated local SVG",
        "",
    ),
    (
        "messier-default-nebula",
        "resources/images/m57.svg",
        "NightScope generated local SVG",
        "",
    ),
    (
        "messier-default-galaxy",
        "resources/images/m31.svg",
        "NightScope generated local SVG",
        "",
    ),
]


def initialize_database(
    database_path: Path,
    schema_path: Path,
    progress_callback: ProgressCallback | None = None,
    geonames_data_dir: Path | None = None,
) -> None:
    _notify_progress(progress_callback, "Creazione database...")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = schema_path.read_text(encoding="utf-8")
    catalogue_objects_path = schema_path.with_name("catalogue_objects_seed.csv")

    if database_path.exists() and not _database_is_healthy(database_path):
        _notify_progress(progress_callback, "Ricostruzione database locale...")
        _quarantine_database(database_path)
    elif database_path.exists():
        _backup_database(database_path)

    try:
        _build_database(
            database_path,
            schema_sql,
            catalogue_objects_path,
            progress_callback=progress_callback,
            geonames_data_dir=geonames_data_dir,
        )
    except sqlite3.DatabaseError as exc:
        if not _is_recoverable_database_error(exc):
            logger.exception("Database bootstrap failed during schema migration.")
            raise
        logger.warning("Database appears damaged; rebuilding from local schema.", exc_info=True)
        _notify_progress(progress_callback, "Ricostruzione database locale...")
        _quarantine_database(database_path)
        _build_database(
            database_path,
            schema_sql,
            catalogue_objects_path,
            progress_callback=progress_callback,
            geonames_data_dir=geonames_data_dir,
        )


def database_initialization_required(
    database_path: Path,
    schema_path: Path,
    geonames_data_dir: Path | None = None,
) -> bool:
    if not database_path.exists():
        return True
    try:
        with closing(sqlite3.connect(database_path)) as connection:
            connection.row_factory = sqlite3.Row
            tables = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            if not REQUIRED_TABLES.issubset(tables):
                return True
            data_dir = schema_path.parent
            for table_name, seed_name in SEEDED_TABLES.items():
                if seed_name and not (data_dir / seed_name).exists():
                    continue
                if _table_count(connection, table_name) == 0:
                    return True
            geonames_source_dir = geonames_data_dir or database_path.parent
            if _geonames_import_needed(connection, geonames_source_dir):
                return True
    except sqlite3.DatabaseError:
        logger.warning("Database preflight check failed; initialization is required.", exc_info=True)
        return True
    return False


def _build_database(
    database_path: Path,
    schema_sql: str,
    catalogue_objects_path: Path,
    progress_callback: ProgressCallback | None = None,
    geonames_data_dir: Path | None = None,
) -> None:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.row_factory = sqlite3.Row
        connection.executescript(schema_sql)
        existing_schema_version = _schema_version(connection)
        _migrate_database(connection)
        if existing_schema_version <= SCHEMA_VERSION:
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        data_dir = catalogue_objects_path.parent
        geonames_source_dir = geonames_data_dir or database_path.parent
        _notify_progress(progress_callback, "Importazione cataloghi...")
        _import_geonames_cities_if_available(
            connection,
            geonames_source_dir,
            warn_if_missing=geonames_source_dir == data_dir,
            progress_callback=progress_callback,
        )
        _seed_catalogue(
            connection,
            catalogue_objects_path,
            data_dir / "catalogue_designations_seed.csv",
        )
        _seed_telescope_catalog(connection, data_dir / "telescope_catalog_seed.csv")
        _seed_optics_catalog(
            connection,
            data_dir / "eyepiece_catalog_seed.csv",
            data_dir / "barlow_catalog_seed.csv",
        )
        _seed_binocular_catalog(connection, data_dir / "binocular_catalog_seed.csv")
        _seed_filters_reducers_catalog(
            connection,
            data_dir / "filter_catalog_seed.csv",
            data_dir / "reducer_catalog_seed.csv",
        )
        _seed_object_images(connection, data_dir / "object_images_seed.csv")
        _seed_object_descriptions(connection, data_dir / "object_descriptions_seed.csv")
        _seed_object_curiosities(connection, data_dir / "object_curiosities_seed.csv")
        _seed_default_profiles(connection)
        _notify_progress(progress_callback, "Finalizzazione...")
        connection.commit()
    logger.info("Database ready.")


def _notify_progress(progress_callback: ProgressCallback | None, message: str) -> None:
    if progress_callback:
        progress_callback(message)


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
    _add_columns(
        connection,
        "TelescopeModel",
        {
            "focal_ratio": "REAL",
            "notes": "TEXT",
            "is_builtin": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    _add_columns(
        connection,
        "EyepieceCatalog",
        {
            "eyepiece_type": "TEXT NOT NULL DEFAULT 'Fixed'",
            "min_focal_length_mm": "REAL",
            "max_focal_length_mm": "REAL",
            "afov_min": "REAL",
            "afov_max": "REAL",
            "barrel_size": "TEXT",
            "zoom_click_positions_mm": "TEXT",
            "notes": "TEXT",
            "is_builtin": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    _add_columns(
        connection,
        "BarlowCatalog",
        {
            "barrel_size": "TEXT",
            "notes": "TEXT",
            "is_builtin": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    _add_columns(
        connection,
        "BinocularCatalog",
        {"is_builtin": "INTEGER NOT NULL DEFAULT 0"},
    )
    _migrate_catalogue_tables(connection)
    _migrate_binocular_catalog(connection)
    _ensure_profile_binocular_table(connection)
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
    connection.execute(
        """
        UPDATE ObjectDescription
        SET best_seen = 'Tutte le fasi tranne Luna piena'
        WHERE object_id = 'moon'
          AND best_seen = 'Tutte le fasi tranne Luna piena piena'
        """
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


def _schema_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _add_columns(connection: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    existing = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, definition in columns.items():
        if column_name not in existing:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _migrate_catalogue_tables(connection: sqlite3.Connection) -> None:
    if not _table_exists(connection, "MessierObject"):
        return
    _add_columns(
        connection,
        "MessierObject",
        {
            "max_angular_size_deg": "REAL",
            "recommended_observation_type": "TEXT",
        },
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO CatalogueObject (
            object_id, nome, tipo, costellazione, magnitudine,
            ascensione_retta, declinazione, dimensione_apparente,
            max_angular_size_deg, recommended_observation_type, descrizione
        )
        SELECT
            'messier-' || messier_id, nome, tipo, costellazione, magnitudine,
            ascensione_retta, declinazione, dimensione_apparente,
            max_angular_size_deg, recommended_observation_type, descrizione
        FROM MessierObject
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO CatalogueDesignation (
            catalogue, designation, object_id, sort_index, is_primary
        )
        SELECT
            'Messier', messier_id, 'messier-' || messier_id,
            CAST(SUBSTR(messier_id, 2) AS INTEGER), 1
        FROM MessierObject
        """
    )
    connection.execute("DROP TABLE MessierObject")


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def _migrate_binocular_catalog(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS BinocularCatalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            magnification INTEGER NOT NULL,
            objective_diameter_mm INTEGER NOT NULL,
            image_stabilized INTEGER NOT NULL DEFAULT 0,
            is_builtin INTEGER NOT NULL DEFAULT 0,
            UNIQUE (brand, model, magnification, objective_diameter_mm)
        )
        """
    )
    existing_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(BinocularCatalog)").fetchall()
    }
    expected_columns = {
        "id",
        "brand",
        "model",
        "magnification",
        "objective_diameter_mm",
        "image_stabilized",
        "is_builtin",
    }
    if existing_columns == expected_columns:
        return
    connection.execute("DROP TABLE IF EXISTS BinocularCatalog_new")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS BinocularCatalog_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            magnification INTEGER NOT NULL,
            objective_diameter_mm INTEGER NOT NULL,
            image_stabilized INTEGER NOT NULL DEFAULT 0,
            is_builtin INTEGER NOT NULL DEFAULT 0,
            UNIQUE (brand, model, magnification, objective_diameter_mm)
        )
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO BinocularCatalog_new (
            id, brand, model, magnification, objective_diameter_mm,
            image_stabilized, is_builtin
        )
        SELECT id, brand, model, magnification, objective_diameter_mm,
               image_stabilized, is_builtin
        FROM BinocularCatalog
        """
    )
    connection.execute("DROP TABLE BinocularCatalog")
    connection.execute("ALTER TABLE BinocularCatalog_new RENAME TO BinocularCatalog")


def _ensure_profile_binocular_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS EquipmentProfileBinocular (
            profile_id INTEGER NOT NULL,
            binocular_id TEXT NOT NULL,
            PRIMARY KEY (profile_id, binocular_id),
            FOREIGN KEY (profile_id) REFERENCES EquipmentProfile(id) ON DELETE CASCADE
        )
        """
    )


def _database_is_healthy(database_path: Path) -> bool:
    try:
        with closing(sqlite3.connect(database_path)) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.DatabaseError:
        logger.warning("Database integrity check failed.", exc_info=True)
        return False
    return bool(result and result[0] == "ok")


def _table_count(connection: sqlite3.Connection, table_name: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _geonames_import_needed(
    connection: sqlite3.Connection,
    data_dir: Path,
) -> bool:
    candidates = [
        data_dir / "cities15000.txt",
        data_dir / "geonames" / "cities15000.txt",
    ]
    source_path = _first_existing_path(*candidates)
    if source_path is None:
        return False
    if _table_count(connection, "City") == 0:
        return True

    source_stat = source_path.stat()
    source_mtime = datetime.fromtimestamp(source_stat.st_mtime).isoformat(timespec="seconds")
    source_data_dir = source_path.parent
    country_info_path = _first_existing_path(source_data_dir / "countryInfo.txt", source_data_dir / "geonames" / "countryInfo.txt")
    admin1_codes_path = _first_existing_path(source_data_dir / "admin1CodesASCII.txt", source_data_dir / "geonames" / "admin1CodesASCII.txt")
    existing_import = connection.execute(
        """
        SELECT source_size, source_mtime, report_json
        FROM DataImportLog
        WHERE source_name = ?
        """,
        ("cities15000.txt",),
    ).fetchone()
    existing_report = _json_dict(existing_import["report_json"]) if existing_import else {}
    return not (
        existing_import
        and int(existing_import["source_size"]) == source_stat.st_size
        and str(existing_import["source_mtime"]) == source_mtime
        and existing_report.get("country_info") == _file_signature(country_info_path)
        and existing_report.get("admin1_codes") == _file_signature(admin1_codes_path)
    )


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
    parsed = _optional_float(value)
    return int(parsed) if parsed is not None else None


def _csv_bool(value: object) -> int:
    return 1 if str(value or "").strip().casefold() in {"1", "true", "yes", "si", "sì"} else 0


def _import_geonames_cities_if_available(
    connection: sqlite3.Connection,
    data_dir: Path,
    warn_if_missing: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> None:
    candidates = [
        data_dir / "cities15000.txt",
        data_dir / "geonames" / "cities15000.txt",
    ]
    source_path = next((candidate for candidate in candidates if candidate.exists()), None)
    if source_path is None:
        log = logger.warning if warn_if_missing else logger.info
        log("GeoNames cities15000.txt not found; city catalog was not imported.")
        return
    source_stat = source_path.stat()
    source_mtime = datetime.fromtimestamp(source_stat.st_mtime).isoformat(timespec="seconds")
    source_data_dir = source_path.parent
    country_info_path = _first_existing_path(
        source_data_dir / "countryInfo.txt",
        source_data_dir / "geonames" / "countryInfo.txt",
    )
    admin1_codes_path = _first_existing_path(
        source_data_dir / "admin1CodesASCII.txt",
        source_data_dir / "geonames" / "admin1CodesASCII.txt",
    )
    country_info_signature = _file_signature(country_info_path)
    admin1_codes_signature = _file_signature(admin1_codes_path)
    existing_import = connection.execute(
        """
        SELECT source_size, source_mtime, report_json
        FROM DataImportLog
        WHERE source_name = ?
        """,
        ("cities15000.txt",),
    ).fetchone()
    existing_report = _json_dict(existing_import["report_json"]) if existing_import else {}
    if (
        existing_import
        and int(existing_import["source_size"]) == source_stat.st_size
        and str(existing_import["source_mtime"]) == source_mtime
        and existing_report.get("country_info") == country_info_signature
        and existing_report.get("admin1_codes") == admin1_codes_signature
    ):
        logger.info("GeoNames cities15000 import already current: %s", existing_import["report_json"])
        return
    from astro_viewer.app.database.geonames_importer import import_geonames_cities

    def report_progress(rows: int) -> None:
        _notify_progress(progress_callback, f"Importazione catalogo città... {rows} righe")

    existing_city_count = connection.execute("SELECT COUNT(*) FROM City").fetchone()[0]
    if existing_city_count:
        logger.info("GeoNames cities15000 changed; rebuilding city catalog from source file.")
        connection.execute("DELETE FROM CityAlias")
        connection.execute("DELETE FROM City")

    report = import_geonames_cities(
        connection,
        source_path,
        country_info_path=country_info_path,
        admin1_codes_path=admin1_codes_path,
        progress_callback=report_progress if progress_callback else None,
    )
    payload = report.to_dict()
    payload["aliases_generated"] = report.aliases_added
    payload["db_size_bytes"] = _database_size_bytes(connection)
    payload["rebuilt_city_catalog"] = bool(existing_city_count)
    payload["country_info"] = country_info_signature
    payload["admin1_codes"] = admin1_codes_signature
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


def _file_signature(path: Path | None) -> dict | None:
    if path is None:
        return None
    stat = path.stat()
    return {
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }


def _json_dict(value: str | None) -> dict:
    if not value:
        return {}
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _database_size_bytes(connection: sqlite3.Connection) -> int:
    row = connection.execute("PRAGMA database_list").fetchone()
    if not row:
        return 0
    database_path = Path(row[2])
    try:
        return database_path.stat().st_size
    except OSError:
        return 0


def _seed_catalogue(
    connection: sqlite3.Connection,
    objects_path: Path,
    designations_path: Path,
) -> None:
    if not objects_path.exists() or not designations_path.exists():
        raise FileNotFoundError("Missing generic catalogue seed CSV.")
    with objects_path.open("r", encoding="utf-8", newline="") as file:
        source_object_rows = list(csv.DictReader(file))
    with designations_path.open("r", encoding="utf-8", newline="") as file:
        source_designation_rows = list(csv.DictReader(file))
    _validate_catalogue_seed(source_object_rows, source_designation_rows)

    object_rows = [
        (
            row["object_id"],
            row["nome"],
            row["tipo"],
            row["costellazione"],
            _optional_float(row["magnitudine"]),
            row["ascensione_retta"],
            row["declinazione"],
            row["dimensione_apparente"],
            _optional_float(row["max_angular_size_deg"]),
            row["recommended_observation_type"],
            row["descrizione"],
        )
        for row in source_object_rows
    ]
    connection.executemany(
        """
        INSERT INTO CatalogueObject (
            object_id, nome, tipo, costellazione, magnitudine,
            ascensione_retta, declinazione, dimensione_apparente,
            max_angular_size_deg, recommended_observation_type, descrizione
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(object_id) DO UPDATE SET
            max_angular_size_deg = excluded.max_angular_size_deg,
            recommended_observation_type = excluded.recommended_observation_type
        """,
        object_rows,
    )

    designation_rows = [
        (
            row["catalogue"],
            row["designation"],
            row["object_id"],
            int(row["sort_index"]) if row["sort_index"].strip() else None,
            1 if row["is_primary"].strip().casefold() in {"1", "true", "yes"} else 0,
        )
        for row in source_designation_rows
    ]
    connection.executemany(
        """
        INSERT INTO CatalogueDesignation (
            catalogue, designation, object_id, sort_index, is_primary
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(catalogue, designation) DO UPDATE SET
            object_id = excluded.object_id,
            sort_index = excluded.sort_index,
            is_primary = excluded.is_primary
        """,
        designation_rows,
    )


def _validate_catalogue_seed(
    object_rows: list[dict[str, str]],
    designation_rows: list[dict[str, str]],
) -> None:
    object_ids: dict[str, str] = {}
    for row in object_rows:
        object_id = row["object_id"].strip()
        normalized_id = object_id.casefold()
        if not object_id:
            raise ValueError("Catalogue seed contains an empty object_id.")
        if normalized_id in object_ids:
            raise ValueError(f"Duplicate catalogue object_id: {object_id}")
        object_ids[normalized_id] = object_id
        if not row["nome"].strip() or not row["tipo"].strip():
            raise ValueError(f"Catalogue object {object_id} is missing name or type.")
        if row["recommended_observation_type"] not in CATALOGUE_OBSERVATION_TYPES:
            raise ValueError(f"Invalid observation type for {object_id}.")
        max_size = _optional_float(row["max_angular_size_deg"])
        if max_size is None or max_size <= 0:
            raise ValueError(f"Invalid angular size for {object_id}.")

    normalized_designations: set[tuple[str, str]] = set()
    object_catalogues: set[tuple[str, str]] = set()
    primary_counts: Counter[str] = Counter()
    designation_counts: Counter[str] = Counter()
    sort_indices: set[tuple[str, int]] = set()
    for row in designation_rows:
        catalogue = row["catalogue"].strip()
        designation = row["designation"].strip()
        object_id = row["object_id"].strip()
        normalized_object_id = object_id.casefold()
        if normalized_object_id not in object_ids:
            raise ValueError(f"Designation {catalogue} {designation} references unknown {object_id}.")
        normalized_key = (catalogue.casefold(), designation.casefold())
        if not catalogue or not designation or normalized_key in normalized_designations:
            raise ValueError(f"Duplicate or empty catalogue designation: {catalogue} {designation}")
        normalized_designations.add(normalized_key)
        object_catalogue_key = (normalized_object_id, catalogue.casefold())
        if object_catalogue_key in object_catalogues:
            raise ValueError(f"Object {object_id} has multiple {catalogue} designations.")
        object_catalogues.add(object_catalogue_key)
        designation_counts[normalized_object_id] += 1

        sort_index_text = row["sort_index"].strip()
        if sort_index_text:
            sort_index = int(sort_index_text)
            if sort_index <= 0 or (catalogue.casefold(), sort_index) in sort_indices:
                raise ValueError(f"Invalid or duplicate sort index for {catalogue} {designation}.")
            sort_indices.add((catalogue.casefold(), sort_index))

        primary_value = row["is_primary"].strip().casefold()
        if primary_value not in {"0", "1", "false", "true", "no", "yes"}:
            raise ValueError(f"Invalid primary flag for {catalogue} {designation}.")
        if primary_value in {"1", "true", "yes"}:
            primary_counts[normalized_object_id] += 1

    for normalized_id, object_id in object_ids.items():
        if designation_counts[normalized_id] == 0:
            raise ValueError(f"Catalogue object {object_id} has no designation.")
        if primary_counts[normalized_id] != 1:
            raise ValueError(f"Catalogue object {object_id} must have one primary designation.")


def _seed_telescope_catalog(connection: sqlite3.Connection, catalog_path: Path | None = None) -> None:
    catalog_rows = _telescope_catalog_rows(catalog_path)
    brand_names = sorted({row[0] for row in catalog_rows})
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
            focal_ratio, mount_type, notes, is_builtin
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(brand_id, name) DO UPDATE SET is_builtin = 1
        """,
        [
            (brand_ids[brand], name, optical_type, aperture, focal, ratio, mount, notes)
            for brand, name, optical_type, aperture, focal, ratio, mount, notes in catalog_rows
        ],
    )


def _telescope_catalog_rows(catalog_path: Path | None) -> list[tuple]:
    if not catalog_path or not catalog_path.exists():
        raise FileNotFoundError("Missing telescope catalog seed CSV.")
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


def _seed_optics_catalog(connection: sqlite3.Connection, eyepiece_path: Path | None = None, barlow_path: Path | None = None) -> None:
    connection.executemany(
        """
        INSERT INTO EyepieceCatalog (
            brand, model, eyepiece_type, focal_length_mm, min_focal_length_mm,
            max_focal_length_mm, apparent_field_deg, afov_min, afov_max, barrel_size,
            zoom_click_positions_mm, notes, is_builtin
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(brand, model, focal_length_mm) DO UPDATE SET is_builtin = 1
        """,
        _eyepiece_catalog_rows(eyepiece_path),
    )
    _backfill_zoom_click_positions(connection)

    connection.executemany(
        """
        INSERT INTO BarlowCatalog (
            brand, model, multiplier, barrel_size, notes, is_builtin
        )
        VALUES (?, ?, ?, ?, ?, 1)
        ON CONFLICT(brand, model, multiplier) DO UPDATE SET is_builtin = 1
        """,
        _barlow_catalog_rows(barlow_path),
    )


def _eyepiece_catalog_rows(eyepiece_path: Path | None) -> list[tuple]:
    if not eyepiece_path or not eyepiece_path.exists():
        raise FileNotFoundError("Missing eyepiece catalog seed CSV.")
    with eyepiece_path.open("r", encoding="utf-8", newline="") as file:
        return [
            (
                row["brand"],
                row["model"],
                row.get("eyepiece_type", "Fixed") or "Fixed",
                float(row["focal_length_mm"]),
                _optional_float(row.get("min_focal_length_mm", "")),
                _optional_float(row.get("max_focal_length_mm", "")),
                float(row["apparent_field_deg"]),
                _optional_float(row.get("afov_min", "")),
                _optional_float(row.get("afov_max", "")),
                row.get("barrel_size", ""),
                row.get("zoom_click_positions_mm", ""),
                row.get("notes", ""),
            )
            for row in csv.DictReader(file)
        ]


def _backfill_zoom_click_positions(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        UPDATE EyepieceCatalog
        SET zoom_click_positions_mm = ?
        WHERE brand = ? AND model = ? AND eyepiece_type = 'Zoom'
          AND (zoom_click_positions_mm IS NULL OR trim(zoom_click_positions_mm) = '')
        """,
        ("24;20;16;12;8", "Baader", "Hyperion Zoom 8-24 mm"),
    )


def _barlow_catalog_rows(barlow_path: Path | None) -> list[tuple]:
    if not barlow_path or not barlow_path.exists():
        raise FileNotFoundError("Missing Barlow catalog seed CSV.")
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


def _seed_binocular_catalog(connection: sqlite3.Connection, binocular_path: Path | None = None) -> None:
    connection.executemany(
        """
        INSERT INTO BinocularCatalog (
            brand, model, magnification, objective_diameter_mm,
            image_stabilized, is_builtin
        )
        VALUES (?, ?, ?, ?, ?, 1)
        ON CONFLICT(brand, model, magnification, objective_diameter_mm)
        DO UPDATE SET is_builtin = 1
        """,
        _binocular_catalog_rows(binocular_path),
    )


def _binocular_catalog_rows(binocular_path: Path | None) -> list[tuple]:
    if not binocular_path or not binocular_path.exists():
        raise FileNotFoundError("Missing binocular catalog seed CSV.")
    with binocular_path.open("r", encoding="utf-8", newline="") as file:
        return [
            (
                row["brand"],
                row["model"],
                int(float(row["magnification"])),
                int(float(row["objective_diameter_mm"])),
                _csv_bool(row.get("image_stabilized", "")),
            )
            for row in csv.DictReader(file)
        ]


def _seed_filters_reducers_catalog(
    connection: sqlite3.Connection,
    filter_path: Path | None = None,
    reducer_path: Path | None = None,
) -> None:
    connection.executemany(
        """
        INSERT INTO FilterCatalog (
            brand, model, filter_class, barrel_size, central_wavelength_nm,
            bandwidth_nm, transmission_pct, minimum_aperture_mm, notes,
            is_builtin
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(brand, model, barrel_size) DO UPDATE SET is_builtin = 1
        """,
        _filter_catalog_rows(filter_path),
    )
    connection.executemany(
        """
        INSERT INTO ReducerCatalog (
            brand, model, reduction_factor, optical_system, compatible_models,
            connection, backfocus_mm, visual_compatible, imaging_compatible,
            corrected_field, notes, is_builtin
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(brand, model, reduction_factor) DO UPDATE SET is_builtin = 1
        """,
        _reducer_catalog_rows(reducer_path),
    )


def _filter_catalog_rows(filter_path: Path | None) -> list[tuple]:
    if not filter_path or not filter_path.exists():
        raise FileNotFoundError("Missing filter catalog seed CSV.")
    with filter_path.open("r", encoding="utf-8", newline="") as file:
        return [
            (
                row["brand"],
                row["model"],
                row["filter_class"],
                row["barrel_size"],
                _optional_float(row.get("central_wavelength_nm", "")),
                _optional_float(row.get("bandwidth_nm", "")),
                _optional_float(row.get("transmission_pct", "")),
                _optional_int(row.get("minimum_aperture_mm", "")),
                row.get("notes", ""),
            )
            for row in csv.DictReader(file)
        ]


def _reducer_catalog_rows(reducer_path: Path | None) -> list[tuple]:
    if not reducer_path or not reducer_path.exists():
        raise FileNotFoundError("Missing reducer catalog seed CSV.")
    with reducer_path.open("r", encoding="utf-8", newline="") as file:
        return [
            (
                row["brand"],
                row["model"],
                float(row["reduction_factor"]),
                row["optical_system"],
                row.get("compatible_models", ""),
                row.get("connection", ""),
                _optional_float(row.get("backfocus_mm", "")),
                _csv_bool(row.get("visual_compatible", "")),
                _csv_bool(row.get("imaging_compatible", "")),
                _csv_bool(row.get("corrected_field", "")),
                row.get("notes", ""),
            )
            for row in csv.DictReader(file)
        ]


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
        WHERE (
            ObjectImages.object_id LIKE 'messier-%'
            OR ObjectImages.object_id LIKE 'caldwell-%'
            OR ObjectImages.object_id IN (
                'sun', 'moon', 'mercury', 'venus', 'mars',
                'jupiter', 'saturn', 'uranus', 'neptune'
            )
        ) AND ObjectImages.license IN (
            'NightScope local generated asset',
            'NightScope local generated placeholder'
        )
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
    rows = []
    for object_id, image_path, attribution, source_url in OBJECT_IMAGES:
        if source_url:
            license_name = "NASA/JPL media; use subject to NASA and JPL image use policies"
        else:
            license_name = "NightScope local generated asset"
        rows.append(
            (
                object_id,
                image_path,
                image_path,
                attribution,
                source_url,
                license_name,
                1,
            )
        )
    return rows


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
        ON CONFLICT(object_id) DO NOTHING
        """,
        rows,
    )


def _seed_object_curiosities(connection: sqlite3.Connection, curiosities_path: Path | None = None) -> None:
    if not curiosities_path or not curiosities_path.exists():
        return
    with curiosities_path.open("r", encoding="utf-8", newline="") as file:
        rows = [
            (
                row["object_id"],
                row["curiosity_text"],
                row["source_label"],
                row["source_url"],
                1 if str(row.get("verified", "")).strip().lower() in {"1", "true", "yes"} else 0,
            )
            for row in csv.DictReader(file)
        ]
    connection.executemany(
        """
        INSERT INTO ObjectCuriosity (
            object_id, curiosity_text, source_label, source_url, verified
        )
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(object_id) DO NOTHING
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


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parents[2]
    runtime_database_path = base_dir.parent / "nightscope.db"
    data_dir = base_dir / "data"
    initialize_database(runtime_database_path, data_dir / "schema.sql", geonames_data_dir=data_dir)
    print("Database inizializzato:", runtime_database_path)
