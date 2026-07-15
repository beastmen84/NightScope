from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.services.equipment_setup_read_model import EquipmentSetupReadModelBuilder
from astro_viewer.app.services.observing_object_detail import ObservingObjectDetailService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_observing_detail_contract_is_score_free_and_distinguishes_window_from_best_time() -> None:
    target = _target()
    setup_model = EquipmentSetupReadModelBuilder().from_suggestion(
        target,
        {
            "setupText": "Newton 200 con 20 mm",
            "setupOptions": [
                {
                    "role": "Consigliato",
                    "displayLabel": "20 mm",
                    "score": 92,
                    "telescopeName": "Newton 200",
                    "equipmentType": "Telescope",
                }
            ],
            "telescopeId": "newton-200",
            "telescopeName": "Newton 200",
            "equipmentType": "Telescope",
            "setupType": "telescope",
        },
    )

    payload = ObservingObjectDetailService().build(
        object_payload={
            **target.to_qml(),
            "homeWindowLabel": "21:00 - 02:00",
            "homeTimeLabel": "23:30 notte",
            "observingStatus": "Meglio più tardi",
            "observingStatusDetail": "Finestra più tardi.",
            "observingReasons": ["Raggiunge una buona altezza."],
        },
        geometry_state="later",
        session={
            "state": "monitor",
            "title": "Sessione da monitorare",
            "badge": "Da monitorare",
            "detail": "Nuvolosità variabile.",
            "limitingFactor": "Fattore limitante: nuvolosità",
        },
        setup_model=setup_model,
        altitude_threshold_deg=15.0,
        is_deep_sky=True,
    )

    assert payload["schemaVersion"] == "observing_object_detail_v3"
    assert "score" not in payload
    assert "scoreLabel" not in payload
    assert "scoreExplanation" not in payload
    assert "score" not in payload["setupOptions"][0]
    assert payload["geometry"]["windowLabel"] == "21:00 - 02:00"
    assert payload["geometry"]["windowStart"] == "21:00"
    assert payload["geometry"]["windowEnd"] == "02:00"
    assert payload["geometry"]["bestTimeLabel"] == "23:30 notte"
    assert payload["geometry"]["durationText"] == "5 h nella finestra utile, sopra 15°"
    assert payload["geometry"]["showHorizonEvents"] is False
    assert payload["session"]["state"] == "monitor"
    assert payload["session"]["badge"] == "Sessione da monitorare"
    assert payload["evaluation"]["warning"] == "Fattore limitante: nuvolosità"
    assert payload["equipment"]["telescopeName"] == "Newton 200"
    assert payload["equipment"]["filterRecommendations"] == {
        "primary": {},
        "optionalColor": {},
    }
    assert payload["equipment"]["reducerRecommendation"] == {}
    assert payload["originMetric"] == {
        "code": "catalogue",
        "label": "Catalogo",
        "value": "Catalogo Messier",
    }


def test_observing_detail_keeps_real_solar_system_distance_semantics() -> None:
    target = replace(_target(), id="moon", distance="384.400 km")
    payload = ObservingObjectDetailService().build(
        object_payload=target.to_qml(),
        geometry_state="observable_now",
        session={"state": "recommended"},
        setup_model=None,
        altitude_threshold_deg=0.0,
        is_deep_sky=False,
    )

    assert payload["originMetric"] == {
        "code": "distance",
        "label": "Distanza",
        "value": "384.400 km",
    }


