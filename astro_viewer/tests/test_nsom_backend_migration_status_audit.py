from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_backend_migration_status_audit import (
    REPORT_PATH,
    generate_backend_migration_status_audit_data,
    render_markdown_report,
)


def test_backend_migration_status_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_backend_migration_status_audit_data()
    second = generate_backend_migration_status_audit_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "runtime_behaviour_changed_by_this_audit": False,
        "planner_changed": False,
        "home_recommended_deep_sky_changed": False,
        "best_object_changed": False,
        "advanced_observing_changed": False,
        "sky_compass_changed": False,
        "report_path": "docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md",
        "source_reports": [
            "docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md",
            "docs/HOME_NSOM_RECOMMENDED_DEEP_SKY_READINESS_AUDIT.md",
            "docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
            "docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
            "docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
        ],
    }


def test_audit_confirms_default_on_surfaces_and_rollbacks() -> None:
    data = generate_backend_migration_status_audit_data()
    surfaces = {surface["surface"]: surface for surface in data["default_on_surfaces"]}

    assert data["readiness"]["verdict"] == "backend_nsom_default_on_surfaces_closed"
    assert data["readiness"]["all_current_default_on_surfaces_closed"] is True
    assert data["readiness"]["runtime_behaviour_changed_by_this_audit"] is False
    assert data["blockers"] == []
    assert data["checks"]["all_default_flags_enabled"] is True
    assert data["checks"]["all_rollback_paths_present"] is True

    assert surfaces["Planner"]["default_flag"] == "NSOM_PLANNER_SCORING_ENABLED = True"
    assert surfaces["Planner"]["rollback"] == "NightPlannerService(use_nsom_planner_scoring=False)"
    assert surfaces["Home recommendedDeepSky"]["rollback"] == (
        "AppController(use_nsom_home_recommended_deep_sky=False)"
    )
    assert surfaces["Best Object"]["rollback"] == "AppController(use_nsom_best_object=False)"
    assert surfaces["Advanced Observing backend"]["rollback"] == (
        "AppController(use_nsom_advanced_observing=False)"
    )
    assert surfaces["Sky Compass"]["rollback"] == "AppController(use_nsom_sky_compass=False)"
    assert all(surface["confidence_score_neutral"] is True for surface in surfaces.values())


def test_audit_identifies_remaining_non_blocking_legacy_or_hybrid_surfaces() -> None:
    data = generate_backend_migration_status_audit_data()
    remaining = {item["area"]: item for item in data["remaining_non_blocking_items"]}

    assert data["checks"]["remaining_surfaces_are_non_blocking"] is True
    assert set(remaining) == {
        "Detail / selected object",
        "Sky Map",
        "Equipment recommendations",
        "ObservationConditions prepared-object cache",
        "Notifications",
        "Catalogue / raw object score",
    }
    assert remaining["Detail / selected object"]["status"] == "default_off_internal_nsom_path"
    assert "NSOM_DETAIL_OBJECT_ENABLED = False" in remaining["Detail / selected object"]["why_it_remains"]
    assert remaining["Sky Map"]["status"] == "legacy_display_order"
    assert remaining["Equipment recommendations"]["status"] == "legacy_practical_setup_scoring"
    assert all(item["blocks_current_default_on_surfaces"] is False for item in remaining.values())


def test_audit_recommends_detail_object_runtime_review_as_next_backend_step() -> None:
    data = generate_backend_migration_status_audit_data()
    sequence = [item["step"] for item in data["recommended_sequence"]]

    assert data["readiness"]["ready_to_start_next_backend_area"] is True
    assert data["readiness"]["ready_for_visible_ui_redesign"] is False
    assert data["readiness"]["recommended_next_step"] == (
        "Review 1.10.3 Detail/Object NSOM default-off runtime path"
    )
    assert sequence[:2] == [
        "Review 1.9.7",
        "Review 1.10.3",
    ]


def test_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_backend_migration_status_audit_data()

    assert data["safety"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "runtime_report_imports_absent": True,
        "qml_audit_exposure_absent": True,
        "runtime_behaviour_changed_by_this_audit": False,
    }
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_backend_migration_status_audit_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Backend Migration Status Audit" in text
    assert "backend_nsom_default_on_surfaces_closed" in text
    assert "Review 1.10.3 Detail/Object NSOM default-off runtime path" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
