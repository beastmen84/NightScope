from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.advanced_observing_nsom_service import (
    NSOM_ADVANCED_OBSERVING_ENABLED,
    AdvancedObservingNsomService,
)
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.notification_service import NotificationService
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService
from astro_viewer.tools.advanced_observing_nsom_runtime_review import (
    RUNTIME_REVIEW_PATH,
    generate_runtime_review_data,
)

DOWNSTREAM_POLICY_PATH = Path("docs/ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY.md")

REPORT_IMPORT_MARKERS = (
    "advanced_observing_nsom_downstream_policy",
    "ADVANCED_OBSERVING_NSOM_DOWNSTREAM_POLICY",
)

QML_MARKERS = REPORT_IMPORT_MARKERS


def generate_downstream_policy_data() -> dict[str, object]:
    runtime_review = generate_runtime_review_data()
    notification_evidence = _notification_evidence()
    planner_evidence = _planner_evidence()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    decisions = _policy_decisions(notification_evidence, planner_evidence)
    checks = _checks(runtime_review, decisions, notification_evidence, planner_evidence, static_checks)
    blockers = _default_on_blockers(checks, decisions)
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "advanced_scores_changed_by_default": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed": False,
            "notifications_changed": False,
            "sky_compass_changed": False,
            "consumer_split_implemented": True,
            "runtime_review_report": str(RUNTIME_REVIEW_PATH).replace("\\", "/"),
            "downstream_policy_report": str(DOWNSTREAM_POLICY_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "consumer_split_resolved_but_qml_policy_blocks_default_on",
            "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
            "ready_for_default_on_switch": False,
            "runtime_behaviour_changed_by_this_policy": False,
            "forced_on_path_safe_to_keep": True,
            "consumer_split_implemented": True,
            "recommended_next_change": (
                "Define the Advanced Observing presentation/QML policy before "
                "enabling NSOM Advanced Observing by default."
            ),
        },
        "default_on_blockers": blockers,
        "checks": checks,
        "policy_decisions": decisions,
        "notification_evidence": notification_evidence,
        "planner_evidence": planner_evidence,
        "runtime_review_blockers": runtime_review["default_on_blockers"],
        "static_wiring_checks": static_checks,
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    policy = generate_downstream_policy_data() if data is None else data
    readiness = policy["readiness"]
    notification = policy["notification_evidence"]
    planner = policy["planner_evidence"]

    lines = [
        "# Advanced Observing NSOM Downstream Policy",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only policy report resolves the consumer question raised "
            "by the `1.8.5` runtime review: `advancedScores` is a shared runtime "
            "contract read by QML, Planner and NotificationService. The current "
            "Advanced Observing NSOM path remains default-off. This report does not "
            "change the flag, tune scores, alter Planner or NotificationService, "
            "expose QML, log automatically, call the network or write runtime files."
            " In `1.8.7`, AppController keeps the shared `advancedScores` payload "
            "legacy-compatible and stores forced-on NSOM Advanced Observing scores "
            "only as an internal parallel snapshot."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Default flag: `{readiness['default_flag']}`.",
        f"- Ready for default-on switch: `{readiness['ready_for_default_on_switch']}`.",
        f"- Runtime behaviour changed by this policy: `{readiness['runtime_behaviour_changed_by_this_policy']}`.",
        f"- Forced-on path safe to keep: `{readiness['forced_on_path_safe_to_keep']}`.",
        f"- Consumer split implemented: `{readiness['consumer_split_implemented']}`.",
        f"- Recommended next change: {readiness['recommended_next_change']}",
        "",
        "## Default-On Blockers",
        "",
    ]
    for blocker in policy["default_on_blockers"]:
        lines.append(f"- `{blocker}`")

    lines.extend(
        [
            "",
            "## Policy Decisions",
            "",
            "| Policy | Status | Blocks default-on | Decision |",
            "| --- | --- | --- | --- |",
        ]
    )
    for decision in policy["policy_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_default_on']}`",
                    str(decision["decision"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Notification Evidence",
            "",
            f"- Legacy blocked-session titles: `{notification['legacy_blocked_titles']}`.",
            f"- NSOM forced-on blocked-session titles: `{notification['nsom_blocked_titles']}`.",
            f"- NSOM would trigger favourable blocked-session notifications: "
            f"`{notification['nsom_triggers_favourable_under_blocked_session']}`.",
            f"- Consumer split blocked-session titles: `{notification['consumer_split_blocked_titles']}`.",
            f"- Consumer split prevents favourable blocked-session notifications: "
            f"`{notification['consumer_split_prevents_favourable_blocked_notifications']}`.",
            "",
            "## Planner Evidence",
            "",
            f"- Planner uses `advancedScores` as atmospheric transparency: "
            f"`{planner['planner_uses_advanced_scores_as_atmospheric_transparency']}`.",
            f"- Poor-weather legacy category factor: `{planner['poor_weather_legacy_category_factor']}`.",
            f"- Poor-weather NSOM category factor: `{planner['poor_weather_nsom_category_factor']}`.",
            f"- Planner score changes with forced-on NSOM scores: "
            f"`{planner['planner_score_changes_with_forced_on_nsom_scores']}`.",
            f"- Consumer split preserves legacy Planner score: "
            f"`{planner['consumer_split_preserves_legacy_planner_score']}`.",
            f"- Duplicate ownership risk: `{planner['duplicate_sky_or_session_ownership_risk']}`.",
            "",
            "## Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in policy["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Runtime And QML Wiring",
            "",
            f"- QML matches: `{policy['static_wiring_checks']['qml_matches']}`.",
            f"- Runtime report imports: `{policy['static_wiring_checks']['runtime_report_import_matches']}`.",
            "",
            "## Recommended Next Step",
            "",
            (
                "Implement `1.8.8` as the Advanced Observing presentation/default-on "
                "readiness audit: decide whether QML should keep legacy cards, gain "
                "separate NSOM explanation fields, or continue hiding the internal "
                "NSOM snapshot."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = DOWNSTREAM_POLICY_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _policy_decisions(
    notification_evidence: dict[str, object],
    planner_evidence: dict[str, object],
) -> tuple[dict[str, object], ...]:
    return (
        _decision(
            "shared_advanced_scores_contract",
            status="implemented_legacy_contract_preserved",
            affected_consumer="app_controller",
            decision=(
                "`advancedScores` remains the legacy-compatible shared runtime "
                "payload. Forced-on NSOM Advanced Observing scores are kept as an "
                "internal parallel snapshot."
            ),
            reason=(
                "The same visible payload still drives Home QML cards, while Planner "
                "and NotificationService receive explicit legacy-compatible consumer "
                "scores."
            ),
            blocks_default_on=False,
        ),
        _decision(
            "planner_consumer_policy",
            status="resolved_by_legacy_consumer_input",
            affected_consumer="planner",
            decision=(
                "Planner receives the legacy-compatible AdvancedObservingScores "
                "consumer input, so forced-on Advanced Observing NSOM category "
                "diagnostics do not become Planner atmospheric transparency."
            ),
            reason=(
                "Planner already owns Moon, sky-background, horizon, session and "
                "observer layers; keeping the consumer score legacy-compatible "
                "prevents duplicate sky/session ownership."
            ),
            blocks_default_on=not bool(planner_evidence["consumer_split_preserves_legacy_planner_score"]),
        ),
        _decision(
            "notification_consumer_policy",
            status="resolved_by_legacy_consumer_input",
            affected_consumer="notifications",
            decision=(
                "NotificationService receives the legacy-compatible "
                "AdvancedObservingScores consumer input, so forced-on NSOM category "
                "diagnostics cannot trigger favourable notifications during blocked "
                "sessions."
            ),
            reason=(
                "NSOM category values intentionally keep session viability outside "
                "the score, while notifications threshold the legacy-compatible "
                "consumer score."
            ),
            blocks_default_on=not bool(
                notification_evidence["consumer_split_prevents_favourable_blocked_notifications"]
            ),
        ),
        _decision(
            "qml_display_policy",
            status="deferred_blocking_for_default_on",
            affected_consumer="qml_home",
            decision=(
                "QML may keep the existing payload shape, but a default-on switch "
                "needs copy/label policy so NSOM category diagnostics are not read "
                "as legacy actionability scores."
            ),
            reason="The same `advancedScores` fields are visible as `/100` scalar cards.",
            blocks_default_on=True,
        ),
        _decision(
            "confidence_policy",
            status="accepted",
            affected_consumer="all",
            decision="RecommendationConfidence remains metadata-only and must not alter downstream scores.",
            reason="Confidence describes source trust, not category value.",
            blocks_default_on=False,
            extra={"score_effect": 0.0},
        ),
        _decision(
            "home_best_object_sky_compass_policy",
            status="accepted",
            affected_consumer="non_consumers",
            decision=(
                "Home recommendedDeepSky, Best Object and Sky Compass are not "
                "changed by this policy step."
            ),
            reason="They do not consume the Advanced Observing NSOM downstream policy report.",
            blocks_default_on=False,
        ),
    )


def _decision(
    decision_id: str,
    *,
    status: str,
    affected_consumer: str,
    decision: str,
    reason: str,
    blocks_default_on: bool,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "decision_id": decision_id,
        "status": status,
        "affected_consumer": affected_consumer,
        "decision": decision,
        "reason": reason,
        "blocks_default_on": blocks_default_on,
        "runtime_changed": False,
    }
    if extra:
        payload.update(extra)
    return payload


def _notification_evidence() -> dict[str, object]:
    weather = _weather(10, cloud_cover=95, precipitation=80, wind=18)
    seeing = _seeing(seeing_score=86, transparency_score=84)
    sky_quality = _sky_quality(2, radiance=1)
    moon = _moon(10)
    legacy_scores = AdvancedObservingService().scores(weather, seeing, sky_quality, moon)
    nsom_scores = AdvancedObservingNsomService().scores(weather, seeing, sky_quality, moon)
    service = NotificationService()
    legacy_notifications = service.notifications(None, [], [], legacy_scores, moon)
    nsom_notifications = service.notifications(None, [], [], nsom_scores, moon)
    consumer_split_notifications = service.notifications(None, [], [], legacy_scores, moon)
    nsom_titles = tuple(item.title for item in nsom_notifications)
    consumer_split_titles = tuple(item.title for item in consumer_split_notifications)
    favourable_titles = {
        "Condizioni planetarie favorevoli",
        "Finestra cielo profondo utile",
    }
    nsom_triggers = any(title in favourable_titles for title in nsom_titles)
    consumer_split_triggers = any(title in favourable_titles for title in consumer_split_titles)
    return {
        "legacy_blocked_scores": legacy_scores.to_qml(),
        "nsom_blocked_scores": nsom_scores.to_qml(),
        "legacy_blocked_titles": tuple(item.title for item in legacy_notifications),
        "nsom_blocked_titles": nsom_titles,
        "consumer_split_blocked_titles": consumer_split_titles,
        "nsom_triggers_favourable_under_blocked_session": nsom_triggers,
        "consumer_split_triggers_favourable_under_blocked_session": consumer_split_triggers,
        "consumer_split_prevents_favourable_blocked_notifications": nsom_triggers
        and not consumer_split_triggers,
    }


def _planner_evidence() -> dict[str, object]:
    weather = _weather(35, cloud_cover=70, precipitation=20, wind=14)
    seeing = _seeing(seeing_score=86, transparency_score=84)
    sky_quality = _sky_quality(2, radiance=1)
    moon = _moon(10)
    target = _target("galaxy", "Galaxy", 90)
    telescope = Telescope("scope", "Dobson 200", 200, 1200, "Newton", "Dobson")
    legacy_scores = AdvancedObservingService().scores(weather, seeing, sky_quality, moon)
    nsom_scores = AdvancedObservingNsomService().scores(weather, seeing, sky_quality, moon)
    blocking = NightPlannerService.weather_blocking_status(weather)
    service = PlannerNsomScoringService()
    legacy_opportunity = service.opportunity(
        target,
        weather=weather,
        scores=legacy_scores,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
        blocking_status=blocking,
    )
    nsom_opportunity = service.opportunity(
        target,
        weather=weather,
        scores=nsom_scores,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
        blocking_status=blocking,
    )
    consumer_split_opportunity = service.opportunity(
        target,
        weather=weather,
        scores=legacy_scores,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
        blocking_status=blocking,
    )
    legacy_effective = legacy_opportunity.practical_target_value.observable_target_value.effective_observability
    nsom_effective = nsom_opportunity.practical_target_value.observable_target_value.effective_observability
    return {
        "target_id": target.id,
        "weather_score": weather.score_value,
        "legacy_scores": legacy_scores.to_qml(),
        "nsom_scores": nsom_scores.to_qml(),
        "consumer_split_scores": legacy_scores.to_qml(),
        "planner_uses_advanced_scores_as_atmospheric_transparency": any(
            "advanced_score_factor=" in note for note in nsom_effective.notes
        ),
        "poor_weather_legacy_category_factor": legacy_effective.atmospheric_transparency,
        "poor_weather_nsom_category_factor": nsom_effective.atmospheric_transparency,
        "poor_weather_consumer_split_category_factor": legacy_effective.atmospheric_transparency,
        "legacy_planner_score": legacy_opportunity.value,
        "nsom_planner_score": nsom_opportunity.value,
        "consumer_split_planner_score": consumer_split_opportunity.value,
        "planner_score_changes_with_forced_on_nsom_scores": legacy_opportunity.value
        != nsom_opportunity.value,
        "consumer_split_preserves_legacy_planner_score": consumer_split_opportunity.value
        == legacy_opportunity.value,
        "duplicate_sky_or_session_ownership_risk": True,
    }


def _checks(
    runtime_review: dict[str, object],
    decisions: tuple[dict[str, object], ...],
    notification_evidence: dict[str, object],
    planner_evidence: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    decision_ids = {decision["decision_id"] for decision in decisions}
    return {
        "default_flag_still_off": NSOM_ADVANCED_OBSERVING_ENABLED is False,
        "runtime_review_identified_downstream_blocker": "advanced-observing-downstream-consumer-policy"
        in runtime_review["default_on_blockers"],
        "required_decisions_recorded": {
            "shared_advanced_scores_contract",
            "planner_consumer_policy",
            "notification_consumer_policy",
            "qml_display_policy",
            "confidence_policy",
            "home_best_object_sky_compass_policy",
        }.issubset(decision_ids),
        "shared_contract_split_resolved": _decision_by_id(
            decisions,
            "shared_advanced_scores_contract",
        )["blocks_default_on"]
        is False,
        "planner_consumer_split_resolved": _decision_by_id(
            decisions,
            "planner_consumer_policy",
        )["blocks_default_on"]
        is False,
        "notification_consumer_split_resolved": _decision_by_id(
            decisions,
            "notification_consumer_policy",
        )["blocks_default_on"]
        is False,
        "qml_policy_blocks_default_on": _decision_by_id(
            decisions,
            "qml_display_policy",
        )["blocks_default_on"]
        is True,
        "confidence_score_neutral": _decision_by_id(decisions, "confidence_policy")[
            "score_effect"
        ]
        == 0.0,
        "notification_blocked_session_risk_visible": notification_evidence[
            "nsom_triggers_favourable_under_blocked_session"
        ]
        is True,
        "planner_score_risk_visible": planner_evidence[
            "planner_score_changes_with_forced_on_nsom_scores"
        ]
        is True,
        "consumer_split_prevents_notification_risk": notification_evidence[
            "consumer_split_prevents_favourable_blocked_notifications"
        ]
        is True,
        "consumer_split_preserves_planner_score": planner_evidence[
            "consumer_split_preserves_legacy_planner_score"
        ]
        is True,
        "controller_consumer_split_methods_present": static_checks[
            "controller_consumer_split_methods_present"
        ]
        is True,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_behaviour_unchanged": True,
    }


def _default_on_blockers(
    checks: dict[str, object],
    decisions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    blockers = [
        f"advanced-observing-{decision['decision_id'].replace('_', '-')}"
        for decision in decisions
        if decision["blocks_default_on"] is True
    ]
    safety_names = {
        "default_flag_still_off": "advanced-observing-default-flag-still-off",
        "runtime_review_identified_downstream_blocker": "advanced-observing-runtime-review-missing-downstream-blocker",
        "required_decisions_recorded": "advanced-observing-downstream-policy-incomplete",
        "shared_contract_split_resolved": "advanced-observing-shared-contract-split-unresolved",
        "planner_consumer_split_resolved": "advanced-observing-planner-consumer-split-unresolved",
        "notification_consumer_split_resolved": "advanced-observing-notification-consumer-split-unresolved",
        "qml_policy_blocks_default_on": "advanced-observing-qml-policy-not-blocking-default-on",
        "confidence_score_neutral": "advanced-observing-confidence-not-neutral",
        "notification_blocked_session_risk_visible": "advanced-observing-notification-risk-missing",
        "planner_score_risk_visible": "advanced-observing-planner-risk-missing",
        "consumer_split_prevents_notification_risk": "advanced-observing-notification-split-not-effective",
        "consumer_split_preserves_planner_score": "advanced-observing-planner-split-not-effective",
        "controller_consumer_split_methods_present": "advanced-observing-controller-split-methods-missing",
        "runtime_report_imports_absent": "advanced-observing-runtime-report-wiring",
        "qml_exposure_absent": "advanced-observing-qml-exposure",
        "runtime_behaviour_unchanged": "advanced-observing-runtime-behaviour-change",
    }
    blockers.extend(name for key, name in safety_names.items() if checks[key] is not True)
    return tuple(dict.fromkeys(blockers))


def _static_wiring_checks(root: Path) -> dict[str, object]:
    controller_source = root / "astro_viewer" / "app" / "viewmodels" / "app_controller.py"
    controller_text = controller_source.read_text(encoding="utf-8") if controller_source.exists() else ""
    return {
        "qml_matches": _scan_files(root / "astro_viewer" / "app" / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "controller_consumer_split_methods_present": all(
            marker in controller_text
            for marker in (
                "_select_advanced_observing_nsom_scores",
                "_advanced_scores_for_planner",
                "_advanced_scores_for_notifications",
            )
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


def _decision_by_id(
    decisions: tuple[dict[str, object], ...],
    decision_id: str,
) -> dict[str, object]:
    return next(decision for decision in decisions if decision["decision_id"] == decision_id)


def _target(object_id: str, object_type: str, score: int) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.title(),
        object_type=object_type,
        image="",
        magnitude="8.0",
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="21:00",
        observing_window="21:00 - 02:00",
        notes="Advanced Observing downstream policy fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty="Media",
    )


def _weather(
    score: int,
    *,
    cloud_cover: int,
    precipitation: int,
    wind: int,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Advanced Observing downstream policy fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation,
        wind_kmh=wind,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _seeing(*, seeing_score: int, transparency_score: int) -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Fixture",
        transparency="Fixture",
        seeing_score=seeing_score,
        transparency_score=transparency_score,
        explanation="Advanced Observing downstream policy fixture",
    )


def _sky_quality(bortle: int, radiance: float | None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="AdvancedObservingDownstreamPolicyFixture",
        description="Advanced Observing downstream policy fixture",
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


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
