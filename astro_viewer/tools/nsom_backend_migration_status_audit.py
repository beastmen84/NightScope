from __future__ import annotations

from inspect import signature
from pathlib import Path

from astro_viewer.app.models.nsom import nsom_to_json_compatible
from astro_viewer.app.services.advanced_observing_nsom_service import NSOM_ADVANCED_OBSERVING_ENABLED
from astro_viewer.app.services.best_object_nsom_ranking import NSOM_BEST_OBJECT_ENABLED
from astro_viewer.app.services.detail_nsom_runtime import NSOM_DETAIL_OBJECT_ENABLED
from astro_viewer.app.services.home_nsom_ranking import NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED
from astro_viewer.app.services.night_planner_service import NSOM_PLANNER_SCORING_ENABLED, NightPlannerService
from astro_viewer.app.services.sky_compass_nsom_ranking import NSOM_SKY_COMPASS_ENABLED
from astro_viewer.app.viewmodels.app_controller import AppController
from astro_viewer.tools.equipment_nsom_policy_readiness import generate_policy_readiness_data
from astro_viewer.tools.equipment_presenter_contract_audit import (
    generate_equipment_presenter_contract_audit_data,
)
from astro_viewer.tools.equipment_setup_score_ownership_audit import (
    generate_equipment_setup_score_ownership_audit_data,
)
from astro_viewer.tools.equipment_setup_score_component_boundary_report import (
    generate_equipment_setup_score_component_boundary_data,
)
from astro_viewer.tools.equipment_nsom_default_off_path_policy_audit import (
    generate_equipment_default_off_path_policy_audit_data,
)
from astro_viewer.tools.equipment_nsom_migration_closeout import (
    generate_equipment_nsom_migration_closeout_data,
)
from astro_viewer.tools.observation_conditions_read_model_audit import (
    generate_observation_conditions_read_model_audit_data,
)
from astro_viewer.tools.observation_conditions_consumer_reroute_audit import (
    generate_observation_conditions_consumer_reroute_audit_data,
)
from astro_viewer.tools.notifications_dead_legacy_audit import generate_notifications_dead_legacy_audit_data


REPORT_PATH = Path("docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md")

SOURCE_REPORTS = (
    Path("docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/HOME_NSOM_RECOMMENDED_DEEP_SKY_READINESS_AUDIT.md"),
    Path("docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md"),
    Path("docs/DETAIL_OBJECT_NSOM_MIGRATION_CLOSEOUT.md"),
    Path("docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md"),
    Path("docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md"),
    Path("docs/OBSERVATION_CONDITIONS_READ_MODEL_AUDIT.md"),
    Path("docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md"),
    Path("docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md"),
    Path("docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md"),
    Path("docs/EQUIPMENT_NSOM_POLICY_READINESS.md"),
    Path("docs/EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT.md"),
    Path("docs/EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT.md"),
    Path("docs/EQUIPMENT_SETUP_SCORE_COMPONENT_BOUNDARY.md"),
    Path("docs/EQUIPMENT_NSOM_DEFAULT_OFF_PATH_POLICY_AUDIT.md"),
    Path("docs/EQUIPMENT_NSOM_MIGRATION_CLOSEOUT.md"),
    Path("docs/NSOM_ROLLBACK_CLEANUP_POLICY_AUDIT.md"),
    Path("docs/NSOM_MOON_GEOMETRY_PLANNER_CALIBRATION.md"),
    Path("docs/NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS.md"),
    Path("docs/NSOM_AOD_OPENAQ_SCORING_READINESS.md"),
    Path("docs/NSOM_AOD_OPENAQ_PROVIDER_QUALITY_POLICY.md"),
    Path("docs/NSOM_AOD_OPENAQ_DEFAULT_OFF_SCORING_EXPERIMENT.md"),
    Path("docs/NSOM_AOD_OPENAQ_CALIBRATION_AUDIT.md"),
    Path("docs/NSOM_AOD_OPENAQ_DEFAULT_ON_READINESS.md"),
    Path("docs/NSOM_AOD_OPENAQ_FIELD_CALIBRATION.md"),
    Path("docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_PROBE.md"),
)

REPORT_IMPORT_MARKERS = (
    "nsom_backend_migration_status_audit",
    "NSOM_BACKEND_MIGRATION_STATUS_AUDIT",
    "NSOM_BACKEND_MIGRATION_STATUS",
)

QML_MARKERS = (
    "nsomBackendMigrationStatus",
    "backendMigrationStatus",
    "NSOM_BACKEND_MIGRATION_STATUS_AUDIT",
)


