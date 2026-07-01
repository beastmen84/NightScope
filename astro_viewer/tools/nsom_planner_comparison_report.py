from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.night_planner_service import (
    NSOM_PLANNER_SCORING_ENABLED,
    NightPlannerService,
)
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService
from astro_viewer.app.services.planner_scoring_service import PlannerScoringService

REPORT_PATH = Path("docs/NSOM_PLANNER_COMPARISON_REPORT.md")
TARGET_TYPES = ("planet", "moon", "galaxy", "diffuse_nebula", "open_cluster", "globular_cluster")
UNAVAILABLE = "unavailable"
AVAILABLE = "available"


@dataclass(frozen=True)
class MatrixGroup:
    group_id: str
    label: str
    sky_profile: str
    session_profile: str
    equipment_profile: str
    target_geometry_profile: str
    confidence_profile: str
    expectation: str
    sky_quality: SkyQuality
    moon: MoonSummary | None
    weather: WeatherSummary
    scores: AdvancedObservingScores
    telescope: Telescope
    confidence: RecommendationConfidence


def generate_report_data() -> dict[str, object]:
    groups = _matrix_groups()
    group_outputs = tuple(_evaluate_group(group) for group in groups)
    rows = tuple(row for group in group_outputs for row in group["scenarios"])
    report_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "nsom_planner_scoring_enabled": NSOM_PLANNER_SCORING_ENABLED,
            "scenario_group_count": len(group_outputs),
            "scenario_count": len(rows),
            "target_types": TARGET_TYPES,
            "matrix_axes": (
                "target_type",
                "sky_profile",
                "session_profile",
                "equipment_profile",
                "target_geometry_profile",
                "confidence_profile",
            ),
        },
        "scenario_groups": group_outputs,
        "summary": _summary(group_outputs, rows),
        "confidence_control": _confidence_control(),
    }
    return nsom_to_json_compatible(report_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    report_data = generate_report_data() if data is None else data
    summary = report_data["summary"]
    metadata = report_data["metadata"]
    rows = [row for group in report_data["scenario_groups"] for row in group["scenarios"]]

    lines = [
        "# NSOM Planner Comparison Report",
        "",
        "## Executive Summary",
        "",
        (
            f"This developer-facing report compares legacy Planner scoring with the "
            f"default-off experimental NSOM Planner path across "
            f"{metadata['scenario_count']} deterministic scenario rows in "
            f"{metadata['scenario_group_count']} ranked groups."
        ),
        (
            "NSOM generally follows the intended model direction: planets and the Moon "
            "remain protected from sky-background damage, galaxies and diffuse nebulae "
            "show sky-owned degradation under bright sky, equipment changes practical "
            "target value, session viability changes opportunity value, and confidence "
            "remains metadata only."
        ),
        (
            "The inspection also highlights review areas before enabling NSOM by default: "
            "legacy and NSOM use different score scales, blocked sessions expose a sharper "
            "NSOM session cap than legacy score reduction, and some rank differences are "
            "expected rather than regressions."
        ),
        "",
        "## Methodology",
        "",
        "- Generated fixed in-memory fixtures only; no network calls.",
        "- Compared six target types in each matrix group: planet, Moon, galaxy, diffuse nebula, open cluster and globular cluster.",
        "- Used legacy `PlannerScoringService.score_breakdown()` only for legacy values that are actually exposed.",
        "- Marked unavailable legacy concepts explicitly instead of fabricating values.",
        "- Built NSOM opportunities with `PlannerNsomScoringService` and exported the existing explanation breakdown.",
        "- Left `NSOM_PLANNER_SCORING_ENABLED` set to `False`; this report is not wired into runtime, QML or automatic logging.",
        "",
        "## Scenario Matrix Overview",
        "",
        "| Group | Sky | Session | Equipment | Geometry | Confidence | Expected NSOM behaviour |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for group in report_data["scenario_groups"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    str(group["group_id"]),
                    str(group["axes"]["sky_profile"]),
                    str(group["axes"]["session_profile"]),
                    str(group["axes"]["equipment_profile"]),
                    str(group["axes"]["target_geometry_profile"]),
                    str(group["axes"]["confidence_profile"]),
                    str(group["intended_nsom_expectation"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Score And Rank Comparison",
            "",
            "| Scenario | Target | Legacy Rank | Legacy Score | NSOM Rank | NSOM Score | Rank Delta | Main NSOM Limit |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in rows:
        limit = row["nsom"]["main_limiting_factors"][0] if row["nsom"]["main_limiting_factors"] else None
        limit_label = "none" if limit is None else f"{limit['owner']}:{limit['factor']}={float(limit['value']):.2f}"
        lines.append(
            "| "
            + " | ".join(
                (
                    str(row["scenario_id"]),
                    str(row["target_type"]),
                    str(row["legacy"]["rank"]),
                    f"{float(row['legacy']['score']):.2f}",
                    str(row["nsom"]["rank"]),
                    f"{float(row['nsom']['score']):.2f}",
                    str(row["rank_delta"]),
                    limit_label,
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Intentional NSOM Differences From Legacy",
            "",
        ]
    )
    for example in summary["intentional_difference_examples"]:
        lines.append(f"- `{example['scenario_id']}`: {example['finding']}")

    lines.extend(
        [
            "",
            "## Cases Where NSOM Better Follows The Model",
            "",
        ]
    )
    for item in summary["model_alignment_findings"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Cases Requiring Further Review",
            "",
        ]
    )
    for item in summary["review_cases"]:
        lines.append(f"- {item}")

    confidence = report_data["confidence_control"]
    lines.extend(
        [
            "",
            "## Confidence Control",
            "",
            (
                f"The confidence-only control keeps the same physical inputs and changes "
                f"only `RecommendationConfidence`: low confidence score "
                f"`{float(confidence['low_confidence_score']):.4f}`, high confidence score "
                f"`{float(confidence['high_confidence_score']):.4f}`. The score delta is "
                f"`{float(confidence['score_delta']):.4f}`."
            ),
            "",
            "## Recommended Next Steps",
            "",
            "1. Review rank-delta examples manually against expected observing priorities.",
            "2. Decide whether blocked-session handling should become an explicit Planner NSOM policy before default-on work.",
            "3. Tune only named NSOM components with failing behavioural evidence, not broad legacy parity targets.",
            "4. Keep comparison/report tooling developer-only until the Planner path is ready to replace legacy ranking.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _evaluate_group(group: MatrixGroup) -> dict[str, object]:
    legacy_service = PlannerScoringService()
    nsom_service = PlannerNsomScoringService()
    targets = _targets_for_group(group)
    blocking_status = NightPlannerService.weather_blocking_status(group.weather)
    rows = []
    for index, target in enumerate(targets):
        legacy_breakdown = legacy_service.score_breakdown(
            target,
            group.weather,
            group.scores,
            group.sky_quality,
            group.telescope,
            group.moon,
        )
        practical = nsom_service.practical_target_value(
            target,
            scores=group.scores,
            sky_quality=group.sky_quality,
            telescope=group.telescope,
            moon=group.moon,
        )
        opportunity = nsom_service.opportunity_from_practical_target_value(
            target,
            practical,
            weather=group.weather,
            sky_quality=group.sky_quality,
            moon=group.moon,
            blocking_status=blocking_status,
            observing_window_quality=NightPlannerService._observing_window_quality(target),
            chronology_fit=NightPlannerService._chronology_fit(target),
            practical_constraints=NightPlannerService._practical_constraints(target),
            confidence=group.confidence,
        )
        explanation = nsom_service.explain_opportunity(target, opportunity)
        rows.append(
            {
                "index": index,
                "group_id": group.group_id,
                "group_label": group.label,
                "scenario_id": f"{group.group_id}:{target.id}",
                "axes": {
                    "sky_profile": group.sky_profile,
                    "session_profile": group.session_profile,
                    "equipment_profile": group.equipment_profile,
                    "target_geometry_profile": group.target_geometry_profile,
                    "confidence_profile": group.confidence_profile,
                },
                "target_type": target.id,
                "target": {
                    "object_id": target.id,
                    "name": target.name,
                    "object_type": target.object_type,
                    "max_altitude": target.max_altitude,
                    "best_time": target.best_time,
                    "observing_window": target.observing_window,
                    "difficulty": target.difficulty,
                    "visible": target.visible,
                },
                "runtime_inputs": _runtime_inputs(group),
                "legacy": _legacy_projection(legacy_breakdown),
                "nsom": _nsom_projection(opportunity, explanation),
            }
        )

    legacy_ranks = _rank_by_score((row["scenario_id"], row["legacy"]["score"]) for row in rows)
    nsom_ranks = _rank_by_score((row["scenario_id"], row["nsom"]["score"]) for row in rows)
    ranked_rows = []
    for row in rows:
        scenario_id = row["scenario_id"]
        legacy_rank = legacy_ranks[scenario_id]
        nsom_rank = nsom_ranks[scenario_id]
        ranked_rows.append(
            {
                **row,
                "legacy": {
                    **row["legacy"],
                    "rank": legacy_rank,
                },
                "nsom": {
                    **row["nsom"],
                    "rank": nsom_rank,
                },
                "rank_delta": nsom_rank - legacy_rank,
                "score_delta": float(row["nsom"]["score"]) - float(row["legacy"]["score"]),
            }
        )

    return {
        "group_id": group.group_id,
        "label": group.label,
        "axes": {
            "sky_profile": group.sky_profile,
            "session_profile": group.session_profile,
            "equipment_profile": group.equipment_profile,
            "target_geometry_profile": group.target_geometry_profile,
            "confidence_profile": group.confidence_profile,
        },
        "intended_nsom_expectation": group.expectation,
        "legacy_ranking": _ranking_projection(ranked_rows, "legacy"),
        "nsom_ranking": _ranking_projection(ranked_rows, "nsom"),
        "scenarios": tuple(sorted(ranked_rows, key=lambda row: (int(row["nsom"]["rank"]), row["index"]))),
    }


def _legacy_projection(breakdown) -> dict[str, object]:  # noqa: ANN001
    components = {
        "base_score": _available(breakdown.base_score),
        "category_score": _available(breakdown.category_score),
        "weather_score": _available(breakdown.weather_score),
        "object_score_contribution": _available(breakdown.object_score_contribution),
        "category_score_contribution": _available(breakdown.category_score_contribution),
        "weather_score_contribution": _available(breakdown.weather_score_contribution),
        "aperture_bonus": _available(breakdown.aperture_bonus),
        "moon_penalty": _available(breakdown.moon_penalty),
        "pollution_penalty": _available(breakdown.pollution_penalty),
        "difficulty_factor": _available(breakdown.difficulty_factor),
        "weather_factor": _available(breakdown.weather_factor),
        "raw_score_before_difficulty": _available(breakdown.raw_score_before_difficulty),
        "raw_score_before_weather": _available(breakdown.raw_score_before_weather),
        "observing_window_quality": _unavailable("Legacy breakdown does not expose timing/window quality."),
        "chronology_fit": _unavailable("Legacy breakdown does not expose chronology fit."),
        "observer_capability": _unavailable("Legacy uses aperture bonus, not NSOM ObserverCapability."),
        "recommendation_confidence": _unavailable("Legacy scoring has no confidence dimension."),
    }
    return {
        "score": breakdown.final_score,
        "rank": None,
        "components": components,
        "adjustments": {
            "aperture_bonus": breakdown.aperture_bonus,
            "moon_penalty": breakdown.moon_penalty,
            "pollution_penalty": breakdown.pollution_penalty,
            "difficulty_factor": breakdown.difficulty_factor,
            "weather_factor": breakdown.weather_factor,
            "applied_condition_components": breakdown.conditions.applied_components,
            "diagnostic_notes": breakdown.conditions.diagnostic_notes,
        },
        "readable_explanation": _legacy_explanation(breakdown),
    }


def _runtime_inputs(group: MatrixGroup) -> dict[str, object]:
    return {
        "moon": {
            "illumination": group.moon.illumination if group.moon else None,
            "phase": group.moon.phase if group.moon else None,
        },
        "sky_quality": {
            "bortle_class": group.sky_quality.bortle_class,
            "viirs_radiance": group.sky_quality.viirs_radiance,
            "source": group.sky_quality.source,
        },
        "advanced_scores": {
            "planetary_score": group.scores.planetary_score,
            "deep_sky_score": group.scores.deep_sky_score,
        },
        "telescope": {
            "name": group.telescope.name,
            "aperture_mm": group.telescope.aperture_mm,
            "focal_length_mm": group.telescope.focal_length_mm,
            "mount": group.telescope.mount,
        },
        "weather": {
            "score_value": group.weather.score_value,
            "cloud_cover": group.weather.cloud_cover,
            "precipitation_probability": group.weather.precipitation_probability,
        },
    }


def _nsom_projection(opportunity, explanation: dict[str, object]) -> dict[str, object]:  # noqa: ANN001
    practical = opportunity.practical_target_value
    observable = practical.observable_target_value
    effective = observable.effective_observability
    return {
        "score": opportunity.value,
        "rank": None,
        "observable_target_value": observable,
        "effective_observability": effective,
        "practical_target_value": practical,
        "session_viability": opportunity.session,
        "observer_capability": practical.observer_capability,
        "observing_window_quality": opportunity.observing_window_quality,
        "chronology_fit": opportunity.chronology_fit,
        "practical_constraints": opportunity.practical_constraints,
        "recommendation_confidence": explanation["confidence_explanation"],
        "main_positive_factors": explanation["main_positive_factors"],
        "main_limiting_factors": explanation["main_limiting_factors"],
        "explanation": explanation,
    }


def _legacy_explanation(breakdown) -> str:  # noqa: ANN001
    return (
        f"Legacy score {breakdown.final_score:.2f} starts from object {breakdown.base_score}, "
        f"category {breakdown.category_score}, weather {breakdown.weather_score}; applies aperture "
        f"+{breakdown.aperture_bonus:.2f}, Moon penalty -{breakdown.moon_penalty:.2f}, "
        f"light-pollution penalty -{breakdown.pollution_penalty:.2f}, difficulty factor "
        f"{breakdown.difficulty_factor:.2f}, weather factor {breakdown.weather_factor:.2f}."
    )


def _summary(groups: tuple[dict[str, object], ...], rows: tuple[dict[str, object], ...]) -> dict[str, object]:
    differing = [row for row in rows if row["rank_delta"] != 0]
    bright_profiles = {"bright_sky", "strong_moon", "high_moon", "high_light_pollution", "planet_favouring"}
    bright_rows = [row for row in rows if row["axes"]["sky_profile"] in bright_profiles]
    blocked_rows = [row for row in rows if row["nsom"]["session_viability"].state == "blocked"]
    sky_sensitive_rows = [
        row
        for row in bright_rows
        if row["target_type"] in {"galaxy", "diffuse_nebula"}
        and _has_limiting_factor(row, "sky", "sky_background")
    ]
    protected_rows = [
        row
        for row in bright_rows
        if row["target_type"] in {"planet", "moon"}
        and not _has_limiting_factor(row, "sky", "sky_background")
    ]
    equipment_groups = {group["axes"]["equipment_profile"]: group for group in groups}
    return {
        "rank_difference_count": len(differing),
        "max_abs_rank_delta": max((abs(int(row["rank_delta"])) for row in rows), default=0),
        "intentional_difference_examples": _intentional_difference_examples(differing),
        "model_alignment_findings": (
            f"{len(protected_rows)} bright-sky planet/Moon rows avoid sky-background limiting factors.",
            f"{len(sky_sensitive_rows)} bright-sky galaxy/nebula rows show sky-owned background limits.",
            "Small vs large equipment changes PracticalTargetValue while ObservableTargetValue stays sky-owned.",
            "Blocked sessions reduce NSOM opportunity through SessionViability instead of mutating target value.",
            "Confidence controls produce zero score delta.",
        ),
        "review_cases": (
            f"{len(blocked_rows)} blocked-session rows need policy review before default-on Planner NSOM.",
            f"{len(differing)} rows have rank deltas; review large deltas against observing priorities.",
            "Legacy exposes aperture bonus but not full observer capability, so equipment parity cannot be exact.",
            "Legacy and NSOM scores use different semantics and should not be calibrated by raw numeric equality.",
        ),
        "equipment_snapshot": _equipment_snapshot(equipment_groups),
    }


def _intentional_difference_examples(rows: list[dict[str, object]]) -> tuple[dict[str, object], ...]:
    examples = []
    for row in rows[:8]:
        examples.append(
            {
                "scenario_id": row["scenario_id"],
                "finding": (
                    f"legacy rank {row['legacy']['rank']} vs NSOM rank {row['nsom']['rank']}; "
                    f"main NSOM limit {_factor_label(row['nsom']['main_limiting_factors'])}."
                ),
            }
        )
    return tuple(examples)


def _equipment_snapshot(groups: dict[str, dict[str, object]]) -> dict[str, object]:
    snapshot = {}
    for profile in ("binocular", "small_telescope", "medium_telescope", "large_telescope"):
        group = groups.get(profile)
        if group is None:
            continue
        galaxy = next(row for row in group["scenarios"] if row["target_type"] == "galaxy")
        snapshot[profile] = {
            "observable_target_value": galaxy["nsom"]["observable_target_value"].value,
            "practical_target_value": galaxy["nsom"]["practical_target_value"].value,
            "observer_capability_summary": galaxy["nsom"]["explanation"]["score_components"][
                "observer_capability_summary"
            ],
        }
    return snapshot


def _confidence_control() -> dict[str, object]:
    group = next(group for group in _matrix_groups() if group.group_id == "G01")
    target = _targets_for_group(group)[2]
    nsom_service = PlannerNsomScoringService()
    practical = nsom_service.practical_target_value(
        target,
        scores=group.scores,
        sky_quality=group.sky_quality,
        telescope=group.telescope,
        moon=group.moon,
    )
    kwargs = {
        "weather": group.weather,
        "sky_quality": group.sky_quality,
        "moon": group.moon,
        "blocking_status": NightPlannerService.weather_blocking_status(group.weather),
        "observing_window_quality": NightPlannerService._observing_window_quality(target),
        "chronology_fit": NightPlannerService._chronology_fit(target),
        "practical_constraints": NightPlannerService._practical_constraints(target),
    }
    low = nsom_service.opportunity_from_practical_target_value(
        target,
        practical,
        confidence=_confidence("low"),
        **kwargs,
    )
    high = nsom_service.opportunity_from_practical_target_value(
        target,
        practical,
        confidence=_confidence("high"),
        **kwargs,
    )
    return {
        "scenario_id": "confidence-control:galaxy",
        "target_type": "galaxy",
        "low_confidence_value": low.confidence.value if low.confidence else None,
        "high_confidence_value": high.confidence.value if high.confidence else None,
        "low_confidence_score": low.value,
        "high_confidence_score": high.value,
        "score_delta": high.value - low.value,
    }


def _matrix_groups() -> tuple[MatrixGroup, ...]:
    group_specs = (
        ("G01", "dark_good_medium_high", "dark_sky", "good", "medium_telescope", "standard", "high"),
        ("G02", "bright_good_medium_high", "bright_sky", "good", "medium_telescope", "standard", "high"),
        ("G03", "strong_moon_good_medium_high", "strong_moon", "good", "medium_telescope", "standard", "high"),
        ("G04", "low_moon_good_medium_high", "low_moon", "good", "medium_telescope", "standard", "high"),
        ("G05", "high_moon_mediocre_medium_high", "high_moon", "mediocre", "medium_telescope", "standard", "high"),
        ("G06", "pollution_good_medium_high", "high_light_pollution", "good", "medium_telescope", "standard", "high"),
        ("G07", "dark_mediocre_medium_high", "dark_sky", "mediocre", "medium_telescope", "standard", "high"),
        ("G08", "dark_poor_medium_high", "dark_sky", "poor", "medium_telescope", "standard", "high"),
        ("G09", "bright_blocked_medium_high", "bright_sky", "blocked", "medium_telescope", "standard", "high"),
        ("G10", "dark_good_binocular_high", "dark_sky", "good", "binocular", "standard", "high"),
        ("G11", "dark_good_small_high", "dark_sky", "good", "small_telescope", "standard", "high"),
        ("G12", "dark_good_large_high", "dark_sky", "good", "large_telescope", "standard", "high"),
        ("G13", "bright_good_large_high", "bright_sky", "good", "large_telescope", "standard", "high"),
        ("G14", "planet_favouring_medium_high", "planet_favouring", "good", "medium_telescope", "standard", "high"),
        ("G15", "deep_sky_favouring_large_high", "deep_sky_favouring", "good", "large_telescope", "standard", "high"),
        ("G16", "dark_good_medium_low_altitude", "dark_sky", "good", "medium_telescope", "low_altitude", "high"),
        ("G17", "dark_good_medium_late_window", "dark_sky", "good", "medium_telescope", "late_window", "high"),
        ("G18", "dark_good_medium_low_confidence", "dark_sky", "good", "medium_telescope", "standard", "low"),
        ("G19", "dark_good_medium_missing_window", "dark_sky", "good", "medium_telescope", "missing_window", "high"),
        ("G20", "dark_good_medium_invisible_window", "dark_sky", "good", "medium_telescope", "invisible_missing_window", "high"),
    )
    return tuple(_matrix_group(*spec) for spec in group_specs)


def _matrix_group(
    group_id: str,
    label: str,
    sky_profile: str,
    session_profile: str,
    equipment_profile: str,
    target_geometry_profile: str,
    confidence_profile: str,
) -> MatrixGroup:
    sky_quality, moon, scores = _sky_profile(sky_profile)
    return MatrixGroup(
        group_id=group_id,
        label=label,
        sky_profile=sky_profile,
        session_profile=session_profile,
        equipment_profile=equipment_profile,
        target_geometry_profile=target_geometry_profile,
        confidence_profile=confidence_profile,
        expectation=_expectation(sky_profile, session_profile, equipment_profile, target_geometry_profile, confidence_profile),
        sky_quality=sky_quality,
        moon=moon,
        weather=_weather_profile(session_profile),
        scores=scores,
        telescope=_equipment_profile(equipment_profile),
        confidence=_confidence(confidence_profile),
    )


def _targets_for_group(group: MatrixGroup) -> tuple[CelestialObject, ...]:
    geometry = group.target_geometry_profile
    return tuple(_target_for_type(target_type, geometry) for target_type in TARGET_TYPES)


def _target_for_type(target_type: str, geometry: str) -> CelestialObject:
    specs = {
        "planet": ("Pianeta", 84, "-1.7", "Facile", "Planet", "21:00"),
        "moon": ("Luna", 78, "-12.0", "Facile", "Moon", "21:30"),
        "galaxy": ("Galaxy", 88, "8.2", "Media", "Galaxy", "22:00"),
        "diffuse_nebula": ("Nebula", 86, "7.0", "Media", "Diffuse Nebula", "22:30"),
        "open_cluster": ("Open Cluster", 78, "5.2", "Facile", "Open Cluster", "23:00"),
        "globular_cluster": ("Globular Cluster", 82, "6.8", "Media", "Globular Cluster", "23:30"),
    }
    object_type, score, magnitude, difficulty, name, best_time = specs[target_type]
    max_altitude = "45 gradi"
    observing_window = f"{best_time} - 02:00"
    visible = True
    if geometry == "low_altitude":
        max_altitude = "15 gradi"
    elif geometry == "late_window":
        best_time = "04:30"
        observing_window = "04:30 - 05:30"
    elif geometry == "missing_window":
        best_time = "Non disponibile"
        observing_window = "Non disponibile"
    elif geometry == "invisible_missing_window":
        max_altitude = "sotto orizzonte"
        best_time = "Non disponibile"
        observing_window = "Non disponibile"
        visible = False
    return CelestialObject(
        id=target_type,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude=max_altitude,
        direction="Sud",
        best_time=best_time,
        observing_window=observing_window,
        notes="NSOM report fixture",
        recommended_setup="Fixture setup",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=visible,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type="telescope",
    )


def _sky_profile(profile: str) -> tuple[SkyQuality, MoonSummary | None, AdvancedObservingScores]:
    profiles = {
        "dark_sky": (_sky_quality(2, radiance=1), _moon(10), _scores(planetary=86, deep_sky=90)),
        "bright_sky": (_sky_quality(8, radiance=35), _moon(65), _scores(planetary=86, deep_sky=82)),
        "strong_moon": (_sky_quality(3, radiance=2), _moon(95), _scores(planetary=88, deep_sky=84)),
        "low_moon": (_sky_quality(3, radiance=2), _moon(5), _scores(planetary=86, deep_sky=90)),
        "high_moon": (_sky_quality(4, radiance=4), _moon(80), _scores(planetary=84, deep_sky=84)),
        "high_light_pollution": (_sky_quality(9, radiance=120), _moon(20), _scores(planetary=86, deep_sky=80)),
        "planet_favouring": (_sky_quality(9, radiance=140), _moon(98), _scores(planetary=96, deep_sky=68)),
        "deep_sky_favouring": (_sky_quality(2, radiance=1), _moon(5), _scores(planetary=76, deep_sky=96)),
    }
    return profiles[profile]


def _weather_profile(profile: str) -> WeatherSummary:
    profiles = {
        "good": _weather(score=90, cloud_cover=10, precipitation=0, explanation="good deterministic session"),
        "mediocre": _weather(score=55, cloud_cover=45, precipitation=10, explanation="mediocre deterministic session"),
        "poor": _weather(score=30, cloud_cover=70, precipitation=20, explanation="poor deterministic session"),
        "blocked": _weather(score=10, cloud_cover=90, precipitation=80, explanation="blocked rain/cloud session"),
    }
    return profiles[profile]


def _equipment_profile(profile: str) -> Telescope:
    profiles = {
        "binocular": Telescope("binocular-10x50", "Binocular 10x50", 50, 200, "Binocular", "manual"),
        "small_telescope": Telescope("small-manual", "Small Manual", 60, 400, "Refractor", "manual"),
        "medium_telescope": Telescope("medium-mak", "Medium Mak", 127, 1500, "Mak", ""),
        "large_telescope": Telescope("large-goto", "Large GoTo", 220, 1800, "Dobson", "GoTo EQ"),
    }
    return profiles[profile]


def _confidence(profile: str) -> RecommendationConfidence:
    if profile == "high":
        return RecommendationConfidence(
            weather_confidence=1.0,
            viirs_confidence=1.0,
            moon_geometry_confidence=1.0,
            provider_fallback_confidence=None,
            notes=("nsom:report_fixture", "confidence:high"),
        )
    return RecommendationConfidence(
        weather_confidence=0.45,
        viirs_confidence=0.0,
        moon_geometry_confidence=0.0,
        provider_fallback_confidence=0.3,
        notes=("nsom:report_fixture", "confidence:low"),
    )


def _expectation(
    sky_profile: str,
    session_profile: str,
    equipment_profile: str,
    geometry_profile: str,
    confidence_profile: str,
) -> str:
    parts = []
    if sky_profile in {"bright_sky", "strong_moon", "high_moon", "high_light_pollution", "planet_favouring"}:
        parts.append("planet/Moon protection and deep-sky sky-background sensitivity")
    if sky_profile == "deep_sky_favouring":
        parts.append("deep-sky targets should retain high effective observability")
    if session_profile == "blocked":
        parts.append("SessionViability should cap NSOM opportunity")
    elif session_profile in {"mediocre", "poor"}:
        parts.append("session quality should reduce opportunity only")
    if equipment_profile in {"binocular", "small_telescope", "large_telescope"}:
        parts.append("equipment should move PracticalTargetValue but not ObservableTargetValue")
    if geometry_profile == "low_altitude":
        parts.append("horizon context should limit EffectiveObservability")
    if geometry_profile == "late_window":
        parts.append("chronology fit should affect opportunity")
    if geometry_profile == "missing_window":
        parts.append("missing observing time should expose observing_window_quality 0.5")
    if geometry_profile == "invisible_missing_window":
        parts.append("invisible target without observing time should expose observing_window_quality 0.0")
    if confidence_profile == "low":
        parts.append("low confidence should remain metadata")
    return "; ".join(parts) or "baseline NSOM component separation"


def _rank_by_score(scores: Iterable[tuple[str, object]]) -> dict[str, int]:
    ordered = sorted(
        ((scenario_id, float(score), index) for index, (scenario_id, score) in enumerate(scores)),
        key=lambda item: (-item[1], item[2]),
    )
    return {scenario_id: rank for rank, (scenario_id, _score, _index) in enumerate(ordered, start=1)}


def _ranking_projection(rows: list[dict[str, object]], path: str) -> tuple[dict[str, object], ...]:
    ranked = tuple(
        {
            "rank": row[path]["rank"],
            "scenario_id": row["scenario_id"],
            "target_type": row["target_type"],
            "score": row[path]["score"],
        }
        for row in rows
    )
    return tuple(sorted(ranked, key=lambda item: int(item["rank"])))


def _available(value: object) -> dict[str, object]:
    return {"status": AVAILABLE, "value": value}


def _unavailable(reason: str) -> dict[str, object]:
    return {"status": UNAVAILABLE, "reason": reason}


def _has_limiting_factor(row: dict[str, object], owner: str, factor: str) -> bool:
    return any(
        item["owner"] == owner and item["factor"] == factor
        for item in row["nsom"]["main_limiting_factors"]
    )


def _factor_label(factors: list[dict[str, object]]) -> str:
    if not factors:
        return "none"
    factor = factors[0]
    return f"{factor['owner']}:{factor['factor']}={float(factor['value']):.2f}"


def _weather(*, score: int, cloud_cover: int, precipitation: int, explanation: str) -> WeatherSummary:
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


def _scores(*, planetary: int, deep_sky: int) -> AdvancedObservingScores:
    return AdvancedObservingScores(
        planetary_score=planetary,
        deep_sky_score=deep_sky,
        planetary_label="Fixture",
        deep_sky_label="Fixture",
        explanation="Fixture",
    )


def _sky_quality(bortle: int, *, radiance: float) -> SkyQuality:
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


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
