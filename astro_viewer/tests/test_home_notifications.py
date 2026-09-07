"""Protect coalesced Home notifications without altering other UI signals."""

from collections import Counter

import pytest
from PySide6.QtCore import QCoreApplication, QTimer

from astro_viewer.tests.test_phase6_real_data import _controller


@pytest.fixture
def notifying_controller():
    app = QCoreApplication.instance() or QCoreApplication([])
    with _controller() as controller:
        for timer in controller.findChildren(QTimer):
            timer.stop()
        try:
            yield app, controller
        finally:
            controller.stopPerformanceWorkers()


@pytest.mark.parametrize("asynchronous", [False, True])
def test_home_notifications_coalesce_only_in_async_ui_mode(notifying_controller, asynchronous):
    app, controller = notifying_controller
    if asynchronous:
        controller._enable_observing_refresh()
    notifications = []
    upstream = Counter()
    controller.homeNightPlanChanged.connect(lambda: notifications.append(controller.homeNightPlanOverview))
    for name in ("equipmentChanged", "dataChanged", "weatherChanged", "selectedObjectChanged"):
        getattr(controller, name).connect(lambda key=name: upstream.update([key]))
    controller._emit_profile_dependent_changes()
    assert len(notifications) == (0 if asynchronous else 3)
    assert upstream == {name: 1 for name in ("equipmentChanged", "dataChanged", "weatherChanged", "selectedObjectChanged")}
    app.processEvents()
    assert len(notifications) == (1 if asynchronous else 3)
    assert all(value == controller.homeNightPlanOverview for value in notifications)
    # A later update is not discarded by the coalescing of the previous turn.
    controller.dataChanged.emit()
    app.processEvents()
    assert len(notifications) == (2 if asynchronous else 4)


def test_home_notification_uses_latest_state_without_delaying_direct_reads(notifying_controller):
    app, controller = notifying_controller
    controller._enable_observing_refresh()
    notifications = []
    controller.homeNightPlanChanged.connect(lambda: notifications.append(controller.homeNightPlanOverview))
    for index in range(5):
        controller._active_profile()["profile_name"] = f"Profile {index}"
        controller._emit_profile_dependent_changes()
        controller._personal_image_changed("jupiter")
        assert controller.homeNightPlanOverview["profile"]["name"] == f"Profile {index}"
    assert notifications == []
    app.processEvents()
    assert len(notifications) == 1
    assert notifications[0]["profile"]["name"] == "Profile 4"


def test_home_notification_during_notification_is_not_lost(notifying_controller):
    app, controller = notifying_controller
    controller._enable_observing_refresh()
    notifications = []

    def on_changed():
        notifications.append(True)
        if len(notifications) == 1:
            controller.dataChanged.emit()

    controller.homeNightPlanChanged.connect(on_changed)
    controller.dataChanged.emit()
    for _ in range(3):
        app.processEvents()
    assert len(notifications) == 2


def test_home_pending_notification_stops_on_shutdown(notifying_controller):
    app, controller = notifying_controller
    controller._enable_observing_refresh()
    notifications = []
    controller.homeNightPlanChanged.connect(lambda: notifications.append(True))
    controller.dataChanged.emit()
    controller.stopPerformanceWorkers()
    app.processEvents()
    assert notifications == []
