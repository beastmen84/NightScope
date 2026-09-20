"""Build weather digests, useful windows, and session advice for QML."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from astro_viewer.app.astronomy.engine import ObservingNightWindow, advance_time, as_utc
from astro_viewer.app.models.weather import (
    ObservingSessionDecision,
    WeatherBlockingStatus,
    WeatherHour,
    WeatherSummary,
)
from astro_viewer.app.services.localization import format_number, tr
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.observing_night_service import (
    MIN_PRACTICAL_OBSERVING_DURATION,
    consecutive_weather_groups,
    is_usable_weather_hour as is_usable_weather_hour,
    usable_weather_intervals,
    weather_hour_datetime,
    weather_hour_observing_score as weather_hour_observing_score,
)
from astro_viewer.app.services.observing_time import parse_hour_minute


class WeatherPresentationService:
    """Builds weather summaries and session advice away from the view model."""

    def __init__(self, night_planner_service: NightPlannerService) -> None:
        self._night_planner_service = night_planner_service

    def digest(
        self,
        night_hours: list[WeatherHour],
        night_window: ObservingNightWindow,
        timezone: str,
    ) -> dict:
        if not night_hours:
            return {
                "bestWindow": tr("n/d"),
                "cloudAverage": 0,
                "cloudAverageLabel": tr("n/d"),
                "windLabel": tr("n/d"),
                "rainProbability": 0,
                "rainProbabilityLabel": tr("n/d"),
                "bestHours": [],
                "goodWindows": [],
                "goodWindowText": "",
                "bestWindowText": "",
                "usableWindowText": "",
            }
        average_cloud = round(
            sum(hour.cloud_cover for hour in night_hours) / len(night_hours)
        )
        max_rain = max(hour.precipitation_probability for hour in night_hours)
        average_wind = round(
            sum(hour.wind_kmh for hour in night_hours) / len(night_hours)
        )
        usable = practical_weather_windows(night_hours, night_window, timezone)
        good_groups = good_weather_windows(night_hours)
        good_labels = [weather_window_label(group, night_window, timezone) for group in good_groups]
        practical_best = best_weather_hours([hour for group in good_groups for hour in group])
        return {
            "usableWindowText": (
                tr("Possibile finestra meteo: {windows}", windows=" · ".join(
                    _interval_label(start, end) for start, end in usable
                )) if usable else ""
            ),
            "goodWindows": good_labels,
            "goodWindowText": (
                tr("Meteo buono: {windows}", windows=" · ".join(good_labels))
                if good_labels else tr("Nessuna fascia meteo buona prevista")
            ),
            "bestWindowText": (
                tr("Picco meteo previsto: {window}",
                   window=weather_window_label(practical_best, night_window, timezone))
                if practical_best else ""
            ),
            "bestWindow": _interval_label(*max(usable, key=lambda pair: as_utc(pair[1]) - as_utc(pair[0])))
            if usable else tr("n/d"),
            "cloudAverage": average_cloud,
            "cloudAverageLabel": tr(
                "{value}%",
                value=format_number(average_cloud),
            ),
            "windLabel": wind_label(average_wind),
            "rainProbability": max_rain,
            "rainProbabilityLabel": tr(
                "{value}%",
                value=format_number(max_rain),
            ),
            "bestHours": [
                {
                    "time": hour.time,
                    "cloudCover": hour.cloud_cover,
                    "cloudCoverLabel": tr(
                        "{value}%",
                        value=format_number(hour.cloud_cover),
                    ),
                    "windKmh": hour.wind_kmh,
                    "windLabel": tr(
                        "{value} km/h",
                        value=format_number(hour.wind_kmh),
                    ),
                    "rainProbability": hour.precipitation_probability,
                    "rainProbabilityLabel": tr(
                        "{value}%",
                        value=format_number(hour.precipitation_probability),
                    ),
                }
                for hour in selected_weather_hours(night_hours)
            ],
        }

    def blocking_status(
        self,
        weather_summary: WeatherSummary | None,
    ) -> WeatherBlockingStatus:
        if not weather_summary:
            return WeatherBlockingStatus(blocks_plan=False, show_warning=False)
        return self._night_planner_service.weather_blocking_status(weather_summary)

    def session_decision(
        self,
        weather_summary: WeatherSummary | None,
        night_hours: list[WeatherHour],
        night_window: ObservingNightWindow | None = None,
        timezone: str = "UTC",
    ) -> ObservingSessionDecision:
        if weather_summary is None or not night_hours:
            return ObservingSessionDecision(
                state="unavailable", title=tr("Sessione non valutabile"),
                detail=tr("Previsioni orarie della notte non disponibili."),
            )
        blocking = self.blocking_status(weather_summary)
        usable = practical_weather_windows(night_hours, night_window, timezone)
        if (usable and good_weather_windows(night_hours)
                and weather_summary.score_value >= 70 and not blocking.show_warning):
            return ObservingSessionDecision(state="recommended")

        if usable:
            return ObservingSessionDecision(
                state="monitor",
                title=tr("Sessione da monitorare"),
                icon="⚠",
                detail=tr("Condizioni variabili: sono previste solo opportunità da verificare."),
                description=tr(
                    "Gli orari suggeriti richiedono conferma del meteo prima di osservare."
                ),
                show_opportunity=True,
            )

        return ObservingSessionDecision(
            state="discouraged",
            title=tr("Sessione sconsigliata"),
            icon="🚫",
            detail=tr(
                "Le condizioni previste rimangono sfavorevoli per tutta la notte."
            ),
            description=tr(
                "Non è consigliabile preparare una sessione osservativa."
            ),
            show_opportunity=False,
        )

    def suggested_observing_window(
        self,
        weather_summary: WeatherSummary | None,
        night_hours: list[WeatherHour],
        night_window: ObservingNightWindow,
        timezone: str,
    ) -> str:
        decision = self.session_decision(weather_summary, night_hours, night_window, timezone)
        if decision.state in {"discouraged", "unavailable"}:
            return ""
        best_window = self.digest(
            night_hours,
            night_window,
            timezone,
        ).get("bestWindow", "")
        if not best_window or best_window == "n/d":
            return ""
        return str(best_window).replace(" - ", "–")


def practical_weather_windows(
    hours: list[WeatherHour],
    night_window: ObservingNightWindow | None,
    timezone: str,
) -> list[tuple[datetime, datetime]]:
    """Use the planner's usable bins and minimum duration, in local time."""
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    # Preserve offset-free timestamps until the shared parser can reject DST
    # folds/gaps. Do not attach an arbitrary offset before validating them.
    if night_window is not None and not night_window.has_observing_window:
        return []
    return [(start.astimezone(zone), end.astimezone(zone))
            for start, end in usable_weather_intervals(hours, night_window, timezone=zone.key)
            if end - start >= MIN_PRACTICAL_OBSERVING_DURATION]


