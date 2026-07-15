from __future__ import annotations

from dataclasses import asdict, dataclass

import re

from astro_viewer.app.services.localization import format_number, tr


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
        data["source"] = _localized_sky_quality_source(self.source)
        data["confidenceLabel"] = _localized_confidence(self.confidence)
        data["viirsRadianceLabel"] = (
            tr(
                "{value} nW/(cm²·sr)",
                value=format_number(self.viirs_radiance, decimals=2),
            )
            if self.viirs_radiance is not None
            else ""
        )
        data["viirsObservationCountLabel"] = (
            tr("1 osservazione")
            if self.viirs_observation_count == 1
            else tr(
                "{count} osservazioni",
                count=self.viirs_observation_count,
            )
            if self.viirs_observation_count is not None
            else ""
        )
        data["skyBrightnessLabel"] = tr(
            "{value} mag/arcsec²",
            value=format_number(self.sky_brightness, decimals=2),
        )
        data["limitingMagnitudeLabel"] = tr(
            "{value} mag",
            value=format_number(self.limiting_magnitude, decimals=1),
        )
        data["bortleLabel"] = tr(
            "{value} - {description}",
            value=self.bortle_class,
            description=self.description,
        )
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
    atmospheric_transparency_score: int | None = None

    @property
    def atmospheric_transparency(self) -> str:
        if self.atmospheric_transparency_score is None:
            return self.transparency
        return _quality_label_from_score(self.atmospheric_transparency_score)

    def to_qml(self) -> dict:
        data = asdict(self)
        data["seeing"] = _localized_quality_label(self.seeing)
        data["transparency"] = _localized_quality_label(self.transparency)
        data["atmosphericTransparency"] = _localized_quality_label(self.atmospheric_transparency)
        data["seeingScore"] = self.seeing_score
        data["transparencyScore"] = self.transparency_score
        data["source"] = _localized_source(self.source)
        data["confidence"] = _localized_confidence(self.confidence)
        data.pop("atmospheric_transparency_score", None)
        return data


@dataclass(frozen=True)
class ObservingCategoryScores:
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
        "Excellent": tr("Eccellente"),
        "Good": tr("Buono"),
        "Average": tr("Discreto"),
        "Poor": tr("Scarso"),
    }
    return labels.get(value, value or tr("n/d"))


def _quality_label_from_score(score: int) -> str:
    if score >= 82:
        return "Excellent"
    if score >= 65:
        return "Good"
    if score >= 42:
        return "Average"
    return "Poor"


def _localized_confidence(value: str) -> str:
    labels = {
        "high": tr("alta"),
        "medium": tr("media"),
        "low": tr("bassa"),
        "unavailable": tr("n/d"),
    }
    return labels.get(value, value or tr("n/d"))


def _localized_source(value: str) -> str:
    labels = {
        "BasicForecastSeeingProvider": tr("Stima meteo base"),
        "MeteoblueSeeingProviderPlaceholder": tr("Stima meteo base"),
        "CustomModelSeeingProvider": tr("Modello seeing personalizzato"),
        "unavailable": tr("n/d"),
    }
    return labels.get(value, value or tr("n/d"))


def _localized_sky_quality_source(value: str) -> str:
    source = (value or "").strip()
    match = re.search(
        r"Fonte: NASA Black Marble VNP46A3 (\d{4}-\d{2}) "
        r"\(radiance ([0-9]+(?:\.[0-9]+)?) nW/cm\^2 sr, obs (\d+)\)",
        source,
    )
    if match:
        return tr(
            "Fonte: NASA Black Marble VNP46A3 {month} "
            "(radianza {radiance} nW/(cm²·sr), osservazioni {observations})",
            month=match.group(1),
            radiance=format_number(float(match.group(2)), decimals=2),
            observations=int(match.group(3)),
        )
    if source.startswith("Fonte: "):
        return tr("Fonte: {source}", source=source.removeprefix("Fonte: "))
    return source or tr("n/d")


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
