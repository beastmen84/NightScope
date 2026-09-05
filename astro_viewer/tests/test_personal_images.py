"""Exercise real image decoding, private storage, DB persistence, and cancellable GUI commands."""

from __future__ import annotations

from contextlib import closing
import hashlib
from io import BytesIO
from pathlib import Path
import sqlite3
import shutil
import time
from threading import Event
from unittest.mock import patch

from PIL import Image
from PySide6.QtCore import QCoreApplication, QUrl
import pytest

from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.personal_image_repository import PersonalImageRepository
from astro_viewer.app.services import personal_images
from astro_viewer.app.services.personal_images import PersonalImageError, PersonalImageService, prepare_image
from astro_viewer.app.viewmodels.object_image_manager import ObjectImageManager
from astro_viewer.tests.database_fixture import prepare_database
from astro_viewer.tests.test_phase6_real_data import _controller


@pytest.fixture
def image_file(tmp_path):
    path = tmp_path / "Original photo with spaces à.png"
    image = Image.new("RGBA", (600, 300), (210, 50, 20, 255))
    image.paste((0, 0, 0, 0), (0, 0, 100, 300))
    image.save(path)
    return path


@pytest.fixture
def service(tmp_path):
    database = tmp_path / "runtime" / "nightscope.db"
    database.parent.mkdir()
    prepare_database(database, Path(__file__).resolve().parents[1] / "data/schema.sql")
    return PersonalImageService(PersonalImageRepository(database))


def _wait(manager):
    application = QCoreApplication.instance() or QCoreApplication([])
    deadline = time.monotonic() + 10
    while manager.state["busy"] and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.005)
    application.processEvents()
    assert not manager.state["busy"]


def test_normalization_preserves_original_aspect_and_dark_alpha(image_file):
    before = image_file.read_bytes()
    result = prepare_image(image_file)
    assert image_file.read_bytes() == before
    assert (result.width, result.height) == (600, 300)
    with Image.open(BytesIO(result.image)) as image:
        assert image.format == "JPEG" and image.mode == "RGB"
        assert image.size == (600, 300)
        assert all(abs(a - b) <= 3 for a, b in zip(image.getpixel((20, 20)), (17, 19, 25), strict=True))
    with Image.open(BytesIO(result.thumbnail)) as thumbnail:
        assert thumbnail.size == (320, 160)


def test_orientation_scaling_and_private_metadata_are_normalized(tmp_path):
    source = tmp_path / "portrait.jpg"
    original = Image.new("RGB", (2400, 1200), "orange")
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "Private capture description"
    original.save(source, exif=exif)
    before = source.read_bytes()
    prepared = prepare_image(source)
    assert (prepared.width, prepared.height) == (800, 1600)
    assert source.read_bytes() == before
    with Image.open(BytesIO(prepared.image)) as normalized:
        assert normalized.size == (800, 1600)
        assert not normalized.getexif()
    assert b"Private capture" not in prepared.image


@pytest.mark.parametrize("case,code", [
    ("missing", "local_file"), ("text", "format"), ("gif", "format"),
    ("animated_png", "format"), ("bytes", "size"), ("edge", "dimensions"),
    ("pixels", "dimensions"),
])
def test_reject_invalid_unbounded_and_animated_inputs(tmp_path, monkeypatch, case, code):
    path = tmp_path / "candidate.png"
    if case == "text":
        path.write_text("not an image", encoding="utf-8")
    elif case == "gif":
        Image.new("RGB", (10, 10)).save(path, format="GIF")
    elif case == "animated_png":
        Image.new("RGB", (10, 10), "red").save(
            path, save_all=True, append_images=[Image.new("RGB", (10, 10), "blue")], duration=100,
        )
    elif case != "missing":
        Image.new("RGB", (200, 100)).save(path)
        if case == "bytes":
            monkeypatch.setattr(personal_images, "MAX_INPUT_BYTES", 16)
        elif case == "edge":
            monkeypatch.setattr(personal_images, "MAX_INPUT_EDGE", 120)
        else:
            monkeypatch.setattr(personal_images, "MAX_INPUT_PIXELS", 100)
    with pytest.raises(PersonalImageError, match=code):
        prepare_image(path)


