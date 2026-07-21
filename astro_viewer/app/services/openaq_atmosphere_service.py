from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.localization import (
    format_compact_number,
    format_datetime,
    format_number,
    join_text,
    tr,
)


logger = logging.getLogger(__name__)

OPENAQ_LOCATIONS_URL = "https://api.openaq.org/v3/locations"
OPENAQ_LOCATION_LATEST_URL = "https://api.openaq.org/v3/locations/{locations_id}/latest"
OPENAQ_DEFAULT_RADIUS_M = 25_000
OPENAQ_CACHE_TTL = timedelta(minutes=45)

PM25_THRESHOLDS = (10.0, 25.0, 50.0)
PM10_THRESHOLDS = (20.0, 50.0, 100.0)
CLARITY_LABELS = (
    tr("Aria limpida"),
    tr("Discreta"),
    tr("Velata"),
    tr("Polverosa"),
    tr("Molto polverosa"),
)
CURRENT_MAX_AGE = timedelta(hours=24)
RECENT_MAX_AGE = timedelta(hours=72)
STALE_MAX_AGE = timedelta(days=7)


@dataclass(frozen=True)
class OpenAQReading:
    pollutant: str
    value: float
    unit: str
    timestamp: datetime | None = None
    source_name: str = ""
    provider_name: str = ""
    distance_km: float | None = None


@dataclass(frozen=True)
class LocalAtmosphere:
    visible: bool
    has_data: bool
    message: str
    pm25: str = "—"
    pm10: str = "—"
    clarity: str = "—"
    source: str = "—"
    source_detail: str = ""
    freshness: str = "—"
    freshness_category: str = "unavailable"
    freshness_warning: bool = False
    source_distance_km: float | None = None
    error_category: str = ""

    @classmethod
    def not_configured(cls) -> LocalAtmosphere:
        return cls(False, False, "")

    @classmethod
    def location_required(cls) -> LocalAtmosphere:
        return cls(
            True,
            False,
            tr("Configura una località per visualizzare l'atmosfera locale."),
        )

    @classmethod
    def no_data(cls) -> LocalAtmosphere:
        return cls(
            True,
            False,
            tr("Nessun dato OpenAQ disponibile per questa località."),
        )

    @classmethod
    def historical(cls, source: str, source_detail: str, freshness: str, measured_at: str) -> LocalAtmosphere:
        message = tr(
            "Nessuna misura OpenAQ recente disponibile. Ultima misura: {measured_at}. "
            "Misura storica.",
            measured_at=measured_at,
        )
        return cls(
            True,
            False,
            message,
            source=source or "OpenAQ",
            source_detail=source_detail,
            freshness=freshness,
            freshness_category="historical",
            freshness_warning=True,
        )

    @classmethod
    def failure(
        cls,
        message: str = tr("Dati OpenAQ non disponibili al momento."),
        *,
        error_category: str = "provider",
    ) -> LocalAtmosphere:
        return cls(True, False, message, error_category=error_category)

    def to_qml(self) -> dict:
        return {
            "visible": self.visible,
            "hasData": self.has_data,
            "message": self.message,
            "pm25": self.pm25,
            "pm10": self.pm10,
            "clarity": self.clarity,
            "source": self.source,
            "sourceDetail": self.source_detail,
            "freshness": self.freshness,
            "freshnessCategory": self.freshness_category,
            "freshnessWarning": self.freshness_warning,
        }


