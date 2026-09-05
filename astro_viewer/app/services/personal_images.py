"""Validate and normalize local pictures, then commit immutable files before their DB association.

Only JPEG/PNG input is decoded, in the image manager's worker. Source originals
are never modified or referenced in the DB. Normalization removes metadata,
retains aspect ratio, applies EXIF orientation, and composites alpha on a dark
matte. Reset/replacement removes associations, not files needed by older backups.
"""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QColor, QColorSpace, QImage, QImageReader, QPainter

from astro_viewer.app.database.personal_image_repository import PersonalImageRepository


MAX_INPUT_BYTES = 20 * 1024 * 1024
MAX_INPUT_PIXELS = 32_000_000
MAX_INPUT_EDGE = 12_000
IMAGE_EDGE = 1600
THUMBNAIL_EDGE = 320
IMAGE_DIRECTORY = "user_images"
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


class PersonalImageError(ValueError):
    """Carry a stable UI error code without exposing a user's source path."""


@dataclass(frozen=True)
class PreparedImage:
    image: bytes
    thumbnail: bytes
    width: int
    height: int

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.image).hexdigest()


def _jpeg(image: QImage, edge: int, quality: int) -> bytes:
    scaled = image.scaled(edge, edge, Qt.KeepAspectRatio, Qt.SmoothTransformation) if (
        max(image.width(), image.height()) > edge
    ) else image
    # Drawing into a new image strips EXIF/GPS/comments rather than copying metadata.
    matte = QImage(scaled.size(), QImage.Format_RGB32)
    matte.fill(QColor("#111319"))
    painter = QPainter(matte)
    painter.drawImage(0, 0, scaled)
    painter.end()
    content = QByteArray()
    buffer = QBuffer(content)
    buffer.open(QIODevice.WriteOnly)
    if not matte.save(buffer, "JPEG", quality):
        raise PersonalImageError("decode")
    return bytes(content)


def prepare_image(source: Path) -> PreparedImage:
    """Bound input bytes/pixels before decoding; return only sanitized application data."""
    if str(source).startswith(("\\\\", "//")) or not source.is_file():
        raise PersonalImageError("local_file")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise PersonalImageError("size")
    with source.open("rb") as stream:
        content = stream.read(MAX_INPUT_BYTES + 1)
    if len(content) > MAX_INPUT_BYTES:
        raise PersonalImageError("size")
    raw = QByteArray(content)
    buffer = QBuffer(raw)
    buffer.open(QIODevice.ReadOnly)
    reader = QImageReader(buffer)
    if bytes(reader.format()).lower() not in {b"jpeg", b"png"}:
        raise PersonalImageError("format")
    if bytes(reader.format()).lower() == b"png":
        position = 8
        while position + 12 <= len(content):
            length = int.from_bytes(content[position:position + 4], "big")
            if content[position + 4:position + 8] == b"acTL":
                raise PersonalImageError("format")
            position += length + 12
    dimensions = reader.size()
    if (
        dimensions.width() <= 0 or dimensions.height() <= 0
        or max(dimensions.width(), dimensions.height()) > MAX_INPUT_EDGE
        or dimensions.width() * dimensions.height() > MAX_INPUT_PIXELS
    ):
        raise PersonalImageError("dimensions")
    reader.setAutoTransform(True)
    if max(dimensions.width(), dimensions.height()) > IMAGE_EDGE:
        reader.setScaledSize(dimensions.scaled(IMAGE_EDGE, IMAGE_EDGE, Qt.KeepAspectRatio))
    decoded = reader.read()
    if decoded.isNull():
        raise PersonalImageError("decode")
    if decoded.colorSpace().isValid():
        decoded.convertToColorSpace(QColorSpace(QColorSpace.SRgb))
    size = decoded.size()
    if max(size.width(), size.height()) > IMAGE_EDGE:
        size = size.scaled(IMAGE_EDGE, IMAGE_EDGE, Qt.KeepAspectRatio)
    return PreparedImage(_jpeg(decoded, IMAGE_EDGE, 90), _jpeg(decoded, THUMBNAIL_EDGE, 85),
                         size.width(), size.height())


class PersonalImageService:
    """Own immutable normalized files; tolerate missing assets without destroying associations."""

    def __init__(self, repository: PersonalImageRepository):
        self.repository = repository
        self.directory = repository.database_path.parent / IMAGE_DIRECTORY
        self.records = repository.all()

    def _directory(self) -> Path:
        # A redirected image directory must never make writes escape runtime data.
        if self.directory.is_symlink():
            raise PersonalImageError("storage")
        self.directory.mkdir(parents=True, exist_ok=True)
        resolved = self.directory.resolve()
        if resolved.parent != self.repository.database_path.parent.resolve():
            raise PersonalImageError("storage")
        return resolved

    def paths(self, digest: str) -> tuple[Path, Path]:
        if not HASH_PATTERN.fullmatch(digest):
            raise PersonalImageError("storage")
        return self.directory / f"{digest}.jpg", self.directory / f"{digest}-thumb.jpg"

    def metadata(self, object_id: str) -> dict | None:
        record = self.records.get(object_id)
        if (
            not record or self.directory.is_symlink()
            or self.directory.resolve().parent != self.repository.database_path.parent.resolve()
        ):
            return None
        try:
            image, thumbnail = self.paths(record["image_hash"])
        except (PersonalImageError, KeyError, TypeError):
            return None
        if image.is_symlink() or thumbnail.is_symlink() or not image.is_file():
            return None
        return {"image_path": image.resolve().as_uri(),
                "thumbnail_path": (thumbnail if thumbnail.is_file() else image).resolve().as_uri(),
                "kind": "personal", "category": "", "attribution": "", "source_url": "",
                "license": "User supplied", "verified": False}

    def _write_asset(self, path: Path, content: bytes) -> None:
        root = self._directory()
        if path.parent.resolve() != root or path.is_symlink():
            raise PersonalImageError("storage")
        if path.exists():
            if path.stat().st_size != len(content) or path.read_bytes() != content:
                raise PersonalImageError("storage")
            return
        with tempfile.NamedTemporaryFile(dir=root, prefix=".pending-", delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            except BaseException:
                stream.close()
                temporary.unlink(missing_ok=True)
                raise
        try:
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def save(self, object_id: str, prepared: PreparedImage) -> None:
        # Install both files before committing their association. Failure never
        # replaces the current DB image; orphaned files remain safe to recover.
        image, thumbnail = self.paths(prepared.digest)
        self._write_asset(image, prepared.image)
        self._write_asset(thumbnail, prepared.thumbnail)
        self.repository.save(object_id, prepared.digest)
        self.records = self.repository.all()

    def reset(self, object_id: str) -> None:
        self.repository.reset(object_id)
        self.records = self.repository.all()
