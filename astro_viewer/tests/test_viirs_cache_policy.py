from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.sky_quality_repository import SkyQualityRepository
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.services.light_pollution_service import (
    LightPollutionService,
    ViirsCacheState,
)


NOW = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
LOCATION = ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa")


class ViirsCachePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        root = Path(self._temp_dir.name)
        self._database_path = root / "nightscope.db"
        schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
        initialize_database(self._database_path, schema_path)
        self._repository = SkyQualityRepository(self._database_path)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def test_fresh_viirs_cache_is_reused_without_remote_lookup(self) -> None:
        cached = _viirs_quality("2026-05", 24.79, 14, 6)
        self._store(cached, NOW - timedelta(days=6))
        provider = _FakeViirsProvider(_viirs_quality("2026-06", 30.0, 16, 6))
        service = self._service(provider)

        result = service.remote_sky_quality(LOCATION)

        self.assertEqual(service.viirs_cache_state(LOCATION), ViirsCacheState.FRESH)
        self.assertEqual(result.source, cached.source)
        self.assertEqual(provider.calls, 0)

    def test_fresh_viirs_cache_reuses_nearby_windows_location_jitter(self) -> None:
        cached_location = ObserverLocation("Addis Ababa", "Ethiopia", 9.0304, 38.7404, "Africa/Addis_Ababa")
        jittered_location = ObserverLocation("Addis Ababa", "Ethiopia", 9.0306, 38.7404, "Africa/Addis_Ababa")
        cached = _viirs_quality("2026-05", 24.79, 14, 6)
        self._store(cached, NOW - timedelta(days=1), location=cached_location)
        provider = _FakeViirsProvider(_viirs_quality("2026-06", 30.0, 16, 6))
        service = self._service(provider)

        immediate = service.sky_quality(jittered_location)
        result = service.remote_sky_quality(jittered_location)

        self.assertEqual(service.viirs_cache_state(jittered_location), ViirsCacheState.FRESH)
        self.assertEqual(immediate.source, cached.source)
        self.assertEqual(result.source, cached.source)
        self.assertEqual(provider.calls, 0)

    def test_viirs_cache_does_not_reuse_location_outside_radius(self) -> None:
        cached_location = ObserverLocation("Addis Ababa", "Ethiopia", 9.0304, 38.7404, "Africa/Addis_Ababa")
        distant_location = ObserverLocation("Addis Ababa", "Ethiopia", 9.0404, 38.7404, "Africa/Addis_Ababa")
        cached = _viirs_quality("2026-05", 24.79, 14, 6)
        refreshed = _viirs_quality("2026-06", 30.0, 16, 6)
        self._store(cached, NOW - timedelta(days=1), location=cached_location)
        provider = _FakeViirsProvider(refreshed)
        service = self._service(provider)

        result = service.remote_sky_quality(distant_location)

        self.assertEqual(result.source, refreshed.source)
        self.assertEqual(provider.calls, 1)

    def test_stale_viirs_cache_is_served_then_revalidated(self) -> None:
        cached = _viirs_quality("2026-05", 24.79, 14, 6)
        refreshed = _viirs_quality("2026-06", 30.0, 16, 6)
        self._store(cached, NOW - timedelta(days=7, seconds=1))
        provider = _FakeViirsProvider(refreshed)
        service = self._service(provider)

        immediate = service.sky_quality(LOCATION)
        result = service.remote_sky_quality(LOCATION)

        self.assertEqual(immediate.source, cached.source)
        self.assertEqual(result.source, refreshed.source)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(service.viirs_cache_state(LOCATION), ViirsCacheState.FRESH)
        row = self._repository.get(LightPollutionService._location_key(LOCATION))
        self.assertEqual(row["updated_at"], NOW.isoformat())

    def test_failed_revalidation_preserves_stale_viirs_cache(self) -> None:
        cached = _viirs_quality("2026-05", 24.79, 14, 6)
        cached_at = NOW - timedelta(days=8)
        self._store(cached, cached_at)
        provider = _FakeViirsProvider(None)
        service = self._service(provider)

        result = service.remote_sky_quality(LOCATION)

        self.assertIsNone(result)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(service.viirs_cache_state(LOCATION), ViirsCacheState.STALE)
        row = self._repository.get(LightPollutionService._location_key(LOCATION))
        self.assertEqual(row["source"], cached.source)
        self.assertEqual(row["updated_at"], cached_at.isoformat())

    def test_missing_or_invalid_viirs_timestamp_requires_revalidation(self) -> None:
        service = self._service(_FakeViirsProvider(None))
        self.assertEqual(service.viirs_cache_state(LOCATION), ViirsCacheState.MISSING)

        cached = _viirs_quality("2026-05", 24.79, 14, 6)
        self._repository.set(
            LightPollutionService._location_key(LOCATION),
            cached.bortle_class,
            cached.limiting_magnitude,
            cached.sky_brightness,
            cached.source,
            cached.confidence,
            "invalid-timestamp",
        )

        self.assertEqual(service.viirs_cache_state(LOCATION), ViirsCacheState.STALE)

    def _service(self, provider: _FakeViirsProvider) -> LightPollutionService:
        service = LightPollutionService(
            self._repository,
            data_dir=Path(self._temp_dir.name) / "missing-data",
            clock=lambda: NOW,
        )
        service._remote_providers = [provider]
        return service

    def _store(
        self,
        quality: SkyQuality,
        updated_at: datetime,
        *,
        location: ObserverLocation = LOCATION,
    ) -> None:
        self._repository.set(
            LightPollutionService._location_key(location),
            quality.bortle_class,
            quality.limiting_magnitude,
            quality.sky_brightness,
            quality.source,
            quality.confidence,
            updated_at.isoformat(),
        )


class _FakeViirsProvider:
    name = "FakeViirsProvider"

    def __init__(self, result: SkyQuality | None) -> None:
        self._result = result
        self.calls = 0

    def lookup(self, _location: ObserverLocation) -> SkyQuality | None:
        self.calls += 1
        return self._result


def _viirs_quality(product_month: str, radiance: float, observations: int, bortle: int) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.1,
        sky_brightness=19.4,
        source=(
            f"Fonte: NASA Black Marble VNP46A3 {product_month} "
            f"(radiance {radiance:.2f} nW/cm^2 sr, obs {observations})"
        ),
        description="Bright Suburban Sky",
        confidence="high",
        viirs_radiance=radiance,
        viirs_observation_count=observations,
    )


if __name__ == "__main__":
    unittest.main()
