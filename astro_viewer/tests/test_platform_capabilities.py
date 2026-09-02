"""Protect platform feature detection and capability-dependent composition."""

from __future__ import annotations

import sys
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

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


def test_implemented_system_location_providers_are_declared_supported() -> None:
    windows = detect_platform_capabilities("win32")
    linux = detect_platform_capabilities("linux")
    macos = detect_platform_capabilities("darwin")

    assert windows.system_location_supported is True
    assert windows.system_location_provider is SystemLocationProvider.WINDOWS
    assert linux.system_location_supported is True
    assert linux.system_location_provider is SystemLocationProvider.GEOCLUE2
    assert macos.system_location_supported is False
    assert macos.system_location_provider is SystemLocationProvider.NONE


def test_qml_context_has_stable_platform_neutral_keys() -> None:
    payload = detect_platform_capabilities("linux").as_qml_context()

    assert payload == {
        "platformId": "linux",
        "family": "linux",
        "isWindows": False,
        "isLinux": True,
        "isMacOS": False,
        "systemLocationSupported": True,
        "systemLocationProvider": "geoclue2",
    }


def test_platform_capabilities_are_immutable() -> None:
    capabilities = detect_platform_capabilities("win32")

    with pytest.raises(FrozenInstanceError):
        capabilities.platform_id = "linux"  # type: ignore[misc]


def test_main_detects_the_host_platform_once() -> None:
    assert main_module.PLATFORM_CAPABILITIES == detect_platform_capabilities(sys.platform)


def test_linux_application_metadata_sets_the_geoclue_desktop_id() -> None:
    app = Mock()

    with patch.object(
        main_module,
        "PLATFORM_CAPABILITIES",
        detect_platform_capabilities("linux"),
    ):
        main_module._configure_application_metadata(app)

    app.setApplicationName.assert_called_once_with("NightScope")
    app.setOrganizationName.assert_called_once_with("NightScope")
    app.setDesktopFileName.assert_called_once_with("io.github.beastmen84.NightScope")


def test_windows_application_metadata_does_not_change_the_desktop_file_name() -> None:
    app = Mock()

    with patch.object(
        main_module,
        "PLATFORM_CAPABILITIES",
        detect_platform_capabilities("win32"),
    ):
        main_module._configure_application_metadata(app)

    app.setApplicationName.assert_called_once_with("NightScope")
    app.setOrganizationName.assert_called_once_with("NightScope")
    app.setDesktopFileName.assert_not_called()
