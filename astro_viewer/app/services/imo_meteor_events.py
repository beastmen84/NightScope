"""Overlay validated annual meteor dates, leaving other astronomy/scoring untouched."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from astro_viewer.app.models.observing import AstronomicalEvent
from astro_viewer.app.astronomy.meteor_windows import remaining_window
from astro_viewer.app.services.imo_calendar import ImoCalendar, IMO_URL, SHOWER_IDS
from astro_viewer.app.services.localization import format_datetime, format_number, join_text, tr
from astro_viewer.app.services.observing_night_service import usable_weather_intervals


_NAMES = {
    "QUA": tr("Quadrantidi"), "LYR": tr("Liridi"), "ETA": tr("Eta Aquaridi"),
    "SDA": tr("Delta Aquaridi meridionali"), "PER": tr("Perseidi"),
    "DRA": tr("Draconidi"), "ORI": tr("Orionidi"), "LEO": tr("Leonidi"),
    "GEM": tr("Geminidi"), "URS": tr("Ursidi"),
}


def annual_meteor_events(events: list[AstronomicalEvent], calendar: ImoCalendar | None,
                         now: datetime, *, geometry=None, weather_hours=(), location=None) -> list[AstronomicalEvent]:
    if calendar is None or not events:
        return events
    ids = {f"shower-{shower_id}-{calendar.year}" for shower_id in SHOWER_IDS.values()}
    result = [event for event in events if event.id not in ids]
    for shower in calendar.showers:
        # Noon UT is a sorting anchor only: the UI deliberately shows a DATE,
        # never this invented instant. Activity bounds are facts, not observing
        # windows; no local visibility or outburst prediction is manufactured.
        anchor = datetime.combine(shower.peak, time(12), UTC)
        if anchor.date() + timedelta(days=1) < now.astimezone(UTC).date() or anchor > now + timedelta(days=365):
            continue
        date_label = tr("{date} (UT)", date=format_datetime(anchor, include_time=False))
        event = AstronomicalEvent(
            id=f"shower-{SHOWER_IDS[shower.code]}-{calendar.year}",
            title=tr("Massimo previsto {name}", name=_NAMES[shower.code]),
            event_type="Sciame meteorico", date_label=date_label,
            best_time=date_label, usefulness=78, setup=tr("Occhio nudo"),
            note=tr("Data indicativa dalla tabella annuale IMO; non è un istante esatto né una previsione di visibilità locale. Eventuali picchi aggiuntivi non sono importati."),
            event_at=anchor.isoformat(), timing_kind="window",
            timing_label=tr("Data del massimo (UT)"),
            observing_window=tr("Da valutare con buio, radiante, Luna e meteo locali"),
            visibility_state="check", visibility_label=tr("Da verificare"),
            visibility_detail=tr("Il tasso ZHR si riferisce a condizioni ideali, non alle meteore effettivamente visibili dalla propria località."),
            source_code="imo_calendar", source_label=tr("Calendario IMO {year}", year=calendar.year),
            data_source=IMO_URL, data_updated_at=calendar.downloaded_at.isoformat(),
            event_facts=(
                ("activity", tr("Periodo di attività (UT)"), tr("{start} - {end}",
                    start=format_datetime(datetime.combine(shower.active_start, time(), UTC), include_time=False),
                    end=format_datetime(datetime.combine(shower.active_end, time(), UTC), include_time=False))),
                ("zhr", tr("ZHR di riferimento (condizioni ideali)"), shower.zhr),
            ),
        )
        local = (geometry or {}).get(shower.code)
        if local is not None and location is not None:
            event = _with_local_geometry(event, local, shower, now, weather_hours, location)
        result.append(event)
    return sorted(result, key=lambda event: event.event_at)


def _window_label(start, end, zone):
    start, end = start.astimezone(zone), end.astimezone(zone)
    if start.utcoffset() != end.utcoffset():
        return tr("{start} (UTC{start_offset}) – {end} (UTC{end_offset})",
                  start=format_datetime(start), end=format_datetime(end),
                  start_offset=start.strftime("%z"), end_offset=end.strftime("%z"))
    return tr("{start} – {end}", start=format_datetime(start.astimezone(zone)),
              end=format_datetime(end.astimezone(zone)))


def _with_local_geometry(event, geometry, shower, now, weather_hours, location):
    """Publish astronomy and forecast separately; never change the predicted peak."""
    utc_now = now.astimezone(UTC)
    zone = ZoneInfo(location.timezone)
    # Ceil the current time to the sampling grid: no expired/made-up minutes.
    lower = utc_now.replace(second=0, microsecond=0)
    if lower < utc_now or lower.minute % 5:
        lower += timedelta(minutes=5 - lower.minute % 5)
    windows = [remaining_window(window, max(window.start, lower)) for window in geometry.windows
               if window.end - max(window.start, lower) >= timedelta(minutes=30)]
    windows.sort(key=lambda window: (not window.favorable, -(window.end - window.start).total_seconds(),
                                     -window.radiant_max, window.start))
    end = datetime.combine(min(shower.active_end, shower.peak + timedelta(days=1)) + timedelta(days=1), time(), UTC)
    scope = tr("Notti vicine al massimo (±1 giorno UT), non l'intero periodo di attività. Orari locali: {zone}.", zone=location.timezone)
    note = tr("Il massimo IMO resta una data prevista, non un istante esatto. La finestra locale descrive la geometria del cielo, non un picco di meteore né una garanzia meteo.")
    if not windows:
        reasons = {
            "no_darkness": tr("Buio astronomico assente nelle notti analizzate."),
            "low_radiant": tr("Radiante sotto 15° durante il buio astronomico nelle notti analizzate."),
            "too_short": tr("Nessun intervallo continuo di almeno 30 minuti supera le soglie osservative."),
            "ok": tr("Le finestre calcolate sono terminate o restano meno di 30 minuti utili."),
            "unavailable": tr("Calcolo locale temporaneamente non disponibile."),
        }
        return replace(event, ends_at=end.isoformat(), note=note, period_note=scope,
                       observing_window=tr("Nessuna finestra astronomica utile") if geometry.reason != "unavailable" else tr("Da verificare"),
                       visibility_state="poor" if geometry.reason != "unavailable" else "check",
                       visibility_label=tr("Geometria sfavorevole") if geometry.reason != "unavailable" else tr("Da verificare"),
                       visibility_detail=reasons.get(geometry.reason, reasons["unavailable"]))
    best = windows[0]
    window_text = _window_label(best.start, best.end, zone)
    radiant = tr("{low}°–{high}°", low=format_number(best.radiant_min, decimals=0), high=format_number(best.radiant_max, decimals=0))
    moon = (tr("Sotto l'orizzonte per tutta la finestra") if best.moon_altitude_max <= -0.83
            else tr("Presente almeno in parte; illuminazione fino al {value}%", value=format_number(best.moon_illumination_max, decimals=0)))
    drift = (tr("Radiante interpolato dalla tabella annuale IMO.") if best.drift_used
             else tr("Radiante approssimato alla posizione del massimo IMO; deriva non disponibile per tutta la finestra."))
    detail = (tr("Buio astronomico, radiante almeno a 30° e Luna sotto l'orizzonte o illuminata al massimo al 25%. Meteo valutato separatamente.") if best.favorable
              else tr("Buio astronomico e radiante almeno a 15°; altezza ridotta o luce lunare limitano l'osservazione. Meteo valutato separatamente."))
    alternatives = []
    for window in sorted(windows[1:], key=lambda item: item.start):
        if window.favorable != best.favorable or (window.start <= best.start and window.end >= best.end):
            continue
        label = _window_label(window.start, window.end, zone)
        if label not in alternatives:
            alternatives.append(label)
    facts = event.event_facts + (
        ("radiant", tr("Altezza del radiante nella finestra"), radiant),
        ("moon", tr("Luna nella finestra"), moon),
        ("meteor_weather", tr("Meteo nella finestra astronomica"), _weather_text(best, weather_hours, location.timezone, now)),
    )
    wider = next((window for window in windows if not window.favorable and window.start <= best.start
                  and window.end >= best.end and window.end - window.start > best.end - best.start), None)
    if best.favorable and wider:
        facts += (("meteor_wider", tr("Finestra più ampia, con limiti di altezza o Luna"),
                   _window_label(wider.start, wider.end, zone)),)
    if alternatives:
        facts += (("meteor_alternatives", tr("Altre finestre astronomiche vicine al massimo"), join_text(alternatives)),)
    return replace(event, ends_at=end.isoformat(), note=note,
                   observing_window=window_text, period_note=join_text((scope, drift), separator=" "),
                   visibility_state="favorable" if best.favorable else "check",
                   visibility_label=tr("Geometria favorevole") if best.favorable else tr("Geometria limitata"),
                   visibility_detail=detail, event_facts=facts)


def _weather_text(window, hours, timezone, now):
    """Never bridge absent/ambiguous forecast hours or call merely usable 'good'."""
    # Neutral copies locate all valid forecast bins using the same DST/gap
    # policy as the planner. Original rows alone determine weather admission.
    neutral = [replace(hour, cloud_cover=0, precipitation_probability=0, wind_kmh=0, humidity=0) for hour in hours]
    coverage = usable_weather_intervals(neutral, None, timezone=timezone)
    usable = usable_weather_intervals(hours, None, timezone=timezone)
    intersections = [(max(start, window.start, now.astimezone(UTC)), min(end, window.end)) for start, end in usable]
    intersections = [(start, end) for start, end in intersections if end - start >= timedelta(minutes=30)]
    complete = any(start <= window.start and end >= window.end for start, end in coverage)
    overlaps = any(start < window.end and end > window.start for start, end in coverage)
    if not overlaps:
        return tr("Previsioni non disponibili per questa finestra; ricontrolla vicino alla data.")
    if intersections:
        intervals = join_text([_window_label(start, end, ZoneInfo(timezone)) for start, end in intersections])
        return (tr("Meteo utilizzabile: {windows}. Da riconfermare vicino all'osservazione.", windows=intervals) if complete
                else tr("Previsioni parziali; meteo utilizzabile: {windows}. Ore mancanti non valutate.", windows=intervals))
    return (tr("Meteo sfavorevole nella finestra astronomica secondo le previsioni disponibili.") if complete
            else tr("Previsioni parziali: nessuna apertura meteo utilizzabile nelle ore coperte; ore mancanti non valutate."))
