from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from astro_viewer.app.services.location_service import (
    LocationService,
    LocationUnavailableError,
    WINDOWS_LOCATION_UNAVAILABLE_MESSAGE,
)


class LocationServiceWindowsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = LocationService()

    def test_valid_windows_location_payload(self) -> None:
        location = self.service._location_from_windows_payload(
            {
                "latitude": -1.2921,
                "longitude": 36.8219,
                "timezone": "E. Africa Standard Time",
            }
        )

        self.assertEqual(location.city, "Posizione Windows")
        self.assertEqual(location.latitude, -1.2921)
        self.assertEqual(location.longitude, 36.8219)
        self.assertEqual(location.timezone, "Africa/Nairobi")

    def test_windows_location_latitude_none(self) -> None:
        with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE):
            self.service._location_from_windows_payload(
                {"latitude": None, "longitude": 36.8219, "timezone": "E. Africa Standard Time"}
            )

    def test_windows_location_longitude_none(self) -> None:
        with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE):
            self.service._location_from_windows_payload(
                {"latitude": -1.2921, "longitude": None, "timezone": "E. Africa Standard Time"}
            )

    def test_windows_location_both_coordinates_none(self) -> None:
        with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE):
            self.service._location_from_windows_payload(
                {"latitude": None, "longitude": None, "timezone": "E. Africa Standard Time"}
            )

    def test_windows_location_permission_denied_or_unavailable_provider(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["powershell"],
            returncode=1,
            stdout="",
            stderr="Access denied",
        )
        with patch("astro_viewer.app.services.location_service.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(LocationUnavailableError, WINDOWS_LOCATION_UNAVAILABLE_MESSAGE):
                self.service.from_windows_location()


if __name__ == "__main__":
    unittest.main()

