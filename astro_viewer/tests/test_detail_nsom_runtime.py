from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.detail_nsom_runtime import (
    DETAIL_SOURCE_CATALOGUE,
    DETAIL_SOURCE_OBSERVING,
    NSOM_DETAIL_OBJECT_ENABLED,
    DetailObjectNsomRuntimeService,
)
from astro_viewer.app.services.observation_conditions_service import ObservationConditionsService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_detail_object_nsom_flag_is_default_off() -> None:
    assert NSOM_DETAIL_OBJECT_ENABLED is False
    assert AppController.__init__.__kwdefaults__["use_nsom_detail_object"] is NSOM_DETAIL_OBJECT_ENABLED


def test_detail_object_nsom_runtime_payload_is_strict_json_internal_and_score_neutral() -> None:
    target = _target("galaxy", "Galaxy", 88)

    payload = _runtime_payload(target, moon=_moon(95)).to_dict()

    json.dumps(payload, sort_keys=True, allow_nan=False)
    assert payload["schemaVersion"] == "detail-object-nsom-runtime-v1"
    assert payload["objectId"] == "galaxy"
    assert {
        "intrinsicTargetQuality",
        "observationEnvironment",
        "effectiveObservability",
        "observableTargetValue",
        "observerCapability",
        "practicalTargetValue",
        "sessionViability",
        "recommendationConfidence",
    } <= set(payload)
    assert payload["sessionViability"]["role"] == "metadata_only_for_detail_object"
    assert payload["sessionViability"]["scoreFactor"] is False
    assert payload["recommendationConfidence"]["role"] == "metadata_only"
    assert payload["recommendationConfidence"]["scoreFactor"] is False
    assert payload["ownership"]["observationOpportunity"] == "not_used_for_detail_object"
    assert payload["metadata"] == {
        "internalOnly": True,
        "runtimePath": True,
        "defaultFlagEnabled": False,
        "qmlExposure": False,
        "selectedObjectPayloadChanged": False,
        "selectedObjectFieldsAdded": False,
        "runtimeObjectMutated": False,
        "fileWrites": False,
        "automaticLogging": False,
        "network": False,
        "homeChanged": False,
        "bestObjectChanged": False,
        "plannerChanged": False,
        "skyCompassChanged": False,
    }


def test_controller_flag_off_preserves_selected_object_and_returns_no_internal_payload() -> None:
    controller = _controller(enabled=False, source=DETAIL_SOURCE_OBSERVING, moon=_moon(95))
    before = AppController.selectedObject.fget(controller)

    payload = controller._selected_object_nsom_payload()
    after = AppController.selectedObject.fget(controller)

    assert payload == {}
    assert after == before
    assert "observableTargetValue" not in after
    assert "detailObjectNsom" not in after


def test_controller_forced_on_builds_internal_payload_without_changing_selected_object_shape() -> None:
    controller = _controller(enabled=True, source=DETAIL_SOURCE_OBSERVING, moon=_moon(95))
    before = AppController.selectedObject.fget(controller)

    payload = controller._selected_object_nsom_payload()
    after = AppController.selectedObject.fget(controller)

    assert payload["objectId"] == controller._selected_object.id
    assert payload["source"] == DETAIL_SOURCE_OBSERVING
    assert payload["selectedObjectPolicy"]["selectedObjectPreserved"] is True
    assert payload["selectedObjectPolicy"]["nsomFieldsAddedToSelectedObject"] is False
    assert payload["selectedObjectPolicy"]["legacyDisplayPolicy"] == "observing_detail_moon_adjusted_copy"
    assert after == before
    assert set(after) == set(before)
    assert "observableTargetValue" not in after
    assert "practicalTargetValue" not in after
    assert "recommendationConfidence" not in after


