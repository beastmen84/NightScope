from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.observation_conditions_consumer_reroute_audit import (
    REPORT_PATH,
    generate_observation_conditions_consumer_reroute_audit_data,
    render_markdown_report,
)


def test_consumer_reroute_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_observation_conditions_consumer_reroute_audit_data()
    second = generate_observation_conditions_consumer_reroute_audit_data()

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
        "home_changed": True,
        "best_object_changed": True,
        "sky_compass_changed": False,
        "report_path": "docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md",
    }


def test_consumer_reroute_audit_tracks_home_runtime_reroute_and_pending_consumers() -> None:
    data = generate_observation_conditions_consumer_reroute_audit_data()
    policies = {item["consumer"]: item for item in data["consumer_policies"]}

    assert data["readiness"]["verdict"] == "sky_compass_read_model_policy_defined_runtime_pending"
    assert data["readiness"]["runtime_reroute_recommended_now"] is True
    assert data["readiness"]["safe_to_change_runtime_in_this_step"] is False
    assert data["checks"]["runtime_behaviour_unchanged_by_audit"] is True

    assert policies["Home recommendedDeepSky"]["candidate_raw_input"] == "read_model.nsom_target_input"
    assert policies["Home recommendedDeepSky"]["current_runtime_input"] == "read_model.nsom_target_input"
    assert policies["Home recommendedDeepSky"]["payload_target"] == "read_model.qml_display_target"
    assert policies["Home recommendedDeepSky"]["status"] == "runtime_rerouted_to_raw_read_model_target"
    assert policies["Best Object"]["current_runtime_input"] == "read_model.nsom_target_input for scoring"
    assert policies["Best Object"]["payload_target"] == "read_model.qml_display_target when selected"
    assert policies["Best Object"]["status"] == "runtime_rerouted_to_raw_read_model_target"
    assert policies["Sky Compass"]["status"] == "read_model_reroute_policy_defined_runtime_pending"
    assert policies["Sky Compass"]["payload_target"] == (
        "read_model.qml_display_target or current live display target"
    )
    assert data["checks"]["home_runtime_reroute_uses_raw_read_model_targets"] is True
    assert data["checks"]["home_runtime_payload_uses_display_target"] is True
    assert data["checks"]["best_object_runtime_reroute_uses_raw_read_model_targets"] is True
    assert data["checks"]["best_object_runtime_returns_display_target"] is True
    assert data["checks"]["sky_compass_policy_defined_runtime_pending"] is True
    assert data["checks"]["sky_compass_policy_report_present"] is True


def test_consumer_reroute_fixture_shows_raw_vs_display_observable_delta() -> None:
    data = generate_observation_conditions_consumer_reroute_audit_data()
    deep_sky = [
        item
        for item in data["fixture"]["evaluations"]
        if item["target_group"] == "deep_sky"
    ]
    solar = [
        item
        for item in data["fixture"]["evaluations"]
        if item["target_group"] == "solar_system"
    ]

    assert deep_sky
    assert all(item["raw_score"] > item["display_score"] for item in deep_sky)
    assert all(item["raw_observable_value"] > item["display_observable_value"] for item in deep_sky)
    assert all(item["raw_minus_display_observable"] > 0.0 for item in deep_sky)
    assert all(item["raw_minus_display_observable"] == 0.0 for item in solar)
    assert data["checks"]["raw_observable_differs_from_display_for_conditioned_targets"] is True
    assert data["checks"]["solar_system_targets_are_not_conditioned"] is True


def test_consumer_reroute_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_observation_conditions_consumer_reroute_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_consumer_reroute_audit_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# ObservationConditions Consumer Reroute Audit" in text
    assert "sky_compass_read_model_policy_defined_runtime_pending" in text
    assert "Home recommendedDeepSky" in text
    assert "Best Object" in text
    assert "Sky Compass" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
