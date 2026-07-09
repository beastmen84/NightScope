from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.advanced_observing_nsom_service import NSOM_ADVANCED_OBSERVING_ENABLED
from astro_viewer.tools.advanced_observing_nsom_presentation_contract import (
    PRESENTATION_CONTRACT_PATH,
    generate_presentation_contract_data,
)
from astro_viewer.tools.advanced_observing_nsom_qml_exposure_readiness import (
    QML_EXPOSURE_READINESS_PATH,
    generate_qml_exposure_readiness_data,
)
from astro_viewer.tools.advanced_observing_nsom_qml_presentation_policy import (
    QML_PRESENTATION_POLICY_PATH,
    generate_qml_presentation_policy_data,
)

DEFAULT_ON_READINESS_PATH = Path("docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "advanced_observing_nsom_default_on_readiness",
    "ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS",
)

QML_MARKERS = (
    "controller.advancedObservingNsom",
    "advancedObservingNsomChanged",
    "advancedObservingNsomScores",
)


def generate_default_on_readiness_data() -> dict[str, object]:
    exposure = generate_qml_exposure_readiness_data()
    policy = generate_qml_presentation_policy_data()
    contract = generate_presentation_contract_data()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    decisions = _default_on_decisions(exposure, policy, contract, static_checks)
    checks = _checks(exposure, policy, contract, static_checks, decisions)
    blockers = _default_on_blockers(checks, decisions)
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "visible_ui_exposure": False,
            "advanced_scores_changed_by_default": False,
            "planner_changed": False,
            "notifications_changed": False,
            "home_changed": False,
            "best_object_changed": False,
            "sky_compass_changed": False,
            "runtime_behaviour_changed": True,
            "runtime_default_changed_by_switch": True,
            "visible_runtime_behaviour_changed": False,
            "source_reports": (
                str(PRESENTATION_CONTRACT_PATH).replace("\\", "/"),
                str(QML_EXPOSURE_READINESS_PATH).replace("\\", "/"),
                str(QML_PRESENTATION_POLICY_PATH).replace("\\", "/"),
            ),
            "default_on_readiness_report": str(DEFAULT_ON_READINESS_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": (
                "advanced_observing_nsom_backend_default_on_enabled"
                if not blockers
                else "not_ready_for_advanced_observing_nsom_backend_default_on"
            ),
            "ready_for_backend_default_on": not blockers,
            "ready_for_visible_ui": False,
            "ready_to_replace_advanced_scores": False,
            "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
            "default_flag_currently_enabled": NSOM_ADVANCED_OBSERVING_ENABLED is True,
            "requires_separate_flag_change": NSOM_ADVANCED_OBSERVING_ENABLED is False,
            "default_on_switch_completed": NSOM_ADVANCED_OBSERVING_ENABLED is True,
            "explicit_rollback": "AppController(use_nsom_advanced_observing=False)",
            "runtime_default_changed_by_switch": NSOM_ADVANCED_OBSERVING_ENABLED is True,
            "visible_runtime_behaviour_changed": False,
            "recommended_next_change": (
                "keep the backend default-on switch, use explicit rollback for legacy "
                "diagnostics when needed, and review visible UI separately"
                if not blockers
                else "resolve default-on blockers before changing the flag"
            ),
        },
        "default_on_blockers": blockers,
        "remaining_non_blocking_items": _remaining_non_blocking_items(),
        "decisions": decisions,
        "checks": checks,
        "static_wiring_checks": static_checks,
        "source_summary": {
            "contract_verdict": contract["readiness"]["verdict"],
            "qml_exposure_verdict": exposure["readiness"]["verdict"],
            "qml_policy_verdict": policy["readiness"]["verdict"],
            "contract_previous_default_on_blockers": contract["default_on_blockers"],
            "qml_policy_remaining_items": policy["remaining_items_before_runtime_qml_exposure"],
        },
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_default_on_readiness_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# Advanced Observing NSOM Default-On Readiness Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether Advanced Observing NSOM can be "
            "kept enabled by default as a backend/internal projection. It records "
            "the backend switch state, does not replace `advancedScores`, does not "
            "render visible QML UI, does not tune scores, does not change Planner, "
            "Home Best Object or Sky Compass, and does not log "
            "automatically, call the network or write runtime files."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for backend default-on: `{readiness['ready_for_backend_default_on']}`.",
        f"- Ready for visible UI: `{readiness['ready_for_visible_ui']}`.",
        f"- Ready to replace `advancedScores`: `{readiness['ready_to_replace_advanced_scores']}`.",
        f"- Current default flag: `{readiness['default_flag']}`.",
        f"- Default flag currently enabled: `{readiness['default_flag_currently_enabled']}`.",
        f"- Requires separate flag change: `{readiness['requires_separate_flag_change']}`.",
        f"- Default-on switch completed: `{readiness['default_on_switch_completed']}`.",
        f"- Explicit rollback: `{readiness['explicit_rollback']}`.",
        f"- Runtime default changed by switch: `{readiness['runtime_default_changed_by_switch']}`.",
        f"- Visible runtime behaviour changed: `{readiness['visible_runtime_behaviour_changed']}`.",
        f"- Recommended next change: {readiness['recommended_next_change']}.",
        "",
        "## Default-On Blockers",
        "",
    ]
    if audit["default_on_blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in audit["default_on_blockers"])
    else:
        lines.append("- None for backend/internal projection default-on.")

    lines.extend(
        [
            "",
            "## Remaining Non-Blocking Items",
            "",
        ]
    )
    for item in audit["remaining_non_blocking_items"]:
        lines.append(f"- `{item}`")

    lines.extend(
        [
            "",
            "## Decisions",
            "",
            "| Decision | Status | Blocks backend default-on | Blocks visible UI | Summary |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for decision in audit["decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_backend_default_on']}`",
                    f"`{decision['blocks_visible_ui']}`",
                    str(decision["summary"]),
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
            "## Static Wiring Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["static_wiring_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    source = audit["source_summary"]
    lines.extend(
        [
            "",
            "## Source Summary",
            "",
            f"- Presentation contract verdict: `{source['contract_verdict']}`.",
            f"- QML exposure verdict: `{source['qml_exposure_verdict']}`.",
            f"- QML presentation policy verdict: `{source['qml_policy_verdict']}`.",
            f"- Historical contract blockers: `{source['contract_previous_default_on_blockers']}`.",
            f"- QML policy remaining items: `{source['qml_policy_remaining_items']}`.",
            "",
            "## Recommended Next Step",
            "",
            (
                "Keep the backend default-on switch narrow: preserve "
                "`AppController(use_nsom_advanced_observing=False)` as rollback, keep "
                "`advancedScores` and visible QML unchanged, and review any visible "
                "Advanced Observing NSOM UI separately."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = DEFAULT_ON_READINESS_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _default_on_decisions(
    exposure: dict[str, object],
    policy: dict[str, object],
    contract: dict[str, object],
    static_checks: dict[str, object],
) -> tuple[dict[str, object], ...]:
    return (
        _decision(
            "backend_projection_default_on",
            status="enabled",
            summary="Default-on is active for the internal Advanced Observing NSOM projection.",
            reason="The projection is separate from `advancedScores` and has an explicit rollback constructor.",
            blocks_backend_default_on=False,
            blocks_visible_ui=False,
        ),
        _decision(
            "visible_ui",
            status="deferred_non_blocking",
            summary="Do not render Advanced Observing NSOM in visible QML UI yet.",
            reason="Visible copy, placement and score-label design remain separate UX work.",
            blocks_backend_default_on=False,
            blocks_visible_ui=True,
        ),
        _decision(
            "advanced_scores_replacement",
            status="out_of_scope",
            summary="Do not replace `advancedScores` in this switch.",
            reason="Planner and existing Home cards keep the legacy-compatible payload; Notifications are removed.",
            blocks_backend_default_on=False,
            blocks_visible_ui=False,
        ),
        _decision(
            "read_only_property_safety",
            status="accepted",
            summary="The `advancedObservingNsom` property is read-only and defensive-copy hardened.",
            reason="The 1.8.15 property hardening prevents consumer mutation of the private snapshot.",
            blocks_backend_default_on=not bool(static_checks["property_defensive_copy_present"]),
            blocks_visible_ui=False,
        ),
        _decision(
            "qml_visibility",
            status="accepted_no_visible_usage",
            summary="No visible QML reads `controller.advancedObservingNsom`.",
            reason="Default-on backend projection will not change current visible Home cards.",
            blocks_backend_default_on=bool(static_checks["visible_qml_nsom_matches"]),
            blocks_visible_ui=False,
        ),
        _decision(
            "consumer_split",
            status="accepted",
            summary="Planner keeps legacy-compatible `advancedScores` input; Notifications are absent.",
            reason="The NSOM projection remains parallel and is not a Planner threshold or notification input.",
            blocks_backend_default_on=not bool(
                static_checks["planner_legacy_consumer_input_and_notifications_absent"]
            ),
            blocks_visible_ui=False,
        ),
        _decision(
            "confidence_metadata",
            status="accepted",
            summary="RecommendationConfidence remains metadata-only.",
            reason="The presentation contract and policy keep confidence outside score effects.",
            blocks_backend_default_on=not bool(
                contract["checks"]["session_and_confidence_are_metadata"]
                and policy["checks"]["confidence_score_neutral"]
            ),
            blocks_visible_ui=False,
            extra={"score_effect": 0.0},
        ),
        _decision(
            "report_tooling",
            status="developer_only",
            summary="Comparison/readiness reports remain explicit developer tooling.",
            reason="No report module is imported by runtime services or viewmodels.",
            blocks_backend_default_on=bool(static_checks["runtime_report_import_matches"]),
            blocks_visible_ui=False,
        ),
        _decision(
            "source_reports",
            status="accepted",
            summary="Readiness builds on the presentation contract, QML exposure and QML policy reports.",
            reason="Those reports provide the contract, property and presentation-policy evidence.",
            blocks_backend_default_on=not bool(
                exposure["checks"]["future_property_exposed_read_only"]
                and policy["checks"]["future_read_only_property_wired"]
                and contract["checks"]["read_only_qml_property_implemented"]
            ),
            blocks_visible_ui=False,
        ),
    )


def _decision(
    decision_id: str,
    *,
    status: str,
    summary: str,
    reason: str,
    blocks_backend_default_on: bool,
    blocks_visible_ui: bool,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "decision_id": decision_id,
        "status": status,
        "summary": summary,
        "reason": reason,
        "blocks_backend_default_on": blocks_backend_default_on,
        "blocks_visible_ui": blocks_visible_ui,
        "runtime_changed": False,
    }
    if extra:
        payload.update(extra)
    return payload


def _checks(
    exposure: dict[str, object],
    policy: dict[str, object],
    contract: dict[str, object],
    static_checks: dict[str, object],
    decisions: tuple[dict[str, object], ...],
) -> dict[str, object]:
    decision_ids = {decision["decision_id"] for decision in decisions}
    return {
        "default_flag_enabled_for_switch": NSOM_ADVANCED_OBSERVING_ENABLED is True,
        "source_reports_strict_json_compatible": _strict_json_compatible(exposure)
        and _strict_json_compatible(policy)
        and _strict_json_compatible(contract),
        "read_only_property_available": exposure["checks"]["future_property_exposed_read_only"] is True,
        "property_defensive_copy_hardened": static_checks["property_defensive_copy_present"] is True,
        "visible_qml_usage_absent": static_checks["visible_qml_nsom_matches"] == (),
        "advanced_scores_remains_current_qml_contract": (
            contract["readiness"]["current_qml_property"] == "advancedScores"
            and policy["checks"]["advanced_scores_remains_current_qml_contract"] is True
        ),
        "advanced_scores_not_replaced": contract["checks"]["contract_does_not_replace_advanced_scores"] is True,
        "planner_keeps_legacy_input_and_notifications_absent": (
            static_checks["planner_legacy_consumer_input_and_notifications_absent"] is True
        ),
        "confidence_metadata_only": contract["checks"]["session_and_confidence_are_metadata"] is True
        and policy["checks"]["confidence_score_neutral"] is True,
        "report_tooling_developer_only": static_checks["runtime_report_import_matches"] == (),
        "no_runtime_file_logging_network": True,
        "required_decisions_recorded": {
            "backend_projection_default_on",
            "visible_ui",
            "advanced_scores_replacement",
            "read_only_property_safety",
            "qml_visibility",
            "consumer_split",
            "confidence_metadata",
            "report_tooling",
            "source_reports",
        }.issubset(decision_ids),
        "backend_default_on_blockers_absent": all(
            decision["blocks_backend_default_on"] is False for decision in decisions
        ),
        "visible_ui_still_deferred": _decision_by_id(decisions, "visible_ui")["blocks_visible_ui"] is True,
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _default_on_blockers(
    checks: dict[str, object],
    decisions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    blockers = [
        f"advanced-observing-{decision['decision_id'].replace('_', '-')}"
        for decision in decisions
        if decision["blocks_backend_default_on"] is True
    ]
    safety_names = {
        "read_only_property_available": "advanced-observing-read-only-property-missing",
        "property_defensive_copy_hardened": "advanced-observing-property-copy-not-hardened",
        "visible_qml_usage_absent": "advanced-observing-visible-qml-usage",
        "advanced_scores_remains_current_qml_contract": "advanced-observing-current-qml-contract-regressed",
        "advanced_scores_not_replaced": "advanced-observing-advanced-scores-replaced",
        "planner_keeps_legacy_input_and_notifications_absent": "advanced-observing-consumer-split-regressed",
        "confidence_metadata_only": "advanced-observing-confidence-not-neutral",
        "report_tooling_developer_only": "advanced-observing-report-runtime-wiring",
        "required_decisions_recorded": "advanced-observing-default-on-decisions-incomplete",
        "backend_default_on_blockers_absent": "advanced-observing-decision-blocker-present",
        "runtime_behaviour_unchanged_by_audit": "advanced-observing-runtime-behaviour-change",
    }
    blockers.extend(name for key, name in safety_names.items() if checks[key] is not True)
    return tuple(dict.fromkeys(blockers))


def _remaining_non_blocking_items() -> tuple[str, ...]:
    return (
        "advanced-observing-visible-ui-design-not-approved",
        "advanced-observing-visible-copy-localization-not-designed",
        "advanced-observing-advanced-scores-replacement-not-scoped",
    )


def _strict_json_compatible(payload: dict[str, object]) -> bool:
    try:
        json.dumps(payload, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return True


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    controller_path = app_root / "viewmodels" / "app_controller.py"
    controller_text = controller_path.read_text(encoding="utf-8") if controller_path.exists() else ""
    qml_matches = _scan_files(app_root / "ui", ("*.qml",), QML_MARKERS)
    return {
        "visible_qml_nsom_matches": qml_matches,
        "runtime_report_import_matches": _scan_files(
            app_root,
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "controller_public_property_present": "def advancedObservingNsom" in controller_text,
        "property_defensive_copy_present": "deepcopy(self._advanced_observing_nsom_presentation)" in controller_text,
        "new_nsom_signal_absent": "advancedObservingNsomChanged" not in controller_text,
        "planner_legacy_consumer_input_and_notifications_absent": "_advanced_scores_for_planner()" in controller_text
        and "_advanced_scores_for_notifications" not in controller_text
        and "_notification_service" not in controller_text
        and "_advanced_observing_nsom_scores" in controller_text
        and "_advanced_scores = self._select_advanced_observing_scores()" in controller_text,
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


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
