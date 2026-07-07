from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

import pytest

from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import NightPlanItem, SkyQuality
from astro_viewer.app.services.sky_compass_nsom_ranking import (
    NSOM_SKY_COMPASS_ENABLED,
    SkyCompassNsomDirectionService,
)
from astro_viewer.app.services.sky_compass_service import SkyCompassService
from astro_viewer.app.viewmodels.app_controller import AppController


def test_sky_compass_nsom_flag_is_default_off() -> None:
    assert NSOM_SKY_COMPASS_ENABLED is False
    assert AppController.__init__.__kwdefaults__["use_nsom_sky_compass"] is False


def test_flag_off_legacy_direction_and_payload_are_unchanged() -> None:
    targets = _targets()
    legacy = _legacy_compass(targets)
    controller = _controller(use_nsom_sky_compass=False, sky_quality=_sky_quality(9, radiance=120.0))

    result = controller._select_sky_compass_payload(targets, has_location=True, caution_text="Fixture caution")

    assert result == legacy | {"cautionText": "Fixture caution"}
    assert result["direction"] == "Sud"
    assert set(result) == set(legacy)
    assert _target_payload_keys(result) == _target_payload_keys(legacy)


def test_flag_on_uses_observable_value_direction_policy_without_qml_shape_change() -> None:
    targets = _targets()
    legacy = _legacy_compass(targets)
    service = SkyCompassNsomDirectionService()

    result = service.compass(
        targets,
        [],
        None,
        sky_quality=_sky_quality(9, radiance=120.0),
        moon=_moon(20),
        has_location=True,
    )

    json.dumps(result, allow_nan=False)
    assert legacy["direction"] == "Sud"
    assert result["direction"] == "Nord-Est"
    assert set(result) == set(legacy)
    assert _target_payload_keys(result) == _target_payload_keys(legacy)
    assert result["primaryTargets"][0]["id"] == "globular_cluster"
    assert result["primaryTargets"][0]["score"] == 84
    assert "observable" not in result["primaryTargets"][0]
    assert "nsom" not in result["primaryTargets"][0]


def test_flag_on_preserves_plan_and_best_object_context_boosts() -> None:
    targets = _targets()
    globular = _find(targets, "globular_cluster")
    plan = [_plan_item(globular)]

    result = SkyCompassNsomDirectionService().compass(
        targets,
        plan,
        globular,
        sky_quality=_sky_quality(2, radiance=1.0),
        moon=_moon(10),
        has_location=True,
    )

    assert result["direction"] == "Nord-Est"
    assert result["primaryTargets"][0] == {
        "id": "globular_cluster",
        "name": "Globular Cluster",
        "type": "Globular Cluster",
        "score": 84,
        "inPlan": True,
        "isBest": True,
    }
    assert result["decisionReasons"][0] == "Include un target già nel piano osservativo"


def test_controller_flag_on_uses_nsom_and_forced_rollback_uses_legacy() -> None:
    targets = _targets()
    enabled = _controller(use_nsom_sky_compass=True, sky_quality=_sky_quality(9, radiance=120.0))
    disabled = _controller(use_nsom_sky_compass=False, sky_quality=_sky_quality(9, radiance=120.0))

    enabled_result = enabled._select_sky_compass_payload(targets, has_location=True, caution_text="")
    disabled_result = disabled._select_sky_compass_payload(targets, has_location=True, caution_text="")

    assert enabled_result["direction"] == "Nord-Est"
    assert disabled_result == _legacy_compass(targets)
    assert disabled_result["direction"] == "Sud"


def test_missing_sky_quality_and_service_failure_fall_back_to_legacy_without_logging_or_shape_change() -> None:
    targets = _targets()
    legacy = _legacy_compass(targets)
    missing_quality = _controller(use_nsom_sky_compass=True, sky_quality=None)
    failing_service = Mock()
    failing_service.compass.side_effect = RuntimeError("fixture")
    failing = _controller(
        use_nsom_sky_compass=True,
        sky_quality=_sky_quality(9, radiance=120.0),
        nsom_service=failing_service,
    )

    assert missing_quality._select_sky_compass_payload(targets, has_location=True, caution_text="") == legacy
    assert failing._select_sky_compass_payload(targets, has_location=True, caution_text="") == legacy
    failing_service.compass.assert_called_once()


def test_no_location_no_targets_and_original_objects_are_not_mutated() -> None:
    targets = _targets()
    before = deepcopy(targets)
    service = SkyCompassNsomDirectionService()

    no_location = service.compass(
        targets,
        [],
        None,
        sky_quality=_sky_quality(2, radiance=1.0),
        moon=_moon(10),
        has_location=False,
    )
    no_targets = service.compass(
        [_object("hidden", "Hidden", "Galaxy", "Sud", 99, visible=False)],
        [],
        None,
        sky_quality=_sky_quality(2, radiance=1.0),
        moon=_moon(10),
        has_location=True,
    )

    assert no_location == SkyCompassService.empty("no_location", "Configura una località per usare Sky Compass.")
    assert no_targets == SkyCompassService.empty("no_targets", "Nessun target consigliato al momento.")
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


def _controller(
    *,
    use_nsom_sky_compass: bool,
    sky_quality: SkyQuality | None,
    nsom_service: object | None = None,
) -> AppController:
    controller = AppController.__new__(AppController)
    controller._use_nsom_sky_compass = use_nsom_sky_compass
    controller._sky_quality = sky_quality
    controller._moon = _moon(20)
    controller._sky_compass_service = SkyCompassService()
    controller._sky_compass_nsom_direction_service = nsom_service or SkyCompassNsomDirectionService()
    controller._night_plan = []
    controller._best_object = None
    return controller


def _legacy_compass(targets: tuple[CelestialObject, ...]) -> dict:
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
