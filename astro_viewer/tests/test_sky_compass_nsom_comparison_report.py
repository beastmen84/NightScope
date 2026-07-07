from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.sky_compass_nsom_comparison_report import (
    REPORT_PATH,
    generate_report_data,
    render_markdown_report,
)


def test_sky_compass_report_data_is_deterministic_and_strict_json() -> None:
    first = generate_report_data()
    second = generate_report_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"]["developer_only"] is True
    assert first["metadata"]["scenario_count"] == 8
    assert first["metadata"]["row_count"] == 48
    assert [scenario["scenario_id"] for scenario in first["scenarios"]] == [
        "S01_dark_sky",
        "S02_bright_moon",
        "S03_high_light_pollution",
        "S04_poor_weather",
        "S05_blocked_session",
        "S06_small_equipment",
        "S07_large_equipment",
        "S08_plan_best_boost",
    ]


def test_report_compares_legacy_direction_order_to_nsom_references() -> None:
    data = generate_report_data()

    for scenario in data["scenarios"]:
        assert scenario["legacy_direction_order"]
        assert scenario["nsom_observable_direction_order"]
        assert scenario["nsom_practical_direction_order"]
        assert scenario["direction_difference"]["runtime_ranking_changed"] is False
        assert scenario["legacy_formula"]["direction_formula"].startswith("sum(item.score")

    boosted = _scenario(data, "S08_plan_best_boost")
    assert boosted["direction_difference"]["legacy_top"] == "Nord-Est"
    assert boosted["legacy_formula"]["selected_direction"] == "Nord-Est"
    globular = _row(boosted, "globular_cluster")
    assert globular["legacy"]["sky_compass_target"]["components"]["in_plan_bonus"] == 42
    assert globular["legacy"]["sky_compass_target"]["components"]["best_object_bonus"] == 58


def test_report_marks_legacy_unavailable_components_without_fabricating_breakdowns() -> None:
    data = generate_report_data()
    baseline = _scenario(data, "S01_dark_sky")
    galaxy = _row(baseline, "galaxy")
    legacy = galaxy["legacy"]["sky_compass_target"]

    assert legacy["formula"] == "item.score + in_plan_bonus + best_object_bonus + target_presence_bonus"
    assert "intrinsic_target_quality:not_exposed_separately" in legacy["unavailable_components"]
    assert "observation_environment:not_exposed" in legacy["unavailable_components"]
    assert "upstream_score_breakdown:not_available_from_sky_compass_candidate" in legacy["unavailable_components"]
    assert legacy["ownership_mixing"]["direction_concentration"]["mixed_into_direction_score"] is True


def test_weather_session_and_equipment_ownership_are_separated_in_report_data() -> None:
    data = generate_report_data()
    good = _scenario(data, "S01_dark_sky")
    poor = _scenario(data, "S04_poor_weather")
    blocked = _scenario(data, "S05_blocked_session")
    small = _scenario(data, "S06_small_equipment")
    large = _scenario(data, "S07_large_equipment")

    for target_id in ("jupiter", "moon", "galaxy", "diffuse_nebula", "open_cluster", "globular_cluster"):
        assert _observable(_row(good, target_id)) == _observable(_row(poor, target_id))
        assert _observable(_row(good, target_id)) == _observable(_row(blocked, target_id))
        assert _practical(_row(good, target_id)) == _practical(_row(poor, target_id))
        assert _practical(_row(good, target_id)) == _practical(_row(blocked, target_id))
        assert _observable(_row(small, target_id)) == _observable(_row(large, target_id))

    assert _practical(_row(small, "galaxy")) != _practical(_row(large, "galaxy"))
    blocked_session = _row(blocked, "galaxy")["nsom"]["session_viability"]
    assert blocked_session["state"] == "blocked"
    assert blocked_session["value"] == 0.0
    assert blocked_session["score_factor"] is False
    assert blocked_session["score_effect_on_observable_target_value"] == 0.0
    assert blocked_session["score_effect_on_practical_target_value"] == 0.0


def test_bright_sky_affects_nsom_sky_reference_not_legacy_formula() -> None:
    data = generate_report_data()
    dark = _scenario(data, "S01_dark_sky")
    bright = _scenario(data, "S02_bright_moon")
    polluted = _scenario(data, "S03_high_light_pollution")

    assert _legacy_contribution(_row(bright, "galaxy")) == _legacy_contribution(_row(dark, "galaxy"))
    assert _legacy_contribution(_row(polluted, "galaxy")) == _legacy_contribution(_row(dark, "galaxy"))
    assert _environment(_row(bright, "galaxy"))["lunar_sky_background"] < _environment(_row(dark, "galaxy"))[
        "lunar_sky_background"
    ]
    assert _environment(_row(polluted, "galaxy"))["static_sky_background"] < _environment(_row(dark, "galaxy"))[
        "static_sky_background"
    ]
    assert _environment(_row(bright, "jupiter"))["lunar_sky_background"] == 1.0
    assert _environment(_row(polluted, "jupiter"))["static_sky_background"] == 1.0


def test_confidence_remains_metadata_only_in_report() -> None:
    data = generate_report_data()
    control = data["confidence_control"]

    assert control["low_legacy_top"] == control["high_legacy_top"]
    assert control["low_observable_top"] == control["high_observable_top"]
    assert control["observable_delta"] == 0.0
    assert control["practical_delta"] == 0.0
    assert control["score_factor"] is False
    assert control["score_effect"] == 0.0

    for row in _rows(data):
        confidence = row["nsom"]["recommendation_confidence"]
        assert confidence["role"] == "metadata_only"
        assert confidence["score_factor"] is False
        assert confidence["score_effect"] == 0.0


def test_sky_compass_report_is_not_wired_into_runtime_or_qml() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    app_controller = Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))
    controller_text = app_controller.read_text(encoding="utf-8")

    assert "sky_compass_nsom_comparison_report" not in qml_text
    assert "SKY_COMPASS_NSOM_COMPARISON_REPORT" not in qml_text
    assert "sky_compass_nsom_comparison_report" not in controller_text
    assert "SKY_COMPASS_NSOM_COMPARISON_REPORT" not in controller_text
    assert str(REPORT_PATH).replace("\\", "/") == "docs/SKY_COMPASS_NSOM_COMPARISON_REPORT.md"


def test_checked_in_sky_compass_markdown_report_exists() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Sky Compass NSOM Comparison Report" in text
    assert "8 deterministic scenarios" in text
    assert "Sky Compass is not a pure target-value ranker" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def _scenario(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(scenario for scenario in data["scenarios"] if scenario["scenario_id"] == scenario_id)


def _row(scenario: dict[str, object], target_id: str) -> dict[str, object]:
    return next(row for row in scenario["rows"] if row["target"]["object_id"] == target_id)


def _rows(data: dict[str, object]) -> list[dict[str, object]]:
    return [row for scenario in data["scenarios"] for row in scenario["rows"]]


def _environment(row: dict[str, object]) -> dict[str, object]:
    return row["nsom"]["observation_environment"]


def _observable(row: dict[str, object]) -> float:
    return float(row["nsom"]["observable_target_value"]["value"])


def _practical(row: dict[str, object]) -> float:
    return float(row["nsom"]["practical_target_value"]["value"])


def _legacy_contribution(row: dict[str, object]) -> float:
    return float(row["legacy"]["sky_compass_target"]["direction_score_contribution"])
