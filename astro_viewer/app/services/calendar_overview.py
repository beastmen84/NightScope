from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime


CALENDAR_OVERVIEW_SCHEMA_VERSION = "calendar_overview_v2"
CALENDAR_HORIZON_DAYS = 365


class CalendarOverviewService:
    """Builds the score-free presentation contract for Calendar and Home events."""

    def build(
        self,
        *,
        events: Sequence[Mapping[str, object]],
        now: datetime,
        has_configured_equipment: bool,
    ) -> dict[str, object]:
        candidates: list[tuple[datetime, int, dict[str, object]]] = []
        seen_event_ids: set[str] = set()
        for event in events:
            event_at = _event_datetime(event, now)
            if event_at is None:
                continue
            days_until = (event_at.date() - now.date()).days
            if not 0 <= days_until <= CALENDAR_HORIZON_DAYS:
                continue
            event_id = _text(event, "id").casefold()
            if event_id:
                if event_id in seen_event_ids:
                    continue
                seen_event_ids.add(event_id)
            usefulness = _integer(event.get("usefulness"))
            candidates.append(
                (
                    event_at,
                    usefulness,
                    _event_payload(
                        event,
                        event_at=event_at,
                        days_until=days_until,
                        usefulness=usefulness,
                        has_configured_equipment=has_configured_equipment,
                    ),
                )
            )

        candidates.sort(key=lambda candidate: candidate[0])
        items = [candidate[2] for candidate in candidates]
        home_items = [item for item in items if item["type"] != "Congiunzione solare"]
        highlights = [
            candidate[2]
            for candidate in sorted(
                (
                    candidate
                    for candidate in candidates
                    if candidate[2]["daysUntil"] <= 30
                    and candidate[2]["type"] != "Congiunzione solare"
                ),
                key=lambda candidate: (
                    -_highlight_value(
                        candidate[1],
                        str(candidate[2]["visibilityState"]),
                    ),
                    candidate[0],
                ),
            )[:3]
        ]
        counts = Counter(str(item["type"]) for item in items)
        return {
            "schemaVersion": CALENDAR_OVERVIEW_SCHEMA_VERSION,
            "horizonDays": CALENDAR_HORIZON_DAYS,
            "horizonLabel": "Prossimi 365 giorni",
            "totalCount": len(items),
            "items": items,
            "homeItems": home_items,
            "highlights": highlights,
            "counts": {
                "moon": counts["Luna"],
                "oppositions": counts["Opposizione"],
                "planetaryConjunctions": counts["Congiunzione planetaria"],
                "solarConjunctions": counts["Congiunzione solare"],
                "conjunctions": (
                    counts["Congiunzione planetaria"]
                    + counts["Congiunzione solare"]
                ),
                "showers": counts["Sciame meteorico"],
                "eclipses": counts["Eclissi"],
            },
        }


def _event_payload(
    event: Mapping[str, object],
    *,
    event_at: datetime,
    days_until: int,
    usefulness: int,
    has_configured_equipment: bool,
) -> dict[str, object]:
    event_type = _text(event, "type") or _text(event, "event_type")
    title = _text(event, "title")
    date_label = _text(event, "date_label") or event_at.strftime("%d/%m/%Y")
    timing_label = _text(event, "timingLabel") or _text(event, "timing_label") or "Istante evento"
    timing_kind = _text(event, "timingKind") or _text(event, "timing_kind") or "instant"
    timing_value = _text(event, "best_time")
    observing_window = _text(event, "observingWindow") or _text(event, "observing_window")
    visibility_state = (
        _text(event, "visibilityState")
        or _text(event, "visibility_state")
        or "unknown"
    )
    visibility_label = (
        _text(event, "visibilityLabel")
        or _text(event, "visibility_label")
        or "Da verificare"
    )
    visibility_detail = (
        _text(event, "visibilityDetail")
        or _text(event, "visibility_detail")
        or "Visibilità locale non disponibile."
    )
    setup = _profile_setup_text(
        event_type,
        title,
        _text(event, "setup"),
        visibility_state=visibility_state,
        has_configured_equipment=has_configured_equipment,
    )
    angular_separation_deg = _optional_float(
        event.get("angularSeparationDeg", event.get("angular_separation_deg"))
    )
    target_object_ids = _text_list(
        event.get("targetObjectIds", event.get("target_object_ids"))
    )
    primary_target_id = _text(event, "targetObjectId") or _text(
        event,
        "target_object_id",
    )
    normalized_target_ids = {item.casefold() for item in target_object_ids}
    if primary_target_id and primary_target_id.casefold() not in normalized_target_ids:
        target_object_ids.insert(0, primary_target_id)
    priority_state, priority_label = _priority(usefulness)
    return {
        "id": _text(event, "id"),
        "title": title,
        "type": event_type,
        "dateLabel": date_label,
        "eventAt": event_at.isoformat(),
        "daysUntil": days_until,
        "timingKind": timing_kind,
        "timingLabel": timing_label,
        "timingValue": timing_value,
        "compactTimingValue": _compact_timing_value(timing_kind, timing_value),
        "observingWindow": observing_window,
        "visibilityState": visibility_state,
        "visibilityLabel": visibility_label,
        "visibilityDetail": visibility_detail,
        "priorityState": priority_state,
        "priorityLabel": priority_label,
        "setupText": setup,
        "note": _text(event, "note"),
        "targetObjectId": primary_target_id,
        "targetObjectIds": target_object_ids,
        "targetObjects": _mapping_list(event.get("targetObjects")),
        "angularSeparationDeg": angular_separation_deg,
        "separationLabel": _separation_label(angular_separation_deg),
        "whyText": _why_text(
            event_type,
            title,
            _text(event, "note"),
            visibility_state=visibility_state,
        ),
        "tips": _observing_tips(
            event_type,
            title,
            visibility_state=visibility_state,
        ),
        "detailSubtitle": _detail_subtitle(date_label, timing_label, timing_value),
    }


