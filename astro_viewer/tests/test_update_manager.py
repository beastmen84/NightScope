from __future__ import annotations

import json
from pathlib import Path
from threading import Event
from unittest.mock import Mock

import pytest
import requests
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

from astro_viewer.app.services.update_manager import (
    LATEST_RELEASE_API_URL,
    REQUEST_TIMEOUT_SECONDS,
    ReleaseInfo,
    UpdateManager,
    find_newer_release,
    parse_version,
)


def _response(payload: object, *, status_code: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.url = LATEST_RELEASE_API_URL
    response._content = json.dumps(payload).encode("utf-8")
    response.headers["Content-Type"] = "application/json"
    return response


def _release_payload(
    tag_name: str,
    *,
    url: str | None = None,
    draft: bool = False,
    prerelease: bool = False,
) -> dict:
    return {
        "tag_name": tag_name,
        "html_url": url
        or f"https://github.com/beastmen84/NightScope/releases/tag/{tag_name}",
        "draft": draft,
        "prerelease": prerelease,
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1.37.0", (1, 37, 0)),
        ("v1.38.0", (1, 38, 0)),
        (" 2.0.1 ", (2, 0, 1)),
        ("1.38", None),
        ("1.38.0-beta", None),
        ("release-1.38.0", None),
    ],
)
def test_parse_version_accepts_only_release_versions(
    value: str,
    expected: tuple[int, int, int] | None,
) -> None:
    assert parse_version(value) == expected


