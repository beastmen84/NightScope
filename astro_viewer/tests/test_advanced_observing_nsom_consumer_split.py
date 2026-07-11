from __future__ import annotations

from types import SimpleNamespace

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.advanced_observing_nsom_service import (
    NSOM_ADVANCED_OBSERVING_ENABLED,
    AdvancedObservingNsomService,
)
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_consumer_split_keeps_public_advanced_scores_legacy() -> None:
    controller = _controller()
    expected_legacy = _legacy_scores(controller)
    expected_nsom = _nsom_scores(controller)

    controller._recalculate_observing_outputs()

    assert controller._advanced_scores == expected_legacy
    assert controller._advanced_observing_nsom_scores == expected_nsom
    assert controller._advanced_observing_nsom_scores != controller._advanced_scores
    assert set(controller._advanced_scores.to_qml()) == {
        "planetary_score",
        "deep_sky_score",
        "planetary_label",
        "deep_sky_label",
        "explanation",
        "planetaryScore",
        "deepSkyScore",
        "planetaryLabel",
        "deepSkyLabel",
    }


def test_default_flag_keeps_public_advanced_scores_legacy_and_computes_parallel_nsom() -> None:
    assert NSOM_ADVANCED_OBSERVING_ENABLED is True
    controller = _controller()
    expected_legacy = _legacy_scores(controller)
    expected_nsom = _nsom_scores(controller)

    controller._recalculate_observing_outputs()

    assert controller._advanced_scores == expected_legacy
    assert controller._advanced_observing_nsom_scores == expected_nsom
    assert controller._advanced_observing_nsom_scores != controller._advanced_scores


def test_planner_receives_legacy_scores_when_parallel_nsom_is_computed() -> None:
    controller = _controller()
    planner = _PlannerSpy()
    controller._night_planner_service = planner
    expected_legacy = _legacy_scores(controller)
    expected_nsom = _nsom_scores(controller)

    controller._recalculate_observing_outputs()

    assert planner.received_scores == expected_legacy
    assert planner.received_scores != expected_nsom


def test_notifications_backend_path_is_absent_from_consumer_split_runtime() -> None:
    controller = _controller()

    controller._recalculate_observing_outputs()

    assert not hasattr(controller, "_notification_service")
    assert not hasattr(controller, "_notifications")
    assert not hasattr(controller, "_advanced_scores_for_notifications")


def test_internal_rollback_removed_so_parallel_nsom_advanced_scores_are_computed() -> None:
    controller = _controller()

    controller._recalculate_observing_outputs()

    assert controller._advanced_scores == _legacy_scores(controller)
    assert controller._advanced_observing_nsom_scores == _nsom_scores(controller)


def test_consumer_split_methods_are_legacy_compatible() -> None:
    controller = _controller()
    controller._advanced_scores = _legacy_scores(controller)
    controller._advanced_observing_nsom_scores = _nsom_scores(controller)

    assert controller._advanced_scores_for_planner() == controller._advanced_scores
    assert controller._advanced_scores_for_planner() != controller._advanced_observing_nsom_scores


class _PlannerSpy:
    def __init__(self) -> None:
        self.received_scores: AdvancedObservingScores | None = None

    def plan(self, _objects, _weather, scores, _sky_quality, _telescope, _moon, **_kwargs):
        self.received_scores = scores
        return []


def _controller(
    *,
    weather: WeatherSummary | None = None,
    seeing: SeeingTransparency | None = None,
    sky_quality: SkyQuality | None = None,
    moon: MoonSummary | None = None,
) -> AppController:
    controller = AppController.__new__(AppController)
    controller._advanced_observing_service = AdvancedObservingService()
    controller._advanced_observing_nsom_service = AdvancedObservingNsomService()
    controller._weather_summary = weather or _weather(90)
    controller._seeing_transparency = seeing or _seeing()
    controller._sky_quality = sky_quality or _sky_quality(9, radiance=120.0)
    controller._moon = moon if moon is not None else _moon(95)
    controller._weather_hours = []
    controller._seeing_service = SimpleNamespace(
        estimate=lambda _hours, _sky_quality: controller._seeing_transparency
    )
    controller._refresh_conditioned_observing_candidates = lambda: None
    controller._home_visible_objects = lambda objects: objects
    controller._select_best_object = lambda _objects, **_kwargs: None
    controller._visible_planets = []
    controller._deep_sky = []
    controller._events = []
    controller._current_telescope = lambda: Telescope(
        "scope",
        "Fixture scope",
        120,
        900,
        "Refractor",
        "Alt-az",
    )
    controller._night_planner_service = _PlannerSpy()
    controller._refresh_sky_compass = lambda: None
    controller._refresh_nsom_diagnostics = lambda: None
    controller._advanced_scores = None
    controller._advanced_observing_nsom_scores = None
    controller._best_object = None
    controller._night_plan = []
    return controller


def _legacy_scores(controller: AppController) -> AdvancedObservingScores:
    return AdvancedObservingService().scores(
        controller._weather_summary,
        controller._seeing_transparency,
        controller._sky_quality,
        controller._moon,
    )


def _nsom_scores(controller: AppController) -> AdvancedObservingScores:
    return AdvancedObservingNsomService().scores(
        controller._weather_summary,
        controller._seeing_transparency,
        controller._sky_quality,
        controller._moon,
    )


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Advanced Observing NSOM consumer split fixture",
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
        explanation="Advanced Observing NSOM consumer split fixture",
    )


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="AdvancedObservingNsomConsumerSplitFixture",
        description="Advanced Observing NSOM consumer split fixture",
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
