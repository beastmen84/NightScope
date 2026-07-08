from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.equipment_nsom_comparison_report import (
    REPORT_PATH,
    generate_report_data,
    render_markdown_report,
)


def test_equipment_report_data_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_report_data()
    second = generate_report_data()

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
    assert first["metadata"]["equipment_recommendations_changed"] is False
    assert first["metadata"]["scenario_count"] == 5
    assert first["metadata"]["candidate_row_count"] > 5


def test_equipment_report_exposes_legacy_formula_and_nsom_observer_fields() -> None:
    data = generate_report_data()
    scenario = _scenario(data, "E01_planet_mixed_equipment")
    row = scenario["candidates"][0]

    assert scenario["legacy_formula"]["formula"].startswith("angular_scale + magnification")
    assert {"angular_scale", "magnification", "exit_pupil", "light_gathering"} <= set(
        row["legacy"]["components"]
    )
    assert "observer_capability" in row["nsom"]
    assert "q_target" in row["nsom"]["observer_capability"]
    assert row["nsom"]["observer_capability"]["target_class_weighting_profile"]
    assert row["nsom"]["ownership"]["confidence_effects"]["score_effect"] == 0.0


def test_equipment_report_marks_legacy_ownership_mixing_without_runtime_change() -> None:
    data = generate_report_data()
    galaxy = _scenario(data, "E03_galaxy_high_light_pollution")
    row = galaxy["candidates"][0]
    legacy = row["legacy"]

    assert legacy["ownership_mixing"]["sky_quality"]["mixed_into_equipment_score"] is True
    assert legacy["ownership_mixing"]["seeing"]["mixed_into_equipment_score"] is True
    assert "q_target:not_part_of_equipment_service_formula" in legacy["unavailable_components"]
    assert row["nsom"]["ownership"]["sky_quality_effects"]["used_in_observer_capability"] is False
    assert row["nsom"]["ownership"]["seeing_effects"]["used_in_observer_capability"] is False


def test_equipment_report_has_no_runtime_or_qml_wiring() -> None:
    app_controller = (Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).parents[1] / "app" / "ui").rglob("*.qml")
    )

    assert "EquipmentNsomComparisonService" not in app_controller
    assert "equipment_nsom_comparison" not in app_controller
    assert "EQUIPMENT_NSOM_COMPARISON_REPORT" not in app_controller
    assert "EquipmentNsomComparisonService" not in qml_text
    assert "equipment_nsom_comparison" not in qml_text
    assert "EQUIPMENT_NSOM_COMPARISON_REPORT" not in qml_text


def test_checked_in_equipment_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# Equipment NSOM Comparison Report" in text
    assert "Equipment/ObserverCapability" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def _scenario(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(scenario for scenario in data["scenarios"] if scenario["scenario_id"] == scenario_id)
