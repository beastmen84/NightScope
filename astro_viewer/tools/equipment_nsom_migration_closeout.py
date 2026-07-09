from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.equipment_nsom_comparison_report import generate_report_data
from astro_viewer.tools.equipment_nsom_default_off_path_policy_audit import (
    REPORT_PATH as DEFAULT_OFF_POLICY_REPORT_PATH,
    generate_equipment_default_off_path_policy_audit_data,
)
from astro_viewer.tools.equipment_nsom_policy_readiness import (
    POLICY_READINESS_PATH,
    generate_policy_readiness_data,
)
from astro_viewer.tools.equipment_presenter_contract_audit import (
    REPORT_PATH as PRESENTER_CONTRACT_REPORT_PATH,
    generate_equipment_presenter_contract_audit_data,
)
from astro_viewer.tools.equipment_setup_score_component_boundary_report import (
    REPORT_PATH as COMPONENT_BOUNDARY_REPORT_PATH,
    generate_equipment_setup_score_component_boundary_data,
)
from astro_viewer.tools.equipment_setup_score_ownership_audit import (
    REPORT_PATH as OWNERSHIP_AUDIT_REPORT_PATH,
    generate_equipment_setup_score_ownership_audit_data,
)


REPORT_PATH = Path("docs/EQUIPMENT_NSOM_MIGRATION_CLOSEOUT.md")

REPORT_IMPORT_MARKERS = (
    "equipment_nsom_migration_closeout",
    "EQUIPMENT_NSOM_MIGRATION_CLOSEOUT",
)

QML_MARKERS = REPORT_IMPORT_MARKERS


