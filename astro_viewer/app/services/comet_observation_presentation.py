"""Explain COBS evidence and the exact scope of short-term brightness corrections."""

from __future__ import annotations

from astro_viewer.app.services.localization import format_datetime, format_number, join_text, tr


def observation_facts(assessment, snapshot, first_window) -> tuple:
    """Compact translated facts; heterogeneous photometry is never a visual mean."""
    rows = assessment.observations
    if not rows:
        return (("cobs_status", tr("Osservazioni COBS"),
                 tr("Nessuna osservazione recente utilizzabile; resta il modello JPL.")),)
    visual = sum(row.kind == "V" for row in rows)
    instrumental = len(rows) - visual
    last = max(row.observed_at for row in rows).astimezone(first_window.start.tzinfo)
    facts = [
        ("cobs_evidence", tr("Osservazioni COBS · ultimi 14 giorni"),
         tr("{visual} visuali, {instrumental} strumentali · ultima: {date}",
            visual=visual, instrumental=instrumental, date=format_datetime(last))),
    ]
    comparable = [row for row in rows if row.kind == "V" and row.method in {"S", "B", "M"}]
    if not comparable:
        comparable = [row for row in rows if row.kind == "C" and row.method == "Z"]
    if comparable:
        latest = max(comparable, key=lambda row: row.observed_at)
        facts.append(("cobs_last_estimate", tr("Ultima stima visuale COBS") if latest.kind == "V"
                      else tr("Ultima stima CCD equivalente visuale (Z)"),
                      tr("{magnitude} mag · {date} · {observer}. Singola misura, non una previsione.",
                         magnitude=format_number(latest.magnitude, decimals=1),
                         date=format_datetime(latest.observed_at.astimezone(first_window.start.tzinfo)),
                         observer=latest.observer or tr("n/d"))))
    calibration = assessment.calibration
    if calibration is None:
        reason = {
            "conflicting": tr("Serie visuali e strumentali discordanti; resta il modello JPL."),
            "unstable": tr("Luminosità discordante o variabile; resta il modello JPL, da verificare sul campo."),
            "stale": tr("Osservazioni troppo datate per correggere la previsione; resta il modello JPL."),
        }.get(assessment.reason, tr("Dati omogenei insufficienti per correggere la previsione; resta il modello JPL."))
        facts.append(("cobs_calibration", tr("Uso nelle raccomandazioni"), reason))
    else:
        family = tr("stime visuali") if calibration.family == "visual" else tr("CCD equivalente visuale, metodo Z")
        facts.append(("cobs_calibration", tr("Correzione della luminosità"),
                      tr("{offset} mag da {count} campioni osservatore/giorno, {observers} osservatori ({method}). Fino al {date}; oltre, modello JPL.",
                         offset=format_number(calibration.offset, decimals=1), count=calibration.count,
                         observers=calibration.observers, method=family,
                         date=format_datetime(calibration.valid_until.astimezone(first_window.start.tzinfo)))))
        if calibration.applies(first_window.peak):
            facts.append(("cobs_next_magnitude", tr("Luminosità nella prossima finestra"),
                          tr("circa {minimum}-{maximum} mag · stima corretta con COBS",
                             minimum=format_number(first_window.predicted_magnitude - calibration.margin, decimals=1),
                             maximum=format_number(first_window.predicted_magnitude + calibration.margin, decimals=1))))
        facts.append(("cobs_limit", tr("Limiti della correzione"),
                      tr("Selezione, notti utili e strumento tengono conto della luminosità corretta solo entro la sua validità. Il margine è prudenziale, non una garanzia di visibilità o una previsione di outburst.")))
    methods = sorted({row.method for row in rows if row.kind == "C" and row.method})
    if methods:
        facts.append(("cobs_methods", tr("Fotometria strumentale COBS"),
                      tr("Metodi: {methods}. Filtri e aperture differenti non sono mediati né equiparati alla visione all'oculare.",
                         methods=", ".join(methods))))
    facts.append(("cobs_credit", tr("Fonte delle osservazioni"), join_text((
        tr("COBS e osservatori contributori · CC BY-NC-SA 4.0 · elaborazione NightScope"),
        tr("Scaricato il {date}", date=format_datetime(snapshot.fetched_at.astimezone(first_window.start.tzinfo)))
        if snapshot.fetched_at else "",
    ), " · ")))
    return tuple(facts)
