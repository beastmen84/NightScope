"""Protect annual download ownership, corrupt-file safety and conservative IMO parsing."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from io import BytesIO
from threading import Event
from unittest.mock import Mock, patch

import pytest
import requests
from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer, QUrl
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.services.imo_calendar import (
    IMO_URL, MAX_PDF_BYTES, SHOWER_IDS, ImoCalendar, ImoCalendarStore, ImoResult,
    parse_calendar_pdf, parse_calendar_text,
)
from astro_viewer.app.services.imo_meteor_events import annual_meteor_events
from astro_viewer.app.viewmodels.imo_calendar_manager import ImoCalendarManager
from astro_viewer.app.viewmodels.app_controller import AppController


def table_pages(year=2026):
    """Synthetic dates/coordinates, not a redistributed IMO publication."""
    return (f"{year} Meteor Shower Calendar. Table 5, page 2", (
        f"Table 5. Working List of Visual Meteor Showers. Maximum dates accurate only for {year}.\n"
        + "\n".join(f"Test ({i:03d} {code}) Jan 01-Jan 10 Jan 03 283 .°15 230° +49° 41 2.1 80+"
                    for i, code in enumerate(SHOWER_IDS))
    ))


def fake_pdf(year=2026):
    """A minimal generated PDF exercises the real reader without copied fixtures."""
    writer = PdfWriter()
    font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                             NameObject("/Subtype"): NameObject("/Type1"),
                             NameObject("/BaseFont"): NameObject("/Helvetica"),
                             NameObject("/Encoding"): NameObject("/WinAnsiEncoding")})
    for text in table_pages(year):
        page = writer.add_blank_page(600, 800)
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})})
        text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = DecodedStreamObject()
        stream.set_data(("BT /F1 8 Tf 20 760 Td (" + text.replace("\n", ") Tj 0 -14 Td (") + ") Tj ET").encode("latin1"))
        page[NameObject("/Contents")] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def iter_content(self, size):
        for start in range(0, len(self.payload), size):
            yield self.payload[start:start + size]


def test_real_reader_extracts_all_synthetic_rows():
    assert parse_calendar_pdf(fake_pdf(), 2026) == parse_calendar_text(table_pages(), 2026)
    assert all(row.zhr == "80+" for row in parse_calendar_pdf(fake_pdf(), 2026))


@pytest.mark.parametrize("payload", [b"<html>Maintenance</html>", b"%PDF-broken%%EOF", b"%PDF-" + b"x" * MAX_PDF_BYTES], ids=["html", "broken", "oversized"])
def test_invalid_pdf_rejected(payload):
    with pytest.raises(ValueError):
        parse_calendar_pdf(payload, 2026)


@pytest.mark.parametrize("change", [
    lambda p: (p[0].replace("2026", "2027"), p[1]),
    lambda p: (p[0], p[1].replace("for 2026", "for 2027")),
    lambda p: (p[0], p[1].replace("000 QUA", "000 XXX")),
    lambda p: (p[0], p[1] + "\n" + p[1].splitlines()[1]),
    lambda p: (p[0], p[1].replace("Jan 03", "Jan 32")),
    lambda p: (p[0], p[1].replace("Jan 03", "Jan 20")),
    lambda p: (p[0], p[1].replace("230°", "360°")),
    lambda p: (p[0], p[1].replace("+49°", "+99°")),
    lambda p: (p[0], p[1].replace("Table 5.", "Table 7.")),
    lambda p: (p[0], p[1].replace("80+", "80-120")),
    lambda p: (p[0], p[1].replace("80+", "80?")),
])
def test_changed_or_partial_tables_fail_closed(change):
    with pytest.raises(ValueError):
        parse_calendar_text(change(table_pages()), 2026)


def test_year_spanning_activity_and_unicode_minus():
    first, table = table_pages()
    rows = parse_calendar_text((first, table.replace("Jan 01-Jan 10", "Dec 28–Jan 10").replace("+49°", "−49◦")), 2026)
    assert rows[0].active_start == date(2025, 12, 28)
    assert rows[0].radiant_dec_deg == -49


def test_download_only_once_across_restarts(tmp_path):
    get = Mock(return_value=Response(fake_pdf()))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = ImoCalendarStore(tmp_path, http_get=get).ensure_year(2026, now=now)
    saved = first.calendar.path.read_bytes()
    for retry in (False, True):
        result = ImoCalendarStore(tmp_path, http_get=get).ensure_year(2026, now=now, retry=retry)
        assert result.calendar.path.read_bytes() == saved
        assert result.calendar.downloaded_at == first.calendar.downloaded_at
    assert get.call_count == 1


def test_rollover_installs_before_deleting_only_owned_older_files(tmp_path):
    (tmp_path / "calendar-2026.pdf").write_bytes(fake_pdf())
    for name in ("personal.pdf", "calendar-2028.pdf", "calendar-2026.notes", "cal2026.pdf"):
        (tmp_path / name).write_text("preserve")
    get = Mock(return_value=Response(fake_pdf(2027)))
    result = ImoCalendarStore(tmp_path, http_get=get).ensure_year(2027, now=datetime(2027, 1, 1, tzinfo=UTC))
    assert result.calendar.year == 2027 and not result.error
    assert not (tmp_path / "calendar-2026.pdf").exists()
    assert all((tmp_path / name).exists() for name in ("personal.pdf", "calendar-2028.pdf", "calendar-2026.notes", "cal2026.pdf"))


@pytest.mark.parametrize("failure", ["network", "html", "wrong_year", "disk", "truncated"])
def test_failed_rollover_preserves_previous_and_defers_retries(tmp_path, failure):
    previous = fake_pdf()
    (tmp_path / "calendar-2026.pdf").write_bytes(previous)
    if failure == "network":
        get = Mock(side_effect=requests.Timeout())
    else:
        payload = {"html": b"<html>Maintenance</html>", "wrong_year": previous,
                   "disk": fake_pdf(2027), "truncated": b"%PDF-broken%%EOF"}[failure]
        get = Mock(return_value=Response(payload))
    store = ImoCalendarStore(tmp_path, http_get=get)
    original_write = store._atomic_write
    def write(path, data):
        if failure == "disk" and path.suffix == ".pdf":
            raise OSError("full")
        original_write(path, data)
    now = datetime(2027, 1, 1, tzinfo=UTC)
    with patch.object(store, "_atomic_write", side_effect=write):
        result = store.ensure_year(2027, now=now)
    assert result.error and result.calendar.year == 2026
    assert (tmp_path / "calendar-2026.pdf").read_bytes() == previous
    assert not (tmp_path / "calendar-2027.pdf").exists()
    count = get.call_count
    assert store.ensure_year(2027, now=now + timedelta(hours=1)).error
    assert get.call_count == count
    store.ensure_year(2027, now=now + timedelta(hours=25))
    assert get.call_count > count


def test_homepage_discovery_uses_only_official_matching_year(tmp_path):
    page = b'<a href="https://evil.example/ShCal27s.pdf">x</a><a href="ShCal26-0.pdf">old</a><a href="./ShCal27s.pdf">new</a>'
    get = Mock(side_effect=[Response(b"maintenance"), Response(page), Response(fake_pdf(2027))])
    result = ImoCalendarStore(tmp_path, http_get=get).ensure_year(2027, now=datetime(2027, 1, 1, tzinfo=UTC))
    assert result.calendar.year == 2027
    assert get.call_args.args[0] == IMO_URL + "ShCal27s.pdf"
    assert all(call.kwargs["allow_redirects"] is False for call in get.call_args_list)


@pytest.mark.parametrize("url", ["http://www.imo.net/x", "https://evil.test/cal2026.pdf", "https://www.imo.net@evil.test/x", "https://www.imo.net/x?secret=1"])
def test_non_official_urls_rejected_before_request(tmp_path, url):
    get = Mock()
    with pytest.raises(ValueError):
        ImoCalendarStore(tmp_path, http_get=get)._read_response(url, 100)
    get.assert_not_called()


@pytest.mark.parametrize("status,payload", [(302, b""), (404, b""), (200, b"x" * 101)])
def test_response_limits(tmp_path, status, payload):
    with pytest.raises((ValueError, requests.RequestException)):
        ImoCalendarStore(tmp_path, http_get=Mock(return_value=Response(payload, status)))._read_response(IMO_URL, 100)


def test_corrupt_current_cache_is_repaired(tmp_path):
    (tmp_path / "calendar-2026.pdf").write_bytes(b"bad")
    get = Mock(return_value=Response(fake_pdf()))
    assert ImoCalendarStore(tmp_path, http_get=get).ensure_year(2026, now=datetime(2026, 1, 1, tzinfo=UTC)).calendar.year == 2026
    assert get.call_count == 1


def test_manual_import_checks_year_preserves_original_and_disables_download(tmp_path):
    source = tmp_path / "original.pdf"
    source.write_bytes(fake_pdf())
    get = Mock(side_effect=AssertionError("No download expected"))
    store = ImoCalendarStore(tmp_path / "imo", http_get=get)
    assert store.import_file(source, 2027).error == "invalid_import"
    assert not (tmp_path / "imo" / "calendar-2027.pdf").exists()
    result = store.import_file(source, 2026)
    assert result.calendar.path.read_bytes() == source.read_bytes()
    assert store.ensure_year(2026, now=datetime(2026, 1, 1, tzinfo=UTC)).calendar
    get.assert_not_called()
    saved_at = result.calendar.downloaded_at
    same_file = store.import_file(result.calendar.path, 2026)
    assert same_file.calendar.downloaded_at == saved_at


def test_atomic_replace_failure_never_deletes_previous(tmp_path):
    path = tmp_path / "calendar-2026.pdf"
    path.write_bytes(b"old")
    with patch("astro_viewer.app.services.imo_calendar.os.replace", side_effect=OSError("disk")), pytest.raises(OSError):
        ImoCalendarStore._atomic_write(path, b"new")
    assert path.read_bytes() == b"old"
    assert list(tmp_path.iterdir()) == [path]


def test_manager_is_async_coalesces_and_handles_rollover(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    entered, release = Event(), Event()
    now = [datetime(2026, 12, 31, 23, 59, tzinfo=UTC)]
    calendar = ImoCalendar(2026, parse_calendar_text(table_pages(), 2026), now[0], tmp_path / "calendar-2026.pdf")
    def ensure(year, **kwargs):
        entered.set()
        assert release.wait(3)
        return ImoResult(year, replace(calendar, year=year))
    store = Mock(ensure_year=Mock(side_effect=ensure))
    manager = ImoCalendarManager(store, clock=lambda: now[0])
    try:
        assert store.ensure_year.call_count == 0
        manager.start()
        assert entered.wait(2)
        manager.retry()
        manager.start()
        assert store.ensure_year.call_count == 1 and manager.info["busy"]
        # Deliver a heartbeat while the network worker is blocked.
        loop = QEventLoop()
        QTimer.singleShot(1, loop.quit)
        loop.exec()
        assert app is QCoreApplication.instance()
        release.set()
        wait_manager(manager)
        manager.check()
        assert manager.info["current"] and store.ensure_year.call_count == 1
        now[0] += timedelta(minutes=2)
        assert manager.calendar is None
        manager.check()
        wait_manager(manager)
        assert manager.info["year"] == 2027 and store.ensure_year.call_count == 2
    finally:
        release.set()
        manager.stop()


def wait_manager(manager):
    if not manager.info["busy"]:
        return
    loop = QEventLoop()
    manager.calendarChanged.connect(loop.quit)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(4000)
    loop.exec()
    timer.stop()
    manager.calendarChanged.disconnect(loop.quit)
    assert not manager.info["busy"]


def test_manager_import_url_and_shutdown_ignore_late_results(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    source = tmp_path / "calendar.pdf"
    source.write_bytes(fake_pdf())
    manager = ImoCalendarManager(ImoCalendarStore(tmp_path / "cache"), clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))
    manager.importFile(QUrl("https://evil.test/file.pdf"))
    assert not manager.info["busy"]
    manager.importFile(QUrl.fromLocalFile(str(source)))
    wait_manager(manager)
    assert manager.info["current"] and app
    before = manager.info
    manager.stop()
    manager._accept(ImoResult(2027))
    manager.retry()
    assert manager.info == before


def test_annual_dates_replace_only_current_year_meteors_and_no_fake_peak_time(tmp_path):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    baseline = SkyfieldAstronomyEngine._recurring_meteor_showers(now, now + timedelta(days=365))
    other = replace(baseline[0], id="planet-test", event_type="Opposizione")
    calendar = ImoCalendar(2026, parse_calendar_text(table_pages(), 2026), now, tmp_path / "calendar-2026.pdf")
    result = annual_meteor_events([*baseline, other], calendar, now)
    assert next(event for event in result if event.id == "planet-test") is other
    assert len([event for event in result if event.source_code == "imo_calendar"]) == 10
    assert len({event.id for event in result}) == len(result)
    assert all(not event.peak_at and "12:00" not in event.best_time for event in result)
    assert annual_meteor_events(baseline, None, now) is baseline
    assert annual_meteor_events([], calendar, now) == []
    assert all(event.source_code != "imo_calendar" for event in annual_meteor_events(baseline, calendar, now + timedelta(days=10)))


def test_retry_corrupt_or_clock_skew_metadata_is_not_permanent(tmp_path):
    store = ImoCalendarStore(tmp_path)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    for payload in ("bad", "[]", json.dumps({"year": 2026, "retry_at": "2099-01-01T00:00:00+00:00"})):
        (tmp_path / "retry.json").write_text(payload)
        assert not store._retry_deferred(2026, now)


def test_retry_deadline_survives_restart_without_adding_another_day(tmp_path):
    store = ImoCalendarStore(tmp_path, http_get=Mock(side_effect=requests.Timeout()))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    first = store.ensure_year(2026, now=now)
    second = store.ensure_year(2026, now=now + timedelta(hours=23))
    assert first.retry_at == second.retry_at == now + timedelta(hours=24)
    app = QCoreApplication.instance() or QCoreApplication([])
    manager = ImoCalendarManager(store, clock=lambda: now + timedelta(hours=23))
    manager._accept(second)
    assert app and manager._next_check == first.retry_at
    manager.stop()


def test_manager_rollover_during_a_download_rechecks_new_year(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    now = datetime(2027, 1, 1, tzinfo=UTC)
    old = ImoCalendar(2026, parse_calendar_text(table_pages(), 2026), now, tmp_path / "calendar-2026.pdf")
    store = Mock(ensure_year=Mock(return_value=ImoResult(2027, replace(old, year=2027))))
    manager = ImoCalendarManager(store, clock=lambda: now)
    try:
        manager._accept(ImoResult(2026, old))
        wait_manager(manager)
        assert app and manager.info["year"] == 2027
        assert store.ensure_year.call_count == 1
    finally:
        manager.stop()


def test_controller_fallback_does_not_require_new_state():
    from types import SimpleNamespace
    events = [object()]
    assert AppController._annual_calendar_events(SimpleNamespace(_events=events)) is events


def test_calendar_subtitle_does_not_repeat_imo_date(tmp_path):
    from astro_viewer.app.services.calendar_overview import CalendarOverviewService
    now = datetime(2026, 1, 1, tzinfo=UTC)
    baseline = SkyfieldAstronomyEngine._recurring_meteor_showers(now, now + timedelta(days=365))
    calendar = ImoCalendar(2026, parse_calendar_text(table_pages(), 2026), now, tmp_path / "calendar-2026.pdf")
    events = annual_meteor_events(baseline, calendar, now)
    overview = CalendarOverviewService().build(events=[event.to_qml() for event in events], now=now, has_configured_equipment=False)
    assert all(item["detailSubtitle"] == item["dateLabel"] for item in overview["items"])
