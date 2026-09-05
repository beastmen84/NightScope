"""Protect seeded fixture equivalence, isolation, provenance and session lifetime."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest

from astro_viewer.app.database import bootstrap
from astro_viewer.tests import database_fixture
from astro_viewer.tests.database_fixture import (
    SCHEMA_PATH,
    SeededDatabaseFactory,
    database_fixture_session,
    prepare_database,
)
from astro_viewer.tests.geonames_fixture import write_small_geonames_fixture


def _snapshot(database_path: Path) -> dict:
    """Compare all schema/data except import-log sequence/time/size telemetry."""
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        schema = [tuple(row) for row in connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name"
        )]
        tables = {}
        for (name,) in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ):
            quoted_name = '"' + name.replace('"', '""') + '"'
            rows = []
            for record in connection.execute(f"SELECT * FROM {quoted_name}"):
                row = dict(record)
                if name == "DataImportLog":
                    # GeoNames and MPC imports have the opposite insertion order;
                    # source_name, not the log's surrogate id, identifies an import.
                    assert row.pop("id") > 0
                    assert row.pop("imported_at")
                    report = json.loads(row["report_json"])
                    # GeoNames runs before seeding in a cold bootstrap and after
                    # copying in fixtures. This measures file size at import time.
                    report.pop("db_size_bytes", None)
                    row["report_json"] = report
                rows.append(json.dumps(row, sort_keys=True, ensure_ascii=True))
            tables[name] = sorted(rows)
        return {
            "schema": schema,
            "version": connection.execute("PRAGMA user_version").fetchone()[0],
            "tables": tables,
        }


@pytest.mark.parametrize("with_geonames", [False, True])
def test_seeded_copy_matches_real_bootstrap_in_every_table(
    tmp_path: Path, with_geonames: bool
) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    if with_geonames:
        write_small_geonames_fixture(tmp_path)
    fresh = tmp_path / "fresh.db"
    copied = tmp_path / "copied.db"

    bootstrap.initialize_database(fresh, SCHEMA_PATH)
    SeededDatabaseFactory(template_dir).prepare(copied, SCHEMA_PATH)

    assert _snapshot(copied) == _snapshot(fresh)
    assert not bootstrap.database_initialization_required(copied, SCHEMA_PATH)


def test_copies_are_independent_and_seed_is_built_only_once(tmp_path: Path) -> None:
    factory = SeededDatabaseFactory(tmp_path)
    first, second, third = (tmp_path / f"{name}.db" for name in ("a", "b", "c"))
    with patch.object(
        bootstrap, "initialize_database", wraps=bootstrap.initialize_database
    ) as initialize:
        factory.prepare(first, SCHEMA_PATH)
        original_hash = hashlib.sha256(first.read_bytes()).hexdigest()
        with closing(sqlite3.connect(first)) as connection:
            connection.execute("DELETE FROM ObjectDescription")
            connection.execute("DELETE FROM EquipmentProfile")
            connection.commit()
        factory.prepare(second, SCHEMA_PATH)
        with closing(sqlite3.connect(second)) as connection:
            connection.execute("UPDATE ObjectCuriosity SET curiosity_text = 'changed'")
            connection.commit()
        factory.prepare(third, SCHEMA_PATH)

    initialize.assert_called_once()
    assert hashlib.sha256(third.read_bytes()).hexdigest() == original_hash
    assert hashlib.sha256(first.read_bytes()).hexdigest() != original_hash
    assert hashlib.sha256(second.read_bytes()).hexdigest() != original_hash


def test_existing_destination_is_not_overwritten(tmp_path: Path) -> None:
    destination = tmp_path / "existing.db"
    destination.write_bytes(b"caller-owned data")
    with patch.object(bootstrap, "initialize_database") as initialize:
        with pytest.raises(FileExistsError):
            SeededDatabaseFactory(tmp_path).prepare(destination, SCHEMA_PATH)
        with pytest.raises(FileExistsError):
            prepare_database(destination, SCHEMA_PATH)
    assert destination.read_bytes() == b"caller-owned data"
    initialize.assert_not_called()


def test_alternate_schema_requires_real_bootstrap(tmp_path: Path) -> None:
    with patch.object(bootstrap, "initialize_database") as initialize:
        with pytest.raises(ValueError, match="repository schema"):
            SeededDatabaseFactory(tmp_path).prepare(
                tmp_path / "copy.db", tmp_path / "schema.sql"
            )
    initialize.assert_not_called()
    assert not (tmp_path / "copy.db").exists()


def test_failed_template_build_is_not_cached(tmp_path: Path) -> None:
    factory = SeededDatabaseFactory(tmp_path)
    candidates = []
    initialize = bootstrap.initialize_database

    def fail_once(database_path: Path, schema_path: Path, **kwargs) -> None:
        candidates.append(database_path)
        assert not database_path.exists()
        if len(candidates) == 1:
            database_path.write_bytes(b"interrupted build")
            raise RuntimeError("interrupted build")
        initialize(database_path, schema_path, **kwargs)

    copied = tmp_path / "copy.db"
    with patch.object(bootstrap, "initialize_database", side_effect=fail_once):
        with pytest.raises(RuntimeError, match="interrupted build"):
            factory.prepare(copied, SCHEMA_PATH)
        assert not copied.exists()
        factory.prepare(copied, SCHEMA_PATH)
    assert len(candidates) == 2
    assert candidates[0] != candidates[1]
    assert not bootstrap.database_initialization_required(copied, SCHEMA_PATH)


def test_geonames_is_imported_from_each_tests_own_files(tmp_path: Path) -> None:
    factory = SeededDatabaseFactory(tmp_path)
    for extra_rows in (1, 4):
        directory = tmp_path / str(extra_rows)
        directory.mkdir()
        write_small_geonames_fixture(directory, extra_rows=extra_rows)
        copied = directory / "copy.db"
        factory.prepare(copied, SCHEMA_PATH)
        with closing(sqlite3.connect(copied)) as connection:
            assert connection.execute("SELECT COUNT(*) FROM City").fetchone()[0] == (
                extra_rows + 3
            )
            source_path = connection.execute(
                "SELECT source_path FROM DataImportLog WHERE source_name = ?",
                ("cities15000.txt",),
            ).fetchone()[0]
            assert Path(source_path) == directory / "cities15000.txt"
        assert not bootstrap.database_initialization_required(copied, SCHEMA_PATH)


def test_sessions_rebuild_from_source_and_remove_their_templates(tmp_path: Path) -> None:
    outer_factory = database_fixture._factory.get()
    template_directories = []
    with patch.object(
        bootstrap, "initialize_database", wraps=bootstrap.initialize_database
    ) as initialize:
        for index in range(2):
            with database_fixture_session():
                prepare_database(tmp_path / f"copy-{index}.db", SCHEMA_PATH)
                template = initialize.call_args.args[0]
                assert template.is_file()
                template_directories.append(template.parent)
            assert database_fixture._factory.get() is outer_factory
            assert not template.parent.exists()
    assert initialize.call_count == 2
    assert template_directories[0] != template_directories[1]
    assert all((tmp_path / f"copy-{index}.db").is_file() for index in range(2))


def test_session_restores_context_and_cleans_up_after_exception(tmp_path: Path) -> None:
    outer_factory = database_fixture._factory.get()
    with pytest.raises(RuntimeError, match="test failure"):
        with database_fixture_session():
            factory = database_fixture._factory.get()
            assert factory is not None
            factory_directory = factory._directory
            raise RuntimeError("test failure")
    assert database_fixture._factory.get() is outer_factory
    assert not factory_directory.exists()


def test_without_session_helper_uses_real_initialization(tmp_path: Path) -> None:
    copied = tmp_path / "standalone.db"
    token = database_fixture._factory.set(None)
    try:
        with patch.object(
            bootstrap, "initialize_database", wraps=bootstrap.initialize_database
        ) as initialize:
            prepare_database(copied, SCHEMA_PATH)
        initialize.assert_called_once_with(copied, SCHEMA_PATH)
        assert not bootstrap.database_initialization_required(copied, SCHEMA_PATH)
    finally:
        database_fixture._factory.reset(token)
