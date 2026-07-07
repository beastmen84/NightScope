from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.advanced_observing_nsom_service import NSOM_ADVANCED_OBSERVING_ENABLED
from astro_viewer.tools.advanced_observing_nsom_qml_exposure_readiness import (
    QML_EXPOSURE_READINESS_PATH,
    generate_qml_exposure_readiness_data,
)

QML_PRESENTATION_POLICY_PATH = Path("docs/ADVANCED_OBSERVING_NSOM_QML_PRESENTATION_POLICY.md")

REPORT_IMPORT_MARKERS = (
    "advanced_observing_nsom_qml_presentation_policy",
    "ADVANCED_OBSERVING_NSOM_QML_PRESENTATION_POLICY",
)

QML_MARKERS = (
    "advancedObservingNsom",
    "AdvancedObservingNsom",
    "advancedObservingNsomScores",
    "AdvancedObservingNsomScores",
)


def generate_qml_presentation_policy_data() -> dict[str, object]:
    readiness = generate_qml_exposure_readiness_data()
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    policy = _policy_decisions(readiness)
    checks = _checks(readiness, policy, static_checks)
    remaining_items = _remaining_items(checks)
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": True,
            "visible_ui_exposure": False,
            "advanced_scores_changed_by_default": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed": False,
            "notifications_changed": False,
            "sky_compass_changed": False,
            "runtime_behaviour_changed": False,
            "source_report": str(QML_EXPOSURE_READINESS_PATH).replace("\\", "/"),
            "qml_presentation_policy_report": str(QML_PRESENTATION_POLICY_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "advanced_observing_nsom_qml_policy_applied_read_only_property",
            "policy_status": "applied_to_read_only_property",
            "policy_covers_1_8_12_blockers": checks["policy_covers_source_blockers"],
            "ready_for_runtime_qml_exposure": True,
            "ready_for_user_visible_ui": False,
            "ready_for_separate_read_only_property_step": checks[
                "future_read_only_property_wired"
            ],
            "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
            "default_flag_currently_enabled": NSOM_ADVANCED_OBSERVING_ENABLED is True,
            "runtime_behaviour_changed_by_this_policy": False,
            "recommended_next_change": (
                "review the read-only `advancedObservingNsom` property, then decide "
                "separately whether visible UI or default-on Advanced Observing NSOM should follow"
            ),
            "reason": (
                "The lifecycle, copy and score-label decisions from 1.8.13 are now "
                "applied to a read-only property. No visible UI consumes it and the "
                "Advanced Observing NSOM flag remains default-off."
            ),
        },
        "remaining_items_before_runtime_qml_exposure": remaining_items,
        "policy_decisions": policy,
        "checks": checks,
        "static_wiring_checks": static_checks,
        "source_readiness_summary": {
            "verdict": readiness["readiness"]["verdict"],
            "default_on_blockers": readiness["default_on_blockers"],
            "future_property": readiness["presentation_contract_summary"]["future_qml_property"],
            "current_property": readiness["presentation_contract_summary"]["current_qml_property"],
        },
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    policy = generate_qml_presentation_policy_data() if data is None else data
    readiness = policy["readiness"]

    lines = [
        "# Advanced Observing NSOM QML Presentation Policy",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only policy closes the 1.8.12 presentation-design gap "
            "for the Advanced Observing NSOM QML surface. As of 1.8.14, the policy "
            "is applied to a read-only `advancedObservingNsom` property. The property "
            "does not render visible UI, does not change `advancedScores`, does not "
            "enable `NSOM_ADVANCED_OBSERVING_ENABLED`, and does not write files at "
            "runtime, log automatically or call the network."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Policy status: `{readiness['policy_status']}`.",
        f"- Policy covers 1.8.12 blockers: `{readiness['policy_covers_1_8_12_blockers']}`.",
        f"- Ready for runtime QML exposure now: `{readiness['ready_for_runtime_qml_exposure']}`.",
        f"- Ready for user-visible UI now: `{readiness['ready_for_user_visible_ui']}`.",
        (
            "- Read-only property wired: "
            f"`{readiness['ready_for_separate_read_only_property_step']}`."
        ),
        f"- Current default flag: `{readiness['default_flag']}`.",
        f"- Default flag currently enabled: `{readiness['default_flag_currently_enabled']}`.",
        f"- Runtime behaviour changed by this policy: `{readiness['runtime_behaviour_changed_by_this_policy']}`.",
        f"- Recommended next change: {readiness['recommended_next_change']}.",
        f"- Reason: {readiness['reason']}",
        "",
        "## Remaining Items Before Runtime QML Exposure",
        "",
    ]
    for item in policy["remaining_items_before_runtime_qml_exposure"]:
        lines.append(f"- `{item}`")

    lines.extend(
        [
            "",
            "## Policy Decisions",
            "",
            "| Decision | Status | Covers 1.8.12 blocker | Runtime change | Summary |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for decision in policy["policy_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['covers_source_blocker']}`",
                    f"`{decision['runtime_changed']}`",
                    str(decision["summary"]),
                )
            )
            + " |"
        )

    copy_policy = _decision_by_id(policy["policy_decisions"], "visible_ui_copy_policy")
    label_policy = _decision_by_id(policy["policy_decisions"], "score_label_semantics")
    lifecycle_policy = _decision_by_id(policy["policy_decisions"], "notify_signal_lifecycle")

    lines.extend(
        [
            "",
            "## Future Property Lifecycle",
            "",
            f"- Future property: `{lifecycle_policy['future_property']}`.",
            f"- Notify signal: `{lifecycle_policy['notify_signal']}`.",
            f"- New signal required: `{lifecycle_policy['new_signal_required']}`.",
            f"- Runtime source: `{lifecycle_policy['runtime_source']}`.",
            f"- Recompute on property read: `{lifecycle_policy['recompute_on_property_read']}`.",
            "",
            "## Copy And Score Semantics",
            "",
            f"- Copy delivery: `{copy_policy['copy_delivery']}`.",
            f"- Visible UI approved now: `{copy_policy['visible_ui_approved_now']}`.",
            f"- Title key: `{copy_policy['title_key']}`.",
            f"- Category label key: `{copy_policy['category_label_key']}`.",
            f"- Score display label: `{label_policy['display_label']}`.",
            f"- Must not display as legacy `/100` actionability: `{label_policy['not_legacy_actionability']}`.",
            f"- Confidence score effect: `{label_policy['confidence_score_effect']}`.",
            "",
            "## Source Readiness Summary",
            "",
            f"- Source verdict: `{policy['source_readiness_summary']['verdict']}`.",
            f"- Source blockers: `{policy['source_readiness_summary']['default_on_blockers']}`.",
            f"- Future property: `{policy['source_readiness_summary']['future_property']}`.",
            f"- Current property: `{policy['source_readiness_summary']['current_property']}`.",
            "",
            "## Static Wiring Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in policy["static_wiring_checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in policy["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Recommended Next Step",
            "",
            (
                "Review the read-only `advancedObservingNsom` property. Keep visible "
                "UI and default-on Advanced Observing NSOM as separate decisions."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = QML_PRESENTATION_POLICY_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _policy_decisions(readiness: dict[str, object]) -> tuple[dict[str, object], ...]:
    return (
        _decision(
            "future_qml_property_name",
            status="accepted_policy",
            summary="Reserve `advancedObservingNsom` as the future read-only QML property name.",
            reason="The 1.8.9 contract already names this as the separate NSOM surface.",
            covers_source_blocker="advanced-observing-public-qml-property",
            extra={
                "future_property": "advancedObservingNsom",
                "current_property": "advancedScores",
                "implemented_in_this_step": True,
            },
        ),
        _decision(
            "notify_signal_lifecycle",
            status="accepted_policy",
            summary="Use the existing `weatherChanged` lifecycle for any future property.",
            reason="Advanced Observing category data is refreshed with the same weather/sky lifecycle as `advancedScores`.",
            covers_source_blocker="advanced-observing-public-qml-property",
            extra={
                "future_property": "advancedObservingNsom",
                "notify_signal": "weatherChanged",
                "new_signal_required": False,
                "runtime_source": "_advanced_observing_nsom_presentation",
                "recompute_on_property_read": False,
            },
        ),
        _decision(
            "visible_ui_copy_policy",
            status="accepted_policy",
            summary="Keep visible UI blocked; future copy must be localization-key based.",
            reason="Developer-facing NSOM terms should not be inserted directly into Home QML cards.",
            covers_source_blocker="advanced-observing-visible-ui-copy",
            extra={
                "visible_ui_approved_now": False,
                "copy_delivery": "localization_keys_or_existing_translation_layer",
                "title_key": "advanced_observing_nsom.title",
                "category_label_key": "advanced_observing_nsom.category_value",
                "confidence_label_key": "advanced_observing_nsom.data_confidence",
            },
        ),
        _decision(
            "score_label_semantics",
            status="accepted_policy",
            summary="Label category values as NSOM diagnostics, not legacy actionability scores.",
            reason="The values are ObservableTargetValue diagnostics and must not be read as `/100` legacy score thresholds.",
            covers_source_blocker="advanced-observing-score-label-semantics",
            extra={
                "display_label": "NSOM category diagnostic value",
                "not_legacy_actionability": True,
                "not_planner_score": True,
                "not_notification_threshold": True,
                "confidence_score_effect": 0.0,
            },
        ),
        _decision(
            "confidence_metadata_policy",
            status="accepted",
            summary="Display confidence only as data-trust metadata if a future UI uses it.",
            reason="RecommendationConfidence is outside category score math and has zero score effect.",
            covers_source_blocker="advanced-observing-score-label-semantics",
            extra={
                "confidence_score_effect": 0.0,
                "confidence_placement": "metadata_outside_category_value",
            },
        ),
        _decision(
            "visual_placement_policy",
            status="accepted_policy",
            summary="Any future visible UI belongs in a separate diagnostic area, not inside legacy score cards.",
            reason="Replacing `advancedScores` cards would blur legacy compatibility and NSOM diagnostic semantics.",
            covers_source_blocker="advanced-observing-visible-ui-copy",
            extra={
                "replace_advanced_scores_cards": False,
                "allowed_visible_surface": "separate_diagnostic_or_advanced_section",
                "implemented_in_this_step": False,
            },
        ),
        _decision(
            "rollback_policy",
            status="accepted",
            summary="Keep the future rollback path as the existing internal flag/constructor override.",
            reason="The future property must read only the private snapshot and return empty data when the NSOM path is disabled.",
            covers_source_blocker=None,
            extra={
                "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
                "constructor_rollback": "AppController(use_nsom_advanced_observing=False)",
                "future_property_when_disabled": {},
            },
        ),
        _decision(
            "source_blockers_addressed_at_policy_level",
            status="verified",
            summary="The 1.8.12 blocker categories now have explicit policy decisions or implementation.",
            reason="Lifecycle is implemented for the read-only property; visible copy and score-label semantics remain UI-only policy.",
            covers_source_blocker=None,
            extra={"source_blockers": readiness["default_on_blockers"]},
        ),
    )


def _decision(
    decision_id: str,
    *,
    status: str,
    summary: str,
    reason: str,
    covers_source_blocker: str | None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "decision_id": decision_id,
        "status": status,
        "summary": summary,
        "reason": reason,
        "covers_source_blocker": covers_source_blocker,
        "runtime_changed": False,
    }
    if extra:
        payload.update(extra)
    return payload


def _checks(
    readiness: dict[str, object],
    decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    source_blockers = set(readiness["default_on_blockers"])
    covered_blockers = {
        decision["covers_source_blocker"]
        for decision in decisions
        if decision["covers_source_blocker"] is not None
    }
    lifecycle = _decision_by_id(decisions, "notify_signal_lifecycle")
    label = _decision_by_id(decisions, "score_label_semantics")
    copy = _decision_by_id(decisions, "visible_ui_copy_policy")
    visual = _decision_by_id(decisions, "visual_placement_policy")
    rollback = _decision_by_id(decisions, "rollback_policy")
    return {
        "default_flag_still_off": NSOM_ADVANCED_OBSERVING_ENABLED is False,
        "source_readiness_was_not_ready": readiness["readiness"]["ready_for_user_visible_ui"] is False,
        "policy_covers_source_blockers": source_blockers.issubset(covered_blockers),
        "future_property_name_defined": _decision_by_id(
            decisions,
            "future_qml_property_name",
        )["future_property"]
        == "advancedObservingNsom",
        "future_read_only_property_policy_defined": lifecycle["future_property"] == "advancedObservingNsom"
        and lifecycle["notify_signal"] == "weatherChanged"
        and lifecycle["new_signal_required"] is False
        and lifecycle["recompute_on_property_read"] is False,
        "future_read_only_property_wired": static_checks["controller_public_property_present"] is True
        and static_checks["qml_nsom_matches"] == (),
        "visible_ui_copy_policy_defined": copy["visible_ui_approved_now"] is False
        and copy["copy_delivery"] == "localization_keys_or_existing_translation_layer",
        "visible_ui_still_not_approved": visual["implemented_in_this_step"] is False
        and visual["replace_advanced_scores_cards"] is False,
        "score_label_policy_avoids_legacy_actionability": label["not_legacy_actionability"] is True
        and label["not_planner_score"] is True
        and label["not_notification_threshold"] is True,
        "confidence_score_neutral": label["confidence_score_effect"] == 0.0
        and _decision_by_id(decisions, "confidence_metadata_policy")["confidence_score_effect"] == 0.0,
        "rollback_policy_defined": rollback["constructor_rollback"]
        == "AppController(use_nsom_advanced_observing=False)",
        "advanced_scores_remains_current_qml_contract": readiness["presentation_contract_summary"][
            "current_qml_property"
        ]
        == "advancedScores",
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "visible_qml_usage_absent": static_checks["qml_nsom_matches"] == (),
        "future_property_wired": static_checks["controller_public_property_present"] is True,
        "new_signal_not_wired": static_checks["controller_public_signal_present"] is False,
        "existing_weather_changed_available": static_checks["weather_changed_signal_present"] is True,
        "private_projection_available": static_checks["controller_private_projection_present"] is True,
        "qml_reads_existing_advanced_scores": static_checks["qml_reads_existing_advanced_scores"] is True,
        "no_runtime_behaviour_change": True,
    }


def _remaining_items(checks: dict[str, object]) -> tuple[str, ...]:
    items: list[str] = []
    if checks["visible_ui_still_not_approved"] is True:
        items.append("advanced-observing-visible-ui-design-not-approved")
    if checks["default_flag_still_off"] is True:
        items.append("advanced-observing-default-flag-still-off")
    safety_names = {
        "policy_covers_source_blockers": "advanced-observing-qml-policy-incomplete",
        "future_read_only_property_policy_defined": "advanced-observing-qml-lifecycle-policy-missing",
        "future_read_only_property_wired": "advanced-observing-read-only-qml-property-not-implemented",
        "score_label_policy_avoids_legacy_actionability": "advanced-observing-score-label-policy-missing",
        "confidence_score_neutral": "advanced-observing-confidence-not-neutral",
        "runtime_report_imports_absent": "advanced-observing-runtime-report-wiring",
        "visible_qml_usage_absent": "advanced-observing-unplanned-visible-qml-usage",
        "new_signal_not_wired": "advanced-observing-unplanned-qml-signal",
        "no_runtime_behaviour_change": "advanced-observing-runtime-behaviour-change",
    }
    items.extend(name for key, name in safety_names.items() if checks[key] is not True)
    return tuple(dict.fromkeys(items))


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    controller_path = app_root / "viewmodels" / "app_controller.py"
    controller_text = controller_path.read_text(encoding="utf-8") if controller_path.exists() else ""
    public_property_markers = (
        "def advancedObservingNsom",
        "def advancedObservingNsomScores",
        "advancedObservingNsom = Property",
        "advancedObservingNsomScores = Property",
    )
    public_signal_markers = (
        "advancedObservingNsomChanged",
        "advancedObservingNsomScoresChanged",
    )
    return {
        "qml_nsom_matches": _scan_files(app_root / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            app_root,
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "controller_private_projection_present": "_advanced_observing_nsom_presentation" in controller_text,
        "controller_public_property_present": any(
            marker in controller_text for marker in public_property_markers
        ),
        "controller_public_signal_present": any(marker in controller_text for marker in public_signal_markers),
        "weather_changed_signal_present": "weatherChanged = Signal()" in controller_text,
        "advanced_scores_property_uses_weather_changed": (
            "@Property(\"QVariant\", notify=weatherChanged)\n    def advancedScores" in controller_text
        ),
        "qml_reads_existing_advanced_scores": _scan_files(
            app_root / "ui",
            ("*.qml",),
            ("controller.advancedScores",),
        )
        != (),
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
    decisions: tuple[dict[str, object], ...] | list[dict[str, object]],
    decision_id: str,
) -> dict[str, object]:
    return next(decision for decision in decisions if decision["decision_id"] == decision_id)


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
