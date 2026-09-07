"""Protect detached observing calculations, publication and latest-request semantics."""

from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
from threading import Event, Thread, get_ident
from time import monotonic, sleep
from types import SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest
from PySide6.QtCore import QCoreApplication, QTimer

from astro_viewer.app.application.observing_refresh import (
    SERVICE_FIELDS, STATE_FIELDS, ObservingRefreshCalculation, ObservingRefreshCancelled,
)
from astro_viewer.app.astronomy.engine import ObserverLocation, ObservingNightWindow
from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.models.observing import MoonGeometrySummary
from astro_viewer.app.services.refresh_lifecycle import RefreshDomain, RefreshReason
from astro_viewer.tests.test_catalogue_recommendation_workflow import _target
from astro_viewer.tests.test_phase6_real_data import _controller, _set_profile_equipment
from astro_viewer.app.viewmodels.observing_refresh_coordinator import ObservingRefreshCoordinator, ObservingRefreshRequest


@pytest.fixture
def observing_controller():
    with _controller() as controller:
        controller._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
        start = datetime(2026, 9, 7, 20, tzinfo=ZoneInfo("Europe/Rome"))
        controller._observing_night_window = ObservingNightWindow.bounded(start, start + timedelta(hours=10))
        planet = replace(_target("jupiter", best_time="23:00", object_type="Pianeta"), direction="Nord", score=72)
        targets = [replace(_target(f"deep-{index}", best_time="23:00" if index != 3 else ""),
                           direction="Est", score=65 + index, magnitude="6.0", apparent_size="20 arcmin",
                           max_altitude="50°", night_eligible=False if index == 2 else None) for index in range(4)]
        controller._base_solar_system_objects = [planet]
        controller._solar_system_objects = [planet]
        controller._visible_planets = [planet]
        controller._base_deep_sky = targets
        controller._deep_sky = list(targets)
        controller._deep_sky_raw_condition_input_by_id = {item.id: item for item in targets}
        controller._recommendation_enabled_by_object_id = {"deep-1": False}
        controller._moon_geometry_condition_cache = {item.id: None for item in [planet, *targets]}
        controller._weather_summary = WeatherSummary("Ottimo", 90, "Test", 5, 0, 3, 40, 15.0, "")
        controller._sky_quality = SkyQuality(3, 6.5, 21.5, "test", "Test")
        controller._seeing_transparency = SeeingTransparency("Buono", "Buona", 80, 90, "Test")
        controller._catalogue_visibility_cache[controller._catalogue_visibility_cache_key()] = {
            str(item["object_id"]): True for item in controller._catalogue_objects
        }
        yield controller


def calculation(controller, **kwargs):
    return ObservingRefreshCalculation(
        controller._capture_observing_refresh(**kwargs),
        {name: getattr(controller, name) for name in SERVICE_FIELDS},
        controller._astronomy_engine, controller._astronomy_engine_lock_instance(),
    )


@pytest.mark.parametrize("rebuild,pollution,outputs", [(True, False, True), (True, True, True),
                                                      (False, False, True), (True, True, False)])
@pytest.mark.parametrize("optical", [False, True])
def test_detached_refresh_matches_all_synchronous_outputs(observing_controller, rebuild, pollution, outputs, optical):
    controller = observing_controller
    if optical:
        _set_profile_equipment(controller, telescopes=controller._telescopes[:1], eyepieces=controller._eyepieces[:2])
    if not outputs:
        controller._weather_summary = None
    worker = calculation(controller, rebuild_equipment=rebuild, apply_pollution=pollution, recalculate_outputs=outputs)
    before = deepcopy(worker.inputs.state)
    worker.calculate()
    # A worker cannot publish even partial list/read-model changes into the host.
    assert {name: getattr(controller, name) for name in STATE_FIELDS} == before
    if rebuild:
        controller._refresh_equipment_recommendations_for_current_objects(refresh_conditioned=False)
    if pollution:
        controller._deep_sky = controller._apply_deep_sky_pollution_context(controller._deep_sky)
    if outputs:
        controller._recalculate_observing_outputs()
    else:
        controller._refresh_conditioned_observing_candidates()
        controller._best_object = None
        controller._night_plan = []
        controller._refresh_sky_compass()
    for name, result in worker.results().items():
        assert result == getattr(controller, name), name
    assert worker.sky_compass == controller._sky_compass
    assert worker.sky_compass_candidates == controller._sky_compass_candidate_snapshot
    assert worker.inputs.state == before


