from __future__ import annotations

from astro_viewer.app.models.sky import SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherHour


class SeeingTransparencyService:
    """Estimates seeing and transparency from available forecast variables."""

    def estimate(self, hours: list[WeatherHour], sky_quality: SkyQuality) -> SeeingTransparency:
        night_hours = self._night_hours(hours)
        if not night_hours:
            return SeeingTransparency("Average", "Average", 50, 50, "Dati meteo insufficienti.")

        avg_wind = sum(hour.wind_kmh for hour in night_hours) / len(night_hours)
        avg_cloud = sum(hour.cloud_cover for hour in night_hours) / len(night_hours)
        avg_humidity = sum(hour.humidity for hour in night_hours) / len(night_hours)
        avg_visibility = sum(hour.visibility_m for hour in night_hours if hour.visibility_m > 0)
        visibility_count = len([hour for hour in night_hours if hour.visibility_m > 0])
        avg_visibility = avg_visibility / visibility_count if visibility_count else 12_000

        seeing_score = 100
        seeing_score -= max(0, round((avg_wind - 8) * 2.3))
        seeing_score -= max(0, round((avg_cloud - 35) * 0.25))
        seeing_score = max(0, min(100, seeing_score))

        transparency_score = 100
        transparency_score -= round(avg_cloud * 0.55)
        transparency_score -= max(0, round((avg_humidity - 65) * 0.45))
        transparency_score -= max(0, (sky_quality.bortle_class - 3) * 6)
        if avg_visibility < 10_000:
            transparency_score -= 12
        transparency_score = max(0, min(100, transparency_score))

        explanation = (
            f"Vento medio {avg_wind:.0f} km/h, nuvolosita {avg_cloud:.0f}%, "
            f"umidita {avg_humidity:.0f}%."
        )
        return SeeingTransparency(
            seeing=self._label(seeing_score),
            transparency=self._label(transparency_score),
            seeing_score=seeing_score,
            transparency_score=transparency_score,
            explanation=explanation,
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

