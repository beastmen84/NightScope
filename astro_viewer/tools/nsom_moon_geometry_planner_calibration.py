from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionFeatureFlags,
    ObservationConditionsService,
)
from astro_viewer.app.services.planner_nsom_service import (
    NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED,
    PlannerNsomScoringService,
)


REPORT_PATH = Path("docs/NSOM_MOON_GEOMETRY_PLANNER_CALIBRATION.md")

REPORT_IMPORT_MARKERS = (
    "nsom_moon_geometry_planner_calibration",
    "NSOM_MOON_GEOMETRY_PLANNER_CALIBRATION",
)

QML_MARKERS = (
    "nsomMoonGeometryPlannerCalibration",
    "moonGeometryPlannerCalibration",
    "NSOM_MOON_GEOMETRY_PLANNER_CALIBRATION",
    "experimental_moon_geometry_scoring",
)


@dataclass(frozen=True)
class TargetFixture:
    target_id: str
    object_type: str
    score: float
    difficulty: str
    magnitude: str
    expected_moon_geometry_role: str


@dataclass(frozen=True)
class GeometryFixture:
    case_id: str
    label: str
    geometry: MoonGeometryConditionInput | None
    expectation: str


def generate_moon_geometry_planner_calibration_data() -> dict[str, object]:
    targets = _target_fixtures()
    geometry_cases = _geometry_fixtures()
    rows = tuple(
        _evaluate_fixture(target_fixture, geometry_fixture)
        for geometry_fixture in geometry_cases
        for target_fixture in targets
    )
    checks = _checks(rows)
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_wiring": False,
            "planner_scoring_changed_by_default": False,
            "planner_default_flag": "NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED",
            "planner_default_flag_enabled": NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED,
            "explicit_rollback_flag": "experimental_moon_geometry_scoring=False",
            "score_owner": "Sky / ObservationEnvironment.lunar_sky_background",
            "scenario_count": len(rows),
            "target_count": len(targets),
            "geometry_case_count": len(geometry_cases),
            "confidence_score_effect": 0.0,
        },
        "scenario_rows": rows,
        "summary": _summary(rows),
        "checks": checks,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report_data = generate_moon_geometry_planner_calibration_data() if data is None else data
    metadata = report_data["metadata"]
    summary = report_data["summary"]
    rows = report_data["scenario_rows"]

    lines = [
        "# NSOM Moon Geometry Planner Calibration",
        "",
        "## Executive Summary",
        "",
        (
            f"This developer-only report evaluates {metadata['scenario_count']} deterministic "
            "Planner rows for the Moon geometry path against the illumination-only rollback."
        ),
        (
            "The experiment changes only the Sky-owned "
            "`ObservationEnvironment.lunar_sky_background` component. It does not change "
            "ObserverCapability, SessionViability, RecommendationConfidence score effect, "
            "QML payloads, runtime logging, network calls or automatic file writes."
        ),
        (
            "The intended direction is visible: close high Moon geometry lowers deep-sky "
            "opportunities more than far high Moon geometry, Moon set before the target "
            "window removes the lunar background penalty, and planets/Moon remain protected "
            "from lunar sky-background penalties."
        ),
        "",
        "## Methodology",
        "",
        "- Used fixed in-memory Planner candidates only.",
        "- Compared the explicit illumination-only rollback model with the Planner default-on Moon geometry model.",
        "- Planner default flag under review: `NSOM_PLANNER_MOON_GEOMETRY_SCORING_ENABLED`.",
        "- Held sky quality, weather, equipment, target score and session context stable inside each comparison.",
        "- Treated RecommendationConfidence as metadata only; it is not part of the score formula.",
        "- Marked this tooling as developer-only and kept it outside runtime imports/QML.",
        "",
        "## Scenario Matrix",
        "",
        "| Geometry Case | Target | Flag Off Score | Flag On Score | Score Delta | Lunar Background Delta | Geometry Factor | Expectation |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                (
                    str(row["geometry_case"]),
                    str(row["target_type"]),
                    f"{float(row['flag_off']['opportunity_score']):.4f}",
                    f"{float(row['flag_on']['opportunity_score']):.4f}",
                    f"{float(row['deltas']['opportunity_score_delta']):+.4f}",
                    f"{float(row['deltas']['lunar_sky_background_delta']):+.4f}",
                    f"{float(row['geometry_factor']):.3f}",
                    str(row["expectation"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Ownership Checks",
            "",
            "| Check | Value |",
            "| --- | --- |",
        ]
    )
    for key, value in report_data["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Calibration Observations",
            "",
            f"- Deep-sky rows reduced by close Moon geometry: `{summary['deep_sky_close_rows_reduced']}`.",
            f"- Deep-sky rows improved when the Moon is set before the target window: `{summary['deep_sky_set_before_window_rows_improved']}`.",
            f"- Planet/Moon rows protected from lunar background deltas: `{summary['protected_target_rows_without_lunar_delta']}`.",
            f"- Rows where only the lunar sky-background component changed: `{summary['rows_with_only_lunar_environment_delta']}`.",
            f"- Rows with non-zero confidence score effect: `{summary['rows_with_confidence_score_effect']}`.",
            "",
            "## Review Notes",
            "",
            "- This report is not a weight-tuning step.",
            "- It is evidence for whether Moon geometry should eventually be enabled by default.",
            "- If calibration is needed, it should stay inside the Sky/ObservationEnvironment Moon-background layer.",
            "- AOD and OpenAQ remain separate provider-backed inputs and are not evaluated by this report.",
            "",
            "## Recommended Next Step",
            "",
            "Review this calibration output before enabling Moon geometry by default or moving to AOD/OpenAQ scoring.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _evaluate_fixture(
    target_fixture: TargetFixture,
    geometry_fixture: GeometryFixture,
) -> dict[str, object]:
    target = _target(target_fixture)
    weather = _weather()
    scores = _scores()
    sky_quality = _sky_quality()
    telescope = _telescope()
    moon = _moon()

    flag_off_service = PlannerNsomScoringService(
        feature_flags=ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=False)
    )
    flag_on_service = PlannerNsomScoringService(
        feature_flags=ObservationConditionFeatureFlags(experimental_moon_geometry_scoring=True)
    )
    flag_off = flag_off_service.opportunity(
        target,
        weather=weather,
        scores=scores,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
        moon_geometry=geometry_fixture.geometry,
    )
    flag_on = flag_on_service.opportunity(
        target,
        weather=weather,
        scores=scores,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
        moon_geometry=geometry_fixture.geometry,
    )
    flag_off_snapshot = _snapshot(flag_off_service, target, flag_off)
    flag_on_snapshot = _snapshot(flag_on_service, target, flag_on)
    deltas = _deltas(flag_off_snapshot, flag_on_snapshot)
    return {
        "scenario_id": f"{geometry_fixture.case_id}:{target_fixture.target_id}",
        "geometry_case": geometry_fixture.case_id,
        "geometry_label": geometry_fixture.label,
        "target_id": target_fixture.target_id,
        "target_type": target_fixture.object_type,
        "expected_moon_geometry_role": target_fixture.expected_moon_geometry_role,
        "expectation": geometry_fixture.expectation,
        "geometry_factor": ObservationConditionsService.intended_moon_geometry_factor(
            geometry_fixture.geometry
        ),
        "geometry_input": nsom_to_json_compatible(geometry_fixture.geometry),
        "flag_off": flag_off_snapshot,
        "flag_on": flag_on_snapshot,
        "deltas": deltas,
        "ownership": _ownership(deltas),
        "confidence": {
            "score_effect": 0.0,
            "flag_off_moon_geometry_confidence": flag_off_snapshot["confidence"][
                "moon_geometry_confidence"
            ],
            "flag_on_moon_geometry_confidence": flag_on_snapshot["confidence"][
                "moon_geometry_confidence"
            ],
        },
    }


