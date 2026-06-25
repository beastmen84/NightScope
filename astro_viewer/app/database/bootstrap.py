from __future__ import annotations

import csv
import json
import logging
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Callable


logger = logging.getLogger(__name__)
ProgressCallback = Callable[[str], None]
SCHEMA_VERSION = 2
REQUIRED_TABLES = {
    "City",
    "CityAlias",
    "DataImportLog",
    "MessierObject",
    "WeatherCache",
    "ObservationHistory",
    "TelescopeBrand",
    "TelescopeModel",
    "EyepieceCatalog",
    "BarlowCatalog",
    "BinocularCatalog",
    "SkyQualityEstimate",
    "ObjectImages",
    "ObjectDescription",
    "EquipmentProfile",
    "EquipmentProfileTelescope",
    "EquipmentProfileEyepiece",
    "EquipmentProfileBarlow",
}
SEEDED_TABLES = {
    "MessierObject": "messier_seed.csv",
    "TelescopeBrand": "telescope_catalog_seed.csv",
    "TelescopeModel": "telescope_catalog_seed.csv",
    "EyepieceCatalog": "eyepiece_catalog_seed.csv",
    "BarlowCatalog": "barlow_catalog_seed.csv",
    "BinocularCatalog": "binocular_catalog_seed.csv",
    "ObjectImages": "object_images_seed.csv",
    "ObjectDescription": "object_descriptions_seed.csv",
    "EquipmentProfile": "",
}

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


def initialize_database(
    database_path: Path,
    schema_path: Path,
    progress_callback: ProgressCallback | None = None,
    geonames_data_dir: Path | None = None,
) -> None:
    _notify_progress(progress_callback, "Creazione database...")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = schema_path.read_text(encoding="utf-8")
    seed_path = schema_path.with_name("messier_seed.csv")

    if database_path.exists() and not _database_is_healthy(database_path):
        _notify_progress(progress_callback, "Ricostruzione database locale...")
        _quarantine_database(database_path)
    elif database_path.exists():
        _backup_database(database_path)

    try:
        _build_database(
            database_path,
            schema_sql,
            seed_path,
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
            seed_path,
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
    seed_path: Path,
    progress_callback: ProgressCallback | None = None,
    geonames_data_dir: Path | None = None,
) -> None:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        connection.executescript(schema_sql)
        existing_schema_version = _schema_version(connection)
        _migrate_database(connection)
        if existing_schema_version <= SCHEMA_VERSION:
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        data_dir = seed_path.parent
        geonames_source_dir = geonames_data_dir or database_path.parent
        _notify_progress(progress_callback, "Importazione cataloghi...")
        _import_geonames_cities_if_available(
            connection,
            geonames_source_dir,
            warn_if_missing=geonames_source_dir == data_dir,
            progress_callback=progress_callback,
        )
        if seed_path.exists():
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
                ON CONFLICT(messier_id) DO NOTHING
                """,
                rows,
            )
        _seed_telescope_catalog(connection, data_dir / "telescope_catalog_seed.csv")
        _seed_optics_catalog(
            connection,
            data_dir / "eyepiece_catalog_seed.csv",
            data_dir / "barlow_catalog_seed.csv",
        )
        _seed_binocular_catalog(connection, data_dir / "binocular_catalog_seed.csv")
        _seed_object_images(connection, data_dir / "object_images_seed.csv")
        _seed_object_descriptions(connection, data_dir / "object_descriptions_seed.csv")
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
    _add_columns(connection, "TelescopeModel", {"focal_ratio": "REAL", "notes": "TEXT"})
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
            "notes": "TEXT",
        },
    )
    _add_columns(connection, "BarlowCatalog", {"barrel_size": "TEXT", "notes": "TEXT"})
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS BinocularCatalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            magnification INTEGER NOT NULL,
            objective_diameter_mm INTEGER NOT NULL,
            true_fov_deg REAL,
            weight_g INTEGER,
            image_stabilized INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            UNIQUE (brand, model, magnification, objective_diameter_mm)
        )
        """
    )
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
    clean_value = value.strip()
    if not clean_value:
        return None
    try:
        return int(float(clean_value))
    except ValueError:
        return None


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
            focal_ratio, mount_type, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(brand_id, name) DO NOTHING
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
            max_focal_length_mm, apparent_field_deg, afov_min, afov_max, barrel_size, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(brand, model, focal_length_mm) DO NOTHING
        """,
        _eyepiece_catalog_rows(eyepiece_path),
    )

    connection.executemany(
        """
        INSERT INTO BarlowCatalog (brand, model, multiplier, barrel_size, notes)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(brand, model, multiplier) DO NOTHING
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
                row.get("notes", ""),
            )
            for row in csv.DictReader(file)
        ]


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
            true_fov_deg, weight_g, image_stabilized, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(brand, model, magnification, objective_diameter_mm) DO NOTHING
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
                _optional_float(row.get("true_fov_deg", "")),
                _optional_int(row.get("weight_g", "")),
                1 if str(row.get("image_stabilized", "")).strip().lower() in {"1", "true", "yes"} else 0,
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
        ON CONFLICT(object_id) DO NOTHING
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
