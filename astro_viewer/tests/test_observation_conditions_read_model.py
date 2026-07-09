from __future__ import annotations

import inspect
import json
from dataclasses import FrozenInstanceError, replace

import pytest

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.home_nsom_ranking import HomeRecommendedDeepSkyNsomRankingService
from astro_viewer.app.services.observation_conditions_read_model import (
    ObservationConditionsReadModelBuilder,
)
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionInputs,
    ObservationConditionsService,
)
from astro_viewer.app.viewmodels.app_controller import AppController


def test_conditioned_target_read_model_separates_raw_and_display_target() -> None:
    service = ObservationConditionsService()
    raw = _target("m31", "M31", "Galaxy", 88, magnitude="8.8")
    sky_quality = _sky_quality(bortle=8, radiance=120.0)
    conditioned = service.apply_deep_sky_pollution_to_target(raw, sky_quality)

    model = ObservationConditionsReadModelBuilder().from_conditioned_target(
        conditioned,
        source="test",
    )

    assert model.raw_target is raw
    assert model.display_target is conditioned.target
    assert model.nsom_target_input is raw
    assert model.qml_display_target is conditioned.target
    assert model.raw_score == raw.score
    assert model.display_score == conditioned.target.score
    assert model.raw_score > model.display_score
    assert raw.score == 88
    assert conditioned.target.condition_flags == ("light_pollution",)


def test_conditioned_target_read_model_is_frozen_and_strict_json_compatible() -> None:
    service = ObservationConditionsService()
    raw = _target("m31", "M31", "Galaxy", 88, magnitude="8.8")
    conditioned = service.condition_target(
        raw,
        ObservationConditionInputs(
            moon=_moon("92%"),
            sky_quality=_sky_quality(bortle=8, radiance=120.0),
        ),
        apply_moon=True,
        apply_pollution=True,
    )
    model = ObservationConditionsReadModelBuilder().from_conditioned_target(
        conditioned,
        source="test",
    )

    with pytest.raises(FrozenInstanceError):
        model.display_score = 100  # type: ignore[misc]

    json.dumps(model.to_dict(), sort_keys=True, allow_nan=False)


def test_condition_deep_sky_pollution_context_matches_legacy_display_output() -> None:
    service = ObservationConditionsService()
    targets = [_target(f"m{i}", f"M{i}", "Galaxy", 95 - i * 3, magnitude="8.8") for i in range(12)]
    sky_quality = _sky_quality(bortle=8, radiance=140.0)

    conditioned = service.condition_deep_sky_pollution_context(targets, sky_quality)
    legacy_display = service.apply_deep_sky_pollution_context(targets, sky_quality)

    assert [item.target for item in conditioned] == legacy_display
    assert [item.original_target for item in conditioned] == targets[: len(conditioned)]


def test_app_controller_pollution_context_builds_internal_read_model_without_output_change() -> None:
    controller = AppController.__new__(AppController)
    controller._conditions_service = ObservationConditionsService()
    controller._conditions_read_model_builder = ObservationConditionsReadModelBuilder()
    controller._sky_quality = _sky_quality(bortle=8, radiance=120.0)
    controller._moon = _moon("20%")
    controller._nasa_aod_result = None
    controller._local_atmosphere = None
    targets = [_target("m31", "M31", "Galaxy", 88, magnitude="8.8")]

    display_targets = controller._apply_deep_sky_pollution_context(targets)

    assert display_targets == [model.display_target for model in controller._deep_sky_pollution_read_model]
    assert controller._deep_sky_pollution_read_model[0].raw_target is targets[0]
    assert controller._deep_sky_pollution_read_model[0].nsom_target_input.score == 88
    assert display_targets[0].score < targets[0].score
    assert targets[0].score == 88


def test_app_controller_conditioned_candidates_preserve_display_order_and_raw_nsom_inputs() -> None:
    controller = AppController.__new__(AppController)
    controller._conditions_service = ObservationConditionsService()
    controller._conditions_read_model_builder = ObservationConditionsReadModelBuilder()
    controller._home_recommended_deep_sky_nsom_ranking_service = HomeRecommendedDeepSkyNsomRankingService()
    controller._use_nsom_home_recommended_deep_sky = True
    controller._sky_quality = _sky_quality(bortle=8, radiance=120.0)
    controller._moon = _moon("20%")
    controller._visible_planets = []
    raw_galaxy = _target("m31", "M31", "Galaxy", 88, magnitude="8.8")
    raw_cluster = _target("m45", "M45", "Open Cluster", 74, magnitude="1.6")
    controller._deep_sky_raw_condition_input_by_id = {
        raw_galaxy.id: raw_galaxy,
        raw_cluster.id: raw_cluster,
    }
    controller._deep_sky = [
        replace(raw_galaxy, score=55, condition_flags=("light_pollution",)),
        replace(raw_cluster, score=70, condition_flags=("light_pollution",)),
    ]

    controller._refresh_conditioned_observing_candidates()

    assert controller._conditioned_deep_sky == [
        model.qml_display_target for model in controller._conditioned_deep_sky_read_model
    ]
    assert {item.id: item.score for item in controller._conditioned_deep_sky_nsom_targets()} == {
        "m31": 88,
        "m45": 74,
    }
    assert [item.score for item in controller._conditioned_deep_sky] == [70, 55]


def test_observation_conditions_read_model_has_no_qml_property_exposure() -> None:
    source = inspect.getsource(AppController)

    assert "@Property" in source
    assert "conditioned_deep_sky_read_model" in source
    assert '@Property("QVariant", notify=dataChanged)\n    def conditioned' not in source
    assert "def observationConditionsReadModel" not in source


def _target(
    object_id: str,
    name: str,
    object_type: str,
    score: int,
    *,
    magnitude: str = "7.0",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="60 deg",
        direction="Sud",
        best_time="22:00",
        observing_window="21:30 - 23:30",
        notes="fixture",
        recommended_setup="fixture",
        visibility_class="Buona",
        azimuth="180 deg",
        time_above_horizon="4 h",
        score=score,
        score_label="Buono",
        difficulty="Facile",
        visible=True,
    )


def _sky_quality(*, bortle: int, radiance: float | None) -> SkyQuality:
    return SkyQuality(
        bortle,
        4.5,
        18.4,
        "Fixture",
        "Fixture",
        "high",
        viirs_radiance=radiance,
    )


def _moon(illumination: str) -> MoonSummary:
    return MoonSummary(
        phase="fixture",
        illumination=illumination,
        rise_time="20:00",
        set_time="06:00",
        best_note="fixture",
        image="",
    )