def test_storage_is_portable_idempotent_and_independent_of_original(service, image_file):
    prepared = prepare_image(image_file)
    service.save("messier-M31", prepared)
    image_file.unlink()
    fresh = PersonalImageService(service.repository)
    row = fresh.records["messier-M31"]
    assert row["image_hash"] == hashlib.sha256(prepared.image).hexdigest()
    assert "file:" not in str(row) and str(image_file) not in str(row)
    metadata = fresh.metadata("messier-M31")
    assert QUrl(metadata["image_path"]).toLocalFile() == str(service.paths(prepared.digest)[0].resolve()).replace("\\", "/")
    fresh.save("messier-M31", prepared)
    assert len(list(fresh.directory.iterdir())) == 2
    assert metadata["kind"] == "personal" and not metadata["verified"]


def test_replacement_reset_and_bootstrap_preserve_files_for_backups(service, image_file):
    first = prepare_image(image_file)
    service.save("messier-M31", first)
    Image.new("RGB", (100, 200), "blue").save(image_file)
    second = prepare_image(image_file)
    service.save("messier-M31", second)
    initialize_database(service.repository.database_path, Path(__file__).resolve().parents[1] / "data/schema.sql")
    restarted = PersonalImageService(service.repository)
    assert restarted.records["messier-M31"]["image_hash"] == second.digest
    restarted.reset("messier-M31")
    assert restarted.metadata("messier-M31") is None
    assert all(path.is_file() for digest in (first.digest, second.digest) for path in service.paths(digest))
    with closing(sqlite3.connect(service.repository.database_path)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()


def test_failed_db_save_keeps_previous_association(service, image_file):
    prepared = prepare_image(image_file)
    service.save("moon", prepared)
    before = service.repository.all()
    with patch.object(service.repository, "save", side_effect=sqlite3.OperationalError("fixture")):
        with pytest.raises(sqlite3.OperationalError):
            service.save("moon", prepared)
    assert service.repository.all() == before


def test_missing_and_unsafe_files_keep_association_but_use_fallback(service, image_file):
    prepared = prepare_image(image_file)
    service.save("moon", prepared)
    service.paths(prepared.digest)[0].unlink()
    assert service.metadata("moon") is None
    assert "moon" in service.records
    service.records["moon"]["image_hash"] = "../outside"
    assert service.metadata("moon") is None
    with pytest.raises(PersonalImageError):
        service.paths("../outside")


def test_database_26_migrates_without_replacing_existing_user_data(service):
    database = service.repository.database_path
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("DROP TABLE PersonalObjectImages")
        connection.execute("PRAGMA user_version = 26")
        connection.execute("UPDATE ObjectDescription SET short_description='User text', is_builtin=0 WHERE object_id='messier-M31'")
    initialize_database(database, Path(__file__).resolve().parents[1] / "data/schema.sql")
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 27
        assert connection.execute("SELECT short_description FROM ObjectDescription WHERE object_id='messier-M31'").fetchone()[0] == "User text"
        assert connection.execute("SELECT COUNT(*) FROM PersonalObjectImages").fetchone()[0] == 0
    assert not list(database.parent.glob("*.corrupt-*.bak"))


def test_portable_copy_rebases_personal_images(service, image_file, tmp_path):
    service.save("moon", prepare_image(image_file))
    copied = tmp_path / "copied runtime"
    shutil.copytree(service.repository.database_path.parent, copied)
    relocated = PersonalImageService(PersonalImageRepository(copied / "nightscope.db"))
    url = relocated.metadata("moon")["image_path"]
    assert Path(QUrl(url).toLocalFile()).parent == copied / "user_images"


def test_partial_file_write_never_changes_previous_association(service, image_file):
    first = prepare_image(image_file)
    service.save("moon", first)
    Image.new("RGB", (100, 100), "yellow").save(image_file)
    second = prepare_image(image_file)
    with patch("astro_viewer.app.services.personal_images.os.replace", side_effect=OSError("fixture")):
        with pytest.raises(OSError):
            service.save("moon", second)
    assert service.repository.all()["moon"]["image_hash"] == first.digest
    assert not list(service.directory.glob(".pending-*"))


def test_existing_content_addressed_file_is_never_overwritten(service, image_file):
    prepared = prepare_image(image_file)
    service.save("moon", prepared)
    path = service.paths(prepared.digest)[0]
    path.write_bytes(b"externally modified")
    with pytest.raises(PersonalImageError, match="storage"):
        service.save("moon", prepared)
    assert path.read_bytes() == b"externally modified"


def test_preview_needs_confirmation_and_resolves_canonical_alias(service, image_file):
    application = QCoreApplication.instance() or QCoreApplication([])
    manager = ObjectImageManager(service, lambda key: "messier-M31" if key in {"M31", "NGC 224"} else "")
    assert manager.setTarget("NGC 224")
    manager.choose(QUrl.fromLocalFile(str(image_file)))
    _wait(manager)
    assert manager.state["ready"] and manager.state["previewUrl"]
    assert not service.records and not service.directory.exists()
    assert manager.save()
    assert list(service.records) == ["messier-M31"]
    manager.setTarget("M31")
    assert manager.state["hasPersonalImage"] and manager.reset()
    assert not service.records
    assert application is not None


def test_cancel_and_target_change_discard_late_results(service, image_file):
    application = QCoreApplication.instance() or QCoreApplication([])
    manager = ObjectImageManager(service, lambda key: key)
    manager.setTarget("moon")
    manager.choose(QUrl.fromLocalFile(str(image_file)))
    manager.setTarget("messier-M31")
    _wait(manager)
    assert not manager.state["ready"] and not manager.save()
    assert not service.records and not service.directory.exists()
    assert application is not None


def test_red_mode_rejects_new_decode_and_discards_preview(service, image_file):
    manager = ObjectImageManager(service, lambda key: key)
    manager.setTarget("moon")
    manager.setNightVision(True)
    with patch("astro_viewer.app.viewmodels.object_image_manager.prepare_image") as decode:
        manager.choose(QUrl.fromLocalFile(str(image_file)))
        decode.assert_not_called()
    assert not manager.state["previewUrl"] and not manager.save()


def test_nonlocal_url_and_storage_errors_are_reported(service, image_file):
    manager = ObjectImageManager(service, lambda key: key)
    manager.setTarget("moon")
    manager.choose(QUrl("https://example.invalid/photo.jpg"))
    assert manager.state["errorCode"] == "local_file"
    manager._candidate = prepare_image(image_file)
    with patch.object(service.repository, "save", side_effect=sqlite3.OperationalError("fixture")):
        assert not manager.save()
    assert manager.state["errorCode"] == "storage"


@pytest.mark.parametrize("action", ["cancel", "red", "target"])
def test_blocked_preview_is_single_worker_and_cannot_publish_after_invalidation(service, image_file, action):
    application = QCoreApplication.instance() or QCoreApplication([])
    manager = ObjectImageManager(service, lambda key: key)
    manager.setTarget("moon")
    started, release = Event(), Event()

    def decode(source):
        started.set()
        assert release.wait(5)
        return prepare_image(source)

    with patch("astro_viewer.app.viewmodels.object_image_manager.prepare_image", side_effect=decode) as worker:
        manager.choose(QUrl.fromLocalFile(str(image_file)))
        assert started.wait(5)
        manager.choose(QUrl.fromLocalFile(str(image_file)))
        worker.assert_called_once()
        if action == "red":
            manager.setNightVision(True)
        elif action == "target":
            manager.setTarget("messier-M31")
        else:
            manager.cancel()
        release.set()
        _wait(manager)
    assert not manager.state["ready"] and not manager.state["previewUrl"]
    assert not manager.save() and not service.records
    assert application is not None


def test_controller_personal_image_updates_alias_and_default_without_scoring(image_file):
    with _controller() as controller:
        manager = controller.objectImageManager
        controller.selectCatalogueObject("NGC 224")
        default = controller.selectedObject["image"]
        assert manager.setTarget("NGC 224")
        manager._candidate = prepare_image(image_file)
        with patch.object(controller._astronomy_engine, "solar_system_objects", side_effect=AssertionError("no astronomy")):
            assert manager.save()
        for alias in ("M31", "NGC 224"):
            controller.selectCatalogueObject(alias)
            selected = controller.selectedObject
            assert selected["id"] == "messier-M31" and selected["hasPersonalImage"]
            assert selected["imageKind"] == "personal" and selected["image"].startswith("file:")
            assert selected["thumbnail"].endswith("-thumb.jpg")
            assert not selected["imageVerified"]
        assert manager.reset()
        assert controller.selectedObject["image"] == default
