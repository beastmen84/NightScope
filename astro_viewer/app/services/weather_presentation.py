"""Build weather digests, useful windows, and session advice for QML."""

from __future__ import annotations

from datetime import datetime, timedelta

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.weather import (
    ObservingSessionDecision,
    WeatherBlockingStatus,
    WeatherHour,
    WeatherSummary,
)
from astro_viewer.app.services.localization import format_number, tr
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.services.observing_night_service import (
    consecutive_weather_groups,
    weather_hour_datetime,
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
            }
        average_cloud = round(
            sum(hour.cloud_cover for hour in night_hours) / len(night_hours)
        )
        max_rain = max(hour.precipitation_probability for hour in night_hours)
        average_wind = round(
            sum(hour.wind_kmh for hour in night_hours) / len(night_hours)
        )
        best_hours = best_weather_hours(night_hours)
        return {
            "bestWindow": weather_window_label(
                best_hours,
                night_window,
                timezone,
            ),
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
    ) -> ObservingSessionDecision:
        blocking = self.blocking_status(weather_summary)
        if not blocking.show_warning:
            return ObservingSessionDecision(state="recommended")

        if best_usable_observing_window(night_hours):
            return ObservingSessionDecision(
                state="monitor",
                title=tr("Sessione da monitorare"),
                icon="⚠",
                detail=tr("Le condizioni attuali non sono ancora favorevoli."),
                description=tr(
                    "Le condizioni migliorano in una finestra osservativa "
                    "successiva.\nRicontrolla il meteo prima di preparare la "
                    "sessione."
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
        decision = self.session_decision(weather_summary, night_hours)
        if decision.state == "discouraged":
            return ""
        if decision.state == "monitor":
            return weather_window_label(
                best_usable_observing_window(night_hours),
                night_window,
                timezone,
            ).replace(" - ", "–")
        best_window = self.digest(
            night_hours,
            night_window,
            timezone,
        ).get("bestWindow", "")
        if not best_window or best_window == "n/d":
            return ""
        return str(best_window).replace(" - ", "–")


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


def is_usable_weather_hour(hour: WeatherHour) -> bool:
    return (
        hour.precipitation_probability <= 35
        and hour.cloud_cover <= 65
        and hour.wind_kmh <= 28
        and weather_hour_observing_score(hour) >= 45
    )


def weather_hour_observing_score(hour: WeatherHour) -> int:
    score = 100
    score -= min(55, round(hour.cloud_cover * 0.55))
    score -= min(30, round(hour.precipitation_probability * 0.45))
    score -= max(0, hour.wind_kmh - 10)
    score -= max(0, round((hour.humidity - 70) * 0.25))
    return max(0, min(100, score))


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
        end_dt = last_timestamp + timedelta(hours=1)
        if night_window is not None and night_window.end is not None:
            end_dt = min(end_dt, night_window.end)
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
