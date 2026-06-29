from __future__ import annotations

from dataclasses import dataclass

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.observation_conditions_service import (
    ObservationConditionsService,
    TargetConditionBreakdown,
)


@dataclass(frozen=True)
class PlannerConditionBreakdown:
    object_id: str
    base_score: int
    moon_penalty: float = 0.0
    pollution_penalty: float = 0.0
    applied_components: tuple[str, ...] = ()
    diagnostic_notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlannerScoreBreakdown:
    object_id: str
    base_score: int
    category_score: int
    weather_score: int
    object_score_contribution: float
    category_score_contribution: float
    weather_score_contribution: float
    aperture_bonus: float
    moon_penalty: float
    pollution_penalty: float
    difficulty_factor: float
    weather_factor: float
    raw_score_before_difficulty: float
    raw_score_before_weather: float
    final_score: float
    conditions: PlannerConditionBreakdown


class PlannerScoringService:
    """Planner-specific score aggregation and diagnostics."""

    def __init__(self, conditions_service: ObservationConditionsService | None = None) -> None:
        self._conditions_service = conditions_service or ObservationConditionsService()

    def score(
        self,
        item: CelestialObject,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
    ) -> float:
        return self.score_breakdown(item, weather, scores, sky_quality, telescope, moon).final_score

    def score_breakdown(
        self,
        item: CelestialObject,
        weather: WeatherSummary,
        scores: AdvancedObservingScores,
        sky_quality: SkyQuality,
        telescope: Telescope,
        moon: MoonSummary | None = None,
    ) -> PlannerScoreBreakdown:
        category_score = scores.planetary_score if item.object_type == "Pianeta" else scores.deep_sky_score
        aperture_bonus = min(14, telescope.aperture_mm / 18)
        conditions = self.condition_breakdown(item, sky_quality, moon)
        difficulty_factor = self.difficulty_factor(item)
        weather_factor = self.weather_factor(weather)
        object_score_contribution = item.score * 0.48
        category_score_contribution = category_score * 0.34
        weather_score_contribution = weather.score_value * 0.18
        raw_score_before_difficulty = (
            object_score_contribution
            + category_score_contribution
            + weather_score_contribution
            + aperture_bonus
            - conditions.pollution_penalty
            - conditions.moon_penalty
        )
        raw_score_before_weather = raw_score_before_difficulty * difficulty_factor
        final_score = raw_score_before_weather * weather_factor
        return PlannerScoreBreakdown(
            object_id=item.id,
            base_score=item.score,
            category_score=category_score,
            weather_score=weather.score_value,
            object_score_contribution=object_score_contribution,
            category_score_contribution=category_score_contribution,
            weather_score_contribution=weather_score_contribution,
            aperture_bonus=aperture_bonus,
            moon_penalty=conditions.moon_penalty,
            pollution_penalty=conditions.pollution_penalty,
            difficulty_factor=difficulty_factor,
            weather_factor=weather_factor,
            raw_score_before_difficulty=raw_score_before_difficulty,
            raw_score_before_weather=raw_score_before_weather,
            final_score=final_score,
            conditions=conditions,
        )

    def moon_adjusted_score(self, item: CelestialObject, moon: MoonSummary | None) -> int:
        return self.moon_condition_breakdown(item, moon).adjusted_score

    def moon_penalty(self, item: CelestialObject, moon: MoonSummary | None) -> float:
        return self.moon_condition_breakdown(item, moon).moon_penalty

    def moon_condition_breakdown(
        self,
        item: CelestialObject,
        moon: MoonSummary | None,
    ) -> TargetConditionBreakdown:
        return self._conditions_service.moon_adjusted_score(item, moon)

    def pollution_penalty(self, item: CelestialObject, sky_quality: SkyQuality) -> float:
        return self._conditions_service.planner_pollution_penalty(item, sky_quality)

    def condition_breakdown(
        self,
        item: CelestialObject,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
    ) -> PlannerConditionBreakdown:
        moon_penalty = self.moon_penalty(item, moon)
        pollution_penalty = self.pollution_penalty(item, sky_quality)
        applied_components = []
        diagnostic_notes = []

        if moon_penalty > 0:
            applied_components.append("moon")
            diagnostic_notes.append(f"moon:illumination={self._conditions_service.moon_illumination(moon):g}")
        else:
            diagnostic_notes.append("moon:neutral")

        diagnostic_notes.extend(self._conditions_service.sky_quality_diagnostics(sky_quality))
        if pollution_penalty > 0:
            applied_components.append("planner_light_pollution")
            diagnostic_notes.append("planner_light_pollution:active")
        else:
            diagnostic_notes.append("planner_light_pollution:neutral")

        diagnostic_notes.extend(
            (
                "weather:planner_owned",
                "difficulty:planner_owned",
                "seeing:advanced_scores_input",
                "transparency:advanced_scores_input",
            )
        )
        return PlannerConditionBreakdown(
            object_id=item.id,
            base_score=item.score,
            moon_penalty=moon_penalty,
            pollution_penalty=pollution_penalty,
            applied_components=tuple(applied_components),
            diagnostic_notes=tuple(diagnostic_notes),
        )

    @staticmethod
    def weather_factor(weather: WeatherSummary) -> float:
        if weather.score_value >= 70:
            return 1.0
        if weather.score_value >= 50:
            return 0.85
        if weather.score_value >= 25:
            return 0.65
        return 0.35

    @staticmethod
    def difficulty_factor(item: CelestialObject) -> float:
        return {"Facile": 1.08, "Media": 0.95, "Difficile": 0.75}.get(item.difficulty, 0.85)
