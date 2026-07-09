from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_legacy_backend_surface_audit import (
    REPORT_PATH,
    generate_legacy_backend_surface_audit_data,
    render_markdown_report,
)


def test_legacy_backend_surface_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_legacy_backend_surface_audit_data()
    second = generate_legacy_backend_surface_audit_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"]["developer_only"] is True
    assert first["metadata"]["runtime_writes"] is False
    assert first["metadata"]["automatic_logging"] is False
    assert first["metadata"]["network"] is False
    assert first["metadata"]["qml_exposure"] is False
    assert first["metadata"]["runtime_behaviour_changed_by_this_audit"] is False


def test_sky_map_removed_dead_legacy_path_stays_out_of_runtime() -> None:
    data = generate_legacy_backend_surface_audit_data()
    dead = {item["surface"]: item for item in data["dead_legacy_surfaces"]}
    sky_map = dead["Sky Map"]

    assert sky_map["surface"] == "Sky Map"
    assert sky_map["classification"] == "removed_dead_legacy"
    assert sky_map["qml_consumed"] is False
    assert sky_map["qml_consumer_matches"] == []
    assert sky_map["controller_computation_present"] is False
    assert sky_map["controller_matches"] == []
    assert sky_map["service_file_present"] is False
    assert data["checks"]["sky_map_removed_not_nsom_target"] is True
    assert data["checks"]["sky_map_controller_computation_absent"] is True
    assert data["checks"]["sky_map_service_file_absent"] is True
    assert data["readiness"]["sky_map_migration_recommendation"] == (
        "removed_dead_legacy_surface"
    )
    assert "Keep removed" in sky_map["recommended_handling"]


def test_notifications_are_dead_legacy_not_active_nsom_migration_target() -> None:
    data = generate_legacy_backend_surface_audit_data()
    dead = {item["surface"]: item for item in data["dead_legacy_surfaces"]}
    notifications = dead["Notifications"]

    assert notifications["classification"] == "removed_dead_legacy"
    assert notifications["qml_consumed"] is False
    assert notifications["controller_runtime_present"] is False
    assert notifications["service_file_present"] is False
    assert notifications["not_a_nsom_migration_target"] is True
    assert data["checks"]["notifications_qml_consumers_absent"] is True
    assert data["checks"]["notifications_not_nsom_target"] is True
    assert data["checks"]["notifications_removed_dead_legacy"] is True
    assert data["readiness"]["notifications_migration_recommendation"] == (
        "removed_dead_legacy"
    )


def test_temporary_rollbacks_are_internal_not_public_compatibility_contracts() -> None:
    data = generate_legacy_backend_surface_audit_data()
    rollbacks = {item["surface"]: item for item in data["temporary_rollback_surfaces"]}

    assert set(rollbacks) == {
        "Planner",
        "Home recommendedDeepSky",
        "Best Object",
        "Advanced Observing backend",
        "Sky Compass",
        "Detail/Object internal payload",
    }
    assert all(item["public_compatibility_contract"] is False for item in rollbacks.values())
    assert all(item["rollback_parameter_present"] is True for item in rollbacks.values())
    assert data["checks"]["temporary_rollbacks_are_internal"] is True


def test_payload_compatibility_fields_are_not_treated_as_ranking_authority() -> None:
    data = generate_legacy_backend_surface_audit_data()
    compatibility = {item["surface"]: item for item in data["payload_compatibility_surfaces"]}

    assert compatibility["Home recommendedDeepSky"]["compatibility_field"] == "score"
    assert compatibility["Best Object"]["compatibility_field"] == "score"
    assert compatibility["Sky Compass"]["compatibility_field"] == "target.score"
    assert compatibility["Detail/Object"]["compatibility_field"] == "selectedObject.score"
    assert all(
        item["ranking_authority"] == "NSOM or separate active service"
        for item in compatibility.values()
    )
    assert data["checks"]["payload_compatibility_not_rank_source"] is True