def test_observing_detail_exposes_only_sanitized_filter_recommendations() -> None:
    payload = ObservingObjectDetailService().build(
        object_payload=_target().to_qml(),
        geometry_state="later",
        session={"state": "monitor"},
        setup_model=None,
        altitude_threshold_deg=15.0,
        is_deep_sky=True,
        filter_recommendations={
            "primary": {
                "applicable": True,
                "available": True,
                "label": "Filtro raccomandato",
                "value": "Astronomik OIII",
                "filterClass": "OIII",
                "filterClassLabel": "OIII",
                "filterId": "catalog-filter-3",
                "internal": "not exposed",
            },
            "optionalColor": {
                "applicable": True,
                "available": False,
                "label": "Filtro colorato opzionale (non disponibile)",
                "value": "Colorato (rosso)",
                "filterClass": "COLOR_RED",
                "filterClassLabel": "Colorato (rosso)",
                "filterId": "",
            },
        },
    )

    recommendations = payload["equipment"]["filterRecommendations"]
    assert recommendations["primary"]["value"] == "Astronomik OIII"
    assert recommendations["primary"]["available"] is True
    assert "internal" not in recommendations["primary"]
    assert recommendations["optionalColor"]["filterClass"] == "COLOR_RED"
    assert recommendations["optionalColor"]["available"] is False


def test_observing_detail_exposes_only_sanitized_reducer_recommendation() -> None:
    payload = ObservingObjectDetailService().build(
        object_payload=_target().to_qml(),
        geometry_state="later",
        session={"state": "monitor"},
        setup_model=None,
        altitude_threshold_deg=15.0,
        is_deep_sky=True,
        reducer_recommendation={
            "applicable": True,
            "available": True,
            "label": "Riduttore fotografico consigliato",
            "value": "Celestron 0.63x",
            "internal": "not exposed",
            "items": [
                {
                    "reducerId": "catalog-reducer-1",
                    "displayLabel": "Celestron 0.63x",
                    "reductionFactor": 0.63,
                    "internal": "not exposed",
                }
            ],
        },
    )

    recommendation = payload["equipment"]["reducerRecommendation"]
    assert recommendation["available"] is True
    assert recommendation["items"] == [
        {
            "reducerId": "catalog-reducer-1",
            "displayLabel": "Celestron 0.63x",
            "reductionFactor": 0.63,
        }
    ]
    assert "internal" not in recommendation


def test_lunar_detail_keeps_phase_fields_and_real_horizon_events() -> None:
    target = replace(
        _target(),
        id="moon",
        name="Luna",
        object_type="Luna",
        rise_time="18:04",
        set_time="06:21",
    )

    payload = ObservingObjectDetailService().build(
        object_payload={
            **target.to_qml(),
            "homeWindowLabel": "19:00 - 05:30",
            "homeTimeLabel": "23:40 notte",
            "observingStatus": "Osservabile ora",
            "observingStatusDetail": "Attualmente in quota utile.",
            "observingReasons": ["Fase lunare favorevole."],
            "moonPhase": "Primo quarto",
            "moonIllumination": "50%",
            "moonCycleDay": "Giorno 7,4 di 29,5",
        },
        geometry_state="observable_now",
        session={
            "state": "recommended",
            "title": "Sessione consigliata",
            "badge": "Consigliata",
            "limitingFactor": "Nessun fattore bloccante",
            "limitingFactorCode": "none",
        },
        setup_model=None,
        altitude_threshold_deg=8.0,
        is_deep_sky=False,
    )

    assert payload["geometry"]["showHorizonEvents"] is True
    assert payload["geometry"]["riseTime"] == "18:04"
    assert payload["geometry"]["setTime"] == "06:21"
    assert payload["moonPhase"] == "Primo quarto"
    assert payload["moonIllumination"] == "50%"
    assert payload["moonCycleDay"] == "Giorno 7,4 di 29,5"
    assert payload["session"]["badge"] == "Sessione consigliata"
    assert payload["evaluation"]["warning"] == ""


def test_observing_detail_qualifies_discouraged_session_badge() -> None:
    payload = ObservingObjectDetailService().build(
        object_payload=_target().to_qml(),
        geometry_state="unavailable",
        session={
            "state": "discouraged",
            "title": "Sessione sconsigliata",
            "badge": "Sconsigliata",
        },
        setup_model=None,
        altitude_threshold_deg=15.0,
        is_deep_sky=True,
    )

    assert payload["session"]["badge"] == "Sessione sconsigliata"


