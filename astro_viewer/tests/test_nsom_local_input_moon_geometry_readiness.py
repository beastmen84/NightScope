from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_local_input_moon_geometry_readiness import (
    REPORT_PATH,
    generate_local_input_moon_geometry_readiness_data,
    render_markdown_report,
)


def test_local_input_moon_geometry_readiness_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_local_input_moon_geometry_readiness_data()
    second = generate_local_input_moon_geometry_readiness_data()

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
    assert first["metadata"]["scoring_changed"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_data_source_taxonomy_separates_local_optional_and_external_inputs() -> None:
    data = generate_local_input_moon_geometry_readiness_data()
    sources = {source["source_id"]: source for source in data["data_source_taxonomy"]}

    assert sources["location"]["availability"] == "minimum_required_input"
    assert sources["location"]["external_provider"] is False
    assert sources["local_astronomy_ephemeris"]["availability"] == "available_after_location"
    assert sources["local_astronomy_ephemeris"]["external_provider"] is False
    assert sources["equipment_profile"]["availability"] == "optional_local"
    assert sources["equipment_profile"]["external_provider"] is False
    assert "naked-eye" in sources["equipment_profile"]["missing_input_policy"]

    assert sources["weather_open_meteo"]["availability"] == "optional_external"
    assert sources["weather_open_meteo"]["external_provider"] is True
    assert sources["sky_quality_viirs_or_fallback"]["availability"] == "optional_hybrid"
    assert sources["sky_quality_viirs_or_fallback"]["external_provider"] == "hybrid"
    assert "real VIIRS radiance" in sources["sky_quality_viirs_or_fallback"]["missing_input_policy"]
    assert sources["nasa_aod"]["external_provider"] is True
    assert sources["openaq_particulate"]["external_provider"] is True
    assert "default-on AOD/OpenAQ modifier" in sources["nasa_aod"]["current_scoring_role"]
    assert "default-on fallback modifier" in sources["openaq_particulate"]["current_scoring_role"]


def test_moon_geometry_is_local_ready_and_active_for_planner_only() -> None:
    data = generate_local_input_moon_geometry_readiness_data()
    readiness = data["moon_readiness"]
    fields = {field["field"]: field for field in data["moon_geometry_field_inventory"]}

    assert data["readiness"]["verdict"] == "local_input_moon_geometry_runtime_diagnostics_available"
    assert data["readiness"]["moon_geometry_scoring_enabled_now"] is True
    assert data["readiness"]["moon_geometry_ready_for_local_implementation"] is True
    assert data["readiness"]["moon_geometry_runtime_diagnostics_available"] is True
    assert data["readiness"]["moon_geometry_planner_scoring_path_available"] is True
    assert data["readiness"]["requires_provider_before_next_step"] is False
    assert data["blockers"] == []

    assert readiness["requires_location"] is True
    assert readiness["requires_current_time_or_session_window"] is True
    assert readiness["requires_weather_provider"] is False
    assert readiness["requires_viirs_provider"] is False
    assert readiness["requires_nasa_aod"] is False
    assert readiness["requires_openaq"] is False
    assert readiness["requires_equipment_profile"] is False
    assert readiness["nsom_owner"] == "Sky / ObservationEnvironment"
    assert readiness["first_consumer"] == "Planner before Home"
    assert readiness["current_modifier_with_flag_off"] == 0.0
    assert readiness["current_modifier_with_flag_on"] == 0.0

    assert fields["moon_illumination"]["status"] == "active_current"
    assert "active lunar_sky_background" in fields["moon_illumination"]["score_role_now"]
    for field_name in (
        "moon_altitude_deg",
        "moon_target_separation_deg",
        "moon_above_horizon",
        "moon_visible_during_target_window",
        "moon_set_before_target_window",
    ):
        assert fields[field_name]["status"] == "runtime_planner_scoring_geometry_input"
        assert "MoonGeometrySummary" in fields[field_name]["source_today"]
        assert fields[field_name]["absent_from_moon_summary"] is True
        assert "active Planner input" in fields[field_name]["score_role_now"]


def test_current_consumers_use_illumination_and_keep_geometry_future() -> None:
    data = generate_local_input_moon_geometry_readiness_data()
    consumers = {consumer["consumer"]: consumer for consumer in data["current_moon_consumers"]}

    assert consumers["Planner NSOM"]["current_moon_input"] == "MoonSummary.illumination"
    assert consumers["Planner NSOM"]["geometry_input"] == "default-on Planner scoring input"
    assert "geometry-aware lunar_sky_background" in consumers["Planner NSOM"]["score_status"]
    assert consumers["Home recommendedDeepSky NSOM"]["geometry_input"] == "diagnostic export only"
    assert consumers["Best Object NSOM"]["geometry_input"] == "diagnostic export only"
    assert consumers["Sky Compass NSOM"]["geometry_input"] == "diagnostic export only"
    assert consumers["ObservationConditions legacy compatibility"]["score_status"] == (
        "geometry modifier is neutral"
    )
    assert consumers["AOD/OpenAQ"]["score_status"] == (
        "external provider data can affect aerosol modifier when policy eligible"
    )


def test_source_markers_and_safety_checks_are_clean() -> None:
    data = generate_local_input_moon_geometry_readiness_data()
    checks = data["checks"]
    sources = {source["surface"]: source for source in data["source_marker_checks"]}

    assert checks["source_markers_all_found"] is True
    assert checks["minimum_location_source_documented"] is True
    assert checks["local_astronomy_is_not_external_provider"] is True
    assert checks["equipment_default_is_local_optional"] is True
    assert checks["weather_marked_external_optional"] is True
    assert checks["viirs_source_distinguishes_fallback"] is True
    assert checks["aod_openaq_external_default_on_gated"] is True
    assert checks["moon_summary_has_phase_illumination"] is True
    assert checks["moon_geometry_fields_are_runtime_diagnostics"] is True
    assert checks["moon_geometry_absent_from_moon_summary"] is True
    assert checks["moon_geometry_requires_no_provider"] is True
    assert checks["moon_geometry_modifier_still_neutral"] is True
    assert checks["moon_geometry_planner_scoring_path_available"] is True
    assert checks["runtime_report_imports_absent"] is True
    assert checks["qml_report_exposure_absent"] is True
    assert checks["no_scoring_change"] is True
    assert checks["runtime_behaviour_unchanged_by_audit"] is True

    assert sources["Manual and automatic location inputs"]["all_markers_found"] is True
    assert sources["Skyfield Moon summary"]["all_markers_found"] is True
    assert sources["MoonSummary runtime DTO"]["all_markers_found"] is True
    assert sources["MoonGeometrySummary runtime DTO"]["all_markers_found"] is True
    assert sources["Skyfield Moon geometry diagnostics"]["all_markers_found"] is True
    assert sources["Moon geometry future condition input"]["all_markers_found"] is True
    assert sources["NSOM runtime Moon geometry diagnostics"]["all_markers_found"] is True
    assert sources["AOD and OpenAQ neutral condition inputs"]["all_markers_found"] is True
    assert sources["Planner NSOM moon background"]["all_markers_found"] is True
    assert sources["Home NSOM moon background"]["all_markers_found"] is True
    assert sources["VIIRS sky-quality distinction"]["all_markers_found"] is True
    assert all(source["missing_markers"] == [] for source in sources.values())


def test_checked_in_local_input_moon_geometry_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Local Input and Moon Geometry Readiness" in text
    assert "local_input_moon_geometry_runtime_diagnostics_available" in text
    assert "moon_geometry_planner_default_on" in text
    assert "nasa_aod" in text
    assert "openaq_particulate" in text
    assert "default-off Planner NSOM scoring input" not in text
    assert "No default runtime scoring" not in text
    assert "default-off Planner NSOM scoring path" not in text
    assert "Review 1.14.6" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
