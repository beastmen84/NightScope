"""Create, migrate, validate, repair, and seed the NightScope SQLite database."""

from __future__ import annotations

import csv
import json
import logging
import shutil
import sqlite3
from collections import Counter
from collections.abc import Mapping
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Callable

from astro_viewer.app.models.filtering import FILTER_CLASS_CODES
from astro_viewer.app.services.equipment_taxonomy import (
    canonical_mount_type,
    canonical_telescope_category,
    canonical_telescope_optical_type,
)
from astro_viewer.app.services.localization import content_key, tr
from astro_viewer.app.services.object_imagery import retired_builtin_image


logger = logging.getLogger(__name__)
ProgressCallback = Callable[[object], None]
SCHEMA_VERSION = 27
CATALOGUE_OBSERVATION_TYPES = {"WideField", "General", "HighMagnification"}
_CATALOGUE_BUILTIN_TEXT_CORRECTIONS = (
    (
        "caldwell-C53",
        "Elliptical galaxy",
        "C53 (NGC 3115) - Galassia ellittica nella costellazione di Sestante.",
        "Lenticular galaxy",
        "C53 (NGC 3115) - Galassia lenticolare nella costellazione del Sestante.",
    ),
)
_CATALOGUE_BUILTIN_IDENTITY_MERGES = (
    ("ngc-NGC6882", "caldwell-C37"),
)
_LEGACY_EQUIPMENT_SEED_SOURCES = {
    "TelescopeModel": (
        "telescope",
        """
        SELECT model.id, brand.name, model.name
        FROM TelescopeModel model
        JOIN TelescopeBrand brand ON brand.id = model.brand_id
        WHERE model.is_builtin = 1 AND model.seed_key IS NULL
        """,
    ),
    "EyepieceCatalog": (
        "eyepiece",
        """
        SELECT id, brand, model, focal_length_mm
        FROM EyepieceCatalog
        WHERE is_builtin = 1 AND seed_key IS NULL
        """,
    ),
    "BarlowCatalog": (
        "barlow",
        """
        SELECT id, brand, model, multiplier
        FROM BarlowCatalog
        WHERE is_builtin = 1 AND seed_key IS NULL
        """,
    ),
    "BinocularCatalog": (
        "binocular",
        """
        SELECT id, brand, model, magnification, objective_diameter_mm
        FROM BinocularCatalog
        WHERE is_builtin = 1 AND seed_key IS NULL
        """,
    ),
    "FilterCatalog": (
        "filter",
        """
        SELECT id, brand, model
        FROM FilterCatalog
        WHERE is_builtin = 1 AND seed_key IS NULL
        """,
    ),
    "ReducerCatalog": (
        "reducer",
        """
        SELECT id, brand, model, reduction_factor
        FROM ReducerCatalog
        WHERE is_builtin = 1 AND seed_key IS NULL
        """,
    ),
}
REQUIRED_TABLES = {
    "PersonalObjectImages",
    "City",
    "CityAlias",
    "MpcObservatory",
    "DataImportLog",
    "CatalogueObject",
    "CatalogueDesignation",
    "CatalogueRecommendationPreference",
    "WeatherCache",
    "OrbitalElementCache",
    "ObservationHistory",
    "TelescopeBrand",
    "TelescopeModel",
    "SmartTelescopeCapability",
    "EyepieceCatalog",
    "BarlowCatalog",
    "BinocularCatalog",
    "AstronomyCameraCatalog",
    "CameraBodyCatalog",
    "FilterCatalog",
    "ReducerCatalog",
    "ReducerTelescopeCompatibility",
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
    "EquipmentProfileAstronomyCamera",
    "EquipmentProfileCameraBody",
}
SEEDED_TABLES = {
    "MpcObservatory": "mpc_observatories_seed.csv",
    "CatalogueObject": "catalogue_objects_seed.csv",
    "CatalogueDesignation": "catalogue_designations_seed.csv",
    "TelescopeBrand": "telescope_catalog_seed.csv",
    "TelescopeModel": "telescope_catalog_seed.csv",
    "EyepieceCatalog": "eyepiece_catalog_seed.csv",
    "BarlowCatalog": "barlow_catalog_seed.csv",
    "BinocularCatalog": "binocular_catalog_seed.csv",
    "AstronomyCameraCatalog": "astronomy_camera_catalog_seed.csv",
    "CameraBodyCatalog": "camera_body_catalog_seed.csv",
    "FilterCatalog": "filter_catalog_seed.csv",
    "ReducerCatalog": "reducer_catalog_seed.csv",
    "ReducerTelescopeCompatibility": "reducer_telescope_compatibility_seed.csv",
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
]


def initialize_database(
    database_path: Path,
    schema_path: Path,
    progress_callback: ProgressCallback | None = None,
    geonames_data_dir: Path | None = None,
) -> None:
    _notify_progress(progress_callback, tr("Creazione database..."))
    database_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = schema_path.read_text(encoding="utf-8")
    catalogue_objects_path = schema_path.with_name("catalogue_objects_seed.csv")

    if database_path.exists() and not _database_is_healthy(database_path):
        _notify_progress(progress_callback, tr("Ricostruzione database locale..."))
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
        _notify_progress(progress_callback, tr("Ricostruzione database locale..."))
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
            if _mpc_import_needed(connection, data_dir / "mpc_observatories_seed.csv"):
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
        _migrate_database(connection, existing_schema_version)
        if existing_schema_version <= SCHEMA_VERSION:
            connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        data_dir = catalogue_objects_path.parent
        geonames_source_dir = geonames_data_dir or database_path.parent
        _notify_progress(progress_callback, tr("Importazione cataloghi..."))
        _import_geonames_cities_if_available(
            connection,
            geonames_source_dir,
            warn_if_missing=geonames_source_dir == data_dir,
            progress_callback=progress_callback,
        )
        _import_mpc_observatories_if_available(
            connection,
            data_dir / "mpc_observatories_seed.csv",
        )
        _seed_catalogue(
            connection,
            catalogue_objects_path,
            data_dir / "catalogue_designations_seed.csv",
        )
        _seed_telescope_catalog(connection, data_dir / "telescope_catalog_seed.csv")
        _seed_smart_telescope_capabilities(
            connection,
            data_dir / "smart_telescope_capabilities_seed.csv",
        )
        _seed_optics_catalog(
            connection,
            data_dir / "eyepiece_catalog_seed.csv",
            data_dir / "barlow_catalog_seed.csv",
        )
        _seed_binocular_catalog(connection, data_dir / "binocular_catalog_seed.csv")
        _seed_camera_catalogs(
            connection,
            data_dir / "astronomy_camera_catalog_seed.csv",
            data_dir / "camera_body_catalog_seed.csv",
        )
        _seed_filters_reducers_catalog(
            connection,
            data_dir / "filter_catalog_seed.csv",
            data_dir / "reducer_catalog_seed.csv",
            data_dir / "reducer_telescope_compatibility_seed.csv",
        )
        _seed_object_images(connection, data_dir / "object_images_seed.csv")
        _seed_object_descriptions(connection, data_dir / "object_descriptions_seed.csv")
        _seed_object_curiosities(connection, data_dir / "object_curiosities_seed.csv")
        _seed_default_profiles(connection)
        _notify_progress(progress_callback, tr("Finalizzazione..."))
        connection.commit()
    logger.info("Database ready.")


