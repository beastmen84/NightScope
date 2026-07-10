from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.services.observation_conditions_service import ObservationConditionFeatureFlags
from astro_viewer.tools.nsom_aod_openaq_default_off_scoring_experiment import (
    REPORT_PATH,
    generate_aod_openaq_default_off_scoring_experiment_data,
    render_markdown_report,
)


def test_default_off_aerosol_experiment_report_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_aod_openaq_default_off_scoring_experiment_data()
    second = generate_aod_openaq_default_off_scoring_experiment_data()

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
    assert first["metadata"]["runtime_behaviour_changed_by_this_report"] is False
    assert first["readiness"]["default_runtime_score_effect"] == 0.0
    assert first["readiness"]["ready_for_default_on"] is False
    assert ObservationConditionFeatureFlags().experimental_aerosol_scoring is False
    assert first["checks"]["strict_json_compatible"] is True


def test_default_off_aerosol_experiment_formula_guardrails() -> None:
    data = generate_aod_openaq_default_off_scoring_experiment_data()
    cases = {case["case"]: case["experimental_breakdown"] for case in data["cases"]}

    assert data["checks"]["default_runtime_neutral"] is True
    assert data["checks"]["aod_is_primary_when_eligible"] is True
    assert data["checks"]["pm_is_fallback_when_aod_rejected"] is True
    assert data["checks"]["rejected_sources_remain_neutral"] is True
    assert data["checks"]["deep_sky_more_sensitive_than_planet_moon"] is True
    assert data["checks"]["confidence_not_in_formula"] is True

    assert cases["fresh_aod_galaxy"]["primary_source"] == "aod"
    assert cases["pm_fallback_galaxy"]["primary_source"] == "particulate"
    assert cases["rejected_sources_neutral"]["primary_source"] == "none"
    assert cases["fresh_aod_galaxy"]["score_modifier"] < cases["fresh_aod_planet"]["score_modifier"] < 0.0
    assert cases["fresh_aod_moon"]["score_modifier"] < 0.0
    assert cases["confidence_product_neutral"]["score_modifier"] == cases["fresh_aod_galaxy"]["score_modifier"]


def test_default_off_aerosol_experiment_report_has_no_runtime_or_qml_wiring() -> None:
    data = generate_aod_openaq_default_off_scoring_experiment_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_default_off_aerosol_experiment_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM AOD/OpenAQ Default-Off Scoring Experiment" in text
    assert "aod_openaq_default_off_scoring_experiment_implemented" in text
    assert "Ready for default-on: `False`" in text
    assert "default-off AOD/OpenAQ scoring experiment" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
