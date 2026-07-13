from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from astro_viewer.app.astronomy.engine import ObserverLocation
from astro_viewer.app.astronomy.skyfield_engine import (
    CALENDAR_EVENT_HORIZON_DAYS,
    PLANETARY_CONJUNCTION_MAX_SEPARATION_DEG,
    SkyfieldAstronomyEngine,
)
from astro_viewer.app.models.equipment import Eyepiece, Telescope
from astro_viewer.app.models.observing import AstronomicalEvent, CelestialObject
from astro_viewer.app.services.calendar_overview import CalendarOverviewService
from astro_viewer.app.viewmodels.app_controller import AppController


ZONE = ZoneInfo("Africa/Addis_Ababa")
NOW = datetime(2026, 7, 11, 12, 0, tzinfo=ZONE)
LOCATION = ObserverLocation(
    "Addis Ababa",
    "Ethiopia",
    9.03,
    38.74,
    "Africa/Addis_Ababa",
)


def test_skyfield_calendar_keeps_every_event_in_the_annual_horizon() -> None:
    engine = SkyfieldAstronomyEngine(Path(__file__).resolve().parents[1] / "data", None)
    engine._now = lambda _location: NOW
    try:
        events = engine.upcoming_events(LOCATION)
    finally:
        engine.close()

    counts = Counter(event.event_type for event in events)
    event_datetimes = [datetime.fromisoformat(event.event_at) for event in events]

    assert len(events) > 18
    assert counts["Luna"] >= 48
    assert counts["Opposizione"] >= 4
    assert counts["Congiunzione planetaria"] >= 1
    assert counts["Congiunzione solare"] >= 4
    assert counts["Sciame meteorico"] == 10
    assert counts["Eclissi"] >= 1
    assert event_datetimes == sorted(event_datetimes)
    assert len({event.id.strip().casefold() for event in events}) == len(events)
    assert all(0 <= (event_at.date() - NOW.date()).days <= CALENDAR_EVENT_HORIZON_DAYS for event_at in event_datetimes)


def test_skyfield_calendar_exposes_event_specific_local_visibility() -> None:
    engine = SkyfieldAstronomyEngine(Path(__file__).resolve().parents[1] / "data", None)
    engine._now = lambda _location: NOW
    try:
        events = engine.upcoming_events(LOCATION)
    finally:
        engine.close()

    opposition = next(event for event in events if event.event_type == "Opposizione")
    solar_conjunction = next(
        event for event in events if event.event_type == "Congiunzione solare"
    )
    planetary_conjunction = next(
        event
        for event in events
        if event.event_type == "Congiunzione planetaria" and event.observing_window
    )
    eclipse = next(event for event in events if event.event_type == "Eclissi")

    assert opposition.observing_window
    assert opposition.visibility_state == "visible"
    assert solar_conjunction.visibility_state == "not_visible"
    assert solar_conjunction.observing_window == ""
    assert "con il Sole" in solar_conjunction.title
    assert planetary_conjunction.visibility_state in {"visible", "check"}
    assert len(planetary_conjunction.target_object_ids) == 2
    assert 0 < planetary_conjunction.angular_separation_deg <= (
        PLANETARY_CONJUNCTION_MAX_SEPARATION_DEG
    )
    assert eclipse.timing_label == "Massimo dell'eclissi"
    assert eclipse.visibility_state in {"visible", "daylight", "below_horizon"}
    assert eclipse.visibility_detail
    if eclipse.visibility_state != "visible":
        assert eclipse.observing_window == ""


def test_calendar_overview_is_score_free_and_does_not_cut_items() -> None:
    events = [
        _event(
            event_id="moon-new",
            title="Luna nuova",
            event_type="Luna",
            event_at="2026-07-14T12:43:00+03:00",
            usefulness=95,
            visibility_state="favorable",
            visibility_label="Cielo profondo favorito",
        ),
        _event(
            event_id="jupiter-conjunction",
            title="Giove in congiunzione con il Sole",
            event_type="Congiunzione solare",
            event_at="2026-07-29T10:00:00+03:00",
            usefulness=38,
            visibility_state="not_visible",
            visibility_label="Non visibile nella notte",
        ),
        _event(
            event_id="saturn-opposition",
            title="Saturno in opposizione",
            event_type="Opposizione",
            event_at="2026-10-04T22:00:00+03:00",
            usefulness=92,
            visibility_state="visible",
            visibility_label="Visibile nella notte",
        ),
    ]

    overview = CalendarOverviewService().build(
        events=[event.to_qml() for event in events],
        now=NOW,
        has_configured_equipment=False,
    )

    assert overview["schemaVersion"] == "calendar_overview_v2"
    assert overview["horizonDays"] == 365
    assert overview["totalCount"] == 3
    assert [item["id"] for item in overview["items"]] == [
        "moon-new",
        "jupiter-conjunction",
        "saturn-opposition",
    ]
    assert all("usefulness" not in item for item in overview["items"])
    assert overview["items"][0]["priorityLabel"] == "In evidenza"
    assert overview["items"][1]["visibilityLabel"] == "Non visibile nella notte"
    assert overview["counts"]["solarConjunctions"] == 1
    assert overview["counts"]["planetaryConjunctions"] == 0
    assert [item["id"] for item in overview["homeItems"]] == [
        "moon-new",
        "saturn-opposition",
    ]


