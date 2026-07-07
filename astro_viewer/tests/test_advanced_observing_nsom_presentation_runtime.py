from __future__ import annotations

import json
import math
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QObject

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.observing import MoonSummary
from astro_viewer.app.models.sky import AdvancedObservingScores, SeeingTransparency, SkyQuality
from astro_viewer.app.models.weather import WeatherHour, WeatherSummary
from astro_viewer.app.services.advanced_observing_nsom_presentation import (
    ADVANCED_OBSERVING_NSOM_PRESENTATION_SCHEMA_VERSION,
    build_advanced_observing_nsom_presentation,
)
from astro_viewer.app.services.advanced_observing_nsom_service import (
    NSOM_ADVANCED_OBSERVING_ENABLED,
    AdvancedObservingNsomService,
)
from astro_viewer.app.services.advanced_observing_service import AdvancedObservingService
from astro_viewer.app.services.night_planner_service import NightPlannerService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_disabled_presentation_projection_is_strict_json_and_private() -> None:
    payload = build_advanced_observing_nsom_presentation(
        None,
        None,
        session_state="",
        confidence_value=math.nan,
    )

    json.dumps(payload, sort_keys=True, allow_nan=False)

    assert payload["schemaVersion"] == ADVANCED_OBSERVING_NSOM_PRESENTATION_SCHEMA_VERSION
    assert payload["runtimeState"] == "disabled"
    assert payload["enabled"] is False
    assert payload["runtimeSafety"]["defaultOff"] is False
    assert payload["categories"] == []
    assert payload["currentQmlProperty"] == "advancedScores"
    assert payload["futureQmlProperty"] == "advancedObservingNsom"
    assert payload["confidence"]["scoreEffect"] == 0.0
    assert payload["confidence"]["value"] is None
    assert payload["consumerPolicy"]["replacesAdvancedScores"] is False
    assert payload["consumerPolicy"]["plannerInput"] is False
    assert payload["consumerPolicy"]["notificationInput"] is False


def test_enabled_presentation_projection_matches_contract_layers() -> None:
    legacy = _legacy_scores(_weather(90), _seeing(), _sky_quality(9, radiance=120.0), _moon(95))
    nsom = _nsom_scores(_weather(90), _seeing(), _sky_quality(9, radiance=120.0), _moon(95))

    payload = build_advanced_observing_nsom_presentation(
        nsom,
        legacy,
        session_state="recommended",
        confidence_value=1.0,
    )

    json.dumps(payload, sort_keys=True, allow_nan=False)

    assert payload["runtimeState"] == "default_on_internal_projection"
    assert payload["enabled"] is True
    assert {category["id"] for category in payload["categories"]} == {"planetary", "deepSky"}
    for category in payload["categories"]:
        assert category["mathPipeline"] == [
            "IntrinsicTargetQuality",
            "ObservationEnvironment",
            "EffectiveObservability",
            "ObservableTargetValue",
        ]
        assert "PracticalTargetValue" in category["excludedFromCategoryValue"]
        assert "SessionViability" in category["excludedFromCategoryValue"]
        assert "RecommendationConfidence" in category["excludedFromCategoryValue"]
        assert "ObservationOpportunity" in category["excludedFromCategoryValue"]
    assert payload["session"]["state"] == "recommended"
    assert payload["session"]["scoreEffect"] == 0.0
    assert payload["confidence"]["value"] == 1.0
    assert payload["confidence"]["scoreEffect"] == 0.0


def test_presentation_projection_sanitizes_non_finite_score_values() -> None:
    malformed = AdvancedObservingScores(
        planetary_score=math.nan,
        deep_sky_score=math.inf,
        planetary_label="n/d",
        deep_sky_label="n/d",
        explanation="Malformed fixture",
    )

    payload = build_advanced_observing_nsom_presentation(
        malformed,
        malformed,
        confidence_value=-math.inf,
    )

    json.dumps(payload, sort_keys=True, allow_nan=False)

    for category in payload["categories"]:
        assert category["diagnosticValue"] is None
        assert category["legacyCompatibilityValue"] is None
    assert payload["confidence"]["value"] is None


def test_controller_flag_off_does_not_project_advanced_observing_nsom_presentation() -> None:
    controller = _controller(enabled=False)

    controller._recalculate_observing_outputs()

    assert controller._advanced_scores == _legacy_scores(
        controller._weather_summary,
        controller._seeing_transparency,
        controller._sky_quality,
        controller._moon,
    )
    assert controller._advanced_observing_nsom_scores is None
    assert controller._advanced_observing_nsom_presentation is None
    assert controller._advanced_observing_nsom_payload() == {}


