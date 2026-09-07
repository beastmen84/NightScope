"""Protect bounded monthly reuse without changing selected-month or location semantics."""

import time
from threading import Event, get_ident
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QCoreApplication, QObject

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.viewmodels.app_controller import AppController


def controller():
    value = AppController.__new__(AppController)
    QObject.__init__(value)
    value._location = ObserverLocation("Roma", "Italia", 41.9, 12.5, "Europe/Rome")
    value._catalogue_year = 2026
    value._catalogue_selected_month = 9
    value._catalogue_visibility_cache = {}
    value._catalogue_objects = [{"object_id": "M31"}]
    value._selected_object = None
    value._refresh_equipment_recommendations_for_current_objects = Mock()
    value._recalculate_observing_outputs = Mock()
    value._astronomy_engine = Mock()
    value._astronomy_engine.catalogue_month_visibility.side_effect = (
        lambda _objects, _location, _year, month, _threshold: {"M31": month == 9}
    )
    value._catalogueMonthRefreshFinished.connect(value._finish_catalogue_month_refresh)
    return value


def test_month_roundtrip_reuses_geometry_but_retains_recommendation_refresh_contract():
    value = controller()
    september = value._catalogue_visibility_map()
    value.setCatalogueMonth(10)
    assert value._catalogue_visibility_map() == {"M31": False}
    value.setCatalogueMonth(9)
    assert value._catalogue_visibility_map() is september
    assert september == {"M31": True}
    assert value._astronomy_engine.catalogue_month_visibility.call_count == 2
    assert value._recalculate_observing_outputs.call_count == 2
    value._refresh_equipment_recommendations_for_current_objects.assert_called_with(refresh_conditioned=False)
    value.setCatalogueMonth(9)
    value.setCatalogueMonth(0)
    value.setCatalogueMonth(13)
    assert value._recalculate_observing_outputs.call_count == 2


def test_month_cache_is_bounded_and_keeps_location_year_and_explicit_invalidation():
    value = controller()
    for year in (2026, 2027):
        value._catalogue_year = year
        for month in range(1, 13):
            value.setCatalogueMonth(month)
            value._catalogue_visibility_map()
            assert len(value._catalogue_visibility_cache) <= 12
    assert value._astronomy_engine.catalogue_month_visibility.call_count == 24
    value._location = ObserverLocation("Tromso", "Norvegia", 69.6, 18.9, "Europe/Oslo")
    value._catalogue_visibility_map()
    assert value._astronomy_engine.catalogue_month_visibility.call_count == 25
    value._invalidate_catalogue_month_visibility_cache()
    assert not value._catalogue_visibility_cache
    value._catalogue_visibility_map()
    assert value._astronomy_engine.catalogue_month_visibility.call_count == 26


def test_month_cache_without_astronomy_provider_is_also_bounded():
    value = controller()
    value._astronomy_engine = object()
    for year in range(2026, 2040):
        value._catalogue_year = year
        assert value._catalogue_visibility_map() == {}
    assert len(value._catalogue_visibility_cache) == 12


@pytest.fixture
def qt_app():
    return QCoreApplication.instance() or QCoreApplication([])


def test_month_request_prepares_only_geometry_and_publishes_with_current_context(qt_app):
    value = controller()
    tasks = []
    value._start_background_task = tasks.append
    value.requestCatalogueMonth(10)
    assert value.catalogueMonthRefreshActive
    assert value.catalogueSelectedMonth == 9
    assert len(tasks) == 1
    value._astronomy_engine.catalogue_month_visibility.assert_not_called()
    value._recalculate_observing_outputs.assert_not_called()
    value._catalogue_objects[0]["object_id"] = "changed-after-submission"
    current_context = []
    value._weather_status = "latest conditions"
    value._recalculate_observing_outputs.side_effect = lambda: current_context.append(value._weather_status)
    tasks[0]()
    assert value.catalogueSelectedMonth == 10
    assert not value.catalogueMonthRefreshActive
    assert not value._catalogue_month_refresh_running
    assert current_context == ["latest conditions"]
    assert value._catalogue_visibility_map() == {"M31": False}
    assert value._astronomy_engine.catalogue_month_visibility.call_args.args[0] == ({"object_id": "M31"},)
    assert value._astronomy_engine.catalogue_month_visibility.call_count == 1