def test_worker_cancellation_prevents_equipment_and_publication(observing_controller):
    worker = calculation(observing_controller, rebuild_equipment=True, apply_pollution=False)
    cancelled = Event()
    cancelled.set()
    worker._cancelled = cancelled.is_set
    with pytest.raises(ObservingRefreshCancelled):
        worker.calculate()
    assert worker.results() == worker.inputs.state


@pytest.fixture
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def coordinator_probe():
    state, tasks, captured, published, failures = {"value": 1}, [], [], [], []

    def capture(requests, cancelled):
        value = state["value"]
        captured.append((tuple(requests), value))
        return SimpleNamespace(calculate=lambda: None if cancelled() else value)

    coordinator = ObservingRefreshCoordinator(
        capture=capture, signature=lambda _requests: state["value"],
        publish=lambda result, requests: published.append((tuple(requests), result)),
        failure=lambda error, requests: failures.append((error, tuple(requests))), start_worker=tasks.append,
    )
    return coordinator, state, tasks, captured, published, failures


def test_coordinator_coalesces_requests_and_never_runs_a_second_worker(qt_app):
    coordinator, state, tasks, captured, published, failures = coordinator_probe()
    coordinator.request("profile", ObservingRefreshRequest(rebuild_equipment=True, apply_pollution=True))
    coordinator._start()
    for value in range(2, 12):
        state["value"] = value
        coordinator.request("weather", ObservingRefreshRequest(rebuild_equipment=True))
        coordinator._start()
    assert len(tasks) == 1
    tasks.pop(0)()
    assert not published
    coordinator._start()
    assert len(tasks) == 1
    tasks.pop(0)()
    assert captured == [(('profile',), 1), (('profile', 'weather'), 11)]
    assert published == [(('profile', 'weather'), 11)]
    assert not coordinator.active
    assert not failures


@pytest.mark.parametrize("cancel", [False, True])
def test_coordinator_drops_stale_context_or_cancelled_work(qt_app, cancel):
    coordinator, state, tasks, _captured, published, failures = coordinator_probe()
    coordinator.request("month", ObservingRefreshRequest(month=10))
    coordinator._start()
    if cancel:
        coordinator.cancel("month")
    else:
        state["value"] = 2
    tasks.pop(0)()
    assert not published
    assert not failures
    coordinator._start()
    if cancel:
        assert not tasks and not coordinator.active
    else:
        tasks.pop(0)()
        assert published == [(('month',), 2)]


def test_async_cached_month_keeps_selection_until_complete_and_matches_sync(qt_app, observing_controller):
    controller = observing_controller
    old_month = controller._catalogue_selected_month
    month = old_month % 12 + 1
    cache_key = (*controller._catalogue_visibility_cache_key()[:4], month,
                 controller._catalogue_visibility_cache_key()[-1])
    controller._catalogue_visibility_cache[cache_key] = dict(controller._catalogue_visibility_map())
    expected = calculation(controller, rebuild_equipment=True, apply_pollution=False, month=month).calculate()
    tasks = []
    controller._start_background_task = tasks.append
    controller._enable_observing_refresh()
    controller.requestCatalogueMonth(month)
    assert controller._catalogue_selected_month == old_month
    assert controller.catalogueMonthRefreshActive
    controller._observing_refresh_coordinator._start()
    assert len(tasks) == 1
    tasks.pop(0)()
    assert controller._catalogue_selected_month == month
    assert not controller.catalogueMonthRefreshActive
    for name, value in expected.results().items():
        assert value == getattr(controller, name), name
    assert controller._sky_compass_service._live_direction == expected._sky_compass_service._live_direction


def test_async_conditions_and_profile_publish_on_latest_context(qt_app, observing_controller):
    controller = observing_controller
    tasks = []
    controller._start_background_task = tasks.append
    controller._enable_observing_refresh()
    controller._complete_profile_publication = Mock()
    controller._complete_condition_provider_publication = Mock()
    controller._refresh_active_profile_dependencies()
    coordinator = controller._observing_refresh_coordinator
    coordinator._start()
    controller._sky_quality = SkyQuality(7, 4.0, 18.0, "test", "Updated")
    controller._recalculate_after_condition_provider_refresh()
    assert len(tasks) == 1
    tasks.pop(0)()
    controller._complete_profile_publication.assert_not_called()
    expected = calculation(controller, rebuild_equipment=True, apply_pollution=True).calculate()
    coordinator._start()
    tasks.pop(0)()
    for name, value in expected.results().items():
        assert value == getattr(controller, name), name
    controller._complete_profile_publication.assert_called_once()
    controller._complete_condition_provider_publication.assert_called_once()


