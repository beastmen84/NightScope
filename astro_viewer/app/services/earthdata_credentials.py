from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


EARTHDATA_SERVICE_NAME = "NightScope Earthdata"
EARTHDATA_USERNAME_KEY = "earthdata_username"
EARTHDATA_OPENDAP_DDS_URL = (
    "https://ladsweb.modaps.eosdis.nasa.gov/opendap/RemoteResources/laads/allData/5200/"
    "VNP46A3/2025/152/VNP46A3.A2025152.h19v04.002.2026064134300.h5.dds"
)


class CredentialBackend(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...

    def set_password(self, service_name: str, username: str, password: str) -> None: ...

    def delete_password(self, service_name: str, username: str) -> None: ...


@dataclass(frozen=True)
class EarthdataCredentialState:
    username: str = ""
    configured: bool = False
    secure_store_available: bool = False
    message: str = "Credenziali Earthdata non configurate."


@dataclass(frozen=True)
class EarthdataConnectionResult:
    ok: bool
    message: str


class EarthdataCredentialStore:
    def __init__(
        self,
        preferences_path: Path,
        *,
        service_name: str = EARTHDATA_SERVICE_NAME,
        backend: CredentialBackend | None = None,
    ):
        self._preferences_path = preferences_path
        self._service_name = service_name
        self._backend = backend if backend is not None else self._load_keyring_backend()

    def state(self) -> EarthdataCredentialState:
        username = self.username()
        secure_store_available = self.secure_store_available
        if not secure_store_available:
            return EarthdataCredentialState(
                username=username,
                configured=False,
                secure_store_available=False,
                message="Archivio credenziali di sistema non disponibile.",
            )
        configured = bool(username and self.password())
        message = "Credenziali Earthdata configurate." if configured else "Credenziali Earthdata non configurate."
        return EarthdataCredentialState(
            username=username,
            configured=configured,
            secure_store_available=True,
            message=message,
        )

    @property
    def secure_store_available(self) -> bool:
        return self._backend is not None

    def username(self) -> str:
        payload = self._read_json(self._preferences_path)
        return str(payload.get(EARTHDATA_USERNAME_KEY) or "").strip()

    def password(self) -> str | None:
        username = self.username()
        if not username or self._backend is None:
            return None
        try:
            return self._backend.get_password(self._service_name, username)
        except Exception:
            logger.warning("Earthdata password could not be read from secure store.", exc_info=True)
            return None

    def save(self, username: str, password: str) -> EarthdataCredentialState:
        clean_username = username.strip()
        clean_password = password
        if not clean_username or not clean_password:
            raise ValueError("Inserisci username e password Earthdata.")
        if self._backend is None:
            raise RuntimeError("Archivio credenziali di sistema non disponibile.")

        old_username = self.username()
        try:
            self._backend.set_password(self._service_name, clean_username, clean_password)
            if old_username and old_username != clean_username:
                self._delete_backend_password(old_username)
        except Exception as exc:
            logger.warning("Earthdata password could not be saved to secure store.", exc_info=True)
            raise RuntimeError("Impossibile salvare le credenziali nel vault di sistema.") from exc

        payload = self._read_json(self._preferences_path)
        payload[EARTHDATA_USERNAME_KEY] = clean_username
        self._write_json(self._preferences_path, payload)
        return EarthdataCredentialState(
            username=clean_username,
            configured=True,
            secure_store_available=True,
            message="Credenziali Earthdata salvate nel vault di sistema.",
        )

    def remove(self) -> EarthdataCredentialState:
        username = self.username()
        if username:
            self._delete_backend_password(username)
        payload = self._read_json(self._preferences_path)
        payload.pop(EARTHDATA_USERNAME_KEY, None)
        self._write_json(self._preferences_path, payload)
        return EarthdataCredentialState(
            username="",
            configured=False,
            secure_store_available=self.secure_store_available,
            message="Credenziali Earthdata rimosse.",
        )

    def _delete_backend_password(self, username: str) -> None:
        if self._backend is None:
            return
        try:
            self._backend.delete_password(self._service_name, username)
        except Exception:
            logger.info("Earthdata password was not present in secure store for user %s.", username)

    @staticmethod
    def _load_keyring_backend() -> CredentialBackend | None:
        try:
            import keyring  # type: ignore[import-not-found]
        except Exception:
            logger.info("Python keyring is not available; Earthdata credentials cannot be stored securely.")
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


class EarthdataConnectionTester:
    def __init__(self, dds_url: str = EARTHDATA_OPENDAP_DDS_URL):
        self._dds_url = dds_url

    def test(self, username: str, password: str) -> EarthdataConnectionResult:
        if not username or not password:
            return EarthdataConnectionResult(False, "Credenziali Earthdata non configurate.")

        with tempfile.TemporaryDirectory(prefix="nightscope-earthdata-") as temp_dir:
            netrc_path = Path(temp_dir) / "_netrc"
            netrc_path.write_text(
                f"machine urs.earthdata.nasa.gov login {username} password {password}\n",
                encoding="ascii",
            )
            previous_netrc = os.environ.get("NETRC")
            os.environ["NETRC"] = str(netrc_path)
            try:
                response = self._session().get(self._dds_url, timeout=(20, 60), allow_redirects=True)
            except requests.RequestException as exc:
                logger.warning("Earthdata connection test failed.", exc_info=True)
                return EarthdataConnectionResult(False, f"Connessione Earthdata non riuscita: {exc.__class__.__name__}.")
            finally:
                if previous_netrc is None:
                    os.environ.pop("NETRC", None)
                else:
                    os.environ["NETRC"] = previous_netrc

        if response.status_code != 200:
            return EarthdataConnectionResult(False, f"Earthdata ha risposto con HTTP {response.status_code}.")
        if "Dataset {" in response.text and "AllAngle_Composite_Snow_Free" in response.text:
            return EarthdataConnectionResult(True, "Connessione Earthdata LAADS verificata.")
        if "approve_app" in response.text or "Pre authorization required" in response.text:
            return EarthdataConnectionResult(False, "Autorizza l'app LAADS OPeNDAP nel profilo Earthdata.")
        if "Earthdata Login" in response.text:
            return EarthdataConnectionResult(False, "Login Earthdata non riuscito. Verifica username e password.")
        return EarthdataConnectionResult(False, "Risposta Earthdata non riconosciuta.")

    @staticmethod
    def _session() -> requests.Session:
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
        session.headers.update({"User-Agent": "NightScope Earthdata credential test", "Accept": "*/*"})
        session.trust_env = True
        return session
