from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.night_planner_service import NSOM_PLANNER_SCORING_ENABLED
from astro_viewer.app.services.planner_nsom_comparison import PlannerNsomComparisonService

CALIBRATION_SCENARIO_NAMES = (
    "bright_sky",
    "poor_session",
    "good_session",
    "small_telescope",
    "large_telescope",
    "planet_favouring_conditions",
    "deep_sky_favouring_conditions",
    "moon_target_case",
)

CALIBRATION_SCORE_COMPONENTS = (
    "practical_target_value",
    "observable_target_value",
    "effective_observability",
    "observer_capability_summary",
    "session_viability",
    "observing_window_quality",
    "chronology_fit",
    "practical_constraints",
)


@dataclass(frozen=True)
class PlannerNsomCalibrationScenario:
    name: str
    intended_nsom_expectation: str
    targets: tuple[CelestialObject, ...]
    weather: WeatherSummary
    scores: AdvancedObservingScores
    sky_quality: SkyQuality
    telescope: Telescope
    moon: MoonSummary | None


class PlannerNsomCalibrationInspectionService:
    """Developer-only NSOM Planner calibration inspection helper.

    This service is passive: it evaluates fixed in-memory fixtures through the
    comparison/explanation layer and returns JSON-compatible dictionaries. It
    does not write files, log automatically, fetch data, emit signals or expose
    anything to QML.
    """

    def __init__(self, comparison_service: PlannerNsomComparisonService | None = None) -> None:
        self._comparison_service = comparison_service or PlannerNsomComparisonService()

    def inspect(self, scenario_names: Iterable[str] | None = None) -> dict[str, object]:
        scenarios = _calibration_scenarios()
        if scenario_names is not None:
            requested = tuple(scenario_names)
            available = {scenario.name for scenario in scenarios}
            unknown = tuple(name for name in requested if name not in available)
            if unknown:
                raise ValueError(f"Unknown NSOM calibration scenario: {', '.join(unknown)}")
            requested_set = set(requested)
            scenarios = tuple(scenario for scenario in scenarios if scenario.name in requested_set)

        scenario_outputs = tuple(self._inspect_scenario(scenario) for scenario in scenarios)
        return nsom_to_json_compatible(
            {
                "scenario_groups": scenario_outputs,
                "component_ranges": _aggregate_component_ranges(scenario_outputs),
                "factor_coverage": _factor_coverage(scenario_outputs),
                "dominant_limiting_factor_summary": _dominant_limiting_factor_summary(
                    scenario_outputs
                ),
                "metadata": {
                    "developer_only": True,
                    "nsom_planner_scoring_enabled": NSOM_PLANNER_SCORING_ENABLED,
                    "scenario_count": len(scenario_outputs),
                    "scenario_names": tuple(scenario.name for scenario in scenarios),
                    "score_components": CALIBRATION_SCORE_COMPONENTS,
                    "side_effects": {
                        "file_writes": False,
                        "automatic_logging": False,
                        "network": False,
                        "qml_exposure": False,
                    },
                },
            }
        )

    def _inspect_scenario(self, scenario: PlannerNsomCalibrationScenario) -> dict[str, object]:
        comparison = self._comparison_service.compare(
            scenario.targets,
            weather=scenario.weather,
            scores=scenario.scores,
            sky_quality=scenario.sky_quality,
            telescope=scenario.telescope,
            moon=scenario.moon,
        )
        ranked = tuple(
            _inspection_row(item)
            for item in sorted(comparison["items"], key=lambda row: int(row["nsom"]["rank"]))
        )
        return {
            "name": scenario.name,
            "intended_nsom_expectation": scenario.intended_nsom_expectation,
            "ranked_nsom_opportunities": ranked,
            "component_ranges": _component_ranges(ranked),
            "dominant_limiting_factor": _dominant_limiting_factor(ranked),
            "legacy_reference_ranking": comparison["rankings"]["legacy"],
            "nsom_ranking": comparison["rankings"]["nsom"],
            "comparison_metadata": comparison["metadata"],
        }


def _inspection_row(item: dict[str, object]) -> dict[str, object]:
    nsom = item["nsom"]
    legacy = item["legacy"]
    explanation = nsom["explanation"]
    return {
        "rank": nsom["rank"],
        "object_id": item["object_id"],
        "name": item["name"],
        "object_type": item["object_type"],
        "nsom_score": nsom["score"],
        "legacy_reference": {
            "rank": legacy["rank"],
            "score": legacy["score"],
        },
        "rank_delta": item["rank_delta"],
        "score_delta": item["score_delta"],
        "score_components": explanation["score_components"],
        "component_breakdown": nsom["components"],
        "explanation": explanation,
        "limiting_factors": explanation["main_limiting_factors"],
        "positive_factors": explanation["main_positive_factors"],
    }


