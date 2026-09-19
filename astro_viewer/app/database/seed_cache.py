"""Skip unchanged built-in seeds without bypassing bootstrap safety or repairs.

The checkpoint covers input contents, schema and every table read or written by
the seed group. It is committed with the seeds, never in a separate transaction.
It is only an optimization: missing/invalid metadata uses the ordinary seed path.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


logger = logging.getLogger(__name__)
SOURCE_NAME = "nightscope-builtin-seeds"
# Bump when seed behavior/dependencies change, including code-only corrections.
# Bundled CSV contents and schema SQL/version are additionally hashed every time.
SEED_REVISION = 1
SEED_FILES = (
    "catalogue_designations_seed.csv",
    "telescope_catalog_seed.csv",
    "smart_telescope_capabilities_seed.csv",
    "eyepiece_catalog_seed.csv",
    "barlow_catalog_seed.csv",
    "binocular_catalog_seed.csv",
    "astronomy_camera_catalog_seed.csv",
    "camera_body_catalog_seed.csv",
    "filter_catalog_seed.csv",
    "reducer_catalog_seed.csv",
    "reducer_telescope_compatibility_seed.csv",
    "object_images_seed.csv",
    "object_descriptions_seed.csv",
    "object_curiosities_seed.csv",
)
# Static queries make both the dependency boundary and stable row order explicit.
# Preferences are a dependency of built-in object identity merging. Default
# profiles remain outside the cache, as do the separate GeoNames/MPC importers.
STATE_QUERIES = (
    "SELECT * FROM CatalogueObject ORDER BY object_id",
    "SELECT * FROM CatalogueDesignation ORDER BY catalogue, designation",
    "SELECT * FROM CatalogueRecommendationPreference ORDER BY object_id",
    "SELECT * FROM TelescopeBrand ORDER BY id",
    "SELECT * FROM TelescopeModel ORDER BY id",
    "SELECT * FROM SmartTelescopeCapability ORDER BY telescope_model_id",
    "SELECT * FROM EyepieceCatalog ORDER BY id",
    "SELECT * FROM BarlowCatalog ORDER BY id",
    "SELECT * FROM BinocularCatalog ORDER BY id",
    "SELECT * FROM AstronomyCameraCatalog ORDER BY id",
    "SELECT * FROM CameraBodyCatalog ORDER BY id",
    "SELECT * FROM FilterCatalog ORDER BY id",
    "SELECT * FROM ReducerCatalog ORDER BY id",
    "SELECT * FROM ReducerTelescopeCompatibility ORDER BY reducer_id, telescope_model_id",
    "SELECT * FROM ObjectImages ORDER BY object_id",
    "SELECT * FROM ObjectDescription ORDER BY object_id",
    "SELECT * FROM ObjectCuriosity ORDER BY object_id",
)


@dataclass(frozen=True)
class _SourceFingerprint:
    digest: str
    size: int


def _source_fingerprint(
    catalogue_objects_path: Path, schema_sql: str, schema_version: int
) -> _SourceFingerprint | None:
    """Hash bytes, not timestamps: same-size or restored files must invalidate."""
    digest = hashlib.sha256()
    schema_bytes = schema_sql.encode("utf-8")
    digest.update(f"{SEED_REVISION}:{schema_version}:".encode("ascii"))
    digest.update(hashlib.sha256(schema_bytes).digest())
    size = len(schema_bytes)
    paths = (catalogue_objects_path,) + tuple(
        catalogue_objects_path.parent / name for name in SEED_FILES
    )
    try:
        for path in paths:
            digest.update(path.name.encode("utf-8") + b"\0")
            try:
                with path.open("rb") as stream:
                    file_digest = hashlib.file_digest(stream, "sha256").digest()
                    size += os.fstat(stream.fileno()).st_size
            except FileNotFoundError:
                # Optional absent sources still belong to the input signature.
                digest.update(b"missing\0")
            else:
                digest.update(b"present\0" + file_digest)
    except OSError:
        logger.debug("Cannot fingerprint built-in sources; running full seeding.", exc_info=True)
        return None
    return _SourceFingerprint(digest.hexdigest(), size)


def _state_fingerprint(connection: sqlite3.Connection) -> str | None:
    """Stream complete rows, including custom fields, with bounded memory use."""
    digest = hashlib.sha256()
    queries = (
        "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name",
        *STATE_QUERIES,
    )
    try:
        for query in queries:
            cursor = connection.execute(query)
            digest.update(query.encode("utf-8") + b"\n")
            digest.update(json.dumps([column[0] for column in cursor.description]).encode("utf-8"))
            for row in cursor:
                digest.update(json.dumps(
                    tuple(row), ensure_ascii=True, separators=(",", ":"), allow_nan=False
                ).encode("ascii") + b"\n")
    except (TypeError, ValueError):
        # Unexpected SQLite value types must not make an otherwise usable DB fail.
        logger.debug("Cannot fingerprint seed state; running full seeding.", exc_info=True)
        return None
    return digest.hexdigest()


def _checkpoint_state(connection: sqlite3.Connection, source_digest: str) -> str | None:
    row = connection.execute(
        "SELECT report_json FROM DataImportLog WHERE source_name = ? "
        "AND length(report_json) <= 4096",
        (SOURCE_NAME,),
    ).fetchone()
    if row is None or not isinstance(row[0], str):
        return None
    try:
        record = json.loads(row[0])
    except (ValueError, RecursionError):
        return None
    if not isinstance(record, dict):
        return None
    if record.get("revision") != SEED_REVISION or record.get("source_sha256") != source_digest:
        return None
    state = record.get("state_sha256")
    return state if isinstance(state, str) and len(state) == 64 else None


def seed_if_needed(
    connection: sqlite3.Connection,
    catalogue_objects_path: Path,
    schema_sql: str,
    schema_version: int,
    seed: Callable[[], None],
) -> None:
    """Run unchanged seed logic unless inputs AND the last seeded state match.

    The caller owns commit/rollback. A writer cannot mutate the checked state before
    the checkpoint is saved. Custom triggers disable skipping altogether: their
    side effects could depend on even an otherwise redundant seed UPDATE.
    """
    if not connection.in_transaction:
        connection.execute("BEGIN IMMEDIATE")
    if connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'trigger' LIMIT 1"
    ).fetchone():
        seed()
        return
    sources = _source_fingerprint(catalogue_objects_path, schema_sql, schema_version)
    if sources is None:
        seed()
        return
    previous_state = _checkpoint_state(connection, sources.digest)
    if previous_state is not None and previous_state == _state_fingerprint(connection):
        logger.info("Built-in seed sources and database state unchanged; skipping reseeding.")
        return

    seed()
    state = _state_fingerprint(connection)
    if state is None or sources != _source_fingerprint(
        catalogue_objects_path, schema_sql, schema_version
    ):
        # Never bless partial input updates or failed/incomparable seed states.
        return
    connection.execute(
        """
        INSERT INTO DataImportLog (
            source_name, source_path, source_size, source_mtime, imported_at, report_json
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(source_name) DO UPDATE SET
            source_path = excluded.source_path,
            source_size = excluded.source_size,
            source_mtime = excluded.source_mtime,
            imported_at = excluded.imported_at,
            report_json = excluded.report_json
        """,
        (
            SOURCE_NAME,
            str(catalogue_objects_path.parent),
            sources.size,
            "sha256:" + sources.digest,
            datetime.now(timezone.utc).isoformat(),
            json.dumps({
                "revision": SEED_REVISION,
                "source_sha256": sources.digest,
                "state_sha256": state,
            }, sort_keys=True),
        ),
    )
