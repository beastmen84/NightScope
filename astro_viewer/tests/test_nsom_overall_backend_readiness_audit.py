from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_overall_backend_readiness_audit import (
    REPORT_PATH,
    generate_overall_backend_readiness_audit_data,
    render_markdown_report,
)


def test_overall_backend_readiness_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_overall_backend_readiness_audit_data()
    second = generate_overall_backend_readiness_audit_data()

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
    assert first["metadata"]["runtime_behaviour_changed_by_this_audit"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_overall_backend_readiness_confirms_closed_backend_surfaces() -> None:
    data = generate_overall_backend_readiness_audit_data()
    surfaces = {surface["surface"]: surface for surface in data["closed_backend_surfaces"]}

    assert data["readiness"]["verdict"] == "overall_backend_nsom_ready_for_next_phase"
    assert data["readiness"]["backend_recommendation_surfaces_closed"] is True
    assert data["readiness"]["equipment_closed_setup_local"] is True
    assert data["readiness"]["dead_legacy_removed"] is True
    assert data["blockers"] == []
    assert data["checks"]["all_default_on_backend_surfaces_closed"] is True
    assert data["checks"]["all_default_flags_enabled"] is True
    assert data["checks"]["all_rollback_paths_present"] is True
    assert data["checks"]["equipment_closed_setup_local"] is True
    assert data["checks"]["legacy_surface_cleanup_complete"] is True

    assert surfaces["Planner"]["status"] == "default_on_closed"
    assert surfaces["Home recommendedDeepSky"]["status"] == "default_on_closed"
    assert surfaces["Best Object"]["status"] == "default_on_closed"
    assert surfaces["Advanced Observing backend"]["status"] == "default_on_closed_backend_only"
    assert surfaces["Sky Compass"]["status"] == "default_on_closed"
    assert surfaces["Detail/Object internal payload"]["status"] == "default_on_closed_backend_only"
    assert surfaces["Equipment recommendations"]["status"] == (
        "equipment_nsom_migration_closed_setup_local"
    )
    assert surfaces["ObservationConditions consumers"]["status"] == (
        "observation_conditions_consumer_reroute_closed"
    )
    assert surfaces["Sky Map"]["status"] == "removed_dead_legacy"
    assert surfaces["Notifications"]["status"] == "removed_dead_legacy"
    assert all(surface["confidence_score_neutral"] is True for surface in surfaces.values())


def test_overall_backend_readiness_classifies_remaining_items_as_non_blocking() -> None:
    data = generate_overall_backend_readiness_audit_data()
    remaining = {item["item"]: item for item in data["remaining_non_blocking_items"]}

    assert set(remaining) == {
        "Internal legacy rollback flags",
        "Legacy/base payload compatibility fields",
        "ObservationConditions prepared-object cache",
        "Catalogue / raw object score",
    }
    assert remaining["Internal legacy rollback flags"]["classification"] == (
        "cleanup_policy_pending"
    )
    assert remaining["Legacy/base payload compatibility fields"]["classification"] == (
        "presentation_compatibility"
    )
    assert remaining["ObservationConditions prepared-object cache"]["classification"] == (
        "observation_conditions_consumer_reroute_closed"
    )
    assert remaining["Catalogue / raw object score"]["classification"] == (
        "upstream_legacy_input"
    )
    assert all(item["blocks_backend_readiness"] is False for item in remaining.values())
    assert data["checks"]["remaining_items_non_blocking"] is True


def test_overall_backend_readiness_recommends_rollback_cleanup_before_ui_explanations() -> None:
    data = generate_overall_backend_readiness_audit_data()
    decisions = {decision["decision_id"]: decision for decision in data["next_phase_decisions"]}
    sequence = [item["step"] for item in data["recommended_sequence"]]

    assert data["readiness"]["safe_to_start_rollback_cleanup_policy"] is True
    assert data["readiness"]["safe_to_start_visible_ui_explanation_design"] is True
    assert data["readiness"]["visible_ui_explanation_recommended_now"] is False
    assert data["readiness"]["recommended_next_step"] == (
        "Review 1.13.6, then run a rollback cleanup policy audit before "
        "any visible UI/explanation work."
    )
    assert decisions["rollback_cleanup_policy"]["status"] == "recommended_next"
    assert decisions["rollback_cleanup_policy"]["priority"] == 1
    assert decisions["visible_ui_explanation_policy"]["status"] == (
        "deferred_until_backend_cleanup_policy"
    )
    assert decisions["payload_score_semantics"]["status"] == "presentation_followup"
    assert decisions["catalogue_universe_score_boundary"]["status"] == "future_backend_audit"
    assert all(
        decision["runtime_change_allowed_by_this_audit"] is False
        for decision in data["next_phase_decisions"]
    )
    assert sequence == [
        "Review 1.13.6",
        "1.13.7 Rollback cleanup policy audit",
        "Visible UI/explanation planning",
    ]


def test_overall_backend_readiness_has_no_runtime_or_qml_wiring() -> None:
    data = generate_overall_backend_readiness_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_audit"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_overall_backend_readiness_audit_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Overall Backend Readiness Audit" in text
    assert "overall_backend_nsom_ready_for_next_phase" in text
    assert "1.13.7 Rollback cleanup policy audit" in text
    assert "Visible UI/explanation planning" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