def test_controller_forced_on_projects_presentation_without_changing_advanced_scores() -> None:
    controller = _controller(enabled=True)
    expected_legacy = _legacy_scores(
        controller._weather_summary,
        controller._seeing_transparency,
        controller._sky_quality,
        controller._moon,
    )
    expected_nsom = _nsom_scores(
        controller._weather_summary,
        controller._seeing_transparency,
        controller._sky_quality,
        controller._moon,
    )

    controller._recalculate_observing_outputs()

    payload = controller._advanced_observing_nsom_presentation
    json.dumps(payload, sort_keys=True, allow_nan=False)

    assert controller._advanced_scores == expected_legacy
    assert controller._advanced_observing_nsom_scores == expected_nsom
    assert controller._advanced_observing_nsom_scores != controller._advanced_scores
    assert payload["enabled"] is True
    assert payload["runtimeState"] == "default_on_internal_projection"
    assert payload["consumerPolicy"]["replacesAdvancedScores"] is False
    values_by_category = {category["id"]: category for category in payload["categories"]}
    assert values_by_category["planetary"]["diagnosticValue"] == expected_nsom.planetary_score
    assert values_by_category["deepSky"]["diagnosticValue"] == expected_nsom.deep_sky_score
    assert values_by_category["planetary"]["legacyCompatibilityValue"] == expected_legacy.planetary_score
    assert values_by_category["deepSky"]["legacyCompatibilityValue"] == expected_legacy.deep_sky_score
    assert controller._advanced_observing_nsom_payload() == payload


def test_controller_default_path_projects_presentation_without_changing_advanced_scores() -> None:
    controller = _controller(enabled=NSOM_ADVANCED_OBSERVING_ENABLED)
    expected_legacy = _legacy_scores(
        controller._weather_summary,
        controller._seeing_transparency,
        controller._sky_quality,
        controller._moon,
    )
    expected_nsom = _nsom_scores(
        controller._weather_summary,
        controller._seeing_transparency,
        controller._sky_quality,
        controller._moon,
    )

    controller._recalculate_observing_outputs()

    payload = controller._advanced_observing_nsom_presentation
    json.dumps(payload, sort_keys=True, allow_nan=False)

    assert controller._advanced_scores == expected_legacy
    assert controller._advanced_observing_nsom_scores == expected_nsom
    assert payload["enabled"] is True
    assert payload["runtimeState"] == "default_on_internal_projection"
    assert payload["summary"]["status"] == "default_on_internal_projection"
    assert payload["runtimeSafety"]["defaultOff"] is False
    assert payload["consumerPolicy"]["replacesAdvancedScores"] is False


def test_presentation_session_metadata_matches_monitor_session_state() -> None:
    controller = _controller(
        enabled=True,
        weather=_weather(10, cloud_cover=88, precipitation_probability=80),
        weather_hours=(
            _weather_hour("02:00", cloud_cover=88, precipitation_probability=80),
            _weather_hour("03:00", cloud_cover=24, precipitation_probability=0),
            _weather_hour("04:00", cloud_cover=24, precipitation_probability=0),
        ),
    )

    controller._recalculate_observing_outputs()

    assert controller._advanced_observing_nsom_presentation["session"]["state"] == "monitor"
    assert controller._observing_session_decision().state == "monitor"


def test_presentation_projection_does_not_feed_planner_or_notifications() -> None:
    controller = _controller(enabled=True)
    planner = _PlannerSpy()
    notifications = _NotificationSpy()
    controller._night_planner_service = planner
    controller._notification_service = notifications

    controller._recalculate_observing_outputs()

    assert controller._advanced_observing_nsom_presentation is not None
    assert planner.received_scores == controller._advanced_scores
    assert notifications.received_scores == controller._advanced_scores
    assert planner.received_scores != controller._advanced_observing_nsom_scores
    assert notifications.received_scores != controller._advanced_observing_nsom_scores


def test_presentation_projection_has_read_only_qml_property_but_no_visible_qml_usage() -> None:
    app_root = Path(__file__).parents[1] / "app"
    controller_text = (app_root / "viewmodels" / "app_controller.py").read_text(encoding="utf-8")
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (app_root / "ui").rglob("*.qml")
    )

    assert '@Property("QVariant", notify=weatherChanged)\n    def advancedObservingNsom' in controller_text
    assert "advancedObservingNsomChanged" not in controller_text
    assert "controller.advancedObservingNsom" not in qml_text


def test_advanced_observing_nsom_property_reads_defensive_copy_without_recomputing() -> None:
    controller = _controller(enabled=True)
    sentinel = {
        "schemaVersion": "sentinel",
        "enabled": True,
        "categories": [{"id": "deepSky", "diagnosticValue": 0.82}],
    }
    controller._advanced_observing_nsom_presentation = sentinel

    payload = controller._advanced_observing_nsom_payload()
    assert payload == sentinel
    assert payload is not sentinel

    payload["categories"][0]["diagnosticValue"] = 0.0
    assert sentinel["categories"][0]["diagnosticValue"] == 0.82


