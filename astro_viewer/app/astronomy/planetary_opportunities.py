"""Sample practical planetary seasons and multi-planet groups, not event instants.

Exact oppositions and pair minima remain owned by SkyfieldAstronomyEngine.
This optional, cached projection adds geometrical guidance only; no weather,
NSOM score, equipment selection or target eligibility is modified.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta
from itertools import combinations

import numpy as np

from astro_viewer.app.astronomy.engine import as_utc, advance_time
from astro_viewer.app.models.observing import AstronomicalEvent
from astro_viewer.app.services.localization import format_datetime, format_number, join_text, tr


BRIGHT_PLANETS = frozenset({"mercury", "venus", "mars", "jupiter", "saturn"})
MIN_ALTITUDE = 15.0
GROUP_SEPARATION = 6.0
SAMPLE_MINUTES = 60


@dataclass(frozen=True)
class PlanetaryNightGrid:
    times: tuple[datetime, ...]
    sun_altitude: np.ndarray
    altitude: dict[str, np.ndarray]
    direction: dict[str, np.ndarray]
    distance: dict[str, np.ndarray]

    def visible(self, ids: tuple[str, ...]) -> np.ndarray:
        limit = -6.0 if all(value in BRIGHT_PLANETS for value in ids) else -18.0
        mask = self.sun_altitude <= limit
        for object_id in ids:
            mask = mask & (self.altitude[object_id] >= MIN_ALTITUDE)
        return mask

    def separation(self, left: str, right: str) -> np.ndarray:
        cosine = np.sum(self.direction[left] * self.direction[right], axis=0)
        return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

    def useful_nights(self, mask: np.ndarray) -> set[int]:
        """Require two consecutive samples (>=1 hour), never bridge a gap."""
        result: set[int] = set()
        previous = None
        for index in np.flatnonzero(mask):
            current = self.times[index]
            night = (current - timedelta(hours=12)).date().toordinal()
            if previous is not None:
                previous_time, previous_night = previous
                elapsed = as_utc(current) - as_utc(previous_time)
                if previous_night == night and elapsed == timedelta(minutes=SAMPLE_MINUTES):
                    result.add(night)
            previous = current, night
        return result


def build_night_grid(engine, location, now: datetime, end: datetime) -> PlanetaryNightGrid:
    """Batch one annual grid; retain only numerical arrays, not Skyfield objects."""
    start = datetime.combine(now.date() - timedelta(days=90), time(12), now.tzinfo)
    stop = datetime.combine(end.date() + timedelta(days=1), time(12), now.tzinfo)
    times = []
    instant = start
    while as_utc(instant) <= as_utc(stop):
        times.append(instant)
        instant = advance_time(instant, timedelta(minutes=SAMPLE_MINUTES))
    sf_times = engine._timescale.from_datetimes(times)
    observer = engine._observer(location)
    sun_alt = np.asarray(observer.at(sf_times).observe(engine._ephemeris["sun"]).apparent().altaz()[0].degrees)
    # Daylight samples cannot qualify; omit their expensive planetary positions.
    keep = sun_alt <= -6.0
    local_times = tuple(value for value, retain in zip(times, keep, strict=True) if retain)
    sf_times = engine._timescale.from_datetimes(local_times) if local_times else None
    altitude, direction, distance = {}, {}, {}
    observer_at = observer.at(sf_times) if sf_times is not None else None
    for config in engine.BODY_CONFIGS:
        if config.object_id not in engine.PLANET_IDS:
            continue
        if observer_at is None:
            altitude[config.object_id] = np.empty(0)
            direction[config.object_id] = np.empty((3, 0))
            distance[config.object_id] = np.empty(0)
            continue
        apparent = observer_at.observe(engine._ephemeris[config.body_key]).apparent()
        altitude[config.object_id] = np.asarray(apparent.altaz()[0].degrees)
        lengths = np.asarray(apparent.distance().au)
        distance[config.object_id] = lengths
        direction[config.object_id] = np.asarray(apparent.position.au) / lengths
    return PlanetaryNightGrid(local_times, sun_alt[keep], altitude, direction, distance)


def night_periods(nights: set[int], zone) -> tuple[tuple[str, str], ...]:
    """ISO noon-to-noon bounds identifying consecutive observing nights."""
    groups: list[list[int]] = []
    for night in sorted(nights):
        if not groups or night != groups[-1][-1] + 1:
            groups.append([])
        groups[-1].append(night)
    return tuple(
        (datetime.combine(datetime.fromordinal(group[0]).date(), time(12), zone).isoformat(),
         datetime.combine(datetime.fromordinal(group[-1] + 1).date(), time(12), zone).isoformat())
        for group in groups
    )


def add_planetary_opportunities(engine, location, events, now: datetime, end: datetime):
    key = (location.latitude, location.longitude, location.timezone, now.date(), end.date())
    cached = getattr(engine, "_planetary_opportunity_cache", None)
    if cached is not None and cached[0] == key:
        grid = cached[1]
    else:
        grid = build_night_grid(engine, location, now, end)
        engine._planetary_opportunity_cache = key, grid
    ordinals = np.asarray([(value - timedelta(hours=12)).date().toordinal() for value in grid.times])
    enriched = []
    for event in events:
        ids = event.target_object_ids or ((event.target_object_id,) if event.target_object_id else ())
        if event.event_type not in {"Opposizione", "Congiunzione planetaria"} or not ids:
            enriched.append(event)
            continue
        instant = datetime.fromisoformat(event.event_at).astimezone(now.tzinfo)
        day = instant.date().toordinal()
        if any(value not in grid.altitude for value in ids):
            enriched.append(event)
            continue
        if event.event_type == "Congiunzione planetaria" and len(ids) != 2:
            enriched.append(event)
            continue
        mask = grid.visible(ids)
        if event.event_type == "Opposizione":
            around = np.abs(ordinals - day) <= 90
            distances = grid.distance[ids[0]]
            if np.any(around):
                nearest = float(np.min(distances[around]))
                mask &= around & (distances <= nearest / 0.95)
            else:
                mask &= False
            note = tr("Dimensione apparente almeno al 95% del massimo stimato vicino all'opposizione, con quota sopra 15° per almeno un'ora. Meteo da verificare.")
        else:
            limit = min(GROUP_SEPARATION, max(1.0, (event.angular_separation_deg or 0.0) + 2.0))
            mask &= (np.abs(ordinals - day) <= 30) & (grid.separation(*ids) <= limit)
            note = tr("Separazione entro {degrees}°, entrambi sopra 15° per almeno un'ora. Il massimo avvicinamento non è l'unica occasione; meteo da verificare.",
                      degrees=format_number(limit, decimals=1))
        nights = grid.useful_nights(mask)
        periods = night_periods(nights, now.tzinfo)
        if periods:
            notes = [note, tr("Le date indicano notti favorevoli, non visibilità continua.")]
            radius = 90 if event.event_type == "Opposizione" else 30
            if min(nights) <= max(day - radius, now.date().toordinal() - 90) or max(nights) >= min(day + radius, end.date().toordinal()):
                notes.append(tr("La finestra raggiunge il limite del periodo analizzato e potrebbe proseguire oltre."))
            note = join_text(notes, " ")
        else:
            note = tr("Nessun periodo favorevole secondo le soglie locali; resta valida l'eventuale finestra breve indicata.")
        analysis_end = min(end, instant + timedelta(days=90 if event.event_type == "Opposizione" else 30))
        enriched.append(replace(event, favorable_periods=periods, period_note=note,
                                analysis_end_at=analysis_end.isoformat()))
    enriched.extend(_multi_planet_events(engine, grid, now, end))
    # Retain a past exact event only while its practical season is still active.
    return [event for event in enriched if not event.event_at
            or datetime.fromisoformat(event.event_at).date() >= now.date()
            or any(as_utc(datetime.fromisoformat(finish)) > as_utc(now)
                   for _, finish in event.favorable_periods)]


def _multi_planet_events(engine, grid: PlanetaryNightGrid, now: datetime, end: datetime):
    ids = tuple(sorted(grid.altitude))
    dates_in_range = {value for value in range(now.date().toordinal() - 1, end.date().toordinal() + 1)}
    pair_masks = {pair: grid.separation(*pair) <= GROUP_SEPARATION for pair in combinations(ids, 2)}
    found: list[tuple[tuple[str, ...], set[int], str]] = []
    # Maximal compact groups, not chains A-B-C with distant endpoints A-C.
    for size in range(len(ids), 2, -1):
        for members in combinations(ids, size):
            mask = grid.visible(members)
            for pair in combinations(members, 2):
                mask &= pair_masks[pair]
            nights = grid.useful_nights(mask) & dates_in_range
            for larger, occupied, kind in found:
                if kind == "planetary_group" and set(members) < set(larger):
                    nights -= occupied
            if nights:
                found.append((members, nights, "planetary_group"))
    bright = tuple(value for value in ids if value in BRIGHT_PLANETS)
    # Four or more bright planets simultaneously visible: unlike a compact
    # grouping, a parade can span the sky and need not fit one optical field.
    for size in range(len(bright), 3, -1):
        for members in combinations(bright, size):
            nights = grid.useful_nights(grid.visible(members)) & dates_in_range
            for larger, occupied, _kind in found:
                if set(members) <= set(larger):
                    nights -= occupied
            if nights:
                found.append((members, nights, "planet_parade"))
    names = {config.object_id: config.name for config in engine.BODY_CONFIGS}
    result = []
    for members, nights, kind in found:
        name = join_text([names[member] for member in members], ", ")
        compact = kind == "planetary_group"
        note = (tr("Tre o più pianeti entro 6° fra ogni coppia, contemporaneamente sopra 15° per almeno un'ora.")
                if compact else tr("Quattro o più pianeti luminosi contemporaneamente sopra 15° per almeno un'ora; distribuiti nel cielo, non necessariamente ravvicinati."))
        for start, finish in night_periods(nights, now.tzinfo):
            first = datetime.fromisoformat(start)
            last = datetime.fromisoformat(finish) - timedelta(days=1)
            label = tr("{start} – {end}", start=format_datetime(first, include_time=False),
                       end=format_datetime(last, include_time=False))
            result.append(AstronomicalEvent(
                id=f"{kind}-{'-'.join(members)}-{first.date().isoformat()}",
                title=tr("Raggruppamento: {names}", names=name) if compact else tr("Parata: {names}", names=name),
                event_type="Raggruppamento planetario" if compact else "Parata planetaria",
                event_type_code=kind, date_label=label, best_time=label,
                usefulness=80 if compact else 70,
                setup=(tr("Binocolo o basso ingrandimento; verificare il campo inquadrato.")
                       if compact else tr("Occhio nudo; i pianeti non sono tutti nello stesso campo.")),
                note=note, event_at=start, starts_at=start, ends_at=finish,
                timing_kind="window", timing_label=tr("Periodo favorevole stimato"),
                observing_window=label, visibility_state="visible",
                visibility_label=tr("Finestra locale favorevole"), visibility_detail=note,
                target_object_id=members[0], target_object_ids=members,
                favorable_periods=((start, finish),),
                period_note=tr("Notti favorevoli stimate, non una finestra continua. Verificare il meteo della singola notte."),
                analysis_end_at=end.isoformat(),
            ))
    return result
