from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
import os
from pathlib import Path
import tempfile
import unittest
import warnings
from unittest.mock import patch

import h5py
import netCDF4
import numpy as np
from PySide6.QtCore import QObject

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.earthdata_credentials import EarthdataCredentialState
from astro_viewer.app.services.nasa_aod_provider import EarthaccessNasaAodClient
from astro_viewer.app.services.nasa_aod_provider import MODIS_MAIAC_AOD
from astro_viewer.app.services.nasa_aod_provider import MaiacAodExtractor
from astro_viewer.app.services.nasa_aod_provider import NasaAodExtraction
from astro_viewer.app.services.nasa_aod_provider import NasaAodGranule
from astro_viewer.app.services.nasa_aod_provider import NasaAodProvider
from astro_viewer.app.services.nasa_aod_provider import NasaAodResult
from astro_viewer.app.services.nasa_aod_provider import VIIRS_MAIAC_AOD
from astro_viewer.app.viewmodels.app_controller import AppController


_STRUCT_METADATA = """
GROUP=GridStructure
    UpperLeftPointMtrs=(-2.500000,2.500000)
    LowerRightMtrs=(2.500000,-2.500000)
    ProjParams=(6371007.181000,0,0,0,0,0,0,0,0,0,0,0,0)
END_GROUP=GridStructure
"""


def _location(latitude: float = 0.0, longitude: float = 0.0) -> ObserverLocation:
    return ObserverLocation("Test", "World", latitude, longitude, "UTC")


def _clock() -> datetime:
    return datetime(2026, 6, 28, 12, 0, tzinfo=UTC)


def _granule(product, granule_id: str, acquisition_date: date) -> NasaAodGranule:
    return NasaAodGranule(product, granule_id, acquisition_date, native={"id": granule_id})


class FakeCredentials:
    def __init__(self, *, verified: bool = True, username: str = "earth-user", password: str | None = "secret") -> None:
        self._state = EarthdataCredentialState(
            username=username,
            configured=bool(username and password),
            secure_store_available=True,
            connection_verified=verified,
        )
        self._password = password

    def state(self) -> EarthdataCredentialState:
        return self._state

    def password(self) -> str | None:
        return self._password


class FakeNasaClient:
    def __init__(
        self,
        *,
        search_results: dict[str, list[NasaAodGranule]] | None = None,
        download_errors: set[str] | None = None,
        external_download_dir: Path | None = None,
    ) -> None:
        self.search_results = search_results or {}
        self.download_errors = download_errors or set()
        self.external_download_dir = external_download_dir
        self.authenticate_calls = 0
        self.search_calls: list[str] = []
        self.download_calls: list[str] = []
        self.downloaded_paths: list[Path] = []

    def authenticate(self, username: str, password: str) -> None:
        if username != "earth-user" or password != "secret":
            raise RuntimeError("bad credentials")
        self.authenticate_calls += 1

    def search(self, product, _location, _start_date, _end_date, _limit) -> list[NasaAodGranule]:
        self.search_calls.append(product.product_id)
        return list(self.search_results.get(product.product_id, []))

    def download(self, granule: NasaAodGranule, target_dir: Path) -> Path:
        self.download_calls.append(granule.granule_id)
        if granule.granule_id in self.download_errors:
            raise RuntimeError("download failed")
        directory = self.external_download_dir or target_dir
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{granule.granule_id}.aod"
        path.write_text("granule", encoding="utf-8")
        self.downloaded_paths.append(path)
        return path


class FakeExtractor:
    def __init__(self, outputs: dict[str, NasaAodExtraction | None | Exception]) -> None:
        self.outputs = outputs
        self.calls: list[tuple[str, str]] = []

    def extract(self, product, path: Path, _location) -> NasaAodExtraction | None:
        self.calls.append((product.product_id, path.stem))
        output = self.outputs.get(path.stem)
        if isinstance(output, Exception):
            raise output
        return output


