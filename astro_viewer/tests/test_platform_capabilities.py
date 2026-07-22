from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError

import pytest

from astro_viewer import main as main_module
from astro_viewer.app.platform_capabilities import (
    PlatformFamily,
    SystemLocationProvider,
    detect_platform_capabilities,
)


@pytest.mark.parametrize(
    ("platform_id", "family", "is_windows", "is_linux", "is_macos"),
    (
        ("win32", PlatformFamily.WINDOWS, True, False, False),
        ("linux", PlatformFamily.LINUX, False, True, False),
        ("linux2", PlatformFamily.LINUX, False, True, False),
        ("darwin", PlatformFamily.MACOS, False, False, True),
        ("freebsd14", PlatformFamily.OTHER, False, False, False),
    ),
)
def test_platform_family_detection(
    platform_id: str,
    family: PlatformFamily,
    is_windows: bool,
    is_linux: bool,
    is_macos: bool,
) -> None:
    capabilities = detect_platform_capabilities(platform_id)

    assert capabilities.platform_id == platform_id
    assert capabilities.family is family
    assert capabilities.is_windows is is_windows
    assert capabilities.is_linux is is_linux
    assert capabilities.is_macos is is_macos


def test_only_the_existing_windows_location_provider_is_declared_supported() -> None:
    windows = detect_platform_capabilities("win32")
    linux = detect_platform_capabilities("linux")
    macos = detect_platform_capabilities("darwin")

    assert windows.system_location_supported is True
    assert windows.system_location_provider is SystemLocationProvider.WINDOWS
    for capabilities in (linux, macos):
        assert capabilities.system_location_supported is False
        assert capabilities.system_location_provider is SystemLocationProvider.NONE


def test_qml_context_has_stable_platform_neutral_keys() -> None:
    payload = detect_platform_capabilities("linux").as_qml_context()

    assert payload == {
        "platformId": "linux",
        "family": "linux",
        "isWindows": False,
        "isLinux": True,
        "isMacOS": False,
        "systemLocationSupported": False,
        "systemLocationProvider": "none",
    }


def test_platform_capabilities_are_immutable() -> None:
    capabilities = detect_platform_capabilities("win32")

    with pytest.raises(FrozenInstanceError):
        capabilities.platform_id = "linux"  # type: ignore[misc]


def test_main_detects_the_host_platform_once() -> None:
    assert main_module.PLATFORM_CAPABILITIES == detect_platform_capabilities(sys.platform)
