"""Fetch, cache, and calculate practical observing windows for bright comets."""

from __future__ import annotations

import json
import logging
import math
import sqlite3
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import pandas as pd
import requests
from skyfield import almanac
from skyfield.api import wgs84
from skyfield.constants import GM_SUN_Pitjeva_2005_km3_s2
from skyfield.data import mpc

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.orbital_element_cache_repository import (
    OrbitalElementCacheRecord,
    OrbitalElementCacheRepository,
)
from astro_viewer.app.models.observing import AstronomicalEvent
from astro_viewer.app.services.localization import format_datetime, format_number, tr


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _CometRecord:
    spk_id: str
    designation: str
    prefix: str
    orbit_class: str
    eccentricity: float
    perihelion_distance_au: float
    inclination_degrees: float
    longitude_of_ascending_node_degrees: float
    argument_of_perihelion_degrees: float
    perihelion_jd: float
    absolute_magnitude: float
    magnitude_slope: float
    condition_code: str
    orbit_id: str


@dataclass(frozen=True)
class _PreparedComets:
    records: tuple[_CometRecord, ...]
    cache_record: OrbitalElementCacheRecord
    freshness: str


@dataclass(frozen=True)
class _NightWindow:
    night_date: date
    start: datetime
    end: datetime
    peak: datetime
    predicted_magnitude: float
    maximum_altitude_deg: float
    solar_elongation_deg: float
    moon_separation_deg: float
    moon_illumination: float

    @property
    def duration(self) -> timedelta:
        return self.end - self.start


