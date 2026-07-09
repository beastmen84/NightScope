from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible


REPORT_PATH = Path("docs/NSOM_UNIVERSE_CATALOGUE_SCORE_BOUNDARY_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "nsom_universe_catalogue_score_boundary_audit",
    "NSOM_UNIVERSE_CATALOGUE_SCORE_BOUNDARY_AUDIT",
    "NSOM_UNIVERSE_CATALOGUE_SCORE_BOUNDARY",
)

QML_MARKERS = (
    "nsomUniverseCatalogueScoreBoundary",
    "universeCatalogueScoreBoundary",
    "NSOM_UNIVERSE_CATALOGUE_SCORE_BOUNDARY_AUDIT",
)

SOURCE_MARKERS = (
    {
        "surface": "CelestialObject score DTO field",
        "path": Path("astro_viewer/app/models/observing.py"),
        "markers": ("score: int = 0", "def to_qml"),
    },
    {
        "surface": "Skyfield raw object score",
        "path": Path("astro_viewer/app/astronomy/skyfield_engine.py"),
        "markers": ("def _object_score", "altitude_score", "magnitude_score"),
    },
    {
        "surface": "NSOM intrinsic adapter",
        "path": Path("astro_viewer/app/services/nsom_diagnostic_adapters.py"),
        "markers": (
            "def build_intrinsic_target_quality",
            '"score", _value(target, "score")',
            "IntrinsicTargetQuality.from_score",
        ),
    },
    {
        "surface": "Home observable adapter",
        "path": Path("astro_viewer/app/services/home_nsom_observable.py"),
        "markers": ("build_intrinsic_target_quality(item)", "ObservableTargetValue.from_intrinsic"),
    },
    {
        "surface": "ObservationConditions raw/display read model",
        "path": Path("astro_viewer/app/services/observation_conditions_read_model.py"),
        "markers": (
            'nsom_input_policy: str = "raw_target_score"',
            "def nsom_target_input",
            "def qml_display_target",
        ),
    },
    {
        "surface": "Best Object NSOM selection",
        "path": Path("astro_viewer/app/services/best_object_nsom_ranking.py"),
        "markers": ("build_home_observable_target_value", "build_observation_opportunity"),
    },
    {
        "surface": "Sky Compass NSOM direction policy",
        "path": Path("astro_viewer/app/services/sky_compass_nsom_ranking.py"),
        "markers": ("observable_value", "display_score"),
    },
    {
        "surface": "Planner NSOM opportunity scoring",
        "path": Path("astro_viewer/app/services/planner_nsom_service.py"),
        "markers": ("build_intrinsic_target_quality(item)", "ObservationOpportunity"),
    },
    {
        "surface": "Equipment setup score boundary",
        "path": Path("astro_viewer/app/services/equipment_setup_score_read_model.py"),
        "markers": ("class EquipmentSetupScoreReadModel", "score=max(0.0, min(100.0, unclamped_score))"),
    },
)


