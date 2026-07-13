from __future__ import annotations

from collections.abc import Mapping

from astro_viewer.app.services.equipment_setup_read_model import EquipmentSetupReadModel
from astro_viewer.app.services.localization import presentation_text, tr


OBSERVING_OBJECT_DETAIL_SCHEMA_VERSION = "observing_object_detail_v3"

_SCORE_KEYS = {
    "score",
    "score_label",
    "scoreLabel",
    "score_explanation",
    "scoreExplanation",
}

_SESSION_BADGES = {
    "recommended": tr("Sessione consigliata"),
    "monitor": tr("Sessione da monitorare"),
    "discouraged": tr("Sessione sconsigliata"),
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
        filter_recommendations: Mapping[str, object] | None = None,
        reducer_recommendation: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        payload = _sanitized_object_payload(object_payload)
        session_payload = _session_payload(session)
        duration = _text(payload, "time_above_horizon")
        window_label = _text(payload, "homeWindowLabel") or tr("n/d")
        window_start, window_end = _window_edges(window_label)
        geometry = {
            "state": geometry_state,
            "status": _text(payload, "observingStatus"),
            "detail": _text(payload, "observingStatusDetail"),
            "observableNow": payload.get("observableNow") is True,
            "windowLabel": window_label,
            "windowStart": window_start,
            "windowEnd": window_end,
            "bestTimeLabel": _text(payload, "homeTimeLabel") or tr("n/d"),
            "duration": duration or tr("n/d"),
            "durationText": _duration_text(duration, altitude_threshold_deg),
            "altitudeThresholdDeg": altitude_threshold_deg,
            "altitudeThresholdLabel": tr(
                "Soglia utile {value:g} gradi",
                value=altitude_threshold_deg,
            ),
            "currentAltitude": _text(payload, "currentAltitude") or tr("n/d"),
            "currentAzimuth": _text(payload, "currentAzimuth") or tr("n/d"),
            "maximumAltitude": _text(payload, "max_altitude") or tr("n/d"),
            "riseTime": _text(payload, "riseTime") or tr("n/d"),
            "setTime": _text(payload, "setTime") or tr("n/d"),
            "culminationTime": _text(payload, "culminationTime") or tr("n/d"),
            "showHorizonEvents": _has_real_horizon_events(payload),
            "isDeepSky": is_deep_sky,
        }
        evaluation = {
            "title": tr("Valutazione osservativa"),
            "subtitle": _evaluation_subtitle(session_payload["state"]),
            "reasons": _string_list(payload.get("observingReasons")),
            "warning": _session_warning(session_payload),
        }
        equipment = {
            "telescopeName": setup_model.telescope_name if setup_model else "",
            "equipmentType": setup_model.equipment_type if setup_model else "",
            "setupType": setup_model.recommended_setup_type if setup_model else "",
            "usesTargetSelection": bool(setup_model and setup_model.telescope_name),
            "filterRecommendations": _filter_recommendations_payload(
                filter_recommendations
            ),
            "reducerRecommendation": _reducer_recommendation_payload(
                reducer_recommendation
            ),
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
        "title": _text(session, "title") or tr("Sessione non valutabile"),
        "badge": _SESSION_BADGES.get(
            state,
            _text(session, "badge") or tr("Non disponibile"),
        ),
        "detail": _text(session, "detail"),
        "description": _text(session, "description"),
        "limitingFactorCode": _text(session, "limitingFactorCode"),
        "limitingFactor": _text(session, "limitingFactor"),
    }


def _filter_recommendations_payload(
    recommendations: Mapping[str, object] | None,
) -> dict[str, object]:
    if not isinstance(recommendations, Mapping):
        return {"primary": {}, "optionalColor": {}}
    return {
        "primary": _filter_recommendation_payload(recommendations.get("primary")),
        "optionalColor": _filter_recommendation_payload(
            recommendations.get("optionalColor")
        ),
    }


def _filter_recommendation_payload(value: object) -> dict[str, object]:
    if not isinstance(value, Mapping) or value.get("applicable") is not True:
        return {}
    return {
        "applicable": True,
        "available": value.get("available") is True,
        "label": _text(value, "label"),
        "value": _text(value, "value"),
        "filterClass": _text(value, "filterClass"),
        "filterClassLabel": _text(value, "filterClassLabel"),
        "filterId": _text(value, "filterId"),
    }


def _reducer_recommendation_payload(
    recommendation: Mapping[str, object] | None,
) -> dict[str, object]:
    if (
        not isinstance(recommendation, Mapping)
        or recommendation.get("applicable") is not True
    ):
        return {}
    items = recommendation.get("items")
    return {
        "applicable": True,
        "available": recommendation.get("available") is True,
        "label": _text(recommendation, "label"),
        "value": _text(recommendation, "value"),
        "items": [
            {
                "reducerId": _text(item, "reducerId"),
                "displayLabel": _text(item, "displayLabel"),
                "reductionFactor": item.get("reductionFactor"),
            }
            for item in items
            if isinstance(item, Mapping)
        ]
        if isinstance(items, list | tuple)
        else [],
    }


def _duration_text(duration: str, altitude_threshold_deg: float) -> str:
    if not duration or duration in {"n/d", "0 h"}:
        return tr("Durata utile non disponibile")
    return tr(
        "{duration} nella finestra utile, sopra {threshold:g} gradi",
        duration=duration,
        threshold=altitude_threshold_deg,
    )


def _has_real_horizon_events(payload: Mapping[str, object]) -> bool:
    invalid = {"", tr("n/d"), tr("calcolato da finestra")}
    return _text(payload, "riseTime") not in invalid and _text(payload, "setTime") not in invalid


def _window_edges(window_label: str) -> tuple[str, str]:
    parts = [part.strip() for part in window_label.split(" - ", maxsplit=1)]
    if len(parts) != 2:
        return tr("n/d"), tr("n/d")
    return parts[0] or tr("n/d"), parts[1] or tr("n/d")


def _evaluation_subtitle(state: str) -> str:
    labels = {
        "recommended": tr("Geometria, cielo e configurazione per la sessione consigliata"),
        "monitor": tr("Geometria favorevole, condizioni da monitorare"),
        "discouraged": tr("Visibilità geometrica con sessione non consigliata"),
        "pending": tr("Valutazione in aggiornamento"),
    }
    return labels.get(state, tr("Condizioni della sessione non disponibili"))


def _session_warning(session: Mapping[str, object]) -> str:
    limiting_factor = _text(session, "limitingFactor")
    if (
        session.get("state") == "recommended"
        and session.get("limitingFactorCode") == "none"
    ):
        return ""
    return limiting_factor or _text(session, "detail")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [presentation_text(item) for item in value if presentation_text(item, strip=True)]


def _text(payload: Mapping[str, object], key: str) -> str:
    return presentation_text(payload.get(key, ""))