@pytest.mark.parametrize("stale", [False, True])
def test_detail_getters_never_take_the_engine_lock_or_cache_pending_as_failure(qt_app, observing_controller, stale):
    controller = observing_controller
    tasks = []
    controller._start_background_task = tasks.append
    controller._enable_observing_refresh()
    controller._catalogue_visibility_cache.clear()
    controller._catalogue_current_month_visibility_cache.clear()
    controller._moon_geometry_condition_cache.clear()
    target = controller._solar_system_objects[0]
    summary = MoonGeometrySummary(target.id, moon_altitude_deg=25., moon_target_separation_deg=50.)
    engine = Mock()
    engine.moon_geometry.return_value = summary
    engine.catalogue_month_visibility.side_effect = lambda rows, *_args: {row["object_id"]: True for row in rows}
    controller._astronomy_engine = engine
    for _ in range(5):
        assert controller._moon_geometry_condition_input(target) is None
        assert controller._catalogue_object_visible_current_month("messier-M31")[0] is None
    engine.moon_geometry.assert_not_called()
    engine.catalogue_month_visibility.assert_not_called()
    assert target.id not in controller._moon_geometry_condition_cache
    assert not controller._catalogue_current_month_visibility_cache
    controller._start_detail_geometry()
    assert len(tasks) == 1
    if stale:
        controller._invalidate_detail_geometry()
    tasks.pop(0)()
    if stale:
        assert target.id not in controller._moon_geometry_condition_cache
        assert not controller._catalogue_current_month_visibility_cache
        engine.moon_geometry.assert_not_called()
    else:
        assert controller._moon_geometry_condition_input(target).moon_altitude_deg == 25.
        assert controller._catalogue_object_visible_current_month("messier-M31")[0] is True
        engine.moon_geometry.assert_called_once()
        engine.catalogue_month_visibility.assert_called_once()


def test_async_failed_current_month_can_retry_through_both_preparation_phases(qt_app, observing_controller):
    controller = observing_controller
    tasks = []
    controller._start_background_task = tasks.append
    controller._enable_observing_refresh()
    key = controller._catalogue_visibility_cache_key()
    controller._cache_catalogue_month_visibility(key, None)
    engine = Mock()
    engine.catalogue_month_visibility.return_value = {"jupiter": True}
    controller._astronomy_engine = engine
    controller.requestCatalogueMonth(controller._catalogue_selected_month)
    assert len(tasks) == 1
    tasks.pop(0)()
    assert controller.catalogueMonthRefreshActive
    coordinator = controller._observing_refresh_coordinator
    assert coordinator.has_request("month")
    coordinator._start()
    tasks.pop(0)()
    assert not coordinator.active
    assert not controller.catalogueMonthRefreshActive
    assert controller._catalogue_visibility_cache[key] == {"jupiter": True}
    engine.catalogue_month_visibility.assert_called_once()


def test_calculation_rechecks_cancellation_after_acquiring_engine_lock(observing_controller):
    controller = observing_controller
    controller._moon_geometry_condition_cache.clear()
    worker = calculation(controller, rebuild_equipment=True, apply_pollution=False)
    cancelled = Event()
    worker._cancelled = cancelled.is_set

    class CancellingLock:
        def __enter__(self):
            cancelled.set()

        def __exit__(self, *_args):
            return False

    worker._engine_lock = CancellingLock()
    worker._astronomy_engine = Mock()
    with pytest.raises(ObservingRefreshCancelled):
        worker.calculate()
    worker._astronomy_engine.moon_geometry_batch.assert_not_called()


@pytest.mark.parametrize("failure", ["capture", "start", "calculate"])
def test_coordinator_failures_release_busy_state_and_allow_a_new_request(qt_app, failure):
    coordinator, _state, tasks, _captured, published, failures = coordinator_probe()
    original_capture, original_start = coordinator._capture, coordinator._start_worker
    if failure == "capture":
        coordinator._capture = Mock(side_effect=RuntimeError("capture"))
    elif failure == "start":
        coordinator._start_worker = Mock(side_effect=RuntimeError("start"))
    else:
        coordinator._capture = lambda *_args: SimpleNamespace(calculate=Mock(side_effect=RuntimeError("calculation")))
    coordinator.request("weather", ObservingRefreshRequest())
    coordinator._start()
    if tasks:
        tasks.pop(0)()
    assert len(failures) == 1 and not published and not coordinator.active
    coordinator._capture, coordinator._start_worker = original_capture, original_start
    coordinator.request("weather", ObservingRefreshRequest())
    coordinator._start()
    tasks.pop(0)()
    assert published == [(('weather',), 1)]


