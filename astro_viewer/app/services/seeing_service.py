from __future__ import annotations

import math
import os
from typing import Protocol

from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherHour


class SeeingTransparencyService:
    """Selects a seeing provider and returns astronomical seeing/transparency estimates."""

    def __init__(self, provider: "SeeingProvider | None" = None):
        self._provider = provider or self._default_provider()

    def estimate(self, hours: list[WeatherHour], sky_quality: SkyQuality) -> SeeingTransparency:
        return self._provider.estimate(hours, sky_quality)

    @staticmethod
    def _default_provider() -> "SeeingProvider":
        if os.getenv("NIGHTSCOPE_METEOBLUE_API_KEY"):
            return MeteoblueSeeingProviderPlaceholder()
        return BasicForecastSeeingProvider()


class SeeingProvider(Protocol):
    name: str

    def estimate(self, hours: list[WeatherHour], sky_quality: SkyQuality) -> SeeingTransparency:
        ...


class BasicForecastSeeingProvider:
    name = "BasicForecastSeeingProvider"

    def estimate(self, hours: list[WeatherHour], sky_quality: SkyQuality) -> SeeingTransparency:
        night_hours = self._night_hours(hours)
        if not night_hours:
            return SeeingTransparency(
                "Average",
                "Average",
                50,
                50,
                "Dati meteo insufficienti.",
                source=self.name,
                confidence="low",
            )

        avg_wind = sum(hour.wind_kmh for hour in night_hours) / len(night_hours)
        avg_gust = sum(hour.wind_gusts_kmh or hour.wind_kmh for hour in night_hours) / len(night_hours)
        avg_cloud = sum(hour.cloud_cover for hour in night_hours) / len(night_hours)
        avg_low_cloud = sum(hour.cloud_cover_low for hour in night_hours) / len(night_hours)
        avg_mid_cloud = sum(hour.cloud_cover_mid for hour in night_hours) / len(night_hours)
        avg_high_cloud = sum(hour.cloud_cover_high for hour in night_hours) / len(night_hours)
        avg_humidity = sum(hour.humidity for hour in night_hours) / len(night_hours)
        avg_dew_gap = self._average_dew_gap(night_hours)
        avg_visibility = sum(hour.visibility_m for hour in night_hours if hour.visibility_m > 0)
        visibility_count = len([hour for hour in night_hours if hour.visibility_m > 0])
        avg_visibility = avg_visibility / visibility_count if visibility_count else 12_000

        seeing_score = 100
        seeing_score -= max(0, round((avg_wind - 8) * 2.0))
        seeing_score -= max(0, round((avg_gust - 18) * 1.3))
        seeing_score -= max(0, round((avg_low_cloud - 35) * 0.2))
        if avg_dew_gap is not None and avg_dew_gap < 2.5:
            seeing_score -= 8
        seeing_score = max(0, min(100, seeing_score))

        transparency_score = 100
        transparency_score -= round(avg_cloud * 0.35)
        transparency_score -= round(avg_low_cloud * 0.25)
        transparency_score -= round(avg_mid_cloud * 0.18)
        transparency_score -= round(avg_high_cloud * 0.08)
        transparency_score -= max(0, round((avg_humidity - 65) * 0.45))
        transparency_score -= self._pollution_transparency_penalty(sky_quality)
        if avg_visibility < 10_000:
            transparency_score -= 12
        transparency_score = max(0, min(100, transparency_score))

        explanation = (
            f"Vento medio {avg_wind:.0f} km/h, raffiche {avg_gust:.0f} km/h, "
            f"nuvolosita bassa/media/alta {avg_low_cloud:.0f}/{avg_mid_cloud:.0f}/{avg_high_cloud:.0f}%, "
            f"umidita {avg_humidity:.0f}%."
        )
        return SeeingTransparency(
            seeing=self._label(seeing_score),
            transparency=self._label(transparency_score),
            seeing_score=seeing_score,
            transparency_score=transparency_score,
            explanation=explanation,
            source=self.name,
            confidence="medium" if visibility_count else "low",
        )

    @staticmethod
    def _label(score: int) -> str:
        if score >= 82:
            return "Excellent"
        if score >= 65:
            return "Good"
        if score >= 42:
            return "Average"
        return "Poor"

    @staticmethod
    def _pollution_transparency_penalty(sky_quality: SkyQuality) -> int:
        radiance = getattr(sky_quality, "viirs_radiance", None)
        if radiance is not None:
            return min(48, round(math.log10(max(0.0, radiance) + 1.0) * 14))
        return max(0, (sky_quality.bortle_class - 3) * 6)

    @staticmethod
    def _night_hours(hours: list[WeatherHour]) -> list[WeatherHour]:
        selected = []
        for hour in hours:
            try:
                hour_value = int(hour.time[:2])
            except ValueError:
                continue
            if hour_value >= 19 or hour_value <= 5:
                selected.append(hour)
        return selected or hours[:8]

    @staticmethod
    def _average_dew_gap(hours: list[WeatherHour]) -> float | None:
        gaps = [
            hour.temperature_c - hour.dew_point_c
            for hour in hours
            if hour.dew_point_c is not None
        ]
        if not gaps:
            return None
        return sum(gaps) / len(gaps)


class MeteoblueSeeingProviderPlaceholder:
    name = "MeteoblueSeeingProviderPlaceholder"

    def estimate(self, hours: list[WeatherHour], sky_quality: SkyQuality) -> SeeingTransparency:
        result = BasicForecastSeeingProvider().estimate(hours, sky_quality)
        return SeeingTransparency(
            result.seeing,
            result.transparency,
            result.seeing_score,
            result.transparency_score,
            f"{result.explanation} Provider Meteoblue non configurato; usata stima base.",
            source=self.name,
            confidence="low",
        )


class CustomModelSeeingProvider(BasicForecastSeeingProvider):
    name = "CustomModelSeeingProvider"