def test_month_requests_keep_one_worker_and_only_latest_pending_month(qt_app):
    value = controller()
    tasks = []
    value._start_background_task = tasks.append
    for month in (10, 11, 12, 1, 2):
        value.requestCatalogueMonth(month)
    assert len(tasks) == 1
    tasks[0]()
    value._astronomy_engine.catalogue_month_visibility.assert_not_called()
    assert len(tasks) == 2
    assert value.catalogueSelectedMonth == 9
    tasks[1]()
    assert value.catalogueSelectedMonth == 2
    assert not value.catalogueMonthRefreshActive
    assert value._astronomy_engine.catalogue_month_visibility.call_count == 1
    value._recalculate_observing_outputs.assert_called_once()


def test_cached_month_can_publish_while_an_obsolete_worker_is_pending(qt_app):
    value = controller()
    value.setCatalogueMonth(11)
    value._catalogue_visibility_map()
    value.setCatalogueMonth(9)
    tasks = []
    value._start_background_task = tasks.append
    value.requestCatalogueMonth(10)
    value.requestCatalogueMonth(11)
    assert value.catalogueSelectedMonth == 11
    assert not value.catalogueMonthRefreshActive
    assert len(tasks) == 1
    tasks[0]()
    assert value.catalogueSelectedMonth == 11
    assert value._astronomy_engine.catalogue_month_visibility.call_count == 1


@pytest.mark.parametrize("cancel", ["current-month", "synchronous-month", "invalidate", "no-location"])
def test_cancelled_month_request_never_publishes_or_recalculates(qt_app, cancel):
    value = controller()
    tasks = []
    value._start_background_task = tasks.append
    value.requestCatalogueMonth(10)
    if cancel == "current-month":
        value.requestCatalogueMonth(9)
    elif cancel == "synchronous-month":
        value.setCatalogueMonth(12)
    elif cancel == "invalidate":
        value._invalidate_catalogue_month_visibility_cache()
    else:
        value._location = None
    value._recalculate_observing_outputs.reset_mock()
    tasks[0]()
    assert value.catalogueSelectedMonth == (12 if cancel == "synchronous-month" else 9)
    assert not value.catalogueMonthRefreshActive
    assert not value._catalogue_month_refresh_running
    value._recalculate_observing_outputs.assert_not_called()
    assert not value._catalogue_visibility_cache


def test_month_result_with_obsolete_year_is_recomputed_before_publication(qt_app):
    value = controller()
    tasks = []
    value._start_background_task = tasks.append
    value.requestCatalogueMonth(10)
    value._catalogue_year = 2027
    tasks[0]()
    assert value.catalogueSelectedMonth == 9
    assert len(tasks) == 2
    tasks[1]()
    assert value.catalogueSelectedMonth == 10
    assert value._astronomy_engine.catalogue_month_visibility.call_args.args[2] == 2027
    assert len(value._catalogue_visibility_cache) == 1


def test_invalid_request_does_not_cancel_a_valid_month_in_progress(qt_app):
    value = controller()
    tasks = []
    value._start_background_task = tasks.append
    value.requestCatalogueMonth(10)
    value.requestCatalogueMonth(0)
    value.requestCatalogueMonth(13)
    assert value.catalogueMonthRefreshActive
    tasks[0]()
    assert value.catalogueSelectedMonth == 10


def test_completed_but_superseded_geometry_is_discarded_before_publication(qt_app):
    value = controller()
    tasks = []
    value._start_background_task = tasks.append

    def visibility(_objects, _location, _year, month, _threshold):
        if month == 10:
            value.requestCatalogueMonth(11)
        return {"M31": month == 10}

    value._astronomy_engine.catalogue_month_visibility.side_effect = visibility
    value.requestCatalogueMonth(10)
    tasks[0]()
    assert value.catalogueSelectedMonth == 9
    assert not value._catalogue_visibility_cache
    value._recalculate_observing_outputs.assert_not_called()
    tasks[1]()
    assert value.catalogueSelectedMonth == 11
    assert value._catalogue_visibility_map() == {"M31": False}
    value._recalculate_observing_outputs.assert_called_once()


