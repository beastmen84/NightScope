from __future__ import annotations

from datetime import datetime, timedelta

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, NightPlanItem, SkyQuality
from astro_viewer.app.models.weather import WeatherBlockingStatus, WeatherSummary
from astro_viewer.app.services.observation_conditions_service import TargetConditionBreakdown
from astro_viewer.app.services.planner_nsom_service import PlannerNsomScoringService
from astro_viewer.app.services.planner_scoring_service import (
    PlannerConditionBreakdown,
    PlannerScoreBreakdown,
    PlannerScoringService,
)


NSOM_PLANNER_SCORING_ENABLED = False


class NightPlannerService:
    """Builds a compact, optimized observing sequence."""

    def __init__(
        self,
        scoring_service: PlannerScoringService | None = None,
        *,
        use_nsom_planner_scoring: bool = NSOM_PLANNER_SCORING_ENABLED,
        nsom_scoring_service: PlannerNsomScoringService | None = None,
    ) -> None:
        self._scoring_service = scoring_service or PlannerScoringService()
        self._use_nsom_planner_scoring = use_nsom_planner_scoring
        nsom_planner_source = self._scoring_service if hasattr(self._scoring_service, "condition_breakdown") else None
        self._nsom_scoring_service = nsom_scoring_service or PlannerNsomScoringService(nsom_planner_source)

    def plan(
        self,
        objects: list[CelestialObject],
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
    ) -> list[NightPlanItem]:
        blocking_status = self.weather_blocking_status(weather)
        if blocking_status.blocks_plan:
            return []

        visible = [item for item in objects if item.visible and item.score > 0 and self._has_useful_window(item)]
        if not visible:
            visible = [item for item in objects if item.visible and item.score > 0]
        scored_visible = self._scored_visible(
            visible,
            weather=weather,
            scores=scores,
            sky_quality=sky_quality,
            telescope=telescope,
            moon=moon,
            blocking_status=blocking_status,
        )
        ranked = sorted(scored_visible, key=lambda item: item[1], reverse=True)
        start = self._start_time([item for item, _score in ranked])
        selected = []
        used_names = set()
        for item, score in ranked:
            if item.name in used_names:
                continue
            used_names.add(item.name)
            selected.append((item, score))
            if len(selected) >= 6:
                break

        items = []
        for item, raw_score in selected:
            score = round(raw_score)
            time_label = self._time_for_item(item, start + timedelta(minutes=45 * len(items)))
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
        return self._sort_plan_items(items)

    def _scored_visible(
        self,
        visible: list[CelestialObject],
        *,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None,
        blocking_status: WeatherBlockingStatus,
    ) -> list[tuple[CelestialObject, float]]:
        if not self._use_nsom_planner_scoring:
            return [
                (item, self._scoring_service.score(item, weather, scores, sky_quality, telescope, moon))
                for item in visible
            ]

        opportunities = [
            (
                item,
                self._nsom_scoring_service.opportunity(
                    item,
                    weather=weather,
                    scores=scores,
                    sky_quality=sky_quality,
                    telescope=telescope,
                    moon=moon,
                    blocking_status=blocking_status,
                    observing_window_quality=self._observing_window_quality(item),
                    chronology_fit=self._chronology_fit(item),
                    practical_constraints=self._practical_constraints(item),
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
    def _observing_window_quality(item: CelestialObject) -> float:
        if NightPlannerService._observing_time(item) is not None:
            return 1.0
        return 0.5 if item.visible else 0.0

    @staticmethod
    def _chronology_fit(item: CelestialObject) -> float:
        parsed = NightPlannerService._observing_time(item)
        if parsed is None:
            return 0.8
        if 21 <= parsed.hour <= 23:
            return 1.0
        if parsed.hour == 20 or 0 <= parsed.hour <= 2:
            return 0.95
        if 3 <= parsed.hour <= 5:
            return 0.85
        return 0.75

    @staticmethod
    def _practical_constraints(item: CelestialObject) -> float:
        return min(1.0, PlannerScoringService.difficulty_factor(item))

    @staticmethod
    def _start_time(objects: list[CelestialObject]) -> datetime:
        now = datetime.now()
        for item in objects:
            parsed = NightPlannerService._parse_time(item.best_time)
            if parsed:
                return parsed
        return now.replace(hour=21, minute=0, second=0, microsecond=0)

    @staticmethod
    def _time_for_item(item: CelestialObject, fallback: datetime) -> str:
        parsed = NightPlannerService._observing_time(item) or fallback
        return NightPlannerService._format_observing_time(parsed)

    @staticmethod
    def _parse_time(value: str) -> datetime | None:
        try:
            hour, minute = [int(part) for part in value.split(":")[:2]]
        except (ValueError, IndexError):
            return None
        now = datetime.now()
        parsed = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if parsed.hour < 12 and now.hour > 12:
            parsed += timedelta(days=1)
        if not NightPlannerService._is_useful_hour(parsed.hour, parsed.minute):
            return None
        return parsed

    @staticmethod
    def _observing_time(item: CelestialObject) -> datetime | None:
        parsed_best = NightPlannerService._parse_time(item.best_time)
        if parsed_best:
            return parsed_best
        for value in NightPlannerService._window_times(item.observing_window):
            parsed = NightPlannerService._parse_time(value)
            if parsed:
                return parsed
        return None

    @staticmethod
    def _has_useful_window(item: CelestialObject) -> bool:
        return NightPlannerService._observing_time(item) is not None

    @staticmethod
    def _window_times(value: str) -> list[str]:
        parts = []
        for token in value.replace("-", " ").split():
            if ":" in token:
                parts.append(token.strip())
        return parts

    @staticmethod
    def _is_useful_hour(hour: int, minute: int) -> bool:
        return hour >= 20 or hour <= 5

    @staticmethod
    def _format_observing_time(value: datetime) -> str:
        label = "sera"
        if 0 <= value.hour <= 2:
            label = "notte"
        elif 3 <= value.hour <= 5:
            label = "prima dell'alba"
        return f"{value.strftime('%H:%M')} {label}"

    @staticmethod
    def _sort_plan_items(items: list[NightPlanItem]) -> list[NightPlanItem]:
        indexed = list(enumerate(items))
        indexed.sort(key=lambda item: (NightPlannerService._time_label_order(item[1].time_label), item[0]))
        return [item for _, item in indexed]

    @staticmethod
    def _time_label_order(value: str) -> int:
        for token in value.replace("–", " ").replace("-", " ").split():
            parsed = NightPlannerService._parse_clock_token(token)
            if parsed is None:
                continue
            hour, minute = parsed
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