class OpenAQLocalAtmosphereService:
    """Fetches local particulate data from OpenAQ for Weather display.

    Limpidezza uses simple particulate thresholds only:
    PM2.5 <= 10 and PM10 <= 20: Aria limpida
    PM2.5 <= 25 and PM10 <= 50: Discreta
    PM2.5 <= 50 and PM10 <= 100: Velata
    PM2.5 <= 75 and PM10 <= 150: Polverosa
    Higher values: Molto polverosa

    AppController may pass usable PM readings to ObservationConditionsService as
    fallback/context input when NASA AOD is missing or not policy-eligible. The
    data remains separate from forecast transparency and seeing.
    """

    def __init__(
        self,
        *,
        locations_url: str = OPENAQ_LOCATIONS_URL,
        location_latest_url: str = OPENAQ_LOCATION_LATEST_URL,
        radius_m: int = OPENAQ_DEFAULT_RADIUS_M,
        cache_ttl: timedelta = OPENAQ_CACHE_TTL,
        session_factory: Callable[[str], requests.Session] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._locations_url = locations_url
        self._location_latest_url = location_latest_url
        self._radius_m = radius_m
        self._cache_ttl = cache_ttl
        self._session_factory = session_factory or self._session
        self._clock = clock or (lambda: datetime.now(UTC))
        self._cache: dict[tuple[float, float], tuple[datetime, LocalAtmosphere]] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    def atmosphere(self, api_key: str | None, location: ObserverLocation | None) -> LocalAtmosphere:
        if not api_key:
            return LocalAtmosphere.not_configured()
        if location is None:
            return LocalAtmosphere.location_required()

        cache_key = self._cache_key(location)
        cached = self._cache.get(cache_key)
        now = self._clock()
        if cached and now - cached[0] <= self._cache_ttl:
            return cached[1]

        result = self._fetch(api_key, location)
        if (
            result.has_data
            or result.message == LocalAtmosphere.no_data().message
            or result.freshness_category == "historical"
        ):
            self._cache[cache_key] = (now, result)
        return result

    def _fetch(self, api_key: str, location: ObserverLocation) -> LocalAtmosphere:
        session = self._session_factory(api_key)
        locations_response = self._get(
            session,
            self._locations_url,
            params={
                "coordinates": f"{location.latitude:.4f},{location.longitude:.4f}",
                "radius": str(min(self._radius_m, OPENAQ_DEFAULT_RADIUS_M)),
                "parameters_id": "1,2",
                "limit": "20",
                "page": "1",
            },
        )
        if isinstance(locations_response, LocalAtmosphere):
            return locations_response

        locations = self._payload_results(locations_response)
        if locations is None:
            return LocalAtmosphere.failure(tr("Risposta OpenAQ non riconosciuta."))
        if not locations:
            return LocalAtmosphere.no_data()

        latest_items = []
        latest_failure: LocalAtmosphere | None = None
        for location_item in self._nearest_locations(locations)[:8]:
            location_id = location_item.get("id") if isinstance(location_item, dict) else None
            if location_id is None:
                continue
            latest_response = self._get(
                session,
                self._location_latest_url.format(locations_id=location_id),
                params={"limit": "100", "page": "1"},
            )
            if isinstance(latest_response, LocalAtmosphere):
                if latest_response.error_category == "authentication":
                    return latest_response
                latest_failure = latest_failure or latest_response
                continue
            latest_results = self._payload_results(latest_response)
            if latest_results is None:
                latest_failure = latest_failure or LocalAtmosphere.failure(
                    tr("Risposta OpenAQ non riconosciuta.")
                )
                continue
            sensor_context = self._sensor_context_by_id(location_item)
            for item in latest_results:
                if isinstance(item, dict):
                    latest_items.append(self._enrich_latest_item(item, location_item, sensor_context))

        readings = self._readings_from_results(latest_items, location)
        if readings:
            return self._from_readings(readings)
        if latest_failure is not None:
            return latest_failure
        return LocalAtmosphere.no_data()

    def _get(self, session: requests.Session, url: str, *, params: dict[str, str]) -> requests.Response | LocalAtmosphere:
        try:
            response = session.get(url, params=params, timeout=(10, 20))
        except requests.RequestException as exc:
            logger.warning("OpenAQ local atmosphere lookup failed: %s", exc.__class__.__name__)
            return LocalAtmosphere.failure(
                tr(
                    "Connessione OpenAQ non riuscita: {error_type}.",
                    error_type=exc.__class__.__name__,
                ),
                error_category="network",
            )

        if response.status_code == 200:
            return response
        if response.status_code in (401, 403):
            return LocalAtmosphere.failure(
                tr("API key OpenAQ non valida o non autorizzata."),
                error_category="authentication",
            )
        if response.status_code == 429:
            return LocalAtmosphere.failure(
                tr("OpenAQ ha applicato un limite di traffico. Riprova più tardi."),
                error_category="rate_limit",
            )
        return LocalAtmosphere.failure(
            tr(
                "OpenAQ ha risposto con HTTP {status_code}.",
                status_code=response.status_code,
            ),
            error_category="http",
        )

    def _from_payload(self, response: requests.Response, location: ObserverLocation) -> LocalAtmosphere:
        try:
            payload = response.json()
        except ValueError:
            return LocalAtmosphere.failure(tr("Risposta OpenAQ non valida."))

        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            return LocalAtmosphere.failure(tr("Risposta OpenAQ non riconosciuta."))

        readings = self._readings_from_results(results, location)
        if not readings:
            return LocalAtmosphere.no_data()
        return self._from_readings(readings)

    def _from_readings(self, readings: dict[str, OpenAQReading]) -> LocalAtmosphere:
        now = self._clock()
        source_reading = self._source_reading(readings.get("pm25"), readings.get("pm10"))
        if source_reading is None:
            return LocalAtmosphere.no_data()

        freshness_category = self._freshness_category(source_reading, now)
        freshness_label = self._freshness_label(source_reading, now)
        source = self._source_label(source_reading)
        source_detail = self._source_detail(source_reading, freshness_label)
        if freshness_category == "historical":
            return LocalAtmosphere.historical(
                source,
                self._source_detail(source_reading, freshness_label, include_timestamp=True),
                freshness_label,
                self._date_label(source_reading),
            )

        pm25 = self._usable_reading(readings.get("pm25"), now)
        pm10 = self._usable_reading(readings.get("pm10"), now)
        return LocalAtmosphere(
            visible=True,
            has_data=True,
            message="",
            pm25=self._format_reading(pm25),
            pm10=self._format_reading(pm10),
            clarity=self._clarity_label(pm25, pm10),
            source=source,
            source_detail=source_detail,
            freshness=freshness_label,
            freshness_category=freshness_category,
            freshness_warning=freshness_category in ("recent", "stale"),
            source_distance_km=source_reading.distance_km,
        )

    @staticmethod
    def _payload_results(response: requests.Response) -> list | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        results = payload.get("results") if isinstance(payload, dict) else None
        return results if isinstance(results, list) else None

    @staticmethod
    def _nearest_locations(locations: list) -> list[dict[str, Any]]:
        usable = [item for item in locations if isinstance(item, dict)]

        def distance_key(item: dict[str, Any]) -> float:
            distance = OpenAQLocalAtmosphereService._float_value(item.get("distance"))
            return distance if distance is not None else math.inf

        return sorted(
            usable,
            key=distance_key,
        )

    @staticmethod
    def _sensor_context_by_id(location_item: dict[str, Any]) -> dict[int, dict[str, Any]]:
        context: dict[int, dict[str, Any]] = {}
        sensors = location_item.get("sensors")
        if not isinstance(sensors, list):
            return context
        for sensor in sensors:
            if not isinstance(sensor, dict):
                continue
            sensor_id = OpenAQLocalAtmosphereService._int_value(sensor.get("id"))
            if sensor_id is None:
                continue
            context[sensor_id] = {
                "parameter": sensor.get("parameter"),
                "unit": sensor.get("units") or sensor.get("unit"),
            }
        return context

    @staticmethod
    def _enrich_latest_item(
        item: dict[str, Any],
        location_item: dict[str, Any],
        sensor_context: dict[int, dict[str, Any]],
    ) -> dict[str, Any]:
        enriched = dict(item)
        sensor_id = OpenAQLocalAtmosphereService._int_value(
            item.get("sensorsId") or item.get("sensor_id") or item.get("sensorId")
        )
        if sensor_id is not None and sensor_id in sensor_context:
            for key, value in sensor_context[sensor_id].items():
                if value is not None:
                    enriched.setdefault(key, value)
        enriched.setdefault(
            "location",
            {
                "name": location_item.get("name") or location_item.get("locality"),
                "coordinates": location_item.get("coordinates"),
            },
        )
        for key in ("provider", "owner", "distance"):
            if key in location_item:
                enriched.setdefault(key, location_item[key])
        return enriched

    def _readings_from_results(
        self,
        results: list,
        location: ObserverLocation,
    ) -> dict[str, OpenAQReading]:
        readings: dict[str, OpenAQReading] = {}
        for item in results:
            if not isinstance(item, dict):
                continue
            pollutant = self._pollutant_name(item)
            if pollutant not in ("pm25", "pm10"):
                continue
            value = self._float_value(item.get("value"))
            if value is None:
                continue

            reading = OpenAQReading(
                pollutant=pollutant,
                value=value,
                unit=self._unit_label(item),
                timestamp=self._timestamp(item),
                source_name=self._source_name(item),
                provider_name=self._provider_name(item),
                distance_km=self._distance_km(item, location),
            )
            current = readings.get(pollutant)
            if current is None or self._is_more_recent_or_nearer(reading, current):
                readings[pollutant] = reading
        return readings

    @staticmethod
    def _is_more_recent_or_nearer(candidate: OpenAQReading, current: OpenAQReading) -> bool:
        candidate_time = candidate.timestamp or datetime.min.replace(tzinfo=UTC)
        current_time = current.timestamp or datetime.min.replace(tzinfo=UTC)
        if candidate_time != current_time:
            return candidate_time > current_time
        if candidate.distance_km is None:
            return False
        if current.distance_km is None:
            return True
        return candidate.distance_km < current.distance_km

    @staticmethod
    def _format_reading(reading: OpenAQReading | None) -> str:
        if reading is None:
            return "—"
        return tr(
            "{value} {unit}",
            value=format_compact_number(reading.value, max_decimals=1),
            unit=reading.unit,
        )

    @staticmethod
    def _clarity_label(pm25: OpenAQReading | None, pm10: OpenAQReading | None) -> str:
        ranks = []
        if pm25 is not None:
            ranks.append(OpenAQLocalAtmosphereService._rank(pm25.value, PM25_THRESHOLDS))
        if pm10 is not None:
            ranks.append(OpenAQLocalAtmosphereService._rank(pm10.value, PM10_THRESHOLDS))
        if not ranks:
            return "—"
        return CLARITY_LABELS[max(ranks)]

    @staticmethod
    def _rank(value: float, thresholds: tuple[float, float, float]) -> int:
        if value <= thresholds[0]:
            return 0
        if value <= thresholds[1]:
            return 1
        if value <= thresholds[2]:
            return 2
        if value <= thresholds[2] * 1.5:
            return 3
        return 4

    @staticmethod
    def _source_reading(pm25: OpenAQReading | None, pm10: OpenAQReading | None) -> OpenAQReading | None:
        candidates = [reading for reading in (pm25, pm10) if reading is not None]
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda reading: (
                reading.timestamp or datetime.min.replace(tzinfo=UTC),
                -(
                    reading.distance_km
                    if reading.distance_km is not None
                    else math.inf
                ),
            ),
            reverse=True,
        )[0]

    @staticmethod
    def _source_label(reading: OpenAQReading | None) -> str:
        if reading is None:
            return "—"
        return reading.source_name or reading.provider_name or "OpenAQ"

    @staticmethod
    def _source_detail(
        reading: OpenAQReading | None,
        freshness_label: str = "",
        *,
        include_timestamp: bool = False,
    ) -> str:
        if reading is None:
            return ""
        parts = []
        if reading.provider_name and reading.provider_name != reading.source_name:
            parts.append(reading.provider_name)
        if reading.distance_km is not None:
            parts.append(
                tr(
                    "{value} km",
                    value=format_number(reading.distance_km, decimals=1),
                )
            )
        if freshness_label:
            parts.append(freshness_label)
        if include_timestamp and reading.timestamp is not None:
            parts.append(
                tr(
                    "{datetime} UTC",
                    datetime=format_datetime(reading.timestamp),
                )
            )
        return join_text(parts)

    @staticmethod
    def _date_label(reading: OpenAQReading) -> str:
        if reading.timestamp is None:
            return tr("data non disponibile")
        return format_datetime(reading.timestamp, include_time=False)

    @staticmethod
    def _usable_reading(reading: OpenAQReading | None, now: datetime) -> OpenAQReading | None:
        if reading is None:
            return None
        if OpenAQLocalAtmosphereService._age(reading, now) > STALE_MAX_AGE:
            return None
        return reading

    @staticmethod
    def _freshness_category(reading: OpenAQReading, now: datetime) -> str:
        age = OpenAQLocalAtmosphereService._age(reading, now)
        if age < CURRENT_MAX_AGE:
            return "current"
        if age < RECENT_MAX_AGE:
            return "recent"
        if age <= STALE_MAX_AGE:
            return "stale"
        return "historical"

    @staticmethod
    def _freshness_label(reading: OpenAQReading, now: datetime) -> str:
        if reading.timestamp is None:
            return tr("Aggiornamento non disponibile")
        age = OpenAQLocalAtmosphereService._age(reading, now)
        if age < CURRENT_MAX_AGE:
            return tr("Aggiornato oggi")
        days = max(1, int(age.total_seconds() // 86_400))
        if days == 1:
            return tr("Aggiornato ieri")
        if age <= STALE_MAX_AGE:
            return tr("Aggiornato {days} giorni fa", days=days)
        return tr("Ultima misura {days} giorni fa", days=days)

    @staticmethod
    def _age(reading: OpenAQReading, now: datetime) -> timedelta:
        if reading.timestamp is None:
            return timedelta.max
        reference = now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)
        return max(timedelta(0), reference - reading.timestamp.astimezone(UTC))

    @staticmethod
    def _pollutant_name(item: dict[str, Any]) -> str:
        parameter = item.get("parameter") or item.get("parameter_name") or item.get("parameterName")
        if isinstance(parameter, dict):
            name = parameter.get("name") or parameter.get("displayName") or parameter.get("label")
            parameter_id = parameter.get("id")
        else:
            name = str(parameter or item.get("name") or "")
            parameter_id = item.get("parameter_id") or item.get("parameterId") or item.get("parameter")
        normalized = name.lower().replace(".", "").replace("_", "").replace(" ", "")
        if normalized in ("pm25", "pm2.5".replace(".", "")):
            return "pm25"
        if normalized == "pm10":
            return "pm10"
        try:
            parsed_id = int(parameter_id)
        except (TypeError, ValueError):
            return ""
        if parsed_id == 2:
            return "pm25"
        if parsed_id == 1:
            return "pm10"
        return ""

    @staticmethod
    def _unit_label(item: dict[str, Any]) -> str:
        unit = item.get("unit") or item.get("units")
        parameter = item.get("parameter")
        if not unit and isinstance(parameter, dict):
            unit = parameter.get("units") or parameter.get("unit")
        if isinstance(unit, dict):
            unit = unit.get("label") or unit.get("name") or unit.get("symbol")
        if not unit:
            return "µg/m³"
        return str(unit).replace("ug/m3", "µg/m³").replace("µg/m3", "µg/m³")

    @staticmethod
    def _timestamp(item: dict[str, Any]) -> datetime | None:
        candidates = [
            item.get("datetime"),
            item.get("date"),
            item.get("lastUpdated"),
            item.get("timestamp"),
        ]
        period = item.get("period")
        if isinstance(period, dict):
            candidates.extend([period.get("datetimeFrom"), period.get("datetimeTo")])
        for candidate in candidates:
            if isinstance(candidate, dict):
                parsed = OpenAQLocalAtmosphereService._parse_datetime(
                    candidate.get("utc") or candidate.get("local") or candidate.get("value")
                )
            else:
                parsed = OpenAQLocalAtmosphereService._parse_datetime(candidate)
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        text = str(value).strip()
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _source_name(item: dict[str, Any]) -> str:
        location = item.get("location")
        if isinstance(location, dict):
            for key in ("name", "locality", "label"):
                if location.get(key):
                    return str(location[key])
        for key in ("location_name", "locationName", "siteName", "sourceName"):
            if item.get(key):
                return str(item[key])
        return ""

    @staticmethod
    def _provider_name(item: dict[str, Any]) -> str:
        for key in ("provider", "owner", "source"):
            value = item.get(key)
            if isinstance(value, dict):
                name = value.get("name") or value.get("label")
                if name:
                    return str(name)
            elif value:
                return str(value)
        return "OpenAQ"

    @staticmethod
    def _distance_km(item: dict[str, Any], location: ObserverLocation) -> float | None:
        for key in ("distance_km", "distanceKm"):
            value = OpenAQLocalAtmosphereService._float_value(item.get(key))
            if value is not None:
                return value

        for key in ("distance", "distance_m", "distanceMeters"):
            value = OpenAQLocalAtmosphereService._float_value(item.get(key))
            if value is not None:
                return value / 1000

        coordinates = item.get("coordinates")
        if not isinstance(coordinates, dict):
            location_data = item.get("location")
            coordinates = location_data.get("coordinates") if isinstance(location_data, dict) else None
        if not isinstance(coordinates, dict):
            return None

        latitude = OpenAQLocalAtmosphereService._float_value(coordinates.get("latitude") or coordinates.get("lat"))
        longitude = OpenAQLocalAtmosphereService._float_value(coordinates.get("longitude") or coordinates.get("lon"))
        if latitude is None or longitude is None:
            return None
        return OpenAQLocalAtmosphereService._haversine_km(
            location.latitude,
            location.longitude,
            latitude,
            longitude,
        )

    @staticmethod
    def _float_value(value: Any) -> float | None:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(parsed) or math.isinf(parsed):
            return None
        return parsed

    @staticmethod
    def _int_value(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_km = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _cache_key(location: ObserverLocation) -> tuple[float, float]:
        return (round(location.latitude, 2), round(location.longitude, 2))

    @staticmethod
    def _session(api_key: str) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=2,
            connect=2,
            read=1,
            backoff_factor=1,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        session.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=2, pool_maxsize=2))
        session.headers.update(
            {
                "User-Agent": "NightScope OpenAQ local atmosphere",
                "Accept": "application/json",
                "X-API-Key": api_key,
            }
        )
        session.trust_env = True
        return session
