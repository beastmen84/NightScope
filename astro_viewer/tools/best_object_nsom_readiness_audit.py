from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.best_object_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)

READINESS_AUDIT_PATH = Path("docs/BEST_OBJECT_NSOM_READINESS_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "best_object_nsom_readiness_audit",
    "BEST_OBJECT_NSOM_READINESS_AUDIT",
)

QML_MARKERS = (
    "bestObjectNsom",
    "BestObjectNsom",
    "best_object_nsom_readiness_audit",
    "BEST_OBJECT_NSOM_READINESS_AUDIT",
)


def generate_readiness_audit_data() -> dict[str, object]:
    comparison = generate_report_data()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    policy = _policy_review(comparison)
    display = _display_score_semantics()
    runtime_safety = _runtime_safety(comparison, static_checks)
    blockers = _default_off_blockers(policy=policy, display=display, runtime_safety=runtime_safety)
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
            "audit_report_path": str(READINESS_AUDIT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "ready_for_default_off_path" if ready else "not_ready_for_default_off_path",
            "ready_for_default_off_path": ready,
            "runtime_path_exists": False,
            "runtime_behaviour_changed": False,
            "recommendation": (
                "add_default_off_best_object_nsom_path"
                if ready
                else "resolve_policy_and_display_semantics_before_runtime_path"
            ),
            "reason": _readiness_reason(ready),
        },
        "blockers": blockers,
        "policy_review": policy,
        "display_score_semantics": display,
        "semantic_migration_target": _semantic_migration_target(comparison),
        "runtime_safety": runtime_safety,
        "static_wiring_checks": static_checks,
        "comparison_summary": comparison["summary"],
    }
    return nsom_to_json_compatible(audit_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_readiness_audit_data() if data is None else data
    readiness = audit["readiness"]
    policy = audit["policy_review"]
    display = audit["display_score_semantics"]
    semantic = audit["semantic_migration_target"]
    runtime = audit["runtime_safety"]

    lines = [
        "# Best Object NSOM Readiness Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether Best Object is ready for a "
            "default-off NSOM runtime path after the comparison report. It does not "
            "change Best Object selection, recommendedDeepSky, Planner, Sky Compass, "
            "QML, logging, network behaviour or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-off path: `{readiness['ready_for_default_off_path']}`.",
        f"- Runtime path exists: `{readiness['runtime_path_exists']}`.",
        f"- Runtime behaviour changed: `{readiness['runtime_behaviour_changed']}`.",
        f"- Recommendation: `{readiness['recommendation']}`.",
        f"- Reason: {readiness['reason']}",
        "",
        "## Default-Off Blockers",
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
            "## Policy Review",
            "",
            "| Policy | Status | Blocks Default-Off Path | Decision |",
            "| --- | --- | --- | --- |",
        ]
    )
    for decision in policy["decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['policy_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_default_off_path']}`",
                    str(decision["decision"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Blocked Session Evidence",
            "",
        ]
    )
    blocked = policy["blocked_session_evidence"]
    lines.extend(
        [
            f"- Scenario: `{blocked['scenario_id']}`.",
            f"- Blocking reason: {blocked['blocking_reason']}.",
            f"- Legacy Best Object order: `{_order_label(blocked['legacy_order'])}`.",
            f"- Diagnostic ObservableTargetValue order: `{_order_label(blocked['observable_order'])}`.",
            f"- Diagnostic PracticalTargetValue order: `{_order_label(blocked['practical_order'])}`.",
            f"- Actionability: `{blocked['actionability']}`.",
            f"- Diagnostic orders are recommendation orders: `{blocked['diagnostic_orders_are_recommendation_orders']}`.",
        ]
    )

    lines.extend(
        [
            "",
            "## Displayed Score Semantics",
            "",
            f"- Decision status: `{display['status']}`.",
            f"- Keep legacy displayed score for compatibility: `{display['keep_legacy_displayed_score_for_compatibility']}`.",
            f"- Score monotonic with proposed NSOM order: `{display['score_monotonic_with_proposed_nsom_order']}`.",
            f"- Blocks default-off path: `{display['blocks_default_off_path']}`.",
            f"- Decision: {display['decision']}",
            "",
            "## Semantic Migration Target",
            "",
            f"- Recommended concept: `{semantic['recommended_future_nsom_concept']}`.",
            f"- Use pure ObservableTargetValue: `{semantic['use_pure_observable_target_value']}`.",
            f"- Use pure PracticalTargetValue: `{semantic['use_pure_practical_target_value']}`.",
            f"- Use ObservationOpportunity with Home policy: `{semantic['use_observation_opportunity_with_home_policy']}`.",
            f"- Reason: {semantic['reason']}",
            "",
            "## Runtime Safety",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in runtime.items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Recommended Next Steps",
            "",
            "1. Define Best Object non-actionable policy before any runtime NSOM path.",
            "2. Add a default-off Best Object NSOM path only after blocked-session and display semantics are settled.",
            "3. Preserve legacy Best Object as explicit rollback when the runtime path is introduced.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = READINESS_AUDIT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _policy_review(comparison: dict[str, object]) -> dict[str, object]:
    blocked = _scenario(comparison, "B03_blocked_session")
    confidence_neutral = all(
        row["nsom"]["recommendation_confidence"]["score_factor"] is False
        and float(row["nsom"]["recommendation_confidence"]["score_effect"]) == 0.0
        for scenario in comparison["scenarios"]
        for row in scenario["rows"]
    )
    return {
        "decisions": (
            {
                "policy_id": "best-object-blocked-session-non-actionable-policy",
                "status": "needs_policy_decision",
                "blocks_default_off_path": True,
                "decision": (
                    "Blocked sessions must not surface legacy, ObservableTargetValue "
                    "or PracticalTargetValue order as an actionable Best Object recommendation."
                ),
            },
            {
                "policy_id": "best-object-observation-opportunity-home-policy",
                "status": "accepted_direction",
                "blocks_default_off_path": False,
                "decision": (
                    "Best Object should migrate toward ObservationOpportunity-style "
                    "actionability with a Home-specific presentation policy."
                ),
            },
            {
                "policy_id": "best-object-confidence-metadata-policy",
                "status": "accepted",
                "blocks_default_off_path": False,
                "decision": "RecommendationConfidence remains metadata and must not modify score.",
            },
        ),
        "blocked_session_evidence": _blocked_session_evidence(blocked),
        "confidence_neutrality_verified": confidence_neutral,
    }


def _blocked_session_evidence(scenario: dict[str, object]) -> dict[str, object]:
    blocking = scenario["metadata"]["blocking_status"]
    return {
        "scenario_id": scenario["scenario_id"],
        "blocking_reason": blocking["reason"],
        "legacy_order": tuple(scenario["legacy_best_object_order"]),
        "observable_order": tuple(scenario["nsom_observable_order"]),
        "practical_order": tuple(scenario["nsom_practical_order"]),
        "actionability": "non_actionable",
        "legacy_weather_floor_still_ranks": True,
        "diagnostic_orders_are_recommendation_orders": False,
        "required_policy": (
            "A future Best Object NSOM path must annotate blocked sessions as "
            "non-actionable before ranking is exposed to Home."
        ),
    }


def _display_score_semantics() -> dict[str, object]:
    return {
        "status": "needs_policy_decision",
        "keep_legacy_displayed_score_for_compatibility": True,
        "score_monotonic_with_proposed_nsom_order": False,
        "blocks_default_off_path": True,
        "decision": (
            "Best Object cannot switch runtime ordering until Home card score/rationale "
            "semantics are defined. Keeping the legacy displayed score is compatible, "
            "but it may not be monotonic with an ObservationOpportunity-based order."
        ),
    }


def _semantic_migration_target(comparison: dict[str, object]) -> dict[str, object]:
    semantic = comparison["semantic_recommendation"]
    return {
        "recommended_future_nsom_concept": semantic["recommended_future_nsom_concept"],
        "use_pure_observable_target_value": False,
        "use_pure_practical_target_value": False,
        "use_observation_opportunity_with_home_policy": True,
        "reason": (
            "Best Object is action-oriented. ObservableTargetValue omits equipment and "
            "session actionability; PracticalTargetValue omits session actionability; "
            "ObservationOpportunity can carry session policy, but Home needs compact "
            "presentation rules distinct from Planner chronology."
        ),
    }


def _runtime_safety(
    comparison: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    metadata = comparison["metadata"]
    return {
        "comparison_tooling_developer_only": metadata["developer_only"] is True,
        "comparison_tooling_has_no_runtime_writes": metadata["runtime_writes"] is False,
        "comparison_tooling_has_no_automatic_logging": metadata["automatic_logging"] is False,
        "comparison_tooling_has_no_network": metadata["network"] is False,
        "comparison_tooling_has_no_qml_exposure": metadata["qml_exposure"] is False,
        "best_object_runtime_unchanged": metadata["best_object_changed"] is False,
        "recommended_deep_sky_runtime_unchanged": metadata["recommended_deep_sky_changed"] is False,
        "planner_runtime_unchanged": metadata["planner_changed"] is False,
        "sky_compass_runtime_unchanged": metadata["sky_compass_changed"] is False,
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
    }


def _default_off_blockers(
    *,
    policy: dict[str, object],
    display: dict[str, object],
    runtime_safety: dict[str, object],
) -> tuple[str, ...]:
    blockers: list[str] = []
    for decision in policy["decisions"]:
        if decision["blocks_default_off_path"] is True:
            blockers.append(str(decision["policy_id"]))
    if display["blocks_default_off_path"] is True:
        blockers.append("best-object-displayed-score-semantics")
    if not all(value is True for value in runtime_safety.values()):
        blockers.append("best-object-runtime-safety")
    return tuple(blockers)


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


def _scenario(data: dict[str, object], scenario_id: str) -> dict[str, object]:
    return next(scenario for scenario in data["scenarios"] if scenario["scenario_id"] == scenario_id)


def _readiness_reason(ready: bool) -> str:
    if ready:
        return (
            "Best Object policy, displayed score semantics and runtime safety are "
            "ready for a default-off NSOM runtime path."
        )
    return (
        "Best Object still needs non-actionable session policy and displayed score "
        "semantics before a runtime NSOM path is introduced."
    )


def _order_label(order: object) -> str:
    return " > ".join(str(item) for item in order)


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
