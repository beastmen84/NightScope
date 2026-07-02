from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.best_object_nsom_comparison import BestObjectNsomComparisonService

REPORT_PATH = Path("docs/BEST_OBJECT_NSOM_COMPARISON_REPORT.md")


@dataclass(frozen=True)
class BestObjectScenario:
    scenario_id: str
    label: str
    sky_profile: str
    session_profile: str
    equipment_profile: str
    confidence_profile: str
    target_profile: str
    expectation: str
    sky_quality: SkyQuality
    moon: MoonSummary
    weather: WeatherSummary
    telescope: Telescope
    confidence: RecommendationConfidence


def generate_report_data() -> dict[str, object]:
    scenarios = tuple(_evaluate_scenario(scenario) for scenario in _scenarios())
    rows = tuple(row for scenario in scenarios for row in scenario["rows"])
    report_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "best_object_changed": False,
            "recommended_deep_sky_changed": False,
            "planner_changed": False,
            "sky_compass_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "scenario_count": len(scenarios),
            "row_count": len(rows),
        },
        "scenarios": scenarios,
        "summary": _summary(scenarios, rows),
        "semantic_recommendation": _semantic_recommendation(),
    }
    return nsom_to_json_compatible(report_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report_data = generate_report_data() if data is None else data
    metadata = report_data["metadata"]
    summary = report_data["summary"]
    semantic = report_data["semantic_recommendation"]

    lines = [
        "# Best Object NSOM Comparison Report",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report compares the current legacy Best Object "
            "selection with NSOM candidate values. It does not change Best Object "
            "selection, recommendedDeepSky, Planner, Sky Compass, QML, logging, "
            "network behaviour or runtime file writes."
        ),
        (
            f"The matrix covers {metadata['scenario_count']} deterministic scenarios "
            f"and {metadata['row_count']} candidate rows. It compares legacy Best "
            "Object rank, NSOM ObservableTargetValue rank and NSOM PracticalTargetValue rank."
        ),
        (
            f"Semantic recommendation: Best Object is currently closest to "
            f"`{semantic['classification']}`. {semantic['reason']}"
        ),
        "",
        "## Methodology",
        "",
        "- Uses `BestObjectNsomComparisonService` with fixed in-memory fixtures only.",
        "- Legacy formula is shown as `item.score * weather_factor * difficulty_factor`.",
        "- NSOM ObservableTargetValue and PracticalTargetValue are ranked separately.",
        "- SessionViability and RecommendationConfidence are shown as metadata.",
        "- Legacy components that are not exposed are marked unavailable, not reconstructed.",
        "- No runtime wiring, QML exposure, automatic logging, network call or runtime file write.",
        "",
        "## Scenario Matrix",
        "",
        "| Scenario | Sky | Session | Equipment | Confidence | Targets | Expected behaviour |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for scenario in report_data["scenarios"]:
        axes = scenario["axes"]
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    str(axes["sky_profile"]),
                    str(axes["session_profile"]),
                    str(axes["equipment_profile"]),
                    str(axes["confidence_profile"]),
                    str(axes["target_profile"]),
                    str(scenario["expectation"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Ranking Comparison",
            "",
            "| Scenario | Legacy Best Object Order | NSOM Observable Order | NSOM Practical Order | Legacy Top | Observable Top | Practical Top |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for scenario in report_data["scenarios"]:
        difference = scenario["selection_difference"]
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    _order_label(scenario["legacy_best_object_order"]),
                    _order_label(scenario["nsom_observable_order"]),
                    _order_label(scenario["nsom_practical_order"]),
                    str(difference["legacy_top"]),
                    str(difference["nsom_observable_top"]),
                    str(difference["nsom_practical_top"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Candidate Details",
            "",
            "| Scenario | Target | Legacy Best | Observable | Practical | Session | Confidence | Legacy Unavailable Components |",
            "| --- | --- | ---: | ---: | ---: | --- | ---: | --- |",
        ]
    )
    for scenario in report_data["scenarios"]:
        for row in scenario["rows"]:
            legacy = row["legacy"]["best_object"]
            nsom = row["nsom"]
            lines.append(
                "| "
                + " | ".join(
                    (
                        str(scenario["scenario_id"]),
                        str(row["target"]["object_id"]),
                        f"{float(legacy['score']):.2f}" if legacy["score"] is not None else "unavailable",
                        f"{float(nsom['observable_target_value']['value']):.2f}",
                        f"{float(nsom['practical_target_value']['value']):.2f}",
                        str(nsom["session_viability"]["state"]),
                        _confidence_label(nsom["recommendation_confidence"]["value"]),
                        ", ".join(str(item) for item in legacy["unavailable_components"]),
                    )
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "## Legacy Ownership Mixing",
            "",
            (
                "Legacy Best Object combines target value, session/weather and difficulty "
                "inside one final scalar. NSOM keeps those concerns separate."
            ),
        ]
    )
    for item in summary["ownership_mismatch_findings"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Main Selection Differences",
            "",
        ]
    )
    for item in summary["selection_difference_findings"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Semantic Recommendation",
            "",
            f"- Classification: `{semantic['classification']}`.",
            f"- Recommended migration target: `{semantic['recommended_future_nsom_concept']}`.",
            f"- Reason: {semantic['reason']}",
            f"- Do not use ObservableTargetValue alone: `{semantic['observable_target_value_alone_is_enough']}`.",
            f"- Do not use PracticalTargetValue alone: `{semantic['practical_target_value_alone_is_enough']}`.",
            f"- Needs session policy: `{semantic['needs_session_policy']}`.",
            "",
            "## Recommended Next Steps",
            "",
            "1. Add a default-off Best Object NSOM path only after this comparison is reviewed.",
            "2. Decide whether Best Object should become an action-oriented ObservationOpportunity recommendation.",
            "3. Keep legacy Best Object rollback until UI score/rationale semantics are designed.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _evaluate_scenario(scenario: BestObjectScenario) -> dict[str, object]:
    targets = _targets(scenario.target_profile)
    comparison = BestObjectNsomComparisonService().compare(
        targets,
        weather=scenario.weather,
        sky_quality=scenario.sky_quality,
        telescope=scenario.telescope,
        moon=scenario.moon,
        confidence=scenario.confidence,
    )
    rows = tuple(_row_projection(scenario, item) for item in comparison["items"])
    legacy_order = _ranked_order(comparison["rankings"]["legacy_best_object"])
    observable_order = _ranked_order(comparison["rankings"]["nsom_observable"])
    practical_order = _ranked_order(comparison["rankings"]["nsom_practical"])
    return {
        "scenario_id": scenario.scenario_id,
        "label": scenario.label,
        "axes": {
            "sky_profile": scenario.sky_profile,
            "session_profile": scenario.session_profile,
            "equipment_profile": scenario.equipment_profile,
            "confidence_profile": scenario.confidence_profile,
            "target_profile": scenario.target_profile,
        },
        "expectation": scenario.expectation,
        "legacy_formula": comparison["legacy_formula"],
        "legacy_best_object_order": legacy_order,
        "nsom_observable_order": observable_order,
        "nsom_practical_order": practical_order,
        "selection_difference": {
            "legacy_top": legacy_order[0] if legacy_order else None,
            "nsom_observable_top": observable_order[0] if observable_order else None,
            "nsom_practical_top": practical_order[0] if practical_order else None,
            "legacy_vs_observable_changed": legacy_order[:1] != observable_order[:1],
            "legacy_vs_practical_changed": legacy_order[:1] != practical_order[:1],
        },
        "rows": rows,
        "metadata": comparison["metadata"],
    }


def _row_projection(scenario: BestObjectScenario, item: dict[str, object]) -> dict[str, object]:
    nsom = item["nsom"]
    legacy = item["legacy"]["best_object"]
    return {
        "scenario_id": scenario.scenario_id,
        "target": {
            "object_id": item["object_id"],
            "name": item["name"],
            "object_type": item["object_type"],
            "target_class": item["target_class"],
        },
        "legacy": {
            "best_object": legacy,
        },
        "nsom": {
            "intrinsic_target_quality": nsom["intrinsic_target_quality"],
            "observation_environment": nsom["observation_environment"],
            "effective_observability": nsom["effective_observability"],
            "observable_target_value": nsom["observable_target_value"],
            "practical_target_value": nsom["practical_target_value"],
            "session_viability": nsom["session_viability"],
            "recommendation_confidence": nsom["recommendation_confidence"],
            "ownership": nsom["ownership"],
        },
        "deltas": item["deltas"],
    }


def _summary(
    scenarios: tuple[dict[str, object], ...],
    rows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    changed = [
        scenario
        for scenario in scenarios
        if scenario["selection_difference"]["legacy_vs_observable_changed"]
        or scenario["selection_difference"]["legacy_vs_practical_changed"]
    ]
    weather_rows = [
        row
        for row in rows
        if row["nsom"]["ownership"]["session_weather_effects"]["legacy_best_object_uses_weather_factor"]
    ]
    return {
        "selection_difference_count": len(changed),
        "scenarios_with_selection_difference": tuple(scenario["scenario_id"] for scenario in changed),
        "selection_difference_findings": tuple(_selection_finding(scenario) for scenario in changed)
        or ("No top-candidate differences in this deterministic matrix.",),
        "ownership_mismatch_findings": (
            f"{len(weather_rows)} rows show legacy weather_factor mixed into Best Object score.",
            "Legacy difficulty_factor is not separated into NSOM target, observer or session ownership.",
            "Sky background, Moon background, observer capability and confidence are unavailable in legacy Best Object.",
            "Blocked sessions still receive the legacy weather floor instead of a non-actionable policy state.",
        ),
    }


def _selection_finding(scenario: dict[str, object]) -> str:
    diff = scenario["selection_difference"]
    return (
        f"`{scenario['scenario_id']}` legacy top `{diff['legacy_top']}` differs from "
        f"Observable `{diff['nsom_observable_top']}` or Practical `{diff['nsom_practical_top']}`."
    )


def _semantic_recommendation() -> dict[str, object]:
    return {
        "classification": "Home-specific hybrid",
        "recommended_future_nsom_concept": "ObservationOpportunity with Home-specific presentation policy",
        "reason": (
            "Best Object answers an action-oriented tonight question, but the current "
            "legacy formula lacks observing-window, chronology and non-actionable policy "
            "semantics. ObservableTargetValue is too sky/object-only, while "
            "PracticalTargetValue omits session actionability."
        ),
        "observable_target_value_alone_is_enough": False,
        "practical_target_value_alone_is_enough": False,
        "needs_session_policy": True,
        "confidence_score_effect": 0.0,
    }


def _scenarios() -> tuple[BestObjectScenario, ...]:
    return tuple(
        _scenario(scenario_id)
        for scenario_id in (
            "B01_good_session",
            "B02_poor_weather",
            "B03_blocked_session",
            "B04_bright_moon",
            "B05_high_light_pollution",
            "B06_small_equipment",
            "B07_large_equipment",
            "B08_mixed_planet_deep_sky",
        )
    )


def _scenario(scenario_id: str) -> BestObjectScenario:
    specs = {
        "B01_good_session": (
            "good session",
            "dark_sky",
            "good",
            "medium_telescope",
            "high",
            "standard_best_object",
            "Baseline mixed Best Object candidates under usable conditions.",
        ),
        "B02_poor_weather": (
            "poor weather",
            "dark_sky",
            "poor",
            "medium_telescope",
            "high",
            "standard_best_object",
            "Legacy weather_factor lowers score while NSOM target values stay stable.",
        ),
        "B03_blocked_session": (
            "blocked session",
            "dark_sky",
            "blocked",
            "medium_telescope",
            "high",
            "standard_best_object",
            "Blocked weather is session metadata in NSOM and a floor-limited legacy factor.",
        ),
        "B04_bright_moon": (
            "bright Moon",
            "bright_moon",
            "good",
            "medium_telescope",
            "high",
            "standard_best_object",
            "Moon-sensitive deep-sky values move through NSOM sky ownership.",
        ),
        "B05_high_light_pollution": (
            "high light pollution",
            "high_light_pollution",
            "good",
            "medium_telescope",
            "high",
            "standard_best_object",
            "Static sky background is visible in NSOM and unavailable in legacy Best Object.",
        ),
        "B06_small_equipment": (
            "small equipment",
            "dark_sky",
            "good",
            "small_telescope",
            "high",
            "standard_best_object",
            "Equipment changes PracticalTargetValue without changing ObservableTargetValue.",
        ),
        "B07_large_equipment": (
            "large equipment",
            "dark_sky",
            "good",
            "large_telescope",
            "high",
            "standard_best_object",
            "Large equipment changes PracticalTargetValue without changing ObservableTargetValue.",
        ),
        "B08_mixed_planet_deep_sky": (
            "mixed planet/deep-sky candidate set",
            "dark_sky",
            "good",
            "medium_telescope",
            "low",
            "expanded_mixed",
            "Planet, Moon and deep-sky candidates are compared without confidence affecting score.",
        ),
    }
    label, sky_profile, session_profile, equipment_profile, confidence_profile, target_profile, expectation = specs[
        scenario_id
    ]
    sky_quality, moon = _sky_profile(sky_profile)
    return BestObjectScenario(
        scenario_id=scenario_id,
        label=label,
        sky_profile=sky_profile,
        session_profile=session_profile,
        equipment_profile=equipment_profile,
        confidence_profile=confidence_profile,
        target_profile=target_profile,
        expectation=expectation,
        sky_quality=sky_quality,
        moon=moon,
        weather=_weather_profile(session_profile),
        telescope=_equipment_profile(equipment_profile),
        confidence=_confidence(confidence_profile),
    )


def _targets(profile: str) -> tuple[CelestialObject, ...]:
    standard = (
        _target("jupiter", "Jupiter", "Pianeta", 86, "-2.1", "Facile", "22:00", "planetary"),
        _target("galaxy", "Galaxy", "Galaxy", 90, "8.2", "Media", "22:30", "telescope"),
        _target("diffuse_nebula", "Diffuse Nebula", "Nebula", 88, "7.0", "Media", "23:00", "telescope"),
        _target("open_cluster", "Open Cluster", "Open Cluster", 78, "5.2", "Facile", "23:30", "binoculars"),
    )
    if profile == "standard_best_object":
        return standard
    if profile == "expanded_mixed":
        return (
            *standard,
            _target("moon", "Moon", "Moon", 82, "-12.0", "Facile", "21:00", "planetary"),
            _target("globular_cluster", "Globular Cluster", "Globular Cluster", 84, "6.8", "Media", "00:00", "telescope"),
        )
    raise ValueError(f"Unknown target profile: {profile}")


def _target(
    object_id: str,
    name: str,
    object_type: str,
    score: int,
    magnitude: str,
    difficulty: str,
    best_time: str,
    setup_type: str,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time=best_time,
        observing_window=f"{best_time} - 02:00",
        notes="Best Object NSOM comparison fixture",
        recommended_setup="Fixture setup",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type=setup_type,
    )


def _sky_profile(profile: str) -> tuple[SkyQuality, MoonSummary]:
    profiles = {
        "bright_moon": (_sky_quality(3, radiance=2), _moon(95)),
        "dark_sky": (_sky_quality(2, radiance=1), _moon(10)),
        "high_light_pollution": (_sky_quality(9, radiance=120), _moon(20)),
    }
    return profiles[profile]


def _weather_profile(profile: str) -> WeatherSummary:
    profiles = {
        "good": _weather(score=90, cloud_cover=10, precipitation=0, explanation="good deterministic session"),
        "poor": _weather(score=30, cloud_cover=70, precipitation=20, explanation="poor deterministic session"),
        "blocked": _weather(score=10, cloud_cover=90, precipitation=80, explanation="blocked rain/cloud session"),
    }
    return profiles[profile]


def _equipment_profile(profile: str) -> Telescope:
    profiles = {
        "small_telescope": Telescope("small", "Small Manual", 60, 400, "Refractor", "manual"),
        "medium_telescope": Telescope("medium", "Mak 127", 127, 1500, "Catadioptric", "manual"),
        "large_telescope": Telescope("large", "Large GoTo", 220, 1800, "Reflector", "GoTo EQ"),
    }
    return profiles[profile]


def _confidence(profile: str) -> RecommendationConfidence:
    if profile == "high":
        return RecommendationConfidence(
            weather_confidence=1.0,
            viirs_confidence=1.0,
            moon_geometry_confidence=1.0,
            provider_fallback_confidence=None,
            notes=("best_object_report:high_confidence",),
        )
    return RecommendationConfidence(
        weather_confidence=0.4,
        viirs_confidence=0.0,
        moon_geometry_confidence=0.5,
        provider_fallback_confidence=0.6,
        notes=("best_object_report:low_confidence",),
    )


def _ranked_order(ranking: list[dict[str, object]]) -> tuple[str, ...]:
    return tuple(str(item["object_id"]) for item in ranking)


def _order_label(order: list[object] | tuple[object, ...]) -> str:
    return " > ".join(str(item) for item in order)


def _confidence_label(value: object) -> str:
    return "n/a" if value is None else f"{float(value):.2f}"


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="BestObjectNsomReportFixture",
        description="Best Object NSOM report fixture",
        viirs_radiance=radiance,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="20:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
    )


def _weather(
    *,
    score: int,
    cloud_cover: int,
    precipitation: int,
    explanation: str,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation=explanation,
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


if __name__ == "__main__":
    write_markdown_report()
