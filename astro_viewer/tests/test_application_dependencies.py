"""Protect composition-root defaults, overrides, and dependency completeness."""

from __future__ import annotations

from contextlib import closing
import sqlite3
from pathlib import Path
from unittest.mock import patch

from astro_viewer.app.application.dependencies import (
    build_app_controller_dependencies,
)
from astro_viewer.app.astronomy.engine import UnavailableAstronomyEngine
from astro_viewer.app.astronomy.skyfield_engine import EphemerisUnavailableError


def test_dependency_factory_owns_ephemeris_fallback(tmp_path: Path) -> None:
    base_dir = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "nightscope.db"
    with closing(sqlite3.connect(database_path)) as connection:
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

    assert isinstance(dependencies.astronomy_engine, UnavailableAstronomyEngine)
    assert dependencies.startup_service_status

    workflow = dependencies.catalogue_recommendation_workflow
    assert workflow._equipment_service is dependencies.equipment_service
    assert (
        workflow._equipment_setup_read_model_builder
        is dependencies.equipment_setup_read_model_builder
    )
    assert workflow._conditions_service is dependencies.conditions_service
    assert (
        workflow._conditions_read_model_builder
        is dependencies.conditions_read_model_builder
    )
    assert (
        workflow._home_ranking_service
        is dependencies.home_recommended_deep_sky_nsom_ranking_service
    )
    assert (
        workflow._category_score_service
        is dependencies.nsom_category_score_service
    )
    assert (
        workflow._best_object_service
        is dependencies.best_object_nsom_selection_service
    )
    assert workflow._night_planner_service is dependencies.night_planner_service
    assert workflow._sky_compass_service is dependencies.sky_compass_service
    assert dependencies.observing_presentation_service is not None
    assert (
        dependencies.weather_presentation_service._night_planner_service
        is dependencies.night_planner_service
    )
    assert (
        dependencies.catalogue_query_service._catalogue_repository
        is dependencies.catalogue_repository
    )
    assert dependencies.catalogue_detail_service is not None
    assert (
        type(dependencies.location_service.windows_provider).__module__
        == "astro_viewer.app.services.location_providers"
    )
    assert (
        dependencies.location_service.ip_provider._cache_path
        == tmp_path / "location_cache.json"
    )
    assert (
        dependencies.location_command_workflow._repository
        is dependencies.location_repository
    )
    assert (
        dependencies.location_command_workflow._service
        is dependencies.location_service
    )
    assert (
        dependencies.equipment_catalog_service._repository
        is dependencies.equipment_catalog_repository
    )
    assert (
        dependencies.equipment_catalog_service._equipment_service
        is dependencies.equipment_service
    )
    assert (
        dependencies.profile_equipment_service._repository
        is dependencies.equipment_profile_repository
    )
    assert (
        dependencies.equipment_profile_repository._database_path
        == dependencies.equipment_catalog_repository._database_path
    )
    assert (
        dependencies.profile_equipment_service._equipment_service
        is dependencies.equipment_service
    )
    assert (
        dependencies.profile_equipment_service._catalogue_service
        is dependencies.equipment_catalog_service
    )
    assert (
        dependencies.equipment_presentation_service._equipment_service
        is dependencies.equipment_service
    )
