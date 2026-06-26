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

        avg_wind = self._average_weather_value(night_hours, "wind_kmh")
        avg_gust = sum(self._gust_value(hour) for hour in night_hours) / len(night_hours)
        avg_cloud = self._average_weather_value(night_hours, "cloud_cover")
        avg_low_cloud = self._average_weather_value(night_hours, "cloud_cover_low")
        avg_mid_cloud = self._average_weather_value(night_hours, "cloud_cover_mid")
        avg_high_cloud = self._average_weather_value(night_hours, "cloud_cover_high")
        avg_humidity = self._average_weather_value(night_hours, "humidity")
        avg_dew_gap = self._average_dew_gap(night_hours)
        visibility_values = [
            visibility
            for hour in night_hours
            if (visibility := self._optional_weather_value(hour, "visibility_m")) is not None and visibility > 0
        ]
        visibility_count = len(visibility_values)
        avg_visibility = sum(visibility_values)
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
            f"nuvolosità bassa/media/alta {avg_low_cloud:.0f}/{avg_mid_cloud:.0f}/{avg_high_cloud:.0f}%, "
            f"umidità {avg_humidity:.0f}%."
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
            except (TypeError, ValueError):
                continue
            if hour_value >= 19 or hour_value <= 5:
                selected.append(hour)
        return selected or hours[:8]

    @classmethod
    def _average_dew_gap(cls, hours: list[WeatherHour]) -> float | None:
        gaps = []
        for hour in hours:
            temperature = cls._optional_weather_value(hour, "temperature_c")
            dew_point = cls._optional_weather_value(hour, "dew_point_c")
            if temperature is not None and dew_point is not None:
                gaps.append(temperature - dew_point)
        if not gaps:
            return None
        return sum(gaps) / len(gaps)

    @classmethod
    def _average_weather_value(cls, hours: list[WeatherHour], field_name: str) -> float:
        if not hours:
            return 0.0
        return sum(cls._weather_value(hour, field_name) for hour in hours) / len(hours)

    @classmethod
    def _gust_value(cls, hour: WeatherHour) -> float:
        gust = cls._optional_weather_value(hour, "wind_gusts_kmh")
        if gust is not None and gust > 0:
            return gust
        return cls._weather_value(hour, "wind_kmh")

    @classmethod
    def _weather_value(cls, hour: WeatherHour, field_name: str) -> float:
        value = cls._optional_weather_value(hour, field_name)
        return value if value is not None else 0.0

    @staticmethod
    def _optional_weather_value(hour: WeatherHour, field_name: str) -> float | None:
        value = getattr(hour, field_name, None)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


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
