"""Build the stable upper-Home observing-condition presentation contract."""

from __future__ import annotations

from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import ObservingCategoryScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import (
    ObservingSessionDecision,
    WeatherBlockingStatus,
    WeatherSummary,
)
from astro_viewer.app.services.localization import tr


HOME_OBSERVING_OVERVIEW_SCHEMA_VERSION = "home_observing_overview_v1"


class HomeObservingOverviewService:
    """Builds the stable presentation contract for the upper Home overview."""

    def build(
        self,
        *,
        location_available: bool,
        location_pending: bool,
        weather: WeatherSummary | None,
        weather_available: bool,
        seeing: SeeingTransparency | None,
        sky_quality: SkyQuality | None,
        moon: MoonSummary | None,
        category_scores: ObservingCategoryScores | None,
        session: ObservingSessionDecision,
        blocking: WeatherBlockingStatus,
        suggested_window: str,
        wind_label: str,
        category_source: str,
    ) -> dict[str, object]:
        if location_pending:
            return _location_context_payload(pending=True)
        if not location_available:
            return _location_context_payload(pending=False)

        available_weather = weather if weather_available else None
        session_payload = _session_payload(
            available_weather,
            session,
            blocking,
            suggested_window=suggested_window,
        )
        return {
            "schemaVersion": HOME_OBSERVING_OVERVIEW_SCHEMA_VERSION,
            "session": session_payload,
            "weather": _weather_payload(available_weather, session_payload),
            "planetary": _planetary_payload(seeing, category_scores, wind_label, category_source),
            "deepSky": _deep_sky_payload(seeing, sky_quality, category_scores, category_source),
            "moon": _moon_payload(moon),
        }


def _session_payload(
    weather: WeatherSummary | None,
    session: ObservingSessionDecision,
    blocking: WeatherBlockingStatus,
    *,
    suggested_window: str,
) -> dict[str, object]:
    if weather is None:
        return {
            "state": "unavailable",
            "title": tr("Sessione non valutabile"),
            "badge": tr("Non disponibile"),
            "detail": tr("Previsioni meteo non disponibili."),
            "description": tr("Aggiorna i dati meteo per valutare la sessione."),
            "windowLabel": "",
            "windowValue": "",
            "windowText": tr("Finestra osservativa non disponibile"),
            "hasWindow": False,
            "limitingFactorCode": "unavailable",
            "limitingFactor": tr("Condizioni della sessione non valutabili"),
        }

    state = session.state or "recommended"
    title = session.title or {
        "recommended": tr("Sessione consigliata"),
        "monitor": tr("Sessione da monitorare"),
        "discouraged": tr("Sessione sconsigliata"),
    }.get(state, tr("Sessione da valutare"))
    badge = {
        "recommended": tr("Consigliata"),
        "monitor": tr("Da monitorare"),
        "discouraged": tr("Sconsigliata"),
    }.get(state, tr("Da valutare"))
    if state == "discouraged":
        window_label = ""
        window_value = ""
        window_text = tr("Nessuna finestra consigliata")
    elif suggested_window:
        window_label = tr("Possibile finestra") if state == "monitor" else tr("Migliore finestra")
        window_value = suggested_window
        window_text = tr("{label}: {value}", label=window_label, value=window_value)
    else:
        window_label = ""
        window_value = ""
        window_text = tr("Finestra osservativa non disponibile")

    detail = blocking.detail if blocking.show_warning and blocking.detail else weather.explanation
    description = session.description or weather.alert
    limiting_factor = (
        tr("Fattore limitante: {reason}", reason=blocking.reason)
        if blocking.show_warning and blocking.reason
        else tr("Nessun fattore bloccante")
    )
    return {
        "state": state,
        "title": title,
        "badge": badge,
        "detail": detail,
        "description": description,
        "windowLabel": window_label,
        "windowValue": window_value,
        "windowText": window_text,
        "hasWindow": bool(window_value),
        "limitingFactorCode": "weather" if blocking.show_warning else "none",
        "limitingFactor": limiting_factor,
    }


def _weather_payload(weather: WeatherSummary | None, session: dict[str, object]) -> dict[str, object]:
    if weather is None:
        return {
            "state": "unavailable",
            "available": False,
            "badge": tr("n/d"),
            "scoreValue": None,
            "scoreLabel": tr("n/d"),
            "explanation": tr("Previsioni non disponibili."),
            "windowText": session["windowText"],
        }
    return {
        "state": "available",
        "available": True,
        "badge": tr("{score}  {value}/100", score=weather.score, value=weather.score_value),
        "scoreValue": weather.score_value,
        "scoreLabel": weather.score,
        "explanation": weather.explanation,
        "windowText": session["windowText"],
    }