def test_controller_forced_on_preserves_catalogue_selected_object_policy() -> None:
    controller = _controller(enabled=True, source=DETAIL_SOURCE_CATALOGUE, moon=_moon(95))
    before = AppController.selectedObject.fget(controller)

    payload = controller._selected_object_nsom_payload()
    after = AppController.selectedObject.fget(controller)

    assert payload["source"] == DETAIL_SOURCE_CATALOGUE
    assert payload["selectedObjectPolicy"]["legacyDisplayPolicy"] == "catalogue_detail_raw_object"
    assert payload["selectedObjectPolicy"]["selectedObjectFormula"] == "_object_to_qml(selected_object)"
    assert after == before
    assert payload["observableTargetValue"]["value"] < before["score"]


def test_missing_runtime_inputs_leave_detail_nsom_payload_empty() -> None:
    controller = _controller(enabled=True, source=DETAIL_SOURCE_OBSERVING)

    controller._sky_quality = None
    assert controller._selected_object_nsom_payload() == {}

    controller = _controller(enabled=True, source=DETAIL_SOURCE_OBSERVING)
    controller._weather_summary = None
    assert controller._selected_object_nsom_payload() == {}


def test_detail_runtime_does_not_mutate_runtime_objects() -> None:
    target = _target("galaxy", "Galaxy", 88)
    before = deepcopy(target)

    _runtime_payload(target, moon=_moon(95)).to_dict()

    assert target == before


def test_detail_runtime_session_viability_is_metadata_only() -> None:
    target = _target("galaxy", "Galaxy", 88)

    good = _runtime_payload(target, weather=_weather(90), moon=_moon(15)).to_dict()
    blocked = _runtime_payload(
        target,
        weather=_weather(10, cloud_cover=96, precipitation_probability=85),
        moon=_moon(15),
    ).to_dict()

    assert blocked["sessionViability"]["state"] == "blocked"
    assert blocked["sessionViability"]["value"] == pytest.approx(0.0)
    assert blocked["observableTargetValue"]["value"] == pytest.approx(good["observableTargetValue"]["value"])
    assert blocked["practicalTargetValue"]["value"] == pytest.approx(good["practicalTargetValue"]["value"])


def test_detail_runtime_equipment_changes_practical_value_only() -> None:
    target = _target("galaxy", "Galaxy", 88)
    small = _runtime_payload(
        target,
        telescope=_telescope(name="Small Manual", aperture_mm=60, focal_length_mm=400, mount="manual"),
        moon=_moon(15),
    ).to_dict()
    large = _runtime_payload(
        target,
        telescope=_telescope(name="Large GoTo", aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
        moon=_moon(15),
    ).to_dict()

    assert large["observableTargetValue"]["value"] == pytest.approx(small["observableTargetValue"]["value"])
    assert large["practicalTargetValue"]["value"] > small["practicalTargetValue"]["value"]
    assert large["observerCapability"]["qTarget"] > small["observerCapability"]["qTarget"]


def test_detail_runtime_confidence_is_score_neutral() -> None:
    target = _target("galaxy", "Galaxy", 88)
    low = _runtime_payload(
        target,
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
        moon=_moon(15),
    ).to_dict()
    high = _runtime_payload(
        target,
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
        moon=_moon(15),
    ).to_dict()

    assert low["recommendationConfidence"]["value"] < high["recommendationConfidence"]["value"]
    assert low["recommendationConfidence"]["scoreFactor"] is False
    assert low["observableTargetValue"]["value"] == pytest.approx(high["observableTargetValue"]["value"])
    assert low["practicalTargetValue"]["value"] == pytest.approx(high["practicalTargetValue"]["value"])


def test_detail_nsom_runtime_path_has_no_qml_or_report_wiring() -> None:
    app_root = Path(__file__).parents[1] / "app"
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in (app_root / "ui").rglob("*.qml"))
    controller_text = (app_root / "viewmodels" / "app_controller.py").read_text(encoding="utf-8")
    service_text = (app_root / "services" / "detail_nsom_runtime.py").read_text(encoding="utf-8")

    assert "NSOM_DETAIL_OBJECT_ENABLED" not in qml_text
    assert "DetailObjectNsomRuntimeService" not in qml_text
    assert "detailObjectNsom" not in qml_text
    assert "@Property(\"QVariant\", notify=selectedObjectChanged)\n    def detailObjectNsom" not in controller_text
    assert "DETAIL_OBJECT_NSOM_COMPARISON_REPORT" not in controller_text
    assert "DETAIL_OBJECT_NSOM_READINESS_AUDIT" not in controller_text
    assert "astro_viewer.tools" not in service_text
    assert "detail_nsom_comparison_report" not in service_text