def _calibration_scenarios() -> tuple[PlannerNsomCalibrationScenario, ...]:
    return (
        PlannerNsomCalibrationScenario(
            name="bright_sky",
            intended_nsom_expectation=(
                "Planets and the Moon keep neutral sky-background factors; galaxies and "
                "diffuse nebulae show sky-owned degradation."
            ),
            targets=_mixed_targets(include_moon=True),
            weather=_weather(85),
            scores=_scores(planetary=86, deep_sky=88),
            sky_quality=_sky_quality(9, radiance=120),
            telescope=_telescope(),
            moon=_moon(95),
        ),
        PlannerNsomCalibrationScenario(
            name="poor_session",
            intended_nsom_expectation=(
                "Poor session viability lowers opportunity value without changing "
                "observable or practical target values."
            ),
            targets=_mixed_targets(),
            weather=_weather(20),
            scores=_scores(planetary=86, deep_sky=88),
            sky_quality=_sky_quality(3, radiance=2),
            telescope=_telescope(),
            moon=_moon(10),
        ),
        PlannerNsomCalibrationScenario(
            name="good_session",
            intended_nsom_expectation=(
                "Good session conditions keep session viability high while timing and "
                "practical constraints remain visible as opportunity components."
            ),
            targets=_mixed_targets(include_timing_variants=True),
            weather=_weather(95),
            scores=_scores(planetary=86, deep_sky=88),
            sky_quality=_sky_quality(3, radiance=2),
            telescope=_telescope(),
            moon=_moon(10),
        ),
        PlannerNsomCalibrationScenario(
            name="small_telescope",
            intended_nsom_expectation=(
                "Small manual equipment reduces observer capability and practical "
                "target value while leaving observable target value unchanged."
            ),
            targets=_deep_sky_targets(),
            weather=_weather(85),
            scores=_scores(planetary=82, deep_sky=90),
            sky_quality=_sky_quality(3, radiance=2),
            telescope=_telescope(
                name="Small Manual",
                aperture_mm=60,
                focal_length_mm=400,
                mount="manual",
            ),
            moon=_moon(10),
        ),
        PlannerNsomCalibrationScenario(
            name="large_telescope",
            intended_nsom_expectation=(
                "Large GoTo equipment improves practical target value while preserving "
                "the same observable target value for the same sky."
            ),
            targets=_deep_sky_targets(),
            weather=_weather(85),
            scores=_scores(planetary=82, deep_sky=90),
            sky_quality=_sky_quality(3, radiance=2),
            telescope=_telescope(
                name="Large GoTo",
                aperture_mm=220,
                focal_length_mm=1800,
                mount="GoTo EQ",
            ),
            moon=_moon(10),
        ),
        PlannerNsomCalibrationScenario(
            name="planet_favouring_conditions",
            intended_nsom_expectation=(
                "Bright sky and strong Moon favour compact planetary targets over "
                "sky-background-sensitive galaxies and diffuse nebulae."
            ),
            targets=_mixed_targets(include_moon=True),
            weather=_weather(88),
            scores=_scores(planetary=95, deep_sky=70),
            sky_quality=_sky_quality(9, radiance=140),
            telescope=_telescope(),
            moon=_moon(98),
        ),
        PlannerNsomCalibrationScenario(
            name="deep_sky_favouring_conditions",
            intended_nsom_expectation=(
                "Dark sky, low Moon and strong deep-sky conditions preserve high "
                "effective observability for galaxies, nebulae and clusters."
            ),
            targets=_mixed_targets(include_timing_variants=True),
            weather=_weather(92),
            scores=_scores(planetary=76, deep_sky=96),
            sky_quality=_sky_quality(2, radiance=1),
            telescope=_telescope(
                name="Large GoTo",
                aperture_mm=220,
                focal_length_mm=1800,
                mount="GoTo EQ",
            ),
            moon=_moon(5),
        ),
        PlannerNsomCalibrationScenario(
            name="moon_target_case",
            intended_nsom_expectation=(
                "Moon target explanations keep Moon and light-pollution background "
                "neutral even under bright Moon conditions."
            ),
            targets=(
                _target("moon", "Luna", 82, magnitude="-12.0", best_time="22:00"),
                _target("planet", "Pianeta", 80, magnitude="-1.0", best_time="21:00"),
                _target("galaxy", "Galaxy", 84, magnitude="8.2", best_time="21:30"),
            ),
            weather=_weather(88),
            scores=_scores(planetary=90, deep_sky=80),
            sky_quality=_sky_quality(9, radiance=120),
            telescope=_telescope(),
            moon=_moon(95),
        ),
    )