def _notify_progress(progress_callback: ProgressCallback | None, message: object) -> None:
    if progress_callback:
        progress_callback(message)


def _migrate_database(
    connection: sqlite3.Connection,
    existing_schema_version: int,
) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS OrbitalElementCache (
            provider TEXT NOT NULL,
            object_id TEXT NOT NULL,
            element_format TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            source_epoch TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY (provider, object_id)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_orbital_element_cache_expiry
        ON OrbitalElementCache(expires_at)
        """
    )
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
            "instrument_category": (
                "TEXT NOT NULL DEFAULT 'TRADITIONAL' "
                "CHECK (instrument_category IN "
                "('TRADITIONAL', 'SMART_INTEGRATED'))"
            ),
            "focal_ratio": "REAL",
            "notes": "TEXT",
            "is_builtin": "INTEGER NOT NULL DEFAULT 0",
            "seed_key": "TEXT",
            "is_user_modified": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    if existing_schema_version < 24:
        _migrate_telescope_categories(connection)
    _add_columns(
        connection,
        "EyepieceCatalog",
        {
            "eyepiece_type": "TEXT NOT NULL DEFAULT 'Fixed'",
            "min_focal_length_mm": "REAL",
            "max_focal_length_mm": "REAL",
            "afov_min": "REAL",
            "afov_max": "REAL",
            "zoom_click_positions_mm": "TEXT",
            "notes": "TEXT",
            "is_builtin": "INTEGER NOT NULL DEFAULT 0",
            "seed_key": "TEXT",
            "is_user_modified": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    _add_columns(
        connection,
        "BarlowCatalog",
        {
            "notes": "TEXT",
            "is_builtin": "INTEGER NOT NULL DEFAULT 0",
            "seed_key": "TEXT",
            "is_user_modified": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    _add_columns(
        connection,
        "BinocularCatalog",
        {
            "is_builtin": "INTEGER NOT NULL DEFAULT 0",
            "seed_key": "TEXT",
            "is_user_modified": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    _migrate_binocular_catalog(connection)
    if existing_schema_version < 23:
        _retire_legacy_equipment_compatibility_fields(connection)
    for table_name, index_name in (
        ("TelescopeModel", "idx_telescope_model_seed_key"),
        ("EyepieceCatalog", "idx_eyepiece_catalog_seed_key"),
        ("BarlowCatalog", "idx_barlow_catalog_seed_key"),
        ("BinocularCatalog", "idx_binocular_catalog_seed_key"),
        ("AstronomyCameraCatalog", "idx_astronomy_camera_catalog_seed_key"),
        ("CameraBodyCatalog", "idx_camera_body_catalog_seed_key"),
        ("FilterCatalog", "idx_filter_catalog_seed_key"),
        ("ReducerCatalog", "idx_reducer_catalog_seed_key"),
    ):
        _add_columns(
            connection,
            table_name,
            {
                "seed_key": "TEXT",
                "is_user_modified": "INTEGER NOT NULL DEFAULT 0",
            },
        )
        connection.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
            f"ON {table_name}(seed_key)"
        )
    if existing_schema_version < 16:
        _migrate_default_profile_name(connection)
    _add_columns(
        connection,
        "CatalogueObject",
        {
            "best_filter_class": "TEXT",
            "fallback_filter_class": "TEXT",
            "optional_color_filter_class": "TEXT",
            "imaging_reducer_recommended": "INTEGER NOT NULL DEFAULT 0",
            "recommendation_enabled_by_default": (
                "INTEGER NOT NULL DEFAULT 1 "
                "CHECK (recommendation_enabled_by_default IN (0, 1))"
            ),
        },
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS CatalogueRecommendationPreference (
            object_id TEXT PRIMARY KEY COLLATE NOCASE,
            enabled INTEGER NOT NULL CHECK (enabled IN (0, 1))
        )
        """
    )
    _migrate_catalogue_tables(connection)
    if existing_schema_version < 19:
        _migrate_catalogue_designation_aliases(connection)
    _add_columns(
        connection,
        "EquipmentProfileTelescope",
        {
            "has_full_aperture_solar_filter": (
                "INTEGER NOT NULL DEFAULT 0 "
                "CHECK (has_full_aperture_solar_filter IN (0, 1))"
            ),
        },
    )
    _ensure_profile_binocular_table(connection)
    _ensure_profile_camera_tables(connection)
    _remove_orphan_profile_assignments(connection)
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
    _add_columns(
        connection,
        "ObjectDescription",
        {"is_builtin": "INTEGER NOT NULL DEFAULT 1"},
    )
    _add_columns(
        connection,
        "ObjectCuriosity",
        {"is_builtin": "INTEGER NOT NULL DEFAULT 1"},
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
        CREATE TABLE IF NOT EXISTS MpcObservatory (
            mpc_code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            short_name TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            elevation_m REAL,
            rho_cos_phi REAL NOT NULL,
            rho_sin_phi REAL NOT NULL,
            observations_type TEXT,
            first_date TEXT,
            last_date TEXT,
            web_link TEXT,
            old_names TEXT,
            source_updated_at TEXT,
            search_name TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_mpc_observatory_name ON MpcObservatory(name)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_mpc_observatory_search ON MpcObservatory(search_name)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_mpc_observatory_coordinates "
        "ON MpcObservatory(latitude, longitude)"
    )
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


def _migrate_default_profile_name(connection: sqlite3.Connection) -> None:
    legacy_profile = connection.execute(
        """
        SELECT id
        FROM EquipmentProfile
        WHERE id = 1 AND profile_name = 'Occhio nudo'
        """
    ).fetchone()
    if legacy_profile is None:
        return

    existing_names = {
        str(row[0])
        for row in connection.execute(
            "SELECT profile_name FROM EquipmentProfile WHERE id != 1"
        ).fetchall()
    }
    profile_name = "Default"
    suffix = 2
    while profile_name in existing_names:
        profile_name = f"Default {suffix}"
        suffix += 1
    connection.execute(
        "UPDATE EquipmentProfile SET profile_name = ? WHERE id = 1",
        (profile_name,),
    )


def _add_columns(connection: sqlite3.Connection, table_name: str, columns: dict[str, str]) -> None:
    existing = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, definition in columns.items():
        if column_name not in existing:
            connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _migrate_telescope_categories(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        UPDATE TelescopeModel
        SET instrument_category = 'SMART_INTEGRATED'
        WHERE seed_key IN (
            'telescope::zwo/seestar::seestar s30',
            'telescope::zwo/seestar::seestar s50'
        )
           OR lower(trim(optical_type)) IN (
               'smart',
               'smart telescope',
               'smart integrato',
               'telescopio intelligente'
           )
        """
    )
    connection.execute(
        """
        UPDATE TelescopeModel
        SET optical_type = 'Rifrattore apocromatico'
        WHERE seed_key IN (
            'telescope::zwo/seestar::seestar s30',
            'telescope::zwo/seestar::seestar s50'
        )
          AND is_user_modified = 0
        """
    )


def _retire_legacy_equipment_compatibility_fields(
    connection: sqlite3.Connection,
) -> None:
    for table_name in ("EyepieceCatalog", "BarlowCatalog"):
        columns = {
            str(row[1])
            for row in connection.execute(
                f"PRAGMA table_info({table_name})"
            ).fetchall()
        }
        if "barrel_size" not in columns:
            continue
        rows = connection.execute(
            f"""
            SELECT id, barrel_size, notes
            FROM {table_name}
            WHERE trim(COALESCE(barrel_size, '')) <> ''
              AND (
                  COALESCE(is_builtin, 0) = 0
                  OR COALESCE(is_user_modified, 0) = 1
              )
            """
        ).fetchall()
        for row in rows:
            technical_note = _legacy_barrel_note(row["barrel_size"])
            existing_notes = str(row["notes"] or "").strip()
            if not technical_note or technical_note in existing_notes:
                continue
            connection.execute(
                f"UPDATE {table_name} SET notes = ? WHERE id = ?",
                (
                    (
                        f"{existing_notes} · {technical_note}"
                        if existing_notes
                        else technical_note
                    ),
                    int(row["id"]),
                ),
            )
        connection.execute(
            f"UPDATE {table_name} SET barrel_size = ''"
        )

    reducer_columns = {
        str(row[1])
        for row in connection.execute(
            "PRAGMA table_info(ReducerCatalog)"
        ).fetchall()
    }
    if "compatible_models" in reducer_columns:
        connection.execute(
            "UPDATE ReducerCatalog SET compatible_models = ''"
        )


def _legacy_barrel_note(value: object) -> str:
    parts = [
        part.strip().rstrip('"″').strip()
        for part in str(value or "").split("/")
        if part.strip()
    ]
    if not parts:
        return ""
    return "Ø " + " / ".join(f"{part}″" for part in parts)


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
            max_angular_size_deg, recommended_observation_type,
            best_filter_class, fallback_filter_class,
            optional_color_filter_class, imaging_reducer_recommended,
            recommendation_enabled_by_default,
            descrizione
        )
        SELECT
            'messier-' || messier_id, nome, tipo, costellazione, magnitudine,
            ascensione_retta, declinazione, dimensione_apparente,
            max_angular_size_deg, recommended_observation_type,
            NULL, NULL, NULL, 0, 1, descrizione
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


def _migrate_catalogue_designation_aliases(
    connection: sqlite3.Connection,
) -> None:
    """Allow several historical codes from one catalogue to share a target."""

    connection.execute("DROP TABLE IF EXISTS CatalogueDesignation_v19")
    connection.execute(
        """
        CREATE TABLE CatalogueDesignation_v19 (
            catalogue TEXT NOT NULL,
            designation TEXT NOT NULL,
            object_id TEXT NOT NULL,
            sort_index INTEGER,
            is_primary INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (catalogue, designation),
            FOREIGN KEY (object_id)
                REFERENCES CatalogueObject(object_id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        INSERT INTO CatalogueDesignation_v19 (
            catalogue, designation, object_id, sort_index, is_primary
        )
        SELECT catalogue, designation, object_id, sort_index, is_primary
        FROM CatalogueDesignation
        """
    )
    connection.execute("DROP TABLE CatalogueDesignation")
    connection.execute(
        "ALTER TABLE CatalogueDesignation_v19 RENAME TO CatalogueDesignation"
    )
    connection.execute(
        """
        CREATE INDEX idx_catalogue_designation_object
        ON CatalogueDesignation(object_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_catalogue_designation_catalogue
        ON CatalogueDesignation(catalogue, sort_index)
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX idx_catalogue_designation_primary
        ON CatalogueDesignation(object_id)
        WHERE is_primary = 1
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX idx_catalogue_designation_normalized
        ON CatalogueDesignation(LOWER(catalogue), LOWER(designation))
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_catalogue_object_catalogue_normalized
        ON CatalogueDesignation(object_id, LOWER(catalogue))
        """
    )


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone() is not None


def _remove_orphan_profile_assignments(connection: sqlite3.Connection) -> None:
    for table_name in (
        "EquipmentProfileTelescope",
        "EquipmentProfileEyepiece",
        "EquipmentProfileBarlow",
        "EquipmentProfileBinocular",
        "EquipmentProfileFilter",
        "EquipmentProfileReducer",
        "EquipmentProfileAstronomyCamera",
        "EquipmentProfileCameraBody",
    ):
        connection.execute(
            f"""
            DELETE FROM {table_name}
            WHERE profile_id NOT IN (SELECT id FROM EquipmentProfile)
            """
        )


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
            seed_key TEXT,
            is_user_modified INTEGER NOT NULL DEFAULT 0,
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
        "seed_key",
        "is_user_modified",
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
            seed_key TEXT,
            is_user_modified INTEGER NOT NULL DEFAULT 0,
            UNIQUE (brand, model, magnification, objective_diameter_mm)
        )
        """
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO BinocularCatalog_new (
            id, brand, model, magnification, objective_diameter_mm,
            image_stabilized, is_builtin, seed_key, is_user_modified
        )
        SELECT id, brand, model, magnification, objective_diameter_mm,
               image_stabilized, is_builtin, seed_key, is_user_modified
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


def _ensure_profile_camera_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS EquipmentProfileAstronomyCamera (
            profile_id INTEGER NOT NULL,
            astronomy_camera_id INTEGER NOT NULL,
            PRIMARY KEY (profile_id, astronomy_camera_id),
            FOREIGN KEY (profile_id)
                REFERENCES EquipmentProfile(id) ON DELETE CASCADE,
            FOREIGN KEY (astronomy_camera_id)
                REFERENCES AstronomyCameraCatalog(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS EquipmentProfileCameraBody (
            profile_id INTEGER NOT NULL,
            camera_body_id INTEGER NOT NULL,
            PRIMARY KEY (profile_id, camera_body_id),
            FOREIGN KEY (profile_id)
                REFERENCES EquipmentProfile(id) ON DELETE CASCADE,
            FOREIGN KEY (camera_body_id)
                REFERENCES CameraBodyCatalog(id) ON DELETE CASCADE
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


def _mpc_import_needed(
    connection: sqlite3.Connection,
    source_path: Path,
) -> bool:
    if not source_path.exists():
        return False
    if _table_count(connection, "MpcObservatory") == 0:
        return True
    source_stat = source_path.stat()
    source_mtime = datetime.fromtimestamp(source_stat.st_mtime).isoformat(timespec="seconds")
    existing_import = connection.execute(
        """
        SELECT source_size, source_mtime
        FROM DataImportLog
        WHERE source_name = ?
        """,
        (source_path.name,),
    ).fetchone()
    return not (
        existing_import
        and int(existing_import["source_size"]) == source_stat.st_size
        and str(existing_import["source_mtime"]) == source_mtime
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
        _notify_progress(
            progress_callback,
            tr("Importazione catalogo città... {rows} righe", rows=rows),
        )

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


def _import_mpc_observatories_if_available(
    connection: sqlite3.Connection,
    source_path: Path,
) -> None:
    if not source_path.exists():
        logger.warning("MPC observatory snapshot not found; observatory search is unavailable.")
        return
    if not _mpc_import_needed(connection, source_path):
        return
    from astro_viewer.app.database.mpc_observatory_importer import (
        import_mpc_observatories,
    )

    imported_rows = import_mpc_observatories(connection, source_path)
    source_stat = source_path.stat()
    source_mtime = datetime.fromtimestamp(source_stat.st_mtime).isoformat(timespec="seconds")
    connection.execute(
        """
        INSERT INTO DataImportLog (
            source_name, source_path, source_size, source_mtime,
            imported_at, report_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_name) DO UPDATE SET
            source_path = excluded.source_path,
            source_size = excluded.source_size,
            source_mtime = excluded.source_mtime,
            imported_at = excluded.imported_at,
            report_json = excluded.report_json
        """,
        (
            source_path.name,
            str(source_path),
            source_stat.st_size,
            source_mtime,
            datetime.now().isoformat(timespec="seconds"),
            json.dumps({"observatories_imported": imported_rows}, ensure_ascii=True),
        ),
    )
    logger.info("MPC observatory snapshot imported: %s rows.", imported_rows)


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
            (row.get("best_filter_class") or "").strip().upper(),
            (row.get("fallback_filter_class") or "").strip().upper(),
            (row.get("optional_color_filter_class") or "").strip().upper(),
            _csv_bool(row.get("imaging_reducer_recommended", "")),
            _csv_bool(row.get("recommendation_enabled_by_default", "")),
            row["descrizione"],
        )
        for row in source_object_rows
    ]
    connection.executemany(
        """
        INSERT INTO CatalogueObject (
            object_id, nome, tipo, costellazione, magnitudine,
            ascensione_retta, declinazione, dimensione_apparente,
            max_angular_size_deg, recommended_observation_type,
            best_filter_class, fallback_filter_class,
            optional_color_filter_class, imaging_reducer_recommended,
            recommendation_enabled_by_default,
            descrizione
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(object_id) DO UPDATE SET
            max_angular_size_deg = excluded.max_angular_size_deg,
            recommended_observation_type = excluded.recommended_observation_type,
            best_filter_class = excluded.best_filter_class,
            fallback_filter_class = excluded.fallback_filter_class,
            optional_color_filter_class = excluded.optional_color_filter_class,
            imaging_reducer_recommended = excluded.imaging_reducer_recommended,
            recommendation_enabled_by_default =
                excluded.recommendation_enabled_by_default
        """,
        object_rows,
    )
    for object_id, old_type, old_description, new_type, new_description in (
        _CATALOGUE_BUILTIN_TEXT_CORRECTIONS
    ):
        connection.execute(
            """
            UPDATE CatalogueObject
            SET tipo = ?, descrizione = ?
            WHERE object_id = ? AND tipo = ? AND descrizione = ?
            """,
            (new_type, new_description, object_id, old_type, old_description),
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
    _merge_catalogue_builtin_identities(connection)


def _merge_catalogue_builtin_identities(
    connection: sqlite3.Connection,
) -> None:
    for obsolete_object_id, canonical_object_id in (
        _CATALOGUE_BUILTIN_IDENTITY_MERGES
    ):
        connection.execute(
            """
            UPDATE CatalogueDesignation
            SET object_id = ?, is_primary = 0
            WHERE object_id = ?
            """,
            (canonical_object_id, obsolete_object_id),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO CatalogueRecommendationPreference (
                object_id, enabled
            )
            SELECT ?, enabled
            FROM CatalogueRecommendationPreference
            WHERE object_id = ?
            """,
            (canonical_object_id, obsolete_object_id),
        )
        connection.execute(
            "DELETE FROM CatalogueRecommendationPreference WHERE object_id = ?",
            (obsolete_object_id,),
        )
        connection.execute(
            "DELETE FROM CatalogueObject WHERE object_id = ?",
            (obsolete_object_id,),
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
        best_filter_class = (row.get("best_filter_class") or "").strip().upper()
        if best_filter_class and best_filter_class not in FILTER_CLASS_CODES:
            raise ValueError(f"Invalid best filter class for {object_id}.")
        fallback_filter_class = (row.get("fallback_filter_class") or "").strip().upper()
        if fallback_filter_class and fallback_filter_class not in FILTER_CLASS_CODES:
            raise ValueError(f"Invalid fallback filter class for {object_id}.")
        if fallback_filter_class and not best_filter_class:
            raise ValueError(f"Fallback filter class without primary class for {object_id}.")
        if fallback_filter_class == best_filter_class and fallback_filter_class:
            raise ValueError(f"Duplicate filter preference for {object_id}.")
        color_filter_class = (row.get("optional_color_filter_class") or "").strip().upper()
        if color_filter_class and (
            color_filter_class not in FILTER_CLASS_CODES
            or not color_filter_class.startswith("COLOR_")
        ):
            raise ValueError(f"Invalid optional color filter class for {object_id}.")
        reducer_recommendation = str(
            row.get("imaging_reducer_recommended") or ""
        ).strip()
        if reducer_recommendation not in {"0", "1"}:
            raise ValueError(
                f"Invalid imaging reducer recommendation for {object_id}."
            )
        recommendation_enabled = str(
            row.get("recommendation_enabled_by_default") or ""
        ).strip()
        if recommendation_enabled not in {"0", "1"}:
            raise ValueError(
                f"Invalid default recommendation state for {object_id}."
            )
        max_size = _optional_float(row["max_angular_size_deg"])
        if max_size is not None and max_size <= 0:
            raise ValueError(f"Invalid angular size for {object_id}.")

    normalized_designations: set[tuple[str, str]] = set()
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


def _required_equipment_seed_key(
    row: Mapping[str, str | None],
    kind: str,
    field_name: str = "seed_key",
) -> str:
    raw_value = row.get(field_name)
    seed_key = raw_value.strip() if raw_value else ""
    prefix = f"{kind}::"
    if not seed_key or not seed_key.startswith(prefix) or seed_key == prefix:
        raise ValueError(f"Invalid {kind} equipment seed key in column {field_name}.")
    return seed_key


def _equipment_catalog_source_rows(
    catalog_path: Path | None,
    catalog_name: str,
    kind: str,
) -> list[tuple[dict[str, str | None], str]]:
    if not catalog_path or not catalog_path.exists():
        raise FileNotFoundError(f"Missing {catalog_name} catalog seed CSV.")
    with catalog_path.open("r", encoding="utf-8", newline="") as file:
        source_rows = list(csv.DictReader(file))

    result: list[tuple[dict[str, str | None], str]] = []
    seed_keys: set[str] = set()
    for row in source_rows:
        seed_key = _required_equipment_seed_key(row, kind)
        if seed_key in seed_keys:
            raise ValueError(f"Duplicate {kind} equipment seed key: {seed_key}.")
        seed_keys.add(seed_key)
        result.append((row, seed_key))
    return result


def _legacy_equipment_seed_row_id(
    connection: sqlite3.Connection,
    table_name: str,
    seed_key: str,
) -> int | None:
    legacy_source = _LEGACY_EQUIPMENT_SEED_SOURCES.get(table_name)
    if legacy_source is None:
        return None
    kind, query = legacy_source
    for row in connection.execute(query).fetchall():
        row_id, *legacy_identity = tuple(row)
        if f"{kind}::{content_key(*legacy_identity)}" == seed_key:
            return int(row_id)
    return None


def _prepare_equipment_seed_row(
    connection: sqlite3.Connection,
    table_name: str,
    seed_key: str,
    natural_key_sql: str,
    natural_key_values: tuple[object, ...],
) -> bool:
    seeded = connection.execute(
        f"SELECT id FROM {table_name} WHERE seed_key = ?",
        (seed_key,),
    ).fetchone()
    seeded_id = int(seeded["id"]) if seeded is not None else None
    if seeded_id is None:
        seeded_id = _legacy_equipment_seed_row_id(
            connection,
            table_name,
            seed_key,
        )
        if seeded_id is not None:
            connection.execute(
                f"UPDATE {table_name} SET seed_key = ? WHERE id = ?",
                (seed_key, seeded_id),
            )

    existing = connection.execute(
        f"SELECT id, is_builtin FROM {table_name} WHERE {natural_key_sql}",
        natural_key_values,
    ).fetchone()
    if seeded_id is not None:
        if existing is not None and int(existing["id"]) != seeded_id:
            logger.warning(
                "Skipping built-in %s seed %s because another row uses the corrected identity.",
                table_name,
                seed_key,
            )
            return False
        return True
    if existing is None:
        return True
    if not bool(existing["is_builtin"]):
        logger.warning(
            "Skipping built-in %s seed %s because a custom row uses the same identity.",
            table_name,
            seed_key,
        )
        return False

    connection.execute(
        f"UPDATE {table_name} SET seed_key = ? WHERE id = ?",
        (seed_key, int(existing["id"])),
    )
    return True


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
    for (
        brand,
        name,
        instrument_category,
        optical_type,
        aperture,
        focal,
        ratio,
        mount,
        notes,
        seed_key,
    ) in catalog_rows:
        brand_id = brand_ids[brand]
        if not _prepare_equipment_seed_row(
            connection,
            "TelescopeModel",
            seed_key,
            "brand_id = ? AND name = ?",
            (brand_id, name),
        ):
            continue
        connection.execute(
            """
            INSERT INTO TelescopeModel (
                brand_id, name, instrument_category, optical_type, aperture_mm,
                focal_length_mm, focal_ratio, mount_type, notes, is_builtin,
                seed_key, is_user_modified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0)
            ON CONFLICT(seed_key) DO UPDATE SET
                brand_id = excluded.brand_id,
                name = excluded.name,
                instrument_category = excluded.instrument_category,
                optical_type = excluded.optical_type,
                aperture_mm = excluded.aperture_mm,
                focal_length_mm = excluded.focal_length_mm,
                focal_ratio = excluded.focal_ratio,
                mount_type = excluded.mount_type,
                notes = excluded.notes,
                is_builtin = 1
            WHERE TelescopeModel.is_user_modified = 0
            """,
            (
                brand_id,
                name,
                instrument_category,
                optical_type,
                aperture,
                focal,
                ratio,
                mount,
                notes,
                seed_key,
            ),
        )


def _telescope_catalog_rows(catalog_path: Path | None) -> list[tuple]:
    return [
        (
            row["brand"],
            row["model"],
            canonical_telescope_category(
                row.get("instrument_category") or "TRADITIONAL",
                preserve_unknown=False,
            ),
            canonical_telescope_optical_type(row["optical_type"]),
            int(float(row["aperture_mm"])),
            int(float(row["focal_length_mm"])),
            _optional_float(row.get("focal_ratio", "")),
            canonical_mount_type(row["mount_type"]),
            row.get("notes", ""),
            seed_key,
        )
        for row, seed_key in _equipment_catalog_source_rows(
            catalog_path,
            "telescope",
            "telescope",
        )
    ]


def _seed_smart_telescope_capabilities(
    connection: sqlite3.Connection,
    catalog_path: Path | None,
) -> None:
    rows = _equipment_catalog_source_rows(
        catalog_path,
        "smart telescope capability",
        "telescope",
    )
    for row, seed_key in rows:
        exposure_control_mode = str(
            row.get("exposure_control_mode") or "DEVICE_MANAGED"
        ).strip().upper()
        color_mode = str(row.get("color_mode") or "").strip().upper()
        if exposure_control_mode not in {
            "DEVICE_MANAGED",
            "USER_CONFIGURABLE",
        }:
            raise ValueError(
                f"Invalid smart exposure control mode for {seed_key}."
            )
        if color_mode not in {"COLOR", "MONO"}:
            raise ValueError(f"Invalid smart sensor color mode for {seed_key}.")
        connection.execute(
            """
            INSERT INTO SmartTelescopeCapability (
                telescope_model_id, supports_optical_visual,
                supports_interchangeable_eyepieces,
                supports_external_cameras,
                supports_external_optical_modifiers, sensor_model,
                sensor_width_mm, sensor_height_mm, resolution_width_px,
                resolution_height_px, pixel_size_um, bit_depth, color_mode,
                full_resolution_fps, supports_live_stacking, supports_video,
                supports_mosaic, exposure_control_mode,
                integrated_filter_codes, specification_source_url
            )
            SELECT
                model.id, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?
            FROM TelescopeModel model
            WHERE model.seed_key = ?
              AND model.instrument_category = 'SMART_INTEGRATED'
            ON CONFLICT(telescope_model_id) DO UPDATE SET
                supports_optical_visual =
                    excluded.supports_optical_visual,
                supports_interchangeable_eyepieces =
                    excluded.supports_interchangeable_eyepieces,
                supports_external_cameras =
                    excluded.supports_external_cameras,
                supports_external_optical_modifiers =
                    excluded.supports_external_optical_modifiers,
                sensor_model = excluded.sensor_model,
                sensor_width_mm = excluded.sensor_width_mm,
                sensor_height_mm = excluded.sensor_height_mm,
                resolution_width_px = excluded.resolution_width_px,
                resolution_height_px = excluded.resolution_height_px,
                pixel_size_um = excluded.pixel_size_um,
                bit_depth = excluded.bit_depth,
                color_mode = excluded.color_mode,
                full_resolution_fps = excluded.full_resolution_fps,
                supports_live_stacking = excluded.supports_live_stacking,
                supports_video = excluded.supports_video,
                supports_mosaic = excluded.supports_mosaic,
                exposure_control_mode = excluded.exposure_control_mode,
                integrated_filter_codes =
                    excluded.integrated_filter_codes,
                specification_source_url =
                    excluded.specification_source_url
            WHERE (
                SELECT is_user_modified
                FROM TelescopeModel
                WHERE id = excluded.telescope_model_id
            ) = 0
            """,
            (
                _csv_bool(row.get("supports_optical_visual")),
                _csv_bool(row.get("supports_interchangeable_eyepieces")),
                _csv_bool(row.get("supports_external_cameras")),
                _csv_bool(row.get("supports_external_optical_modifiers")),
                str(row.get("sensor_model") or "").strip(),
                _optional_float(str(row.get("sensor_width_mm") or "")),
                _optional_float(str(row.get("sensor_height_mm") or "")),
                _optional_int(str(row.get("resolution_width_px") or "")),
                _optional_int(str(row.get("resolution_height_px") or "")),
                _optional_float(str(row.get("pixel_size_um") or "")),
                _optional_int(str(row.get("bit_depth") or "")),
                color_mode,
                _optional_float(
                    str(row.get("full_resolution_fps") or "")
                ),
                _csv_bool(row.get("supports_live_stacking")),
                _csv_bool(row.get("supports_video")),
                _csv_bool(row.get("supports_mosaic")),
                exposure_control_mode,
                str(row.get("integrated_filter_codes") or "").strip(),
                str(row.get("specification_source_url") or "").strip(),
                seed_key,
            ),
        )


def _seed_optics_catalog(connection: sqlite3.Connection, eyepiece_path: Path | None = None, barlow_path: Path | None = None) -> None:
    for row in _eyepiece_catalog_rows(eyepiece_path):
        values = row[:-1]
        seed_key = row[-1]
        brand, model, _, focal_length, *_ = values
        if not _prepare_equipment_seed_row(
            connection,
            "EyepieceCatalog",
            seed_key,
            "brand = ? AND model = ? AND focal_length_mm = ?",
            (brand, model, focal_length),
        ):
            continue
        connection.execute(
            """
            INSERT INTO EyepieceCatalog (
                brand, model, eyepiece_type, focal_length_mm,
                min_focal_length_mm, max_focal_length_mm, apparent_field_deg,
                afov_min, afov_max, zoom_click_positions_mm,
                notes, is_builtin, seed_key, is_user_modified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0)
            ON CONFLICT(seed_key) DO UPDATE SET
                brand = excluded.brand,
                model = excluded.model,
                eyepiece_type = excluded.eyepiece_type,
                focal_length_mm = excluded.focal_length_mm,
                min_focal_length_mm = excluded.min_focal_length_mm,
                max_focal_length_mm = excluded.max_focal_length_mm,
                apparent_field_deg = excluded.apparent_field_deg,
                afov_min = excluded.afov_min,
                afov_max = excluded.afov_max,
                zoom_click_positions_mm = excluded.zoom_click_positions_mm,
                notes = excluded.notes,
                is_builtin = 1
            WHERE EyepieceCatalog.is_user_modified = 0
            """,
            values + (seed_key,),
        )
    _backfill_zoom_click_positions(connection)

    for row in _barlow_catalog_rows(barlow_path):
        values = row[:-1]
        seed_key = row[-1]
        brand, model, multiplier, *_ = values
        if not _prepare_equipment_seed_row(
            connection,
            "BarlowCatalog",
            seed_key,
            "brand = ? AND model = ? AND multiplier = ?",
            (brand, model, multiplier),
        ):
            continue
        connection.execute(
            """
            INSERT INTO BarlowCatalog (
                brand, model, multiplier, notes, is_builtin,
                seed_key, is_user_modified
            )
            VALUES (?, ?, ?, ?, 1, ?, 0)
            ON CONFLICT(seed_key) DO UPDATE SET
                brand = excluded.brand,
                model = excluded.model,
                multiplier = excluded.multiplier,
                notes = excluded.notes,
                is_builtin = 1
            WHERE BarlowCatalog.is_user_modified = 0
            """,
            values + (seed_key,),
        )


def _eyepiece_catalog_rows(eyepiece_path: Path | None) -> list[tuple]:
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
            row.get("zoom_click_positions_mm", ""),
            row.get("notes", ""),
            seed_key,
        )
        for row, seed_key in _equipment_catalog_source_rows(
            eyepiece_path,
            "eyepiece",
            "eyepiece",
        )
    ]


def _backfill_zoom_click_positions(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        UPDATE EyepieceCatalog
        SET zoom_click_positions_mm = ?
        WHERE brand = ? AND model = ? AND eyepiece_type = 'Zoom'
          AND is_user_modified = 0
          AND (zoom_click_positions_mm IS NULL OR trim(zoom_click_positions_mm) = '')
        """,
        ("24;20;16;12;8", "Baader", "Hyperion Zoom 8-24 mm"),
    )


def _barlow_catalog_rows(barlow_path: Path | None) -> list[tuple]:
    return [
        (
            row["brand"],
            row["model"],
            float(row["multiplier"]),
            row.get("notes", ""),
            seed_key,
        )
        for row, seed_key in _equipment_catalog_source_rows(
            barlow_path,
            "Barlow",
            "barlow",
        )
    ]


def _seed_binocular_catalog(connection: sqlite3.Connection, binocular_path: Path | None = None) -> None:
    for row in _binocular_catalog_rows(binocular_path):
        values = row[:-1]
        seed_key = row[-1]
        brand, model, magnification, objective, *_ = values
        if not _prepare_equipment_seed_row(
            connection,
            "BinocularCatalog",
            seed_key,
            "brand = ? AND model = ? AND magnification = ? "
            "AND objective_diameter_mm = ?",
            (brand, model, magnification, objective),
        ):
            continue
        connection.execute(
            """
            INSERT INTO BinocularCatalog (
                brand, model, magnification, objective_diameter_mm,
                image_stabilized, is_builtin, seed_key, is_user_modified
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, 0)
            ON CONFLICT(seed_key) DO UPDATE SET
                brand = excluded.brand,
                model = excluded.model,
                magnification = excluded.magnification,
                objective_diameter_mm = excluded.objective_diameter_mm,
                image_stabilized = excluded.image_stabilized,
                is_builtin = 1
            WHERE BinocularCatalog.is_user_modified = 0
            """,
            values + (seed_key,),
        )


def _binocular_catalog_rows(binocular_path: Path | None) -> list[tuple]:
    return [
        (
            row["brand"],
            row["model"],
            int(float(row["magnification"])),
            int(float(row["objective_diameter_mm"])),
            _csv_bool(row.get("image_stabilized", "")),
            seed_key,
        )
        for row, seed_key in _equipment_catalog_source_rows(
            binocular_path,
            "binocular",
            "binocular",
        )
    ]


def _seed_camera_catalogs(
    connection: sqlite3.Connection,
    astronomy_camera_path: Path | None = None,
    camera_body_path: Path | None = None,
) -> None:
    for row in _astronomy_camera_catalog_rows(astronomy_camera_path):
        values = row[:-1]
        seed_key = row[-1]
        brand, model, *_ = values
        if not _prepare_equipment_seed_row(
            connection,
            "AstronomyCameraCatalog",
            seed_key,
            "brand = ? AND model = ?",
            (brand, model),
        ):
            continue
        connection.execute(
            """
            INSERT INTO AstronomyCameraCatalog (
                brand, model, camera_class, sensor_model, sensor_technology,
                color_mode, sensor_width_mm, sensor_height_mm,
                resolution_width_px, resolution_height_px, pixel_size_um,
                bit_depth, max_fps, cooled, cooling_delta_c, shutter_type,
                backfocus_mm, source_url, is_builtin, seed_key,
                is_user_modified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0)
            ON CONFLICT(seed_key) DO UPDATE SET
                brand = excluded.brand,
                model = excluded.model,
                camera_class = excluded.camera_class,
                sensor_model = excluded.sensor_model,
                sensor_technology = excluded.sensor_technology,
                color_mode = excluded.color_mode,
                sensor_width_mm = excluded.sensor_width_mm,
                sensor_height_mm = excluded.sensor_height_mm,
                resolution_width_px = excluded.resolution_width_px,
                resolution_height_px = excluded.resolution_height_px,
                pixel_size_um = excluded.pixel_size_um,
                bit_depth = excluded.bit_depth,
                max_fps = excluded.max_fps,
                cooled = excluded.cooled,
                cooling_delta_c = excluded.cooling_delta_c,
                shutter_type = excluded.shutter_type,
                backfocus_mm = excluded.backfocus_mm,
                source_url = excluded.source_url,
                is_builtin = 1
            WHERE AstronomyCameraCatalog.is_user_modified = 0
            """,
            values + (seed_key,),
        )

    for row in _camera_body_catalog_rows(camera_body_path):
        values = row[:-1]
        seed_key = row[-1]
        brand, model, *_ = values
        if not _prepare_equipment_seed_row(
            connection,
            "CameraBodyCatalog",
            seed_key,
            "brand = ? AND model = ?",
            (brand, model),
        ):
            continue
        connection.execute(
            """
            INSERT INTO CameraBodyCatalog (
                brand, model, body_type, sensor_format, lens_mount,
                sensor_width_mm, sensor_height_mm, resolution_width_px,
                resolution_height_px, raw_bit_depth, max_video_width_px,
                max_video_height_px, max_video_fps, live_view, bulb_mode,
                source_url, is_builtin, seed_key, is_user_modified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0)
            ON CONFLICT(seed_key) DO UPDATE SET
                brand = excluded.brand,
                model = excluded.model,
                body_type = excluded.body_type,
                sensor_format = excluded.sensor_format,
                lens_mount = excluded.lens_mount,
                sensor_width_mm = excluded.sensor_width_mm,
                sensor_height_mm = excluded.sensor_height_mm,
                resolution_width_px = excluded.resolution_width_px,
                resolution_height_px = excluded.resolution_height_px,
                raw_bit_depth = excluded.raw_bit_depth,
                max_video_width_px = excluded.max_video_width_px,
                max_video_height_px = excluded.max_video_height_px,
                max_video_fps = excluded.max_video_fps,
                live_view = excluded.live_view,
                bulb_mode = excluded.bulb_mode,
                source_url = excluded.source_url,
                is_builtin = 1
            WHERE CameraBodyCatalog.is_user_modified = 0
            """,
            values + (seed_key,),
        )


def _astronomy_camera_catalog_rows(
    astronomy_camera_path: Path | None,
) -> list[tuple]:
    return [
        (
            row["brand"],
            row["model"],
            row["camera_class"],
            row["sensor_model"],
            row["sensor_technology"],
            row["color_mode"],
            float(row["sensor_width_mm"]),
            float(row["sensor_height_mm"]),
            int(row["resolution_width_px"]),
            int(row["resolution_height_px"]),
            float(row["pixel_size_um"]),
            int(row["bit_depth"]),
            _optional_float(row.get("max_fps", "")),
            _csv_bool(row.get("cooled", "")),
            _optional_float(row.get("cooling_delta_c", "")),
            row["shutter_type"],
            _optional_float(row.get("backfocus_mm", "")),
            row.get("source_url", ""),
            seed_key,
        )
        for row, seed_key in _equipment_catalog_source_rows(
            astronomy_camera_path,
            "astronomy camera",
            "astro-camera",
        )
    ]


def _camera_body_catalog_rows(camera_body_path: Path | None) -> list[tuple]:
    return [
        (
            row["brand"],
            row["model"],
            row["body_type"],
            row["sensor_format"],
            row["lens_mount"],
            float(row["sensor_width_mm"]),
            float(row["sensor_height_mm"]),
            int(row["resolution_width_px"]),
            int(row["resolution_height_px"]),
            int(row["raw_bit_depth"]),
            _optional_int(row.get("max_video_width_px", "")),
            _optional_int(row.get("max_video_height_px", "")),
            _optional_float(row.get("max_video_fps", "")),
            _csv_bool(row.get("live_view", "")),
            _csv_bool(row.get("bulb_mode", "")),
            row.get("source_url", ""),
            seed_key,
        )
        for row, seed_key in _equipment_catalog_source_rows(
            camera_body_path,
            "camera body",
            "camera-body",
        )
    ]


def _seed_filters_reducers_catalog(
    connection: sqlite3.Connection,
    filter_path: Path | None = None,
    reducer_path: Path | None = None,
    compatibility_path: Path | None = None,
) -> None:
    for row in _filter_catalog_rows(filter_path):
        values = row[:-1]
        seed_key = row[-1]
        brand, model, *_ = values
        if not _prepare_equipment_seed_row(
            connection,
            "FilterCatalog",
            seed_key,
            "brand = ? AND model = ?",
            (brand, model),
        ):
            continue
        connection.execute(
            """
            INSERT INTO FilterCatalog (
                brand, model, filter_class, central_wavelength_nm,
                bandwidth_nm, transmission_pct, minimum_aperture_mm, notes,
                is_builtin, seed_key, is_user_modified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0)
            ON CONFLICT(seed_key) DO UPDATE SET
                brand = excluded.brand,
                model = excluded.model,
                filter_class = excluded.filter_class,
                central_wavelength_nm = excluded.central_wavelength_nm,
                bandwidth_nm = excluded.bandwidth_nm,
                transmission_pct = excluded.transmission_pct,
                minimum_aperture_mm = excluded.minimum_aperture_mm,
                notes = excluded.notes,
                is_builtin = 1
            WHERE FilterCatalog.is_user_modified = 0
            """,
            values + (seed_key,),
        )
    for row in _reducer_catalog_rows(reducer_path):
        values = row[:-1]
        seed_key = row[-1]
        brand, model, factor, *_ = values
        if not _prepare_equipment_seed_row(
            connection,
            "ReducerCatalog",
            seed_key,
            "brand = ? AND model = ? AND reduction_factor = ?",
            (brand, model, factor),
        ):
            continue
        connection.execute(
            """
            INSERT INTO ReducerCatalog (
                brand, model, reduction_factor, optical_system,
                connection, backfocus_mm,
                visual_compatible, imaging_compatible, corrected_field,
                notes, is_builtin, seed_key, is_user_modified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0)
            ON CONFLICT(seed_key) DO UPDATE SET
                brand = excluded.brand,
                model = excluded.model,
                reduction_factor = excluded.reduction_factor,
                optical_system = excluded.optical_system,
                connection = excluded.connection,
                backfocus_mm = excluded.backfocus_mm,
                visual_compatible = excluded.visual_compatible,
                imaging_compatible = excluded.imaging_compatible,
                corrected_field = excluded.corrected_field,
                notes = excluded.notes,
                is_builtin = 1
            WHERE ReducerCatalog.is_user_modified = 0
            """,
            values + (seed_key,),
        )
    _seed_reducer_telescope_compatibility(connection, compatibility_path)


def _seed_reducer_telescope_compatibility(
    connection: sqlite3.Connection,
    compatibility_path: Path | None,
) -> None:
    if not compatibility_path or not compatibility_path.exists():
        raise FileNotFoundError("Missing reducer telescope compatibility seed CSV.")
    with compatibility_path.open("r", encoding="utf-8", newline="") as file:
        source_rows = list(csv.DictReader(file))

    resolved_rows: list[tuple[int, int]] = []
    for row in source_rows:
        reducer_seed_key = _required_equipment_seed_key(
            row,
            "reducer",
            "reducer_seed_key",
        )
        telescope_seed_key = _required_equipment_seed_key(
            row,
            "telescope",
            "telescope_seed_key",
        )
        reducer = connection.execute(
            """
            SELECT id, is_user_modified
            FROM ReducerCatalog
            WHERE seed_key = ?
            """,
            (reducer_seed_key,),
        ).fetchone()
        telescope = connection.execute(
            """
            SELECT model.id
            FROM TelescopeModel model
            WHERE model.seed_key = ?
            """,
            (telescope_seed_key,),
        ).fetchone()
        if reducer is None or telescope is None:
            raise ValueError(
                "Unresolved reducer compatibility: "
                f"{row['reducer_brand']} {row['reducer_model']} -> "
                f"{row['telescope_brand']} {row['telescope_model']}"
            )
        if bool(reducer["is_user_modified"]):
            continue
        resolved_rows.append((int(reducer["id"]), int(telescope["id"])))

    if len(resolved_rows) != len(set(resolved_rows)):
        raise ValueError("Duplicate reducer telescope compatibility seed row.")
    connection.execute(
        """
        DELETE FROM ReducerTelescopeCompatibility
        WHERE reducer_id IN (
            SELECT id
            FROM ReducerCatalog
            WHERE is_builtin = 1 AND is_user_modified = 0
        )
        """
    )
    connection.executemany(
        """
        INSERT INTO ReducerTelescopeCompatibility (reducer_id, telescope_model_id)
        VALUES (?, ?)
        """,
        resolved_rows,
    )


def _filter_catalog_rows(filter_path: Path | None) -> list[tuple]:
    return [
        (
            row["brand"],
            row["model"],
            row["filter_class"],
            _optional_float(row.get("central_wavelength_nm", "")),
            _optional_float(row.get("bandwidth_nm", "")),
            _optional_float(row.get("transmission_pct", "")),
            _optional_int(row.get("minimum_aperture_mm", "")),
            row.get("notes", ""),
            seed_key,
        )
        for row, seed_key in _equipment_catalog_source_rows(
            filter_path,
            "filter",
            "filter",
        )
    ]


def _reducer_catalog_rows(reducer_path: Path | None) -> list[tuple]:
    return [
        (
            row["brand"],
            row["model"],
            float(row["reduction_factor"]),
            row["optical_system"],
            row.get("connection", ""),
            _optional_float(row.get("backfocus_mm", "")),
            _csv_bool(row.get("visual_compatible", "")),
            _csv_bool(row.get("imaging_compatible", "")),
            _csv_bool(row.get("corrected_field", "")),
            row.get("notes", ""),
            seed_key,
        )
        for row, seed_key in _equipment_catalog_source_rows(
            reducer_path,
            "reducer",
            "reducer",
        )
    ]


def _seed_object_images(connection: sqlite3.Connection, images_path: Path | None = None) -> None:
    # Retire only the known bundled deep-sky records. User-supplied metadata
    # is not a seed and must survive initialization, even for a Messier ID.
    retired = [
        (object_id, image_path, license_label)
        for object_id, image_path, license_label in connection.execute(
            "SELECT object_id, image_path, license FROM ObjectImages"
        )
        if retired_builtin_image(
            {"object_id": object_id, "image_path": image_path, "license": license_label}
        )
    ]
    connection.executemany(
        "DELETE FROM ObjectImages WHERE object_id = ? AND image_path = ? AND license = ?",
        retired,
    )
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
            difficulty_medium_scope, difficulty_large_scope, is_builtin
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ON CONFLICT(object_id) DO UPDATE SET
            short_description = excluded.short_description,
            observing_notes = excluded.observing_notes,
            best_seen = excluded.best_seen,
            difficulty_naked_eye = excluded.difficulty_naked_eye,
            difficulty_binocular = excluded.difficulty_binocular,
            difficulty_small_scope = excluded.difficulty_small_scope,
            difficulty_medium_scope = excluded.difficulty_medium_scope,
            difficulty_large_scope = excluded.difficulty_large_scope
        WHERE ObjectDescription.is_builtin = 1
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
            object_id, curiosity_text, source_label, source_url, verified, is_builtin
        )
        VALUES (?, ?, ?, ?, ?, 1)
        ON CONFLICT(object_id) DO UPDATE SET
            curiosity_text = excluded.curiosity_text,
            source_label = excluded.source_label,
            source_url = excluded.source_url,
            verified = excluded.verified
        WHERE ObjectCuriosity.is_builtin = 1
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
                ("Default", 1, "preset:naked-eye"),
            ],
        )