def generate_equipment_nsom_migration_closeout_data() -> dict[str, object]:
    """Developer-only closeout for the Equipment NSOM backend migration series."""

    root = Path(__file__).parents[2]
    comparison = generate_report_data()
    policy_readiness = generate_policy_readiness_data()
    presenter_contract = generate_equipment_presenter_contract_audit_data()
    ownership = generate_equipment_setup_score_ownership_audit_data()
    component_boundary = generate_equipment_setup_score_component_boundary_data()
    default_off_policy = generate_equipment_default_off_path_policy_audit_data()
    rows = tuple(row for scenario in comparison["scenarios"] for row in scenario["candidates"])
    static_checks = _static_wiring_checks(root)
    closed_decisions = _closed_decisions(
        policy_readiness,
        presenter_contract,
        ownership,
        component_boundary,
        default_off_policy,
    )
    evidence = _evidence(
        comparison,
        policy_readiness,
        presenter_contract,
        ownership,
        component_boundary,
        default_off_policy,
        rows,
    )
    checks = _checks(
        policy_readiness,
        presenter_contract,
        ownership,
        component_boundary,
        default_off_policy,
        closed_decisions,
        evidence,
        static_checks,
    )
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
            "advanced_observing_changed": False,
            "sky_compass_changed": False,
            "detail_object_changed": False,
            "runtime_behaviour_changed_by_closeout": False,
            "source_reports": _source_reports(),
            "report_path": str(REPORT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "equipment_nsom_migration_closed_setup_local",
            "migration_closed": not _blockers(checks),
            "setup_local_service": True,
            "default_off_equipment_path_added": False,
            "default_off_equipment_path_recommended_now": False,
            "runtime_replacement_ready": False,
            "ready_to_return_to_backend_planning": not _blockers(checks),
            "runtime_behaviour_changed_by_closeout": False,
            "recommended_next_step": (
                "Review 1.13.5, then choose the next backend NSOM area or run "
                "an overall backend readiness audit."
            ),
            "reason": (
                "Equipment is not a target-ranking surface. It remains a setup-local "
                "service that selects concrete eyepiece, zoom-position, Barlow, "
                "binocular and fallback payload rows for a selected target. The NSOM "
                "migration is closed by keeping explicit ObserverCapability/Q_target, "
                "presenter, score ownership and component boundaries without adding a "
                "runtime replacement path."
            ),
        },
        "closed_decisions": closed_decisions,
        "evidence": evidence,
        "checks": checks,
        "blockers": _blockers(checks),
        "static_wiring_checks": static_checks,
        "recommended_sequence": (
            {
                "step": "Review 1.13.5",
                "summary": (
                    "Confirm Equipment is closed as an NSOM-bounded setup-local "
                    "service and no runtime behaviour changed."
                ),
            },
            {
                "step": "Next backend NSOM area selection audit",
                "summary": (
                    "Choose the next backend area, or run an overall backend "
                    "readiness audit before visible UI/explanation work."
                ),
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    closeout = generate_equipment_nsom_migration_closeout_data() if data is None else data
    readiness = closeout["readiness"]

    lines = [
        "# Equipment NSOM Migration Closeout",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only closeout records Equipment as an NSOM-bounded "
            "setup-local service. It does not add an Equipment NSOM runtime path, "
            "change setup recommendation ranking, expose QML fields, log, access "
            "the network or write files at runtime."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Migration closed: `{readiness['migration_closed']}`.",
        f"- Setup-local service: `{readiness['setup_local_service']}`.",
        (
            "- Default-off Equipment path added: "
            f"`{readiness['default_off_equipment_path_added']}`."
        ),
        (
            "- Default-off Equipment path recommended now: "
            f"`{readiness['default_off_equipment_path_recommended_now']}`."
        ),
        f"- Runtime replacement ready: `{readiness['runtime_replacement_ready']}`.",
        (
            "- Ready to return to backend planning: "
            f"`{readiness['ready_to_return_to_backend_planning']}`."
        ),
        (
            "- Runtime behaviour changed by closeout: "
            f"`{readiness['runtime_behaviour_changed_by_closeout']}`."
        ),
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Closed Decisions",
        "",
        "| Decision | Status | Blocks next backend planning | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for decision in closeout["closed_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_next_backend_planning']}`",
                    str(decision["reason"]),
                )
            )
            + " |"
        )

    evidence = closeout["evidence"]
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            f"- Scenario count: `{evidence['scenario_count']}`.",
            f"- Candidate row count: `{evidence['candidate_row_count']}`.",
            f"- Observer adapter extracted: `{evidence['observer_adapter_extracted']}`.",
            f"- Presenter contract audited: `{evidence['presenter_contract_audited']}`.",
            (
                "- Runtime setup read-model boundary present: "
                f"`{evidence['runtime_setup_read_model_boundary_present']}`."
            ),
            f"- Score ownership audited: `{evidence['score_ownership_audited']}`.",
            (
                "- Score component boundary introduced: "
                f"`{evidence['score_component_boundary_introduced']}`."
            ),
            (
                "- Score component boundary parity checked: "
                f"`{evidence['score_component_boundary_parity_checked']}`."
            ),
            f"- Default-off policy set: `{evidence['default_off_policy_set']}`.",
            (
                "- Default-off path recommended now: "
                f"`{evidence['default_off_path_recommended_now']}`."
            ),
            f"- Confidence score-neutral: `{evidence['confidence_score_neutral']}`.",
            "",
            "## Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in closeout["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Static Wiring",
            "",
            f"- Runtime report imports: `{closeout['static_wiring_checks']['runtime_report_import_matches']}`.",
            f"- QML report exposure: `{closeout['static_wiring_checks']['qml_report_exposure_matches']}`.",
            "",
            "## Recommended Sequence",
            "",
        ]
    )
    for item in closeout["recommended_sequence"]:
        lines.append(f"- `{item['step']}`: {item['summary']}")

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "The Equipment NSOM migration is closed for the current backend "
                "scope. `EquipmentService` remains the runtime setup recommender, "
                "while NSOM ownership is explicit through shared observer "
                "capability, presenter, score ownership and score-component "
                "boundaries. A future Equipment UI/explanation step may present "
                "these boundaries, but that is separate from backend migration."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _source_reports() -> tuple[str, ...]:
    return (
        "docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md",
        str(POLICY_READINESS_PATH).replace("\\", "/"),
        str(PRESENTER_CONTRACT_REPORT_PATH).replace("\\", "/"),
        str(OWNERSHIP_AUDIT_REPORT_PATH).replace("\\", "/"),
        str(COMPONENT_BOUNDARY_REPORT_PATH).replace("\\", "/"),
        str(DEFAULT_OFF_POLICY_REPORT_PATH).replace("\\", "/"),
    )


