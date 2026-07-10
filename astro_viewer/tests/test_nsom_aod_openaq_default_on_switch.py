from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionFeatureFlags,
)
from astro_viewer.tools.nsom_aod_openaq_default_on_switch import (
    REPORT_PATH,
    generate_aod_openaq_default_on_switch_data,
    render_markdown_report,
)


def test_aod_openaq_default_on_switch_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_aod_openaq_default_on_switch_data()
    second = generate_aod_openaq_default_on_switch_data()

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
    assert first["checks"]["strict_json_compatible"] is True


def test_aod_openaq_default_path_is_on_and_forced_off_rollback_is_neutral() -> None:
    data = generate_aod_openaq_default_on_switch_data()
    example = data["example"]

    assert ObservationConditionFeatureFlags().experimental_aerosol_scoring is True
    assert data["switch"]["default_flag"] == (
        "ObservationConditionFeatureFlags.experimental_aerosol_scoring = True"
    )
    assert data["switch"]["rollback"] == (
        "ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)"
    )
    assert data["checks"]["default_flag_enabled"] is True
    assert data["checks"]["default_path_uses_aod_openaq_when_policy_eligible"] is True
    assert data["checks"]["forced_off_rollback_is_neutral"] is True
    assert example["default_adjusted_score"] < example["base_score"]
    assert example["forced_off_adjusted_score"] == example["base_score"]
    assert example["default_breakdown"]["primary_source"] == "aod"
    assert example["default_breakdown"]["score_modifier"] == -7.38


def test_aod_openaq_default_on_switch_confidence_and_wiring_are_safe() -> None:
    data = generate_aod_openaq_default_on_switch_data()

    assert data["checks"]["confidence_metadata_does_not_scale_score"] is True
    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_aod_openaq_default_on_switch_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM AOD/OpenAQ Default-On Switch" in text
    assert "ObservationConditionFeatureFlags.experimental_aerosol_scoring = True" in text
    assert "ObservationConditionFeatureFlags(experimental_aerosol_scoring=False)" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
