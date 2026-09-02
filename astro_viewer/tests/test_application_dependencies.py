from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

from astro_viewer.app.application.dependencies import (
    build_app_controller_dependencies,
)
from astro_viewer.app.astronomy.engine import MockAstronomyEngine
from astro_viewer.app.astronomy.skyfield_engine import EphemerisUnavailableError


def test_dependency_factory_owns_ephemeris_fallback(tmp_path: Path) -> None:
    base_dir = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "nightscope.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            (base_dir / "data" / "schema.sql").read_text(encoding="utf-8")
        )

    with patch(
        "astro_viewer.app.application.dependencies.SkyfieldAstronomyEngine",
        side_effect=EphemerisUnavailableError("test fixture"),
    ):
        dependencies = build_app_controller_dependencies(
            base_dir=base_dir,
            database_path=database_path,
            preferences_path=tmp_path / "user_preferences.json",
            location_cache_path=tmp_path / "location_cache.json",
            nasa_aod_cache_path=tmp_path / "nasa_aod_cache.json",
        )

    assert isinstance(dependencies.astronomy_engine, MockAstronomyEngine)
    assert dependencies.startup_service_status
