from __future__ import annotations

from astro_viewer.app.models.sky import NightPlanItem
from astro_viewer.app.services.equipment_setup_read_model import (
    EquipmentSetupOptionReadModel,
    EquipmentSetupReadModel,
)
from astro_viewer.app.services.home_night_plan_overview import (
    HOME_NIGHT_PLAN_OVERVIEW_SCHEMA_VERSION,
    HomeNightPlanOverviewService,
)


def test_recommended_plan_is_compact_and_identifies_multi_telescope_choice() -> None:
    payload = _build(
        session=_session("recommended"),
        assigned_equipment=[
            {"kind": "telescope"},
            {"kind": "telescope"},
            {"kind": "eyepiece"},
            {"kind": "eyepiece"},
            {"kind": "barlow"},
        ],
        alternatives=[_alternative("mars", "Marte", "Pianeta", "planet")],
    )

    assert payload["schemaVersion"] == HOME_NIGHT_PLAN_OVERVIEW_SCHEMA_VERSION
    assert payload["profile"]["summary"] == (
        "Profilo attivo: Serate urbane  ·  2 telescopi  ·  2 oculari  ·  1 Barlow"
    )
    assert payload["profile"]["hasMultipleTelescopes"] is True
    assert payload["plan"]["showsSequence"] is True
    assert payload["plan"]["title"] == "Piano osservativo consigliato"
    assert len(payload["plan"]["items"]) == 1

    item = payload["plan"]["items"][0]
    assert item["sequence"] == 1
    assert item["compactSetup"] == "Mak 127  ·  16 mm  ·  94x"
    assert item["instrumentLabel"] == "Mak 127"
    assert item["usesProfileChoice"] is True
    assert "score" not in item
    assert "reason" not in item
    assert "equipmentExplanation" not in item


def test_single_telescope_plan_omits_redundant_instrument_name() -> None:
    payload = _build(
        session=_session("recommended"),
        assigned_equipment=[{"kind": "telescope"}, {"kind": "eyepiece"}],
    )

    item = payload["plan"]["items"][0]
    assert item["compactSetup"] == "16 mm  ·  94x"
    assert item["usesProfileChoice"] is False


def test_monitor_state_never_exposes_a_numbered_plan() -> None:
    payload = _build(
        session=_session("monitor"),
        assigned_equipment=[{"kind": "telescope"}],
    )

    assert payload["plan"]["title"] == "Finestra da monitorare"
    assert payload["plan"]["items"] == []
    assert payload["plan"]["showsSequence"] is False
    assert payload["plan"]["showWindow"] is True
    assert payload["plan"]["windowValue"] == "23:00 - 02:00"
    assert payload["alternatives"]["title"] == "Oggetti visibili da monitorare"


def test_discouraged_state_keeps_visibility_separate_from_recommendation() -> None:
    payload = _build(
        session=_session("discouraged"),
        assigned_equipment=[],
        alternatives=[_alternative("messier-31", "M31", "Spiral Galaxy", "deep_sky")],
    )

    assert payload["profile"]["summary"] == "Profilo attivo: Serate urbane  ·  occhio nudo"
    assert payload["plan"]["title"] == "Sessione sconsigliata"
    assert payload["plan"]["items"] == []
    assert payload["alternatives"]["title"] == "Oggetti astronomicamente visibili stasera"
    assert payload["alternatives"]["subtitle"] == (
        "Geometria favorevole, ma la sessione non è consigliata"
    )


def test_alternatives_contract_keeps_full_rows_without_legacy_scores() -> None:
    payload = _build(
        session=_session("recommended"),
        assigned_equipment=[],
        alternatives=[
            _alternative("mars", "Marte", "Pianeta", "planet"),
            _alternative("messier-31", "M31", "Spiral Galaxy", "deep_sky"),
            _alternative("messier-42", "M42", "Diffuse Nebula", "deep_sky"),
        ],
    )

    alternatives = payload["alternatives"]
    assert alternatives["totalCount"] == 3
    assert alternatives["planetCount"] == 1
    assert alternatives["deepSkyCount"] == 2
    assert [item["objectId"] for item in alternatives["items"]] == [
        "mars",
        "messier-31",
        "messier-42",
    ]
    assert alternatives["items"][1]["typeLabel"] == "Galassia spirale"
    assert alternatives["items"][2]["typeLabel"] == "Nebulosa diffusa"
    assert all("score" not in item for item in alternatives["items"])
    assert all("recommendedSetup" not in item for item in alternatives["items"])


def _build(
    *,
    session: dict[str, object],
    assigned_equipment: list[dict[str, object]],
    alternatives: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    plan = NightPlanItem(
        time_label="23:30",
        object_id="messier-42",
        name="M42",
        score=91,
        difficulty="Media",
        setup="Mak 127 + 16 mm",
        direction="Sud",
        image="images/m42.png",
    )
    return HomeNightPlanOverviewService().build(
        session=session,
        night_plan=[plan],
        target_payloads_by_id={"messier-42": {"type": "Diffuse Nebula"}},
        setup_models_by_object_id={"messier-42": _setup_model()},
        alternatives=alternatives or [],
        active_profile={"profile_name": "Serate urbane"},
        assigned_equipment=assigned_equipment,
        loading=False,
        sky_quality_warning="",
    )


def _session(state: str) -> dict[str, object]:
    return {
        "state": state,
        "badge": {
            "recommended": "Consigliata",
            "monitor": "Da monitorare",
            "discouraged": "Sconsigliata",
        }.get(state, "Non disponibile"),
        "detail": "Nuvolosità variabile durante la notte.",
        "description": "Controlla le condizioni prima di uscire.",
        "windowLabel": "Possibile finestra" if state == "monitor" else "Migliore finestra",
        "windowValue": "23:00 - 02:00" if state != "discouraged" else "",
    }


def _alternative(object_id: str, name: str, object_type: str, category: str) -> dict[str, object]:
    return {
        "id": object_id,
        "name": name,
        "image": f"images/{object_id}.png",
        "type": object_type,
        "homeCategory": category,
        "homeWindowLabel": "22:00 - 01:00",
        "direction": "Sud-Est",
        "difficulty": "Media",
        "score": 88,
        "equipmentExplanation": "Testo lungo da non esporre nella tabella.",
    }


def _setup_model() -> EquipmentSetupReadModel:
    option = EquipmentSetupOptionReadModel(
        role="Consigliato",
        label="16 mm",
        detail_label="16 mm",
        display_label="16 mm",
        suggested_position="",
        magnification="94x",
        true_field="0.7 gradi",
        exit_pupil="1.4 mm",
        barlow="No",
        score=90,
        telescope_name="Mak 127",
        equipment_type="Telescope",
    )
    return EquipmentSetupReadModel(
        object_id="messier-42",
        name="M42",
        payload_keys=(),
        best_eyepiece="16 mm",
        suggested_position="",
        barlow="No",
        difficulty="Media",
        alternative="25 mm",
        high_magnification="10 mm",
        wide_field="25 mm",
        setup_text="Mak 127 + 16 mm",
        setup_options=(option,),
        explanation="94x con pupilla 1.4 mm; altezza massima 45 gradi.",
        telescope_id="mak-127",
        telescope_name="Mak 127",
        equipment_type="Telescope",
        setup_type="telescope",
        selection_score=90,
    )
