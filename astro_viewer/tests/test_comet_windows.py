"""Protect comet element caching, visibility windows, identifiers, and fallback policy."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

import requests
from skyfield.api import Loader

from astro_viewer.app.astronomy.comet_windows import CometWindowEventSource
from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.database.orbital_element_cache_repository import (
    OrbitalElementCacheRepository,
)
from astro_viewer.app.models.observing import AstronomicalEvent


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
NOW = datetime(2026, 7, 14, 12, 0, tzinfo=ZoneInfo("Europe/Rome"))
ROME = ObserverLocation("Roma", "Italia", 41.9028, 12.4964, "Europe/Rome")
FIELDS = list(CometWindowEventSource.FIELDS)
COMET_ROW = [
    1004035,
    "     C/2024 T5 (ATLAS)",
    "2024 T5",
    "C",
    "HYP",
    "1.002297644806498",
    "3.840898795556198",
    "52.38678628063384",
    "100.680214064837",
    "352.4469809970417",
    "2461531.687811087382",
    "5.9",
    "7.75",
    None,
    "JPL 37",
]


class _Response:
    def __init__(self, rows: list[list[object]] | None = None):
        self._rows = rows or [COMET_ROW]

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, object]:
        return {
            "signature": {"source": "NASA/JPL Small-Body Database"},
            "fields": FIELDS,
            "data": self._rows,
            "count": len(self._rows),
        }


class _ServerErrorResponse:
    status_code = 502

    def raise_for_status(self) -> None:
        response = requests.Response()
        response.status_code = self.status_code
        raise requests.HTTPError("server error", response=response)


class _CountingTransientSource:
    def __init__(self, name: str, refresh_interval: timedelta):
        self.name = name
        self.refresh_interval = refresh_interval
        self.prepare_calls = 0
        self.build_calls = 0

    def prepare_event_data(
        self,
        _location: ObserverLocation,
        *,
        now: datetime,
    ) -> datetime:
        self.prepare_calls += 1
        return now

    def build_events(
        self,
        _location: ObserverLocation,
        *,
        now: datetime,
        timescale: object,
        ephemeris: object,
        prepared_data: object,
    ) -> list[AstronomicalEvent]:
        del timescale, ephemeris, prepared_data
        self.build_calls += 1
        return [
            AstronomicalEvent(
                id=self.name,
                title=self.name,
                event_type=self.name,
                date_label="",
                best_time="",
                usefulness=0,
                setup="",
                note="",
                event_at=now.isoformat(),
            )
        ]


def _repository(tmp_path: Path) -> OrbitalElementCacheRepository:
    database_path = tmp_path / "comet-cache.db"
    with closing(sqlite3.connect(database_path)) as connection:
        connection.executescript((DATA_DIR / "schema.sql").read_text(encoding="utf-8"))
    return OrbitalElementCacheRepository(database_path)


def _skyfield_context() -> tuple[object, object]:
    loader = Loader(str(DATA_DIR / "skyfield"))
    return loader.timescale(), loader("de421.bsp")


def test_comet_source_builds_one_aggregate_window_and_reuses_cache(
    tmp_path: Path,
) -> None:
    http_get = Mock(return_value=_Response())
    source = CometWindowEventSource(_repository(tmp_path), http_get=http_get)
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

    assert len(events) == 1
    assert len(cached_events) == 1
    http_get.assert_called_once()
    event = events[0]
    assert event.id == "comet-window-1004035"
    assert event.event_type_code == "comet_window"
    assert event.source_code == "short_horizon_comet_windows"
    assert event.target_object_id == ""
    assert event.target_object_ids == ()
    assert event.usefulness == 0
    assert event.data_source == "NASA/JPL SBDB"
    assert event.data_freshness == "Dati cometari aggiornati"
    assert cached_events[0].data_freshness == "Dati cometari recenti in cache"
    assert event.id == cached_events[0].id
    start = datetime.fromisoformat(event.starts_at)
    end = datetime.fromisoformat(event.ends_at)
    peak = datetime.fromisoformat(event.peak_at)
    assert end - start > timedelta(days=30)
    assert start <= peak <= end
    facts = {code: value for code, _label, value in event.event_facts}
    assert int(facts["useful_nights"]) > 1
    assert facts["predicted_magnitude"].startswith("circa ")
    assert facts["estimate_reliability"] == "Bassa"
    assert event.observing_window.startswith("Dal 29/08/2026 al 11/10/2026")


def test_comet_source_uses_recent_stale_cache_but_rejects_old_data(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    initial_source = CometWindowEventSource(
        repository,
        http_get=Mock(return_value=_Response()),
    )
    assert initial_source.prepare_event_data(ROME, now=NOW) is not None

    http_get = Mock(side_effect=requests.Timeout("offline"))
    offline_source = CometWindowEventSource(repository, http_get=http_get)
    stale = offline_source.prepare_event_data(ROME, now=NOW + timedelta(hours=25))
    old = offline_source.prepare_event_data(ROME, now=NOW + timedelta(days=8))

    assert stale is not None
    assert stale.freshness == "stale"
    assert old is None
    assert http_get.call_count == CometWindowEventSource.FETCH_ATTEMPTS * 2


def test_comet_source_retries_server_errors_before_caching(tmp_path: Path) -> None:
    http_get = Mock(side_effect=[_ServerErrorResponse(), _Response()])
    source = CometWindowEventSource(_repository(tmp_path), http_get=http_get)

    with patch("astro_viewer.app.astronomy.comet_windows.time.sleep") as sleep:
        prepared = source.prepare_event_data(ROME, now=NOW)

    assert prepared is not None
    assert prepared.freshness == "updated"
    assert http_get.call_count == 2
    sleep.assert_called_once_with(1)


def test_comet_source_excludes_candidates_below_the_brightness_limit(
    tmp_path: Path,
) -> None:
    faint_row = list(COMET_ROW)
    faint_row[0] = 9999999
    faint_row[1] = "     C/2099 A1 (FAINT)"
    faint_row[11] = "25.0"
    source = CometWindowEventSource(
        _repository(tmp_path),
        http_get=Mock(return_value=_Response([faint_row])),
    )
    timescale, ephemeris = _skyfield_context()
    try:
        events = source.upcoming_events(
            ROME,
            now=NOW,
            timescale=timescale,
            ephemeris=ephemeris,
        )
    finally:
        ephemeris.close()

    assert events == []


def test_transient_engine_respects_each_source_refresh_interval() -> None:
    fast = _CountingTransientSource("fast", timedelta(hours=1))
    slow = _CountingTransientSource("slow", timedelta(hours=6))
    engine = SkyfieldAstronomyEngine(DATA_DIR, None, (fast, slow))
    current_now = [NOW]
    engine._now = lambda _location: current_now[0]
    try:
        first = engine.upcoming_transient_events(
            ROME,
            engine.prepare_transient_events(ROME),
        )
        current_now[0] = NOW + timedelta(hours=1)
        second = engine.upcoming_transient_events(
            ROME,
            engine.prepare_transient_events(ROME),
        )
        current_now[0] = NOW + timedelta(hours=6)
        third = engine.upcoming_transient_events(
            ROME,
            engine.prepare_transient_events(ROME),
        )
        other_location = ObserverLocation(
            "Milano",
            "Italia",
            45.4642,
            9.1900,
            "Europe/Rome",
        )
        current_now[0] = NOW + timedelta(hours=7)
        changed_location = engine.upcoming_transient_events(
            other_location,
            engine.prepare_transient_events(other_location),
        )
    finally:
        engine.close()

    assert {event.id for event in first} == {"fast", "slow"}
    assert {event.id for event in second} == {"fast", "slow"}
    assert {event.id for event in third} == {"fast", "slow"}
    assert {event.id for event in changed_location} == {"fast", "slow"}
    assert (fast.prepare_calls, fast.build_calls) == (4, 4)
    assert (slow.prepare_calls, slow.build_calls) == (3, 3)
