from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class CelestialObject:
    id: str
    name: str
    object_type: str
    image: str
    magnitude: str
    distance: str
    max_altitude: str
    direction: str
    best_time: str
    observing_window: str
    notes: str
    recommended_setup: str
    visibility_class: str
    azimuth: str
    time_above_horizon: str
    visible: bool = True
    rise_time: str = "n/d"
    set_time: str = "n/d"
    culmination_time: str = "n/d"
    current_altitude: str = "n/d"
    current_azimuth: str = "n/d"
    score: int = 0
    score_label: str = "n/d"
    difficulty: str = "n/d"
    best_eyepiece: str = "n/d"
    barlow: str = "No"
    score_explanation: str = ""
    apparent_size: str = ""
    max_angular_size_deg: float | None = None
    recommended_observation_type: str = ""
    recommended_setup_type: str = ""
    setup_options: list[dict] = field(default_factory=list)
    equipment_explanation: str = ""

    def to_qml(self) -> dict:
        data = asdict(self)
        data["type"] = self.object_type
        data["riseTime"] = self.rise_time
        data["setTime"] = self.set_time
        data["culminationTime"] = self.culmination_time
        data["currentAltitude"] = self.current_altitude
        data["currentAzimuth"] = self.current_azimuth
        data["scoreLabel"] = self.score_label
        data["bestEyepiece"] = self.best_eyepiece
        data["scoreExplanation"] = self.score_explanation
        data["apparentSize"] = self.apparent_size
        data["maxAngularSizeDeg"] = self.max_angular_size_deg
        data["recommendedObservationType"] = self.recommended_observation_type
        data["recommendedSetupType"] = self.recommended_setup_type
        data["setupOptions"] = self.setup_options
        data["equipmentExplanation"] = self.equipment_explanation
        return data


@dataclass(frozen=True)
class MoonSummary:
    phase: str
    illumination: str
    rise_time: str
    set_time: str
    best_note: str
    image: str
    phase_angle: float = 0.0

    def to_qml(self) -> dict:
        data = asdict(self)
        data["phaseAngle"] = self.phase_angle
        return data


@dataclass(frozen=True)
class AstronomicalEvent:
    id: str
    title: str
    event_type: str
    date_label: str
    best_time: str
    usefulness: int
    setup: str
    note: str

    def to_qml(self) -> dict:
        data = asdict(self)
        data["type"] = self.event_type
        return data
