from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_aod_openaq_field_calibration import (
    REPORT_PATH,
    generate_aod_openaq_field_calibration_data,
    render_markdown_report,
)


def test_aod_openaq_field_calibration_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_aod_openaq_field_calibration_data()
    second = generate_aod_openaq_field_calibration_data()

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


def test_aod_openaq_field_calibration_classifies_scale_without_enabling_default_on() -> None:
    data = generate_aod_openaq_field_calibration_data()

    assert data["readiness"]["verdict"] == "aod_openaq_field_calibration_scale_acceptance_ready"
    assert data["readiness"]["ready_for_default_on"] is False
    assert data["readiness"]["default_runtime_score_effect"] == 0.0
    assert data["readiness"]["field_calibration_complete"] is True
    assert data["readiness"]["score_scale_status"] == "accepted_for_narrow_default_on_review"
    assert data["assessment"]["warning_rows"] == 0
    assert data["assessment"]["remaining_blocker"] == "human_acceptance_or_real_field_observations"
    assert data["readiness_blockers_before_field_calibration"] == ["aerosol_score_scale"]


def test_aod_openaq_field_calibration_scenarios_are_directional() -> None:
    data = generate_aod_openaq_field_calibration_data()
    rows = {
        (row["target_class"], row["source_case"]): row
        for row in data["scenarios"]
    }

    assert data["scenario_count"] == 20
    assert data["checks"]["clean_air_neutral"] is True
    assert data["checks"]["rejected_providers_neutral"] is True
    assert data["checks"]["deep_sky_more_affected_than_solar_system"] is True
    assert data["checks"]["pm_fallback_weaker_than_high_aod"] is True
    assert rows[("galaxy", "high_aod_current")]["score_modifier"] < rows[
        ("diffuse_nebula", "high_aod_current")
    ]["score_modifier"]
    assert rows[("planet", "high_aod_current")]["score_modifier"] < 0.0
    assert rows[("moon", "high_aod_current")]["score_modifier"] < 0.0
    assert rows[("galaxy", "context_pm_rejected")]["score_modifier"] == 0.0


def test_aod_openaq_field_calibration_bands_are_explicit() -> None:
    data = generate_aod_openaq_field_calibration_data()

    assert data["checks"]["all_rows_within_or_near_expected_band"] is True
    assert all(row["status"] in {"accepted", "review"} for row in data["scenarios"])
    assert data["assessment"]["review_rows"] == 0
    assert data["assessment"]["warning_rows"] == 0
    assert all(
        row["expected_min"] <= row["score_modifier"] <= row["expected_max"]
        or row["status"] == "review"
        for row in data["scenarios"]
    )


def test_aod_openaq_field_calibration_has_no_runtime_or_qml_wiring() -> None:
    data = generate_aod_openaq_field_calibration_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_aod_openaq_field_calibration_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM AOD/OpenAQ Field Calibration" in text
    assert "aod_openaq_field_calibration_scale_acceptance_ready" in text
    assert "Ready for default-on: `False`" in text
    assert "human_acceptance_or_real_field_observations" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
