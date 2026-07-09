from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.models.equipment import Barlow, Binocular, Eyepiece, Telescope
from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.equipment_service import EquipmentService
from astro_viewer.app.services.equipment_setup_read_model import EquipmentSetupReadModelBuilder
from astro_viewer.tools.equipment_nsom_comparison_report import (
    REPORT_PATH as COMPARISON_REPORT_PATH,
    generate_report_data,
)
from astro_viewer.tools.equipment_nsom_policy_readiness import (
    POLICY_READINESS_PATH,
    generate_policy_readiness_data,
)


REPORT_PATH = Path("docs/EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT.md")

REPORT_IMPORT_MARKERS = (
    "equipment_presenter_contract_audit",
    "EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT",
)

QML_MARKERS = REPORT_IMPORT_MARKERS

REQUIRED_PAYLOAD_KEYS = (
    "bestEyepiece",
    "suggestedPosition",
    "barlow",
    "difficulty",
    "alternative",
    "highMagnification",
    "wideField",
    "setupText",
    "setupOptions",
    "explanation",
    "telescopeId",
    "telescopeName",
    "equipmentType",
    "setupType",
    "selectionScore",
)

REQUIRED_SETUP_OPTION_KEYS = (
    "role",
    "label",
    "detailLabel",
    "displayLabel",
    "suggestedPosition",
    "magnification",
    "trueField",
    "exitPupil",
    "barlow",
    "score",
    "telescopeName",
    "equipmentType",
)

CONTROLLER_PROJECTION_FIELDS = (
    "recommended_setup",
    "best_eyepiece",
    "barlow",
    "difficulty",
    "recommended_setup_type",
    "setup_options",
    "equipment_explanation",
)