class NasaAodProviderTests(unittest.TestCase):
    def test_success_result_exposes_display_ready_qml_fields(self) -> None:
        result = NasaAodResult.ok(
            product=VIIRS_MAIAC_AOD.product_id,
            extraction=NasaAodExtraction(0.658, 0.0185, 1089, "local_neighborhood", 3),
            granule=_granule(VIIRS_MAIAC_AOD, "granule-valid", date.today()),
            retrieved_at=datetime.now(UTC),
        )

        qml = result.to_qml()

        self.assertTrue(qml["visible"])
        self.assertTrue(qml["hasData"])
        self.assertEqual(qml["aod550"], "0.658")
        self.assertEqual(qml["transparency"], "Velata")
        self.assertEqual(qml["freshness"], "Misura di oggi")
        self.assertEqual(qml["freshnessCategory"], "current")
        self.assertFalse(qml["freshnessWarning"])
        self.assertEqual(qml["productLabel"], "VIIRS MAIAC")
        self.assertEqual(qml["methodLabel"], "Area locale 5x5")
        self.assertIn("3 pixel validi", qml["sourceDetail"])
        self.assertFalse(qml["running"])

    def test_no_credentials_qml_hides_atmospheric_transparency_section(self) -> None:
        qml = NasaAodResult.no_credentials().to_qml()

        self.assertFalse(qml["visible"])
        self.assertFalse(qml["hasData"])
        self.assertEqual(qml["message"], "Credenziali Earthdata non configurate o non verificate.")

    def test_no_location_returns_no_location_without_network(self) -> None:
        client = FakeNasaClient()
        provider = NasaAodProvider(FakeCredentials(), client=client, extractor=FakeExtractor({}), clock=_clock)

        result = provider.aod(None)

        self.assertFalse(result.available)
        self.assertEqual(result.status, "no_location")
        self.assertEqual(client.authenticate_calls, 0)

    def test_no_verified_credentials_returns_no_credentials(self) -> None:
        client = FakeNasaClient()
        provider = NasaAodProvider(FakeCredentials(verified=False), client=client, extractor=FakeExtractor({}), clock=_clock)

        result = provider.aod(_location())

        self.assertFalse(result.available)
        self.assertEqual(result.status, "no_credentials")
        self.assertEqual(client.authenticate_calls, 0)

    def test_search_results_are_processed_newest_first(self) -> None:
        old = _granule(VIIRS_MAIAC_AOD, "old", date(2026, 6, 20))
        new = _granule(VIIRS_MAIAC_AOD, "new", date(2026, 6, 27))
        client = FakeNasaClient(search_results={VIIRS_MAIAC_AOD.product_id: [old, new]})
        extractor = FakeExtractor({"new": NasaAodExtraction(0.123, 0.01, 8, "direct_pixel")})
        provider = NasaAodProvider(FakeCredentials(), client=client, extractor=extractor, clock=_clock)

        result = provider.aod(_location())

        self.assertTrue(result.available)
        self.assertEqual(result.granule_id, "new")
        self.assertEqual(client.download_calls, ["new"])
        self.assertEqual(result.aod_550, 0.123)

    def test_viirs_no_valid_result_falls_back_to_modis(self) -> None:
        viirs = _granule(VIIRS_MAIAC_AOD, "viirs-cloud", date(2026, 6, 27))
        modis = _granule(MODIS_MAIAC_AOD, "modis-valid", date(2026, 6, 26))
        client = FakeNasaClient(
            search_results={
                VIIRS_MAIAC_AOD.product_id: [viirs],
                MODIS_MAIAC_AOD.product_id: [modis],
            }
        )
        extractor = FakeExtractor({"viirs-cloud": None, "modis-valid": NasaAodExtraction(0.244, 0.02, 16, "direct_pixel")})
        provider = NasaAodProvider(FakeCredentials(), client=client, extractor=extractor, clock=_clock)

        result = provider.aod(_location())

        self.assertTrue(result.available)
        self.assertEqual(result.product, MODIS_MAIAC_AOD.product_id)
        self.assertEqual(client.search_calls, [VIIRS_MAIAC_AOD.product_id, MODIS_MAIAC_AOD.product_id])
        self.assertEqual(client.download_calls, ["viirs-cloud", "modis-valid"])

    def test_all_candidates_invalid_returns_no_valid_pixel(self) -> None:
        granule = _granule(VIIRS_MAIAC_AOD, "invalid", date(2026, 6, 27))
        client = FakeNasaClient(search_results={VIIRS_MAIAC_AOD.product_id: [granule]})
        provider = NasaAodProvider(FakeCredentials(), client=client, extractor=FakeExtractor({"invalid": None}), clock=_clock)

        result = provider.aod(_location())

        self.assertFalse(result.available)
        self.assertEqual(result.status, "no_valid_pixel")

    def test_cache_hit_returns_without_second_download(self) -> None:
        granule = _granule(VIIRS_MAIAC_AOD, "valid", date(2026, 6, 27))
        client = FakeNasaClient(search_results={VIIRS_MAIAC_AOD.product_id: [granule]})
        extractor = FakeExtractor({"valid": NasaAodExtraction(0.2, None, 1, "direct_pixel")})
        provider = NasaAodProvider(FakeCredentials(), client=client, extractor=extractor, clock=_clock)

        first = provider.aod(_location())
        second = provider.aod(_location())

        self.assertTrue(first.available)
        self.assertTrue(second.available)
        self.assertEqual(second.status, "cache_hit")
        self.assertTrue(second.cache_hit)
        self.assertEqual(client.download_calls, ["valid"])

    def test_processed_cache_survives_provider_restart_without_download(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "nasa_aod_cache.json"
            granule = _granule(VIIRS_MAIAC_AOD, "valid", date(2026, 6, 27))
            client = FakeNasaClient(search_results={VIIRS_MAIAC_AOD.product_id: [granule]})
            extractor = FakeExtractor({"valid": NasaAodExtraction(0.2, None, 1, "direct_pixel")})
            provider = NasaAodProvider(
                FakeCredentials(),
                client=client,
                extractor=extractor,
                clock=_clock,
                cache_path=cache_path,
            )

            first = provider.aod(_location())

            reloaded_client = FakeNasaClient()
            reloaded = NasaAodProvider(
                FakeCredentials(),
                client=reloaded_client,
                extractor=FakeExtractor({}),
                clock=_clock,
                cache_path=cache_path,
            )
            second = reloaded.aod(_location())

            self.assertTrue(first.available)
            self.assertTrue(second.available)
            self.assertEqual(second.status, "cache_hit")
            self.assertTrue(second.cache_hit)
            self.assertEqual(second.aod_550, 0.2)
            self.assertEqual(reloaded_client.authenticate_calls, 0)
            self.assertEqual(reloaded_client.download_calls, [])

    def test_stale_processed_disk_cache_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "nasa_aod_cache.json"
            granule = _granule(VIIRS_MAIAC_AOD, "valid", date(2026, 6, 27))
            client = FakeNasaClient(search_results={VIIRS_MAIAC_AOD.product_id: [granule]})
            extractor = FakeExtractor({"valid": NasaAodExtraction(0.2, None, 1, "direct_pixel")})
            provider = NasaAodProvider(
                FakeCredentials(),
                client=client,
                extractor=extractor,
                clock=_clock,
                cache_path=cache_path,
            )
            provider.aod(_location())

            reloaded_client = FakeNasaClient()

            def stale_clock() -> datetime:
                return _clock() + timedelta(hours=19)

            reloaded = NasaAodProvider(
                FakeCredentials(),
                client=reloaded_client,
                extractor=FakeExtractor({}),
                clock=stale_clock,
                cache_path=cache_path,
            )

            result = reloaded.aod(_location())

            self.assertFalse(result.available)
            self.assertEqual(result.status, "no_granules")
            self.assertEqual(reloaded_client.authenticate_calls, 1)

    def test_clear_cache_removes_processed_disk_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "nasa_aod_cache.json"
            granule = _granule(VIIRS_MAIAC_AOD, "valid", date(2026, 6, 27))
            client = FakeNasaClient(search_results={VIIRS_MAIAC_AOD.product_id: [granule]})
            extractor = FakeExtractor({"valid": NasaAodExtraction(0.2, None, 1, "direct_pixel")})
            provider = NasaAodProvider(
                FakeCredentials(),
                client=client,
                extractor=extractor,
                clock=_clock,
                cache_path=cache_path,
            )
            provider.aod(_location())

            provider.clear_cache()

            self.assertFalse(cache_path.exists())

    def test_downloaded_granule_is_deleted_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            external_dir = Path(temp_dir)
            granule = _granule(VIIRS_MAIAC_AOD, "valid", date(2026, 6, 27))
            client = FakeNasaClient(
                search_results={VIIRS_MAIAC_AOD.product_id: [granule]},
                external_download_dir=external_dir,
            )
            extractor = FakeExtractor({"valid": NasaAodExtraction(0.2, None, 1, "direct_pixel")})
            provider = NasaAodProvider(FakeCredentials(), client=client, extractor=extractor, clock=_clock)

            result = provider.aod(_location())

            self.assertTrue(result.available)
            self.assertEqual(len(client.downloaded_paths), 1)
            self.assertFalse(client.downloaded_paths[0].exists())

    def test_downloaded_granule_is_deleted_after_parse_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            external_dir = Path(temp_dir)
            granule = _granule(VIIRS_MAIAC_AOD, "broken", date(2026, 6, 27))
            client = FakeNasaClient(
                search_results={VIIRS_MAIAC_AOD.product_id: [granule]},
                external_download_dir=external_dir,
            )
            extractor = FakeExtractor({"broken": ValueError("bad file")})
            provider = NasaAodProvider(FakeCredentials(), client=client, extractor=extractor, clock=_clock)

            result = provider.aod(_location())

            self.assertFalse(result.available)
            self.assertEqual(result.status, "parse_error")
            self.assertEqual(len(client.downloaded_paths), 1)
            self.assertFalse(client.downloaded_paths[0].exists())

    def test_download_error_is_reported_separately(self) -> None:
        granule = _granule(VIIRS_MAIAC_AOD, "download-fails", date(2026, 6, 27))
        client = FakeNasaClient(
            search_results={VIIRS_MAIAC_AOD.product_id: [granule]},
            download_errors={"download-fails"},
        )
        provider = NasaAodProvider(FakeCredentials(), client=client, extractor=FakeExtractor({}), clock=_clock)

        result = provider.aod(_location())

        self.assertFalse(result.available)
        self.assertEqual(result.status, "download_error")


class NasaAodControllerRefreshTests(unittest.TestCase):
    def test_atmospheric_transparency_is_hidden_without_verified_earthdata(self) -> None:
        controller = _aod_controller(verified=False)

        qml = controller.atmosphericTransparency

        self.assertFalse(qml["visible"])
        self.assertFalse(qml["running"])

    def test_atmospheric_transparency_requires_location_after_earthdata_verification(self) -> None:
        controller = _aod_controller(location=None, verified=True)

        qml = controller.atmosphericTransparency

        self.assertTrue(qml["visible"])
        self.assertFalse(qml["hasData"])
        self.assertEqual(qml["status"], "no_location")

    def test_refresh_is_skipped_without_location(self) -> None:
        controller = _aod_controller(location=None, verified=True)

        with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="INFO") as logs:
            controller._schedule_nasa_aod_refresh()

        self.assertEqual(controller._nasa_aod_result.status, "no_location")
        self.assertFalse(controller._nasa_aod_refresh_running)
        self.assertIn("no valid observing location", "\n".join(logs.output))

    def test_refresh_is_skipped_without_verified_earthdata(self) -> None:
        provider = _FakeControllerAodProvider()
        controller = _aod_controller(provider=provider, verified=False)

        with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="INFO") as logs:
            controller._schedule_nasa_aod_refresh()

        self.assertEqual(controller._nasa_aod_result.status, "no_credentials")
        self.assertEqual(provider.calls, 0)
        self.assertIn("credentials are not verified", "\n".join(logs.output))

    def test_refresh_starts_background_lookup_when_location_and_credentials_are_ready(self) -> None:
        controller = _aod_controller(verified=True)
        emissions: list[bool] = []
        controller.weatherChanged.connect(lambda: emissions.append(True))

        with patch("astro_viewer.app.viewmodels.app_controller.Thread") as thread_cls:
            with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="INFO") as logs:
                controller._schedule_nasa_aod_refresh()

        thread_cls.assert_called_once()
        thread_cls.return_value.start.assert_called_once()
        self.assertTrue(controller._nasa_aod_refresh_running)
        self.assertTrue(controller.atmosphericTransparency["running"])
        self.assertEqual(len(emissions), 1)
        self.assertIn("NASA AOD refresh started", "\n".join(logs.output))

    def test_finished_refresh_stores_and_logs_result(self) -> None:
        controller = _aod_controller(verified=True)
        emissions: list[bool] = []
        controller.weatherChanged.connect(lambda: emissions.append(True))
        result = NasaAodResult.ok(
            product=VIIRS_MAIAC_AOD.product_id,
            extraction=NasaAodExtraction(0.18, 0.01, 4, "direct_pixel"),
            granule=_granule(VIIRS_MAIAC_AOD, "granule-valid", date(2026, 6, 27)),
            retrieved_at=_clock(),
        )
        controller._nasa_aod_refresh_running = True

        with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="INFO") as logs:
            controller._finish_nasa_aod_refresh("9.030:38.740:test", result)

        self.assertFalse(controller._nasa_aod_refresh_running)
        self.assertIs(controller._nasa_aod_result, result)
        self.assertEqual(len(emissions), 1)
        self.assertEqual(controller.atmosphericTransparency["aod550"], "0.180")
        self.assertIn("NASA AOD refresh ok", "\n".join(logs.output))
        self.assertIn("granule-valid", "\n".join(logs.output))

    def test_finished_refresh_discards_stale_location_result(self) -> None:
        controller = _aod_controller(verified=True)
        previous = NasaAodResult.no_location()
        controller._nasa_aod_result = previous
        controller._nasa_aod_refresh_running = True

        with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="INFO") as logs:
            controller._finish_nasa_aod_refresh("44.495:11.343:bologna", NasaAodResult.failure("no_valid_pixel", "No data"))

        self.assertFalse(controller._nasa_aod_refresh_running)
        self.assertIs(controller._nasa_aod_result, previous)
        self.assertIn("stale location", "\n".join(logs.output))

    def test_finished_refresh_discards_result_after_credentials_are_unverified(self) -> None:
        controller = _aod_controller(verified=False)
        previous = NasaAodResult.no_credentials()
        controller._nasa_aod_result = previous
        controller._nasa_aod_refresh_running = True

        with self.assertLogs("astro_viewer.app.viewmodels.app_controller", level="INFO") as logs:
            controller._finish_nasa_aod_refresh("9.030:38.740:test", NasaAodResult.failure("no_valid_pixel", "No data"))

        self.assertFalse(controller._nasa_aod_refresh_running)
        self.assertIs(controller._nasa_aod_result, previous)
        self.assertIn("credentials are no longer verified", "\n".join(logs.output))


