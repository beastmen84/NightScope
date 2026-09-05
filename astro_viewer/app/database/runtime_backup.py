"""Create consistent SQLite snapshots and preserve managed photographs during runtime relocation.

Snapshots replace the previous backup only after SQLite validation and file
flush. Personal files are immutable and copied before their database moves;
partial failures leave originals and existing target files intact. Neither
operation deletes photographs or constitutes a complete settings/keyring export.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import sqlite3
import tempfile
import time
from contextlib import closing
from pathlib import Path


BACKUP_TIMEOUT_SECONDS = 10.0
MAX_MANAGED_IMAGE_BYTES = 16 * 1024 * 1024
_MANAGED_IMAGE_NAME = re.compile(r"([0-9a-f]{64})(-thumb)?\.jpg")


def snapshot_database(source: Path, target: Path) -> None:
    """Copy committed SQLite state, including WAL, without replacing a good backup on failure."""
    if not source.is_file() or source.resolve() == target.resolve() or target.is_symlink():
        raise OSError("Unsafe database snapshot path")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".nightscope-backup-", delete=False) as stream:
        temporary = Path(stream.name)
    deadline = time.monotonic() + BACKUP_TIMEOUT_SECONDS

    def progress(_status: int, _remaining: int, _total: int) -> None:
        if time.monotonic() > deadline:
            raise TimeoutError("Database snapshot exceeded its time limit")

    try:
        with (
            closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as origin,
            closing(sqlite3.connect(temporary)) as destination,
        ):
            origin.backup(destination, pages=256, progress=progress, sleep=0.025)
            destination.execute("PRAGMA journal_mode=DELETE")
            if destination.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise sqlite3.DatabaseError("Invalid database snapshot")
        with temporary.open("r+b") as stream:
            os.fsync(stream.fileno())
        if target.is_symlink():
            raise OSError("Redirected database snapshot path")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def migrate_database(source: Path, target: Path) -> None:
    """Relocate healthy SQLite including WAL; retain corrupt bytes for bootstrap quarantine."""
    try:
        snapshot_database(source, target)
        return
    except sqlite3.DatabaseError as error:
        if getattr(error, "sqlite_errorcode", 0) & 0xFF not in {sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB}:
            raise
    # Preserve the established corrupt-database recovery path, but do not turn
    # locking, permission or disk errors into a potentially incomplete raw copy.
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".nightscope-backup-", delete=False) as stream:
        temporary = Path(stream.name)
    try:
        shutil.copyfile(source, temporary)
        with temporary.open("r+b") as stream:
            os.fsync(stream.fileno())
        if target.is_symlink():
            raise OSError("Redirected database migration path")
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _managed_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANAGED_IMAGE_BYTES:
        raise OSError("Unsafe managed image file")
    with path.open("rb") as stream:
        content = stream.read(MAX_MANAGED_IMAGE_BYTES + 1)
    if len(content) > MAX_MANAGED_IMAGE_BYTES:
        raise OSError("Oversized managed image file")
    return content


def copy_personal_image_store(source: Path, target: Path) -> None:
    """Copy only flat managed filenames; never follow redirects or overwrite conflicting content.

    Called before legacy database installation. Identical files can be reused
    after an interrupted migration; old/orphaned hashes are retained because
    a database backup may reference them. Preview and unknown files are ignored.
    """
    if source.is_symlink():
        raise OSError("Redirected personal image directory")
    if not source.exists():
        return
    if not source.is_dir() or source.resolve().parent != source.parent.resolve():
        raise OSError("Unsafe personal image directory")
    if target.is_symlink() or target.resolve().parent != target.parent.resolve():
        raise OSError("Redirected personal image destination")
    if source.resolve() == target.resolve():
        return
    for path in sorted(source.iterdir()):
        match = _MANAGED_IMAGE_NAME.fullmatch(path.name)
        if match is None:
            continue
        content = _managed_bytes(path)
        if not match.group(2) and hashlib.sha256(content).hexdigest() != match.group(1):
            raise OSError("Personal image hash mismatch")
        target.mkdir(parents=True, exist_ok=True)
        destination = target / path.name
        if destination.exists() or destination.is_symlink():
            if _managed_bytes(destination) != content:
                raise OSError("Conflicting personal image destination")
            continue
        with tempfile.NamedTemporaryFile(dir=target, prefix=".pending-", delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                stream.close()
                temporary.unlink(missing_ok=True)
                raise
        try:
            if destination.is_symlink():
                raise OSError("Redirected personal image destination")
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
