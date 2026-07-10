from __future__ import annotations

import json
from pathlib import Path

from astro_viewer.app.services.aerosol_provider_quality_policy import AerosolProviderQualityPolicyService
from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    ObservationConditionFeatureFlags,
    ParticulateConditionInput,
)
from astro_viewer.tools.nsom_aod_openaq_provider_quality_policy import (
    REPORT_PATH,
    generate_aod_openaq_provider_quality_policy_data,
    render_markdown_report,
)


def test_provider_quality_policy_report_is_deterministic_strict_json_and_developer_only() -> None:
    first = generate_aod_openaq_provider_quality_policy_data()
    second = generate_aod_openaq_provider_quality_policy_data()

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
    assert first["readiness"]["ready_for_default_off_experiment"] is True
    assert first["readiness"]["ready_for_default_on"] is False
    assert first["readiness"]["scoring_formula_implemented"] is True
    assert first["readiness"]["scoring_formula_enabled"] is False
    assert first["readiness"]["current_runtime_score_effect"] == 0.0
    assert first["checks"]["strict_json_compatible"] is True


def test_aod_quality_requires_freshness_uncertainty_qa_and_pixel_support() -> None:
    service = AerosolProviderQualityPolicyService()
    good = service.aod_quality(_aod())
    high_uncertainty = service.aod_quality(_aod(uncertainty=0.22))
    missing_qa = service.aod_quality(_aod(qa_raw=None))
    sparse_neighborhood = service.aod_quality(
        _aod(method="local_neighborhood", local_valid_pixel_count=1)
    )
    supported_neighborhood = service.aod_quality(
        _aod(method="local_neighborhood", local_valid_pixel_count=3)
    )

    assert good.eligible_for_future_scoring is True
    assert good.role == "primary_aerosol_column"
    assert good.confidence_weight == 1.0
    assert high_uncertainty.eligible_for_future_scoring is False
    assert "aod_uncertainty_missing_or_high" in high_uncertainty.reasons
    assert missing_qa.eligible_for_future_scoring is False
    assert "aod_qa_raw_missing" in missing_qa.reasons
    assert sparse_neighborhood.eligible_for_future_scoring is False
    assert "aod_local_neighborhood_too_sparse" in sparse_neighborhood.reasons
    assert supported_neighborhood.eligible_for_future_scoring is True


def test_openaq_quality_requires_local_representativeness_for_fallback() -> None:
    service = AerosolProviderQualityPolicyService()
    local = service.particulate_quality(_pm(distance_km=4.0))
    context_only = service.particulate_quality(_pm(distance_km=35.0))
    distant = service.particulate_quality(_pm(distance_km=75.0))
    unknown = service.particulate_quality(_pm(distance_km=None))

    assert local.eligible_for_future_fallback is True
    assert local.role == "fallback_ground_particulate"
    assert local.confidence_weight == 1.0
    assert context_only.eligible_for_future_fallback is False
    assert context_only.locality_weight == 0.5
    assert "openaq_context_distance_not_scoring_representative" in context_only.reasons
    assert distant.eligible_for_future_fallback is False
    assert "openaq_too_distant" in distant.reasons
    assert unknown.eligible_for_future_fallback is False
    assert "openaq_distance_unknown" in unknown.reasons


def test_source_precedence_uses_aod_primary_and_pm_fallback_only() -> None:
    service = AerosolProviderQualityPolicyService()

    assert service.policy(_aod(), _pm(distance_km=4.0)).primary_source == "aod"
    assert service.policy(_aod(uncertainty=0.22), _pm(distance_km=4.0)).primary_source == "particulate"
    assert service.policy(_aod(qa_raw=None), _pm(distance_km=4.0)).primary_source == "particulate"
    assert service.policy(None, _pm(distance_km=4.0)).primary_source == "particulate"
    assert service.policy(None, _pm(distance_km=35.0)).primary_source == "none"
    assert service.policy(None, _pm(distance_km=75.0)).primary_source == "none"


def test_double_counting_policy_and_confidence_are_target_neutral_even_with_flag_on() -> None:
    service = AerosolProviderQualityPolicyService()
    policy = service.policy(
        _aod(),
        _pm(distance_km=4.0),
        ObservationConditionFeatureFlags(experimental_aerosol_scoring=True),
    )

    assert policy.score_modifier == 0.0
    assert policy.scoring_formula_enabled is True
    assert "aod_and_particulate_are_not_additive" in policy.double_counting_rules
    assert "viirs_sky_background_remains_separate" in policy.double_counting_rules
    assert "weather_transparency_remains_separate" in policy.double_counting_rules
    assert "moon_geometry_remains_separate" in policy.double_counting_rules
    assert "provider_quality_does_not_change_target_specific_score" in policy.confidence_notes
    assert "recommendation_confidence_remains_score_neutral" in policy.confidence_notes


def test_provider_quality_policy_report_has_expected_cases_and_no_wiring() -> None:
    data = generate_aod_openaq_provider_quality_policy_data()
    cases = {case["case"]: case["policy"] for case in data["cases"]}

    assert data["checks"]["runtime_report_imports_absent"] is True
    assert data["checks"]["qml_report_exposure_absent"] is True
    assert data["checks"]["fresh_aod_is_primary"] is True
    assert data["checks"]["pm_is_fallback_when_aod_rejected"] is True
    assert data["checks"]["pm_context_distance_not_fallback"] is True
    assert data["checks"]["targetless_policy_score_modifier_neutral"] is True
    assert data["checks"]["forced_flag_marks_formula_enabled"] is True
    assert data["blockers"] == []
    assert cases["fresh_viirs_aod_local_pm"]["primary_source"] == "aod"
    assert cases["aod_high_uncertainty_pm_local_fallback"]["primary_source"] == "particulate"
    assert cases["missing_aod_context_distance_pm"]["primary_source"] == "none"


def test_checked_in_provider_quality_policy_report_matches_renderer() -> None:
    report = Path(__file__).parents[2] / REPORT_PATH

    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "# NSOM AOD/OpenAQ Provider Quality Policy" in text
    assert "aod_openaq_provider_quality_policy_hardened" in text
    assert "Ready for default-off experiment: `True`" in text
    assert "Ready for default-on: `False`" in text
    assert "Scoring formula implemented: `True`" in text
    assert "fresh_aod_owns_column_aerosol_when_policy_eligible" in text
    assert text.rstrip("\n") == render_markdown_report().rstrip("\n")


def _aod(
    *,
    uncertainty: float | None = 0.04,
    qa_raw: int | None = 1089,
    method: str = "direct_pixel",
    local_valid_pixel_count: int | None = None,
) -> AodConditionInput:
    return AodConditionInput(
        available=True,
        freshness_category="current",
        aod_550=0.24,
        source="NASA Earthdata",
        product="VNP19A2.002",
        status="ok",
        age_days=1.0,
        uncertainty=uncertainty,
        qa_raw=qa_raw,
        method=method,
        local_valid_pixel_count=local_valid_pixel_count,
    )


def _pm(*, distance_km: float | None) -> ParticulateConditionInput:
    return ParticulateConditionInput(
        available=True,
        freshness_category="current",
        pm25=18.0,
        pm10=42.0,
        source="OpenAQ Local",
        status="ok",
        age_days=0.25,
        distance_km=distance_km,
    )
