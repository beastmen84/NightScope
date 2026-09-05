"""Verify consistent backups, portable restore, image relocation and private bundle boundaries."""

from __future__ import annotations

import ast
from contextlib import closing
import hashlib
from pathlib import Path
import shutil
import sqlite3
from unittest.mock import patch

from PIL import Image
from PySide6.QtCore import QUrl
import pytest

from astro_viewer import main
from astro_viewer.app.database import runtime_backup
from astro_viewer.app.database.bootstrap import _backup_database, initialize_database
from astro_viewer.app.database.personal_image_repository import PersonalImageRepository
from astro_viewer.app.database.runtime_backup import copy_personal_image_store, snapshot_database
from astro_viewer.app.runtime_paths import RuntimePaths
from astro_viewer.app.services.home_night_plan_overview import _alternative_item, _plan_items
from astro_viewer.app.models.sky import NightPlanItem
from astro_viewer.app.services.personal_images import PersonalImageService, prepare_image
from astro_viewer.tests.database_fixture import prepare_database
from tools.audit_qt_bundle import (
    REQUIRED_DATA_FILES, REQUIRED_DLLS, REQUIRED_LEGAL_FILES, audit_bundle,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "astro_viewer/data/schema.sql"


@pytest.fixture
def runtime(tmp_path):
    directory = tmp_path / "original runtime"
    directory.mkdir()
    database = directory / "nightscope.db"
    prepare_database(database, SCHEMA)
    source = tmp_path / "Personal photo à.png"
    Image.new("RGB", (400, 200), "#254667").save(source)
    service = PersonalImageService(PersonalImageRepository(database))
    service.save("moon", prepare_image(source))
    return service, source


@pytest.mark.parametrize("journal", ["DELETE", "WAL"])
def test_snapshot_copies_committed_state_not_uncommitted_transactions(tmp_path, journal):
    source, target = tmp_path / "live.sqlite", tmp_path / "safe.backup"
    with closing(sqlite3.connect(source)) as live:
        live.execute(f"PRAGMA journal_mode={journal}")
        live.execute("PRAGMA wal_autocheckpoint=0")
        live.execute("CREATE TABLE KeepMe (value TEXT)")
        live.execute("INSERT INTO KeepMe VALUES ('committed')")
        live.commit()
        live.execute("INSERT INTO KeepMe VALUES ('uncommitted')")
        if journal == "WAL":
            assert Path(str(source) + "-wal").stat().st_size > 0
        snapshot_database(source, target)
        with closing(sqlite3.connect(target)) as restored:
            assert restored.execute("SELECT value FROM KeepMe").fetchall() == [("committed",)]
            assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert not list(tmp_path.glob(".nightscope-backup-*"))


@pytest.mark.parametrize("failure", ["replace", "corrupt", "timeout"])
def test_failed_snapshot_preserves_previous_backup_and_cleans_temporary(runtime, monkeypatch, failure):
    service, _ = runtime
    database = service.repository.database_path
    _backup_database(database)
    backup = database.with_suffix(".db.backup")
    before = backup.read_bytes()
    if failure == "replace":
        def fail_replace(*_args):
            raise OSError("fixture disk failure")
        monkeypatch.setattr(runtime_backup.os, "replace", fail_replace)
    elif failure == "corrupt":
        database.write_bytes(b"damaged disposable test database")
    else:
        monkeypatch.setattr(runtime_backup, "BACKUP_TIMEOUT_SECONDS", -1)
    _backup_database(database)
    assert backup.read_bytes() == before
    assert not list(database.parent.glob(".nightscope-backup-*"))


def test_snapshot_refuses_original_as_target_and_redirected_backup(runtime, monkeypatch):
    service, _ = runtime
    database = service.repository.database_path
    before = database.read_bytes()
    with pytest.raises(OSError, match="Unsafe"):
        snapshot_database(database, database)
    target = database.with_suffix(".db.backup")
    target.write_bytes(b"existing backup")
    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == target or original_is_symlink(path))
    with pytest.raises(OSError, match="Unsafe"):
        snapshot_database(database, target)
    assert target.read_bytes() == b"existing backup" and database.read_bytes() == before


