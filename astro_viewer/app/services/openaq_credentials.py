from __future__ import annotations

import json
import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


OPENAQ_SERVICE_NAME = "NightScope OpenAQ"
OPENAQ_API_KEY_ACCOUNT = "openaq_api_key"
OPENAQ_CONFIGURED_KEY = "openaq_api_key_configured"
OPENAQ_CONNECTION_TEST_URL = "https://api.openaq.org/v3/parameters?limit=1"


class CredentialBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


@dataclass(frozen=True)
class OpenAQCredentialState:
    configured: bool = False
    secure_store_available: bool = False
    connection_verified: bool = False
    message: str = "API key OpenAQ non configurata."


@dataclass(frozen=True)
class OpenAQConnectionResult:
    ok: bool
    message: str


class OpenAQCredentialStore:
    def __init__(
        self,
        preferences_path: Path,
        *,
        service_name: str = OPENAQ_SERVICE_NAME,
        backend: CredentialBackend | None = None,
    ):
        self._preferences_path = preferences_path
        self._service_name = service_name
        self._backend = backend if backend is not None else self._load_keyring_backend()

    def state(self) -> OpenAQCredentialState:
        secure_store_available = self.secure_store_available
        if not secure_store_available:
            return OpenAQCredentialState(
                configured=False,
                secure_store_available=False,
                message="Archivio credenziali di sistema non disponibile.",
            )
        configured = self.configured()
        if configured:
            message = "API key OpenAQ salvata. Esegui il test connessione."
        else:
            message = "API key OpenAQ non configurata."
        return OpenAQCredentialState(
            configured=configured,
            secure_store_available=True,
            connection_verified=False,
            message=message,
        )

    @property
    def secure_store_available(self) -> bool:
        return self._backend is not None

    def configured(self) -> bool:
        payload = self._read_json(self._preferences_path)
        return bool(payload.get(OPENAQ_CONFIGURED_KEY) and self.api_key())

    def api_key(self) -> str | None:
        if self._backend is None:
            return None
        try:
            return self._backend.get_password(self._service_name, OPENAQ_API_KEY_ACCOUNT)
        except Exception:
            logger.warning("OpenAQ API key could not be read from secure store.", exc_info=True)
            return None

    def save(self, api_key: str) -> OpenAQCredentialState:
        clean_api_key = api_key.strip()
        if not clean_api_key:
            raise ValueError("Inserisci una API key OpenAQ.")
        if self._backend is None:
            raise RuntimeError("Archivio credenziali di sistema non disponibile.")

        try:
            self._backend.set_password(self._service_name, OPENAQ_API_KEY_ACCOUNT, clean_api_key)
        except Exception as exc:
            logger.warning("OpenAQ API key could not be saved to secure store.", exc_info=True)
            raise RuntimeError("Impossibile salvare la API key nel vault di sistema.") from exc

        payload = self._read_json(self._preferences_path)
        payload[OPENAQ_CONFIGURED_KEY] = True
        self._write_json(self._preferences_path, payload)
        return OpenAQCredentialState(
            configured=True,
            secure_store_available=True,
            message="API key OpenAQ salvata. Esegui il test connessione.",
        )

    def remove(self) -> OpenAQCredentialState:
        if self._backend is not None:
            try:
                self._backend.delete_password(self._service_name, OPENAQ_API_KEY_ACCOUNT)
            except Exception:
                logger.info("OpenAQ API key was not present in secure store.")
        payload = self._read_json(self._preferences_path)
        payload.pop(OPENAQ_CONFIGURED_KEY, None)
        self._write_json(self._preferences_path, payload)
        return OpenAQCredentialState(
            configured=False,
            secure_store_available=self.secure_store_available,
            message="API key OpenAQ rimossa.",
        )

    def with_connection_result(self, ok: bool, message: str) -> OpenAQCredentialState:
        return replace(self.state(), connection_verified=ok, message=message)

    @staticmethod
    def _load_keyring_backend() -> CredentialBackend | None:
        try:
            import keyring  # type: ignore[import-not-found]
        except Exception:
            logger.info("Python keyring is not available; OpenAQ credentials cannot be stored securely.")
            return None
        return keyring

    @staticmethod
    def _read_json(path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Preference file could not be read: %s", path, exc_info=True)
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _write_json(path: Path, payload: dict) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            logger.warning("Preference file could not be written: %s", path, exc_info=True)


class OpenAQConnectionTester:
    def __init__(self, test_url: str = OPENAQ_CONNECTION_TEST_URL):
        self._test_url = test_url

    def test(self, api_key: str) -> OpenAQConnectionResult:
        clean_api_key = api_key.strip()
        if not clean_api_key:
            return OpenAQConnectionResult(False, "API key OpenAQ non configurata.")
        try:
            response = self._session(clean_api_key).get(self._test_url, timeout=(10, 20))
        except requests.RequestException as exc:
            logger.warning("OpenAQ connection test failed.", exc_info=True)
            return OpenAQConnectionResult(False, f"Connessione OpenAQ non riuscita: {exc.__class__.__name__}.")

        if response.status_code == 200:
            return self._validate_success_payload(response)
        if response.status_code in (401, 403):
            return OpenAQConnectionResult(False, "API key OpenAQ non valida o non autorizzata.")
        if response.status_code == 429:
            return OpenAQConnectionResult(False, "OpenAQ ha applicato un limite di traffico. Riprova più tardi.")
        return OpenAQConnectionResult(False, f"OpenAQ ha risposto con HTTP {response.status_code}.")

    @staticmethod
    def _validate_success_payload(response: requests.Response) -> OpenAQConnectionResult:
        try:
            payload = response.json()
        except ValueError:
            return OpenAQConnectionResult(False, "Risposta OpenAQ non valida.")
        if isinstance(payload, dict) and "results" in payload:
            return OpenAQConnectionResult(True, "Connessione OpenAQ verificata.")
        return OpenAQConnectionResult(False, "Risposta OpenAQ non riconosciuta.")

    @staticmethod
    def _session(api_key: str) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=2,
            connect=2,
            read=1,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=2, pool_maxsize=2))
        session.headers.update(
            {
                "User-Agent": "NightScope OpenAQ credential test",
                "Accept": "application/json",
                "X-API-Key": api_key,
            }
        )
        session.trust_env = True
        return session
