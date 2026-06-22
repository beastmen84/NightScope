from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astro_viewer.app.services.earthdata_credentials import EarthdataConnectionTester, EarthdataCredentialStore


class FakeCredentialBackend:
    def __init__(self) -> None:
        self.passwords: dict[tuple[str, str], str] = {}

    def get_password(self, service_name: str, username: str) -> str | None:
        return self.passwords.get((service_name, username))

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self.passwords[(service_name, username)] = password

    def delete_password(self, service_name: str, username: str) -> None:
        self.passwords.pop((service_name, username), None)


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
        self.assertIn("Autorizza l'app LAADS OPeNDAP", result.message)


if __name__ == "__main__":
    unittest.main()