def test_calendar_counts_event_and_participant_ids_once() -> None:
    event = _event(
        event_id="mars-jupiter-conjunction",
        title="Marte e Giove in congiunzione",
        event_type="Congiunzione planetaria",
        event_at="2026-08-14T22:00:00+03:00",
        usefulness=80,
        visibility_state="visible",
        visibility_label="Visibile nella notte",
    ).to_qml()
    event["targetObjectId"] = "mars"
    event["targetObjectIds"] = ["mars", " MARS ", "jupiter"]
    event["targetObjects"] = [
        {"id": "mars", "name": "Marte"},
        {"id": " MARS ", "name": "Marte duplicate"},
        {"id": "jupiter", "name": "Giove"},
    ]
    duplicate = dict(event)
    duplicate["id"] = " MARS-JUPITER-CONJUNCTION "
    out_of_range_duplicate = dict(event)
    out_of_range_duplicate["eventAt"] = "2025-08-14T22:00:00+03:00"

    overview = CalendarOverviewService().build(
        events=[out_of_range_duplicate, event, duplicate],
        now=NOW,
        has_configured_equipment=False,
    )

    assert overview["totalCount"] == 1
    assert overview["counts"]["planetaryConjunctions"] == 1
    assert overview["items"][0]["targetObjectIds"] == ["mars", "jupiter"]
    assert [item["id"] for item in overview["items"][0]["targetObjects"]] == [
        "mars",
        "jupiter",
    ]


def test_calendar_highlights_balance_priority_with_local_visibility() -> None:
    events = [
        _event(
            event_id="moon-new",
            title="Luna nuova",
            event_type="Luna",
            event_at="2026-07-14T12:43:00+03:00",
            usefulness=95,
            visibility_state="favorable",
            visibility_label="Cielo profondo favorito",
        ),
        _event(
            event_id="partial-eclipse",
            title="Eclissi lunare parziale",
            event_type="Eclissi",
            event_at="2026-07-16T07:12:00+03:00",
            usefulness=86,
            visibility_state="below_horizon",
            visibility_label="Massimo sotto l'orizzonte",
        ),
        _event(
            event_id="meteor-shower",
            title="Delta Aquaridi",
            event_type="Sciame meteorico",
            event_at="2026-07-18T00:00:00+03:00",
            usefulness=78,
            visibility_state="check",
            visibility_label="Da verificare",
        ),
        _event(
            event_id="first-quarter",
            title="Primo quarto",
            event_type="Luna",
            event_at="2026-07-20T20:00:00+03:00",
            usefulness=68,
            visibility_state="visible",
            visibility_label="Visibile all'istante",
        ),
    ]

    overview = CalendarOverviewService().build(
        events=[event.to_qml() for event in events],
        now=NOW,
        has_configured_equipment=False,
    )

    assert [item["id"] for item in overview["highlights"]] == [
        "moon-new",
        "meteor-shower",
        "first-quarter",
    ]


def test_calendar_event_copy_is_compact_and_visibility_aware() -> None:
    shower = _event(
        event_id="meteor-shower",
        title="Delta Aquaridi",
        event_type="Sciame meteorico",
        event_at="2026-07-18T00:00:00+03:00",
        usefulness=78,
        visibility_state="check",
        visibility_label="Da verificare",
    ).to_qml()
    shower["timingKind"] = "window"
    shower["best_time"] = "Dopo mezzanotte"
    shower["observingWindow"] = "Dopo mezzanotte"
    eclipse = _event(
        event_id="partial-eclipse",
        title="Eclissi lunare parziale",
        event_type="Eclissi",
        event_at="2026-07-20T07:12:00+03:00",
        usefulness=86,
        visibility_state="below_horizon",
        visibility_label="Massimo sotto l'orizzonte",
    ).to_qml()
    eclipse["observingWindow"] = ""
    solar = _event(
        event_id="jupiter-solar-conjunction",
        title="Giove in congiunzione con il Sole",
        event_type="Congiunzione solare",
        event_at="2026-07-29T15:17:00+03:00",
        usefulness=20,
        visibility_state="not_visible",
        visibility_label="Non osservabile",
    ).to_qml()
    solar["observingWindow"] = ""

    overview = CalendarOverviewService().build(
        events=[shower, eclipse, solar],
        now=NOW,
        has_configured_equipment=True,
    )
    items = {item["id"]: item for item in overview["items"]}

    assert items["meteor-shower"]["compactTimingValue"] == "Notte"
    assert "massimo non è osservabile" in items["partial-eclipse"]["setupText"]
    assert "fasi" in items["partial-eclipse"]["whyText"]
    assert "Nessun setup osservativo" in items["jupiter-solar-conjunction"]["setupText"]
    assert any("Non puntare" in tip for tip in items["jupiter-solar-conjunction"]["tips"])