class EarthaccessNasaAodClientTests(unittest.TestCase):
    def test_login_retries_before_success(self) -> None:
        fake_earthaccess = _FlakyEarthaccess(failures=2)
        sleeps: list[float] = []
        client = _FakeEarthaccessClient(
            fake_earthaccess,
            login_attempts=3,
            backoff_seconds=(0.0, 0.5, 1.0),
            sleep=sleeps.append,
        )

        client.authenticate("earth-user", "secret")

        self.assertEqual(fake_earthaccess.login_calls, 3)
        self.assertEqual(sleeps, [0.5, 1.0])

    def test_login_uses_environment_credentials_without_persisting_token(self) -> None:
        fake_earthaccess = _FlakyEarthaccess(failures=0)
        previous_token = os.environ.get("EARTHDATA_TOKEN")
        os.environ["EARTHDATA_TOKEN"] = "old-token"
        try:
            client = _FakeEarthaccessClient(fake_earthaccess, login_attempts=1, backoff_seconds=(0.0,), sleep=lambda _x: None)

            client.authenticate("earth-user", "secret")

            self.assertEqual(fake_earthaccess.seen_username, "earth-user")
            self.assertEqual(fake_earthaccess.seen_password, "secret")
            self.assertEqual(os.environ.get("EARTHDATA_TOKEN"), "old-token")
        finally:
            if previous_token is None:
                os.environ.pop("EARTHDATA_TOKEN", None)
            else:
                os.environ["EARTHDATA_TOKEN"] = previous_token


