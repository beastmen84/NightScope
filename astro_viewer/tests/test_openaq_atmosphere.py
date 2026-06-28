from __future__ import annotations

from datetime import UTC, datetime, timedelta
import unittest

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.openaq_atmosphere_service import OpenAQLocalAtmosphereService


class FakeOpenAQResponse:
    def __init__(self, status_code: int, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


class FakeOpenAQSession:
    def __init__(self, response: FakeOpenAQResponse) -> None:
        self._response = response
        self.calls: list[dict] = []

    def get(self, url: str, **kwargs) -> FakeOpenAQResponse:
        self.calls.append({"url": url, **kwargs})
        return self._response


def _location() -> ObserverLocation:
    return ObserverLocation("Addis Ababa", "Ethiopia", 9.03, 38.74, "Africa/Addis_Ababa")


def _service(response: FakeOpenAQResponse, clock=None) -> tuple[OpenAQLocalAtmosphereService, FakeOpenAQSession]:
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
            FakeOpenAQResponse(
                200,
                {
                    "results": [
                        {
                            "parameter": {"id": 2, "name": "pm25"},
                            "value": 8.4,
                            "unit": "ug/m3",
                            "datetime": {"utc": "2026-06-28T08:10:00Z"},
                            "location": {
                                "name": "Addis Ababa Central",
                                "coordinates": {"latitude": 9.04, "longitude": 38.75},
                            },
                            "provider": {"name": "OpenAQ"},
                        },
                        {
                            "parameter": {"id": 1, "name": "pm10"},
                            "value": 33,
                            "unit": "ug/m3",
                            "datetime": {"utc": "2026-06-28T08:00:00Z"},
                            "location": {"name": "Addis Ababa Central"},
                            "provider": {"name": "OpenAQ"},
                        },
                    ]
                },
            )
        )

        result = service.atmosphere("openaq-secret", _location())

        self.assertTrue(result.visible)
        self.assertTrue(result.has_data)
        self.assertEqual(result.pm25, "8.4 µg/m³")
        self.assertEqual(result.pm10, "33 µg/m³")
        self.assertEqual(result.clarity, "Discreta")
        self.assertEqual(result.source, "Addis Ababa Central")
        self.assertIn("Aggiornato 2026-06-28 08:10 UTC", result.source_detail)
        self.assertEqual(session.calls[0]["params"]["coordinates"], "9.03,38.74")

    def test_partial_data_keeps_missing_pollutant_unavailable(self) -> None:
        service, _session = _service(
            FakeOpenAQResponse(
                200,
                {
                    "results": [
                        {
                            "parameter": {"id": 1, "name": "pm10"},
                            "value": 118,
                            "unit": "ug/m3",
                            "datetime": {"utc": "2026-06-28T08:00:00Z"},
                            "location": {"name": "Dust Station"},
                        }
                    ]
                },
            )
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
            FakeOpenAQResponse(
                200,
                {
                    "results": [
                        {
                            "parameter": "pm25",
                            "value": 6,
                            "unit": "ug/m3",
                            "datetime": {"utc": "2026-06-28T08:00:00Z"},
                        }
                    ]
                },
            ),
            clock=lambda: clock_value["now"],
        )

        first = service.atmosphere("openaq-secret", _location())
        second = service.atmosphere("openaq-secret", _location())
        clock_value["now"] = now + timedelta(minutes=46)
        third = service.atmosphere("openaq-secret", _location())

        self.assertTrue(first.has_data)
        self.assertEqual(second.pm25, first.pm25)
        self.assertEqual(third.pm25, first.pm25)
        self.assertEqual(len(session.calls), 2)


if __name__ == "__main__":
    unittest.main()
