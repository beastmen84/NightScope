from __future__ import annotations

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import ObservableTargetValue, RecommendationConfidence
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService


def test_sensitivity_sky_background_changes_effective_and_observable_target_value() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy")
    scores = _scores()
    moon = _moon(10)

    dark = service.effective_observability(target, scores=scores, sky_quality=_sky_quality(2, radiance=1), moon=moon)
    bright = service.effective_observability(target, scores=scores, sky_quality=_sky_quality(9, radiance=140), moon=moon)
    dark_observable = ObservableTargetValue.from_intrinsic(intrinsic_target_quality=80.0, effective_observability=dark)
    bright_observable = ObservableTargetValue.from_intrinsic(intrinsic_target_quality=80.0, effective_observability=bright)

    assert dark.static_sky_background > bright.static_sky_background
    assert dark.value > bright.value
    assert dark_observable.value > bright_observable.value


def test_sensitivity_moon_background_changes_deep_sky_but_not_planet_target() -> None:
    service = PlannerNsomScoringService()
    scores = _scores(planetary=90, deep_sky=90)
    sky_quality = _sky_quality(2, radiance=1)

    galaxy_low_moon = service.effective_observability(_target("galaxy", "Galaxy"), scores=scores, sky_quality=sky_quality, moon=_moon(5))
    galaxy_high_moon = service.effective_observability(_target("galaxy", "Galaxy"), scores=scores, sky_quality=sky_quality, moon=_moon(95))
    planet_low_moon = service.effective_observability(_target("planet", "Pianeta"), scores=scores, sky_quality=sky_quality, moon=_moon(5))
    planet_high_moon = service.effective_observability(_target("planet", "Pianeta"), scores=scores, sky_quality=sky_quality, moon=_moon(95))

    assert galaxy_low_moon.lunar_sky_background > galaxy_high_moon.lunar_sky_background
    assert galaxy_low_moon.value > galaxy_high_moon.value
    assert planet_low_moon.lunar_sky_background == pytest.approx(1.0)
    assert planet_high_moon.lunar_sky_background == pytest.approx(1.0)
    assert planet_low_moon.value == pytest.approx(planet_high_moon.value)


def test_sensitivity_equipment_changes_practical_value_but_not_observable_value() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy")
    effective = service.effective_observability(target, scores=_scores(), sky_quality=_sky_quality(2, radiance=1), moon=_moon(10))
    observable = ObservableTargetValue.from_intrinsic(intrinsic_target_quality=80.0, effective_observability=effective)

    small = service.practical_target_value_from_observable(
        observable,
        target,
        telescope=_telescope(aperture_mm=60, focal_length_mm=400, mount="manual"),
    )
    large = service.practical_target_value_from_observable(
        observable,
        target,
        telescope=_telescope(aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
    )

    assert small.observable_target_value is observable
    assert large.observable_target_value is observable
    assert observable.value == pytest.approx(80.0 * effective.value)
    assert large.observer_capability_summary > small.observer_capability_summary
    assert large.value > small.value


def test_sensitivity_session_viability_blocks_opportunity_only() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy")
    practical = _practical(service, target)
    observable_value = practical.observable_target_value.value
    practical_value = practical.value

    good = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
    )
    blocked = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(20),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
    )

    assert blocked.session.value == 0.0
    assert good.session.value == 1.0
    assert blocked.value == 0.0
    assert good.value > 0.0
    assert practical.observable_target_value.value == pytest.approx(observable_value)
    assert practical.value == pytest.approx(practical_value)


def test_sensitivity_observing_window_quality_lowers_opportunity_only() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy")
    practical = _practical(service, target)

    full = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
        observing_window_quality=1.0,
    )
    half = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
        observing_window_quality=0.5,
    )
    none = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
        observing_window_quality=0.0,
    )

    assert half.value == pytest.approx(full.value * 0.5)
    assert none.value == pytest.approx(0.0)
    assert half.practical_target_value is practical
    assert none.practical_target_value.observable_target_value.value == pytest.approx(
        full.practical_target_value.observable_target_value.value
    )


def test_sensitivity_horizon_context_lowers_effective_observability() -> None:
    service = PlannerNsomScoringService()
    scores = _scores()
    sky_quality = _sky_quality(2, radiance=1)
    moon = _moon(10)

    high = service.effective_observability(
        _target("galaxy", "Galaxy", max_altitude="45 gradi"),
        scores=scores,
        sky_quality=sky_quality,
        moon=moon,
    )
    low = service.effective_observability(
        _target("galaxy", "Galaxy", max_altitude="15 gradi"),
        scores=scores,
        sky_quality=sky_quality,
        moon=moon,
    )

    assert low.horizon_context < high.horizon_context
    assert low.value < high.value


def test_sensitivity_confidence_does_not_change_opportunity_score() -> None:
    service = PlannerNsomScoringService()
    target = _target("galaxy", "Galaxy")
    practical = _practical(service, target)

    low = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = service.opportunity_from_practical_target_value(
        target,
        practical,
        weather=_weather(90),
        sky_quality=_sky_quality(2, radiance=1),
        moon=_moon(10),
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    assert low.confidence is not None
    assert high.confidence is not None
    assert low.confidence.value < high.confidence.value
    assert low.value == pytest.approx(high.value)


def _practical(service: PlannerNsomScoringService, target: CelestialObject):
    return service.practical_target_value(
        target,
        scores=_scores(),
        sky_quality=_sky_quality(2, radiance=1),
        telescope=_telescope(),
        moon=_moon(10),
    )


def _target(
    object_id: str,
    object_type: str,
    *,
    score: float = 82,
    max_altitude: str = "45 gradi",
    best_time: str = "21:00",
    observing_window: str | None = None,
    difficulty: str = "Media",
    visible: bool = True,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.title(),
        object_type=object_type,
        image="",
        magnitude="8.5",
        distance="",
        max_altitude=max_altitude,
        direction="Sud",
        best_time=best_time,
        observing_window=observing_window or f"{best_time} - 02:00",
        notes="Fixture",
        recommended_setup="Fixture setup",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=visible,
        score=round(score),
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type="telescope",
    )


def _scores(planetary: float = 85, deep_sky: float = 88) -> AdvancedObservingScores:
    return AdvancedObservingScores(
        planetary_score=planetary,
        deep_sky_score=deep_sky,
        planetary_label="Good",
        deep_sky_label="Good",
        explanation="Fixture",
    )


def _sky_quality(bortle: int, *, radiance: float | None, source: str = "Fixture") -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source=source,
        description="Fixture",
        viirs_radiance=radiance,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="18:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
        phase_angle=0.0,
    )


def _weather(score: int, *, cloud_cover: int = 10, precipitation: int = 0) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _telescope(
    *,
    name: str = "Test Scope",
    aperture_mm: int = 127,
    focal_length_mm: int = 1500,
    mount: str = "",
) -> Telescope:
    return Telescope(
        id="test-scope",
        name=name,
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Mak",
        mount=mount,
    )
