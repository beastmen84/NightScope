from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.tools.nsom_universe_catalogue_score_boundary_audit import (
    REPORT_PATH as SCORE_BOUNDARY_REPORT_PATH,
    generate_universe_catalogue_score_boundary_audit_data,
)


REPORT_PATH = Path("docs/NSOM_UNIVERSE_TARGET_PROFILE_POLICY.md")

REPORT_IMPORT_MARKERS = (
    "nsom_universe_target_profile_policy",
    "NSOM_UNIVERSE_TARGET_PROFILE_POLICY",
)

QML_MARKERS = (
    "nsomUniverseTargetProfilePolicy",
    "universeTargetProfilePolicy",
    "NSOM_UNIVERSE_TARGET_PROFILE_POLICY",
)

SOURCE_MARKERS = (
    {
        "surface": "IntrinsicTargetQuality core DTO",
        "path": Path("astro_viewer/app/models/nsom.py"),
        "markers": (
            "class IntrinsicTargetQuality",
            "owner: ClassVar[NsomOwnershipBoundary] = NsomOwnershipBoundary.UNIVERSE",
            "source_fields: NsomDiagnosticFields",
            "def from_score",
        ),
    },
    {
        "surface": "Runtime intrinsic adapter",
        "path": Path("astro_viewer/app/services/nsom_diagnostic_adapters.py"),
        "markers": (
            "def build_intrinsic_target_quality",
            '("score", _value(target, "score"))',
            "target_class_from_runtime_target(target)",
        ),
    },
    {
        "surface": "ObservationConditions raw target input",
        "path": Path("astro_viewer/app/services/observation_conditions_read_model.py"),
        "markers": (
            'nsom_input_policy: str = "raw_target_score"',
            "return self.raw_target",
            "return self.display_target",
        ),
    },
)


