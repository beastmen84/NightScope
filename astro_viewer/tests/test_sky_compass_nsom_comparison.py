from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from astro_viewer.app.models.equipment import Telescope
from astro_viewer.app.models.nsom import RecommendationConfidence
from astro_viewer.app.models.observing import CelestialObject, MoonSummary
from astro_viewer.app.models.sky import NightPlanItem, SkyQuality
from astro_viewer.app.models.weather import WeatherSummary
from astro_viewer.app.services.sky_compass_nsom_comparison import SkyCompassNsomComparisonService
from astro_viewer.app.services.sky_compass_service import SkyCompassService


def test_sky_compass_nsom_comparison_is_strict_json_and_developer_only() -> None:
    comparison = _compare(
        [
            _target("planet", "Pianeta", 84, direction="Est"),
            _target("galaxy", "Galaxy", 88, direction="Sud"),
        ],
        sky_quality=_sky_quality(8, radiance=45.0),
        moon=_moon(85),
    )

    json.dumps(comparison, allow_nan=False)

    assert comparison["metadata"]["developer_only"] is True
    assert comparison["metadata"]["runtime_wiring"] is False
    assert comparison["metadata"]["reference_only"] is True
    assert comparison["metadata"]["score_parity_expected"] is False
    assert comparison["metadata"]["side_effects"] == {
        "file_writes": False,
        "automatic_logging": False,
        "network": False,
        "qml_exposure": False,
        "sky_compass_changed": False,
        "home_changed": False,
        "best_object_changed": False,
        "planner_changed": False,
    }
    assert comparison["legacy_formula"]["direction_formula"].startswith("sum(item.score")
    assert comparison["legacy_formula"]["selected_direction"] == "Sud"

    galaxy = _entry(comparison, "galaxy")
    assert {
        "intrinsic_target_quality",
        "observation_environment",
        "effective_observability",
        "observable_target_value",
        "observer_capability",
        "practical_target_value",
        "session_viability",
        "recommendation_confidence",
        "ownership",
    } <= set(galaxy["nsom"])
    assert "upstream_score_breakdown:not_available_from_sky_compass_candidate" in galaxy["legacy"][
        "sky_compass_target"
    ]["unavailable_components"]


def test_legacy_direction_formula_matches_sky_compass_service() -> None:
    m13 = _target("messier-M13", "Ammasso globulare", 72, direction="Nord-Est")
    m92 = _target("messier-M92", "Ammasso globulare", 58, direction="Nord-Est")
    venus = _target("venus", "Pianeta", 94, direction="Est")
    plan = [_plan_item(m13)]
    targets = [venus, m92, m13]

    comparison = _compare(targets, night_plan=plan, best_object=m13)
    compass = SkyCompassService().compass(targets, plan, m13, has_location=True)

    assert comparison["legacy_formula"]["selected_direction"] == compass["direction"] == "Nord-Est"
    north_east = _direction_group(comparison, "Nord-Est")
    assert north_east["legacy"]["direction_score"] == (72 + 42 + 58 + 10) + (58 + 10)
    assert north_east["selected_by_runtime"] is True
    assert _legacy_target(comparison, "messier-M13")["components"] == {
        "item_score": 72,
        "in_plan_bonus": 42,
        "best_object_bonus": 58,
        "target_presence_bonus": 10,
    }
    assert comparison["rankings"]["legacy_direction"][0]["direction"] == "Nord-Est"


def test_bright_moon_and_light_pollution_are_sky_owned_reference_effects() -> None:
    targets = [
        _target("planet", "Pianeta", 84, direction="Est"),
        _target("galaxy", "Galaxy", 88, direction="Sud"),
    ]
    dark = _compare(targets, sky_quality=_sky_quality(3), moon=_moon(10))
    bright = _compare(targets, sky_quality=_sky_quality(9, radiance=120.0), moon=_moon(95))

    assert _legacy_contribution(bright, "galaxy") == pytest.approx(_legacy_contribution(dark, "galaxy"))
    assert _environment(bright, "galaxy")["lunar_sky_background"] < _environment(dark, "galaxy")[
        "lunar_sky_background"
    ]
    assert _environment(bright, "galaxy")["static_sky_background"] < _environment(dark, "galaxy")[
        "static_sky_background"
    ]
    assert _effective(bright, "galaxy") < _effective(dark, "galaxy")

    assert _environment(bright, "planet")["lunar_sky_background"] == pytest.approx(1.0)
    assert _environment(bright, "planet")["static_sky_background"] == pytest.approx(1.0)
    ownership = _ownership(bright, "galaxy")
    assert ownership["sky_effects"]["used_in_observable_target_value"] is True
    assert ownership["sky_effects"]["used_in_legacy_sky_compass_formula"] is False


