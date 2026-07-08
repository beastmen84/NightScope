from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.detail_nsom_comparison_report import (
    REPORT_PATH,
    generate_report_data,
    render_markdown_report,
)


def test_detail_nsom_report_data_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_report_data()
    second = generate_report_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "selected_object_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
        "sky_compass_changed": False,
        "report_path": "docs/DETAIL_OBJECT_NSOM_COMPARISON_REPORT.md",
        "scenario_count": 6,
    }
    assert [scenario["scenario_id"] for scenario in first["scenarios"]] == [
        "D01_observing_bright_moon",
        "D02_catalogue_bright_moon",
        "D03_high_light_pollution",
        "D04_blocked_session",
        "D05_small_equipment",
        "D06_large_equipment",
    ]


def test_report_captures_observing_vs_catalogue_detail_source_policy() -> None:
    data = generate_report_data()
    observing = _scenario(data, "D01_observing_bright_moon")
    catalogue = _scenario(data, "D02_catalogue_bright_moon")

    observing_legacy = observing["legacy"]["selected_object_detail"]
    catalogue_legacy = catalogue["legacy"]["selected_object_detail"]
    assert observing_legacy["policy"] == "observing_detail_moon_adjusted_copy"
    assert observing_legacy["score_delta"] < 0
    assert observing_legacy["conditioned_copy_created"] is True
    assert catalogue_legacy["policy"] == "catalogue_detail_raw_object"
    assert catalogue_legacy["score_delta"] == 0
    assert catalogue_legacy["conditioned_copy_created"] is False

    assert observing["nsom"]["ownership"]["sky_effects"]["legacy_detail_uses_moon_adjustment"] is True
    assert catalogue["nsom"]["ownership"]["sky_effects"]["legacy_detail_uses_moon_adjustment"] is False
    assert catalogue["nsom"]["observation_environment"]["lunar_sky_background"] < 1.0


def test_report_keeps_sky_session_observer_and_confidence_ownership_separate() -> None:
    data = generate_report_data()
    polluted = _scenario(data, "D03_high_light_pollution")
    blocked = _scenario(data, "D04_blocked_session")
    small = _scenario(data, "D05_small_equipment")
    large = _scenario(data, "D06_large_equipment")
    confidence = data["confidence_control"]

    assert polluted["nsom"]["observation_environment"]["static_sky_background"] < 0.8
    assert polluted["nsom"]["ownership"]["sky_effects"]["legacy_detail_uses_static_sky_background"] is False

    assert blocked["nsom"]["session_viability"]["state"] == "blocked"
    assert blocked["nsom"]["session_viability"]["value"] == 0.0
    assert blocked["nsom"]["ownership"]["session_weather_effects"]["used_in_observable_target_value"] is False
    assert blocked["nsom"]["ownership"]["session_weather_effects"]["used_in_practical_target_value"] is False

    assert _observable(small) == _observable(large)
    assert _practical(large) > _practical(small)
    assert data["equipment_control"]["observable_delta"] == 0.0
    assert data["equipment_control"]["practical_delta"] > 0.0

    assert confidence["low_confidence_value"] < confidence["high_confidence_value"]
    assert confidence["observable_delta"] == 0.0
    assert confidence["practical_delta"] == 0.0
    assert confidence["legacy_display_delta"] == 0.0
    assert confidence["score_factor"] is False
    assert confidence["score_effect"] == 0.0


def test_detail_nsom_report_is_not_wired_into_runtime_or_qml() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    app_controller = Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))
    controller_text = app_controller.read_text(encoding="utf-8")

    assert "detail_nsom_comparison_report" not in qml_text
    assert "DETAIL_OBJECT_NSOM_COMPARISON_REPORT" not in qml_text
    assert "detail_nsom_comparison_report" not in controller_text
    assert "DETAIL_OBJECT_NSOM_COMPARISON_REPORT" not in controller_text
    assert str(REPORT_PATH).replace("\\", "/") == "docs/DETAIL_OBJECT_NSOM_COMPARISON_REPORT.md"


def test_checked_in_detail_nsom_markdown_report_exists() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Detail/Object NSOM Comparison Report" in text
    assert "6 deterministic Detail scenarios" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def _scenario(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(scenario for scenario in data["scenarios"] if scenario["scenario_id"] == scenario_id)


def _observable(scenario: dict[str, object]) -> float:
    return float(scenario["nsom"]["observable_target_value"]["value"])


def _practical(scenario: dict[str, object]) -> float:
    return float(scenario["nsom"]["practical_target_value"]["value"])
