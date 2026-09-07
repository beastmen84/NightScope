"""Protect detached Home timing preparation, exact-input reuse and cancellation."""

from dataclasses import replace
from datetime import timedelta
from threading import Thread, get_ident
from unittest.mock import Mock

import pytest

from astro_viewer.app.application.observing_refresh import ObservingRefreshCancelled
from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.services.home_target_timing import HomeTargetTimingSnapshot
from astro_viewer.tests.test_home_projection import home_controller as home_controller, legacy_overview
from astro_viewer.tests.test_observing_refresh import (
    calculation,
    observing_controller as observing_controller,
    qt_app as qt_app,
)


def test_matching_home_reads_reuse_timings_but_rebuild_final_payload(home_controller, monkeypatch):
    controller = home_controller
    expected = controller.homeNightPlanOverview
    snapshot = controller._home_target_timing
    monkeypatch.setattr(HomeTargetTimingSnapshot, "build", Mock(side_effect=AssertionError("duplicate timings")))
    controller._active_profile_payload = lambda: {"profile_name": "Changed profile"}
    actual = controller.homeNightPlanOverview
    assert actual == legacy_overview(controller)
    assert actual["profile"]["name"] == "Changed profile"
    assert actual["alternatives"] == expected["alternatives"]
    assert controller._home_target_timing is snapshot
    assert actual is not expected


@pytest.mark.parametrize("change", ["equal_copy", "order", "remove", "night", "name", "type", "window", "absolute"])
def test_replaced_targets_or_night_never_reuse_old_home_timings(home_controller, change):
    controller = home_controller
    controller.homeNightPlanOverview
    previous = controller._home_target_timing
    if change == "night":
        night = controller._observing_night_window
        controller._observing_night_window = ObservingNightWindow.bounded(
            night.start + timedelta(days=1), night.end + timedelta(days=1),
        )
    elif change == "order":
        controller._test_deep_sky.reverse()
    elif change == "remove":
        controller._test_deep_sky.pop(4)
    else:
        changes = {
            "equal_copy": {}, "name": {"name": "NGC 1"}, "type": {"object_type": "Open cluster"},
            "window": {"observing_window": "04:00 - 05:00", "best_time": "04:30"},
            "absolute": {"observing_start_at": "2026-09-08T03:00:00+02:00",
                         "observing_end_at": "2026-09-08T05:00:00+02:00"},
        }[change]
        controller._test_deep_sky[4] = replace(controller._test_deep_sky[4], **changes)
    assert controller.homeNightPlanOverview == legacy_overview(controller)
    assert controller._home_target_timing is not previous


def test_snapshot_mapping_is_read_only_and_old_list_mutation_is_detected(home_controller):
    controller = home_controller
    targets = controller._tonight_target_pool()
    night = controller._observing_night_window
    snapshot = HomeTargetTimingSnapshot.build(targets, night)
    assert snapshot.matches(targets, night)
    with pytest.raises(TypeError):
        snapshot.labels_by_id[targets[0].id] = ("changed", "")
    targets.clear()
    assert snapshot.targets
    assert not snapshot.matches(targets, night)


def test_equal_looking_dst_fold_boundaries_do_not_match(home_controller):
    controller = home_controller
    night = controller._observing_night_window
    snapshot = HomeTargetTimingSnapshot.build(controller._tonight_target_pool(), night)
    equal_night = replace(night, start=night.start.replace(fold=1))
    assert equal_night == night
    assert not snapshot.matches(controller._tonight_target_pool(), equal_night)


def test_empty_snapshot_and_absent_night_are_valid():
    snapshot = HomeTargetTimingSnapshot.build([], None)
    assert snapshot.matches([], None)
    assert snapshot.ordered_targets == ()
    assert dict(snapshot.labels_by_id) == {}
    assert not snapshot.matches([], ObservingNightWindow.unavailable())


def test_timing_preparation_checks_cancellation_between_targets(home_controller):
    checks = []

    def cancelled():
        checks.append(True)
        if len(checks) == 3:
            raise ObservingRefreshCancelled()

    with pytest.raises(ObservingRefreshCancelled):
        HomeTargetTimingSnapshot.build(home_controller._tonight_target_pool(),
                                       home_controller._observing_night_window, check_cancelled=cancelled)
    assert len(checks) == 3
    assert not hasattr(home_controller, "_home_target_timing")


def test_existing_worker_prepares_home_off_qt_before_atomic_publication(observing_controller, monkeypatch):
    controller = observing_controller
    before = controller.homeNightPlanOverview
    previous = controller._home_target_timing
    worker = calculation(controller, rebuild_equipment=True, apply_pollution=True)
    original = HomeTargetTimingSnapshot.build
    preparation_threads, errors = [], []

    def build(*args, **kwargs):
        preparation_threads.append(get_ident())
        return original(*args, **kwargs)

    monkeypatch.setattr(HomeTargetTimingSnapshot, "build", build)

    def run():
        try:
            worker.calculate()
        except Exception as error:
            errors.append(error)

    thread = Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout=10)
    assert not thread.is_alive() and not errors
    assert preparation_threads == [thread.ident] and thread.ident != get_ident()
    assert controller._home_target_timing is previous
    assert controller.homeNightPlanOverview == before
    monkeypatch.setattr(HomeTargetTimingSnapshot, "build", Mock(side_effect=AssertionError("Qt timing rebuild")))
    controller._publish_observing_calculation(worker, {})
    assert controller._home_target_timing is worker.home_target_timing
    assert worker.home_target_timing.matches(controller._tonight_target_pool(), controller._observing_night_window)
    assert controller.homeNightPlanOverview == legacy_overview(controller)


def test_superseded_worker_cannot_publish_its_home_snapshot(qt_app, observing_controller):
    controller = observing_controller
    controller.homeNightPlanOverview
    previous = controller._home_target_timing
    tasks = []
    controller._start_background_task = tasks.append
    controller._enable_observing_refresh()
    controller._refresh_active_profile_dependencies()
    coordinator = controller._observing_refresh_coordinator
    coordinator._start()
    controller._presentation_generation = getattr(controller, "_presentation_generation", 0) + 1
    tasks.pop(0)()
    assert controller._home_target_timing is previous
    coordinator._start()
    tasks.pop(0)()
    assert controller._home_target_timing is not previous
    assert controller.homeNightPlanOverview == legacy_overview(controller)
    controller.stopPerformanceWorkers()