def _event_datetime(event: Mapping[str, object], now: datetime) -> datetime | None:
    value = _text(event, "eventAt") or _text(event, "event_at")
    if value:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=now.tzinfo)
            return parsed.astimezone(now.tzinfo)

    date_label = _text(event, "date_label")
    try:
        parsed = datetime.strptime(date_label, "%d/%m/%Y")
    except ValueError:
        return None
    best_time = _text(event, "best_time")
    if len(best_time) == 5 and best_time[2] == ":":
        try:
            hour, minute = (int(part) for part in best_time.split(":", 1))
            parsed = parsed.replace(hour=hour, minute=minute)
        except ValueError:
            pass
    return parsed.replace(tzinfo=now.tzinfo)


def _profile_setup_text(
    event_type: str,
    title: str,
    setup: str,
    *,
    visibility_state: str,
    has_configured_equipment: bool,
) -> str:
    normalized_title = title.casefold()
    if event_type == "Sciame meteorico":
        return (
            "Il telescopio non serve: osserva a occhio nudo. Un binocolo può essere utile "
            "solo per esplorare il cielo tra una meteora e l'altra."
        )
    if event_type == "Eclissi" and "solare" in normalized_title:
        return (
            "Osserva il Sole solo con filtri solari certificati davanti all'obiettivo. "
            "Non usare oculari o cercatori non filtrati."
        )
    if event_type == "Congiunzione solare":
        return (
            "Nessun setup osservativo: il pianeta è troppo vicino al Sole per "
            "un'osservazione visuale sicura."
        )
    if event_type == "Eclissi":
        if visibility_state != "visible":
            return (
                "Il massimo non è osservabile localmente. Prepara binocolo o basso "
                "ingrandimento solo dopo aver verificato gli orari completi delle fasi."
            )
        return (
            "Osservabile a occhio nudo. Con binocolo o telescopio usa basso "
            "ingrandimento: l'intero disco lunare deve restare nel campo."
        )
    if event_type == "Luna" and "nuova" in normalized_title:
        if not _is_generic_setup(setup):
            return setup
        return (
            "Configura un profilo per consigli più precisi; resta comunque la notte "
            "migliore del mese per galassie, nebulose e ammassi deboli."
        )
    if event_type == "Luna":
        lunar_setup = "Osservabile a occhio nudo o con binocolo." if _is_generic_setup(setup) else setup
        if "primo quarto" in normalized_title or "ultimo quarto" in normalized_title:
            return _append_guidance(
                lunar_setup,
                "Il terminatore evidenzia crateri e rilievi; usa ingrandimenti progressivi.",
            )
        if "piena" in normalized_title:
            return _append_guidance(
                lunar_setup,
                "Usa filtro lunare o ingrandimenti moderati: il disco è molto luminoso.",
            )
        return _append_guidance(
            lunar_setup,
            "Mantieni il disco comodo nel campo e aumenta l'ingrandimento solo con immagine stabile.",
        )
    if event_type == "Opposizione" and setup:
        return _append_guidance(
            setup,
            "Aumenta l'ingrandimento solo se il seeing della notte dell'evento mantiene il pianeta nitido.",
        )
    if event_type in {"Congiunzione", "Congiunzione planetaria"} and setup:
        return _append_guidance(
            setup,
            "La separazione indicata determina se entrambi entrano nello stesso campo.",
        )
    if setup == "Occhio nudo":
        return "Osservabile a occhio nudo"
    if not has_configured_equipment and event_type in {
        "Opposizione",
        "Congiunzione",
        "Congiunzione planetaria",
    }:
        return "Configura un profilo per consigli più precisi."
    if _is_generic_setup(setup):
        return "Configura un profilo per consigli più precisi."
    return setup or "Configura un profilo per consigli più precisi."


