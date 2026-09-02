"""Protect robust right-ascension and declination parsing."""

from __future__ import annotations

import unittest

from astro_viewer.app.astronomy.coordinates import parse_dec_degrees, parse_ra_hours


class CoordinateParsingTests(unittest.TestCase):
    def test_parse_ra_hours(self) -> None:
        self.assertAlmostEqual(parse_ra_hours("05h 34m 31.9s"), 5.5755, places=3)

    def test_parse_negative_declination(self) -> None:
        self.assertAlmostEqual(parse_dec_degrees("-26° 31′ 32.7″"), -26.5258, places=3)

    def test_parse_positive_declination(self) -> None:
        self.assertAlmostEqual(parse_dec_degrees("+22° 00′ 52.2″"), 22.0145, places=3)


if __name__ == "__main__":
    unittest.main()
