from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.advanced_observing_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)

POLICY_READINESS_PATH = Path("docs/ADVANCED_OBSERVING_NSOM_POLICY_READINESS.md")

REPORT_IMPORT_MARKERS = (
    "advanced_observing_nsom_policy_readiness",
    "ADVANCED_OBSERVING_NSOM_POLICY_READINESS",
)

QML_MARKERS = REPORT_IMPORT_MARKERS


def generate_policy_readiness_data() -> dict[str, object]:
    comparison = generate_report_data()
    decisions = _policy_decisions()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    checks = _readiness_checks(comparison, decisions, static_checks)
    blockers = _default_off_blockers(checks)
    ready = blockers == ()

    readiness_data = {
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
            "source_report": str(COMPARISON_REPORT_PATH).replace("\\", "/"),
            "policy_report_path": str(POLICY_READINESS_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": (
                "ready_for_default_off_advanced_observing_nsom_path"
                if ready
                else "not_ready_for_default_off_advanced_observing_nsom_path"
            ),
            "ready_for_default_off_path": ready,
            "runtime_behaviour_changed_by_this_review": False,
            "explicit_legacy_default": "AdvancedObservingService.scores(...) remains unchanged",
            "recommended_next_change": (
                "Add NSOM_ADVANCED_OBSERVING_ENABLED = False and keep "
                "AdvancedObservingService legacy by default."
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
    }
    return nsom_to_json_compatible(readiness_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_policy_readiness_data() if data is None else data
    metadata = audit["metadata"]
    readiness = audit["readiness"]
    evidence = audit["comparison_evidence"]

    lines = [
        "# Advanced Observing NSOM Policy Readiness",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit records the Advanced Observing NSOM policy "
            "decisions needed before a default-off runtime path can be added. It "
            "uses the existing comparison report as evidence and does not change "
            "`AdvancedObservingService`, Home, Best Object, Planner, Sky Compass, "
            "QML, logging, network behaviour or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-off path: `{readiness['ready_for_default_off_path']}`.",
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
        for blocker in audit["blockers"]:
            lines.append(f"- `{blocker}`")
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
            "## Evidence From Comparison Report",
            "",
            f"- Source report: `{metadata['source_report']}`.",
            f"- Scenario count: `{evidence['scenario_count']}`.",
            f"- Category rows: `{evidence['category_row_count']}`.",
            f"- Semantic recommendation: `{evidence['semantic_recommendation']}`.",
            f"- Runtime score replacement ready in comparison report: "
            f"`{evidence['runtime_score_replacement_ready']}`.",
            f"- Confidence score effect: `{evidence['confidence_score_effect']}`.",
            "",
            "## Main Mismatches",
            "",
        ]
    )
    for item in audit["comparison_summary"]["main_mismatches"]:
        lines.append(f"- {item}")

    lines.extend(
        [
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
                "Implement `1.8.4` as a default-off Advanced Observing NSOM runtime "
                "path behind `NSOM_ADVANCED_OBSERVING_ENABLED = False`, preserving "
                "the existing legacy advanced score output by default."
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
            "advanced_observing_role",
            status="accepted",
            affected_layer="presentation",
            decision=(
                "Advanced Observing is a presentation/category diagnostic surface, "
                "not an owner of independent target ranking."
            ),
            reason=(
                "The current surface produces planetary and deep-sky category badges; "
                "it does not rank concrete observing targets."
            ),
            intentional=True,
        ),
        _decision(
            "session_viability_policy",
            status="accepted",
            affected_layer="session",
            decision=(
                "SessionViability must stay separate from category sky values. "
                "Blocked sessions should be displayed as non-actionable session "
                "context, not hidden inside target or sky quality."
            ),
            reason=(
                "Legacy weather caps mix session actionability into both category "
                "scores; NSOM should keep the session layer explicit."
            ),
            intentional=True,
        ),
        _decision(
            "planetary_seeing_policy",
            status="accepted_for_experimental_path",
            affected_layer="sky",
            decision=(
                "Seeing may feed a planetary atmospheric stability diagnostic, but "
                "it must remain separate from Moon and light-pollution background."
            ),
            reason=(
                "The comparison report shows poor seeing pressures the planetary "
                "reference while deep-sky transparency remains a separate sky input."
            ),
            intentional=True,
        ),
        _decision(
            "planetary_moon_policy",
            status="accepted",
            affected_layer="sky",
            decision=(
                "Planetary and Moon diagnostics should be protected from Moon and "
                "light-pollution sky-background penalties."
            ),
            reason=(
                "Planets can remain useful under bright Moon/light pollution; those "
                "conditions are context metadata for planetary viewing, not target "
                "background penalties."
            ),
            intentional=True,
        ),
        _decision(
            "deep_sky_target_class_policy",
            status="accepted",
            affected_layer="sky",
            decision=(
                "Deep-sky diagnostics should preserve target-class sensitivity for "
                "galaxies, diffuse nebulae, open clusters and globular clusters even "
                "if the current UI keeps one broad deep-sky badge."
            ),
            reason=(
                "A single deep-sky scalar can hide that galaxies/nebulosity are more "
                "sensitive to sky background than cluster classes."
            ),
            intentional=True,
            extra={"preserve_target_class_components": True},
        ),
        _decision(
            "weather_cap_policy",
            status="accepted_for_rollback_only",
            affected_layer="session",
            decision=(
                "Legacy weather caps remain only in the legacy rollback/default path "
                "until a default-off NSOM path is added."
            ),
            reason=(
                "NSOM should expose session viability separately instead of encoding "
                "weather caps into category sky/target values."
            ),
            intentional=True,
        ),
        _decision(
            "observer_capability_policy",
            status="deferred_non_blocking",
            affected_layer="observer",
            decision=(
                "Advanced Observing 1.8.x will not consume ObserverCapability until "
                "a later equipment-specific category advice pass."
            ),
            reason=(
                "The current Advanced Observing UI is condition/category oriented, "
                "while ObserverCapability belongs to practical target value."
            ),
            intentional=True,
        ),
        _decision(
            "confidence_policy",
            status="accepted",
            affected_layer="confidence",
            decision=(
                "RecommendationConfidence remains metadata-only and never modifies "
                "advanced category scores or future NSOM category values."
            ),
            reason="Confidence describes data trust, not physical observing value.",
            intentional=True,
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
    intentional: bool,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "decision_id": decision_id,
        "status": status,
        "decision": decision,
        "reason": reason,
        "affected_nsom_layer": affected_layer,
        "intentional_nsom_behaviour": intentional,
        "possible_calibration_issue": False,
        "tuning_required": False,
        "blocks_default_off_path": False,
    }
    if extra:
        payload.update(extra)
    return payload


def _readiness_checks(
    comparison: dict[str, object],
    decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    decision_ids = {decision["decision_id"] for decision in decisions}
    required_decisions = {
        "advanced_observing_role",
        "session_viability_policy",
        "planetary_seeing_policy",
        "planetary_moon_policy",
        "deep_sky_target_class_policy",
        "weather_cap_policy",
        "observer_capability_policy",
        "confidence_policy",
    }
    return {
        "comparison_report_developer_only": comparison["metadata"]["developer_only"] is True,
        "comparison_report_has_no_runtime_writes": comparison["metadata"]["runtime_writes"] is False,
        "legacy_formula_components_available": comparison["metadata"]["category_row_count"] > 0,
        "required_policy_decisions_recorded": required_decisions.issubset(decision_ids),
        "policy_decisions_do_not_block_default_off": all(
            decision["blocks_default_off_path"] is False for decision in decisions
        ),
        "confidence_score_neutral": _decision_by_id(decisions, "confidence_policy")[
            "score_effect"
        ]
        == 0.0
        and comparison["semantic_recommendation"]["confidence_score_effect"] == 0.0,
        "deep_sky_target_classes_preserved": _decision_by_id(
            decisions,
            "deep_sky_target_class_policy",
        )["preserve_target_class_components"]
        is True,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_scores_unchanged_by_review": True,
    }


def _default_off_blockers(checks: dict[str, object]) -> tuple[str, ...]:
    names = {
        "comparison_report_developer_only": "advanced-observing-comparison-not-developer-only",
        "comparison_report_has_no_runtime_writes": "advanced-observing-comparison-runtime-writes",
        "legacy_formula_components_available": "advanced-observing-legacy-components-missing",
        "required_policy_decisions_recorded": "advanced-observing-policy-decisions-missing",
        "policy_decisions_do_not_block_default_off": "advanced-observing-policy-blocker",
        "confidence_score_neutral": "advanced-observing-confidence-not-neutral",
        "deep_sky_target_classes_preserved": "advanced-observing-deep-sky-class-policy",
        "runtime_report_imports_absent": "advanced-observing-runtime-report-wiring",
        "qml_exposure_absent": "advanced-observing-qml-exposure",
        "runtime_scores_unchanged_by_review": "advanced-observing-runtime-score-change",
    }
    return tuple(names[key] for key, ok in checks.items() if key in names and ok is not True)


def _comparison_evidence(comparison: dict[str, object]) -> dict[str, object]:
    return {
        "scenario_count": comparison["metadata"]["scenario_count"],
        "category_row_count": comparison["metadata"]["category_row_count"],
        "semantic_recommendation": comparison["semantic_recommendation"]["classification"],
        "runtime_score_replacement_ready": comparison["semantic_recommendation"][
            "runtime_score_replacement_ready"
        ],
        "confidence_score_effect": comparison["semantic_recommendation"]["confidence_score_effect"],
    }


def _non_blocking_risks() -> tuple[str, ...]:
    return (
        "The current UI expects scalar planetary and deep-sky score labels.",
        "A future default-off path must preserve the legacy output shape until UI semantics are designed.",
        "Seeing ownership may need a later calibration review before any default-on switch.",
        "One broad deep-sky badge can hide target-class differences unless diagnostic data stays class-aware.",
        "ObserverCapability is intentionally deferred for Advanced Observing 1.8.x.",
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
            "Advanced Observing policy decisions are documented, remaining items are "
            "non-blocking, confidence remains metadata-only, and no runtime/QML wiring "
            "exists. A separate default-off NSOM path can now be implemented."
        )
    return "One or more Advanced Observing policy or runtime-safety checks still blocks the path."


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
