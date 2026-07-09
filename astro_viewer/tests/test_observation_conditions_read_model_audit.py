from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.observation_conditions_read_model_audit import (
    REPORT_PATH,
    generate_observation_conditions_read_model_audit_data,
    render_markdown_report,
)


def test_observation_conditions_read_model_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_observation_conditions_read_model_audit_data()
    second = generate_observation_conditions_read_model_audit_data()

    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
        second,
        sort_keys=True,
        allow_nan=False,
    )
    assert first["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "runtime_behaviour_changed_by_this_audit": False,
        "planner_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "sky_compass_changed": False,
        "report_path": "docs/OBSERVATION_CONDITIONS_READ_MODEL_AUDIT.md",
    }


def test_observation_conditions_audit_identifies_read_model_boundary_requirement() -> None:
    data = generate_observation_conditions_read_model_audit_data()

    assert data["readiness"]["verdict"] == "read_model_boundary_required_before_cleanup"
    assert data["readiness"]["runtime_migration_recommended_now"] is False
    assert data["readiness"]["safe_to_remove_service"] is False
    assert data["readiness"]["safe_to_keep_current_runtime_temporarily"] is True
    assert data["checks"]["service_is_active_runtime_code"] is True
    assert data["checks"]["conditioned_caches_present"] is True
    assert data["checks"]["pollution_context_writes_deep_sky_cache"] is True
    assert "observation-conditions-read-model-boundary-missing" in data["blockers"]


def test_observation_conditions_audit_exposes_conditioned_score_nsom_input_risk() -> None:
    data = generate_observation_conditions_read_model_audit_data()
    fixture = data["phenomenon_fixture"]

    assert fixture["raw_score"] > fixture["pollution_conditioned_score"]
    assert fixture["pollution_conditioned_observable_value"] < fixture["raw_observable_value"]
    assert fixture["combined_conditioned_observable_value"] < fixture["raw_observable_value"]
    assert fixture["nsom_conditioned_score_input_risk"] is True
    assert data["checks"]["nsom_conditioned_score_input_risk_visible"] is True
    assert "observation-conditions-conditioned-score-as-nsom-intrinsic" in data["blockers"]


def test_observation_conditions_audit_keeps_service_characterization_precise() -> None:
    data = generate_observation_conditions_read_model_audit_data()
    fixture = data["phenomenon_fixture"]

    assert fixture["original_target_mutated"] is False
    assert fixture["original_target_preserved"] is True
    assert fixture["pollution_reapply_guarded"] is True
    assert data["checks"]["service_uses_replacement_not_mutation"] is True
    assert data["checks"]["service_preserves_original_target_reference"] is True
    assert data["checks"]["double_count_guard_present_for_pollution"] is True
    assert data["checks"]["aod_pm_score_neutral_today"] is True


def test_observation_conditions_audit_maps_active_consumers_without_claiming_planner_use() -> None:
    data = generate_observation_conditions_read_model_audit_data()
    consumers = {item["consumer"]: item for item in data["runtime_consumers"]}

    assert consumers["Home recommendedDeepSky"]["uses_conditioned_object"] is True
    assert consumers["Home recommendedDeepSky"]["uses_nsom_observable"] is True
    assert consumers["Best Object"]["uses_nsom_observable"] is True
    assert consumers["Sky Compass"]["uses_conditioned_object"] is True
    assert consumers["Detail/Object selectedObject"]["uses_nsom_observable"] is False
    assert consumers["Planner"]["uses_conditioned_object"] is False
    assert consumers["Planner"]["uses_nsom_observable"] is False


def test_observation_conditions_read_model_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_observation_conditions_read_model_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_audit"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_observation_conditions_read_model_audit_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# ObservationConditions NSOM Read-Model Audit" in text
    assert "read_model_boundary_required_before_cleanup" in text
    assert "observation-conditions-conditioned-score-as-nsom-intrinsic" in text
    assert "ObservationConditions is not dead legacy" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
