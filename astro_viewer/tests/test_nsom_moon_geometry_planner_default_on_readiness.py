from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.observation_conditions_service import ObservationConditionFeatureFlags
from astro_viewer.tools.nsom_moon_geometry_planner_default_on_readiness import (
    REPORT_PATH,
    generate_moon_geometry_planner_default_on_readiness_data,
    render_markdown_report,
)


def test_moon_geometry_default_on_readiness_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_moon_geometry_planner_default_on_readiness_data()
    second = generate_moon_geometry_planner_default_on_readiness_data()

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
    assert first["metadata"]["planner_scoring_changed_by_this_audit"] is False
    assert first["metadata"]["report_path"] == "docs/NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS.md"
    assert "docs/NSOM_MOON_GEOMETRY_PLANNER_CALIBRATION.md" in first["metadata"]["source_reports"]
    assert first["checks"]["strict_json_compatible"] is True


def test_moon_geometry_default_on_readiness_reports_ready_but_does_not_enable_default() -> None:
    data = generate_moon_geometry_planner_default_on_readiness_data()

    assert data["readiness"]["verdict"] == "moon_geometry_planner_ready_for_default_on_switch"
    assert data["readiness"]["ready_for_default_on_switch"] is True
    assert data["readiness"]["default_on_switch_completed"] is False
    assert data["readiness"]["requires_separate_switch"] is True
    assert data["readiness"]["night_planner_default_uses_moon_geometry"] is False
    assert data["readiness"]["opt_in_path_available"] is True
    assert data["readiness"]["ready_for_aod_openaq_scoring"] is False
    assert data["default_on_blockers"] == []
    assert ObservationConditionFeatureFlags().experimental_moon_geometry_scoring is False
    assert NightPlannerService().uses_moon_geometry_scoring is False


def test_moon_geometry_default_on_readiness_accepts_calibration_without_tuning() -> None:
    data = generate_moon_geometry_planner_default_on_readiness_data()
    decisions = {decision["decision_id"]: decision for decision in data["decisions"]}

    assert decisions["calibration_direction"]["status"] == "accepted_for_default_on_review"
    assert decisions["missing_geometry_fallback"]["status"] == "accepted"
    assert decisions["protected_targets"]["status"] == "accepted"
    assert decisions["ownership_boundary"]["status"] == "accepted"
    assert decisions["confidence_metadata"]["status"] == "accepted"
    assert decisions["runtime_cost"]["status"] == "monitor_after_switch"
    assert decisions["aod_openaq_scope"]["status"] == "deferred"
    assert all(decision["blocks_default_on"] is False for decision in data["decisions"])

    assert data["checks"]["deep_sky_close_moon_reduces_value"] is True
    assert data["checks"]["moon_set_before_window_improves_deep_sky"] is True
    assert data["checks"]["planet_and_moon_protected"] is True
    assert data["checks"]["only_lunar_environment_component_changes"] is True
    assert data["checks"]["confidence_zero_score_effect"] is True
    assert data["checks"]["missing_geometry_keeps_baseline"] is True


def test_moon_geometry_default_on_readiness_keeps_report_tooling_out_of_runtime_and_qml() -> None:
    data = generate_moon_geometry_planner_default_on_readiness_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["runtime_behaviour_unchanged_by_audit"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_moon_geometry_default_on_readiness_records_representative_cases() -> None:
    data = generate_moon_geometry_planner_default_on_readiness_data()
    cases = {
        f"{case['geometry_case']}:{case['target_id']}": case
        for case in data["representative_cases"]
    }

    assert cases["missing:galaxy"]["opportunity_score_delta"] == 0.0
    assert cases["set_before_window:galaxy"]["opportunity_score_delta"] > 0.0
    assert cases["high_altitude_close:galaxy"]["opportunity_score_delta"] < 0.0
    assert cases["high_altitude_far:galaxy"]["opportunity_score_delta"] > 0.0
    assert cases["high_altitude_close:planet"]["opportunity_score_delta"] == 0.0
    assert all(case["confidence_score_effect"] == 0.0 for case in cases.values())


def test_checked_in_moon_geometry_default_on_readiness_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Moon Geometry Planner Default-On Readiness" in text
    assert "moon_geometry_planner_ready_for_default_on_switch" in text
    assert "None for a narrow Planner Moon geometry default-on switch" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