class CometWindowEventSource:
    """Builds aggregate, short-horizon observing windows for selected comets."""

    PROVIDER = "jpl_sbdb"
    OBJECT_ID = "observable_comet_candidates"
    ELEMENT_FORMAT = "sbdb_query_v1"
    ENDPOINT = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"
    DATA_SOURCE = "NASA/JPL SBDB"
    CACHE_TTL = timedelta(hours=24)
    MAX_STALE_DATA_AGE = timedelta(days=7)
    refresh_interval = timedelta(hours=6)
    HORIZON = timedelta(days=90)
    QUERY_PERIHELION_MARGIN = timedelta(days=730)
    REQUEST_TIMEOUT_SECONDS = 20
    FETCH_ATTEMPTS = 3
    SAMPLE_MINUTES = 30
    MIN_NIGHTLY_DURATION_MINUTES = 60
    MAX_PREDICTED_MAGNITUDE = 14.5
    COARSE_MAGNITUDE_MARGIN = 1.5
    MIN_ALTITUDE_DEG = 20.0
    MAX_OBSERVER_SUN_ALTITUDE_DEG = -12.0
    MIN_SOLAR_ELONGATION_DEG = 30.0
    MIN_MOON_SEPARATION_DEG = 25.0
    MAX_MOON_ILLUMINATION_FOR_CLOSE_PASS = 0.35
    MAX_EVENTS = 12
    FIELDS = (
        "spkid",
        "full_name",
        "pdes",
        "prefix",
        "class",
        "e",
        "q",
        "i",
        "om",
        "w",
        "tp",
        "M1",
        "K1",
        "condition_code",
        "orbit_id",
    )

    def __init__(
        self,
        cache_repository: OrbitalElementCacheRepository,
        *,
        http_get: Callable[..., requests.Response] = requests.get,
    ):
        self._cache_repository = cache_repository
        self._http_get = http_get

    def upcoming_events(
        self,
        location: ObserverLocation,
        *,
        now: datetime,
        timescale: object,
        ephemeris: object,
    ) -> list[AstronomicalEvent]:
        now_utc = _as_utc(now)
        prepared = self.prepare_event_data(location, now=now_utc)
        if prepared is None:
            return []
        return self.build_events(
            location,
            now=now_utc,
            timescale=timescale,
            ephemeris=ephemeris,
            prepared_data=prepared,
        )

    def prepare_event_data(
        self,
        _location: ObserverLocation,
        *,
        now: datetime,
    ) -> _PreparedComets | None:
        return self._comet_records(_as_utc(now))

    def build_events(
        self,
        location: ObserverLocation,
        *,
        now: datetime,
        timescale: object,
        ephemeris: object,
        prepared_data: object,
    ) -> list[AstronomicalEvent]:
        if not isinstance(prepared_data, _PreparedComets):
            return []
        if not prepared_data.records:
            return []

        now_utc = _as_utc(now)
        horizon_end = now_utc + self.HORIZON
        try:
            context = self._sampling_context(
                location,
                now=now_utc,
                end=horizon_end,
                timescale=timescale,
                ephemeris=ephemeris,
            )
            coarse_times = timescale.from_datetimes(
                _sample_datetimes(now_utc, horizon_end, timedelta(days=1))
            )
        except Exception:
            logger.warning("Comet sampling context could not be prepared.", exc_info=True)
            return []

        candidates: list[tuple[float, AstronomicalEvent]] = []
        for record in prepared_data.records:
            try:
                comet = _comet_vector(record, timescale, ephemeris["sun"])
                if not self._passes_coarse_magnitude_filter(
                    comet,
                    record,
                    coarse_times=coarse_times,
                    earth=ephemeris["earth"],
                    sun=ephemeris["sun"],
                ):
                    continue
                windows = self._night_windows(comet, record, context=context)
                best_group = _best_consecutive_group(windows)
                if not best_group:
                    continue
                event = self._event(record, best_group, prepared_data)
                candidates.append(
                    (min(window.predicted_magnitude for window in best_group), event)
                )
            except Exception:
                logger.warning(
                    "Comet window prediction failed for %s.",
                    record.designation,
                    exc_info=True,
                )

        brightest = sorted(candidates, key=lambda item: (item[0], item[1].starts_at))[
            : self.MAX_EVENTS
        ]
        return sorted(
            (event for _, event in brightest),
            key=lambda event: (event.starts_at, event.title),
        )

    def _comet_records(self, now: datetime) -> _PreparedComets | None:
        cached = self._cached_record()
        if cached is not None and self._cache_is_fresh(cached, now):
            records = self._record_payload(cached)
            if records:
                return _PreparedComets(records, cached, "fresh")

        try:
            payload = self._fetch_payload(now)
            records = _parse_records(payload)
            if not records:
                raise ValueError("NASA/JPL returned no usable comet records.")
            record = OrbitalElementCacheRecord(
                provider=self.PROVIDER,
                object_id=self.OBJECT_ID,
                element_format=self.ELEMENT_FORMAT,
                fetched_at=now.isoformat(),
                source_epoch=now.isoformat(),
                expires_at=(now + self.CACHE_TTL).isoformat(),
                payload=json.dumps(payload, ensure_ascii=True, separators=(",", ":")),
            )
            try:
                self._cache_repository.set(record)
            except (sqlite3.Error, OSError):
                logger.warning("Comet orbital data could not be cached.", exc_info=True)
            return _PreparedComets(records, record, "updated")
        except (
            OSError,
            requests.RequestException,
            sqlite3.Error,
            TypeError,
            ValueError,
            KeyError,
        ):
            logger.warning("Comet orbital data could not be refreshed.", exc_info=True)

        if cached is None or not self._stale_cache_is_usable(cached, now):
            return None
        records = self._record_payload(cached)
        if not records:
            return None
        return _PreparedComets(records, cached, "stale")

    def _cached_record(self) -> OrbitalElementCacheRecord | None:
        try:
            return self._cache_repository.get(self.PROVIDER, self.OBJECT_ID)
        except (sqlite3.Error, OSError):
            logger.warning("Comet orbital cache could not be read.", exc_info=True)
            return None

    def _fetch_payload(self, now: datetime) -> Mapping[str, object]:
        start_jd = _julian_day(now - self.QUERY_PERIHELION_MARGIN)
        end_jd = _julian_day(now + self.QUERY_PERIHELION_MARGIN)
        constraints = {
            "AND": [
                "M1|DF",
                "K1|DF",
                f"tp|RG|{start_jd:.6f}|{end_jd:.6f}",
            ]
        }
        params = {
            "fields": ",".join(self.FIELDS),
            "sb-kind": "c",
            "sb-xfrag": "1",
            "full-prec": "true",
            "sb-cdata": json.dumps(constraints, separators=(",", ":")),
        }
        last_error: requests.RequestException | None = None
        for attempt in range(self.FETCH_ATTEMPTS):
            try:
                response = self._http_get(
                    self.ENDPOINT,
                    params=params,
                    timeout=self.REQUEST_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, Mapping):
                    raise ValueError("Unexpected NASA/JPL SBDB response.")
                _validate_payload(payload)
                return payload
            except requests.RequestException as exc:
                last_error = exc
                status_code = getattr(exc.response, "status_code", None)
                if attempt + 1 < self.FETCH_ATTEMPTS and status_code is not None:
                    if status_code >= 500:
                        time.sleep(min(2**attempt, 2))
        if last_error is not None:
            raise last_error
        raise ValueError("NASA/JPL SBDB response could not be read.")

    def _record_payload(
        self,
        record: OrbitalElementCacheRecord,
    ) -> tuple[_CometRecord, ...]:
        try:
            payload = json.loads(record.payload)
            if not isinstance(payload, Mapping):
                return ()
            return _parse_records(payload)
        except (TypeError, ValueError, KeyError):
            return ()

    def _cache_is_fresh(self, record: OrbitalElementCacheRecord, now: datetime) -> bool:
        try:
            return (
                record.element_format == self.ELEMENT_FORMAT
                and _parse_datetime(record.expires_at) > now
                and _parse_datetime(record.fetched_at) <= now + timedelta(hours=1)
            )
        except ValueError:
            return False

    def _stale_cache_is_usable(
        self,
        record: OrbitalElementCacheRecord,
        now: datetime,
    ) -> bool:
        try:
            fetched_at = _parse_datetime(record.fetched_at)
        except ValueError:
            return False
        return (
            record.element_format == self.ELEMENT_FORMAT
            and timedelta(0) <= now - fetched_at <= self.MAX_STALE_DATA_AGE
        )

    def _sampling_context(
        self,
        location: ObserverLocation,
        *,
        now: datetime,
        end: datetime,
        timescale: object,
        ephemeris: object,
    ) -> dict[str, object]:
        datetimes = _sample_datetimes(
            now,
            end,
            timedelta(minutes=self.SAMPLE_MINUTES),
        )
        times = timescale.from_datetimes(datetimes)
        topos = wgs84.latlon(location.latitude, location.longitude)
        observer = ephemeris["earth"] + topos
        observer_at = observer.at(times)
        sun_apparent = observer_at.observe(ephemeris["sun"]).apparent()
        moon_apparent = observer_at.observe(ephemeris["moon"]).apparent()
        sun_altitudes, _, _ = sun_apparent.altaz()
        moon_illumination = almanac.fraction_illuminated(ephemeris, "moon", times)
        zone = _zone(location.timezone)
        return {
            "datetimes": datetimes,
            "local_datetimes": [value.astimezone(zone) for value in datetimes],
            "times": times,
            "observer_at": observer_at,
            "sun": ephemeris["sun"],
            "sun_apparent": sun_apparent,
            "moon_apparent": moon_apparent,
            "sun_altitudes": np.asarray(sun_altitudes.degrees, dtype=float),
            "moon_illumination": np.asarray(moon_illumination, dtype=float),
            "end": end,
        }

    def _passes_coarse_magnitude_filter(
        self,
        comet: object,
        record: _CometRecord,
        *,
        coarse_times: object,
        earth: object,
        sun: object,
    ) -> bool:
        solar_distance = np.asarray(
            (comet - sun).at(coarse_times).distance().au,
            dtype=float,
        )
        earth_distance = np.asarray(
            earth.at(coarse_times).observe(comet).distance().au,
            dtype=float,
        )
        magnitudes = _predicted_magnitude(record, solar_distance, earth_distance)
        finite = magnitudes[np.isfinite(magnitudes)]
        return bool(
            finite.size
            and float(np.min(finite))
            <= self.MAX_PREDICTED_MAGNITUDE + self.COARSE_MAGNITUDE_MARGIN
        )

    def _night_windows(
        self,
        comet: object,
        record: _CometRecord,
        *,
        context: Mapping[str, object],
    ) -> list[_NightWindow]:
        times = context["times"]
        observer_at = context["observer_at"]
        comet_apparent = observer_at.observe(comet).apparent()
        altitudes, _, observer_distances = comet_apparent.altaz()
        altitude_values = np.asarray(altitudes.degrees, dtype=float)
        solar_distances = np.asarray(
            (comet - context["sun"]).at(times).distance().au,
            dtype=float,
        )
        predicted_magnitudes = _predicted_magnitude(
            record,
            solar_distances,
            np.asarray(observer_distances.au, dtype=float),
        )
        solar_elongations = np.asarray(
            comet_apparent.separation_from(context["sun_apparent"]).degrees,
            dtype=float,
        )
        moon_separations = np.asarray(
            comet_apparent.separation_from(context["moon_apparent"]).degrees,
            dtype=float,
        )
        moon_illumination = context["moon_illumination"]
        sun_altitudes = context["sun_altitudes"]
        valid = (
            np.isfinite(predicted_magnitudes)
            & (predicted_magnitudes <= self.MAX_PREDICTED_MAGNITUDE)
            & (altitude_values >= self.MIN_ALTITUDE_DEG)
            & (sun_altitudes <= self.MAX_OBSERVER_SUN_ALTITUDE_DEG)
            & (solar_elongations >= self.MIN_SOLAR_ELONGATION_DEG)
            & (
                (moon_separations >= self.MIN_MOON_SEPARATION_DEG)
                | (
                    moon_illumination
                    <= self.MAX_MOON_ILLUMINATION_FOR_CLOSE_PASS
                )
            )
        )
        valid_indices = np.flatnonzero(valid).tolist()
        if not valid_indices:
            return []

        local_datetimes = context["local_datetimes"]
        segments: list[list[int]] = []
        current: list[int] = []
        current_night: date | None = None
        previous_index: int | None = None
        for index in valid_indices:
            local_time = local_datetimes[index]
            night_date = _observing_night_date(local_time)
            if (
                current
                and (index != previous_index + 1 or night_date != current_night)
            ):
                segments.append(current)
                current = []
            current.append(index)
            current_night = night_date
            previous_index = index
        if current:
            segments.append(current)

        by_night: dict[date, _NightWindow] = {}
        step = timedelta(minutes=self.SAMPLE_MINUTES)
        datetimes = context["datetimes"]
        horizon_end = context["end"]
        for segment in segments:
            first_index = segment[0]
            last_index = segment[-1]
            start = datetimes[first_index]
            end = min(datetimes[last_index] + step, horizon_end)
            if end - start < timedelta(minutes=self.MIN_NIGHTLY_DURATION_MINUTES):
                continue
            peak_index = max(segment, key=lambda item: altitude_values[item])
            local_start = local_datetimes[first_index]
            local_end = end.astimezone(local_start.tzinfo)
            local_peak = local_datetimes[peak_index]
            window = _NightWindow(
                night_date=_observing_night_date(local_start),
                start=local_start,
                end=local_end,
                peak=local_peak,
                predicted_magnitude=float(predicted_magnitudes[peak_index]),
                maximum_altitude_deg=float(altitude_values[peak_index]),
                solar_elongation_deg=float(solar_elongations[peak_index]),
                moon_separation_deg=float(moon_separations[peak_index]),
                moon_illumination=float(moon_illumination[peak_index]),
            )
            previous = by_night.get(window.night_date)
            if previous is None or _window_rank(window) > _window_rank(previous):
                by_night[window.night_date] = window
        return [by_night[key] for key in sorted(by_night)]

    def _event(
        self,
        record: _CometRecord,
        windows: Sequence[_NightWindow],
        prepared: _PreparedComets,
    ) -> AstronomicalEvent:
        first = windows[0]
        last = windows[-1]
        peak = max(
            windows,
            key=lambda window: (
                window.maximum_altitude_deg,
                -window.predicted_magnitude,
            ),
        )
        date_label = _date_range_label(first.night_date, last.night_date, first.start)
        peak_label = format_datetime(peak.peak)
        observing_window = _observing_window_label(
            first.night_date,
            last.night_date,
            peak_label,
            first.start,
        )
        lower_magnitude = math.floor(peak.predicted_magnitude - 1.0)
        upper_magnitude = math.ceil(peak.predicted_magnitude + 1.0)
        valid_until = _parse_datetime(prepared.cache_record.fetched_at) + (
            self.MAX_STALE_DATA_AGE
        )
        freshness_label = {
            "updated": tr("Dati cometari aggiornati"),
            "fresh": tr("Dati cometari recenti in cache"),
            "stale": tr("Dati cometari di riserva"),
        }[prepared.freshness]
        return AstronomicalEvent(
            id=f"comet-window-{record.spk_id}",
            title=tr("{name}: finestra osservativa", name=record.designation),
            event_type=tr("Cometa"),
            date_label=date_label,
            best_time=tr("Momento consigliato: {date}", date=peak_label),
            usefulness=0,
            setup=_setup_for_magnitude(peak.predicted_magnitude),
            note=tr(
                "La luminosità cometaria è una previsione indicativa e può differire "
                "anche sensibilmente da quella osservata."
            ),
            event_at=first.start.isoformat(),
            timing_kind="window",
            timing_label=tr("Finestra osservativa"),
            observing_window=observing_window,
            visibility_state="visible",
            visibility_label=tr("Finestra locale favorevole"),
            visibility_detail=tr(
                "La cometa supera le soglie locali di altezza, buio, elongazione "
                "solare e disturbo lunare."
            ),
            event_type_code="comet_window",
            source_code="short_horizon_comet_windows",
            source_label=tr("Finestre cometarie a breve termine"),
            starts_at=first.start.isoformat(),
            ends_at=last.end.isoformat(),
            peak_at=peak.peak.isoformat(),
            event_facts=(
                (
                    "predicted_magnitude",
                    tr("Magnitudine prevista"),
                    tr(
                        "circa {minimum}-{maximum}",
                        minimum=lower_magnitude,
                        maximum=upper_magnitude,
                    ),
                ),
                (
                    "maximum_altitude",
                    tr("Altezza massima"),
                    tr(
                        "{degrees}°",
                        degrees=format_number(
                            peak.maximum_altitude_deg,
                            decimals=0,
                        ),
                    ),
                ),
                (
                    "solar_elongation",
                    tr("Elongazione solare"),
                    tr(
                        "{degrees}°",
                        degrees=format_number(
                            peak.solar_elongation_deg,
                            decimals=0,
                        ),
                    ),
                ),
                (
                    "moon_separation",
                    tr("Distanza dalla Luna"),
                    tr(
                        "{degrees}°",
                        degrees=format_number(
                            peak.moon_separation_deg,
                            decimals=0,
                        ),
                    ),
                ),
                (
                    "moon_illumination",
                    tr("Illuminazione lunare"),
                    tr(
                        "{percent}%",
                        percent=format_number(
                            peak.moon_illumination * 100.0,
                            decimals=0,
                        ),
                    ),
                ),
                (
                    "useful_nights",
                    tr("Notti utili stimate"),
                    format_number(len(windows), decimals=0),
                ),
                (
                    "estimate_reliability",
                    tr("Affidabilità della stima"),
                    tr("Bassa"),
                ),
            ),
            data_source=self.DATA_SOURCE,
            data_updated_at=prepared.cache_record.fetched_at,
            data_valid_until=valid_until.isoformat(),
            data_freshness=freshness_label,
        )


