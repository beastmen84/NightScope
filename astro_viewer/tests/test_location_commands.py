"""Protect framework-independent location commands and startup fallback policy."""

from __future__ import annotations

from typing import cast
from unittest.mock import Mock

import pytest

from astro_viewer.app.application.location_commands import (
    LocationCommandWorkflow,
    LocationRepositoryPort,
    LocationServicePort,
    StartupLocationInputs,
    StoredLocationInputs,
)
from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.services.location_preferences import (
    StartupLocationPreferences,
)
from astro_viewer.app.services.location_service import (
    APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE,
    LocationDetectionResult,
    LocationUnavailableError,
)


def _result(
    city: str = "Rome",
    *,
    country: str = "Italy",
    latitude: float = 41.9,
    longitude: float = 12.5,
    timezone: str = "Europe/Rome",
    provider: str = "manual_city",
    source: str = "test",
    message: str = "",
) -> LocationDetectionResult:
    return LocationDetectionResult(
        location=ObserverLocation(
            city,
            country,
            latitude,
            longitude,
            timezone,
        ),
        provider=provider,
        source=source,
        accuracy="test accuracy",
        approximate=provider == "ip_geolocation",
        message=message,
    )


def _workflow(
    *,
    repository: Mock | None = None,
    service: Mock | None = None,
) -> tuple[LocationCommandWorkflow, Mock, Mock]:
    resolved_repository = repository or Mock()
    resolved_service = service or Mock()
    return (
        LocationCommandWorkflow(
            repository=cast(
                LocationRepositoryPort,
                cast(object, resolved_repository),
            ),
            service=cast(
                LocationServicePort,
                cast(object, resolved_service),
            ),
        ),
        resolved_repository,
        resolved_service,
    )


def _stored_inputs(
    saved: LocationDetectionResult | None = None,
    cached: LocationDetectionResult | None = None,
) -> tuple[StoredLocationInputs, Mock, Mock]:
    load_saved = Mock(return_value=saved)
    load_cached = Mock(return_value=cached)
    return StoredLocationInputs(load_saved, load_cached), load_saved, load_cached


def test_search_distinguishes_blank_and_active_queries() -> None:
    workflow, repository, _service = _workflow()
    repository.search.return_value = [{"kind": "city", "selection_id": "1"}]

    blank = workflow.search("   ")
    active = workflow.search("Rome", limit=7)

    assert blank.has_query is False
    assert blank.matches == ()
    assert active.has_query is True
    assert active.matches == ({"kind": "city", "selection_id": "1"},)
    repository.search.assert_called_once_with("Rome", limit=7)


def test_city_and_observatory_commands_resolve_repository_records() -> None:
    workflow, repository, service = _workflow()
    city_result = _result()
    observatory_result = _result(
        "La Cañada",
        country="",
        provider="mpc_observatory",
    )
    repository.get_city.return_value = {"id": 12, "city": "Rome"}
    repository.get_observatory.return_value = {"mpc_code": "R50"}
    service.from_city_result.return_value = city_result
    service.from_mpc_observatory_result.return_value = observatory_result

    selected_city = workflow.select("city", "12")
    selected_observatory = workflow.select("mpc_observatory", "R50")

    assert selected_city.detection is city_result
    assert selected_observatory.detection is observatory_result
    repository.get_city.assert_called_once_with(12)
    repository.get_observatory.assert_called_once_with("R50")


@pytest.mark.parametrize(
    ("kind", "selection_id"),
    (("city", "not-an-id"), ("unknown", "12")),
)
def test_unknown_search_selections_are_ignored(kind: str, selection_id: str) -> None:
    workflow, repository, service = _workflow()

    outcome = workflow.select(kind, selection_id)

    assert outcome.handled is False
    repository.get_city.assert_not_called()
    repository.get_observatory.assert_not_called()
    assert not service.mock_calls


def test_deleted_city_or_observatory_selections_are_ignored() -> None:
    workflow, repository, service = _workflow()
    repository.get_city.return_value = None
    repository.get_observatory.return_value = None

    city = workflow.select_city(404)
    observatory = workflow.select_observatory("ZZZ")

    assert city.handled is False
    assert observatory.handled is False
    assert not service.mock_calls