def test_active_legacy_or_hybrid_surfaces_remain_separate_from_dead_code_removal() -> None:
    data = generate_legacy_backend_surface_audit_data()
    active = {item["surface"]: item for item in data["active_legacy_or_hybrid_surfaces"]}

    assert set(active) == {
        "Equipment recommendations",
        "ObservationConditions prepared-object cache",
        "Catalogue / raw object score",
    }
    assert active["Equipment recommendations"]["classification"] == "active_legacy_or_hybrid"
    assert "observer_capability_adapter.py" in active["Equipment recommendations"]["why_active"]
    assert "equipment_setup_score_ownership_audited" in active["Equipment recommendations"]["why_active"]
    assert "equipment_setup_score_component_boundary_introduced" in active[
        "Equipment recommendations"
    ]["why_active"]
    assert "equipment_default_off_path_policy_set_setup_local" in active[
        "Equipment recommendations"
    ]["why_active"]
    assert "equipment_nsom_migration_closed_setup_local" in active[
        "Equipment recommendations"
    ]["why_active"]
    assert "NSOM_OVERALL_BACKEND_READINESS_AUDIT" in active[
        "Equipment recommendations"
    ]["why_active"]
    assert "setup-local service" in active[
        "Equipment recommendations"
    ]["recommended_handling"]
    assert "observation_conditions_consumer_reroute_closed" in active[
        "ObservationConditions prepared-object cache"
    ]["why_active"]
    assert "no ObservationConditions consumer reroute work remains open" in active[
        "ObservationConditions prepared-object cache"
    ]["recommended_handling"]
    assert data["readiness"]["observation_conditions_recommendation"] == (
        "observation_conditions_consumer_reroute_closed"
    )


def test_legacy_backend_surface_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_legacy_backend_surface_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_audit"] is True
    assert data["static_checks"]["runtime_report_import_matches"] == []
    assert data["static_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_legacy_backend_surface_audit_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Legacy Backend Surface Audit" in text
    assert "removed_dead_legacy_surface" in text
    assert "Review 1.11.1" in text
    assert "Review 1.12.2" in text
    assert "1.12.1 Equipment NSOM policy readiness" in text
    assert "1.12.2 ObserverCapability adapter extraction" in text
    assert "1.12.3 Notifications dead legacy audit" in text
    assert "1.12.5 ObservationConditions read-model audit" in text
    assert "observation_conditions_consumer_reroute_closed" in text
    assert "removed_dead_legacy" in text
    assert "dead legacy pending removal" not in text
    assert "1.12.6 ObservationConditions read-model boundary" in text
    assert "1.12.7 ObservationConditions consumer reroute audit" in text
    assert "1.12.8 Home recommendedDeepSky raw-target reroute" in text
    assert "1.12.9 Best Object raw-target reroute" in text
    assert "1.12.10 Sky Compass read-model reroute policy" in text
    assert "1.12.11 Sky Compass read-model reroute" in text
    assert "1.13.0 Equipment presenter contract audit" in text
    assert "Review 1.13.0" in text
    assert "1.13.1 Equipment setup read-model boundary" in text
    assert "Review 1.13.1" in text
    assert "1.13.2 Equipment setup score ownership audit" in text
    assert "Review 1.13.2" in text
    assert "1.13.3 Equipment setup-score component boundary" in text
    assert "Review 1.13.3" in text
    assert "1.13.4 Equipment default-off path policy audit" in text
    assert "Review 1.13.4" in text
    assert "1.13.5 Equipment NSOM migration closeout" in text
    assert "Review 1.13.5" in text
    assert "Next backend NSOM area selection audit" in text
    assert "1.13.6 Overall backend readiness audit" in text
    assert "Review 1.13.6" in text
    assert "1.13.7 Rollback cleanup policy audit" in text
    assert "equipment_nsom_migration_closed_setup_local" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
