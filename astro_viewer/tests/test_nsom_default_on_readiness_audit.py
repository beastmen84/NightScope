from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.night_planner_service import (
    NSOM_PLANNER_SCORING_ENABLED,
    NightPlannerService,
)
from astro_viewer.tools.nsom_default_on_readiness_audit import (
    READINESS_AUDIT_PATH,
    generate_readiness_audit_data,
    render_markdown_report,
)


def test_readiness_audit_is_strict_json_and_developer_only() -> None:
    data = generate_readiness_audit_data()

    json.dumps(data, sort_keys=True, allow_nan=False)

    assert data["metadata"]["developer_only"] is True
    assert data["metadata"]["runtime_writes"] is False
    assert data["metadata"]["automatic_logging"] is False
    assert data["metadata"]["network"] is False
    assert data["metadata"]["qml_exposure"] is False
    assert data["metadata"]["nsom_planner_scoring_enabled"] is False


def test_readiness_verdict_allows_next_pr_but_does_not_enable_now() -> None:
    data = generate_readiness_audit_data()

    assert data["readiness"]["verdict"] == "ready_for_default_on_switch_pr"
    assert data["readiness"]["ready_for_default_on_switch_pr"] is True
    assert data["readiness"]["ready_to_enable_in_this_commit"] is False
    assert data["readiness"]["recommendation"] == "ready_for_default_on_switch_pr"
    assert NSOM_PLANNER_SCORING_ENABLED is False


def test_no_calibration_or_policy_blockers_remain() -> None:
    data = generate_readiness_audit_data()

    assert data["blockers"]["default_on_blockers"] == []
    assert data["blockers"]["needs_calibration"] == []
    assert data["blockers"]["needs_policy_decision"] == []
    assert data["blockers"]["unlinked_review_or_policy_rows"] == []


def test_accepted_and_deferred_decisions_are_documented() -> None:
    data = generate_readiness_audit_data()

    assert data["decisions"]["accepted_decisions_documented"] is True
    assert data["decisions"]["deferred_decisions_documented"] is True
    assert data["decisions"]["deferred_non_blocking"] is True
    assert set(data["decisions"]["deferred_decision_ids"]) == {
        "medium-equipment-q-target-review-band",
        "moon-planet-favouring-category-factor",
    }
    assert set(data["decisions"]["deferred_possible_calibration_issues"]) == {
        "moon-planet-favouring-category-factor"
    }

    remaining = {
        item["decision_id"]: item
        for item in data["remaining_non_blocking_review_items"]
    }
    assert set(remaining) == {
        "medium-equipment-q-target-review-band",
        "moon-planet-favouring-category-factor",
    }
    assert all(item["decision_reason"] for item in remaining.values())


def test_runtime_safety_checks_remain_green() -> None:
    data = generate_readiness_audit_data()

    assert data["runtime_safety"] == {
        "flag_default_off": True,
        "legacy_planner_preserved_by_default_flag": True,
        "qml_exposure_absent": True,
        "runtime_report_imports_absent": True,
        "tooling_developer_only": True,
        "tooling_has_no_runtime_writes": True,
        "tooling_has_no_automatic_logging": True,
        "tooling_has_no_network": True,
        "tooling_has_no_qml_exposure": True,
    }
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_source_tooling_remains_developer_only() -> None:
    data = generate_readiness_audit_data()

    assert set(data["tooling_checks"]) == {
        "comparison_report",
        "mathematical_trace_report",
        "calibration_decision_log",
    }
    for check in data["tooling_checks"].values():
        assert check == {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "nsom_planner_scoring_enabled": False,
        }


def test_readiness_report_generation_is_not_wired_into_runtime_or_qml() -> None:
    data = generate_readiness_audit_data()

    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["metadata"]["audit_report_path"] == (
        "docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md"
    )


def test_flag_off_runtime_planner_remains_legacy_with_readiness_audit_present() -> None:
    class FailingNsomService:
        def opportunity(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("NSOM planner path should stay disabled.")

        def score(self, opportunity):  # noqa: ANN001
            raise AssertionError("NSOM planner path should stay disabled.")

    objects = [
        _target("planet", "Pianeta", 84, magnitude="-1.7", best_time="21:00"),
        _target("galaxy", "Galaxy", 83, magnitude="8.5", best_time="21:30"),
        _target("open", "Open Cluster", 82, magnitude="5.2", best_time="22:00"),
    ]
    weather = _weather(85)
    scores = _scores()
    sky_quality = _sky_quality()
    telescope = _telescope()
    moon = _moon(10)

    legacy_plan = NightPlannerService().plan(
        objects,
        weather,
        scores,
        sky_quality,
        telescope,
        moon,
    )
    flag_off_plan = NightPlannerService(nsom_scoring_service=FailingNsomService()).plan(
        objects,
        weather,
        scores,
        sky_quality,
        telescope,
        moon,
    )

    assert _plan_summary(flag_off_plan) == _plan_summary(legacy_plan)


def test_checked_in_readiness_audit_report_exists() -> None:
    report = Path(__file__).parents[2] / READINESS_AUDIT_PATH

    assert report.exists()
    assert report.read_text(encoding="utf-8").rstrip("\n") == render_markdown_report().rstrip(
        "\n"
    )


def _target(
    object_id: str,
    object_type: str,
    score: int,
    *,
    magnitude: str = "8.0",
    best_time: str = "21:00",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.title(),
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time=best_time,
        observing_window=f"{best_time} - 02:00",
        notes="Fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty="Media",
        recommended_setup_type="telescope",
    )


def _weather(score: int) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=10,
        precipitation_probability=0,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _scores() -> AdvancedObservingScores:
    return AdvancedObservingScores(
        planetary_score=85,
        deep_sky_score=88,
        planetary_label="Good",
        deep_sky_label="Good",
        explanation="Fixture",
    )


def _sky_quality() -> SkyQuality:
    return SkyQuality(
        bortle_class=3,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="Fixture",
        description="Fixture",
        viirs_radiance=2,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="18:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
        phase_angle=0.0,
    )


def _telescope() -> Telescope:
    return Telescope(
        id="test-scope",
        name="Test Scope",
        aperture_mm=127,
        focal_length_mm=1500,
        optical_type="Mak",
        mount="",
    )


def _plan_summary(plan):
    return [(item.object_id, item.score, item.time_label) for item in plan]
