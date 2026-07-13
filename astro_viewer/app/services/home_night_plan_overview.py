from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

from astro_viewer.app.models.sky import NightPlanItem
from astro_viewer.app.services.catalogue_presentation import catalogue_object_type_label
from astro_viewer.app.services.direction_presentation import direction_code, direction_label
from astro_viewer.app.services.equipment_setup_read_model import EquipmentSetupReadModel
from astro_viewer.app.services.localization import join_text, presentation_text, tr
from astro_viewer.app.services.nsom_target import unique_targets_by_id


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
    counts = Counter(
        _text(item, "kind").strip().casefold()
        for item in _unique_assigned_equipment(assigned_equipment)
    )
    telescope_count = counts["telescope"]
    eyepiece_count = counts["eyepiece"]
    barlow_count = counts["barlow"]
    binocular_count = counts["binocular"]
    equipment_parts = [
        part
        for part in (
            _telescope_count_label(telescope_count),
            _binocular_count_label(binocular_count),
            _eyepiece_count_label(eyepiece_count),
            _barlow_count_label(barlow_count),
        )
        if part
    ]
    if not equipment_parts:
        equipment_parts.append(tr("occhio nudo"))
    name = _text(active_profile, "profile_name") or tr("Occhio nudo")
    return {
        "name": name,
        "summary": tr(
            "Profilo attivo: {name}  ·  {equipment}",
            name=name,
            equipment=join_text(equipment_parts, "  ·  "),
        ),
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
        "pending": tr("Piano in aggiornamento"),
        "recommended": tr("Piano osservativo consigliato"),
        "monitor": tr("Finestra da monitorare"),
        "discouraged": tr("Sessione sconsigliata"),
        "unavailable": tr("Piano osservativo non disponibile"),
    }
    subtitles = {
        "pending": tr("La sequenza sarà calcolata appena la posizione è disponibile"),
        "recommended": tr("Le quattro opportunità migliori, ordinate per orario"),
        "monitor": tr("Condizioni variabili: nessuna sequenza viene consigliata"),
        "discouraged": tr("Nessun piano consigliato nelle condizioni previste"),
        "unavailable": tr("Servono posizione e condizioni aggiornate"),
    }
    if state == "recommended" and not items:
        message = (
            tr("Aggiornamento del piano osservativo...")
            if loading
            else tr("Nessun oggetto utile nella finestra notturna.")
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
    for sequence, item in enumerate(unique_targets_by_id(night_plan)[:4], start=1):
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
                "directionCode": direction_code(item.direction),
                "direction": direction_label(item.direction),
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
    items = [_alternative_item(item) for item in unique_targets_by_id(alternatives)]
    planet_count = sum(item["category"] == "planet" for item in items)
    deep_sky_count = len(items) - planet_count
    titles = {
        "monitor": tr("Oggetti visibili da monitorare"),
        "discouraged": tr("Oggetti astronomicamente visibili stasera"),
    }
    subtitles = {
        "pending": tr("La lista sarà calcolata appena la posizione è disponibile"),
        "recommended": tr("Fuori dal piano, ordinati per finestra osservativa"),
        "monitor": tr("Visibilità astronomica; verifica le condizioni prima di osservare"),
        "discouraged": tr("Geometria favorevole, ma la sessione non è consigliata"),
        "unavailable": tr("Servono posizione e condizioni aggiornate"),
    }
    subtitle = subtitles[state]
    if sky_quality_warning and state in {"recommended", "monitor"}:
        subtitle = sky_quality_warning
    empty_text = (
        tr("Calcolo della visibilità...")
        if loading or state == "pending"
        else tr("Nessun altro oggetto utile fuori dal piano.")
    )
    return {
        "state": state,
        "title": titles.get(state, tr("Altri oggetti visibili stasera")),
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
        "categoryLabel": tr("Pianeta") if category == "planet" else tr("Cielo profondo"),
        "typeLabel": _localized_type(_text(item, "type")),
        "windowLabel": window_label or tr("n/d"),
        "directionCode": direction_code(_text(item, "direction")),
        "direction": direction_label(_text(item, "direction")),
        "difficulty": _text(item, "difficulty") or tr("n/d"),
    }


def _unique_assigned_equipment(
    assigned_equipment: Sequence[Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    unique: list[Mapping[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for item in assigned_equipment:
        kind = _text(item, "kind").strip().casefold()
        equipment_id = _text(item, "id").strip().casefold()
        if kind and equipment_id:
            key = (kind, equipment_id)
            if key in seen:
                continue
            seen.add(key)
        unique.append(item)
    return tuple(unique)


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
        (candidate for candidate in setup_model.setup_options if candidate.role_code == "recommended"),
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
    return join_text(list(dict.fromkeys(parts)), "  ·  ") if parts else fallback


def _instrument_label(setup_model: EquipmentSetupReadModel | None) -> str:
    if setup_model is None:
        return ""
    if _is_telescope(setup_model):
        return setup_model.telescope_name
    if setup_model.equipment_type == "Binocular":
        return setup_model.setup_text or tr("Binocolo")
    if setup_model.equipment_type == "NakedEye" or setup_model.setup_type == "naked_eye":
        return tr("Occhio nudo")
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
    return catalogue_object_type_label(value) if value else tr("Oggetto")


def _telescope_count_label(count: int) -> str:
    if count <= 0:
        return ""
    return tr("{count} telescopio", count=count) if count == 1 else tr("{count} telescopi", count=count)


def _binocular_count_label(count: int) -> str:
    if count <= 0:
        return ""
    return tr("{count} binocolo", count=count) if count == 1 else tr("{count} binocoli", count=count)


def _eyepiece_count_label(count: int) -> str:
    if count <= 0:
        return ""
    return tr("{count} oculare", count=count) if count == 1 else tr("{count} oculari", count=count)


def _barlow_count_label(count: int) -> str:
    if count <= 0:
        return ""
    return tr("{count} Barlow", count=count)


def _text(payload: Mapping[str, object], key: str) -> str:
    return presentation_text(payload.get(key, ""))
