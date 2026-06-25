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
    cloud_cover_low: int = 0
    cloud_cover_mid: int = 0
    cloud_cover_high: int = 0
    wind_gusts_kmh: int = 0
    dew_point_c: float | None = None

    def to_qml(self) -> dict:
        data = asdict(self)
        data["timestamp"] = self.timestamp
        data["cloudCover"] = self.cloud_cover
        data["precipitationProbability"] = self.precipitation_probability
        data["windKmh"] = self.wind_kmh
        data["humidity"] = self.humidity
        data["temperatureC"] = self.temperature_c
        data["visibilityM"] = self.visibility_m
        data["cloudCoverLow"] = self.cloud_cover_low
        data["cloudCoverMid"] = self.cloud_cover_mid
        data["cloudCoverHigh"] = self.cloud_cover_high
        data["windGustsKmh"] = self.wind_gusts_kmh
        data["dewPointC"] = self.dew_point_c
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


@dataclass(frozen=True)
class WeatherBlockingStatus:
    blocks_plan: bool
    show_warning: bool
    reason: str = ""
    detail: str = ""


@dataclass(frozen=True)
class ObservingSessionDecision:
    state: str
    title: str = ""
    icon: str = ""
    detail: str = ""
    description: str = ""
    show_opportunity: bool = False