def test_deep_sky_detail_does_not_claim_observable_below_fifteen_degrees() -> None:
    controller = AppController.__new__(AppController)
    zone = ZoneInfo("Africa/Addis_Ababa")
    now = datetime.now(zone)
    controller._observing_night_window = ObservingNightWindow.bounded(
        now - timedelta(hours=1),
        now + timedelta(hours=5),
    )
    controller._zone = lambda: zone
    controller._first_observing_datetime = lambda _value: now + timedelta(hours=1)
    controller._home_window_label = lambda item: item.observing_window
    target = replace(_target(), current_altitude="12.0 gradi", observable_now=False)

    status, detail = controller._observing_status(target)

    assert status != "Osservabile ora"
    assert "Finestra" in detail
    assert controller._observing_altitude_threshold(target) == 15.0


def test_planet_detail_fallback_uses_eight_degree_threshold() -> None:
    controller = AppController.__new__(AppController)
    zone = ZoneInfo("Africa/Addis_Ababa")
    now = datetime.now(zone)
    controller._observing_night_window = ObservingNightWindow.bounded(
        now - timedelta(hours=1),
        now + timedelta(hours=5),
    )
    controller._zone = lambda: zone
    controller._first_observing_datetime = lambda _value: now + timedelta(hours=1)
    controller._home_window_label = lambda item: item.observing_window
    target = replace(
        _target(),
        id="mars",
        object_type="Pianeta",
        current_altitude="9.0 gradi",
        observable_now=None,
    )
    controller._is_solar_system_monthly_visibility_blocked = lambda _item: False

    status, _detail = controller._observing_status(target)

    assert status == "Osservabile ora"
    assert controller._observing_altitude_threshold(target) == 8.0


def test_observing_detail_prefers_live_target_over_conditioned_display_target() -> None:
    controller = AppController.__new__(AppController)
    selected = _target()
    display = replace(selected, score=63)
    live = replace(display, current_altitude="28.0 gradi", observable_now=True)
    controller._selected_object = selected
    controller._selected_object_source = "observing"
    controller._sky_compass_candidate_snapshot = [live]
    controller._conditioned_home_read_model = [
        SimpleNamespace(
            object_id=selected.id,
            qml_display_target=display,
        )
    ]

    assert controller._observing_detail_display_target() is live


def test_catalogue_selection_does_not_use_observing_detail_contract() -> None:
    controller = AppController.__new__(AppController)
    selected = replace(_target(), visibility_class="Catalogo Messier")
    controller._selected_object = selected
    controller._selected_object_source = "catalogue"

    assert controller._observing_detail_display_target() is None


def test_observing_detail_uses_target_specific_telescope() -> None:
    controller = AppController.__new__(AppController)
    selected = Telescope("selected", "Selected 200", 200, 1000, "Newton", "Dobson")
    fallback = Telescope("fallback", "Fallback 80", 80, 600, "Refractor", "Alt-Az")
    controller._equipment_setup_read_models_by_object_id = {
        "messier-M3": SimpleNamespace(
            equipment_type="Telescope",
            telescope_id="selected",
        )
    }
    controller._find_telescope = lambda telescope_id: selected if telescope_id == "selected" else None
    controller._current_telescope = lambda: fallback

    assert controller._detail_telescope_for_target("messier-M3") is selected


def _target() -> CelestialObject:
    return CelestialObject(
        id="messier-M3",
        name="M3",
        object_type="Globular cluster",
        image="",
        magnitude="6.2",
        distance="Catalogo Messier",
        max_altitude="58 gradi",
        direction="Sud",
        best_time="23:30",
        observing_window="21:00 - 02:00",
        notes="Fixture",
        recommended_setup="Newton 200 con 20 mm",
        visibility_class="Telescopio",
        azimuth="180 gradi",
        time_above_horizon="5 h",
        visible=True,
        rise_time="calcolato da finestra",
        set_time="calcolato da finestra",
        culmination_time="23:30",
        current_altitude="12.0 gradi",
        current_azimuth="180.0 gradi",
        score=88,
        score_label="Ottima",
        score_explanation="Legacy score fixture",
        setup_options=[{"role": "Consigliato", "score": 92}],
    )