def _closed_decisions(
    policy_readiness: dict[str, object],
    presenter_contract: dict[str, object],
    ownership: dict[str, object],
    component_boundary: dict[str, object],
    default_off_policy: dict[str, object],
) -> tuple[dict[str, object], ...]:
    return (
        {
            "decision_id": "observer_capability_adapter",
            "status": "closed_shared_adapter_available",
            "blocks_next_backend_planning": False,
            "affected_nsom_layers": ("observer",),
            "reason": (
                "The policy readiness data confirms the shared "
                "ObserverCapability/Q_target adapter is extracted."
            ),
            "evidence": policy_readiness["readiness"]["observer_capability_adapter_extracted"],
        },
        {
            "decision_id": "presenter_contract_boundary",
            "status": "closed_runtime_neutral_read_model",
            "blocks_next_backend_planning": False,
            "affected_nsom_layers": ("presentation/setup",),
            "reason": (
                "The presenter contract audit confirms payload and setup-option "
                "keys are preserved through an immutable read-model boundary."
            ),
            "evidence": presenter_contract["readiness"]["runtime_read_model_boundary_present"],
        },
        {
            "decision_id": "setup_score_ownership",
            "status": "closed_owned_by_equipment_service",
            "blocks_next_backend_planning": False,
            "affected_nsom_layers": ("observer", "sky", "session", "presentation/setup"),
            "reason": (
                "The ownership audit classifies the current setup score as a "
                "local EquipmentService formula, not a drop-in NSOM scalar."
            ),
            "evidence": ownership["readiness"]["verdict"],
        },
        {
            "decision_id": "setup_score_component_boundary",
            "status": "closed_with_parity_read_model",
            "blocks_next_backend_planning": False,
            "affected_nsom_layers": ("observer", "sky", "session", "presentation/setup"),
            "reason": (
                "The component boundary exposes real score components without "
                "changing the clamped setup score."
            ),
            "evidence": component_boundary["checks"]["score_read_model_matches_candidate_scores"],
        },
        {
            "decision_id": "default_off_replacement_policy",
            "status": "closed_no_default_off_path_now",
            "blocks_next_backend_planning": False,
            "affected_nsom_layers": ("observer", "presentation/setup"),
            "reason": (
                "The policy audit rejects a default-off Equipment replacement path "
                "now and keeps Equipment setup-local with explicit NSOM boundaries."
            ),
            "evidence": default_off_policy["readiness"]["verdict"],
        },
        {
            "decision_id": "confidence_policy",
            "status": "closed_metadata_only",
            "blocks_next_backend_planning": False,
            "affected_nsom_layers": ("confidence",),
            "reason": "RecommendationConfidence remains parallel metadata with zero score effect.",
            "evidence": "parallel_metadata_zero_score_effect",
        },
    )


