from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from threading import Event, get_ident
from unittest.mock import Mock

from PySide6.QtCore import QCoreApplication, QObject

from astro_viewer.app.astronomy.engine import ObserverLocation, ObservingNightWindow
from astro_viewer.app.models.observing import (
    AstronomicalEvent,
    CelestialObject,
    MoonGeometrySummary,
    MoonSummary,
)
from astro_viewer.app.services.observation_conditions_service import MoonGeometryConditionInput
from astro_viewer.app.services.refresh_lifecycle import RefreshManager
from astro_viewer.app.viewmodels.app_controller import (
    ASTRONOMY_REFRESH_FULL,
    ASTRONOMY_REFRESH_NIGHT_ROLLOVER,
    ASTRONOMY_REFRESH_VIIRS_DEEP_SKY,
    AppController,
    AstronomyRefreshSnapshot,
)


def test_astronomy_refresh_schedules_engine_work_without_running_inline() -> None:
    controller, engine = _controller()
    tasks = []
    controller._start_background_task = tasks.append

    started = controller._start_astronomy_refresh(
        ASTRONOMY_REFRESH_VIIRS_DEEP_SKY,
        context="VIIRS ready",
    )

    assert started is True
    assert engine.deep_sky_calls == 0
    assert controller._astronomy_refresh_running is True
    assert len(tasks) == 1

    tasks[0]()

    assert engine.deep_sky_calls == 1
    assert controller._astronomy_refresh_running is False
    snapshot, message = controller._finish_viirs_deep_sky_refresh.call_args.args
    assert snapshot.deep_sky[0].id == "messier-M13"
    assert message == "VIIRS ready"


def test_astronomy_refresh_calculates_off_thread_and_applies_on_qt_thread() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    controller, engine = _controller()
    main_thread_id = get_ident()
    finish_thread_ids = []
    controller._finish_viirs_deep_sky_refresh.side_effect = (
        lambda _snapshot, _message: finish_thread_ids.append(get_ident())
    )

    controller._start_astronomy_refresh(ASTRONOMY_REFRESH_VIIRS_DEEP_SKY)

    deadline = time.monotonic() + 3.0
    while controller._astronomy_refresh_running and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()

    assert engine.worker_thread_id is not None
    assert engine.worker_thread_id != main_thread_id
    assert finish_thread_ids == [main_thread_id]


def test_astronomy_refresh_discards_stale_request_result() -> None:
    controller, _engine = _controller()
    tasks = []
    controller._start_background_task = tasks.append

    controller._start_astronomy_refresh(ASTRONOMY_REFRESH_VIIRS_DEEP_SKY, context="old")
    controller._start_astronomy_refresh(ASTRONOMY_REFRESH_VIIRS_DEEP_SKY, context="new")

    tasks[0]()
    controller._finish_viirs_deep_sky_refresh.assert_not_called()

    tasks[1]()
    controller._finish_viirs_deep_sky_refresh.assert_called_once()
    assert controller._finish_viirs_deep_sky_refresh.call_args.args[1] == "new"


def test_full_astronomy_refresh_builds_snapshot_before_weather_continuation() -> None:
    controller, _engine = _controller()
    tasks = []
    controller._start_background_task = tasks.append
    controller._apply_astronomy_snapshot = Mock()
    controller._refresh_weather_and_conditions = Mock(return_value=False)
    controller._complete_refresh_all = Mock()

    controller._start_astronomy_refresh(ASTRONOMY_REFRESH_FULL)
    tasks[0]()

    snapshot = controller._apply_astronomy_snapshot.call_args.args[0]
    assert snapshot.observing_night_window.has_observing_window is True
    assert snapshot.solar_system_objects[0].id == "mars"
    assert snapshot.deep_sky[0].id == "messier-M13"
    assert {object_id for object_id, _summary in snapshot.moon_geometry} == {
        "mars",
        "messier-M13",
    }
    controller._refresh_weather_and_conditions.assert_called_once()
    controller._complete_refresh_all.assert_called_once()


def test_initial_weather_continuation_delegates_network_work_to_worker() -> None:
    controller, _engine = _controller()
    controller._weather_refresh_request_id = 0
    controller._weather_refresh_running = False
    controller._weather_full_refresh_request_id = None
    controller._weather_hours = []
    controller._weather_status = ""
    controller._moon = None
    controller._weather_service = Mock()
    controller._score_service = Mock()
    controller._score_service.weather_score.return_value = Mock()
    controller._light_pollution_service = Mock()
    controller._light_pollution_service.sky_quality.return_value = Mock()
    controller._seeing_service = Mock()
    controller._refresh_local_atmosphere = Mock()
    controller._schedule_viirs_sky_quality_refresh = Mock()
    controller._schedule_nasa_aod_refresh = Mock()
    controller._start_weather_refresh = Mock(return_value=True)

    started = controller._refresh_weather_and_conditions()

    assert started is True
    controller._weather_service.hourly_forecast.assert_not_called()
    controller._start_weather_refresh.assert_called_once_with(
        force_refresh=False,
        complete_full_refresh=True,
    )


