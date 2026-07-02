from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.home_nsom_comparison import HomeNsomComparisonService

REPORT_PATH = Path("docs/HOME_NSOM_COMPARISON_REPORT.md")
TARGET_TYPES = ("galaxy", "diffuse_nebula", "open_cluster", "globular_cluster")


@dataclass(frozen=True)
class HomeScenario:
    scenario_id: str
    label: str
    sky_profile: str
    session_profile: str
    equipment_profile: str
    confidence_profile: str
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
            "home_ranking_changed": False,
            "best_object_changed": False,
            "sky_compass_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "scenario_count": len(scenarios),
            "row_count": len(rows),
            "target_types": TARGET_TYPES,
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
        "# Home NSOM Comparison Report",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report compares the current Home `recommendedDeepSky` "
            "ordering with NSOM `ObservableTargetValue` ordering. It does not change "
            "Home ranking, Best Object selection, Sky Compass, QML, logging, network "
            "behaviour or runtime file writes."
        ),
        (
            f"The matrix covers {metadata['scenario_count']} deterministic scenarios "
            f"and {metadata['row_count']} deep-sky candidate rows. "
            "`PracticalTargetValue` is shown for inspection only and is not used as "
            "the proposed Home ranking decision."
        ),
        (
            "Result: `recommendedDeepSky` looks safe to migrate behind a default-off "
            "flag only after the ordering differences below are reviewed. The first "
            "runtime migration should use `ObservableTargetValue`, not "
            "`PracticalTargetValue` or `ObservationOpportunity`."
        ),
        "",
        "## Methodology",
        "",
        "- Uses `HomeNsomComparisonService` with fixed in-memory fixtures only.",
        "- Compares current Home deep-sky Moon-adjusted legacy order with NSOM `ObservableTargetValue` order.",
        "- Shows `PracticalTargetValue` separately to inspect equipment sensitivity before Home uses it.",
        "- Marks legacy components unavailable instead of reconstructing non-existent breakdowns.",
        "- Keeps `RecommendationConfidence` as metadata only with zero score effect.",
        "- No runtime wiring, QML exposure, automatic logging, network call or runtime file write.",
        "",
        "## Scenario Matrix",
        "",
        "| Scenario | Sky | Session | Equipment | Confidence | Expected behaviour |",
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
                    str(axes["confidence_profile"]),
                    str(scenario["expectation"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Ordering Comparison",
            "",
            "| Scenario | Legacy Home Order | NSOM Observable Order | Order Changed | Practical Top |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for scenario in report_data["scenarios"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    _order_label(scenario["legacy_home_order"]),
                    _order_label(scenario["nsom_observable_order"]),
                    "yes" if scenario["ordering_difference"]["changed"] else "no",
                    _order_label(scenario["nsom_practical_order"][:1]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Candidate Details",
            "",
            "| Scenario | Target | Legacy Adjusted | Mutation Delta | Observable | Practical | Legacy Unavailable Components |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for scenario in report_data["scenarios"]:
        for row in scenario["rows"]:
            unavailable = row["legacy"]["home_deep_sky_adjusted"]["unavailable_components"]
            lines.append(
                "| "
                + " | ".join(
                    (
                        str(scenario["scenario_id"]),
                        str(row["target"]["object_id"]),
                        f"{float(row['legacy']['home_deep_sky_adjusted']['score']):.2f}",
                        f"{float(row['legacy_score_mutation']['delta']):.2f}",
                        f"{float(row['nsom']['observable_target_value']['value']):.2f}",
                        f"{float(row['nsom']['practical_target_value']['value']):.2f}",
                        ", ".join(str(item) for item in unavailable),
                    )
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "## Main Ordering Differences",
            "",
        ]
    )
    for item in summary["ordering_difference_findings"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Legacy Score Mutation Notes",
            "",
            (
                "Current Home deep-sky conditioning returns replacement `CelestialObject` "
                "instances with adjusted `score` and `score_label`. The original runtime "
                "objects are not mutated by this report, but the Home presentation path "
                "does rank by the adjusted replacement score."
            ),
        ]
    )
    for item in summary["legacy_mutation_findings"]:
        lines.append(f"- {item}")

    confidence = report_data["confidence_control"]
    lines.extend(
        [
            "",
            "## Confidence Control",
            "",
            (
                f"Changing only confidence keeps `ObservableTargetValue` delta "
                f"`{float(confidence['observable_delta']):.4f}` and "
                f"`PracticalTargetValue` delta `{float(confidence['practical_delta']):.4f}`. "
                "Confidence remains metadata-only and is not a ranking factor."
            ),
            "",
            "## Migration Readiness",
            "",
            f"- RecommendedDeepSky safe behind flag: `{summary['safe_to_migrate_behind_flag']}`.",
            "- Use `ObservableTargetValue` as the first candidate ranking value.",
            "- Keep `PracticalTargetValue` comparison-only until equipment-driven Home semantics are reviewed.",
            "- Do not use session/weather or `ObservationOpportunity` for base Home ranking in the first migration.",
            "",
            "## Recommended Next Steps",
            "",
            "1. Add a default-off Home NSOM flag around `recommendedDeepSky` ordering only.",
            "2. Preserve current legacy Home order as rollback and comparison baseline.",
            "3. Add runtime characterization tests before exposing any QML-visible ordering change.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _evaluate_scenario(scenario: HomeScenario) -> dict[str, object]:
    targets = _targets()
    comparison = HomeNsomComparisonService().compare(
        targets,
        weather=scenario.weather,
        sky_quality=scenario.sky_quality,
        telescope=scenario.telescope,
        moon=scenario.moon,
        confidence=scenario.confidence,
    )
    rows = tuple(_row_projection(scenario, item) for item in comparison["items"])
    legacy_order = _ranked_order(comparison["rankings"]["legacy_home_deep_sky"])
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
        },
        "expectation": scenario.expectation,
        "runtime_inputs": _runtime_inputs(scenario),
        "legacy_home_order": legacy_order,
        "nsom_observable_order": observable_order,
        "nsom_practical_order": practical_order,
        "ordering_difference": {
            "changed": legacy_order != observable_order,
            "legacy_top": legacy_order[0] if legacy_order else None,
            "nsom_observable_top": observable_order[0] if observable_order else None,
            "practical_top": practical_order[0] if practical_order else None,
            "practical_used_for_home_ranking": False,
        },
        "rows": rows,
    }


def _row_projection(scenario: HomeScenario, item: dict[str, object]) -> dict[str, object]:
    legacy = item["legacy"]["home_deep_sky_adjusted"]
    nsom = item["nsom"]
    base_score = float(legacy["components"]["base_score"])
    adjusted_score = float(legacy["components"]["adjusted_score"])
    return {
        "scenario_id": scenario.scenario_id,
        "target": {
            "object_id": item["object_id"],
            "name": item["name"],
            "object_type": item["object_type"],
            "target_class": item["target_class"],
        },
        "legacy": {
            "home_deep_sky_adjusted": legacy,
            "best_object_reference": item["legacy"]["best_object"],
        },
        "legacy_score_mutation": {
            "base_score": base_score,
            "adjusted_score": adjusted_score,
            "delta": adjusted_score - base_score,
            "replacement_object_score_differs": adjusted_score != base_score,
            "runtime_object_mutated_by_report": False,
        },
        "nsom": {
            "intrinsic_target_quality": nsom["intrinsic_target_quality"],
            "observation_environment": nsom["observation_environment"],
            "effective_observability": nsom["effective_observability"],
            "observable_target_value": nsom["observable_target_value"],
            "practical_target_value": nsom["practical_target_value"],
            "recommendation_confidence": nsom["recommendation_confidence"],
            "ownership": nsom["ownership"],
        },
        "deltas": item["deltas"],
    }


def _summary(
    scenarios: tuple[dict[str, object], ...],
    rows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    changed = [scenario for scenario in scenarios if scenario["ordering_difference"]["changed"]]
    mutation_rows = [row for row in rows if row["legacy_score_mutation"]["replacement_object_score_differs"]]
    bright_rows = [
        row
        for row in rows
        if row["scenario_id"] in {"H01_bright_moon", "H03_high_light_pollution"}
    ]
    return {
        "safe_to_migrate_behind_flag": True,
        "ordering_difference_count": len(changed),
        "scenarios_with_ordering_difference": tuple(scenario["scenario_id"] for scenario in changed),
        "ordering_difference_findings": tuple(_ordering_finding(scenario) for scenario in changed)
        or ("No ordering differences in this deterministic matrix.",),
        "legacy_mutation_row_count": len(mutation_rows),
        "legacy_mutation_findings": tuple(_mutation_finding(row) for row in mutation_rows[:8])
        or ("No legacy score mutation differences in this deterministic matrix.",),
        "model_alignment_findings": (
            f"{len(bright_rows)} bright-sky rows expose sky-owned NSOM components separately.",
            "Poor and blocked weather are metadata in this Home comparison, not ObservableTargetValue inputs.",
            "Small and large equipment affect PracticalTargetValue, not ObservableTargetValue.",
            "Confidence metadata has zero ObservableTargetValue and PracticalTargetValue delta.",
        ),
    }


def _ordering_finding(scenario: dict[str, object]) -> str:
    difference = scenario["ordering_difference"]
    return (
        f"`{scenario['scenario_id']}` changes top candidate from "
        f"`{difference['legacy_top']}` to `{difference['nsom_observable_top']}`; "
        "`PracticalTargetValue` remains inspection-only."
    )


def _mutation_finding(row: dict[str, object]) -> str:
    mutation = row["legacy_score_mutation"]
    return (
        f"`{row['scenario_id']}:{row['target']['object_id']}` legacy Home adjusted score "
        f"{mutation['base_score']:.0f} -> {mutation['adjusted_score']:.0f} "
        f"(delta {mutation['delta']:.0f})."
    )


def _confidence_control() -> dict[str, object]:
    target = _targets()[0]
    scenario = _scenario("H02_dark_sky")
    low = HomeNsomComparisonService().compare(
        [target],
        weather=scenario.weather,
        sky_quality=scenario.sky_quality,
        telescope=scenario.telescope,
        moon=scenario.moon,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = HomeNsomComparisonService().compare(
        [target],
        weather=scenario.weather,
        sky_quality=scenario.sky_quality,
        telescope=scenario.telescope,
        moon=scenario.moon,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )
    low_item = low["items"][0]["nsom"]
    high_item = high["items"][0]["nsom"]
    return {
        "target_id": target.id,
        "low_confidence_value": low_item["recommendation_confidence"]["value"],
        "high_confidence_value": high_item["recommendation_confidence"]["value"],
        "observable_delta": high_item["observable_target_value"]["value"] - low_item["observable_target_value"]["value"],
        "practical_delta": high_item["practical_target_value"]["value"] - low_item["practical_target_value"]["value"],
        "score_factor": False,
        "score_effect": 0.0,
    }


def _scenarios() -> tuple[HomeScenario, ...]:
    return tuple(
        _scenario(scenario_id)
        for scenario_id in (
            "H01_bright_moon",
            "H02_dark_sky",
            "H03_high_light_pollution",
            "H04_poor_weather",
            "H05_blocked_session",
            "H06_small_equipment",
            "H07_large_equipment",
        )
    )


def _scenario(scenario_id: str) -> HomeScenario:
    specs = {
        "H01_bright_moon": (
            "bright Moon",
            "bright_moon",
            "good",
            "medium_telescope",
            "high",
            "Moon-sensitive deep-sky classes should move through sky-owned NSOM factors.",
        ),
        "H02_dark_sky": (
            "dark sky baseline",
            "dark_sky",
            "good",
            "medium_telescope",
            "high",
            "Baseline should show limited sky degradation.",
        ),
        "H03_high_light_pollution": (
            "high light pollution",
            "high_light_pollution",
            "good",
            "medium_telescope",
            "high",
            "NSOM should expose static sky background where legacy Home Moon adjustment does not.",
        ),
        "H04_poor_weather": (
            "poor weather",
            "dark_sky",
            "poor",
            "medium_telescope",
            "high",
            "Weather should stay outside Home ObservableTargetValue in this comparison.",
        ),
        "H05_blocked_session": (
            "blocked session",
            "dark_sky",
            "blocked",
            "medium_telescope",
            "high",
            "Blocked session should not mutate Home ObservableTargetValue.",
        ),
        "H06_small_equipment": (
            "small equipment",
            "dark_sky",
            "good",
            "small_telescope",
            "high",
            "Equipment should change PracticalTargetValue only.",
        ),
        "H07_large_equipment": (
            "large equipment",
            "dark_sky",
            "good",
            "large_telescope",
            "high",
            "Large equipment should change PracticalTargetValue only.",
        ),
    }
    label, sky_profile, session_profile, equipment_profile, confidence_profile, expectation = specs[scenario_id]
    return HomeScenario(
        scenario_id=scenario_id,
        label=label,
        sky_profile=sky_profile,
        session_profile=session_profile,
        equipment_profile=equipment_profile,
        confidence_profile=confidence_profile,
        expectation=expectation,
        sky_quality=_sky_profile(sky_profile)[0],
        moon=_sky_profile(sky_profile)[1],
        weather=_weather_profile(session_profile),
        telescope=_equipment_profile(equipment_profile),
        confidence=_confidence(confidence_profile),
    )


def _targets() -> tuple[CelestialObject, ...]:
    specs = {
        "galaxy": ("Galaxy", "Galaxy", 88, "8.2", "Media", "22:00"),
        "diffuse_nebula": ("Diffuse Nebula", "Nebula", 86, "7.0", "Media", "22:30"),
        "open_cluster": ("Open Cluster", "Open Cluster", 78, "5.2", "Facile", "23:30"),
        "globular_cluster": ("Globular Cluster", "Globular Cluster", 84, "6.8", "Media", "00:00"),
    }
    return tuple(_target(target_id, *specs[target_id]) for target_id in TARGET_TYPES)


def _target(
    object_id: str,
    name: str,
    object_type: str,
    score: int,
    magnitude: str,
    difficulty: str,
    best_time: str,
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
        notes="Home NSOM comparison fixture",
        recommended_setup="Fixture setup",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type="telescope",
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
            notes=("home_nsom_report:high_confidence",),
        )
    return RecommendationConfidence(
        weather_confidence=0.4,
        viirs_confidence=0.0,
        moon_geometry_confidence=0.5,
        provider_fallback_confidence=0.6,
        notes=("home_nsom_report:low_confidence",),
    )


def _runtime_inputs(scenario: HomeScenario) -> dict[str, object]:
    return {
        "moon": {
            "illumination": scenario.moon.illumination,
            "phase": scenario.moon.phase,
        },
        "sky_quality": {
            "bortle_class": scenario.sky_quality.bortle_class,
            "viirs_radiance": scenario.sky_quality.viirs_radiance,
            "source": scenario.sky_quality.source,
        },
        "weather": {
            "score_value": scenario.weather.score_value,
            "cloud_cover": scenario.weather.cloud_cover,
            "precipitation_probability": scenario.weather.precipitation_probability,
        },
        "telescope": {
            "name": scenario.telescope.name,
            "aperture_mm": scenario.telescope.aperture_mm,
            "focal_length_mm": scenario.telescope.focal_length_mm,
            "mount": scenario.telescope.mount,
        },
    }


def _ranked_order(ranking: list[dict[str, object]]) -> tuple[str, ...]:
    return tuple(str(item["object_id"]) for item in ranking)


def _order_label(order: list[object] | tuple[object, ...]) -> str:
    return " > ".join(str(item) for item in order)


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="HomeNsomReportFixture",
        description="Home NSOM report fixture",
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