def _validate_payload(payload: Mapping[str, object]) -> None:
    fields = payload.get("fields")
    data = payload.get("data")
    if not isinstance(fields, list) or not isinstance(data, list):
        raise ValueError("Incomplete NASA/JPL SBDB response.")
    if not set(CometWindowEventSource.FIELDS).issubset(fields):
        raise ValueError("NASA/JPL SBDB response is missing required fields.")


def _parse_records(payload: Mapping[str, object]) -> tuple[_CometRecord, ...]:
    _validate_payload(payload)
    fields = payload["fields"]
    data = payload["data"]
    indices = {str(field): index for index, field in enumerate(fields)}
    records: dict[str, _CometRecord] = {}
    for row in data:
        if not isinstance(row, list) or len(row) < len(fields):
            continue
        try:
            prefix = str(row[indices["prefix"]] or "").strip().upper()
            if prefix not in {"C", "P"}:
                continue
            spk_id = str(row[indices["spkid"]]).strip()
            designation = str(row[indices["full_name"]] or "").strip()
            if not spk_id or not designation:
                continue
            record = _CometRecord(
                spk_id=spk_id,
                designation=designation,
                prefix=prefix,
                orbit_class=str(row[indices["class"]] or "").strip(),
                eccentricity=_finite_float(row[indices["e"]]),
                perihelion_distance_au=_finite_float(row[indices["q"]]),
                inclination_degrees=_finite_float(row[indices["i"]]),
                longitude_of_ascending_node_degrees=_finite_float(
                    row[indices["om"]]
                ),
                argument_of_perihelion_degrees=_finite_float(row[indices["w"]]),
                perihelion_jd=_finite_float(row[indices["tp"]]),
                absolute_magnitude=_finite_float(row[indices["M1"]]),
                magnitude_slope=_finite_float(row[indices["K1"]]),
                condition_code=str(row[indices["condition_code"]] or "").strip(),
                orbit_id=str(row[indices["orbit_id"]] or "").strip(),
            )
            if record.eccentricity <= 0 or record.perihelion_distance_au <= 0:
                continue
            records[spk_id] = record
        except (TypeError, ValueError, OverflowError):
            continue
    return tuple(records[key] for key in sorted(records))


