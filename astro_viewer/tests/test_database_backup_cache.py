"""Verify whole-DB backup reuse, corruption fallback and SQLite locking safety."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import pytest

from astro_viewer.app.database import backup_cache, bootstrap, runtime_backup
from astro_viewer.tests.database_fixture import SCHEMA_PATH, prepare_database


@pytest.fixture
def database_pair(tmp_path: Path) -> tuple[Path, Path]:
    source, backup = tmp_path / "live.db", tmp_path / "live.db.backup"
    with closing(sqlite3.connect(source)) as connection:
        connection.execute("CREATE TABLE KeepMe(value TEXT)")
        connection.execute("INSERT INTO KeepMe VALUES ('original')")
        connection.commit()
    return source, backup


def _value(path: Path) -> str:
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        return connection.execute("SELECT value FROM KeepMe").fetchone()[0]


def _edit(path: Path, value: str) -> None:
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("UPDATE KeepMe SET value = ?", (value,))
        connection.commit()


def test_unchanged_source_and_verified_backup_skip_copy(database_pair) -> None:
    source, backup = database_pair
    assert backup_cache.refresh_database_backup(source, backup)
    before = backup.stat().st_mtime_ns, backup.read_bytes()
    with patch.object(backup_cache, "snapshot_database") as snapshot:
        assert not backup_cache.refresh_database_backup(source, backup)
    snapshot.assert_not_called()
    assert (backup.stat().st_mtime_ns, backup.read_bytes()) == before
    assert _value(backup) == "original"


def test_same_size_timestamp_change_anywhere_in_db_is_detected(database_pair) -> None:
    source, backup = database_pair
    backup_cache.refresh_database_backup(source, backup)
    before = source.stat()
    _edit(source, "modified")
    assert source.stat().st_size == before.st_size
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert backup_cache.refresh_database_backup(source, backup)
    assert _value(backup) == "modified"
    assert not backup_cache.refresh_database_backup(source, backup)


@pytest.mark.parametrize("damage", ["missing", "corrupt", "valid-but-altered"])
def test_missing_or_changed_backup_is_rebuilt(database_pair, damage: str) -> None:
    source, backup = database_pair
    backup_cache.refresh_database_backup(source, backup)
    if damage == "missing":
        backup.unlink()
    elif damage == "corrupt":
        backup.write_bytes(b"corrupt copy")
    else:
        _edit(backup, "tampered")
    assert backup_cache.refresh_database_backup(source, backup)
    assert _value(backup) == "original"


@pytest.mark.parametrize("record", [
    None, b"{", b"null", b"[]", b"{}", b"\xff", b"x" * 5000,
    b"[" * 2000 + b"]" * 2000,
    json.dumps({"version": 999, "source_sha256": "a" * 64, "backup_sha256": "b" * 64}).encode(),
    json.dumps({"version": 1, "source_sha256": "z" * 64, "backup_sha256": "b" * 64}).encode(),
])
def test_untrusted_checkpoint_uses_full_validated_snapshot(database_pair, record) -> None:
    source, backup = database_pair
    backup_cache.refresh_database_backup(source, backup)
    checkpoint = backup_cache.checkpoint_path(backup)
    if record is None:
        checkpoint.unlink()
    else:
        checkpoint.write_bytes(record)
    assert backup_cache.refresh_database_backup(source, backup)
    assert _value(backup) == "original"
    assert not backup_cache.refresh_database_backup(source, backup)


def test_failed_copy_preserves_previous_backup_and_checkpoint(database_pair) -> None:
    source, backup = database_pair
    backup_cache.refresh_database_backup(source, backup)
    checkpoint = backup_cache.checkpoint_path(backup)
    old = backup.read_bytes(), checkpoint.read_bytes()
    _edit(source, "modified")
    with patch.object(runtime_backup.os, "replace", side_effect=OSError("disk failure")):
        with pytest.raises(OSError, match="disk failure"):
            backup_cache.refresh_database_backup(source, backup)
    assert (backup.read_bytes(), checkpoint.read_bytes()) == old
    assert not list(source.parent.glob(".nightscope-backup-*"))


def test_optional_checkpoint_write_failure_does_not_lose_valid_backup(database_pair) -> None:
    source, backup = database_pair
    checkpoint = backup_cache.checkpoint_path(backup)
    replace = os.replace

    def fail_metadata(origin, target):
        if target == checkpoint:
            raise OSError("metadata unavailable")
        replace(origin, target)

    with patch.object(backup_cache.os, "replace", side_effect=fail_metadata):
        assert backup_cache.refresh_database_backup(source, backup)
    assert _value(backup) == "original"
    assert not checkpoint.exists()
    assert not list(source.parent.glob(".nightscope-backup-*"))
    assert backup_cache.refresh_database_backup(source, backup)


def test_unavailable_source_fingerprint_falls_back_to_copy(database_pair) -> None:
    source, backup = database_pair
    with patch.object(backup_cache, "_file_digest", side_effect=OSError("cannot fingerprint")):
        assert backup_cache.refresh_database_backup(source, backup)
    assert _value(backup) == "original"
    assert not backup_cache.checkpoint_path(backup).exists()


def test_wal_commits_are_never_skipped_or_lost(database_pair) -> None:
    source, backup = database_pair
    backup_cache.refresh_database_backup(source, backup)
    with closing(sqlite3.connect(source)) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("PRAGMA wal_autocheckpoint=0")
        live.execute("UPDATE KeepMe SET value = 'wal commit'")
        live.commit()
        live.execute("UPDATE KeepMe SET value = 'uncommitted'")
        assert source.with_name(source.name + "-wal").stat().st_size > 0
        for _ in range(2):
            assert backup_cache.refresh_database_backup(source, backup)
            assert _value(backup) == "wal commit"
        live.rollback()
    assert backup_cache.refresh_database_backup(source, backup)  # WAL mode persists.


def test_external_wal_on_backup_is_not_overwritten(database_pair) -> None:
    source, backup = database_pair
    backup_cache.refresh_database_backup(source, backup)
    with closing(sqlite3.connect(backup)) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("UPDATE KeepMe SET value = 'external copy'")
        live.commit()
        before = backup.read_bytes()
        with pytest.raises(OSError, match="external WAL"):
            backup_cache.refresh_database_backup(source, backup)
        assert backup.read_bytes() == before
        assert live.execute("SELECT value FROM KeepMe").fetchone()[0] == "external copy"


def test_uncommitted_rollback_journal_write_does_not_make_backup_dirty(database_pair) -> None:
    source, backup = database_pair
    backup_cache.refresh_database_backup(source, backup)
    with closing(sqlite3.connect(source)) as writer:
        writer.execute("UPDATE KeepMe SET value = 'uncommitted'")
        assert not backup_cache.refresh_database_backup(source, backup)
        assert _value(backup) == "original"
        writer.rollback()


def test_source_and_backup_commits_are_blocked_during_comparison(database_pair) -> None:
    source, backup = database_pair
    backup_cache.refresh_database_backup(source, backup)
    fingerprint = backup_cache._file_digest
    checked = []

    def check_lock(path: Path) -> str:
        with closing(sqlite3.connect(path, timeout=0)) as other:
            other.execute("UPDATE KeepMe SET value = 'racing commit'")
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                other.commit()
            other.rollback()
        checked.append(path)
        return fingerprint(path)

    with patch.object(backup_cache, "_file_digest", side_effect=check_lock):
        assert not backup_cache.refresh_database_backup(source, backup)
    assert checked == [source, backup]


def test_post_install_backup_change_cannot_be_blessed_by_metadata(database_pair) -> None:
    source, backup = database_pair
    snapshot = backup_cache.snapshot_database

    def replace_after_snapshot(*args, **kwargs):
        digest = snapshot(*args, **kwargs)
        _edit(backup, "tampered")
        return digest

    with patch.object(backup_cache, "snapshot_database", side_effect=replace_after_snapshot):
        assert backup_cache.refresh_database_backup(source, backup)
    assert backup_cache.refresh_database_backup(source, backup)
    assert _value(backup) == "original"


@pytest.mark.parametrize("path_kind", ["backup", "checkpoint"])
def test_redirected_paths_are_not_followed(database_pair, path_kind: str) -> None:
    source, backup = database_pair
    redirected = backup if path_kind == "backup" else backup_cache.checkpoint_path(backup)
    original = Path.is_symlink
    with patch.object(Path, "is_symlink", side_effect=lambda path: path == redirected or original(path), autospec=True):
        if path_kind == "backup":
            with pytest.raises(OSError, match="Unsafe"):
                backup_cache.refresh_database_backup(source, backup)
        else:
            assert backup_cache.refresh_database_backup(source, backup)
            assert not redirected.exists()


def test_complete_unchanged_bootstrap_preserves_db_bytes_and_reuses_backup(tmp_path: Path) -> None:
    source = tmp_path / "nightscope.db"
    prepare_database(source, SCHEMA_PATH)
    bootstrap.initialize_database(source, SCHEMA_PATH)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with patch.object(backup_cache, "snapshot_database", wraps=backup_cache.snapshot_database) as snapshot:
        bootstrap.initialize_database(source, SCHEMA_PATH)
        bootstrap.initialize_database(source, SCHEMA_PATH)
    snapshot.assert_not_called()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest


def test_backup_still_captures_state_before_seed_repairs(tmp_path: Path) -> None:
    source = tmp_path / "nightscope.db"
    prepare_database(source, SCHEMA_PATH)
    bootstrap.initialize_database(source, SCHEMA_PATH)
    with closing(sqlite3.connect(source)) as connection:
        connection.execute("UPDATE ObjectCuriosity SET curiosity_text='before repair' WHERE object_id='sun'")
        connection.commit()
    bootstrap.initialize_database(source, SCHEMA_PATH)
    with closing(sqlite3.connect(source.with_suffix(".db.backup"))) as backup:
        assert backup.execute("SELECT curiosity_text FROM ObjectCuriosity WHERE object_id='sun'").fetchone()[0] == "before repair"
    with closing(sqlite3.connect(source)) as connection:
        assert connection.execute("SELECT curiosity_text FROM ObjectCuriosity WHERE object_id='sun'").fetchone()[0] != "before repair"
