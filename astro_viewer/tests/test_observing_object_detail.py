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

    assert payload["schemaVersion"] == "observing_object_detail_v1"
    assert "score" not in payload
    assert "scoreLabel" not in payload
    assert "scoreExplanation" not in payload
    assert "score" not in payload["setupOptions"][0]
    assert payload["geometry"]["windowLabel"] == "21:00 - 02:00"
    assert payload["geometry"]["windowStart"] == "21:00"
    assert payload["geometry"]["windowEnd"] == "02:00"
    assert payload["geometry"]["bestTimeLabel"] == "23:30 notte"
    assert payload["geometry"]["durationText"] == "5 h nella finestra utile, sopra 15 gradi"
    assert payload["geometry"]["showHorizonEvents"] is False
    assert payload["session"]["state"] == "monitor"
    assert payload["evaluation"]["warning"] == "Fattore limitante: nuvolosità"
    assert payload["equipment"]["telescopeName"] == "Newton 200"


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


def test_observing_detail_uses_live_display_target_and_raw_nsom_target() -> None:
    controller = AppController.__new__(AppController)
    selected = _target()
    raw = replace(selected, score=91)
    display = replace(selected, score=63)
    live = replace(display, current_altitude="28.0 gradi", observable_now=True)
    controller._selected_object = selected
    controller._selected_object_source = "observing"
    controller._sky_compass_candidate_snapshot = [live]
    controller._conditioned_home_read_model = [
        SimpleNamespace(
            object_id=selected.id,
            nsom_target_input=raw,
            qml_display_target=display,
        )
    ]

    assert controller._observing_detail_display_target() is live
    assert controller._observing_detail_nsom_target() is raw


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
