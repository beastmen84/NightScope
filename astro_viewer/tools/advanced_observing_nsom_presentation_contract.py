from __future__ import annotations

from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.advanced_observing_nsom_service import (
    NSOM_ADVANCED_OBSERVING_ENABLED,
    AdvancedObservingNsomService,
)
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.tools.advanced_observing_nsom_presentation_readiness import (
    PRESENTATION_READINESS_PATH,
    generate_presentation_readiness_data,
)

PRESENTATION_CONTRACT_PATH = Path("docs/ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT.md")
SCHEMA_VERSION = "advanced_observing_nsom_presentation_v1"

REPORT_IMPORT_MARKERS = (
    "advanced_observing_nsom_presentation_contract",
    "ADVANCED_OBSERVING_NSOM_PRESENTATION_CONTRACT",
)

QML_MARKERS = (
    "advancedObservingNsom",
    "AdvancedObservingNsom",
    *REPORT_IMPORT_MARKERS,
)


def generate_presentation_contract_data() -> dict[str, object]:
    readiness = generate_presentation_readiness_data()
    payload = _contract_payload_example()
    decisions = _contract_decisions(readiness)
    static_checks = _static_wiring_checks(Path(__file__).parents[2])
    checks = _checks(readiness, payload, decisions, static_checks)
    blockers = _default_on_blockers(checks)
    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "advanced_scores_changed_by_default": False,
            "home_changed": False,
            "best_object_changed": False,
            "planner_changed": False,
            "notifications_changed": False,
            "sky_compass_changed": False,
            "runtime_behaviour_changed": False,
            "source_report": str(PRESENTATION_READINESS_PATH).replace("\\", "/"),
            "presentation_contract_report": str(PRESENTATION_CONTRACT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "advanced_observing_nsom_presentation_contract_defined_not_wired",
            "ready_for_default_on_switch": False,
            "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
            "default_flag_currently_enabled": NSOM_ADVANCED_OBSERVING_ENABLED is True,
            "runtime_behaviour_changed_by_this_contract": False,
            "contract_status": "defined_developer_only",
            "future_qml_property": "advancedObservingNsom",
            "current_qml_property": "advancedScores",
            "recommended_next_change": (
                "Implement a default-off `advancedObservingNsom` runtime property "
                "using this contract, while leaving `advancedScores` legacy-compatible."
            ),
        },
        "default_on_blockers": blockers,
        "checks": checks,
        "contract_decisions": decisions,
        "contract_payload_example": payload,
        "static_wiring_checks": static_checks,
        "readiness_summary": {
            "previous_verdict": readiness["readiness"]["verdict"],
            "previous_blockers": readiness["default_on_blockers"],
            "consumer_split_resolved": readiness["readiness"]["consumer_split_resolved"],
        },
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    contract = generate_presentation_contract_data() if data is None else data
    readiness = contract["readiness"]
    payload = contract["contract_payload_example"]

    lines = [
        "# Advanced Observing NSOM Presentation Contract",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only contract defines the future QML-safe Advanced "
            "Observing NSOM presentation payload. It does not expose QML, change "
            "`advancedScores`, enable `NSOM_ADVANCED_OBSERVING_ENABLED`, tune scores, "
            "log automatically, call the network or write runtime files. The contract "
            "keeps NSOM category diagnostics separate from legacy scores, Planner "
            "inputs and notification thresholds."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Ready for default-on switch: `{readiness['ready_for_default_on_switch']}`.",
        f"- Current default flag: `{readiness['default_flag']}`.",
        f"- Runtime behaviour changed by this contract: `{readiness['runtime_behaviour_changed_by_this_contract']}`.",
        f"- Contract status: `{readiness['contract_status']}`.",
        f"- Future QML property: `{readiness['future_qml_property']}`.",
        f"- Current QML property: `{readiness['current_qml_property']}`.",
        f"- Recommended next change: {readiness['recommended_next_change']}",
        "",
        "## Remaining Default-On Blockers",
        "",
    ]
    for blocker in contract["default_on_blockers"]:
        lines.append(f"- `{blocker}`")

    lines.extend(
        [
            "",
            "## Contract Decisions",
            "",
            "| Decision | Status | Blocks default-on | Summary |",
            "| --- | --- | --- | --- |",
        ]
    )
    for decision in contract["contract_decisions"]:
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
            "## Payload Shape",
            "",
            f"- Schema version: `{payload['schemaVersion']}`.",
            f"- Runtime state: `{payload['runtimeState']}`.",
            f"- Replaces `advancedScores`: `{payload['consumerPolicy']['replacesAdvancedScores']}`.",
            f"- Planner input: `{payload['consumerPolicy']['plannerInput']}`.",
            f"- Notification input: `{payload['consumerPolicy']['notificationInput']}`.",
            f"- Session score effect: `{payload['session']['scoreEffect']}`.",
            f"- Confidence score effect: `{payload['confidence']['scoreEffect']}`.",
            "",
            "## Categories",
            "",
            "| Category | NSOM value | Legacy value | Score meaning |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    for category in payload["categories"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{category['id']}`",
                    str(category["diagnosticValue"]),
                    str(category["legacyCompatibilityValue"]),
                    category["scoreMeaning"],
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
    for key, value in contract["checks"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Runtime And QML Wiring",
            "",
            f"- QML matches: `{contract['static_wiring_checks']['qml_matches']}`.",
            f"- Runtime report imports: `{contract['static_wiring_checks']['runtime_report_import_matches']}`.",
            f"- Future property already wired: `{contract['static_wiring_checks']['future_property_already_wired']}`.",
            "",
            "## Recommended Next Step",
            "",
            (
                "Implement `1.8.10` as a default-off runtime projection for the "
                "`advancedObservingNsom` contract. Keep `advancedScores` unchanged "
                "and do not expose the new property to QML until a separate UI review."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = PRESENTATION_CONTRACT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _contract_payload_example() -> dict[str, object]:
    weather = _weather(90)
    seeing = _seeing(seeing_score=86, transparency_score=84)
    sky_quality = _sky_quality(9, radiance=120.0)
    moon = _moon(95)
    legacy_scores = AdvancedObservingService().scores(weather, seeing, sky_quality, moon)
    nsom_scores = AdvancedObservingNsomService().scores(weather, seeing, sky_quality, moon)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "runtimeState": "contract_only_not_wired",
        "currentQmlProperty": "advancedScores",
        "futureQmlProperty": "advancedObservingNsom",
        "summary": {
            "title": "Advanced Observing NSOM",
            "status": "diagnostic_presentation_contract",
            "displayPolicy": "separate_from_legacy_advanced_scores",
            "scoreSemantics": (
                "Category diagnostics from NSOM ObservableTargetValue; not an "
                "actionability score, Planner input or notification threshold."
            ),
        },
        "categories": (
            _category_payload(
                "planetary",
                "Planetary conditions",
                nsom_scores.planetary_score,
                legacy_scores.planetary_score,
                nsom_scores.planetary_label,
                legacy_scores.planetary_label,
                included_sky_components=(
                    "geometric_visibility",
                    "horizon_context",
                    "atmospheric_transparency_from_seeing",
                    "planetary_moon_background_protected",
                    "planetary_static_sky_background_protected",
                ),
            ),
            _category_payload(
                "deepSky",
                "Deep-sky conditions",
                nsom_scores.deep_sky_score,
                legacy_scores.deep_sky_score,
                nsom_scores.deep_sky_label,
                legacy_scores.deep_sky_label,
                included_sky_components=(
                    "geometric_visibility",
                    "horizon_context",
                    "atmospheric_transparency_from_transparency",
                    "lunar_sky_background",
                    "static_sky_background",
                ),
            ),
        ),
        "session": {
            "included": True,
            "placement": "metadata_outside_category_value",
            "scoreEffect": 0.0,
            "semantics": "actionability and caution text only",
        },
        "confidence": {
            "included": True,
            "placement": "metadata_outside_category_value",
            "scoreEffect": 0.0,
            "semantics": "source trust only",
        },
        "consumerPolicy": {
            "replacesAdvancedScores": False,
            "plannerInput": False,
            "notificationInput": False,
            "homeBestObjectInput": False,
            "skyCompassInput": False,
        },
        "runtimeSafety": {
            "defaultOff": True,
            "noRuntimeFileWrites": True,
            "noAutomaticLogging": True,
            "noNetwork": True,
            "noMutationOfRuntimeObjects": True,
        },
    }


def _category_payload(
    category_id: str,
    title: str,
    diagnostic_value: int,
    legacy_value: int,
    label: str,
    legacy_label: str,
    *,
    included_sky_components: tuple[str, ...],
) -> dict[str, object]:
    return {
        "id": category_id,
        "title": title,
        "diagnosticValue": diagnostic_value,
        "diagnosticLabel": label,
        "legacyCompatibilityValue": legacy_value,
        "legacyCompatibilityLabel": legacy_label,
        "scoreMeaning": "NSOM ObservableTargetValue category diagnostic",
        "scoreRange": "0..100",
        "mathPipeline": (
            "IntrinsicTargetQuality",
            "ObservationEnvironment",
            "EffectiveObservability",
            "ObservableTargetValue",
        ),
        "includedSkyComponents": included_sky_components,
        "excludedFromCategoryValue": (
            "ObserverCapability",
            "PracticalTargetValue",
            "SessionViability",
            "RecommendationConfidence",
            "ObservationOpportunity",
        ),
        "positiveFactors": (),
        "limitingFactors": (),
    }


def _contract_decisions(readiness: dict[str, object]) -> tuple[dict[str, object], ...]:
    return (
        _decision(
            "separate_nsom_presentation_payload",
            status="accepted_design",
            summary="Add a future separate `advancedObservingNsom` payload instead of replacing `advancedScores`.",
            reason="The current `advancedScores` payload is a legacy-compatible QML/Planner/notification contract.",
            blocks_default_on=False,
        ),
        _decision(
            "advanced_scores_legacy_compatibility",
            status="accepted",
            summary="Keep `advancedScores` legacy-compatible and unchanged.",
            reason="Planner and NotificationService depend on legacy-compatible score semantics.",
            blocks_default_on=False,
        ),
        _decision(
            "observable_value_only",
            status="accepted",
            summary="Use ObservableTargetValue category diagnostics for Advanced Observing NSOM presentation.",
            reason="Advanced Observing is a sky/category surface, not equipment-specific target practicality.",
            blocks_default_on=False,
        ),
        _decision(
            "session_and_confidence_metadata",
            status="accepted",
            summary="Keep SessionViability and RecommendationConfidence outside category values.",
            reason="Session state and source trust annotate the presentation but do not modify score.",
            blocks_default_on=False,
            extra={"confidence_score_effect": 0.0, "session_score_effect": 0.0},
        ),
        _decision(
            "runtime_projection_not_implemented",
            status="blocks_default_on",
            summary="The future payload is designed but not yet projected by AppController.",
            reason="Default-on requires a runtime projection that follows this contract.",
            blocks_default_on=True,
        ),
        _decision(
            "qml_exposure_review_required",
            status="blocks_default_on",
            summary="QML exposure requires a later UI/review step.",
            reason="The contract defines data semantics, not UI placement or visible copy.",
            blocks_default_on=True,
        ),
        _decision(
            "previous_readiness_blocker_addressed",
            status="accepted",
            summary="The 1.8.8 presentation-contract blocker is addressed at design level.",
            reason="This contract defines the missing payload shape and score semantics.",
            blocks_default_on=not bool(readiness["checks"]["hidden_snapshot_blocks_default_on"]),
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


def _checks(
    readiness: dict[str, object],
    payload: dict[str, object],
    decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    decision_ids = {decision["decision_id"] for decision in decisions}
    categories = payload["categories"]
    return {
        "default_flag_still_off": NSOM_ADVANCED_OBSERVING_ENABLED is False,
        "presentation_readiness_was_blocked": readiness["readiness"]["ready_for_default_on_switch"] is False,
        "contract_schema_versioned": payload["schemaVersion"] == SCHEMA_VERSION,
        "contract_defines_separate_future_property": payload["futureQmlProperty"] == "advancedObservingNsom"
        and payload["currentQmlProperty"] == "advancedScores",
        "contract_does_not_replace_advanced_scores": payload["consumerPolicy"]["replacesAdvancedScores"] is False,
        "contract_excludes_planner_and_notifications": payload["consumerPolicy"]["plannerInput"] is False
        and payload["consumerPolicy"]["notificationInput"] is False,
        "categories_use_observable_value_only": all(
            category["mathPipeline"]
            == (
                "IntrinsicTargetQuality",
                "ObservationEnvironment",
                "EffectiveObservability",
                "ObservableTargetValue",
            )
            for category in categories
        ),
        "session_and_confidence_are_metadata": payload["session"]["scoreEffect"] == 0.0
        and payload["confidence"]["scoreEffect"] == 0.0,
        "observer_and_opportunity_excluded": all(
            "ObserverCapability" in category["excludedFromCategoryValue"]
            and "ObservationOpportunity" in category["excludedFromCategoryValue"]
            for category in categories
        ),
        "required_contract_decisions_recorded": {
            "separate_nsom_presentation_payload",
            "advanced_scores_legacy_compatibility",
            "observable_value_only",
            "session_and_confidence_metadata",
            "runtime_projection_not_implemented",
            "qml_exposure_review_required",
            "previous_readiness_blocker_addressed",
        }.issubset(decision_ids),
        "runtime_projection_still_blocks_default_on": _decision_by_id(
            decisions,
            "runtime_projection_not_implemented",
        )["blocks_default_on"]
        is True,
        "qml_exposure_review_still_blocks_default_on": _decision_by_id(
            decisions,
            "qml_exposure_review_required",
        )["blocks_default_on"]
        is True,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "future_property_not_wired": static_checks["future_property_already_wired"] is False,
        "runtime_behaviour_unchanged": True,
    }


def _default_on_blockers(checks: dict[str, object]) -> tuple[str, ...]:
    names = {
        "default_flag_still_off": "advanced-observing-default-flag-still-off",
        "contract_schema_versioned": "advanced-observing-contract-schema-missing",
        "contract_defines_separate_future_property": "advanced-observing-contract-property-missing",
        "contract_does_not_replace_advanced_scores": "advanced-observing-contract-replaces-legacy-score",
        "contract_excludes_planner_and_notifications": "advanced-observing-contract-consumer-leak",
        "categories_use_observable_value_only": "advanced-observing-contract-wrong-nsom-layer",
        "session_and_confidence_are_metadata": "advanced-observing-contract-metadata-score-effect",
        "observer_and_opportunity_excluded": "advanced-observing-contract-opportunity-leak",
        "required_contract_decisions_recorded": "advanced-observing-contract-decisions-incomplete",
        "runtime_report_imports_absent": "advanced-observing-runtime-report-wiring",
        "qml_exposure_absent": "advanced-observing-unplanned-qml-exposure",
        "future_property_not_wired": "advanced-observing-future-property-already-wired",
        "runtime_behaviour_unchanged": "advanced-observing-runtime-behaviour-change",
    }
    blockers = [
        "advanced-observing-runtime-projection-not-implemented",
        "advanced-observing-qml-exposure-review-required",
    ]
    blockers.extend(name for key, name in names.items() if checks[key] is not True)
    return tuple(dict.fromkeys(blockers))


def _static_wiring_checks(root: Path) -> dict[str, object]:
    app_root = root / "astro_viewer" / "app"
    controller_path = app_root / "viewmodels" / "app_controller.py"
    controller_text = controller_path.read_text(encoding="utf-8") if controller_path.exists() else ""
    future_property_already_wired = "def advancedObservingNsom" in controller_text
    return {
        "qml_matches": _scan_files(app_root / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            app_root,
            ("*.py",),
            REPORT_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "future_property_already_wired": future_property_already_wired,
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
        explanation="Advanced Observing presentation contract fixture",
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
        explanation="Advanced Observing presentation contract fixture",
    )


def _sky_quality(bortle: int, radiance: float | None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="AdvancedObservingPresentationContractFixture",
        description="Advanced Observing presentation contract fixture",
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
