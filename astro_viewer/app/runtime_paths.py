"""Resolve portable and XDG runtime storage paths before app construction."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from astro_viewer.app.platform_capabilities import PlatformFamily


APP_DIRECTORY_NAME = "NightScope"


@dataclass(frozen=True, slots=True)
class RuntimePaths:
    data_dir: Path
    config_dir: Path
    cache_dir: Path
    state_dir: Path

    @classmethod
    def colocated(cls, directory: Path) -> RuntimePaths:
        resolved = directory.expanduser().resolve()
        return cls(
            data_dir=resolved,
            config_dir=resolved,
            cache_dir=resolved,
            state_dir=resolved,
        )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "nightscope.db"

    @property
    def database_backup_path(self) -> Path:
        return self.data_dir / "nightscope.db.backup"

    @property
    def preferences_path(self) -> Path:
        return self.config_dir / "user_preferences.json"

    @property
    def location_cache_path(self) -> Path:
        return self.cache_dir / "location_cache.json"

    @property
    def nasa_aod_cache_path(self) -> Path:
        return self.cache_dir / "nasa_aod_cache.json"


def resolve_runtime_paths(
    *,
    platform_family: PlatformFamily,
    project_root: Path,
    executable_dir: Path,
    frozen: bool,
    override: str = "",
    environment: Mapping[str, str] | None = None,
    home_dir: Path | None = None,
) -> RuntimePaths:
    normalized_override = override.strip()
    if normalized_override:
        return RuntimePaths.colocated(Path(normalized_override))

    if platform_family is not PlatformFamily.LINUX:
        portable_dir = executable_dir if frozen else project_root
        return RuntimePaths.colocated(portable_dir)

    env = os.environ if environment is None else environment
    home = (Path.home() if home_dir is None else home_dir).expanduser().resolve()
    data_home = _xdg_home(env, "XDG_DATA_HOME", home / ".local" / "share")
    config_home = _xdg_home(env, "XDG_CONFIG_HOME", home / ".config")
    cache_home = _xdg_home(env, "XDG_CACHE_HOME", home / ".cache")
    state_home = _xdg_home(env, "XDG_STATE_HOME", home / ".local" / "state")
    return RuntimePaths(
        data_dir=data_home / APP_DIRECTORY_NAME,
        config_dir=config_home / APP_DIRECTORY_NAME,
        cache_dir=cache_home / APP_DIRECTORY_NAME,
        state_dir=state_home / APP_DIRECTORY_NAME,
    )


def _xdg_home(
    environment: Mapping[str, str],
    variable: str,
    fallback: Path,
) -> Path:
    raw_value = str(environment.get(variable) or "").strip()
    if raw_value:
        candidate = Path(raw_value).expanduser()
        if candidate.is_absolute():
            return candidate.resolve()
    return fallback.resolve()
