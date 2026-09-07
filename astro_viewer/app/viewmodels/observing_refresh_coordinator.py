"""Bound observing preparation to one worker and coalesced Qt-owned requests.

Only capture, signature checks, publication and continuations run on Qt. Workers
receive detached calculations and a cancellation event, never the controller.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from threading import Event
from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from astro_viewer.app.application.observing_refresh import ObservingRefreshCancelled


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ObservingRefreshRequest:
    rebuild_equipment: bool = False
    apply_pollution: bool = False
    recalculate_outputs: bool | None = True
    month: int | None = None
    completion: Callable[[], None] | None = None


class ObservingRefreshCoordinator(QObject):
    changed = Signal()
    _finished = Signal(int, object, object)

    def __init__(self, *, capture, signature, publish, failure, start_worker, parent=None):
        super().__init__(parent)
        self._capture = capture
        self._signature = signature
        self._publish = publish
        self._failure = failure
        self._start_worker = start_worker
        self._requests: dict[str, ObservingRefreshRequest] = {}
        self._running = False
        self._generation = 0
        self._cancelled = Event()
        self._start_timer = QTimer(self)
        self._start_timer.setSingleShot(True)
        self._start_timer.timeout.connect(self._start)
        self._finished.connect(self._finish)

    @property
    def active(self):
        return bool(self._requests)

    def has_request(self, key):
        return key in self._requests

    def request(self, key, request):
        # Replacing a kind also moves it to the latest position for policy order.
        self._requests.pop(key, None)
        self._requests[key] = request
        self._cancelled.set()
        self._generation += 1
        if not self._running:
            self._start_timer.start(0)
        self.changed.emit()

    def cancel(self, key=None):
        if key is None:
            self._requests.clear()
        else:
            self._requests.pop(key, None)
        self._generation += 1
        self._cancelled.set()
        if not self._requests:
            self._start_timer.stop()
        elif not self._running:
            self._start_timer.start(0)
        self.changed.emit()

    @Slot()
    def _start(self):
        if self._running or not self._requests:
            return
        requests = dict(self._requests)
        self._cancelled = Event()
        cancellation = self._cancelled
        try:
            signature = self._signature(requests)
            calculation = self._capture(requests, cancellation.is_set)
        except Exception as error:
            self._requests.clear()
            self._failure(error, requests)
            self.changed.emit()
            return
        generation = self._generation
        self._active_generation = generation
        self._active_signature = signature
        self._running = True
        finished = self._finished

        def run():
            result, error = None, None
            try:
                result = calculation.calculate()
            except ObservingRefreshCancelled:
                logger.debug("Observing preparation superseded by a newer request.")
            except Exception as caught:
                logger.exception("Observing preparation failed.")
                error = caught
            try:
                finished.emit(generation, result, error)
            except RuntimeError:
                # The window/controller may have been destroyed during shutdown.
                logger.debug("Observing result discarded after Qt shutdown.")

        try:
            self._start_worker(run)
        except Exception as error:
            self._running = False
            self._requests.clear()
            self._failure(error, requests)
            self.changed.emit()

    @Slot(int, object, object)
    def _finish(self, generation, result, error):
        if generation != self._active_generation:
            return
        self._running = False
        requests = dict(self._requests)
        current = generation == self._generation and bool(requests)
        try:
            if current and self._signature(requests) != self._active_signature:
                current = False
            if current:
                self._requests.clear()
                if result is not None:
                    self._publish(result, requests)
                elif error is not None:
                    self._failure(error, requests)
        except Exception as caught:
            self._requests.clear()
            self._failure(caught, requests)
        finally:
            if self._requests:
                self._start_timer.start(0)
            self.changed.emit()
