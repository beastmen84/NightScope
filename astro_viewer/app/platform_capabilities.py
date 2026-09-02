"""Describe platform families and the host capabilities exposed to QML."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import StrEnum


NIGHTSCOPE_DESKTOP_ID = "io.github.beastmen84.NightScope"


class PlatformFamily(StrEnum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    OTHER = "other"


class SystemLocationProvider(StrEnum):
    WINDOWS = "windows"
    GEOCLUE2 = "geoclue2"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class PlatformCapabilities:
    platform_id: str
    family: PlatformFamily
    system_location_provider: SystemLocationProvider

    @property
    def is_windows(self) -> bool:
        return self.family is PlatformFamily.WINDOWS

    @property
    def is_linux(self) -> bool:
        return self.family is PlatformFamily.LINUX

    @property
    def is_macos(self) -> bool:
        return self.family is PlatformFamily.MACOS

    @property
    def system_location_supported(self) -> bool:
        return self.system_location_provider is not SystemLocationProvider.NONE

    def as_qml_context(self) -> dict[str, object]:
        return {
            "platformId": self.platform_id,
            "family": self.family.value,
            "isWindows": self.is_windows,
            "isLinux": self.is_linux,
            "isMacOS": self.is_macos,
            "systemLocationSupported": self.system_location_supported,
            "systemLocationProvider": self.system_location_provider.value,
        }


def detect_platform_capabilities(platform_id: str | None = None) -> PlatformCapabilities:
    resolved_platform_id = sys.platform if platform_id is None else platform_id
    normalized_platform_id = resolved_platform_id.strip().lower()

    if normalized_platform_id == "win32":
        family = PlatformFamily.WINDOWS
        location_provider = SystemLocationProvider.WINDOWS
    elif normalized_platform_id.startswith("linux"):
        family = PlatformFamily.LINUX
        location_provider = SystemLocationProvider.GEOCLUE2
    elif normalized_platform_id == "darwin":
        family = PlatformFamily.MACOS
        location_provider = SystemLocationProvider.NONE
    else:
        family = PlatformFamily.OTHER
        location_provider = SystemLocationProvider.NONE

    return PlatformCapabilities(
        platform_id=resolved_platform_id,
        family=family,
        system_location_provider=location_provider,
    )
