from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.tools.nsom_backend_migration_status_audit import (
    REPORT_PATH,
    generate_backend_migration_status_audit_data,
    render_markdown_report,
)


def test_backend_migration_status_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_backend_migration_status_audit_data()
    second = generate_backend_migration_status_audit_data()

    first_json = json.dumps(first, sort_keys=True, allow_nan=False)
    second_json = json.dumps(second, sort_keys=True, allow_nan=False)

    assert first_json == second_json
    assert first["metadata"] == {
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
        "report_path": "docs/NSOM_BACKEND_MIGRATION_STATUS_AUDIT.md",
        "source_reports": [
            "docs/NSOM_PLANNER_DEFAULT_ON_READINESS_AUDIT.md",
            "docs/HOME_NSOM_RECOMMENDED_DEEP_SKY_READINESS_AUDIT.md",
            "docs/BEST_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
            "docs/ADVANCED_OBSERVING_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
            "docs/SKY_COMPASS_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
            "docs/DETAIL_OBJECT_NSOM_DEFAULT_ON_READINESS_AUDIT.md",
            "docs/DETAIL_OBJECT_NSOM_MIGRATION_CLOSEOUT.md",
            "docs/NSOM_LEGACY_BACKEND_SURFACE_AUDIT.md",
            "docs/NOTIFICATIONS_DEAD_LEGACY_AUDIT.md",
            "docs/OBSERVATION_CONDITIONS_READ_MODEL_AUDIT.md",
            "docs/OBSERVATION_CONDITIONS_CONSUMER_REROUTE_AUDIT.md",
            "docs/SKY_COMPASS_READ_MODEL_REROUTE_POLICY.md",
            "docs/EQUIPMENT_NSOM_COMPARISON_REPORT.md",
            "docs/EQUIPMENT_NSOM_POLICY_READINESS.md",
            "docs/EQUIPMENT_NSOM_PRESENTER_CONTRACT_AUDIT.md",
            "docs/EQUIPMENT_SETUP_SCORE_OWNERSHIP_AUDIT.md",
            "docs/EQUIPMENT_SETUP_SCORE_COMPONENT_BOUNDARY.md",
            "docs/EQUIPMENT_NSOM_DEFAULT_OFF_PATH_POLICY_AUDIT.md",
            "docs/EQUIPMENT_NSOM_MIGRATION_CLOSEOUT.md",
            "docs/NSOM_ROLLBACK_CLEANUP_POLICY_AUDIT.md",
            "docs/NSOM_MOON_GEOMETRY_PLANNER_CALIBRATION.md",
            "docs/NSOM_MOON_GEOMETRY_PLANNER_DEFAULT_ON_READINESS.md",
            "docs/NSOM_AOD_OPENAQ_SCORING_READINESS.md",
            "docs/NSOM_AOD_OPENAQ_PROVIDER_QUALITY_POLICY.md",
            "docs/NSOM_AOD_OPENAQ_DEFAULT_OFF_SCORING_EXPERIMENT.md",
            "docs/NSOM_AOD_OPENAQ_CALIBRATION_AUDIT.md",
            "docs/NSOM_AOD_OPENAQ_DEFAULT_ON_READINESS.md",
            "docs/NSOM_AOD_OPENAQ_FIELD_CALIBRATION.md",
            "docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_PROBE.md",
            "docs/NSOM_AOD_OPENAQ_REAL_PROVIDER_READINESS_AUDIT.md",
            "docs/NSOM_AOD_OPENAQ_STALE_CURRENT_REPLAY_AUDIT.md",
        ],
    }


