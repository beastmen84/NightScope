"""Protect secure OpenAQ key persistence, state, and connection-test behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from astro_viewer.app.services.openaq_credentials import (
    OPENAQ_API_KEY_ACCOUNT,
    OPENAQ_SERVICE_NAME,
    OpenAQConnectionTester,
    OpenAQCredentialStore,
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


class FakeOpenAQResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


class FakeOpenAQSession:
    def __init__(self, response: FakeOpenAQResponse) -> None:
        self._response = response

    def get(self, *_args, **_kwargs) -> FakeOpenAQResponse:
        return self._response


class OpenAQCredentialStoreTests(unittest.TestCase):
    def test_save_reload_and_remove_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preferences_path = Path(temp_dir) / "user_preferences.json"
            backend = FakeCredentialBackend()
            store = OpenAQCredentialStore(preferences_path, backend=backend)

            state = store.save("openaq-secret")

            self.assertTrue(state.configured)
            self.assertTrue(state.secure_store_available)
            self.assertEqual(store.api_key(), "openaq-secret")

            reloaded = OpenAQCredentialStore(preferences_path, backend=backend)

            self.assertTrue(reloaded.state().configured)
            self.assertEqual(reloaded.api_key(), "openaq-secret")

            removed = reloaded.remove()

            self.assertFalse(removed.configured)
            self.assertNotIn((OPENAQ_SERVICE_NAME, OPENAQ_API_KEY_ACCOUNT), backend.passwords)

    def test_connection_result_is_persisted_for_same_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preferences_path = Path(temp_dir) / "user_preferences.json"
            backend = FakeCredentialBackend()
            store = OpenAQCredentialStore(preferences_path, backend=backend)
            store.save("openaq-secret")

            verified = store.with_connection_result(True, "Connessione OpenAQ verificata.")

            self.assertTrue(verified.connection_verified)
            reloaded = OpenAQCredentialStore(preferences_path, backend=backend)
            self.assertTrue(reloaded.state().connection_verified)

    def test_saving_new_api_key_clears_verified_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            preferences_path = Path(temp_dir) / "user_preferences.json"
            backend = FakeCredentialBackend()
            store = OpenAQCredentialStore(preferences_path, backend=backend)
            store.save("openaq-secret")
            store.with_connection_result(True, "Connessione OpenAQ verificata.")

            store.save("openaq-new-secret")

            reloaded = OpenAQCredentialStore(preferences_path, backend=backend)
            self.assertFalse(reloaded.state().connection_verified)

    def test_rejects_empty_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = OpenAQCredentialStore(Path(temp_dir) / "user_preferences.json", backend=FakeCredentialBackend())

            with self.assertRaises(ValueError):
                store.save("")


class OpenAQConnectionTesterTests(unittest.TestCase):
    def test_success_uses_metadata_endpoint(self) -> None:
        response = FakeOpenAQResponse(200, {"results": [{"id": 1, "name": "pm25"}]})
        tester = OpenAQConnectionTester()

        with patch.object(OpenAQConnectionTester, "_session", return_value=FakeOpenAQSession(response)):
            result = tester.test("openaq-secret")

        self.assertTrue(result.ok)
        self.assertEqual(result.message, "Connessione OpenAQ verificata.")

    def test_invalid_key_reports_meaningful_error(self) -> None:
        tester = OpenAQConnectionTester()

        with patch.object(OpenAQConnectionTester, "_session", return_value=FakeOpenAQSession(FakeOpenAQResponse(401))):
            result = tester.test("invalid-key")

        self.assertFalse(result.ok)
        self.assertIn("API key OpenAQ non valida", result.message)

    def test_session_sends_api_key_header(self) -> None:
        session = OpenAQConnectionTester._session("openaq-secret")

        self.assertEqual(session.headers["X-API-Key"], "openaq-secret")
        self.assertEqual(session.headers["Accept"], "application/json")


class OpenAQIsolationTests(unittest.TestCase):
    def test_openaq_is_not_integrated_into_weather_planner_or_recommendations(self) -> None:
        root = Path(__file__).resolve().parents[1] / "app"
        checked_paths = [
            root / "services" / "weather_service.py",
            root / "services" / "night_planner_service.py",
            root / "services" / "recommendation_presenter.py",
            root / "services" / "observing_score_service.py",
        ]
        for path in checked_paths:
            self.assertNotIn("OpenAQ", path.read_text(encoding="utf-8"))
            self.assertNotIn("openaq", path.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