def test_blocked_weather_is_session_metadata_not_sky_compass_or_target_value_input() -> None:
    target = _target("galaxy", "Galaxy", 88, direction="Sud")
    good = _compare([target], weather=_weather(88), sky_quality=_sky_quality(3), moon=_moon(10))
    blocked = _compare(
        [target],
        weather=_weather(15, cloud_cover=95, precipitation_probability=85),
        sky_quality=_sky_quality(3),
        moon=_moon(10),
        caution_text="Condizioni non ideali",
    )

    assert _legacy_contribution(blocked, "galaxy") == pytest.approx(_legacy_contribution(good, "galaxy"))
    assert _observable(blocked, "galaxy") == pytest.approx(_observable(good, "galaxy"))
    assert _practical(blocked, "galaxy") == pytest.approx(_practical(good, "galaxy"))
    assert blocked["metadata"]["session_viability"]["state"] == "blocked"
    assert blocked["metadata"]["session_viability"]["value"] == pytest.approx(0.0)
    assert _ownership(blocked, "galaxy")["session_weather_effects"]["used_in_legacy_sky_compass_formula"] is False


def test_equipment_changes_practical_reference_only() -> None:
    target = _target("galaxy", "Galaxy", 88, direction="Sud")
    small = _compare(
        [target],
        telescope=_telescope(name="Small Manual", aperture_mm=60, focal_length_mm=400, mount="manual"),
    )
    large = _compare(
        [target],
        telescope=_telescope(name="Large GoTo", aperture_mm=220, focal_length_mm=1800, mount="GoTo EQ"),
    )

    assert _legacy_contribution(large, "galaxy") == pytest.approx(_legacy_contribution(small, "galaxy"))
    assert _observable(large, "galaxy") == pytest.approx(_observable(small, "galaxy"))
    assert _practical(large, "galaxy") > _practical(small, "galaxy")
    ownership = _ownership(small, "galaxy")
    assert ownership["observer_equipment_effects"]["used_in_observable_target_value"] is False
    assert ownership["observer_equipment_effects"]["used_in_practical_target_value"] is True
    assert ownership["observer_equipment_effects"]["used_in_legacy_sky_compass_formula"] is False


def test_confidence_is_metadata_only_and_does_not_change_scores() -> None:
    target = _target("galaxy", "Galaxy", 88, direction="Sud")
    low = _compare(
        [target],
        confidence=RecommendationConfidence(weather_confidence=0.1, viirs_confidence=0.0),
    )
    high = _compare(
        [target],
        confidence=RecommendationConfidence(weather_confidence=1.0, viirs_confidence=1.0),
    )

    assert _confidence(low, "galaxy")["value"] < _confidence(high, "galaxy")["value"]
    assert _confidence(low, "galaxy")["score_factor"] is False
    assert _confidence(low, "galaxy")["score_effect"] == pytest.approx(0.0)
    assert _legacy_contribution(low, "galaxy") == pytest.approx(_legacy_contribution(high, "galaxy"))
    assert _observable(low, "galaxy") == pytest.approx(_observable(high, "galaxy"))
    assert _practical(low, "galaxy") == pytest.approx(_practical(high, "galaxy"))


def test_invisible_and_missing_direction_candidates_are_marked_unavailable() -> None:
    invisible = _target("hidden", "Galaxy", 88, direction="Sud", visible=False)
    no_direction = _target("no-direction", "Galaxy", 82, direction="n/d")
    comparison = _compare([invisible, no_direction])

    assert _legacy_target(comparison, "hidden")["available"] is False
    assert _legacy_target(comparison, "hidden")["reason"] == "not_visible"
    assert _legacy_target(comparison, "no-direction")["available"] is False
    assert _legacy_target(comparison, "no-direction")["reason"] == "missing_direction"
    assert comparison["metadata"]["ranked_target_count"] == 0
    assert comparison["rankings"]["legacy_direction"] == []


