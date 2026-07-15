from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import replace
from inspect import signature
from pathlib import Path
from unittest.mock import Mock

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import NightPlanItem, SkyQuality
from astro_viewer.app.services.observation_conditions_read_model import ObservationConditionsReadModelBuilder
from astro_viewer.app.services.observation_conditions_service import ObservationConditionInputs
from astro_viewer.app.services.sky_compass_service import SkyCompassService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_sky_compass_has_no_legacy_rollback_parameter() -> None:
    assert "use_nsom_sky_compass" not in signature(AppController.__init__).parameters


def test_missing_sky_quality_keeps_nsom_payload_contract() -> None:
    targets = _targets()
    expected = SkyCompassService().compass(
        list(targets),
        [],
        None,
        has_location=True,
        caution_text="Fixture caution",
        condition_inputs=_condition_inputs(None, radiance=None, illumination=20),
    )
    controller = _controller(sky_quality=None)

    result = controller._select_sky_compass_payload(targets, has_location=True, caution_text="Fixture caution")

    assert result == expected
    assert set(result) == set(_geometry_compass(targets))
    assert _target_payload_keys(result) == _target_payload_keys(_geometry_compass(targets))


def test_nsom_uses_observable_value_direction_policy_without_qml_shape_change() -> None:
    targets = _targets()
    geometry = _geometry_compass(targets)
    service = SkyCompassService()

    result = service.compass(
        targets,
        [],
        None,
        has_location=True,
        condition_inputs=_condition_inputs(9, radiance=120.0, illumination=20),
    )

    json.dumps(result, allow_nan=False)
    assert geometry["direction"] == "Sud"
    assert result["direction"] == "Nord-Est"
    assert set(result) == set(geometry)
    assert _target_payload_keys(result) == _target_payload_keys(geometry)
    assert result["primaryTargets"][0]["id"] == "globular_cluster"
    assert result["primaryTargets"][0]["score"] == 84
    assert "observable" not in result["primaryTargets"][0]
    assert "nsom" not in result["primaryTargets"][0]


def test_plan_and_best_object_are_annotations_not_direction_boosts() -> None:
    targets = _targets()
    globular = _find(targets, "globular_cluster")
    plan = [_plan_item(globular)]
    service = SkyCompassService()

    result = service.compass(
        targets,
        plan,
        globular,
        has_location=True,
        condition_inputs=_condition_inputs(2, radiance=1.0, illumination=10),
    )
    annotated_targets = service._targets(
        list(targets),
        {globular.id},
        globular.id,
        condition_inputs=_condition_inputs(2, radiance=1.0, illumination=10),
        moon_geometry_by_object_id=None,
        observable_objects_by_id=None,
    )

    assert result["direction"] == "Sud"
    planned = next(item for item in annotated_targets if item.id == globular.id)
    assert planned.in_plan is True
    assert planned.is_best is True
    assert all("piano" not in reason.lower() for reason in result["decisionReasons"])


def test_service_uses_observable_target_map_without_changing_payload_geometry() -> None:
    display_south = _object("galaxy", "Galaxy", "Galaxy", "Sud", 10, magnitude="8.2")
    display_north = _object("cluster", "Cluster", "Open Cluster", "Nord", 20, magnitude="5.0")
    raw_south = replace(display_south, score=96, max_altitude="80 gradi")

    result = SkyCompassService().compass(
        [display_south, display_north],
        [],
        None,
        has_location=True,
        condition_inputs=_condition_inputs(2, radiance=1.0, illumination=10),
        observable_objects_by_id={"galaxy": raw_south},
    )

    assert result["direction"] == "Sud"
    assert result["primaryTargets"][0] == {
        "id": "galaxy",
        "name": "Galaxy",
        "type": "Galaxy",
        "typeLabel": "Galassia",
        "typeCode": "galaxy",
        "score": 10,
        "inPlan": False,
        "isBest": False,
    }