def _why_text(
    event_type: str,
    title: str,
    fallback: str,
    *,
    visibility_state: str,
) -> str:
    normalized_title = title.casefold()
    if event_type == "Opposizione":
        return (
            "Il pianeta resta visibile a lungo, diventa più luminoso e permette di "
            "aspettare i momenti di seeing stabile."
        )
    if event_type == "Luna" and "nuova" in normalized_title:
        return (
            "È la finestra con meno luce lunare: riservala a galassie, nebulose e "
            "ammassi deboli che perdono contrasto nelle altre notti."
        )
    if event_type == "Luna" and (
        "primo quarto" in normalized_title or "ultimo quarto" in normalized_title
    ):
        return (
            "Il terminatore attraversa zone ricche di rilievi e mostra più dettaglio "
            "rispetto alla Luna piena."
        )
    if event_type == "Luna" and "piena" in normalized_title:
        return (
            "La Luna piena è facile e luminosa, ma penalizza il cielo profondo debole."
        )
    if event_type == "Luna":
        return "La fase lunare determina il fondo cielo e i dettagli lunari più accessibili."
    if event_type == "Sciame meteorico":
        return (
            "Conta più il cielo buio del telescopio: servono campo ampio, pazienza e "
            "vista adattata al buio."
        )
    if event_type == "Eclissi" and "solare" in normalized_title:
        return "È un evento da pianificare con protezione solare certificata."
    if event_type == "Eclissi":
        if visibility_state != "visible":
            return (
                "Il massimo non è osservabile dalla posizione attuale; le fasi iniziali "
                "o finali possono avere una visibilità diversa e vanno verificate."
            )
        return (
            "È osservabile anche a occhio nudo; binocolo o basso ingrandimento aiutano "
            "a seguire ombra e colore sul disco lunare."
        )
    if event_type == "Congiunzione solare":
        return (
            "È un riferimento effemeride che segna il passaggio del pianeta dalla "
            "visibilità serale a quella mattutina, non un'opportunità visuale."
        )
    if event_type in {"Congiunzione", "Congiunzione planetaria"}:
        return (
            "I due pianeti raggiungono la minima separazione apparente e possono entrare "
            "nello stesso campo con binocolo o bassi ingrandimenti."
        )
    return fallback or "Evento astronomico nell'orizzonte annuale."