class MaiacAodExtractorTests(unittest.TestCase):
    def test_viirs_hdf5_direct_pixel(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "viirs.h5"
            _write_hdf5_fixture(path, center_raw=150, center_uncertainty=25)

            result = MaiacAodExtractor().extract(VIIRS_MAIAC_AOD, path, _location())

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.method, "direct_pixel")
        self.assertAlmostEqual(result.aod_550, 0.15)
        self.assertAlmostEqual(result.uncertainty or 0, 0.0025)
        self.assertEqual(result.qa_raw, 4)

    def test_viirs_hdf5_invalid_exact_pixel_uses_5x5_neighborhood(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "viirs.h5"
            _write_hdf5_fixture(path, center_raw=-28672, neighbor_raw=300, center_uncertainty=-28672)

            result = MaiacAodExtractor().extract(VIIRS_MAIAC_AOD, path, _location())

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.method, "local_neighborhood")
        self.assertEqual(result.local_valid_pixel_count, 24)
        self.assertAlmostEqual(result.aod_550, 0.3)

    def test_modis_netcdf4_direct_pixel(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "modis.nc"
            _write_netcdf4_fixture(path, center_raw=220, center_uncertainty=30)

            result = MaiacAodExtractor().extract(MODIS_MAIAC_AOD, path, _location())

        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result.method, "direct_pixel")
        self.assertAlmostEqual(result.aod_550, 0.22)
        self.assertAlmostEqual(result.uncertainty or 0, 0.003)
        self.assertEqual(result.qa_raw, 4)