def test_restore_old_backup_recovers_replaced_reset_and_shared_photos(runtime, tmp_path):
    service, original = runtime
    first_hash = service.records["moon"]["image_hash"]
    database = service.repository.database_path
    service.save("messier-M31", prepare_image(original))
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("UPDATE ObjectDescription SET short_description='Personal observing text', is_builtin=0 WHERE object_id='messier-M31'")
        connection.execute("UPDATE EquipmentProfile SET profile_name='Personal profile'")
        profiles = connection.execute("SELECT * FROM EquipmentProfile").fetchall()
    _backup_database(database)
    expected_records = service.repository.all()
    Image.new("RGB", (500, 250), "#cc5511").save(original)
    service.save("moon", prepare_image(original))
    service.reset("messier-M31")
    original.unlink()

    restored_paths = RuntimePaths.colocated(tmp_path / "restored elsewhere à")
    restored_paths.data_dir.mkdir()
    copy_personal_image_store(service.directory, restored_paths.personal_images_dir)
    shutil.copy2(database.with_suffix(".db.backup"), restored_paths.database_path)
    initialize_database(restored_paths.database_path, SCHEMA)
    restored = PersonalImageService(PersonalImageRepository(restored_paths.database_path))
    assert restored.records == expected_records
    for object_id in ("moon", "messier-M31"):
        assert restored.records[object_id]["image_hash"] == first_hash
        image = Path(QUrl(restored.metadata(object_id)["image_path"]).toLocalFile())
        assert image.parent == restored_paths.personal_images_dir
        assert hashlib.sha256(image.read_bytes()).hexdigest() == first_hash
    assert len(list(restored.directory.iterdir())) == 4  # Retain both old and new pairs.
    with closing(sqlite3.connect(restored_paths.database_path)) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert not connection.execute("PRAGMA foreign_key_check").fetchall()
        assert connection.execute("SELECT * FROM EquipmentProfile").fetchall() == profiles
        assert connection.execute("SELECT short_description FROM ObjectDescription WHERE object_id='messier-M31'").fetchone() == ("Personal observing text",)


def test_personal_store_copy_is_idempotent_and_keeps_originals(runtime, tmp_path):
    service, _ = runtime
    original = {file.name: file.read_bytes() for file in service.directory.iterdir()}
    (service.directory / ".pending-interrupted").write_bytes(b"not referenced")
    target = tmp_path / "copied" / "user_images"
    copy_personal_image_store(service.directory, target)
    copy_personal_image_store(service.directory, target)
    assert {file.name: file.read_bytes() for file in target.iterdir()} == original
    assert all((service.directory / name).read_bytes() == content for name, content in original.items())


@pytest.mark.parametrize("problem", ["hash", "oversized", "conflict", "redirect"])
def test_personal_store_copy_rejects_unsafe_or_conflicting_files(runtime, tmp_path, monkeypatch, problem):
    service, _ = runtime
    target = tmp_path / "target" / "user_images"
    full, _thumbnail = service.paths(service.records["moon"]["image_hash"])
    if problem == "hash":
        full.write_bytes(b"modified fixture")
    elif problem == "oversized":
        monkeypatch.setattr(runtime_backup, "MAX_MANAGED_IMAGE_BYTES", 16)
    elif problem == "conflict":
        target.mkdir(parents=True)
        (target / full.name).write_bytes(b"keep this existing target")
    else:
        original_is_symlink = Path.is_symlink
        monkeypatch.setattr(Path, "is_symlink", lambda path: path == target or original_is_symlink(path))
    with pytest.raises(OSError):
        copy_personal_image_store(service.directory, target)
    assert full.is_file()
    if problem == "conflict":
        assert (target / full.name).read_bytes() == b"keep this existing target"
    assert not list(target.glob(".pending-*"))


@pytest.mark.parametrize("active_exists", [False, True])
def test_legacy_relocation_copies_images_only_with_its_database(runtime, tmp_path, active_exists):
    service, _ = runtime
    paths = RuntimePaths(tmp_path / "data", tmp_path / "config", tmp_path / "cache", tmp_path / "state")
    assert paths.personal_images_dir == paths.data_dir / "user_images"
    if active_exists:
        paths.data_dir.mkdir()
        prepare_database(paths.database_path, SCHEMA)
    with (
        patch.object(main, "RUNTIME_PATHS", paths),
        patch.object(main, "_legacy_runtime_paths", return_value=[service.repository.database_path]),
    ):
        main._copy_legacy_runtime_files()
    relocated = PersonalImageService(PersonalImageRepository(paths.database_path))
    if active_exists:
        assert not relocated.records and not paths.personal_images_dir.exists()
    else:
        assert relocated.records == service.records
        assert Path(QUrl(relocated.metadata("moon")["image_path"]).toLocalFile()).parent == paths.personal_images_dir
    assert service.metadata("moon") is not None


