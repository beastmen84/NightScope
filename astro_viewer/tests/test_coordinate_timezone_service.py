"""Protect offline coordinate-to-IANA-timezone resolution."""

from __future__ import annotations

import unittest

from astro_viewer.app.services.coordinate_timezone_service import (
    CoordinateTimezoneService,
    is_iana_timezone,
)


class CoordinateTimezoneServiceTests(unittest.TestCase):
    def test_packaged_timezone_data_resolves_land_and_ocean_coordinates(self) -> None:
        service = CoordinateTimezoneService()

        self.assertEqual(service.timezone_at(8.9515, 38.7811), "Africa/Addis_Ababa")
        self.assertEqual(service.timezone_at(41.9028, 12.4964), "Europe/Rome")
        self.assertEqual(service.timezone_at(0.0, -160.0), "Etc/GMT+11")

    def test_finder_is_initialized_lazily_and_reused(self) -> None:
        finder = _FakeFinder("Europe/Rome")
        factory_calls = 0

        def factory() -> _FakeFinder:
            nonlocal factory_calls
            factory_calls += 1
            return finder

        service = CoordinateTimezoneService(finder_factory=factory)

        self.assertEqual(factory_calls, 0)
        self.assertEqual(service.timezone_at(41.9, 12.5), "Europe/Rome")
        self.assertEqual(service.timezone_at(42.0, 12.6), "Europe/Rome")
        self.assertEqual(factory_calls, 1)
        self.assertEqual(finder.calls, [(41.9, 12.5), (42.0, 12.6)])

    def test_invalid_coordinates_do_not_initialize_finder(self) -> None:
        def factory() -> _FakeFinder:
            raise AssertionError("Invalid coordinates must not initialize timezone data.")

        service = CoordinateTimezoneService(finder_factory=factory)

        self.assertIsNone(service.timezone_at(91.0, 12.5))
        self.assertIsNone(service.timezone_at(41.9, float("nan")))

    def test_invalid_timezone_name_is_rejected(self) -> None:
        service = CoordinateTimezoneService(
            finder_factory=lambda: _FakeFinder("not/a-timezone")
        )

        self.assertIsNone(service.timezone_at(41.9, 12.5))
        self.assertTrue(is_iana_timezone("Africa/Addis_Ababa"))
        self.assertFalse(is_iana_timezone("E. Africa Standard Time"))

    def test_lookup_failure_returns_none_for_caller_fallback(self) -> None:
        service = CoordinateTimezoneService(finder_factory=_ExplodingFinder)

        with self.assertLogs(
            "astro_viewer.app.services.coordinate_timezone_service",
            level="WARNING",
        ):
            result = service.timezone_at(41.9, 12.5)

        self.assertIsNone(result)


class _FakeFinder:
    def __init__(self, timezone_name: str):
        self.timezone_name = timezone_name
        self.calls: list[tuple[float, float]] = []

    def timezone_at(self, *, lat: float, lng: float) -> str:
        self.calls.append((lat, lng))
        return self.timezone_name


class _ExplodingFinder:
    def timezone_at(self, *, lat: float, lng: float) -> str:
        raise RuntimeError("timezone data unavailable")


if __name__ == "__main__":
    unittest.main()
