from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.services.observation_conditions_service import ObservationConditionFeatureFlags
from astro_viewer.tools.nsom_aod_openaq_scoring_readiness import (
    REPORT_PATH,
    generate_aod_openaq_scoring_readiness_data,
    render_markdown_report,
)


def test_aod_openaq_readiness_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_aod_openaq_scoring_readiness_data()
    second = generate_aod_openaq_scoring_readiness_data()

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
    assert first["metadata"]["planner_changed"] is False
    assert first["metadata"]["home_changed"] is False
    assert first["metadata"]["best_object_changed"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_aod_openaq_scoring_is_not_ready_and_blockers_are_explicit() -> None:
    data = generate_aod_openaq_scoring_readiness_data()
    decisions = {item["decision_id"]: item for item in data["policy_decisions"]}

    assert data["readiness"]["verdict"] == "aod_openaq_default_off_scoring_experiment_available"
    assert data["readiness"]["ready_for_default_on"] is False
    assert data["readiness"]["ready_for_default_off_experiment"] is True
    assert data["readiness"]["score_formula_implemented"] is True
    assert data["readiness"]["experimental_aerosol_scoring_default"] is False
    assert ObservationConditionFeatureFlags().experimental_aerosol_scoring is False

    assert decisions["aod_qa_policy"]["status"] == "accepted_for_default_off_experiment"
    assert decisions["aod_qa_policy"]["blocks_scoring"] is False
    assert decisions["openaq_locality_policy"]["status"] == "accepted_for_default_off_experiment"
    assert decisions["openaq_locality_policy"]["blocks_scoring"] is False
    assert decisions["double_counting_policy"]["status"] == "accepted_for_default_off_experiment"
    assert decisions["double_counting_policy"]["blocks_scoring"] is False
    assert decisions["confidence_metadata_policy"]["blocks_scoring"] is False
    assert data["blockers"] == []


def test_freshness_and_source_precedence_are_characterized() -> None:
    data = generate_aod_openaq_scoring_readiness_data()
    freshness = {
        (row["input"], row["age_or_category"]): row["weight"]
        for row in data["freshness_policy"]
    }
    precedence = {row["case"]: row["primary_source"] for row in data["source_precedence_rows"]}

    assert freshness[("nasa_aod", "0 days")] == 1.0
    assert freshness[("nasa_aod", "4 days")] == 0.5
    assert freshness[("nasa_aod", "7.01 days")] == 0.0
    assert freshness[("openaq_particulate", "0 days")] == 1.0
    assert freshness[("openaq_particulate", "4 days")] == 0.3
    assert freshness[("openaq_particulate", "7.01 days")] == 0.0

    assert precedence["fresh_aod_and_pm"] == "aod"
    assert precedence["historical_aod_fresh_pm"] == "particulate"
    assert precedence["fresh_aod_missing_pm"] == "aod"
    assert precedence["no_eligible_provider"] == "none"
    assert data["checks"]["aod_primary_pm_fallback"] is True


def test_target_sensitivity_is_directional_without_default_score_effect() -> None:
    data = generate_aod_openaq_scoring_readiness_data()
    by_class = {row["target_class"]: row for row in data["target_sensitivity_rows"]}

    assert by_class["galaxy"]["sensitivity"] > by_class["diffuse_nebula"]["sensitivity"]
    assert by_class["diffuse_nebula"]["sensitivity"] > by_class["open_cluster"]["sensitivity"]
    assert by_class["open_cluster"]["sensitivity"] > by_class["planet"]["sensitivity"]
    assert by_class["planet"]["sensitivity"] > by_class["moon"]["sensitivity"]
    assert by_class["galaxy"]["penalty_cap"] == 12.0
    assert by_class["moon"]["penalty_cap"] == 1.0
    assert all(
        row["scoring_status"] == "default-off formula input; no default score effect"
        for row in by_class.values()
    )
    assert data["checks"]["target_sensitivity_order_characterized"] is True


def test_aerosol_default_runtime_is_neutral_and_flag_on_has_target_specific_effect() -> None:
    data = generate_aod_openaq_scoring_readiness_data()

    assert data["checks"]["aerosol_modifier_default_runtime_neutral"] is True
    assert data["checks"]["aerosol_experiment_has_target_specific_effect"] is True
    assert data["checks"]["aerosol_experiment_uses_single_source"] is True
    assert data["checks"]["recommendation_confidence_not_in_formula"] is True
    for row in data["score_neutrality_rows"]:
        assert row["flag_off_modifier"] == 0.0
        assert row["default_adjusted_score_delta"] == 0
        assert "confidence" not in row["experimental_breakdown"]["formula"].lower()
    galaxy = next(row for row in data["score_neutrality_rows"] if row["case"] == "galaxy_high_aerosol")
    moon = next(row for row in data["score_neutrality_rows"] if row["case"] == "moon_protected")
    assert galaxy["flag_on_modifier"] < moon["flag_on_modifier"] <= 0.0


def test_source_markers_and_runtime_qml_wiring_are_clean() -> None:
    data = generate_aod_openaq_scoring_readiness_data()

    assert data["checks"]["source_markers_all_found"] is True
    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_aod_openaq_readiness_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM AOD/OpenAQ Scoring Readiness" in text
    assert "aod_openaq_default_off_scoring_experiment_available" in text
    assert "Ready for default-on: `False`" in text
    assert "Ready for default-off experiment: `True`" in text
    assert "Score formula implemented: `True`" in text
    assert "confidence_metadata_policy" in text
    assert "RecommendationConfidence remains metadata" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
