"""Expose annual IMO cache state to QML without network or PDF work on Qt's UI thread."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from threading import Thread
from typing import Callable

from PySide6.QtCore import QObject, Property, QTimer, QUrl, Signal, Slot

from astro_viewer.app.services.imo_calendar import ImoCalendarStore, ImoResult, IMO_URL


logger = logging.getLogger(__name__)


class ImoCalendarManager(QObject):
    changed = Signal()
    calendarChanged = Signal()
    _finished = Signal(object)

    def __init__(self, store: ImoCalendarStore, parent=None, *, clock: Callable = datetime.now):
        super().__init__(parent)
        self._store = store
        self._clock = clock
        self._result = ImoResult(clock().year)
        self._busy = False
        self._stopped = False
        self._checked = False
        self._next_check = clock()
        self._finished.connect(self._accept)
        self._timer = QTimer(self)
        self._timer.setInterval(60 * 1000)
        self._timer.timeout.connect(self.check)

    @property
    def calendar(self):
        cached = self._result.calendar
        return cached if cached and cached.year == self._clock().year else None

    @Property("QVariantMap", notify=changed)
    def info(self) -> dict:
        cached = self._result.calendar
        current_year = self._clock().year
        current = bool(cached and cached.year == current_year)
        state = ("loading" if self._busy else "invalid_import" if self._result.error == "invalid_import"
                 else "ready" if current else "stale" if cached else "unavailable" if self._checked else "pending")
        return {
            "state": state, "busy": self._busy, "current": current,
            "requestedYear": current_year, "year": cached.year if cached else 0,
            "downloadedAt": cached.downloaded_at.astimezone().isoformat() if cached else "",
            "filename": cached.path.name if cached else "",
            "count": len(cached.showers) if cached else 0,
            "sourceUrl": IMO_URL,
        }

    @Slot()
    def start(self):
        if self._stopped:
            return
        self._timer.start()
        self.check()

    @Slot()
    def check(self):
        now = self._clock()
        if self._stopped or self._busy:
            return
        if self._checked and self._result.requested_year == now.year and now < self._next_check:
            return
        self._run(lambda: self._store.ensure_year(now.year, now=now))

    @Slot()
    def retry(self):
        now = self._clock()
        self._run(lambda: self._store.ensure_year(now.year, now=now, retry=True))

    @Slot(QUrl)
    def importFile(self, url: QUrl):
        if url.isLocalFile():
            from pathlib import Path
            year = self._clock().year
            self._run(lambda: self._store.import_file(Path(url.toLocalFile()), year))

    @Slot()
    def stop(self):
        self._stopped = True
        self._timer.stop()

    def _run(self, operation):
        if self._stopped or self._busy:
            return
        self._busy = True
        requested_year = self._clock().year
        previous = self._result.calendar
        self.changed.emit()

        def work():
            try:
                result = operation()
            except Exception:
                logger.exception("Unexpected IMO provider failure.")
                result = ImoResult(requested_year, previous, "unavailable")
            try:
                self._finished.emit(result)
            except RuntimeError:
                logger.debug("IMO worker completed after Qt shutdown.")

        try:
            Thread(target=work, name="NightScopeIMO", daemon=True).start()
        except RuntimeError:
            self._accept(ImoResult(requested_year, previous, "unavailable"))

    @Slot(object)
    def _accept(self, result):
        if self._stopped:
            return
        self._busy = False
        self._checked = True
        self._result = result
        now = self._clock()
        # Successful years require no more disk/network work until rollover.
        self._next_check = (datetime(now.year + 1, 1, 1, tzinfo=now.tzinfo)
                            if self.calendar else datetime.fromtimestamp(result.retry_at.timestamp(), tz=now.tzinfo)
                            if result.retry_at else now + timedelta(hours=24))
        self.changed.emit()
        self.calendarChanged.emit()
        if result.requested_year != now.year:
            self.check()