def test_legacy_relocation_keeps_committed_wal_rows(runtime, tmp_path):
    service, _ = runtime
    paths = RuntimePaths.colocated(tmp_path / "new runtime")
    with closing(sqlite3.connect(service.repository.database_path)) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("PRAGMA wal_autocheckpoint=0")
        live.execute("UPDATE ObjectDescription SET short_description='Still in WAL', is_builtin=0 WHERE object_id='moon'")
        live.commit()
        with (
            patch.object(main, "RUNTIME_PATHS", paths),
            patch.object(main, "_legacy_runtime_paths", return_value=[service.repository.database_path]),
        ):
            main._copy_legacy_runtime_files()
        with closing(sqlite3.connect(paths.database_path)) as migrated:
            assert migrated.execute("SELECT short_description FROM ObjectDescription WHERE object_id='moon'").fetchone() == ("Still in WAL",)
            assert migrated.execute("PRAGMA integrity_check").fetchone() == ("ok",)


def test_failed_image_relocation_does_not_install_database(runtime, tmp_path):
    service, _ = runtime
    paths = RuntimePaths.colocated(tmp_path / "new runtime")
    original_bytes = service.repository.database_path.read_bytes()
    with (
        patch.object(main, "RUNTIME_PATHS", paths),
        patch.object(main, "_legacy_runtime_paths", return_value=[service.repository.database_path]),
        patch.object(runtime_backup.os, "replace", side_effect=OSError("fixture write failure")),
        pytest.raises(OSError),
    ):
        main._copy_legacy_runtime_files()
    assert not paths.database_path.exists()
    assert service.repository.database_path.read_bytes() == original_bytes
    assert not list(paths.personal_images_dir.glob(".pending-*"))


def test_home_plan_and_alternatives_carry_current_thumbnail_and_default():
    target = {"id": "moon", "image": "file:///personal/full.jpg", "thumbnail": "file:///personal/thumb.jpg",
              "defaultImageUrl": "file:///resources/moon.jpg"}
    plan = NightPlanItem(time_label="22:00", object_id="moon", name="Moon", score=80,
                         difficulty="Easy", setup="", direction="S", image="stale.jpg")
    row = _plan_items([plan], target_payloads_by_id={"moon": target}, setup_models_by_object_id={}, telescope_count=0)[0]
    for payload in (row, _alternative_item(target)):
        assert payload["image"] == target["thumbnail"]
        assert payload["defaultImage"] == target["defaultImageUrl"]


@pytest.mark.parametrize("relative", ["user_images", "_internal/astro_viewer/data/user_images"])
def test_bundle_audit_rejects_personal_images_at_any_depth(tmp_path, relative):
    for filename in REQUIRED_DLLS | REQUIRED_DATA_FILES | REQUIRED_LEGAL_FILES:
        (tmp_path / filename).touch()
    (tmp_path / relative).mkdir(parents=True)
    assert audit_bundle(tmp_path) == ["runtime state present in release bundle: " + relative]


def test_qml_hook_retains_dialogs_and_folder_model_without_widening_gpl_modules():
    # Read the allowlist statically: importing a PyInstaller hook would execute
    # collection and need an active build context. Exercise its real predicate.
    path = ROOT / "packaging/pyinstaller_hooks/hook-PySide6.QtQml.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    safe_nodes = [node for node in tree.body if not isinstance(node, ast.ImportFrom) or node.module == "pathlib"]
    safe_nodes = [node for node in safe_nodes if not isinstance(node, ast.Assign)
                  or (isinstance(node.targets[0], ast.Name) and node.targets[0].id.startswith("_QML_"))]
    safe_nodes = [node for node in safe_nodes if not isinstance(node, ast.AugAssign)]
    namespace = {}
    exec(compile(ast.Module(body=safe_nodes, type_ignores=[]), str(path), "exec"), namespace)
    allowed = namespace["_is_allowed_qml_item"]
    for destination in ("QtQuick/Dialogs", "QtQuick/Dialogs/quickimpl/qml", "Qt/labs/folderlistmodel"):
        assert allowed(("fixture", "PySide6/qml/" + destination))
    for destination in ("QtQuick3D", "QtQuick/VirtualKeyboard", "QtQuick/Timeline"):
        assert not allowed(("fixture", "PySide6/qml/" + destination))
