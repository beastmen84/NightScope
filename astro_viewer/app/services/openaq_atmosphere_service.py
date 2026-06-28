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


logger = logging.getLogger(__name__)

OPENAQ_LOCATIONS_URL = "https://api.openaq.org/v3/locations"
OPENAQ_LOCATION_LATEST_URL = "https://api.openaq.org/v3/locations/{locations_id}/latest"
OPENAQ_DEFAULT_RADIUS_M = 25_000
OPENAQ_CACHE_TTL = timedelta(minutes=45)

PM25_THRESHOLDS = (10.0, 25.0, 50.0)
PM10_THRESHOLDS = (20.0, 50.0, 100.0)
CLARITY_LABELS = ("Aria limpida", "Discreta", "Polverosa", "Molto polverosa")


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

    @classmethod
    def not_configured(cls) -> LocalAtmosphere:
        return cls(False, False, "")

    @classmethod
    def location_required(cls) -> LocalAtmosphere:
        return cls(True, False, "Configura una posizione per visualizzare l'atmosfera locale.")

    @classmethod
    def no_data(cls) -> LocalAtmosphere:
        return cls(True, False, "Nessun dato OpenAQ disponibile per questa località.")

    @classmethod
    def failure(cls, message: str = "Dati OpenAQ non disponibili al momento.") -> LocalAtmosphere:
        return cls(True, False, message)

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
        }


class OpenAQLocalAtmosphereService:
    """Fetches display-only local atmosphere data from OpenAQ.

    Limpidezza uses simple particulate thresholds only:
    PM2.5 <= 10 and PM10 <= 20: Aria limpida
    PM2.5 <= 25 and PM10 <= 50: Discreta
    PM2.5 <= 50 and PM10 <= 100: Polverosa
    Higher values: Molto polverosa

    The result is not used for seeing, transparency, planner or recommendation scores.
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
        if result.has_data or result.message == LocalAtmosphere.no_data().message:
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
            return LocalAtmosphere.failure("Risposta OpenAQ non riconosciuta.")
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
                latest_failure = latest_response
                continue
            latest_results = self._payload_results(latest_response)
            if latest_results is None:
                latest_failure = LocalAtmosphere.failure("Risposta OpenAQ non riconosciuta.")
                continue
            sensor_context = self._sensor_context_by_id(location_item)
            for item in latest_results:
                if isinstance(item, dict):
                    latest_items.append(self._enrich_latest_item(item, location_item, sensor_context))

        readings = self._readings_from_results(latest_items, location)
        if readings:
            return self._from_readings(readings)
        if latest_failure is not None and latest_failure.message.startswith("API key"):
            return latest_failure
        return LocalAtmosphere.no_data()

    def _get(self, session: requests.Session, url: str, *, params: dict[str, str]) -> requests.Response | LocalAtmosphere:
        try:
            response = session.get(url, params=params, timeout=(10, 20))
        except requests.RequestException as exc:
            logger.warning("OpenAQ local atmosphere lookup failed: %s", exc.__class__.__name__)
            return LocalAtmosphere.failure(f"Connessione OpenAQ non riuscita: {exc.__class__.__name__}.")

        if response.status_code == 200:
            return response
        if response.status_code in (401, 403):
            return LocalAtmosphere.failure("API key OpenAQ non valida o non autorizzata.")
        if response.status_code == 429:
            return LocalAtmosphere.failure("OpenAQ ha applicato un limite di traffico. Riprova più tardi.")
        return LocalAtmosphere.failure(f"OpenAQ ha risposto con HTTP {response.status_code}.")

    def _from_payload(self, response: requests.Response, location: ObserverLocation) -> LocalAtmosphere:
        try:
            payload = response.json()
        except ValueError:
            return LocalAtmosphere.failure("Risposta OpenAQ non valida.")

        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            return LocalAtmosphere.failure("Risposta OpenAQ non riconosciuta.")

        readings = self._readings_from_results(results, location)
        if not readings:
            return LocalAtmosphere.no_data()
        return self._from_readings(readings)

    @staticmethod
    def _from_readings(readings: dict[str, OpenAQReading]) -> LocalAtmosphere:
        pm25 = readings.get("pm25")
        pm10 = readings.get("pm10")
        source_reading = OpenAQLocalAtmosphereService._source_reading(pm25, pm10)
        return LocalAtmosphere(
            visible=True,
            has_data=True,
            message="",
            pm25=OpenAQLocalAtmosphereService._format_reading(pm25),
            pm10=OpenAQLocalAtmosphereService._format_reading(pm10),
            clarity=OpenAQLocalAtmosphereService._clarity_label(pm25, pm10),
            source=OpenAQLocalAtmosphereService._source_label(source_reading),
            source_detail=OpenAQLocalAtmosphereService._source_detail(source_reading),
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
        return sorted(
            usable,
            key=lambda item: OpenAQLocalAtmosphereService._float_value(item.get("distance")) or math.inf,
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
        value = f"{reading.value:.1f}".rstrip("0").rstrip(".")
        return f"{value} {reading.unit}".strip()

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
        return 3

    @staticmethod
    def _source_reading(pm25: OpenAQReading | None, pm10: OpenAQReading | None) -> OpenAQReading | None:
        candidates = [reading for reading in (pm25, pm10) if reading is not None]
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda reading: (
                reading.timestamp or datetime.min.replace(tzinfo=UTC),
                -(reading.distance_km or math.inf),
            ),
            reverse=True,
        )[0]

    @staticmethod
    def _source_label(reading: OpenAQReading | None) -> str:
        if reading is None:
            return "—"
        return reading.source_name or reading.provider_name or "OpenAQ"

    @staticmethod
    def _source_detail(reading: OpenAQReading | None) -> str:
        if reading is None:
            return ""
        parts = []
        if reading.provider_name and reading.provider_name != reading.source_name:
            parts.append(reading.provider_name)
        if reading.distance_km is not None:
            parts.append(f"{reading.distance_km:.1f} km")
        if reading.timestamp is not None:
            parts.append(f"Aggiornato {reading.timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
        return " · ".join(parts)

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
        for key in ("distance", "distance_m", "distanceMeters"):
            value = OpenAQLocalAtmosphereService._float_value(item.get(key))
            if value is not None:
                return value / 1000 if value > 500 else value

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
