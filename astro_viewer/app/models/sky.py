from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SkyQuality:
    bortle_class: int
    limiting_magnitude: float
    sky_brightness: float
    source: str
    description: str
    confidence: str = "medium"
    viirs_radiance: float | None = None
    viirs_observation_count: int | None = None

    def to_qml(self) -> dict:
        data = asdict(self)
        data["bortleClass"] = self.bortle_class
        data["limitingMagnitude"] = self.limiting_magnitude
        data["skyBrightness"] = self.sky_brightness
        data["viirsRadiance"] = self.viirs_radiance
        data["viirsObservationCount"] = self.viirs_observation_count
        data["hasViirsRadiance"] = self.viirs_radiance is not None
        return data


@dataclass(frozen=True)
class SeeingTransparency:
    seeing: str
    transparency: str
    seeing_score: int
    transparency_score: int
    explanation: str
    source: str = "BasicForecastSeeingProvider"
    confidence: str = "medium"

    def to_qml(self) -> dict:
        data = asdict(self)
        data["seeing"] = _localized_quality_label(self.seeing)
        data["transparency"] = _localized_quality_label(self.transparency)
        data["seeingScore"] = self.seeing_score
        data["transparencyScore"] = self.transparency_score
        data["source"] = _localized_source(self.source)
        data["confidence"] = _localized_confidence(self.confidence)
        return data


@dataclass(frozen=True)
class AdvancedObservingScores:
    planetary_score: int
    deep_sky_score: int
    planetary_label: str
    deep_sky_label: str
    explanation: str

    def to_qml(self) -> dict:
        data = asdict(self)
        data["planetaryScore"] = self.planetary_score
        data["deepSkyScore"] = self.deep_sky_score
        data["planetaryLabel"] = self.planetary_label
        data["deepSkyLabel"] = self.deep_sky_label
        return data


def _localized_quality_label(value: str) -> str:
    labels = {
        "Excellent": "Eccellente",
        "Good": "Buono",
        "Average": "Discreto",
        "Poor": "Scarso",
    }
    return labels.get(value, value or "n/d")


def _localized_confidence(value: str) -> str:
    labels = {
        "high": "alta",
        "medium": "media",
        "low": "bassa",
    }
    return labels.get(value, value or "n/d")


def _localized_source(value: str) -> str:
    labels = {
        "BasicForecastSeeingProvider": "Stima meteo base",
        "MeteoblueSeeingProviderPlaceholder": "Stima meteo base",
        "CustomModelSeeingProvider": "Modello seeing personalizzato",
    }
    return labels.get(value, value or "n/d")


@dataclass(frozen=True)
class NightPlanItem:
    time_label: str
    object_id: str
    name: str
    score: int
    difficulty: str
    setup: str
    direction: str
    image: str

    def to_qml(self) -> dict:
        data = asdict(self)
        data["timeLabel"] = self.time_label
        data["objectId"] = self.object_id
        return data


@dataclass(frozen=True)
class Notification:
    title: str
    message: str
    trigger_time: str
    priority: int

    def to_qml(self) -> dict:
        data = asdict(self)
        data["triggerTime"] = self.trigger_time
        return data
