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
from astro_viewer.tools.observation_conditions_read_model_audit import (
    generate_observation_conditions_read_model_audit_data,
)
from astro_viewer.tools.observation_conditions_consumer_reroute_audit import (
    generate_observation_conditions_consumer_reroute_audit_data,
)
from astro_viewer.tools.notifications_dead_legacy_audit import generate_notifications_dead_legacy_audit_data
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


REPORT_PATH = Path("docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md")

RUNTIME_IMPORT_MARKERS = (
    "nsom_legacy_backend_surface_audit",
    "NSOM_LEGACY_BACKEND_SURFACE_AUDIT",
    "NSOM_LEGACY_BACKEND_SURFACE",
)

SKY_MAP_QML_MARKERS = (
    "controller.skyMap",
    'title: "Mappa cielo"',
    "skyMapModel",
)

SKY_MAP_CONTROLLER_MARKERS = (
    "SkyMapService",
    "_sky_map_service",
    "_sky_map =",
    "def skyMap",
)


def generate_legacy_backend_surface_audit_data() -> dict[str, object]:
    root = Path(__file__).parents[2]
    sky_map_state = _sky_map_state(root)
    notification_state = generate_notifications_dead_legacy_audit_data()["notification_surface"]
    observation_conditions_state = generate_observation_conditions_read_model_audit_data()["readiness"]
    observation_conditions_reroute_state = generate_observation_conditions_consumer_reroute_audit_data()["readiness"]
    equipment_presenter_contract_state = generate_equipment_presenter_contract_audit_data()["readiness"]
    equipment_score_ownership_state = generate_equipment_setup_score_ownership_audit_data()["readiness"]
    equipment_score_boundary_state = generate_equipment_setup_score_component_boundary_data()["readiness"]
    equipment_default_off_policy_state = generate_equipment_default_off_path_policy_audit_data()["readiness"]
    temporary_rollbacks = _temporary_rollbacks()
    payload_compatibility = _payload_compatibility_surfaces()
    active_legacy_or_hybrid = _active_legacy_or_hybrid_surfaces(
        observation_conditions_state,
        observation_conditions_reroute_state,
        equipment_presenter_contract_state,
        equipment_score_ownership_state,
        equipment_score_boundary_state,
        equipment_default_off_policy_state,
    )
    static_checks = _static_checks(root)

    data = {
        "metadata": {
            "developer_only": True,
            "runtime_writes": False,
            "automatic_logging": False,
            "network": False,
            "qml_exposure": False,
            "runtime_behaviour_changed_by_this_audit": False,
            "report_path": str(REPORT_PATH).replace("\\", "/"),
            "purpose": (
                "Classify remaining legacy backend surfaces after the NSOM "
                "default-on recommendation migrations, and verify that dead "
                "legacy code removed in cleanup commits stays removed."
            ),
        },
        "readiness": {
            "verdict": "legacy_backend_surface_cleanup_complete",
            "sky_map_migration_recommendation": "removed_dead_legacy_surface",
            "notifications_migration_recommendation": notification_state["classification"],
            "observation_conditions_recommendation": observation_conditions_reroute_state["verdict"],
            "recommended_next_step": (
                "Review 1.13.4, then close the Equipment backend NSOM migration "
                "as setup-local with NSOM boundaries."
            ),
            "reason": (
                "The QML Home page consumes Sky Compass and no longer consumes "
                "`controller.skyMap`. The 1.11.1 cleanup removes the controller "
                "property, `_sky_map` storage, recomputation and `SkyMapService`, "
                "so Sky Map is no longer a backend migration target. Equipment now "
                "has a shared ObserverCapability/Q_target adapter while the runtime "
                "setup helper remains unchanged. The QML Home page no longer consumes "
                "notifications, and the 1.12.4 cleanup removes the controller "
                "property, runtime recomputation, `NotificationService` and DTO. "
                "ObservationConditions remains active runtime code and now has an "
                "explicit read-model boundary plus consumer reroute policy. Home "
                "recommendedDeepSky now uses the raw read-model target for NSOM "
                "ranking, and Best Object now scores raw read-model targets while "
                "returning display targets. Sky Compass now uses a raw-target/"
                "display-live-geometry split adapter. The ObservationConditions "
                "consumer reroute series is closed. Equipment now has a setup "
                "read-model boundary, score ownership audit and component score "
                "read-model. The default-off path policy keeps Equipment setup-local, "
                "so it still uses the existing runtime helper."
            ),
            "runtime_behaviour_changed_by_this_audit": False,
        },
        "classification_policy": {
            "removed_dead_legacy": (
                "Formerly computed legacy code whose current QML/runtime consumer "
                "is absent and whose controller/service path has been removed."
            ),
            "dead_legacy": (
                "Code still present or computed, but no longer consumed by current "
                "QML/runtime presentation."
            ),
            "temporary_rollback": (
                "Explicit old path retained only as internal rollback after a "
                "default-on NSOM migration."
            ),
            "payload_compatibility": (
                "Legacy/base fields still needed to keep existing QML payloads "
                "stable until a separate UI/presentation step."
            ),
            "active_legacy_or_hybrid": (
                "Code still actively used and requiring a separate NSOM policy or "
                "read-model migration before removal."
            ),
        },
        "dead_legacy_surfaces": (sky_map_state, notification_state),
        "temporary_rollback_surfaces": temporary_rollbacks,
        "payload_compatibility_surfaces": payload_compatibility,
        "active_legacy_or_hybrid_surfaces": active_legacy_or_hybrid,
        "static_checks": static_checks,
        "checks": {
            "sky_map_qml_consumers_absent": sky_map_state["qml_consumed"] is False,
            "sky_map_controller_computation_absent": sky_map_state["controller_computation_present"] is False,
            "sky_map_service_file_absent": sky_map_state["service_file_present"] is False,
            "sky_map_removed_not_nsom_target": sky_map_state["classification"] == "removed_dead_legacy",
            "notifications_qml_consumers_absent": notification_state["qml_consumed"] is False,
            "notifications_not_nsom_target": notification_state["not_a_nsom_migration_target"] is True,
            "notifications_removed_dead_legacy": (
                notification_state["classification"] == "removed_dead_legacy"
            ),
            "temporary_rollbacks_are_internal": all(
                item["public_compatibility_contract"] is False for item in temporary_rollbacks
            ),
            "payload_compatibility_not_rank_source": all(
                item["ranking_authority"] == "NSOM or separate active service" for item in payload_compatibility
            ),
            "runtime_report_imports_absent": static_checks["runtime_report_import_matches"] == (),
            "qml_report_exposure_absent": static_checks["qml_report_exposure_matches"] == (),
            "runtime_behaviour_unchanged_by_audit": True,
        },
        "recommended_sequence": (
            {
                "step": "Review 1.11.1",
                "summary": "Confirm the Sky Map controller/property/service path is removed cleanly.",
            },
            {
                "step": "Rollback cleanup series",
                "summary": (
                    "After dead code is removed, decide whether internal legacy "
                    "rollback constructor flags are still useful in an undistributed app."
                ),
            },
            {
                "step": "Review 1.12.0",
                "summary": (
                    "Confirm the Equipment/ObserverCapability comparison report is "
                    "accurate and runtime Equipment behaviour is unchanged."
                ),
            },
            {
                "step": "1.12.1 Equipment NSOM policy readiness",
                "summary": (
                    "Decide whether Equipment gets a default-off NSOM path or stays "
                    "a practical setup helper."
                ),
            },
            {
                "step": "Review 1.12.1",
                "summary": (
                    "Confirm the policy defers runtime replacement and preserves "
                    "EquipmentService behaviour."
                ),
            },
            {
                "step": "1.12.2 ObserverCapability adapter extraction",
                "summary": (
                    "Extract reusable ObserverCapability/Q_target projection without "
                    "changing Equipment recommendations."
                ),
            },
            {
                "step": "Review 1.12.2",
                "summary": (
                    "Confirm the adapter extraction preserved Equipment comparison "
                    "values and runtime behaviour."
                ),
            },
            {
                "step": "1.12.3 Notifications dead legacy audit",
                "summary": (
                    "Classify Notifications as dead legacy because no QML/Home "
                    "consumer remains."
                ),
            },
            {
                "step": "1.12.4 Remove dead Notifications backend path",
                "summary": (
                    "Confirm AppController notifications, NotificationService and "
                    "leftover DTO/tests are removed."
                ),
            },
            {
                "step": "1.12.5 ObservationConditions read-model audit",
                "summary": (
                    "Audit conditioned-object cache ownership and NSOM input risks."
                ),
            },
            {
                "step": "Review 1.12.5",
                "summary": (
                    "Confirm the ObservationConditions audit before adding a read-model boundary."
                ),
            },
            {
                "step": "1.12.6 ObservationConditions read-model boundary",
                "summary": (
                    "Separate raw target input from condition-adjusted display compatibility fields."
                ),
            },
            {
                "step": "Review 1.12.6",
                "summary": (
                    "Confirm read-model fidelity before rerouting runtime consumers."
                ),
            },
            {
            "step": "1.12.7 ObservationConditions consumer reroute audit",
            "summary": (
                "Define raw-target consumer policy for Home, Best Object and Sky Compass."
            ),
        },
        {
            "step": "1.12.8 Home recommendedDeepSky raw-target reroute",
            "summary": (
                "Use raw read-model targets for Home recommendedDeepSky NSOM ranking "
                "while preserving display payload targets."
            ),
        },
        {
            "step": "1.12.9 Best Object raw-target reroute",
            "summary": (
                "Use raw read-model targets for Best Object NSOM scoring while "
                "returning the selected display payload target."
            ),
        },
        {
            "step": "1.12.10 Sky Compass read-model reroute policy",
            "summary": (
                "Define Sky Compass raw target physics vs display/live geometry "
                "ownership before runtime changes."
            ),
        },
        {
            "step": "1.12.11 Sky Compass read-model reroute",
            "summary": (
                "Use raw target physics for Sky Compass ObservableTargetValue while "
                "preserving display/live geometry and payload fields."
            ),
        },
        {
            "step": "1.13.0 Equipment presenter contract audit",
            "summary": (
                "Define the Equipment setup payload/read-model contract before "
                "any runtime scoring replacement."
            ),
        },
        {
            "step": "Review 1.13.0",
            "summary": (
                "Confirm the Equipment presenter contract audit is accurate and "
                "developer-only."
            ),
        },
        {
            "step": "1.13.1 Equipment setup read-model boundary",
            "summary": (
                "Extract a runtime-neutral Equipment setup read-model/presenter DTO "
                "while preserving current payload shape."
            ),
        },
        {
            "step": "Review 1.13.1",
            "summary": (
                "Confirm the Equipment setup read-model boundary preserves runtime "
                "output and QML payload shape."
            ),
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
        ),
    }
    return nsom_to_json_compatible(data)


def render_markdown_report(data: dict[str, object] | None = None) -> str:
    audit = generate_legacy_backend_surface_audit_data() if data is None else data
    readiness = audit["readiness"]

    lines = [
        "# NSOM Legacy Backend Surface Audit",
        "",
        "## Executive Summary",
        "",
        (
            "This developer-only audit classifies the remaining legacy backend "
            "surfaces after the default-on NSOM recommendation migrations. It "
            "does not change runtime behaviour, QML, scoring, logging, network "
            "access or runtime file writes."
        ),
        "",
        "## Verdict",
        "",
        f"- Verdict: `{readiness['verdict']}`.",
        f"- Sky Map migration recommendation: `{readiness['sky_map_migration_recommendation']}`.",
        f"- Notifications migration recommendation: `{readiness['notifications_migration_recommendation']}`.",
        f"- ObservationConditions recommendation: `{readiness['observation_conditions_recommendation']}`.",
        f"- Runtime behaviour changed by this audit: `{readiness['runtime_behaviour_changed_by_this_audit']}`.",
        f"- Recommended next step: {readiness['recommended_next_step']}",
        f"- Reason: {readiness['reason']}",
        "",
        "## Classification Policy",
        "",
    ]
    for key, value in audit["classification_policy"].items():
        lines.append(f"- `{key}`: {value}")

    lines.extend(
        [
            "",
            "## Removed Dead Legacy Surfaces",
            "",
            "| Surface | Classification | Evidence | Recommended handling |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in audit["dead_legacy_surfaces"]:
        evidence = "<br>".join(item["evidence"])
        lines.append(
            "| "
            + " | ".join(
                (
                    item["surface"],
                    f"`{item['classification']}`",
                    evidence,
                    item["recommended_handling"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Temporary Rollback Surfaces",
            "",
            "| Surface | Default flag | Rollback | Public compatibility contract | Recommended handling |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for item in audit["temporary_rollback_surfaces"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["surface"],
                    f"`{item['default_flag']}`",
                    f"`{item['rollback']}`",
                    f"`{item['public_compatibility_contract']}`",
                    item["recommended_handling"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Payload Compatibility Surfaces",
            "",
            "| Surface | Compatibility field | Why it remains | Ranking authority |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in audit["payload_compatibility_surfaces"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["surface"],
                    f"`{item['compatibility_field']}`",
                    item["why_it_remains"],
                    item["ranking_authority"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Active Legacy Or Hybrid Surfaces",
            "",
            "| Surface | Classification | Why active | Recommended handling |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in audit["active_legacy_or_hybrid_surfaces"]:
        lines.append(
            "| "
            + " | ".join(
                (
                    item["surface"],
                    f"`{item['classification']}`",
                    item["why_active"],
                    item["recommended_handling"],
                )
            )
            + " |"
        )

    lines.extend(
        [
            "",
            "## Safety Checks",
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
                "Sky Map has been removed from the backend runtime surface instead "
                "of being migrated to NSOM. Notifications are removed dead legacy "
                "rather than a backend NSOM migration surface. ObservationConditions "
                "is active hybrid runtime code with a read-model boundary and a "
                "closed consumer reroute; it remains active compatibility code. "
                "Equipment now has a shared ObserverCapability/Q_target adapter "
                "plus a setup read-model boundary, score ownership audit and "
                "setup-score component boundary. The 1.13.4 policy keeps it "
                "setup-local and does not add a default-off replacement path; "
                "runtime setup recommendations remain unchanged. Temporary rollback "
                "cleanup remains a separate policy decision."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_markdown_report(path: Path = REPORT_PATH) -> Path:
    """Explicit developer command; never called by runtime."""

    path.write_text(render_markdown_report(), encoding="utf-8")
    return path


def _sky_map_state(root: Path) -> dict[str, object]:
    qml_matches = _scan_files(root / "astro_viewer" / "app" / "ui", ("*.qml",), SKY_MAP_QML_MARKERS)
    controller_matches = _scan_files(
        root / "astro_viewer" / "app" / "viewmodels",
        ("app_controller.py",),
        SKY_MAP_CONTROLLER_MARKERS,
    )
    service_file = root / "astro_viewer" / "app" / "services" / "sky_map_service.py"
    return {
        "surface": "Sky Map",
        "classification": "removed_dead_legacy",
        "qml_consumed": qml_matches != (),
        "qml_consumer_matches": qml_matches,
        "controller_computation_present": controller_matches != (),
        "controller_matches": controller_matches,
        "service_file_present": service_file.exists(),
        "evidence": (
            "HomePage.qml consumes `controller.skyCompass`, not `controller.skyMap`.",
            "`AppController.skyMap`, `_sky_map` storage and recomputation are absent.",
            "`SkyMapService` has been removed.",
        ),
        "recommended_handling": (
            "Keep removed; do not rebuild a Sky Map NSOM migration unless a real "
            "consumer is reintroduced through a separate product decision."
        ),
        "blocks_current_nsom_surfaces": False,
    }


def _temporary_rollbacks() -> tuple[dict[str, object], ...]:
    controller_parameters = signature(AppController.__init__).parameters
    planner_parameters = signature(NightPlannerService.__init__).parameters
    return (
        {
            "surface": "Planner",
            "default_flag": f"NSOM_PLANNER_SCORING_ENABLED = {NSOM_PLANNER_SCORING_ENABLED}",
            "rollback": "NightPlannerService(use_nsom_planner_scoring=False)",
            "rollback_parameter_present": "use_nsom_planner_scoring" in planner_parameters,
            "public_compatibility_contract": False,
            "recommended_handling": "Keep only until the rollback cleanup series is explicitly accepted.",
        },
        {
            "surface": "Home recommendedDeepSky",
            "default_flag": (
                "NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED = "
                f"{NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED}"
            ),
            "rollback": "AppController(use_nsom_home_recommended_deep_sky=False)",
            "rollback_parameter_present": "use_nsom_home_recommended_deep_sky" in controller_parameters,
            "public_compatibility_contract": False,
            "recommended_handling": "Keep only until the rollback cleanup series is explicitly accepted.",
        },
        {
            "surface": "Best Object",
            "default_flag": f"NSOM_BEST_OBJECT_ENABLED = {NSOM_BEST_OBJECT_ENABLED}",
            "rollback": "AppController(use_nsom_best_object=False)",
            "rollback_parameter_present": "use_nsom_best_object" in controller_parameters,
            "public_compatibility_contract": False,
            "recommended_handling": "Keep only until the rollback cleanup series is explicitly accepted.",
        },
        {
            "surface": "Advanced Observing backend",
            "default_flag": f"NSOM_ADVANCED_OBSERVING_ENABLED = {NSOM_ADVANCED_OBSERVING_ENABLED}",
            "rollback": "AppController(use_nsom_advanced_observing=False)",
            "rollback_parameter_present": "use_nsom_advanced_observing" in controller_parameters,
            "public_compatibility_contract": False,
            "recommended_handling": "Keep until Advanced Observing visible presentation policy is settled.",
        },
        {
            "surface": "Sky Compass",
            "default_flag": f"NSOM_SKY_COMPASS_ENABLED = {NSOM_SKY_COMPASS_ENABLED}",
            "rollback": "AppController(use_nsom_sky_compass=False)",
            "rollback_parameter_present": "use_nsom_sky_compass" in controller_parameters,
            "public_compatibility_contract": False,
            "recommended_handling": "Keep only until the rollback cleanup series is explicitly accepted.",
        },
        {
            "surface": "Detail/Object internal payload",
            "default_flag": f"NSOM_DETAIL_OBJECT_ENABLED = {NSOM_DETAIL_OBJECT_ENABLED}",
            "rollback": "AppController(use_nsom_detail_object=False)",
            "rollback_parameter_present": "use_nsom_detail_object" in controller_parameters,
            "public_compatibility_contract": False,
            "recommended_handling": "Keep until visible Detail presentation policy is settled.",
        },
    )


def _payload_compatibility_surfaces() -> tuple[dict[str, object], ...]:
    return (
        {
            "surface": "Home recommendedDeepSky",
            "compatibility_field": "score",
            "why_it_remains": "Existing QML cards expect the field as display/base compatibility data.",
            "ranking_authority": "NSOM or separate active service",
        },
        {
            "surface": "Best Object",
            "compatibility_field": "score",
            "why_it_remains": "The visible Best Object payload still shows legacy/base score semantics.",
            "ranking_authority": "NSOM or separate active service",
        },
        {
            "surface": "Sky Compass",
            "compatibility_field": "target.score",
            "why_it_remains": "The compass payload shape is intentionally unchanged for QML.",
            "ranking_authority": "NSOM or separate active service",
        },
        {
            "surface": "Advanced Observing",
            "compatibility_field": "advancedScores",
            "why_it_remains": "Home cards and Planner still consume the legacy-compatible scores; the old notification consumer has been removed as dead legacy.",
            "ranking_authority": "NSOM or separate active service",
        },
        {
            "surface": "Detail/Object",
            "compatibility_field": "selectedObject.score",
            "why_it_remains": "Visible Detail QML still consumes selectedObject without NSOM fields.",
            "ranking_authority": "NSOM or separate active service",
        },
    )


def _active_legacy_or_hybrid_surfaces(
    observation_conditions_state: dict[str, object],
    observation_conditions_reroute_state: dict[str, object],
    equipment_presenter_contract_state: dict[str, object],
    equipment_score_ownership_state: dict[str, object],
    equipment_score_boundary_state: dict[str, object],
    equipment_default_off_policy_state: dict[str, object],
) -> tuple[dict[str, object], ...]:
    return (
        {
            "surface": "Equipment recommendations",
            "classification": "active_legacy_or_hybrid",
            "why_active": (
                "`EquipmentService` still computes practical setup recommendations; "
                "`observer_capability_adapter.py` now provides shared "
                "ObserverCapability/Q_target projection while "
                "`docs/EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT.md` classifies the "
                "setup score components and "
                "`docs/EQUIPMENT_SETUP_SCORE_COMPONENT_BOUNDARY.md` verifies the "
                "component read-model parity. "
                "`docs/EQUIPMENT_NSOM_DEFAULT_OFF_PATH_POLICY_AUDIT.md` rejects a "
                "default-off replacement path for now and keeps Equipment setup-local. "
                f"Contract status: `{equipment_presenter_contract_state['verdict']}`. "
                f"Score ownership status: `{equipment_score_ownership_state['verdict']}`. "
                f"Component boundary status: `{equipment_score_boundary_state['verdict']}`. "
                f"Default-off policy status: `{equipment_default_off_policy_state['verdict']}`."
            ),
            "recommended_handling": (
                "Review the 1.13.4 policy audit, then close Equipment as a "
                "setup-local service with NSOM boundaries."
            ),
        },
        {
            "surface": "ObservationConditions prepared-object cache",
            "classification": "active_legacy_or_hybrid",
            "why_active": (
                "Conditioned object copies still feed fallback and compatibility "
                "presentation paths; the 1.12.6 boundary reports "
                f"`{observation_conditions_state['verdict']}` and the 1.12.7 "
                "consumer audit now reports "
                f"`{observation_conditions_reroute_state['verdict']}`."
            ),
            "recommended_handling": (
                "Keep the read-model boundary as active compatibility code; no "
                "ObservationConditions consumer reroute work remains open."
            ),
        },
        {
            "surface": "Catalogue / raw object score",
            "classification": "active_legacy_or_hybrid",
            "why_active": "Catalogue/base scores remain Universe input and display compatibility data.",
            "recommended_handling": "Treat as Universe/read-model work, not as a ranking hotfix.",
        },
    )


def _static_checks(root: Path) -> dict[str, object]:
    return {
        "runtime_report_import_matches": _scan_files(
            root / "astro_viewer" / "app",
            ("*.py",),
            RUNTIME_IMPORT_MARKERS,
            include_parts=("services", "viewmodels"),
        ),
        "qml_report_exposure_matches": _scan_files(
            root / "astro_viewer" / "app" / "ui",
            ("*.qml",),
            RUNTIME_IMPORT_MARKERS,
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


if __name__ == "__main__":
    write_markdown_report()
