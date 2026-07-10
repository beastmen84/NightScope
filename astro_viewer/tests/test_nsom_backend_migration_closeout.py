from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_backend_migration_closeout import (
    REPORT_PATH,
    generate_backend_migration_closeout_data,
    render_markdown_report,
)


def test_backend_migration_closeout_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_backend_migration_closeout_data()
    second = generate_backend_migration_closeout_data()

    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
        second,
        sort_keys=True,
        allow_nan=False,
    )
    assert first["metadata"]["developer_only"] is True
    assert first["metadata"]["runtime_writes"] is False
    assert first["metadata"]["automatic_logging"] is False
    assert first["metadata"]["network"] is False
    assert first["metadata"]["qml_exposure"] is False
    assert first["metadata"]["runtime_behaviour_changed_by_closeout"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_backend_migration_closeout_closes_current_default_on_surfaces() -> None:
    data = generate_backend_migration_closeout_data()
    surfaces = {surface["surface"]: surface for surface in data["closed_surfaces"]}

    assert data["closeout"]["verdict"] == "backend_nsom_recommendation_surfaces_closed"
    assert data["closeout"]["migration_status"] == "closed_for_backend_recommendation_surfaces"
    assert data["closeout"]["backend_default_on_blockers"] == []
    assert data["checks"]["backend_status_has_no_blockers"] is True
    assert data["checks"]["all_current_default_on_surfaces_closed"] is True
    assert set(surfaces) == {
        "Planner",
        "Home recommendedDeepSky",
        "Best Object",
        "Advanced Observing backend",
        "Sky Compass",
        "Detail/Object internal payload",
    }
    assert all(surface["status"].startswith("default_on_closed") for surface in surfaces.values())


def test_backend_migration_closeout_records_aod_openaq_default_on_and_rollback() -> None:
    data = generate_backend_migration_closeout_data()
    switch = data["aod_openaq_switch"]

    assert switch["default_flag"] == (
        "ObservationConditionFeatureFlags.experimental_aerosol_scoring = True"
    )
    assert switch["rollback"] == "ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)"
    assert switch["formula_changed"] is False
    assert switch["weights_changed"] is False
    assert switch["provider_calls_changed"] is False
    assert switch["confidence_metadata_does_not_scale_score"] is True
    assert data["checks"]["aod_openaq_default_on"] is True
    assert data["checks"]["aod_openaq_rollback_documented"] is True
    assert data["checks"]["aod_openaq_confidence_score_neutral"] is True


def test_backend_migration_closeout_keeps_remaining_items_non_blocking() -> None:
    data = generate_backend_migration_closeout_data()
    remaining = {item["area"]: item for item in data["remaining_non_blocking_items"]}
    future = {item["area"]: item for item in data["future_work_policy"]}

    assert set(remaining) == {
        "Equipment recommendations",
        "ObservationConditions prepared-object cache",
        "Catalogue / raw object score",
    }
    assert all(item["blocks_current_default_on_surfaces"] is False for item in remaining.values())
    assert data["checks"]["remaining_items_are_non_blocking"] is True
    assert future["AOD/OpenAQ real observing feedback"]["status"] == "monitor_before_tuning"
    assert future["Catalogue / Universe raw score semantics"]["status"] == "future_universe_policy"
    assert future["Visible UI explanations"]["status"] == "future_design_step"
    assert all(item["blocks_backend_closeout"] is False for item in future.values())


def test_backend_migration_closeout_has_no_runtime_or_qml_wiring() -> None:
    data = generate_backend_migration_closeout_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_backend_migration_closeout_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Backend Migration Closeout" in text
    assert "backend_nsom_recommendation_surfaces_closed" in text
    assert "ObservationConditionFeatureFlags.experimental_aerosol_scoring = True" in text
    assert "Catalogue / Universe raw score semantics" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
