from __future__ import annotations

from collections.abc import Mapping

from astro_viewer.app.services.equipment_setup_read_model import EquipmentSetupReadModel


OBSERVING_OBJECT_DETAIL_SCHEMA_VERSION = "observing_object_detail_v1"

_SCORE_KEYS = {
    "score",
    "score_label",
    "scoreLabel",
    "score_explanation",
    "scoreExplanation",
}


class ObservingObjectDetailService:
    """Builds the score-free presentation contract for Home object detail."""

    def build(
        self,
        *,
        object_payload: Mapping[str, object],
        geometry_state: str,
        session: Mapping[str, object],
        setup_model: EquipmentSetupReadModel | None,
        altitude_threshold_deg: float,
        is_deep_sky: bool,
    ) -> dict[str, object]:
        payload = _sanitized_object_payload(object_payload)
        session_payload = _session_payload(session)
        duration = _text(payload, "time_above_horizon")
        window_label = _text(payload, "homeWindowLabel") or "n/d"
        window_start, window_end = _window_edges(window_label)
        geometry = {
            "state": geometry_state,
            "status": _text(payload, "observingStatus"),
            "detail": _text(payload, "observingStatusDetail"),
            "observableNow": payload.get("observableNow") is True,
            "windowLabel": window_label,
            "windowStart": window_start,
            "windowEnd": window_end,
            "bestTimeLabel": _text(payload, "homeTimeLabel") or "n/d",
            "duration": duration or "n/d",
            "durationText": _duration_text(duration, altitude_threshold_deg),
            "altitudeThresholdDeg": altitude_threshold_deg,
            "altitudeThresholdLabel": f"Soglia utile {altitude_threshold_deg:g} gradi",
            "currentAltitude": _text(payload, "currentAltitude") or "n/d",
            "currentAzimuth": _text(payload, "currentAzimuth") or "n/d",
            "maximumAltitude": _text(payload, "max_altitude") or "n/d",
            "riseTime": _text(payload, "riseTime") or "n/d",
            "setTime": _text(payload, "setTime") or "n/d",
            "culminationTime": _text(payload, "culminationTime") or "n/d",
            "showHorizonEvents": _has_real_horizon_events(payload),
            "isDeepSky": is_deep_sky,
        }
        evaluation = {
            "title": "Valutazione osservativa",
            "subtitle": _evaluation_subtitle(session_payload["state"]),
            "reasons": _string_list(payload.get("observingReasons")),
            "warning": _session_warning(session_payload),
        }
        equipment = {
            "telescopeName": setup_model.telescope_name if setup_model else "",
            "equipmentType": setup_model.equipment_type if setup_model else "",
            "setupType": setup_model.recommended_setup_type if setup_model else "",
            "usesTargetSelection": bool(setup_model and setup_model.telescope_name),
        }
        payload.update(
            {
                "schemaVersion": OBSERVING_OBJECT_DETAIL_SCHEMA_VERSION,
                "detailSource": "home_observing",
                "geometry": geometry,
                "session": session_payload,
                "evaluation": evaluation,
                "equipment": equipment,
            }
        )
        return payload


def _sanitized_object_payload(payload: Mapping[str, object]) -> dict[str, object]:
    clean = {key: value for key, value in payload.items() if key not in _SCORE_KEYS}
    clean.pop("setup_options", None)
    options = clean.get("setupOptions")
    if isinstance(options, list | tuple):
        clean["setupOptions"] = [
            {key: value for key, value in option.items() if key != "score"}
            for option in options
            if isinstance(option, Mapping)
        ]
    return clean


def _session_payload(session: Mapping[str, object]) -> dict[str, object]:
    state = _text(session, "state") or "unavailable"
    return {
        "state": state,
        "title": _text(session, "title") or "Sessione non valutabile",
        "badge": _text(session, "badge") or "Non disponibile",
        "detail": _text(session, "detail"),
        "description": _text(session, "description"),
        "limitingFactor": _text(session, "limitingFactor"),
    }


def _duration_text(duration: str, altitude_threshold_deg: float) -> str:
    if not duration or duration in {"n/d", "0 h"}:
        return "Durata utile non disponibile"
    return f"{duration} nella finestra utile, sopra {altitude_threshold_deg:g} gradi"


def _has_real_horizon_events(payload: Mapping[str, object]) -> bool:
    invalid = {"", "n/d", "calcolato da finestra"}
    return _text(payload, "riseTime") not in invalid and _text(payload, "setTime") not in invalid


def _window_edges(window_label: str) -> tuple[str, str]:
    parts = [part.strip() for part in window_label.split(" - ", maxsplit=1)]
    if len(parts) != 2:
        return "n/d", "n/d"
    return parts[0] or "n/d", parts[1] or "n/d"


def _evaluation_subtitle(state: str) -> str:
    labels = {
        "recommended": "Geometria, cielo e configurazione per la sessione consigliata",
        "monitor": "Geometria favorevole, condizioni da monitorare",
        "discouraged": "Visibilita geometrica con sessione non consigliata",
        "pending": "Valutazione in aggiornamento",
    }
    return labels.get(state, "Condizioni della sessione non disponibili")


def _session_warning(session: Mapping[str, object]) -> str:
    limiting_factor = _text(session, "limitingFactor")
    if session.get("state") == "recommended" and limiting_factor == "Nessun fattore bloccante":
        return ""
    return limiting_factor or _text(session, "detail")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value if str(item).strip()]


def _text(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key, "")
    return "" if value is None else str(value)
