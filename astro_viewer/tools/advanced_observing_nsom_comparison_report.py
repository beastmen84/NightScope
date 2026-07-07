from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.advanced_observing_nsom_comparison import (
    AdvancedObservingNsomComparisonService,
)

REPORT_PATH = Path("docs/ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT.md")


@dataclass(frozen=True)
class AdvancedObservingScenario:
    scenario_id: str
    label: str
    sky_profile: str
    session_profile: str
    seeing_profile: str
    confidence_profile: str
    expectation: str
    weather: WeatherSummary
    seeing: SeeingTransparency
    sky_quality: SkyQuality
    moon: MoonSummary
    confidence: RecommendationConfidence


def generate_report_data() -> dict[str, object]:
    scenarios = tuple(_evaluate_scenario(scenario) for scenario in _scenarios())
    category_rows = tuple(row for scenario in scenarios for row in scenario["category_rows"])
    report_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "advanced_scores_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed": False,
            "sky_compass_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "scenario_count": len(scenarios),
            "category_row_count": len(category_rows),
        },
        "scenarios": scenarios,
        "summary": _summary(scenarios),
        "semantic_recommendation": _semantic_recommendation(),
    }
    return nsom_to_json_compatible(report_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report_data = generate_report_data() if data is None else data
    metadata = report_data["metadata"]
    summary = report_data["summary"]
    semantic = report_data["semantic_recommendation"]

    lines = [
        "# Advanced Observing NSOM Comparison Report",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report compares the current legacy advanced "
            "planetary/deep-sky scores with NSOM reference concepts. It does not "
            "change `AdvancedObservingService`, Home, Best Object, Planner, Sky "
            "Compass, QML, logging, network behaviour or runtime file writes."
        ),
        (
            f"The matrix covers {metadata['scenario_count']} deterministic scenarios "
            f"and {metadata['category_row_count']} category rows. It exposes the "
            "legacy formula components and shows NSOM reference projections for "
            "session, sky/environment, effective observability and confidence."
        ),
        (
            "Result: Advanced Observing should be migrated as a presentation/diagnostic "
            "consumer of NSOM components, not as another independent scoring owner."
        ),
        "",
        "## Methodology",
        "",
        "- Uses `AdvancedObservingNsomComparisonService` with fixed in-memory fixtures only.",
        "- Legacy formulas are shown exactly from `AdvancedObservingService`.",
        "- NSOM projections are reference-only; score parity is not expected.",
        "- Weather/session is shown as `SessionViability` metadata in NSOM.",
        "- Moon and light pollution are shown as target-class sky/environment effects.",
        "- `RecommendationConfidence` remains metadata-only with zero score effect.",
        "- No runtime wiring, QML exposure, automatic logging, network call or runtime file write.",
        "",
        "## Scenario Matrix",
        "",
        "| Scenario | Sky | Session | Seeing/Transparency | Confidence | Expected behaviour |",
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
                    str(axes["seeing_profile"]),
                    str(axes["confidence_profile"]),
                    str(scenario["expectation"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Score Comparison",
            "",
            "| Scenario | Legacy Planetary | Legacy Deep-Sky | Planet Reference OTV | Deep-Sky Avg OTV | Session | Confidence |",
            "| --- | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for scenario in report_data["scenarios"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    f"{float(scenario['legacy']['planetary']['score']):.0f}",
                    f"{float(scenario['legacy']['deep_sky']['score']):.0f}",
                    f"{float(scenario['nsom']['planetary_reference']['observable_target_value']['value']):.2f}",
                    f"{float(scenario['nsom']['deep_sky_reference_summary']['average_observable_target_value']):.2f}",
                    str(scenario["nsom"]["session_viability"]["state"]),
                    _confidence_label(scenario["nsom"]["recommendation_confidence"]["value"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Legacy Formula Details",
            "",
            "| Scenario | Category | Formula | Raw Before Cap | Weather Cap | Ownership Mixing | Unavailable Components |",
            "| --- | --- | --- | ---: | ---: | --- | --- |",
        ]
    )
    for scenario in report_data["scenarios"]:
        for row in scenario["category_rows"]:
            legacy = row["legacy"]
            lines.append(
                "| "
                + " | ".join(
                    (
                        str(scenario["scenario_id"]),
                        str(row["category"]),
                        str(legacy["formula"]),
                        f"{float(legacy['raw_score_before_cap']):.0f}",
                        f"{float(legacy['weather_cap']):.0f}",
                        ", ".join(str(item) for item in legacy["ownership_mixing"]),
                        ", ".join(str(item) for item in legacy["unavailable_components"]),
                    )
                )
                + " |"
            )

    lines.extend(
        [
            "",
            "## Main Mismatches",
            "",
        ]
    )
    for item in summary["main_mismatches"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## NSOM Behaviour Checks",
            "",
        ]
    )
    for item in summary["nsom_behaviour_checks"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Semantic Recommendation",
            "",
            f"- Classification: `{semantic['classification']}`.",
            f"- Recommended migration target: `{semantic['recommended_future_nsom_concept']}`.",
            f"- Reason: {semantic['reason']}",
            f"- Runtime score replacement ready: `{semantic['runtime_score_replacement_ready']}`.",
            f"- Confidence score effect: `{float(semantic['confidence_score_effect']):.1f}`.",
            "",
            "## Recommended Next Steps",
            "",
            "1. Review whether advanced scores should become NSOM-derived presentation diagnostics.",
            "2. Decide whether planetary and deep-sky category badges should consume session viability or show it separately.",
            "3. Add a default-off Advanced Observing NSOM path only after score-display semantics are decided.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _evaluate_scenario(scenario: AdvancedObservingScenario) -> dict[str, object]:
    comparison = AdvancedObservingNsomComparisonService().compare(
        weather=scenario.weather,
        seeing=scenario.seeing,
        sky_quality=scenario.sky_quality,
        moon=scenario.moon,
        confidence=scenario.confidence,
    )
    category_rows = (
        _category_row("planetary", comparison["legacy"]["planetary"]),
        _category_row("deep_sky", comparison["legacy"]["deep_sky"]),
    )
    return {
        "scenario_id": scenario.scenario_id,
        "label": scenario.label,
        "axes": {
            "sky_profile": scenario.sky_profile,
            "session_profile": scenario.session_profile,
            "seeing_profile": scenario.seeing_profile,
            "confidence_profile": scenario.confidence_profile,
        },
        "expectation": scenario.expectation,
        "runtime_inputs": _runtime_inputs(scenario),
        "legacy": {
            "advanced_scores": comparison["legacy"]["advanced_scores"],
            "planetary": comparison["legacy"]["planetary"],
            "deep_sky": comparison["legacy"]["deep_sky"],
        },
        "nsom": comparison["nsom"],
        "category_rows": category_rows,
        "metadata": comparison["metadata"],
    }


def _category_row(category: str, legacy: dict[str, object]) -> dict[str, object]:
    return {
        "category": category,
        "legacy": legacy,
    }


def _summary(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    bright_moon = _scenario_by_id(scenarios, "A04_bright_moon")
    dark = _scenario_by_id(scenarios, "A01_good_session")
    high_lp = _scenario_by_id(scenarios, "A05_high_light_pollution")
    blocked = _scenario_by_id(scenarios, "A03_blocked_session")
    low_confidence = _scenario_by_id(scenarios, "A08_low_confidence")
    high_confidence = _scenario_by_id(scenarios, "A01_good_session")

    return {
        "main_mismatches": (
            "Legacy advanced scores mix weather/session directly into both category scores.",
            "Legacy deep-sky score has one broad scalar for galaxy, nebula and cluster classes.",
            "Legacy planetary score includes a Moon component even though NSOM protects planets from sky-background damage.",
            "Weather caps duplicate session viability and can hide whether the limiting factor is sky or actionability.",
            "Legacy advanced scores do not expose observer capability or confidence as separate concepts.",
        ),
        "nsom_behaviour_checks": (
            _check_line(
                "Bright Moon lowers deep-sky reference OTV",
                _deep_sky_average(bright_moon) < _deep_sky_average(dark),
            ),
            _check_line(
                "Bright Moon leaves planet sky background protected",
                _planet_environment(bright_moon)["lunar_sky_background"] == 1.0,
            ),
            _check_line(
                "High light pollution lowers deep-sky reference OTV",
                _deep_sky_average(high_lp) < _deep_sky_average(dark),
            ),
            _check_line(
                "Blocked weather changes session viability but not reference observable values",
                blocked["nsom"]["session_viability"]["state"] == "blocked"
                and _planet_observable(blocked) == _planet_observable(dark),
            ),
            _check_line(
                "Changing confidence alone does not change reference observable values",
                _planet_observable(low_confidence) == _planet_observable(high_confidence)
                and _deep_sky_average(low_confidence) == _deep_sky_average(high_confidence),
            ),
        ),
    }


def _semantic_recommendation() -> dict[str, object]:
    return {
        "classification": "presentation diagnostic / category quality surface",
        "recommended_future_nsom_concept": "NSOM-derived category diagnostics with separate session policy",
        "reason": (
            "Advanced Observing produces user-facing category badges rather than a "
            "target ranking. It should consume NSOM sky/session components instead "
            "of owning independent Moon, weather and transparency penalties."
        ),
        "runtime_score_replacement_ready": False,
        "confidence_score_effect": 0.0,
    }


def _scenarios() -> tuple[AdvancedObservingScenario, ...]:
    return tuple(
        _scenario(scenario_id)
        for scenario_id in (
            "A01_good_session",
            "A02_poor_weather",
            "A03_blocked_session",
            "A04_bright_moon",
            "A05_high_light_pollution",
            "A06_poor_seeing",
            "A07_poor_transparency",
            "A08_low_confidence",
        )
    )


def _scenario(scenario_id: str) -> AdvancedObservingScenario:
    specs = {
        "A01_good_session": (
            "good session",
            "dark_sky",
            "good",
            "good",
            "high",
            "Baseline advanced observing conditions.",
        ),
        "A02_poor_weather": (
            "poor weather",
            "dark_sky",
            "poor",
            "good",
            "high",
            "Legacy scores fall through weather factors while NSOM keeps target references stable.",
        ),
        "A03_blocked_session": (
            "blocked session",
            "dark_sky",
            "blocked",
            "good",
            "high",
            "Weather cap and SessionViability both expose non-actionable session pressure.",
        ),
        "A04_bright_moon": (
            "bright Moon",
            "bright_moon",
            "good",
            "good",
            "high",
            "Moon should affect deep-sky references more than planetary sky background.",
        ),
        "A05_high_light_pollution": (
            "high light pollution",
            "high_light_pollution",
            "good",
            "good",
            "high",
            "Light pollution should affect deep-sky references more than planetary references.",
        ),
        "A06_poor_seeing": (
            "poor seeing",
            "dark_sky",
            "good",
            "poor_seeing",
            "high",
            "Seeing should mostly pressure planetary legacy score and planetary atmospheric reference.",
        ),
        "A07_poor_transparency": (
            "poor transparency",
            "dark_sky",
            "good",
            "poor_transparency",
            "high",
            "Transparency should mostly pressure deep-sky legacy score and deep-sky atmospheric reference.",
        ),
        "A08_low_confidence": (
            "low confidence",
            "dark_sky",
            "good",
            "good",
            "low",
            "Confidence should change metadata only.",
        ),
    }
    label, sky_profile, session_profile, seeing_profile, confidence_profile, expectation = specs[scenario_id]
    sky_quality, moon = _sky_profile(sky_profile)
    return AdvancedObservingScenario(
        scenario_id=scenario_id,
        label=label,
        sky_profile=sky_profile,
        session_profile=session_profile,
        seeing_profile=seeing_profile,
        confidence_profile=confidence_profile,
        expectation=expectation,
        weather=_weather_profile(session_profile),
        seeing=_seeing_profile(seeing_profile),
        sky_quality=sky_quality,
        moon=moon,
        confidence=_confidence(confidence_profile),
    )


def _scenario_by_id(
    scenarios: tuple[dict[str, object], ...],
    scenario_id: str,
) -> dict[str, object]:
    return next(scenario for scenario in scenarios if scenario["scenario_id"] == scenario_id)


def _runtime_inputs(scenario: AdvancedObservingScenario) -> dict[str, object]:
    return {
        "weather": {
            "score_value": scenario.weather.score_value,
            "cloud_cover": scenario.weather.cloud_cover,
            "precipitation_probability": scenario.weather.precipitation_probability,
            "wind_kmh": scenario.weather.wind_kmh,
        },
        "seeing": {
            "seeing_score": scenario.seeing.seeing_score,
            "transparency_score": scenario.seeing.transparency_score,
            "source": scenario.seeing.source,
        },
        "sky_quality": {
            "bortle_class": scenario.sky_quality.bortle_class,
            "viirs_radiance": scenario.sky_quality.viirs_radiance,
            "source": scenario.sky_quality.source,
        },
        "moon": {
            "illumination": scenario.moon.illumination,
            "phase": scenario.moon.phase,
        },
    }


def _sky_profile(profile: str) -> tuple[SkyQuality, MoonSummary]:
    profiles = {
        "bright_moon": (_sky_quality(3, radiance=2), _moon(95)),
        "dark_sky": (_sky_quality(2, radiance=1), _moon(10)),
        "high_light_pollution": (_sky_quality(9, radiance=120), _moon(20)),
    }
    return profiles[profile]


def _weather_profile(profile: str) -> WeatherSummary:
    profiles = {
        "good": _weather(score=90, cloud_cover=10, precipitation=0, wind=5, explanation="good session"),
        "poor": _weather(score=35, cloud_cover=70, precipitation=20, wind=14, explanation="poor session"),
        "blocked": _weather(score=10, cloud_cover=92, precipitation=80, wind=18, explanation="blocked session"),
    }
    return profiles[profile]


def _seeing_profile(profile: str) -> SeeingTransparency:
    profiles = {
        "good": _seeing(seeing_score=86, transparency_score=84),
        "poor_seeing": _seeing(seeing_score=30, transparency_score=84),
        "poor_transparency": _seeing(seeing_score=86, transparency_score=30),
    }
    return profiles[profile]


def _confidence(profile: str) -> RecommendationConfidence:
    if profile == "high":
        return RecommendationConfidence(
            weather_confidence=1.0,
            viirs_confidence=1.0,
            moon_geometry_confidence=1.0,
            provider_fallback_confidence=None,
            notes=("advanced_observing_report:high_confidence",),
        )
    return RecommendationConfidence(
        weather_confidence=0.4,
        viirs_confidence=0.0,
        moon_geometry_confidence=0.5,
        provider_fallback_confidence=0.6,
        notes=("advanced_observing_report:low_confidence",),
    )


def _planet_environment(scenario: dict[str, object]) -> dict[str, object]:
    return scenario["nsom"]["planetary_reference"]["observation_environment"]


def _planet_observable(scenario: dict[str, object]) -> float:
    return float(scenario["nsom"]["planetary_reference"]["observable_target_value"]["value"])


def _deep_sky_average(scenario: dict[str, object]) -> float:
    return float(scenario["nsom"]["deep_sky_reference_summary"]["average_observable_target_value"])


def _check_line(label: str, passed: bool) -> str:
    return f"{label}: {'passed' if passed else 'review'}"


def _confidence_label(value: object) -> str:
    return "n/a" if value is None else f"{float(value):.2f}"


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="AdvancedObservingNsomReportFixture",
        description="Advanced Observing NSOM report fixture",
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
    wind: int,
    explanation: str,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation=explanation,
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation,
        wind_kmh=wind,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _seeing(
    *,
    seeing_score: int,
    transparency_score: int,
) -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Fixture",
        transparency="Fixture",
        seeing_score=seeing_score,
        transparency_score=transparency_score,
        explanation="Fixture",
    )


if __name__ == "__main__":
    write_markdown_report()
