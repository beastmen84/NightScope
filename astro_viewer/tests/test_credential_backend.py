"""Protect rejection of insecure keyring backends and supported backend selection."""

from __future__ import annotations

from unittest.mock import Mock, patch

from astro_viewer.app.services.credential_backend import (
    load_system_credential_backend,
)


def test_windows_keeps_the_keyring_platform_dispatcher() -> None:
    keyring_module = Mock()

    with (
        patch(
            "astro_viewer.app.services.credential_backend._import_keyring_module",
            return_value=keyring_module,
        ),
        patch(
            "astro_viewer.app.services.credential_backend._create_secret_service_backend"
        ) as create_secret_service,
    ):
        backend = load_system_credential_backend("win32")

    assert backend is keyring_module
    create_secret_service.assert_not_called()


def test_linux_uses_secret_service_instead_of_the_configured_keyring_backend() -> None:
    keyring_module = Mock()
    secret_service = Mock(priority=5)

    with (
        patch(
            "astro_viewer.app.services.credential_backend._import_keyring_module",
            return_value=keyring_module,
        ),
        patch(
            "astro_viewer.app.services.credential_backend._create_secret_service_backend",
            return_value=secret_service,
        ),
    ):
        backend = load_system_credential_backend("linux")

    assert backend is secret_service
    keyring_module.get_keyring.assert_not_called()


def test_linux_rejects_an_unavailable_secret_service() -> None:
    with (
        patch(
            "astro_viewer.app.services.credential_backend._import_keyring_module",
            return_value=Mock(),
        ),
        patch(
            "astro_viewer.app.services.credential_backend._create_secret_service_backend",
            side_effect=RuntimeError("D-Bus service is unavailable"),
        ),
    ):
        backend = load_system_credential_backend("linux")

    assert backend is None


def test_linux_rejects_a_non_recommended_secret_service_backend() -> None:
    with (
        patch(
            "astro_viewer.app.services.credential_backend._import_keyring_module",
            return_value=Mock(),
        ),
        patch(
            "astro_viewer.app.services.credential_backend._create_secret_service_backend",
            return_value=Mock(priority=0),
        ),
    ):
        backend = load_system_credential_backend("linux2")

    assert backend is None


def test_missing_keyring_disables_secure_storage() -> None:
    with patch(
        "astro_viewer.app.services.credential_backend._import_keyring_module",
        side_effect=ImportError,
    ):
        backend = load_system_credential_backend("win32")

    assert backend is None