def _component_ranges(rows: tuple[dict[str, object], ...]) -> dict[str, object]:
    ranges: dict[str, object] = {}
    for component in CALIBRATION_SCORE_COMPONENTS:
        values = [float(row["score_components"][component]) for row in rows]
        minimum = min(values) if values else None
        maximum = max(values) if values else None
        ranges[component] = {
            "min": minimum,
            "max": maximum,
            "range": None if minimum is None or maximum is None else maximum - minimum,
        }
    return ranges


def _aggregate_component_ranges(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    rows = tuple(
        row
        for scenario in scenarios
        for row in scenario["ranked_nsom_opportunities"]
    )
    return _component_ranges(rows)


def _dominant_limiting_factor(rows: tuple[dict[str, object], ...]) -> object:
    factors = tuple(factor for row in rows for factor in row["limiting_factors"])
    if not factors:
        return None
    factor = min(factors, key=lambda item: float(item["value"]))
    return {
        "owner": factor["owner"],
        "component": factor["component"],
        "factor": factor["factor"],
        "value": factor["value"],
    }


def _factor_coverage(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    limiting = set()
    positive = set()
    owners = set()
    for scenario in scenarios:
        for row in scenario["ranked_nsom_opportunities"]:
            for factor in row["limiting_factors"]:
                owners.add(factor["owner"])
                limiting.add(f"{factor['owner']}:{factor['factor']}")
            for factor in row["positive_factors"]:
                owners.add(factor["owner"])
                positive.add(f"{factor['owner']}:{factor['factor']}")
    return {
        "owners": tuple(sorted(owners)),
        "limiting_factors": tuple(sorted(limiting)),
        "positive_factors": tuple(sorted(positive)),
    }


def _dominant_limiting_factor_summary(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    factor_counts: dict[str, int] = {}
    owner_counts: dict[str, int] = {}
    for scenario in scenarios:
        dominant = scenario["dominant_limiting_factor"]
        if dominant is None:
            continue
        factor_key = f"{dominant['owner']}:{dominant['factor']}"
        factor_counts[factor_key] = factor_counts.get(factor_key, 0) + 1
        owner = str(dominant["owner"])
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
    return {
        "by_factor": dict(sorted(factor_counts.items())),
        "by_owner": dict(sorted(owner_counts.items())),
    }


def _mixed_targets(
    *,
    include_moon: bool = False,
    include_timing_variants: bool = False,
) -> tuple[CelestialObject, ...]:
    targets = [
        _target("planet", "Pianeta", 84, magnitude="-1.7", best_time="21:00", difficulty="Facile"),
        _target("galaxy", "Galaxy", 88, magnitude="8.2", best_time="21:30", difficulty="Media"),
        _target("diffuse-nebula", "Nebula", 86, magnitude="7.0", best_time="22:00", difficulty="Media"),
        _target("open-cluster", "Open Cluster", 78, magnitude="5.2", best_time="23:00", difficulty="Facile"),
    ]
    if include_moon:
        targets.append(
            _target("moon", "Luna", 78, magnitude="-12.0", best_time="22:30", difficulty="Facile")
        )
    if include_timing_variants:
        targets.extend(
            (
                _target("late-galaxy", "Galaxy", 82, magnitude="9.0", best_time="04:30", difficulty="Difficile"),
                _target(
                    "unknown-window-cluster",
                    "Open Cluster",
                    74,
                    magnitude="6.0",
                    best_time="not available",
                    difficulty="Facile",
                    observing_window="",
                ),
            )
        )
    return tuple(targets)


def _deep_sky_targets() -> tuple[CelestialObject, ...]:
    return (
        _target("galaxy", "Galaxy", 88, magnitude="8.2", best_time="21:30", difficulty="Media"),
        _target("diffuse-nebula", "Nebula", 86, magnitude="7.0", best_time="22:00", difficulty="Media"),
        _target("open-cluster", "Open Cluster", 78, magnitude="5.2", best_time="23:00", difficulty="Facile"),
    )


def _target(
    object_id: str,
    object_type: str,
    score: int,
    *,
    magnitude: str = "8.0",
    best_time: str = "21:00",
    difficulty: str = "Media",
    observing_window: str | None = None,
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
        observing_window=observing_window if observing_window is not None else f"{best_time} - 02:00",
        notes="NSOM calibration fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
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


def _scores(planetary: int, deep_sky: int) -> AdvancedObservingScores:
    return AdvancedObservingScores(
        planetary_score=planetary,
        deep_sky_score=deep_sky,
        planetary_label="Fixture",
        deep_sky_label="Fixture",
        explanation="Fixture",
    )


def _sky_quality(bortle: int, *, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="Fixture",
        description="Fixture",
        viirs_radiance=radiance,
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


def _telescope(
    *,
    name: str = "Test Scope",
    aperture_mm: int = 127,
    focal_length_mm: int = 1500,
    mount: str = "",
) -> Telescope:
    return Telescope(
        id=name.lower().replace(" ", "-"),
        name=name,
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Mak",
        mount=mount,
    )
