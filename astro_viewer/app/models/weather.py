from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class WeatherHour:
    timestamp: str
    time: str
    cloud_cover: int
    precipitation_probability: int
    wind_kmh: int
    humidity: int
    temperature_c: float
    visibility_m: int = 0

    def to_qml(self) -> dict:
        data = asdict(self)
        data["timestamp"] = self.timestamp
        data["cloudCover"] = self.cloud_cover
        data["precipitationProbability"] = self.precipitation_probability
        data["windKmh"] = self.wind_kmh
        data["humidity"] = self.humidity
        data["temperatureC"] = self.temperature_c
        data["visibilityM"] = self.visibility_m
        return data


@dataclass(frozen=True)
class WeatherSummary:
    score: str
    score_value: int
    explanation: str
    cloud_cover: int
    precipitation_probability: int
    wind_kmh: int
    humidity: int
    temperature_c: float
    alert: str

    def to_qml(self) -> dict:
        data = asdict(self)
        data["scoreValue"] = self.score_value
        data["explanation"] = self.explanation
        data["cloudCover"] = self.cloud_cover
        data["precipitationProbability"] = self.precipitation_probability
        data["windKmh"] = self.wind_kmh
        data["temperatureC"] = self.temperature_c
        return data
