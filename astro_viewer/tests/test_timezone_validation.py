"""Protect IANA timezone availability and reference DST conversions."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from zoneinfo import ZoneInfo


class TimezoneValidationTests(unittest.TestCase):
    def test_rome_and_milan_use_correct_dst_offsets(self) -> None:
        rome_zone = ZoneInfo("Europe/Rome")
        winter = datetime(2026, 1, 15, 12, 0, tzinfo=UTC).astimezone(rome_zone)
        summer = datetime(2026, 7, 15, 12, 0, tzinfo=UTC).astimezone(rome_zone)

        self.assertEqual(winter.utcoffset().total_seconds(), 3600)
        self.assertEqual(summer.utcoffset().total_seconds(), 7200)
        self.assertEqual(winter.strftime("%H:%M"), "13:00")
        self.assertEqual(summer.strftime("%H:%M"), "14:00")

    def test_reference_locations_have_valid_timezones(self) -> None:
        for timezone in [
            "Africa/Addis_Ababa",
            "Europe/Rome",
            "Africa/Johannesburg",
            "Europe/Oslo",
        ]:
            converted = datetime(2026, 6, 21, 0, 0, tzinfo=UTC).astimezone(ZoneInfo(timezone))
            self.assertIsNotNone(converted.utcoffset())


if __name__ == "__main__":
    unittest.main()