def test_recent_selection_rejects_stale_indexes() -> None:
    workflow, _repository, _service = _workflow()
    recent = _result()

    assert workflow.select_recent(0, (recent,)).detection is recent
    assert workflow.select_recent(-1, (recent,)).handled is False
    assert workflow.select_recent(1, (recent,)).handled is False


@pytest.mark.parametrize(
    ("latitude", "longitude", "message"),
    (
        ("north", "12.5", "Coordinate non valide."),
        ("91", "12.5", "Coordinate fuori intervallo."),
        ("41.9", "181", "Coordinate fuori intervallo."),
        ("nan", "12.5", "Coordinate fuori intervallo."),
    ),
)
def test_manual_coordinates_return_explicit_validation_errors(
    latitude: str,
    longitude: str,
    message: str,
) -> None:
    workflow, _repository, service = _workflow()

    outcome = workflow.set_manual(latitude, longitude, "Rome")

    assert outcome.handled is True
    assert outcome.detection is None
    assert outcome.message == message
    service.from_manual_coordinates_result.assert_not_called()


def test_manual_coordinates_accept_decimal_commas_and_default_label() -> None:
    workflow, _repository, service = _workflow()
    detected = _result(provider="manual_coordinates")
    service.from_manual_coordinates_result.return_value = detected

    outcome = workflow.set_manual("41,9", "12,5", "  ")

    assert outcome.detection is detected
    service.from_manual_coordinates_result.assert_called_once_with(
        41.9,
        12.5,
        label="Coordinate manuali",
    )


def test_system_detection_returns_fallback_offer_instead_of_exception() -> None:
    workflow, _repository, service = _workflow()
    service.detect_system_location.side_effect = LocationUnavailableError(
        reason="permission denied"
    )

    outcome = workflow.detect_system()

    assert outcome.handled is True
    assert outcome.detection is None
    assert outcome.offer_online_fallback is True
    assert "posizione approssimata online" in outcome.message
    assert outcome.failure is not None
    assert outcome.failure.provider == "system"
    assert outcome.failure.reason == "permission denied"


def test_online_detection_returns_consent_and_failure_metadata() -> None:
    workflow, _repository, service = _workflow()
    detected = _result(provider="ip_geolocation")
    service.detect_ip_location.return_value = detected

    success = workflow.detect_online()

    assert success.detection is detected
    assert success.remember_online_consent is True
    service.detect_ip_location.assert_called_once_with(allow_online=True)

    service.detect_ip_location.side_effect = LocationUnavailableError(
        reason="network unavailable"
    )
    failure = workflow.detect_online()
    assert failure.detection is None
    assert failure.message == APPROXIMATE_LOCATION_UNAVAILABLE_MESSAGE
    assert failure.offer_online_fallback is None
    assert failure.failure is not None
    assert failure.failure.provider == "approximate_online"


def test_startup_system_success_does_not_read_online_or_persisted_fallbacks() -> None:
    workflow, _repository, service = _workflow()
    detected = _result(provider="windows_precise")
    service.detect_system_location.return_value = detected
    stored, load_saved, load_cached = _stored_inputs()

    outcome = workflow.resolve_startup(
        StartupLocationInputs(
            StartupLocationPreferences(
                auto_detect_location_on_startup=True,
                allow_approximate_online_location=True,
                use_system_location_on_startup=True,
            ),
            stored,
        )
    )

    assert outcome.detection is detected
    assert outcome.persist is True
    assert outcome.failures == ()
    service.detect_ip_location.assert_not_called()
    load_saved.assert_not_called()
    load_cached.assert_not_called()


def test_startup_falls_back_from_system_to_online_and_reports_first_failure() -> None:
    workflow, _repository, service = _workflow()
    online = _result(provider="ip_geolocation")
    service.detect_system_location.side_effect = LocationUnavailableError(
        reason="service disabled"
    )
    service.detect_ip_location.return_value = online
    stored, load_saved, load_cached = _stored_inputs()

    outcome = workflow.resolve_startup(
        StartupLocationInputs(
            StartupLocationPreferences(
                auto_detect_location_on_startup=True,
                allow_approximate_online_location=True,
                use_system_location_on_startup=True,
            ),
            stored,
        )
    )

    assert outcome.detection is online
    assert outcome.persist is True
    assert [(item.provider, item.reason) for item in outcome.failures] == [
        ("system", "service disabled")
    ]
    load_saved.assert_not_called()
    load_cached.assert_not_called()


