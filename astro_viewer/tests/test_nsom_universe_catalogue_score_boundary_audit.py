from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_universe_catalogue_score_boundary_audit import (
    REPORT_PATH,
    generate_universe_catalogue_score_boundary_audit_data,
    render_markdown_report,
)


def test_universe_catalogue_score_boundary_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_universe_catalogue_score_boundary_audit_data()
    second = generate_universe_catalogue_score_boundary_audit_data()

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


def test_universe_catalogue_score_boundary_classifies_score_as_interim_intrinsic_seed() -> None:
    data = generate_universe_catalogue_score_boundary_audit_data()
    decisions = {item["decision_id"]: item for item in data["boundary_decisions"]}
    semantics = {item["score_concept"]: item for item in data["score_semantics"]}

    assert data["readiness"]["verdict"] == "universe_catalogue_score_boundary_audited"
    assert data["readiness"]["safe_to_keep_score_as_intrinsic_seed"] is True
    assert data["readiness"]["score_change_recommended_now"] is False
    assert data["blockers"] == []

    assert semantics["CelestialObject.score"]["owner"] == (
        "prepared target DTO / Universe seed compatibility"
    )
    assert "Accepted interim intrinsic seed" in semantics["CelestialObject.score"]["nsom_policy"]

    assert decisions["catalogue_score_as_intrinsic_seed"]["status"] == "accepted_interim"
    assert decisions["catalogue_score_as_intrinsic_seed"]["affected_nsom_layer"] == (
        "Universe / IntrinsicTargetQuality"
    )
    assert decisions["catalogue_score_as_intrinsic_seed"]["blocks_default_on_work"] is False
    assert decisions["prepared_score_provenance"]["status"] == (
        "deferred_targeted_backend_policy"
    )
    assert decisions["prepared_score_provenance"]["possible_calibration_issue"] is True


def test_universe_catalogue_inventory_separates_payload_and_equipment_scores_from_universe_score() -> None:
    data = generate_universe_catalogue_score_boundary_audit_data()
    inventory = {item["surface"]: item for item in data["score_boundary_inventory"]}
    remaining = {item["item"]: item for item in data["remaining_policy_items"]}

    assert inventory["NSOM intrinsic adapter"]["classification"] == "universe_adapter"
    assert inventory["NSOM intrinsic adapter"]["decision"] == (
        "keep_stable_until_explicit_universe_profile"
    )
    assert inventory["ObservationConditions read model"]["classification"] == (
        "closed_raw_display_boundary"
    )
    assert inventory["ObservationConditions read model"]["decision"] == (
        "accepted_boundary_prevents_conditioning_from_becoming_intrinsic"
    )
    assert inventory["Home recommendedDeepSky"]["ranking_authority"] == (
        "ObservableTargetValue from raw target plus sky environment."
    )
    assert inventory["Best Object"]["ranking_authority"] == (
        "Home-specific ObservationOpportunity."
    )
    assert inventory["Sky Compass"]["decision"] == "accepted_direction_policy_boundary"
    assert inventory["Planner"]["decision"] == "document_input_output_score_boundary"
    assert inventory["Equipment recommendations"]["decision"] == (
        "keep_outside_universe_score_boundary"
    )

    assert remaining["Visible score semantics"]["status"] == "presentation_followup"
    assert remaining["Catalogue score calibration"]["status"] == "not_recommended_now"
    assert all(item["blocks_current_runtime"] is False for item in remaining.values())
    assert data["checks"]["payload_scores_classified_as_compatibility"] is True
    assert data["checks"]["equipment_score_kept_outside_universe"] is True


def test_universe_catalogue_audit_verifies_current_source_boundaries() -> None:
    data = generate_universe_catalogue_score_boundary_audit_data()
    sources = {item["surface"]: item for item in data["source_marker_checks"]}

    assert data["checks"]["source_markers_all_found"] is True
    assert data["checks"]["intrinsic_adapter_boundary_present"] is True
    assert data["checks"]["read_model_raw_display_boundary_present"] is True
    assert sources["NSOM intrinsic adapter"]["all_markers_found"] is True
    assert sources["ObservationConditions raw/display read model"]["all_markers_found"] is True
    assert sources["Equipment setup score boundary"]["all_markers_found"] is True
    assert all(item["missing_markers"] == [] for item in sources.values())


def test_universe_catalogue_score_boundary_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_universe_catalogue_score_boundary_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_audit"] is True
    assert data["checks"]["confidence_not_in_score_boundary"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []
    assert all(
        decision["blocks_default_on_work"] is False for decision in data["boundary_decisions"]
    )


def test_checked_in_universe_catalogue_score_boundary_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Universe/Catalogue Score Boundary Audit" in text
    assert "universe_catalogue_score_boundary_audited" in text
    assert "catalogue_score_as_intrinsic_seed" in text
    assert "prepared_score_provenance" in text
    assert "Visible score semantics" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
