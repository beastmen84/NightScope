from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import QCoreApplication

from astro_viewer.app.platform_capabilities import PlatformFamily
from astro_viewer.app.runtime_paths import RuntimePaths, resolve_runtime_paths


@pytest.mark.parametrize(
    "platform_family",
    [
        PlatformFamily.WINDOWS,
        PlatformFamily.MACOS,
        PlatformFamily.OTHER,
    ],
)
def test_non_linux_source_keeps_project_portable_layout(
    platform_family: PlatformFamily,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "source"
    executable_dir = tmp_path / "python"

    paths = resolve_runtime_paths(
        platform_family=platform_family,
        project_root=project_root,
        executable_dir=executable_dir,
        frozen=False,
        environment={},
        home_dir=tmp_path / "home",
    )

    assert paths == RuntimePaths.colocated(project_root)


@pytest.mark.parametrize(
    "platform_family",
    [
        PlatformFamily.WINDOWS,
        PlatformFamily.MACOS,
        PlatformFamily.OTHER,
    ],
)
def test_non_linux_frozen_build_keeps_executable_portable_layout(
    platform_family: PlatformFamily,
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "bundle" / "_internal"
    executable_dir = tmp_path / "bundle"

    paths = resolve_runtime_paths(
        platform_family=platform_family,
        project_root=project_root,
        executable_dir=executable_dir,
        frozen=True,
        environment={},
        home_dir=tmp_path / "home",
    )

    assert paths == RuntimePaths.colocated(executable_dir)


def test_linux_uses_default_xdg_directories(tmp_path: Path) -> None:
    home = tmp_path / "home"

    paths = resolve_runtime_paths(
        platform_family=PlatformFamily.LINUX,
        project_root=tmp_path / "source",
        executable_dir=tmp_path / "bundle",
        frozen=True,
        environment={},
        home_dir=home,
    )

    assert paths.data_dir == (home / ".local" / "share" / "NightScope").resolve()
    assert paths.config_dir == (home / ".config" / "NightScope").resolve()
    assert paths.cache_dir == (home / ".cache" / "NightScope").resolve()
    assert paths.state_dir == (home / ".local" / "state" / "NightScope").resolve()


def test_linux_honors_absolute_xdg_overrides(tmp_path: Path) -> None:
    environment = {
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_STATE_HOME": str(tmp_path / "state"),
    }

    paths = resolve_runtime_paths(
        platform_family=PlatformFamily.LINUX,
        project_root=tmp_path / "source",
        executable_dir=tmp_path / "bundle",
        frozen=False,
        environment=environment,
        home_dir=tmp_path / "home",
    )

    assert paths.data_dir == (tmp_path / "data" / "NightScope").resolve()
    assert paths.config_dir == (tmp_path / "config" / "NightScope").resolve()
    assert paths.cache_dir == (tmp_path / "cache" / "NightScope").resolve()
    assert paths.state_dir == (tmp_path / "state" / "NightScope").resolve()


def test_linux_ignores_relative_xdg_values(tmp_path: Path) -> None:
    home = tmp_path / "home"
    environment = {
        "XDG_DATA_HOME": "relative-data",
        "XDG_CONFIG_HOME": "relative-config",
        "XDG_CACHE_HOME": "relative-cache",
        "XDG_STATE_HOME": "relative-state",
    }

    paths = resolve_runtime_paths(
        platform_family=PlatformFamily.LINUX,
        project_root=tmp_path / "source",
        executable_dir=tmp_path / "bundle",
        frozen=False,
        environment=environment,
        home_dir=home,
    )

    assert paths.data_dir == (home / ".local" / "share" / "NightScope").resolve()
    assert paths.config_dir == (home / ".config" / "NightScope").resolve()
    assert paths.cache_dir == (home / ".cache" / "NightScope").resolve()
    assert paths.state_dir == (home / ".local" / "state" / "NightScope").resolve()


@pytest.mark.parametrize("platform_family", list(PlatformFamily))
def test_runtime_override_colocates_every_path(
    platform_family: PlatformFamily,
    tmp_path: Path,
) -> None:
    isolated_runtime = tmp_path / "isolated"

    paths = resolve_runtime_paths(
        platform_family=platform_family,
        project_root=tmp_path / "source",
        executable_dir=tmp_path / "bundle",
        frozen=platform_family is PlatformFamily.LINUX,
        override=str(isolated_runtime),
        environment={},
        home_dir=tmp_path / "home",
    )

    assert paths == RuntimePaths.colocated(isolated_runtime)


def test_runtime_file_contract() -> None:
    paths = RuntimePaths(
        data_dir=Path("/data/NightScope"),
        config_dir=Path("/config/NightScope"),
        cache_dir=Path("/cache/NightScope"),
        state_dir=Path("/state/NightScope"),
    )

    assert paths.database_path == Path("/data/NightScope/nightscope.db")
    assert paths.database_backup_path == Path(
        "/data/NightScope/nightscope.db.backup"
    )
    assert paths.preferences_path == Path(
        "/config/NightScope/user_preferences.json"
    )
    assert paths.location_cache_path == Path(
        "/cache/NightScope/location_cache.json"
    )
    assert paths.nasa_aod_cache_path == Path(
        "/cache/NightScope/nasa_aod_cache.json"
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows entrypoint contract")
def test_windows_entrypoint_keeps_current_colocated_runtime() -> None:
    from astro_viewer import main as main_module

    assert main_module.RUNTIME_PATHS == RuntimePaths.colocated(
        main_module.PROJECT_ROOT
    )
    assert main_module.RUNTIME_DIR == main_module.PROJECT_ROOT


def test_database_bootstrap_cli_uses_canonical_runtime_paths() -> None:
    bootstrap = (
        Path(__file__).resolve().parents[1] / "app" / "database" / "bootstrap.py"
    ).read_text(encoding="utf-8")

    main_block = bootstrap[bootstrap.index('if __name__ == "__main__":') :]
    assert "from astro_viewer.main import _data_dir, _database_paths" in main_block
    assert "runtime_database_path, schema_path = _database_paths()" in main_block
    assert 'base_dir.parent / "nightscope.db"' not in main_block


def test_app_controller_uses_explicit_config_and_cache_paths(
    tmp_path: Path,
) -> None:
    from astro_viewer.app.database.bootstrap import initialize_database
    from astro_viewer.app.viewmodels.app_controller import AppController

    app = QCoreApplication.instance() or QCoreApplication([])
    base_dir = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "data" / "NightScope" / "nightscope.db"
    preferences_path = tmp_path / "config" / "NightScope" / "user_preferences.json"
    location_cache_path = tmp_path / "cache" / "NightScope" / "location_cache.json"
    nasa_aod_cache_path = tmp_path / "cache" / "NightScope" / "nasa_aod_cache.json"
    initialize_database(
        database_path,
        base_dir / "data" / "schema.sql",
        geonames_data_dir=base_dir / "data",
    )

    with patch.object(
        AppController,
        "_start_background_task",
        new=staticmethod(lambda target: None),
    ):
        controller = AppController(
            base_dir=base_dir,
            database_path=database_path,
            preferences_path=preferences_path,
            location_cache_path=location_cache_path,
            nasa_aod_cache_path=nasa_aod_cache_path,
        )

    try:
        assert controller._location_preferences._preferences_path == preferences_path
        assert controller._location_preferences._cache_path == location_cache_path
        assert controller._earthdata_credential_store._preferences_path == (
            preferences_path
        )
        assert controller._openaq_credential_store._preferences_path == (
            preferences_path
        )
        assert controller._location_service.ip_provider._cache_path == (
            location_cache_path
        )
        assert controller._nasa_aod_provider._cache_path == nasa_aod_cache_path
        assert app is QCoreApplication.instance()
    finally:
        if hasattr(controller._astronomy_engine, "close"):
            controller._astronomy_engine.close()
