"""Check GitHub releases asynchronously and persist user update preferences."""

from __future__ import annotations

import json
import logging
import platform
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from threading import Lock, Thread
from typing import Callable
from urllib.parse import urlparse

import requests
from PySide6.QtCore import QObject, Property, Signal, Slot


logger = logging.getLogger(__name__)

RELEASES_API_URL = "https://api.github.com/repos/beastmen84/NightScope/releases"
OFFICIAL_RELEASE_PATH_PREFIX = "/beastmen84/NightScope/releases/"
REQUEST_TIMEOUT_SECONDS = 4.0
_VERSION_PATTERN = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    url: str


def parse_version(value: str) -> tuple[int, int, int] | None:
    match = _VERSION_PATTERN.fullmatch(value.strip())
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def find_newer_release(
    current_version: str,
    *,
    http_get: Callable[..., requests.Response] = requests.get,
    platform_name: str | None = None,
    machine: str | None = None,
) -> ReleaseInfo | None:
    """Find a newer public release with an uploaded compatible portable artifact.

    Inspect at most 300 releases (three bounded requests), not the repository's
    source-only/latest tag. Current bundles target Windows/Linux x86-64; no
    architecture or unrecognized-platform guess authorizes an update offer.
    Only an official release page is returned; no package is downloaded here.
    """
    current = parse_version(current_version)
    if current is None:
        raise ValueError(f"Invalid current NightScope version: {current_version!r}")

    system = platform_name if platform_name is not None else sys.platform
    architecture = (machine if machine is not None else platform.machine()).lower()
    suffixes = ("windows-x64.zip",) if system == "win32" else (
        ("debian-12-x64.tar.gz", "linux-x64.tar.gz") if system.startswith("linux") else ()
    )
    if not suffixes or architecture not in {"amd64", "x86_64"}:
        return None
    best: tuple[tuple[int, int, int], str] | None = None
    for page in range(1, 4):
        response = http_get(
            RELEASES_API_URL,
            params={"per_page": 100, "page": page},
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"NightScope/{current_version.strip()}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("Invalid GitHub release response.")
        for release in payload:
            if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
                continue
            tag = str(release.get("tag_name") or "").strip()
            version = parse_version(tag)
            url = str(release.get("html_url") or "").strip()
            if version is None or version <= current or not _is_official_release_url(url):
                continue
            if best is not None and version <= best[0]:
                continue
            assets = release.get("assets")
            if not isinstance(assets, list):
                continue
            if any(_compatible_asset(asset, tag, suffixes) for asset in assets):
                best = version, url
        if len(payload) < 100:
            break
    return ReleaseInfo(".".join(map(str, best[0])), best[1]) if best else None


def _compatible_asset(asset: object, tag: str, suffixes: tuple[str, ...]) -> bool:
    if not isinstance(asset, dict) or asset.get("state") != "uploaded":
        return False
    size = asset.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        return False
    name = str(asset.get("name") or "")
    version = tag.removeprefix("v")
    expected_names = {
        f"NightScope-{prefix}{version}-{suffix}"
        for prefix in ("", "v") for suffix in suffixes
    }
    url = str(asset.get("browser_download_url") or "")
    return name in expected_names and _is_official_release_url(url) and urlparse(url).path == (
        f"{OFFICIAL_RELEASE_PATH_PREFIX}download/{tag}/{name}"
    )


def _is_official_release_url(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "github.com"
        and not parsed.username
        and not parsed.password
        and parsed.netloc == "github.com"
        and parsed.path.startswith(OFFICIAL_RELEASE_PATH_PREFIX)
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    )


class UpdateManager(QObject):
    updateChanged = Signal()
    updateAvailable = Signal()
    _checkFinished = Signal(object)

    def __init__(
        self,
        *,
        version_path: Path,
        preferences_path: Path,
        http_get: Callable[..., requests.Response] = requests.get,
    ):
        super().__init__()
        self._version_path = version_path
        self._preferences_path = preferences_path
        self._http_get = http_get
        self._current_version = self._read_current_version()
        self._latest_version = ""
        self._release_url = ""
        self._check_started = False
        self._check_lock = Lock()
        self._checkFinished.connect(self._handle_check_finished)

    @Property(str, constant=True)
    def currentVersion(self) -> str:
        return self._current_version

    @Property(str, notify=updateChanged)
    def latestVersion(self) -> str:
        return self._latest_version

    @Property(str, notify=updateChanged)
    def releaseUrl(self) -> str:
        return self._release_url

    @Slot()
    def checkForUpdates(self) -> None:
        with self._check_lock:
            if self._check_started:
                return
            self._check_started = True
        if not self._current_version:
            return

        def run_check() -> None:
            release = None
            try:
                release = find_newer_release(
                    self._current_version,
                    http_get=self._http_get,
                )
            except (OSError, ValueError, requests.RequestException):
                logger.debug("Startup update check unavailable.", exc_info=True)
            self._checkFinished.emit(release)

        Thread(target=run_check, name="NightScopeUpdateCheck", daemon=True).start()

    @Slot()
    def ignoreCurrentUpdate(self) -> None:
        if not self._latest_version:
            return
        payload = self._read_preferences()
        payload["ignored_update_version"] = self._latest_version
        self._write_preferences(payload)

    @Slot(object)
    def _handle_check_finished(self, release: object) -> None:
        if not isinstance(release, ReleaseInfo):
            return
        ignored_version = str(
            self._read_preferences().get("ignored_update_version") or ""
        ).strip()
        if release.version == ignored_version:
            return
        self._latest_version = release.version
        self._release_url = release.url
        self.updateChanged.emit()
        self.updateAvailable.emit()

    def _read_current_version(self) -> str:
        try:
            version = self._version_path.read_text(encoding="utf-8").strip()
        except OSError:
            logger.warning(
                "NightScope version file is unavailable: %s",
                self._version_path,
                exc_info=True,
            )
            return ""
        if parse_version(version) is None:
            logger.warning("NightScope version is invalid: %r", version)
            return ""
        return version

    def _read_preferences(self) -> dict:
        if not self._preferences_path.exists():
            return {}
        try:
            payload = json.loads(self._preferences_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning(
                "Update preference could not be read: %s",
                self._preferences_path,
                exc_info=True,
            )
            return {}
        return payload if isinstance(payload, dict) else {}

    def _write_preferences(self, payload: dict) -> None:
        temporary_path = self._preferences_path.with_suffix(
            self._preferences_path.suffix + ".tmp"
        )
        try:
            self._preferences_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            temporary_path.replace(self._preferences_path)
        except OSError:
            logger.warning(
                "Update preference could not be written: %s",
                self._preferences_path,
                exc_info=True,
            )
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
