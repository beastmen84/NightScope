from __future__ import annotations

from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import (
    ObservingSessionDecision,
    WeatherBlockingStatus,
    WeatherSummary,
)


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
        category_scores: AdvancedObservingScores | None,
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
            "title": "Sessione non valutabile",
            "badge": "Non disponibile",
            "detail": "Previsioni meteo non disponibili.",
            "description": "Aggiorna i dati meteo per valutare la sessione.",
            "windowLabel": "",
            "windowValue": "",
            "windowText": "Finestra osservativa non disponibile",
            "hasWindow": False,
            "limitingFactor": "Condizioni della sessione non valutabili",
        }

    state = session.state or "recommended"
    title = session.title or {
        "recommended": "Sessione consigliata",
        "monitor": "Sessione da monitorare",
        "discouraged": "Sessione sconsigliata",
    }.get(state, "Sessione da valutare")
    badge = {
        "recommended": "Consigliata",
        "monitor": "Da monitorare",
        "discouraged": "Sconsigliata",
    }.get(state, "Da valutare")
    if state == "discouraged":
        window_label = ""
        window_value = ""
        window_text = "Nessuna finestra consigliata"
    elif suggested_window:
        window_label = "Possibile finestra" if state == "monitor" else "Migliore finestra"
        window_value = suggested_window
        window_text = f"{window_label}: {window_value}"
    else:
        window_label = ""
        window_value = ""
        window_text = "Finestra osservativa non disponibile"

    detail = blocking.detail if blocking.show_warning and blocking.detail else weather.explanation
    description = session.description or weather.alert
    limiting_factor = (
        f"Fattore limitante: {blocking.reason}"
        if blocking.show_warning and blocking.reason
        else "Nessun fattore bloccante"
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
        "limitingFactor": limiting_factor,
    }


def _weather_payload(weather: WeatherSummary | None, session: dict[str, object]) -> dict[str, object]:
    if weather is None:
        return {
            "state": "unavailable",
            "available": False,
            "badge": "n/d",
            "scoreValue": None,
            "scoreLabel": "n/d",
            "explanation": "Previsioni non disponibili.",
            "windowText": session["windowText"],
        }
    return {
        "state": "available",
        "available": True,
        "badge": f"{weather.score}  {weather.score_value}/100",
        "scoreValue": weather.score_value,
        "scoreLabel": weather.score,
        "explanation": weather.explanation,
        "windowText": session["windowText"],
    }


def _planetary_payload(
    seeing: SeeingTransparency | None,
    scores: AdvancedObservingScores | None,
    wind_label: str,
    source: str,
) -> dict[str, object]:
    seeing_label = _quality_label(seeing.seeing if seeing else "")
    label = scores.planetary_label if scores else "n/d"
    return {
        "state": "available" if seeing_label != "n/d" and label != "n/d" else "unavailable",
        "label": label,
        "primaryMetric": f"Seeing {seeing_label}" if seeing_label != "n/d" else "Seeing non disponibile",
        "secondaryMetric": f"Vento {wind_label}" if wind_label and wind_label != "n/d" else "Vento non disponibile",
        "hint": _planetary_hint(seeing),
        "source": source,
    }


def _deep_sky_payload(
    seeing: SeeingTransparency | None,
    sky_quality: SkyQuality | None,
    scores: AdvancedObservingScores | None,
    source: str,
) -> dict[str, object]:
    transparency = _quality_label(seeing.transparency if seeing else "")
    bortle = sky_quality.bortle_class if sky_quality else 0
    label = scores.deep_sky_label if scores else "n/d"
    return {
        "state": "available" if label != "n/d" else "unavailable",
        "label": label,
        "primaryMetric": (
            f"Trasparenza {transparency}" if transparency != "n/d" else "Trasparenza non disponibile"
        ),
        "secondaryMetric": (
            f"Bortle {bortle} - {_bortle_label(bortle)}" if bortle else "Qualità del cielo non disponibile"
        ),
        "hint": _deep_sky_hint(seeing, sky_quality),
        "source": source,
    }


def _moon_payload(moon: MoonSummary | None) -> dict[str, object]:
    if moon is None:
        return {
            "impact": "unavailable",
            "impactLabel": "Impatto lunare non disponibile",
            "summary": "Dati lunari non disponibili.",
        }
    illumination = _percentage(moon.illumination)
    if illumination is None:
        return {
            "impact": "unavailable",
            "impactLabel": "Impatto lunare non disponibile",
            "summary": "Dati lunari non disponibili.",
        }
    if illumination >= 70:
        return {
            "impact": "high",
            "impactLabel": "Impatto lunare elevato",
            "summary": "Luna luminosa: maggiore fondo cielo per gli oggetti deboli.",
        }
    if illumination >= 35:
        return {
            "impact": "medium",
            "impactLabel": "Impatto lunare medio",
            "summary": "Luna moderatamente luminosa: impatto variabile sul cielo profondo.",
        }
    return {
        "impact": "low",
        "impactLabel": "Impatto lunare basso",
        "summary": "Luna poco luminosa: impatto ridotto sul cielo profondo.",
    }


