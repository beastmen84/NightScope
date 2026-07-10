from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionFeatureFlags,
)
from astro_viewer.tools.nsom_aod_openaq_calibration_audit import (
    REPORT_PATH,
    generate_aod_openaq_calibration_audit_data,
    render_markdown_report,
)


def test_aod_openaq_calibration_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_aod_openaq_calibration_audit_data()
    second = generate_aod_openaq_calibration_audit_data()

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
    assert first["readiness"]["formula_changed_by_calibration"] is True
    assert first["readiness"]["weights_tuned_by_calibration"] is False
    assert first["readiness"]["penalty_cap_transparency_shape_calibrated"] is True
    assert first["readiness"]["ready_for_default_on"] is False
    assert first["checks"]["strict_json_compatible"] is True
    assert ObservationConditionFeatureFlags().experimental_aerosol_scoring is False


def test_aod_openaq_calibration_audit_formula_direction_and_source_policy() -> None:
    data = generate_aod_openaq_calibration_audit_data()
    cases = {
        (case["target_class"], case["source_case"]): case
        for case in data["cases"]
    }

    assert data["case_count"] == 70
    assert data["checks"]["default_runtime_neutral"] is True
    assert data["checks"]["feature_flag_default_off"] is True
    assert data["checks"]["aod_primary_when_eligible"] is True
    assert data["checks"]["pm_fallback_when_aod_rejected"] is True
    assert data["checks"]["pm_context_only_rejected"] is True
    assert data["checks"]["historical_aod_without_pm_neutral"] is True
    assert data["checks"]["high_aod_target_class_order_directional"] is True
    assert data["checks"]["stale_aod_reduces_current_effect"] is True
    assert data["checks"]["pm_fallback_weaker_than_aod"] is True

    assert cases[("galaxy", "high_aod_current")]["primary_source"] == "aod"
    assert cases[("galaxy", "high_aod_current")]["max_transparency_loss"] == 0.12
    assert cases[("galaxy", "high_aod_current")]["transparency_loss"] == 0.12
    assert cases[("galaxy", "high_aod_current")]["score_modifier"] == -9.84
    assert cases[("galaxy", "local_pm_fallback")]["primary_source"] == "particulate"
    assert cases[("galaxy", "context_pm_rejected")]["primary_source"] == "none"
    assert cases[("galaxy", "historical_aod_no_pm")]["score_modifier"] == 0.0
    assert (
        cases[("galaxy", "high_aod_current")]["penalty_points"]
        > cases[("diffuse_nebula", "high_aod_current")]["penalty_points"]
        > cases[("planetary_nebula", "high_aod_current")]["penalty_points"]
        > cases[("globular_cluster", "high_aod_current")]["penalty_points"]
        > cases[("open_cluster", "high_aod_current")]["penalty_points"]
        > cases[("planet", "high_aod_current")]["penalty_points"]
        > cases[("moon", "high_aod_current")]["penalty_points"]
    )


def test_aod_openaq_calibration_audit_confidence_is_metadata_only() -> None:
    data = generate_aod_openaq_calibration_audit_data()
    cases = {
        (case["target_class"], case["source_case"]): case
        for case in data["cases"]
    }

    assert data["checks"]["provider_product_confidence_not_in_score"] is True
    assert data["checks"]["confidence_not_in_formula"] is True
    assert data["formula"]["confidence_role"].startswith("Provider confidence")
    assert data["formula"]["max_transparency_loss"] == "penalty_cap / 100"
    assert "target_score" in data["formula"]["score_modifier"]
    assert "provider_product_weight" in data["formula"]["not_in_formula"]
    assert "recommendation_confidence" in data["formula"]["not_in_formula"]
    assert cases[("galaxy", "high_aod_modis_confidence")]["score_modifier"] == cases[
        ("galaxy", "high_aod_current")
    ]["score_modifier"]
    assert all(case["confidence_score_role"] == "metadata_only" for case in data["cases"])


def test_aod_openaq_calibration_audit_surfaces_default_on_review_items() -> None:
    data = generate_aod_openaq_calibration_audit_data()
    review_items = {item["id"]: item for item in data["review_items"]}

    assert set(data["default_on_blockers"]) == {
        "aerosol-score-scale-field-validation",
    }
    assert review_items["aerosol-score-scale-field-validation"]["blocks_default_on"] is True
    assert review_items["penalty-cap-vs-transparency-shape"]["severity"] == "calibrated"
    assert review_items["penalty-cap-vs-transparency-shape"]["blocks_default_on"] is False
    assert review_items["protected-target-small-modifier-rounding"]["blocks_default_on"] is False
    assert data["checks"]["protected_target_rounding_cases_identified"] is True
    assert data["checks"]["default_on_blockers_explicit"] is True


def test_aod_openaq_calibration_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_aod_openaq_calibration_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_aod_openaq_calibration_audit_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM AOD/OpenAQ Calibration Audit" in text
    assert "aod_openaq_targeted_transparency_calibration_applied" in text
    assert "Ready for default-on: `False`" in text
    assert "aerosol-score-scale-field-validation" in text
    assert "protected-target-small-modifier-rounding" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