def _interval_label(start: datetime, end: datetime) -> str:
    return f"{start:%H:%M} - {end:%H:%M}"


def best_weather_hours(hours: list[WeatherHour]) -> list[WeatherHour]:
    groups = consecutive_weather_groups(hours)
    full_groups = [group for group in groups if len(group) >= 3]
    if full_groups:
        candidates = [
            group[index : index + 3]
            for group in full_groups
            for index in range(len(group) - 2)
        ]
    else:
        longest = max((len(group) for group in groups), default=0)
        candidates = [group for group in groups if len(group) == longest]
    if not candidates:
        return []
    return min(candidates, key=weather_slice_score)


def best_usable_observing_window(hours: list[WeatherHour]) -> list[WeatherHour]:
    best_group: list[WeatherHour] = []
    for forecast_group in consecutive_weather_groups(hours):
        current_group: list[WeatherHour] = []
        for hour in forecast_group:
            if is_usable_weather_hour(hour):
                current_group.append(hour)
                if len(current_group) > len(best_group):
                    best_group = list(current_group)
            else:
                current_group = []
    return best_group if len(best_group) >= 2 else []


def good_weather_windows(hours: list[WeatherHour]) -> list[list[WeatherHour]]:
    """Continuous good forecasts, not the looser plan-admission policy.

    Require two hourly samples, <=35% clouds, <=20% rain probability, <=20 km/h
    wind and >=70/100 including humidity. Never bridge missing/bad hours.
    These are presentation thresholds, not changes to session/NSOM scoring.
    """
    result: list[list[WeatherHour]] = []
    for group in consecutive_weather_groups(hours):
        current: list[WeatherHour] = []
        for hour in group:
            if (0 <= hour.cloud_cover <= 35
                    and 0 <= hour.precipitation_probability <= 20
                    and 0 <= hour.wind_kmh <= 20
                    and 0 <= hour.humidity <= 100
                    and weather_hour_observing_score(hour) >= 70):
                current.append(hour)
            else:
                if len(current) >= 2:
                    result.append(current)
                current = []
        if len(current) >= 2:
            result.append(current)
    return result


def weather_slice_score(hours: list[WeatherHour]) -> float:
    cloud = sum(hour.cloud_cover for hour in hours) / len(hours)
    rain = max(hour.precipitation_probability for hour in hours)
    wind = sum(hour.wind_kmh for hour in hours) / len(hours)
    return cloud + rain * 1.3 + max(0.0, wind - 10.0) * 1.8


def selected_weather_hours(hours: list[WeatherHour]) -> list[WeatherHour]:
    if len(hours) <= 5:
        return list(hours)
    last_index = len(hours) - 1
    indices = [round(position * last_index / 4) for position in range(5)]
    return [hours[index] for index in dict.fromkeys(indices)]


def weather_window_label(
    hours: list[WeatherHour],
    night_window: ObservingNightWindow | None = None,
    timezone: str = "UTC",
) -> str:
    if not hours:
        return tr("n/d")
    contiguous = consecutive_weather_groups(hours)
    selected = max(contiguous, key=len, default=[])
    if not selected:
        return tr("n/d")
    start = selected[0].time
    last_timestamp = weather_hour_datetime(selected[-1], timezone)
    if last_timestamp is not None:
        end_dt = advance_time(last_timestamp, timedelta(hours=1))
        if night_window is not None and night_window.end is not None:
            end_dt = min(end_dt, night_window.end, key=as_utc)
    else:
        parsed_end = parse_hour_minute(selected[-1].time)
        if not parsed_end:
            return start
        end_dt = datetime(2000, 1, 1, parsed_end[0], parsed_end[1]) + timedelta(
            hours=1
        )
    return f"{start} - {end_dt.strftime('%H:%M')}"


def wind_label(wind_kmh: int) -> str:
    if wind_kmh <= 12:
        return tr("debole")
    if wind_kmh <= 24:
        return tr("moderato")
    return tr("sostenuto")
