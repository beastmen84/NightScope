"""Download and validate one annual IMO calendar; never use another year's dates.

The PDF is fetched directly for the local installation, not redistributed as
seed data. Only the ten existing major showers in the Working List are read;
outburst prose and solar-longitude predictions are not interpreted as exact UT.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import time
from io import BytesIO
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from html.parser import HTMLParser
from threading import Lock
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse

import requests


logger = logging.getLogger(__name__)
IMO_URL = "https://www.imo.net/"
MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_HTML_BYTES = 128 * 1024
RETRY_HOURS = 24
SHOWER_IDS = {
    "QUA": "quadrantids", "LYR": "lyrids", "ETA": "eta-aquariids",
    "SDA": "southern-delta-aquariids", "PER": "perseids", "DRA": "draconids",
    "ORI": "orionids", "LEO": "leonids", "GEM": "geminids", "URS": "ursids",
}
_MONTHS = {name: i for i, name in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1
)}
_MONTH = "(" + "|".join(_MONTHS) + ")"
_DATE = _MONTH + r"\s+(\d{1,2})"
_ROW = re.compile(
    r"\(\d{3}\s+(" + "|".join(SHOWER_IDS) + r")\)\s+"
    + _DATE + r"\s*[-–]\s*" + _DATE + r"\s+" + _DATE
    + r"\s+[\d.\s°◦]+?\s+(\d+)\s*[°◦]\s+([+−-]\d+)\s*[°◦]"
    + r"\s+\d+\s+\d+\.\d+\s+(\S+)"
)
_FILE = re.compile(r"calendar-(\d{4})\.pdf")


@dataclass(frozen=True)
class MeteorShower:
    code: str
    peak: date
    active_start: date
    active_end: date
    radiant_ra_deg: int
    radiant_dec_deg: int
    zhr: str


@dataclass(frozen=True)
class ImoCalendar:
    year: int
    showers: tuple[MeteorShower, ...]
    downloaded_at: datetime
    path: Path


@dataclass(frozen=True)
class ImoResult:
    requested_year: int
    calendar: ImoCalendar | None = None
    error: str = ""
    retry_at: datetime | None = None


def parse_calendar_text(pages: tuple[str, ...], year: int) -> tuple[MeteorShower, ...]:
    """Reject incomplete/changed tables rather than silently guessing columns."""
    if not pages or not re.search(rf"\b{year}\s+Meteor\s+Shower\s+Calendar\b", pages[0]):
        raise ValueError("IMO calendar title/year mismatch")
    tables = [page for page in pages if re.search(
        r"Table\s+5\.\s+Working\s+List\s+of\s+Visual\s+Meteor\s+Showers", page
    )]
    if len(tables) != 1:
        raise ValueError("IMO Working List missing or ambiguous")
    table = " ".join(tables[0].split())
    if not re.search(rf"accurate only for {year}\b", table):
        raise ValueError("IMO table year mismatch")
    records = {}
    for match in _ROW.finditer(table):
        code, sm, sd, em, ed, pm, pd, ra, dec, zhr = match.groups()
        peak = date(year, _MONTHS[pm], int(pd))
        start = date(year, _MONTHS[sm], int(sd))
        end = date(year, _MONTHS[em], int(ed))
        if start > end:
            if peak <= end:
                start = start.replace(year=year - 1)
            else:
                end = end.replace(year=year + 1)
        ra_value, dec_value = int(ra), int(dec.replace("−", "-"))
        if code in records or not start <= peak <= end or (end - start).days > 100:
            raise ValueError("Invalid IMO activity interval or duplicate shower")
        if not 0 <= ra_value < 360 or not -90 <= dec_value <= 90:
            raise ValueError("Invalid IMO radiant")
        # Preserve qualifiers such as 80+. Never silently truncate an unfamiliar
        # range, qualifier or missing column to its leading numeric component.
        if not re.fullmatch(r"\d{1,4}\+?|Var", zhr):
            raise ValueError("Unsupported IMO ZHR format")
        records[code] = MeteorShower(code, peak, start, end, ra_value, dec_value, zhr)
    if set(records) != set(SHOWER_IDS):
        raise ValueError("Incomplete IMO major-shower table")
    return tuple(records[code] for code in SHOWER_IDS)


def parse_calendar_pdf(payload: bytes, year: int) -> tuple[MeteorShower, ...]:
    """Read PDF text without rendering pages or executing document actions."""
    if not payload.startswith(b"%PDF-") or b"%%EOF" not in payload[-2048:] or len(payload) > MAX_PDF_BYTES:
        raise ValueError("Invalid IMO PDF envelope")
    # A small pure-Python reader avoids adding Qt PDF/PDFium native libraries.
    # Lazy import: PDF support is not loaded during the startup splash.
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        document = PdfReader(BytesIO(payload))
        if document.is_encrypted or not 2 <= len(document.pages) <= 60:
            raise ValueError("Unreadable or oversized IMO PDF")
        first = document.pages[0].extract_text()
        reference = re.search(r"Table\s+5,\s+page\s+(\d+)", first)
        if reference and 1 < int(reference[1]) <= len(document.pages):
            # Both verified editions point to the table from the introduction.
            # Read two pages, not every chart and prose page on every startup.
            pages = (first, document.pages[int(reference[1]) - 1].extract_text())
        else:
            pages = (first, *(page.extract_text() for page in document.pages[1:]))
        return parse_calendar_text(pages, year)
    except (PyPdfError, KeyError, TypeError, IndexError) as exc:
        raise ValueError("Unreadable IMO PDF") from exc


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href" and value)


def _official_url(url: str) -> bool:
    parsed = urlparse(url)
    return (parsed.scheme == "https" and parsed.netloc in {"www.imo.net", "imo.net"}
            and not parsed.query and not parsed.fragment)


class ImoCalendarStore:
    """Blocking I/O boundary, called only by the dedicated provider worker."""

    def __init__(self, directory: Path, *, http_get: Callable = requests.get,
                 parser: Callable = parse_calendar_pdf):
        self.directory = directory
        self._http_get = http_get
        self._parser = parser
        self._lock = Lock()

    def ensure_year(self, year: int, *, now: datetime, retry: bool = False) -> ImoResult:
        with self._lock:
            return self._ensure_year(year, now=now, retry=retry)

    def _ensure_year(self, year: int, *, now: datetime, retry: bool) -> ImoResult:
        if not 2000 <= year <= 2199:
            return ImoResult(year, error="unavailable")
        now = now.astimezone(UTC)
        current = self._load(year)
        if current:
            self._remove_older(year)
            return ImoResult(year, current)
        previous = self._previous(year)
        deferred = self._retry_deferred(year, now)
        if not retry and deferred:
            return ImoResult(year, previous, "unavailable", deferred)
        try:
            payload = self._download(year)
            showers = self._parser(payload, year)
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"calendar-{year}.pdf"
            self._atomic_write(path, payload)
            calendar = ImoCalendar(year, showers, datetime.fromtimestamp(path.stat().st_mtime, UTC), path)
        except (OSError, ValueError, requests.RequestException):
            logger.warning("IMO calendar %s unavailable; keeping the previous local file.", year, exc_info=True)
            self._record_retry(year, now)
            return ImoResult(year, previous, "unavailable", now + timedelta(hours=RETRY_HOURS))
        self._remove_older(year)
        return ImoResult(year, calendar)

    def _load(self, year: int) -> ImoCalendar | None:
        path = self.directory / f"calendar-{year}.pdf"
        try:
            if path.is_symlink() or path.stat().st_size > MAX_PDF_BYTES:
                return None
            showers = self._parser(path.read_bytes(), year)
            return ImoCalendar(year, showers, datetime.fromtimestamp(path.stat().st_mtime, UTC), path)
        except (OSError, ValueError):
            return None

    def _previous(self, year: int) -> ImoCalendar | None:
        try:
            years = sorted((int(match[1]) for path in self.directory.iterdir()
                            if (match := _FILE.fullmatch(path.name)) and int(match[1]) < year), reverse=True)
        except OSError:
            return None
        for candidate in years[:3]:
            if calendar := self._load(candidate):
                return calendar
        return None

    def _remove_older(self, year: int) -> None:
        # Only this provider's exact cache filenames. Never recurse or use a
        # filename supplied by a server; keep newer files if the PC clock regresses.
        try:
            for path in self.directory.iterdir():
                match = _FILE.fullmatch(path.name)
                if match and int(match[1]) < year and path.is_file() and not path.is_symlink():
                    path.unlink()
        except OSError:
            logger.warning("Old IMO calendar cleanup deferred.", exc_info=True)

    def _read_response(self, url: str, limit: int) -> bytes:
        if not _official_url(url):
            raise ValueError("Non-official IMO download URL")
        started = time.monotonic()
        with self._http_get(url, timeout=(5, 10), stream=True, allow_redirects=False,
                            headers={"User-Agent": "NightScope/IMO-calendar", "Accept": "application/pdf,text/html"}) as response:
            # Do not follow redirects to login pages, third parties or HTTP.
            if 300 <= response.status_code < 400:
                raise ValueError("Unexpected IMO redirect")
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_content(64 * 1024):
                size += len(chunk)
                if size > limit or time.monotonic() - started > 30:
                    raise ValueError("IMO response limit exceeded")
                chunks.append(chunk)
            return b"".join(chunks)

    def _download(self, year: int) -> bytes:
        try:
            payload = self._read_response(f"{IMO_URL}files/meteor-shower/cal{year}.pdf", MAX_PDF_BYTES)
            if payload.startswith(b"%PDF-"):
                return payload
        except (ValueError, requests.RequestException):
            pass
        # The restored IMO site currently links ShCal27s.pdf from its home page.
        # Discover that official link instead of guessing a new endpoint yearly.
        links = _Links()
        links.feed(self._read_response(IMO_URL, MAX_HTML_BYTES).decode("utf-8", errors="replace"))
        name_pattern = re.compile(rf"(?:cal{year}|shcal{year % 100:02d}[a-z]*(?:-\d+)?)\.pdf", re.I)
        for href in links.links:
            url = urljoin(IMO_URL, href)
            if _official_url(url) and name_pattern.fullmatch(Path(urlparse(url).path).name):
                return self._read_response(url, MAX_PDF_BYTES)
        raise ValueError(f"No official calendar for {year}")

    def import_file(self, source: Path, year: int) -> ImoResult:
        """Optional recovery during IMO outages; never alter the original PDF."""
        with self._lock:
            return self._import_file(source, year)

    def _import_file(self, source: Path, year: int) -> ImoResult:
        previous = self._load(year) or self._previous(year)
        try:
            if source.stat().st_size > MAX_PDF_BYTES:
                raise ValueError("IMO import too large")
            payload = source.read_bytes()
            showers = self._parser(payload, year)
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.directory / f"calendar-{year}.pdf"
            if source.resolve() != path.resolve():
                self._atomic_write(path, payload)
            calendar = ImoCalendar(year, showers, datetime.fromtimestamp(path.stat().st_mtime, UTC), path)
        except (OSError, ValueError):
            logger.warning("IMO local import rejected; retaining existing calendar.", exc_info=True)
            return ImoResult(year, previous, "invalid_import")
        self._remove_older(year)
        return ImoResult(year, calendar)

    def _retry_deferred(self, year: int, now: datetime) -> datetime | None:
        try:
            path = self.directory / "retry.json"
            if path.stat().st_size > 1024:
                return None
            state = json.loads(path.read_text(encoding="utf-8"))
            until = datetime.fromisoformat(state["retry_at"])
            if state["year"] == year and until.tzinfo is not None and now < until <= now + timedelta(hours=RETRY_HOURS):
                return until
            return None
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _record_retry(self, year: int, now: datetime) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            payload = json.dumps({"year": year, "retry_at": (now + timedelta(hours=RETRY_HOURS)).isoformat()}).encode()
            self._atomic_write(self.directory / "retry.json", payload)
        except OSError:
            logger.debug("IMO retry state could not be saved.", exc_info=True)

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".imo-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
