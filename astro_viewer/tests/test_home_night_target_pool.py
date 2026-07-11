from __future__ import annotations

from astro_viewer.app.astronomy.engine import ObserverLocation, ObservingNightWindow
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import NightPlanItem, SkyQuality
from astro_viewer.app.services.observation_conditions_read_model import ObservationConditionsReadModelBuilder
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionInputs,
    ObservationConditionsService,
)
from astro_viewer.app.viewmodels.app_controller import AppController


def test_home_visible_alternatives_use_the_full_pool_minus_the_four_step_plan() -> None:
    controller = AppController.__new__(AppController)
    planet = _target("mars", "Marte", "Pianeta", "04:00", 90)
    planned = _target("m-plan", "Planned", "Globular cluster", "21:00", 88)
    late = _target("m-late", "Late", "Galaxy", "02:30", 70)
    early = _target("m-early", "Early", "Open cluster", "22:00", 80)
    duplicate = _target("mars", "Marte duplicate", "Pianeta", "04:00", 10)
    controller._visible_planets = [planet]
    controller._conditioned_deep_sky_candidates = lambda: [planned, late, early, duplicate]
    controller._night_plan = [_plan_item(planned)]
    controller._object_to_qml = lambda item: item.to_qml()

    payload = AppController.__dict__["homeVisibleAlternatives"].fget(controller)

    assert [item["id"] for item in payload] == ["m-early", "m-late", "mars"]
    assert [item["homeCategory"] for item in payload] == ["deep_sky", "deep_sky", "planet"]
    assert all(item["id"] != planned.id for item in payload)


def test_skyfield_recommended_deep_sky_does_not_cap_the_visible_catalogue_to_ten() -> None:
    rows = [
        {
            "messier_id": f"M{index}",
            "dec": "0",
            "magnitude": 6.0,
            "object_type": "Open cluster",
        }
        for index in range(1, 61)
    ]
    engine = SkyfieldAstronomyEngine.__new__(SkyfieldAstronomyEngine)
    engine._messier_repository = _MessierRows(rows)
    engine._object_score = lambda *_args: 80
    engine.observing_night_window = lambda *_args, **_kwargs: ObservingNightWindow.unavailable()
    engine._messier_details = lambda row, _location, dec_degrees=None, **_kwargs: _target(
        f"messier-{row['messier_id']}",
        row["messier_id"],
        row["object_type"],
        "22:00",
        80,
    )

    targets = engine.recommended_deep_sky(
        ObserverLocation("Test", "Earth", 0.0, 0.0, "UTC")
    )

    assert len(targets) == 60
    assert all(target.visible for target in targets)


def test_home_alternatives_keep_more_than_ten_targets_with_active_pollution_context() -> None:
    controller = AppController.__new__(AppController)
    controller._conditions_service = ObservationConditionsService()
    controller._conditions_read_model_builder = ObservationConditionsReadModelBuilder()
    controller._sky_quality = SkyQuality(
        bortle_class=8,
        limiting_magnitude=5.0,
        sky_brightness=19.0,
        source="fixture",
        description="fixture",
        viirs_radiance=140.0,
    )
    controller._build_observation_condition_inputs = lambda **_kwargs: ObservationConditionInputs(
        sky_quality=controller._sky_quality
    )
    targets = [
        _target(f"m-{index}", f"Target {index}", "Open cluster", "22:00", 95 - index)
        for index in range(16)
    ]

    conditioned = controller._apply_deep_sky_pollution_context(targets)
    controller._conditioned_deep_sky = conditioned
    controller._visible_planets = []
    controller._night_plan = [_plan_item(item) for item in conditioned[:4]]
    controller._object_to_qml = lambda item: item.to_qml()

    payload = AppController.__dict__["homeVisibleAlternatives"].fget(controller)

    assert len(conditioned) == 16
    assert len(payload) == 12
    assert {item["id"] for item in payload} == {item.id for item in conditioned[4:]}


class _MessierRows:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def list_objects(self) -> list[dict]:
        return list(self._rows)


def _target(
    object_id: str,
    name: str,
    object_type: str,
    best_time: str,
    score: int,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="6.0",
        distance="",
        max_altitude="50 gradi",
        direction="Sud",
        best_time=best_time,
        observing_window=f"{best_time} - 05:00",
        notes="Fixture",
        recommended_setup="Fixture setup",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        difficulty="Media",
    )


def _plan_item(item: CelestialObject) -> NightPlanItem:
    return NightPlanItem(
        time_label="21:00 sera",
        object_id=item.id,
        name=item.name,
        score=item.score,
        difficulty=item.difficulty,
        setup=item.recommended_setup,
        direction=item.direction,
        image=item.image,
    )
