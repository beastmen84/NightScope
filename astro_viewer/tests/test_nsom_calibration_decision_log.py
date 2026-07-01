from __future__ import annotations

import json
from pathlib import Path

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.night_planner_service import (
    NSOM_PLANNER_SCORING_ENABLED,
    NightPlannerService,
)
from astro_viewer.tools.nsom_calibration_decision_log import (
    DECISION_LOG_PATH,
    DECISION_STATUSES,
    generate_decision_log_data,
    render_markdown_report,
)


def test_decision_log_is_strict_json_and_developer_only() -> None:
    data = generate_decision_log_data()

    json.dumps(data, sort_keys=True, allow_nan=False)

    assert data["metadata"]["developer_only"] is True
    assert data["metadata"]["nsom_planner_scoring_enabled"] is False
    assert tuple(data["metadata"]["decision_statuses"]) == DECISION_STATUSES
    assert data["metadata"]["runtime_writes"] is False
    assert data["metadata"]["automatic_logging"] is False
    assert data["metadata"]["network"] is False
    assert data["metadata"]["qml_exposure"] is False


def test_decision_log_covers_all_warning_rows_and_links_review_rows() -> None:
    data = generate_decision_log_data()

    assert data["summary"]["warning_rows_covered"] is True
    assert data["summary"]["review_rows_linked"] is True
    assert data["summary"]["policy_rows_linked"] is True
    assert data["summary"]["unlinked_rows"] == []
    assert data["warning_rows"]
    assert data["review_rows"]
    assert data["policy_rows"]

    for scenario_id in (*data["warning_rows"], *data["review_rows"], *data["policy_rows"]):
        assert data["row_decisions"][scenario_id]


def test_decision_statuses_and_expected_focus_cases_are_present() -> None:
    data = generate_decision_log_data()
    decisions = {decision["decision_id"]: decision for decision in data["decisions"]}

    assert decisions["blocked-session-hard-block-policy"]["decision_status"] == "accepted"
    assert decisions["blocked-session-hard-block-policy"][
        "blocked_session_policy_decision_placeholder"
    ] is False
    assert decisions["invisible-target-non-actionable-policy"]["decision_status"] == "accepted"
    assert decisions["missing-window-policy"]["decision_status"] == "accepted"
    assert decisions["small-equipment-planet-q-target"]["decision_status"] == "accepted"
    assert decisions["open-cluster-recurring-demotion"]["decision_status"] == (
        "accepted"
    )
    assert decisions["deep-sky-favouring-planet-review-row"]["decision_status"] == (
        "accepted"
    )
    assert decisions["globular-large-telescope-promotion"]["decision_status"] == "accepted"

    assert "blocked-session-hard-block-policy" in data["row_decisions"]["G09:planet"]
    assert "invisible-target-non-actionable-policy" in data["row_decisions"]["G20:moon"]
    assert "missing-window-policy" in data["row_decisions"]["G19:planet"]
    assert "small-equipment-planet-q-target" in data["row_decisions"]["G10:planet"]
    assert "small-equipment-planet-q-target" in data["row_decisions"]["G11:planet"]
    assert "globular-large-telescope-promotion" in data["row_decisions"][
        "G15:globular_cluster"
    ]
    assert "open-cluster-recurring-demotion" in data["row_decisions"]["G15:open_cluster"]
    assert "deep-sky-favouring-planet-review-row" in data["row_decisions"]["G15:planet"]


def test_accepted_differences_do_not_become_tuning_requirements() -> None:
    data = generate_decision_log_data()
    decisions = {decision["decision_id"]: decision for decision in data["decisions"]}

    accepted = [
        decision
        for decision in decisions.values()
        if decision["decision_status"] == "accepted"
    ]

    assert accepted
    assert all(decision["requires_tuning"] is False for decision in accepted)
    assert all(decision["blocks_default_on_work"] is False for decision in accepted)
    assert set(data["summary"]["accepted_without_tuning"]) == {
        "blocked-session-hard-block-policy",
        "invisible-target-non-actionable-policy",
        "small-equipment-planet-q-target",
        "open-cluster-recurring-demotion",
        "globular-large-telescope-promotion",
        "deep-sky-favouring-planet-review-row",
        "missing-window-policy",
    }


