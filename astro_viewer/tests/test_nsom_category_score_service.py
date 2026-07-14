from __future__ import annotations

from dataclasses import replace

from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.services.nsom_category_score_service import NsomCategoryScoreService
from astro_viewer.app.services.observation_conditions_service import (
    AodConditionInput,
    ObservationConditionInputs,
)


def test_category_scores_use_canonical_atmospheric_transparency_only_once() -> None:
    service = NsomCategoryScoreService()
    seeing = _seeing()
    common = ObservationConditionInputs(
        moon=_moon(20),
        sky_quality=_sky_quality(4, radiance=2.0),
        seeing=seeing,
    )

    low_legacy_display = service.scores(
        replace(common, seeing=replace(seeing, transparency_score=20))
    )
    high_legacy_display = service.scores(
        replace(common, seeing=replace(seeing, transparency_score=90))
    )

    assert low_legacy_display == high_legacy_display


def test_light_pollution_reduces_deep_sky_but_not_planetary_category() -> None:
    service = NsomCategoryScoreService()
    dark = service.scores(
        ObservationConditionInputs(
            moon=_moon(10),
            sky_quality=_sky_quality(2, radiance=0.2),
            seeing=_seeing(),
        )
    )
    bright = service.scores(
        ObservationConditionInputs(
            moon=_moon(10),
            sky_quality=_sky_quality(9, radiance=140.0),
            seeing=_seeing(),
        )
    )

    assert bright.planetary_score == dark.planetary_score
    assert bright.deep_sky_score < dark.deep_sky_score


def test_eligible_aod_uses_target_class_sensitivity_without_mutating_inputs() -> None:
    service = NsomCategoryScoreService()
    aod = AodConditionInput(
        available=True,
        freshness_category="current",
        aod_550=0.7,
        source="NASA AOD",
        product="VNP19A2.002",
        status="available",
        age_days=1.0,
        uncertainty=0.05,
        qa_raw=1,
        method="local_neighborhood",
        local_valid_pixel_count=9,
    )
    baseline_inputs = ObservationConditionInputs(
        moon=_moon(10),
        sky_quality=_sky_quality(3),
        seeing=_seeing(),
    )
    aod_inputs = replace(baseline_inputs, aod=aod)

    baseline = service.scores(baseline_inputs)
    affected = service.scores(aod_inputs)

    assert affected.planetary_score <= baseline.planetary_score
    assert affected.deep_sky_score < baseline.deep_sky_score
    assert aod_inputs.aod is aod


def _seeing() -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Good",
        transparency="Good",
        seeing_score=82,
        transparency_score=65,
        atmospheric_transparency_score=74,
        explanation="",
    )


def _sky_quality(bortle: int, *, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=6.0,
        sky_brightness=21.0,
        source="Fixture",
        description="",
        viirs_radiance=radiance,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary("Fixture", f"{illumination}%", "", "", "", "")