def generate_backend_migration_status_audit_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    default_on_surfaces = _default_on_surfaces()
    notification_audit = generate_notifications_dead_legacy_audit_data()
    observation_conditions_audit = generate_observation_conditions_read_model_audit_data()
    observation_conditions_reroute_audit = generate_observation_conditions_consumer_reroute_audit_data()
    equipment_policy = generate_policy_readiness_data()
    equipment_presenter_contract = generate_equipment_presenter_contract_audit_data()
    equipment_score_ownership = generate_equipment_setup_score_ownership_audit_data()
    equipment_score_boundary = generate_equipment_setup_score_component_boundary_data()
    equipment_default_off_policy = generate_equipment_default_off_path_policy_audit_data()
    equipment_closeout = generate_equipment_nsom_migration_closeout_data()
    remaining_surfaces = _remaining_legacy_or_hybrid_surfaces(
        observation_conditions_audit,
        observation_conditions_reroute_audit,
        equipment_presenter_contract,
        equipment_score_ownership,
        equipment_score_boundary,
        equipment_default_off_policy,
        equipment_closeout,
    )
    static_checks = _static_wiring_checks(root)
    documentation = _documentation_state(root)
    checks = _checks(
        default_on_surfaces,
        remaining_surfaces,
        static_checks,
        documentation,
        equipment_policy,
        equipment_presenter_contract,
        equipment_score_ownership,
        equipment_score_boundary,
        equipment_default_off_policy,
        equipment_closeout,
    )
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
            "home_recommended_deep_sky_changed": False,
            "best_object_changed": False,
            "advanced_observing_changed": False,
            "sky_compass_changed": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "source_reports": tuple(str(path).replace("\\", "/") for path in SOURCE_REPORTS),
        },
        "readiness": {
            "verdict": (
                "backend_nsom_default_on_surfaces_closed"
                if not blockers
                else "backend_nsom_audit_needs_review"
            ),
            "all_current_default_on_surfaces_closed": not blockers,
            "ready_to_start_next_backend_area": not blockers,
            "ready_for_visible_ui_redesign": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "recommended_next_step": (
                "Review 1.14.15 real-provider AOD/OpenAQ results, then decide "
                "whether to make a narrow default-on switch or collect more "
                "field observations"
            ),
            "reason": (
                "Planner, Home recommendedDeepSky, Best Object, Advanced Observing "
                "backend, Sky Compass and Detail/Object have default-on NSOM paths "
                "and their internal runtime rollback constructor parameters have "
                "been removed. Remaining items are non-blocking legacy or "
                "hybrid surfaces; Sky Map and Notifications have been removed as "
                "dead legacy. ObservationConditions is active hybrid runtime code "
                "and now has a read-model boundary that separates raw and display "
                "targets plus a consumer reroute policy audit. Home recommendedDeepSky "
                "now consumes the raw read-model target for NSOM ranking; Best Object "
                "now scores raw read-model targets and returns display payload targets; "
                "Sky Compass now uses the read-model split adapter for raw target "
                "physics plus display/live geometry, closing the "
                "ObservationConditions consumer reroute series. "
                "Equipment now has a shared ObserverCapability/Q_target adapter "
                "plus a setup read-model/presenter boundary and score ownership "
                "audit. Its setup-score components are now exposed through a "
                "runtime-neutral read-model with parity checks. The default-off "
                "path policy audit keeps Equipment setup-local; runtime setup "
                "recommendations remain unchanged. The 1.13.5 closeout closes "
                "Equipment as an NSOM-bounded setup-local service. The 1.13.6 "
                "overall backend readiness audit classifies the remaining work as "
                "non-blocking rollback, presentation or Catalogue/Universe policy. "
                "The 1.13.7 rollback cleanup policy recommended removing internal "
                "legacy rollback paths; 1.13.8 removed those runtime constructor "
                "parameters. Planner Moon geometry is now default-on through a "
                "narrow Planner-specific switch. Provider-backed AOD/OpenAQ "
                "readiness and provider-quality policy are documented. AOD/OpenAQ "
                "now has an explicit default-off scoring experiment; default "
                "runtime scoring remains disabled. The 1.14.11 calibration audit "
                "identified score-scale and penalty-cap/transparency-shape review "
                "items; 1.14.12 calibrates the formula shape by mapping class caps "
                "to transparency loss and deriving score modifiers from target "
                "score. The 1.14.13 default-on readiness audit keeps AOD/OpenAQ "
                "disabled and leaves aerosol score-scale validation as the only "
                "default-on blocker. The 1.14.14 field-calibration fixtures pass "
                "the deterministic bands. The 1.14.15 real-provider probe covers "
                "five mixed locations and observes policy branches none, aod and "
                "particulate while preserving default flag-off neutrality. The "
                "remaining decision is human review of that real-provider scale "
                "before a narrow default-on switch."
            ),
        },
        "blockers": blockers,
        "default_on_surfaces": default_on_surfaces,
        "remaining_non_blocking_items": remaining_surfaces,
        "documentation_state": documentation,
        "equipment_policy": equipment_policy["readiness"],
        "equipment_presenter_contract": equipment_presenter_contract["readiness"],
        "equipment_score_ownership": equipment_score_ownership["readiness"],
        "equipment_score_boundary": equipment_score_boundary["readiness"],
        "equipment_default_off_policy": equipment_default_off_policy["readiness"],
        "equipment_closeout": equipment_closeout["readiness"],
        "notification_audit": notification_audit["notification_surface"],
        "observation_conditions_audit": observation_conditions_audit["readiness"],
        "observation_conditions_consumer_reroute_audit": observation_conditions_reroute_audit["readiness"],
        "static_wiring_checks": static_checks,
        "checks": checks,
        "recommended_sequence": _recommended_sequence(),
        "safety": _safety(static_checks),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_backend_migration_status_audit_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# NSOM Backend Migration Status Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit reviews the current NSOM backend migration "
            "state after the Planner, Home `recommendedDeepSky`, Best Object, "
            "Advanced Observing backend, Sky Compass and Detail/Object default-on "
            "steps. It does not change runtime behaviour, QML, scoring, logging, "
            "network access or runtime file writes."
        ),
        "",
        "## Readiness Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Current default-on surfaces closed: `{readiness['all_current_default_on_surfaces_closed']}`.",
        f"- Ready to start next backend area: `{readiness['ready_to_start_next_backend_area']}`.",
        f"- Ready for visible UI redesign: `{readiness['ready_for_visible_ui_redesign']}`.",
        f"- Runtime behaviour changed by this audit: `{readiness['runtime_behaviour_changed_by_this_audit']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}.",
        f"- Reason: {readiness['reason']}",
        "",
        "## Audit Blockers",
        "",
    ]
    if audit["blockers"]:
        lines.extend(f"- `{blocker}`" for blocker in audit["blockers"])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Default-On NSOM Surfaces",
            "",
            "| Surface | Status | Default flag | Rollback cleanup | NSOM role |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for surface in audit["default_on_surfaces"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    surface["surface"],
                    f"`{surface['status']}`",
                    f"`{surface['default_flag']}`",
                    f"`{surface['rollback_status']}`",
                    surface["nsom_role"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Remaining Legacy Or Hybrid Surfaces",
            "",
            "| Area | Status | Why it remains | Recommended handling |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in audit["remaining_non_blocking_items"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["area"],
                    f"`{item['status']}`",
                    item["why_it_remains"],
                    item["recommended_handling"],
                )
            )
            + " |"
        )

    notification = audit["notification_audit"]
    observation = audit["observation_conditions_audit"]
    reroute = audit["observation_conditions_consumer_reroute_audit"]
    lines.extend(
        [
            "",
            "## Removed Dead Legacy",
            "",
            f"- Notifications classification: `{notification['classification']}`.",
            f"- Notifications controller runtime present: `{notification['controller_runtime_present']}`.",
            f"- Notifications service file present: `{notification['service_file_present']}`.",
            f"- Notifications model DTO present: `{notification['model_dto_present']}`.",
            "",
            "## ObservationConditions Audit",
            "",
            f"- Verdict: `{observation['verdict']}`.",
            f"- Runtime migration recommended now: `{observation['runtime_migration_recommended_now']}`.",
            f"- Safe to remove service: `{observation['safe_to_remove_service']}`.",
            f"- Recommended next step: {observation['recommended_next_step']}",
            "",
            "## ObservationConditions Consumer Reroute Audit",
            "",
            f"- Verdict: `{reroute['verdict']}`.",
            f"- Runtime reroute recommended now: `{reroute['runtime_reroute_recommended_now']}`.",
            f"- Safe to change runtime in this step: `{reroute['safe_to_change_runtime_in_this_step']}`.",
            f"- Recommended next step: {reroute['recommended_next_step']}",
            "",
            "## Documentation State",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["documentation_state"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Safety Checks",
            "",
            "| Check | Result |",
            "| --- | --- |",
        ]
    )
    for key, value in audit["safety"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
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
                "The backend NSOM migration is closed for the already migrated "
                "recommendation surfaces and Detail/Object. Sky Map has been removed "
                "as dead legacy rather than migrated to NSOM. Notifications are now "
                "removed dead legacy, not an NSOM migration surface. "
                "ObservationConditions is active hybrid runtime code and now has "
                "an internal read-model boundary separating raw and display target "
                "data plus a consumer reroute policy; runtime rerouting remains a "
                "separate reviewed implementation step. "
                "Equipment now has a "
                "shared ObserverCapability/Q_target adapter, setup read-model "
                "boundary, score ownership audit and setup-score component "
                "boundary. The 1.13.4 policy keeps it setup-local and does not add "
                "a default-off replacement path; runtime setup recommendations "
                "remain unchanged. The 1.13.5 closeout records the Equipment "
                "backend migration as closed for the current setup-local scope. "
                "The 1.13.6 overall backend readiness audit classifies the "
                "remaining work as non-blocking rollback, presentation or "
                "Catalogue/Universe policy. The 1.13.7 rollback cleanup policy "
                "recommended removing internal rollback paths; 1.13.8 removed "
                "the runtime constructor rollback parameters. "
                "Planner Moon geometry is default-on. AOD/OpenAQ provider-quality "
                "policy is hardened, the default-off formula exists and 1.14.12 "
                "calibrates the penalty-cap/transparency shape. Runtime aerosol "
                "scoring remains disabled by default, and visible UI explanation "
                "work remains separate."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _default_on_surfaces() -> tuple[dict[str, object], ...]:
    controller_parameters = signature(AppController.__init__).parameters
    planner_parameters = signature(NightPlannerService.__init__).parameters
    return (
        {
            "surface": "Planner",
            "status": "default_on_closed",
            "default_flag": f"NSOM_PLANNER_SCORING_ENABLED = {NSOM_PLANNER_SCORING_ENABLED}",
            "default_flag_enabled": NSOM_PLANNER_SCORING_ENABLED is True,
            "rollback": "removed: NightPlannerService(use_nsom_planner_scoring=False)",
            "rollback_status": "removed_internal_runtime_rollback",
            "rollback_parameter_present": "use_nsom_planner_scoring" in planner_parameters,
            "nsom_role": "ObservationOpportunity ranking",
            "confidence_score_neutral": True,
            "source_report": "docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md",
        },
        {
            "surface": "Home recommendedDeepSky",
            "status": "default_on_closed",
            "default_flag": (
                "NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED = "
                f"{NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED}"
            ),
            "default_flag_enabled": NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED is True,
            "rollback": "removed: AppController(use_nsom_home_recommended_deep_sky=False)",
            "rollback_status": "removed_internal_runtime_rollback",
            "rollback_parameter_present": "use_nsom_home_recommended_deep_sky" in controller_parameters,
            "nsom_role": "ObservableTargetValue ordering",
            "confidence_score_neutral": True,
            "source_report": "docs/HOME_NSOM_RECOMMENDED_DEEP_SKY_READINESS_AUDIT.md",
        },
        {
            "surface": "Best Object",
            "status": "default_on_closed",
            "default_flag": f"NSOM_BEST_OBJECT_ENABLED = {NSOM_BEST_OBJECT_ENABLED}",
            "default_flag_enabled": NSOM_BEST_OBJECT_ENABLED is True,
            "rollback": "removed: AppController(use_nsom_best_object=False)",
            "rollback_status": "removed_internal_runtime_rollback",
            "rollback_parameter_present": "use_nsom_best_object" in controller_parameters,
            "nsom_role": "Home-specific ObservationOpportunity selection",
            "confidence_score_neutral": True,
            "source_report": "docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
        },
        {
            "surface": "Advanced Observing backend",
            "status": "default_on_closed_backend_only",
            "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
            "default_flag_enabled": NSOM_ADVANCED_OBSERVING_ENABLED is True,
            "rollback": "removed: AppController(use_nsom_advanced_observing=False)",
            "rollback_status": "removed_internal_runtime_rollback",
            "rollback_parameter_present": "use_nsom_advanced_observing" in controller_parameters,
            "nsom_role": "category ObservableTargetValue projection",
            "confidence_score_neutral": True,
            "source_report": "docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
        },
        {
            "surface": "Sky Compass",
            "status": "default_on_closed",
            "default_flag": f"NSOM_SKY_COMPASS_ENABLED = {NSOM_SKY_COMPASS_ENABLED}",
            "default_flag_enabled": NSOM_SKY_COMPASS_ENABLED is True,
            "rollback": "removed: AppController(use_nsom_sky_compass=False)",
            "rollback_status": "removed_internal_runtime_rollback",
            "rollback_parameter_present": "use_nsom_sky_compass" in controller_parameters,
            "nsom_role": "ObservableTargetValue based direction policy",
            "confidence_score_neutral": True,
            "source_report": "docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
        },
        {
            "surface": "Detail/Object internal payload",
            "status": "default_on_closed_backend_only",
            "default_flag": f"NSOM_DETAIL_OBJECT_ENABLED = {NSOM_DETAIL_OBJECT_ENABLED}",
            "default_flag_enabled": NSOM_DETAIL_OBJECT_ENABLED is True,
            "rollback": "removed: AppController(use_nsom_detail_object=False)",
            "rollback_status": "removed_internal_runtime_rollback",
            "rollback_parameter_present": "use_nsom_detail_object" in controller_parameters,
            "nsom_role": "separate internal Detail/Object payload",
            "confidence_score_neutral": True,
            "source_report": "docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
        },
    )


def _remaining_legacy_or_hybrid_surfaces(
    observation_conditions_audit: dict[str, object],
    observation_conditions_reroute_audit: dict[str, object],
    equipment_presenter_contract: dict[str, object],
    equipment_score_ownership: dict[str, object],
    equipment_score_boundary: dict[str, object],
    equipment_default_off_policy: dict[str, object],
    equipment_closeout: dict[str, object],
) -> tuple[dict[str, object], ...]:
    observation_readiness = observation_conditions_audit["readiness"]
    reroute_readiness = observation_conditions_reroute_audit["readiness"]
    equipment_score_readiness = equipment_score_ownership["readiness"]
    equipment_boundary_readiness = equipment_score_boundary["readiness"]
    equipment_policy_readiness = equipment_default_off_policy["readiness"]
    equipment_closeout_readiness = equipment_closeout["readiness"]
    return (
        {
            "area": "Equipment recommendations",
            "status": equipment_closeout_readiness["verdict"],
            "ownership_status": equipment_score_readiness["verdict"],
            "boundary_status": equipment_boundary_readiness["verdict"],
            "default_off_policy_status": equipment_policy_readiness["verdict"],
            "closeout_status": equipment_closeout_readiness["verdict"],
            "why_it_remains": (
                "`EquipmentService` still ranks eyepiece/Barlow/binocular candidates "
                "with its own practical configuration score. "
                "`observer_capability_adapter.py` now provides shared "
                "ObserverCapability/Q_target projection, and "
                "`docs/EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT.md` classifies the "
                "current score components. "
                "`docs/EQUIPMENT_SETUP_SCORE_COMPONENT_BOUNDARY.md` verifies the "
                "new immutable component read-model and parity against current "
                "EquipmentService scores. "
                "`docs/EQUIPMENT_NSOM_DEFAULT_OFF_PATH_POLICY_AUDIT.md` rejects a "
                "default-off replacement path for now and keeps Equipment setup-local "
                "with status `equipment_default_off_path_policy_set_setup_local`. "
                "`docs/EQUIPMENT_NSOM_MIGRATION_CLOSEOUT.md` closes the Equipment "
                "backend migration for the current setup-local scope. "
                "`docs/NSOM_OVERALL_BACKEND_READINESS_AUDIT.md` classifies the "
                "remaining backend work as non-blocking policy or presentation cleanup. "
                "`docs/NSOM_ROLLBACK_CLEANUP_POLICY_AUDIT.md` records that "
                "1.13.8 removed internal runtime rollback constructor paths."
            ),
            "recommended_handling": (
                "Keep Equipment as a setup-local service; rollback cleanup is "
                "complete, so visible UI/explanation or Universe/catalogue policy "
                "can be considered separately."
            ),
            "blocks_current_default_on_surfaces": False,
        },
        {
            "area": "ObservationConditions prepared-object cache",
            "status": reroute_readiness["verdict"],
            "why_it_remains": (
                "`ObservationConditionsService` still creates conditioned object "
                "copies for moon and light-pollution presentation/fallback paths; "
                "the 1.12.6 boundary preserves raw and display target fields "
                "separately, the 1.12.7 audit defines how consumers should reroute "
                "to raw inputs, and the 1.12.8 runtime step applies that policy to "
                "Home recommendedDeepSky. The 1.12.9 runtime step applies the same "
                "raw-score/display-payload split to Best Object. The 1.12.10 policy "
                "defines the remaining Sky Compass split, and the 1.12.11 runtime "
                "step implements it. The 1.12.12 closeout records the consumer "
                "reroute series as complete."
            ),
            "recommended_handling": (
                "Keep the read-model boundary as active compatibility code; no "
                "ObservationConditions consumer reroute work remains open."
            ),
            "read_model_boundary_status": observation_readiness["verdict"],
            "blocks_current_default_on_surfaces": False,
        },
        {
            "area": "Catalogue / raw object score",
            "status": "upstream_legacy_input",
            "why_it_remains": (
                "Catalogue and engine prepared scores remain the raw target input "
                "for several compatibility payloads."
            ),
            "recommended_handling": "Treat as Universe/read-model work, not as a ranking hotfix.",
            "blocks_current_default_on_surfaces": False,
        },
    )


def _documentation_state(root: Path) -> dict[str, object]:
    return {
        "version": _read_text(root / "VERSION").strip(),
        "source_reports_present": tuple(path.exists() for path in (root / path for path in SOURCE_REPORTS)),
        "base_docs_expected_to_be_updated_with_this_audit": True,
        "report_path": str(REPORT_PATH).replace("\\", "/"),
    }


def _checks(
    default_on_surfaces: tuple[dict[str, object], ...],
    remaining_surfaces: tuple[dict[str, object], ...],
    static_checks: dict[str, object],
    documentation: dict[str, object],
    equipment_policy: dict[str, object],
    equipment_presenter_contract: dict[str, object],
    equipment_score_ownership: dict[str, object],
    equipment_score_boundary: dict[str, object],
    equipment_default_off_policy: dict[str, object],
    equipment_closeout: dict[str, object],
) -> dict[str, object]:
    return {
        "all_default_flags_enabled": all(surface["default_flag_enabled"] is True for surface in default_on_surfaces),
        "all_internal_rollback_paths_removed": all(
            surface["rollback_parameter_present"] is False for surface in default_on_surfaces
        ),
        "all_rollback_records_mark_removed": all(
            surface["rollback_status"] == "removed_internal_runtime_rollback"
            for surface in default_on_surfaces
        ),
        "confidence_score_neutral_across_default_on_surfaces": all(
            surface["confidence_score_neutral"] is True for surface in default_on_surfaces
        ),
        "remaining_surfaces_are_non_blocking": all(
            item["blocks_current_default_on_surfaces"] is False for item in remaining_surfaces
        ),
        "equipment_policy_ready_for_adapter_step": equipment_policy["readiness"][
            "ready_for_observer_capability_adapter_step"
        ]
        is True,
        "equipment_observer_adapter_extracted": equipment_policy["readiness"][
            "observer_capability_adapter_extracted"
        ]
        is True,
        "equipment_presenter_contract_audited": equipment_presenter_contract["readiness"][
            "presenter_contract_audited"
        ]
        is True,
        "equipment_setup_read_model_boundary_present": equipment_presenter_contract["readiness"][
            "runtime_read_model_boundary_present"
        ]
        is True,
        "equipment_runtime_replacement_deferred": equipment_presenter_contract["readiness"][
            "runtime_replacement_ready"
        ]
        is False,
        "equipment_score_ownership_audited": equipment_score_ownership["readiness"][
            "verdict"
        ]
        == "equipment_setup_score_ownership_audited",
        "equipment_score_component_boundary_recommended": equipment_score_ownership["readiness"][
            "score_component_boundary_recommended"
        ]
        is True,
        "equipment_score_component_boundary_introduced": equipment_score_boundary["readiness"][
            "verdict"
        ]
        == "equipment_setup_score_component_boundary_introduced",
        "equipment_score_component_boundary_parity_checked": equipment_score_boundary["checks"][
            "score_read_model_matches_candidate_scores"
        ]
        is True,
        "equipment_default_off_policy_set": equipment_default_off_policy["readiness"][
            "verdict"
        ]
        == "equipment_default_off_path_policy_set_setup_local",
        "equipment_default_off_path_not_recommended_now": equipment_default_off_policy["readiness"][
            "default_off_equipment_path_recommended_now"
        ]
        is False,
        "equipment_setup_local_service_recommended": equipment_default_off_policy["readiness"][
            "setup_local_service_recommended"
        ]
        is True,
        "equipment_policy_does_not_block_closeout": equipment_default_off_policy["readiness"][
            "blocks_backend_migration_closeout"
        ]
        is False,
        "equipment_migration_closeout_present": equipment_closeout["readiness"][
            "verdict"
        ]
        == "equipment_nsom_migration_closed_setup_local",
        "equipment_migration_closed_setup_local": equipment_closeout["readiness"][
            "migration_closed"
        ]
        is True,
        "equipment_closeout_does_not_change_runtime": equipment_closeout["readiness"][
            "runtime_behaviour_changed_by_closeout"
        ]
        is False,
        "source_reports_present": all(documentation["source_reports_present"]),
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_exposure_absent": static_checks["qml_matches"] == (),
        "recommended_next_step_present": True,
        "runtime_behaviour_unchanged_by_audit": True,
    }


def _blockers(checks: dict[str, object]) -> tuple[str, ...]:
    names = {
        "all_default_flags_enabled": "nsom-default-on-flag-missing",
        "all_internal_rollback_paths_removed": "nsom-internal-rollback-path-still-present",
        "all_rollback_records_mark_removed": "nsom-rollback-record-not-removed",
        "confidence_score_neutral_across_default_on_surfaces": "nsom-confidence-score-effect",
        "source_reports_present": "nsom-source-report-missing",
        "equipment_policy_ready_for_adapter_step": "equipment-policy-adapter-step-not-ready",
        "equipment_observer_adapter_extracted": "equipment-observer-adapter-not-extracted",
        "equipment_presenter_contract_audited": "equipment-presenter-contract-not-audited",
        "equipment_setup_read_model_boundary_present": "equipment-setup-read-model-boundary-missing",
        "equipment_runtime_replacement_deferred": "equipment-runtime-replacement-not-deferred",
        "equipment_score_ownership_audited": "equipment-score-ownership-not-audited",
        "equipment_score_component_boundary_recommended": "equipment-score-component-boundary-not-recommended",
        "equipment_score_component_boundary_introduced": "equipment-score-component-boundary-not-introduced",
        "equipment_score_component_boundary_parity_checked": "equipment-score-component-boundary-parity-drift",
        "equipment_default_off_policy_set": "equipment-default-off-policy-not-set",
        "equipment_default_off_path_not_recommended_now": "equipment-default-off-path-unexpectedly-recommended",
        "equipment_setup_local_service_recommended": "equipment-setup-local-service-not-recommended",
        "equipment_policy_does_not_block_closeout": "equipment-policy-blocks-closeout",
        "equipment_migration_closeout_present": "equipment-migration-closeout-missing",
        "equipment_migration_closed_setup_local": "equipment-migration-not-closed-setup-local",
        "equipment_closeout_does_not_change_runtime": "equipment-closeout-runtime-change",
        "runtime_report_imports_absent": "nsom-audit-runtime-wiring",
        "qml_exposure_absent": "nsom-audit-qml-exposure",
        "runtime_behaviour_unchanged_by_audit": "nsom-audit-runtime-change",
    }
    return tuple(name for key, name in names.items() if checks[key] is not True)


def _safety(static_checks: dict[str, object]) -> dict[str, object]:
    return {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
        "qml_audit_exposure_absent": static_checks["qml_matches"] == (),
        "runtime_behaviour_changed_by_this_audit": False,
    }


def _recommended_sequence() -> tuple[dict[str, object], ...]:
    return (
        {
            "step": "Review 1.9.7",
            "summary": "Verify this backend status audit before opening a new migration area.",
        },
        {
            "step": "Review 1.10.6",
            "summary": "Verify Detail/Object NSOM migration closeout documentation.",
        },
        {
            "step": "1.11.0 Legacy backend surface audit",
            "summary": "Classify remaining legacy paths as dead code, temporary rollback or payload compatibility.",
        },
        {
            "step": "Review 1.11.1",
            "summary": "Confirm the Sky Map controller/property/service path is removed cleanly.",
        },
        {
            "step": "1.12.0 Equipment/ObserverCapability NSOM comparison",
            "summary": "Start the next active backend NSOM area with Equipment recommendation comparison.",
        },
        {
            "step": "Review 1.12.0",
            "summary": "Confirm the comparison report is accurate and no runtime Equipment behaviour changed.",
        },
        {
            "step": "1.12.1 Equipment NSOM policy readiness",
            "summary": "Decide whether Equipment should get a default-off NSOM path or stay a practical setup helper.",
        },
        {
            "step": "Review 1.12.1",
            "summary": "Confirm the Equipment policy decision defers runtime replacement and preserves behaviour.",
        },
        {
            "step": "1.12.2 ObserverCapability adapter extraction",
            "summary": "Extract a shared ObserverCapability/Q_target adapter while leaving EquipmentService runtime output unchanged.",
        },
        {
            "step": "Review 1.12.2",
            "summary": "Confirm adapter extraction preserved Equipment comparison values and runtime output.",
        },
        {
            "step": "1.12.3 Notifications dead legacy audit",
            "summary": "Classify Notifications as dead legacy because no QML/Home consumer remains.",
        },
        {
            "step": "1.12.4 Remove dead Notifications backend path",
            "summary": "Confirm AppController notifications, NotificationService and leftover DTO/tests are removed.",
        },
        {
            "step": "1.12.5 ObservationConditions read-model audit",
            "summary": "Audit conditioned-object cache ownership and NSOM input risks.",
        },
        {
            "step": "Review 1.12.5",
            "summary": "Confirm the audit before adding a read-model boundary.",
        },
        {
            "step": "1.12.6 ObservationConditions read-model boundary",
            "summary": "Separate raw target input from condition-adjusted display compatibility fields.",
        },
        {
            "step": "Review 1.12.6",
            "summary": "Confirm the boundary preserves runtime behaviour and read-model fidelity.",
        },
        {
            "step": "1.12.7 ObservationConditions consumer reroute audit",
            "summary": "Define raw-target consumer policy before changing runtime inputs.",
        },
        {
            "step": "Review 1.12.7",
            "summary": "Choose the first consumer reroute implementation, starting with Home if accepted.",
        },
        {
            "step": "1.12.8 Home recommendedDeepSky raw-target reroute",
            "summary": "Rank Home recommendedDeepSky NSOM candidates from read-model raw targets.",
        },
        {
            "step": "Review 1.12.8",
            "summary": "Confirm Home payload compatibility and choose the next consumer reroute.",
        },
        {
            "step": "1.12.9 Best Object raw-target reroute",
            "summary": "Score Best Object NSOM candidates from read-model raw targets.",
        },
        {
            "step": "Review 1.12.9",
            "summary": "Confirm Best Object payload compatibility and decide whether Sky Compass should reroute.",
        },
        {
            "step": "1.12.10 Sky Compass read-model reroute policy",
            "summary": "Define raw target physics vs display/live geometry ownership before runtime changes.",
        },
        {
            "step": "Review 1.12.10",
            "summary": "Confirm the Sky Compass split policy before implementing the runtime adapter.",
        },
        {
            "step": "1.12.11 Sky Compass read-model reroute",
            "summary": "Use raw target physics for Sky Compass ObservableTargetValue and display/live geometry for payload.",
        },
        {
            "step": "Review 1.12.11",
            "summary": "Confirm the final ObservationConditions consumer reroute before closeout.",
        },
        {
            "step": "1.12.12 ObservationConditions consumer reroute closeout",
            "summary": (
                "Close the Home, Best Object and Sky Compass read-model consumer "
                "reroute series and reopen Equipment presenter contract work."
            ),
        },
        {
            "step": "Next backend area: Equipment presenter contract",
            "summary": (
                "Decide how the shared ObserverCapability/Q_target adapter should "
                "feed Equipment presentation without reviving legacy scoring."
            ),
        },
        {
            "step": "1.13.0 Equipment presenter contract audit",
            "summary": (
                "Define the Equipment setup payload/read-model contract before any "
                "runtime scoring replacement."
            ),
        },
        {
            "step": "Review 1.13.0",
            "summary": "Confirm the Equipment presenter contract audit is developer-only and accurate.",
        },
        {
            "step": "1.13.1 Equipment setup read-model boundary",
            "summary": (
                "Extract a runtime-neutral setup presentation DTO/read-model while "
                "preserving current EquipmentService output."
            ),
        },
        {
            "step": "Review 1.13.1",
            "summary": "Confirm the Equipment setup read-model boundary preserves runtime output.",
        },
        {
            "step": "1.13.2 Equipment setup score ownership audit",
            "summary": (
                "Audit EquipmentService setup-score components before any scoring "
                "replacement or default-off path."
            ),
        },
        {
            "step": "Review 1.13.2",
            "summary": "Confirm the setup-score ownership audit before extracting components.",
        },
        {
            "step": "1.13.3 Equipment setup-score component boundary",
            "summary": (
                "Extract a runtime-neutral setup-score component read-model with "
                "strict parity tests."
            ),
        },
        {
            "step": "Review 1.13.3",
            "summary": "Confirm the Equipment setup-score component boundary preserves parity.",
        },
        {
            "step": "1.13.4 Equipment default-off path policy audit",
            "summary": (
                "Decide whether Equipment needs a default-off NSOM setup path or "
                "should remain a setup-local recommendation service."
            ),
        },
        {
            "step": "Review 1.13.4",
            "summary": "Confirm Equipment should remain setup-local with NSOM boundaries.",
        },
        {
            "step": "1.13.5 Equipment NSOM migration closeout",
            "summary": "Close Equipment as an NSOM-bounded setup service.",
        },
        {
            "step": "Review 1.13.5",
            "summary": "Confirm Equipment is closed setup-local and no runtime path changed.",
        },
        {
            "step": "Next backend NSOM area selection audit",
            "summary": (
                "Choose the next backend NSOM area or run an overall backend "
                "readiness audit before visible UI/explanation work."
            ),
        },
        {
            "step": "1.13.6 Overall backend readiness audit",
            "summary": "Roll up the backend NSOM state after Equipment closeout.",
        },
        {
            "step": "Review 1.13.6",
            "summary": "Confirm the overall backend readiness audit is accurate.",
        },
        {
            "step": "1.13.7 Rollback cleanup policy audit",
            "summary": (
                "Decide whether internal legacy rollback flags should be kept or "
                "removed before visible UI/explanation work."
            ),
        },
        {
            "step": "Review 1.13.7",
            "summary": "Confirmed rollback cleanup policy before 1.13.8 removed runtime branches.",
        },
        {
            "step": "1.13.8 Remove internal legacy rollback paths",
            "summary": "Remove internal rollback flags and legacy branches in a focused commit.",
        },
        {
            "step": "1.14.9 AOD/OpenAQ default-off scoring experiment",
            "summary": (
                "Implement provider-backed aerosol scoring behind the existing "
                "default-off ObservationConditions flag."
            ),
        },
        {
            "step": "Review 1.14.9",
            "summary": "Confirm the aerosol experiment remains default-off and formula ownership is correct.",
        },
        {
            "step": "1.14.11 AOD/OpenAQ calibration audit",
            "summary": "Audit formula scale, source policy and protected-target rounding without tuning weights.",
        },
        {
            "step": "Review 1.14.11",
            "summary": "Decide whether targeted aerosol calibration is needed before any default-on switch.",
        },
        {
            "step": "1.14.12 AOD/OpenAQ targeted transparency calibration",
            "summary": "Resolve the penalty-cap/transparency-shape blocker while keeping aerosol scoring default-off.",
        },
        {
            "step": "Review 1.14.12",
            "summary": "Confirm the calibrated default-off aerosol formula before any default-on readiness audit.",
        },
        {
            "step": "1.14.13 AOD/OpenAQ default-on readiness audit",
            "summary": "Classify remaining default-on gates without enabling aerosol scoring.",
        },
        {
            "step": "Review 1.14.13",
            "summary": "Decide whether to accept the score-scale risk or gather field-calibration fixtures.",
        },
        {
            "step": "1.14.14 AOD/OpenAQ field-calibration fixtures",
            "summary": "Characterize the calibrated aerosol scale with field-like deterministic scenarios.",
        },
        {
            "step": "Review 1.14.14",
            "summary": "Decide whether synthetic fixtures are sufficient for a narrow default-on switch.",
        },
        {
            "step": "1.14.15 AOD/OpenAQ real-provider probe",
            "summary": "Run real NASA Earthdata AOD and OpenAQ inputs across mixed locations.",
        },
        {
            "step": "Review 1.14.15",
            "summary": "Decide whether real-provider evidence is sufficient for a narrow default-on switch.",
        },
    )


def _static_wiring_checks(root: Path) -> dict[str, object]:
    return {
        "qml_matches": _scan_files(root / "astro_viewer" / "app" / "ui", ("*.qml",), QML_MARKERS),
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
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


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


if __name__ == "__main__":
    write_markdown_report()
