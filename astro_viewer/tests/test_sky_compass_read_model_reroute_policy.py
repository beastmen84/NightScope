from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.sky_compass_read_model_reroute_policy import (
    REPORT_PATH,
    generate_sky_compass_read_model_reroute_policy_data,
    render_markdown_report,
)


def test_sky_compass_read_model_policy_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_sky_compass_read_model_reroute_policy_data()
    second = generate_sky_compass_read_model_reroute_policy_data()

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
        "runtime_behaviour_changed_by_this_policy": False,
        "sky_compass_runtime_changed": True,
        "planner_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "report_path": "docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md",
    }


def test_policy_splits_raw_observable_from_display_live_geometry_and_payload() -> None:
    data = generate_sky_compass_read_model_reroute_policy_data()
    decisions = {item["boundary"]: item for item in data["policy_decisions"]}
    fixture = data["fixture"]

    assert data["readiness"]["verdict"] == "sky_compass_read_model_reroute_implemented"
    assert data["readiness"]["runtime_changed_by_this_step"] is True
    assert data["readiness"]["accepted_for_observation_conditions_closeout"] is True
    assert fixture["raw_observable_value"] > fixture["display_observable_value"]
    assert fixture["live_display_target"]["direction"] == "Sud-Ovest"
    assert fixture["policy_projection"]["observable_source"] == "read_model.nsom_target_input"
    assert fixture["policy_projection"]["geometry_source"] == "current_display_or_live_target"
    assert fixture["policy_projection"]["payload_source"] == "read_model.qml_display_target_or_live_display_target"

    assert decisions["ObservableTargetValue target physics"]["source"] == "read_model.nsom_target_input"
    assert decisions["Direction grouping"]["source"] == "current display/live target"
    assert decisions["Visibility and horizon geometry"]["source"] == "current display/live target"
    assert decisions["QML payload"]["source"] == "read_model.qml_display_target or current live display target"


def test_policy_keeps_context_boosts_outside_target_physics_and_defines_fallback() -> None:
    data = generate_sky_compass_read_model_reroute_policy_data()
    decisions = {item["boundary"]: item for item in data["policy_decisions"]}

    assert decisions["Night Plan and Best Object boosts"]["runtime_role"] == "Presentation/context boost"
    assert decisions["Missing read-model fallback"]["source"] == "current display/live target"
    assert data["checks"]["context_boosts_remain_presentation"] is True
    assert data["checks"]["missing_read_model_fallback_defined"] is True


def test_policy_has_no_runtime_qml_wiring_and_current_runtime_remains_unchanged() -> None:
    data = generate_sky_compass_read_model_reroute_policy_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_split_adapter_present"] is True
    assert data["checks"]["nsom_service_accepts_observable_target_map"] is True
    assert data["checks"]["runtime_behaviour_changed_by_adapter"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []
    assert data["static_wiring_checks"]["sky_compass_uses_conditioned_display_candidates_now"] is True
    assert data["static_wiring_checks"]["live_refresh_updates_current_candidate_geometry"] is True
    assert data["static_wiring_checks"]["sky_compass_split_adapter_present"] is True
    assert data["static_wiring_checks"]["nsom_service_accepts_observable_target_map"] is True


def test_checked_in_sky_compass_read_model_policy_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Sky Compass Read-Model Reroute Policy" in text
    assert "sky_compass_read_model_reroute_implemented" in text
    assert "current display/live target" in text
    assert "read_model.nsom_target_input" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