def test_advanced_observing_nsom_qt_property_is_read_only_and_returns_copy() -> None:
    controller = AppController.__new__(AppController)
    QObject.__init__(controller)
    snapshot = {
        "schemaVersion": ADVANCED_OBSERVING_NSOM_PRESENTATION_SCHEMA_VERSION,
        "enabled": True,
        "categories": [{"id": "planetary", "diagnosticValue": 0.74}],
        "confidence": {"value": 1.0, "scoreEffect": 0.0},
    }
    controller._advanced_observing_nsom_presentation = snapshot

    property_index = controller.metaObject().indexOfProperty("advancedObservingNsom")
    assert property_index >= 0
    qml_property = controller.metaObject().property(property_index)

    assert qml_property.name() == "advancedObservingNsom"
    assert qml_property.isWritable() is False
    assert qml_property.hasNotifySignal() is True
    assert qml_property.notifySignal().name().data().decode() == "weatherChanged"

    payload = controller.property("advancedObservingNsom")
    json.dumps(payload, sort_keys=True, allow_nan=False)

    assert payload == snapshot
    assert payload is not snapshot
    payload["categories"][0]["diagnosticValue"] = 0.0
    assert snapshot["categories"][0]["diagnosticValue"] == 0.74


class _PlannerSpy:
    def __init__(self) -> None:
        self.received_scores: AdvancedObservingScores | None = None

    def plan(self, _objects, _weather, scores, _sky_quality, _telescope, _moon):
        self.received_scores = scores
        return []

    @staticmethod
    def weather_blocking_status(weather: WeatherSummary):
        return NightPlannerService.weather_blocking_status(weather)


class _NotificationSpy:
    def __init__(self) -> None:
        self.received_scores: AdvancedObservingScores | None = None

    def notifications(self, _best_object, _plan, _events, scores, _moon):
        self.received_scores = scores
        return []


def _controller(
    *,
    enabled: bool,
    weather: WeatherSummary | None = None,
    weather_hours: tuple[WeatherHour, ...] = (),
) -> AppController:
    controller = AppController.__new__(AppController)
    controller._use_nsom_advanced_observing = enabled
    controller._advanced_observing_service = AdvancedObservingService()
    controller._advanced_observing_nsom_service = AdvancedObservingNsomService()
    controller._weather_summary = weather or _weather(90)
    controller._seeing_transparency = _seeing()
    controller._sky_quality = _sky_quality(9, radiance=120.0)
    controller._moon = _moon(95)
    controller._weather_hours = list(weather_hours)
    controller._seeing_service = SimpleNamespace(
        estimate=lambda _hours, _sky_quality: controller._seeing_transparency
    )
    controller._refresh_conditioned_observing_candidates = lambda: None
    controller._home_visible_objects = lambda objects: objects
    controller._select_best_object = lambda _objects: None
    controller._visible_planets = []
    controller._deep_sky = []
    controller._events = []
    controller._current_telescope = lambda: Telescope(
        "scope",
        "Fixture scope",
        120,
        900,
        "Refractor",
        "Alt-az",
    )
    controller._night_planner_service = _PlannerSpy()
    controller._sky_map_service = SimpleNamespace(map_targets=lambda _objects: [])
    controller._refresh_sky_compass = lambda: None
    controller._notification_service = _NotificationSpy()
    controller._refresh_nsom_diagnostics = lambda: None
    controller._advanced_scores = None
    controller._advanced_observing_nsom_scores = None
    controller._advanced_observing_nsom_presentation = None
    controller._best_object = None
    controller._night_plan = []
    controller._sky_map = []
    controller._notifications = []
    return controller


def _legacy_scores(
    weather: WeatherSummary,
    seeing: SeeingTransparency,
    sky_quality: SkyQuality,
    moon: MoonSummary,
) -> AdvancedObservingScores:
    return AdvancedObservingService().scores(weather, seeing, sky_quality, moon)


def _nsom_scores(
    weather: WeatherSummary,
    seeing: SeeingTransparency,
    sky_quality: SkyQuality,
    moon: MoonSummary,
) -> AdvancedObservingScores:
    return AdvancedObservingNsomService().scores(weather, seeing, sky_quality, moon)


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Advanced Observing NSOM presentation fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _weather_hour(
    time: str,
    *,
    cloud_cover: int,
    precipitation_probability: int,
) -> WeatherHour:
    return WeatherHour(
        timestamp=f"2026-06-21T{time}",
        time=time,
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=6,
        humidity=55,
        temperature_c=18.0,
        visibility_m=18_000,
    )


def _seeing() -> SeeingTransparency:
    return SeeingTransparency(
        seeing="Fixture",
        transparency="Fixture",
        seeing_score=86,
        transparency_score=84,
        explanation="Advanced Observing NSOM presentation fixture",
    )


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="AdvancedObservingNsomPresentationFixture",
        description="Advanced Observing NSOM presentation fixture",
        viirs_radiance=radiance,
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="20:00",
        set_time="06:00",
        best_note="Fixture",
        image="",
    )