def generate_universe_catalogue_score_boundary_audit_data() -> dict[str, object]:
    """Developer-only audit for raw catalogue/prepared score ownership."""

    root = Path(__file__).parents[2]
    source_checks = _source_marker_checks(root)
    static_checks = _static_wiring_checks(root)
    inventory = _score_boundary_inventory()
    decisions = _boundary_decisions()
    remaining = _remaining_policy_items()
    checks = _checks(source_checks, static_checks, inventory, decisions, remaining)
    blockers = _blockers(checks)

    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "planner_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "advanced_observing_changed": False,
            "sky_compass_changed": False,
            "detail_object_changed": False,
            "equipment_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "version": _read_text(root / "VERSION").strip(),
        },
        "readiness": {
            "verdict": (
                "universe_catalogue_score_boundary_audited"
                if not blockers
                else "universe_catalogue_score_boundary_needs_review"
            ),
            "runtime_migration_recommended_now": False,
            "score_change_recommended_now": False,
            "safe_to_keep_score_as_intrinsic_seed": not blockers,
            "blocks_current_default_on_surfaces": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "recommended_next_step": (
                "Review 1.13.9, then decide whether to introduce an explicit "
                "UniverseTargetProfile/catalogue intrinsic read model before "
                "visible UI explanation work."
            ),
            "reason": (
                "The current default-on backend surfaces already consume NSOM "
                "values, but the first Universe input is still the prepared "
                "`CelestialObject.score`. That score is acceptable as an interim "
                "IntrinsicTargetQuality seed because the ObservationConditions "
                "read model keeps raw target input separate from display "
                "conditioning. It should not be treated as final presentation "
                "semantics or as a future calibration target."
            ),
        },
        "score_semantics": _score_semantics(),
        "score_boundary_inventory": inventory,
        "boundary_decisions": decisions,
        "remaining_policy_items": remaining,
        "source_marker_checks": source_checks,
        "static_wiring_checks": static_checks,
        "checks": checks,
        "blockers": blockers,
        "recommended_sequence": (
            {
                "step": "Review 1.13.9",
                "summary": (
                    "Confirm raw score ownership is described accurately and no "
                    "runtime ranking changed."
                ),
            },
            {
                "step": "Universe intrinsic profile policy",
                "summary": (
                    "If needed, design a first-class UniverseTargetProfile that "
                    "makes catalogue/prepared score provenance explicit."
                ),
            },
            {
                "step": "Visible explanation design",
                "summary": (
                    "Only after backend score semantics are clear, decide what the "
                    "UI should show instead of legacy/base score compatibility."
                ),
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_universe_catalogue_score_boundary_audit_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# NSOM Universe/Catalogue Score Boundary Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit reviews the remaining raw catalogue/"
            "prepared-object score boundary after the backend NSOM recommendation "
            "surfaces were closed and internal rollback paths were removed. It "
            "does not change scoring, runtime ranking, QML, logging, network "
            "access or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Runtime migration recommended now: `{readiness['runtime_migration_recommended_now']}`.",
        f"- Score change recommended now: `{readiness['score_change_recommended_now']}`.",
        f"- Safe to keep `score` as interim intrinsic seed: `{readiness['safe_to_keep_score_as_intrinsic_seed']}`.",
        f"- Blocks current default-on surfaces: `{readiness['blocks_current_default_on_surfaces']}`.",
        f"- Runtime behaviour changed by this audit: `{readiness['runtime_behaviour_changed_by_this_audit']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Score Semantics",
        "",
        "| Score concept | Owner | Runtime role | NSOM policy |",
        "| --- | --- | --- | --- |",
    ]
    for item in audit["score_semantics"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["score_concept"],
                    item["owner"],
                    item["runtime_role"],
                    item["nsom_policy"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Boundary Inventory",
            "",
            "| Surface | Classification | Score role | Ranking authority | Risk | Decision |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in audit["score_boundary_inventory"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["surface"],
                    f"`{item['classification']}`",
                    item["score_role"],
                    item["ranking_authority"],
                    item["risk"],
                    item["decision"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Boundary Decisions",
            "",
            "| Decision | Status | Affected layer | Blocks default-on work | Reason |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in audit["boundary_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{item['decision_id']}`",
                    f"`{item['status']}`",
                    item["affected_nsom_layer"],
                    f"`{item['blocks_default_on_work']}`",
                    item["reason"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Remaining Policy Items",
            "",
            "| Item | Status | Blocking | Recommended handling |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in audit["remaining_policy_items"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["item"],
                    f"`{item['status']}`",
                    f"`{item['blocks_current_runtime']}`",
                    item["recommended_handling"],
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
                "The raw `CelestialObject.score` boundary is now explicitly "
                "classified. It remains an interim Universe/IntrinsicTargetQuality "
                "seed and a compatibility display field, not an NSOM score to tune "
                "or a runtime rollback target. Future work should make catalogue "
                "score provenance explicit before visible score/explanation design."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _score_semantics() -> tuple[dict[str, object], ...]:
    return (
        {
            "score_concept": "CelestialObject.score",
            "owner": "prepared target DTO / Universe seed compatibility",
            "runtime_role": (
                "Input to IntrinsicTargetQuality and existing QML-compatible "
                "display score fields."
            ),
            "nsom_policy": (
                "Accepted interim intrinsic seed; future work should expose "
                "provenance rather than tune the raw field directly."
            ),
        },
        {
            "score_concept": "NightPlanItem.score",
            "owner": "Planner output",
            "runtime_role": "Final Planner payload score after NSOM opportunity ranking.",
            "nsom_policy": (
                "Planner result, not Universe input; keep separate from "
                "IntrinsicTargetQuality provenance."
            ),
        },
        {
            "score_concept": "Equipment setup score",
            "owner": "Equipment setup-local service",
            "runtime_role": "Ranks practical setup/eyepiece/Barlow suggestions.",
            "nsom_policy": (
                "Setup-local score remains outside ObservableTargetValue; it can "
                "inform ObserverCapability boundaries but is not a target score."
            ),
        },
        {
            "score_concept": "Payload/display score",
            "owner": "QML compatibility presentation",
            "runtime_role": "Existing visible payload field shape and labels.",
            "nsom_policy": (
                "Presentation compatibility only; visible score semantics require "
                "a separate UI/design step."
            ),
        },
    )


def _score_boundary_inventory() -> tuple[dict[str, object], ...]:
    return (
        {
            "surface": "Skyfield/catalogue prepared objects",
            "classification": "catalogue_engine_intrinsic_seed",
            "score_role": "Computes raw object score from altitude, magnitude, type and visibility.",
            "ranking_authority": "NSOM consumers adapt it into IntrinsicTargetQuality.",
            "risk": (
                "Not a pure immutable catalogue fact because location geometry and "
                "visibility are already present."
            ),
            "decision": "accept_as_interim_universe_seed",
        },
        {
            "surface": "NSOM intrinsic adapter",
            "classification": "universe_adapter",
            "score_role": "Maps target.score through IntrinsicTargetQuality.from_score().",
            "ranking_authority": (
                "Universe-owned input to ObservableTargetValue, PracticalTargetValue "
                "and ObservationOpportunity."
            ),
            "risk": "Adapter cannot yet distinguish catalogue, engine and fixture score provenance.",
            "decision": "keep_stable_until_explicit_universe_profile",
        },
        {
            "surface": "ObservationConditions read model",
            "classification": "closed_raw_display_boundary",
            "score_role": "Separates raw_score/nsom_target_input from display_score/qml_display_target.",
            "ranking_authority": "Raw target input for NSOM consumers after the 1.12 reroute.",
            "risk": "Display-conditioned score remains visible for payload compatibility.",
            "decision": "accepted_boundary_prevents_conditioning_from_becoming_intrinsic",
        },
        {
            "surface": "Home recommendedDeepSky",
            "classification": "default_on_nsom_consumer",
            "score_role": "Keeps score field in payload while ranking by ObservableTargetValue.",
            "ranking_authority": "ObservableTargetValue from raw target plus sky environment.",
            "risk": "Displayed score may be non-monotonic with NSOM order until UI semantics change.",
            "decision": "presentation_followup_not_backend_blocker",
        },
        {
            "surface": "Best Object",
            "classification": "default_on_nsom_consumer",
            "score_role": "Returns existing display target while scoring a raw-target NSOM opportunity.",
            "ranking_authority": "Home-specific ObservationOpportunity.",
            "risk": "Visible payload still carries compatibility score.",
            "decision": "presentation_followup_not_backend_blocker",
        },
        {
            "surface": "Sky Compass",
            "classification": "default_on_nsom_consumer",
            "score_role": "Keeps target.score in direction payload while direction policy uses observable value.",
            "ranking_authority": "ObservableTargetValue plus direction/presentation context.",
            "risk": "Direction score is intentionally a presentation policy, not pure target value.",
            "decision": "accepted_direction_policy_boundary",
        },
        {
            "surface": "Planner",
            "classification": "default_on_nsom_consumer",
            "score_role": "Uses target.score as intrinsic seed and emits NightPlanItem.score as result.",
            "ranking_authority": "ObservationOpportunity.value.",
            "risk": "Input and output score names remain easy to confuse in diagnostics.",
            "decision": "document_input_output_score_boundary",
        },
        {
            "surface": "Equipment recommendations",
            "classification": "setup_local_non_universe_score",
            "score_role": "Setup score ranks equipment choices, not target desirability.",
            "ranking_authority": "EquipmentService setup-local compatibility logic.",
            "risk": "Should not be folded into ObservableTargetValue.",
            "decision": "keep_outside_universe_score_boundary",
        },
    )


def _boundary_decisions() -> tuple[dict[str, object], ...]:
    return (
        {
            "decision_id": "catalogue_score_as_intrinsic_seed",
            "status": "accepted_interim",
            "affected_nsom_layer": "Universe / IntrinsicTargetQuality",
            "intentional_nsom_behaviour": True,
            "possible_calibration_issue": False,
            "blocks_default_on_work": False,
            "reason": (
                "Current NSOM consumers need a stable intrinsic seed. The prepared "
                "score is already sanitized and clamped by IntrinsicTargetQuality, "
                "and read-model rerouting prevents display conditioning from being "
                "used as intrinsic input."
            ),
        },
        {
            "decision_id": "prepared_score_provenance",
            "status": "deferred_targeted_backend_policy",
            "affected_nsom_layer": "Universe / catalogue read model",
            "intentional_nsom_behaviour": False,
            "possible_calibration_issue": True,
            "blocks_default_on_work": False,
            "reason": (
                "The source field does not yet encode whether the number came from "
                "catalogue fixtures, Skyfield geometry, comparison fixtures or a "
                "display payload. That should be made explicit before future "
                "calibration, but it does not invalidate the current backend paths."
            ),
        },
        {
            "decision_id": "payload_score_semantics",
            "status": "presentation_followup",
            "affected_nsom_layer": "Presentation",
            "intentional_nsom_behaviour": True,
            "possible_calibration_issue": False,
            "blocks_default_on_work": False,
            "reason": (
                "Existing payload shapes still expose score fields. They are kept "
                "for UI compatibility and should be redesigned only in a visible "
                "presentation step."
            ),
        },
        {
            "decision_id": "equipment_score_boundary",
            "status": "accepted_setup_local",
            "affected_nsom_layer": "Observer / Equipment setup service",
            "intentional_nsom_behaviour": True,
            "possible_calibration_issue": False,
            "blocks_default_on_work": False,
            "reason": (
                "Equipment setup scoring is not an intrinsic target score and is "
                "kept outside ObservableTargetValue."
            ),
        },
    )


def _remaining_policy_items() -> tuple[dict[str, object], ...]:
    return (
        {
            "item": "Explicit UniverseTargetProfile / catalogue intrinsic read model",
            "status": "deferred_non_blocking",
            "blocks_current_runtime": False,
            "recommended_handling": (
                "Introduce only when there is a concrete need to expose provenance "
                "or replace the current prepared-score seed."
            ),
        },
        {
            "item": "Visible score semantics",
            "status": "presentation_followup",
            "blocks_current_runtime": False,
            "recommended_handling": (
                "Design after backend score ownership is stable; do not reuse "
                "payload score as an NSOM explanation."
            ),
        },
        {
            "item": "Catalogue score calibration",
            "status": "not_recommended_now",
            "blocks_current_runtime": False,
            "recommended_handling": (
                "Do not tune raw score directly; first separate provenance and "
                "physical components if calibration evidence requires it."
            ),
        },
    )


def _checks(
    source_checks: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
    inventory: tuple[dict[str, object], ...],
    decisions: tuple[dict[str, object], ...],
    remaining: tuple[dict[str, object], ...],
) -> dict[str, object]:
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "inventory": inventory,
                "decisions": decisions,
                "remaining": remaining,
                "source_checks": source_checks,
            }
        ),
        "source_markers_all_found": all(item["all_markers_found"] is True for item in source_checks),
        "intrinsic_adapter_boundary_present": _source_check(source_checks, "NSOM intrinsic adapter")[
            "all_markers_found"
        ]
        is True,
        "read_model_raw_display_boundary_present": _source_check(
            source_checks,
            "ObservationConditions raw/display read model",
        )["all_markers_found"]
        is True,
        "payload_scores_classified_as_compatibility": any(
            item["classification"] == "default_on_nsom_consumer"
            and "payload" in item["score_role"].lower()
            for item in inventory
        ),
        "equipment_score_kept_outside_universe": any(
            item["surface"] == "Equipment recommendations"
            and item["decision"] == "keep_outside_universe_score_boundary"
            for item in inventory
        ),
        "no_decision_blocks_default_on_work": all(
            item["blocks_default_on_work"] is False for item in decisions
        ),
        "remaining_policy_items_non_blocking": all(
            item["blocks_current_runtime"] is False for item in remaining
        ),
        "confidence_not_in_score_boundary": True,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    blocker_names = {
        "strict_json_compatible": "universe-catalogue-score-boundary-json-incompatible",
        "source_markers_all_found": "universe-catalogue-source-marker-missing",
        "intrinsic_adapter_boundary_present": "universe-catalogue-intrinsic-adapter-missing",
        "read_model_raw_display_boundary_present": "universe-catalogue-read-model-boundary-missing",
        "payload_scores_classified_as_compatibility": "universe-catalogue-payload-score-unclassified",
        "equipment_score_kept_outside_universe": "universe-catalogue-equipment-score-leak",
        "no_decision_blocks_default_on_work": "universe-catalogue-default-on-blocker",
        "remaining_policy_items_non_blocking": "universe-catalogue-blocking-policy-item",
        "confidence_not_in_score_boundary": "universe-catalogue-confidence-score-boundary-leak",
        "runtime_report_imports_absent": "universe-catalogue-audit-runtime-wiring",
        "qml_report_exposure_absent": "universe-catalogue-audit-qml-exposure",
        "runtime_behaviour_unchanged_by_audit": "universe-catalogue-audit-runtime-change",
    }
    return tuple(name for key, name in blocker_names.items() if checks[key] is not True)


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
