from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

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
    duplicate = _target(" MARS ", "Marte duplicate", "Pianeta", "04:00", 10)
    controller._visible_planets = [planet]
    controller._conditioned_deep_sky_candidates = lambda: [planned, late, early, duplicate]
    controller._night_plan = [_plan_item(planned)]
    controller._object_to_qml = lambda item: item.to_qml()

    payload = AppController.__dict__["homeVisibleAlternatives"].fget(controller)

    assert [item["id"] for item in payload] == ["m-early", "m-late", "mars"]
    assert [item["homeCategory"] for item in payload] == ["deep_sky", "deep_sky", "planet"]
    assert all(item["id"] != planned.id for item in payload)


def test_home_alternatives_with_shared_best_time_follow_window_start() -> None:
    controller = AppController.__new__(AppController)
    controller._observing_night_window = ObservingNightWindow.bounded(
        datetime(2026, 7, 11, 18, 48, tzinfo=ZoneInfo("Africa/Addis_Ababa")),
        datetime(2026, 7, 12, 6, 12, tzinfo=ZoneInfo("Africa/Addis_Ababa")),
    )
    controller._visible_planets = []
    controller._conditioned_deep_sky_candidates = lambda: [
        _target("m37", "M37", "Open cluster", "05:48", 70, "05:47 - 06:12"),
        _target("m38", "M38", "Open cluster", "05:48", 70, "05:23 - 06:12"),
        _target("m45", "M45", "Open cluster", "05:48", 70, "03:44 - 06:12"),
        _target("m74", "M74", "Galaxy", "05:48", 70, "01:36 - 06:12"),
        _target("m76", "M76", "Planetary nebula", "05:48", 70, "01:41 - 06:12"),
        _target("m77", "M77", "Galaxy", "05:48", 70, "02:50 - 06:12"),
    ]
    controller._night_plan = []
    controller._object_to_qml = lambda item: item.to_qml()

    payload = AppController.__dict__["homeVisibleAlternatives"].fget(controller)

    assert [item["id"] for item in payload] == [
        "m74",
        "m76",
        "m77",
        "m45",
        "m38",
        "m37",
    ]


def test_home_alternatives_use_natural_catalogue_name_order_as_final_tie_break() -> None:
    controller = AppController.__new__(AppController)
    controller._observing_night_window = ObservingNightWindow.bounded(
        datetime(2026, 7, 11, 18, 48, tzinfo=ZoneInfo("Africa/Addis_Ababa")),
        datetime(2026, 7, 12, 6, 12, tzinfo=ZoneInfo("Africa/Addis_Ababa")),
    )
    controller._visible_planets = []
    controller._conditioned_deep_sky_candidates = lambda: [
        _target("m100", "M100", "Galaxy", "22:30", 70, "22:00 - 23:00"),
        _target("m40", "M40", "Double star", "22:30", 70, "22:00 - 23:00"),
        _target("c14", "C14", "Double cluster", "22:30", 70, "22:00 - 23:00"),
        _target("m3", "M3", "Globular cluster", "22:30", 70, "22:00 - 23:00"),
        _target("c2", "C2", "Planetary nebula", "22:30", 70, "22:00 - 23:00"),
    ]
    controller._night_plan = []
    controller._object_to_qml = lambda item: item.to_qml()

    payload = AppController.__dict__["homeVisibleAlternatives"].fget(controller)

    assert [item["id"] for item in payload] == ["c2", "c14", "m3", "m40", "m100"]


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
    observing_window: str | None = None,
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
        observing_window=observing_window or f"{best_time} - 05:00",
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
