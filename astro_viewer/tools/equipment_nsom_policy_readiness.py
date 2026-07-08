from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.equipment_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)


POLICY_READINESS_PATH = Path("docs/EQUIPMENT_NSOM_POLICY_READINESS.md")

REPORT_IMPORT_MARKERS = (
    "equipment_nsom_policy_readiness",
    "EQUIPMENT_NSOM_POLICY_READINESS",
)

QML_MARKERS = REPORT_IMPORT_MARKERS


def generate_policy_readiness_data() -> dict[str, object]:
    comparison = generate_report_data()
    decisions = _policy_decisions()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    evidence = _comparison_evidence(comparison)
    checks = _readiness_checks(comparison, decisions, static_checks, evidence)
    blockers = _default_off_blockers(checks, decisions)
    ready_for_default_off = blockers == ()

    readiness_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "equipment_recommendations_changed": False,
            "planner_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "sky_compass_changed": False,
            "source_report": str(COMPARISON_REPORT_PATH).replace("\\", "/"),
            "policy_report_path": str(POLICY_READINESS_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": (
                "ready_for_default_off_equipment_nsom_path"
                if ready_for_default_off
                else "equipment_nsom_policy_set_runtime_replacement_deferred"
            ),
            "ready_for_default_off_path": ready_for_default_off,
            "ready_for_observer_capability_adapter_step": True,
            "runtime_behaviour_changed_by_this_review": False,
            "explicit_legacy_default": "EquipmentService.suggest_for_profile(...) remains unchanged",
            "recommended_next_change": (
                "Extract a shared ObserverCapability/Q_target adapter or read model "
                "from the comparison layer while keeping EquipmentService runtime "
                "setup recommendations unchanged."
            ),
            "reason": _readiness_reason(ready_for_default_off),
        },
        "blockers": blockers,
        "checks": checks,
        "policy_decisions": decisions,
        "recommended_policy": _recommended_policy(),
        "non_blocking_risks": _non_blocking_risks(),
        "static_wiring_checks": static_checks,
        "comparison_summary": comparison["summary"],
        "comparison_evidence": evidence,
    }
    return nsom_to_json_compatible(readiness_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_policy_readiness_data() if data is None else data
    metadata = audit["metadata"]
    readiness = audit["readiness"]
    evidence = audit["comparison_evidence"]
    recommended = audit["recommended_policy"]

    lines = [
        "# Equipment NSOM Policy Readiness",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit records the Equipment/ObserverCapability "
            "policy decision after the comparison report. It does not change "
            "`EquipmentService`, Planner, Home, Best Object, Sky Compass, "
            "Detail/Object, QML, logging, network behaviour or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-off path: `{readiness['ready_for_default_off_path']}`.",
        (
            "- Ready for ObserverCapability adapter step: "
            f"`{readiness['ready_for_observer_capability_adapter_step']}`."
        ),
        (
            "- Runtime behaviour changed by this review: "
            f"`{readiness['runtime_behaviour_changed_by_this_review']}`."
        ),
        f"- Explicit legacy default: {readiness['explicit_legacy_default']}.",
        f"- Recommended next change: {readiness['recommended_next_change']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Default-Off Runtime Replacement Blockers",
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
            "| Policy | Status | NSOM layer | Blocks default-off runtime path | Decision |",
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
            "## Recommended Policy",
            "",
            f"- Equipment runtime role: `{recommended['equipment_runtime_role']}`.",
            f"- NSOM-owned output: `{recommended['nsom_owned_output']}`.",
            f"- First runtime-safe step: `{recommended['first_runtime_safe_step']}`.",
            f"- Default-off replacement policy: `{recommended['default_off_replacement_policy']}`.",
            f"- Seeing policy: `{recommended['seeing_policy']}`.",
            f"- Sky-quality policy: `{recommended['sky_quality_policy']}`.",
            f"- Confidence policy: `{recommended['confidence_policy']}`.",
            f"- QML payload policy: `{recommended['qml_payload_policy']}`.",
            "",
            "## Evidence From Comparison Report",
            "",
            f"- Source report: `{metadata['source_report']}`.",
            f"- Scenario count: `{evidence['scenario_count']}`.",
            f"- Candidate rows: `{evidence['candidate_row_count']}`.",
            f"- Ranking disagreement scenarios: `{evidence['ranking_disagreement_scenarios']}`.",
            f"- Legacy ownership mixing observed: `{evidence['legacy_ownership_mixing_observed']}`.",
            f"- Observer isolated from ObservableTargetValue: `{evidence['observer_isolated_from_observable']}`.",
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
                "Implement `1.12.2` as an internal ObserverCapability/Q_target "
                "adapter extraction. Keep `EquipmentService.suggest_for_profile(...)` "
                "as the runtime setup recommender and do not add a default-off "
                "Equipment replacement path yet."
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
            "equipment_runtime_role",
            status="accepted",
            affected_layer="observer",
            decision=(
                "Equipment remains a practical setup helper for eyepieces, Barlow, "
                "binoculars, focal position, difficulty and setup-option payloads."
            ),
            reason=(
                "The comparison report shows NSOM can project capability, but the "
                "runtime service also owns concrete setup presentation and fallback "
                "states that Q_target does not replace."
            ),
            blocks_default_off=True,
        ),
        _decision(
            "observer_capability_adapter_policy",
            status="accepted_for_next_step",
            affected_layer="observer",
            decision=(
                "The next NSOM backend step should extract a shared "
                "ObserverCapability/Q_target adapter or read model from the "
                "comparison implementation."
            ),
            reason=(
                "ObserverCapability is the NSOM-owned projection needed by Planner, "
                "Detail and future explanations, while EquipmentService should keep "
                "owning setup selection."
            ),
            extra={"adapter_extraction_ready": True},
        ),
        _decision(
            "q_target_runtime_policy",
            status="accepted_reference_only",
            affected_layer="observer",
            decision=(
                "Q_target may feed PracticalTargetValue and diagnostics, but it is "
                "not sufficient by itself to rank concrete eyepiece/Barlow choices."
            ),
            reason=(
                "Q_target is target-class capability, not a full setup-option "
                "presenter with focal position, roles and user-facing labels."
            ),
            blocks_default_off=True,
            extra={"q_target_replaces_equipment_score": False},
        ),
        _decision(
            "seeing_policy",
            status="deferred_non_blocking",
            affected_layer="sky",
            decision=(
                "Seeing may remain legacy setup feasibility context for now; a "
                "future NSOM adapter must keep atmospheric conditions separate from "
                "ObserverCapability unless a narrow setup-stability field is defined."
            ),
            reason=(
                "The 1.12.0 comparison shows legacy Equipment scoring uses seeing, "
                "but NSOM ownership treats seeing as environment/session context."
            ),
            blocks_default_off=True,
        ),
        _decision(
            "sky_quality_policy",
            status="accepted_for_legacy_helper_only",
            affected_layer="sky",
            decision=(
                "Sky quality must not change ObserverCapability; any Equipment "
                "runtime replacement would need an explicit environment input "
                "boundary rather than mixing Bortle/VIIRS into capability."
            ),
            reason=(
                "The comparison proves Q_target stays stable across sky quality for "
                "the same configuration, while legacy setup scoring may still use "
                "sky quality as practical context."
            ),
            blocks_default_off=True,
        ),
        _decision(
            "payload_policy",
            status="accepted",
            affected_layer="presentation",
            decision=(
                "Any future path must preserve the existing recommendation payload "
                "shape and setupOptions roles, and expose no NSOM fields to QML in "
                "a backend migration step."
            ),
            reason=(
                "Home and Detail UI already depend on setup labels, alternatives, "
                "high-magnification and wide-field options."
            ),
            blocks_default_off=True,
        ),
        _decision(
            "fallback_policy",
            status="accepted",
            affected_layer="presentation",
            decision=(
                "Missing eyepieces, no useful configuration, naked-eye and binocular "
                "fallbacks remain owned by EquipmentService until an equivalent "
                "presenter contract exists."
            ),
            reason="These are user-facing setup states, not NSOM target values.",
            blocks_default_off=True,
        ),
        _decision(
            "confidence_policy",
            status="accepted",
            affected_layer="confidence",
            decision=(
                "RecommendationConfidence remains metadata-only and never modifies "
                "Equipment setup scores, Q_target or PracticalTargetValue."
            ),
            reason="Confidence describes data trust, not equipment suitability.",
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
    blocks_default_off: bool = False,
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
        "blocks_default_off_path": blocks_default_off,
    }
    if extra:
        payload.update(extra)
    return payload


def _recommended_policy() -> dict[str, object]:
    return {
        "equipment_runtime_role": "practical_setup_helper_preserved",
        "nsom_owned_output": "ObserverCapability_profile_and_Q_target_projection",
        "first_runtime_safe_step": "shared_observer_capability_adapter_extraction",
        "default_off_replacement_policy": "defer_until_payload_and_environment_boundaries_exist",
        "seeing_policy": "environment_or_setup_stability_context_not_capability_scalar",
        "sky_quality_policy": "ObservationEnvironment_input_not_ObserverCapability_modifier",
        "confidence_policy": "metadata_only_zero_score_effect",
        "qml_payload_policy": "preserve_existing_equipment_payload_no_nsom_fields",
    }


def _readiness_checks(
    comparison: dict[str, object],
    decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
    evidence: dict[str, object],
) -> dict[str, object]:
    decision_ids = {decision["decision_id"] for decision in decisions}
    required_decisions = {
        "equipment_runtime_role",
        "observer_capability_adapter_policy",
        "q_target_runtime_policy",
        "seeing_policy",
        "sky_quality_policy",
        "payload_policy",
        "fallback_policy",
        "confidence_policy",
    }
    confidence = _decision_by_id(decisions, "confidence_policy")
    adapter = _decision_by_id(decisions, "observer_capability_adapter_policy")
    return {
        "comparison_report_developer_only": comparison["metadata"]["developer_only"] is True,
        "comparison_report_has_no_runtime_writes": comparison["metadata"]["runtime_writes"] is False,
        "comparison_report_has_candidate_evidence": comparison["metadata"]["candidate_row_count"] > 0,
        "required_policy_decisions_recorded": required_decisions.issubset(decision_ids),
        "default_off_runtime_replacement_deferred": any(
            decision["blocks_default_off_path"] is True for decision in decisions
        ),
        "observer_capability_adapter_ready_next": adapter["adapter_extraction_ready"] is True,
        "q_target_does_not_replace_setup_score": _decision_by_id(
            decisions,
            "q_target_runtime_policy",
        )["q_target_replaces_equipment_score"]
        is False,
        "observer_isolated_from_observable": evidence["observer_isolated_from_observable"] is True,
        "legacy_ownership_mixing_documented": evidence["legacy_ownership_mixing_observed"] is True,
        "confidence_score_neutral": confidence["score_effect"] == 0.0
        and evidence["confidence_score_effect"] == 0.0,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_behaviour_unchanged_by_review": True,
    }


def _default_off_blockers(
    checks: dict[str, object],
    decisions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    blockers = [
        f"equipment-{decision['decision_id'].replace('_', '-')}"
        for decision in decisions
        if decision["blocks_default_off_path"] is True
    ]
    safety_names = {
        "comparison_report_developer_only": "equipment-comparison-not-developer-only",
        "comparison_report_has_no_runtime_writes": "equipment-comparison-runtime-writes",
        "comparison_report_has_candidate_evidence": "equipment-comparison-evidence-missing",
        "required_policy_decisions_recorded": "equipment-policy-decisions-missing",
        "observer_capability_adapter_ready_next": "equipment-observer-adapter-not-ready",
        "q_target_does_not_replace_setup_score": "equipment-q-target-replaces-setup-score",
        "observer_isolated_from_observable": "equipment-observer-leaks-into-observable",
        "legacy_ownership_mixing_documented": "equipment-ownership-mixing-undocumented",
        "confidence_score_neutral": "equipment-confidence-not-neutral",
        "runtime_report_imports_absent": "equipment-runtime-report-wiring",
        "qml_exposure_absent": "equipment-qml-exposure",
        "runtime_behaviour_unchanged_by_review": "equipment-runtime-behaviour-change",
    }
    blockers.extend(name for key, name in safety_names.items() if checks[key] is not True)
    return tuple(dict.fromkeys(blockers))


def _comparison_evidence(comparison: dict[str, object]) -> dict[str, object]:
    scenarios = comparison["scenarios"]
    rows = tuple(row for scenario in scenarios for row in scenario["candidates"])
    disagreement_ids = tuple(
        scenario["scenario_id"]
        for scenario in scenarios
        if _top_id(scenario["rankings"]["legacy_equipment_score"])
        != _top_id(scenario["rankings"]["nsom_q_target"])
        or _top_id(scenario["rankings"]["legacy_equipment_score"])
        != _top_id(scenario["rankings"]["nsom_practical_target_value"])
    )
    confidence_effects = [
        abs(float(row["nsom"]["recommendation_confidence"]["score_effect"]))
        for row in rows
    ]
    return {
        "scenario_count": comparison["metadata"]["scenario_count"],
        "candidate_row_count": comparison["metadata"]["candidate_row_count"],
        "ranking_disagreement_scenarios": disagreement_ids,
        "legacy_ownership_mixing_observed": any(
            any(info.get("mixed_into_equipment_score") is True for info in row["legacy"]["ownership_mixing"].values())
            for row in rows
        ),
        "observer_isolated_from_observable": all(
            row["nsom"]["ownership"]["observer_equipment_effects"]["used_in_observable_target_value"] is False
            for row in rows
        ),
        "confidence_score_effect": max(confidence_effects) if confidence_effects else 0.0,
    }


def _top_id(rows: object) -> str | None:
    if not rows:
        return None
    first = rows[0]
    return str(first["candidate_id"])


def _non_blocking_risks() -> tuple[str, ...]:
    return (
        "The existing setup recommendation copy and setupOptions roles are UI-facing compatibility data.",
        "Seeing and sky quality still affect legacy EquipmentService setup scoring and need explicit boundaries before replacement.",
        "A shared ObserverCapability adapter should avoid depending on private EquipmentService helper methods long term.",
        "Q_target can rank capability differently from legacy setup score; this is expected evidence, not a calibration target.",
        "A future visible UI explanation step can expose rationale only after backend semantics are stable.",
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


def _readiness_reason(ready_for_default_off: bool) -> str:
    if ready_for_default_off:
        return (
            "Equipment policy decisions allow a default-off runtime replacement "
            "with no remaining blockers."
        )
    return (
        "EquipmentService is still the concrete setup presenter and fallback owner. "
        "The comparison is sufficient to extract ObserverCapability/Q_target, but "
        "a default-off runtime replacement should wait for payload and environment "
        "boundaries."
    )


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
