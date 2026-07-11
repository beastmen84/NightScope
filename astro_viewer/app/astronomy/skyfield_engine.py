from __future__ import annotations

import math
import logging
from calendar import monthrange
from dataclasses import dataclass, replace
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from skyfield import almanac, eclipselib, magnitudelib
from skyfield.api import Loader, Star, wgs84

from astro_viewer.app.astronomy.coordinates import parse_dec_degrees, parse_ra_hours
from astro_viewer.app.astronomy.engine import AstronomyEngine, ObserverLocation, ObservingNightWindow
from astro_viewer.app.database.messier_repository import MessierRepository
from astro_viewer.app.models.observing import (
    AstronomicalEvent,
    CelestialObject,
    MoonGeometrySummary,
    MoonSummary,
)


logger = logging.getLogger(__name__)

DEEP_SKY_USEFUL_ALTITUDE_DEG = 15.0
CATALOGUE_MONTH_SAMPLE_MINUTES = 60


class EphemerisUnavailableError(RuntimeError):
    """Raised when Skyfield ephemeris data cannot be loaded or recovered."""


@dataclass(frozen=True)
class SolarSystemBodyConfig:
    object_id: str
    name: str
    body_key: str
    object_type: str
    image: str


def _italian_lunar_eclipse_kind(kind_name: str) -> str:
    return {
        "total": "totale",
        "partial": "parziale",
        "penumbral": "penombrale",
    }.get(kind_name.strip().lower(), kind_name.strip().lower())


