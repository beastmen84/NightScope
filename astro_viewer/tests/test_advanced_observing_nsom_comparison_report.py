from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.advanced_observing_nsom_comparison_report import (
    REPORT_PATH,
    generate_report_data,
    render_markdown_report,
)


def test_advanced_observing_report_data_is_deterministic_and_strict_json() -> None:
    first = generate_report_data()
    second = generate_report_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"]["developer_only"] is True
    assert first["metadata"]["runtime_writes"] is False
    assert first["metadata"]["scenario_count"] == 8
    assert first["metadata"]["category_row_count"] == 16
    assert [scenario["scenario_id"] for scenario in first["scenarios"]] == [
        "A01_good_session",
        "A02_poor_weather",
        "A03_blocked_session",
        "A04_bright_moon",
        "A05_high_light_pollution",
        "A06_poor_seeing",
        "A07_poor_transparency",
        "A08_low_confidence",
    ]


def test_report_exposes_legacy_advanced_formula_components() -> None:
    data = generate_report_data()
    good = _scenario(data, "A01_good_session")

    planetary = good["legacy"]["planetary"]
    deep_sky = good["legacy"]["deep_sky"]

    assert planetary["formula"].startswith("round(weather.score_value*0.36")
    assert deep_sky["formula"].startswith("round(weather.score_value*0.34")
    assert planetary["components"]["weather"]["weight"] == 0.36
    assert planetary["components"]["seeing"]["weight"] == 0.42
    assert planetary["components"]["wind"]["weight"] == 0.12
    assert planetary["components"]["moon"]["weight"] == 0.10
    assert deep_sky["components"]["weather"]["weight"] == 0.34
    assert deep_sky["components"]["transparency"]["weight"] == 0.30
    assert deep_sky["components"]["light_pollution"]["weight"] == 0.24
    assert deep_sky["components"]["moon"]["weight"] == 0.12
    assert "observer_capability:not_part_of_advanced_scores" in deep_sky["unavailable_components"]


def test_report_keeps_nsom_reference_projection_separate_from_score_parity() -> None:
    data = generate_report_data()

    for scenario in data["scenarios"]:
        assert scenario["metadata"]["score_parity_expected"] is False
        assert scenario["metadata"]["reference_only"] is True
        assert scenario["nsom"]["planetary_reference"]["reference_only"] is True
        assert scenario["nsom"]["deep_sky_reference_summary"]["reference_only"] is True
        assert scenario["nsom"]["session_viability"]["role"] == "session_metadata"
        assert scenario["nsom"]["recommendation_confidence"]["role"] == "metadata_only"
        assert scenario["nsom"]["recommendation_confidence"]["score_factor"] is False
        assert scenario["nsom"]["recommendation_confidence"]["score_effect"] == 0.0


def test_bright_moon_and_light_pollution_behaviour_is_visible_in_report() -> None:
    data = generate_report_data()
    dark = _scenario(data, "A01_good_session")
    bright_moon = _scenario(data, "A04_bright_moon")
    high_lp = _scenario(data, "A05_high_light_pollution")

    assert _planet_env(bright_moon)["lunar_sky_background"] == 1.0
    assert _deep_sky_average(bright_moon) < _deep_sky_average(dark)
    assert bright_moon["legacy"]["deep_sky"]["score"] < dark["legacy"]["deep_sky"]["score"]

    assert _planet_env(high_lp)["static_sky_background"] == 1.0
    assert _deep_sky_average(high_lp) < _deep_sky_average(dark)
    assert high_lp["legacy"]["deep_sky"]["score"] < dark["legacy"]["deep_sky"]["score"]


def test_weather_seeing_transparency_and_confidence_controls_are_characterized() -> None:
    data = generate_report_data()
    good = _scenario(data, "A01_good_session")
    poor_weather = _scenario(data, "A02_poor_weather")
    blocked = _scenario(data, "A03_blocked_session")
    poor_seeing = _scenario(data, "A06_poor_seeing")
    poor_transparency = _scenario(data, "A07_poor_transparency")
    low_confidence = _scenario(data, "A08_low_confidence")

    assert poor_weather["legacy"]["planetary"]["score"] < good["legacy"]["planetary"]["score"]
    assert poor_weather["legacy"]["deep_sky"]["score"] < good["legacy"]["deep_sky"]["score"]
    assert _planet_observable(poor_weather) == _planet_observable(good)
    assert _deep_sky_average(poor_weather) == _deep_sky_average(good)

    assert blocked["nsom"]["session_viability"]["state"] == "blocked"
    assert blocked["nsom"]["session_viability"]["value"] == 0.0
    assert _planet_observable(blocked) == _planet_observable(good)

    assert poor_seeing["legacy"]["planetary"]["score"] < good["legacy"]["planetary"]["score"]
    assert _planet_observable(poor_seeing) < _planet_observable(good)
    assert poor_transparency["legacy"]["deep_sky"]["score"] < good["legacy"]["deep_sky"]["score"]
    assert _deep_sky_average(poor_transparency) < _deep_sky_average(good)

    assert low_confidence["nsom"]["recommendation_confidence"]["value"] < good["nsom"][
        "recommendation_confidence"
    ]["value"]
    assert _planet_observable(low_confidence) == _planet_observable(good)
    assert _deep_sky_average(low_confidence) == _deep_sky_average(good)


def test_report_semantic_recommendation_and_summary_are_review_oriented() -> None:
    data = generate_report_data()
    semantic = data["semantic_recommendation"]
    summary = data["summary"]

    assert semantic["classification"] == "presentation diagnostic / category quality surface"
    assert semantic["recommended_future_nsom_concept"] == (
        "NSOM-derived category diagnostics with separate session policy"
    )
    assert semantic["runtime_score_replacement_ready"] is False
    assert semantic["confidence_score_effect"] == 0.0
    assert any("weather/session" in item for item in summary["main_mismatches"])
    assert all(item.endswith(("passed", "review")) for item in summary["nsom_behaviour_checks"])


def test_advanced_observing_report_is_not_wired_into_runtime_or_qml() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    app_controller = Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))
    controller_text = app_controller.read_text(encoding="utf-8")

    assert "advanced_observing_nsom_comparison_report" not in qml_text
    assert "ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT" not in qml_text
    assert "advanced_observing_nsom_comparison_report" not in controller_text
    assert "ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT" not in controller_text
    assert str(REPORT_PATH).replace("\\", "/") == (
        "docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md"
    )


def test_checked_in_advanced_observing_markdown_report_exists() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Advanced Observing NSOM Comparison Report" in text
    assert "8 deterministic scenarios" in text
    assert "Advanced Observing should be migrated" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def _scenario(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(scenario for scenario in data["scenarios"] if scenario["scenario_id"] == scenario_id)


def _planet_env(scenario: dict[str, object]) -> dict[str, object]:
    return scenario["nsom"]["planetary_reference"]["observation_environment"]


def _planet_observable(scenario: dict[str, object]) -> float:
    return float(scenario["nsom"]["planetary_reference"]["observable_target_value"]["value"])


def _deep_sky_average(scenario: dict[str, object]) -> float:
    return float(scenario["nsom"]["deep_sky_reference_summary"]["average_observable_target_value"])
