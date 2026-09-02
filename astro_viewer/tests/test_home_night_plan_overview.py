"""Protect the compact, score-free lower-Home night-plan read model."""

from __future__ import annotations

from dataclasses import replace

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
    assert payload["alternatives"]["title"] == "Oggetti compatibili con l'occhio nudo stasera"
    assert payload["alternatives"]["subtitle"] == (
        "Geometria favorevole, ma la sessione non è consigliata"
    )


def test_missing_profile_name_uses_default_while_naked_eye_remains_the_mode() -> None:
    payload = _build(
        session=_session("unavailable"),
        active_profile={},
        assigned_equipment=[],
    )

    assert payload["profile"]["name"] == "Default"
    assert payload["profile"]["summary"] == "Profilo attivo: Default  ·  occhio nudo"


def test_alternatives_contract_keeps_full_rows_without_legacy_scores() -> None:
    payload = _build(
        session=_session("recommended"),
        assigned_equipment=[{"kind": "telescope"}],
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


def test_naked_eye_profile_hides_targets_requiring_an_optical_instrument() -> None:
    naked_eye_model = replace(
        _setup_model(),
        object_id="mars",
        name="Marte",
        equipment_type="NakedEye",
        setup_type="naked_eye",
        recommendation_state="naked_eye",
        requires_optical_instrument=False,
    )
    optical_model = replace(
        _setup_model(),
        object_id="messier-31",
        name="M31",
        recommendation_state="requires_optical_instrument",
        requires_optical_instrument=True,
    )

    payload = _build(
        session=_session("recommended"),
        assigned_equipment=[],
        alternatives=[
            _alternative("mars", "Marte", "Pianeta", "planet"),
            _alternative("messier-31", "M31", "Spiral Galaxy", "deep_sky"),
        ],
        setup_models_by_object_id={
            "mars": naked_eye_model,
            "messier-31": optical_model,
        },
    )

    alternatives = payload["alternatives"]
    assert alternatives["title"] == "Altri oggetti compatibili con l'occhio nudo"
    assert alternatives["totalCount"] == 1
    assert alternatives["planetCount"] == 1
    assert alternatives["deepSkyCount"] == 0
    assert [item["objectId"] for item in alternatives["items"]] == ["mars"]


def test_overview_deduplicates_plan_alternatives_and_equipment_counts() -> None:
    plan = _plan_item()
    duplicate_alternative = _alternative(
        "messier-31",
        "M31 duplicate",
        "Spiral Galaxy",
        "deep_sky",
    )
    duplicate_alternative["id"] = " MESSIER-31 "

    payload = _build(
        session=_session("recommended"),
        night_plan=[plan, plan],
        assigned_equipment=[
            {"kind": "telescope", "id": "scope-a"},
            {"kind": "TELESCOPE", "id": " SCOPE-A "},
            {"kind": "eyepiece", "id": "scope-a"},
            {"kind": "eyepiece", "id": "ep-1"},
            {"kind": "eyepiece", "id": "EP-1"},
        ],
        alternatives=[
            _alternative("messier-31", "M31", "Spiral Galaxy", "deep_sky"),
            duplicate_alternative,
        ],
    )

    assert len(payload["plan"]["items"]) == 1
    assert payload["alternatives"]["totalCount"] == 1
    assert payload["profile"]["telescopeCount"] == 1
    assert payload["profile"]["eyepieceCount"] == 2


def _build(
    *,
    session: dict[str, object],
    assigned_equipment: list[dict[str, object]],
    active_profile: dict[str, object] | None = None,
    alternatives: list[dict[str, object]] | None = None,
    night_plan: list[NightPlanItem] | None = None,
    setup_models_by_object_id: dict[str, EquipmentSetupReadModel] | None = None,
) -> dict[str, object]:
    plan = _plan_item()
    return HomeNightPlanOverviewService().build(
        session=session,
        night_plan=[plan] if night_plan is None else night_plan,
        target_payloads_by_id={"messier-42": {"type": "Diffuse Nebula"}},
        setup_models_by_object_id=(
            {"messier-42": _setup_model()}
            if setup_models_by_object_id is None
            else setup_models_by_object_id
        ),
        alternatives=alternatives or [],
        active_profile=(
            {"profile_name": "Serate urbane"}
            if active_profile is None
            else active_profile
        ),
        assigned_equipment=assigned_equipment,
        loading=False,
        sky_quality_warning="",
    )


def _plan_item() -> NightPlanItem:
    return NightPlanItem(
        time_label="23:30",
        object_id="messier-42",
        name="M42",
        score=91,
        difficulty="Media",
        setup="Mak 127 + 16 mm",
        direction="Sud",
        image="images/m42.png",
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
        role_code="recommended",
        role="Consigliato",
        label="16 mm",
        detail_label="16 mm",
        display_label="16 mm",
        suggested_position="",
        magnification="94x",
        true_field="0.7 gradi",
        exit_pupil="1.4 mm",
        exit_pupil_available=True,
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
        recommendation_state="ready",
        requires_optical_instrument=True,
        selection_score=90,
    )
