from __future__ import annotations

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.weather import WeatherHour, WeatherSummary


class ObservingScoreService:
    """Combines weather and Moon conditions into a compact astronomy score."""

    def weather_score(self, hours: list[WeatherHour], moon: MoonSummary | None = None) -> WeatherSummary:
        night_hours = self._night_hours(hours)
        if not night_hours:
            return WeatherSummary(
                score="Pessima",
                score_value=0,
                explanation="Previsioni non disponibili.",
                cloud_cover=0,
                precipitation_probability=0,
                wind_kmh=0,
                humidity=0,
                temperature_c=0.0,
                alert="Meteo non disponibile: uso dei dati astronomici possibile, ma senza valutazione del cielo.",
            )

        avg_cloud = round(sum(hour.cloud_cover for hour in night_hours) / len(night_hours))
        max_rain = max(hour.precipitation_probability for hour in night_hours)
        avg_wind = round(sum(hour.wind_kmh for hour in night_hours) / len(night_hours))
        avg_humidity = round(sum(hour.humidity for hour in night_hours) / len(night_hours))
        avg_temp = round(sum(hour.temperature_c for hour in night_hours) / len(night_hours), 1)
        moon_penalty = self._moon_penalty(moon)

        score = 100
        score -= min(55, round(avg_cloud * 0.55))
        score -= min(30, round(max_rain * 0.45))
        score -= max(0, avg_wind - 10)
        score -= max(0, round((avg_humidity - 70) * 0.25))
        score -= moon_penalty
        score = max(0, min(100, score))

        label = self.score_label(score)
        explanation_parts = []
        if avg_cloud < 25:
            explanation_parts.append("poche nuvole")
        elif avg_cloud < 55:
            explanation_parts.append("nuvolosita moderata")
        else:
            explanation_parts.append("nuvolosita elevata")
        if max_rain >= 35:
            explanation_parts.append("rischio precipitazioni")
        if avg_wind < 15:
            explanation_parts.append("vento debole")
        elif avg_wind > 28:
            explanation_parts.append("vento sostenuto")
        if moon_penalty >= 12:
            explanation_parts.append("Luna luminosa")

        explanation = ", ".join(explanation_parts).capitalize() + "."
        alert = f"Qualita osservativa stanotte: {score}/100, {label.lower()}. {explanation}"
        return WeatherSummary(label, score, explanation, avg_cloud, max_rain, avg_wind, avg_humidity, avg_temp, alert)

    def best_object(self, objects: list[CelestialObject], weather_summary: WeatherSummary) -> CelestialObject | None:
        visible_objects = [item for item in objects if item.visible]
        if not visible_objects:
            return None
        weather_factor = max(0.25, weather_summary.score_value / 100.0)
        return max(
            visible_objects,
            key=lambda item: item.score * weather_factor * self._difficulty_factor(item.difficulty),
        )

    @staticmethod
    def score_label(score: int) -> str:
        if score <= 25:
            return "Pessima"
        if score <= 50:
            return "Scarsa"
        if score <= 70:
            return "Discreta"
        if score <= 85:
            return "Buona"
        return "Ottima"

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
    def _moon_penalty(moon: MoonSummary | None) -> int:
        if moon is None:
            return 0
        illumination = moon.illumination.strip().replace("%", "")
        try:
            value = float(illumination)
        except ValueError:
            return 0
        return round(max(0.0, value - 35.0) * 0.28)

    @staticmethod
    def _difficulty_factor(difficulty: str) -> float:
        return {
            "Facile": 1.12,
            "Media": 0.94,
            "Difficile": 0.68,
        }.get(difficulty, 0.85)
