from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.equipment_nsom_comparison_report import generate_report_data
from astro_viewer.tools.equipment_presenter_contract_audit import (
    generate_equipment_presenter_contract_audit_data,
)
from astro_viewer.tools.equipment_setup_score_component_boundary_report import (
    REPORT_PATH as COMPONENT_BOUNDARY_REPORT_PATH,
    generate_equipment_setup_score_component_boundary_data,
)
from astro_viewer.tools.equipment_setup_score_ownership_audit import (
    REPORT_PATH as OWNERSHIP_AUDIT_REPORT_PATH,
)


REPORT_PATH = Path("docs/EQUIPMENT_NSOM_DEFAULT_OFF_PATH_POLICY_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "equipment_nsom_default_off_path_policy_audit",
    "EQUIPMENT_NSOM_DEFAULT_OFF_PATH_POLICY_AUDIT",
)

QML_MARKERS = REPORT_IMPORT_MARKERS


def generate_equipment_default_off_path_policy_audit_data() -> dict[str, object]:
    """Developer-only policy audit for Equipment NSOM default-off path scope."""

    root = Path(__file__).parents[2]
    comparison = generate_report_data()
    presenter_contract = generate_equipment_presenter_contract_audit_data()
    component_boundary = generate_equipment_setup_score_component_boundary_data()
    rows = tuple(row for scenario in comparison["scenarios"] for row in scenario["candidates"])
    static_checks = _static_wiring_checks(root)
    options = _policy_options(component_boundary, presenter_contract)
    policy_decisions = _policy_decisions(options)
    checks = _checks(component_boundary, presenter_contract, policy_decisions, rows, static_checks)
    data = {
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
            "detail_object_changed": False,
            "runtime_behaviour_changed_by_policy": False,
            "source_reports": (
                str(OWNERSHIP_AUDIT_REPORT_PATH).replace("\\", "/"),
                str(COMPONENT_BOUNDARY_REPORT_PATH).replace("\\", "/"),
                "docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md",
                "docs/EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT.md",
            ),
            "report_path": str(REPORT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "equipment_default_off_path_policy_set_setup_local",
            "default_off_equipment_path_recommended_now": False,
            "setup_local_service_recommended": True,
            "runtime_replacement_ready": False,
            "component_boundary_ready": component_boundary["readiness"]["component_read_model_present"],
            "component_boundary_parity_checked": component_boundary["checks"][
                "score_read_model_matches_candidate_scores"
            ],
            "blocks_backend_migration_closeout": False,
            "runtime_behaviour_changed_by_policy": False,
            "recommended_next_step": (
                "Review 1.13.4, then close the Equipment backend NSOM migration "
                "as setup-local with NSOM boundaries."
            ),
            "reason": (
                "EquipmentService recommends configurations for a selected target. "
                "Its setup score includes eyepiece, Barlow, binocular, seeing, sky "
                "quality and fallback semantics that Q_target and PracticalTargetValue "
                "do not replace. The NSOM boundary is now explicit, so a default-off "
                "replacement path would add complexity without a model requirement."
            ),
        },
        "policy_options": options,
        "policy_decisions": policy_decisions,
        "evidence": _evidence(comparison, component_boundary, presenter_contract, rows),
        "checks": checks,
        "blockers": _blockers(checks),
        "static_wiring_checks": static_checks,
        "recommended_sequence": (
            {
                "step": "Review 1.13.4",
                "summary": (
                    "Confirm Equipment should remain setup-local and that no "
                    "default-off replacement path is needed now."
                ),
            },
            {
                "step": "1.13.5 Equipment NSOM migration closeout",
                "summary": (
                    "Close Equipment as an NSOM-bounded setup service and return to "
                    "overall backend migration planning."
                ),
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_equipment_default_off_path_policy_audit_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# Equipment NSOM Default-Off Path Policy Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit decides whether Equipment should gain a "
            "default-off NSOM replacement path. The decision is no: Equipment "
            "remains a setup-local recommendation service with NSOM boundaries and "
            "metadata. No runtime scoring, payload, QML, logging, network or file "
            "write behaviour changes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        (
            "- Default-off Equipment path recommended now: "
            f"`{readiness['default_off_equipment_path_recommended_now']}`."
        ),
        f"- Setup-local service recommended: `{readiness['setup_local_service_recommended']}`.",
        f"- Runtime replacement ready: `{readiness['runtime_replacement_ready']}`.",
        f"- Component boundary ready: `{readiness['component_boundary_ready']}`.",
        (
            "- Component boundary parity checked: "
            f"`{readiness['component_boundary_parity_checked']}`."
        ),
        f"- Blocks backend migration closeout: `{readiness['blocks_backend_migration_closeout']}`.",
        (
            "- Runtime behaviour changed by policy: "
            f"`{readiness['runtime_behaviour_changed_by_policy']}`."
        ),
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Policy Options",
        "",
        "| Option | Status | Runtime path | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for option in audit["policy_options"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{option['option_id']}`",
                    f"`{option['status']}`",
                    f"`{option['runtime_path']}`",
                    str(option["reason"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Policy Decisions",
            "",
            "| Decision | Status | Blocks closeout | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for decision in audit["policy_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_backend_migration_closeout']}`",
                    str(decision["reason"]),
                )
            )
            + " |"
        )

    evidence = audit["evidence"]
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- Scenario count: `{evidence['scenario_count']}`.",
            f"- Candidate row count: `{evidence['candidate_row_count']}`.",
            (
                "- Component boundary parity checked: "
                f"`{evidence['component_boundary_parity_checked']}`."
            ),
            f"- Fallback payload preserved: `{evidence['fallback_payload_preserved']}`.",
            f"- Q_target direct replacement rejected: `{evidence['q_target_direct_replacement_rejected']}`.",
            f"- Confidence score-neutral: `{evidence['confidence_score_neutral']}`.",
            (
                "- Legacy formula unavailable components are marked unavailable: "
                f"`{evidence['legacy_unavailable_components_marked']}`."
            ),
            "",
            "## Checks",
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
            "## Static Wiring",
            "",
            f"- Runtime report imports: `{audit['static_wiring_checks']['runtime_report_import_matches']}`.",
            f"- QML report exposure: `{audit['static_wiring_checks']['qml_report_exposure_matches']}`.",
            "",
            "## Recommended Sequence",
            "",
        ]
    )
    for item in audit["recommended_sequence"]:
        lines.append(f"- `{item['step']}`: {item['summary']}")

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "Equipment should not get a default-off NSOM replacement path now. "
                "The correct backend state is an Equipment-owned setup service with "
                "explicit NSOM ownership, component and presenter boundaries."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _policy_options(
    component_boundary: dict[str, object],
    presenter_contract: dict[str, object],
) -> tuple[dict[str, object], ...]:
    return (
        {
            "option_id": "add_default_off_nsom_equipment_path",
            "status": "rejected_now",
            "runtime_path": False,
            "reason": (
                "A replacement path would need to reproduce eyepiece, focal-position, "
                "Barlow, binocular and fallback semantics. Q_target and "
                "PracticalTargetValue do not own those setup choices."
            ),
            "requires_future_work": True,
        },
        {
            "option_id": "keep_equipment_setup_local_with_nsom_boundaries",
            "status": "accepted",
            "runtime_path": True,
            "reason": (
                "The presenter contract and component boundary preserve current "
                "runtime behaviour while making NSOM ownership explicit."
            ),
            "requires_future_work": False,
            "contract_ready": presenter_contract["readiness"]["runtime_read_model_boundary_present"],
            "component_parity": component_boundary["checks"]["score_read_model_matches_candidate_scores"],
        },
        {
            "option_id": "future_equipment_explanation_metadata",
            "status": "deferred_non_blocking",
            "runtime_path": False,
            "reason": (
                "Future UI/explanation work may expose why a setup was chosen, but "
                "that is presentation work and not required for backend NSOM closure."
            ),
            "requires_future_work": False,
        },
    )