def test_policy_decisions_are_resolved_and_not_default_on_blockers() -> None:
    data = generate_decision_log_data()

    assert data["summary"]["unresolved_policy_decisions"] == []
    assert data["summary"]["remaining_policy_blockers"] == []
    assert data["summary"]["default_on_blockers"] == []
    assert "blocked-session-hard-block-policy" not in data["summary"]["default_on_blockers"]
    assert "invisible-target-non-actionable-policy" not in data["summary"]["default_on_blockers"]
    assert "missing-window-policy" not in data["summary"]["default_on_blockers"]


def test_confidence_remains_score_neutral_in_decision_log() -> None:
    data = generate_decision_log_data()
    confidence = data["confidence_control"]

    assert confidence["low_confidence_value"] < confidence["high_confidence_value"]
    assert confidence["low_confidence_score"] == pytest.approx(
        confidence["high_confidence_score"]
    )
    assert confidence["score_delta"] == pytest.approx(0.0)
    assert data["summary"]["confidence_score_delta"] == pytest.approx(0.0)


def test_decision_log_markdown_contains_required_sections() -> None:
    markdown = render_markdown_report()

    assert "# NSOM Calibration Decision Log" in markdown
    assert "## Decision Status Counts" in markdown
    assert "## Decision Entries" in markdown
    assert "## Warning And Review Row Links" in markdown
    assert "## Resolved Opportunity Policies" in markdown
    assert "blocked-session-hard-block-policy" in markdown
    assert "small-equipment-planet-q-target" in markdown


def test_decision_log_generation_is_not_wired_into_runtime_or_qml() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    runtime_roots = [
        Path(__file__).parents[1] / "app" / "viewmodels",
        Path(__file__).parents[1] / "app" / "services",
    ]
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in runtime_roots
        for path in root.rglob("*.py")
    )

    assert NSOM_PLANNER_SCORING_ENABLED is False
    assert "nsom_calibration_decision_log" not in qml_text
    assert "NSOM_CALIBRATION_DECISION_LOG" not in qml_text
    assert "nsom_calibration_decision_log" not in runtime_text


def test_flag_off_runtime_planner_remains_unchanged_with_decision_log_present() -> None:
    class FailingNsomService:
        def opportunity(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("NSOM planner path should stay disabled.")

        def score(self, opportunity):  # noqa: ANN001
            raise AssertionError("NSOM planner path should stay disabled.")

    objects = [
        _target("planet", "Pianeta", 84, magnitude="-1.7", best_time="21:00"),
        _target("galaxy", "Galaxy", 83, magnitude="8.5", best_time="21:30"),
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


def test_non_actionable_policy_metadata_does_not_change_legacy_planner_output() -> None:
    class FailingNsomService:
        def opportunity(self, *args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("NSOM planner path should stay disabled.")

        def score(self, opportunity):  # noqa: ANN001
            raise AssertionError("NSOM planner path should stay disabled.")

    objects = [
        _target(
            "missing",
            "Galaxy",
            83,
            best_time="Non disponibile",
            observing_window="Non disponibile",
        ),
        _target(
            "invisible",
            "Galaxy",
            82,
            best_time="Non disponibile",
            observing_window="Non disponibile",
            visible=False,
            max_altitude="sotto orizzonte",
        ),
        _target("normal", "Pianeta", 84, magnitude="-1.7", best_time="21:00"),
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
    blocked_legacy_plan = NightPlannerService().plan(
        objects,
        _weather(10, cloud_cover=90, precipitation=80),
        scores,
        sky_quality,
        telescope,
        moon,
    )
    blocked_flag_off_plan = NightPlannerService(
        nsom_scoring_service=FailingNsomService()
    ).plan(
        objects,
        _weather(10, cloud_cover=90, precipitation=80),
        scores,
        sky_quality,
        telescope,
        moon,
    )

    assert _plan_summary(flag_off_plan) == _plan_summary(legacy_plan)
    assert blocked_flag_off_plan == blocked_legacy_plan == []


def test_checked_in_decision_log_report_exists() -> None:
    report = Path(__file__).parents[2] / DECISION_LOG_PATH

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
    observing_window: str | None = None,
    max_altitude: str = "45 gradi",
    visible: bool = True,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.title(),
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude=max_altitude,
        direction="Sud",
        best_time=best_time,
        observing_window=observing_window or f"{best_time} - 02:00",
        notes="Fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=visible,
        score=score,
        score_label="Fixture",
        difficulty="Media",
        recommended_setup_type="telescope",
    )


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation,
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
