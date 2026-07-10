from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_aod_openaq_default_on_readiness import (
    REPORT_PATH,
    generate_aod_openaq_default_on_readiness_data,
    render_markdown_report,
)


def test_aod_openaq_default_on_readiness_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_aod_openaq_default_on_readiness_data()
    second = generate_aod_openaq_default_on_readiness_data()

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
    assert first["readiness"]["feature_flag_change_in_this_audit"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_aod_openaq_default_on_readiness_keeps_flag_off_and_blocks_default_on() -> None:
    data = generate_aod_openaq_default_on_readiness_data()
    gates = {gate["gate"]: gate for gate in data["readiness_gates"]}

    assert data["readiness"]["verdict"] == "aod_openaq_default_on_blocked_by_score_scale_review"
    assert data["readiness"]["ready_for_default_on"] is False
    assert data["readiness"]["default_runtime_score_effect"] == 0.0
    assert data["blockers"] == ["aerosol_score_scale"]
    assert gates["formula_shape"]["status"] == "accepted"
    assert gates["formula_shape"]["blocks_default_on"] is False
    assert gates["aerosol_score_scale"]["status"] == "review"
    assert gates["aerosol_score_scale"]["blocks_default_on"] is True
    assert data["checks"]["feature_flag_default_off"] is True
    assert data["checks"]["default_runtime_neutral"] is True
    assert data["checks"]["score_scale_remains_blocking"] is True
    assert data["checks"]["ready_for_default_on_is_false"] is True


def test_aod_openaq_default_on_readiness_accepts_non_score_scale_gates() -> None:
    data = generate_aod_openaq_default_on_readiness_data()
    gates = {gate["gate"]: gate for gate in data["readiness_gates"]}

    assert gates["provider_quality_policy"]["status"] == "accepted"
    assert gates["source_ownership"]["status"] == "accepted"
    assert gates["confidence_neutrality"]["status"] == "accepted"
    assert gates["default_runtime_safety"]["status"] == "accepted"
    assert data["checks"]["provider_quality_policy_accepted"] is True
    assert data["checks"]["source_ownership_accepted"] is True
    assert data["checks"]["formula_shape_calibrated"] is True
    assert data["checks"]["confidence_neutral"] is True
    assert data["calibration_summary"]["penalty_cap_transparency_shape_calibrated"] is True
    assert data["calibration_summary"]["default_on_blockers"] == [
        "aerosol-score-scale-field-validation"
    ]


def test_aod_openaq_default_on_readiness_impact_rows_are_directional() -> None:
    data = generate_aod_openaq_default_on_readiness_data()
    rows = {
        (row["target_class"], row["source_case"]): row
        for row in data["impact_rows"]
    }

    assert rows[("galaxy", "high_aod_current")]["score_modifier"] < rows[
        ("diffuse_nebula", "high_aod_current")
    ]["score_modifier"]
    assert rows[("diffuse_nebula", "high_aod_current")]["score_modifier"] < rows[
        ("planet", "high_aod_current")
    ]["score_modifier"]
    assert rows[("planet", "high_aod_current")]["score_modifier"] < rows[
        ("moon", "high_aod_current")
    ]["score_modifier"]
    assert rows[("galaxy", "pm_only_local")]["score_modifier"] > rows[
        ("galaxy", "high_aod_current")
    ]["score_modifier"]
    assert rows[("galaxy", "context_pm_rejected")]["score_modifier"] == 0.0


def test_aod_openaq_default_on_readiness_has_no_runtime_or_qml_wiring() -> None:
    data = generate_aod_openaq_default_on_readiness_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_aod_openaq_default_on_readiness_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM AOD/OpenAQ Default-On Readiness" in text
    assert "aod_openaq_default_on_blocked_by_score_scale_review" in text
    assert "Ready for default-on: `False`" in text
    assert "aerosol_score_scale" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
