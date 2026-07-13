from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import requests
from skyfield.api import Loader

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.astronomy.iss_passes import IssPassEventSource
from astro_viewer.app.database.orbital_element_cache_repository import (
    OrbitalElementCacheRecord,
    OrbitalElementCacheRepository,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
NOW = datetime(2026, 7, 13, 12, 0, tzinfo=ZoneInfo("Europe/Rome"))
ROME = ObserverLocation("Roma", "Italia", 41.9028, 12.4964, "Europe/Rome")
OMM_FIELDS = {
    "OBJECT_NAME": "ISS (ZARYA)",
    "OBJECT_ID": "1998-067A",
    "EPOCH": "2026-07-13T07:33:22.422240",
    "MEAN_MOTION": 15.48997295,
    "ECCENTRICITY": 0.0006687,
    "INCLINATION": 51.6305,
    "RA_OF_ASC_NODE": 170.7871,
    "ARG_OF_PERICENTER": 290.3592,
    "MEAN_ANOMALY": 69.6678,
    "EPHEMERIS_TYPE": 0,
    "CLASSIFICATION_TYPE": "U",
    "NORAD_CAT_ID": 25544,
    "ELEMENT_SET_NO": 999,
    "REV_AT_EPOCH": 57580,
    "BSTAR": 0.000081266,
    "MEAN_MOTION_DOT": 0.00004029,
    "MEAN_MOTION_DDOT": 0,
}


class _Response:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> list[dict[str, object]]:
        return [OMM_FIELDS]


def _repository(tmp_path: Path) -> OrbitalElementCacheRepository:
    database_path = tmp_path / "iss-cache.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript((DATA_DIR / "schema.sql").read_text(encoding="utf-8"))
    return OrbitalElementCacheRepository(database_path)


def _skyfield_context() -> tuple[object, object]:
    loader = Loader(str(DATA_DIR / "skyfield"))
    return loader.timescale(), loader("de421.bsp")


def test_orbital_element_cache_round_trip(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    record = OrbitalElementCacheRecord(
        provider="celestrak",
        object_id="25544",
        element_format="omm_json",
        fetched_at="2026-07-13T10:00:00+00:00",
        source_epoch="2026-07-13T07:33:22+00:00",
        expires_at="2026-07-13T16:00:00+00:00",
        payload=json.dumps(OMM_FIELDS),
    )

    repository.set(record)

    assert repository.get("celestrak", "25544") == record


def test_iss_source_builds_visible_pass_intervals_and_reuses_fresh_cache(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    http_get = Mock(return_value=_Response())
    source = IssPassEventSource(repository, http_get=http_get)
    timescale, ephemeris = _skyfield_context()
    try:
        events = source.upcoming_events(
            ROME,
            now=NOW,
            timescale=timescale,
            ephemeris=ephemeris,
        )
        cached_events = source.upcoming_events(
            ROME,
            now=NOW + timedelta(hours=1),
            timescale=timescale,
            ephemeris=ephemeris,
        )
    finally:
        ephemeris.close()

    assert events
    assert cached_events
    http_get.assert_called_once()
    first = events[0]
    assert first.event_type_code == "satellite_pass"
    assert first.source_code == "short_horizon_satellite_passes"
    assert first.target_object_id == ""
    assert datetime.fromisoformat(first.starts_at) < datetime.fromisoformat(first.ends_at)
    assert datetime.fromisoformat(first.starts_at) <= datetime.fromisoformat(first.peak_at)
    assert datetime.fromisoformat(first.peak_at) <= datetime.fromisoformat(first.ends_at)
    assert {fact[0] for fact in first.event_facts} == {
        "culmination",
        "maximum_altitude",
        "start_direction",
        "end_direction",
        "duration",
        "illumination",
    }
    assert first.data_source == "CelesTrak GP / OMM"
    assert first.data_freshness == "Dati orbitali aggiornati ora"
    assert cached_events[0].data_freshness == "Dati orbitali recenti in cache"


def test_iss_source_uses_recent_stale_cache_but_rejects_old_elements(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    initial_source = IssPassEventSource(repository, http_get=Mock(return_value=_Response()))
    timescale, ephemeris = _skyfield_context()
    try:
        assert initial_source.upcoming_events(
            ROME,
            now=NOW,
            timescale=timescale,
            ephemeris=ephemeris,
        )
        offline_source = IssPassEventSource(
            repository,
            http_get=Mock(side_effect=requests.Timeout("offline")),
        )
        stale_events = offline_source.upcoming_events(
            ROME,
            now=NOW + timedelta(hours=7),
            timescale=timescale,
            ephemeris=ephemeris,
        )
        old_events = offline_source.upcoming_events(
            ROME,
            now=NOW + timedelta(days=4),
            timescale=timescale,
            ephemeris=ephemeris,
        )
    finally:
        ephemeris.close()

    assert stale_events
    assert all(event.data_freshness == "Dati orbitali di riserva" for event in stale_events)
    assert old_events == []