class SkyfieldAstronomyEngine(AstronomyEngine):
    """Skyfield-backed astronomy service for Solar System and Messier visibility."""

    BODY_CONFIGS = [
        SolarSystemBodyConfig("sun", "Sole", "sun", "Stella", "resources/images/sun.svg"),
        SolarSystemBodyConfig("moon", "Luna", "moon", "Satellite naturale", "resources/images/moon.svg"),
        SolarSystemBodyConfig("mercury", "Mercurio", "mercury", "Pianeta", "resources/images/mercury.svg"),
        SolarSystemBodyConfig("venus", "Venere", "venus", "Pianeta", "resources/images/venus.svg"),
        SolarSystemBodyConfig("mars", "Marte", "mars", "Pianeta", "resources/images/mars.svg"),
        SolarSystemBodyConfig("jupiter", "Giove", "jupiter barycenter", "Pianeta", "resources/images/jupiter.svg"),
        SolarSystemBodyConfig("saturn", "Saturno", "saturn barycenter", "Pianeta", "resources/images/saturn.svg"),
        SolarSystemBodyConfig("uranus", "Urano", "uranus barycenter", "Pianeta", "resources/images/uranus.svg"),
        SolarSystemBodyConfig("neptune", "Nettuno", "neptune barycenter", "Pianeta", "resources/images/neptune.svg"),
    ]

    PLANET_IDS = {"mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune"}

    def __init__(self, data_dir: Path, messier_repository: MessierRepository):
        self._data_dir = data_dir
        self._messier_repository = messier_repository
        self._loader = Loader(str(data_dir / "skyfield"))
        self._timescale = self._loader.timescale()
        self._ephemeris = self._load_ephemeris()
        self._night_window_cache: dict[
            tuple[float, float, str],
            tuple[datetime, ObservingNightWindow],
        ] = {}
        self._messier_star_cache: dict[str, Star | None] = {}

    def _load_ephemeris(self):
        ephemeris_path = self._data_dir / "skyfield" / "de421.bsp"
        try:
            return self._loader("de421.bsp")
        except Exception:
            logger.warning("Skyfield ephemeris could not be loaded.", exc_info=True)
            if ephemeris_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                quarantine_path = ephemeris_path.with_suffix(ephemeris_path.suffix + f".corrupt-{timestamp}.bak")
                try:
                    ephemeris_path.replace(quarantine_path)
                    logger.warning("Corrupt ephemeris was quarantined.")
                except OSError:
                    logger.warning("Corrupt ephemeris could not be quarantined.", exc_info=True)
            try:
                return self._loader("de421.bsp")
            except Exception as retry_exc:
                logger.error("Skyfield ephemeris recovery failed.", exc_info=True)
                raise EphemerisUnavailableError(
                    "Effemeridi astronomiche non disponibili. Controlla la connessione o ripristina de421.bsp."
                ) from retry_exc

    def solar_system_objects(self, location: ObserverLocation) -> list[CelestialObject]:
        now = self._now(location)
        night_window = self.observing_night_window(location, reference=now)
        return [
            self._body_details(config, location, now=now, night_window=night_window)
            for config in self.BODY_CONFIGS
        ]

    def close(self) -> None:
        close_method = getattr(self._ephemeris, "close", None)
        if callable(close_method):
            close_method()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def visible_planets(self, location: ObserverLocation) -> list[CelestialObject]:
        return [
            item
            for item in self.solar_system_objects(location)
            if item.id in self.PLANET_IDS and item.visible
        ]

    def observing_night_window(
        self,
        location: ObserverLocation,
        reference: datetime | None = None,
    ) -> ObservingNightWindow:
        zone = self._zone(location)
        now = reference.astimezone(zone) if reference else self._now(location)
        cache_key = (round(location.latitude, 6), round(location.longitude, 6), location.timezone)
        cached = getattr(self, "_night_window_cache", {}).get(cache_key)
        if cached is not None and self._night_window_cache_is_current(cached, now):
            return cached[1]
        topos = wgs84.latlon(latitude_degrees=location.latitude, longitude_degrees=location.longitude)
        daylight_at = almanac.sunrise_sunset(self._ephemeris, topos)
        search_start = now - timedelta(hours=36)
        search_end = now + timedelta(hours=72)
        try:
            times, states = almanac.find_discrete(
                self._to_skyfield_time(search_start),
                self._to_skyfield_time(search_end),
                daylight_at,
            )
            events = [
                (event_time.utc_datetime().astimezone(zone), bool(state))
                for event_time, state in zip(times, states)
            ]
            is_daylight = bool(daylight_at(self._to_skyfield_time(now)))
        except Exception:
            logger.warning("Skyfield night-window calculation failed.", exc_info=True)
            return self._cache_night_window(cache_key, now, ObservingNightWindow.unavailable())

        sunsets = [event_time for event_time, daylight in events if not daylight]
        sunrises = [event_time for event_time, daylight in events if daylight]
        if is_daylight:
            sunset = next((event_time for event_time in sunsets if event_time > now), None)
            if sunset is None:
                return self._cache_night_window(cache_key, now, ObservingNightWindow.no_night())
            sunrise = next((event_time for event_time in sunrises if event_time > sunset), None)
            if sunrise is None:
                return self._cache_night_window(
                    cache_key,
                    now,
                    ObservingNightWindow.continuous_night(sunset),
                )
            return self._cache_night_window(
                cache_key,
                now,
                ObservingNightWindow.bounded(sunset, sunrise),
            )

        sunset = next((event_time for event_time in reversed(sunsets) if event_time <= now), None)
        sunrise = next((event_time for event_time in sunrises if event_time > now), None)
        if sunset is not None and sunrise is not None:
            return self._cache_night_window(
                cache_key,
                now,
                ObservingNightWindow.bounded(sunset, sunrise),
            )
        if sunrise is not None:
            return self._cache_night_window(
                cache_key,
                now,
                ObservingNightWindow.continuous_night(now, sunrise),
            )
        return self._cache_night_window(
            cache_key,
            now,
            ObservingNightWindow.continuous_night(sunset or now),
        )

    def _cache_night_window(
        self,
        key: tuple[float, float, str],
        calculated_at: datetime,
        window: ObservingNightWindow,
    ) -> ObservingNightWindow:
        cache = getattr(self, "_night_window_cache", None)
        if cache is None:
            cache = {}
            self._night_window_cache = cache
        cache[key] = (calculated_at, window)
        return window

    @staticmethod
    def _night_window_cache_is_current(
        cached: tuple[datetime, ObservingNightWindow],
        reference: datetime,
    ) -> bool:
        calculated_at, window = cached
        if reference < calculated_at:
            return False
        if window.has_observing_window:
            return reference < window.end
        return reference - calculated_at < timedelta(minutes=30)

    def recommended_deep_sky(self, location: ObserverLocation) -> list[CelestialObject]:
        now = self._now(location)
        night_window = self.observing_night_window(location, reference=now)
        candidates = []
        for row in self._messier_repository.list_objects():
            try:
                dec_degrees = parse_dec_degrees(row["dec"])
                theoretical_max_altitude = 90.0 - abs(location.latitude - dec_degrees)
                if theoretical_max_altitude < 12.0:
                    continue
                magnitude = row["magnitude"] if row["magnitude"] is not None else 10.0
                cheap_score = self._object_score(theoretical_max_altitude, magnitude, row["object_type"], True)
                candidates.append((cheap_score, row, dec_degrees))
            except ValueError:
                continue
        objects = []
        for _, row, dec_degrees in sorted(candidates, key=lambda item: item[0], reverse=True):
            try:
                objects.append(
                    self._messier_details(
                        row,
                        location,
                        dec_degrees=dec_degrees,
                        now=now,
                        night_window=night_window,
                    )
                )
            except ValueError:
                continue
        visible = [item for item in objects if item.visible]
        return sorted(visible, key=lambda item: item.score, reverse=True)

    def refresh_current_positions(
        self,
        objects: list[CelestialObject],
        location: ObserverLocation,
    ) -> list[CelestialObject]:
        if not objects:
            return objects
        now = self._now(location)
        observer = self._observer(location)
        current_time = self._to_skyfield_time(now)
        night_window = self.observing_night_window(location, reference=now)
        is_observing_night = night_window.contains(now)
        body_configs = {config.object_id: config for config in self.BODY_CONFIGS}
        updated = []
        for item in objects:
            try:
                position = self._current_position(item, observer, current_time, body_configs)
            except Exception:
                logger.debug("Sky Compass live position update skipped for %s.", item.id, exc_info=True)
                position = None
            if position is None:
                updated.append(item)
                continue
            altitude_degrees, azimuth_degrees = position
            observable_now = is_observing_night and altitude_degrees >= self._geometry_altitude_threshold(item)
            updated.append(
                replace(
                    item,
                    direction=self._azimuth_direction(azimuth_degrees),
                    azimuth=f"{azimuth_degrees:.0f} gradi",
                    current_altitude=f"{altitude_degrees:.1f} gradi",
                    current_azimuth=f"{azimuth_degrees:.1f} gradi",
                    observable_now=observable_now,
                    current_altitude_degrees=altitude_degrees,
                    current_azimuth_degrees=azimuth_degrees,
                )
            )
        return updated

    def _current_position(self, item: CelestialObject, observer, current_time, body_configs: dict):
        config = body_configs.get(item.id)
        if config is not None:
            body = self._ephemeris[config.body_key]
        else:
            body = self._star_for_current_position(item)
        if body is None:
            return None
        altitude, azimuth, _ = observer.at(current_time).observe(body).apparent().altaz()
        return float(altitude.degrees), float(azimuth.degrees)

    def _star_for_current_position(self, item: CelestialObject):
        if not item.id.startswith("messier-"):
            return None
        cached = self._messier_star_cache.get(item.id)
        if item.id in self._messier_star_cache:
            return cached
        messier_id = item.id.removeprefix("messier-").upper()
        row = self._messier_repository.get_by_messier_id(messier_id)
        if not row:
            self._messier_star_cache[item.id] = None
            return None
        star = Star(ra_hours=parse_ra_hours(row["ra"]), dec_degrees=parse_dec_degrees(row["dec"]))
        self._messier_star_cache[item.id] = star
        return star

    def _geometry_target_body(self, target: CelestialObject):
        body_configs = {config.object_id: config for config in self.BODY_CONFIGS}
        config = body_configs.get(target.id)
        if config is not None:
            return self._ephemeris[config.body_key]
        return self._star_for_current_position(target)

    @staticmethod
    def _geometry_altitude_threshold(target: CelestialObject) -> float:
        lower_type = target.object_type.lower()
        if (
            target.id
            in {
                "sun",
                "moon",
                "mercury",
                "venus",
                "mars",
                "jupiter",
                "saturn",
                "uranus",
                "neptune",
            }
            or "pianeta" in lower_type
            or "planet" in lower_type
        ):
            return 8.0
        return DEEP_SKY_USEFUL_ALTITUDE_DEG

    def catalogue_month_visibility(
        self,
        catalogue_objects: list[dict],
        location: ObserverLocation,
        year: int,
        month: int,
        altitude_threshold: float = DEEP_SKY_USEFUL_ALTITUDE_DEG,
    ) -> dict[str, bool]:
        observer = self._observer(location)
        zone = self._zone(location)
        samples = self._month_dark_samples(location, year, month, zone, step_minutes=CATALOGUE_MONTH_SAMPLE_MINUTES)
        daylight_samples = self._month_day_samples(year, month, zone, step_minutes=CATALOGUE_MONTH_SAMPLE_MINUTES)
        visibility: dict[str, bool] = {}
        body_configs = {config.object_id: config for config in self.BODY_CONFIGS}

        for item in catalogue_objects:
            object_key = self._catalogue_visibility_key(item)
            if not object_key:
                continue
            visibility[object_key] = False
            solar_system_body_id = str(item.get("solar_system_body_id") or "").strip()
            if solar_system_body_id:
                config = body_configs.get(solar_system_body_id)
                if not config:
                    continue
                body = self._ephemeris[config.body_key]
                body_samples = daylight_samples if solar_system_body_id == "sun" else samples
                visibility[object_key] = self._reaches_altitude_threshold(
                    observer,
                    body,
                    body_samples,
                    threshold=altitude_threshold,
                )
                continue
            try:
                ra_hours = parse_ra_hours(str(item.get("ra") or item.get("right_ascension") or ""))
                dec_degrees = parse_dec_degrees(str(item.get("dec") or item.get("declination") or ""))
            except ValueError:
                continue
            theoretical_max_altitude = 90.0 - abs(location.latitude - dec_degrees)
            if theoretical_max_altitude < altitude_threshold:
                continue
            star = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)
            visibility[object_key] = self._reaches_altitude_threshold(
                observer,
                star,
                samples,
                threshold=altitude_threshold,
            )
        return visibility

    def moon_summary(self, location: ObserverLocation) -> MoonSummary:
        now = self._now(location)
        skyfield_time = self._to_skyfield_time(now)
        phase_angle = almanac.moon_phase(self._ephemeris, skyfield_time).degrees
        illumination = (1.0 - math.cos(math.radians(phase_angle))) / 2.0
        night_window = self.observing_night_window(location, reference=now)
        moon_details = self._body_details(
            SolarSystemBodyConfig("moon", "Luna", "moon", "Satellite naturale", "resources/images/moon.svg"),
            location,
            now=now,
            night_window=night_window,
        )
        return MoonSummary(
            phase=self._moon_phase_name(phase_angle),
            illumination=f"{illumination * 100:.0f}%",
            rise_time=moon_details.rise_time,
            set_time=moon_details.set_time,
            best_note=self._moon_observing_note(illumination),
            image="resources/images/moon.svg",
            phase_angle=round(phase_angle, 1),
        )

    def moon_geometry(self, location: ObserverLocation, target: CelestialObject) -> MoonGeometrySummary | None:
        """Compute bounded local Moon-target geometry diagnostics without scoring."""

        return self.moon_geometry_batch(location, [target]).get(target.id)

    def moon_geometry_batch(
        self,
        location: ObserverLocation,
        targets: list[CelestialObject],
    ) -> dict[str, MoonGeometrySummary | None]:
        """Compute Moon geometry on one shared observing-night timeline."""

        results: dict[str, MoonGeometrySummary | None] = {target.id: None for target in targets}
        if not targets:
            return results
        now = self._now(location)
        observer = self._observer(location)
        moon_body = self._ephemeris["moon"]
        night_window = self.observing_night_window(location, reference=now)
        if not night_window.has_observing_window:
            return results
        samples = self._datetime_samples(night_window.start, night_window.end, step_minutes=30)
        if not samples:
            return results
        times = self._timescale.from_datetimes([sample.astimezone(UTC) for sample in samples])
        observer_at = observer.at(times)
        moon_apparent = observer_at.observe(moon_body).apparent()
        moon_altitudes = dict(
            zip(samples, [float(value) for value in moon_apparent.altaz()[0].degrees])
        )

        for target in targets:
            try:
                target_body = self._geometry_target_body(target)
                if target_body is None:
                    continue
                target_apparent = observer_at.observe(target_body).apparent()
                target_altitudes = dict(
                    zip(samples, [float(value) for value in target_apparent.altaz()[0].degrees])
                )
                separations = dict(
                    zip(
                        samples,
                        [float(value) for value in moon_apparent.separation_from(target_apparent).degrees],
                    )
                )
                results[target.id] = self._moon_geometry_summary_from_samples(
                    target,
                    samples,
                    moon_altitudes,
                    target_altitudes,
                    separations,
                )
            except Exception:
                logger.debug("Moon geometry batch skipped target %s.", target.id, exc_info=True)
        return results

    def _moon_geometry_summary_from_samples(
        self,
        target: CelestialObject,
        samples: list[datetime],
        moon_altitudes: dict[datetime, float],
        target_altitudes: dict[datetime, float],
        separations: dict[datetime, float],
    ) -> MoonGeometrySummary | None:
        target_samples = [(sample, target_altitudes[sample]) for sample in samples]

        threshold = self._geometry_altitude_threshold(target)
        visible_target_samples = [
            (sample_time, altitude)
            for sample_time, altitude in target_samples
            if altitude >= threshold
        ]
        meaningful_samples = visible_target_samples or target_samples
        sample_times = self._bounded_moon_geometry_sample_times(meaningful_samples)
        if not sample_times:
            return None
        if not moon_altitudes or not separations:
            return None

        target_visible_times = [
            sample_time
            for sample_time in sample_times
            if target_altitudes.get(sample_time, -90.0) >= threshold
        ]
        representative_times = target_visible_times or sample_times
        moon_altitude = max(moon_altitudes[sample_time] for sample_time in representative_times)
        moon_target_separation = min(separations[sample_time] for sample_time in representative_times)
        moon_above_horizon = any(
            moon_altitudes[sample_time] > 0.0 for sample_time in representative_times
        )
        moon_visible_during_target_window = any(
            moon_altitudes[sample_time] > 0.0
            and target_altitudes.get(sample_time, -90.0) >= threshold
            for sample_time in sample_times
        )
        moon_set_before_target_window = self._moon_set_before_target_window(
            moon_altitudes,
            visible_target_samples,
        )

        return MoonGeometrySummary(
            object_id=target.id,
            moon_altitude_deg=round(float(moon_altitude), 2),
            moon_target_separation_deg=round(float(moon_target_separation), 2),
            moon_above_horizon=moon_above_horizon,
            moon_visible_during_target_window=moon_visible_during_target_window,
            moon_set_before_target_window=moon_set_before_target_window,
            sample_count=len(sample_times),
            sampled_at=self._format_dt(max(representative_times, key=lambda sample: moon_altitudes[sample])),
            sample_times=tuple(self._format_dt(sample_time) for sample_time in sample_times),
        )

    def upcoming_events(self, location: ObserverLocation) -> list[AstronomicalEvent]:
        now = self._now(location)
        start = self._to_skyfield_time(now)
        end = self._to_skyfield_time(now + timedelta(days=365))
        events: list[AstronomicalEvent] = []

        moon_times, moon_indices = almanac.find_discrete(start, self._to_skyfield_time(now + timedelta(days=90)), almanac.moon_phases(self._ephemeris))
        for event_time, index in zip(moon_times, moon_indices):
            phase_name = self._moon_phase_event_name(int(index))
            usefulness = 95 if int(index) == 0 else 42 if int(index) == 2 else 68
            events.append(
                AstronomicalEvent(
                    id=f"moon-{event_time.tt}",
                    title=phase_name,
                    event_type="Luna",
                    date_label=self._format_date(event_time.utc_datetime().astimezone(self._zone(location))),
                    best_time=self._format_dt(event_time.utc_datetime().astimezone(self._zone(location))),
                    usefulness=usefulness,
                    setup="Qualsiasi setup",
                    note="Evento calcolato con Skyfield.",
                )
            )

        for config in self.BODY_CONFIGS:
            if config.object_id not in {"mars", "jupiter", "saturn", "uranus", "neptune"}:
                continue
            body = self._ephemeris[config.body_key]
            function = almanac.oppositions_conjunctions(self._ephemeris, body)
            times, kinds = almanac.find_discrete(start, end, function)
            for event_time, kind in zip(times, kinds):
                is_opposition = int(kind) == 1
                events.append(
                    AstronomicalEvent(
                        id=f"{config.object_id}-{int(kind)}-{event_time.tt}",
                        title=f"{config.name} in {'opposizione' if is_opposition else 'congiunzione'}",
                        event_type="Opposizione" if is_opposition else "Congiunzione",
                        date_label=self._format_date(event_time.utc_datetime().astimezone(self._zone(location))),
                        best_time=self._format_dt(event_time.utc_datetime().astimezone(self._zone(location))),
                        usefulness=92 if is_opposition else 38,
                        setup="Telescopio medio" if is_opposition else "Non prioritario",
                        note="Calcolato dalla longitudine eclittica relativa al Sole.",
                    )
                )

        eclipse_times, eclipse_kinds, _ = eclipselib.lunar_eclipses(start, self._to_skyfield_time(now + timedelta(days=730)), self._ephemeris)
        for eclipse_time, eclipse_kind in zip(eclipse_times, eclipse_kinds):
            kind_name = eclipselib.LUNAR_ECLIPSES[int(eclipse_kind)]
            eclipse_label = _italian_lunar_eclipse_kind(kind_name)
            local_dt = eclipse_time.utc_datetime().astimezone(self._zone(location))
            events.append(
                AstronomicalEvent(
                    id=f"lunar-eclipse-{eclipse_time.tt}",
                    title=f"Eclissi lunare {eclipse_label}",
                    event_type="Eclissi",
                    date_label=self._format_date(local_dt),
                    best_time=self._format_dt(local_dt),
                    usefulness=86 if int(eclipse_kind) >= 1 else 62,
                    setup="Occhio nudo o teleobiettivo",
                    note="Evento calcolato con Skyfield; visibilità locale da verificare sull'orizzonte.",
                )
            )

        events.extend(self._recurring_meteor_showers(now))
        return sorted(events, key=lambda event: (event.usefulness, event.date_label), reverse=True)[:18]

    def _body_details(
        self,
        config: SolarSystemBodyConfig,
        location: ObserverLocation,
        *,
        now: datetime | None = None,
        night_window: ObservingNightWindow | None = None,
    ) -> CelestialObject:
        now = now or self._now(location)
        night_window = night_window or self.observing_night_window(location, reference=now)
        zone = self._zone(location)
        observer = self._observer(location)
        body = self._ephemeris[config.body_key]
        current_time = self._to_skyfield_time(now)
        astrometric = observer.at(current_time).observe(body)
        apparent = astrometric.apparent()
        altitude, azimuth, distance = apparent.altaz()

        rise_time, culmination, set_time = self._ordered_event_labels(observer, body, now, zone)
        sample = (
            self._sample_altitudes(observer, body, night_window.start, night_window.end)
            if night_window.has_observing_window
            else []
        )
        max_altitude, best_dt, observing_window = self._sample_summary(sample, threshold=8.0)
        magnitude = self._magnitude(astrometric, config.object_id)
        visible = altitude.degrees > 0.0 or max_altitude > 8.0
        observable_now = self._is_observable_now(night_window, now, altitude.degrees, threshold=8.0)
        score = self._object_score(max_altitude, magnitude, config.object_type, visible)

        return CelestialObject(
            id=config.object_id,
            name=config.name,
            object_type=config.object_type,
            image=config.image,
            magnitude=self._format_magnitude(magnitude),
            distance=self._format_distance(distance.au, config.object_id),
            max_altitude=f"{max_altitude:.0f} gradi",
            direction=self._azimuth_direction(azimuth.degrees),
            best_time=self._format_dt(best_dt) if best_dt else culmination,
            observing_window=observing_window,
            notes=self._body_note(config.object_id, max_altitude),
            recommended_setup=self._default_setup(config.object_id),
            visibility_class=self._visibility_class(magnitude, config.object_id),
            azimuth=f"{azimuth.degrees:.0f} gradi",
            time_above_horizon=self._window_duration(observing_window),
            visible=visible,
            rise_time=rise_time,
            set_time=set_time,
            culmination_time=culmination,
            current_altitude=f"{altitude.degrees:.1f} gradi",
            current_azimuth=f"{azimuth.degrees:.1f} gradi",
            observable_now=observable_now,
            current_altitude_degrees=float(altitude.degrees),
            current_azimuth_degrees=float(azimuth.degrees),
            score=score,
            score_label=self._score_label(score),
            score_explanation=f"Altezza massima {max_altitude:.0f} gradi e magnitudine {self._format_magnitude(magnitude)}.",
        )

    def _messier_details(
        self,
        row: dict,
        location: ObserverLocation,
        dec_degrees: float | None = None,
        *,
        now: datetime | None = None,
        night_window: ObservingNightWindow | None = None,
    ) -> CelestialObject:
        ra_hours = parse_ra_hours(row["ra"])
        dec_degrees = dec_degrees if dec_degrees is not None else parse_dec_degrees(row["dec"])
        star = Star(ra_hours=ra_hours, dec_degrees=dec_degrees)
        now = now or self._now(location)
        night_window = night_window or self.observing_night_window(location, reference=now)
        observer = self._observer(location)
        current_time = self._to_skyfield_time(now)
        apparent = observer.at(current_time).observe(star).apparent()
        altitude, azimuth, _ = apparent.altaz()
        sample = (
            self._sample_altitudes(
                observer,
                star,
                night_window.start,
                night_window.end,
                step_minutes=30,
            )
            if night_window.has_observing_window
            else []
        )
        max_altitude, best_dt, observing_window = self._sample_summary(sample, threshold=DEEP_SKY_USEFUL_ALTITUDE_DEG)
        magnitude = row["magnitude"]
        visible = max_altitude >= DEEP_SKY_USEFUL_ALTITUDE_DEG
        observable_now = self._is_observable_now(
            night_window,
            now,
            altitude.degrees,
            threshold=DEEP_SKY_USEFUL_ALTITUDE_DEG,
        )
        score = self._object_score(max_altitude, magnitude, row["object_type"], visible)
        setup = self._deep_sky_setup(row["object_type"], magnitude)

        return CelestialObject(
            id=f"messier-{row['messier_id']}",
            name=f"{row['messier_id']} {row['name']}" if row["name"] != row["messier_id"] else row["messier_id"],
            object_type=row["object_type"],
            image=self._messier_image(row["messier_id"], row["object_type"]),
            magnitude=self._format_magnitude(magnitude),
            distance="Catalogo Messier",
            max_altitude=f"{max_altitude:.0f} gradi",
            direction=self._azimuth_direction(azimuth.degrees),
            best_time=self._format_dt(best_dt) if best_dt else "n/d",
            observing_window=observing_window,
            notes=row["description"],
            recommended_setup=setup,
            visibility_class=self._deep_sky_visibility_class(magnitude),
            azimuth=f"{azimuth.degrees:.0f} gradi",
            time_above_horizon=self._window_duration(observing_window),
            visible=visible,
            rise_time="calcolato da finestra",
            set_time="calcolato da finestra",
            culmination_time=self._format_dt(best_dt) if best_dt else "n/d",
            current_altitude=f"{altitude.degrees:.1f} gradi",
            current_azimuth=f"{azimuth.degrees:.1f} gradi",
            observable_now=observable_now,
            current_altitude_degrees=float(altitude.degrees),
            current_azimuth_degrees=float(azimuth.degrees),
            score=score,
            score_label=self._score_label(score),
            score_explanation=f"Massima altezza {max_altitude:.0f} gradi; magnitudine {self._format_magnitude(magnitude)}.",
            apparent_size=row.get("apparent_size") or "",
            max_angular_size_deg=row.get("max_angular_size_deg"),
            recommended_observation_type=row.get("recommended_observation_type") or "",
        )

    def _observer(self, location: ObserverLocation):
        topos = wgs84.latlon(latitude_degrees=location.latitude, longitude_degrees=location.longitude)
        return self._ephemeris["earth"] + topos

    def _to_skyfield_time(self, value: datetime):
        return self._timescale.from_datetime(value.astimezone(UTC))

    def _now(self, location: ObserverLocation) -> datetime:
        return datetime.now(self._zone(location))

    def _zone(self, location: ObserverLocation) -> ZoneInfo:
        try:
            return ZoneInfo(location.timezone)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    @staticmethod
    def _is_observable_now(
        night_window: ObservingNightWindow,
        now: datetime,
        altitude_degrees: float,
        *,
        threshold: float,
    ) -> bool:
        return night_window.contains(now) and altitude_degrees >= threshold

    def _sample_altitudes(
        self,
        observer,
        body,
        start: datetime,
        end: datetime,
        step_minutes: int = 15,
    ) -> list[tuple[datetime, float]]:
        return self._altitudes_for_samples(
            observer,
            body,
            self._datetime_samples(start, end, step_minutes=step_minutes),
        )

    @staticmethod
    def _datetime_samples(
        start: datetime,
        end: datetime,
        *,
        step_minutes: int,
    ) -> list[datetime]:
        samples: list[datetime] = []
        current = start
        while current <= end:
            samples.append(current)
            current += timedelta(minutes=step_minutes)
        if samples and samples[-1] < end:
            samples.append(end)
        return samples

    def _altitudes_for_samples(self, observer, body, samples: list[datetime]) -> list[tuple[datetime, float]]:
        if not samples:
            return []
        times = self._timescale.from_datetimes([sample.astimezone(UTC) for sample in samples])
        altitudes, _, _ = observer.at(times).observe(body).apparent().altaz()
        return list(zip(samples, [float(value) for value in altitudes.degrees]))

    @staticmethod
    def _bounded_moon_geometry_sample_times(
        samples: list[tuple[datetime, float]],
    ) -> list[datetime]:
        if not samples:
            return []
        ordered = sorted(samples, key=lambda item: item[0])
        start_time = ordered[0][0]
        end_time = ordered[-1][0]
        best_time = max(ordered, key=lambda item: item[1])[0]
        midpoint = start_time + (end_time - start_time) / 2
        mid_time = min(ordered, key=lambda item: abs((item[0] - midpoint).total_seconds()))[0]
        result: list[datetime] = []
        for sample_time in (start_time, mid_time, best_time, end_time):
            if sample_time not in result:
                result.append(sample_time)
        return result

    @staticmethod
    def _moon_set_before_target_window(
        moon_altitudes: dict[datetime, float],
        visible_target_samples: list[tuple[datetime, float]],
    ) -> bool | None:
        if not visible_target_samples:
            return None
        first_target_time = min(sample_time for sample_time, _altitude in visible_target_samples)
        last_target_time = max(sample_time for sample_time, _altitude in visible_target_samples)
        moon_above_before = any(
            sample_time < first_target_time and altitude > 0.0
            for sample_time, altitude in moon_altitudes.items()
        )
        moon_above_during = any(
            first_target_time <= sample_time <= last_target_time and altitude > 0.0
            for sample_time, altitude in moon_altitudes.items()
        )
        return moon_above_before and not moon_above_during

    def _month_dark_samples(
        self,
        location: ObserverLocation,
        year: int,
        month: int,
        zone: ZoneInfo,
        step_minutes: int,
    ) -> list[datetime]:
        candidates: list[datetime] = []
        for day in range(1, monthrange(year, month)[1] + 1):
            current = datetime(year, month, day, 0, 0, tzinfo=zone)
            end = current + timedelta(hours=24)
            while current < end:
                candidates.append(current)
                current += timedelta(minutes=step_minutes)
        if not candidates:
            return []
        topos = wgs84.latlon(latitude_degrees=location.latitude, longitude_degrees=location.longitude)
        twilight_at = almanac.dark_twilight_day(self._ephemeris, topos)
        times = self._timescale.from_datetimes([sample.astimezone(UTC) for sample in candidates])
        states = twilight_at(times)
        return [sample for sample, state in zip(candidates, states) if int(state) == 0]

    @staticmethod
    def _month_day_samples(
        year: int,
        month: int,
        zone: ZoneInfo,
        step_minutes: int,
    ) -> list[datetime]:
        samples: list[datetime] = []
        for day in range(1, monthrange(year, month)[1] + 1):
            current = datetime(year, month, day, 6, 0, tzinfo=zone)
            end = current + timedelta(hours=12)
            while current <= end:
                samples.append(current)
                current += timedelta(minutes=step_minutes)
        return samples

    def _reaches_altitude_threshold(
        self,
        observer,
        body,
        samples: list[datetime],
        threshold: float,
    ) -> bool:
        return any(altitude >= threshold for _, altitude in self._altitudes_for_samples(observer, body, samples))

    @staticmethod
    def _catalogue_visibility_key(item: dict) -> str:
        for key in ("object_id", "id", "catalogue_id", "messier_id"):
            value = item.get(key)
            if value is not None and str(value).strip():
                return str(value)
        return ""

    def _sample_summary(self, samples: list[tuple[datetime, float]], threshold: float) -> tuple[float, datetime | None, str]:
        if not samples:
            return 0.0, None, "n/d"

        ordered = sorted(samples, key=lambda item: item[0])
        usable_samples = ordered[:-1] if len(ordered) > 1 else ordered
        best_dt, max_altitude = max(usable_samples, key=lambda item: item[1])
        if max_altitude < threshold:
            return max_altitude, best_dt, "Non sopra la soglia osservativa"

        best_index = ordered.index((best_dt, max_altitude))
        first_index = best_index
        while first_index > 0 and ordered[first_index - 1][1] >= threshold:
            first_index -= 1
        last_index = best_index
        while last_index + 1 < len(ordered) and ordered[last_index + 1][1] >= threshold:
            last_index += 1

        start_dt = ordered[first_index][0]
        if first_index > 0:
            start_dt = self._threshold_crossing(
                ordered[first_index - 1],
                ordered[first_index],
                threshold,
            )

        end_dt = ordered[last_index][0]
        if last_index + 1 < len(ordered):
            end_dt = self._threshold_crossing(
                ordered[last_index],
                ordered[last_index + 1],
                threshold,
            )

        if end_dt <= start_dt:
            return max_altitude, best_dt, "Non sopra la soglia osservativa"
        return max_altitude, best_dt, self._sampled_window_label(start_dt, end_dt)

    @staticmethod
    def _threshold_crossing(
        first: tuple[datetime, float],
        second: tuple[datetime, float],
        threshold: float,
    ) -> datetime:
        first_dt, first_altitude = first
        second_dt, second_altitude = second
        altitude_delta = second_altitude - first_altitude
        if math.isclose(altitude_delta, 0.0):
            return second_dt
        fraction = (threshold - first_altitude) / altitude_delta
        bounded_fraction = max(0.0, min(1.0, fraction))
        return first_dt + (second_dt - first_dt) * bounded_fraction

    def _sampled_window_label(self, start: datetime, end: datetime) -> str:
        start_label = self._format_dt(start)
        end_label = self._format_dt(end)
        if start_label == end_label and end > start:
            rounded_end = (end + timedelta(minutes=1)).replace(second=0, microsecond=0)
            end_label = self._format_dt(rounded_end)
        return f"{start_label} - {end_label}"

    def _ordered_event_labels(self, observer, body, now: datetime, zone: ZoneInfo) -> tuple[str, str, str]:
        start = datetime.combine(now.date(), time(0, 0), tzinfo=zone)
        end = start + timedelta(hours=48)
        rises = self._event_datetimes(almanac.find_risings, observer, body, start, end, zone)
        transits = self._transit_datetimes(observer, body, start, end, zone)
        settings = self._event_datetimes(almanac.find_settings, observer, body, start, end, zone)

        for rise_dt in rises:
            transit_dt = next((candidate for candidate in transits if candidate >= rise_dt), None)
            if not transit_dt:
                continue
            setting_dt = next((candidate for candidate in settings if candidate >= transit_dt), None)
            if setting_dt:
                return self._format_dt(rise_dt), self._format_dt(transit_dt), self._format_dt(setting_dt)

        return (
            self._format_dt(rises[0]) if rises else "n/d",
            self._format_dt(transits[0]) if transits else "n/d",
            self._format_dt(settings[0]) if settings else "n/d",
        )

    def _event_datetimes(self, function, observer, body, start: datetime, end: datetime, zone: ZoneInfo) -> list[datetime]:
        try:
            times, flags = function(observer, body, self._to_skyfield_time(start), self._to_skyfield_time(end))
        except Exception:
            logger.warning("Skyfield horizon event calculation failed.", exc_info=True)
            return []
        return [
            event_time.utc_datetime().astimezone(zone)
            for event_time, is_valid in zip(times, flags)
            if bool(is_valid)
        ]

    def _transit_datetimes(self, observer, body, start: datetime, end: datetime, zone: ZoneInfo) -> list[datetime]:
        try:
            times = almanac.find_transits(observer, body, self._to_skyfield_time(start), self._to_skyfield_time(end))
        except Exception:
            logger.warning("Skyfield transit calculation failed.", exc_info=True)
            return []
        return [event_time.utc_datetime().astimezone(zone) for event_time in times]

    def _first_event(self, function, observer, body, start: datetime, end: datetime, zone: ZoneInfo) -> str:
        times, flags = function(observer, body, self._to_skyfield_time(start), self._to_skyfield_time(end))
        for event_time, is_valid in zip(times, flags):
            if bool(is_valid):
                return self._format_dt(event_time.utc_datetime().astimezone(zone))
        return "n/d"

    def _first_transit(self, observer, body, start: datetime, end: datetime, zone: ZoneInfo) -> str:
        try:
            times = almanac.find_transits(observer, body, self._to_skyfield_time(start), self._to_skyfield_time(end))
        except Exception:
            return "n/d"
        if len(times) == 0:
            return "n/d"
        return self._format_dt(times[0].utc_datetime().astimezone(zone))

    def _magnitude(self, astrometric, object_id: str) -> float | None:
        if object_id in {"sun", "moon"}:
            return -26.7 if object_id == "sun" else -12.7
        try:
            return float(magnitudelib.planetary_magnitude(astrometric))
        except Exception:
            return None

    @staticmethod
    def _object_score(max_altitude: float, magnitude: float | None, object_type: str, visible: bool) -> int:
        if not visible:
            return 0
        altitude_score = max(0.0, min(55.0, max_altitude * 0.75))
        if magnitude is None:
            magnitude_score = 18.0
        else:
            magnitude_score = max(0.0, min(35.0, (10.5 - magnitude) * 4.0))
        type_bonus = 10 if any(word in object_type.lower() for word in ["planet", "pianeta", "globular", "nebula"]) else 4
        return round(max(0.0, min(100.0, altitude_score + magnitude_score + type_bonus)))

    @staticmethod
    def _score_label(score: int) -> str:
        if score <= 25:
            return "Pessima"
        if score <= 50:
            return "Scarsa"
        if score <= 70:
            return "Discreta"
        if score <= 85:
            return "Buona"
        return "Ottima"

    @staticmethod
    def _format_dt(value: datetime) -> str:
        return value.strftime("%H:%M")

    @staticmethod
    def _format_date(value: datetime) -> str:
        return value.strftime("%d/%m/%Y")

    @staticmethod
    def _format_magnitude(value: float | None) -> str:
        return "n/d" if value is None else f"{value:.1f}"

    @staticmethod
    def _format_distance(au: float, object_id: str) -> str:
        kilometers = au * 149_597_870.7
        if object_id == "moon":
            return f"{kilometers:,.0f} km".replace(",", ".")
        if au < 0.1:
            return f"{kilometers:,.0f} km".replace(",", ".")
        return f"{au:.2f} UA"

    @staticmethod
    def _azimuth_direction(azimuth_degrees: float) -> str:
        directions = ["Nord", "Nord-est", "Est", "Sud-est", "Sud", "Sud-ovest", "Ovest", "Nord-ovest"]
        index = round((azimuth_degrees % 360) / 45) % 8
        return directions[index]

    @staticmethod
    def _window_duration(window: str) -> str:
        if " - " not in window or window.startswith("Non"):
            return "0 h"
        start_text, end_text = [part.strip() for part in window.split(" - ", 1)]
        try:
            start_hour, start_minute = [int(part) for part in start_text.split(":", 1)]
            end_hour, end_minute = [int(part) for part in end_text.split(":", 1)]
        except ValueError:
            return "finestra utile"
        start_minutes = start_hour * 60 + start_minute
        end_minutes = end_hour * 60 + end_minute
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
        duration_minutes = max(0, end_minutes - start_minutes)
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        if minutes == 0:
            return f"{hours} h"
        return f"{hours} h {minutes:02d} min"

    @staticmethod
    def _visibility_class(magnitude: float | None, object_id: str) -> str:
        if object_id in {"sun", "moon"}:
            return "Occhio nudo"
        if magnitude is None:
            return "Telescopio"
        if magnitude <= 1.0:
            return "Occhio nudo"
        if magnitude <= 6.5:
            return "Binocolo"
        return "Telescopio"

    @staticmethod
    def _deep_sky_visibility_class(magnitude: float | None) -> str:
        if magnitude is None:
            return "Telescopio"
        if magnitude <= 4.5:
            return "Occhio nudo"
        if magnitude <= 7.5:
            return "Binocolo"
        if magnitude <= 9.5:
            return "Piccolo telescopio"
        return "Medio telescopio"

    @staticmethod
    def _default_setup(object_id: str) -> str:
        if object_id in {"jupiter", "saturn", "mars"}:
            return "10 mm + Barlow 2x se il seeing lo consente"
        if object_id in {"uranus", "neptune"}:
            return "Telescopio medio, 10 mm"
        if object_id == "venus":
            return "Piccolo telescopio, filtro neutro opzionale"
        if object_id == "mercury":
            return "Orizzonte libero, bassi ingrandimenti"
        return "Filtro adeguato e osservazione sicura"

    @staticmethod
    def _body_note(object_id: str, max_altitude: float) -> str:
        if object_id == "sun":
            return "Osservare solo con filtro solare certificato."
        if object_id == "moon":
            return "Filtro lunare consigliato oltre 100 mm di apertura."
        if max_altitude < 15:
            return "Basso sull'orizzonte: serve visuale libera e seeing stabile."
        return "Calcolo reale Skyfield per la posizione selezionata."

    @staticmethod
    def _deep_sky_setup(object_type: str, magnitude: float | None) -> str:
        lower_type = object_type.lower()
        if "galaxy" in lower_type:
            return "Oculare 25 mm, cielo buio"
        if "planetary" in lower_type:
            return "10 mm, filtro UHC opzionale"
        if "globular" in lower_type:
            return "25 mm per ricerca, 10 mm per risoluzione"
        if "open" in lower_type:
            return "25 mm o binocolo 10x50"
        if magnitude is not None and magnitude > 9:
            return "Telescopio medio, cielo buio"
        return "25 mm, bassi ingrandimenti"

    @staticmethod
    def _messier_image(messier_id: str, object_type: str) -> str:
        if messier_id == "M13":
            return "resources/images/m13.svg"
        if messier_id == "M57":
            return "resources/images/m57.svg"
        if messier_id == "M31":
            return "resources/images/m31.svg"
        lower_type = object_type.lower()
        if "galaxy" in lower_type:
            return "resources/images/m31.svg"
        if "nebula" in lower_type:
            return "resources/images/m57.svg"
        return "resources/images/m13.svg"

    @staticmethod
    def _moon_phase_name(angle: float) -> str:
        if angle < 22.5 or angle >= 337.5:
            return "Nuova"
        if angle < 67.5:
            return "Crescente"
        if angle < 112.5:
            return "Primo quarto"
        if angle < 157.5:
            return "Gibbosa crescente"
        if angle < 202.5:
            return "Piena"
        if angle < 247.5:
            return "Gibbosa calante"
        if angle < 292.5:
            return "Ultimo quarto"
        return "Calante"

    @staticmethod
    def _moon_phase_event_name(index: int) -> str:
        return {
            0: "Luna nuova",
            1: "Primo quarto",
            2: "Luna piena",
            3: "Ultimo quarto",
        }.get(index, "Fase lunare")

    @staticmethod
    def _moon_observing_note(illumination: float) -> str:
        if illumination < 0.25:
            return "Cielo favorevole per galassie e nebulose deboli."
        if illumination < 0.65:
            return "Buon compromesso per Luna, pianeti e oggetti brillanti."
        return "Luna luminosa: cielo profondo debole penalizzato."

    @staticmethod
    def _recurring_meteor_showers(now: datetime) -> list[AstronomicalEvent]:
        showers = [
            ("Quadrantidi", 1, 3, "Nord-est prima dell'alba"),
            ("Liridi", 4, 22, "Dopo mezzanotte"),
            ("Eta Aquaridi", 5, 6, "Pre-alba"),
            ("Perseidi", 8, 12, "02:00 - 04:30"),
            ("Orionidi", 10, 21, "Dopo mezzanotte"),
            ("Geminidi", 12, 14, "22:00 - 03:00"),
        ]
        events = []
        for name, month, day, best_time in showers:
            event_date = datetime(now.year, month, day, 0, 0, tzinfo=now.tzinfo)
            if event_date < now:
                event_date = datetime(now.year + 1, month, day, 0, 0, tzinfo=now.tzinfo)
            events.append(
                AstronomicalEvent(
                    id=f"shower-{name.lower()}-{event_date.year}",
                    title=f"Massimo {name}",
                    event_type="Sciame meteorico",
                    date_label=event_date.strftime("%d/%m/%Y"),
                    best_time=best_time,
                    usefulness=78,
                    setup="Occhio nudo",
                    note="Evento ricorrente; verificare fase lunare e meteo.",
                )
            )
        return events