class _FlakyEarthaccess:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.login_calls = 0
        self.seen_username = ""
        self.seen_password = ""

    def login(self, *, strategy: str, persist: bool) -> None:
        self.login_calls += 1
        self.seen_username = os.environ.get("EARTHDATA_USERNAME", "")
        self.seen_password = os.environ.get("EARTHDATA_PASSWORD", "")
        self.assertion_strategy = strategy
        self.assertion_persist = persist
        if self.login_calls <= self.failures:
            raise TimeoutError("URS timed out")


class _FakeEarthaccessClient(EarthaccessNasaAodClient):
    def __init__(self, fake_earthaccess, **kwargs) -> None:
        super().__init__(**kwargs)
        self._fake_earthaccess = fake_earthaccess

    def _import_earthaccess(self):
        return self._fake_earthaccess


class _FakeControllerAodProvider:
    def __init__(self) -> None:
        self.calls = 0
        self.cache_cleared = False

    def aod(self, _location) -> NasaAodResult:
        self.calls += 1
        return NasaAodResult.failure("no_valid_pixel", "No data")

    def clear_cache(self) -> None:
        self.cache_cleared = True


def _aod_controller(
    *,
    location: ObserverLocation | None = _location(9.03, 38.74),
    verified: bool,
    provider: _FakeControllerAodProvider | None = None,
):
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    controller._location = location
    controller._earthdata_credentials_state = EarthdataCredentialState(
        username="earth-user",
        configured=True,
        secure_store_available=True,
        connection_verified=verified,
    )
    controller._nasa_aod_refresh_running = False
    controller._nasa_aod_result = NasaAodResult.no_location()
    controller._nasa_aod_provider = provider or _FakeControllerAodProvider()
    return controller