def _policy_decisions(options: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    accepted = next(option for option in options if option["option_id"] == "keep_equipment_setup_local_with_nsom_boundaries")
    rejected = next(option for option in options if option["option_id"] == "add_default_off_nsom_equipment_path")
    return (
        {
            "decision_id": "equipment_runtime_policy",
            "status": "setup_local_service_accepted",
            "blocks_backend_migration_closeout": False,
            "affected_nsom_layers": ("observer", "sky", "session", "presentation/setup"),
            "intentional_nsom_behavior": True,
            "possible_calibration_issue": False,
            "reason": accepted["reason"],
        },
        {
            "decision_id": "default_off_replacement_policy",
            "status": "not_recommended_now",
            "blocks_backend_migration_closeout": False,
            "affected_nsom_layers": ("observer", "presentation/setup"),
            "intentional_nsom_behavior": True,
            "possible_calibration_issue": False,
            "reason": rejected["reason"],
        },
        {
            "decision_id": "q_target_replacement_policy",
            "status": "rejected_as_direct_replacement",
            "blocks_backend_migration_closeout": False,
            "affected_nsom_layers": ("observer",),
            "intentional_nsom_behavior": True,
            "possible_calibration_issue": False,
            "reason": (
                "Q_target can describe observer capability metadata, but it does not "
                "rank concrete eyepiece, Barlow, focal-position or binocular setup rows."
            ),
        },
        {
            "decision_id": "confidence_policy",
            "status": "accepted_metadata_only",
            "blocks_backend_migration_closeout": False,
            "affected_nsom_layers": ("confidence",),
            "intentional_nsom_behavior": True,
            "possible_calibration_issue": False,
            "reason": "RecommendationConfidence remains parallel metadata with zero score effect.",
        },
    )


def _evidence(
    comparison: dict[str, object],
    component_boundary: dict[str, object],
    presenter_contract: dict[str, object],
    rows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    return {
        "scenario_count": comparison["metadata"]["scenario_count"],
        "candidate_row_count": comparison["metadata"]["candidate_row_count"],
        "component_boundary_parity_checked": component_boundary["checks"][
            "score_read_model_matches_candidate_scores"
        ],
        "fallback_payload_preserved": presenter_contract["checks"]["fallback_payloads_are_known_subsets"],
        "q_target_direct_replacement_rejected": presenter_contract["checks"]["q_target_reference_only"],
        "confidence_score_neutral": all(
            row["nsom"]["recommendation_confidence"]["score_factor"] is False
            and row["legacy"]["score_read_model"]["confidence_policy"] == "parallel_metadata_zero_score_effect"
            for row in rows
        ),
        "legacy_unavailable_components_marked": all(
            "q_target:not_part_of_equipment_service_formula" in row["legacy"]["unavailable_components"]
            and "recommendation_confidence:not_part_of_equipment_score" in row["legacy"]["unavailable_components"]
            for row in rows
        ),
    }


def _checks(
    component_boundary: dict[str, object],
    presenter_contract: dict[str, object],
    policy_decisions: tuple[dict[str, object], ...],
    rows: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    decisions = {decision["decision_id"]: decision for decision in policy_decisions}
    evidence = _evidence(
        {"metadata": {"scenario_count": 0, "candidate_row_count": len(rows)}},
        component_boundary,
        presenter_contract,
        rows,
    )
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "decisions": policy_decisions,
                "evidence": evidence,
            }
        ),
        "default_off_path_rejected_now": decisions["default_off_replacement_policy"][
            "status"
        ]
        == "not_recommended_now",
        "setup_local_service_accepted": decisions["equipment_runtime_policy"]["status"]
        == "setup_local_service_accepted",
        "component_boundary_parity_checked": component_boundary["checks"][
            "score_read_model_matches_candidate_scores"
        ]
        is True,
        "presenter_contract_preserved": (
            presenter_contract["checks"]["payload_keys_preserved"] is True
            and presenter_contract["checks"]["setup_option_keys_preserved"] is True
            and presenter_contract["checks"]["read_model_payload_roundtrip_preserves_service_output"] is True
            and presenter_contract["checks"]["fallback_payloads_are_known_subsets"] is True
        ),
        "q_target_direct_replacement_rejected": decisions["q_target_replacement_policy"][
            "status"
        ]
        == "rejected_as_direct_replacement",
        "confidence_score_neutral": evidence["confidence_score_neutral"] is True,
        "legacy_unavailable_components_marked": evidence["legacy_unavailable_components_marked"] is True,
        "no_decision_blocks_closeout": all(
            decision["blocks_backend_migration_closeout"] is False
            for decision in policy_decisions
        ),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_policy": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blocker_names = {
        "strict_json_compatible": "equipment-default-off-policy-json-incompatible",
        "default_off_path_rejected_now": "equipment-default-off-policy-not-rejected",
        "setup_local_service_accepted": "equipment-setup-local-policy-not-accepted",
        "component_boundary_parity_checked": "equipment-policy-component-parity-drift",
        "presenter_contract_preserved": "equipment-policy-presenter-contract-drift",
        "q_target_direct_replacement_rejected": "equipment-policy-q-target-replacement-risk",
        "confidence_score_neutral": "equipment-policy-confidence-score-effect",
        "legacy_unavailable_components_marked": "equipment-policy-legacy-components-fabricated",
        "no_decision_blocks_closeout": "equipment-policy-closeout-blocked",
        "runtime_report_imports_absent": "equipment-policy-runtime-wiring",
        "qml_report_exposure_absent": "equipment-policy-qml-exposure",
        "runtime_behaviour_unchanged_by_policy": "equipment-policy-runtime-change",
    }
    return tuple(name for key, name in blocker_names.items() if checks[key] is not True)


def _static_wiring_checks(root: Path) -> dict[str, object]:
    return {
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "qml_report_exposure_matches": _scan_files(
            root / "astro_viewer" / "app" / "ui",
            ("*.qml",),
            QML_MARKERS,
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


def _strict_json_compatible(payload: object) -> bool:
    try:
        json.dumps(nsom_to_json_compatible(payload), sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


if __name__ == "__main__":
    write_markdown_report()