def test_startup_uses_saved_location_after_provider_failures_without_cache_read() -> None:
    workflow, _repository, service = _workflow()
    saved = _result("Milan")
    service.detect_system_location.side_effect = LocationUnavailableError(
        reason="service disabled"
    )
    service.detect_ip_location.side_effect = LocationUnavailableError(
        reason="network unavailable"
    )
    stored, load_saved, load_cached = _stored_inputs(saved=saved)

    outcome = workflow.resolve_startup(
        StartupLocationInputs(
            StartupLocationPreferences(
                auto_detect_location_on_startup=True,
                allow_approximate_online_location=True,
                use_system_location_on_startup=True,
            ),
            stored,
        )
    )

    assert outcome.detection is saved
    assert outcome.persist is False
    assert outcome.message == "Posizione salvata caricata: Milan."
    assert [item.provider for item in outcome.failures] == [
        "system",
        "approximate_online",
    ]
    load_saved.assert_called_once_with()
    load_cached.assert_not_called()


def test_stored_resolution_skips_invalid_saved_result_and_uses_cache() -> None:
    workflow, _repository, _service = _workflow()
    invalid_saved = _result("Invalid", timezone="")
    cached = _result("Bologna", provider="cached")
    stored, load_saved, load_cached = _stored_inputs(invalid_saved, cached)

    outcome = workflow.resolve_stored(stored)

    assert outcome is not None
    assert outcome.detection is cached
    assert outcome.persist is False
    assert outcome.message == "Ultima posizione caricata: Bologna."
    load_saved.assert_called_once_with()
    load_cached.assert_called_once_with()


def test_startup_without_any_location_returns_configuration_message() -> None:
    workflow, _repository, _service = _workflow()
    stored, _load_saved, _load_cached = _stored_inputs()

    outcome = workflow.resolve_startup(
        StartupLocationInputs(StartupLocationPreferences(), stored)
    )

    assert outcome.detection is None
    assert outcome.persist is False
    assert outcome.message == (
        "Configura una località per ottenere meteo e cielo locale."
    )


def test_recent_locations_are_valid_ordered_and_deduplicated() -> None:
    workflow, _repository, _service = _workflow()
    active = _result("Rome")
    duplicate_saved = _result("Rome", latitude=41.9004, longitude=12.5004)
    cached = _result("Milan", provider="cached")
    stored, _load_saved, _load_cached = _stored_inputs(duplicate_saved, cached)

    recent = workflow.recent_results(active, stored)

    assert recent == (active, cached)


@pytest.mark.parametrize(
    ("result", "expected"),
    (
        (_result(), "Posizione impostata su Rome, Italy."),
        (
            _result(provider="manual_coordinates"),
            "Coordinate impostate: 41,9000, 12,5000.",
        ),
        (
            _result(provider="mpc_observatory", message="MPC selected"),
            "MPC selected",
        ),
        (
            _result(provider="ip_geolocation", source="test cached"),
            "Ultima posizione caricata: Rome.",
        ),
        (
            _result(provider="ip_geolocation"),
            "Posizione approssimata rilevata tramite connessione internet: "
            "Rome, Italy. La precisione può essere limitata.",
        ),
        (
            _result(provider="windows_precise"),
            "Posizione di sistema acquisita: Rome, Italy.",
        ),
        (
            _result(country="", provider="geoclue2"),
            "Posizione di sistema acquisita.",
        ),
        (
            _result(provider="custom", message="Custom provider"),
            "Custom provider",
        ),
    ),
)
def test_result_messages_preserve_provider_specific_copy(
    result: LocationDetectionResult,
    expected: str,
) -> None:
    assert LocationCommandWorkflow.result_message(result) == expected


def test_result_validation_requires_timezone_and_bounded_coordinates() -> None:
    assert LocationCommandWorkflow.result_has_valid_location(_result()) is True
    assert (
        LocationCommandWorkflow.result_has_valid_location(_result(timezone=""))
        is False
    )
    assert (
        LocationCommandWorkflow.result_has_valid_location(_result(latitude=91))
        is False
    )
    assert LocationCommandWorkflow.result_has_valid_location(None) is False
