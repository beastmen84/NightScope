"""Initialize the canonical NightScope SQLite database outside the GUI startup path."""

from __future__ import annotations

from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.main import _data_dir, _database_paths


def main() -> None:
    """Initialize the canonical runtime database from the application paths."""

    runtime_database_path, schema_path = _database_paths()
    initialize_database(
        runtime_database_path,
        schema_path,
        geonames_data_dir=_data_dir(),
    )
    print("Database inizializzato:", runtime_database_path)


if __name__ == "__main__":
    main()
