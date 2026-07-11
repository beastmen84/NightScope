from __future__ import annotations

import inspect
import unittest
from dataclasses import replace
from unittest.mock import Mock

from PySide6.QtCore import QObject

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.refresh_lifecycle import RefreshDomain, RefreshManager
from astro_viewer.app.services.sky_compass_nsom_ranking import SkyCompassNsomDirectionService
from astro_viewer.app.services.sky_compass_service import SkyCompassService
from astro_viewer.app.viewmodels.app_controller import AppController


class SkyCompassLiveRefreshTest(unittest.TestCase):
    def test_live_refresh_updates_only_compass_live_domain_and_clears_it(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, engine, _timer = _controller([target])

        controller._refresh_sky_compass_live()

        self.assertEqual(engine.calls, 1)
        controller._sky_compass_candidates.assert_not_called()
        self.assertEqual(controller._refresh_manager.snapshot(), frozenset())
        self.assertIsNone(controller._refresh_manager.reason_for_domain(RefreshDomain.COMPASS_LIVE))
        for domain in (
            RefreshDomain.WEATHER,
            RefreshDomain.EQUIPMENT,
            RefreshDomain.PLANNER,
            RefreshDomain.SKY_QUALITY,
            RefreshDomain.AIR_QUALITY,
            RefreshDomain.AOD,
            RefreshDomain.COMPASS,
        ):
            self.assertFalse(controller._refresh_manager.is_dirty(domain))

    def test_live_refresh_does_not_call_heavy_refresh_paths(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, engine, _timer = _controller([target])
        heavy_methods = (
            "_refresh_all",
            "_refresh_astronomy",
            "_refresh_weather_and_conditions",
            "_recalculate_observing_outputs",
            "_refresh_equipment_recommendations_for_current_objects",
            "_refresh_weather_from_timer",
            "_start_weather_refresh",
            "_refresh_local_atmosphere",
            "_schedule_nasa_aod_refresh",
            "_schedule_viirs_sky_quality_refresh",
        )
        for method_name in heavy_methods:
            setattr(controller, method_name, Mock(side_effect=AssertionError(method_name)))

        controller._refresh_sky_compass_live()

        self.assertEqual(engine.calls, 1)
        controller._sky_compass_candidates.assert_not_called()
        for method_name in heavy_methods:
            getattr(controller, method_name).assert_not_called()

    def test_live_refresh_does_not_use_observation_conditions_service(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, engine, _timer = _controller([target])
        controller._conditions_service = Mock()

        controller._refresh_sky_compass_live()

        self.assertEqual(engine.calls, 1)
        controller._conditions_service.assert_not_called()
        self.assertEqual(controller._conditions_service.method_calls, [])

    def test_live_refresh_uses_stored_candidate_snapshot(self) -> None:
        live_target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        stale_current_target = _object("saturn", "Saturno", "Pianeta", "Ovest", 90)
        controller, engine, _timer = _controller([live_target])
        controller._sky_compass_candidates = Mock(return_value=[stale_current_target])

        controller._refresh_sky_compass_live()

        controller._sky_compass_candidates.assert_not_called()
        self.assertEqual([item.id for item in engine.last_objects], ["mars"])
        self.assertEqual(controller._sky_compass["primaryTargets"][0]["id"], "mars")

    def test_normal_refresh_updates_candidate_snapshot(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, _engine, timer = _controller([])
        controller._sky_compass_candidates = Mock(return_value=[target])

        controller._refresh_sky_compass()

        controller._sky_compass_candidates.assert_called_once()
        self.assertEqual(controller._sky_compass_candidate_snapshot, [target])
        self.assertEqual(controller._sky_compass["primaryTargets"][0]["id"], "mars")
        self.assertTrue(timer.isActive())

    def test_live_refresh_emits_only_sky_compass_signal(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, _engine, _timer = _controller([target])
        signal_counts = {
            "sky": 0,
            "data": 0,
            "weather": 0,
            "equipment": 0,
            "observation": 0,
        }
        controller.skyCompassChanged.connect(lambda: signal_counts.__setitem__("sky", signal_counts["sky"] + 1))
        controller.dataChanged.connect(lambda: signal_counts.__setitem__("data", signal_counts["data"] + 1))
        controller.weatherChanged.connect(lambda: signal_counts.__setitem__("weather", signal_counts["weather"] + 1))
        controller.equipmentChanged.connect(
            lambda: signal_counts.__setitem__("equipment", signal_counts["equipment"] + 1)
        )
        controller.observationChanged.connect(
            lambda: signal_counts.__setitem__("observation", signal_counts["observation"] + 1)
        )

        controller._refresh_sky_compass_live()

        self.assertEqual(signal_counts, {"sky": 1, "data": 0, "weather": 0, "equipment": 0, "observation": 0})

    def test_live_refresh_updates_positional_fields_only_in_snapshot(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, _engine, _timer = _controller([target])

        controller._refresh_sky_compass_live()

        updated = controller._sky_compass_candidate_snapshot[0]
        self.assertEqual(updated.id, target.id)
        self.assertEqual(updated.name, target.name)
        self.assertEqual(updated.object_type, target.object_type)
        self.assertEqual(updated.score, target.score)
        self.assertEqual(updated.recommended_setup, target.recommended_setup)
        self.assertEqual(updated.best_time, target.best_time)
        self.assertEqual(updated.observing_window, target.observing_window)
        self.assertEqual(updated.direction, "Est")
        self.assertEqual(updated.azimuth, "90 gradi")
        self.assertEqual(updated.current_altitude, "12.3 gradi")
        self.assertEqual(updated.current_azimuth, "90.0 gradi")
        self.assertTrue(updated.observable_now)
        self.assertEqual(updated.current_altitude_degrees, 12.3)
        self.assertEqual(updated.current_azimuth_degrees, 90.0)

    def test_live_refresh_updates_direction_from_position_engine(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, _engine, _timer = _controller([target])

        controller._refresh_sky_compass_live()

        self.assertEqual(controller._sky_compass["direction"], "Est")
        self.assertEqual(controller._sky_compass["primaryTargets"][0]["name"], "Marte")

    def test_live_refresh_schedules_work_without_running_engine_inline(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, engine, _timer = _controller([target])
        tasks = []
        controller._start_background_task = tasks.append

        controller._refresh_sky_compass_live()

        self.assertEqual(engine.calls, 0)
        self.assertTrue(controller._sky_compass_live_refresh_running)
        self.assertEqual(len(tasks), 1)

        tasks[0]()

        self.assertEqual(engine.calls, 1)
        self.assertFalse(controller._sky_compass_live_refresh_running)
        self.assertEqual(controller._sky_compass["direction"], "Est")

    def test_live_refresh_skips_duplicate_tick_while_worker_is_running(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, engine, _timer = _controller([target])
        tasks = []
        controller._start_background_task = tasks.append

        controller._refresh_sky_compass_live()
        controller._refresh_sky_compass_live()

        self.assertEqual(engine.calls, 0)
        self.assertEqual(len(tasks), 1)

    def test_full_refresh_discards_in_flight_live_result(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, _engine, _timer = _controller([target])
        tasks = []
        controller._start_background_task = tasks.append

        controller._refresh_sky_compass_live()
        controller._refresh_sky_compass()
        tasks[0]()

        self.assertFalse(controller._sky_compass_live_refresh_running)
        self.assertEqual(controller._sky_compass_candidate_snapshot[0].direction, "Sud")
        self.assertEqual(controller._sky_compass["direction"], "Sud")

    def test_live_refresh_is_safe_without_targets(self) -> None:
        controller, engine, _timer = _controller([])
        signal_events = []
        controller.skyCompassChanged.connect(lambda: signal_events.append("sky"))

        controller._refresh_sky_compass_live()

        self.assertEqual(engine.calls, 0)
        controller._sky_compass_candidates.assert_not_called()
        self.assertEqual(controller._refresh_manager.snapshot(), frozenset())
        self.assertEqual(signal_events, [])

    def test_live_refresh_is_safe_without_snapshot(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, engine, timer = _controller([target])
        controller._sky_compass_candidate_snapshot = []
        signal_events = []
        controller.skyCompassChanged.connect(lambda: signal_events.append("sky"))

        controller._refresh_sky_compass_live()

        self.assertEqual(engine.calls, 0)
        controller._sky_compass_candidates.assert_not_called()
        self.assertEqual(controller._refresh_manager.snapshot(), frozenset())
        self.assertEqual(signal_events, [])
        self.assertFalse(timer.isActive())

    def test_timer_setup_does_not_create_duplicate_timers(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, _engine, timer = _controller([target])

        controller._update_sky_compass_live_timer()
        controller._update_sky_compass_live_timer()

        self.assertTrue(timer.isActive())
        self.assertEqual(timer.start_count, 1)

        controller._set_sky_compass(SkyCompassService.empty("no_targets", "Nessun target."))

        self.assertTrue(timer.isActive())
        self.assertEqual(timer.stop_count, 0)

        controller._sky_compass_candidate_snapshot = []
        controller._update_sky_compass_live_timer()

        self.assertFalse(timer.isActive())
        self.assertEqual(timer.stop_count, 1)

    def test_live_refresh_continues_from_an_empty_current_compass_state(self) -> None:
        target = _object("mars", "Marte", "Pianeta", "Sud", 80)
        controller, engine, timer = _controller([target])
        controller._sky_compass = SkyCompassService.empty("no_targets", "Nessun target osservabile ora.")

        controller._refresh_sky_compass_live()

        self.assertEqual(engine.calls, 1)
        self.assertTrue(controller._sky_compass["available"])
        self.assertTrue(timer.isActive())

    def test_full_refresh_still_uses_existing_heavy_refresh_branches(self) -> None:
        source = inspect.getsource(AppController._refresh_all)

        self.assertIn("self._start_astronomy_refresh(ASTRONOMY_REFRESH_FULL)", source)
        self.assertIn("self._refresh_astronomy()", source)
        self.assertIn("self._refresh_no_location_context()", source)
        self.assertNotIn("_refresh_sky_compass_live", source)


class _PositionEngine:
    def __init__(self) -> None:
        self.calls = 0
        self.last_objects: list[CelestialObject] = []

    def refresh_current_positions(
        self,
        objects: list[CelestialObject],
        _location: ObserverLocation,
    ) -> list[CelestialObject]:
        self.calls += 1
        self.last_objects = list(objects)
        return [
            replace(
                item,
                direction="Est",
                azimuth="90 gradi",
                current_altitude="12.3 gradi",
                current_azimuth="90.0 gradi",
                observable_now=True,
                current_altitude_degrees=12.3,
                current_azimuth_degrees=90.0,
            )
            for item in objects
        ]


class _FakeTimer:
    def __init__(self) -> None:
        self._active = False
        self.start_count = 0
        self.stop_count = 0

    def isActive(self) -> bool:
        return self._active

    def start(self) -> None:
        self.start_count += 1
        self._active = True

    def stop(self) -> None:
        self.stop_count += 1
        self._active = False


def _controller(candidates: list[CelestialObject]) -> tuple[AppController, _PositionEngine, _FakeTimer]:
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._skyCompassLiveRefreshFinished.connect(controller._finish_sky_compass_live_refresh)
    engine = _PositionEngine()
    timer = _FakeTimer()
    controller._location = ObserverLocation("Test", "Earth", 0.0, 0.0, "UTC")
    controller._astronomy_engine = engine
    controller._refresh_manager = RefreshManager()
    controller._sky_compass_service = SkyCompassService()
    controller._sky_quality = None
    controller._moon = None
    controller._sky_compass_nsom_direction_service = SkyCompassNsomDirectionService()
    controller._sky_compass_live_timer = timer
    controller._sky_compass_live_refresh_running = False
    controller._sky_compass_live_refresh_request_id = 0
    controller._start_background_task = lambda target: target()
    controller._night_plan = []
    controller._best_object = candidates[0] if candidates else None
    controller._weather_summary = None
    controller._visible_planets = []
    controller._deep_sky = []
    controller._sky_compass_candidates = Mock(return_value=candidates)
    controller._sky_compass_caution_text = Mock(return_value="")
    controller._sky_compass_candidate_snapshot = list(candidates)
    controller._sky_compass = (
        SkyCompassService().compass(candidates, [], controller._best_object, has_location=True)
        if candidates
        else {"available": True}
    )
    return controller, engine, timer


def _object(object_id: str, name: str, object_type: str, direction: str, score: int) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="",
        distance="",
        max_altitude="45 gradi",
        direction=direction,
        best_time="22:00",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="",
        time_above_horizon="3 h",
        visible=True,
        score=score,
        difficulty="Media",
    )

if __name__ == "__main__":
    unittest.main()
