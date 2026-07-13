from __future__ import annotations

from dataclasses import asdict, dataclass, field

from astro_viewer.app.services.localization import tr


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
    rise_time: str = field(default_factory=lambda: tr("n/d"))
    set_time: str = field(default_factory=lambda: tr("n/d"))
    culmination_time: str = field(default_factory=lambda: tr("n/d"))
    current_altitude: str = field(default_factory=lambda: tr("n/d"))
    current_azimuth: str = field(default_factory=lambda: tr("n/d"))
    score: int = 0
    score_label: str = field(default_factory=lambda: tr("n/d"))
    difficulty: str = field(default_factory=lambda: tr("n/d"))
    best_eyepiece: str = field(default_factory=lambda: tr("n/d"))
    barlow: str = field(default_factory=lambda: tr("No"))
    score_explanation: str = ""
    apparent_size: str = ""
    max_angular_size_deg: float | None = None
    recommended_observation_type: str = ""
    best_filter_class: str = ""
    fallback_filter_class: str = ""
    optional_color_filter_class: str = ""
    imaging_reducer_recommended: bool = False
    recommended_setup_type: str = ""
    setup_options: list[dict] = field(default_factory=list)
    equipment_explanation: str = ""
    observable_now: bool | None = None
    current_altitude_degrees: float | None = None
    current_azimuth_degrees: float | None = None
    intrinsic_score: int | None = None
    condition_flags: tuple[str, ...] = field(default_factory=tuple, compare=False, repr=False)
    detail_source: str = field(default="", compare=False, repr=False)

    def to_qml(self) -> dict:
        data = asdict(self)
        data.pop("condition_flags", None)
        data.pop("intrinsic_score", None)
        data.pop("detail_source", None)
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
        data["bestFilterClass"] = self.best_filter_class
        data["fallbackFilterClass"] = self.fallback_filter_class
        data["optionalColorFilterClass"] = self.optional_color_filter_class
        data["imagingReducerRecommended"] = self.imaging_reducer_recommended
        data["recommendedSetupType"] = self.recommended_setup_type
        data["setupOptions"] = self.setup_options
        data["equipmentExplanation"] = self.equipment_explanation
        data["observableNow"] = self.observable_now
        data["currentAltitudeDegrees"] = self.current_altitude_degrees
        data["currentAzimuthDegrees"] = self.current_azimuth_degrees
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
class MoonGeometrySummary:
    """Local Moon-target geometry diagnostic; never a direct score modifier."""

    object_id: str
    moon_altitude_deg: float | None = None
    moon_target_separation_deg: float | None = None
    moon_above_horizon: bool | None = None
    moon_visible_during_target_window: bool | None = None
    moon_set_before_target_window: bool | None = None
    sample_count: int = 0
    sample_policy: str = "bounded_start_mid_best_end"
    sampled_at: str = ""
    sample_times: tuple[str, ...] = field(default_factory=tuple)


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
    event_at: str = ""
    timing_kind: str = "instant"
    timing_label: str = field(default_factory=lambda: tr("Istante evento"))
    observing_window: str = ""
    visibility_state: str = "unknown"
    visibility_label: str = field(default_factory=lambda: tr("Da verificare"))
    visibility_detail: str = ""
    target_object_id: str = ""
    target_object_ids: tuple[str, ...] = field(default_factory=tuple)
    angular_separation_deg: float | None = None

    def to_qml(self) -> dict:
        data = asdict(self)
        data["type"] = self.event_type
        data["eventAt"] = self.event_at
        data["timingKind"] = self.timing_kind
        data["timingLabel"] = self.timing_label
        data["observingWindow"] = self.observing_window
        data["visibilityState"] = self.visibility_state
        data["visibilityLabel"] = self.visibility_label
        data["visibilityDetail"] = self.visibility_detail
        data["targetObjectId"] = self.target_object_id
        data["targetObjectIds"] = list(self.target_object_ids)
        data["angularSeparationDeg"] = self.angular_separation_deg
        return data
