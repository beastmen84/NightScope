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


def test_sky_map_is_classified_as_dead_legacy_not_nsom_migration_target() -> None:
    data = generate_legacy_backend_surface_audit_data()
    sky_map = data["dead_legacy_surfaces"][0]

    assert sky_map["surface"] == "Sky Map"
    assert sky_map["classification"] == "dead_legacy"
    assert sky_map["qml_consumed"] is False
    assert sky_map["qml_consumer_matches"] == []
    assert sky_map["controller_computation_present"] is True
    assert data["checks"]["sky_map_is_dead_legacy_not_nsom_target"] is True
    assert data["readiness"]["sky_map_migration_recommendation"] == (
        "do_not_migrate_dead_legacy_surface"
    )
    assert "Remove" in sky_map["recommended_handling"]


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
        "Notifications",
        "Catalogue / raw object score",
    }
    assert active["Equipment recommendations"]["classification"] == "active_legacy_or_hybrid"
    assert "ObserverCapability/Q_target" in active["Equipment recommendations"]["recommended_handling"]


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
    assert "do_not_migrate_dead_legacy_surface" in text
    assert "1.11.1 Remove dead Sky Map legacy path" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