def test_current_altitude_changes_direction_priority_without_exposing_nsom_fields() -> None:
    low = replace(
        _object("low", "Low", "Galaxy", "Sud", 80, magnitude="6.0"),
        observable_now=True,
        current_altitude_degrees=16.0,
    )
    high = replace(
        _object("high", "High", "Galaxy", "Nord", 80, magnitude="6.0"),
        observable_now=True,
        current_altitude_degrees=55.0,
    )

    result = SkyCompassService().compass(
        [low, high],
        [],
        None,
        has_location=True,
        condition_inputs=_condition_inputs(3, radiance=1.0, illumination=10),
    )

    assert result["direction"] == "Nord"
    assert result["primaryTargets"][0]["id"] == "high"
    assert "observableValue" not in result["primaryTargets"][0]


def test_controller_uses_nsom_with_and_without_sky_quality() -> None:
    targets = _targets()
    enabled = _controller(sky_quality=_sky_quality(9, radiance=120.0))
    missing_quality = _controller(sky_quality=None)

    enabled_result = enabled._select_sky_compass_payload(targets, has_location=True, caution_text="")
    missing_sky_result = missing_quality._select_sky_compass_payload(targets, has_location=True, caution_text="")

    assert enabled_result["direction"] == "Nord-Est"
    assert missing_sky_result == SkyCompassService().compass(
        list(targets),
        [],
        None,
        has_location=True,
        condition_inputs=_condition_inputs(None, radiance=None, illumination=20),
    )


def test_controller_sky_compass_split_adapter_uses_raw_physics_and_display_live_geometry() -> None:
    raw = _object("galaxy", "Galaxy", "Galaxy", "Sud", 90, magnitude="8.2")
    display = replace(
        raw,
        score=12,
        direction="Nord-Est",
        max_altitude="18 gradi",
        current_altitude="17 gradi",
        current_azimuth="45 gradi",
        condition_flags=("light_pollution",),
    )
    controller = _controller(
        sky_quality=_sky_quality(9, radiance=120.0),
        compass_service=Mock(return_value={"available": True}),
    )
    controller._deep_sky_raw_condition_input_by_id = {raw.id: raw}
    controller._conditioned_home_read_model = list(
        ObservationConditionsReadModelBuilder().from_display_targets(
            [display],
            source="test_sky_compass_read_model",
            raw_targets_by_id=controller._deep_sky_raw_condition_input_by_id,
        )
    )
    controller._sky_compass_service.compass.return_value = {"available": True}

    result = controller._select_sky_compass_payload([display], has_location=True, caution_text="")

    assert result == {"available": True}
    kwargs = controller._sky_compass_service.compass.call_args.kwargs
    observable = kwargs["observable_objects_by_id"]["galaxy"]
    assert observable.score == 90
    assert observable.direction == "Nord-Est"
    assert observable.max_altitude == "18 gradi"
    assert observable.current_altitude == "17 gradi"
    assert observable.current_azimuth == "45 gradi"
    assert controller._sky_compass_service.compass.call_args.args[0] == [display]


def test_service_failure_falls_back_to_geometry_with_diagnostic_log(caplog) -> None:
    targets = _targets()
    geometry = _geometry_compass(targets)
    failing_service = Mock()
    failing_service.compass.side_effect = [RuntimeError("fixture"), geometry]
    failing = _controller(
        sky_quality=_sky_quality(9, radiance=120.0),
        compass_service=failing_service,
    )

    with caplog.at_level(logging.WARNING, logger="astro_viewer.app.viewmodels.app_controller"):
        assert failing._select_sky_compass_payload(targets, has_location=True, caution_text="") == geometry
    assert failing_service.compass.call_count == 2
    assert "NSOM Sky Compass selection failed; using geometry fallback." in caplog.text


def test_no_location_no_targets_and_original_objects_are_not_mutated() -> None:
    targets = _targets()
    before = deepcopy(targets)
    service = SkyCompassService()

    no_location = service.compass(
        targets,
        [],
        None,
        has_location=False,
        condition_inputs=_condition_inputs(2, radiance=1.0, illumination=10),
    )
    no_targets = service.compass(
        [_object("hidden", "Hidden", "Galaxy", "Sud", 99, visible=False)],
        [],
        None,
        has_location=True,
        condition_inputs=_condition_inputs(2, radiance=1.0, illumination=10),
    )

    assert no_location == SkyCompassService.empty("no_location", "Configura una località per usare Sky Compass.")
    assert no_targets == SkyCompassService.empty("no_targets", "Nessun oggetto osservabile in questo momento.")
    assert targets == before


