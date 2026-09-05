"""Define hourly weather, summary, blocking, and session-decision records."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from astro_viewer.app.services.localization import format_compact_number, format_number, tr


@dataclass(frozen=True)
class WeatherHour:
    timestamp: str
    time: str
    cloud_cover: int
    precipitation_probability: int
    wind_kmh: int
    humidity: int
    temperature_c: float
    visibility_m: int | None = 0
    cloud_cover_low: int | None = 0
    cloud_cover_mid: int | None = 0
    cloud_cover_high: int | None = 0
    wind_gusts_kmh: int | None = 0
    dew_point_c: float | None = None
    # Provider rows can support weather but lack the extra seeing inputs.
    seeing_inputs_complete: bool = True

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
        data["cloudCoverLabel"] = tr(
            "{value}%", value=format_number(self.cloud_cover)
        )
        data["precipitationProbabilityLabel"] = tr(
            "{value}%", value=format_number(self.precipitation_probability)
        )
        data["windLabel"] = tr(
            "{value} km/h", value=format_number(self.wind_kmh)
        )
        data["humidityLabel"] = tr(
            "{value}%", value=format_number(self.humidity)
        )
        data["temperatureLabel"] = tr(
            "{value} °C",
            value=format_compact_number(self.temperature_c, max_decimals=1),
        )
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
    limiting_factors: tuple[str, ...] = ()

    def to_qml(self) -> dict:
        data = asdict(self)
        data["scoreValue"] = self.score_value
        data["explanation"] = self.explanation
        data["cloudCover"] = self.cloud_cover
        data["precipitationProbability"] = self.precipitation_probability
        data["windKmh"] = self.wind_kmh
        data["temperatureC"] = self.temperature_c
        data["cloudCoverLabel"] = tr(
            "{value}%", value=format_number(self.cloud_cover)
        )
        data["precipitationProbabilityLabel"] = tr(
            "{value}%", value=format_number(self.precipitation_probability)
        )
        data["windLabel"] = tr(
            "{value} km/h", value=format_number(self.wind_kmh)
        )
        data["humidityLabel"] = tr(
            "{value}%", value=format_number(self.humidity)
        )
        data["temperatureLabel"] = tr(
            "{value} °C",
            value=format_compact_number(self.temperature_c, max_decimals=1),
        )
        data["limitingFactors"] = list(self.limiting_factors)
        data.pop("limiting_factors", None)
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