def generate_universe_target_profile_policy_data() -> dict[str, object]:
    """Developer-only policy decision for a first-class UniverseTargetProfile."""

    root = Path(__file__).parents[2]
    score_boundary = generate_universe_catalogue_score_boundary_audit_data()
    source_checks = _source_marker_checks(root)
    static_checks = _static_wiring_checks(root)
    options = _policy_options(score_boundary)
    decisions = _policy_decisions()
    entry_criteria = _future_entry_criteria()
    contract = _future_profile_contract()
    checks = _checks(score_boundary, source_checks, static_checks, options, decisions, entry_criteria, contract)
    blockers = _blockers(checks)

    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_policy": False,
            "scoring_changed": False,
            "planner_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "advanced_observing_changed": False,
            "sky_compass_changed": False,
            "detail_object_changed": False,
            "equipment_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "source_reports": (str(SCORE_BOUNDARY_REPORT_PATH).replace("\\", "/"),),
            "version": _read_text(root / "VERSION").strip(),
        },
        "readiness": {
            "verdict": (
                "universe_target_profile_deferred_non_blocking"
                if not blockers
                else "universe_target_profile_policy_needs_review"
            ),
            "introduce_runtime_profile_now": False,
            "keep_current_intrinsic_adapter": not blockers,
            "score_change_recommended_now": False,
            "visible_ui_change_recommended_now": False,
            "blocks_current_default_on_surfaces": False,
            "runtime_behaviour_changed_by_this_policy": False,
            "recommended_next_step": (
                "Review 1.14.0, then start visible score/explanation policy only "
                "if the UI needs to present NSOM rationale; otherwise keep the "
                "backend stable."
            ),
            "reason": (
                "A first-class UniverseTargetProfile would currently duplicate "
                "IntrinsicTargetQuality plus diagnostic source fields without "
                "changing any backend recommendation. The score boundary audit "
                "already prevents display-conditioned scores from becoming "
                "intrinsic target input, so the runtime profile should wait until "
                "there is a concrete provenance, catalogue-import, intrinsic-"
                "calibration or visible explanation requirement."
            ),
        },
        "policy_options": options,
        "policy_decisions": decisions,
        "future_profile_contract": contract,
        "future_entry_criteria": entry_criteria,
        "source_marker_checks": source_checks,
        "static_wiring_checks": static_checks,
        "checks": checks,
        "blockers": blockers,
        "recommended_sequence": (
            {
                "step": "Review 1.14.0",
                "summary": (
                    "Confirm the UniverseTargetProfile deferral is accurate and "
                    "does not hide a runtime scoring bug."
                ),
            },
            {
                "step": "Visible score/explanation policy",
                "summary": (
                    "Decide what, if anything, the UI should show for NSOM score "
                    "rationale without changing the established QML layout first."
                ),
            },
            {
                "step": "Future UniverseTargetProfile implementation",
                "summary": (
                    "Implement only when entry criteria such as score provenance, "
                    "new catalogue imports or intrinsic calibration are active."
                ),
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_universe_target_profile_policy_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# NSOM UniverseTargetProfile Policy",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only policy report decides whether to introduce a "
            "first-class UniverseTargetProfile after the 1.13.9 raw score boundary "
            "audit. The decision is no for now: keep the current "
            "IntrinsicTargetQuality adapter and defer the profile until a concrete "
            "provenance, catalogue-import, calibration or visible explanation need "
            "exists. No runtime scoring, ranking, QML, logging, network or runtime "
            "file-write behaviour changes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Introduce runtime profile now: `{readiness['introduce_runtime_profile_now']}`.",
        f"- Keep current intrinsic adapter: `{readiness['keep_current_intrinsic_adapter']}`.",
        f"- Score change recommended now: `{readiness['score_change_recommended_now']}`.",
        f"- Visible UI change recommended now: `{readiness['visible_ui_change_recommended_now']}`.",
        f"- Blocks current default-on surfaces: `{readiness['blocks_current_default_on_surfaces']}`.",
        (
            "- Runtime behaviour changed by this policy: "
            f"`{readiness['runtime_behaviour_changed_by_this_policy']}`."
        ),
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Policy Options",
        "",
        "| Option | Status | Runtime impact | Reason |",
        "| --- | --- | --- | --- |",
    ]
    for option in audit["policy_options"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{option['option_id']}`",
                    f"`{option['status']}`",
                    f"`{option['runtime_impact']}`",
                    option["reason"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Policy Decisions",
            "",
            "| Decision | Status | Affected layer | Blocks runtime | Reason |",
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
                    decision["affected_nsom_layer"],
                    f"`{decision['blocks_current_runtime']}`",
                    decision["reason"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Future Profile Contract",
            "",
            "| Field | Owner | Source today | Required before implementation |",
            "| --- | --- | --- | --- |",
        ]
    )
    for field in audit["future_profile_contract"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{field['field']}`",
                    field["owner"],
                    field["source_today"],
                    field["required_before_implementation"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Future Entry Criteria",
            "",
            "| Criterion | Status | Why it matters |",
            "| --- | --- | --- |",
        ]
    )
    for criterion in audit["future_entry_criteria"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{criterion['criterion_id']}`",
                    f"`{criterion['status']}`",
                    criterion["why_it_matters"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Source Marker Checks",
            "",
            "| Surface | Path | All markers found | Missing markers |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in audit["source_marker_checks"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["surface"],
                    f"`{item['path']}`",
                    f"`{item['all_markers_found']}`",
                    f"`{item['missing_markers']}`",
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
                "UniverseTargetProfile is a valid future boundary, but introducing "
                "it now would add a pass-through abstraction without improving "
                "runtime recommendations. Keep IntrinsicTargetQuality as the "
                "current internal Universe DTO, keep CelestialObject.score as an "
                "interim intrinsic seed, and revisit the profile only when "
                "provenance or visible explanation requirements become concrete."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _policy_options(score_boundary: dict[str, object]) -> tuple[dict[str, object], ...]:
    score_decisions = {
        decision["decision_id"]: decision for decision in score_boundary["boundary_decisions"]
    }
    return (
        {
            "option_id": "introduce_runtime_universe_target_profile_now",
            "status": "rejected_now",
            "runtime_impact": "would add runtime DTO/adaptation churn",
            "reason": (
                "Current default-on NSOM consumers already receive "
                "IntrinsicTargetQuality. A new runtime profile would mostly wrap "
                "the same prepared score and source fields without new semantics."
            ),
            "linked_1_13_9_decision": score_decisions["prepared_score_provenance"]["status"],
        },
        {
            "option_id": "keep_intrinsic_target_quality_adapter",
            "status": "accepted",
            "runtime_impact": "none",
            "reason": (
                "The adapter is already immutable/JSON-compatible through NSOM "
                "DTOs, and the read-model boundary keeps display-conditioned score "
                "out of intrinsic input."
            ),
            "linked_1_13_9_decision": score_decisions["catalogue_score_as_intrinsic_seed"]["status"],
        },
        {
            "option_id": "define_future_profile_contract_only",
            "status": "accepted_developer_policy",
            "runtime_impact": "none",
            "reason": (
                "Documenting the future fields prevents ad hoc provenance work "
                "without introducing unused runtime code."
            ),
            "linked_1_13_9_decision": "prepared_score_provenance",
        },
        {
            "option_id": "start_visible_score_explanation_now",
            "status": "deferred",
            "runtime_impact": "would require UI/presentation policy",
            "reason": (
                "Visible explanation should be a separate design step after backend "
                "score ownership is stable."
            ),
            "linked_1_13_9_decision": score_decisions["payload_score_semantics"]["status"],
        },
    )


def _policy_decisions() -> tuple[dict[str, object], ...]:
    return (
        {
            "decision_id": "runtime_universe_target_profile",
            "status": "deferred_non_blocking",
            "affected_nsom_layer": "Universe",
            "blocks_current_runtime": False,
            "reason": (
                "No current consumer requires a distinct profile beyond "
                "IntrinsicTargetQuality and diagnostic source fields."
            ),
        },
        {
            "decision_id": "intrinsic_adapter_policy",
            "status": "keep_current_adapter",
            "affected_nsom_layer": "Universe / IntrinsicTargetQuality",
            "blocks_current_runtime": False,
            "reason": (
                "The current adapter is the stable input boundary for default-on "
                "Planner, Home, Best Object, Sky Compass, Advanced Observing and "
                "Detail/Object projections."
            ),
        },
        {
            "decision_id": "score_provenance_policy",
            "status": "future_entry_criterion",
            "affected_nsom_layer": "Universe / catalogue read model",
            "blocks_current_runtime": False,
            "reason": (
                "Provenance becomes necessary before intrinsic calibration or "
                "visible score explanation, but is not required for the current "
                "closed backend recommendations."
            ),
        },
        {
            "decision_id": "visible_score_policy",
            "status": "separate_presentation_step",
            "affected_nsom_layer": "Presentation",
            "blocks_current_runtime": False,
            "reason": (
                "QML payload score compatibility remains unchanged; visible NSOM "
                "rationale needs product/UI policy before code exposure."
            ),
        },
    )


def _future_profile_contract() -> tuple[dict[str, object], ...]:
    return (
        {
            "field": "object_id",
            "owner": "Universe",
            "source_today": "CelestialObject.id",
            "required_before_implementation": "already available",
        },
        {
            "field": "target_class",
            "owner": "Universe",
            "source_today": "target_class_from_runtime_target()",
            "required_before_implementation": "already available",
        },
        {
            "field": "intrinsic_score_seed",
            "owner": "Universe",
            "source_today": "CelestialObject.score",
            "required_before_implementation": "explicit provenance label",
        },
        {
            "field": "score_provenance",
            "owner": "Universe / catalogue read model",
            "source_today": "not explicit",
            "required_before_implementation": "catalogue, engine, fixture and display-source distinction",
        },
        {
            "field": "geometry_summary",
            "owner": "Universe/location geometry",
            "source_today": "max_altitude, visible, observing_window",
            "required_before_implementation": "define which geometry is intrinsic seed vs session opportunity",
        },
        {
            "field": "magnitude_and_size",
            "owner": "Universe",
            "source_today": "magnitude, apparent_size",
            "required_before_implementation": "already available but surface-brightness model remains future work",
        },
        {
            "field": "display_score_projection",
            "owner": "Presentation",
            "source_today": "existing payload score fields",
            "required_before_implementation": "keep out of UniverseTargetProfile unless explicitly labelled presentation-only",
        },
    )


def _future_entry_criteria() -> tuple[dict[str, object], ...]:
    return (
        {
            "criterion_id": "intrinsic_calibration_requested",
            "status": "not_active",
            "why_it_matters": (
                "Calibrating target intrinsic value requires provenance and "
                "physical component separation."
            ),
        },
        {
            "criterion_id": "multiple_catalogue_sources_active",
            "status": "not_active",
            "why_it_matters": (
                "Different catalogue/import sources would need explicit source "
                "and score provenance."
            ),
        },
        {
            "criterion_id": "visible_score_explanation_required",
            "status": "not_active",
            "why_it_matters": (
                "UI explanation should not expose raw payload score as if it were "
                "the final NSOM rationale."
            ),
        },
        {
            "criterion_id": "remove_celestial_object_score_payload",
            "status": "not_active",
            "why_it_matters": (
                "Removing compatibility score fields requires a replacement "
                "presentation contract."
            ),
        },
        {
            "criterion_id": "surface_brightness_model_added",
            "status": "not_active",
            "why_it_matters": (
                "A richer intrinsic model would justify a dedicated Universe DTO "
                "instead of a score-seed adapter."
            ),
        },
    )


def _checks(
    score_boundary: dict[str, object],
    source_checks: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
    options: tuple[dict[str, object], ...],
    decisions: tuple[dict[str, object], ...],
    entry_criteria: tuple[dict[str, object], ...],
    contract: tuple[dict[str, object], ...],
) -> dict[str, object]:
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "score_boundary": score_boundary,
                "source_checks": source_checks,
                "options": options,
                "decisions": decisions,
                "entry_criteria": entry_criteria,
                "contract": contract,
            }
        ),
        "score_boundary_audit_clean": score_boundary["readiness"]["verdict"]
        == "universe_catalogue_score_boundary_audited",
        "runtime_profile_not_recommended_now": _option(
            options,
            "introduce_runtime_universe_target_profile_now",
        )["status"]
        == "rejected_now",
        "current_intrinsic_adapter_kept": _option(
            options,
            "keep_intrinsic_target_quality_adapter",
        )["status"]
        == "accepted",
        "future_contract_documented": len(contract) >= 6
        and any(item["field"] == "score_provenance" for item in contract),
        "entry_criteria_all_non_active": all(
            item["status"] == "not_active" for item in entry_criteria
        ),
        "policy_decisions_non_blocking": all(
            item["blocks_current_runtime"] is False for item in decisions
        ),
        "source_markers_all_found": all(item["all_markers_found"] is True for item in source_checks),
        "intrinsic_dto_boundary_present": _source_check(source_checks, "IntrinsicTargetQuality core DTO")[
            "all_markers_found"
        ]
        is True,
        "read_model_boundary_present": _source_check(
            source_checks,
            "ObservationConditions raw target input",
        )["all_markers_found"]
        is True,
        "no_scoring_change": True,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_policy": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blocker_names = {
        "strict_json_compatible": "universe-target-profile-json-incompatible",
        "score_boundary_audit_clean": "universe-target-profile-score-boundary-open",
        "runtime_profile_not_recommended_now": "universe-target-profile-runtime-profile-recommended",
        "current_intrinsic_adapter_kept": "universe-target-profile-current-adapter-not-kept",
        "future_contract_documented": "universe-target-profile-contract-missing",
        "entry_criteria_all_non_active": "universe-target-profile-entry-criterion-active",
        "policy_decisions_non_blocking": "universe-target-profile-blocking-decision",
        "source_markers_all_found": "universe-target-profile-source-marker-missing",
        "intrinsic_dto_boundary_present": "universe-target-profile-intrinsic-dto-missing",
        "read_model_boundary_present": "universe-target-profile-read-model-boundary-missing",
        "no_scoring_change": "universe-target-profile-scoring-change",
        "runtime_report_imports_absent": "universe-target-profile-runtime-wiring",
        "qml_report_exposure_absent": "universe-target-profile-qml-exposure",
        "runtime_behaviour_unchanged_by_policy": "universe-target-profile-runtime-change",
    }
    return tuple(name for key, name in blocker_names.items() if checks[key] is not True)


def _option(options: tuple[dict[str, object], ...], option_id: str) -> dict[str, object]:
    return next(item for item in options if item["option_id"] == option_id)


def _source_marker_checks(root: Path) -> tuple[dict[str, object], ...]:
    checks: list[dict[str, object]] = []
    for item in SOURCE_MARKERS:
        path = root / item["path"]
        text = _read_text(path)
        found = tuple(marker for marker in item["markers"] if marker in text)
        missing = tuple(marker for marker in item["markers"] if marker not in text)
        checks.append(
            {
                "surface": item["surface"],
                "path": str(item["path"]).replace("\\", "/"),
                "markers": item["markers"],
                "found_markers": found,
                "missing_markers": missing,
                "all_markers_found": path.exists() and not missing,
            }
        )
    return tuple(checks)


def _source_check(
    source_checks: tuple[dict[str, object], ...],
    surface: str,
) -> dict[str, object]:
    return next(item for item in source_checks if item["surface"] == surface)


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


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    write_markdown_report()
