from __future__ import annotations

import math

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
            + self._light_pollution_quality(sky_quality) * 0.24
            + (100 - moon_illumination) * 0.12
        )
        planetary = max(0, min(100, planetary))
        deep_sky = max(0, min(100, deep_sky))
        explanation = (
            f"Planetario pesa seeing e vento; cielo profondo pesa trasparenza, Luna e Bortle {sky_quality.bortle_class}."
        )
        scorer = ObservingScoreService()
        deep_sky_label = scorer.score_label(deep_sky)
        if sky_quality.bortle_class >= 8 and 51 <= deep_sky <= 65:
            deep_sky_label = "Limitata"
        return AdvancedObservingScores(
            planetary_score=planetary,
            deep_sky_score=deep_sky,
            planetary_label=scorer.score_label(planetary),
            deep_sky_label=deep_sky_label,
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

    @staticmethod
    def _light_pollution_quality(sky_quality: SkyQuality) -> int:
        radiance = getattr(sky_quality, "viirs_radiance", None)
        if radiance is not None:
            return max(8, min(100, round(100 - math.log10(max(0.0, radiance) + 1.0) * 38)))
        return 100 - max(0, sky_quality.bortle_class - 1) * 11