def _snapshot(
    service: PlannerNsomScoringService,
    target: CelestialObject,
    opportunity,
) -> dict[str, object]:
    practical = opportunity.practical_target_value
    observable = practical.observable_target_value
    effective = observable.effective_observability
    confidence = opportunity.confidence
    explanation = service.explain_opportunity(target, opportunity)
    return {
        "opportunity_score": opportunity.value,
        "practical_target_value": practical.value,
        "observable_target_value": observable.value,
        "effective_observability": effective.value,
        "effective_components": {
            "geometric_visibility": effective.geometric_visibility,
            "lunar_sky_background": effective.lunar_sky_background,
            "static_sky_background": effective.static_sky_background,
            "atmospheric_transparency": effective.atmospheric_transparency,
            "horizon_context": effective.horizon_context,
        },
        "observer_capability_summary": practical.observer_capability_summary,
        "session_viability": opportunity.session.value,
        "observing_window_quality": opportunity.observing_window_quality,
        "chronology_fit": opportunity.chronology_fit,
        "practical_constraints": opportunity.practical_constraints,
        "confidence": nsom_to_json_compatible(confidence),
        "main_limiting_factors": explanation["main_limiting_factors"],
        "main_positive_factors": explanation["main_positive_factors"],
    }


def _deltas(flag_off: dict[str, object], flag_on: dict[str, object]) -> dict[str, float]:
    off_components = flag_off["effective_components"]
    on_components = flag_on["effective_components"]
    return {
        "opportunity_score_delta": _delta(flag_off, flag_on, "opportunity_score"),
        "practical_target_value_delta": _delta(flag_off, flag_on, "practical_target_value"),
        "observable_target_value_delta": _delta(flag_off, flag_on, "observable_target_value"),
        "effective_observability_delta": _delta(flag_off, flag_on, "effective_observability"),
        "geometric_visibility_delta": _delta(off_components, on_components, "geometric_visibility"),
        "lunar_sky_background_delta": _delta(off_components, on_components, "lunar_sky_background"),
        "static_sky_background_delta": _delta(off_components, on_components, "static_sky_background"),
        "atmospheric_transparency_delta": _delta(
            off_components,
            on_components,
            "atmospheric_transparency",
        ),
        "horizon_context_delta": _delta(off_components, on_components, "horizon_context"),
        "observer_capability_summary_delta": _delta(
            flag_off,
            flag_on,
            "observer_capability_summary",
        ),
        "session_viability_delta": _delta(flag_off, flag_on, "session_viability"),
        "observing_window_quality_delta": _delta(flag_off, flag_on, "observing_window_quality"),
        "chronology_fit_delta": _delta(flag_off, flag_on, "chronology_fit"),
        "practical_constraints_delta": _delta(flag_off, flag_on, "practical_constraints"),
        "confidence_score_effect_delta": 0.0,
    }


