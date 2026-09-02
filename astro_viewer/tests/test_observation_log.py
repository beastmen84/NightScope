"""Protect observation validation, persistence, summaries, and presentation rows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from astro_viewer.app.database.bootstrap import initialize_database
from astro_viewer.app.database.observation_repository import ObservationRepository
from astro_viewer.app.services.observation_log_service import (
    ObservationLogService,
    ObservationLogValidationError,
)


def test_repository_supports_complete_crud_without_result_limit(tmp_path: Path) -> None:
    database_path = tmp_path / "nightscope.db"
    schema_path = Path(__file__).resolve().parents[1] / "data" / "schema.sql"
    initialize_database(database_path, schema_path)
    repository = ObservationRepository(database_path)

    inserted_ids = [
        repository.add(
            f"2026-07-{day:02d}T22:00",
            f"M{day}",
            "Roma",
            "Dobson",
            "10 mm",
            4,
            f"Nota {day}",
        )
        for day in range(1, 16)
    ]

    assert len(repository.list_all()) == 15
    assert repository.update(
        inserted_ids[0],
        "2026-07-01T23:00",
        "M1",
        "Milano",
        "Newton",
        "8 mm",
        5,
        "Aggiornata",
    )
    updated = next(item for item in repository.list_all() if item["id"] == inserted_ids[0])
    assert updated["location"] == "Milano"
    assert updated["rating"] == 5
    assert repository.delete(inserted_ids[-1])
    assert len(repository.list_all()) == 14
    assert not repository.update(999999, "2026-07-01", "M1", "", "", "", 1, "")
    assert not repository.delete(999999)


def test_service_normalizes_and_presents_observation_entries() -> None:
    service = ObservationLogService()
    now = datetime(2026, 7, 13, 23, 0, tzinfo=ZoneInfo("Europe/Rome"))

    values = service.normalize(
        date_text="2026-07-13",
        time_text="22:15",
        object_name="  M42 ",
        location=" Roma ",
        telescope=" Dobson ",
        eyepiece=" 10 mm ",
        rating=5,
        notes="  Ottimo contrasto ",
        now=now,
    )
    entry = service.build_entries([{"id": 7, **values}])[0]
    summary = service.build_summary([{"id": 7, **values}])

    assert values["date"] == "2026-07-13T22:15"
    assert entry["dateLabel"] == "13/07/2026 22:15"
    assert entry["setupLabel"] == "Dobson / 10 mm"
    assert entry["ratingLabel"] == "5/5"
    assert "ottimo contrasto" in entry["searchText"]
    assert summary == {
        "total": 1,
            "uniqueObjects": 1,
            "averageRating": 5.0,
            "averageRatingLabel": "5,0",
            "latestLabel": "13/07/2026 22:15",
        }


@pytest.mark.parametrize(
    ("date_text", "time_text", "object_name", "rating", "message"),
    [
        ("13/07/2026", "22:00", "M42", 4, "formati"),
        ("2026-07-14", "22:00", "M42", 4, "effettuate"),
        ("2026-07-13", "22:00", "", 4, "oggetto"),
        ("2026-07-13", "22:00", "M42", 0, "compresa"),
    ],
)
def test_service_rejects_invalid_log_values(
    date_text: str,
    time_text: str,
    object_name: str,
    rating: int,
    message: str,
) -> None:
    service = ObservationLogService()
    with pytest.raises(ObservationLogValidationError, match=message):
        service.normalize(
            date_text=date_text,
            time_text=time_text,
            object_name=object_name,
            location="",
            telescope="",
            eyepiece="",
            rating=rating,
            notes="",
            now=datetime(2026, 7, 13, 23, 0),
        )


def test_observation_log_qml_uses_crud_contract_and_navigation_order() -> None:
    ui_dir = Path(__file__).resolve().parents[1] / "app" / "ui"
    main_qml = (ui_dir / "main.qml").read_text(encoding="utf-8")
    page_qml = (ui_dir / "pages" / "ObservationLogPage.qml").read_text(encoding="utf-8")

    assert main_qml.index('text: qsTr("Calendario")') < main_qml.index(
        'text: qsTr("Log Osservazioni")'
    )
    assert main_qml.index('text: qsTr("Log Osservazioni")') < main_qml.index(
        'text: qsTr("Meteo")'
    )
    assert 'window.currentPage === "observationLog"' in main_qml
    assert "controller.observationLog" in page_qml
    assert "controller.addObservation" in page_qml
    assert "controller.updateObservation" in page_qml
    assert "controller.deleteObservation" in page_qml
    assert "observationHistory" not in page_qml
