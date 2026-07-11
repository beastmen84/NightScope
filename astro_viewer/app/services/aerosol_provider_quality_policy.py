from __future__ import annotations

import math
from dataclasses import dataclass

from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    ObservationConditionsService,
    ParticulateConditionInput,
)


AOD_MAX_VALUE_FOR_POLICY = 3.0
AOD_MAX_UNCERTAINTY_FOR_POLICY = 0.15
AOD_LOCAL_NEIGHBORHOOD_MIN_PIXELS = 3
OPENAQ_LOCAL_REPRESENTATIVE_KM = 25.0
OPENAQ_CONTEXT_ONLY_KM = 50.0
@dataclass(frozen=True)
class AodProviderQualityDecision:
    """Formal AOD quality gate for aerosol condition scoring."""

    available: bool
    eligible_for_scoring: bool
    role: str
    freshness_weight: float
    uncertainty_weight: float
    qa_weight: float
    locality_weight: float
    product_weight: float
    confidence_weight: float
    reasons: tuple[str, ...]
    source_notes: tuple[str, ...]


@dataclass(frozen=True)
class ParticulateProviderQualityDecision:
    """Formal OpenAQ particulate representativeness gate for fallback/context use."""

    available: bool
    eligible_for_fallback: bool
    role: str
    freshness_weight: float
    locality_weight: float
    value_weight: float
    confidence_weight: float
    reasons: tuple[str, ...]
    source_notes: tuple[str, ...]


@dataclass(frozen=True)
class AerosolProviderQualityPolicy:
    """Combined source-precedence and double-counting policy.

    This object is target-neutral. It defines whether AOD/PM data is
    trustworthy enough for aerosol condition scoring. Target-specific score
    modifiers are computed by ObservationConditionsService.
    """

    primary_source: str
    aod: AodProviderQualityDecision
    particulate: ParticulateProviderQualityDecision
    double_counting_rules: tuple[str, ...]
    confidence_notes: tuple[str, ...]


