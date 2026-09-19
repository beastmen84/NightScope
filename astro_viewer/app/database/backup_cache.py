"""Reuse an unchanged, previously validated startup backup; fail back to a full copy.

Whole-file SHA-256 checks cover both database and backup. Read transactions keep
rollback-journal SQLite writers from committing during comparison and copying.
WAL sources/backups always use the original consistent snapshot path.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from contextlib import ExitStack, closing, contextmanager
from pathlib import Path

from astro_viewer.app.database.runtime_backup import snapshot_database


logger = logging.getLogger(__name__)
CHECKPOINT_VERSION = 1


def checkpoint_path(backup: Path) -> Path:
    """Return optional local cache metadata, not a replacement for the backup."""
    return backup.with_suffix(backup.suffix + ".state.json")


@contextmanager
def _read_transaction(path: Path) -> Iterator[sqlite3.Connection]:
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
        connection.execute("BEGIN")
        connection.execute("SELECT name FROM sqlite_master").fetchall()
        yield connection


def _has_wal(path: Path, connection: sqlite3.Connection) -> bool:
    return (
        connection.execute("PRAGMA journal_mode").fetchone()[0].casefold() == "wal"
        or path.with_name(path.name + "-wal").exists()
    )


def _file_digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _read_checkpoint(path: Path) -> dict | None:
    try:
        if path.is_symlink():
            return None
        with path.open("rb") as stream:
            raw = stream.read(4097)
        if len(raw) > 4096:
            return None
        record = json.loads(raw)
    except (OSError, ValueError, UnicodeError, RecursionError):
        return None
    if not isinstance(record, dict) or record.get("version") != CHECKPOINT_VERSION:
        return None
    for key in ("source_sha256", "backup_sha256"):
        value = record.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(
            char not in "0123456789abcdef" for char in value
        ):
            return None
    return record


def _backup_matches(backup: Path, source_digest: str) -> bool:
    record = _read_checkpoint(checkpoint_path(backup))
    if record is None or record["source_sha256"] != source_digest or backup.is_symlink():
        return False
    try:
        with _read_transaction(backup) as connection:
            return not _has_wal(backup, connection) and _file_digest(backup) == record["backup_sha256"]
    except (OSError, sqlite3.Error):
        return False


def _write_checkpoint(backup: Path, source_digest: str, backup_digest: str) -> None:
    path = checkpoint_path(backup)
    temporary: Path | None = None
    try:
        if path.is_symlink():
            raise OSError("Redirected backup checkpoint path")
        payload = json.dumps({
            "version": CHECKPOINT_VERSION,
            "source_sha256": source_digest,
            "backup_sha256": backup_digest,
        }, sort_keys=True).encode("utf-8")
        with tempfile.NamedTemporaryFile(
            dir=backup.parent, prefix=".nightscope-backup-state-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if path.is_symlink():
            raise OSError("Redirected backup checkpoint path")
        os.replace(temporary, path)
    except OSError:
        # The actual backup is already installed and valid. Metadata is optional.
        logger.debug("Backup checkpoint unavailable; next start will copy again.", exc_info=True)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def refresh_database_backup(source: Path, backup: Path) -> bool:
    """Return whether a new backup was installed; never skip on uncertain state.

    No timestamp shortcut, no table subset and no weakening of snapshot validation.
    A checksum is recorded from the validated temporary copy before atomic replace,
    so a subsequently altered backup cannot be blessed by a newly saved checkpoint.
    """
    if not source.is_file() or source.resolve() == backup.resolve() or backup.is_symlink():
        raise OSError("Unsafe database snapshot path")
    with ExitStack() as scope:
        try:
            connection = scope.enter_context(_read_transaction(source))
            source_digest = None if _has_wal(source, connection) else _file_digest(source)
        except (OSError, sqlite3.Error):
            scope.close()
            source_digest = None
        if source_digest is not None and _backup_matches(backup, source_digest):
            return False
        # Do not catch copy failures here or overwrite the previous checkpoint.
        # Bootstrap retains its existing warning/recovery policy for those errors.
        if source_digest is None:
            snapshot_database(source, backup)
        else:
            backup_digest = snapshot_database(source, backup, fingerprint=True)
            if backup_digest is not None:
                _write_checkpoint(backup, source_digest, backup_digest)
        return True