def _observing_tips(
    event_type: str,
    title: str,
    *,
    visibility_state: str,
) -> list[str]:
    normalized_title = title.casefold()
    if event_type == "Opposizione":
        return [
            "Usa alti ingrandimenti solo se il seeing lo permette.",
            "Osserva nella finestra locale indicata, quando il pianeta è più alto.",
            "Lascia acclimatare il telescopio prima dei dettagli fini.",
        ]
    if event_type == "Sciame meteorico":
        return [
            "Non serve il telescopio.",
            "Scegli una zona ampia e buia, lontana da luci dirette.",
            "Controlla fase lunare e meteo vicino alla data del massimo.",
            "Osserva a lungo con una sedia reclinabile.",
        ]
    if event_type == "Luna" and "nuova" in normalized_title:
        return [
            "Dai priorità a galassie, nebulose e ammassi deboli.",
            "Evita luci dirette e lascia adattare la vista al buio.",
            "Controlla il meteo quando la data entra nell'orizzonte previsionale.",
        ]
    if event_type == "Luna" and (
        "primo quarto" in normalized_title or "ultimo quarto" in normalized_title
    ):
        return [
            "Osserva lungo il terminatore.",
            "Aumenta l'ingrandimento a piccoli passi.",
            "Usa un filtro lunare se l'immagine è troppo luminosa.",
        ]
    if event_type == "Luna" and "piena" in normalized_title:
        return [
            "Usa filtro lunare o riduci l'ingrandimento.",
            "Evita gli oggetti più deboli del cielo profondo.",
            "Preferisci pianeti brillanti, stelle doppie e osservazione lunare.",
        ]
    if event_type == "Eclissi" and "solare" in normalized_title:
        return [
            "Usa solo filtri solari certificati davanti all'obiettivo.",
            "Non guardare mai il Sole attraverso strumenti non filtrati.",
            "Prepara il setup prima dell'inizio dell'evento.",
        ]
    if event_type == "Eclissi":
        if visibility_state != "visible":
            return [
                "Verifica gli orari completi delle fasi per la tua posizione.",
                "Non considerare il solo massimo come finestra osservativa.",
                "Prepara lo strumento solo se almeno una fase risulta visibile.",
            ]
        return [
            "Controlla lo stato di visibilità locale del massimo.",
            "Usa binocolo o basso ingrandimento.",
            "Mantieni il disco lunare completo nel campo.",
        ]
    if event_type == "Congiunzione solare":
        return [
            "Non puntare binocoli, telescopi o cercatori vicino al Sole.",
            "Attendi che il pianeta riemerga nel cielo mattutino dopo la congiunzione.",
            "Usa la scheda del pianeta per controllarne la visibilità nelle notti successive.",
        ]
    if event_type in {"Congiunzione", "Congiunzione planetaria"}:
        return [
            "Preferisci bassi ingrandimenti o binocolo.",
            "Usa la finestra locale in cui entrambi superano la soglia utile.",
            "Cerca un orizzonte libero nella direzione indicata dalle schede dei pianeti.",
        ]
    return [
        "Controlla visibilità locale e meteo vicino alla data.",
        "Prepara il setup in anticipo per non perdere la finestra utile.",
    ]


def _priority(usefulness: int) -> tuple[str, str]:
    if usefulness >= 90:
        return "highlight", "In evidenza"
    if usefulness >= 75:
        return "relevant", "Rilevante"
    return "informational", "Informativo"


def _highlight_value(usefulness: int, visibility_state: str) -> int:
    if visibility_state in {"visible", "favorable", "nearby_night"}:
        penalty = 0
    elif visibility_state in {"check", "unknown"}:
        penalty = 5
    else:
        penalty = 50
    return usefulness - penalty


def _compact_timing_value(timing_kind: str, timing_value: str) -> str:
    if timing_kind != "window" or not timing_value:
        return timing_value
    if re.fullmatch(r"\d{2}:\d{2}(?:\s*-\s*\d{2}:\d{2})?", timing_value):
        return timing_value
    normalized = timing_value.casefold()
    if "prima dell'alba" in normalized or "pre-alba" in normalized:
        return "Pre-alba"
    if "mezzanotte" in normalized:
        return "Notte"
    if "prima parte" in normalized:
        return "Sera"
    return timing_value if len(timing_value) <= 12 else "Notte"


def _separation_label(value: float | None) -> str:
    if value is None:
        return ""
    precision = 2 if value < 1.0 else 1
    return f"{value:.{precision}f}".replace(".", ",") + " gradi"


def _detail_subtitle(date_label: str, timing_label: str, timing_value: str) -> str:
    if timing_value:
        return f"{date_label} - {timing_label}: {timing_value}"
    return date_label


def _append_guidance(setup: str, guidance: str) -> str:
    base = setup.strip()
    if base and base[-1] not in ".!?":
        base += "."
    return f"{base} {guidance}".strip()


def _is_generic_setup(setup: str) -> bool:
    return setup in {"", "Nota osservativa", "Qualsiasi setup"}


def _integer(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text_list(value: object) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if not isinstance(value, Sequence):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item).strip()
        canonical = text.casefold()
        if text and canonical not in seen:
            result.append(text)
            seen.add(canonical)
    return result


def _mapping_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    result: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            continue
        mapped = dict(item)
        object_id = (_text(mapped, "id") or _text(mapped, "objectId")).casefold()
        if object_id:
            if object_id in seen_ids:
                continue
            seen_ids.add(object_id)
        result.append(mapped)
    return result


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key, "")
    return "" if value is None else str(value).strip()
