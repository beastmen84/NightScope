from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from astro_viewer.app.models.nsom import RecommendationConfidence
from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.advanced_observing_nsom_service import (
    NSOM_ADVANCED_OBSERVING_ENABLED,
    AdvancedObservingNsomService,
)
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_advanced_observing_nsom_flag_is_default_off() -> None:
    assert NSOM_ADVANCED_OBSERVING_ENABLED is False
    assert (
        AppController.__init__.__kwdefaults__["use_nsom_advanced_observing"]
        is NSOM_ADVANCED_OBSERVING_ENABLED
    )


def test_flag_off_preserves_legacy_advanced_scores() -> None:
    controller = _controller(enabled=False)
    expected = AdvancedObservingService().scores(
        controller._weather_summary,
        controller._seeing_transparency,
        controller._sky_quality,
        controller._moon,
    )

    scores = controller._select_advanced_observing_scores()

    assert scores == expected


def test_forced_on_keeps_advanced_scores_legacy_and_computes_internal_nsom_scores() -> None:
    controller = _controller(
        enabled=True,
        weather=_weather(90),
        seeing=_seeing(seeing_score=86, transparency_score=84),
        sky_quality=_sky_quality(9, radiance=120.0),
        moon=_moon(95),
    )
    expected = AdvancedObservingNsomService().scores(
        controller._weather_summary,
        controller._seeing_transparency,
        controller._sky_quality,
        controller._moon,
    )
    legacy = AdvancedObservingService().scores(
        controller._weather_summary,
        controller._seeing_transparency,
        controller._sky_quality,
        controller._moon,
    )

    scores = controller._select_advanced_observing_scores()
    nsom_scores = controller._select_advanced_observing_nsom_scores()

    assert scores == legacy
    assert nsom_scores == expected
    assert nsom_scores != scores
    assert nsom_scores.planetary_score == 86
    assert "NSOM sperimentale" in nsom_scores.explanation


def test_nsom_planetary_score_is_protected_from_moon_and_light_pollution_background() -> None:
    service = AdvancedObservingNsomService()
    dark = service.scores(_weather(90), _seeing(seeing_score=82), _sky_quality(2), _moon(10))
    bright = service.scores(
        _weather(90),
        _seeing(seeing_score=82),
        _sky_quality(9, radiance=120.0),
        _moon(95),
    )

    assert bright.planetary_score == dark.planetary_score
    assert bright.deep_sky_score < dark.deep_sky_score


def test_nsom_advanced_scores_keep_session_viability_out_of_category_values() -> None:
    service = AdvancedObservingNsomService()
    sky_quality = _sky_quality(3)
    seeing = _seeing(seeing_score=80, transparency_score=78)
    moon = _moon(20)

    good = service.scores(_weather(90), seeing, sky_quality, moon)
    blocked = service.scores(
        _weather(10, cloud_cover=95, precipitation_probability=80),
        seeing,
        sky_quality,
        moon,
    )
    legacy_blocked = AdvancedObservingService().scores(
        _weather(10, cloud_cover=95, precipitation_probability=80),
        seeing,
        sky_quality,
        moon,
    )

    assert blocked.planetary_score == good.planetary_score
    assert blocked.deep_sky_score == good.deep_sky_score
    assert "blocked" in blocked.explanation
    assert legacy_blocked.planetary_score < good.planetary_score
    assert legacy_blocked.deep_sky_score < good.deep_sky_score


def test_nsom_advanced_observing_confidence_is_score_neutral() -> None:
    service = AdvancedObservingNsomService()
    low = service.scores(
        _weather(90),
        _seeing(),
        _sky_quality(3),
        _moon(10),
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = service.scores(
        _weather(90),
        _seeing(),
        _sky_quality(3),
        _moon(10),
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    assert low.planetary_score == high.planetary_score
    assert low.deep_sky_score == high.deep_sky_score
    assert low.planetary_label == high.planetary_label
    assert low.deep_sky_label == high.deep_sky_label
    assert "confidence" in low.explanation


def test_nsom_advanced_observing_does_not_mutate_runtime_inputs() -> None:
    weather = _weather(90)
    seeing = _seeing()
    sky_quality = _sky_quality(8, radiance=45.0)
    moon = _moon(85)
    before = deepcopy((weather, seeing, sky_quality, moon))

    AdvancedObservingNsomService().scores(weather, seeing, sky_quality, moon)

    assert (weather, seeing, sky_quality, moon) == before


def test_nsom_advanced_observing_payload_shape_remains_legacy_compatible() -> None:
    legacy = AdvancedObservingService().scores(_weather(90), _seeing(), _sky_quality(3), _moon(10))
    nsom = AdvancedObservingNsomService().scores(_weather(90), _seeing(), _sky_quality(3), _moon(10))

    json.dumps(nsom.to_qml(), sort_keys=True, allow_nan=False)

    assert set(nsom.to_qml()) == set(legacy.to_qml())
    assert "observableTargetValue" not in nsom.to_qml()
    assert "sessionViability" not in nsom.to_qml()
    assert "recommendationConfidence" not in nsom.to_qml()


def test_nsom_advanced_observing_runtime_path_has_no_qml_or_report_wiring() -> None:
    app_root = Path(__file__).parents[1] / "app"
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (app_root / "ui").rglob("*.qml")
    )
    controller_text = (app_root / "viewmodels" / "app_controller.py").read_text(encoding="utf-8")
    service_text = (app_root / "services" / "advanced_observing_nsom_service.py").read_text(
        encoding="utf-8"
    )

    assert "NSOM_ADVANCED_OBSERVING_ENABLED" not in qml_text
    assert "AdvancedObservingNsomService" not in qml_text
    assert "advanced_observing_nsom_service" not in qml_text
    assert "ADVANCED_OBSERVING_NSOM_COMPARISON_REPORT" not in controller_text
    assert "ADVANCED_OBSERVING_NSOM_POLICY_READINESS" not in controller_text
    assert "astro_viewer.tools" not in service_text
    assert "advanced_observing_nsom_comparison_report" not in service_text
    assert "advanced_observing_nsom_policy_readiness" not in service_text


def _controller(
    *,
    enabled: bool,
    weather: WeatherSummary | None = None,
    seeing: SeeingTransparency | None = None,
    sky_quality: SkyQuality | None = None,
    moon: MoonSummary | None = None,
) -> AppController:
    controller = AppController.__new__(AppController)
    controller._use_nsom_advanced_observing = enabled
    controller._advanced_observing_service = AdvancedObservingService()
    controller._advanced_observing_nsom_service = AdvancedObservingNsomService()
    controller._weather_summary = weather or _weather(90)
    controller._seeing_transparency = seeing or _seeing()
    controller._sky_quality = sky_quality or _sky_quality(3)
    controller._moon = moon if moon is not None else _moon(10)
    return controller


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Advanced Observing NSOM fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _seeing(
    *,
    seeing_score: int = 86,
    transparency_score: int = 84,
) -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Fixture",
        transparency="Fixture",
        seeing_score=seeing_score,
        transparency_score=transparency_score,
        explanation="Advanced Observing NSOM fixture",
    )


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="AdvancedObservingNsomRuntimeFixture",
        description="Advanced Observing NSOM runtime fixture",
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