def test_calendar_qml_consumes_the_annual_score_free_contract() -> None:
    ui_dir = Path(__file__).resolve().parents[1] / "app" / "ui"
    calendar_qml = (ui_dir / "pages" / "CalendarPage.qml").read_text(encoding="utf-8")
    event_row_qml = (ui_dir / "components" / "EventRow.qml").read_text(encoding="utf-8")
    event_detail_qml = (ui_dir / "pages" / "EventDetailPage.qml").read_text(encoding="utf-8")
    home_qml = (ui_dir / "pages" / "HomePage.qml").read_text(encoding="utf-8")

    assert "controller.calendarOverview" in calendar_qml
    assert "root.calendarEvents" in calendar_qml
    for label in ("30 giorni", "6 mesi", "12 mesi"):
        assert f'"label": qsTr("{label}")' in calendar_qml
        assert f'"value": "{label}"' in calendar_qml
    assert "function periodEvents()" in calendar_qml
    assert "controller.events" not in calendar_qml
    assert "usefulness" not in event_row_qml
    assert "root.eventData.visibilityLabel" in event_row_qml
    assert "root.eventData.compactTimingValue" in event_row_qml
    assert "root.hasDistinctWindow" in event_detail_qml
    assert "root.eventData.separationLabel" in event_detail_qml
    assert "model: root.eventObjects()" in event_detail_qml
    assert "Apri oggetto per stasera" not in event_detail_qml
    assert "controller.calendarOverview" in home_qml
    assert "controller.events" not in home_qml
    assert "root.calendarOverview.homeItems" in home_qml


def test_calendar_future_setup_does_not_consume_current_seeing() -> None:
    controller = AppController.__new__(AppController)
    telescope = Telescope("scope", "Scope", 150, 750, "Newton", "Dobson")
    eyepiece = Eyepiece("ep", "10 mm", 10, 60)
    controller._equipment_service = Mock()
    controller._equipment_service.suggest_for_profile.return_value = {
        "setupText": "Scope + 10 mm",
    }
    controller._active_profile_telescopes = lambda: [telescope]
    controller._active_profile_binoculars = lambda: []
    controller._active_profile_eyepieces = lambda: [eyepiece]
    controller._active_profile_barlows = lambda: []
    controller._seeing_transparency = object()
    controller._sky_quality = object()

    setup = controller._calendar_profile_setup(_target(), "Telescopio medio")

    assert setup == "Scope + 10 mm"
    args = controller._equipment_service.suggest_for_profile.call_args.args
    assert args[4] is None
    assert args[5] is controller._sky_quality


def _event(
    *,
    event_id: str,
    title: str,
    event_type: str,
    event_at: str,
    usefulness: int,
    visibility_state: str,
    visibility_label: str,
) -> AstronomicalEvent:
    local_dt = datetime.fromisoformat(event_at)
    return AstronomicalEvent(
        id=event_id,
        title=title,
        event_type=event_type,
        date_label=local_dt.strftime("%d/%m/%Y"),
        best_time=local_dt.strftime("%H:%M"),
        usefulness=usefulness,
        setup="Qualsiasi setup",
        note="Fixture",
        event_at=event_at,
        timing_kind="instant",
        timing_label="Istante evento",
        observing_window="Notte locale",
        visibility_state=visibility_state,
        visibility_label=visibility_label,
        visibility_detail="Dettaglio locale",
    )


def _target() -> CelestialObject:
    return CelestialObject(
        id="saturn",
        name="Saturno",
        object_type="Pianeta",
        image="",
        magnitude="0.7",
        distance="n/d",
        max_altitude="70 gradi",
        direction="Sud",
        best_time="23:00",
        observing_window="20:00 - 05:00",
        notes="Fixture",
        recommended_setup="",
        visibility_class="Pianeta",
        azimuth="180 gradi",
        time_above_horizon="9 h",
    )
