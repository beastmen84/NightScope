from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import RecommendationConfidence, nsom_to_json_compatible
from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.advanced_observing_nsom_service import (
    NSOM_ADVANCED_OBSERVING_ENABLED,
    AdvancedObservingNsomService,
)
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.tools.advanced_observing_nsom_downstream_policy import (
    DOWNSTREAM_POLICY_PATH,
    generate_downstream_policy_data,
)

PRESENTATION_READINESS_PATH = Path("docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_READINESS.md")

REPORT_IMPORT_MARKERS = (
    "advanced_observing_nsom_presentation_readiness",
    "ADVANCED_OBSERVING_NSOM_PRESENTATION_READINESS",
)

QML_MARKERS = (
    "advancedObservingNsom",
    "advancedObservingNsomScores",
    "AdvancedObservingNsom",
    "_advanced_observing_nsom_scores",
    *REPORT_IMPORT_MARKERS,
)


def generate_presentation_readiness_data() -> dict[str, object]:
    downstream = generate_downstream_policy_data()
    presentation = _presentation_evidence()
    decisions = _presentation_decisions(downstream, presentation)
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    checks = _checks(downstream, presentation, decisions, static_checks)
    blockers = _default_on_blockers(checks, decisions)
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
            "source_report": str(DOWNSTREAM_POLICY_PATH).replace("\\", "/"),
            "presentation_readiness_report": str(PRESENTATION_READINESS_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "not_ready_for_advanced_observing_nsom_default_on",
            "ready_for_default_on_switch": False,
            "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
            "default_flag_currently_enabled": NSOM_ADVANCED_OBSERVING_ENABLED is True,
            "requires_separate_flag_change": NSOM_ADVANCED_OBSERVING_ENABLED is False,
            "runtime_behaviour_changed_by_this_audit": False,
            "consumer_split_resolved": downstream["checks"]["shared_contract_split_resolved"]
            and downstream["checks"]["planner_consumer_split_resolved"]
            and downstream["checks"]["notification_consumer_split_resolved"],
            "recommended_switch_change": (
                "do not set NSOM_ADVANCED_OBSERVING_ENABLED = True yet; review the "
                "read-only QML property and visible presentation policy first"
            ),
            "reason": (
                "Planner and NotificationService are protected by the consumer split, "
                "but the forced-on NSOM Advanced Observing values still do not affect "
                "the visible Advanced Observing UI. Enabling the flag now would not "
                "complete the Advanced Observing migration."
            ),
        },
        "default_on_blockers": blockers,
        "checks": checks,
        "presentation_decisions": decisions,
        "presentation_evidence": presentation,
        "static_wiring_checks": static_checks,
        "downstream_summary": {
            "verdict": downstream["readiness"]["verdict"],
            "blockers": downstream["default_on_blockers"],
            "consumer_split_implemented": downstream["readiness"]["consumer_split_implemented"],
        },
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_presentation_readiness_data() if data is None else data
    readiness = audit["readiness"]
    presentation = audit["presentation_evidence"]

    lines = [
        "# Advanced Observing NSOM Presentation Readiness",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit checks whether Advanced Observing NSOM can be "
            "enabled by default after the 1.8.7 consumer split. It does not change "
            "the flag, tune scores, render visible QML UI, log automatically, call "
            "the network or write runtime files. Planner and NotificationService are "
            "protected by legacy-compatible consumer inputs; as of 1.8.14 the NSOM "
            "category values are available through a read-only property but are not "
            "consumed by visible UI."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-on switch: `{readiness['ready_for_default_on_switch']}`.",
        f"- Current default flag: `{readiness['default_flag']}`.",
        f"- Default flag currently enabled: `{readiness['default_flag_currently_enabled']}`.",
        f"- Requires separate flag change: `{readiness['requires_separate_flag_change']}`.",
        f"- Runtime behaviour changed by this audit: `{readiness['runtime_behaviour_changed_by_this_audit']}`.",
        f"- Consumer split resolved: `{readiness['consumer_split_resolved']}`.",
        f"- Recommended switch change: {readiness['recommended_switch_change']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Default-On Blockers",
        "",
    ]
    for blocker in audit["default_on_blockers"]:
        lines.append(f"- `{blocker}`")

    lines.extend(
        [
            "",
            "## Presentation Decisions",
            "",
            "| Decision | Status | Blocks default-on | Summary |",
            "| --- | --- | --- | --- |",
        ]
    )
    for decision in audit["presentation_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['blocks_default_on']}`",
                    str(decision["summary"]),
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Presentation Evidence",
            "",
            f"- QML reads existing `advancedScores`: `{presentation['qml_reads_existing_advanced_scores']}`.",
            f"- QML reads NSOM Advanced Observing snapshot: "
            f"`{presentation['qml_reads_nsom_advanced_observing_snapshot']}`.",
            f"- Public advancedScores payload keys: `{presentation['public_advanced_scores_payload_keys']}`.",
            f"- Forced-on NSOM snapshot differs from legacy scores: "
            f"`{presentation['forced_on_nsom_snapshot_differs_from_legacy']}`.",
            f"- Forced-on NSOM snapshot has presentation effect: "
            f"`{presentation['forced_on_nsom_snapshot_has_presentation_effect']}`.",
            f"- No visible UI blocks meaningful default-on switch: "
            f"`{presentation['hidden_snapshot_blocks_meaningful_default_on']}`.",
            f"- Confidence score-neutral: `{presentation['confidence_score_neutral']}`.",
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
            "## Runtime And QML Wiring",
            "",
            f"- QML NSOM exposure matches: `{audit['static_wiring_checks']['qml_nsom_matches']}`.",
            f"- Runtime report imports: `{audit['static_wiring_checks']['runtime_report_import_matches']}`.",
            f"- Controller internal snapshot present: "
            f"`{audit['static_wiring_checks']['controller_internal_snapshot_present']}`.",
            f"- Controller public NSOM Advanced Observing property present: "
            f"`{audit['static_wiring_checks']['controller_public_nsom_property_present']}`.",
            "",
            "## Recommended Next Step",
            "",
            (
                "Implement `1.8.9` as an Advanced Observing NSOM presentation contract "
                "design step: either keep NSOM hidden as developer diagnostics, or add "
                "a separate QML-safe NSOM explanation/payload with explicit labels "
                "before any default-on switch."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = PRESENTATION_READINESS_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _presentation_decisions(
    downstream: dict[str, object],
    presentation: dict[str, object],
) -> tuple[dict[str, object], ...]:
    return (
        _decision(
            "legacy_advanced_scores_cards",
            status="accepted_current_runtime_contract",
            summary="Keep existing Home advanced score cards legacy-compatible for now.",
            reason="They are current user-facing compatibility fields and remain consumed by QML.",
            blocks_default_on=False,
        ),
        _decision(
            "nsom_snapshot_visibility",
            status="read_only_property_exposed_no_visible_ui",
            summary="Expose the presentation snapshot through read-only QML, but do not render it in UI.",
            reason="The property exists for inspection; no visible NSOM presentation is approved yet.",
            blocks_default_on=bool(presentation["hidden_snapshot_blocks_meaningful_default_on"]),
        ),
        _decision(
            "nsom_presentation_contract",
            status="implemented_read_only",
            summary="The Advanced Observing NSOM presentation contract has a read-only QML property.",
            reason="The property is wired, but visible UI remains a separate decision.",
            blocks_default_on=False,
        ),
        _decision(
            "score_label_semantics",
            status="needs_copy_policy_before_default_on",
            summary="Resolve `/100` score and label wording before showing NSOM category values.",
            reason="NSOM ObservableTargetValue diagnostics are not legacy actionability scores.",
            blocks_default_on=True,
        ),
        _decision(
            "downstream_consumer_split",
            status="resolved",
            summary="Planner and NotificationService receive legacy-compatible consumer scores.",
            reason="The 1.8.7 split removed Planner/notification default-on blockers.",
            blocks_default_on=not bool(downstream["readiness"]["consumer_split_implemented"]),
        ),
        _decision(
            "confidence_policy",
            status="accepted",
            summary="RecommendationConfidence remains metadata-only.",
            reason="Confidence describes trust and has zero score effect.",
            blocks_default_on=not bool(presentation["confidence_score_neutral"]),
            extra={"score_effect": 0.0},
        ),
    )


def _decision(
    decision_id: str,
    *,
    status: str,
    summary: str,
    reason: str,
    blocks_default_on: bool,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "decision_id": decision_id,
        "status": status,
        "summary": summary,
        "reason": reason,
        "blocks_default_on": blocks_default_on,
        "runtime_changed": False,
    }
    if extra:
        payload.update(extra)
    return payload


def _presentation_evidence() -> dict[str, object]:
    weather = _weather(90)
    seeing = _seeing(seeing_score=86, transparency_score=84)
    sky_quality = _sky_quality(9, radiance=120.0)
    moon = _moon(95)
    legacy_scores = AdvancedObservingService().scores(weather, seeing, sky_quality, moon)
    nsom_scores = AdvancedObservingNsomService().scores(weather, seeing, sky_quality, moon)
    low_confidence = AdvancedObservingNsomService().scores(
        weather,
        seeing,
        sky_quality,
        moon,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high_confidence = AdvancedObservingNsomService().scores(
        weather,
        seeing,
        sky_quality,
        moon,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    forced_on_differs = nsom_scores != legacy_scores
    qml_reads_snapshot = bool(static_checks["qml_nsom_matches"])
    return {
        "legacy_scores": legacy_scores.to_qml(),
        "forced_on_nsom_scores": nsom_scores.to_qml(),
        "public_advanced_scores_payload_keys": tuple(legacy_scores.to_qml().keys()),
        "public_payload_shape_unchanged": tuple(legacy_scores.to_qml().keys())
        == tuple(nsom_scores.to_qml().keys()),
        "qml_reads_existing_advanced_scores": static_checks["qml_reads_existing_advanced_scores"],
        "qml_reads_nsom_advanced_observing_snapshot": qml_reads_snapshot,
        "forced_on_nsom_snapshot_differs_from_legacy": forced_on_differs,
        "forced_on_nsom_snapshot_has_presentation_effect": qml_reads_snapshot,
        "hidden_snapshot_blocks_meaningful_default_on": forced_on_differs and not qml_reads_snapshot,
        "confidence_score_neutral": low_confidence.planetary_score == high_confidence.planetary_score
        and low_confidence.deep_sky_score == high_confidence.deep_sky_score,
        "confidence_score_effect": 0.0,
    }


def _checks(
    downstream: dict[str, object],
    presentation: dict[str, object],
    decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    decision_ids = {decision["decision_id"] for decision in decisions}
    return {
        "default_flag_still_off": NSOM_ADVANCED_OBSERVING_ENABLED is False,
        "downstream_consumer_split_resolved": downstream["readiness"]["consumer_split_implemented"] is True
        and downstream["checks"]["planner_consumer_split_resolved"] is True
        and downstream["checks"]["notification_consumer_split_resolved"] is True,
        "required_presentation_decisions_recorded": {
            "legacy_advanced_scores_cards",
            "nsom_snapshot_visibility",
            "nsom_presentation_contract",
            "score_label_semantics",
            "downstream_consumer_split",
            "confidence_policy",
        }.issubset(decision_ids),
        "existing_qml_payload_remains_legacy_compatible": presentation["public_payload_shape_unchanged"] is True,
        "existing_qml_advanced_scores_still_used": presentation["qml_reads_existing_advanced_scores"] is True,
        "nsom_snapshot_not_visible_in_qml": presentation["qml_reads_nsom_advanced_observing_snapshot"] is False,
        "read_only_qml_property_present": static_checks["controller_public_nsom_property_present"] is True,
        "hidden_snapshot_blocks_default_on": presentation["hidden_snapshot_blocks_meaningful_default_on"] is True,
        "presentation_contract_available": _decision_by_id(
            decisions,
            "nsom_presentation_contract",
        )["blocks_default_on"]
        is False,
        "score_label_semantics_blocks_default_on": _decision_by_id(
            decisions,
            "score_label_semantics",
        )["blocks_default_on"]
        is True,
        "confidence_score_neutral": presentation["confidence_score_neutral"] is True,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_nsom_exposure_absent": static_checks["qml_nsom_matches"] == (),
        "runtime_behaviour_unchanged": True,
    }


def _default_on_blockers(
    checks: dict[str, object],
    decisions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    blockers = [
        f"advanced-observing-{decision['decision_id'].replace('_', '-')}"
        for decision in decisions
        if decision["blocks_default_on"] is True
    ]
    safety_names = {
        "downstream_consumer_split_resolved": "advanced-observing-consumer-split-regressed",
        "required_presentation_decisions_recorded": "advanced-observing-presentation-decisions-incomplete",
        "existing_qml_payload_remains_legacy_compatible": "advanced-observing-payload-shape-regressed",
        "existing_qml_advanced_scores_still_used": "advanced-observing-existing-qml-contract-missing",
        "nsom_snapshot_not_visible_in_qml": "advanced-observing-unplanned-visible-qml-nsom-usage",
        "read_only_qml_property_present": "advanced-observing-read-only-qml-property-missing",
        "hidden_snapshot_blocks_default_on": "advanced-observing-hidden-snapshot-not-recognized",
        "presentation_contract_available": "advanced-observing-presentation-contract-missing",
        "score_label_semantics_blocks_default_on": "advanced-observing-score-label-policy-not-blocking",
        "confidence_score_neutral": "advanced-observing-confidence-not-neutral",
        "runtime_report_imports_absent": "advanced-observing-runtime-report-wiring",
        "qml_nsom_exposure_absent": "advanced-observing-visible-qml-nsom-usage",
        "runtime_behaviour_unchanged": "advanced-observing-runtime-behaviour-change",
    }
    blockers.extend(name for key, name in safety_names.items() if checks[key] is not True)
    return tuple(dict.fromkeys(blockers))


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    controller_source = app_root / "viewmodels" / "app_controller.py"
    controller_text = controller_source.read_text(encoding="utf-8") if controller_source.exists() else ""
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (app_root / "ui").rglob("*.qml")
    )
    public_property_markers = (
        "def advancedObservingNsom",
        "def advancedObservingNsomScores",
        "advancedObservingNsom = Property",
        "advancedObservingNsomScores = Property",
    )
    return {
        "qml_reads_existing_advanced_scores": "controller.advancedScores" in qml_text,
        "qml_nsom_matches": _scan_files(app_root / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            app_root,
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "controller_internal_snapshot_present": "_advanced_observing_nsom_scores" in controller_text,
        "controller_public_nsom_property_present": any(
            marker in controller_text for marker in public_property_markers
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


def _weather(score: int) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Advanced Observing presentation readiness fixture",
        cloud_cover=10,
        precipitation_probability=0,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _seeing(*, seeing_score: int, transparency_score: int) -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Fixture",
        transparency="Fixture",
        seeing_score=seeing_score,
        transparency_score=transparency_score,
        explanation="Advanced Observing presentation readiness fixture",
    )


def _sky_quality(bortle: int, radiance: float | None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="AdvancedObservingPresentationReadinessFixture",
        description="Advanced Observing presentation readiness fixture",
        viirs_radiance=radiance,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="20:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
    )


def main() -> None:
    write_markdown_report()


if __name__ == "__main__":
    main()
