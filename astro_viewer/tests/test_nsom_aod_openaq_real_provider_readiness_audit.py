from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionFeatureFlags,
)
from astro_viewer.tools.nsom_aod_openaq_real_provider_readiness_audit import (
    REPORT_PATH,
    generate_aod_openaq_real_provider_readiness_audit_data,
    render_markdown_report,
)


def test_real_provider_readiness_audit_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_aod_openaq_real_provider_readiness_audit_data()
    second = generate_aod_openaq_real_provider_readiness_audit_data()

    assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
        second,
        sort_keys=True,
        allow_nan=False,
    )
    assert first["metadata"]["developer_only"] is True
    assert first["metadata"]["runtime_writes"] is False
    assert first["metadata"]["automatic_logging"] is False
    assert first["metadata"]["network"] is False
    assert first["metadata"]["qml_exposure"] is False
    assert first["metadata"]["runtime_behaviour_changed_by_this_audit"] is False
    assert first["readiness"]["feature_flag_change_in_this_audit"] is False
    assert first["checks"]["strict_json_compatible"] is True


def test_real_provider_readiness_audit_parses_expanded_provider_evidence() -> None:
    data = generate_aod_openaq_real_provider_readiness_audit_data()
    summary = data["evidence_summary"]

    assert summary["location_set"] == "expanded"
    assert summary["location_count"] == 15
    assert summary["policy_source_counts"] == {
        "aod": 8,
        "none": 2,
        "particulate": 5,
    }
    assert summary["nasa_aod_status_counts"] == {
        "download_error": 1,
        "no_valid_pixel": 2,
        "ok": 12,
    }
    assert summary["openaq_status_counts"] == {
        "historical": 5,
        "ok": 7,
        "unavailable": 3,
    }
    assert summary["aod_freshness_counts"] == {"none": 3, "stale": 12}
    assert summary["particulate_freshness_counts"] == {"current": 7, "none": 8}
    assert summary["all_policy_sources_observed"] is True
    assert summary["zero_effect_provider_locations"] == [
        "San Pedro de Atacama, Chile",
        "Mauna Kea, USA",
        "Cairo, Egypt",
        "Los Angeles, USA",
        "Cape Town, South Africa",
        "Reykjavik, Iceland",
    ]
    assert len(summary["penalty_effect_locations"]) == 7


def test_real_provider_readiness_resolves_score_scale_but_blocks_default_on_for_temporal_evidence() -> None:
    data = generate_aod_openaq_real_provider_readiness_audit_data()
    gates = {gate["gate"]: gate for gate in data["readiness_gates"]}

    assert ObservationConditionFeatureFlags().experimental_aerosol_scoring is False
    assert data["readiness"]["verdict"] == (
        "aod_openaq_default_on_deferred_for_temporal_provider_evidence"
    )
    assert data["readiness"]["ready_for_default_on"] is False
    assert data["readiness"]["default_runtime_score_effect"] == 0.0
    assert data["blockers"] == [
        "aod_current_coverage_absent",
        "single_snapshot_repeatability",
    ]
    assert gates["real_provider_score_scale"]["status"] == "accepted"
    assert gates["real_provider_score_scale"]["blocks_default_on"] is False
    assert gates["aod_current_coverage_absent"]["status"] == "review"
    assert gates["aod_current_coverage_absent"]["blocks_default_on"] is True
    assert gates["single_snapshot_repeatability"]["status"] == "review"
    assert gates["single_snapshot_repeatability"]["blocks_default_on"] is True
    assert data["checks"]["score_scale_resolved_by_real_provider_probe"] is True
    assert data["checks"]["has_no_current_aod_input"] is True
    assert data["checks"]["temporal_evidence_still_blocks_default_on"] is True
    assert data["checks"]["ready_for_default_on_is_false"] is True


def test_real_provider_readiness_accepts_source_policy_and_zero_effect_cases() -> None:
    data = generate_aod_openaq_real_provider_readiness_audit_data()
    gates = {gate["gate"]: gate for gate in data["readiness_gates"]}

    assert gates["expanded_real_provider_coverage"]["status"] == "accepted"
    assert gates["policy_branch_coverage"]["status"] == "accepted"
    assert gates["provider_rejection_and_fallback_policy"]["status"] == "accepted"
    assert gates["zero_effect_provider_success"]["status"] == "accepted"
    assert gates["credential_and_runtime_safety"]["status"] == "accepted"
    assert data["checks"]["default_runtime_neutral"] is True
    assert data["checks"]["all_policy_sources_observed"] is True
    assert data["checks"]["zero_effect_provider_success_observed"] is True
    assert data["checks"]["rejection_and_fallback_observed"] is True
    assert data["checks"]["confidence_neutral_notes_present"] is True


def test_real_provider_readiness_has_no_runtime_or_qml_wiring() -> None:
    data = generate_aod_openaq_real_provider_readiness_audit_data()

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["static_wiring_checks"]["runtime_report_import_matches"] == []
    assert data["static_wiring_checks"]["qml_report_exposure_matches"] == []


def test_checked_in_real_provider_readiness_audit_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM AOD/OpenAQ Real-Provider Readiness Audit" in text
    assert "aod_openaq_default_on_deferred_for_temporal_provider_evidence" in text
    assert "Ready for default-on: `False`" in text
    assert "aod_current_coverage_absent" in text
    assert "single_snapshot_repeatability" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")
