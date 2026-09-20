"""Protect screenshot-derived weather, duration, zoom and calendar coherence."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.astronomy.skyfield_engine import SkyfieldAstronomyEngine
from astro_viewer.app.models.equipment import Eyepiece, Telescope
from astro_viewer.app.models.weather import WeatherHour, WeatherSummary
from astro_viewer.app.services.calendar_overview import CalendarOverviewService
from astro_viewer.app.services.equipment_catalog_service import eyepiece_from_catalog_row
from astro_viewer.app.services.equipment_configuration import EquipmentConfigurationService
from astro_viewer.app.services.home_observing_overview import HomeObservingOverviewService, _session_payload
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.weather_presentation import WeatherPresentationService, practical_weather_windows
from astro_viewer.tests.test_recommendation_guidance_audit import START, NIGHT, hour, target, plan
from astro_viewer.tests.test_planner_nsom_service import _inputs, _telescope


WEATHER = WeatherSummary("Scarsa", 34, "Nuvolosità elevata", 81, 16, 5, 92, 14, "",
                         ("Nuvolosità elevata", "umidità elevata"))


def test_cloudy_screenshot_uses_only_the_dawn_opening_and_never_claims_green():
    zone = ZoneInfo("Africa/Addis_Ababa")
    start = datetime(2030, 9, 20, 19, tzinfo=zone)
    night = ObservingNightWindow.bounded(start, start + timedelta(hours=11, minutes=14))
    clouds = (88, 77, 84, 96, 80, 75, 72, 90, 90, 95, 61, 64)
    hours = [WeatherHour((start + timedelta(hours=i)).isoformat(),
                        (start + timedelta(hours=i)).strftime("%H:%M"), cloud, 5, 5, 92, 14)
             for i, cloud in enumerate(clouds)]
    service = WeatherPresentationService(NightPlannerService())
    decision = service.session_decision(WEATHER, hours, night, zone.key)
    digest = service.digest(hours, night, zone.key)
    assert decision.state == "monitor"
    assert digest["bestWindow"] == "05:00 - 06:14"
    assert digest["goodWindows"] == []
    assert "05:00 - 06:14" in digest["usableWindowText"]
    payload = _session_payload(WEATHER, decision, service.blocking_status(WEATHER),
                               suggested_window="05:00–06:14")
    assert payload["badge"] == "Da monitorare"
    assert "Nuvolosità" in payload["limitingFactor"]
    assert "Nessun fattore bloccante" != payload["limitingFactor"]


@pytest.mark.parametrize("score,cloud", [(34, 81), (0, 100), (90, 100)])
def test_no_usable_hour_is_never_a_recommended_session(score, cloud):
    service = WeatherPresentationService(NightPlannerService())
    weather = replace(WEATHER, score_value=score, cloud_cover=cloud)
    hours = [hour(START + timedelta(hours=i), cloud) for i in range(5)]
    assert service.session_decision(weather, hours, NIGHT).state == "discouraged"
    assert service.suggested_observing_window(weather, hours, NIGHT, "UTC") == ""
    assert service.digest(hours, NIGHT, "UTC")["bestWindow"] == "n/d"


def test_missing_hours_is_unavailable_and_clear_hours_can_be_recommended():
    service = WeatherPresentationService(NightPlannerService())
    assert service.session_decision(WEATHER, [], NIGHT).state == "unavailable"
    assert service.session_decision(None, [hour(START)], NIGHT).state == "unavailable"
    good = replace(WEATHER, score_value=90, cloud_cover=10, humidity=50, limiting_factors=())
    assert service.session_decision(good, [hour(START), hour(START + timedelta(hours=1))], NIGHT).state == "recommended"


def test_missing_night_hours_do_not_present_a_stale_weather_summary_as_available():
    service = WeatherPresentationService(NightPlannerService())
    payload = HomeObservingOverviewService().build(
        location_available=True, location_pending=False, weather=WEATHER, weather_available=True,
        seeing=None, sky_quality=None, moon=None, category_scores=None,
        session=service.session_decision(WEATHER, [], NIGHT), blocking=service.blocking_status(WEATHER),
        suggested_window="", wind_label="", category_source="test")
    assert payload["session"]["state"] == "unavailable"
    assert payload["weather"]["available"] is False
    assert payload["weather"]["scoreValue"] is None


@pytest.mark.parametrize("minutes,expected", [(5, False), (14, False), (15, True), (30, True)])
def test_plan_requires_fifteen_minutes_after_the_suggested_time(minutes, expected):
    result = plan([target(start=0, best=0, end=minutes / 60)], [hour(START)])
    assert bool(result) is expected


def test_weather_shift_retains_a_practical_margin_not_the_last_minute():
    result = plan([target(best=2)], [hour(START), hour(START + timedelta(hours=1), 100)])
    assert result[0].observing_at == (START + timedelta(minutes=45)).isoformat()
    assert not plan([target(start=1, best=1, end=1.08)], [hour(START + timedelta(hours=1))])


@pytest.mark.parametrize("minutes,expected", [(5, False), (14, False), (15, True)])
def test_legacy_instant_does_not_advertise_a_five_minute_weather_opening(minutes, expected):
    item = replace(target(), night_eligible=None, observing_start_at="", observing_end_at="",
                   observing_window="", best_time=START.strftime("%H:%M"), best_observing_at="")
    result = NightPlannerService._weather_observing_time(
        item, NIGHT, ((START, START + timedelta(minutes=minutes)),))
    assert (result is not None) is expected


def test_displayed_minute_does_not_precede_partial_minute_visibility():
    item = target(start=0.01, best=0.01, end=1)
    result = NightPlannerService._weather_observing_time(
        item, NIGHT, ((START, START + timedelta(hours=1)),))
    assert result == START + timedelta(minutes=1)


def test_hourly_opening_can_override_a_bad_nightly_average_but_not_bad_hours():
    weather = replace(WEATHER, cloud_cover=95, score_value=20)
    planner = NightPlannerService()
    args = dict(condition_inputs=_inputs(), night_window=NIGHT)
    assert planner.plan([target()], weather, _telescope("scope"), weather_hours=[hour(START)], **args)
    assert not planner.plan([target()], weather, _telescope("scope"), weather_hours=[hour(START, 100)], **args)
    assert not planner.plan([target()], weather, _telescope("scope"), **args)


def test_short_polar_and_ambiguous_weather_windows_are_not_advertised():
    short = ObservingNightWindow.bounded(START, START + timedelta(minutes=5))
    assert not practical_weather_windows([hour(START)], short, "UTC")
    assert not practical_weather_windows([hour(START)], ObservingNightWindow.unavailable(), "UTC")
    for stamp in (datetime(2030, 10, 27, 2), datetime(2030, 3, 31, 2)):
        assert not practical_weather_windows([hour(stamp)], None, "Europe/Rome")
    assert practical_weather_windows([hour(START)], None, "Invalid/Zone")


@pytest.mark.parametrize("focal,barlow,afov", [(8, 1, 68), (12, 1, 63), (16, 1, 58),
                                             (20, 1, 53), (24, 1, 48), (16, 2, 58), (12, 2, 63)])
def test_zoom_nominal_fields_follow_focal_position_from_catalogue(focal, barlow, afov):
    zoom = eyepiece_from_catalog_row(dict(catalog_id="zoom", brand="Baader", model="Hyperion Zoom",
        focal_length_mm=24, apparent_field_deg=60, eyepiece_type="Zoom", min_focal_length_mm=8,
        max_focal_length_mm=24, afov_min=48, afov_max=68, zoom_click_positions_mm="24;20;16;12;8"))
    scope = Telescope("scope", "C6", 150, 1500, "SCT", "AltAz")
    result = EquipmentConfigurationService().telescope_configuration_values(scope, zoom, focal, barlow_multiplier=barlow)
    assert result["magnification"] == 1500 / focal * barlow
    assert result["exit_pupil_mm"] == 150 / result["magnification"]
    assert result["true_field_of_view_deg"] == pytest.approx(afov / result["magnification"])
    assert zoom.to_qml()["afovMin"] == 48
    assert zoom.to_qml()["afovMax"] == 68


@pytest.mark.parametrize("changes", [dict(eyepiece_type="Fixed"), dict(afov_min=None), dict(afov_max=None),
                                    dict(afov_min=float("nan")), dict(afov_max=40),
                                    dict(max_focal_length_mm=8), dict(afov_max=180)])
def test_fixed_and_incomplete_zoom_models_retain_nominal_fallback(changes):
    zoom = Eyepiece("zoom", "Zoom", 24, 60, "Zoom", 8, 24, (), 48, 68)
    assert replace(zoom, **changes).apparent_field_at(8) == 60
    assert zoom.apparent_field_at(1) == 68
    assert zoom.apparent_field_at(40) == 48


@pytest.mark.parametrize("angle,label", [(0, "Nuova"), (45, "Crescente"), (90, "Primo quarto"),
                                        (105.1, "Gibbosa crescente"), (180, "Piena"),
                                        (240, "Gibbosa calante"), (270, "Ultimo quarto"), (315, "Calante")])
def test_moon_labels_do_not_call_a_63_percent_moon_a_quarter(angle, label):
    assert SkyfieldAstronomyEngine._moon_phase_name(angle) == label


def test_calendar_sorts_visible_event_dates_and_flags_analysis_boundary():
    now = datetime(2030, 9, 20, tzinfo=UTC)
    events = [dict(id="opposition", title="Opposition", event_at="2030-11-26T12:00:00+00:00",
                   favorable_periods=(("2030-08-20T12:00:00+00:00", "2031-01-20T12:00:00+00:00"),)),
              dict(id="moon", title="Moon", event_at="2030-09-26T12:00:00+00:00"),
              dict(id="comet", title="Comet", event_at="2030-09-20T20:00:00+00:00",
                   ends_at="2030-12-19T05:00:00+00:00", analysis_end_at="2030-12-19T12:00:00+00:00")]
    result = CalendarOverviewService().build(events=events, now=now, has_configured_equipment=True)
    assert [item["id"] for item in result["homeItems"]] == ["comet", "moon", "opposition"]
    assert "potrebbe proseguire" in result["homeItems"][0]["analysisBoundaryText"]
    assert result["homeItems"][2]["daysUntil"] == 0  # The useful season is already active.


def test_provider_grid_reserves_one_half_width_slot_without_a_visible_placeholder():
    source = (Path(__file__).parents[1] / "app/ui/pages/DataProvidersPage.qml").read_text(encoding="utf-8")
    imo = source[source.index("id: imoCard"):source.index("id: earthdataCard")]
    assert "Layout.columnSpan" not in imo
    assert "providersGrid.columns" in imo
    assert 'objectName: "providerExpansionSpace"' in imo
    assert "visible: providersGrid.columns === 2" in imo
    assert source.count("Layout.preferredWidth: imoCard.Layout.preferredWidth") == 3


def test_observing_image_absorbs_extra_height_instead_of_the_window_card():
    source = (Path(__file__).parents[1] / "app/ui/pages/ObjectDetailPage.qml").read_text(encoding="utf-8")
    image = source[source.index('objectName: "observingImagePanel"'):source.index('objectName: "observingWindowCard"')]
    window = source[source.index('objectName: "observingWindowCard"'):source.index('title: qsTr("Finestra osservativa")')]
    assert "Layout.fillHeight: visible" in image
    assert "observingDetailGrid.columns === 1 ? 420" in image
    assert "Layout.minimumHeight: visible && observingDetailGrid.columns === 1 ? 360 : 0" in image
    assert "observingFactsColumn.implicitHeight" in image
    assert "Math.max(observingWindowCard.implicitHeight, observingWindowCard.Layout.minimumHeight)" in image
    assert "- observingMediaColumn.spacing" in image
    assert "fillMode: Image.PreserveAspectFit" in image
    assert "Layout.fillHeight: false" in window
    assert "Layout.alignment: Qt.AlignTop" in window


def test_calendar_summary_cards_share_height_only_when_side_by_side():
    source = (Path(__file__).parents[1] / "app/ui/pages/CalendarPage.qml").read_text(encoding="utf-8")
    assert source.count("Layout.fillHeight: calendarSummaryGrid.columns === 2") == 2
    assert 'objectName: "calendarHighlightsCard"' in source
    assert 'objectName: "calendarOverviewCard"' in source


def test_home_hides_only_the_redundant_session_peak_and_keeps_adaptive_rows():
    source = (Path(__file__).parents[1] / "app/ui/pages/HomePage.qml").read_text(encoding="utf-8")
    peak = source[source.index('objectName: "homeSessionPeak"'):source.index('text: root.sessionOverview.bestWindowText')]
    assert 'bestWindowText || ""' in peak
    assert "root.sessionOverview.hasGoodWindows" in peak
    assert "root.sessionOverview.bestWindowMatchesGood === true" in peak
    overview = source[source.index("id: topOverview"):source.index("id: skyCompassCard")]
    assert overview.count("Layout.fillHeight: true") == 5
    assert "Layout.rowSpan: 2" in overview


def test_meteor_summary_cards_share_height_only_in_the_two_column_layout():
    source = (Path(__file__).parents[1] / "app/ui/pages/EventDetailPage.qml").read_text(encoding="utf-8")
    assert source.count("Layout.fillHeight: root.isMeteorShower && eventSummaryGrid.columns === 2") == 2
    assert 'objectName: "eventTimingCard"' in source
    assert 'objectName: "eventProfileCard"' in source


def test_home_event_cards_stack_the_date_above_full_width_details():
    source = (Path(__file__).parents[1] / "app/ui/pages/HomePage.qml").read_text(encoding="utf-8")
    cards = source[source.index('objectName: "homeEventCard_"'):]
    assert "Layout.preferredHeight: Math.max(140, homeEventContent.implicitHeight + 20)" in cards
    assert "ColumnLayout {\n                                id: homeEventContent" in cards
    assert "Layout.alignment: Qt.AlignLeft | Qt.AlignTop" in cards
    assert 'objectName: "homeEventDetails_"' in cards
    assert "Layout.preferredWidth: 1" in cards
    assert "onClicked: root.openEvent(modelData.id)" in cards