def _runtime_payload(
    target: CelestialObject,
    *,
    source: str = DETAIL_SOURCE_OBSERVING,
    weather: WeatherSummary | None = None,
    sky_quality: SkyQuality | None = None,
    telescope: Telescope | None = None,
    moon: MoonSummary | None = None,
    confidence: RecommendationConfidence | None = None,
):
    return DetailObjectNsomRuntimeService().payload(
        target,
        source=source,
        weather=weather or _weather(90),
        sky_quality=sky_quality or _sky_quality(3),
        telescope=telescope or _telescope(),
        moon=moon or _moon(15),
        confidence=confidence,
    )


def _controller(
    *,
    enabled: bool,
    source: str,
    weather: WeatherSummary | None = None,
    sky_quality: SkyQuality | None = None,
    moon: MoonSummary | None = None,
) -> AppController:
    controller = AppController.__new__(AppController)
    controller._use_nsom_detail_object = enabled
    controller._detail_object_nsom_runtime_service = DetailObjectNsomRuntimeService()
    controller._selected_object = _target("galaxy", "Galaxy", 88)
    controller._selected_object_source = source
    controller._weather_summary = weather or _weather(90)
    controller._sky_quality = sky_quality or _sky_quality(3)
    controller._moon = moon if moon is not None else _moon(15)
    controller._current_telescope = lambda: _telescope()
    controller._conditions_service = ObservationConditionsService()
    controller._object_descriptions = {}
    controller._is_catalogue_detail_object = lambda _item: False
    controller._home_time_label = lambda item: item.best_time
    controller._home_window_label = lambda item: item.observing_window
    controller._observing_status = lambda _item: ("", "")
    controller._observing_reasons = lambda _item: []
    controller._setup_reason = lambda _item: ""
    return controller


def _target(
    object_id: str,
    object_type: str,
    score: int,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.replace("_", " ").title(),
        object_type=object_type,
        image="",
        magnitude="8.0",
        distance="",
        max_altitude="55 gradi",
        direction="Sud",
        best_time="22:30",
        observing_window="21:00 - 02:00",
        notes="Deterministic Detail NSOM runtime fixture.",
        recommended_setup="Telescopio",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="4 h",
        visible=True,
        score=score,
        score_label="Buono",
        difficulty="Media",
        recommended_setup_type="Telescope",
        apparent_size="20 arcmin",
    )


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Buono",
        score_value=score,
        explanation="Deterministic Detail NSOM runtime weather fixture.",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=8,
        humidity=55,
        temperature_c=12.0,
        alert="",
    )


def _sky_quality(bortle: int) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=6.2,
        sky_brightness=21.2,
        source="deterministic_fixture",
        description="Deterministic Detail NSOM runtime sky fixture.",
        confidence="high",
    )


def _moon(illumination: int) -> MoonSummary:
    return MoonSummary(
        phase="Fixture",
        illumination=f"{illumination}%",
        rise_time="18:00",
        set_time="06:00",
        best_note="Fixture Moon.",
        image="",
        phase_angle=90.0,
    )


def _telescope(
    *,
    name: str = "Medium GoTo",
    aperture_mm: int = 130,
    focal_length_mm: int = 900,
    mount: str = "GoTo EQ",
) -> Telescope:
    return Telescope(
        id=name.casefold().replace(" ", "-"),
        name=name,
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Reflector",
        mount=mount,
    )
