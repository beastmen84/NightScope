from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from threading import Event, Thread
from unittest.mock import patch

from astro_viewer.app.services.earthdata_credentials import (
    EarthdataConnectionTester,
    EarthdataCredentialStore,
    temporary_earthdata_netrc,
)


class FakeCredentialBackend:
    def __init__(self) -> None:
        self.passwords: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.passwords.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.passwords[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        self.passwords.pop((service_name, username), None)


class FailingDeleteCredentialBackend(FakeCredentialBackend):
    def delete_password(self, service_name: str, username: str) -> None:
        raise RuntimeError("missing")


class FakeEarthdataResponse:
    def __init__(self, text: str, url: str = "https://example.test", status_code: int = 200) -> None:
        self.text = text
        self.url = url
        self.status_code = status_code


class FakeEarthdataSession:
    def __init__(self, response: FakeEarthdataResponse) -> None:
        self._response = response

    def get(self, *_args, **_kwargs) -> FakeEarthdataResponse:
        return self._response


class EarthdataCredentialStoreTests(unittest.TestCase):
    def test_save_reads_and_removes_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = FakeCredentialBackend()
            store = EarthdataCredentialStore(Path(temp_dir) / "user_preferences.json", backend=backend)

            state = store.save("astro-user", "secret-password")

            self.assertTrue(state.configured)
            self.assertTrue(state.secure_store_available)
            self.assertFalse(state.connection_verified)
            self.assertFalse(state.authorization_required)
            self.assertEqual(state.username, "astro-user")
            self.assertEqual(store.username(), "astro-user")
            self.assertEqual(store.password(), "secret-password")

            removed = store.remove()

            self.assertFalse(removed.configured)
            self.assertEqual(store.username(), "")
            self.assertIsNone(store.password())

    def test_changing_username_removes_old_password(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = FakeCredentialBackend()
            store = EarthdataCredentialStore(Path(temp_dir) / "user_preferences.json", backend=backend)

            store.save("old-user", "old-password")
            store.save("new-user", "new-password")

            self.assertEqual(store.username(), "new-user")
            self.assertEqual(store.password(), "new-password")
            self.assertNotIn(("NightScope Earthdata", "old-user"), backend.passwords)

    def test_missing_secure_password_log_does_not_expose_username(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = EarthdataCredentialStore(
                Path(temp_dir) / "user_preferences.json",
                backend=FailingDeleteCredentialBackend(),
            )

            with self.assertLogs(
                "astro_viewer.app.services.earthdata_credentials", level="INFO"
            ) as logs:
                store._delete_backend_password("private-earthdata-user")

        log_text = "\n".join(logs.output)
        self.assertIn("password was not present", log_text)
        self.assertNotIn("private-earthdata-user", log_text)

    def test_connection_status_is_persisted_and_reset_by_save(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = FakeCredentialBackend()
            store = EarthdataCredentialStore(Path(temp_dir) / "user_preferences.json", backend=backend)
            store.save("astro-user", "secret-password")

            verified = store.mark_connection_verified("Connessione Earthdata LAADS verificata.")

            self.assertTrue(verified.connection_verified)
            self.assertFalse(verified.authorization_required)
            self.assertTrue(store.state().connection_verified)

            saved = store.save("astro-user", "new-password")

            self.assertFalse(saved.connection_verified)
            self.assertFalse(saved.authorization_required)
            self.assertFalse(store.state().connection_verified)

    def test_authorization_required_state_is_persisted_until_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = FakeCredentialBackend()
            store = EarthdataCredentialStore(Path(temp_dir) / "user_preferences.json", backend=backend)
            store.save("astro-user", "secret-password")

            authorization_required = store.mark_authorization_required("Autorizza l'app LAADS OPeNDAP.")

            self.assertFalse(authorization_required.connection_verified)
            self.assertTrue(authorization_required.authorization_required)
            self.assertTrue(store.state().authorization_required)

            verified = store.mark_connection_verified("Connessione Earthdata LAADS verificata.")

            self.assertTrue(verified.connection_verified)
            self.assertFalse(verified.authorization_required)

    def test_rejects_empty_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = EarthdataCredentialStore(Path(temp_dir) / "user_preferences.json", backend=FakeCredentialBackend())

            with self.assertRaises(ValueError):
                store.save("", "secret-password")

            with self.assertRaises(ValueError):
                store.save("astro-user", "")


class EarthdataConnectionTesterTests(unittest.TestCase):
    def test_reports_laads_authorization_requirement(self) -> None:
        response = FakeEarthdataResponse(
            "Pre authorization required",
            "https://urs.earthdata.nasa.gov/approve_app?client_id=A6th7HB-3EBoO7iOCiCLlA",
        )
        tester = EarthdataConnectionTester()

        with patch.object(EarthdataConnectionTester, "_session", return_value=FakeEarthdataSession(response)):
            result = tester.test("astro-user", "secret-password")

        self.assertFalse(result.ok)
        self.assertTrue(result.authorization_required)
        self.assertIn("Autorizza l'app LAADS OPeNDAP", result.message)

    def test_reports_laads_authorization_requirement_before_http_403(self) -> None:
        response = FakeEarthdataResponse(
            "Access Denied by OAuth2 Provider",
            "https://ladsweb.modaps.eosdis.nasa.gov/oauth/callback?error=Pre+authorization+required",
            status_code=403,
        )
        tester = EarthdataConnectionTester()

        with patch.object(EarthdataConnectionTester, "_session", return_value=FakeEarthdataSession(response)):
            result = tester.test("astro-user", "secret-password")

        self.assertFalse(result.ok)
        self.assertTrue(result.authorization_required)
        self.assertIn("Autorizza l'app LAADS OPeNDAP", result.message)

    def test_reports_invalid_credentials_before_http_401(self) -> None:
        response = FakeEarthdataResponse(
            "Credentials (username, password) are invalid",
            "https://urs.earthdata.nasa.gov/oauth/authorize",
            status_code=401,
        )
        tester = EarthdataConnectionTester()

        with patch.object(EarthdataConnectionTester, "_session", return_value=FakeEarthdataSession(response)):
            result = tester.test("astro-user", "wrong-password")

        self.assertFalse(result.ok)
        self.assertFalse(result.authorization_required)
        self.assertIn("Verifica username e password", result.message)

    def test_keeps_unrecognized_http_403_generic(self) -> None:
        response = FakeEarthdataResponse(
            "Forbidden",
            "https://ladsweb.modaps.eosdis.nasa.gov/opendap/resource",
            status_code=403,
        )
        tester = EarthdataConnectionTester()

        with patch.object(EarthdataConnectionTester, "_session", return_value=FakeEarthdataSession(response)):
            result = tester.test("astro-user", "secret-password")

        self.assertFalse(result.ok)
        self.assertFalse(result.authorization_required)
        self.assertIn("HTTP 403", result.message)

    def test_does_not_accept_dataset_markers_without_http_200(self) -> None:
        response = FakeEarthdataResponse(
            "Dataset { AllAngle_Composite_Snow_Free }",
            "https://ladsweb.modaps.eosdis.nasa.gov/opendap/resource",
            status_code=503,
        )
        tester = EarthdataConnectionTester()

        with patch.object(EarthdataConnectionTester, "_session", return_value=FakeEarthdataSession(response)):
            result = tester.test("astro-user", "secret-password")

        self.assertFalse(result.ok)
        self.assertFalse(result.authorization_required)
        self.assertIn("HTTP 503", result.message)

    def test_temporary_netrc_contexts_are_serialized_and_restore_environment(self) -> None:
        first_entered = Event()
        release_first = Event()
        second_attempted = Event()
        second_entered = Event()
        paths: list[Path] = []

        def first_worker() -> None:
            with temporary_earthdata_netrc("first", "secret") as path:
                paths.append(path)
                first_entered.set()
                self.assertTrue(release_first.wait(timeout=2))
                self.assertEqual(Path(os.environ["NETRC"]), path)

        def second_worker() -> None:
            second_attempted.set()
            with temporary_earthdata_netrc("second", "secret") as path:
                paths.append(path)
                self.assertEqual(Path(os.environ["NETRC"]), path)
                second_entered.set()

        with patch.dict(os.environ, {"NETRC": "original-netrc"}, clear=False):
            first = Thread(target=first_worker)
            second = Thread(target=second_worker)
            first.start()
            self.assertTrue(first_entered.wait(timeout=2))
            second.start()
            self.assertTrue(second_attempted.wait(timeout=2))
            self.assertFalse(second_entered.wait(timeout=0.1))
            release_first.set()
            first.join(timeout=2)
            second.join(timeout=2)

            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())
            self.assertTrue(second_entered.is_set())
            self.assertEqual(os.environ["NETRC"], "original-netrc")

        self.assertEqual(len(paths), 2)
        self.assertTrue(all(not path.exists() for path in paths))


if __name__ == "__main__":
    unittest.main()
