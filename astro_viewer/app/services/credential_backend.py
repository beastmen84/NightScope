from __future__ import annotations

import logging
import sys
from types import ModuleType
from typing import Protocol


logger = logging.getLogger(__name__)


class CredentialBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


def load_system_credential_backend(
    platform_id: str | None = None,
) -> CredentialBackend | None:
    """Load only the platform credential backend NightScope declares secure."""

    try:
        keyring_module = _import_keyring_module()
    except Exception:
        logger.info("Python keyring is not available; credentials cannot be stored securely.")
        return None

    if not (platform_id or sys.platform).lower().startswith("linux"):
        return keyring_module

    try:
        backend = _create_secret_service_backend()
        if backend.priority < 1:
            raise RuntimeError("Secret Service backend is not recommended")
    except Exception as exc:
        logger.info(
            "Secret Service credential backend is unavailable on Linux (%s).",
            type(exc).__name__,
        )
        return None
    return backend


def _import_keyring_module() -> ModuleType:
    import keyring

    return keyring


def _create_secret_service_backend() -> CredentialBackend:
    from keyring.backends.SecretService import Keyring

    return Keyring()
