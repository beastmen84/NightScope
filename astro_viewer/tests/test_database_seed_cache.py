"""Protect cached bootstrap parity, invalidation, repairs and transaction safety."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest

from astro_viewer.app.database import bootstrap, seed_cache
from astro_viewer.tests.database_fixture import SCHEMA_PATH, prepare_database
from astro_viewer.tests.geonames_fixture import write_small_geonames_fixture
from astro_viewer.tests.test_database_fixture import _snapshot


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    database_path = tmp_path / "cached.db"
    prepare_database(database_path, SCHEMA_PATH)
    return database_path


def _execute(database_path: Path, sql: str, parameters: tuple = ()) -> None:
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(sql, parameters)
        connection.commit()


def _checkpoint(database_path: Path) -> str | None:
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute(
            "SELECT report_json FROM DataImportLog WHERE source_name = ?",
            (seed_cache.SOURCE_NAME,),
        ).fetchone()
        return row[0] if row else None


def _domain_snapshot(database_path: Path) -> dict:
    """Compare all data/schema, excluding only import telemetry and allocators.

    Redundant INSERT ON CONFLICT attempts advance sqlite_sequence even when no
    row changes. Skipping those attempts deliberately avoids that internal churn.
    All actual object/equipment/profile IDs and every stored field are compared.
    """
    snapshot = _snapshot(database_path)
    snapshot["tables"].pop("sqlite_sequence")
    snapshot["tables"]["DataImportLog"] = [
        row for row in snapshot["tables"]["DataImportLog"]
        if json.loads(row)["source_name"] != seed_cache.SOURCE_NAME
    ]
    return snapshot


def _initialize_without_cache(database_path: Path, schema: Path = SCHEMA_PATH) -> None:
    with patch.object(bootstrap, "seed_if_needed", side_effect=lambda *args: args[-1]()):
        bootstrap.initialize_database(database_path, schema)


def _copy_sources(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for path in (SCHEMA_PATH, *SCHEMA_PATH.parent.glob("*_seed.csv")):
        shutil.copy2(path, data_dir / path.name)
    return data_dir / SCHEMA_PATH.name


def test_unchanged_bootstrap_skips_seeds_but_keeps_safety_and_progress(seeded_db: Path) -> None:
    before = _domain_snapshot(seeded_db)
    stamp = _checkpoint(seeded_db)
    assert stamp is not None
    messages = []
    with (
        patch.object(bootstrap, "_seed_builtin_catalogues") as seed,
        patch.object(bootstrap, "_database_is_healthy", wraps=bootstrap._database_is_healthy) as health,
        patch.object(bootstrap, "_backup_database", wraps=bootstrap._backup_database) as backup,
        patch.object(bootstrap, "_migrate_database", wraps=bootstrap._migrate_database) as migrate,
    ):
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH, progress_callback=messages.append)
    seed.assert_not_called()
    health.assert_called_once_with(seeded_db)
    backup.assert_called_once_with(seeded_db)
    migrate.assert_called_once()
    assert len(messages) >= 3
    assert _checkpoint(seeded_db) == stamp
    assert _domain_snapshot(seeded_db) == before
    assert _domain_snapshot(seeded_db.with_suffix(".db.backup")) == before


def test_cached_and_unconditional_bootstrap_match_every_business_row(seeded_db: Path) -> None:
    full = seeded_db.with_name("full.db")
    shutil.copy2(seeded_db, full)
    for _ in range(3):
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
        _initialize_without_cache(full)
        assert _domain_snapshot(seeded_db) == _domain_snapshot(full)


@pytest.mark.parametrize("sql", [
    "UPDATE CatalogueObject SET descrizione = 'local' WHERE object_id = 'messier-M1'",
    "UPDATE CatalogueDesignation SET sort_index = sort_index + 1 WHERE designation = 'M1'",
    "INSERT INTO CatalogueRecommendationPreference VALUES ('messier-M1', 0)",
    "UPDATE TelescopeBrand SET name = name || ' local' WHERE id = 1",
    "UPDATE TelescopeModel SET notes = 'local' WHERE id = 1",
    "UPDATE SmartTelescopeCapability SET sensor_model = 'local'",
    "UPDATE EyepieceCatalog SET notes = 'local' WHERE id = 1",
    "UPDATE BarlowCatalog SET notes = 'local' WHERE id = 1",
    "UPDATE BinocularCatalog SET magnification = magnification + 1 WHERE id = 1",
    "UPDATE AstronomyCameraCatalog SET source_url = 'local' WHERE id = 1",
    "UPDATE CameraBodyCatalog SET source_url = 'local' WHERE id = 1",
    "UPDATE FilterCatalog SET notes = 'local' WHERE id = 1",
    "UPDATE ReducerCatalog SET notes = 'local' WHERE id = 1",
    "DELETE FROM ReducerTelescopeCompatibility",
    "UPDATE ObjectImages SET attribution = 'local' WHERE object_id = 'sun'",
    "UPDATE ObjectDescription SET short_description = 'local' WHERE object_id = 'messier-M1'",
    "UPDATE ObjectCuriosity SET curiosity_text = 'local' WHERE object_id = 'sun'",
    "DELETE FROM CatalogueObject WHERE object_id = 'messier-M110'",
], ids=[
    "object", "designation", "preference", "brand", "telescope", "smart",
    "eyepiece", "barlow", "binocular", "astro-camera", "camera-body", "filter",
    "reducer", "compatibility", "image", "description", "curiosity", "missing-object",
])
def test_each_seed_dependency_invalidates_and_matches_full_repair(seeded_db: Path, sql: str) -> None:
    _execute(seeded_db, sql)
    full = seeded_db.with_name("full.db")
    shutil.copy2(seeded_db, full)
    with patch.object(
        bootstrap, "_seed_builtin_catalogues", wraps=bootstrap._seed_builtin_catalogues
    ) as seed:
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    seed.assert_called_once()
    _initialize_without_cache(full)
    assert _domain_snapshot(seeded_db) == _domain_snapshot(full)
    with patch.object(bootstrap, "_seed_builtin_catalogues") as seed:
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    seed.assert_not_called()


def test_user_customizations_survive_both_refresh_and_cache_hit(seeded_db: Path) -> None:
    for sql in (
        "UPDATE TelescopeModel SET notes = 'my telescope', is_user_modified = 1 WHERE id = 1",
        "UPDATE ObjectDescription SET short_description = 'my note', is_builtin = 0 "
        "WHERE object_id = 'messier-M1'",
        "UPDATE ObjectCuriosity SET curiosity_text = 'my curiosity', is_builtin = 0 "
        "WHERE object_id = 'sun'",
        "INSERT INTO CatalogueRecommendationPreference VALUES ('messier-M1', 0)",
    ):
        _execute(seeded_db, sql)
    before = _domain_snapshot(seeded_db)
    bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    assert _domain_snapshot(seeded_db) == before


@pytest.mark.parametrize("sql", [
    "DELETE FROM EquipmentProfile",
    "INSERT INTO WeatherCache(cache_key, fetched_at, payload) VALUES ('test', 'today', '{}')",
    "INSERT INTO ObservationHistory(date, object_name, location) VALUES ('today', 'M1', 'here')",
    "UPDATE EquipmentProfile SET profile_name = 'my profile', active = 0",
])
def test_unrelated_runtime_writes_do_not_force_reseeding(seeded_db: Path, sql: str) -> None:
    _execute(seeded_db, sql)
    with patch.object(bootstrap, "_seed_builtin_catalogues") as seed:
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    seed.assert_not_called()
    with closing(sqlite3.connect(seeded_db)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM EquipmentProfile").fetchone()[0] == 1


@pytest.mark.parametrize("record", [
    None, "{", "[]", "null", "{}", '"' + "x" * 5000 + '"', "[" * 2000 + "]" * 2000,
])
def test_missing_or_invalid_checkpoint_falls_back(seeded_db: Path, record: str | None) -> None:
    if record is None:
        _execute(seeded_db, "DELETE FROM DataImportLog WHERE source_name = ?", (seed_cache.SOURCE_NAME,))
    else:
        _execute(seeded_db, "UPDATE DataImportLog SET report_json = ? WHERE source_name = ?",
                 (record, seed_cache.SOURCE_NAME))
    with patch.object(
        bootstrap, "_seed_builtin_catalogues", wraps=bootstrap._seed_builtin_catalogues
    ) as seed:
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    seed.assert_called_once()
    assert json.loads(_checkpoint(seeded_db))["revision"] == seed_cache.SEED_REVISION


@pytest.mark.parametrize("change", ["revision", "schema-version", "schema-sql", "database-schema"])
def test_seed_or_schema_changes_invalidate(
    seeded_db: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    if change == "revision":
        monkeypatch.setattr(seed_cache, "SEED_REVISION", seed_cache.SEED_REVISION + 1)
    elif change == "schema-version":
        monkeypatch.setattr(bootstrap, "SCHEMA_VERSION", bootstrap.SCHEMA_VERSION + 1)
    elif change == "schema-sql":
        schema_sql += "\n-- changed bundle\n"
    else:
        _execute(seeded_db, "CREATE INDEX custom_seed_index ON CatalogueObject(nome)")
    with patch.object(
        bootstrap, "_seed_builtin_catalogues", wraps=bootstrap._seed_builtin_catalogues
    ) as seed:
        bootstrap._build_database(seeded_db, schema_sql, SCHEMA_PATH.with_name("catalogue_objects_seed.csv"))
    seed.assert_called_once()


def test_same_size_and_mtime_source_edit_is_detected(seeded_db: Path, tmp_path: Path) -> None:
    schema = _copy_sources(tmp_path)
    source = schema.with_name("object_curiosities_seed.csv")
    stat = source.stat()
    original = source.read_bytes()
    changed = original.replace(b"NASA Science", b"Test Science", 1)
    assert len(changed) == len(original) and changed != original
    source.write_bytes(changed)
    os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with patch.object(
        bootstrap, "_seed_builtin_catalogues", wraps=bootstrap._seed_builtin_catalogues
    ) as seed:
        bootstrap.initialize_database(seeded_db, schema)
    seed.assert_called_once()
    with closing(sqlite3.connect(seeded_db)) as connection:
        assert connection.execute(
            "SELECT source_label FROM ObjectCuriosity WHERE object_id = 'sun'"
        ).fetchone()[0] == "Test Science"


def test_optional_source_removal_and_return_invalidate(seeded_db: Path, tmp_path: Path) -> None:
    schema = _copy_sources(tmp_path)
    source = schema.with_name("object_curiosities_seed.csv")
    source.unlink()
    with patch.object(
        bootstrap, "_seed_builtin_catalogues", wraps=bootstrap._seed_builtin_catalogues
    ) as seed:
        bootstrap.initialize_database(seeded_db, schema)
        shutil.copy2(SCHEMA_PATH.with_name(source.name), source)
        bootstrap.initialize_database(seeded_db, schema)
    assert seed.call_count == 2


@pytest.mark.parametrize("invalid", [False, True])
def test_required_source_failure_is_not_hidden_by_checkpoint(
    seeded_db: Path, tmp_path: Path, invalid: bool
) -> None:
    schema = _copy_sources(tmp_path)
    source = schema.with_name("catalogue_objects_seed.csv")
    before = _domain_snapshot(seeded_db)
    stamp = _checkpoint(seeded_db)
    if invalid:
        source.write_text("object_id,nome,tipo\ninvalid-object,,\n", encoding="utf-8")
    else:
        source.unlink()
    with pytest.raises(ValueError if invalid else FileNotFoundError):
        bootstrap.initialize_database(seeded_db, schema)
    assert _checkpoint(seeded_db) == stamp
    assert _domain_snapshot(seeded_db) == before


def test_city_import_still_runs_on_seed_cache_hit(seeded_db: Path) -> None:
    write_small_geonames_fixture(seeded_db.parent, extra_rows=0)
    with patch.object(bootstrap, "_seed_builtin_catalogues") as seed:
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    seed.assert_not_called()
    with closing(sqlite3.connect(seeded_db)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM City").fetchone()[0] == 3


def test_triggers_disable_skipping_and_checkpoint_writes(seeded_db: Path) -> None:
    stamp = _checkpoint(seeded_db)
    _execute(seeded_db, "CREATE TABLE SeedAudit (value TEXT)")
    _execute(seeded_db, """
        CREATE TRIGGER record_seed_update AFTER UPDATE ON CatalogueObject
        BEGIN INSERT INTO SeedAudit VALUES (NEW.object_id); END
    """)
    with patch.object(
        bootstrap, "_seed_builtin_catalogues", wraps=bootstrap._seed_builtin_catalogues
    ) as seed:
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    assert seed.call_count == 2
    assert _checkpoint(seeded_db) == stamp
    with closing(sqlite3.connect(seeded_db)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM SeedAudit").fetchone()[0] > 0


def test_failed_seed_does_not_commit_partial_data_or_checkpoint(seeded_db: Path) -> None:
    _execute(seeded_db, "UPDATE CatalogueObject SET descrizione = 'local' WHERE object_id = 'messier-M1'")
    before = _domain_snapshot(seeded_db)
    stamp = _checkpoint(seeded_db)

    def fail(connection: sqlite3.Connection, _path: Path) -> None:
        connection.execute("UPDATE CatalogueObject SET descrizione = 'partial'")
        raise ValueError("invalid seed")

    with patch.object(bootstrap, "_seed_builtin_catalogues", side_effect=fail):
        with pytest.raises(ValueError, match="invalid seed"):
            bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    assert _checkpoint(seeded_db) == stamp
    assert _domain_snapshot(seeded_db) == before


def test_sources_changed_during_seed_are_not_checkpointed(seeded_db: Path, tmp_path: Path) -> None:
    schema = _copy_sources(tmp_path)
    source = schema.with_name("object_curiosities_seed.csv")
    _execute(seeded_db, "DELETE FROM DataImportLog WHERE source_name = ?", (seed_cache.SOURCE_NAME,))
    real_seed = bootstrap._seed_builtin_catalogues

    def change_source(connection: sqlite3.Connection, path: Path) -> None:
        real_seed(connection, path)
        source.write_bytes(source.read_bytes().replace(b"NASA Science", b"Test Science", 1))

    with patch.object(bootstrap, "_seed_builtin_catalogues", side_effect=change_source):
        bootstrap.initialize_database(seeded_db, schema)
    assert _checkpoint(seeded_db) is None
    bootstrap.initialize_database(seeded_db, schema)
    assert _checkpoint(seeded_db) is not None


def test_input_io_error_uses_original_seed_path(seeded_db: Path) -> None:
    with (
        patch.object(seed_cache.hashlib, "file_digest", side_effect=PermissionError("test")),
        patch.object(bootstrap, "_seed_builtin_catalogues", wraps=bootstrap._seed_builtin_catalogues) as seed,
    ):
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    seed.assert_called_once()


def test_unknown_sqlite_value_type_uses_original_seed_path(seeded_db: Path) -> None:
    _execute(seeded_db, "UPDATE CatalogueObject SET descrizione = ? WHERE object_id = 'messier-M1'", (b"local",))
    stamp = _checkpoint(seeded_db)
    with patch.object(
        bootstrap, "_seed_builtin_catalogues", wraps=bootstrap._seed_builtin_catalogues
    ) as seed:
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    seed.assert_called_once()
    assert _checkpoint(seeded_db) == stamp


def test_other_writer_cannot_change_checked_state(seeded_db: Path) -> None:
    real_fingerprint = seed_cache._state_fingerprint

    def check_lock(connection: sqlite3.Connection) -> str | None:
        assert connection.in_transaction
        with closing(sqlite3.connect(seeded_db, timeout=0)) as other:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                other.execute("UPDATE CatalogueObject SET descrizione = 'racing writer'")
        return real_fingerprint(connection)

    with patch.object(seed_cache, "_state_fingerprint", side_effect=check_lock) as checked:
        bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    checked.assert_called_once()


def test_cache_starts_transaction_when_caller_has_not_started_one(seeded_db: Path) -> None:
    with closing(sqlite3.connect(seeded_db)) as connection:
        assert not connection.in_transaction
        with patch.object(bootstrap, "_seed_builtin_catalogues") as seed:
            seed_cache.seed_if_needed(
                connection, SCHEMA_PATH.with_name("catalogue_objects_seed.csv"),
                SCHEMA_PATH.read_text(encoding="utf-8"), bootstrap.SCHEMA_VERSION, seed,
            )
        seed.assert_not_called()
        assert connection.in_transaction
        with closing(sqlite3.connect(seeded_db, timeout=0)) as other:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                other.execute("UPDATE CatalogueObject SET descrizione = 'racing writer'")
        connection.rollback()


def test_failure_after_checkpoint_rolls_back_checkpoint_and_seeds(seeded_db: Path) -> None:
    _execute(seeded_db, "DELETE FROM DataImportLog WHERE source_name = ?", (seed_cache.SOURCE_NAME,))
    before = _domain_snapshot(seeded_db)
    with patch.object(bootstrap, "_seed_default_profiles", side_effect=ValueError("final step")):
        with pytest.raises(ValueError, match="final step"):
            bootstrap.initialize_database(seeded_db, SCHEMA_PATH)
    assert _checkpoint(seeded_db) is None
    assert _domain_snapshot(seeded_db) == before