def test_find_newer_release_uses_github_latest_endpoint() -> None:
    http_get = Mock(return_value=_response(_release_payload("v1.10.0")))

    release = find_newer_release("1.9.0", http_get=http_get)

    assert release == ReleaseInfo(
        version="1.10.0",
        url="https://github.com/beastmen84/NightScope/releases/tag/v1.10.0",
    )
    http_get.assert_called_once_with(
        LATEST_RELEASE_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "NightScope/1.9.0",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


@pytest.mark.parametrize(
    "payload",
    [
        _release_payload("v1.37.0"),
        _release_payload("v1.36.9"),
        _release_payload("v1.38.0", draft=True),
        _release_payload("v1.38.0", prerelease=True),
        _release_payload(
            "v1.38.0",
            url="https://example.com/beastmen84/NightScope/releases/tag/v1.38.0",
        ),
        _release_payload("not-a-version"),
    ],
)
def test_find_newer_release_rejects_non_updates(payload: dict) -> None:
    assert (
        find_newer_release("1.37.0", http_get=Mock(return_value=_response(payload)))
        is None
    )


def test_find_newer_release_rejects_invalid_current_version() -> None:
    with pytest.raises(ValueError, match="Invalid current NightScope version"):
        find_newer_release("development", http_get=Mock())


def test_update_manager_notifies_for_a_non_ignored_release(tmp_path: Path) -> None:
    version_path = tmp_path / "VERSION"
    version_path.write_text("1.37.0\n", encoding="utf-8")
    manager = UpdateManager(
        version_path=version_path,
        preferences_path=tmp_path / "user_preferences.json",
    )
    available = []
    changed = []
    manager.updateAvailable.connect(lambda: available.append(True))
    manager.updateChanged.connect(lambda: changed.append(True))

    manager._handle_check_finished(
        ReleaseInfo(
            version="1.38.0",
            url="https://github.com/beastmen84/NightScope/releases/tag/v1.38.0",
        )
    )

    assert manager.currentVersion == "1.37.0"
    assert manager.latestVersion == "1.38.0"
    assert manager.releaseUrl.endswith("/v1.38.0")
    assert changed == [True]
    assert available == [True]


def test_update_manager_respects_ignored_release(tmp_path: Path) -> None:
    version_path = tmp_path / "VERSION"
    preferences_path = tmp_path / "user_preferences.json"
    version_path.write_text("1.37.0", encoding="utf-8")
    preferences_path.write_text(
        json.dumps({"language": "es", "ignored_update_version": "1.38.0"}),
        encoding="utf-8",
    )
    manager = UpdateManager(
        version_path=version_path,
        preferences_path=preferences_path,
    )
    available = []
    manager.updateAvailable.connect(lambda: available.append(True))

    manager._handle_check_finished(
        ReleaseInfo(
            version="1.38.0",
            url="https://github.com/beastmen84/NightScope/releases/tag/v1.38.0",
        )
    )

    assert manager.latestVersion == ""
    assert manager.releaseUrl == ""
    assert available == []


def test_ignoring_update_preserves_other_preferences(tmp_path: Path) -> None:
    version_path = tmp_path / "VERSION"
    preferences_path = tmp_path / "user_preferences.json"
    version_path.write_text("1.37.0", encoding="utf-8")
    preferences_path.write_text(
        json.dumps({"language": "en", "red_night_vision_enabled": True}),
        encoding="utf-8",
    )
    manager = UpdateManager(
        version_path=version_path,
        preferences_path=preferences_path,
    )
    manager._handle_check_finished(
        ReleaseInfo(
            version="1.38.0",
            url="https://github.com/beastmen84/NightScope/releases/tag/v1.38.0",
        )
    )

    manager.ignoreCurrentUpdate()

    assert json.loads(preferences_path.read_text(encoding="utf-8")) == {
        "language": "en",
        "red_night_vision_enabled": True,
        "ignored_update_version": "1.38.0",
    }


def test_update_manager_starts_only_one_background_check(tmp_path: Path) -> None:
    version_path = tmp_path / "VERSION"
    version_path.write_text("1.37.0", encoding="utf-8")
    request_started = Event()
    release_request = Mock(
        side_effect=lambda *args, **kwargs: (
            request_started.set(),
            _response(_release_payload("v1.38.0")),
        )[1]
    )
    manager = UpdateManager(
        version_path=version_path,
        preferences_path=tmp_path / "user_preferences.json",
        http_get=release_request,
    )

    manager.checkForUpdates()
    manager.checkForUpdates()

    assert request_started.wait(timeout=2)
    assert release_request.call_count == 1


def test_background_result_reaches_qt_event_loop(tmp_path: Path) -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    version_path = tmp_path / "VERSION"
    version_path.write_text("1.37.0", encoding="utf-8")
    manager = UpdateManager(
        version_path=version_path,
        preferences_path=tmp_path / "user_preferences.json",
        http_get=Mock(return_value=_response(_release_payload("v1.38.0"))),
    )
    loop = QEventLoop()
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    manager.updateAvailable.connect(loop.quit)

    timeout.start(2_000)
    manager.checkForUpdates()
    loop.exec()
    completed_before_timeout = timeout.isActive()
    timeout.stop()

    assert app is QCoreApplication.instance()
    assert completed_before_timeout is True
    assert manager.latestVersion == "1.38.0"
    assert manager.releaseUrl.endswith("/v1.38.0")


@pytest.mark.parametrize("version_text", [None, "development"])
def test_invalid_version_file_disables_check_without_blocking_startup(
    tmp_path: Path,
    version_text: str | None,
) -> None:
    version_path = tmp_path / "VERSION"
    if version_text is not None:
        version_path.write_text(version_text, encoding="utf-8")
    http_get = Mock()
    manager = UpdateManager(
        version_path=version_path,
        preferences_path=tmp_path / "user_preferences.json",
        http_get=http_get,
    )

    manager.checkForUpdates()

    assert manager.currentVersion == ""
    http_get.assert_not_called()


def test_update_popup_uses_themed_localized_controls() -> None:
    qml = (
        Path(__file__).resolve().parents[1] / "app" / "ui" / "main.qml"
    ).read_text(encoding="utf-8")

    assert 'objectName: "updateAvailableDialog"' in qml
    assert 'title: qsTr("Nuova versione disponibile")' in qml
    assert 'acceptText: qsTr("Scarica aggiornamento")' in qml
    assert 'cancelText: qsTr("Più tardi")' in qml
    assert "Qt.openUrlExternally(updateManager.releaseUrl)" in qml
    assert "updateManager.ignoreCurrentUpdate()" in qml
