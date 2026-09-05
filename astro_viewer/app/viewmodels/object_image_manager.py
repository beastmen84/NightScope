"""Coordinate a cancellable image preview worker and explicit per-object save/reset actions."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sqlite3
from threading import Thread
from uuid import uuid4

from PySide6.QtCore import QObject, Property, QTemporaryDir, QUrl, Signal, Slot

from astro_viewer.app.services.personal_images import (
    PersonalImageError, PersonalImageService, PreparedImage, prepare_image,
)


class ObjectImageManager(QObject):
    """Keep GUI mutations on the owning thread and reject results for cancelled targets."""

    changed = Signal()
    imageChanged = Signal(str)
    _prepared = Signal(int, object, str)

    def __init__(self, service: PersonalImageService, canonical_id: Callable[[str], str], parent=None):
        super().__init__(parent)
        self.service = service
        self._canonical_id = canonical_id
        self._target = ""
        self._generation = 0
        self._worker_running = False
        self._night_vision = False
        self._candidate: PreparedImage | None = None
        self._preview_path: Path | None = None
        self._error = ""
        self._temporary = QTemporaryDir()
        self._prepared.connect(self._finish)

    @Property("QVariantMap", notify=changed)
    def state(self) -> dict:
        return {"objectId": self._target, "busy": self._worker_running,
                "ready": self._candidate is not None,
                "hasPersonalImage": self._target in self.service.records,
                "errorCode": self._error,
                "previewUrl": self._preview_path.as_uri() if self._preview_path and not self._night_vision else "",
                "width": self._candidate.width if self._candidate else 0,
                "height": self._candidate.height if self._candidate else 0}

    def _clear_preview(self) -> None:
        self._candidate = None
        if self._preview_path:
            try:
                self._preview_path.unlink(missing_ok=True)
            except OSError:
                # Qt can still be finishing a cancelled read on Windows;
                # the private temporary directory cleans up when released.
                pass
        self._preview_path = None

    @Slot()
    def cancel(self) -> None:
        self._generation += 1
        self._clear_preview()
        self._error = ""
        self.changed.emit()

    @Slot(str, result=bool)
    def setTarget(self, identifier: str) -> bool:
        self.cancel()
        self._target = self._canonical_id(identifier)
        self.changed.emit()
        return bool(self._target)

    @Slot(bool)
    def setNightVision(self, enabled: bool) -> None:
        self._night_vision = enabled
        if enabled:
            self.cancel()
        self.changed.emit()

    @Slot(QUrl)
    def choose(self, url: QUrl) -> None:
        if self._worker_running or not self._target or self._night_vision:
            return
        self.cancel()
        if not url.isLocalFile() or url.host() not in {"", "localhost"}:
            self._error = "local_file"
            self.changed.emit()
            return
        self._worker_running = True
        generation = self._generation
        source = Path(url.toLocalFile())
        self.changed.emit()

        def work():
            result = None
            error = ""
            try:
                result = prepare_image(source)
            except PersonalImageError as exc:
                error = str(exc)
            except (OSError, ValueError, RuntimeError):
                error = "read"
            try:
                self._prepared.emit(generation, result, error)
            except RuntimeError:
                # Closing the app/owning controller invalidates the receiver.
                pass

        Thread(target=work, name="nightscope-image-preview", daemon=True).start()

    @Slot(int, object, str)
    def _finish(self, generation: int, prepared: PreparedImage | None, error: str) -> None:
        self._worker_running = False
        if generation != self._generation or self._night_vision:
            self.changed.emit()
            return
        self._error = error
        if prepared is not None and not error:
            try:
                if not self._temporary.isValid():
                    raise OSError("Preview storage unavailable")
                path = Path(self._temporary.path()) / f"{uuid4().hex}.jpg"
                path.write_bytes(prepared.image)
                self._preview_path = path
                self._candidate = prepared
            except OSError:
                self._error = "storage"
        self.changed.emit()

    @Slot(result=bool)
    def save(self) -> bool:
        if self._candidate is None or not self._target or self._night_vision:
            return False
        try:
            self.service.save(self._target, self._candidate)
        except (OSError, ValueError, RuntimeError, sqlite3.Error):
            self._error = "storage"
            self.changed.emit()
            return False
        self.cancel()
        self.imageChanged.emit(self._target)
        return True

    @Slot(result=bool)
    def reset(self) -> bool:
        if not self._target:
            return False
        try:
            self.service.reset(self._target)
        except (OSError, ValueError, RuntimeError, sqlite3.Error):
            self._error = "storage"
            self.changed.emit()
            return False
        self.cancel()
        self.imageChanged.emit(self._target)
        return True
