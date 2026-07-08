from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.detail_nsom_comparison import (
    DETAIL_SOURCE_CATALOGUE,
    DETAIL_SOURCE_OBSERVING,
    DetailObjectNsomComparisonService,
)


REPORT_PATH = Path("docs/DETAIL_OBJECT_NSOM_COMPARISON_REPORT.md")


@dataclass(frozen=True)
class DetailScenario:
    scenario_id: str
    label: str
    source: str
    target: CelestialObject
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
    report_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "selected_object_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed": False,
            "sky_compass_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "scenario_count": len(scenarios),
        },
        "scenarios": scenarios,
        "summary": _summary(scenarios),
        "confidence_control": _confidence_control(),
        "equipment_control": _equipment_control(),
    }
    return nsom_to_json_compatible(report_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report_data = generate_report_data() if data is None else data
    metadata = report_data["metadata"]
    summary = report_data["summary"]

    lines = [
        "# Detail/Object NSOM Comparison Report",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report compares current selected-object Detail "
            "semantics with NSOM target projections. It does not change "
            "`selectedObject`, QML, Home, Best Object, Planner, Sky Compass, "
            "logging, network behaviour or runtime file writes."
        ),
        (
            f"The matrix covers {metadata['scenario_count']} deterministic Detail "
            "scenarios. Observing-source Detail currently displays a moon-adjusted "
            "replacement object; catalogue Detail displays the raw catalogue object. "
            "NSOM values are parallel comparison data only."
        ),
        "",
        "## Methodology",
        "",
        "- Uses `DetailObjectNsomComparisonService` with fixed in-memory fixtures only.",
        "- Replicates the current selected-object score policy without calling `AppController`.",
        "- Computes NSOM `ObservableTargetValue` and `PracticalTargetValue` separately.",
        "- Keeps `SessionViability` and `RecommendationConfidence` as metadata.",
        "- Marks unavailable legacy components instead of fabricating breakdowns.",
        "- No runtime wiring, QML exposure, automatic logging, network call or runtime file write.",
        "",
        "## Scenario Matrix",
        "",
        "| Scenario | Source | Target | Sky | Session | Equipment | Confidence | Expectation |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for scenario in report_data["scenarios"]:
        axes = scenario["axes"]
        target = scenario["target"]
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    str(axes["source"]),
                    str(target["object_id"]),
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
            "## Detail Comparison",
            "",
            (
                "| Scenario | Policy | Legacy Display | Score Delta | Lunar Sky | Static Sky | "
                "Observable | Practical | Session | Confidence |"
            ),
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for scenario in report_data["scenarios"]:
        legacy = scenario["legacy"]["selected_object_detail"]
        nsom = scenario["nsom"]
        env = nsom["observation_environment"]
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    str(legacy["policy"]),
                    f"{float(legacy['display_score']):.2f}",
                    f"{float(legacy['score_delta']):.2f}",
                    f"{float(env['lunar_sky_background']):.3f}",
                    f"{float(env['static_sky_background']):.3f}",
                    f"{float(nsom['observable_target_value']['value']):.2f}",
                    f"{float(nsom['practical_target_value']['value']):.2f}",
                    str(nsom["session_viability"]["state"]),
                    f"{float(nsom['recommendation_confidence']['value'] or 0.0):.2f}",
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Findings",
            "",
        ]
    )
    for finding in summary["findings"]:
        lines.append(f"- {finding}")

    equipment = report_data["equipment_control"]
    confidence = report_data["confidence_control"]
    lines.extend(
        [
            "",
            "## Controls",
            "",
            (
                f"- Equipment control: observable delta "
                f"`{float(equipment['observable_delta']):.4f}`, practical delta "
                f"`{float(equipment['practical_delta']):.4f}`."
            ),
            (
                f"- Confidence control: observable delta "
                f"`{float(confidence['observable_delta']):.4f}`, practical delta "
                f"`{float(confidence['practical_delta']):.4f}`, score factor "
                f"`{confidence['score_factor']}`."
            ),
            "",
            "## Migration Recommendation",
            "",
            (
                "Do not change Detail UI yet. First review whether selected-object "
                "Detail should present NSOM explanation fields separately from the "
                "legacy/base `score`, because the current payload uses compatibility "
                "score semantics and source-specific conditioning."
            ),
            "",
            "## Recommended Next Steps",
            "",
            "1. Review this report for source-specific Detail semantics.",
            "2. Add a readiness audit before any default-off Detail NSOM runtime path.",
            "3. Keep any visible NSOM explanation UI as a separate design step.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _evaluate_scenario(scenario: DetailScenario) -> dict[str, object]:
    comparison = DetailObjectNsomComparisonService().compare(
        scenario.target,
        source=scenario.source,
        weather=scenario.weather,
        sky_quality=scenario.sky_quality,
        telescope=scenario.telescope,
        moon=scenario.moon,
        confidence=scenario.confidence,
    )
    return {
        "scenario_id": scenario.scenario_id,
        "label": scenario.label,
        "axes": {
            "source": scenario.source,
            "sky_profile": scenario.sky_profile,
            "session_profile": scenario.session_profile,
            "equipment_profile": scenario.equipment_profile,
            "confidence_profile": scenario.confidence_profile,
        },
        "expectation": scenario.expectation,
        "target": {
            "object_id": comparison["object_id"],
            "name": comparison["name"],
            "object_type": comparison["object_type"],
            "target_class": comparison["target_class"],
        },
        "legacy": comparison["legacy"],
        "nsom": comparison["nsom"],
        "deltas": comparison["deltas"],
        "metadata": comparison["metadata"],
    }


def _summary(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    observing_adjusted = [
        scenario["scenario_id"]
        for scenario in scenarios
        if scenario["legacy"]["selected_object_detail"]["policy"] == "observing_detail_moon_adjusted_copy"
        and float(scenario["legacy"]["selected_object_detail"]["score_delta"]) < 0.0
    ]
    catalogue_raw = [
        scenario["scenario_id"]
        for scenario in scenarios
        if scenario["legacy"]["selected_object_detail"]["policy"] == "catalogue_detail_raw_object"
    ]
    high_static_sky = [
        scenario["scenario_id"]
        for scenario in scenarios
        if float(scenario["nsom"]["observation_environment"]["static_sky_background"]) < 0.8
    ]
    blocked = [
        scenario["scenario_id"]
        for scenario in scenarios
        if scenario["nsom"]["session_viability"]["state"] == "blocked"
    ]
    return {
        "observing_detail_moon_adjusted_scenarios": tuple(observing_adjusted),
        "catalogue_raw_detail_scenarios": tuple(catalogue_raw),
        "high_static_sky_background_scenarios": tuple(high_static_sky),
        "blocked_session_metadata_scenarios": tuple(blocked),
        "findings": (
            "Observing-source Detail still uses a moon-adjusted replacement object for displayed score.",
            "Catalogue Detail keeps raw selected-object score and does not expose a moon-adjustment breakdown.",
            "Static sky background is visible in NSOM ObservableTargetValue but not in legacy selectedObject score.",
            "Session viability is useful Detail metadata but does not modify target values.",
            "Equipment changes PracticalTargetValue only; ObservableTargetValue remains objective.",
            "RecommendationConfidence remains metadata-only with zero score effect.",
        ),
    }


def _confidence_control() -> dict[str, object]:
    target = _target("galaxy", "Galaxy", 88)
    low = DetailObjectNsomComparisonService().compare(
        target,
        source=DETAIL_SOURCE_OBSERVING,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(15),
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = DetailObjectNsomComparisonService().compare(
        target,
        source=DETAIL_SOURCE_OBSERVING,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(),
        moon=_moon(15),
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )
    return {
        "low_confidence_value": low["nsom"]["recommendation_confidence"]["value"],
        "high_confidence_value": high["nsom"]["recommendation_confidence"]["value"],
        "observable_delta": _observable(high) - _observable(low),
        "practical_delta": _practical(high) - _practical(low),
        "legacy_display_delta": _legacy_display(high) - _legacy_display(low),
        "score_factor": False,
        "score_effect": 0.0,
    }


def _equipment_control() -> dict[str, object]:
    target = _target("galaxy", "Galaxy", 88)
    small = DetailObjectNsomComparisonService().compare(
        target,
        source=DETAIL_SOURCE_OBSERVING,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(name="Small Manual", aperture_mm=60, focal_length_mm=400, mount="manual"),
        moon=_moon(15),
    )
    large = DetailObjectNsomComparisonService().compare(
        target,
        source=DETAIL_SOURCE_OBSERVING,
        weather=_weather(90),
        sky_quality=_sky_quality(3),
        telescope=_telescope(name="Large GoTo", aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
        moon=_moon(15),
    )
    return {
        "small_practical_target_value": _practical(small),
        "large_practical_target_value": _practical(large),
        "observable_delta": _observable(large) - _observable(small),
        "practical_delta": _practical(large) - _practical(small),
        "legacy_display_delta": _legacy_display(large) - _legacy_display(small),
    }


def _scenarios() -> tuple[DetailScenario, ...]:
    return (
        DetailScenario(
            "D01_observing_bright_moon",
            "Observing Detail under bright Moon",
            DETAIL_SOURCE_OBSERVING,
            _target("galaxy", "Galaxy", 88),
            "bright_moon",
            "good",
            "medium",
            "high",
            "Observing-source Detail should show a legacy moon-adjusted score copy.",
            _sky_quality(3),
            _moon(95),
            _weather(90),
            _telescope(),
            RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
        ),
        DetailScenario(
            "D02_catalogue_bright_moon",
            "Catalogue Detail under bright Moon",
            DETAIL_SOURCE_CATALOGUE,
            _target("catalogue-galaxy", "Galaxy", 88, visibility_class="Catalogo Messier"),
            "bright_moon",
            "good",
            "medium",
            "high",
            "Catalogue Detail should keep raw legacy score while NSOM still reports sky context.",
            _sky_quality(3),
            _moon(95),
            _weather(90),
            _telescope(),
            RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
        ),
        DetailScenario(
            "D03_high_light_pollution",
            "Observing Detail under high light pollution",
            DETAIL_SOURCE_OBSERVING,
            _target("diffuse_nebula", "Diffuse nebula", 86),
            "high_light_pollution",
            "good",
            "medium",
            "high",
            "NSOM should expose static sky background separately from legacy Detail score.",
            _sky_quality(9, radiance=140.0),
            _moon(15),
            _weather(90),
            _telescope(),
            RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
        ),
        DetailScenario(
            "D04_blocked_session",
            "Observing Detail during blocked session",
            DETAIL_SOURCE_OBSERVING,
            _target("galaxy", "Galaxy", 88),
            "dark",
            "blocked",
            "medium",
            "high",
            "Session viability should be metadata and not mutate target values.",
            _sky_quality(3),
            _moon(15),
            _weather(10, cloud_cover=96, precipitation_probability=85),
            _telescope(),
            RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
        ),
        DetailScenario(
            "D05_small_equipment",
            "Observing Detail with small equipment",
            DETAIL_SOURCE_OBSERVING,
            _target("galaxy", "Galaxy", 88),
            "dark",
            "good",
            "small",
            "high",
            "Equipment should affect PracticalTargetValue only.",
            _sky_quality(3),
            _moon(15),
            _weather(90),
            _telescope(name="Small Manual", aperture_mm=60, focal_length_mm=400, mount="manual"),
            RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
        ),
        DetailScenario(
            "D06_large_equipment",
            "Observing Detail with large equipment",
            DETAIL_SOURCE_OBSERVING,
            _target("galaxy", "Galaxy", 88),
            "dark",
            "good",
            "large",
            "high",
            "Large equipment should increase PracticalTargetValue without changing ObservableTargetValue.",
            _sky_quality(3),
            _moon(15),
            _weather(90),
            _telescope(name="Large GoTo", aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
            RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
        ),
    )


def _target(
    object_id: str,
    object_type: str,
    score: int,
    *,
    visibility_class: str = "",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.replace("_", " ").title(),
        object_type=object_type,
        image="",
        magnitude="8.0",
        distance="",
        max_altitude="55 gradi",
        direction="Sud",
        best_time="22:30",
        observing_window="21:00 - 02:00",
        notes="Deterministic Detail NSOM fixture.",
        recommended_setup="Telescopio",
        visibility_class=visibility_class,
        azimuth="180 gradi",
        time_above_horizon="4 h",
        visible=True,
        score=score,
        score_label="Buono",
        difficulty="Media",
        recommended_setup_type="Telescope",
        apparent_size="20 arcmin",
    )


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Buono",
        score_value=score,
        explanation="Deterministic Detail NSOM weather fixture.",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=8,
        humidity=55,
        temperature_c=12.0,
        alert="",
    )


def _sky_quality(bortle: int, *, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=6.2,
        sky_brightness=21.2,
        source="deterministic_fixture",
        description="Deterministic Detail NSOM sky fixture.",
        confidence="high",
        viirs_radiance=radiance,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="18:00",
        set_time="06:00",
        best_note="Fixture Moon.",
        image="",
        phase_angle=90.0,
    )


def _telescope(
    *,
    name: str = "Medium GoTo",
    aperture_mm: int = 130,
    focal_length_mm: int = 900,
    mount: str = "GoTo EQ",
) -> Telescope:
    return Telescope(
        id=name.casefold().replace(" ", "-"),
        name=name,
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Reflector",
        mount=mount,
    )


def _observable(comparison: dict[str, object]) -> float:
    return float(comparison["nsom"]["observable_target_value"]["value"])


def _practical(comparison: dict[str, object]) -> float:
    return float(comparison["nsom"]["practical_target_value"]["value"])


def _legacy_display(comparison: dict[str, object]) -> float:
    return float(comparison["legacy"]["selected_object_detail"]["display_score"])


if __name__ == "__main__":
    write_markdown_report()