def test_sky_compass_nsom_comparison_does_not_mutate_or_wire_runtime_outputs() -> None:
    targets = [
        _target("planet", "Pianeta", 84, direction="Est"),
        _target("galaxy", "Galaxy", 88, direction="Sud"),
    ]
    plan = [_plan_item(targets[1])]
    before = deepcopy((targets, plan))

    _compare(targets, night_plan=plan, best_object=targets[1])

    assert (targets, plan) == before
    app_controller = (Path(__file__).parents[1] / "app" / "viewmodels" / "app_controller.py").read_text(
        encoding="utf-8"
    )
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (Path(__file__).parents[1] / "app" / "ui").rglob("*.qml")
    )
    assert "SkyCompassNsomComparisonService" not in app_controller
    assert "sky_compass_nsom_comparison" not in app_controller
    assert "SkyCompassNsomComparisonService" not in qml_text
    assert "sky_compass_nsom_comparison" not in qml_text


def _compare(
    targets: list[CelestialObject],
    *,
    night_plan: list[NightPlanItem] | None = None,
    best_object: CelestialObject | None = None,
    weather: WeatherSummary | None = None,
    sky_quality: SkyQuality | None = None,
    telescope: Telescope | None = None,
    moon: MoonSummary | None = None,
    confidence: RecommendationConfidence | None = None,
    has_location: bool = True,
    caution_text: str = "",
) -> dict[str, object]:
    return SkyCompassNsomComparisonService().compare(
        targets,
        night_plan or [],
        best_object,
        weather=weather or _weather(88),
        sky_quality=sky_quality or _sky_quality(3),
        telescope=telescope or _telescope(),
        moon=moon or _moon(10),
        confidence=confidence,
        has_location=has_location,
        caution_text=caution_text,
    )


def _entry(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return next(item for item in comparison["items"] if item["object_id"] == object_id)


def _direction_group(comparison: dict[str, object], direction: str) -> dict[str, object]:
    return next(item for item in comparison["direction_groups"] if item["direction"] == direction)


def _legacy_target(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return _entry(comparison, object_id)["legacy"]["sky_compass_target"]


def _environment(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return _entry(comparison, object_id)["nsom"]["observation_environment"]


def _ownership(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return _entry(comparison, object_id)["nsom"]["ownership"]


def _confidence(comparison: dict[str, object], object_id: str) -> dict[str, object]:
    return _entry(comparison, object_id)["nsom"]["recommendation_confidence"]


def _effective(comparison: dict[str, object], object_id: str) -> float:
    return float(_entry(comparison, object_id)["nsom"]["effective_observability"]["value"])


def _observable(comparison: dict[str, object], object_id: str) -> float:
    return float(_entry(comparison, object_id)["nsom"]["observable_target_value"]["value"])


def _practical(comparison: dict[str, object], object_id: str) -> float:
    return float(_entry(comparison, object_id)["nsom"]["practical_target_value"]["value"])


def _legacy_contribution(comparison: dict[str, object], object_id: str) -> float:
    return float(_legacy_target(comparison, object_id)["direction_score_contribution"])


def _target(
    object_id: str,
    object_type: str,
    score: int,
    *,
    direction: str,
    visible: bool = True,
    magnitude: str = "8.0",
    difficulty: str = "Media",
) -> CelestialObject:
    return CelestialObject(
        id=object_id,
        name=object_id.title(),
        object_type=object_type,
        image="",
        magnitude=magnitude,
        distance="",
        max_altitude="45 gradi",
        direction=direction,
        best_time="21:00",
        observing_window="21:00 - 02:00",
        notes="Fixture",
        recommended_setup="Mak 127 + 16 mm",
        visibility_class="",
        azimuth="180 gradi",
        time_above_horizon="3 h",
        visible=visible,
        score=score,
        score_label="Fixture",
        difficulty=difficulty,
        recommended_setup_type="telescope",
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


def _weather(
    score: int,
    *,
    cloud_cover: int = 10,
    precipitation_probability: int = 0,
) -> WeatherSummary:
    return WeatherSummary(
        score="Fixture",
        score_value=score,
        explanation="Fixture",
        cloud_cover=cloud_cover,
        precipitation_probability=precipitation_probability,
        wind_kmh=5,
        humidity=50,
        temperature_c=12,
        alert="",
    )


def _sky_quality(bortle: int, radiance: float | None = None) -> SkyQuality:
    return SkyQuality(
        bortle_class=bortle,
        limiting_magnitude=5.5,
        sky_brightness=19.0,
        source="Fixture",
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


def _telescope(
    *,
    name: str = "Mak 127",
    aperture_mm: int = 127,
    focal_length_mm: int = 1500,
    mount: str = "manual",
) -> Telescope:
    return Telescope(
        id=name.lower().replace(" ", "-"),
        name=name,
        aperture_mm=aperture_mm,
        focal_length_mm=focal_length_mm,
        optical_type="Reflector",
        mount=mount,
    )
