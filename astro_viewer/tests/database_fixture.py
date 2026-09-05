"""Prepare private test databases from a freshly bootstrapped, worker-local seed.

Only setup code opts in: bootstrap, migration and recovery tests must keep calling
the real initializer. No template or connection survives a pytest session, and
no mutable database is shared between tests. Outside the session context, the
helper falls back to ordinary initialization (including direct unittest runs).
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from contextvars import ContextVar
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from uuid import uuid4

from astro_viewer.app.database import bootstrap


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "data" / "schema.sql"


class SeededDatabaseFactory:
    """Own one lazy, closed seed file in a caller-owned temporary directory.

    Copies are exclusive new files, not links. GeoNames is imported normally
    into each copy from that test's directory, retaining its own provenance.
    Templates support only the repository schema and unmodified seed inputs;
    tests of alternate schemas or seed changes must use real initialization.
    """

    def __init__(self, directory: Path) -> None:
        self._directory = directory
        self._template: Path | None = None
        self._lock = Lock()

    def prepare(self, database_path: Path, schema_path: Path) -> None:
        if schema_path.resolve() != SCHEMA_PATH:
            raise ValueError("Seeded fixtures require the repository schema.")
        _require_new_database(database_path)
        with self._lock:
            if self._template is None:
                # A failed build is never reused; the session owns its cleanup.
                candidate = self._directory / f"seed-{uuid4().hex}.db"
                bootstrap.initialize_database(
                    candidate, SCHEMA_PATH, geonames_data_dir=self._directory
                )
                self._template = candidate
            template = self._template

        # initialize_database has closed/committed every connection at this point.
        with template.open("rb") as source, database_path.open("xb") as target:
            shutil.copyfileobj(source, target)

        with closing(sqlite3.connect(database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            bootstrap._import_geonames_cities_if_available(
                connection, database_path.parent, warn_if_missing=False
            )
            connection.commit()


_factory: ContextVar[SeededDatabaseFactory | None] = ContextVar(
    "nightscope_test_database_factory", default=None
)


def _require_new_database(database_path: Path) -> None:
    if database_path.exists() or database_path.is_symlink():
        raise FileExistsError(f"Test database already exists: {database_path}")


def prepare_database(database_path: Path, schema_path: Path) -> None:
    """Create an isolated, fully seeded fixture; never migrate/overwrite a file."""
    _require_new_database(database_path)
    factory = _factory.get()
    if factory is None:
        bootstrap.initialize_database(database_path, schema_path)
    else:
        factory.prepare(database_path, schema_path)


@contextmanager
def database_fixture_session() -> Iterator[None]:
    """Install a disposable factory in this worker, restoring any outer context."""
    with TemporaryDirectory(prefix="nightscope-test-seed-") as directory:
        token = _factory.set(SeededDatabaseFactory(Path(directory)))
        try:
            yield
        finally:
            _factory.reset(token)