def _finite_float(value: object) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite comet element.")
    return result


def _comet_vector(record: _CometRecord, timescale: object, sun: object) -> object:
    perihelion = timescale.tdb_jd(record.perihelion_jd)
    year, month, day, hour, minute, second = perihelion.tt_calendar()
    fractional_day = float(day) + (
        float(hour) + (float(minute) + float(second) / 60.0) / 60.0
    ) / 24.0
    row = pd.Series(
        {
            "designation": record.designation,
            "eccentricity": record.eccentricity,
            "perihelion_distance_au": record.perihelion_distance_au,
            "inclination_degrees": record.inclination_degrees,
            "longitude_of_ascending_node_degrees": (
                record.longitude_of_ascending_node_degrees
            ),
            "argument_of_perihelion_degrees": (
                record.argument_of_perihelion_degrees
            ),
            "perihelion_year": int(year),
            "perihelion_month": int(month),
            "perihelion_day": fractional_day,
        }
    )
    orbit = mpc.comet_orbit(row, timescale, GM_SUN_Pitjeva_2005_km3_s2)
    return sun + orbit


def _predicted_magnitude(
    record: _CometRecord,
    solar_distance_au: np.ndarray,
    observer_distance_au: np.ndarray,
) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return (
            record.absolute_magnitude
            + 5.0 * np.log10(observer_distance_au)
            + record.magnitude_slope * np.log10(solar_distance_au)
        )


