from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime


CALENDAR_OVERVIEW_SCHEMA_VERSION = "calendar_overview_v1"
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
        for event in events:
            event_at = _event_datetime(event, now)
            if event_at is None:
                continue
            days_until = (event_at.date() - now.date()).days
            if not 0 <= days_until <= CALENDAR_HORIZON_DAYS:
                continue
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
        highlights = [
            candidate[2]
            for candidate in sorted(
                (candidate for candidate in candidates if candidate[2]["daysUntil"] <= 30),
                key=lambda candidate: (
                    _visibility_order(str(candidate[2]["visibilityState"])),
                    -candidate[1],
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
            "highlights": highlights,
            "counts": {
                "moon": counts["Luna"],
                "oppositions": counts["Opposizione"],
                "conjunctions": counts["Congiunzione"],
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
        has_configured_equipment=has_configured_equipment,
    )
    priority_state, priority_label = _priority(usefulness)
    return {
        "id": _text(event, "id"),
        "title": title,
        "type": event_type,
        "dateLabel": date_label,
        "eventAt": event_at.isoformat(),
        "daysUntil": days_until,
        "timingKind": _text(event, "timingKind") or _text(event, "timing_kind") or "instant",
        "timingLabel": timing_label,
        "timingValue": timing_value,
        "observingWindow": observing_window,
        "visibilityState": visibility_state,
        "visibilityLabel": visibility_label,
        "visibilityDetail": visibility_detail,
        "priorityState": priority_state,
        "priorityLabel": priority_label,
        "setupText": setup,
        "note": _text(event, "note"),
        "targetObjectId": _text(event, "targetObjectId") or _text(event, "target_object_id"),
        "whyText": _why_text(event_type, title, _text(event, "note")),
        "tips": _observing_tips(event_type, title),
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
    if event_type == "Eclissi":
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
    if event_type == "Congiunzione" and setup:
        return _append_guidance(
            setup,
            "Preferisci campo largo: l'obiettivo è vedere gli oggetti insieme.",
        )
    if setup == "Occhio nudo":
        return "Osservabile a occhio nudo"
    if not has_configured_equipment and event_type in {"Opposizione", "Congiunzione"}:
        return "Configura un profilo per consigli più precisi."
    if _is_generic_setup(setup):
        return "Configura un profilo per consigli più precisi."
    return setup or "Configura un profilo per consigli più precisi."


def _why_text(event_type: str, title: str, fallback: str) -> str:
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
        return (
            "È osservabile anche a occhio nudo; binocolo o basso ingrandimento aiutano "
            "a seguire ombra e colore sul disco lunare."
        )
    if event_type == "Congiunzione":
        return (
            "È interessante quando più oggetti entrano nello stesso campo con binocolo, "
            "bassi ingrandimenti o fotografia a campo largo."
        )
    return fallback or "Evento astronomico nell'orizzonte annuale."


def _observing_tips(event_type: str, title: str) -> list[str]:
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
        return [
            "Controlla lo stato di visibilità locale del massimo.",
            "Usa binocolo o basso ingrandimento.",
            "Mantieni il disco lunare completo nel campo.",
        ]
    if event_type == "Congiunzione":
        return [
            "Preferisci bassi ingrandimenti o binocolo.",
            "Controlla la visibilità locale prima di preparare il setup.",
            "Cerca un orizzonte libero vicino alla finestra indicata.",
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


def _visibility_order(state: str) -> int:
    if state in {"visible", "favorable", "nearby_night"}:
        return 0
    if state in {"check", "unknown"}:
        return 1
    return 2


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


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key, "")
    return "" if value is None else str(value).strip()
