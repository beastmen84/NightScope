from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from inspect import signature
from pathlib import Path

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.home_nsom_ranking import (
    HomeRecommendedDeepSkyNsomRankingService,
    NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED,
)
from astro_viewer.app.services.observation_conditions_service import ObservationConditionsService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_home_nsom_recommended_deep_sky_flag_defaults_on() -> None:
    assert NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED is True


def test_controller_constructor_default_uses_current_home_nsom_flag() -> None:
    assert "use_nsom_home_recommended_deep_sky" not in signature(AppController.__init__).parameters


def test_default_path_uses_nsom_observable_target_value_order() -> None:
    controller = _controller(
        sky_quality=_sky_quality(9, radiance=120.0),
        moon=_moon(20),
    )

    controller._refresh_conditioned_observing_candidates()

    assert _ids(controller._conditioned_deep_sky) == [
        "globular_cluster",
        "open_cluster",
        "diffuse_nebula",
        "galaxy",
    ]


def test_no_constructor_rollback_parameter_remains_for_home_recommended_deep_sky() -> None:
    controller = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(95))
    expected = controller._moon_adjusted_objects(controller._home_visible_objects(controller._deep_sky))

    controller._refresh_conditioned_observing_candidates()

    assert _ids(controller._conditioned_deep_sky) != _ids(expected)
    assert "use_nsom_home_recommended_deep_sky" not in signature(AppController.__init__).parameters


def test_missing_sky_quality_falls_back_to_legacy_moon_adjusted_order() -> None:
    controller = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(95))
    controller._sky_quality = None
    expected = controller._moon_adjusted_objects(controller._home_visible_objects(controller._deep_sky))

    controller._refresh_conditioned_observing_candidates()

    assert _ids(controller._conditioned_deep_sky) == _ids(expected)
    assert controller._conditioned_deep_sky == expected


def test_flag_on_uses_observable_target_value_order_under_high_light_pollution() -> None:
    controller = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(20))

    controller._refresh_conditioned_observing_candidates()

    assert _ids(controller._conditioned_deep_sky) == [
        "globular_cluster",
        "open_cluster",
        "diffuse_nebula",
        "galaxy",
    ]


def test_default_path_ranks_raw_read_model_targets_and_returns_display_targets() -> None:
    controller = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(20))
    raw_low = _target("raw_low", "Galaxy", 30)
    raw_high = _target("raw_high", "Open Cluster", 90)
    display_low = replace(raw_low, score=99, condition_flags=("light_pollution",))
    display_high = replace(raw_high, score=10, condition_flags=("light_pollution",))
    ranking = _CapturingRawScoreRankingService()
    controller._home_recommended_deep_sky_nsom_ranking_service = ranking
    controller._deep_sky_raw_condition_input_by_id = {
        raw_low.id: raw_low,
        raw_high.id: raw_high,
    }
    controller._deep_sky = [display_low, display_high]

    controller._refresh_conditioned_observing_candidates()

    assert ranking.candidates == [raw_low, raw_high]
    assert controller._conditioned_deep_sky == [display_high, display_low]
    assert [model.nsom_target_input for model in controller._conditioned_deep_sky_read_model] == [
        raw_high,
        raw_low,
    ]
    assert [model.qml_display_target for model in controller._conditioned_deep_sky_read_model] == [
        display_high,
        display_low,
    ]
    assert [item.score for item in controller._conditioned_deep_sky] == [10, 99]


def test_flag_on_does_not_mutate_original_celestial_objects() -> None:
    controller = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(95))
    original = deepcopy(controller._deep_sky)

    controller._refresh_conditioned_observing_candidates()

    assert controller._deep_sky == original
    assert [item.score for item in controller._deep_sky] == [88, 86, 78, 82]


def test_weather_does_not_change_home_observable_order() -> None:
    controller = _controller(sky_quality=_sky_quality(4), moon=_moon(20))
    controller._weather_summary = _weather(85)
    controller._refresh_conditioned_observing_candidates()
    good_order = _ids(controller._conditioned_deep_sky)

    controller._weather_summary = _weather(10, cloud_cover=95, precipitation_probability=90)
    controller._refresh_conditioned_observing_candidates()

    assert _ids(controller._conditioned_deep_sky) == good_order


def test_equipment_does_not_change_home_observable_order() -> None:
    controller = _controller(sky_quality=_sky_quality(4), moon=_moon(20))
    controller._current_telescope = lambda: object()
    controller._refresh_conditioned_observing_candidates()
    first_order = _ids(controller._conditioned_deep_sky)

    controller._current_telescope = lambda: object()
    controller._refresh_conditioned_observing_candidates()

    assert _ids(controller._conditioned_deep_sky) == first_order


def test_practical_session_opportunity_and_confidence_are_not_home_ranking_inputs() -> None:
    module = Path(__file__).parents[1] / "app" / "services" / "home_nsom_ranking.py"
    tree = ast.parse(module.read_text(encoding="utf-8"))
    imported_names = {
        alias.name
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert "PracticalTargetValue" not in imported_names
    assert "ObserverCapability" not in imported_names
    assert "SessionViability" not in imported_names
    assert "RecommendationConfidence" not in imported_names
    assert "ObservationOpportunity" not in imported_names


def test_best_object_and_sky_compass_are_unchanged_by_home_ranking_refresh() -> None:
    controller = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(20))
    best_object = _target("best", "Spiral galaxy", 91)
    sky_compass = {"available": True, "items": [{"id": "stable"}]}
    controller._best_object = best_object
    controller._sky_compass = sky_compass

    controller._refresh_conditioned_observing_candidates()

    assert controller._best_object == best_object
    assert controller._sky_compass == sky_compass


