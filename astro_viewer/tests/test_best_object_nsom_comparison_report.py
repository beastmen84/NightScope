from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.best_object_nsom_comparison_report import (
    REPORT_PATH,
    generate_report_data,
    render_markdown_report,
)


def test_best_object_report_data_is_deterministic_and_strict_json() -> None:
    first = generate_report_data()
    second = generate_report_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"]["developer_only"] is True
    assert first["metadata"]["scenario_count"] == 8
    assert first["metadata"]["row_count"] == 34
    assert [scenario["scenario_id"] for scenario in first["scenarios"]] == [
        "B01_good_session",
        "B02_poor_weather",
        "B03_blocked_session",
        "B04_bright_moon",
        "B05_high_light_pollution",
        "B06_small_equipment",
        "B07_large_equipment",
        "B08_mixed_planet_deep_sky",
    ]


def test_best_object_report_compares_legacy_observable_and_practical_orders() -> None:
    data = generate_report_data()

    for scenario in data["scenarios"]:
        assert scenario["legacy_best_object_order"]
        assert scenario["nsom_observable_order"]
        assert scenario["nsom_practical_order"]
        assert scenario["selection_difference"]["legacy_top"] == scenario["legacy_best_object_order"][0]
        assert scenario["selection_difference"]["nsom_observable_top"] == scenario["nsom_observable_order"][0]
        assert scenario["selection_difference"]["nsom_practical_top"] == scenario["nsom_practical_order"][0]

    mixed = _scenario(data, "B08_mixed_planet_deep_sky")
    assert {"jupiter", "moon", "galaxy", "diffuse_nebula", "open_cluster", "globular_cluster"} == {
        row["target"]["object_id"] for row in mixed["rows"]
    }
    assert mixed["axes"]["target_profile"] == "expanded_mixed"


def test_report_marks_legacy_unavailable_components_and_ownership_mixing() -> None:
    data = generate_report_data()
    good = _scenario(data, "B01_good_session")
    row = _row(good, "galaxy")
    legacy = row["legacy"]["best_object"]

    assert legacy["formula"] == "item.score * weather_factor * difficulty_factor"
    assert legacy["ownership_mixing"]["target_value"]["mixed_into_final_score"] is True
    assert legacy["ownership_mixing"]["weather_session"]["mixed_into_final_score"] is True
    assert legacy["ownership_mixing"]["difficulty"]["mixed_into_final_score"] is True
    assert "sky_background_component:not_part_of_best_object_formula" in legacy["unavailable_components"]
    assert "observer_capability_profile:not_part_of_best_object_formula" in legacy["unavailable_components"]
    assert "recommendation_confidence:not_part_of_best_object_formula" in legacy["unavailable_components"]


def test_report_exposes_session_viability_and_confidence_as_metadata() -> None:
    data = generate_report_data()
    good = _scenario(data, "B01_good_session")
    poor = _scenario(data, "B02_poor_weather")
    blocked = _scenario(data, "B03_blocked_session")

    for target_id in ("jupiter", "galaxy", "diffuse_nebula", "open_cluster"):
        assert _observable(_row(good, target_id)) == _observable(_row(poor, target_id))
        assert _practical(_row(good, target_id)) == _practical(_row(poor, target_id))
        assert _observable(_row(good, target_id)) == _observable(_row(blocked, target_id))
        assert _practical(_row(good, target_id)) == _practical(_row(blocked, target_id))

    blocked_session = _row(blocked, "galaxy")["nsom"]["session_viability"]
    assert blocked_session["state"] == "blocked"
    assert blocked_session["value"] == 0.0
    assert blocked_session["score_factor"] is False
    assert blocked_session["score_effect_on_observable_target_value"] == 0.0
    assert blocked_session["score_effect_on_practical_target_value"] == 0.0

    mixed = _scenario(data, "B08_mixed_planet_deep_sky")
    confidence = _row(mixed, "galaxy")["nsom"]["recommendation_confidence"]
    assert confidence["role"] == "metadata_only"
    assert confidence["score_factor"] is False
    assert confidence["score_effect"] == 0.0


def test_report_identifies_best_object_semantic_target() -> None:
    data = generate_report_data()
    semantic = data["semantic_recommendation"]

    assert semantic["classification"] == "Home-specific hybrid"
    assert semantic["recommended_future_nsom_concept"] == (
        "ObservationOpportunity with Home-specific presentation policy"
    )
    assert semantic["observable_target_value_alone_is_enough"] is False
    assert semantic["practical_target_value_alone_is_enough"] is False
    assert semantic["needs_session_policy"] is True
    assert semantic["confidence_score_effect"] == 0.0


def test_best_object_report_is_not_wired_into_runtime_or_qml() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    app_controller = Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))
    controller_text = app_controller.read_text(encoding="utf-8")

    assert "best_object_nsom_comparison_report" not in qml_text
    assert "BEST_OBJECT_NSOM_COMPARISON_REPORT" not in qml_text
    assert "best_object_nsom_comparison_report" not in controller_text
    assert "BEST_OBJECT_NSOM_COMPARISON_REPORT" not in controller_text
    assert str(REPORT_PATH).replace("\\", "/") == "docs/BEST_OBJECT_NSOM_COMPARISON_REPORT.md"


def test_checked_in_best_object_markdown_report_exists() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Best Object NSOM Comparison Report" in text
    assert "8 deterministic scenarios" in text
    assert "Semantic recommendation" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def _scenario(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(scenario for scenario in data["scenarios"] if scenario["scenario_id"] == scenario_id)


def _row(scenario: dict[str, object], target_id: str) -> dict[str, object]:
    return next(row for row in scenario["rows"] if row["target"]["object_id"] == target_id)


def _observable(row: dict[str, object]) -> float:
    return float(row["nsom"]["observable_target_value"]["value"])


def _practical(row: dict[str, object]) -> float:
    return float(row["nsom"]["practical_target_value"]["value"])