def _sample_datetimes(
    start: datetime,
    end: datetime,
    step: timedelta,
) -> list[datetime]:
    values: list[datetime] = []
    current = start
    while current < end:
        values.append(current)
        current += step
    values.append(end)
    return values


def _best_consecutive_group(
    windows: Sequence[_NightWindow],
) -> list[_NightWindow]:
    groups: list[list[_NightWindow]] = []
    current: list[_NightWindow] = []
    for window in sorted(windows, key=lambda item: item.night_date):
        if current and window.night_date != current[-1].night_date + timedelta(days=1):
            groups.append(current)
            current = []
        current.append(window)
    if current:
        groups.append(current)
    if not groups:
        return []
    return max(
        groups,
        key=lambda group: (
            len(group),
            sum((window.duration for window in group), timedelta()),
            -min(window.predicted_magnitude for window in group),
            max(window.maximum_altitude_deg for window in group),
        ),
    )


def _window_rank(window: _NightWindow) -> tuple[float, float, float]:
    return (
        window.duration.total_seconds(),
        window.maximum_altitude_deg,
        -window.predicted_magnitude,
    )


def _observing_night_date(value: datetime) -> date:
    if value.hour < 12:
        return (value - timedelta(days=1)).date()
    return value.date()


def _date_range_label(start: date, end: date, local_reference: datetime) -> str:
    start_label = _local_date_label(start, local_reference)
    if start == end:
        return start_label
    return tr(
        "{start} - {end}",
        start=start_label,
        end=_local_date_label(end, local_reference),
    )