def test_audit_confirms_default_on_surfaces_and_removed_rollbacks() -> None:
    data = generate_backend_migration_status_audit_data()
    surfaces = {surface["surface"]: surface for surface in data["default_on_surfaces"]}

    assert data["readiness"]["verdict"] == "backend_nsom_default_on_surfaces_closed"
    assert data["readiness"]["all_current_default_on_surfaces_closed"] is True
    assert data["readiness"]["runtime_behaviour_changed_by_this_audit"] is False
    assert data["blockers"] == []
    assert data["checks"]["all_default_flags_enabled"] is True
    assert data["checks"]["all_internal_rollback_paths_removed"] is True
    assert data["checks"]["all_rollback_records_mark_removed"] is True

    assert surfaces["Planner"]["default_flag"] == "NSOM_PLANNER_SCORING_ENABLED = True"
    assert surfaces["Planner"]["rollback"] == "removed: NightPlannerService(use_nsom_planner_scoring=False)"
    assert surfaces["Planner"]["rollback_parameter_present"] is False
    assert surfaces["Home recommendedDeepSky"]["rollback"] == (
        "removed: AppController(use_nsom_home_recommended_deep_sky=False)"
    )
    assert surfaces["Home recommendedDeepSky"]["rollback_parameter_present"] is False
    assert surfaces["Best Object"]["rollback"] == "removed: AppController(use_nsom_best_object=False)"
    assert surfaces["Best Object"]["rollback_parameter_present"] is False
    assert surfaces["Advanced Observing backend"]["rollback"] == (
        "removed: AppController(use_nsom_advanced_observing=False)"
    )
    assert surfaces["Advanced Observing backend"]["rollback_parameter_present"] is False
    assert surfaces["Sky Compass"]["rollback"] == "removed: AppController(use_nsom_sky_compass=False)"
    assert surfaces["Sky Compass"]["rollback_parameter_present"] is False
    assert surfaces["Detail/Object internal payload"]["default_flag"] == "NSOM_DETAIL_OBJECT_ENABLED = True"
    assert surfaces["Detail/Object internal payload"]["rollback"] == "removed: AppController(use_nsom_detail_object=False)"
    assert surfaces["Detail/Object internal payload"]["rollback_parameter_present"] is False
    assert all(
        surface["rollback_status"] == "removed_internal_runtime_rollback"
        for surface in surfaces.values()
    )
    assert all(surface["confidence_score_neutral"] is True for surface in surfaces.values())


def test_audit_identifies_remaining_non_blocking_legacy_or_hybrid_surfaces() -> None:
    data = generate_backend_migration_status_audit_data()
    remaining = {item["area"]: item for item in data["remaining_non_blocking_items"]}

    assert data["checks"]["remaining_surfaces_are_non_blocking"] is True
    assert set(remaining) == {
        "Equipment recommendations",
        "ObservationConditions prepared-object cache",
        "Catalogue / raw object score",
    }
    assert remaining["Equipment recommendations"]["status"] == (
        "equipment_nsom_migration_closed_setup_local"
    )
    assert remaining["Equipment recommendations"]["ownership_status"] == "equipment_setup_score_ownership_audited"
    assert remaining["Equipment recommendations"]["boundary_status"] == (
        "equipment_setup_score_component_boundary_introduced"
    )
    assert remaining["Equipment recommendations"]["default_off_policy_status"] == (
        "equipment_default_off_path_policy_set_setup_local"
    )
    assert remaining["Equipment recommendations"]["closeout_status"] == (
        "equipment_nsom_migration_closed_setup_local"
    )
    assert remaining["ObservationConditions prepared-object cache"]["status"] == (
        "observation_conditions_consumer_reroute_closed"
    )
    assert "no ObservationConditions consumer reroute work remains open" in remaining[
        "ObservationConditions prepared-object cache"
    ]["recommended_handling"]
    assert data["notification_audit"]["classification"] == "removed_dead_legacy"
    assert data["observation_conditions_audit"]["verdict"] == (
        "read_model_boundary_introduced_consumer_reroute_pending"
    )
    assert data["observation_conditions_consumer_reroute_audit"]["verdict"] == (
        "observation_conditions_consumer_reroute_closed"
    )
    assert "observer_capability_adapter.py" in remaining["Equipment recommendations"]["why_it_remains"]
    assert "setup-local service" in remaining["Equipment recommendations"]["recommended_handling"]
    assert all(item["blocks_current_default_on_surfaces"] is False for item in remaining.values())