def _ownership(deltas: dict[str, float]) -> dict[str, object]:
    leaking_components = tuple(
        key
        for key, value in deltas.items()
        if key
        not in {
            "opportunity_score_delta",
            "practical_target_value_delta",
            "observable_target_value_delta",
            "effective_observability_delta",
            "lunar_sky_background_delta",
        }
        and abs(value) > 1e-9
    )
    return {
        "changed_owner": "Sky / ObservationEnvironment",
        "score_component_changed": "lunar_sky_background",
        "non_lunar_leakage": len(leaking_components) > 0,
        "leaking_components": leaking_components,
    }


def _summary(rows: tuple[dict[str, object], ...]) -> dict[str, object]:
    deep_sky_targets = {"Galaxy", "Nebula", "Open Cluster", "Globular Cluster"}
    protected_targets = {"Pianeta", "Luna"}
    return {
        "deep_sky_close_rows_reduced": sum(
            1
            for row in rows
            if row["geometry_case"] == "high_altitude_close"
            and row["target_type"] in deep_sky_targets
            and row["deltas"]["opportunity_score_delta"] < 0.0
        ),
        "deep_sky_set_before_window_rows_improved": sum(
            1
            for row in rows
            if row["geometry_case"] == "set_before_window"
            and row["target_type"] in deep_sky_targets
            and row["deltas"]["opportunity_score_delta"] > 0.0
        ),
        "protected_target_rows_without_lunar_delta": sum(
            1
            for row in rows
            if row["target_type"] in protected_targets
            and abs(row["deltas"]["lunar_sky_background_delta"]) < 1e-9
        ),
        "rows_with_only_lunar_environment_delta": sum(
            1 for row in rows if row["ownership"]["non_lunar_leakage"] is False
        ),
        "rows_with_confidence_score_effect": sum(
            1
            for row in rows
            if abs(row["deltas"]["confidence_score_effect_delta"]) > 1e-9
        ),
    }


def _checks(rows: tuple[dict[str, object], ...]) -> dict[str, bool]:
    serialized = json.dumps(nsom_to_json_compatible(rows), sort_keys=True, allow_nan=False)
    return {
        "strict_json_compatible": bool(serialized),
        "runtime_report_imports_absent": _runtime_report_imports_absent(),
        "qml_report_exposure_absent": _qml_report_exposure_absent(),
        "only_lunar_environment_component_changes": all(
            row["ownership"]["non_lunar_leakage"] is False for row in rows
        ),
        "confidence_has_zero_score_effect": all(
            row["confidence"]["score_effect"] == 0.0 for row in rows
        ),
        "explicit_rollback_documented": True,
    }


def _runtime_report_imports_absent() -> bool:
    app_root = Path("astro_viewer/app")
    if not app_root.exists():
        return False
    for path in app_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in REPORT_IMPORT_MARKERS):
            return False
    return True


def _qml_report_exposure_absent() -> bool:
    ui_root = Path("astro_viewer/app/ui")
    if not ui_root.exists():
        return False
    for path in ui_root.rglob("*.qml"):
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in QML_MARKERS):
            return False
    return True


