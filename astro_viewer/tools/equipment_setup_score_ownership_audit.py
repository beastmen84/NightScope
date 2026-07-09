from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.equipment_setup_score_read_model import (
    EQUIPMENT_SETUP_SCORE_COMPONENT_METADATA,
    EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER,
    EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS,
    EQUIPMENT_SETUP_SCORE_FORMULA,
)
from astro_viewer.tools.equipment_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)
from astro_viewer.tools.equipment_presenter_contract_audit import (
    REPORT_PATH as PRESENTER_CONTRACT_REPORT_PATH,
    generate_equipment_presenter_contract_audit_data,
)


REPORT_PATH = Path("docs/EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "equipment_setup_score_ownership_audit",
    "EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT",
)

QML_MARKERS = REPORT_IMPORT_MARKERS

COMPONENT_WEIGHTS = dict(EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS)


def generate_equipment_setup_score_ownership_audit_data() -> dict[str, object]:
    """Developer-only audit of EquipmentService setup score ownership."""

    root = Path(__file__).parents[2]
    comparison = generate_report_data()
    presenter_contract = generate_equipment_presenter_contract_audit_data()
    rows = tuple(row for scenario in comparison["scenarios"] for row in scenario["candidates"])
    component_policies = _component_policies()
    static_checks = _static_wiring_checks(root)
    checks = _checks(comparison, presenter_contract, rows, component_policies, static_checks)
    blockers = _blockers(checks)

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
            "runtime_behaviour_changed_by_this_audit": False,
            "source_reports": (
                str(COMPARISON_REPORT_PATH).replace("\\", "/"),
                str(PRESENTER_CONTRACT_REPORT_PATH).replace("\\", "/"),
            ),
            "report_path": str(REPORT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "equipment_setup_score_ownership_audited",
            "runtime_replacement_ready": False,
            "score_component_boundary_recommended": True,
            "default_off_equipment_path_recommended_now": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "recommended_next_step": (
                "Review 1.13.3, then audit whether Equipment needs a default-off "
                "NSOM setup path or should remain setup-local."
            ),
            "reason": (
                "EquipmentService setup score is useful and deterministic, but its "
                "single scalar mixes target traits, observer configuration, seeing, "
                "sky quality and presentation practicality. The 1.13.3 component "
                "read-model makes that boundary explicit; replacement still needs "
                "a separate policy audit."
            ),
        },
        "formula": {
            "name": "EquipmentService._configuration_score",
            "formula": EQUIPMENT_SETUP_SCORE_FORMULA,
            "component_weights": COMPONENT_WEIGHTS,
            "total_weight": sum(COMPONENT_WEIGHTS.values()),
            "source": "astro_viewer/app/services/equipment_service.py",
            "component_boundary": "EquipmentSetupScoreReadModel",
        },
        "component_policies": component_policies,
        "component_statistics": _component_statistics(rows),
        "scenario_evidence": _scenario_evidence(comparison),
        "decision_log": _decision_log(component_policies),
        "presenter_contract_readiness": presenter_contract["readiness"],
        "checks": checks,
        "blockers": blockers,
        "static_wiring_checks": static_checks,
        "recommended_sequence": (
            {
                "step": "Review 1.13.2",
                "summary": (
                    "Confirm setup-score ownership is classified correctly and "
                    "does not imply score tuning."
                ),
            },
            {
                "step": "1.13.3 Equipment setup-score component boundary",
                "summary": (
                    "Extract a runtime-neutral setup-score component read-model "
                    "with parity tests before any replacement path."
                ),
            },
            {
                "step": "Review 1.13.3",
                "summary": (
                    "Confirm the component boundary preserves EquipmentService "
                    "score parity and remains internal."
                ),
            },
            {
                "step": "1.13.4 Equipment default-off path policy audit",
                "summary": (
                    "Decide whether Equipment needs a default-off NSOM setup path "
                    "or should remain a setup-local recommendation service."
                ),
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_equipment_setup_score_ownership_audit_data() if data is None else data
    readiness = audit["readiness"]
    formula = audit["formula"]

    lines = [
        "# Equipment Setup Score Ownership Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit classifies the current EquipmentService "
            "setup-score components from EquipmentService._configuration_score "
            "before any scoring replacement. It does not change "
            "EquipmentService, Planner, Home, Best Object, Advanced Observing, "
            "Sky Compass, Detail/Object, QML, logging, network behaviour or "
            "runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Runtime replacement ready: `{readiness['runtime_replacement_ready']}`.",
        (
            "- Score component boundary recommended: "
            f"`{readiness['score_component_boundary_recommended']}`."
        ),
        (
            "- Default-off Equipment path recommended now: "
            f"`{readiness['default_off_equipment_path_recommended_now']}`."
        ),
        (
            "- Runtime behaviour changed by this audit: "
            f"`{readiness['runtime_behaviour_changed_by_this_audit']}`."
        ),
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Current Formula",
        "",
        f"- Formula: `{formula['formula']}`.",
        f"- Total weight: `{formula['total_weight']}`.",
        f"- Source: `{formula['source']}`.",
        "",
        "| Component | Weight | Current inputs | NSOM ownership | Replacement policy |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for component in audit["component_policies"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{component['component']}`",
                    f"{float(component['weight']):.0f}",
                    ", ".join(component["current_inputs"]),
                    ", ".join(component["nsom_layers"]),
                    str(component["replacement_policy"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Component Statistics",
            "",
            "| Component | Average | Max | Appears in rows |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for component, stats in audit["component_statistics"].items():
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{component}`",
                    f"{float(stats['average']):.2f}",
                    f"{float(stats['max']):.2f}",
                    str(stats["row_count"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Scenario Evidence",
            "",
            "| Scenario | Rows | Score sums match | Main mixed components |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for scenario in audit["scenario_evidence"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    str(scenario["scenario_id"]),
                    str(scenario["candidate_count"]),
                    f"`{scenario['component_sums_match_scores']}`",
                    ", ".join(scenario["main_mixed_components"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Decision Log",
            "",
            "| Decision | Status | Blocks replacement | Reason |",
            "| --- | --- | --- | --- |",
        ]
    )
    for decision in audit["decision_log"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_runtime_replacement']}`",
                    str(decision["reason"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
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
                "EquipmentService should not be replaced by Q_target or by a raw "
                "NSOM target-value score. The setup-score component boundary is "
                "now explicit; only after review and a policy audit should a "
                "default-off replacement path be considered."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _component_policies() -> tuple[dict[str, object], ...]:
    return tuple(
        _component_policy(
            component,
            current_inputs=tuple(
                str(item)
                for item in EQUIPMENT_SETUP_SCORE_COMPONENT_METADATA[component]["current_inputs"]
            ),
            nsom_layers=tuple(
                str(item)
                for item in EQUIPMENT_SETUP_SCORE_COMPONENT_METADATA[component]["nsom_layers"]
            ),
            replacement_policy=str(
                EQUIPMENT_SETUP_SCORE_COMPONENT_METADATA[component]["replacement_policy"]
            ),
        )
        for component in EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER
    )


def _component_policy(
    component: str,
    *,
    current_inputs: tuple[str, ...],
    nsom_layers: tuple[str, ...],
    replacement_policy: str,
) -> dict[str, object]:
    return {
        "component": component,
        "weight": COMPONENT_WEIGHTS[component],
        "current_inputs": current_inputs,
        "nsom_layers": nsom_layers,
        "replacement_policy": replacement_policy,
        "blocks_runtime_replacement": True,
        "score_tuning_recommended": False,
    }


def _component_statistics(rows: tuple[dict[str, object], ...]) -> dict[str, dict[str, object]]:
    stats: dict[str, dict[str, object]] = {}
    for component in COMPONENT_WEIGHTS:
        values = [
            float(row["legacy"]["components"][component])
            for row in rows
            if component in row["legacy"]["components"]
        ]
        stats[component] = {
            "row_count": len(values),
            "average": sum(values) / len(values) if values else 0.0,
            "max": max(values) if values else 0.0,
            "weight": COMPONENT_WEIGHTS[component],
        }
    return stats


def _scenario_evidence(comparison: dict[str, object]) -> tuple[dict[str, object], ...]:
    scenarios = []
    for scenario in comparison["scenarios"]:
        rows = tuple(scenario["candidates"])
        scenarios.append(
            {
                "scenario_id": scenario["scenario_id"],
                "candidate_count": len(rows),
                "component_sums_match_scores": all(
                    abs(float(row["legacy"]["component_sum"]) - float(row["legacy"]["score"])) < 1e-9
                    for row in rows
                ),
                "main_mixed_components": _main_mixed_components(rows),
            }
        )
    return tuple(scenarios)


def _main_mixed_components(rows: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    component_max = {
        component: max(float(row["legacy"]["components"][component]) for row in rows)
        for component in COMPONENT_WEIGHTS
    }
    ordered = sorted(component_max.items(), key=lambda item: item[1], reverse=True)
    return tuple(component for component, value in ordered[:3] if value > 0.0)


def _decision_log(component_policies: tuple[dict[str, object], ...]) -> tuple[dict[str, object], ...]:
    return (
        {
            "decision_id": "equipment_score_scalar_policy",
            "status": "needs_component_boundary",
            "blocks_runtime_replacement": True,
            "reason": (
                "The current scalar is a setup-local score, not NSOM target value, "
                "PracticalTargetValue or RecommendationConfidence."
            ),
        },
        {
            "decision_id": "sky_and_seeing_ownership",
            "status": "needs_explicit_setup_context",
            "blocks_runtime_replacement": True,
            "reason": (
                "Sky quality and seeing affect the legacy score and must be visible "
                "as setup context before replacement."
            ),
        },
        {
            "decision_id": "q_target_replacement_policy",
            "status": "rejected_as_direct_replacement",
            "blocks_runtime_replacement": True,
            "reason": (
                "Q_target lacks eyepiece, focal-position, Barlow and fallback semantics."
            ),
        },
        {
            "decision_id": "component_coverage",
            "status": "covered",
            "blocks_runtime_replacement": False,
            "reason": f"{len(component_policies)} score components are classified.",
        },
        {
            "decision_id": "confidence_policy",
            "status": "accepted_metadata_only",
            "blocks_runtime_replacement": False,
            "reason": "RecommendationConfidence remains parallel metadata with zero score effect.",
        },
    )


def _checks(
    comparison: dict[str, object],
    presenter_contract: dict[str, object],
    rows: tuple[dict[str, object], ...],
    component_policies: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    component_names = {component["component"] for component in component_policies}
    scenario_evidence = _scenario_evidence(comparison)
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "component_policies": component_policies,
                "scenario_evidence": scenario_evidence,
            }
        ),
        "formula_components_match_equipment_service": set(COMPONENT_WEIGHTS) == component_names,
        "component_weights_sum_to_100": sum(COMPONENT_WEIGHTS.values()) == 100.0,
        "all_component_sums_match_scores": all(
            scenario["component_sums_match_scores"] is True for scenario in scenario_evidence
        ),
        "all_components_block_replacement_until_boundary": all(
            component["blocks_runtime_replacement"] is True for component in component_policies
        ),
        "sky_and_seeing_not_hidden_in_observer_capability": _sky_and_seeing_not_hidden(rows),
        "q_target_not_direct_replacement": presenter_contract["checks"]["q_target_reference_only"] is True,
        "confidence_score_neutral": presenter_contract["checks"]["confidence_score_neutral"] is True,
        "setup_read_model_boundary_present": presenter_contract["checks"]["setup_read_model_boundary_present"] is True,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _sky_and_seeing_not_hidden(rows: tuple[dict[str, object], ...]) -> bool:
    return all(
        row["nsom"]["ownership"]["sky_quality_effects"]["used_in_observer_capability"] is False
        and row["nsom"]["ownership"]["seeing_effects"]["used_in_observer_capability"] is False
        for row in rows
    )


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blocker_names = {
        "strict_json_compatible": "equipment-score-audit-json-incompatible",
        "formula_components_match_equipment_service": "equipment-score-audit-formula-drift",
        "component_weights_sum_to_100": "equipment-score-audit-weight-drift",
        "all_component_sums_match_scores": "equipment-score-audit-component-parity-drift",
        "all_components_block_replacement_until_boundary": "equipment-score-audit-component-boundary-not-blocking",
        "sky_and_seeing_not_hidden_in_observer_capability": "equipment-score-audit-sky-seeing-hidden-in-observer",
        "q_target_not_direct_replacement": "equipment-score-audit-q-target-replacement-risk",
        "confidence_score_neutral": "equipment-score-audit-confidence-score-effect",
        "setup_read_model_boundary_present": "equipment-score-audit-read-model-boundary-missing",
        "runtime_report_imports_absent": "equipment-score-audit-runtime-wiring",
        "qml_report_exposure_absent": "equipment-score-audit-qml-exposure",
        "runtime_behaviour_unchanged_by_audit": "equipment-score-audit-runtime-change",
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
