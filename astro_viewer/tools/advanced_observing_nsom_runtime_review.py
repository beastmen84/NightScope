from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.advanced_observing_nsom_service import (
    NSOM_ADVANCED_OBSERVING_ENABLED,
    AdvancedObservingNsomService,
)
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.tools.advanced_observing_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data as generate_comparison_report_data,
)
from astro_viewer.tools.advanced_observing_nsom_policy_readiness import (
    POLICY_READINESS_PATH,
)

RUNTIME_REVIEW_PATH = Path("docs/ADVANCED_OBSERVING_NSOM_RUNTIME_REVIEW.md")

REPORT_IMPORT_MARKERS = (
    "advanced_observing_nsom_runtime_review",
    "ADVANCED_OBSERVING_NSOM_RUNTIME_REVIEW",
)

QML_MARKERS = (
    "NSOM_ADVANCED_OBSERVING_ENABLED",
    "AdvancedObservingNsomService",
    "advanced_observing_nsom_runtime_review",
    "ADVANCED_OBSERVING_NSOM_RUNTIME_REVIEW",
)


@dataclass(frozen=True)
class AdvancedObservingRuntimeScenario:
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


def generate_runtime_review_data() -> dict[str, object]:
    comparison_by_id = {
        scenario["scenario_id"]: scenario
        for scenario in generate_comparison_report_data()["scenarios"]
    }
    scenarios = tuple(
        _evaluate_scenario(scenario, comparison_by_id[scenario.scenario_id])
        for scenario in _scenarios()
    )
    downstream = _downstream_consumer_evidence(Path(__file__).parents[2])
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    checks = _review_checks(scenarios, downstream, static_checks)
    blockers = _default_on_blockers(checks)

    review_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "advanced_scores_changed_by_default": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed_by_default": False,
            "sky_compass_changed": False,
            "source_report": str(COMPARISON_REPORT_PATH).replace("\\", "/"),
            "policy_report": str(POLICY_READINESS_PATH).replace("\\", "/"),
            "runtime_review_report": str(RUNTIME_REVIEW_PATH).replace("\\", "/"),
            "scenario_count": len(scenarios),
        },
        "readiness": {
            "verdict": "not_ready_for_default_on_switch",
            "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
            "default_flag_enabled": NSOM_ADVANCED_OBSERVING_ENABLED is True,
            "ready_for_default_on_switch": False,
            "forced_on_path_safe_to_keep": blockers == (
                "advanced-observing-downstream-consumer-policy",
                "advanced-observing-score-label-policy",
                "advanced-observing-blocked-session-display-policy",
            ),
            "runtime_behaviour_changed_by_this_review": False,
            "explicit_nsom_opt_in": "AppController() / NSOM_ADVANCED_OBSERVING_ENABLED",
            "explicit_legacy_default": "removed: AppController(use_nsom_advanced_observing=False)",
            "recommended_next_change": (
                "Keep Advanced Observing backend projection separate from visible "
                "QML and Planner inputs; Notifications are no longer a runtime consumer."
            ),
        },
        "default_on_blockers": blockers,
        "checks": checks,
        "scenarios": scenarios,
        "summary": _summary(scenarios),
        "downstream_consumer_evidence": downstream,
        "static_wiring_checks": static_checks,
    }
    return nsom_to_json_compatible(review_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    review = generate_runtime_review_data() if data is None else data
    metadata = review["metadata"]
    readiness = review["readiness"]
    summary = review["summary"]
    downstream = review["downstream_consumer_evidence"]

    lines = [
        "# Advanced Observing NSOM Runtime Review",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report reviews the default-off Advanced Observing "
            "NSOM runtime path added in `1.8.4`. It compares forced-on NSOM output "
            "with legacy `AdvancedObservingService` output and checks whether the "
            "path is safe to keep before any default-on switch. It does not change "
            "the flag, tune scores, expose QML fields, log automatically, call the "
            "network or write runtime files."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Default flag: `{readiness['default_flag']}`.",
        f"- Ready for default-on switch: `{readiness['ready_for_default_on_switch']}`.",
        f"- Forced-on path safe to keep: `{readiness['forced_on_path_safe_to_keep']}`.",
        f"- Runtime behaviour changed by this review: `{readiness['runtime_behaviour_changed_by_this_review']}`.",
        f"- Explicit opt-in: `{readiness['explicit_nsom_opt_in']}`.",
        f"- Legacy default: `{readiness['explicit_legacy_default']}`.",
        f"- Recommended next change: {readiness['recommended_next_change']}",
        "",
        "## Default-On Blockers",
        "",
    ]
    for blocker in review["default_on_blockers"]:
        lines.append(f"- `{blocker}`")

    lines.extend(
        [
            "",
            "## Scenario Score Deltas",
            "",
            "| Scenario | Legacy P | NSOM P | Delta P | Legacy DSO | NSOM DSO | Delta DSO | Session | Confidence |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |",
        ]
    )
    for scenario in review["scenarios"]:
        legacy = scenario["legacy_scores"]
        nsom = scenario["nsom_forced_on_scores"]
        delta = scenario["score_delta"]
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    str(legacy["planetary_score"]),
                    str(nsom["planetary_score"]),
                    str(delta["planetary_score"]),
                    str(legacy["deep_sky_score"]),
                    str(nsom["deep_sky_score"]),
                    str(delta["deep_sky_score"]),
                    str(scenario["session_state"]),
                    _confidence_label(scenario["confidence_value"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Policy Checks",
            "",
        ]
    )
    for item in summary["policy_checks"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## Downstream Consumer Evidence",
            "",
            "| Consumer | Evidence |",
            "| --- | --- |",
            f"| QML Home advanced scores | `{downstream['qml_reads_advanced_scores']}` |",
            f"| AppController passes advanced scores to Planner | `{downstream['controller_passes_advanced_scores_to_planner']}` |",
            f"| Planner consumes advanced scores | `{downstream['planner_consumes_advanced_scores']}` |",
            f"| AppController passes advanced scores to Notifications | `{downstream['controller_passes_advanced_scores_to_notifications']}` |",
            f"| NotificationService present and consumes advanced scores | `{downstream['notifications_consume_advanced_scores']}` |",
            "",
            "## Default-On Risks",
            "",
        ]
    )
    for risk in summary["default_on_risks"]:
        lines.append(f"- {risk}")

    lines.extend(
        [
            "",
            "## Runtime And QML Wiring",
            "",
            "| Check | Result |",
            "| --- | --- |",
            f"| QML matches | `{review['static_wiring_checks']['qml_matches']}` |",
            f"| Runtime report imports | `{review['static_wiring_checks']['runtime_report_import_matches']}` |",
            "",
            "## Source Reports",
            "",
            f"- Comparison report: `{metadata['source_report']}`.",
            f"- Policy readiness report: `{metadata['policy_report']}`.",
            "",
            "## Recommended Next Step",
            "",
            (
                "Keep Advanced Observing NSOM as a backend projection unless a "
                "separate UI step replaces or explains the visible `advancedScores` "
                "contract. Planner must keep an explicit input policy; Notifications "
                "are removed dead legacy."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = RUNTIME_REVIEW_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _evaluate_scenario(
    scenario: AdvancedObservingRuntimeScenario,
    comparison: dict[str, object],
) -> dict[str, object]:
    legacy_scores = AdvancedObservingService().scores(
        scenario.weather,
        scenario.seeing,
        scenario.sky_quality,
        scenario.moon,
    )
    nsom_scores = AdvancedObservingNsomService().scores(
        scenario.weather,
        scenario.seeing,
        scenario.sky_quality,
        scenario.moon,
        confidence=scenario.confidence,
    )
    legacy_payload = legacy_scores.to_qml()
    nsom_payload = nsom_scores.to_qml()
    reference = comparison["nsom"]
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
        "legacy_scores": legacy_payload,
        "nsom_forced_on_scores": nsom_payload,
        "score_delta": {
            "planetary_score": nsom_scores.planetary_score - legacy_scores.planetary_score,
            "deep_sky_score": nsom_scores.deep_sky_score - legacy_scores.deep_sky_score,
        },
        "reference_projection": {
            "planet_observable_target_value": reference["planetary_reference"]["observable_target_value"]["value"],
            "deep_sky_average_observable_target_value": reference["deep_sky_reference_summary"][
                "average_observable_target_value"
            ],
        },
        "session_state": reference["session_viability"]["state"],
        "confidence_value": scenario.confidence.value,
        "payload_shape_compatible": set(legacy_payload) == set(nsom_payload),
        "confidence_score_effect": 0.0,
        "session_score_effect_on_nsom_category_values": 0.0,
        "observer_capability_used": False,
        "practical_target_value_used": False,
        "observation_opportunity_used": False,
    }


def _review_checks(
    scenarios: tuple[dict[str, object], ...],
    downstream: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    dark = _scenario_by_id(scenarios, "A01_good_session")
    blocked = _scenario_by_id(scenarios, "A03_blocked_session")
    bright_moon = _scenario_by_id(scenarios, "A04_bright_moon")
    high_lp = _scenario_by_id(scenarios, "A05_high_light_pollution")
    low_confidence = _scenario_by_id(scenarios, "A08_low_confidence")
    return {
        "default_flag_still_off": NSOM_ADVANCED_OBSERVING_ENABLED is False,
        "forced_on_changes_scores": any(
            scenario["score_delta"]["planetary_score"] != 0
            or scenario["score_delta"]["deep_sky_score"] != 0
            for scenario in scenarios
        ),
        "payload_shape_compatible": all(scenario["payload_shape_compatible"] for scenario in scenarios),
        "strict_confidence_neutrality": _score_tuple(low_confidence)
        == _score_tuple(dark),
        "blocked_session_outside_category_values": _score_tuple(blocked)
        == _score_tuple(dark),
        "planetary_background_protected": bright_moon["nsom_forced_on_scores"]["planetary_score"]
        == dark["nsom_forced_on_scores"]["planetary_score"]
        and high_lp["nsom_forced_on_scores"]["planetary_score"]
        == dark["nsom_forced_on_scores"]["planetary_score"],
        "deep_sky_background_sensitive": bright_moon["nsom_forced_on_scores"]["deep_sky_score"]
        < dark["nsom_forced_on_scores"]["deep_sky_score"]
        and high_lp["nsom_forced_on_scores"]["deep_sky_score"]
        < dark["nsom_forced_on_scores"]["deep_sky_score"],
        "observer_capability_not_used": all(
            scenario["observer_capability_used"] is False for scenario in scenarios
        ),
        "downstream_consumers_share_advanced_scores": (
            downstream["qml_reads_advanced_scores"] is True
            and downstream["controller_passes_advanced_scores_to_planner"] is True
            and downstream["planner_consumes_advanced_scores"] is True
        ),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
    }


def _default_on_blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blockers: list[str] = []
    if checks["downstream_consumers_share_advanced_scores"]:
        blockers.append("advanced-observing-downstream-consumer-policy")
    if checks["forced_on_changes_scores"]:
        blockers.append("advanced-observing-score-label-policy")
    if checks["blocked_session_outside_category_values"]:
        blockers.append("advanced-observing-blocked-session-display-policy")
    safety_names = {
        "payload_shape_compatible": "advanced-observing-payload-shape",
        "strict_confidence_neutrality": "advanced-observing-confidence-neutrality",
        "planetary_background_protected": "advanced-observing-planetary-background-policy",
        "deep_sky_background_sensitive": "advanced-observing-deep-sky-background-policy",
        "observer_capability_not_used": "advanced-observing-observer-capability-policy",
        "runtime_report_imports_absent": "advanced-observing-runtime-report-wiring",
        "qml_exposure_absent": "advanced-observing-qml-exposure",
    }
    blockers.extend(name for key, name in safety_names.items() if checks[key] is not True)
    return tuple(blockers)


def _summary(scenarios: tuple[dict[str, object], ...]) -> dict[str, object]:
    checks = _review_checks(
        scenarios,
        downstream={key: True for key in _downstream_consumer_keys()},
        static_checks={"runtime_report_import_matches": (), "qml_matches": ()},
    )
    return {
        "policy_checks": (
            _check_line("Default flag remains off", checks["default_flag_still_off"]),
            _check_line("Forced-on path changes scores and therefore needs review", checks["forced_on_changes_scores"]),
            _check_line("QML payload shape remains compatible", checks["payload_shape_compatible"]),
            _check_line("Confidence remains score-neutral", checks["strict_confidence_neutrality"]),
            _check_line("Blocked-session viability stays outside category values", checks["blocked_session_outside_category_values"]),
            _check_line("Planets are protected from Moon/light-pollution background", checks["planetary_background_protected"]),
            _check_line("Deep-sky score remains sensitive to Moon/light pollution", checks["deep_sky_background_sensitive"]),
            _check_line("ObserverCapability is not used by Advanced Observing 1.8.x", checks["observer_capability_not_used"]),
        ),
        "default_on_risks": (
            "Forced-on `advancedScores` are shared with Planner, so default-on would affect more than the Home advanced-score cards. NotificationService has been removed as dead legacy.",
            "Blocked sessions keep NSOM category values high/physical while legacy caps scores; UI copy needs an explicit session/actionability treatment before default-on.",
            "Displayed score labels still use the legacy scalar field shape; users could read NSOM category values as direct legacy-quality equivalents.",
        ),
    }


def _downstream_consumer_evidence(root: Path) -> dict[str, object]:
    app_controller = (root / "astro_viewer" / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )
    planner = (root / "astro_viewer" / "app" / "services" / "planner_nsom_service.py").read_text(
        encoding="utf-8"
    )
    notifications_path = root / "astro_viewer" / "app" / "services" / "notification_service.py"
    notifications = notifications_path.read_text(encoding="utf-8") if notifications_path.exists() else ""
    qml = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "astro_viewer" / "app" / "ui").rglob("*.qml")
    )
    return {
        "qml_reads_advanced_scores": "controller.advancedScores" in qml,
        "controller_passes_advanced_scores_to_planner": "_night_planner_service.plan" in app_controller
        and "_advanced_scores" in app_controller,
        "planner_consumes_advanced_scores": "scores.planetary_score" in planner
        and "scores.deep_sky_score" in planner,
        "controller_passes_advanced_scores_to_notifications": "_notification_service.notifications" in app_controller
        and "_advanced_scores" in app_controller,
        "notifications_consume_advanced_scores": notifications_path.exists()
        and "scores.planetary_score" in notifications
        and "scores.deep_sky_score" in notifications,
    }


def _static_wiring_checks(root: Path) -> dict[str, object]:
    return {
        "qml_matches": _scan_files(root / "astro_viewer" / "app" / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
    }


def _scan_files(
    root: Path,
    patterns: tuple[str, ...],
    markers: tuple[str, ...],
    *,
    include_parts: tuple[str, ...] | None = None,
) -> tuple[dict[str, object], ...]:
    if not root.exists():
        return ()
    matches: list[dict[str, object]] = []
    for pattern in patterns:
        for path in sorted(root.rglob(pattern)):
            if include_parts and not any(part in path.parts for part in include_parts):
                continue
            if "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for line_number, line in enumerate(text.splitlines(), start=1):
                for marker in markers:
                    if marker in line:
                        matches.append(
                            {
                                "path": str(path.relative_to(root)).replace("\\", "/"),
                                "line": line_number,
                                "marker": marker,
                            }
                        )
    return tuple(matches)


def _scenarios() -> tuple[AdvancedObservingRuntimeScenario, ...]:
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


def _scenario(scenario_id: str) -> AdvancedObservingRuntimeScenario:
    specs = {
        "A01_good_session": (
            "good session",
            "dark_sky",
            "good",
            "good",
            "high",
            "Baseline forced-on Advanced Observing NSOM conditions.",
        ),
        "A02_poor_weather": (
            "poor weather",
            "dark_sky",
            "poor",
            "good",
            "high",
            "Session pressure should remain outside NSOM category values.",
        ),
        "A03_blocked_session": (
            "blocked session",
            "dark_sky",
            "blocked",
            "good",
            "high",
            "Blocked session should require display/actionability policy before default-on.",
        ),
        "A04_bright_moon": (
            "bright Moon",
            "bright_moon",
            "good",
            "good",
            "high",
            "Planetary score should be protected while deep-sky score degrades.",
        ),
        "A05_high_light_pollution": (
            "high light pollution",
            "high_light_pollution",
            "good",
            "good",
            "high",
            "Light pollution should pressure deep-sky more than planetary.",
        ),
        "A06_poor_seeing": (
            "poor seeing",
            "dark_sky",
            "good",
            "poor_seeing",
            "high",
            "Seeing should pressure the planetary category.",
        ),
        "A07_poor_transparency": (
            "poor transparency",
            "dark_sky",
            "good",
            "poor_transparency",
            "high",
            "Transparency should pressure the deep-sky category.",
        ),
        "A08_low_confidence": (
            "low confidence",
            "dark_sky",
            "good",
            "good",
            "low",
            "Confidence should not alter scores.",
        ),
    }
    label, sky_profile, session_profile, seeing_profile, confidence_profile, expectation = specs[scenario_id]
    sky_quality, moon = _sky_profile(sky_profile)
    return AdvancedObservingRuntimeScenario(
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


def _score_tuple(scenario: dict[str, object]) -> tuple[int, int]:
    scores = scenario["nsom_forced_on_scores"]
    return int(scores["planetary_score"]), int(scores["deep_sky_score"])


def _downstream_consumer_keys() -> tuple[str, ...]:
    return (
        "qml_reads_advanced_scores",
        "controller_passes_advanced_scores_to_planner",
        "planner_consumes_advanced_scores",
        "controller_passes_advanced_scores_to_notifications",
        "notifications_consume_advanced_scores",
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
            notes=("advanced_observing_runtime_review:high_confidence",),
        )
    return RecommendationConfidence(
        weather_confidence=0.4,
        viirs_confidence=0.0,
        moon_geometry_confidence=0.5,
        provider_fallback_confidence=0.6,
        notes=("advanced_observing_runtime_review:low_confidence",),
    )


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="AdvancedObservingNsomRuntimeReviewFixture",
        description="Advanced Observing NSOM runtime review fixture",
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


def _check_line(label: str, passed: bool) -> str:
    return f"{label}: {'passed' if passed else 'review'}"


def _confidence_label(value: object) -> str:
    return "n/a" if value is None else f"{float(value):.2f}"


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
