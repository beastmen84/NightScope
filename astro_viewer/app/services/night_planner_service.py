from __future__ import annotations

import math
from datetime import datetime, timedelta

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
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
        moon: MoonSummary | None = None,
    ) -> list[NightPlanItem]:
        if self._weather_blocks_plan(weather):
            return []

        visible = [item for item in objects if item.visible and item.score > 0 and self._has_useful_window(item)]
        if not visible:
            visible = [item for item in objects if item.visible and item.score > 0]
        ranked = sorted(
            visible,
            key=lambda item: self._planner_score(item, weather, scores, sky_quality, telescope, moon),
            reverse=True,
        )
        start = self._start_time(ranked)
        items = []
        used_names = set()
        for index, item in enumerate(ranked):
            if item.name in used_names:
                continue
            used_names.add(item.name)
            score = round(self._planner_score(item, weather, scores, sky_quality, telescope, moon))
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
        moon: MoonSummary | None = None,
    ) -> float:
        category_score = scores.planetary_score if item.object_type == "Pianeta" else scores.deep_sky_score
        aperture_bonus = min(14, telescope.aperture_mm / 18)
        pollution_penalty = NightPlannerService._pollution_penalty(item, sky_quality)
        moon_penalty = NightPlannerService.moon_penalty(item, moon)
        difficulty_factor = {"Facile": 1.08, "Media": 0.95, "Difficile": 0.75}.get(item.difficulty, 0.85)
        raw_score = (
            item.score * 0.48
            + category_score * 0.34
            + weather.score_value * 0.18
            + aperture_bonus
            - pollution_penalty
            - moon_penalty
        ) * difficulty_factor
        return raw_score * NightPlannerService._weather_factor(weather)

    @staticmethod
    def _weather_blocks_plan(weather: WeatherSummary) -> bool:
        return (
            weather.score_value <= 25
            or weather.precipitation_probability >= 65
            or weather.cloud_cover >= 85
        )

    @staticmethod
    def _weather_factor(weather: WeatherSummary) -> float:
        if weather.score_value >= 70:
            return 1.0
        if weather.score_value >= 50:
            return 0.85
        if weather.score_value >= 25:
            return 0.65
        return 0.35

    @staticmethod
    def moon_adjusted_score(item: CelestialObject, moon: MoonSummary | None) -> int:
        return max(0, min(100, round(item.score - NightPlannerService.moon_penalty(item, moon))))

    @staticmethod
    def moon_penalty(item: CelestialObject, moon: MoonSummary | None) -> float:
        sensitivity = NightPlannerService._moon_sensitivity(item)
        if sensitivity <= 0:
            return 0.0
        illumination = NightPlannerService._moon_illumination(moon)
        illumination_factor = max(0.0, min(1.0, (illumination - 25.0) / 75.0))
        return sensitivity * illumination_factor

    @staticmethod
    def _moon_illumination(moon: MoonSummary | None) -> float:
        if moon is None:
            return 0.0
        try:
            return float(moon.illumination.strip().replace("%", "").replace(",", "."))
        except ValueError:
            return 0.0

    @staticmethod
    def _moon_sensitivity(item: CelestialObject) -> float:
        lower_type = item.object_type.lower()
        if item.object_type == "Pianeta" or item.id in {
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
        }:
            return 0.0
        if "diffuse" in lower_type:
            return 42.0
        if "galaxy" in lower_type or "galassia" in lower_type:
            return 38.0
        if "planetary nebula" in lower_type or "nebulosa planetaria" in lower_type:
            return 18.0
        if "h ii" in lower_type or "emission" in lower_type or "supernova" in lower_type or "nebula" in lower_type or "nebul" in lower_type:
            return 26.0
        if "globular" in lower_type or "ammasso globulare" in lower_type:
            return 18.0
        if "open" in lower_type or "cluster" in lower_type or "star cloud" in lower_type or "asterism" in lower_type:
            return 10.0
        return 14.0

    @staticmethod
    def _pollution_penalty(item: CelestialObject, sky_quality: SkyQuality) -> float:
        lower_type = item.object_type.lower()
        if item.object_type == "Pianeta":
            return 0.0

        radiance = getattr(sky_quality, "viirs_radiance", None)
        if radiance is not None:
            base = min(30.0, math.log10(max(0.0, radiance) + 1.0) * 9.0)
        else:
            base = max(0, sky_quality.bortle_class - 4) * 4.0

        if "galaxy" in lower_type or "galassia" in lower_type:
            base *= 1.65
        elif "nebula" in lower_type or "nebul" in lower_type:
            base *= 1.35
        elif "globular" in lower_type:
            base *= 1.05
        elif "open" in lower_type or "cluster" in lower_type:
            base *= 0.7
        return base

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
