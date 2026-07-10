from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from astro_viewer.app.models.sky import NightPlanItem
from astro_viewer.app.services.equipment_setup_read_model import EquipmentSetupReadModel


HOME_NIGHT_PLAN_OVERVIEW_SCHEMA_VERSION = "home_night_plan_overview_v1"


class HomeNightPlanOverviewService:
    """Builds the stable presentation contract for the lower Home surface."""

    def build(
        self,
        *,
        session: Mapping[str, object],
        night_plan: Sequence[NightPlanItem],
        target_payloads_by_id: Mapping[str, Mapping[str, object]],
        setup_models_by_object_id: Mapping[str, EquipmentSetupReadModel],
        alternatives: Sequence[Mapping[str, object]],
        active_profile: Mapping[str, object],
        assigned_equipment: Sequence[Mapping[str, object]],
        loading: bool,
        sky_quality_warning: str,
    ) -> dict[str, object]:
        profile = _profile_payload(active_profile, assigned_equipment)
        state = _session_state(session)
        plan_items = (
            _plan_items(
                night_plan,
                target_payloads_by_id=target_payloads_by_id,
                setup_models_by_object_id=setup_models_by_object_id,
                telescope_count=int(profile["telescopeCount"]),
            )
            if state == "recommended"
            else []
        )
        return {
            "schemaVersion": HOME_NIGHT_PLAN_OVERVIEW_SCHEMA_VERSION,
            "profile": profile,
            "plan": _plan_payload(session, state=state, items=plan_items, loading=loading),
            "alternatives": _alternatives_payload(
                alternatives,
                state=state,
                loading=loading,
                sky_quality_warning=sky_quality_warning,
            ),
        }


