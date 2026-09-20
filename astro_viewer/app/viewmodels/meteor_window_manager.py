"""Coalesce immutable meteor-geometry requests in one worker, outside Qt paint."""

from __future__ import annotations

import logging
from threading import Event, Thread

from PySide6.QtCore import QObject, QTimer, Signal, Slot

from astro_viewer.app.astronomy.meteor_windows import MeteorGeometry


logger = logging.getLogger(__name__)


class MeteorWindowManager(QObject):
    changed = Signal()
    _finished = Signal(object, object)

    def __init__(self, calculate, engine_lock, parent=None):
        super().__init__(parent)
        self._calculate = calculate
        self._lock = engine_lock
        self._key = None
        self._published_key = None
        self._results = {}
        self._running = False
        self._stopped = False
        self._cancelled = Event()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start)
        self._finished.connect(self._accept)

    def request(self, calendar, location, day):
        key = (calendar.year, calendar.showers, location, day) if calendar and location and callable(self._calculate) else None
        if self._stopped:
            return {}
        if key != self._key:
            self._key = key
            self._cancelled.set()
            self._results = {}
            self._published_key = None
            if not self._running and key:
                self._timer.start(0)
        return self._results if key and key == self._published_key else {}

    @Slot()
    def _start(self):
        if self._running or self._stopped or self._key is None:
            return
        key = self._key
        _, showers, location, _ = key
        self._running = True
        self._cancelled = Event()
        cancelled, calculate, lock, finished = self._cancelled, self._calculate, self._lock, self._finished

        def work():
            results = {}
            for shower in showers:
                if cancelled.is_set():
                    break
                try:
                    with lock:
                        if cancelled.is_set():
                            break
                        results[shower.code] = calculate(location, shower)
                except Exception:
                    logger.warning("Meteor geometry unavailable for %s.", shower.code, exc_info=True)
                    results[shower.code] = MeteorGeometry()
            try:
                finished.emit(key, results)
            except RuntimeError:
                logger.debug("Meteor worker completed after Qt shutdown.")

        try:
            Thread(target=work, name="NightScopeMeteorWindows", daemon=True).start()
        except RuntimeError:
            self._accept(key, {shower.code: MeteorGeometry() for shower in showers})

    @Slot(object, object)
    def _accept(self, key, results):
        self._running = False
        if self._stopped:
            return
        # A -> B -> A must not publish the cancelled first A's partial results.
        if key == self._key and not self._cancelled.is_set():
            self._results = results
            self._published_key = key
            self.changed.emit()
        elif self._key:
            self._timer.start(0)

    def stop(self):
        self._stopped = True
        self._cancelled.set()
        self._timer.stop()