def test_audit_recommends_equipment_after_sky_map_removal() -> None:
    data = generate_backend_migration_status_audit_data()
    sequence = [item["step"] for item in data["recommended_sequence"]]

    assert data["readiness"]["ready_to_start_next_backend_area"] is True
    assert data["readiness"]["ready_for_visible_ui_redesign"] is False
    assert data["readiness"]["recommended_next_step"] == (
        "Review 1.14.18 AOD/OpenAQ stale-vs-current replay, then "
        "decide whether to implement a narrow default-on switch"
    )
    assert data["equipment_policy"]["ready_for_observer_capability_adapter_step"] is True
    assert data["equipment_policy"]["observer_capability_adapter_extracted"] is True
    assert data["equipment_presenter_contract"]["verdict"] == "equipment_setup_read_model_boundary_introduced"
    assert data["equipment_presenter_contract"]["presenter_contract_audited"] is True
    assert data["equipment_presenter_contract"]["runtime_read_model_boundary_present"] is True
    assert data["equipment_presenter_contract"]["runtime_replacement_ready"] is False
    assert data["equipment_score_ownership"]["verdict"] == "equipment_setup_score_ownership_audited"
    assert data["equipment_score_ownership"]["score_component_boundary_recommended"] is True
    assert data["equipment_score_boundary"]["verdict"] == (
        "equipment_setup_score_component_boundary_introduced"
    )
    assert data["equipment_score_boundary"]["component_read_model_present"] is True
    assert data["equipment_score_boundary"]["runtime_replacement_ready"] is False
    assert data["equipment_default_off_policy"]["verdict"] == (
        "equipment_default_off_path_policy_set_setup_local"
    )
    assert data["equipment_default_off_policy"]["default_off_equipment_path_recommended_now"] is False
    assert data["equipment_default_off_policy"]["setup_local_service_recommended"] is True
    assert data["equipment_default_off_policy"]["blocks_backend_migration_closeout"] is False
    assert data["equipment_closeout"]["verdict"] == "equipment_nsom_migration_closed_setup_local"
    assert data["equipment_closeout"]["migration_closed"] is True
    assert data["equipment_closeout"]["runtime_behaviour_changed_by_closeout"] is False
    assert data["checks"]["equipment_policy_ready_for_adapter_step"] is True
    assert data["checks"]["equipment_observer_adapter_extracted"] is True
    assert data["checks"]["equipment_presenter_contract_audited"] is True
    assert data["checks"]["equipment_setup_read_model_boundary_present"] is True
    assert data["checks"]["equipment_runtime_replacement_deferred"] is True
    assert data["checks"]["equipment_score_ownership_audited"] is True
    assert data["checks"]["equipment_score_component_boundary_recommended"] is True
    assert data["checks"]["equipment_score_component_boundary_introduced"] is True
    assert data["checks"]["equipment_score_component_boundary_parity_checked"] is True
    assert data["checks"]["equipment_default_off_policy_set"] is True
    assert data["checks"]["equipment_default_off_path_not_recommended_now"] is True
    assert data["checks"]["equipment_setup_local_service_recommended"] is True
    assert data["checks"]["equipment_policy_does_not_block_closeout"] is True
    assert data["checks"]["equipment_migration_closeout_present"] is True
    assert data["checks"]["equipment_migration_closed_setup_local"] is True
    assert data["checks"]["equipment_closeout_does_not_change_runtime"] is True
    assert sequence[:3] == [
        "Review 1.9.7",
        "Review 1.10.6",
        "1.11.0 Legacy backend surface audit",
    ]
    assert sequence[3] == "Review 1.11.1"
    assert sequence[4] == "1.12.0 Equipment/ObserverCapability NSOM comparison"
    assert sequence[5] == "Review 1.12.0"
    assert sequence[6] == "1.12.1 Equipment NSOM policy readiness"
    assert sequence[7] == "Review 1.12.1"
    assert sequence[8] == "1.12.2 ObserverCapability adapter extraction"
    assert sequence[9] == "Review 1.12.2"
    assert sequence[10] == "1.12.3 Notifications dead legacy audit"
    assert sequence[11] == "1.12.4 Remove dead Notifications backend path"
    assert sequence[12] == "1.12.5 ObservationConditions read-model audit"
    assert sequence[13] == "Review 1.12.5"
    assert sequence[14] == "1.12.6 ObservationConditions read-model boundary"
    assert sequence[15] == "Review 1.12.6"
    assert sequence[16] == "1.12.7 ObservationConditions consumer reroute audit"
    assert sequence[17] == "Review 1.12.7"
    assert sequence[18] == "1.12.8 Home recommendedDeepSky raw-target reroute"
    assert sequence[19] == "Review 1.12.8"
    assert sequence[20] == "1.12.9 Best Object raw-target reroute"
    assert sequence[21] == "Review 1.12.9"
    assert sequence[22] == "1.12.10 Sky Compass read-model reroute policy"
    assert sequence[23] == "Review 1.12.10"
    assert sequence[24] == "1.12.11 Sky Compass read-model reroute"
    assert sequence[25] == "Review 1.12.11"
    assert sequence[26] == "1.12.12 ObservationConditions consumer reroute closeout"
    assert sequence[27] == "Next backend area: Equipment presenter contract"
    assert sequence[28] == "1.13.0 Equipment presenter contract audit"
    assert sequence[29] == "Review 1.13.0"
    assert sequence[30] == "1.13.1 Equipment setup read-model boundary"
    assert sequence[31] == "Review 1.13.1"
    assert sequence[32] == "1.13.2 Equipment setup score ownership audit"
    assert sequence[33] == "Review 1.13.2"
    assert sequence[34] == "1.13.3 Equipment setup-score component boundary"
    assert sequence[35] == "Review 1.13.3"
    assert sequence[36] == "1.13.4 Equipment default-off path policy audit"
    assert sequence[37] == "Review 1.13.4"
    assert sequence[38] == "1.13.5 Equipment NSOM migration closeout"
    assert sequence[39] == "Review 1.13.5"
    assert sequence[40] == "Next backend NSOM area selection audit"
    assert sequence[41] == "1.13.6 Overall backend readiness audit"
    assert sequence[42] == "Review 1.13.6"
    assert sequence[43] == "1.13.7 Rollback cleanup policy audit"
    assert sequence[44] == "Review 1.13.7"
    assert sequence[45] == "1.13.8 Remove internal legacy rollback paths"
    assert sequence[46] == "1.14.9 AOD/OpenAQ default-off scoring experiment"
    assert sequence[47] == "Review 1.14.9"
    assert sequence[48] == "1.14.11 AOD/OpenAQ calibration audit"
    assert sequence[49] == "Review 1.14.11"
    assert sequence[50] == "1.14.12 AOD/OpenAQ targeted transparency calibration"
    assert sequence[51] == "Review 1.14.12"
    assert sequence[52] == "1.14.13 AOD/OpenAQ default-on readiness audit"
    assert sequence[53] == "Review 1.14.13"
    assert sequence[54] == "1.14.14 AOD/OpenAQ field-calibration fixtures"
    assert sequence[55] == "Review 1.14.14"
    assert sequence[56] == "1.14.15 AOD/OpenAQ real-provider probe"
    assert sequence[57] == "Review 1.14.15"
    assert sequence[58] == "1.14.16 Expanded AOD/OpenAQ real-provider probe"
    assert sequence[59] == "Review 1.14.16"
    assert sequence[60] == "1.14.17 AOD/OpenAQ real-provider readiness audit"
    assert sequence[61] == "Review 1.14.17"
    assert sequence[62] == "1.14.18 AOD/OpenAQ stale-vs-current replay audit"
    assert sequence[63] == "Review 1.14.18"


