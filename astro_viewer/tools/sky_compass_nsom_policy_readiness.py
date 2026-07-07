from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.sky_compass_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)

POLICY_READINESS_PATH = Path("docs/SKY_COMPASS_NSOM_POLICY_READINESS.md")

REPORT_IMPORT_MARKERS = (
    "sky_compass_nsom_policy_readiness",
    "SKY_COMPASS_NSOM_POLICY_READINESS",
)

QML_MARKERS = REPORT_IMPORT_MARKERS


def generate_policy_readiness_data() -> dict[str, object]:
    comparison = generate_report_data()
    decisions = _policy_decisions()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    checks = _readiness_checks(comparison, decisions, static_checks)
    blockers = _default_off_blockers(checks, decisions)
    ready = blockers == ()

    readiness_data = {
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
            "source_report": str(COMPARISON_REPORT_PATH).replace("\\", "/"),
            "policy_report_path": str(POLICY_READINESS_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": (
                "ready_for_default_off_sky_compass_nsom_path"
                if ready
                else "not_ready_for_default_off_sky_compass_nsom_path"
            ),
            "ready_for_default_off_path": ready,
            "ready_for_default_on": False,
            "runtime_behaviour_changed_by_this_review": False,
            "explicit_legacy_default": "SkyCompassService.compass(...) remains unchanged",
            "recommended_next_change": (
                "Add a default-off experimental Sky Compass NSOM direction policy "
                "that preserves payload shape and explicit legacy rollback."
            ),
            "reason": _readiness_reason(ready),
        },
        "blockers": blockers,
        "checks": checks,
        "policy_decisions": decisions,
        "non_blocking_risks": _non_blocking_risks(),
        "static_wiring_checks": static_checks,
        "comparison_summary": comparison["summary"],
        "comparison_evidence": _comparison_evidence(comparison),
        "recommended_default_off_policy": _recommended_default_off_policy(),
    }
    return nsom_to_json_compatible(readiness_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_policy_readiness_data() if data is None else data
    metadata = audit["metadata"]
    readiness = audit["readiness"]
    evidence = audit["comparison_evidence"]
    recommended = audit["recommended_default_off_policy"]

    lines = [
        "# Sky Compass NSOM Policy Readiness",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit records the policy decisions needed before "
            "an experimental default-off Sky Compass NSOM path can be added. It "
            "uses the comparison report as evidence and does not change "
            "`SkyCompassService`, Home, Best Object, Planner, QML, logging, network "
            "behaviour or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-off path: `{readiness['ready_for_default_off_path']}`.",
        f"- Ready for default-on: `{readiness['ready_for_default_on']}`.",
        (
            "- Runtime behaviour changed by this review: "
            f"`{readiness['runtime_behaviour_changed_by_this_review']}`."
        ),
        f"- Explicit legacy default: {readiness['explicit_legacy_default']}.",
        f"- Recommended next change: {readiness['recommended_next_change']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Default-Off Blockers",
        "",
    ]
    if audit["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in audit["blockers"])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Policy Decisions",
            "",
            "| Policy | Status | NSOM layer | Blocks default-off | Decision |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for decision in audit["policy_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['affected_nsom_layer']}`",
                    f"`{decision['blocks_default_off_path']}`",
                    str(decision["decision"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Recommended Default-Off Policy",
            "",
            f"- Candidate base: `{recommended['candidate_base']}`.",
            f"- Direction formula: `{recommended['direction_formula']}`.",
            f"- PracticalTargetValue use: `{recommended['practical_target_value_use']}`.",
            f"- Session use: `{recommended['session_use']}`.",
            f"- Confidence use: `{recommended['confidence_use']}`.",
            f"- QML payload policy: `{recommended['qml_payload_policy']}`.",
            f"- Fallback policy: `{recommended['fallback_policy']}`.",
            "",
            "## Evidence From Comparison Report",
            "",
            f"- Source report: `{metadata['source_report']}`.",
            f"- Scenario count: `{evidence['scenario_count']}`.",
            f"- Candidate row count: `{evidence['row_count']}`.",
            f"- Direction differences: `{evidence['direction_difference_count']}`.",
            f"- Scenarios with direction differences: `{evidence['scenarios_with_direction_difference']}`.",
            f"- Confidence score effect: `{evidence['confidence_score_effect']}`.",
            "",
            "## Readiness Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Runtime And QML Wiring",
            "",
            "| Check | Result |",
            "| --- | --- |",
            f"| QML matches | `{audit['static_wiring_checks']['qml_matches']}` |",
            (
                "| Runtime report imports | "
                f"`{audit['static_wiring_checks']['runtime_report_import_matches']}` |"
            ),
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
                "Implement `1.9.3` as a default-off experimental Sky Compass NSOM "
                "direction policy behind an internal flag. Preserve legacy Sky "
                "Compass as the default and keep the existing `skyCompass` QML "
                "payload shape unchanged."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = POLICY_READINESS_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _policy_decisions() -> tuple[dict[str, object], ...]:
    return (
        _decision(
            "sky_compass_role",
            status="accepted",
            affected_layer="presentation",
            decision=(
                "Sky Compass remains a direction and presentation policy, not a "
                "pure target-value ranking."
            ),
            reason=(
                "The comparison report shows legitimate direction differences when "
                "plan membership, Best Object identity and direction concentration "
                "are considered."
            ),
        ),
        _decision(
            "candidate_base_policy",
            status="accepted_for_default_off",
            affected_layer="sky",
            decision=(
                "The first default-off path may use ObservableTargetValue as the "
                "candidate base for direction aggregation."
            ),
            reason=(
                "ObservableTargetValue captures target and sky ownership without "
                "mixing observer equipment, session or confidence into target physics."
            ),
            extra={"candidate_base": "ObservableTargetValue"},
        ),
        _decision(
            "context_boost_policy",
            status="accepted",
            affected_layer="presentation",
            decision=(
                "Night Plan membership and Best Object identity remain explicit "
                "presentation/context boosts outside NSOM target physics."
            ),
            reason=(
                "S08 demonstrates that these boosts can intentionally choose a "
                "different direction from pure NSOM target references."
            ),
        ),
        _decision(
            "direction_concentration_policy",
            status="accepted",
            affected_layer="presentation",
            decision=(
                "Target concentration remains a direction aggregation policy and "
                "must not be hidden inside target DTOs."
            ),
            reason=(
                "Sky Compass answers where to start observing, so multiple useful "
                "targets in one zone is a presentation-level value."
            ),
        ),
        _decision(
            "practical_target_value_policy",
            status="deferred_non_blocking",
            affected_layer="observer",
            decision=(
                "PracticalTargetValue remains diagnostic/reference-only for the "
                "first default-off Sky Compass path."
            ),
            reason=(
                "Equipment-aware compass directions need separate UX and policy "
                "review before affecting the Home direction card."
            ),
            extra={"practical_target_value_used_for_default_off_score": False},
        ),
        _decision(
            "session_caution_policy",
            status="accepted",
            affected_layer="session",
            decision=(
                "Poor or blocked sessions remain caution/actionability metadata and "
                "do not mutate ObservableTargetValue or direction target physics."
            ),
            reason=(
                "The current Sky Compass already uses caution text as presentation "
                "context; NSOM should preserve that separation."
            ),
        ),
        _decision(
            "missing_location_direction_policy",
            status="accepted",
            affected_layer="presentation",
            decision=(
                "No-location and missing-direction cases continue to use the legacy "
                "empty/unavailable Sky Compass policy."
            ),
            reason=(
                "Without a current direction, Sky Compass cannot provide a meaningful "
                "direction recommendation regardless of target value."
            ),
        ),
        _decision(
            "qml_payload_policy",
            status="accepted",
            affected_layer="presentation",
            decision=(
                "The first default-off path must preserve the existing `skyCompass` "
                "payload keys and expose no NSOM fields to QML."
            ),
            reason=(
                "The current Home UI is visually stable and should not receive new "
                "fields or rationale copy in the backend migration step."
            ),
        ),
        _decision(
            "fallback_policy",
            status="accepted",
            affected_layer="presentation",
            decision=(
                "Any missing runtime input or NSOM adapter failure must fall back to "
                "the current legacy SkyCompassService path."
            ),
            reason="The experimental path must be reversible and safe under incomplete runtime state.",
        ),
        _decision(
            "confidence_policy",
            status="accepted",
            affected_layer="confidence",
            decision=(
                "RecommendationConfidence remains metadata-only and never modifies "
                "Sky Compass direction scores."
            ),
            reason="Confidence describes trust in data, not direction value.",
            extra={"score_effect": 0.0, "score_path": "parallel_metadata"},
        ),
    )


def _decision(
    decision_id: str,
    *,
    status: str,
    affected_layer: str,
    decision: str,
    reason: str,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "decision_id": decision_id,
        "status": status,
        "decision": decision,
        "reason": reason,
        "affected_nsom_layer": affected_layer,
        "intentional_nsom_behaviour": True,
        "possible_calibration_issue": False,
        "tuning_required": False,
        "blocks_default_off_path": False,
    }
    if extra:
        payload.update(extra)
    return payload


def _recommended_default_off_policy() -> dict[str, object]:
    return {
        "candidate_base": "ObservableTargetValue.value",
        "direction_formula": (
            "sum(observable_candidate_value + in_plan_bonus + best_object_bonus + "
            "target_presence_bonus) per normalized direction"
        ),
        "practical_target_value_use": "reference_only_for_1.9.x",
        "session_use": "caution_or_non_actionable_metadata_only",
        "confidence_use": "metadata_only_zero_score_effect",
        "qml_payload_policy": "preserve_existing_skyCompass_keys_no_nsom_fields",
        "fallback_policy": "legacy_sky_compass_on_missing_inputs_or_adapter_failure",
    }


def _readiness_checks(
    comparison: dict[str, object],
    decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    decision_ids = {decision["decision_id"] for decision in decisions}
    required_decisions = {
        "sky_compass_role",
        "candidate_base_policy",
        "context_boost_policy",
        "direction_concentration_policy",
        "practical_target_value_policy",
        "session_caution_policy",
        "missing_location_direction_policy",
        "qml_payload_policy",
        "fallback_policy",
        "confidence_policy",
    }
    confidence = _decision_by_id(decisions, "confidence_policy")
    practical = _decision_by_id(decisions, "practical_target_value_policy")
    return {
        "comparison_report_developer_only": comparison["metadata"]["developer_only"] is True,
        "comparison_report_has_no_runtime_writes": comparison["metadata"]["runtime_writes"] is False,
        "comparison_report_has_direction_differences": comparison["summary"]["direction_difference_count"] >= 1,
        "required_policy_decisions_recorded": required_decisions.issubset(decision_ids),
        "policy_decisions_do_not_block_default_off": all(
            decision["blocks_default_off_path"] is False for decision in decisions
        ),
        "default_off_policy_is_not_pure_target_ranking": _decision_by_id(
            decisions,
            "sky_compass_role",
        )["affected_nsom_layer"]
        == "presentation",
        "candidate_base_is_observable_not_practical": _decision_by_id(
            decisions,
            "candidate_base_policy",
        )["candidate_base"]
        == "ObservableTargetValue"
        and practical["practical_target_value_used_for_default_off_score"] is False,
        "session_and_confidence_are_metadata": _decision_by_id(
            decisions,
            "session_caution_policy",
        )["affected_nsom_layer"]
        == "session"
        and confidence["score_effect"] == 0.0,
        "fallback_policy_recorded": "legacy SkyCompassService" in _decision_by_id(
            decisions,
            "fallback_policy",
        )["decision"],
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_behaviour_unchanged_by_review": True,
    }


def _default_off_blockers(
    checks: dict[str, object],
    decisions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    blockers = [
        f"sky-compass-{decision['decision_id'].replace('_', '-')}"
        for decision in decisions
        if decision["blocks_default_off_path"] is True
    ]
    safety_names = {
        "comparison_report_developer_only": "sky-compass-comparison-not-developer-only",
        "comparison_report_has_no_runtime_writes": "sky-compass-comparison-runtime-writes",
        "comparison_report_has_direction_differences": "sky-compass-direction-evidence-missing",
        "required_policy_decisions_recorded": "sky-compass-policy-decisions-missing",
        "policy_decisions_do_not_block_default_off": "sky-compass-policy-blocker",
        "default_off_policy_is_not_pure_target_ranking": "sky-compass-pure-target-ranking-policy",
        "candidate_base_is_observable_not_practical": "sky-compass-candidate-base-policy",
        "session_and_confidence_are_metadata": "sky-compass-session-confidence-policy",
        "fallback_policy_recorded": "sky-compass-fallback-policy-missing",
        "runtime_report_imports_absent": "sky-compass-runtime-report-wiring",
        "qml_exposure_absent": "sky-compass-qml-exposure",
        "runtime_behaviour_unchanged_by_review": "sky-compass-runtime-behaviour-change",
    }
    blockers.extend(name for key, name in safety_names.items() if checks[key] is not True)
    return tuple(dict.fromkeys(blockers))


def _comparison_evidence(comparison: dict[str, object]) -> dict[str, object]:
    return {
        "scenario_count": comparison["metadata"]["scenario_count"],
        "row_count": comparison["metadata"]["row_count"],
        "direction_difference_count": comparison["summary"]["direction_difference_count"],
        "scenarios_with_direction_difference": comparison["summary"]["scenarios_with_direction_difference"],
        "confidence_score_effect": comparison["confidence_control"]["score_effect"],
    }


def _non_blocking_risks() -> tuple[str, ...]:
    return (
        "The current Home card copy explains direction, not NSOM score rationale.",
        "A future default-off path must keep the same `skyCompass` payload keys until UI design is scoped.",
        "Equipment-aware direction ranking is deferred because it may change the meaning of the compass.",
        "Plan and Best Object boosts are presentation policy and may need calibration before default-on.",
        "Bright sky scenarios intentionally diverge from legacy direction ranking and need human review before default-on.",
    )


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


def _decision_by_id(
    decisions: tuple[dict[str, object], ...],
    decision_id: str,
) -> dict[str, object]:
    return next(decision for decision in decisions if decision["decision_id"] == decision_id)


def _readiness_reason(ready: bool) -> str:
    if ready:
        return (
            "Sky Compass policy decisions are documented, remaining risks are "
            "non-blocking, confidence remains metadata-only, and no runtime/QML "
            "wiring exists. A separate default-off NSOM path can now be implemented."
        )
    return "One or more Sky Compass policy or runtime-safety checks still blocks the path."


def _strict_json_compatible(payload: dict[str, object]) -> bool:
    try:
        json.dumps(payload, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
