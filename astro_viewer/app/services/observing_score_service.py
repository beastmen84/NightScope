from __future__ import annotations

from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.weather import WeatherHour, WeatherSummary


class ObservingScoreService:
    """Combines weather and Moon conditions into a compact astronomy score."""

    def weather_score(self, hours: list[WeatherHour], moon: MoonSummary | None = None) -> WeatherSummary:
        observing_hours = list(hours)
        if not observing_hours:
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

        avg_cloud = round(sum(hour.cloud_cover for hour in observing_hours) / len(observing_hours))
        max_rain = max(hour.precipitation_probability for hour in observing_hours)
        avg_wind = round(sum(hour.wind_kmh for hour in observing_hours) / len(observing_hours))
        avg_humidity = round(sum(hour.humidity for hour in observing_hours) / len(observing_hours))
        avg_temp = round(sum(hour.temperature_c for hour in observing_hours) / len(observing_hours), 1)
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
            explanation_parts.append("nuvolosità moderata")
        else:
            explanation_parts.append("nuvolosità elevata")
        if max_rain >= 35:
            explanation_parts.append("rischio precipitazioni")
        if avg_wind < 15:
            explanation_parts.append("vento debole")
        elif avg_wind > 28:
            explanation_parts.append("vento sostenuto")
        if moon_penalty >= 12:
            explanation_parts.append("Luna luminosa")

        explanation = ", ".join(explanation_parts).capitalize() + "."
        alert = f"Qualità osservativa stanotte: {score}/100, {label.lower()}. {explanation}"
        return WeatherSummary(label, score, explanation, avg_cloud, max_rain, avg_wind, avg_humidity, avg_temp, alert)

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
    def _moon_penalty(moon: MoonSummary | None) -> int:
        if moon is None:
            return 0
        illumination = moon.illumination.strip().replace("%", "")
        try:
            value = float(illumination)
        except ValueError:
            return 0
        return round(max(0.0, value - 35.0) * 0.28)
