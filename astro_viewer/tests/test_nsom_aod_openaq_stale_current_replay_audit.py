from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionFeatureFlags,
)
from astro_viewer.tools.nsom_aod_openaq_stale_current_replay_audit import (
    REPORT_PATH,
    generate_aod_openaq_stale_current_replay_audit_data,
    render_markdown_report,
)


def test_stale_current_replay_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_aod_openaq_stale_current_replay_audit_data()
    second = generate_aod_openaq_stale_current_replay_audit_data()

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


def test_stale_current_replay_keeps_flag_off_but_accepts_stale_policy_for_review() -> None:
    data = generate_aod_openaq_stale_current_replay_audit_data()
    gates = {gate["gate"]: gate for gate in data["readiness_gates"]}

    assert ObservationConditionFeatureFlags().experimental_aerosol_scoring is False
    assert data["readiness"]["verdict"] == (
        "aod_openaq_stale_policy_ready_for_default_on_review"
    )
    assert data["readiness"]["ready_for_default_on_review"] is True
    assert data["readiness"]["default_on_enabled_by_this_audit"] is False
    assert data["readiness"]["stale_aod_weight_policy"] == "keep_stale_aod_weight_0_5"
    assert data["blockers"] == []
    assert gates["stale_weight_policy"]["status"] == "accepted"
    assert gates["current_replay_score_scale"]["status"] == "accepted"
    assert gates["protected_target_current_replay"]["status"] == "accepted"
    assert data["checks"]["feature_flag_default_off"] is True
    assert data["checks"]["default_runtime_neutral"] is True
    assert data["checks"]["ready_for_default_on_review"] is True


def test_stale_current_replay_quantifies_current_aod_effect_without_changing_pm_or_none() -> None:
    data = generate_aod_openaq_stale_current_replay_audit_data()
    summary = data["summary"]

    assert summary["aod_source_location_count"] == 8
    assert summary["aod_replay_row_count"] == 48
    assert summary["stale_deep_sky_max_penalty"] == -3.69
    assert summary["current_deep_sky_max_penalty"] == -7.38
    assert summary["stale_solar_system_max_penalty"] == -0.139
    assert summary["current_solar_system_max_penalty"] == -0.277
    assert summary["max_additional_deep_sky_penalty"] == -3.69
    assert summary["max_additional_solar_system_penalty"] == -0.138
    assert summary["max_current_to_stale_ratio"] <= 2.01
    assert summary["particulate_rows_unchanged"] is True
    assert summary["none_rows_unchanged"] is True


def test_stale_current_replay_preserves_zero_effect_aod_locations_and_confidence_neutrality() -> None:
    data = generate_aod_openaq_stale_current_replay_audit_data()

    assert data["summary"]["zero_effect_aod_locations_preserved"] == [
        "Cairo, Egypt",
        "Cape Town, South Africa",
        "Los Angeles, USA",
        "Mauna Kea, USA",
        "San Pedro de Atacama, Chile",
    ]
    assert data["checks"]["protected_targets_remain_protected"] is True
    assert data["checks"]["pm_and_none_rows_unchanged"] is True
    assert data["checks"]["confidence_neutral"] is True


def test_stale_current_replay_has_no_runtime_or_qml_wiring() -> None:
    data = generate_aod_openaq_stale_current_replay_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_stale_current_replay_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM AOD/OpenAQ Stale-vs-Current Replay Audit" in text
    assert "aod_openaq_stale_policy_ready_for_default_on_review" in text
    assert "Ready for default-on review: `True`" in text
    assert "Stale AOD weight policy: `keep_stale_aod_weight_0_5`" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