def test_real_worker_keeps_qt_responsive_and_publishes_only_on_qt(qt_app, observing_controller):
    controller = observing_controller
    main_thread = get_ident()
    entered, release = Event(), Event()
    threads, calculation_threads, publication_threads, heartbeats = [], [], [], []
    worker = calculation(controller, rebuild_equipment=True, apply_pollution=False)
    original_suggest = worker._equipment_service.suggest_for_profile

    def suggest(*args):
        calculation_threads.append(get_ident())
        entered.set()
        assert release.wait(5), "test must release the worker"
        return original_suggest(*args)

    worker._equipment_service = SimpleNamespace(suggest_for_profile=suggest)

    def start(target):
        thread = Thread(target=target, daemon=True)
        threads.append(thread)
        thread.start()

    coordinator = ObservingRefreshCoordinator(
        capture=lambda *_args: worker, signature=lambda _requests: 1,
        publish=lambda *_args: publication_threads.append(get_ident()),
        failure=lambda error, _requests: pytest.fail(str(error)), start_worker=start,
    )
    timer = QTimer()
    timer.setInterval(1)
    timer.timeout.connect(lambda: heartbeats.append(get_ident()))
    timer.start()
    try:
        coordinator.request("weather", ObservingRefreshRequest(rebuild_equipment=True))
        deadline = monotonic() + 5
        while (not entered.is_set() or len(heartbeats) < 5) and monotonic() < deadline:
            qt_app.processEvents()
            sleep(.002)
        assert entered.is_set() and len(heartbeats) >= 5
        assert coordinator.active and not publication_threads
        release.set()
        while coordinator.active and monotonic() < deadline:
            qt_app.processEvents()
            sleep(.002)
        assert not coordinator.active
        assert publication_threads == [main_thread]
        assert set(heartbeats) == {main_thread}
        assert calculation_threads and main_thread not in calculation_threads
    finally:
        release.set()
        timer.stop()
        for thread in threads:
            thread.join(timeout=5)
        coordinator.cancel()


def test_failed_observing_refresh_keeps_outputs_and_weather_cadence(qt_app, observing_controller):
    controller = observing_controller
    controller._enable_observing_refresh()
    coordinator = controller._observing_refresh_coordinator
    coordinator._capture = Mock(side_effect=RuntimeError("injected failure"))
    controller._schedule_next_weather_refresh = Mock()
    controller._refresh_local_atmosphere = Mock()
    controller._mark_refresh_dirty(RefreshReason.WEATHER_COMPLETED)
    before = {name: getattr(controller, name) for name in STATE_FIELDS}
    month = controller._catalogue_selected_month
    publish_month = Mock()
    controller._queue_observing_update("month", month=month % 12 + 1, completion=publish_month)
    controller._complete_weather_refresh("weather unavailable", True)
    coordinator._start()
    assert not controller.isLoading and not controller.catalogueMonthRefreshActive
    assert {name: getattr(controller, name) for name in STATE_FIELDS} == before
    assert controller._catalogue_selected_month == month
    publish_month.assert_not_called()
    controller._schedule_next_weather_refresh.assert_called_once_with(retry_soon=True)
    assert not controller._refresh_lifecycle().is_dirty(RefreshDomain.WEATHER)
    assert not controller._refresh_lifecycle().is_dirty(RefreshDomain.EQUIPMENT)
    assert "dati esistenti" in controller._service_status


@pytest.mark.parametrize("shutdown", [False, True])
def test_language_change_or_shutdown_prevents_stale_observing_publication(qt_app, observing_controller, shutdown):
    controller = observing_controller
    tasks, publications = [], []
    controller._start_background_task = tasks.append
    controller._enable_observing_refresh()
    coordinator = controller._observing_refresh_coordinator
    coordinator._publish = lambda *_args: publications.append(True)
    controller._queue_observing_update("conditions")
    coordinator._start()
    if shutdown:
        controller.stopPerformanceWorkers()
    else:
        controller._presentation_generation = getattr(controller, "_presentation_generation", 0) + 1
    tasks.pop(0)()
    assert not publications
    coordinator._start()
    if shutdown:
        assert not tasks and not coordinator.active
    else:
        tasks.pop(0)()
        assert publications == [True]


@pytest.mark.parametrize("failure", ["signature", "publication"])
def test_publication_boundary_failure_releases_coordinator(qt_app, failure):
    coordinator, _state, tasks, _captured, _published, failures = coordinator_probe()
    coordinator.request("weather", ObservingRefreshRequest())
    coordinator._start()
    if failure == "signature":
        coordinator._signature = Mock(side_effect=RuntimeError("signature"))
    else:
        coordinator._publish = Mock(side_effect=RuntimeError("publication"))
    tasks.pop(0)()
    assert not coordinator.active and len(failures) == 1
