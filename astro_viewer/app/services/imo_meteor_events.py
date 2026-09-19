"""Overlay validated annual meteor dates, leaving other astronomy/scoring untouched."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from astro_viewer.app.models.observing import AstronomicalEvent
from astro_viewer.app.services.imo_calendar import ImoCalendar, IMO_URL, SHOWER_IDS
from astro_viewer.app.services.localization import format_datetime, tr


_NAMES = {
    "QUA": tr("Quadrantidi"), "LYR": tr("Liridi"), "ETA": tr("Eta Aquaridi"),
    "SDA": tr("Delta Aquaridi meridionali"), "PER": tr("Perseidi"),
    "DRA": tr("Draconidi"), "ORI": tr("Orionidi"), "LEO": tr("Leonidi"),
    "GEM": tr("Geminidi"), "URS": tr("Ursidi"),
}


def annual_meteor_events(events: list[AstronomicalEvent], calendar: ImoCalendar | None,
                         now: datetime) -> list[AstronomicalEvent]:
    if calendar is None or not events:
        return events
    ids = {f"shower-{shower_id}-{calendar.year}" for shower_id in SHOWER_IDS.values()}
    result = [event for event in events if event.id not in ids]
    for shower in calendar.showers:
        # Noon UT is a sorting anchor only: the UI deliberately shows a DATE,
        # never this invented instant. Activity bounds are facts, not observing
        # windows; no local visibility or outburst prediction is manufactured.
        anchor = datetime.combine(shower.peak, time(12), UTC)
        if anchor.date() < now.astimezone(UTC).date() or anchor > now + timedelta(days=365):
            continue
        date_label = tr("{date} (UT)", date=format_datetime(anchor, include_time=False))
        result.append(AstronomicalEvent(
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
        ))
    return sorted(result, key=lambda event: event.event_at)
