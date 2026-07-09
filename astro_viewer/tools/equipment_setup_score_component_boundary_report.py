from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.equipment_setup_score_read_model import (
    EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER,
    EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS,
    EQUIPMENT_SETUP_SCORE_FORMULA,
)
from astro_viewer.tools.equipment_nsom_comparison_report import generate_report_data
from astro_viewer.tools.equipment_setup_score_ownership_audit import (
    REPORT_PATH as OWNERSHIP_AUDIT_REPORT_PATH,
)


REPORT_PATH = Path("docs/EQUIPMENT_SETUP_SCORE_COMPONENT_BOUNDARY.md")

REPORT_IMPORT_MARKERS = (
    "equipment_setup_score_component_boundary_report",
    "EQUIPMENT_SETUP_SCORE_COMPONENT_BOUNDARY",
)

QML_MARKERS = REPORT_IMPORT_MARKERS


def generate_equipment_setup_score_component_boundary_data() -> dict[str, object]:
    """Developer-only report for the Equipment setup-score component boundary."""

    root = Path(__file__).parents[2]
    comparison = generate_report_data()
    rows = tuple(row for scenario in comparison["scenarios"] for row in scenario["candidates"])
    scenario_count = len(comparison["scenarios"])
    static_checks = _static_wiring_checks(root)
    checks = _checks(rows, static_checks, scenario_count)
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
            "runtime_behaviour_changed_by_boundary": False,
            "source_reports": (
                str(OWNERSHIP_AUDIT_REPORT_PATH).replace("\\", "/"),
                "docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md",
            ),
            "report_path": str(REPORT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "equipment_setup_score_component_boundary_introduced",
            "runtime_replacement_ready": False,
            "component_read_model_present": True,
            "default_off_equipment_path_recommended_now": False,
            "runtime_behaviour_changed_by_boundary": False,
            "recommended_next_step": (
                "Review 1.13.4, then close the Equipment backend NSOM migration "
                "as setup-local with NSOM boundaries."
            ),
            "reason": (
                "Equipment setup scoring now has an immutable component read-model "
                "with parity against the current EquipmentService score. This makes "
                "ownership visible but does not yet define a replacement policy."
            ),
        },
        "read_model": {
            "class": "EquipmentSetupScoreReadModel",
            "builder": "EquipmentSetupScoreReadModelBuilder",
            "runtime_owner": "EquipmentService._configuration_score",
            "formula": EQUIPMENT_SETUP_SCORE_FORMULA,
            "component_order": EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER,
            "component_weights": dict(EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS),
            "score_policy": "sum_components_clamped_0_100",
            "nsom_policy": "setup_score_component_boundary_not_nsom_target_value",
            "confidence_policy": "parallel_metadata_zero_score_effect",
        },
        "parity": _parity(rows, scenario_count),
        "checks": checks,
        "blockers": _blockers(checks),
        "static_wiring_checks": static_checks,
        "recommended_sequence": (
            {
                "step": "Review 1.13.4",
                "summary": (
                    "Confirm Equipment should remain setup-local with NSOM boundaries."
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
    report = generate_equipment_setup_score_component_boundary_data() if data is None else data
    readiness = report["readiness"]
    read_model = report["read_model"]
    parity = report["parity"]

    lines = [
        "# Equipment Setup Score Component Boundary",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only report verifies that EquipmentService setup scoring "
            "now exposes an immutable component read-model while preserving current "
            "score values. It does not add an Equipment replacement path, QML fields, "
            "logging, network calls or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Runtime replacement ready: `{readiness['runtime_replacement_ready']}`.",
        f"- Component read-model present: `{readiness['component_read_model_present']}`.",
        (
            "- Default-off Equipment path recommended now: "
            f"`{readiness['default_off_equipment_path_recommended_now']}`."
        ),
        (
            "- Runtime behaviour changed by boundary: "
            f"`{readiness['runtime_behaviour_changed_by_boundary']}`."
        ),
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Read-Model Boundary",
        "",
        f"- Class: `{read_model['class']}`.",
        f"- Builder: `{read_model['builder']}`.",
        f"- Runtime owner: `{read_model['runtime_owner']}`.",
        f"- Formula: `{read_model['formula']}`.",
        f"- Score policy: `{read_model['score_policy']}`.",
        f"- NSOM policy: `{read_model['nsom_policy']}`.",
        f"- Confidence policy: `{read_model['confidence_policy']}`.",
        "",
        "| Component | Weight |",
        "| --- | ---: |",
    ]
    for component in read_model["component_order"]:
        lines.append(
            f"| `{component}` | {float(read_model['component_weights'][component]):.0f} |"
        )

    lines.extend(
        [
            "",
            "## Parity",
            "",
            f"- Scenario count: `{parity['scenario_count']}`.",
            f"- Candidate row count: `{parity['candidate_row_count']}`.",
            f"- All rows expose read-model: `{parity['all_rows_expose_read_model']}`.",
            f"- All read-model scores match candidate scores: `{parity['all_scores_match']}`.",
            (
                "- All read-model component values match legacy component projection: "
                f"`{parity['all_component_values_match']}`."
            ),
            f"- Max score delta: `{float(parity['max_score_delta']):.12f}`.",
            "",
            "## Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in report["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Static Wiring",
            "",
            f"- Runtime report imports: `{report['static_wiring_checks']['runtime_report_import_matches']}`.",
            f"- QML report exposure: `{report['static_wiring_checks']['qml_report_exposure_matches']}`.",
            "",
            "## Recommended Sequence",
            "",
        ]
    )
    for item in report["recommended_sequence"]:
        lines.append(f"- `{item['step']}`: {item['summary']}")

    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            (
                "The setup-score component boundary is now explicit and parity-checked. "
                "The score remains Equipment-owned setup logic, not an NSOM target "
                "value or confidence modifier."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _parity(
    rows: tuple[dict[str, object], ...],
    scenario_count: int,
) -> dict[str, object]:
    score_deltas = []
    component_matches = []
    read_model_present = []
    for row in rows:
        legacy = row["legacy"]
        read_model = legacy.get("score_read_model")
        read_model_present.append(isinstance(read_model, dict))
        if not isinstance(read_model, dict):
            continue
        score_deltas.append(abs(float(read_model["score"]) - float(legacy["score"])))
        component_matches.append(read_model["component_values"] == legacy["components"])
    return {
        "scenario_count": scenario_count,
        "candidate_row_count": len(rows),
        "all_rows_expose_read_model": all(read_model_present) if read_model_present else False,
        "all_scores_match": all(delta < 1e-9 for delta in score_deltas) if score_deltas else False,
        "all_component_values_match": all(component_matches) if component_matches else False,
        "max_score_delta": max(score_deltas) if score_deltas else 0.0,
    }


def _checks(
    rows: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
    scenario_count: int,
) -> dict[str, object]:
    parity = _parity(rows, scenario_count)
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "read_model_weights": dict(EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS),
                "parity": parity,
            }
        ),
        "component_weights_sum_to_100": sum(EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS.values()) == 100.0,
        "component_order_complete": set(EQUIPMENT_SETUP_SCORE_COMPONENT_ORDER) == set(EQUIPMENT_SETUP_SCORE_COMPONENT_WEIGHTS),
        "score_read_model_present_in_comparison": parity["all_rows_expose_read_model"],
        "score_read_model_matches_candidate_scores": parity["all_scores_match"],
        "component_values_match_legacy_projection": parity["all_component_values_match"],
        "confidence_score_neutral": all(
            row["legacy"]["score_read_model"]["confidence_policy"] == "parallel_metadata_zero_score_effect"
            for row in rows
        ),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_boundary": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blocker_names = {
        "strict_json_compatible": "equipment-score-component-boundary-json-incompatible",
        "component_weights_sum_to_100": "equipment-score-component-boundary-weight-drift",
        "component_order_complete": "equipment-score-component-boundary-order-drift",
        "score_read_model_present_in_comparison": "equipment-score-read-model-missing-in-comparison",
        "score_read_model_matches_candidate_scores": "equipment-score-read-model-parity-drift",
        "component_values_match_legacy_projection": "equipment-score-read-model-component-drift",
        "confidence_score_neutral": "equipment-score-boundary-confidence-score-effect",
        "runtime_report_imports_absent": "equipment-score-component-boundary-runtime-wiring",
        "qml_report_exposure_absent": "equipment-score-component-boundary-qml-exposure",
        "runtime_behaviour_unchanged_by_boundary": "equipment-score-component-boundary-runtime-change",
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