def _write_hdf5_fixture(
    path: Path,
    *,
    center_raw: int,
    neighbor_raw: int | None = None,
    center_uncertainty: int,
) -> None:
    fill = -28672
    aod = np.full((1, 5, 5), neighbor_raw if neighbor_raw is not None else fill, dtype=np.int16)
    uncertainty = np.full((1, 5, 5), 20, dtype=np.int16)
    qa = np.full((1, 5, 5), 4, dtype=np.int16)
    aod[0, 2, 2] = center_raw
    uncertainty[0, 2, 2] = center_uncertainty

    with h5py.File(path, "w") as handle:
        data_fields = handle.create_group("HDFEOS/GRIDS/MAIAC/Data Fields")
        aod_dataset = data_fields.create_dataset("Optical_Depth_055", data=aod)
        aod_dataset.attrs["scale_factor"] = np.array([0.001])
        aod_dataset.attrs["_FillValue"] = np.array([fill], dtype=np.int16)
        qa_dataset = data_fields.create_dataset("AOD_QA", data=qa)
        qa_dataset.attrs["_FillValue"] = np.array([fill], dtype=np.int16)
        uncertainty_dataset = data_fields.create_dataset("AOD_Uncertainty", data=uncertainty)
        uncertainty_dataset.attrs["scale_factor"] = np.array([0.0001])
        uncertainty_dataset.attrs["_FillValue"] = np.array([fill], dtype=np.int16)
        info = handle.create_group("HDFEOS INFORMATION")
        info.create_dataset("StructMetadata.0", data=np.bytes_(_STRUCT_METADATA))