def test_weather_service_call_runs_outside_controller_thread() -> None:
    controller, _engine = _controller()
    controller._weather_refresh_timer = Mock()
    controller._startup_location_detection_running = False
    controller._weather_retry_pending = False
    controller._weather_refresh_request_id = 0
    controller._weather_refresh_running = False
    controller._weather_full_refresh_request_id = None
    worker_started = Event()
    worker_finished = Event()
    worker_thread_ids = []

    def hourly_forecast(_location, *, force_refresh=False):
        worker_thread_ids.append(get_ident())
        worker_started.set()
        worker_finished.set()
        return []

    controller._weather_service = Mock(
        hourly_forecast=Mock(side_effect=hourly_forecast),
        last_error="",
        retry_recommended=False,
    )

    started = controller._start_weather_refresh(force_refresh=False)

    assert started is True
    assert worker_started.wait(1.0)
    assert worker_finished.wait(1.0)
    assert len(worker_thread_ids) == 1
    assert worker_thread_ids[0] != get_ident()


def test_full_refresh_loading_finishes_after_weather_completion() -> None:
    controller, _engine = _controller()
    controller._weather_refresh_request_id = 12
    controller._weather_full_refresh_request_id = 12
    controller._weather_refresh_running = True
    controller._weather_hours = []
    controller._weather_status = ""
    controller._update_observing_night_window = Mock(return_value=False)
    controller._complete_weather_refresh = Mock()
    controller._complete_refresh_all = Mock()

    controller._finish_weather_refresh(
        12,
        "41.900:12.500:roma",
        [],
        "",
        False,
    )

    controller._complete_weather_refresh.assert_called_once_with("", False)
    controller._complete_refresh_all.assert_called_once_with()
    assert controller._weather_full_refresh_request_id is None


def test_night_rollover_continues_weather_refresh_after_snapshot_application() -> None:
    controller, _engine = _controller()
    tasks = []
    controller._start_background_task = tasks.append
    controller._apply_astronomy_snapshot = Mock()
    controller._complete_weather_refresh = Mock()

    controller._start_astronomy_refresh(
        ASTRONOMY_REFRESH_NIGHT_ROLLOVER,
        context=("temporary error", True),
    )
    tasks[0]()

    controller._apply_astronomy_snapshot.assert_called_once()
    controller._complete_weather_refresh.assert_called_once_with("temporary error", True)


def test_astronomy_snapshot_preloads_geometry_and_catalogue_visibility() -> None:
    controller, _engine = _controller()
    controller._catalogue_visibility_cache = {}
    controller._moon_geometry_condition_cache = {}
    controller._refresh_equipment_recommendations_for_current_objects = Mock()
    cache_key = (41.9, 12.5, "Europe/Rome", 2026, 7, 15.0)
    target = _target("messier-M13", "M13", "Ammasso globulare")
    summary = MoonGeometrySummary(
        object_id=target.id,
        moon_altitude_deg=35.0,
        moon_target_separation_deg=80.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
        moon_set_before_target_window=False,
    )
    snapshot = AstronomyRefreshSnapshot(
        observing_night_window=ObservingNightWindow.bounded(
            datetime(2026, 7, 11, 20, 0, tzinfo=UTC),
            datetime(2026, 7, 12, 5, 0, tzinfo=UTC),
        ),
        deep_sky=(target,),
        moon=MoonSummary("Crescente", "20%", "20:00", "05:00", "", ""),
        moon_geometry=((target.id, summary),),
        catalogue_visibility_cache_key=cache_key,
        catalogue_visibility=((target.id, True),),
    )

    controller._apply_astronomy_snapshot(snapshot)

    assert controller._moon_geometry_condition_cache[target.id] == MoonGeometryConditionInput(
        moon_altitude_deg=35.0,
        moon_target_separation_deg=80.0,
        moon_above_horizon=True,
        moon_visible_during_target_window=True,
        moon_set_before_target_window=False,
    )
    assert controller._catalogue_visibility_cache[cache_key] == {target.id: True}
    controller._refresh_equipment_recommendations_for_current_objects.assert_called_once()