def _planetary_hint(seeing: SeeingTransparency | None) -> str:
    if seeing is None or _quality_label(seeing.seeing) == "n/d":
        return "Dati atmosferici non disponibili"
    score = seeing.seeing_score if seeing else 0
    if score >= 80:
        return "Atmosfera stabile per i dettagli fini"
    if score >= 60:
        return "Dettaglio planetario generalmente favorito"
    if score >= 40:
        return "Dettaglio planetario variabile"
    return "Seeing limitante per i dettagli fini"


def _deep_sky_hint(seeing: SeeingTransparency | None, sky_quality: SkyQuality | None) -> str:
    transparency_available = seeing is not None and _quality_label(seeing.transparency) != "n/d"
    sky_quality_available = sky_quality is not None and sky_quality.bortle_class > 0
    if not transparency_available and not sky_quality_available:
        return "Dati del cielo non disponibili"
    if transparency_available and seeing.transparency_score < 40:
        return "Trasparenza limitante per gli oggetti deboli"
    bortle = sky_quality.bortle_class if sky_quality else 0
    if bortle >= 8:
        return "Privilegiare gli oggetti più brillanti"
    if bortle >= 6:
        return "Ammassi favoriti rispetto agli oggetti diffusi"
    if bortle >= 4:
        return "Galassie brillanti più accessibili"
    return "Buon potenziale per gli oggetti deboli"


def _quality_label(value: str) -> str:
    return {
        "excellent": "eccellente",
        "good": "buona",
        "average": "discreta",
        "poor": "scarsa",
        "eccellente": "eccellente",
        "buono": "buona",
        "buona": "buona",
        "discreto": "discreta",
        "discreta": "discreta",
        "scarso": "scarsa",
        "scarsa": "scarsa",
    }.get((value or "").strip().lower(), "n/d")


def _bortle_label(bortle: int) -> str:
    return {
        1: "cielo eccezionalmente buio",
        2: "cielo molto buio",
        3: "cielo rurale",
        4: "transizione rurale-suburbana",
        5: "cielo suburbano",
        6: "cielo suburbano luminoso",
        7: "cielo urbano",
        8: "cielo urbano luminoso",
        9: "centro urbano",
    }.get(bortle, "qualità non classificata")


def _percentage(value: str) -> float | None:
    try:
        return float((value or "").replace("%", "").strip())
    except ValueError:
        return None


def _location_context_payload(*, pending: bool) -> dict[str, object]:
    if pending:
        session = {
            "state": "pending",
            "title": "Posizione in aggiornamento",
            "badge": "In attesa",
            "detail": "Ricerca della posizione in corso.",
            "description": "Le condizioni saranno valutate appena la posizione è disponibile.",
            "windowLabel": "",
            "windowValue": "",
            "windowText": "Finestra in attesa della posizione",
            "hasWindow": False,
            "limitingFactor": "Dati locali in aggiornamento",
        }
        return {
            "schemaVersion": HOME_OBSERVING_OVERVIEW_SCHEMA_VERSION,
            "session": session,
            "weather": {
                "state": "pending",
                "available": False,
                "badge": "In attesa",
                "scoreValue": None,
                "scoreLabel": "n/d",
                "explanation": "Previsioni in attesa della posizione.",
                "windowText": session["windowText"],
            },
            "planetary": {
                "state": "pending",
                "label": "In attesa",
                "primaryMetric": "Seeing in attesa",
                "secondaryMetric": "Posizione in aggiornamento",
                "hint": "Calcolo dopo il rilevamento",
                "source": "location_pending",
            },
            "deepSky": {
                "state": "pending",
                "label": "In attesa",
                "primaryMetric": "Trasparenza in attesa",
                "secondaryMetric": "Cielo locale in aggiornamento",
                "hint": "Calcolo dopo il rilevamento",
                "source": "location_pending",
            },
            "moon": {
                "impact": "pending",
                "impactLabel": "Calcolo dopo il rilevamento",
                "summary": "Dati lunari in attesa.",
            },
        }

    session = {
        "state": "unavailable",
        "title": "Sessione non valutabile",
        "badge": "Non disponibile",
        "detail": "Posizione necessaria per valutare la sessione.",
        "description": "Configura una posizione per ottenere le condizioni locali.",
        "windowLabel": "",
        "windowValue": "",
        "windowText": "Finestra non disponibile",
        "hasWindow": False,
        "limitingFactor": "Posizione non disponibile",
    }
    return {
        "schemaVersion": HOME_OBSERVING_OVERVIEW_SCHEMA_VERSION,
        "session": session,
        "weather": {
            "state": "unavailable",
            "available": False,
            "badge": "n/d",
            "scoreValue": None,
            "scoreLabel": "n/d",
            "explanation": "Posizione necessaria per il meteo.",
            "windowText": session["windowText"],
        },
        "planetary": {
            "state": "unavailable",
            "label": "n/d",
            "primaryMetric": "Seeing non disponibile",
            "secondaryMetric": "Posizione necessaria",
            "hint": "Configura una posizione",
            "source": "no_location",
        },
        "deepSky": {
            "state": "unavailable",
            "label": "n/d",
            "primaryMetric": "Trasparenza non disponibile",
            "secondaryMetric": "Posizione necessaria",
            "hint": "Configura una posizione",
            "source": "no_location",
        },
        "moon": {
            "impact": "unavailable",
            "impactLabel": "Impatto lunare non disponibile",
            "summary": "Posizione necessaria per la Luna.",
        },
    }
