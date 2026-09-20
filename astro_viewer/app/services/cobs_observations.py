"""Bounded, account-free COBS downloads and immutable local observation snapshots.

Data remain CC BY-NC-SA 4.0, separate from the MPL application. Network/disk
work belongs to the provider worker; astronomical workers only read snapshots.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Callable

import requests


logger = logging.getLogger(__name__)
COBS_URL = "https://cobs.si/"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc-sa/4.0/"
ENDPOINT = "https://cobs.si/api/obs_list.api"
LOOKBACK = timedelta(days=14)
CACHE_TTL = timedelta(hours=24)
MAX_PAGES = 8
MAX_PAGE_BYTES = 6 * 1024 * 1024


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def designation_key(value: str) -> str:
    """Match full JPL names to COBS designations, never names or fragments loosely."""
    compact = re.sub(r"\s+", "", str(value).upper())
    periodic = re.match(r"^(\d+P)(?=/|\(|$)", compact)
    if periodic:
        # Numbered fragment designations must not silently match the parent.
        if re.match(r"^\d+P/[A-Z](?:\(|$)", compact):
            return ""
        return periodic[1]
    provisional = re.match(r"^([CP]/\d{4}[A-Z]\d+)(?=\(|$)", compact)
    return provisional[1] if provisional else ""


@dataclass(frozen=True)
class CometObservation:
    designation: str
    observed_at: datetime
    magnitude: float
    observer: str
    kind: str
    method: str
    error: float | None = None


@dataclass(frozen=True)
class CobsSnapshot:
    observations: tuple[CometObservation, ...] = ()
    fetched_at: datetime | None = None
    revision: str = ""

    def for_comet(self, designation: str, now: datetime) -> tuple[CometObservation, ...]:
        key = designation_key(designation)
        now = utc(now)
        return tuple(row for row in self.observations if key and row.designation == key
                     and now - LOOKBACK <= row.observed_at <= now)


@dataclass(frozen=True)
class CobsResult:
    snapshot: CobsSnapshot
    next_check: datetime
    error: str = ""


def parse_observations(rows: list, now: datetime) -> tuple[CometObservation, ...]:
    """Reject limits/flagged or malformed records, deduplicating observer measurements."""
    observations = {}
    for row in rows:
        try:
            if not isinstance(row, dict):
                continue
            if any(row.get(key) not in (None, "", False) for key in (
                "comet_visibility", "conditions", "issue", "issues", "has_issue",
            )):
                continue
            comet = row["comet"]
            if comet.get("component") not in (None, ""):
                continue
            designation = designation_key(comet["name"])
            observed = utc(datetime.fromisoformat(row["obs_date"]))
            if isinstance(row["magnitude"], bool) or isinstance(row.get("magnitude_error"), bool):
                continue
            magnitude = float(row["magnitude"])
            kind = row["type"]
            method = str((row.get("obs_method") or {}).get("key", "")).strip()
            observer = str((row.get("observer") or {}).get("icq_name", "")).strip()
            # Only compact ICQ identifiers/codes cross the text UI boundary.
            # Full upstream attribution metadata remains in the local cache.
            observer = observer if re.fullmatch(r"[A-Za-z0-9]{1,12}", observer) else ""
            method = method if re.fullmatch(r"[A-Za-z0-9]{1,3}", method) else ""
            error = row.get("magnitude_error")
            error = None if error in (None, "") else float(error)
            if (not designation or kind not in {"V", "C"}
                    or not math.isfinite(magnitude) or not -10 <= magnitude <= 35
                    or not utc(now) - LOOKBACK <= observed <= utc(now)
                    or (error is not None and (not math.isfinite(error) or error < 0))):
                continue
            observation = CometObservation(designation, observed, magnitude, observer, kind, method, error)
            key = (designation, observed, observer, kind, method, magnitude)
            observations[key] = observation
        except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
            continue
    return tuple(sorted(observations.values(), key=lambda row: (
        row.designation, row.observed_at, row.observer, row.kind, row.method, row.magnitude,
    )))


class CobsObservationStore:
    """One global daily cache; failed/incomplete refreshes never replace valid data."""

    def __init__(self, path: Path, *, http_get: Callable = requests.get):
        self.path = path
        self._http_get = http_get
        self._lock = Lock()
        self._snapshot = CobsSnapshot()
        self._payload: dict = {}
        self._loaded = False
        self._next_check = datetime.min.replace(tzinfo=UTC)

    @property
    def snapshot(self) -> CobsSnapshot:
        return self._snapshot

    def refresh(self, now: datetime) -> CobsResult:
        now = utc(now)
        with self._lock:
            if not self._loaded:
                self._load(now)
                self._loaded = True
            if now < self._next_check <= now + CACHE_TTL:
                return CobsResult(self._snapshot, self._next_check,
                                  str(self._payload.get("error", "")))
            self._next_check = now + CACHE_TTL
            error = ""
            try:
                pages = self._fetch(now)
                rows = [row for page in pages for row in page["objects"]]
                observations = parse_observations(rows, now)
                if rows and not observations:
                    raise ValueError("COBS returned no usable observations in a nonempty response")
                self._payload = {
                    "schema": 1, "fetched_at": now.isoformat(), "pages": pages,
                    "source": COBS_URL, "license": LICENSE_URL,
                    "attribution": "COBS Comet Observation Database and contributing observers",
                    "changes": "API query filtered by date and quality; observations analysed by NightScope.",
                }
                self._snapshot = self._make_snapshot(self._payload, now)
            except (OSError, requests.RequestException, ValueError, TypeError, KeyError, AttributeError):
                logger.warning("COBS observations unavailable; retaining local data.", exc_info=True)
                error = "unavailable"
            self._payload["next_check"] = self._next_check.isoformat()
            self._payload["error"] = error
            try:
                self._save()
            except OSError:
                logger.warning("COBS cache could not be saved.", exc_info=True)
                error = error or "cache_write"
            return CobsResult(self._snapshot, self._next_check, error)

    def _fetch(self, now: datetime) -> list[dict]:
        pages = []
        deadline = time.monotonic() + 45.0
        expected_pages = expected_total = None
        total = 0
        for number in range(1, MAX_PAGES + 1):
            if time.monotonic() > deadline:
                raise ValueError("COBS download deadline exceeded")
            params = {
                "format": "json", "from_date": (now - LOOKBACK).strftime("%Y-%m-%d %H:%M"),
                "to_date": now.strftime("%Y-%m-%d %H:%M"), "page": number,
                "exclude_faint": "true", "exclude_not_accurate": "true", "exclude_issue": "true",
            }
            with self._http_get(ENDPOINT, params=params, timeout=(5, 15), stream=True,
                                allow_redirects=False) as response:
                if response.status_code != 200:
                    raise ValueError(f"COBS HTTP {response.status_code}")
                content = bytearray()
                for chunk in response.iter_content(64 * 1024):
                    content.extend(chunk)
                    if len(content) > MAX_PAGE_BYTES or time.monotonic() > deadline:
                        raise ValueError("COBS response exceeded size/time budget")
                page = json.loads(content)
            self._validate_page(page, number)
            info = page["info"]
            if expected_pages is None:
                expected_pages, expected_total = info["pages"], info["recordsTotal"]
            if info["pages"] != expected_pages or info["recordsTotal"] != expected_total:
                raise ValueError("COBS pagination changed during download")
            pages.append(page)
            total += len(page["objects"])
            if number >= max(1, expected_pages):
                if total != expected_total:
                    raise ValueError("Incomplete COBS pagination")
                return pages
        raise ValueError("COBS pagination limit exceeded")

    @staticmethod
    def _validate_page(page: dict, number: int) -> None:
        if not isinstance(page, dict) or page.get("signature", {}).get("version") != "1.5":
            raise ValueError("Unsupported COBS API version")
        info = page.get("info", {})
        if (not isinstance(page.get("objects"), list)
                or info.get("page") != number
                or type(info.get("pages")) is not int or not 0 <= info["pages"] <= MAX_PAGES
                or type(info.get("recordsTotal")) is not int
                or not 0 <= info["recordsTotal"] <= MAX_PAGES * 2500
                or len(page["objects"]) > 2500):
            raise ValueError("Invalid COBS response structure")

    @staticmethod
    def _make_snapshot(payload: dict, now: datetime) -> CobsSnapshot:
        fetched = utc(datetime.fromisoformat(payload["fetched_at"]))
        if fetched > now:
            raise ValueError("Future COBS cache")
        pages = payload["pages"]
        if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
            raise ValueError("Invalid cached COBS pages")
        for number, page in enumerate(pages, 1):
            CobsObservationStore._validate_page(page, number)
            if (page["info"]["pages"] != pages[0]["info"]["pages"]
                    or page["info"]["recordsTotal"] != pages[0]["info"]["recordsTotal"]):
                raise ValueError("Inconsistent cached COBS pages")
        rows = [row for page in pages for row in page["objects"]]
        if len(pages) != max(1, pages[0]["info"]["pages"]) or len(rows) != pages[0]["info"]["recordsTotal"]:
            raise ValueError("Incomplete cached COBS response")
        # Validate against fetch date; use-time selection independently rejects old/future data.
        observations = parse_observations(rows, fetched)
        revision = hashlib.sha256(repr(observations).encode("utf-8")).hexdigest()
        return CobsSnapshot(observations, fetched, revision)

    def _load(self, now: datetime) -> None:
        try:
            if self.path.stat().st_size > MAX_PAGES * MAX_PAGE_BYTES:
                raise ValueError("COBS cache too large")
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Invalid COBS cache")
            if payload.get("schema") == 1:
                self._snapshot = self._make_snapshot(payload, now)
                self._payload = payload
            elif payload.get("error") == "unavailable" and not payload.get("pages"):
                self._payload = payload
            else:
                raise ValueError("Unsupported COBS cache")
            self._next_check = utc(datetime.fromisoformat(payload["next_check"]))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            logger.debug("No valid COBS cache available.")

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=".cobs-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(self._payload, stream, ensure_ascii=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