def test_transient_event_refresh_prepares_without_lock_and_schedules_next_run() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    assert app is not None
    controller, _engine = _controller()
    tasks = []
    lock = _TrackingLock()
    transient_engine = _TransientAstronomyEngine(lock)
    controller._astronomy_engine = transient_engine
    controller._astronomy_engine_lock_instance = lambda: lock
    controller._start_background_task = tasks.append
    controller._events = [_calendar_event("annual", "annual_astronomy")]

    assert controller._start_transient_event_refresh() is True
    assert transient_engine.calls == []
    assert len(tasks) == 1

    tasks[0]()

    assert transient_engine.calls == ["prepare_unlocked", "build_locked"]
    assert [event.id for event in controller._events] == ["annual", "iss"]
    assert controller._transient_events_location_key == "41.900:12.500:roma"
    controller._transient_event_refresh_timer.start.assert_called_once_with(3_600_000)


def _controller() -> tuple[AppController, _AstronomyEngine]:
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._astronomyRefreshFinished.connect(controller._finish_astronomy_refresh)
    controller._transientEventsRefreshFinished.connect(
        controller._finish_transient_event_refresh
    )
    controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
    controller._astronomy_engine = _AstronomyEngine()
    controller._astronomy_refresh_running = False
    controller._astronomy_refresh_request_id = 0
    controller._transient_event_refresh_running = False
    controller._transient_event_refresh_request_id = 0
    controller._transient_event_refresh_timer = Mock()
    controller._transient_events_location_key = ""
    controller._events = []
    controller._sky_compass_live_refresh_running = False
    controller._sky_compass_live_refresh_request_id = 0
    controller._refresh_manager = RefreshManager()
    controller._moon_geometry_condition_cache = {}
    controller._catalogue_objects = []
    controller._catalogue_year = 2026
    controller._catalogue_selected_month = 7
    controller._catalogue_visibility_cache = {}
    controller._finish_viirs_deep_sky_refresh = Mock()
    return controller, controller._astronomy_engine


class _AstronomyEngine:
    def __init__(self) -> None:
        self.deep_sky_calls = 0
        self.worker_thread_id: int | None = None

    def observing_night_window(self, _location: ObserverLocation) -> ObservingNightWindow:
        start = datetime(2026, 7, 11, 20, 0, tzinfo=UTC)
        return ObservingNightWindow.bounded(start, start + timedelta(hours=9))

    def solar_system_objects(self, _location: ObserverLocation) -> list[CelestialObject]:
        return [_target("mars", "Marte", "Pianeta")]

    def recommended_deep_sky(self, _location: ObserverLocation) -> list[CelestialObject]:
        self.deep_sky_calls += 1
        self.worker_thread_id = get_ident()
        return [_target("messier-M13", "M13", "Ammasso globulare")]

    def moon_summary(self, _location: ObserverLocation) -> MoonSummary:
        return MoonSummary("Crescente", "20%", "20:00", "05:00", "", "")

    def upcoming_annual_events(self, _location: ObserverLocation) -> list:
        return []

    def upcoming_events(self, _location: ObserverLocation) -> list:
        raise AssertionError("The annual snapshot must not invoke transient sources.")

    def moon_geometry_batch(
        self,
        _location: ObserverLocation,
        targets: list[CelestialObject],
    ) -> dict[str, MoonGeometrySummary]:
        return {target.id: MoonGeometrySummary(target.id) for target in targets}


def _target(object_id: str, name: str, object_type: str) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude="5",
        distance="",
        max_altitude="45 gradi",
        direction="Sud",
        best_time="22:00",
        observing_window="21:00 - 01:00",
        notes="",
        recommended_setup="",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="4 h",
    )


class _TrackingLock:
    def __init__(self) -> None:
        self.active = False

    def __enter__(self):
        assert self.active is False
        self.active = True
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback) -> None:
        self.active = False


class _TransientAstronomyEngine:
    def __init__(self, lock: _TrackingLock) -> None:
        self._lock = lock
        self.calls: list[str] = []

    def prepare_transient_events(self, _location: ObserverLocation) -> object:
        assert self._lock.active is False
        self.calls.append("prepare_unlocked")
        return object()

    def upcoming_transient_events(
        self,
        _location: ObserverLocation,
        _prepared: object,
    ) -> list[AstronomicalEvent]:
        assert self._lock.active is True
        self.calls.append("build_locked")
        return [_calendar_event("iss", "short_horizon_satellite_passes")]

    @staticmethod
    def transient_event_refresh_interval() -> timedelta:
        return timedelta(hours=1)


def _calendar_event(event_id: str, source_code: str) -> AstronomicalEvent:
    return AstronomicalEvent(
        id=event_id,
        title=event_id,
        event_type="Passaggio ISS" if event_id == "iss" else "Luna",
        date_label="11/07/2026",
        best_time="22:00",
        usefulness=0,
        setup="",
        note="",
        event_at=(
            "2026-07-11T22:00:00+00:00"
            if event_id == "iss"
            else "2026-07-11T20:00:00+00:00"
        ),
        source_code=source_code,
    )