def _planetary_payload(
    seeing: SeeingTransparency | None,
    scores: ObservingCategoryScores | None,
    wind_label: str,
    source: str,
) -> dict[str, object]:
    seeing_label = _quality_label(seeing.seeing if seeing else "")
    label = scores.planetary_label if scores else tr("n/d")
    return {
        "state": "available" if seeing_label != "n/d" and label != "n/d" else "unavailable",
        "label": label,
        "scoreValue": scores.planetary_score if scores else None,
        "primaryMetric": tr("Seeing {value}", value=seeing_label)
        if seeing_label != "n/d"
        else tr("Seeing non disponibile"),
        "secondaryMetric": tr("Vento {value}", value=wind_label)
        if wind_label and wind_label != "n/d"
        else tr("Vento non disponibile"),
        "hint": _planetary_hint(seeing),
        "source": source,
    }


def _deep_sky_payload(
    seeing: SeeingTransparency | None,
    sky_quality: SkyQuality | None,
    scores: ObservingCategoryScores | None,
    source: str,
) -> dict[str, object]:
    transparency = _quality_label(seeing.atmospheric_transparency if seeing else "")
    bortle = sky_quality.bortle_class if sky_quality else 0
    label = scores.deep_sky_label if scores else tr("n/d")
    sky_quality_available = bortle > 0
    if label == "n/d":
        state = "unavailable"
        display_label = label
    elif not sky_quality_available:
        state = "partial"
        display_label = tr("Parziale")
    else:
        state = "available"
        display_label = label
    return {
        "state": state,
        "label": display_label,
        "scoreValue": scores.deep_sky_score if scores else None,
        "primaryMetric": (
            tr("Trasparenza {value}", value=transparency)
            if transparency != "n/d"
            else tr("Trasparenza non disponibile")
        ),
        "secondaryMetric": (
            tr("Bortle {value} - {label}", value=bortle, label=bortle_sky_label(bortle))
            if bortle
            else tr("Qualità del cielo non disponibile")
        ),
        "hint": _deep_sky_hint(seeing, sky_quality),
        "source": source,
    }


def _moon_payload(moon: MoonSummary | None) -> dict[str, object]:
    if moon is None:
        return {
            "impact": "unavailable",
            "impactLabel": tr("Impatto lunare non disponibile"),
            "summary": tr("Dati lunari non disponibili."),
        }
    illumination = _percentage(moon.illumination)
    if illumination is None:
        return {
            "impact": "unavailable",
            "impactLabel": tr("Impatto lunare non disponibile"),
            "summary": tr("Dati lunari non disponibili."),
        }
    if illumination >= 70:
        return {
            "impact": "high",
            "impactLabel": tr("Impatto lunare elevato"),
            "summary": tr("Luna luminosa: maggiore fondo cielo per gli oggetti deboli."),
        }
    if illumination >= 35:
        return {
            "impact": "medium",
            "impactLabel": tr("Impatto lunare medio"),
            "summary": tr("Luna moderatamente luminosa: impatto variabile sul cielo profondo."),
        }
    return {
        "impact": "low",
        "impactLabel": tr("Impatto lunare basso"),
        "summary": tr("Luna poco luminosa: impatto ridotto sul cielo profondo."),
    }


def _planetary_hint(seeing: SeeingTransparency | None) -> str:
    if seeing is None or _quality_label(seeing.seeing) == "n/d":
        return tr("Dati atmosferici non disponibili")
    score = seeing.seeing_score if seeing else 0
    if score >= 80:
        return tr("Atmosfera stabile per i dettagli fini")
    if score >= 60:
        return tr("Dettaglio planetario generalmente favorito")
    if score >= 40:
        return tr("Dettaglio planetario variabile")
    return tr("Seeing limitante per i dettagli fini")


def _deep_sky_hint(seeing: SeeingTransparency | None, sky_quality: SkyQuality | None) -> str:
    transparency_available = seeing is not None and _quality_label(seeing.atmospheric_transparency) != "n/d"
    transparency_score = 0
    if seeing is not None:
        transparency_score = (
            seeing.atmospheric_transparency_score
            if seeing.atmospheric_transparency_score is not None
            else seeing.transparency_score
        )
    sky_quality_available = sky_quality is not None and sky_quality.bortle_class > 0
    if not transparency_available and not sky_quality_available:
        return tr("Dati del cielo non disponibili")
    if not sky_quality_available:
        if seeing is not None and transparency_score < 40:
            return tr("Trasparenza limitante; inquinamento luminoso non disponibile")
        return tr(
            "Inquinamento luminoso non disponibile: visibilità degli oggetti deboli da verificare"
        )
    if transparency_available and transparency_score < 40:
        return tr("Trasparenza limitante per gli oggetti deboli")
    bortle = sky_quality.bortle_class if sky_quality else 0
    if bortle >= 8:
        return tr("Privilegiare gli oggetti più brillanti")
    if bortle >= 6:
        return tr("Ammassi favoriti rispetto agli oggetti diffusi")
    if bortle >= 4:
        return tr("Galassie brillanti più accessibili")
    return tr("Buon potenziale per gli oggetti deboli")


def _quality_label(value: str) -> str:
    return {
        "excellent": tr("eccellente"),
        "good": tr("buona"),
        "average": tr("discreta"),
        "poor": tr("scarsa"),
        "eccellente": tr("eccellente"),
        "buono": tr("buona"),
        "buona": tr("buona"),
        "discreto": tr("discreta"),
        "discreta": tr("discreta"),
        "scarso": tr("scarsa"),
        "scarsa": tr("scarsa"),
    }.get((value or "").strip().lower(), tr("n/d"))


