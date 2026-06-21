from __future__ import annotations

from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.observing_score_service import ObservingScoreService


class AdvancedObservingService:
    """Produces separate planetary and deep-sky scores."""

    def scores(
        self,
        weather: WeatherSummary,
        seeing: SeeingTransparency,
        sky_quality: SkyQuality,
        moon: MoonSummary | None,
    ) -> AdvancedObservingScores:
        moon_illumination = self._moon_illumination(moon)

        planetary = round(
            weather.score_value * 0.36
            + seeing.seeing_score * 0.42
            + (100 - min(55, weather.wind_kmh * 1.4)) * 0.12
            + (100 - min(25, moon_illumination * 0.15)) * 0.10
        )
        deep_sky = round(
            weather.score_value * 0.34
            + seeing.transparency_score * 0.30
            + (100 - max(0, sky_quality.bortle_class - 1) * 11) * 0.24
            + (100 - moon_illumination) * 0.12
        )
        planetary = max(0, min(100, planetary))
        deep_sky = max(0, min(100, deep_sky))
        explanation = (
            f"Planetary pesa seeing e vento; Deep Sky pesa trasparenza, Luna e Bortle {sky_quality.bortle_class}."
        )
        scorer = ObservingScoreService()
        return AdvancedObservingScores(
            planetary_score=planetary,
            deep_sky_score=deep_sky,
            planetary_label=scorer.score_label(planetary),
            deep_sky_label=scorer.score_label(deep_sky),
            explanation=explanation,
        )

    @staticmethod
    def _moon_illumination(moon: MoonSummary | None) -> float:
        if moon is None:
            return 50.0
        try:
            return float(moon.illumination.replace("%", ""))
        except ValueError:
            return 50.0