def generate_equipment_presenter_contract_audit_data() -> dict[str, object]:
    """Developer-only audit for the Equipment presenter contract."""

    root = Path(__file__).parents[2]
    comparison = generate_report_data()
    policy = generate_policy_readiness_data()
    fixture = _presenter_fixture()
    decisions = _contract_decisions(fixture)
    static_checks = _static_wiring_checks(root)
    checks = _checks(comparison, policy, fixture, decisions, static_checks)
    blockers = _blockers(checks, decisions)

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
            "runtime_behaviour_changed_by_this_audit": False,
            "source_reports": (
                str(COMPARISON_REPORT_PATH).replace("\\", "/"),
                str(POLICY_READINESS_PATH).replace("\\", "/"),
            ),
            "report_path": str(REPORT_PATH).replace("\\", "/"),
        },
        "readiness": {
            "verdict": "equipment_setup_read_model_boundary_introduced",
            "presenter_contract_audited": True,
            "runtime_replacement_ready": False,
            "runtime_read_model_boundary_recommended": False,
            "runtime_read_model_boundary_present": static_checks["setup_read_model_boundary_present"] is True,
            "default_off_equipment_path_recommended_now": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "recommended_next_step": (
                "Review 1.13.1, then audit EquipmentService setup-score ownership "
                "before any scoring replacement."
            ),
            "reason": (
                "Equipment is an active setup-presentation helper. The existing "
                "runtime payload owns eyepiece, Barlow, binocular, fallback and "
                "setupOptions fields that Q_target does not replace. A "
                "runtime-neutral setup read-model boundary now preserves that "
                "payload before AppController projects it to CelestialObject fields. "
                "NSOM can own ObserverCapability/Q_target and future "
                "PracticalTargetValue metadata, but EquipmentService scoring is not "
                "ready for replacement."
            ),
        },
        "blockers": blockers,
        "presenter_contract": _presenter_contract(fixture),
        "contract_decisions": decisions,
        "fixture": fixture,
        "comparison_summary": comparison["summary"],
        "policy_readiness": policy["readiness"],
        "checks": checks,
        "static_wiring_checks": static_checks,
        "recommended_sequence": (
            {
                "step": "Review 1.13.1",
                "summary": (
                    "Confirm the Equipment setup read-model boundary preserves "
                    "runtime output and QML payload shape."
                ),
            },
            {
                "step": "1.13.2 Equipment setup score ownership audit",
                "summary": (
                    "Separate setup score components, sky/seeing inputs and "
                    "presentation-owned fallback semantics before any scoring "
                    "replacement."
                ),
            },
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_equipment_presenter_contract_audit_data() if data is None else data
    readiness = audit["readiness"]
    contract = audit["presenter_contract"]
    fixture = audit["fixture"]

    lines = [
        "# Equipment NSOM Presenter Contract Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit defines the presenter contract that must "
            "exist before any Equipment runtime scoring replacement. It does not "
            "change EquipmentService, Planner, Home, Best Object, Sky Compass, "
            "Detail/Object, QML, logging, network behaviour or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Presenter contract audited: `{readiness['presenter_contract_audited']}`.",
        f"- Runtime replacement ready: `{readiness['runtime_replacement_ready']}`.",
        (
            "- Runtime read-model boundary recommended: "
            f"`{readiness['runtime_read_model_boundary_recommended']}`."
        ),
        (
            "- Runtime read-model boundary present: "
            f"`{readiness['runtime_read_model_boundary_present']}`."
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
        "## Presenter Contract",
        "",
        f"- Runtime role: `{contract['runtime_role']}`.",
        f"- NSOM-owned input: `{contract['nsom_owned_input']}`.",
        f"- Presentation-owned output: `{contract['presentation_owned_output']}`.",
        f"- Replacement policy: `{contract['replacement_policy']}`.",
        f"- QML policy: `{contract['qml_policy']}`.",
        f"- Confidence policy: `{contract['confidence_policy']}`.",
        "",
        "## Payload Shape",
        "",
        f"- Suggestion payload keys: `{fixture['suggestion_payload_keys']}`.",
        f"- Setup option keys: `{fixture['setup_option_keys']}`.",
        f"- Setup option roles: `{fixture['setup_option_roles']}`.",
        f"- Fallback payloads are compatible subsets: `{fixture['fallback_payloads_are_known_subsets']}`.",
        (
            "- Read-model payload roundtrip matches service output: "
            f"`{fixture['read_model_payload_roundtrip_matches_service_output']}`."
        ),
        f"- Read-model celestial projection keys: `{fixture['read_model_celestial_projection_keys']}`.",
        "",
        "## Contract Decisions",
        "",
        "| Decision | Status | Layer | Blocks runtime replacement | Summary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for decision in audit["contract_decisions"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    f"`{decision['decision_id']}`",
                    f"`{decision['status']}`",
                    f"`{decision['affected_nsom_layer']}`",
                    f"`{decision['blocks_runtime_replacement']}`",
                    str(decision["decision"]),
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
            (
                "- AppController Equipment projection fields present: "
                f"`{audit['static_wiring_checks']['controller_projection_fields_present']}`."
            ),
            (
                "- AppController uses Equipment setup read-model boundary: "
                f"`{audit['static_wiring_checks']['setup_read_model_boundary_present']}`."
            ),
            (
                "- QML uses current Equipment payload fields: "
                f"`{audit['static_wiring_checks']['qml_payload_consumers_present']}`."
            ),
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
                "Equipment should not be migrated by replacing its setup score with "
                "Q_target. The setup read-model boundary now preserves the current "
                "payload while making ObserverCapability/Q_target ownership explicit; "
                "the next work is score-ownership review."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _presenter_contract(fixture: dict[str, object]) -> dict[str, object]:
    return {
        "runtime_role": "active_practical_setup_presenter",
        "nsom_owned_input": "ObserverCapability_profile_Q_target_reference",
        "presentation_owned_output": "equipment_setup_payload_and_setupOptions",
        "replacement_policy": "defer_scoring_replacement_until_setup_read_model_exists",
        "qml_policy": "preserve_existing_payload_no_nsom_fields",
        "confidence_policy": "metadata_only_zero_score_effect",
        "required_payload_keys": fixture["suggestion_payload_keys"],
        "required_setup_option_keys": fixture["setup_option_keys"],
        "controller_projection_fields": CONTROLLER_PROJECTION_FIELDS,
    }


def _contract_decisions(fixture: dict[str, object]) -> tuple[dict[str, object], ...]:
    return (
        _decision(
            "equipment_runtime_role",
            status="accepted",
            layer="presentation",
            decision="Equipment remains the runtime setup presenter, not a target recommendation score.",
            reason=(
                "It owns eyepiece, Barlow, binocular, naked-eye and missing-equipment "
                "states that are not represented by Q_target."
            ),
            blocks=True,
        ),
        _decision(
            "payload_shape_contract",
            status="accepted",
            layer="presentation",
            decision="Future work must preserve suggestion payload keys and setupOptions roles.",
            reason=(
                "Home and Object Detail consume the current payload directly, including "
                "`setupText`, `setupOptions`, `difficulty`, `barlow` and explanation fields."
            ),
            blocks=True,
            extra={
                "required_payload_keys": fixture["suggestion_payload_keys"],
                "required_setup_option_keys": fixture["setup_option_keys"],
            },
        ),
        _decision(
            "q_target_policy",
            status="accepted_reference_only",
            layer="observer",
            decision="Q_target is a reference projection for PracticalTargetValue, not a setup-option score.",
            reason="Q_target lacks focal position, eyepiece label, Barlow policy and fallback semantics.",
            blocks=True,
            extra={"q_target_replaces_selection_score": False},
        ),
        _decision(
            "seeing_and_sky_boundary",
            status="needs_score_ownership_audit",
            layer="sky",
            decision=(
                "Seeing and sky quality need explicit setup-score ownership review "
                "before Equipment scoring can be separated from legacy mixing."
            ),
            reason=(
                "Existing EquipmentService uses seeing and sky quality in setup score, "
                "while NSOM keeps them outside ObserverCapability. The setup read-model "
                "boundary preserves the payload but does not yet split that score."
            ),
            blocks=True,
        ),
        _decision(
            "fallback_policy",
            status="accepted",
            layer="presentation",
            decision="Naked-eye, missing-eyepiece and no-useful-configuration fallbacks stay presenter-owned.",
            reason="These states are UI-operational setup guidance, not target physics.",
            blocks=True,
        ),
        _decision(
            "selection_score_policy",
            status="accepted_compatibility",
            layer="presentation",
            decision="selectionScore remains a setup-local compatibility score until replaced by a named setup metric.",
            reason="It must not be interpreted as NSOM target value or recommendation confidence.",
            blocks=True,
        ),
        _decision(
            "confidence_policy",
            status="accepted",
            layer="confidence",
            decision="RecommendationConfidence remains metadata only and does not affect Equipment score or Q_target.",
            reason="Confidence describes trust, not optical setup suitability.",
            extra={"score_effect": 0.0, "score_path": "parallel_metadata"},
        ),
    )


def _decision(
    decision_id: str,
    *,
    status: str,
    layer: str,
    decision: str,
    reason: str,
    blocks: bool = False,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload = {
        "decision_id": decision_id,
        "status": status,
        "affected_nsom_layer": layer,
        "decision": decision,
        "reason": reason,
        "blocks_runtime_replacement": blocks,
        "runtime_behaviour_changed": False,
    }
    if extra:
        payload.update(extra)
    return payload


def _presenter_fixture() -> dict[str, object]:
    service = EquipmentService()
    builder = EquipmentSetupReadModelBuilder()
    target = _target()
    sky_quality = _sky_quality()
    seeing = _seeing()
    suggestion = service.suggest_for_profile(
        target,
        [_small_scope()],
        _eyepieces(),
        [_barlow()],
        seeing=seeing,
        sky_quality=sky_quality,
        binoculars=[_binocular()],
    )
    naked_eye = service.suggest_for_profile(
        _faint_target(),
        [],
        [],
        [],
        seeing=seeing,
        sky_quality=sky_quality,
        binoculars=[],
    )
    missing_eyepieces = service.suggest_for_profile(
        target,
        [_small_scope()],
        [],
        [],
        seeing=seeing,
        sky_quality=sky_quality,
        binoculars=[],
    )
    setup_options = suggestion.get("setupOptions", [])
    first_option = setup_options[0] if setup_options else {}
    read_model = builder.from_suggestion(target, suggestion)
    read_model_updates = read_model.to_celestial_object_updates()
    payload_keys = tuple(suggestion)
    setup_option_keys = tuple(first_option)
    return {
        "target_id": target.id,
        "suggestion_payload_keys": payload_keys,
        "required_payload_keys": REQUIRED_PAYLOAD_KEYS,
        "setup_option_keys": setup_option_keys,
        "required_setup_option_keys": REQUIRED_SETUP_OPTION_KEYS,
        "setup_option_roles": tuple(option.get("role", "") for option in setup_options),
        "recommended_setup_text": suggestion.get("setupText", ""),
        "recommended_equipment_type": suggestion.get("equipmentType", ""),
        "selection_score": suggestion.get("selectionScore", 0.0),
        "read_model_payload_roundtrip_matches_service_output": (
            read_model.to_equipment_service_payload() == suggestion
        ),
        "read_model_celestial_projection_keys": tuple(read_model_updates),
        "read_model_recommended_setup_type": read_model.recommended_setup_type,
        "fallback_payloads_are_known_subsets": (
            set(naked_eye).issubset(REQUIRED_PAYLOAD_KEYS)
            and set(missing_eyepieces).issubset(REQUIRED_PAYLOAD_KEYS)
        ),
        "fallback_payload_key_variants": {
            "naked_eye": tuple(naked_eye),
            "missing_eyepieces": tuple(missing_eyepieces),
        },
        "fallback_examples": {
            "naked_eye_setup_type": naked_eye.get("setupType", ""),
            "missing_eyepieces_setup_type": missing_eyepieces.get("setupType", ""),
            "missing_eyepieces_setup_text": missing_eyepieces.get("setupText", ""),
        },
    }


def _checks(
    comparison: dict[str, object],
    policy: dict[str, object],
    fixture: dict[str, object],
    decisions: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
) -> dict[str, object]:
    decision_ids = {decision["decision_id"] for decision in decisions}
    required_decisions = {
        "equipment_runtime_role",
        "payload_shape_contract",
        "q_target_policy",
        "seeing_and_sky_boundary",
        "fallback_policy",
        "selection_score_policy",
        "confidence_policy",
    }
    confidence = _decision_by_id(decisions, "confidence_policy")
    q_target = _decision_by_id(decisions, "q_target_policy")
    return {
        "strict_json_compatible": _strict_json_compatible(
            {
                "fixture": fixture,
                "decisions": decisions,
                "comparison_summary": comparison["summary"],
            }
        ),
        "required_contract_decisions_recorded": required_decisions.issubset(decision_ids),
        "payload_keys_preserved": tuple(fixture["suggestion_payload_keys"]) == REQUIRED_PAYLOAD_KEYS,
        "setup_option_keys_preserved": tuple(fixture["setup_option_keys"]) == REQUIRED_SETUP_OPTION_KEYS,
        "recommended_setup_option_present": "Consigliato" in tuple(fixture["setup_option_roles"]),
        "fallback_payloads_are_known_subsets": fixture["fallback_payloads_are_known_subsets"] is True,
        "read_model_payload_roundtrip_preserves_service_output": (
            fixture["read_model_payload_roundtrip_matches_service_output"] is True
        ),
        "read_model_celestial_projection_preserves_contract": set(
            fixture["read_model_celestial_projection_keys"]
        )
        == {
            "recommended_setup",
            "best_eyepiece",
            "barlow",
            "difficulty",
            "recommended_setup_type",
            "setup_options",
            "equipment_explanation",
        },
        "q_target_reference_only": q_target["q_target_replaces_selection_score"] is False,
        "policy_runtime_replacement_deferred": policy["readiness"]["ready_for_default_off_path"] is False,
        "observer_capability_adapter_extracted": policy["readiness"]["observer_capability_adapter_extracted"] is True,
        "comparison_evidence_available": comparison["metadata"]["candidate_row_count"] > 0,
        "confidence_score_neutral": confidence["score_effect"] == 0.0
        and policy["comparison_evidence"]["confidence_score_effect"] == 0.0,
        "controller_projection_fields_present": static_checks["controller_projection_fields_present"] is True,
        "setup_read_model_boundary_present": static_checks["setup_read_model_boundary_present"] is True,
        "qml_payload_consumers_present": static_checks["qml_payload_consumers_present"] is True,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _blockers(
    checks: dict[str, object],
    decisions: tuple[dict[str, object], ...],
) -> tuple[str, ...]:
    blockers = [
        f"equipment-presenter-{decision['decision_id'].replace('_', '-')}"
        for decision in decisions
        if decision["blocks_runtime_replacement"] is True
    ]
    safety_names = {
        "strict_json_compatible": "equipment-presenter-json-incompatible",
        "required_contract_decisions_recorded": "equipment-presenter-decisions-missing",
        "payload_keys_preserved": "equipment-presenter-payload-keys-missing",
        "setup_option_keys_preserved": "equipment-presenter-setup-option-keys-missing",
        "recommended_setup_option_present": "equipment-presenter-recommended-option-missing",
        "fallback_payloads_are_known_subsets": "equipment-presenter-fallback-shape-drift",
        "read_model_payload_roundtrip_preserves_service_output": "equipment-presenter-read-model-roundtrip-drift",
        "read_model_celestial_projection_preserves_contract": "equipment-presenter-read-model-projection-drift",
        "q_target_reference_only": "equipment-presenter-q-target-replaces-setup-score",
        "policy_runtime_replacement_deferred": "equipment-presenter-runtime-replacement-not-deferred",
        "observer_capability_adapter_extracted": "equipment-presenter-observer-adapter-missing",
        "comparison_evidence_available": "equipment-presenter-comparison-evidence-missing",
        "confidence_score_neutral": "equipment-presenter-confidence-score-effect",
        "controller_projection_fields_present": "equipment-presenter-controller-projection-drift",
        "setup_read_model_boundary_present": "equipment-presenter-read-model-boundary-missing",
        "qml_payload_consumers_present": "equipment-presenter-qml-payload-drift",
        "runtime_report_imports_absent": "equipment-presenter-runtime-wiring",
        "qml_report_exposure_absent": "equipment-presenter-qml-exposure",
        "runtime_behaviour_unchanged_by_audit": "equipment-presenter-runtime-change",
    }
    blockers.extend(name for key, name in safety_names.items() if checks[key] is not True)
    return tuple(dict.fromkeys(blockers))


def _decision_by_id(decisions: tuple[dict[str, object], ...], decision_id: str) -> dict[str, object]:
    return next(decision for decision in decisions if decision["decision_id"] == decision_id)


def _static_wiring_checks(root: Path) -> dict[str, object]:
    controller = (root / "astro_viewer" / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )
    setup_read_model = (
        root
        / "astro_viewer"
        / "app"
        / "services"
        / "equipment_setup_read_model.py"
    ).read_text(encoding="utf-8")
    home_qml = (root / "astro_viewer" / "app" / "ui" / "pages" / "HomePage.qml").read_text(
        encoding="utf-8"
    )
    detail_qml = (root / "astro_viewer" / "app" / "ui" / "pages" / "ObjectDetailPage.qml").read_text(
        encoding="utf-8"
    )
    return {
        "equipment_service_runtime_present": (
            "_equipment_service.suggest_for_profile" in controller
            and "def _apply_equipment" in controller
        ),
        "controller_projection_fields_present": all(
            field in controller for field in CONTROLLER_PROJECTION_FIELDS
        ),
        "setup_read_model_boundary_present": (
            "EquipmentSetupReadModelBuilder" in controller
            and "_equipment_setup_read_model_builder.from_suggestion" in controller
            and "EquipmentSetupReadModel" in setup_read_model
        ),
        "qml_payload_consumers_present": (
            "setupOptions" in home_qml
            and "equipmentExplanation" in home_qml
            and "recommended_setup" in home_qml
            and "setupOptions" in detail_qml
            and "recommended_setup" in detail_qml
        ),
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


def _target() -> CelestialObject:
    return CelestialObject(
        id="m45",
        name="Pleiades",
        object_type="Ammasso aperto",
        image="",
        magnitude="1.6",
        distance="444 ly",
        max_altitude="65 deg",
        direction="Sud",
        best_time="22:00",
        observing_window="21:00-01:00",
        notes="Fixture target.",
        recommended_setup="Fixture setup",
        visibility_class="Buona",
        azimuth="180 deg",
        time_above_horizon="5 h",
        visible=True,
        score=88,
        difficulty="Facile",
        apparent_size="1.8 deg",
        max_angular_size_deg=1.8,
        recommended_observation_type="WideField",
    )


def _faint_target() -> CelestialObject:
    return CelestialObject(
        id="m51",
        name="M51",
        object_type="Galassia",
        image="",
        magnitude="8.4",
        distance="23 Mly",
        max_altitude="55 deg",
        direction="Nord",
        best_time="23:00",
        observing_window="22:00-02:00",
        notes="Fixture target.",
        recommended_setup="Fixture setup",
        visibility_class="Buona",
        azimuth="20 deg",
        time_above_horizon="5 h",
        visible=True,
        score=84,
        difficulty="Media",
        apparent_size="0.2 deg",
        max_angular_size_deg=0.2,
        recommended_observation_type="General",
    )


def _small_scope() -> Telescope:
    return Telescope("small-70", "Small 70/500", 70, 500, "Refractor", "manual altaz")


def _eyepieces() -> list[Eyepiece]:
    return [
        Eyepiece("wide-32", "Wide 32 mm", 32.0, 68.0),
        Eyepiece("plossl-25", "Plossl 25 mm", 25.0, 52.0),
        Eyepiece("planetary-10", "Planetary 10 mm", 10.0, 60.0),
    ]


def _barlow() -> Barlow:
    return Barlow("barlow-2x", "2x Barlow", 2.0)


def _binocular() -> Binocular:
    return Binocular("bino-10x50", "Nikon 10x50", 10, 50)


def _sky_quality() -> SkyQuality:
    return SkyQuality(
        bortle_class=4,
        limiting_magnitude=6.2,
        sky_brightness=20.8,
        source="deterministic_fixture",
        description="Equipment presenter contract sky fixture.",
        confidence="high",
        viirs_radiance=1.5,
        viirs_observation_count=8,
    )


def _seeing() -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Good",
        transparency="Good",
        seeing_score=82,
        transparency_score=80,
        explanation="Equipment presenter contract seeing fixture.",
        source="deterministic_fixture",
        confidence="high",
    )


if __name__ == "__main__":
    write_markdown_report()
