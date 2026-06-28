from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.openaq_atmosphere_service import LocalAtmosphere
from astro_viewer.app.services.openaq_atmosphere_service import OpenAQLocalAtmosphereService
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
        self.assertIn("Configura una posizione", result.message)
        self.assertEqual(session.calls, [])

    def test_successful_pm25_pm10_dto(self) -> None:
        service, session = _service(
            [
                _locations_response(),
                FakeOpenAQResponse(
                    200,
                    {
                        "results": [
                            {
                                "sensorsId": 2002,
                                "value": 8.4,
                                "datetime": {"utc": "2026-06-28T08:10:00Z"},
                                "coordinates": {"latitude": 9.04, "longitude": 38.75},
                            },
                            {
                                "sensorsId": 2001,
                                "value": 33,
                                "datetime": {"utc": "2026-06-28T08:00:00Z"},
                            },
                        ]
                    },
                ),
            ]
        )

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.visible)
        self.assertTrue(result.has_data)
        self.assertEqual(result.pm25, "8.4 µg/m³")
        self.assertEqual(result.pm10, "33 µg/m³")
        self.assertEqual(result.clarity, "Discreta")
        self.assertEqual(result.source, "Addis Ababa Central")
        self.assertIn("Aggiornato 2026-06-28 08:10 UTC", result.source_detail)
        self.assertEqual(session.calls[0]["params"]["coordinates"], "9.0300,38.7400")
        self.assertIn("/v3/locations", session.calls[0]["url"])
        self.assertIn("/v3/locations/101/latest", session.calls[1]["url"])
        self.assertNotIn("/v3/measurements", session.calls[0]["url"])

    def test_partial_data_keeps_missing_pollutant_unavailable(self) -> None:
        service, _session = _service(
            [
                _locations_response(name="Dust Station"),
                FakeOpenAQResponse(
                    200,
                    {
                        "results": [
                            {
                                "sensorsId": 2001,
                                "value": 118,
                                "datetime": {"utc": "2026-06-28T08:00:00Z"},
                            }
                        ]
                    },
                ),
            ]
        )

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.has_data)
        self.assertEqual(result.pm25, "—")
        self.assertEqual(result.pm10, "118 µg/m³")
        self.assertEqual(result.clarity, "Molto polverosa")

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

    def test_cache_reuses_recent_location_lookup(self) -> None:
        now = datetime(2026, 6, 28, 8, 0, tzinfo=UTC)
        clock_value = {"now": now}
        service, session = _service(
            [
                _locations_response(),
                FakeOpenAQResponse(
                    200,
                    {
                        "results": [
                            {
                                "sensorsId": 2002,
                                "value": 6,
                                "datetime": {"utc": "2026-06-28T08:00:00Z"},
                            }
                        ]
                    },
                ),
                _locations_response(),
                FakeOpenAQResponse(
                    200,
                    {
                        "results": [
                            {
                                "sensorsId": 2002,
                                "value": 6,
                                "datetime": {"utc": "2026-06-28T08:00:00Z"},
                            }
                        ]
                    },
                ),
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
