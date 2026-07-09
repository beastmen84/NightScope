from __future__ import annotations

import json
from pathlib import Path

import pytest

from astro_viewer.tools.nsom_moon_geometry_planner_calibration import (
    REPORT_PATH,
    generate_moon_geometry_planner_calibration_data,
    render_markdown_report,
)


def test_moon_geometry_planner_calibration_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_moon_geometry_planner_calibration_data()
    second = generate_moon_geometry_planner_calibration_data()

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
    assert first["metadata"]["runtime_wiring"] is False
    assert first["metadata"]["experimental_flag_default"] is False
    assert first["metadata"]["score_owner"] == "Sky / ObservationEnvironment.lunar_sky_background"
    assert first["metadata"]["scenario_count"] == 30
    assert first["checks"]["strict_json_compatible"] is True
    assert first["checks"]["runtime_report_imports_absent"] is True
    assert first["checks"]["qml_report_exposure_absent"] is True


def test_moon_geometry_flag_off_matches_baseline_and_flag_on_changes_expected_cases() -> None:
    data = generate_moon_geometry_planner_calibration_data()

    missing_galaxy = _row(data, "missing", "galaxy")
    set_before_window_galaxy = _row(data, "set_before_window", "galaxy")
    close_galaxy = _row(data, "high_altitude_close", "galaxy")
    far_galaxy = _row(data, "high_altitude_far", "galaxy")

    assert missing_galaxy["deltas"]["opportunity_score_delta"] == pytest.approx(0.0)
    assert missing_galaxy["deltas"]["lunar_sky_background_delta"] == pytest.approx(0.0)

    assert set_before_window_galaxy["flag_on"]["effective_components"]["lunar_sky_background"] > (
        set_before_window_galaxy["flag_off"]["effective_components"]["lunar_sky_background"]
    )
    assert set_before_window_galaxy["deltas"]["opportunity_score_delta"] > 0.0

    assert close_galaxy["flag_on"]["effective_components"]["lunar_sky_background"] < (
        far_galaxy["flag_on"]["effective_components"]["lunar_sky_background"]
    )
    assert close_galaxy["flag_on"]["opportunity_score"] < far_galaxy["flag_on"]["opportunity_score"]


def test_moon_geometry_planner_calibration_keeps_planets_and_moon_protected() -> None:
    data = generate_moon_geometry_planner_calibration_data()

    for target_id in ("planet", "moon"):
        for geometry_case in (
            "missing",
            "set_before_window",
            "low_altitude_close",
            "high_altitude_close",
            "high_altitude_far",
        ):
            row = _row(data, geometry_case, target_id)

            assert row["deltas"]["lunar_sky_background_delta"] == pytest.approx(0.0)
            assert row["deltas"]["opportunity_score_delta"] == pytest.approx(0.0)
            assert row["flag_on"]["effective_components"]["lunar_sky_background"] == pytest.approx(1.0)


def test_moon_geometry_planner_calibration_changes_only_lunar_environment_component() -> None:
    data = generate_moon_geometry_planner_calibration_data()
    row = _row(data, "high_altitude_close", "galaxy")

    assert row["deltas"]["lunar_sky_background_delta"] < 0.0
    assert row["deltas"]["geometric_visibility_delta"] == pytest.approx(0.0)
    assert row["deltas"]["static_sky_background_delta"] == pytest.approx(0.0)
    assert row["deltas"]["atmospheric_transparency_delta"] == pytest.approx(0.0)
    assert row["deltas"]["horizon_context_delta"] == pytest.approx(0.0)
    assert row["deltas"]["observer_capability_summary_delta"] == pytest.approx(0.0)
    assert row["deltas"]["session_viability_delta"] == pytest.approx(0.0)
    assert row["deltas"]["observing_window_quality_delta"] == pytest.approx(0.0)
    assert row["deltas"]["chronology_fit_delta"] == pytest.approx(0.0)
    assert row["deltas"]["practical_constraints_delta"] == pytest.approx(0.0)
    assert row["ownership"]["non_lunar_leakage"] is False


def test_moon_geometry_confidence_is_metadata_only_and_tracks_geometry_availability() -> None:
    data = generate_moon_geometry_planner_calibration_data()
    missing = _row(data, "missing", "galaxy")
    close = _row(data, "high_altitude_close", "galaxy")

    assert missing["confidence"]["score_effect"] == pytest.approx(0.0)
    assert missing["confidence"]["flag_on_moon_geometry_confidence"] is None
    assert close["confidence"]["score_effect"] == pytest.approx(0.0)
    assert close["confidence"]["flag_on_moon_geometry_confidence"] == pytest.approx(1.0)
    assert close["deltas"]["confidence_score_effect_delta"] == pytest.approx(0.0)


def test_checked_in_moon_geometry_planner_calibration_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Moon Geometry Planner Calibration" in text
    assert "experimental_moon_geometry_scoring" in text
    assert "AOD and OpenAQ remain separate provider-backed inputs" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def _row(data: dict[str, object], geometry_case: str, target_id: str) -> dict[str, object]:
    matches = [
        row
        for row in data["scenario_rows"]
        if row["geometry_case"] == geometry_case and row["target_id"] == target_id
    ]
    assert len(matches) == 1
    return matches[0]
