"""Refresh COBS after the first frame, exposing cache health without blocking Qt."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from threading import Thread
from typing import Callable

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

from astro_viewer.app.services.cobs_observations import (
    COBS_URL, LICENSE_URL, CobsObservationStore, CobsResult, utc,
)


logger = logging.getLogger(__name__)


class CobsManager(QObject):
    changed = Signal()
    observationsChanged = Signal()
    _finished = Signal(object)

    def __init__(self, store: CobsObservationStore, parent=None, *, clock: Callable = lambda: datetime.now(UTC)):
        super().__init__(parent)
        self._store = store
        self._clock = clock
        self._busy = self._stopped = self._checked = False
        self._revision = ""
        self._error = ""
        self._next_check = utc(clock())
        self._finished.connect(self._accept)
        self._timer = QTimer(self)
        self._timer.setInterval(60 * 1000)
        self._timer.timeout.connect(self.check)

    @Property("QVariantMap", notify=changed)
    def info(self):
        snapshot = self._store.snapshot
        now = utc(self._clock())
        recent = [row for row in snapshot.observations if now - timedelta(days=14) <= row.observed_at <= now]
        fresh = bool(snapshot.fetched_at and timedelta(0) <= now - snapshot.fetched_at < timedelta(hours=24))
        state = ("loading" if self._busy else "pending" if not self._checked
                 else "stale" if snapshot.fetched_at and (not fresh or self._error)
                 else "ready" if snapshot.fetched_at else "unavailable")
        return {"state": state, "busy": self._busy, "count": len(recent),
                "comets": len({row.designation for row in recent}),
                "downloadedAt": snapshot.fetched_at.isoformat() if snapshot.fetched_at else "",
                "latestAt": max((row.observed_at for row in recent)).isoformat() if recent else "",
                "sourceUrl": COBS_URL, "licenseUrl": LICENSE_URL}

    @Slot()
    def start(self):
        if not self._stopped:
            self._timer.start()
            self.check()

    @Slot()
    def check(self):
        now = utc(self._clock())
        if self._busy or self._stopped or now < self._next_check <= now + timedelta(hours=24):
            return
        self._busy = True
        self.changed.emit()

        def work():
            try:
                result = self._store.refresh(now)
            except Exception:
                logger.exception("Unexpected COBS provider failure.")
                result = CobsResult(self._store.snapshot, now + timedelta(hours=24), "unavailable")
            try:
                self._finished.emit(result)
            except RuntimeError:
                logger.debug("COBS worker completed after Qt shutdown.")

        try:
            Thread(target=work, name="NightScopeCOBS", daemon=True).start()
        except RuntimeError:
            self._accept(CobsResult(self._store.snapshot, now + timedelta(hours=24), "unavailable"))

    @Slot(object)
    def _accept(self, result):
        if self._stopped:
            return
        self._busy = False
        self._checked = True
        self._error = result.error
        self._next_check = result.next_check
        changed = self._revision != result.snapshot.revision
        self._revision = result.snapshot.revision
        self.changed.emit()
        if changed:
            self.observationsChanged.emit()

    @Slot()
    def stop(self):
        self._stopped = True
        self._timer.stop()