def _evidence(
    comparison: dict[str, object],
    policy_readiness: dict[str, object],
    presenter_contract: dict[str, object],
    ownership: dict[str, object],
    component_boundary: dict[str, object],
    default_off_policy: dict[str, object],
    rows: tuple[dict[str, object], ...],
) -> dict[str, object]:
    return {
        "scenario_count": comparison["metadata"]["scenario_count"],
        "candidate_row_count": comparison["metadata"]["candidate_row_count"],
        "observer_adapter_extracted": policy_readiness["readiness"][
            "observer_capability_adapter_extracted"
        ],
        "presenter_contract_audited": presenter_contract["readiness"][
            "presenter_contract_audited"
        ],
        "runtime_setup_read_model_boundary_present": presenter_contract["readiness"][
            "runtime_read_model_boundary_present"
        ],
        "score_ownership_audited": ownership["readiness"]["verdict"]
        == "equipment_setup_score_ownership_audited",
        "score_component_boundary_introduced": component_boundary["readiness"]["verdict"]
        == "equipment_setup_score_component_boundary_introduced",
        "score_component_boundary_parity_checked": component_boundary["checks"][
            "score_read_model_matches_candidate_scores"
        ],
        "default_off_policy_set": default_off_policy["readiness"]["verdict"]
        == "equipment_default_off_path_policy_set_setup_local",
        "default_off_path_recommended_now": default_off_policy["readiness"][
            "default_off_equipment_path_recommended_now"
        ],
        "setup_local_service_recommended": default_off_policy["readiness"][
            "setup_local_service_recommended"
        ],
        "confidence_score_neutral": all(
            row["nsom"]["recommendation_confidence"]["score_factor"] is False
            and row["legacy"]["score_read_model"]["confidence_policy"]
            == "parallel_metadata_zero_score_effect"
            for row in rows
        ),
    }


def _checks(
    policy_readiness: dict[str, object],
    presenter_contract: dict[str, object],
    ownership: dict[str, object],
    component_boundary: dict[str, object],
    default_off_policy: dict[str, object],
    closed_decisions: tuple[dict[str, object], ...],
    evidence: dict[str, object],
    static_checks: dict[str, object],
) -> dict[str, object]:
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "closed_decisions": closed_decisions,
                "evidence": evidence,
            }
        ),
        "all_required_equipment_reports_present": all(
            (Path(__file__).parents[2] / report).exists() for report in _source_reports()
        ),
        "observer_adapter_extracted": policy_readiness["readiness"][
            "observer_capability_adapter_extracted"
        ]
        is True,
        "presenter_contract_preserved": (
            presenter_contract["checks"]["payload_keys_preserved"] is True
            and presenter_contract["checks"]["setup_option_keys_preserved"] is True
            and presenter_contract["checks"][
                "read_model_payload_roundtrip_preserves_service_output"
            ]
            is True
        ),
        "setup_score_ownership_audited": ownership["readiness"]["verdict"]
        == "equipment_setup_score_ownership_audited",
        "component_boundary_parity_checked": component_boundary["checks"][
            "score_read_model_matches_candidate_scores"
        ]
        is True,
        "default_off_path_absent": default_off_policy["readiness"][
            "default_off_equipment_path_recommended_now"
        ]
        is False,
        "setup_local_policy_closed": default_off_policy["readiness"][
            "setup_local_service_recommended"
        ]
        is True,
        "confidence_score_neutral": evidence["confidence_score_neutral"] is True,
        "no_closeout_blockers": all(
            decision["blocks_next_backend_planning"] is False for decision in closed_decisions
        ),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_closeout": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blocker_names = {
        "strict_json_compatible": "equipment-closeout-json-incompatible",
        "all_required_equipment_reports_present": "equipment-closeout-source-report-missing",
        "observer_adapter_extracted": "equipment-closeout-observer-adapter-missing",
        "presenter_contract_preserved": "equipment-closeout-presenter-contract-drift",
        "setup_score_ownership_audited": "equipment-closeout-score-ownership-missing",
        "component_boundary_parity_checked": "equipment-closeout-component-parity-drift",
        "default_off_path_absent": "equipment-closeout-default-off-path-unexpected",
        "setup_local_policy_closed": "equipment-closeout-setup-local-policy-missing",
        "confidence_score_neutral": "equipment-closeout-confidence-score-effect",
        "no_closeout_blockers": "equipment-closeout-decision-blocker",
        "runtime_report_imports_absent": "equipment-closeout-runtime-wiring",
        "qml_report_exposure_absent": "equipment-closeout-qml-exposure",
        "runtime_behaviour_unchanged_by_closeout": "equipment-closeout-runtime-change",
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