def test_nsom_sky_compass_runtime_path_is_not_exposed_to_qml_or_report_wiring() -> None:
    root = Path(__file__).parents[1]
    qml_text = "\n".join(path.read_text(encoding="utf-8") for path in (root / "app" / "ui").rglob("*.qml"))
    controller_text = (root / "app" / "viewmodels" / "app_controller.py").read_text(encoding="utf-8")

    assert "NSOM_SKY_COMPASS_ENABLED" not in qml_text
    assert "SkyCompassNsomDirectionService" not in qml_text
    assert "sky_compass_nsom_ranking" not in qml_text
    assert "sky_compass_nsom_comparison_report" not in controller_text
    assert "sky_compass_nsom_policy_readiness" not in controller_text
    assert not (root / "app" / "services" / "sky_compass_nsom_ranking.py").exists()


def _controller(
    *,
    sky_quality: SkyQuality | None,
    compass_service: object | None = None,
) -> AppController:
    controller = AppController.__new__(AppController)
    controller._sky_quality = sky_quality
    controller._moon = _moon(20)
    controller._sky_compass_service = compass_service or SkyCompassService()
    controller._night_plan = []
    controller._best_object = None
    return controller


def _geometry_compass(targets: tuple[CelestialObject, ...]) -> dict:
    return SkyCompassService().compass(list(targets), [], None, has_location=True)


def _target_payload_keys(payload: dict) -> set[str]:
    keys: set[str] = set()
    for key in ("targets", "primaryTargets"):
        for item in payload[key]:
            keys.update(item)
    return keys


def _targets() -> tuple[CelestialObject, ...]:
    return (
        _object("jupiter", "Jupiter", "Pianeta", "Est", 86, magnitude="-2.1", difficulty="Facile"),
        _object("moon", "Moon", "Moon", "Ovest", 82, magnitude="-12.0", difficulty="Facile"),
        _object("galaxy", "Galaxy", "Galaxy", "Sud", 90, magnitude="8.2"),
        _object("diffuse_nebula", "Diffuse Nebula", "Nebula", "Sud", 88, magnitude="7.0"),
        _object(
            "open_cluster",
            "Open Cluster",
            "Open Cluster",
            "Nord-Est",
            78,
            magnitude="5.2",
            difficulty="Facile",
        ),
        _object("globular_cluster", "Globular Cluster", "Globular Cluster", "Nord-Est", 84, magnitude="6.8"),
    )


def _object(
    object_id: str,
    name: str,
    object_type: str,
    direction: str,
    score: int,
    *,
    magnitude: str = "8.0",
    difficulty: str = "Media",
    visible: bool = True,
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=name,
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction=direction,
        best_time="22:00",
        observing_window="22:00 - 02:00",
        notes="Fixture",
        recommended_setup="Fixture setup",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=visible,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
    )


def _plan_item(item: CelestialObject) -> NightPlanItem:
    return NightPlanItem(
        time_label="22:00 sera",
        object_id=item.id,
        name=item.name,
        score=item.score,
        difficulty=item.difficulty,
        setup=item.recommended_setup,
        direction=item.direction,
        image=item.image,
    )


def _find(targets: tuple[CelestialObject, ...], object_id: str) -> CelestialObject:
    return next(item for item in targets if item.id == object_id)


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="SkyCompassNsomRankingFixture",
        description="Fixture",
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


def _condition_inputs(
    bortle: int | None,
    *,
    radiance: float | None,
    illumination: int,
) -> ObservationConditionInputs:
    return ObservationConditionInputs(
        sky_quality=(
            _sky_quality(bortle, radiance=radiance)
            if bortle is not None
            else None
        ),
        moon=_moon(illumination),
    )