def test_qml_payload_shape_remains_compatible() -> None:
    legacy = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(95))
    legacy._sky_quality = None
    nsom = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(95))

    legacy._refresh_conditioned_observing_candidates()
    nsom._refresh_conditioned_observing_candidates()

    legacy_keys = set(legacy._conditioned_deep_sky[0].to_qml())
    for item in nsom._conditioned_deep_sky:
        payload = item.to_qml()
        assert set(payload) == legacy_keys
        assert "nsom" not in payload
        assert "observableTargetValue" not in payload


def test_recommended_deep_sky_property_preserves_payload_shape_and_scores() -> None:
    legacy = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(20))
    legacy._sky_quality = None
    nsom = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(20))

    legacy_payload = _recommended_deep_sky_payload(legacy)
    nsom_payload = _recommended_deep_sky_payload(nsom)

    assert _payload_ids(legacy_payload) == [
        "galaxy",
        "diffuse_nebula",
        "globular_cluster",
        "open_cluster",
    ]
    assert _payload_ids(nsom_payload) == [
        "globular_cluster",
        "open_cluster",
        "diffuse_nebula",
        "galaxy",
    ]

    legacy_by_id = {item["id"]: item for item in legacy_payload}
    nsom_by_id = {item["id"]: item for item in nsom_payload}
    assert legacy_by_id.keys() == nsom_by_id.keys()
    for object_id, legacy_item in legacy_by_id.items():
        nsom_item = nsom_by_id[object_id]
        assert set(nsom_item) == set(legacy_item)
        assert nsom_item["score"] == legacy_item["score"]
        assert nsom_item["scoreLabel"] == legacy_item["scoreLabel"]
        assert "nsom" not in nsom_item
        assert "observableTargetValue" not in nsom_item
        assert "practicalTargetValue" not in nsom_item


def test_missing_sky_quality_recommended_deep_sky_property_payload_uses_fallback() -> None:
    controller = _controller(sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(95))
    controller._sky_quality = None

    payload = _recommended_deep_sky_payload(controller)
    direct = [controller._object_to_qml(item) for item in controller._moon_adjusted_objects(controller._deep_sky)]

    assert payload == direct


def test_readiness_audit_report_documents_score_semantics_and_runtime_safety() -> None:
    report = Path(__file__).parents[2] / "docs" / "HOME_NSOM_RECOMMENDED_DEEP_SKY_READINESS_AUDIT.md"

    text = report.read_text(encoding="utf-8")

    assert "Readiness verdict: ready for a separate default-on switch PR" in text
    assert "Displayed Score Semantics Decision" in text
    assert "keep the legacy/base displayed score for compatibility" in text
    assert "NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED` remains `False" in text
    assert "No QML/UI changes" in text
    assert "No report runtime wiring" in text
    assert "globular_cluster > open_cluster > diffuse_nebula > galaxy" in text


def test_no_home_nsom_ranking_qml_exposure_or_report_runtime_wiring() -> None:
    ui_root = Path(__file__).parents[1] / "app" / "ui"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in ui_root.rglob("*.qml"))
    controller_text = (Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )

    assert "NSOM_HOME_RECOMMENDED_DEEP_SKY_ENABLED" not in qml_text
    assert "HomeRecommendedDeepSkyNsomRankingService" not in qml_text
    assert "home_nsom_comparison_report" not in controller_text
    assert "HOME_NSOM_COMPARISON_REPORT" not in controller_text


def _controller(*, sky_quality: SkyQuality, moon: MoonSummary) -> AppController:
    controller = AppController.__new__(AppController)
    controller._conditions_service = ObservationConditionsService()
    controller._home_recommended_deep_sky_nsom_ranking_service = HomeRecommendedDeepSkyNsomRankingService()
    controller._moon = moon
    controller._sky_quality = sky_quality
    controller._weather_summary = _weather(85)
    controller._seeing_transparency = None
    controller._location = None
    controller._object_descriptions = {}
    controller._catalogue_visible_this_month_only = False
    controller._catalogue_selected_month = 1
    controller._catalogue_year = 2026
    controller._visible_planets = [_target("planet", "Pianeta", 90)]
    controller._deep_sky = [
        _target("galaxy", "Spiral galaxy", 88),
        _target("diffuse_nebula", "Diffuse nebula", 86),
        _target("open_cluster", "Open cluster", 78),
        _target("globular_cluster", "Globular cluster", 82),
    ]
    controller._conditioned_deep_sky = []
    controller._conditioned_home_objects = []
    controller._best_object = None
    controller._sky_compass = {}
    return controller


def _ids(items: list[CelestialObject]) -> list[str]:
    return [item.id for item in items]


def _payload_ids(items: list[dict[str, object]]) -> list[str]:
    return [str(item["id"]) for item in items]


def _recommended_deep_sky_payload(controller: AppController) -> list[dict[str, object]]:
    return AppController.__dict__["recommendedDeepSky"].fget(controller)


def _target(object_id: str, object_type: str, score: int) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.replace("_", " ").title(),
        object_type=object_type,
        image="",
        magnitude="8.0",
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="21:00",
        observing_window="21:00 - 02:00",
        notes="Fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        score_label="Fixture",
        difficulty="Media",
        recommended_setup_type="telescope",
    )


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="Fixture",
        description="Fixture",
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


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


class _CapturingRawScoreRankingService:
    def __init__(self) -> None:
        self.candidates: list[CelestialObject] = []

    def rank_by_observable_target_value(
        self,
        candidates: list[CelestialObject],
        *,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
    ) -> list[CelestialObject]:
        self.candidates = list(candidates)
        return sorted(self.candidates, key=lambda item: item.score, reverse=True)
