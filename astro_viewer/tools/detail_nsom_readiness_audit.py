from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.detail_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)


READINESS_AUDIT_PATH = Path("docs/DETAIL_OBJECT_NSOM_READINESS_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "detail_nsom_readiness_audit",
    "DETAIL_OBJECT_NSOM_READINESS_AUDIT",
)

QML_MARKERS = (
    "detailObjectNsom",
    "selectedObjectNsom",
    "DETAIL_OBJECT_NSOM_READINESS_AUDIT",
)

RUNTIME_DETAIL_MARKERS = (
    "DetailObjectNsomComparisonService",
    "detail_nsom_comparison",
    "detail_nsom_readiness_audit",
    "DETAIL_OBJECT_NSOM_READINESS_AUDIT",
)


def generate_readiness_audit_data() -> dict[str, object]:
    comparison = generate_report_data()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    source_policy = _source_policy_review(comparison)
    display = _display_score_semantics(comparison)
    payload = _payload_contract_review()
    confidence = _confidence_review(comparison)
    runtime_safety = _runtime_safety(comparison, static_checks)
    blockers = _default_off_blockers(
        source_policy=source_policy,
        display=display,
        payload=payload,
        confidence=confidence,
        runtime_safety=runtime_safety,
    )
    ready = blockers == ()
    audit_data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "selected_object_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed": False,
            "sky_compass_changed": False,
            "source_report": str(COMPARISON_REPORT_PATH).replace("\\", "/"),
            "audit_report_path": str(READINESS_AUDIT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": (
                "ready_for_default_off_detail_nsom_path"
                if ready
                else "not_ready_for_default_off_detail_nsom_path"
            ),
            "ready_for_default_off_path": ready,
            "runtime_path_exists": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "ready_for_visible_ui": False,
            "recommended_next_step": (
                "1.10.2 Detail/Object source and display policy contract"
                if not ready
                else "implement a default-off Detail/Object NSOM path behind explicit rollback"
            ),
            "reason": _readiness_reason(ready),
        },
        "blockers": blockers,
        "source_policy_review": source_policy,
        "display_score_semantics": display,
        "payload_contract_review": payload,
        "confidence_review": confidence,
        "runtime_safety": runtime_safety,
        "static_wiring_checks": static_checks,
        "comparison_summary": comparison["summary"],
    }
    return nsom_to_json_compatible(audit_data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_readiness_audit_data() if data is None else data
    readiness = audit["readiness"]
    source = audit["source_policy_review"]
    display = audit["display_score_semantics"]
    payload = audit["payload_contract_review"]
    confidence = audit["confidence_review"]

    lines = [
        "# Detail/Object NSOM Readiness Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether the Detail/Object comparison "
            "evidence is ready for a default-off runtime path. It does not change "
            "`selectedObject`, QML, Home, Best Object, Planner, Sky Compass, logging, "
            "network behaviour or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-off path: `{readiness['ready_for_default_off_path']}`.",
        f"- Runtime path exists: `{readiness['runtime_path_exists']}`.",
        f"- Ready for visible UI: `{readiness['ready_for_visible_ui']}`.",
        f"- Runtime behaviour changed by this audit: `{readiness['runtime_behaviour_changed_by_this_audit']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}.",
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
            "## Source Policy Review",
            "",
            f"- Status: `{source['status']}`.",
            f"- Blocks default-off path: `{source['blocks_default_off_path']}`.",
            f"- Observing policy: `{source['observing_source_policy']}`.",
            f"- Catalogue policy: `{source['catalogue_source_policy']}`.",
            f"- Observing display score: `{source['observing_bright_moon_display_score']}`.",
            f"- Catalogue display score: `{source['catalogue_bright_moon_display_score']}`.",
            f"- Comparable observable values: `{source['comparable_observable_values']}`.",
            f"- Decision needed: {source['decision_needed']}",
            "",
            "## Displayed Score Semantics",
            "",
            f"- Status: `{display['status']}`.",
            f"- Blocks default-off path: `{display['blocks_default_off_path']}`.",
            f"- Keep legacy displayed score for compatibility: `{display['keep_legacy_displayed_score_for_compatibility']}`.",
            f"- Score monotonic with NSOM values: `{display['score_monotonic_with_nsom_values']}`.",
            f"- Decision needed: {display['decision_needed']}",
            "",
            "## Payload Contract Review",
            "",
            f"- Status: `{payload['status']}`.",
            f"- Blocks default-off path: `{payload['blocks_default_off_path']}`.",
            f"- Existing payload should remain unchanged: `{payload['preserve_existing_selected_object_payload']}`.",
            f"- Add NSOM fields now: `{payload['add_nsom_fields_now']}`.",
            f"- Decision needed: {payload['decision_needed']}",
            "",
            "## Confidence Review",
            "",
            f"- Status: `{confidence['status']}`.",
            f"- Blocks default-off path: `{confidence['blocks_default_off_path']}`.",
            f"- Score factor: `{confidence['score_factor']}`.",
            f"- Score effect: `{confidence['score_effect']}`.",
            "",
            "## Runtime Safety",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["runtime_safety"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Recommended Next Steps",
            "",
            "1. Review and decide the Detail source policy explicitly.",
            "2. Define a payload/display contract before adding any default-off runtime path.",
            "3. Keep visible NSOM explanation UI as a later design step.",
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = READINESS_AUDIT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _source_policy_review(comparison: dict[str, object]) -> dict[str, object]:
    observing = _scenario(comparison, "D01_observing_bright_moon")
    catalogue = _scenario(comparison, "D02_catalogue_bright_moon")
    observing_legacy = observing["legacy"]["selected_object_detail"]
    catalogue_legacy = catalogue["legacy"]["selected_object_detail"]
    observable_equal = (
        float(observing["nsom"]["observable_target_value"]["value"])
        == float(catalogue["nsom"]["observable_target_value"]["value"])
    )
    return {
        "status": "needs_policy_decision",
        "blocks_default_off_path": True,
        "observing_source_policy": observing_legacy["policy"],
        "catalogue_source_policy": catalogue_legacy["policy"],
        "observing_bright_moon_display_score": observing_legacy["display_score"],
        "catalogue_bright_moon_display_score": catalogue_legacy["display_score"],
        "comparable_observable_values": observable_equal,
        "decision_needed": (
            "Decide whether a future Detail NSOM path preserves source-specific "
            "legacy display score semantics, or introduces a separate NSOM "
            "explanation/rationale payload while leaving `selectedObject.score` "
            "as compatibility data."
        ),
    }


def _display_score_semantics(comparison: dict[str, object]) -> dict[str, object]:
    observing = _scenario(comparison, "D01_observing_bright_moon")
    catalogue = _scenario(comparison, "D02_catalogue_bright_moon")
    observing_legacy = observing["legacy"]["selected_object_detail"]
    catalogue_legacy = catalogue["legacy"]["selected_object_detail"]
    score_monotonic = (
        float(observing_legacy["display_score"]) == float(catalogue_legacy["display_score"])
        if float(observing["nsom"]["observable_target_value"]["value"])
        == float(catalogue["nsom"]["observable_target_value"]["value"])
        else False
    )
    return {
        "status": "needs_contract",
        "blocks_default_off_path": True,
        "keep_legacy_displayed_score_for_compatibility": True,
        "score_monotonic_with_nsom_values": score_monotonic,
        "observing_display_score": observing_legacy["display_score"],
        "catalogue_display_score": catalogue_legacy["display_score"],
        "observing_observable_value": observing["nsom"]["observable_target_value"]["value"],
        "catalogue_observable_value": catalogue["nsom"]["observable_target_value"]["value"],
        "decision_needed": (
            "Document that visible `score` remains legacy/base compatibility data, "
            "then define any future NSOM rationale fields separately."
        ),
    }


def _payload_contract_review() -> dict[str, object]:
    return {
        "status": "not_defined",
        "blocks_default_off_path": True,
        "preserve_existing_selected_object_payload": True,
        "add_nsom_fields_now": False,
        "qml_payload_shape_change_allowed": False,
        "decision_needed": (
            "Define a future internal payload contract before runtime code starts "
            "building Detail NSOM data. The first runtime path should preserve "
            "`selectedObject` keys and keep NSOM fields private or separately named."
        ),
    }


def _confidence_review(comparison: dict[str, object]) -> dict[str, object]:
    control = comparison["confidence_control"]
    return {
        "status": "accepted",
        "blocks_default_off_path": False,
        "low_confidence_value": control["low_confidence_value"],
        "high_confidence_value": control["high_confidence_value"],
        "observable_delta": control["observable_delta"],
        "practical_delta": control["practical_delta"],
        "legacy_display_delta": control["legacy_display_delta"],
        "score_factor": control["score_factor"],
        "score_effect": control["score_effect"],
        "decision": "RecommendationConfidence remains metadata-only and does not modify Detail values.",
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
        "selected_object_runtime_unchanged": metadata["selected_object_changed"] is False,
        "home_runtime_unchanged": metadata["home_changed"] is False,
        "best_object_runtime_unchanged": metadata["best_object_changed"] is False,
        "planner_runtime_unchanged": metadata["planner_changed"] is False,
        "sky_compass_runtime_unchanged": metadata["sky_compass_changed"] is False,
        "controller_runtime_wiring_absent": static_checks["controller_detail_comparison_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
    }


def _default_off_blockers(
    *,
    source_policy: dict[str, object],
    display: dict[str, object],
    payload: dict[str, object],
    confidence: dict[str, object],
    runtime_safety: dict[str, object],
) -> tuple[str, ...]:
    blockers: list[str] = []
    if source_policy["blocks_default_off_path"] is True:
        blockers.append("detail-source-policy-unresolved")
    if display["blocks_default_off_path"] is True:
        blockers.append("detail-displayed-score-semantics-unresolved")
    if payload["blocks_default_off_path"] is True:
        blockers.append("detail-payload-contract-not-defined")
    if confidence["blocks_default_off_path"] is True:
        blockers.append("detail-confidence-policy-unresolved")
    if not all(value is True for value in runtime_safety.values()):
        blockers.append("detail-runtime-safety")
    return tuple(blockers)


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    return {
        "qml_matches": _scan_files(app_root / "ui", ("*.qml",), QML_MARKERS),
        "controller_detail_comparison_matches": _scan_files(
            app_root / "viewmodels",
            ("*.py",),
            RUNTIME_DETAIL_MARKERS,
        ),
        "runtime_report_import_matches": _scan_files(
            app_root,
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
            "Detail source policy, displayed score semantics, payload contract, "
            "confidence neutrality and runtime safety are all documented."
        )
    return (
        "Detail has source-specific legacy display semantics and no defined NSOM "
        "payload/display contract yet. A default-off runtime path should wait "
        "until those policies are explicit."
    )


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