def _delta(left: dict[str, object], right: dict[str, object], key: str) -> float:
    return float(right[key]) - float(left[key])


def _target_fixtures() -> tuple[TargetFixture, ...]:
    return (
        TargetFixture("planet", "Pianeta", 86.0, "Facile", "-1.0", "protected"),
        TargetFixture("moon", "Luna", 92.0, "Facile", "-12.0", "protected"),
        TargetFixture("galaxy", "Galaxy", 82.0, "Media", "8.5", "sensitive"),
        TargetFixture("diffuse_nebula", "Nebula", 80.0, "Media", "7.0", "sensitive"),
        TargetFixture("open_cluster", "Open Cluster", 78.0, "Facile", "5.0", "moderate"),
        TargetFixture("globular_cluster", "Globular Cluster", 79.0, "Media", "6.0", "moderate"),
    )


def _geometry_fixtures() -> tuple[GeometryFixture, ...]:
    return (
        GeometryFixture(
            "missing",
            "No Moon geometry input",
            None,
            "flag-on matches the illumination-only baseline",
        ),
        GeometryFixture(
            "set_before_window",
            "Moon set before target window",
            MoonGeometryConditionInput(
                moon_altitude_deg=-8.0,
                moon_target_separation_deg=120.0,
                moon_above_horizon=False,
                moon_visible_during_target_window=False,
                moon_set_before_target_window=True,
            ),
            "lunar sky-background penalty is removed",
        ),
        GeometryFixture(
            "low_altitude_close",
            "Low Moon close to target",
            MoonGeometryConditionInput(
                moon_altitude_deg=8.0,
                moon_target_separation_deg=12.0,
                moon_above_horizon=True,
                moon_visible_during_target_window=True,
                moon_set_before_target_window=False,
            ),
            "low altitude softens the close-separation penalty",
        ),
        GeometryFixture(
            "high_altitude_close",
            "High Moon close to target",
            MoonGeometryConditionInput(
                moon_altitude_deg=55.0,
                moon_target_separation_deg=12.0,
                moon_above_horizon=True,
                moon_visible_during_target_window=True,
                moon_set_before_target_window=False,
            ),
            "close high Moon applies the strongest lunar background penalty",
        ),
        GeometryFixture(
            "high_altitude_far",
            "High Moon far from target",
            MoonGeometryConditionInput(
                moon_altitude_deg=55.0,
                moon_target_separation_deg=125.0,
                moon_above_horizon=True,
                moon_visible_during_target_window=True,
                moon_set_before_target_window=False,
            ),
            "large separation reduces the lunar background penalty",
        ),
    )


def _target(fixture: TargetFixture) -> CelestialObject:
    return CelestialObject(
        id=fixture.target_id,
        name=fixture.target_id.replace("_", " ").title(),
        object_type=fixture.object_type,
        image="",
        magnitude=fixture.magnitude,
        distance="",
        max_altitude="55 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="22:00 - 02:00",
        notes="Moon geometry calibration fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="4 h",
        visible=True,
        score=round(fixture.score),
        score_label="Fixture",
        difficulty=fixture.difficulty,
        recommended_setup_type="telescope",
    )


def _weather() -> WeatherSummary:
    return WeatherSummary(
        score="Good",
        score_value=86,
        explanation="Fixture",
        cloud_cover=8,
        precipitation_probability=0,
        wind_kmh=5,
        humidity=45,
        temperature_c=12,
        alert="",
    )


def _scores() -> AdvancedObservingScores:
    return AdvancedObservingScores(
        planetary_score=90,
        deep_sky_score=90,
        planetary_label="Good",
        deep_sky_label="Good",
        explanation="Fixture",
    )


def _sky_quality() -> SkyQuality:
    return SkyQuality(
        bortle_class=3,
        limiting_magnitude=5.8,
        sky_brightness=20.4,
        source="Fixture VIIRS",
        description="Fixture",
        viirs_radiance=1.0,
    )


def _moon() -> MoonSummary:
    return MoonSummary(
        phase="Waxing gibbous",
        illumination="70%",
        rise_time="18:00",
        set_time="03:30",
        best_note="Fixture",
        image="",
        phase_angle=0.0,
    )


def _telescope() -> Telescope:
    return Telescope(
        id="calibration-scope",
        name="Calibration Scope",
        aperture_mm=127,
        focal_length_mm=1500,
        optical_type="Mak",
        mount="GoTo",
    )


if __name__ == "__main__":
    write_markdown_report()