def _write_netcdf4_fixture(path: Path, *, center_raw: int, center_uncertainty: int) -> None:
    fill = -28672
    with netCDF4.Dataset(path, "w") as dataset:
        dataset.createDimension("orbit", 1)
        dataset.createDimension("y", 5)
        dataset.createDimension("x", 5)
        dataset.setncattr("StructMetadata.0", _STRUCT_METADATA)

        aod = dataset.createVariable("Optical_Depth_055", "i2", ("orbit", "y", "x"), fill_value=fill)
        aod.set_auto_maskandscale(False)
        aod_values = np.full((1, 5, 5), fill, dtype=np.int16)
        aod_values[0, 2, 2] = center_raw
        _assign_netcdf_values(aod, aod_values)
        aod.scale_factor = 0.001

        qa = dataset.createVariable("AOD_QA", "i2", ("orbit", "y", "x"), fill_value=fill)
        qa.set_auto_maskandscale(False)
        _assign_netcdf_values(qa, np.full((1, 5, 5), 4, dtype=np.int16))

        uncertainty = dataset.createVariable("AOD_Uncertainty", "i2", ("orbit", "y", "x"), fill_value=fill)
        uncertainty.set_auto_maskandscale(False)
        uncertainty_values = np.full((1, 5, 5), fill, dtype=np.int16)
        uncertainty_values[0, 2, 2] = center_uncertainty
        _assign_netcdf_values(uncertainty, uncertainty_values)
        uncertainty.scale_factor = 0.0001


def _assign_netcdf_values(variable, values: np.ndarray) -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Setting the shape on a NumPy array", category=DeprecationWarning)
        variable[:, :, :] = values


if __name__ == "__main__":
    unittest.main()
