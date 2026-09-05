"""Protect runtime Moon geometry diagnostics and conditioned target payloads."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.catalogue_repository import CatalogueRepository
from astro_viewer.app.models.observing import MoonGeometrySummary


def test_skyfield_moon_geometry_summary_is_bounded_local_and_json_compatible(tmp_path) -> None:
    base_dir = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "nightscope.db"
    initialize_database(database_path, base_dir / "data" / "schema.sql")
    engine = SkyfieldAstronomyEngine(base_dir / "data", CatalogueRepository(database_path))
    location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
    fixed_now = datetime(2026, 7, 9, 22, 0, tzinfo=ZoneInfo("Europe/Rome"))
    engine._now = lambda _location: fixed_now

    try:
        target = next(item for item in engine.solar_system_objects(location) if item.id == "jupiter")
        summary = engine.moon_geometry(location, target)
    finally:
        engine.close()

    assert isinstance(summary, MoonGeometrySummary)
    assert summary.object_id == "jupiter"
    assert summary.sample_policy == "bounded_start_mid_best_end"
    assert 1 <= summary.sample_count <= 4
    assert len(summary.sample_times) == summary.sample_count
    assert summary.sampled_at in summary.sample_times
    assert summary.moon_altitude_deg is not None
    assert -90.0 <= summary.moon_altitude_deg <= 90.0
    assert summary.moon_target_separation_deg is not None
    assert 0.0 <= summary.moon_target_separation_deg <= 180.0
    assert isinstance(summary.moon_above_horizon, bool)
    assert isinstance(summary.moon_visible_during_target_window, bool)
    assert summary.moon_set_before_target_window in (True, False, None)
    json.dumps(asdict(summary), allow_nan=False)


def test_skyfield_moon_geometry_batch_preserves_planet_and_messier_results(tmp_path) -> None:
    base_dir = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "nightscope.db"
    initialize_database(database_path, base_dir / "data" / "schema.sql")
    engine = SkyfieldAstronomyEngine(base_dir / "data", CatalogueRepository(database_path))
    location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
    fixed_now = datetime(2026, 7, 9, 22, 0, tzinfo=ZoneInfo("Europe/Rome"))
    engine._now = lambda _location: fixed_now

    try:
        jupiter = next(item for item in engine.solar_system_objects(location) if item.id == "jupiter")
        m13 = next(item for item in engine.recommended_deep_sky(location) if item.id == "messier-M13")
        summaries = engine.moon_geometry_batch(location, [jupiter, m13])
        jupiter_single = engine.moon_geometry(location, jupiter)
        m13_single = engine.moon_geometry(location, m13)
    finally:
        engine.close()

    assert summaries == {
        "jupiter": jupiter_single,
        "messier-M13": m13_single,
    }
    assert summaries["jupiter"].moon_target_separation_deg == 73.5
    assert summaries["jupiter"].moon_visible_during_target_window is False
    # DSO geometry now uses the dark useful interval, excluding twilight samples.
    assert summaries["messier-M13"].moon_target_separation_deg == 116.92
    assert summaries["messier-M13"].moon_visible_during_target_window is True