def test_audit_has_no_runtime_or_qml_wiring() -> None:
    data = generate_backend_migration_status_audit_data()

    assert data["safety"] == {
        "developer_only": True,
        "runtime_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "runtime_report_imports_absent": True,
        "qml_audit_exposure_absent": True,
        "runtime_behaviour_changed_by_this_audit": False,
    }
    assert data["static_wiring_checks"]["qml_matches"] == []
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []


def test_checked_in_backend_migration_status_audit_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM Backend Migration Status Audit" in text
    assert "backend_nsom_default_on_surfaces_closed" in text
    assert "ObservationConditions Audit" in text
    assert "observation_conditions_consumer_reroute_closed" in text
    assert "equipment_default_off_path_policy_set_setup_local" in text
    assert "equipment_nsom_migration_closed_setup_local" in text
    assert "NSOM_ROLLBACK_CLEANUP_POLICY_AUDIT" in text
    assert "AOD/OpenAQ provider-quality policy is hardened" in text
    assert "1.14.12 calibrates the penalty-cap/transparency shape" in text
    assert "aerosol score-scale validation as the only default-on blocker" in text
    assert "1.14.14 field-calibration fixtures pass" in text
    assert "1.14.15 real-provider probe covers" in text
    assert "1.14.16 expanded real-provider probe covers" in text
    assert "1.14.17 real-provider readiness audit accepts" in text
    assert "1.14.18 stale-vs-current replay accepts" in text
    assert "removed_dead_legacy" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