def _observing_window_label(
    start: date,
    end: date,
    peak_label: str,
    local_reference: datetime,
) -> str:
    start_label = _local_date_label(start, local_reference)
    if start == end:
        return tr(
            "Notte del {date}; momento consigliato {peak}",
            date=start_label,
            peak=peak_label,
        )
    return tr(
        "Dal {start} al {end}; momento consigliato {peak}",
        start=start_label,
        end=_local_date_label(end, local_reference),
        peak=peak_label,
    )


def _local_date_label(value: date, local_reference: datetime) -> str:
    local_value = datetime.combine(
        value,
        datetime.min.time(),
        tzinfo=local_reference.tzinfo,
    )
    return format_datetime(local_value, include_time=False)


def _setup_for_magnitude(predicted_magnitude: float) -> str:
    if predicted_magnitude <= 6.5:
        return tr(
            "Prova prima a occhio nudo sotto un cielo buio; un binocolo facilita "
            "l'individuazione."
        )
    if predicted_magnitude <= 9.5:
        return tr(
            "Usa un binocolo o un piccolo telescopio sotto un cielo buio, con campo "
            "ampio e basso ingrandimento."
        )
    return tr(
        "Serve un telescopio sotto un cielo buio; inizia con basso ingrandimento e "
        "aumentalo solo dopo aver individuato la cometa."
    )


def _julian_day(value: datetime) -> float:
    return _as_utc(value).timestamp() / 86_400.0 + 2_440_587.5


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")
