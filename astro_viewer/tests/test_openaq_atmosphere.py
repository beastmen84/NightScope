from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest
from unittest.mock import Mock

from PySide6.QtCore import QObject

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.openaq_atmosphere_service import (
    LocalAtmosphere,
    OpenAQLocalAtmosphereService,
    OpenAQReading,
)
from astro_viewer.app.services.openaq_credentials import OpenAQCredentialState
from astro_viewer.app.viewmodels.app_controller import AppController


class FakeOpenAQResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


class FakeOpenAQSession:
    def __init__(self, responses: FakeOpenAQResponse | list[FakeOpenAQResponse]) -> None:
        self._responses = responses if isinstance(responses, list) else [responses]
        self.calls: list[dict] = []

    def get(self, url: str, **kwargs) -> FakeOpenAQResponse:
        self.calls.append({"url": url, **kwargs})
        if len(self._responses) == 1:
            return self._responses[0]
        return self._responses.pop(0)


def _location() -> ObserverLocation:
    return ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa")


def _locations_response(name: str = "Addis Ababa Central") -> FakeOpenAQResponse:
    return FakeOpenAQResponse(
        200,
        {
            "results": [
                {
                    "id": 101,
                    "name": name,
                    "provider": {"name": "OpenAQ"},
                    "distance": 1600,
                    "coordinates": {"latitude": 9.04, "longitude": 38.75},
                    "sensors": [
                        {
                            "id": 2001,
                            "parameter": {"id": 1, "name": "pm10"},
                            "units": "ug/m3",
                        },
                        {
                            "id": 2002,
                            "parameter": {"id": 2, "name": "pm25"},
                            "units": "ug/m3",
                        },
                    ],
                }
            ]
        },
    )


def _latest_response(*items: dict) -> FakeOpenAQResponse:
    return FakeOpenAQResponse(200, {"results": list(items)})


def _latest_item(sensor_id: int, value: float, timestamp: str) -> dict:
    return {
        "sensorsId": sensor_id,
        "value": value,
        "datetime": {"utc": timestamp},
    }


def _service(
    response: FakeOpenAQResponse | list[FakeOpenAQResponse],
    clock=None,
) -> tuple[OpenAQLocalAtmosphereService, FakeOpenAQSession]:
    session = FakeOpenAQSession(response)
    service = OpenAQLocalAtmosphereService(
        session_factory=lambda _api_key: session,
        clock=clock,
    )
    return service, session


class OpenAQLocalAtmosphereServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 6, 28, 12, 0, tzinfo=UTC)

    def test_no_credentials_hides_section(self) -> None:
        service, session = _service(FakeOpenAQResponse(200, {"results": []}))

        result = service.atmosphere(None, _location())

        self.assertFalse(result.visible)
        self.assertFalse(result.has_data)
        self.assertEqual(session.calls, [])

    def test_no_location_returns_location_required_fallback(self) -> None:
        service, session = _service(FakeOpenAQResponse(200, {"results": []}))

        result = service.atmosphere("openaq-secret", None)

        self.assertTrue(result.visible)
        self.assertFalse(result.has_data)
        self.assertIn("Configura una località", result.message)
        self.assertEqual(session.calls, [])

    def test_successful_pm25_pm10_dto(self) -> None:
        service, session = _service(
            [
                _locations_response(),
                _latest_response(
                    {
                        **_latest_item(2002, 8.4, "2026-06-28T08:10:00Z"),
                        "coordinates": {"latitude": 9.04, "longitude": 38.75},
                    },
                    _latest_item(2001, 33, "2026-06-28T08:00:00Z"),
                ),
            ],
            clock=lambda: self.now,
        )

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.visible)
        self.assertTrue(result.has_data)
        self.assertEqual(result.pm25, "8,4 µg/m³")
        self.assertEqual(result.pm10, "33 µg/m³")
        self.assertEqual(result.clarity, "Discreta")
        self.assertEqual(result.source, "Addis Ababa Central")
        self.assertEqual(result.source_distance_km, 1.6)
        self.assertEqual(result.freshness_category, "current")
        self.assertEqual(result.freshness, "Aggiornato oggi")
        self.assertIn("Aggiornato oggi", result.source_detail)
        self.assertNotIn("sourceDistanceKm", result.to_qml())
        self.assertEqual(session.calls[0]["params"]["coordinates"], "9.0300,38.7400")
        self.assertIn("/v3/locations", session.calls[0]["url"])
        self.assertIn("/v3/locations/101/latest", session.calls[1]["url"])
        self.assertNotIn("/v3/measurements", session.calls[0]["url"])

    def test_pm10_only_keeps_missing_pm25_unavailable(self) -> None:
        service, _session = _service(
            [
                _locations_response(name="Dust Station"),
                _latest_response(_latest_item(2001, 118, "2026-06-28T08:00:00Z")),
            ],
            clock=lambda: self.now,
        )

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.has_data)
        self.assertEqual(result.pm25, "—")
        self.assertEqual(result.pm10, "118 µg/m³")
        self.assertEqual(result.clarity, "Polverosa")

    def test_pm25_only_keeps_missing_pm10_unavailable(self) -> None:
        service, _session = _service(
            [
                _locations_response(),
                _latest_response(_latest_item(2002, 27, "2026-06-28T08:00:00Z")),
            ],
            clock=lambda: self.now,
        )

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.has_data)
        self.assertEqual(result.pm25, "27 µg/m³")
        self.assertEqual(result.pm10, "—")
        self.assertEqual(result.clarity, "Velata")

    def test_no_nearby_data_returns_no_data_message(self) -> None:
        service, _session = _service(FakeOpenAQResponse(200, {"results": []}))

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.visible)
        self.assertFalse(result.has_data)
        self.assertEqual(result.message, "Nessun dato OpenAQ disponibile per questa località.")

    def test_api_failure_returns_user_friendly_message(self) -> None:
        service, _session = _service(FakeOpenAQResponse(500, {"detail": "server error"}))

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.visible)
        self.assertFalse(result.has_data)
        self.assertIn("HTTP 500", result.message)

    def test_latest_endpoint_failure_is_not_cached_as_no_data(self) -> None:
        service, session = _service(
            [
                _locations_response(),
                FakeOpenAQResponse(429),
                _locations_response(),
                _latest_response(),
            ],
            clock=lambda: self.now,
        )

        first = service.atmosphere("openaq-secret", _location())
        second = service.atmosphere("openaq-secret", _location())

        self.assertIn("limite di traffico", first.message)
        self.assertEqual(
            second.message,
            "Nessun dato OpenAQ disponibile per questa località.",
        )
        self.assertEqual(len(session.calls), 4)

    def test_latest_authentication_failure_uses_language_independent_category(self) -> None:
        service, _session = _service(
            [
                _locations_response(),
                FakeOpenAQResponse(401),
            ],
            clock=lambda: self.now,
        )

        result = service.atmosphere("openaq-secret", _location())

        self.assertEqual(result.error_category, "authentication")
        self.assertIn("API key OpenAQ", result.message)

    def test_distance_fields_use_documented_units_and_preserve_zero(self) -> None:
        self.assertEqual(
            OpenAQLocalAtmosphereService._distance_km(
                {"distance": 100},
                _location(),
            ),
            0.1,
        )
        self.assertEqual(
            OpenAQLocalAtmosphereService._distance_km(
                {"distance": 0},
                _location(),
            ),
            0.0,
        )
        self.assertEqual(
            OpenAQLocalAtmosphereService._distance_km(
                {"distance_km": 0.4},
                _location(),
            ),
            0.4,
        )

    def test_exact_station_is_sorted_and_selected_before_more_distant_data(self) -> None:
        ordered = OpenAQLocalAtmosphereService._nearest_locations(
            [
                {"id": 2, "distance": 100},
                {"id": 1, "distance": 0},
                {"id": 3},
            ]
        )
        self.assertEqual([item["id"] for item in ordered], [1, 2, 3])

        timestamp = datetime(2026, 6, 28, 8, 0, tzinfo=UTC)
        selected = OpenAQLocalAtmosphereService._source_reading(
            OpenAQReading("pm25", 8, "ug/m3", timestamp, distance_km=0.0),
            OpenAQReading("pm10", 20, "ug/m3", timestamp, distance_km=0.1),
        )
        self.assertEqual(selected.distance_km, 0.0)

    def test_recent_measurements_show_warning_freshness(self) -> None:
        service, _session = _service(
            [
                _locations_response(),
                _latest_response(_latest_item(2002, 12, "2026-06-26T11:00:00Z")),
            ],
            clock=lambda: self.now,
        )

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.has_data)
        self.assertEqual(result.freshness_category, "recent")
        self.assertEqual(result.freshness, "Aggiornato 2 giorni fa")
        self.assertTrue(result.freshness_warning)

    def test_stale_measurements_remain_visible_with_warning(self) -> None:
        service, _session = _service(
            [
                _locations_response(),
                _latest_response(_latest_item(2002, 12, "2026-06-23T12:00:00Z")),
            ],
            clock=lambda: self.now,
        )

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.has_data)
        self.assertEqual(result.freshness_category, "stale")
        self.assertEqual(result.freshness, "Aggiornato 5 giorni fa")
        self.assertTrue(result.freshness_warning)

    def test_historical_measurements_do_not_show_current_clarity(self) -> None:
        service, _session = _service(
            [
                _locations_response(),
                _latest_response(_latest_item(2002, 90, "2026-05-21T18:00:00Z")),
            ],
            clock=lambda: self.now,
        )

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.visible)
        self.assertFalse(result.has_data)
        self.assertEqual(result.clarity, "—")
        self.assertEqual(result.freshness_category, "historical")
        self.assertEqual(result.freshness, "Ultima misura 37 giorni fa")
        self.assertIn("Ultima misura: 21/05/2026", result.message)
        self.assertIn("Misura storica", result.message)

    def test_cache_reuses_recent_location_lookup(self) -> None:
        now = datetime(2026, 6, 28, 8, 0, tzinfo=UTC)
        clock_value = {"now": now}
        service, session = _service(
            [
                _locations_response(),
                _latest_response(_latest_item(2002, 6, "2026-06-28T08:00:00Z")),
                _locations_response(),
                _latest_response(_latest_item(2002, 6, "2026-06-28T08:00:00Z")),
            ],
            clock=lambda: clock_value["now"],
        )

        first = service.atmosphere("openaq-secret", _location())
        second = service.atmosphere("openaq-secret", _location())
        clock_value["now"] = now + timedelta(minutes=46)
        third = service.atmosphere("openaq-secret", _location())

        self.assertTrue(first.has_data)
        self.assertEqual(second.pm25, first.pm25)
        self.assertEqual(third.pm25, first.pm25)
        self.assertEqual(len(session.calls), 4)


