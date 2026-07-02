from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.home_nsom_comparison_report import (
    REPORT_PATH,
    generate_report_data,
    render_markdown_report,
)


def test_home_nsom_report_data_is_deterministic_and_strict_json() -> None:
    first = generate_report_data()
    second = generate_report_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"]["developer_only"] is True
    assert first["metadata"]["scenario_count"] == 7
    assert first["metadata"]["row_count"] == 28
    assert [scenario["scenario_id"] for scenario in first["scenarios"]] == [
        "H01_bright_moon",
        "H02_dark_sky",
        "H03_high_light_pollution",
        "H04_poor_weather",
        "H05_blocked_session",
        "H06_small_equipment",
        "H07_large_equipment",
    ]


def test_report_compares_home_order_to_observable_order_and_keeps_practical_separate() -> None:
    data = generate_report_data()

    for scenario in data["scenarios"]:
        assert scenario["legacy_home_order"]
        assert scenario["nsom_observable_order"]
        assert scenario["nsom_practical_order"]
        assert "practical_used_for_home_ranking" in scenario["ordering_difference"]
        assert scenario["ordering_difference"]["practical_used_for_home_ranking"] is False
        assert len(scenario["legacy_home_order"]) == len(scenario["nsom_observable_order"]) == 4

    high_pollution = _scenario(data, "H03_high_light_pollution")
    assert high_pollution["ordering_difference"]["changed"] is True
    assert high_pollution["legacy_home_order"] != high_pollution["nsom_observable_order"]
    assert "H03_high_light_pollution" in data["summary"]["scenarios_with_ordering_difference"]


def test_report_marks_legacy_unavailable_components_and_score_replacement_effects() -> None:
    data = generate_report_data()
    bright_moon = _scenario(data, "H01_bright_moon")

    for row in bright_moon["rows"]:
        unavailable = row["legacy"]["home_deep_sky_adjusted"]["unavailable_components"]
        assert "weather_session_component:not_part_of_home_deep_sky_adjustment" in unavailable
        assert "observer_capability_component:not_part_of_home_deep_sky_adjustment" in unavailable
        assert row["legacy_score_mutation"]["runtime_object_mutated_by_report"] is False

    galaxy = _row(bright_moon, "galaxy")
    assert galaxy["legacy_score_mutation"]["replacement_object_score_differs"] is True
    assert galaxy["legacy_score_mutation"]["adjusted_score"] < galaxy["legacy_score_mutation"]["base_score"]


def test_weather_and_equipment_ownership_stay_separated_in_report_data() -> None:
    data = generate_report_data()
    good = _scenario(data, "H02_dark_sky")
    poor = _scenario(data, "H04_poor_weather")
    blocked = _scenario(data, "H05_blocked_session")
    small = _scenario(data, "H06_small_equipment")
    large = _scenario(data, "H07_large_equipment")

    for target_id in ("galaxy", "diffuse_nebula", "open_cluster", "globular_cluster"):
        assert _observable(_row(good, target_id)) == _observable(_row(poor, target_id))
        assert _observable(_row(good, target_id)) == _observable(_row(blocked, target_id))
        assert _practical(_row(good, target_id)) == _practical(_row(poor, target_id))
        assert _practical(_row(good, target_id)) == _practical(_row(blocked, target_id))

        assert _observable(_row(small, target_id)) == _observable(_row(large, target_id))

    assert _practical(_row(small, "galaxy")) != _practical(_row(large, "galaxy"))
    session = _row(blocked, "galaxy")["nsom"]["ownership"]["session_weather_effects"]
    assert session["blocking_status"]["blocks_plan"] is True
    assert session["used_in_observable_target_value"] is False
    assert session["used_in_practical_target_value"] is False


def test_confidence_remains_metadata_only_in_report() -> None:
    data = generate_report_data()
    control = data["confidence_control"]

    assert control["low_confidence_value"] < control["high_confidence_value"]
    assert control["observable_delta"] == 0.0
    assert control["practical_delta"] == 0.0
    assert control["score_factor"] is False
    assert control["score_effect"] == 0.0

    for row in _rows(data):
        confidence = row["nsom"]["recommendation_confidence"]
        assert confidence["role"] == "metadata_only"
        assert confidence["score_factor"] is False
        assert confidence["score_effect"] == 0.0


def test_home_nsom_report_is_not_wired_into_runtime_or_qml() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    app_controller = Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))
    controller_text = app_controller.read_text(encoding="utf-8")

    assert "home_nsom_comparison_report" not in qml_text
    assert "HOME_NSOM_COMPARISON_REPORT" not in qml_text
    assert "home_nsom_comparison_report" not in controller_text
    assert "HOME_NSOM_COMPARISON_REPORT" not in controller_text
    assert str(REPORT_PATH).replace("\\", "/") == "docs/HOME_NSOM_COMPARISON_REPORT.md"


def test_checked_in_home_nsom_markdown_report_exists() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Home NSOM Comparison Report" in text
    assert "7 deterministic scenarios" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def _scenario(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(scenario for scenario in data["scenarios"] if scenario["scenario_id"] == scenario_id)


def _row(scenario: dict[str, object], target_id: str) -> dict[str, object]:
    return next(row for row in scenario["rows"] if row["target"]["object_id"] == target_id)


def _rows(data: dict[str, object]) -> list[dict[str, object]]:
    return [row for scenario in data["scenarios"] for row in scenario["rows"]]


def _observable(row: dict[str, object]) -> float:
    return float(row["nsom"]["observable_target_value"]["value"])


def _practical(row: dict[str, object]) -> float:
    return float(row["nsom"]["practical_target_value"]["value"])
