from __future__ import annotations

from datetime import datetime, timedelta

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject
from astro_viewer.app.models.sky import AdvancedObservingScores, NightPlanItem, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary


class NightPlannerService:
    """Builds a compact, optimized observing sequence."""

    def plan(
        self,
        objects: list[CelestialObject],
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
    ) -> list[NightPlanItem]:
        visible = [item for item in objects if item.visible and item.score > 0]
        ranked = sorted(
            visible,
            key=lambda item: self._planner_score(item, weather, scores, sky_quality, telescope),
            reverse=True,
        )
        start = self._start_time(ranked)
        items = []
        used_names = set()
        for index, item in enumerate(ranked):
            if item.name in used_names:
                continue
            used_names.add(item.name)
            score = round(self._planner_score(item, weather, scores, sky_quality, telescope))
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
            if len(items) >= 6:
                break
        return items

    @staticmethod
    def _planner_score(
        item: CelestialObject,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
    ) -> float:
        lower_type = item.object_type.lower()
        category_score = scores.planetary_score if item.object_type == "Pianeta" else scores.deep_sky_score
        aperture_bonus = min(14, telescope.aperture_mm / 18)
        pollution_penalty = max(0, sky_quality.bortle_class - 4) * (7 if "galaxy" in lower_type else 4)
        difficulty_factor = {"Facile": 1.08, "Media": 0.95, "Difficile": 0.75}.get(item.difficulty, 0.85)
        return (item.score * 0.48 + category_score * 0.34 + weather.score_value * 0.18 + aperture_bonus - pollution_penalty) * difficulty_factor

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
        parsed = NightPlannerService._parse_time(item.best_time)
        return (parsed or fallback).strftime("%H:%M")

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
        return parsed