def bortle_sky_label(bortle: int) -> str:
    return {
        1: tr("cielo eccezionalmente buio"),
        2: tr("cielo molto buio"),
        3: tr("cielo rurale"),
        4: tr("transizione rurale-suburbana"),
        5: tr("cielo suburbano"),
        6: tr("cielo suburbano luminoso"),
        7: tr("transizione suburbana-urbana"),
        8: tr("cielo urbano"),
        9: tr("centro urbano"),
    }.get(bortle, tr("qualità non classificata"))


def bortle_observing_warning(bortle: int) -> str:
    if bortle >= 8:
        return tr(
            "{label}: oggetti cielo profondo limitati. Preferire ammassi aperti, pianeti e Luna.",
            label=_bortle_warning_label(bortle),
        )
    if bortle >= 7:
        return tr(
            "{label}: privilegiare oggetti brillanti e pianeti.",
            label=_bortle_warning_label(bortle),
        )
    return ""


def _bortle_warning_label(bortle: int) -> str:
    return {
        7: tr("Transizione suburbana-urbana"),
        8: tr("Cielo urbano"),
        9: tr("Centro urbano"),
    }.get(bortle, tr("Qualità non classificata"))


def _percentage(value: str) -> float | None:
    try:
        return float((value or "").replace("%", "").strip())
    except ValueError:
        return None


def _location_context_payload(*, pending: bool) -> dict[str, object]:
    if pending:
        session = {
            "state": "pending",
            "title": tr("Posizione in aggiornamento"),
            "badge": tr("In attesa"),
            "detail": tr("Ricerca della posizione in corso."),
            "description": tr("Le condizioni saranno valutate appena la posizione è disponibile."),
            "windowLabel": "",
            "windowValue": "",
            "windowText": tr("Finestra in attesa della posizione"),
            "hasWindow": False,
            "limitingFactorCode": "location_pending",
            "limitingFactor": tr("Dati locali in aggiornamento"),
        }
        return {
            "schemaVersion": HOME_OBSERVING_OVERVIEW_SCHEMA_VERSION,
            "session": session,
            "weather": {
                "state": "pending",
                "available": False,
                "badge": tr("In attesa"),
                "scoreValue": None,
                "scoreLabel": tr("n/d"),
                "explanation": tr("Previsioni in attesa della posizione."),
                "windowText": session["windowText"],
            },
            "planetary": {
                "state": "pending",
                "label": tr("In attesa"),
                "scoreValue": None,
                "primaryMetric": tr("Seeing in attesa"),
                "secondaryMetric": tr("Posizione in aggiornamento"),
                "hint": tr("Calcolo dopo il rilevamento"),
                "source": "location_pending",
            },
            "deepSky": {
                "state": "pending",
                "label": tr("In attesa"),
                "scoreValue": None,
                "primaryMetric": tr("Trasparenza in attesa"),
                "secondaryMetric": tr("Cielo locale in aggiornamento"),
                "hint": tr("Calcolo dopo il rilevamento"),
                "source": "location_pending",
            },
            "moon": {
                "impact": "pending",
                "impactLabel": tr("Calcolo dopo il rilevamento"),
                "summary": tr("Dati lunari in attesa."),
            },
        }

    session = {
        "state": "unavailable",
        "title": tr("Sessione non valutabile"),
        "badge": tr("Non disponibile"),
        "detail": tr("Località necessaria per valutare la sessione."),
        "description": tr("Configura una località per ottenere le condizioni locali."),
        "windowLabel": "",
        "windowValue": "",
        "windowText": tr("Finestra non disponibile"),
        "hasWindow": False,
        "limitingFactorCode": "no_location",
        "limitingFactor": tr("Località non disponibile"),
    }
    return {
        "schemaVersion": HOME_OBSERVING_OVERVIEW_SCHEMA_VERSION,
        "session": session,
        "weather": {
            "state": "unavailable",
            "available": False,
            "badge": tr("n/d"),
            "scoreValue": None,
            "scoreLabel": tr("n/d"),
            "explanation": tr("Località necessaria per il meteo."),
            "windowText": session["windowText"],
        },
        "planetary": {
            "state": "unavailable",
            "label": tr("n/d"),
            "scoreValue": None,
            "primaryMetric": tr("Seeing non disponibile"),
            "secondaryMetric": tr("Località necessaria"),
            "hint": tr("Configura una località"),
            "source": "no_location",
        },
        "deepSky": {
            "state": "unavailable",
            "label": tr("n/d"),
            "scoreValue": None,
            "primaryMetric": tr("Trasparenza non disponibile"),
            "secondaryMetric": tr("Località necessaria"),
            "hint": tr("Configura una località"),
            "source": "no_location",
        },
        "moon": {
            "impact": "unavailable",
            "impactLabel": tr("Impatto lunare non disponibile"),
            "summary": tr("Località necessaria per la Luna."),
        },
    }
