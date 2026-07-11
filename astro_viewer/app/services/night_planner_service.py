from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta

from astro_viewer.app.astronomy.engine import ObservingNightWindow
from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, NightPlanItem, SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.observation_conditions_service import (
    MoonGeometryConditionInput,
    ObservationConditionInputs,
    TargetConditionBreakdown,
)
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService
from astro_viewer.app.services.planner_scoring_service import (
    PlannerConditionBreakdown,
    PlannerScoreBreakdown,
    PlannerScoringService,
)


NSOM_PLANNER_SCORING_ENABLED = True


class NightPlannerService:
    """Builds a compact, optimized observing sequence."""

    def __init__(
        self,
        *,
        nsom_scoring_service: PlannerNsomScoringService | None = None,
    ) -> None:
        self._nsom_scoring_service = nsom_scoring_service or PlannerNsomScoringService()

    @property
    def uses_moon_geometry_scoring(self) -> bool:
        return bool(getattr(self._nsom_scoring_service, "uses_moon_geometry_scoring", False))

    @property
    def uses_target_equipment(self) -> bool:
        return True

    def plan(
        self,
        objects: list[CelestialObject],
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None = None,
        telescope_by_object_id: Mapping[str, Telescope] | None = None,
        night_window: ObservingNightWindow | None = None,
        condition_inputs: ObservationConditionInputs | None = None,
    ) -> list[NightPlanItem]:
        blocking_status = self.weather_blocking_status(weather)
        if blocking_status.blocks_plan:
            return []

        visible = [
            item
            for item in objects
            if item.visible and item.score > 0 and self._has_useful_window(item, night_window)
        ]
        if not visible:
            visible = [item for item in objects if item.visible and item.score > 0]
        scored_visible = self._scored_visible(
            visible,
            weather=weather,
            scores=scores,
            sky_quality=sky_quality,
            telescope=telescope,
            moon=moon,
            moon_geometry_by_object_id=moon_geometry_by_object_id,
            telescope_by_object_id=telescope_by_object_id,
            blocking_status=blocking_status,
            night_window=night_window,
            condition_inputs=condition_inputs,
        )
        ranked = sorted(scored_visible, key=lambda item: item[1], reverse=True)
        start = self._start_time([item for item, _score in ranked], night_window)
        selected = []
        used_names = set()
        for item, score in ranked:
            if item.name in used_names:
                continue
            used_names.add(item.name)
            selected.append((item, score))
            if len(selected) >= 4:
                break

        items = []
        for item, raw_score in selected:
            score = round(raw_score)
            time_label = self._time_for_item(
                item,
                start + timedelta(minutes=45 * len(items)),
                night_window,
            )
            items.append(
                NightPlanItem(
                    time_label=time_label,
                    object_id=item.id,
                    name=item.name,
                    score=max(0, min(100, score)),
                    difficulty=item.difficulty,
                    setup=item.recommended_setup,
                    direction=item.direction,
                    image=item.image,
                )
            )
        return self._sort_plan_items(items, night_window)

    def _scored_visible(
        self,
        visible: list[CelestialObject],
        *,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None,
        moon_geometry_by_object_id: Mapping[str, MoonGeometryConditionInput] | None,
        telescope_by_object_id: Mapping[str, Telescope] | None,
        blocking_status: WeatherBlockingStatus,
        night_window: ObservingNightWindow | None,
        condition_inputs: ObservationConditionInputs | None,
    ) -> list[tuple[CelestialObject, float]]:
        opportunities = [
            (
                item,
                self._nsom_scoring_service.opportunity(
                    item,
                    weather=weather,
                    scores=scores,
                    sky_quality=sky_quality,
                    telescope=(telescope_by_object_id or {}).get(item.id, telescope),
                    moon=moon,
                    moon_geometry=moon_geometry_by_object_id.get(item.id)
                    if moon_geometry_by_object_id is not None
                    else None,
                    blocking_status=blocking_status,
                    observing_window_quality=self._observing_window_quality(item, night_window),
                    chronology_fit=self._chronology_fit(item, night_window),
                    practical_constraints=self._practical_constraints(item),
                    condition_inputs=condition_inputs,
                ),
            )
            for item in visible
        ]
        return [(item, self._nsom_scoring_service.score(opportunity)) for item, opportunity in opportunities]

    @staticmethod
    def _planner_score(
        item: CelestialObject,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
    ) -> float:
        return NightPlannerService._planner_score_breakdown(
            item,
            weather,
            scores,
            sky_quality,
            telescope,
            moon,
        ).final_score

    @staticmethod
    def _planner_score_breakdown(
        item: CelestialObject,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
    ) -> PlannerScoreBreakdown:
        return PlannerScoringService().score_breakdown(item, weather, scores, sky_quality, telescope, moon)

    @staticmethod
    def weather_blocking_status(weather: WeatherSummary) -> WeatherBlockingStatus:
        if weather.precipitation_probability >= 65:
            return WeatherBlockingStatus(
                blocks_plan=True,
                show_warning=True,
                reason="rischio precipitazioni",
                detail="Rischio precipitazioni elevato.",
            )
        if weather.cloud_cover >= 85:
            return WeatherBlockingStatus(
                blocks_plan=True,
                show_warning=True,
                reason="nuvolosità quasi coperta",
                detail="Copertura nuvolosa severa.",
            )
        if weather.score_value <= 25:
            show_warning = weather.score_value > 0
            return WeatherBlockingStatus(
                blocks_plan=True,
                show_warning=show_warning,
                reason=(weather.explanation or "qualità osservativa pessima") if show_warning else "",
                detail="Punteggio osservativo sotto la soglia minima." if show_warning else "",
            )
        return WeatherBlockingStatus(blocks_plan=False, show_warning=False)

    @staticmethod
    def _weather_factor(weather: WeatherSummary) -> float:
        return PlannerScoringService.weather_factor(weather)

    @staticmethod
    def moon_adjusted_score(item: CelestialObject, moon: MoonSummary | None) -> int:
        return PlannerScoringService().moon_adjusted_score(item, moon)

    @staticmethod
    def moon_penalty(item: CelestialObject, moon: MoonSummary | None) -> float:
        return PlannerScoringService().moon_penalty(item, moon)

    @staticmethod
    def _moon_condition_breakdown(item: CelestialObject, moon: MoonSummary | None) -> TargetConditionBreakdown:
        return PlannerScoringService().moon_condition_breakdown(item, moon)

    @staticmethod
    def _pollution_penalty(item: CelestialObject, sky_quality: SkyQuality) -> float:
        return PlannerScoringService().pollution_penalty(item, sky_quality)

    @staticmethod
    def _planner_condition_breakdown(
        item: CelestialObject,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
    ) -> PlannerConditionBreakdown:
        return PlannerScoringService().condition_breakdown(item, sky_quality, moon)

    @staticmethod
    def _observing_window_quality(
        item: CelestialObject,
        night_window: ObservingNightWindow | None = None,
    ) -> float:
        if NightPlannerService._observing_time(item, night_window) is not None:
            return 1.0
        return 0.5 if item.visible else 0.0

    @staticmethod
    def _chronology_fit(
        item: CelestialObject,
        night_window: ObservingNightWindow | None = None,
    ) -> float:
        parsed = NightPlannerService._observing_time(item, night_window)
        if parsed is None:
            return 0.8
        if night_window is None or not night_window.has_observing_window:
            if 21 <= parsed.hour <= 23:
                return 1.0
            if parsed.hour == 20 or 0 <= parsed.hour <= 2:
                return 0.95
            if 3 <= parsed.hour <= 5:
                return 0.85
            return 0.75
        duration = (night_window.end - night_window.start).total_seconds()
        progress = (parsed - night_window.start).total_seconds() / duration
        if progress <= 0.35:
            return 1.0
        if progress <= 0.7:
            return 0.95
        return 0.85

    @staticmethod
    def _practical_constraints(item: CelestialObject) -> float:
        return min(1.0, {"Facile": 1.08, "Media": 0.95, "Difficile": 0.75}.get(item.difficulty, 0.85))

    @staticmethod
    def _start_time(
        objects: list[CelestialObject],
        night_window: ObservingNightWindow | None = None,
    ) -> datetime:
        now = datetime.now(night_window.start.tzinfo) if night_window and night_window.start else datetime.now()
        for item in objects:
            parsed = NightPlannerService._parse_time(item.best_time, night_window)
            if parsed:
                return parsed
        if night_window is not None and night_window.start is not None:
            return max(now, night_window.start)
        return now.replace(hour=21, minute=0, second=0, microsecond=0)

    @staticmethod
    def _time_for_item(
        item: CelestialObject,
        fallback: datetime,
        night_window: ObservingNightWindow | None = None,
    ) -> str:
        parsed = NightPlannerService._observing_time(item, night_window) or fallback
        return NightPlannerService._format_observing_time(parsed, night_window)

    @staticmethod
    def _parse_time(
        value: str,
        night_window: ObservingNightWindow | None = None,
    ) -> datetime | None:
        try:
            hour, minute = [int(part) for part in value.split(":")[:2]]
        except (ValueError, IndexError):
            return None
        if night_window is not None:
            parsed = night_window.datetime_for_clock(hour, minute)
            if parsed is None:
                return None
            now = datetime.now(parsed.tzinfo)
            if night_window.contains(now) and parsed < now:
                return None
            return parsed
        now = datetime.now()
        parsed = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if parsed.hour < 12 and now.hour > 12:
            parsed += timedelta(days=1)
        return parsed

    @staticmethod
    def _observing_time(
        item: CelestialObject,
        night_window: ObservingNightWindow | None = None,
    ) -> datetime | None:
        parsed_best = NightPlannerService._parse_time(item.best_time, night_window)
        if parsed_best:
            return parsed_best
        interval = NightPlannerService._observing_window_interval(
            item.observing_window,
            night_window,
        )
        if interval is None:
            return None
        start, end = interval
        now = datetime.now(start.tzinfo)
        if start <= now < end:
            return now.replace(second=0, microsecond=0)
        return start if start >= now else None

    @staticmethod
    def _observing_window_interval(
        value: str,
        night_window: ObservingNightWindow | None = None,
    ) -> tuple[datetime, datetime] | None:
        times = NightPlannerService._window_times(value)
        if len(times) < 2:
            return None
        start_clock = NightPlannerService._parse_clock_token(times[0])
        end_clock = NightPlannerService._parse_clock_token(times[1])
        if start_clock is None or end_clock is None:
            return None

        if night_window is not None and night_window.has_observing_window:
            start = night_window.datetime_for_clock(*start_clock)
            end = night_window.datetime_for_clock(*end_clock)
            if start is None or end is None:
                return None
            if end <= start:
                return None
            return start, end

        now = datetime.now()
        intervals = []
        for day_offset in (-1, 0, 1):
            day = now.date() + timedelta(days=day_offset)
            start = now.replace(
                year=day.year,
                month=day.month,
                day=day.day,
                hour=start_clock[0],
                minute=start_clock[1],
                second=0,
                microsecond=0,
            )
            end = start.replace(hour=end_clock[0], minute=end_clock[1])
            if end <= start:
                end += timedelta(days=1)
            intervals.append((start, end))
        active = next((interval for interval in intervals if interval[0] <= now < interval[1]), None)
        if active is not None:
            return active
        return min(
            (interval for interval in intervals if interval[0] >= now),
            default=None,
            key=lambda interval: interval[0],
        )

    @staticmethod
    def _has_useful_window(
        item: CelestialObject,
        night_window: ObservingNightWindow | None = None,
    ) -> bool:
        return NightPlannerService._observing_time(item, night_window) is not None

    @staticmethod
    def _window_times(value: str) -> list[str]:
        parts = []
        for token in value.replace("-", " ").split():
            if ":" in token:
                parts.append(token.strip())
        return parts

    @staticmethod
    def _format_observing_time(
        value: datetime,
        night_window: ObservingNightWindow | None = None,
    ) -> str:
        if night_window is None:
            label = "sera" if value.hour >= 12 else "notte"
            if 3 <= value.hour <= 5:
                label = "prima dell'alba"
        else:
            label = "notte"
        if night_window is not None and night_window.state == "bounded":
            if night_window.start is not None and value.date() == night_window.start.date():
                label = "sera"
            elif night_window.end is not None and night_window.end - value <= timedelta(hours=3):
                label = "prima dell'alba"
        return f"{value.strftime('%H:%M')} {label}"

    @staticmethod
    def _sort_plan_items(
        items: list[NightPlanItem],
        night_window: ObservingNightWindow | None = None,
    ) -> list[NightPlanItem]:
        indexed = list(enumerate(items))
        indexed.sort(
            key=lambda item: (
                NightPlannerService._time_label_order(item[1].time_label, night_window),
                item[0],
            )
        )
        return [item for _, item in indexed]

    @staticmethod
    def _time_label_order(
        value: str,
        night_window: ObservingNightWindow | None = None,
    ) -> int:
        for token in value.replace("–", " ").replace("-", " ").split():
            parsed = NightPlannerService._parse_clock_token(token)
            if parsed is None:
                continue
            hour, minute = parsed
            if night_window is not None and night_window.start is not None:
                candidate = night_window.datetime_for_clock(hour, minute)
                if candidate is not None:
                    return round((candidate - night_window.start).total_seconds() / 60)
            if hour >= 12:
                return (hour - 12) * 60 + minute
            return (hour + 12) * 60 + minute
        return 99_999

    @staticmethod
    def _parse_clock_token(value: str) -> tuple[int, int] | None:
        try:
            hour, minute = [int(part) for part in value.split(":")[:2]]
        except (ValueError, IndexError):
            return None
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            return None
        return hour, minute