def test_month_request_rechecks_generation_after_waiting_for_engine_lock(qt_app):
    value = controller()
    tasks = []
    value._start_background_task = tasks.append

    class CancellingLock:
        def __enter__(self):
            value.requestCatalogueMonth(9)

        def __exit__(self, *_args):
            return False

    value._astronomy_engine_lock = CancellingLock()
    value.requestCatalogueMonth(10)
    tasks[0]()
    value._astronomy_engine.catalogue_month_visibility.assert_not_called()
    assert value.catalogueSelectedMonth == 9
    assert not value.catalogueMonthRefreshActive


@pytest.mark.parametrize("failure", ["engine", "worker", "no-provider"])
def test_month_preparation_failure_retains_existing_fallback_policy(qt_app, failure):
    value = controller()
    tasks = []
    value._start_background_task = tasks.append
    if failure == "engine":
        value._astronomy_engine.catalogue_month_visibility.side_effect = RuntimeError("offline")
    elif failure == "worker":
        value._start_background_task = Mock(side_effect=RuntimeError("worker unavailable"))
    else:
        value._astronomy_engine = object()
    value.requestCatalogueMonth(10)
    for task in tasks:
        task()
    assert value.catalogueSelectedMonth == 10
    assert not value.catalogueMonthRefreshActive
    value._recalculate_observing_outputs.assert_called_once()
    if failure != "worker":
        assert value._catalogue_visibility_map() == {}


@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("other_month", [None, 11])
def test_failed_month_retries_on_explicit_request_without_getter_retry_storm(qt_app, asynchronous, other_month):
    value = controller()
    tasks = []
    value._start_background_task = tasks.append
    calculate = value._astronomy_engine.catalogue_month_visibility
    calculate.side_effect = [RuntimeError("temporary failure"), {"M31": True}, {"M31": True}]

    def select(month):
        if asynchronous:
            value.requestCatalogueMonth(month)
            while tasks:
                tasks.pop(0)()
        else:
            value.setCatalogueMonth(month)
        return value._catalogue_visibility_map()

    assert select(10) == {}
    for _ in range(5):
        assert value._catalogue_visibility_map() == {}
    assert calculate.call_count == 1
    if other_month is not None:
        assert select(other_month) == {"M31": True}
    assert select(10) == {"M31": True}
    assert calculate.call_count == (2 if other_month is None else 3)
    assert value.catalogueSelectedMonth == 10
    assert not value.catalogueMonthRefreshActive


def test_successful_empty_month_is_cached_and_not_treated_as_failure(qt_app):
    value = controller()
    tasks = []
    value._start_background_task = tasks.append
    value._astronomy_engine.catalogue_month_visibility.side_effect = lambda *_args: {}
    for month in (10, 11, 10, 10):
        value.requestCatalogueMonth(month)
        while tasks:
            tasks.pop(0)()
        assert value._catalogue_visibility_map() == {}
    assert value._astronomy_engine.catalogue_month_visibility.call_count == 2


def test_month_engine_runs_off_thread_and_publication_returns_to_qt_thread(qt_app):
    value = controller()
    started, release = Event(), Event()
    main_thread = get_ident()
    engine_threads, publish_threads = [], []

    def visibility(*_args):
        engine_threads.append(get_ident())
        started.set()
        assert release.wait(3)
        return {"M31": True}

    value._astronomy_engine.catalogue_month_visibility.side_effect = visibility
    value._recalculate_observing_outputs.side_effect = lambda: publish_threads.append(get_ident())
    value.requestCatalogueMonth(10)
    try:
        assert started.wait(3)
        assert value.catalogueSelectedMonth == 9
        qt_app.processEvents()
        assert value.catalogueMonthRefreshActive
    finally:
        release.set()
    deadline = time.monotonic() + 3
    while value.catalogueMonthRefreshActive and time.monotonic() < deadline:
        qt_app.processEvents()
        time.sleep(0.005)
    assert engine_threads and engine_threads[0] != main_thread
    assert publish_threads == [main_thread]
    assert value.catalogueSelectedMonth == 10
    assert not value.catalogueMonthRefreshActive