class OpenAQLocalAtmosphereControllerTests(unittest.TestCase):
    def test_saved_api_key_without_successful_test_keeps_section_hidden(self) -> None:
        controller = AppController.__new__(AppController)
        fake_service = _FakeAtmosphereService()
        controller._openaq_credential_store = _FakeOpenAQCredentialStore("openaq-secret")
        controller._openaq_credentials_state = OpenAQCredentialState(
            configured=True,
            secure_store_available=True,
            connection_verified=False,
        )
        controller._local_atmosphere = LocalAtmosphere.location_required()
        controller._local_atmosphere_service = fake_service
        controller._local_atmosphere_refresh_running = False
        controller._location = _location()

        controller._refresh_local_atmosphere()

        self.assertFalse(controller._local_atmosphere.visible)
        self.assertEqual(fake_service.calls, 0)

    def test_stale_location_completion_reschedules_current_location(self) -> None:
        controller = AppController.__new__(AppController)
        QObject.__init__(controller)
        controller._openaq_credential_store = _FakeOpenAQCredentialStore("openaq-secret")
        controller._openaq_credentials_state = OpenAQCredentialState(
            configured=True,
            secure_store_available=True,
            connection_verified=True,
        )
        previous = LocalAtmosphere.no_data()
        controller._local_atmosphere = previous
        controller._local_atmosphere_refresh_running = True
        controller._local_atmosphere_refresh_request_id = 1
        controller._location = _location()
        controller._refresh_local_atmosphere = Mock()

        controller._finish_local_atmosphere_refresh(
            "44.495:11.343:bologna",
            LocalAtmosphere.failure(),
        )

        self.assertFalse(controller._local_atmosphere_refresh_running)
        self.assertIs(controller._local_atmosphere, previous)
        controller._refresh_local_atmosphere.assert_called_once_with()

    def test_completion_after_credentials_removal_stays_hidden(self) -> None:
        controller = AppController.__new__(AppController)
        QObject.__init__(controller)
        controller._openaq_credential_store = _FakeOpenAQCredentialStore(None)
        controller._openaq_credentials_state = OpenAQCredentialState(
            configured=False,
            secure_store_available=True,
            connection_verified=False,
        )
        controller._local_atmosphere = LocalAtmosphere.no_data()
        controller._local_atmosphere_refresh_running = True
        controller._location = _location()

        controller._finish_local_atmosphere_refresh(
            "9.030:38.740:addis ababa",
            LocalAtmosphere.failure(),
        )

        self.assertFalse(controller._local_atmosphere.visible)

    def test_stale_request_generation_cannot_finish_current_refresh(self) -> None:
        controller = AppController.__new__(AppController)
        QObject.__init__(controller)
        previous = LocalAtmosphere.no_data()
        controller._local_atmosphere = previous
        controller._local_atmosphere_refresh_running = True
        controller._local_atmosphere_refresh_request_id = 2
        controller._location = _location()

        controller._finish_local_atmosphere_refresh(
            1,
            "9.030:38.740:addis ababa",
            LocalAtmosphere.failure(),
        )

        self.assertTrue(controller._local_atmosphere_refresh_running)
        self.assertIs(controller._local_atmosphere, previous)


class _FakeOpenAQCredentialStore:
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def api_key(self) -> str | None:
        return self._api_key


class _FakeAtmosphereService:
    def __init__(self) -> None:
        self.calls = 0

    def atmosphere(self, _api_key, _location) -> LocalAtmosphere:
        self.calls += 1
        return LocalAtmosphere.no_data()


if __name__ == "__main__":
    unittest.main()
