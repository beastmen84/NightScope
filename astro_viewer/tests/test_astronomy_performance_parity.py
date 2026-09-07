"""Compare optimized astronomy against original arithmetic and adversarial boundaries."""

from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from skyfield.api import Star

from astro_viewer.app.astronomy.catalog import mock_planets
from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine


@pytest.fixture
def engine():
    instance = SkyfieldAstronomyEngine(Path(__file__).resolve().parents[1] / "data", None)
    yield instance
    instance.close()


SCENARIOS = (
    (41.9, 12.5, "Europe/Rome", "2026-09-07T22:00"),
    (41.9, 12.5, "Europe/Rome", "2026-03-29T03:30"),
    (41.9, 12.5, "Europe/Rome", "2026-10-25T02:30"),
    (-33.9, 18.4, "Africa/Johannesburg", "2026-01-15T22:00"),
    (69.6, 18.9, "Europe/Oslo", "2026-06-21T12:00"),
    (69.6, 18.9, "Europe/Oslo", "2026-12-21T22:00"),
    (-89.0, 0.0, "UTC", "2026-06-21T22:00"),
    (0.0, 179.0, "Pacific/Fiji", "2026-09-07T06:00"),
)


def fixed_objects(engine):
    template = mock_planets()[0]
    objects = []
    for index, (ra, dec) in enumerate(zip(np.linspace(0, 23.9, 17), np.linspace(-89, 89, 17))):
        object_id = f"parity-{index}"
        engine._catalogue_coordinate_cache[object_id] = (float(ra), float(dec))
        objects.append(replace(template, id=object_id, notes="unchanged", score=73))
    return objects


@pytest.mark.parametrize("latitude,longitude,zone,instant", SCENARIOS)
def test_live_batch_preserves_all_payload_fields_and_numeric_positions(engine, latitude, longitude, zone, instant):
    location = ObserverLocation("Audit", "", latitude, longitude, zone)
    engine._now = lambda _location: datetime.fromisoformat(instant).replace(tzinfo=ZoneInfo(zone))
    objects = fixed_objects(engine) + engine.solar_system_objects(location)
    unknown = replace(objects[0], id="unresolvable")
    objects += [unknown, objects[0]]  # Missing coordinates and duplicate IDs retain order/identity.
    before = [asdict(item) for item in objects]
    with patch.object(engine, "_fixed_current_positions", return_value={}):
        expected = engine.refresh_current_positions(objects, location)
    actual = engine.refresh_current_positions(objects, location)
    assert [asdict(item) for item in objects] == before
    assert actual[-2] is unknown
    for result, original in zip(actual, expected, strict=True):
        result_fields, original_fields = asdict(result), asdict(original)
        for field in ("current_altitude_degrees", "current_azimuth_degrees"):
            value, reference = result_fields.pop(field), original_fields.pop(field)
            if reference is None:
                assert value is None
            else:
                assert value == pytest.approx(reference, abs=1e-8, rel=0)
        assert result_fields == original_fields


def test_live_batch_failure_recovers_each_target_without_losing_valid_objects(engine):
    location = ObserverLocation("Roma", "", 41.9, 12.5, "Europe/Rome")
    engine._now = lambda _location: datetime(2026, 9, 7, 22, tzinfo=ZoneInfo(location.timezone))
    objects = fixed_objects(engine)
    invalid = replace(objects[0], id="invalid-coordinates")
    engine._catalogue_coordinate_cache[invalid.id] = ("not-a-number", 3.0)
    objects.insert(2, invalid)
    with patch.object(engine, "_fixed_current_positions", return_value={}):
        expected = engine.refresh_current_positions(objects, location)
    assert engine.refresh_current_positions(objects, location) == expected
    assert expected[2] is invalid
    empty = []
    assert engine.refresh_current_positions(empty, location) is empty


@pytest.mark.parametrize("altitude,azimuth", [(15.0, 10.0), (0.0, 10.0), (3.05, 10.0), (5.0, 22.5),
                                               (5.0, 10.05), (5.0, 0.0), (5.0, 360.0), (float("nan"), 4.0)])
def test_live_rounding_and_visibility_boundaries_retain_scalar_arithmetic(engine, altitude, azimuth):
    target = replace(mock_planets()[0], id="fixed-star")
    assert engine._position_near_display_boundary(target, (altitude, azimuth))
    assert not engine._position_near_display_boundary(target, (14.1234, 56.1234))


def original_month_batch(engine, observer, targets, samples, threshold):
    """Original full-array arithmetic, kept independent of the pending-mask helper."""
    if not samples:
        # The public monthly method never calls its batch without dark samples.
        return {row[0]: False for row in targets}
    stars = Star(ra_hours=np.asarray([row[1] for row in targets]), dec_degrees=np.asarray([row[2] for row in targets]))
    times = engine._timescale.from_datetimes([sample.astimezone(UTC) for sample in samples])
    reaches = np.zeros(len(targets), dtype=bool)
    for index in range(len(samples)):
        altitude = observer.at(times[index]).observe(stars).apparent().altaz()[0].degrees
        reaches |= np.atleast_1d(np.asarray(altitude, dtype=float)) >= threshold
        if bool(np.all(reaches)):
            break
    return {row[0]: bool(reaches[index]) for index, row in enumerate(targets)}


@pytest.mark.parametrize("latitude,longitude,zone,instant", SCENARIOS)
def test_month_pending_mask_preserves_original_sampled_visibility(engine, latitude, longitude, zone, instant):
    location = ObserverLocation("Audit", "", latitude, longitude, zone)
    now = datetime.fromisoformat(instant).replace(tzinfo=ZoneInfo(zone))
    samples = engine._month_dark_samples(location, now.year, now.month, ZoneInfo(zone), step_minutes=30)
    targets = [(str(index), float(ra), float(dec)) for index, (ra, dec) in
               enumerate(zip(np.linspace(0, 23.9, 25), np.linspace(-89, 89, 25)))]
    observer = engine._observer(location)
    expected = original_month_batch(engine, observer, targets, samples, 15.0)
    assert engine._fixed_catalogue_visibility_batch(observer, targets, samples, 15.0) == expected


def test_month_batch_stops_rechecking_successes_and_retains_exact_threshold_fallback(engine):
    samples = [datetime(2026, 9, 7, tzinfo=UTC) + timedelta(hours=index) for index in range(3)]
    evaluated = []

    def observe(stars):
        ra = np.atleast_1d(stars.ra.hours)
        evaluated.append(list(ra))
        # Target 1 succeeds immediately; target 2 grazes the exact threshold.
        altitudes = np.asarray([20.0 if value == 1.0 else 15.0 for value in ra])
        return SimpleNamespace(apparent=lambda: SimpleNamespace(altaz=lambda: (SimpleNamespace(degrees=altitudes),)))

    observer = SimpleNamespace(at=lambda _time: SimpleNamespace(observe=observe))
    targets = [("first", 1.0, 0.0), ("second", 2.0, 0.0)]
    assert engine._fixed_catalogue_visibility_batch(observer, targets, samples, 15.0) == {"first": True, "second": True}
    assert evaluated == [[1.0, 2.0], [1.0, 2.0]]  # Threshold guard uses the original full array.
    evaluated.clear()
    assert engine._fixed_catalogue_visibility_batch(observer, targets, samples, 18.0) == {"first": True, "second": False}
    assert evaluated == [[1.0, 2.0], [2.0], [2.0]]
    assert engine._fixed_catalogue_visibility_batch(observer, [], samples, 18.0) == {}
