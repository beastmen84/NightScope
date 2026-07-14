from __future__ import annotations

import json
import logging
import math
import sqlite3
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from skyfield.api import EarthSatellite, wgs84

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.database.orbital_element_cache_repository import (
    OrbitalElementCacheRecord,
    OrbitalElementCacheRepository,
)
from astro_viewer.app.models.observing import AstronomicalEvent
from astro_viewer.app.services.localization import format_datetime, format_number, tr


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _OrbitalElements:
    fields: dict[str, object]
    record: OrbitalElementCacheRecord
    freshness: str


class IssPassEventSource:
    """Builds short-horizon, locally visible ISS pass intervals."""

    PROVIDER = "celestrak"
    OBJECT_ID = "25544"
    ELEMENT_FORMAT = "omm_json"
    ENDPOINT = "https://celestrak.org/NORAD/elements/gp.php"
    CACHE_TTL = timedelta(hours=6)
    refresh_interval = timedelta(hours=1)
    MAX_STALE_ELEMENT_AGE = timedelta(days=3)
    MAX_PROPAGATION_AGE = timedelta(days=14)
    HORIZON = timedelta(days=10)
    REQUEST_TIMEOUT_SECONDS = 10
    MIN_ALTITUDE_DEG = 10.0
    MAX_OBSERVER_SUN_ALTITUDE_DEG = -6.0
    SAMPLE_SECONDS = 10
    MIN_VISIBLE_DURATION_SECONDS = 30

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
        elements = self.prepare_event_data(location, now=now_utc)
        if elements is None:
            return []
        return self.build_events(
            location,
            now=now_utc,
            timescale=timescale,
            ephemeris=ephemeris,
            prepared_data=elements,
        )

    def prepare_event_data(
        self,
        _location: ObserverLocation,
        *,
        now: datetime,
    ) -> _OrbitalElements | None:
        return self._orbital_elements(_as_utc(now))

    def build_events(
        self,
        location: ObserverLocation,
        *,
        now: datetime,
        timescale: object,
        ephemeris: object,
        prepared_data: object,
    ) -> list[AstronomicalEvent]:
        if not isinstance(prepared_data, _OrbitalElements):
            return []
        now_utc = _as_utc(now)
        elements = prepared_data

        source_epoch = _parse_datetime(elements.record.source_epoch)
        prediction_end = min(
            now_utc + self.HORIZON,
            source_epoch + self.MAX_PROPAGATION_AGE,
        )
        if prediction_end <= now_utc:
            return []

        try:
            satellite = EarthSatellite.from_omm(timescale, elements.fields)
            return self._visible_passes(
                satellite,
                location,
                now=now_utc,
                end=prediction_end,
                timescale=timescale,
                ephemeris=ephemeris,
                elements=elements,
            )
        except Exception:
            logger.warning("ISS pass prediction failed.", exc_info=True)
            return []

    def _orbital_elements(self, now: datetime) -> _OrbitalElements | None:
        cached = self._cached_record()
        if cached is not None and self._cache_is_fresh(cached, now):
            fields = self._record_fields(cached)
            if fields is not None:
                return _OrbitalElements(fields, cached, "fresh")

        try:
            fields = self._fetch_fields()
            source_epoch = _parse_datetime(str(fields["EPOCH"]))
            if not self._epoch_is_usable(source_epoch, now):
                raise ValueError("CelesTrak returned orbital elements outside the supported age.")
            record = OrbitalElementCacheRecord(
                provider=self.PROVIDER,
                object_id=self.OBJECT_ID,
                element_format=self.ELEMENT_FORMAT,
                fetched_at=now.isoformat(),
                source_epoch=source_epoch.isoformat(),
                expires_at=(now + self.CACHE_TTL).isoformat(),
                payload=json.dumps(fields, ensure_ascii=True, separators=(",", ":")),
            )
            try:
                self._cache_repository.set(record)
            except (sqlite3.Error, OSError):
                logger.warning("ISS orbital elements could not be cached.", exc_info=True)
            return _OrbitalElements(fields, record, "updated")
        except (
            OSError,
            requests.RequestException,
            sqlite3.Error,
            TypeError,
            ValueError,
            KeyError,
        ):
            logger.warning("ISS orbital elements could not be refreshed.", exc_info=True)

        if cached is None or not self._stale_cache_is_usable(cached, now):
            return None
        fields = self._record_fields(cached)
        if fields is None:
            return None
        return _OrbitalElements(fields, cached, "stale")

    def _cached_record(self) -> OrbitalElementCacheRecord | None:
        try:
            return self._cache_repository.get(self.PROVIDER, self.OBJECT_ID)
        except (sqlite3.Error, OSError):
            logger.warning("ISS orbital cache could not be read.", exc_info=True)
            return None

    def _fetch_fields(self) -> dict[str, object]:
        response = self._http_get(
            self.ENDPOINT,
            params={"CATNR": self.OBJECT_ID, "FORMAT": "JSON"},
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or len(payload) != 1:
            raise ValueError("Unexpected CelesTrak OMM response.")
        fields = payload[0]
        if not isinstance(fields, Mapping):
            raise ValueError("Unexpected CelesTrak OMM record.")
        required = {"EPOCH", "NORAD_CAT_ID", "MEAN_MOTION", "ECCENTRICITY"}
        if not required.issubset(fields):
            raise ValueError("Incomplete CelesTrak OMM record.")
        if str(fields["NORAD_CAT_ID"]) != self.OBJECT_ID:
            raise ValueError("CelesTrak returned a different satellite.")
        return dict(fields)

    def _record_fields(self, record: OrbitalElementCacheRecord) -> dict[str, object] | None:
        try:
            payload = json.loads(record.payload)
        except (TypeError, ValueError):
            return None
        return dict(payload) if isinstance(payload, Mapping) else None

    def _cache_is_fresh(self, record: OrbitalElementCacheRecord, now: datetime) -> bool:
        try:
            return (
                record.element_format == self.ELEMENT_FORMAT
                and _parse_datetime(record.expires_at) > now
                and self._epoch_is_usable(_parse_datetime(record.source_epoch), now)
            )
        except ValueError:
            return False

    def _stale_cache_is_usable(
        self,
        record: OrbitalElementCacheRecord,
        now: datetime,
    ) -> bool:
        try:
            epoch = _parse_datetime(record.source_epoch)
        except ValueError:
            return False
        return now - epoch <= self.MAX_STALE_ELEMENT_AGE and epoch <= now + timedelta(hours=1)

    def _epoch_is_usable(self, epoch: datetime, now: datetime) -> bool:
        return now - epoch <= self.MAX_STALE_ELEMENT_AGE and epoch <= now + timedelta(hours=1)

    def _visible_passes(
        self,
        satellite: EarthSatellite,
        location: ObserverLocation,
        *,
        now: datetime,
        end: datetime,
        timescale: object,
        ephemeris: object,
        elements: _OrbitalElements,
    ) -> list[AstronomicalEvent]:
        topos = wgs84.latlon(location.latitude, location.longitude)
        search_start = now - timedelta(minutes=20)
        times, event_codes = satellite.find_events(
            topos,
            timescale.from_datetime(search_start),
            timescale.from_datetime(end),
            altitude_degrees=self.MIN_ALTITUDE_DEG,
        )
        zone = _zone(location.timezone)
        visible_events: list[AstronomicalEvent] = []
        rise_time: datetime | None = None
        for event_time, event_code in zip(times, event_codes):
            code = int(event_code)
            if code == 0:
                rise_time = _as_utc(event_time.utc_datetime())
            elif code == 2 and rise_time is not None:
                set_time = _as_utc(event_time.utc_datetime())
                event = self._visible_interval(
                    satellite,
                    topos,
                    rise_time,
                    set_time,
                    zone=zone,
                    timescale=timescale,
                    ephemeris=ephemeris,
                    elements=elements,
                )
                if event is not None and _parse_datetime(event.ends_at) >= now:
                    visible_events.append(event)
                rise_time = None
        return visible_events

    def _visible_interval(
        self,
        satellite: EarthSatellite,
        topos: object,
        rise_time: datetime,
        set_time: datetime,
        *,
        zone: ZoneInfo,
        timescale: object,
        ephemeris: object,
        elements: _OrbitalElements,
    ) -> AstronomicalEvent | None:
        sample_datetimes = _sample_datetimes(rise_time, set_time, self.SAMPLE_SECONDS)
        sample_times = timescale.from_datetimes(sample_datetimes)
        satellite_view = (satellite - topos).at(sample_times)
        altitudes, azimuths, _ = satellite_view.altaz()
        observer = ephemeris["earth"] + topos
        sun_altitudes, _, _ = (ephemeris["sun"] - observer).at(sample_times).altaz()
        sunlit = satellite.at(sample_times).is_sunlit(ephemeris)
        visible_indices = [
            index
            for index, (altitude, sun_altitude, illuminated) in enumerate(
                zip(altitudes.degrees, sun_altitudes.degrees, sunlit)
            )
            if altitude >= self.MIN_ALTITUDE_DEG
            and sun_altitude <= self.MAX_OBSERVER_SUN_ALTITUDE_DEG
            and bool(illuminated)
        ]
        if not visible_indices:
            return None

        first_index = visible_indices[0]
        last_index = visible_indices[-1]
        visible_start = sample_datetimes[first_index]
        visible_end = sample_datetimes[last_index]
        duration_seconds = int((visible_end - visible_start).total_seconds())
        if duration_seconds < self.MIN_VISIBLE_DURATION_SECONDS:
            return None
        peak_index = max(visible_indices, key=lambda index: float(altitudes.degrees[index]))
        peak_time = sample_datetimes[peak_index]
        peak_altitude = float(altitudes.degrees[peak_index])
        start_azimuth = float(azimuths.degrees[first_index])
        end_azimuth = float(azimuths.degrees[last_index])
        local_start = visible_start.astimezone(zone)
        local_end = visible_end.astimezone(zone)
        local_peak = peak_time.astimezone(zone)
        window_label = tr(
            "{start} - {end}",
            start=local_start.strftime("%H:%M"),
            end=local_end.strftime("%H:%M"),
        )
        source_epoch = _parse_datetime(elements.record.source_epoch)
        valid_until = source_epoch + self.MAX_PROPAGATION_AGE
        freshness_label = {
            "updated": tr("Dati orbitali aggiornati"),
            "fresh": tr("Dati orbitali recenti in cache"),
            "stale": tr("Dati orbitali di riserva"),
        }[elements.freshness]
        return AstronomicalEvent(
            id=_pass_id(peak_time, elements, source_epoch),
            title=tr("Passaggio della ISS"),
            event_type=tr("Passaggio ISS"),
            date_label=format_datetime(local_start, include_time=False),
            best_time=window_label,
            usefulness=0,
            setup=tr("Occhio nudo o binocolo; non serve il telescopio."),
            note=tr("Gli orari possono variare dopo un aggiornamento dell'orbita."),
            event_at=local_start.isoformat(),
            timing_kind="window",
            timing_label=tr("Finestra visibile"),
            observing_window=window_label,
            visibility_state="visible",
            visibility_label=tr("Visibile localmente"),
            visibility_detail=tr(
                "La ISS è illuminata dal Sole mentre il cielo locale è sufficientemente buio."
            ),
            event_type_code="satellite_pass",
            source_code="short_horizon_satellite_passes",
            source_label=tr("Passaggi satellitari a breve termine"),
            starts_at=local_start.isoformat(),
            ends_at=local_end.isoformat(),
            peak_at=local_peak.isoformat(),
            event_facts=(
                ("culmination", tr("Culminazione"), local_peak.strftime("%H:%M")),
                (
                    "maximum_altitude",
                    tr("Altezza massima"),
                    tr("{degrees}°", degrees=format_number(peak_altitude, decimals=0)),
                ),
                ("start_direction", tr("Direzione iniziale"), _direction(start_azimuth)),
                ("end_direction", tr("Direzione finale"), _direction(end_azimuth)),
                ("duration", tr("Durata"), _duration_label(duration_seconds)),
                ("illumination", tr("Illuminazione"), tr("ISS illuminata dal Sole")),
            ),
            data_source="CelesTrak GP / OMM",
            data_updated_at=elements.record.fetched_at,
            data_valid_until=valid_until.isoformat(),
            data_freshness=freshness_label,
        )


def _sample_datetimes(start: datetime, end: datetime, step_seconds: int) -> list[datetime]:
    values: list[datetime] = []
    current = start
    while current < end:
        values.append(current)
        current += timedelta(seconds=step_seconds)
    values.append(end)
    return values


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


def _direction(azimuth_degrees: float) -> str:
    labels = (
        tr("N"),
        tr("NE"),
        tr("E"),
        tr("SE"),
        tr("S"),
        tr("SO"),
        tr("O"),
        tr("NO"),
    )
    return labels[int((azimuth_degrees + 22.5) // 45) % len(labels)]


def _duration_label(seconds: int) -> str:
    minutes, remaining_seconds = divmod(seconds, 60)
    if minutes == 0:
        return tr("{seconds} s", seconds=remaining_seconds)
    return tr("{minutes} min {seconds} s", minutes=minutes, seconds=remaining_seconds)


def _pass_id(
    peak_time: datetime,
    elements: _OrbitalElements,
    source_epoch: datetime,
) -> str:
    """Use the continuous ISS revolution number instead of mutable peak seconds."""

    try:
        revolution_at_epoch = int(elements.fields["REV_AT_EPOCH"])
        mean_anomaly_revolutions = float(elements.fields["MEAN_ANOMALY"]) / 360.0
        mean_motion = float(elements.fields["MEAN_MOTION"])
        elapsed_days = (_as_utc(peak_time) - source_epoch).total_seconds() / 86_400.0
        revolution = math.floor(
            revolution_at_epoch + mean_anomaly_revolutions + elapsed_days * mean_motion
        )
        return f"iss-pass-{IssPassEventSource.OBJECT_ID}-rev-{revolution}"
    except (KeyError, TypeError, ValueError, OverflowError):
        bucket_seconds = 15 * 60
        bucket = round(_as_utc(peak_time).timestamp() / bucket_seconds) * bucket_seconds
        bucket_time = datetime.fromtimestamp(bucket, tz=UTC)
        return f"iss-pass-{IssPassEventSource.OBJECT_ID}-{bucket_time.strftime('%Y%m%dT%H%MZ')}"
