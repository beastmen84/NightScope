from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import NightPlanItem, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.sky_compass_nsom_comparison import SkyCompassNsomComparisonService

REPORT_PATH = Path("docs/SKY_COMPASS_NSOM_COMPARISON_REPORT.md")
TARGET_IDS = (
    "jupiter",
    "moon",
    "galaxy",
    "diffuse_nebula",
    "open_cluster",
    "globular_cluster",
)


@dataclass(frozen=True)
class SkyCompassScenario:
    scenario_id: str
    label: str
    sky_profile: str
    session_profile: str
    equipment_profile: str
    confidence_profile: str
    context_profile: str
    expectation: str
    sky_quality: SkyQuality
    moon: MoonSummary
    weather: WeatherSummary
    telescope: Telescope
    confidence: RecommendationConfidence
    has_location: bool = True


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
            "sky_compass_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "scenario_count": len(scenarios),
            "row_count": len(rows),
            "target_ids": TARGET_IDS,
        },
        "scenarios": scenarios,
        "summary": _summary(scenarios, rows),
        "confidence_control": _confidence_control(),
    }
    return nsom_to_json_compatible(report_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report_data = generate_report_data() if data is None else data
    metadata = report_data["metadata"]
    summary = report_data["summary"]

    lines = [
        "# Sky Compass NSOM Comparison Report",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report compares the current Sky Compass direction "
            "ranking with NSOM target and direction reference values. It does not "
            "change Sky Compass runtime output, Home, Best Object, Planner, QML, "
            "logging, network behaviour or runtime file writes."
        ),
        (
            f"The matrix covers {metadata['scenario_count']} deterministic scenarios "
            f"and {metadata['row_count']} candidate rows. Legacy direction ranking "
            "is compared with NSOM `ObservableTargetValue` and "
            "`PracticalTargetValue` direction references."
        ),
        (
            "Result: Sky Compass is not a pure target-value ranker. It is a "
            "direction/presentation policy that combines prepared candidate score, "
            "Night Plan membership, Best Object status and target concentration."
        ),
        "",
        "## Methodology",
        "",
        "- Uses `SkyCompassNsomComparisonService` with fixed in-memory fixtures only.",
        "- Repeats the current legacy direction formula without changing runtime output.",
        "- Shows NSOM Observable and Practical direction references separately.",
        "- Marks unavailable legacy components instead of reconstructing upstream score details.",
        "- Keeps SessionViability and RecommendationConfidence as metadata only.",
        "- No controller/QML import, automatic logging, network call or runtime file write.",
        "",
        "## Scenario Matrix",
        "",
        "| Scenario | Sky | Session | Equipment | Context | Expected behaviour |",
        "| --- | --- | --- | --- | --- | --- |",
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
                    str(axes["context_profile"]),
                    str(scenario["expectation"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Direction Ranking Comparison",
            "",
            "| Scenario | Legacy Direction Order | NSOM Observable Direction Reference | NSOM Practical Direction Reference | Legacy Top | Observable Top |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for scenario in report_data["scenarios"]:
        difference = scenario["direction_difference"]
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    _order_label(scenario["legacy_direction_order"]),
                    _order_label(scenario["nsom_observable_direction_order"]),
                    _order_label(scenario["nsom_practical_direction_order"]),
                    str(difference["legacy_top"]),
                    str(difference["nsom_observable_top"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Candidate Details",
            "",
            "| Scenario | Target | Direction | Legacy Contribution | Observable | Practical | Session | Confidence |",
            "| --- | --- | --- | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for scenario in report_data["scenarios"]:
        for row in scenario["rows"]:
            legacy = row["legacy"]["sky_compass_target"]
            nsom = row["nsom"]
            lines.append(
                "| "
                + " | ".join(
                    (
                        str(scenario["scenario_id"]),
                        str(row["target"]["object_id"]),
                        str(row["target"]["direction"]),
                        f"{float(legacy['direction_score_contribution']):.2f}"
                        if legacy["direction_score_contribution"] is not None
                        else "unavailable",
                        f"{float(nsom['observable_target_value']['value']):.2f}",
                        f"{float(nsom['practical_target_value']['value']):.2f}",
                        str(nsom["session_viability"]["state"]),
                        _confidence_label(nsom["recommendation_confidence"]["value"]),
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
                "Sky Compass legacy direction score is intentionally presentation "
                "oriented. It mixes a prepared target score with plan membership, "
                "Best Object status and one fixed target-presence bonus."
            ),
        ]
    )
    for item in summary["ownership_mismatch_findings"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Main Direction Differences",
            "",
        ]
    )
    for item in summary["direction_difference_findings"]:
        lines.append(f"- {item}")

    confidence = report_data["confidence_control"]
    lines.extend(
        [
            "",
            "## Confidence Control",
            "",
            (
                f"Changing only confidence keeps legacy direction top "
                f"`{confidence['low_legacy_top']}` -> `{confidence['high_legacy_top']}`, "
                f"Observable top `{confidence['low_observable_top']}` -> "
                f"`{confidence['high_observable_top']}`, and target value deltas "
                f"`{float(confidence['observable_delta']):.4f}` / "
                f"`{float(confidence['practical_delta']):.4f}`."
            ),
            "Confidence remains metadata-only and is not a score factor.",
            "",
            "## Migration Readiness",
            "",
            "- Sky Compass should not be migrated as a pure target ranking.",
            "- A future default-off path should preserve direction/presentation policy explicitly.",
            "- `ObservableTargetValue` can inform direction references but should not replace plan/best/context boosts blindly.",
            "- `PracticalTargetValue` should remain inspection-only until equipment-aware compass semantics are designed.",
            "- Session blocked/poor-weather state should stay caution/actionability metadata, not target physics.",
            "",
            "## Recommended Next Steps",
            "",
            "1. Review whether Sky Compass should remain a presentation policy over NSOM-prepared candidates.",
            "2. Add a default-off experimental Sky Compass NSOM direction policy only after that review.",
            "3. Keep the current `skyCompass` QML payload shape unchanged until a UI/rationale design step.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _evaluate_scenario(scenario: SkyCompassScenario) -> dict[str, object]:
    targets = _targets()
    plan = _night_plan(targets, scenario.context_profile)
    best_object = _best_object(targets, scenario.context_profile)
    comparison = SkyCompassNsomComparisonService().compare(
        targets,
        plan,
        best_object,
        weather=scenario.weather,
        sky_quality=scenario.sky_quality,
        telescope=scenario.telescope,
        moon=scenario.moon,
        confidence=scenario.confidence,
        has_location=scenario.has_location,
        caution_text=_caution_text(scenario.session_profile),
    )
    rows = tuple(_row_projection(scenario, item) for item in comparison["items"])
    legacy_order = _direction_order(comparison["rankings"]["legacy_direction"])
    observable_order = _direction_order(comparison["rankings"]["nsom_observable_direction_reference"])
    practical_order = _direction_order(comparison["rankings"]["nsom_practical_direction_reference"])
    return {
        "scenario_id": scenario.scenario_id,
        "label": scenario.label,
        "axes": {
            "sky_profile": scenario.sky_profile,
            "session_profile": scenario.session_profile,
            "equipment_profile": scenario.equipment_profile,
            "confidence_profile": scenario.confidence_profile,
            "context_profile": scenario.context_profile,
        },
        "expectation": scenario.expectation,
        "legacy_formula": comparison["legacy_formula"],
        "legacy_direction_order": legacy_order,
        "nsom_observable_direction_order": observable_order,
        "nsom_practical_direction_order": practical_order,
        "direction_difference": {
            "legacy_top": legacy_order[0] if legacy_order else None,
            "nsom_observable_top": observable_order[0] if observable_order else None,
            "nsom_practical_top": practical_order[0] if practical_order else None,
            "legacy_vs_observable_changed": legacy_order[:1] != observable_order[:1],
            "legacy_vs_practical_changed": legacy_order[:1] != practical_order[:1],
            "runtime_ranking_changed": False,
        },
        "direction_groups": comparison["direction_groups"],
        "rows": rows,
        "metadata": comparison["metadata"],
    }


def _row_projection(scenario: SkyCompassScenario, item: dict[str, object]) -> dict[str, object]:
    nsom = item["nsom"]
    return {
        "scenario_id": scenario.scenario_id,
        "target": {
            "object_id": item["object_id"],
            "name": item["name"],
            "object_type": item["object_type"],
            "direction": item["direction"],
            "target_class": item["target_class"],
        },
        "legacy": {
            "sky_compass_target": item["legacy"]["sky_compass_target"],
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
        if scenario["direction_difference"]["legacy_vs_observable_changed"]
        or scenario["direction_difference"]["legacy_vs_practical_changed"]
    ]
    boost_rows = [
        row
        for row in rows
        if row["legacy"]["sky_compass_target"]["available"]
        and (
            row["legacy"]["sky_compass_target"]["components"]["in_plan_bonus"] > 0
            or row["legacy"]["sky_compass_target"]["components"]["best_object_bonus"] > 0
        )
    ]
    return {
        "direction_difference_count": len(changed),
        "scenarios_with_direction_difference": tuple(scenario["scenario_id"] for scenario in changed),
        "direction_difference_findings": tuple(_direction_finding(scenario) for scenario in changed)
        or ("No direction-top differences in this deterministic matrix.",),
        "ownership_mismatch_findings": (
            f"{len(boost_rows)} rows include plan or Best Object boosts that are presentation context, not target physics.",
            "Legacy Sky Compass receives an already prepared candidate score and cannot expose upstream score components.",
            "Moon and sky background are visible in NSOM sky ownership but unavailable in the legacy direction formula.",
            "SessionViability and RecommendationConfidence are metadata and have zero target-value effect.",
            "Observer equipment changes PracticalTargetValue references, not legacy Sky Compass direction contribution.",
        ),
    }


def _direction_finding(scenario: dict[str, object]) -> str:
    diff = scenario["direction_difference"]
    return (
        f"`{scenario['scenario_id']}` legacy top `{diff['legacy_top']}` differs from "
        f"Observable `{diff['nsom_observable_top']}` or Practical `{diff['nsom_practical_top']}`."
    )


def _confidence_control() -> dict[str, object]:
    scenario = _scenario("S01_dark_sky")
    targets = _targets()
    low = SkyCompassNsomComparisonService().compare(
        targets,
        [],
        None,
        weather=scenario.weather,
        sky_quality=scenario.sky_quality,
        telescope=scenario.telescope,
        moon=scenario.moon,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = SkyCompassNsomComparisonService().compare(
        targets,
        [],
        None,
        weather=scenario.weather,
        sky_quality=scenario.sky_quality,
        telescope=scenario.telescope,
        moon=scenario.moon,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )
    low_item = _item(low, "galaxy")["nsom"]
    high_item = _item(high, "galaxy")["nsom"]
    return {
        "low_legacy_top": _direction_order(low["rankings"]["legacy_direction"])[0],
        "high_legacy_top": _direction_order(high["rankings"]["legacy_direction"])[0],
        "low_observable_top": _direction_order(low["rankings"]["nsom_observable_direction_reference"])[0],
        "high_observable_top": _direction_order(high["rankings"]["nsom_observable_direction_reference"])[0],
        "observable_delta": high_item["observable_target_value"]["value"] - low_item["observable_target_value"]["value"],
        "practical_delta": high_item["practical_target_value"]["value"] - low_item["practical_target_value"]["value"],
        "score_factor": False,
        "score_effect": 0.0,
    }


def _scenarios() -> tuple[SkyCompassScenario, ...]:
    return tuple(
        _scenario(scenario_id)
        for scenario_id in (
            "S01_dark_sky",
            "S02_bright_moon",
            "S03_high_light_pollution",
            "S04_poor_weather",
            "S05_blocked_session",
            "S06_small_equipment",
            "S07_large_equipment",
            "S08_plan_best_boost",
        )
    )


def _scenario(scenario_id: str) -> SkyCompassScenario:
    specs = {
        "S01_dark_sky": (
            "dark sky baseline",
            "dark_sky",
            "good",
            "medium_telescope",
            "high",
            "none",
            "Baseline should show current direction policy and NSOM direction references.",
        ),
        "S02_bright_moon": (
            "bright Moon",
            "bright_moon",
            "good",
            "medium_telescope",
            "high",
            "none",
            "Moon-sensitive deep-sky targets should degrade through NSOM sky ownership only.",
        ),
        "S03_high_light_pollution": (
            "high light pollution",
            "high_light_pollution",
            "good",
            "medium_telescope",
            "high",
            "none",
            "Static sky background should affect NSOM references, not legacy direction formula.",
        ),
        "S04_poor_weather": (
            "poor weather",
            "dark_sky",
            "poor",
            "medium_telescope",
            "high",
            "none",
            "Poor weather should remain session/caution metadata for Sky Compass.",
        ),
        "S05_blocked_session": (
            "blocked session",
            "dark_sky",
            "blocked",
            "medium_telescope",
            "high",
            "none",
            "Blocked weather should not mutate target or direction physics.",
        ),
        "S06_small_equipment": (
            "small equipment",
            "dark_sky",
            "good",
            "small_telescope",
            "high",
            "none",
            "Equipment should change PracticalTargetValue references only.",
        ),
        "S07_large_equipment": (
            "large equipment",
            "dark_sky",
            "good",
            "large_telescope",
            "high",
            "none",
            "Large equipment should change PracticalTargetValue references only.",
        ),
        "S08_plan_best_boost": (
            "plan and best-object boost",
            "dark_sky",
            "good",
            "medium_telescope",
            "high",
            "plan_best",
            "Plan membership and Best Object identity should be visible as presentation boosts.",
        ),
    }
    label, sky_profile, session_profile, equipment_profile, confidence_profile, context_profile, expectation = specs[
        scenario_id
    ]
    sky_quality, moon = _sky_profile(sky_profile)
    return SkyCompassScenario(
        scenario_id=scenario_id,
        label=label,
        sky_profile=sky_profile,
        session_profile=session_profile,
        equipment_profile=equipment_profile,
        confidence_profile=confidence_profile,
        context_profile=context_profile,
        expectation=expectation,
        sky_quality=sky_quality,
        moon=moon,
        weather=_weather_profile(session_profile),
        telescope=_equipment_profile(equipment_profile),
        confidence=_confidence(confidence_profile),
    )


def _targets() -> tuple[CelestialObject, ...]:
    specs = {
        "jupiter": ("Jupiter", "Pianeta", 86, "-2.1", "Facile", "Est", "22:00", "planetary"),
        "moon": ("Moon", "Moon", 82, "-12.0", "Facile", "Ovest", "21:00", "planetary"),
        "galaxy": ("Galaxy", "Galaxy", 90, "8.2", "Media", "Sud", "22:30", "telescope"),
        "diffuse_nebula": ("Diffuse Nebula", "Nebula", 88, "7.0", "Media", "Sud", "23:00", "telescope"),
        "open_cluster": ("Open Cluster", "Open Cluster", 78, "5.2", "Facile", "Nord-Est", "23:30", "binoculars"),
        "globular_cluster": ("Globular Cluster", "Globular Cluster", 84, "6.8", "Media", "Nord-Est", "00:00", "telescope"),
    }
    return tuple(_target(target_id, *specs[target_id]) for target_id in TARGET_IDS)


def _target(
    object_id: str,
    name: str,
    object_type: str,
    score: int,
    magnitude: str,
    difficulty: str,
    direction: str,
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
        direction=direction,
        best_time=best_time,
        observing_window=f"{best_time} - 02:00",
        notes="Sky Compass NSOM report fixture",
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


def _night_plan(
    targets: tuple[CelestialObject, ...],
    context_profile: str,
) -> tuple[NightPlanItem, ...]:
    if context_profile != "plan_best":
        return ()
    cluster = _find_target(targets, "globular_cluster")
    return (
        NightPlanItem(
            time_label="00:00 notte",
            object_id=cluster.id,
            name=cluster.name,
            score=cluster.score,
            difficulty=cluster.difficulty,
            setup=cluster.recommended_setup,
            direction=cluster.direction,
            image=cluster.image,
        ),
    )


def _best_object(
    targets: tuple[CelestialObject, ...],
    context_profile: str,
) -> CelestialObject | None:
    if context_profile != "plan_best":
        return None
    return _find_target(targets, "globular_cluster")


def _find_target(targets: tuple[CelestialObject, ...], object_id: str) -> CelestialObject:
    return next(target for target in targets if target.id == object_id)


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
            notes=("sky_compass_report:high_confidence",),
        )
    return RecommendationConfidence(
        weather_confidence=0.4,
        viirs_confidence=0.0,
        moon_geometry_confidence=0.5,
        provider_fallback_confidence=0.6,
        notes=("sky_compass_report:low_confidence",),
    )


def _caution_text(session_profile: str) -> str:
    if session_profile in {"poor", "blocked"}:
        return "Fixture caution: conditions are not ideal."
    return ""


def _item(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return next(item for item in comparison["items"] if item["object_id"] == object_id)


def _direction_order(ranking: list[dict[str, object]]) -> tuple[str, ...]:
    return tuple(str(item["direction"]) for item in ranking)


def _order_label(order: list[object] | tuple[object, ...]) -> str:
    return " > ".join(str(item) for item in order)


def _confidence_label(value: object) -> str:
    return "n/a" if value is None else f"{float(value):.2f}"


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="SkyCompassNsomReportFixture",
        description="Sky Compass NSOM report fixture",
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