class AerosolProviderQualityPolicyService:
    """Classifies AOD/OpenAQ provider inputs without applying target modifiers."""

    def aod_quality(self, aod: AodConditionInput | None) -> AodProviderQualityDecision:
        if aod is None:
            return AodProviderQualityDecision(
                available=False,
                eligible_for_scoring=False,
                role="missing",
                freshness_weight=0.0,
                uncertainty_weight=0.0,
                qa_weight=0.0,
                locality_weight=0.0,
                product_weight=0.0,
                confidence_weight=0.0,
                reasons=("aod_missing",),
                source_notes=("no_aod_provider_input",),
            )

        reasons: list[str] = []
        notes: list[str] = []
        freshness_weight = ObservationConditionsService.aod_freshness_weight(
            aod.age_days,
            aod.freshness_category,
        )
        if not aod.available:
            reasons.append(f"aod_unavailable:{aod.status or 'unknown'}")
        if freshness_weight <= 0.0:
            reasons.append("aod_not_fresh_enough")

        value = _finite_float(aod.aod_550)
        if value is None:
            reasons.append("aod_value_missing_or_non_finite")
        elif value < 0.0 or value > AOD_MAX_VALUE_FOR_POLICY:
            reasons.append("aod_value_outside_policy_range")
        else:
            notes.append(f"aod_550={value:g}")

        uncertainty_weight = self._aod_uncertainty_weight(aod.uncertainty)
        if uncertainty_weight <= 0.0:
            reasons.append("aod_uncertainty_missing_or_high")
        elif aod.uncertainty is not None:
            notes.append(f"aod_uncertainty={aod.uncertainty:g}")

        qa_weight = 1.0 if aod.qa_raw is not None else 0.0
        if qa_weight <= 0.0:
            reasons.append("aod_qa_raw_missing")
        else:
            notes.append(f"aod_qa_raw={aod.qa_raw}")
            notes.append("aod_qa_policy=raw_present_required")

        locality_weight = self._aod_locality_weight(aod)
        if locality_weight <= 0.0:
            reasons.append("aod_local_neighborhood_too_sparse")

        product_weight = self._aod_product_weight(aod.product)
        if aod.product:
            notes.append(f"aod_product={aod.product}")
        if aod.method:
            notes.append(f"aod_method={aod.method}")
        if aod.local_valid_pixel_count is not None:
            notes.append(f"aod_local_valid_pixel_count={aod.local_valid_pixel_count}")

        confidence_weight = min(
            freshness_weight,
            uncertainty_weight,
            qa_weight,
            locality_weight,
            product_weight,
        )
        eligible = not reasons and confidence_weight > 0.0
        return AodProviderQualityDecision(
            available=bool(aod.available),
            eligible_for_scoring=eligible,
            role="primary_aerosol_column" if eligible else "metadata_only",
            freshness_weight=freshness_weight,
            uncertainty_weight=uncertainty_weight,
            qa_weight=qa_weight,
            locality_weight=locality_weight,
            product_weight=product_weight,
            confidence_weight=confidence_weight if eligible else 0.0,
            reasons=tuple(reasons),
            source_notes=tuple(notes),
        )

    def particulate_quality(
        self,
        particulate: ParticulateConditionInput | None,
    ) -> ParticulateProviderQualityDecision:
        if particulate is None:
            return ParticulateProviderQualityDecision(
                available=False,
                eligible_for_fallback=False,
                role="missing",
                freshness_weight=0.0,
                locality_weight=0.0,
                value_weight=0.0,
                confidence_weight=0.0,
                reasons=("particulate_missing",),
                source_notes=("no_openaq_provider_input",),
            )

        reasons: list[str] = []
        notes: list[str] = []
        freshness_weight = ObservationConditionsService.particulate_freshness_weight(
            particulate.age_days,
            particulate.freshness_category,
        )
        if not particulate.available:
            reasons.append(f"particulate_unavailable:{particulate.status or 'unknown'}")
        if freshness_weight <= 0.0:
            reasons.append("particulate_not_fresh_enough")

        values = tuple(
            value
            for value in (_finite_float(particulate.pm25), _finite_float(particulate.pm10))
            if value is not None
        )
        value_weight = 1.0 if values and all(value >= 0.0 for value in values) else 0.0
        if value_weight <= 0.0:
            reasons.append("particulate_value_missing_or_non_finite")
        else:
            if particulate.pm25 is not None:
                notes.append(f"pm25={particulate.pm25:g}")
            if particulate.pm10 is not None:
                notes.append(f"pm10={particulate.pm10:g}")

        locality_weight, locality_reason = self._particulate_locality_weight(particulate.distance_km)
        if locality_reason:
            reasons.append(locality_reason)
        if particulate.distance_km is not None:
            notes.append(f"openaq_distance_km={particulate.distance_km:g}")
        if particulate.source:
            notes.append(f"openaq_source={particulate.source}")

        confidence_weight = min(freshness_weight, locality_weight, value_weight)
        eligible = not reasons and confidence_weight > 0.0
        return ParticulateProviderQualityDecision(
            available=bool(particulate.available),
            eligible_for_fallback=eligible,
            role="fallback_ground_particulate" if eligible else "metadata_only",
            freshness_weight=freshness_weight,
            locality_weight=locality_weight,
            value_weight=value_weight,
            confidence_weight=confidence_weight if eligible else 0.0,
            reasons=tuple(reasons),
            source_notes=tuple(notes),
        )

    def policy(
        self,
        aod: AodConditionInput | None,
        particulate: ParticulateConditionInput | None,
    ) -> AerosolProviderQualityPolicy:
        aod_quality = self.aod_quality(aod)
        particulate_quality = self.particulate_quality(particulate)

        if aod_quality.eligible_for_scoring:
            primary_source = "aod"
        elif particulate_quality.eligible_for_fallback:
            primary_source = "particulate"
        else:
            primary_source = "none"
        return AerosolProviderQualityPolicy(
            primary_source=primary_source,
            aod=aod_quality,
            particulate=particulate_quality,
            double_counting_rules=(
                "aod_and_particulate_are_not_additive",
                "fresh_aod_owns_column_aerosol_when_policy_eligible",
                "openaq_pm_is_fallback_or_context_only",
                "viirs_sky_background_remains_separate",
                "weather_transparency_remains_separate",
                "moon_geometry_remains_separate",
            ),
            confidence_notes=(
                "provider_quality_changes_confidence_metadata_only",
                "provider_quality_does_not_change_target_specific_score",
                "recommendation_confidence_remains_score_neutral",
            ),
        )

    @staticmethod
    def _aod_uncertainty_weight(value: float | None) -> float:
        parsed = _finite_float(value)
        if parsed is None or parsed < 0.0:
            return 0.0
        if parsed <= AOD_MAX_UNCERTAINTY_FOR_POLICY:
            return 1.0
        return 0.0

    @staticmethod
    def _aod_locality_weight(aod: AodConditionInput) -> float:
        if aod.method != "local_neighborhood":
            return 1.0
        if aod.local_valid_pixel_count is None:
            return 0.0
        return 1.0 if aod.local_valid_pixel_count >= AOD_LOCAL_NEIGHBORHOOD_MIN_PIXELS else 0.0

    @staticmethod
    def _aod_product_weight(product: str) -> float:
        if "VNP19A2" in product:
            return 1.0
        if "MCD19A2" in product:
            return 0.85
        if product:
            return 0.7
        return 0.0

    @staticmethod
    def _particulate_locality_weight(distance_km: float | None) -> tuple[float, str]:
        distance = _finite_float(distance_km)
        if distance is None:
            return 0.0, "openaq_distance_unknown"
        if distance < 0.0:
            return 0.0, "openaq_distance_invalid"
        if distance <= OPENAQ_LOCAL_REPRESENTATIVE_KM:
            return 1.0, ""
        if distance <= OPENAQ_CONTEXT_ONLY_KM:
            return 0.5, "openaq_context_distance_not_scoring_representative"
        return 0.0, "openaq_too_distant"


def _finite_float(value: float | None) -> float | None:
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed
