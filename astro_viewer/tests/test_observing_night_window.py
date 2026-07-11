from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine


@pytest.fixture(scope="module")
def astronomy_engine() -> SkyfieldAstronomyEngine:
    base_dir = Path(__file__).resolve().parents[1]
    engine = SkyfieldAstronomyEngine(base_dir / "data", Mock())
    yield engine
    engine.close()


def test_addis_ababa_upcoming_night_uses_local_sunset_and_sunrise(
    astronomy_engine: SkyfieldAstronomyEngine,
) -> None:
    location = ObserverLocation(
        "Addis Ababa",
        "Etiopia",
        9.03,
        38.74,
        "Africa/Addis_Ababa",
    )
    zone = ZoneInfo(location.timezone)

    window = astronomy_engine.observing_night_window(
        location,
        datetime(2026, 7, 10, 12, 0, tzinfo=zone),
    )

    assert window.state == "bounded"
    assert window.start is not None
    assert window.end is not None
    assert window.start.date().isoformat() == "2026-07-10"
    assert window.start.strftime("%H:%M") == "18:48"
    assert window.end.date().isoformat() == "2026-07-11"
    assert window.end.strftime("%H:%M") == "06:12"


def test_addis_ababa_current_night_keeps_previous_sunset(
    astronomy_engine: SkyfieldAstronomyEngine,
) -> None:
    location = ObserverLocation(
        "Addis Ababa",
        "Etiopia",
        9.03,
        38.74,
        "Africa/Addis_Ababa",
    )
    zone = ZoneInfo(location.timezone)
    reference = datetime(2026, 7, 11, 3, 0, tzinfo=zone)

    window = astronomy_engine.observing_night_window(location, reference)

    assert window.state == "bounded"
    assert window.start is not None
    assert window.end is not None
    assert window.start.date().isoformat() == "2026-07-10"
    assert window.end.date().isoformat() == "2026-07-11"
    assert window.contains(reference)


@pytest.mark.parametrize(
    ("reference", "expected_state"),
    (
        (datetime(2026, 6, 21, 12, 0, tzinfo=ZoneInfo("Europe/Oslo")), "no_night"),
        (
            datetime(2026, 12, 21, 12, 0, tzinfo=ZoneInfo("Europe/Oslo")),
            "continuous_night",
        ),
    ),
)
def test_polar_day_and_night_are_explicit(
    astronomy_engine: SkyfieldAstronomyEngine,
    reference: datetime,
    expected_state: str,
) -> None:
    location = ObserverLocation(
        "Tromso",
        "Norvegia",
        69.6492,
        18.9553,
        "Europe/Oslo",
    )

    window = astronomy_engine.observing_night_window(location, reference)

    assert window.state == expected_state
    assert window.has_observing_window is (expected_state == "continuous_night")
