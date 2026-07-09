from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_universe_target_profile_policy import (
    REPORT_PATH,
    generate_universe_target_profile_policy_data,
    render_markdown_report,
)


def test_universe_target_profile_policy_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_universe_target_profile_policy_data()
    second = generate_universe_target_profile_policy_data()

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
    assert first["metadata"]["runtime_behaviour_changed_by_this_policy"] is False
    assert first["metadata"]["scoring_changed"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_universe_target_profile_policy_defers_runtime_profile_without_blocking_current_nsom() -> None:
    data = generate_universe_target_profile_policy_data()
    options = {option["option_id"]: option for option in data["policy_options"]}
    decisions = {decision["decision_id"]: decision for decision in data["policy_decisions"]}

    assert data["readiness"]["verdict"] == "universe_target_profile_deferred_non_blocking"
    assert data["readiness"]["introduce_runtime_profile_now"] is False
    assert data["readiness"]["keep_current_intrinsic_adapter"] is True
    assert data["readiness"]["score_change_recommended_now"] is False
    assert data["readiness"]["visible_ui_change_recommended_now"] is False
    assert data["readiness"]["blocks_current_default_on_surfaces"] is False
    assert data["blockers"] == []

    assert options["introduce_runtime_universe_target_profile_now"]["status"] == "rejected_now"
    assert options["keep_intrinsic_target_quality_adapter"]["status"] == "accepted"
    assert options["define_future_profile_contract_only"]["status"] == (
        "accepted_developer_policy"
    )
    assert options["start_visible_score_explanation_now"]["status"] == "deferred"
    assert decisions["runtime_universe_target_profile"]["status"] == "deferred_non_blocking"
    assert decisions["intrinsic_adapter_policy"]["status"] == "keep_current_adapter"
    assert decisions["score_provenance_policy"]["status"] == "future_entry_criterion"
    assert decisions["visible_score_policy"]["status"] == "separate_presentation_step"
    assert all(decision["blocks_current_runtime"] is False for decision in data["policy_decisions"])


def test_universe_target_profile_policy_defines_future_contract_without_runtime_dto() -> None:
    data = generate_universe_target_profile_policy_data()
    contract = {item["field"]: item for item in data["future_profile_contract"]}
    criteria = {item["criterion_id"]: item for item in data["future_entry_criteria"]}

    assert set(contract) == {
        "object_id",
        "target_class",
        "intrinsic_score_seed",
        "score_provenance",
        "geometry_summary",
        "magnitude_and_size",
        "display_score_projection",
    }
    assert contract["score_provenance"]["source_today"] == "not explicit"
    assert "explicit provenance label" in contract["intrinsic_score_seed"][
        "required_before_implementation"
    ]
    assert contract["display_score_projection"]["owner"] == "Presentation"
    assert data["checks"]["future_contract_documented"] is True

    assert set(criteria) == {
        "intrinsic_calibration_requested",
        "multiple_catalogue_sources_active",
        "visible_score_explanation_required",
        "remove_celestial_object_score_payload",
        "surface_brightness_model_added",
    }
    assert all(item["status"] == "not_active" for item in criteria.values())
    assert data["checks"]["entry_criteria_all_non_active"] is True


def test_universe_target_profile_policy_links_to_clean_1_13_9_score_boundary() -> None:
    data = generate_universe_target_profile_policy_data()
    sources = {item["surface"]: item for item in data["source_marker_checks"]}

    assert data["checks"]["score_boundary_audit_clean"] is True
    assert data["checks"]["current_intrinsic_adapter_kept"] is True
    assert data["checks"]["runtime_profile_not_recommended_now"] is True
    assert data["checks"]["source_markers_all_found"] is True
    assert data["checks"]["intrinsic_dto_boundary_present"] is True
    assert data["checks"]["read_model_boundary_present"] is True
    assert sources["IntrinsicTargetQuality core DTO"]["all_markers_found"] is True
    assert sources["Runtime intrinsic adapter"]["all_markers_found"] is True
    assert sources["ObservationConditions raw target input"]["all_markers_found"] is True
    assert all(item["missing_markers"] == [] for item in sources.values())


def test_universe_target_profile_policy_has_no_runtime_or_qml_wiring() -> None:
    data = generate_universe_target_profile_policy_data()

    assert data["checks"]["no_scoring_change"] is True
    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_policy"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_universe_target_profile_policy_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM UniverseTargetProfile Policy" in text
    assert "universe_target_profile_deferred_non_blocking" in text
    assert "introduce_runtime_universe_target_profile_now" in text
    assert "score_provenance" in text
    assert "Visible score/explanation policy" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
