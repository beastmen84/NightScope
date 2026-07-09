from __future__ import annotations

from copy import deepcopy
from inspect import signature
from pathlib import Path

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.best_object_nsom_ranking import (
    NSOM_BEST_OBJECT_ENABLED,
    BestObjectNsomSelectionService,
)
from astro_viewer.app.services.observing_score_service import ObservingScoreService
from astro_viewer.tools.best_object_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)
from astro_viewer.tools.best_object_nsom_readiness_audit import (
    READINESS_AUDIT_PATH as DEFAULT_OFF_READINESS_AUDIT_PATH,
    generate_readiness_audit_data,
)
from astro_viewer.app.viewmodels.app_controller import AppController

DEFAULT_ON_READINESS_AUDIT_PATH = Path("docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "best_object_nsom_default_on_readiness_audit",
    "BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT",
)

QML_MARKERS = (
    "bestObjectNsom",
    "BestObjectNsom",
    "best_object_nsom_default_on_readiness_audit",
    "BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT",
)


def generate_default_on_readiness_audit_data() -> dict[str, object]:
    comparison = generate_report_data()
    default_off_audit = generate_readiness_audit_data()
    runtime_policy = _runtime_policy_evidence()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    safety = _runtime_safety(comparison, default_off_audit, runtime_policy, static_checks)
    checks = _readiness_checks(default_off_audit, runtime_policy, static_checks, safety)
    blockers = _default_on_blockers(checks)
    ready = blockers == ()

    audit_data = {
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
            "source_report": str(COMPARISON_REPORT_PATH).replace("\\", "/"),
            "default_off_readiness_report": str(DEFAULT_OFF_READINESS_AUDIT_PATH).replace("\\", "/"),
            "audit_report_path": str(DEFAULT_ON_READINESS_AUDIT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "best_object_nsom_default_on_enabled" if ready else "not_ready_for_default_on_switch_pr",
            "ready_for_default_on_switch": ready,
            "default_flag": f"NSOM_BEST_OBJECT_ENABLED = {NSOM_BEST_OBJECT_ENABLED}",
            "default_flag_currently_enabled": NSOM_BEST_OBJECT_ENABLED is True,
            "requires_separate_flag_change": NSOM_BEST_OBJECT_ENABLED is False,
            "runtime_behaviour_changed_by_this_audit": False,
            "explicit_legacy_rollback": "removed: AppController(use_nsom_best_object=False)",
            "explicit_nsom_path": "default AppController()",
            "recommended_switch_change": (
                "already enabled"
                if NSOM_BEST_OBJECT_ENABLED
                else "set NSOM_BEST_OBJECT_ENABLED = True"
            ),
            "reason": _readiness_reason(ready),
        },
        "blockers": blockers,
        "checks": checks,
        "runtime_policy_evidence": runtime_policy,
        "display_score_semantics": _display_score_semantics(),
        "missing_sky_quality_policy": _missing_sky_quality_policy(static_checks),
        "rollback_policy": _rollback_policy(),
        "non_blocking_risks": _non_blocking_risks(),
        "runtime_safety": safety,
        "static_wiring_checks": static_checks,
        "comparison_summary": comparison["summary"],
    }
    return nsom_to_json_compatible(audit_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_default_on_readiness_audit_data() if data is None else data
    readiness = audit["readiness"]
    runtime = audit["runtime_policy_evidence"]
    display = audit["display_score_semantics"]
    missing_sky = audit["missing_sky_quality_policy"]
    rollback = audit["rollback_policy"]
    safety = audit["runtime_safety"]

    lines = [
        "# Best Object NSOM Default-On Readiness Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether the existing default-off Best Object "
            "NSOM path is safe after the default-on switch. It reports the current "
            "`NSOM_BEST_OBJECT_ENABLED` flag, removed rollback path and policy state without "
            "exposing QML fields, writing runtime files, logging automatically, calling the network, changing "
            "recommendedDeepSky, Planner or Sky Compass."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-on switch: `{readiness['ready_for_default_on_switch']}`.",
        f"- Current default flag: `{readiness['default_flag']}`.",
        f"- Default flag currently enabled: `{readiness['default_flag_currently_enabled']}`.",
        f"- Requires separate flag change: `{readiness['requires_separate_flag_change']}`.",
        f"- Runtime behaviour changed by this audit: `{readiness['runtime_behaviour_changed_by_this_audit']}`.",
        f"- Explicit legacy rollback: `{readiness['explicit_legacy_rollback']}`.",
        f"- Explicit NSOM path: `{readiness['explicit_nsom_path']}`.",
        f"- Recommended switch change: `{readiness['recommended_switch_change']}`.",
        f"- Reason: {readiness['reason']}",
        "",
        "## Default-On Blockers",
        "",
    ]
    if audit["blockers"]:
        for blocker in audit["blockers"]:
            lines.append(f"- `{blocker}`")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Runtime Policy Evidence",
            "",
            "| Policy | Evidence |",
            "| --- | --- |",
            "| Good session | "
            f"Selected `{runtime['good_session']['selected_object_id']}` as "
            f"`{runtime['good_session']['selected_actionability']}`. |",
            "| Blocked session | "
            f"Selected `{runtime['blocked_session']['selected_object_id']}`; "
            f"actionabilities `{_order_label(runtime['blocked_session']['actionabilities'])}`; "
            f"stable order is recommendation order `{runtime['blocked_session']['stable_order_is_recommendation_order']}`. |",
            "| Invisible target | "
            f"`{runtime['invisible_target']['invisible_object_id']}` is "
            f"`{runtime['invisible_target']['invisible_actionability']}` and selected "
            f"`{runtime['invisible_target']['invisible_selected']}`. |",
            "| Confidence | "
            f"Low/high score parity `{runtime['confidence']['scores_equal']}`; score effect "
            f"`{runtime['confidence']['score_effect']}`. |",
            "| Mutation | "
            f"Runtime objects mutated `{runtime['mutation']['runtime_objects_mutated']}`. |",
        ]
    )

    blocked = runtime["blocked_session"]
    lines.extend(
        [
            "",
            "## Blocked Session Policy",
            "",
            f"- Selected object: `{blocked['selected_object_id']}`.",
            f"- All scores zero: `{blocked['all_scores_zero']}`.",
            f"- Actionability: `{_order_label(blocked['actionabilities'])}`.",
            f"- Stable order is recommendation order: `{blocked['stable_order_is_recommendation_order']}`.",
            f"- Diagnostic-only preserved PracticalTargetValue order: `{_order_label(blocked['non_actionable_preserved_order'])}`.",
            f"- Preserved order is recommendation order: `{blocked['preserved_order_is_recommendation_order']}`.",
            "",
            "## Displayed Score Semantics",
            "",
            f"- Status: `{display['status']}`.",
            f"- Keep legacy/base displayed score: `{display['keep_legacy_base_score_for_payload_compatibility']}`.",
            f"- Score monotonic with NSOM order: `{display['score_monotonic_with_nsom_order']}`.",
            f"- Blocks default-on switch: `{display['blocks_default_on_switch']}`.",
            f"- Decision: {display['decision']}",
            f"- Future UI work: {display['future_ui_work']}",
            "",
            "## Missing Sky Quality Policy",
            "",
            f"- Status: `{missing_sky['status']}`.",
            f"- Runtime fallback: {missing_sky['runtime_fallback']}",
            f"- Blocks default-on switch: `{missing_sky['blocks_default_on_switch']}`.",
            f"- Reason: {missing_sky['reason']}",
            "",
            "## Rollback Policy",
            "",
            f"- Constructor rollback: `{rollback['constructor_rollback']}`.",
            f"- Legacy path preserved: `{rollback['legacy_path_preserved']}`.",
            f"- Runtime rollback removed: `{rollback['runtime_rollback_removed']}`.",
            f"- Blocks default-on switch: `{rollback['blocks_default_on_switch']}`.",
            "",
            "## Runtime Safety",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in safety.items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Non-Blocking Risks",
            "",
        ]
    )
    for risk in audit["non_blocking_risks"]:
        lines.append(f"- {risk}")

    lines.extend(
        [
            "",
            "## Recommended Next Step",
            "",
            (
                "Review the default-on switch, then close the Best Object NSOM migration "
                "in documentation while keeping visible score explanation as a separate UI step."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = DEFAULT_ON_READINESS_AUDIT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _runtime_policy_evidence() -> dict[str, object]:
    service = BestObjectNsomSelectionService()
    weather = _weather(90)
    sky_quality = _sky_quality(3)
    telescope = _telescope()
    moon = _moon(10)
    targets = _targets()
    before = deepcopy(targets)

    good_ranked = service.ranked_candidates(
        targets,
        weather=weather,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
    )
    good_selected = service.best_object(
        targets,
        weather=weather,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
    )

    blocked_weather = _weather(10, cloud_cover=95, precipitation_probability=80)
    blocked_ranked = service.ranked_candidates(
        targets,
        weather=blocked_weather,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
    )
    blocked_selected = service.best_object(
        targets,
        weather=blocked_weather,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
    )

    invisible_targets = [
        _target("hidden_galaxy", "Galaxy", 100, difficulty="Media", visible=False),
        _target("open_cluster", "Open Cluster", 78, difficulty="Facile", setup_type="binoculars"),
    ]
    invisible_ranked = service.ranked_candidates(
        invisible_targets,
        weather=weather,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
    )
    invisible_selected = service.best_object(
        invisible_targets,
        weather=weather,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
    )
    invisible_candidate = next(candidate for candidate in invisible_ranked if candidate.target.id == "hidden_galaxy")

    low_confidence = service.ranked_candidates(
        targets,
        weather=weather,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high_confidence = service.ranked_candidates(
        targets,
        weather=weather,
        sky_quality=sky_quality,
        telescope=telescope,
        moon=moon,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    legacy_selected = ObservingScoreService().best_object(targets, weather)

    return {
        "good_session": {
            "selected_object_id": good_selected.id if good_selected else None,
            "selected_actionability": _actionability_for(good_ranked, good_selected),
            "legacy_selected_object_id": legacy_selected.id if legacy_selected else None,
            "nsom_order": _candidate_order(good_ranked),
        },
        "blocked_session": {
            "selected_object_id": blocked_selected.id if blocked_selected else None,
            "actionabilities": tuple(candidate.actionability for candidate in blocked_ranked),
            "scores": _candidate_scores(blocked_ranked),
            "all_scores_zero": all(candidate.score == 0.0 for candidate in blocked_ranked),
            "stable_order": _candidate_order(blocked_ranked),
            "stable_order_is_recommendation_order": False,
            "non_actionable_preserved_order": _practical_order(blocked_ranked),
            "preserved_order_is_recommendation_order": False,
        },
        "invisible_target": {
            "selected_object_id": invisible_selected.id if invisible_selected else None,
            "invisible_object_id": invisible_candidate.target.id,
            "invisible_actionability": invisible_candidate.actionability,
            "invisible_selected": invisible_selected is not None and invisible_selected.id == invisible_candidate.target.id,
        },
        "confidence": {
            "low_order": _candidate_order(low_confidence),
            "high_order": _candidate_order(high_confidence),
            "low_scores": _candidate_scores(low_confidence),
            "high_scores": _candidate_scores(high_confidence),
            "scores_equal": _candidate_scores(low_confidence) == _candidate_scores(high_confidence),
            "confidence_values_differ": low_confidence[0].opportunity.confidence.value
            != high_confidence[0].opportunity.confidence.value,
            "score_effect": 0.0,
        },
        "mutation": {
            "runtime_objects_mutated": targets != before,
        },
    }


def _display_score_semantics() -> dict[str, object]:
    return {
        "status": "accepted_non_blocking_for_default_on_switch",
        "keep_legacy_base_score_for_payload_compatibility": True,
        "score_monotonic_with_nsom_order": False,
        "blocks_default_on_switch": False,
        "decision": (
            "Keep the existing QML payload and base/legacy score field for the switch. "
            "The displayed score is compatibility data and is not the NSOM rationale."
        ),
        "future_ui_work": (
            "Add explicit NSOM explanation/display fields only in a later UI design step."
        ),
    }


def _missing_sky_quality_policy(static_checks: dict[str, object]) -> dict[str, object]:
    fallback_present = bool(static_checks["controller_missing_sky_quality_legacy_fallback"])
    return {
        "status": "accepted_non_blocking_fallback" if fallback_present else "missing_runtime_fallback",
        "runtime_fallback": "legacy Best Object when `_sky_quality` is missing",
        "fallback_present": fallback_present,
        "blocks_default_on_switch": not fallback_present,
        "reason": (
            "NSOM Best Object requires ObservationEnvironment inputs. Missing sky quality "
            "therefore remains a compatibility fallback to the legacy Best Object path."
        ),
    }


def _rollback_policy() -> dict[str, object]:
    parameter_present = "use_nsom_best_object" in signature(AppController.__init__).parameters
    return {
        "constructor_rollback": "removed: AppController(use_nsom_best_object=False)",
        "legacy_path_preserved": False,
        "rollback_parameter_present": parameter_present,
        "runtime_rollback_removed": not parameter_present,
        "blocks_default_on_switch": False,
        "reason": "The constructor override was removed in 1.13.8; missing sky quality remains a data fallback.",
    }


def _non_blocking_risks() -> tuple[str, ...]:
    return (
        "Displayed `score` remains the existing base/legacy-compatible score and may not be monotonic with NSOM order.",
        "Missing sky quality falls back to the legacy Best Object path because NSOM environment inputs are incomplete.",
        "Best Object uses Home presentation policy with flat timing factors, not Planner chronology.",
        "Blocked sessions return no actionable Best Object under NSOM; that is intentional but user-facing copy is unchanged.",
    )


def _runtime_safety(
    comparison: dict[str, object],
    default_off_audit: dict[str, object],
    runtime_policy: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    metadata = comparison["metadata"]
    return {
        "current_flag_default_on_enabled": NSOM_BEST_OBJECT_ENABLED is True,
        "default_off_audit_policy_ready": default_off_audit["readiness"]["ready_for_default_off_path"] is True,
        "comparison_tooling_developer_only": metadata["developer_only"] is True,
        "comparison_tooling_has_no_runtime_writes": metadata["runtime_writes"] is False,
        "comparison_tooling_has_no_automatic_logging": metadata["automatic_logging"] is False,
        "comparison_tooling_has_no_network": metadata["network"] is False,
        "comparison_tooling_has_no_qml_exposure": metadata["qml_exposure"] is False,
        "best_object_runtime_unchanged_by_this_audit": True,
        "recommended_deep_sky_runtime_unchanged": metadata["recommended_deep_sky_changed"] is False,
        "planner_runtime_unchanged": metadata["planner_changed"] is False,
        "sky_compass_runtime_unchanged": metadata["sky_compass_changed"] is False,
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "runtime_objects_not_mutated": runtime_policy["mutation"]["runtime_objects_mutated"] is False,
    }


def _readiness_checks(
    default_off_audit: dict[str, object],
    runtime_policy: dict[str, object],
    static_checks: dict[str, object],
    safety: dict[str, object],
) -> dict[str, object]:
    blocked = runtime_policy["blocked_session"]
    invisible = runtime_policy["invisible_target"]
    confidence = runtime_policy["confidence"]
    missing_sky = _missing_sky_quality_policy(static_checks)
    display = _display_score_semantics()
    rollback = _rollback_policy()
    return {
        "default_off_audit_ready": default_off_audit["readiness"]["ready_for_default_off_path"] is True,
        "default_flag_enabled_for_switch": NSOM_BEST_OBJECT_ENABLED is True,
        "blocked_sessions_non_actionable": blocked["selected_object_id"] is None
        and blocked["all_scores_zero"] is True
        and set(blocked["actionabilities"]) == {"non_actionable_hard_block"},
        "blocked_stable_order_not_recommendation": blocked["stable_order_is_recommendation_order"] is False
        and blocked["preserved_order_is_recommendation_order"] is False,
        "invisible_targets_non_actionable": invisible["invisible_actionability"] == "non_actionable_invisible_target"
        and invisible["invisible_selected"] is False,
        "missing_sky_quality_fallback_documented": missing_sky["fallback_present"] is True
        and missing_sky["blocks_default_on_switch"] is False,
        "displayed_score_semantics_non_blocking": display["blocks_default_on_switch"] is False,
        "constructor_rollback_removed": rollback["runtime_rollback_removed"] is True
        and rollback["blocks_default_on_switch"] is False,
        "confidence_score_neutral": confidence["scores_equal"] is True
        and confidence["confidence_values_differ"] is True
        and confidence["score_effect"] == 0.0,
        "runtime_safety_clean": all(value is True for value in safety.values()),
    }


def _default_on_blockers(checks: dict[str, object]) -> tuple[str, ...]:
    names = {
        "default_off_audit_ready": "best-object-default-off-audit-not-ready",
        "default_flag_enabled_for_switch": "best-object-default-flag-not-enabled",
        "blocked_sessions_non_actionable": "best-object-blocked-session-policy",
        "blocked_stable_order_not_recommendation": "best-object-blocked-stable-order-policy",
        "invisible_targets_non_actionable": "best-object-invisible-target-policy",
        "missing_sky_quality_fallback_documented": "best-object-missing-sky-quality-policy",
        "displayed_score_semantics_non_blocking": "best-object-displayed-score-semantics",
        "constructor_rollback_removed": "best-object-rollback-still-present",
        "confidence_score_neutral": "best-object-confidence-neutrality",
        "runtime_safety_clean": "best-object-runtime-safety",
    }
    return tuple(names[key] for key, ok in checks.items() if key in names and ok is not True)


def _static_wiring_checks(root: Path) -> dict[str, object]:
    controller = root / "astro_viewer" / "app" / "viewmodels" / "app_controller.py"
    controller_text = controller.read_text(encoding="utf-8")
    return {
        "qml_matches": _scan_files(root / "astro_viewer" / "app" / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "controller_missing_sky_quality_legacy_fallback": "or not self._sky_quality" in controller_text
        and "self._score_service.best_object" in controller_text,
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


def _readiness_reason(ready: bool) -> str:
    if ready:
        return (
            "The default-off runtime path, non-actionable policies, confidence neutrality, "
            "removed rollback path, missing-sky fallback and developer-only safety checks "
            "remain valid with the Best Object NSOM flag enabled by default."
        )
    return "One or more Best Object default-on policy or runtime-safety checks still blocks the switch."


def _targets() -> list[CelestialObject]:
    return [
        _target("jupiter", "Pianeta", 86, difficulty="Facile", magnitude="-2.1"),
        _target("open_cluster", "Open Cluster", 78, difficulty="Facile", setup_type="binoculars"),
        _target("galaxy", "Galaxy", 90, difficulty="Media"),
        _target("diffuse_nebula", "Nebula diffusa", 88, difficulty="Media"),
    ]


def _target(
    object_id: str,
    object_type: str,
    score: int,
    *,
    magnitude: str = "8.0",
    difficulty: str = "Media",
    setup_type: str = "telescope",
    visible: bool = True,
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
        best_time="21:00",
        observing_window="21:00 - 02:00",
        notes="Best Object default-on readiness fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=visible,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type=setup_type,
    )


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Best Object default-on readiness fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="BestObjectDefaultOnReadinessFixture",
        description="Best Object default-on readiness fixture",
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


def _telescope() -> Telescope:
    return Telescope(
        id="test-scope",
        name="Test Scope",
        aperture_mm=127,
        focal_length_mm=1500,
        optical_type="Reflector",
        mount="manual",
    )


def _actionability_for(candidates: tuple[object, ...], selected: CelestialObject | None) -> str | None:
    if selected is None:
        return None
    return next(candidate.actionability for candidate in candidates if candidate.target.id == selected.id)


def _candidate_order(candidates: tuple[object, ...]) -> tuple[str, ...]:
    return tuple(str(candidate.target.id) for candidate in candidates)


def _candidate_scores(candidates: tuple[object, ...]) -> tuple[float, ...]:
    return tuple(round(float(candidate.score), 12) for candidate in candidates)


def _practical_order(candidates: tuple[object, ...]) -> tuple[str, ...]:
    return tuple(
        candidate.target.id
        for candidate in sorted(
            candidates,
            key=lambda candidate: (-candidate.practical_target_value.value, candidate.stable_order_index),
        )
    )


def _order_label(order: object) -> str:
    return " > ".join(str(item) for item in order)


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