def _profile_payload(
    active_profile: Mapping[str, object],
    assigned_equipment: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    counts = Counter(_text(item, "kind") for item in assigned_equipment)
    telescope_count = counts["telescope"]
    eyepiece_count = counts["eyepiece"]
    barlow_count = counts["barlow"]
    binocular_count = counts["binocular"]
    equipment_parts = [
        part
        for part in (
            _count_label(telescope_count, "telescopio", "telescopi"),
            _count_label(binocular_count, "binocolo", "binocoli"),
            _count_label(eyepiece_count, "oculare", "oculari"),
            _count_label(barlow_count, "Barlow", "Barlow"),
        )
        if part
    ]
    if not equipment_parts:
        equipment_parts.append("occhio nudo")
    name = _text(active_profile, "profile_name") or "Occhio nudo"
    return {
        "name": name,
        "summary": f"Profilo attivo: {name}  ·  {'  ·  '.join(equipment_parts)}",
        "telescopeCount": telescope_count,
        "eyepieceCount": eyepiece_count,
        "barlowCount": barlow_count,
        "binocularCount": binocular_count,
        "hasMultipleTelescopes": telescope_count > 1,
    }


def _plan_payload(
    session: Mapping[str, object],
    *,
    state: str,
    items: list[dict[str, object]],
    loading: bool,
) -> dict[str, object]:
    titles = {
        "pending": "Piano in aggiornamento",
        "recommended": "Piano osservativo consigliato",
        "monitor": "Finestra da monitorare",
        "discouraged": "Sessione sconsigliata",
        "unavailable": "Piano osservativo non disponibile",
    }
    subtitles = {
        "pending": "La sequenza sarà calcolata appena la posizione è disponibile",
        "recommended": "Le quattro opportunità migliori, ordinate per orario",
        "monitor": "Condizioni variabili: nessuna sequenza viene consigliata",
        "discouraged": "Nessun piano consigliato nelle condizioni previste",
        "unavailable": "Servono posizione e condizioni aggiornate",
    }
    if state == "recommended" and not items:
        message = (
            "Aggiornamento del piano osservativo..."
            if loading
            else "Nessun oggetto utile nella finestra notturna."
        )
    elif state == "recommended":
        message = ""
    else:
        message = _text(session, "detail") or _text(session, "description")
    supporting_text = _text(session, "description")
    if supporting_text == message:
        supporting_text = ""
    return {
        "state": state,
        "title": titles[state],
        "subtitle": subtitles[state],
        "badge": _text(session, "badge"),
        "message": message,
        "supportingText": supporting_text,
        "windowLabel": _text(session, "windowLabel"),
        "windowValue": _text(session, "windowValue"),
        "showWindow": state == "monitor" and bool(_text(session, "windowValue")),
        "showsSequence": state == "recommended" and bool(items),
        "items": items,
    }


def _plan_items(
    night_plan: Sequence[NightPlanItem],
    *,
    target_payloads_by_id: Mapping[str, Mapping[str, object]],
    setup_models_by_object_id: Mapping[str, EquipmentSetupReadModel],
    telescope_count: int,
) -> list[dict[str, object]]:
    payload = []
    for sequence, item in enumerate(night_plan[:4], start=1):
        target = target_payloads_by_id.get(item.object_id, {})
        setup_model = setup_models_by_object_id.get(item.object_id)
        payload.append(
            {
                "sequence": sequence,
                "objectId": item.object_id,
                "name": item.name,
                "image": item.image,
                "typeLabel": _localized_type(_text(target, "type")),
                "timeLabel": item.time_label,
                "direction": item.direction,
                "difficulty": item.difficulty,
                "compactSetup": _compact_setup(
                    item.setup,
                    setup_model,
                    include_telescope=telescope_count > 1,
                ),
                "instrumentLabel": _instrument_label(setup_model),
                "usesProfileChoice": telescope_count > 1 and _is_telescope(setup_model),
            }
        )
    return payload


def _alternatives_payload(
    alternatives: Sequence[Mapping[str, object]],
    *,
    state: str,
    loading: bool,
    sky_quality_warning: str,
) -> dict[str, object]:
    items = [_alternative_item(item) for item in alternatives]
    planet_count = sum(item["category"] == "planet" for item in items)
    deep_sky_count = len(items) - planet_count
    titles = {
        "monitor": "Oggetti visibili da monitorare",
        "discouraged": "Oggetti astronomicamente visibili stasera",
    }
    subtitles = {
        "pending": "La lista sarà calcolata appena la posizione è disponibile",
        "recommended": "Fuori dal piano, ordinati per finestra osservativa",
        "monitor": "Visibilità astronomica; verifica le condizioni prima di osservare",
        "discouraged": "Geometria favorevole, ma la sessione non è consigliata",
        "unavailable": "Servono posizione e condizioni aggiornate",
    }
    subtitle = subtitles[state]
    if sky_quality_warning and state in {"recommended", "monitor"}:
        subtitle = sky_quality_warning
    empty_text = (
        "Calcolo della visibilità..."
        if loading or state == "pending"
        else "Nessun altro oggetto utile fuori dal piano."
    )
    return {
        "state": state,
        "title": titles.get(state, "Altri oggetti visibili stasera"),
        "subtitle": subtitle,
        "emptyText": empty_text,
        "totalCount": len(items),
        "planetCount": planet_count,
        "deepSkyCount": deep_sky_count,
        "items": items,
    }


def _alternative_item(item: Mapping[str, object]) -> dict[str, object]:
    category = _text(item, "homeCategory") or (
        "planet" if _text(item, "type").casefold() == "pianeta" else "deep_sky"
    )
    window_label = _text(item, "homeWindowLabel") or _text(item, "homeTimeLabel")
    return {
        "objectId": _text(item, "id"),
        "name": _text(item, "name"),
        "image": _text(item, "image"),
        "category": category,
        "categoryLabel": "Pianeta" if category == "planet" else "Cielo profondo",
        "typeLabel": _localized_type(_text(item, "type")),
        "windowLabel": window_label or "n/d",
        "direction": _text(item, "direction") or "n/d",
        "difficulty": _text(item, "difficulty") or "n/d",
    }


def _compact_setup(
    fallback: str,
    setup_model: EquipmentSetupReadModel | None,
    *,
    include_telescope: bool,
) -> str:
    if setup_model is None:
        return fallback
    if not _is_telescope(setup_model):
        return setup_model.setup_text or fallback

    option = next(
        (candidate for candidate in setup_model.setup_options if candidate.role == "Consigliato"),
        setup_model.setup_options[0] if setup_model.setup_options else None,
    )
    setup_label = option.detail_label if option else setup_model.setup_text
    setup_label = _without_telescope_prefix(setup_label or fallback, setup_model.telescope_name)
    parts = []
    if include_telescope and setup_model.telescope_name:
        parts.append(setup_model.telescope_name)
    if setup_label:
        parts.append(setup_label)
    if option and option.magnification and option.magnification.casefold() not in setup_label.casefold():
        parts.append(option.magnification)
    if (
        option
        and option.barlow
        and option.barlow.casefold() not in {"no", "n/d"}
        and option.barlow.casefold() not in setup_label.casefold()
    ):
        parts.append(option.barlow)
    return "  ·  ".join(dict.fromkeys(parts)) or fallback


def _instrument_label(setup_model: EquipmentSetupReadModel | None) -> str:
    if setup_model is None:
        return ""
    if _is_telescope(setup_model):
        return setup_model.telescope_name
    if setup_model.equipment_type == "Binocular":
        return setup_model.setup_text or "Binocolo"
    if setup_model.equipment_type == "NakedEye" or setup_model.setup_type == "naked_eye":
        return "Occhio nudo"
    return setup_model.telescope_name


def _is_telescope(setup_model: EquipmentSetupReadModel | None) -> bool:
    return bool(
        setup_model
        and (
            setup_model.equipment_type == "Telescope"
            or setup_model.setup_type == "telescope"
        )
    )


def _without_telescope_prefix(value: str, telescope_name: str) -> str:
    prefix = f"{telescope_name} + "
    return value[len(prefix) :] if telescope_name and value.startswith(prefix) else value


def _session_state(session: Mapping[str, object]) -> str:
    state = _text(session, "state")
    return state if state in {"pending", "recommended", "monitor", "discouraged"} else "unavailable"


def _localized_type(value: str) -> str:
    normalized = value.casefold()
    labels = (
        ("milky way star cloud", "Nube stellare della Via Lattea"),
        ("supernova remnant", "Resto di supernova"),
        ("optical double", "Stella doppia ottica"),
        ("asterism", "Asterismo"),
        ("planetary nebula", "Nebulosa planetaria"),
        ("h ii region nebula with cluster", "Regione H II con ammasso"),
        ("h ii region", "Regione H II"),
        ("nebula with cluster", "Nebulosa con ammasso"),
        ("diffuse nebula", "Nebulosa diffusa"),
        ("barred spiral galaxy", "Galassia spirale barrata"),
        ("dwarf elliptical galaxy", "Galassia ellittica nana"),
        ("elliptical galaxy", "Galassia ellittica"),
        ("lenticular galaxy", "Galassia lenticolare"),
        ("spiral galaxy", "Galassia spirale"),
        ("starburst galaxy", "Galassia starburst"),
        ("galaxy", "Galassia"),
        ("globular cluster", "Ammasso globulare"),
        ("open cluster", "Ammasso aperto"),
        ("cluster", "Ammasso"),
        ("nebula", "Nebulosa"),
    )
    if normalized in {"planet", "pianeta"}:
        return "Pianeta"
    for fragment, label in labels:
        if fragment in normalized:
            return label
    return value or "Oggetto"


def _count_label(count: int, singular: str, plural: str) -> str:
    if count <= 0:
        return ""
    return f"{count} {singular if count == 1 else plural}"


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key, "")
    return "" if value is None else str(value)
